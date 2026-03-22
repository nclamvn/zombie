"""
Simulation Engine Protocol
Abstracts the multi-agent simulation backend — OASIS, custom engines, etc.
"""

from typing import Protocol, Dict, Any, List, Optional, Callable, runtime_checkable
from ..models.simulation import (
    SimulationConfig,
    AgentProfile,
    SimulationRound,
    AgentAction,
    SimulationStatus,
)


@runtime_checkable
class SimulationEngine(Protocol):
    """
    Abstract simulation engine interface.
    
    Decouples the kernel from OASIS/CAMEL or any specific simulation framework.
    Enables custom engines (supply chain, social matching, financial, etc.)
    """
    
    def initialize(
        self,
        config: SimulationConfig,
        agents: List[AgentProfile],
        working_dir: str,
    ) -> str:
        """
        Initialize a simulation instance.
        
        Args:
            config: Simulation parameters (rounds, platforms, events, timing)
            agents: List of agent profiles with personas
            working_dir: Directory for simulation data/logs
            
        Returns:
            Simulation instance ID
        """
        ...
    
    def start(
        self,
        sim_id: str,
        round_callback: Optional[Callable[[SimulationRound], None]] = None,
    ) -> None:
        """
        Start running the simulation.
        
        Args:
            sim_id: Simulation instance ID
            round_callback: Called after each round completes
        """
        ...
    
    def pause(self, sim_id: str) -> None:
        """Pause a running simulation."""
        ...
    
    def resume(self, sim_id: str) -> None:
        """Resume a paused simulation."""
        ...
    
    def stop(self, sim_id: str) -> None:
        """Stop and terminate a simulation."""
        ...
    
    def get_status(self, sim_id: str) -> SimulationStatus:
        """Get current simulation status."""
        ...
    
    def get_round_data(self, sim_id: str, round_num: int) -> SimulationRound:
        """Get data for a specific round."""
        ...
    
    def get_all_actions(self, sim_id: str) -> List[AgentAction]:
        """Get all agent actions across all rounds."""
        ...
    
    def inject_event(self, sim_id: str, event: Dict[str, Any]) -> None:
        """
        Dynamically inject an event into the running simulation.
        
        Args:
            sim_id: Target simulation
            event: Event data (type, content, affected_agents, etc.)
        """
        ...
    
    def chat_with_agent(
        self,
        sim_id: str,
        agent_id: int,
        message: str,
    ) -> str:
        """
        Chat with a specific agent in the simulation.
        
        Args:
            sim_id: Simulation instance
            agent_id: Target agent
            message: User message
            
        Returns:
            Agent's response
        """
        ...
    
    def cleanup(self, sim_id: str) -> None:
        """Clean up simulation resources."""
        ...
