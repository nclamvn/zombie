"""
Ray Distributed Simulation Engine — TIP-12

Parallel agent execution using Ray actors. Each agent runs as a
remote actor, enabling 10K+ concurrent agents across multi-GPU/multi-node.

Falls back to ThreadPoolExecutor when Ray is not installed.

Key patterns:
- Fan-out: all agents decide in parallel per round
- Fan-in: collect actions, update environment
- Invocation distance optimization: skip inactive agents
- Configurable: num_workers, batch_size, gpu_fraction
"""

import os
import time
import random
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.models.simulation import (
    SimulationConfig, AgentProfile, SimulationRound,
    AgentAction, SimulationStatus,
)

logger = logging.getLogger("mirofish.adapter.ray_sim")

# Try importing Ray
try:
    import ray
    RAY_AVAILABLE = True
except ImportError:
    RAY_AVAILABLE = False
    logger.info("Ray not installed — using ThreadPool fallback for parallel execution")


# ─── Agent Decision Function ─────────────────────────────────

def _agent_decide(
    agent: AgentProfile,
    round_num: int,
    simulated_hour: int,
    activity_mult: float,
    events: List[Dict],
    llm_config: Optional[Dict] = None,
) -> Optional[AgentAction]:
    """
    Decide what an agent does this round.

    Without LLM: algorithmic decision based on activity_level + influence.
    With LLM: can be extended to call LLM for each agent decision.
    """
    # Activity check
    event_boost = 1.3 if events else 1.0
    if random.random() > agent.activity_level * activity_mult * event_boost:
        return None  # Agent inactive this round

    # Pick platform
    platform = agent.platforms[0] if agent.platforms else "twitter"

    # Pick action type based on influence
    if agent.influence_score > 0.7 and random.random() < 0.5:
        action_type = "CREATE_POST"
    elif random.random() < 0.25:
        action_type = random.choice(["LIKE_POST", "REPOST", "FOLLOW"])
    else:
        action_type = random.choice(["CREATE_POST", "LIKE_POST", "REPOST", "CREATE_COMMENT"])

    # Generate content for content-creating actions
    content = ""
    if action_type in ("CREATE_POST", "QUOTE_POST", "CREATE_COMMENT"):
        event_ref = f" regarding {events[0].get('name', 'current events')}" if events else ""
        content = (
            f"[{agent.name}] As a {agent.entity_type} with expertise in "
            f"{', '.join(agent.expertise[:2]) if agent.expertise else 'this domain'}, "
            f"I believe{event_ref}: {agent.stance or 'this is significant.'}"
        )

    return AgentAction(
        round_num=round_num,
        timestamp=datetime.now().isoformat(),
        platform=platform,
        agent_id=agent.agent_id,
        agent_name=agent.name,
        action_type=action_type,
        action_args={"simulated_hour": simulated_hour},
        result=content,
        success=True,
    )


# ─── Ray Actor (when Ray available) ──────────────────────────

if RAY_AVAILABLE:
    @ray.remote
    class AgentActor:
        """Ray remote actor for a single agent."""

        def __init__(self, profile_dict: Dict, llm_config: Dict = None):
            self.profile = AgentProfile(**{
                k: v for k, v in profile_dict.items()
                if k in AgentProfile.__dataclass_fields__
            })
            self.llm_config = llm_config
            self.memories = []

        def decide(self, round_num, simulated_hour, activity_mult, events):
            action = _agent_decide(
                self.profile, round_num, simulated_hour,
                activity_mult, events, self.llm_config,
            )
            if action:
                self.memories.append(action.to_dict())
            return action.to_dict() if action else None

        def get_memories(self):
            return self.memories


# ─── RaySimulationEngine ─────────────────────────────────────

class RaySimulationEngine:
    """
    Distributed simulation engine using Ray for parallel agent execution.

    When Ray is available: each agent is a Ray actor, fan-out/fan-in per round.
    When Ray is not available: ThreadPoolExecutor with configurable workers.

    Usage:
        engine = RaySimulationEngine(num_workers=4)
        engine.initialize(config, agents, working_dir)
        engine.start(sim_id, round_callback=on_round)
    """

    def __init__(
        self,
        num_workers: int = None,
        batch_size: int = 50,
        gpu_fraction: float = 0.0,
        use_ray: bool = None,
    ):
        self._num_workers = num_workers or int(os.environ.get("RAY_NUM_WORKERS", "4"))
        self._batch_size = batch_size
        self._gpu_fraction = gpu_fraction
        self._use_ray = use_ray if use_ray is not None else RAY_AVAILABLE
        self._simulations: Dict[str, Dict[str, Any]] = {}

        if self._use_ray and RAY_AVAILABLE:
            if not ray.is_initialized():
                ray.init(ignore_reinit_error=True, num_cpus=self._num_workers)
            logger.info(f"RaySimulationEngine initialized — Ray mode, {self._num_workers} workers")
        else:
            self._use_ray = False
            logger.info(f"RaySimulationEngine initialized — ThreadPool mode, {self._num_workers} workers")

    def initialize(
        self,
        config: SimulationConfig,
        agents: List[AgentProfile],
        working_dir: str,
    ) -> str:
        sim_id = config.sim_id or f"ray_{random.randint(10000, 99999)}"

        sim_data = {
            "config": config,
            "agents": agents,
            "working_dir": working_dir,
            "status": SimulationStatus.IDLE,
            "rounds": [],
        }

        # Create Ray actors or keep profiles for ThreadPool
        if self._use_ray and RAY_AVAILABLE:
            actors = []
            for agent in agents:
                actor = AgentActor.remote(agent.to_dict())
                actors.append(actor)
            sim_data["actors"] = actors
        else:
            sim_data["actors"] = None

        self._simulations[sim_id] = sim_data
        logger.info(f"Simulation initialized: {sim_id}, {len(agents)} agents")
        return sim_id

    def start(
        self,
        sim_id: str,
        round_callback: Optional[Callable[[SimulationRound], None]] = None,
    ) -> None:
        sim = self._simulations[sim_id]
        config = sim["config"]
        agents = sim["agents"]
        sim["status"] = SimulationStatus.RUNNING

        start_time = datetime.now()
        start_hour = config.time_config.start_hour

        for round_num in range(1, config.time_config.max_rounds + 1):
            if sim["status"] == SimulationStatus.STOPPED:
                break

            simulated_hour = (start_hour + (round_num - 1) * config.time_config.hours_per_round) % 24
            activity_mult = config.time_config.activity_pattern.get(simulated_hour, 0.5)

            # Get active events for this round
            active_events = [
                {"name": e.name, "content": e.content, "description": e.description}
                for e in config.events if e.trigger_round == round_num
            ]

            # Execute round — parallel
            if self._use_ray and sim["actors"]:
                actions = self._execute_round_ray(
                    sim["actors"], round_num, simulated_hour, activity_mult, active_events
                )
            else:
                actions = self._execute_round_threadpool(
                    agents, round_num, simulated_hour, activity_mult, active_events
                )

            # Build round data
            platform_stats = {}
            active_ids = []
            for a in actions:
                platform_stats[a.platform] = platform_stats.get(a.platform, 0) + 1
                if a.agent_id not in active_ids:
                    active_ids.append(a.agent_id)

            round_data = SimulationRound(
                round_num=round_num,
                start_time=(start_time + timedelta(hours=round_num - 1)).isoformat(),
                end_time=(start_time + timedelta(hours=round_num)).isoformat(),
                simulated_hour=simulated_hour,
                actions=actions,
                active_agent_ids=active_ids,
                platform_stats=platform_stats,
            )

            sim["rounds"].append(round_data)
            if round_callback:
                round_callback(round_data)

        sim["status"] = SimulationStatus.COMPLETED

    def _execute_round_ray(self, actors, round_num, simulated_hour, activity_mult, events):
        """Fan-out to Ray actors, fan-in results."""
        futures = [
            actor.decide.remote(round_num, simulated_hour, activity_mult, events)
            for actor in actors
        ]
        results = ray.get(futures)
        actions = []
        for r in results:
            if r:
                actions.append(AgentAction(**{
                    k: v for k, v in r.items()
                    if k in AgentAction.__dataclass_fields__
                }))
        return actions

    def _execute_round_threadpool(self, agents, round_num, simulated_hour, activity_mult, events):
        """Fan-out via ThreadPoolExecutor, fan-in results."""
        actions = []
        with ThreadPoolExecutor(max_workers=self._num_workers) as pool:
            futures = {
                pool.submit(_agent_decide, agent, round_num, simulated_hour, activity_mult, events): agent
                for agent in agents
            }
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        actions.append(result)
                except Exception as e:
                    logger.warning(f"Agent decision failed: {e}")
        return actions

    # ── Lifecycle methods ────────────────────────────────────

    def pause(self, sim_id: str) -> None:
        self._simulations[sim_id]["status"] = SimulationStatus.PAUSED

    def resume(self, sim_id: str) -> None:
        self._simulations[sim_id]["status"] = SimulationStatus.RUNNING

    def stop(self, sim_id: str) -> None:
        self._simulations[sim_id]["status"] = SimulationStatus.STOPPED

    def get_status(self, sim_id: str) -> SimulationStatus:
        return self._simulations[sim_id]["status"]

    def get_round_data(self, sim_id: str, round_num: int) -> SimulationRound:
        for r in self._simulations[sim_id]["rounds"]:
            if r.round_num == round_num:
                return r
        raise ValueError(f"Round {round_num} not found")

    def get_all_actions(self, sim_id: str) -> List[AgentAction]:
        actions = []
        for r in self._simulations[sim_id]["rounds"]:
            actions.extend(r.actions)
        return actions

    def inject_event(self, sim_id: str, event: Dict[str, Any]) -> None:
        logger.info(f"Event injected into {sim_id}: {event.get('name', '?')}")

    def chat_with_agent(self, sim_id: str, agent_id: int, message: str) -> str:
        agents = self._simulations[sim_id]["agents"]
        agent = next((a for a in agents if a.agent_id == agent_id), None)
        if not agent:
            return f"Agent {agent_id} not found."
        return f"[{agent.name}] As a {agent.entity_type}: {agent.stance or 'I have no strong opinion on this.'}"

    def cleanup(self, sim_id: str) -> None:
        sim = self._simulations.pop(sim_id, None)
        if sim and self._use_ray and sim.get("actors"):
            for actor in sim["actors"]:
                try:
                    ray.kill(actor)
                except Exception:
                    pass
