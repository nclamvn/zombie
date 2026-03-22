"""
Mock Simulation Engine — For testing and graph-only analysis.

Generates synthetic agent actions based on profiles and config,
without requiring OASIS or any external simulation framework.
"""

import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable

from core.models.simulation import (
    SimulationConfig,
    AgentProfile,
    SimulationRound,
    AgentAction,
    SimulationStatus,
)


# Default social media actions
TWITTER_ACTIONS = ["CREATE_POST", "LIKE_POST", "REPOST", "FOLLOW", "DO_NOTHING", "QUOTE_POST"]
REDDIT_ACTIONS = ["CREATE_POST", "CREATE_COMMENT", "LIKE_POST", "DISLIKE_POST", "DO_NOTHING"]


class MockSimulationEngine:
    """
    Mock simulation engine for testing and quick prototyping.
    
    Generates realistic-looking agent actions based on:
    - Agent activity_level and influence_score
    - Time-of-day activity patterns
    - Scheduled events
    """
    
    def __init__(self):
        self._simulations: Dict[str, Dict[str, Any]] = {}
    
    def initialize(
        self,
        config: SimulationConfig,
        agents: List[AgentProfile],
        working_dir: str,
    ) -> str:
        sim_id = config.sim_id or f"mock_{random.randint(1000, 9999)}"
        self._simulations[sim_id] = {
            "config": config,
            "agents": agents,
            "working_dir": working_dir,
            "status": SimulationStatus.IDLE,
            "rounds": [],
        }
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
            sim_hour = (start_hour + (round_num - 1) * config.time_config.hours_per_round) % 24
            activity_mult = config.time_config.activity_pattern.get(sim_hour, 0.5)
            
            # Check for events this round
            active_events = [
                e for e in config.events
                if e.trigger_round == round_num
            ]
            event_boost = 1.5 if active_events else 1.0
            
            # Generate actions for each agent
            actions = []
            active_ids = []
            
            for agent in agents:
                # Decide if agent is active this round
                activity_chance = agent.activity_level * activity_mult * event_boost
                if random.random() > activity_chance:
                    continue
                
                active_ids.append(agent.agent_id)
                
                # Pick action type based on influence
                platform = agent.platforms[0] if agent.platforms else "twitter"
                action_pool = TWITTER_ACTIONS if platform == "twitter" else REDDIT_ACTIONS
                
                # Higher influence → more content creation
                if agent.influence_score > 0.7 and random.random() < 0.6:
                    action_type = "CREATE_POST"
                elif random.random() < 0.3:
                    action_type = "DO_NOTHING"
                else:
                    action_type = random.choice(action_pool)
                
                action = AgentAction(
                    round_num=round_num,
                    timestamp=(start_time + timedelta(hours=round_num - 1)).isoformat(),
                    platform=platform,
                    agent_id=agent.agent_id,
                    agent_name=agent.name,
                    action_type=action_type,
                    action_args={"simulated_hour": sim_hour},
                    result=self._generate_content(agent, action_type, active_events),
                    success=True,
                )
                actions.append(action)
            
            # Build platform stats
            platform_stats: Dict[str, int] = {}
            for a in actions:
                platform_stats[a.platform] = platform_stats.get(a.platform, 0) + 1
            
            round_data = SimulationRound(
                round_num=round_num,
                start_time=(start_time + timedelta(hours=round_num - 1)).isoformat(),
                end_time=(start_time + timedelta(hours=round_num)).isoformat(),
                simulated_hour=sim_hour,
                actions=actions,
                active_agent_ids=active_ids,
                platform_stats=platform_stats,
            )
            
            sim["rounds"].append(round_data)
            
            if round_callback:
                round_callback(round_data)
        
        sim["status"] = SimulationStatus.COMPLETED
    
    def pause(self, sim_id: str) -> None:
        self._simulations[sim_id]["status"] = SimulationStatus.PAUSED
    
    def resume(self, sim_id: str) -> None:
        self._simulations[sim_id]["status"] = SimulationStatus.RUNNING
    
    def stop(self, sim_id: str) -> None:
        self._simulations[sim_id]["status"] = SimulationStatus.STOPPED
    
    def get_status(self, sim_id: str) -> SimulationStatus:
        return self._simulations[sim_id]["status"]
    
    def get_round_data(self, sim_id: str, round_num: int) -> SimulationRound:
        rounds = self._simulations[sim_id]["rounds"]
        for r in rounds:
            if r.round_num == round_num:
                return r
        raise ValueError(f"Round {round_num} not found")
    
    def get_all_actions(self, sim_id: str) -> List[AgentAction]:
        actions = []
        for r in self._simulations[sim_id]["rounds"]:
            actions.extend(r.actions)
        return actions
    
    def inject_event(self, sim_id: str, event: Dict[str, Any]) -> None:
        pass  # Mock: no-op
    
    def chat_with_agent(self, sim_id: str, agent_id: int, message: str) -> str:
        agents = self._simulations[sim_id]["agents"]
        agent = next((a for a in agents if a.agent_id == agent_id), None)
        if not agent:
            return f"Agent {agent_id} not found."
        return (
            f"[Mock response from {agent.name}] "
            f"As a {agent.personality} {agent.entity_type}, "
            f"my stance is: {agent.stance}. "
            f"Regarding your question: I would need to think about that."
        )
    
    def cleanup(self, sim_id: str) -> None:
        self._simulations.pop(sim_id, None)
    
    def _generate_content(
        self,
        agent: AgentProfile,
        action_type: str,
        events: list,
    ) -> str:
        """Generate mock content for content-creation actions."""
        if action_type not in ("CREATE_POST", "QUOTE_POST", "CREATE_COMMENT"):
            return ""
        
        event_text = ""
        if events:
            event_text = f" regarding {events[0].name}"
        
        return (
            f"[{agent.name}] As someone with expertise in "
            f"{', '.join(agent.expertise[:2]) if agent.expertise else 'this area'}, "
            f"I believe{event_text}: {agent.stance or 'this is worth discussing.'}"
        )
