"""
Simulation Orchestrator — Stage 6 of the MiroFish Pipeline

Manages the full simulation lifecycle through the SimulationEngine interface.
Handles: initialization, execution, monitoring, memory sync, and cleanup.

Decoupled from OASIS — works with any SimulationEngine adapter.
"""

import os
import uuid
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime

from ..interfaces.simulation_engine import SimulationEngine
from ..interfaces.memory_store import MemoryStore
from ..models.simulation import (
    SimulationConfig,
    AgentProfile,
    SimulationState,
    SimulationStatus,
    SimulationRound,
    AgentAction,
)
from ..tools.logger import get_logger

logger = get_logger("mirofish.pipeline.simulation")


class SimulationOrchestrator:
    """
    Orchestrates multi-agent simulation execution.
    
    Responsibilities:
    - Initialize simulation with config + agent profiles
    - Monitor execution, track rounds and actions
    - Sync agent activities to memory/graph
    - Handle pause/resume/stop lifecycle
    - Aggregate results for report generation
    """
    
    def __init__(
        self,
        engine: SimulationEngine,
        memory_store: Optional[MemoryStore] = None,
        working_dir: str = "/tmp/mirofish_sims",
    ):
        self.engine = engine
        self.memory_store = memory_store
        self.working_dir = working_dir
        self._active_states: Dict[str, SimulationState] = {}
    
    def run_simulation(
        self,
        config: SimulationConfig,
        agents: List[AgentProfile],
        graph_id: Optional[str] = None,
        round_callback: Optional[Callable[[SimulationRound], None]] = None,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> SimulationState:
        """
        Run a complete simulation end-to-end.
        
        Args:
            config: Simulation parameters
            agents: Agent profiles
            graph_id: Optional graph ID for memory sync
            round_callback: Called after each round
            progress_callback: Overall progress callback
            
        Returns:
            Final SimulationState
        """
        # Generate sim_id
        sim_id = config.sim_id or f"sim_{uuid.uuid4().hex[:12]}"
        config.sim_id = sim_id
        
        # Create working directory
        sim_dir = os.path.join(self.working_dir, sim_id)
        os.makedirs(sim_dir, exist_ok=True)
        
        # Initialize state
        state = SimulationState(
            sim_id=sim_id,
            status=SimulationStatus.STARTING,
            total_rounds=config.time_config.max_rounds,
            agents=agents,
            started_at=datetime.now().isoformat(),
        )
        self._active_states[sim_id] = state
        
        if progress_callback:
            progress_callback("Initializing simulation...", 0.05)
        
        try:
            # Initialize engine
            logger.info(f"Initializing simulation {sim_id} with {len(agents)} agents")
            self.engine.initialize(config, agents, sim_dir)
            
            if progress_callback:
                progress_callback("Starting simulation...", 0.10)
            
            # Set up round tracking
            def on_round_complete(round_data: SimulationRound):
                state.rounds.append(round_data)
                state.current_round = round_data.round_num
                
                # Sync memories if available
                if self.memory_store and graph_id:
                    self._sync_round_memories(graph_id, round_data, agents)
                
                # Report progress
                if progress_callback:
                    pct = 0.10 + (state.progress * 0.85)
                    progress_callback(
                        f"Round {round_data.round_num}/{state.total_rounds} "
                        f"({len(round_data.actions)} actions)",
                        pct,
                    )
                
                if round_callback:
                    round_callback(round_data)
            
            # Run simulation
            state.status = SimulationStatus.RUNNING
            self.engine.start(sim_id, round_callback=on_round_complete)
            
            # Mark completed
            state.status = SimulationStatus.COMPLETED
            state.completed_at = datetime.now().isoformat()
            
            if progress_callback:
                progress_callback("Simulation completed", 1.0)
            
            logger.info(
                f"Simulation {sim_id} completed: "
                f"{len(state.rounds)} rounds, {state.total_actions} total actions"
            )
            
        except Exception as e:
            state.status = SimulationStatus.FAILED
            state.error_message = str(e)
            logger.error(f"Simulation {sim_id} failed: {e}")
            raise
        
        return state
    
    def get_state(self, sim_id: str) -> Optional[SimulationState]:
        """Get current simulation state."""
        return self._active_states.get(sim_id)
    
    def get_simulation_summary(self, state: SimulationState) -> Dict[str, Any]:
        """
        Generate a summary of simulation results for report generation.
        
        Returns:
            Summary dict with key metrics, trends, and notable actions
        """
        all_actions = []
        for r in state.rounds:
            all_actions.extend(r.actions)
        
        # Action type distribution
        action_types: Dict[str, int] = {}
        for a in all_actions:
            action_types[a.action_type] = action_types.get(a.action_type, 0) + 1
        
        # Per-agent activity
        agent_activity: Dict[str, int] = {}
        for a in all_actions:
            agent_activity[a.agent_name] = agent_activity.get(a.agent_name, 0) + 1
        
        # Most active agents
        top_agents = sorted(
            agent_activity.items(), key=lambda x: x[1], reverse=True
        )[:10]
        
        # Content creation (posts)
        content_actions = [
            a for a in all_actions 
            if a.action_type in ("CREATE_POST", "QUOTE_POST", "CREATE_COMMENT")
        ]
        
        return {
            "sim_id": state.sim_id,
            "total_rounds": len(state.rounds),
            "total_actions": state.total_actions,
            "total_agents": len(state.agents),
            "action_type_distribution": action_types,
            "top_active_agents": [
                {"name": name, "actions": count} for name, count in top_agents
            ],
            "content_created": len(content_actions),
            "platform_stats": self._aggregate_platform_stats(state.rounds),
            "timeline": [
                {
                    "round": r.round_num,
                    "hour": r.simulated_hour,
                    "actions": len(r.actions),
                }
                for r in state.rounds
            ],
        }
    
    def _aggregate_platform_stats(
        self, rounds: List[SimulationRound]
    ) -> Dict[str, int]:
        """Aggregate actions by platform across all rounds."""
        stats: Dict[str, int] = {}
        for r in rounds:
            for action in r.actions:
                stats[action.platform] = stats.get(action.platform, 0) + 1
        return stats
    
    def _sync_round_memories(
        self,
        graph_id: str,
        round_data: SimulationRound,
        agents: List[AgentProfile],
    ):
        """Sync round activities to memory store."""
        if not self.memory_store:
            return
        
        try:
            activities = []
            for action in round_data.actions:
                activities.append({
                    "agent_id": str(action.agent_id),
                    "agent_name": action.agent_name,
                    "action_type": action.action_type,
                    "content": action.result or "",
                    "platform": action.platform,
                })
            
            self.memory_store.sync_to_graph(
                graph_id=graph_id,
                agent_activities=activities,
                round_num=round_data.round_num,
            )
        except Exception as e:
            logger.warning(f"Memory sync failed for round {round_data.round_num}: {e}")
    
    def cleanup(self, sim_id: str) -> None:
        """Clean up simulation resources."""
        try:
            self.engine.cleanup(sim_id)
        except Exception as e:
            logger.warning(f"Engine cleanup failed: {e}")
        
        self._active_states.pop(sim_id, None)
