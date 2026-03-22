"""
Memory Store Protocol
Abstracts agent memory persistence — Zep, Redis, local JSON, etc.
"""

from typing import Protocol, Dict, Any, List, Optional, runtime_checkable


@runtime_checkable
class MemoryStore(Protocol):
    """
    Abstract memory store for agent memories during and after simulation.
    
    Handles temporal memory (what happened when), entity memory (who did what),
    and graph memory updates (syncing simulation results back to knowledge graph).
    """
    
    def store_agent_memory(
        self,
        agent_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[str] = None,
    ) -> str:
        """
        Store a memory entry for an agent.
        
        Args:
            agent_id: Agent identifier
            content: Memory content (action description, observation, etc.)
            metadata: Optional metadata (round, platform, action_type, etc.)
            timestamp: Optional simulated timestamp
            
        Returns:
            Memory entry ID
        """
        ...
    
    def retrieve_agent_memories(
        self,
        agent_id: str,
        query: Optional[str] = None,
        limit: int = 10,
        time_range: Optional[tuple] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve memories for an agent.
        
        Args:
            agent_id: Agent identifier
            query: Optional semantic search query
            limit: Max memories to return
            time_range: Optional (start, end) time filter
            
        Returns:
            List of memory entries
        """
        ...
    
    def sync_to_graph(
        self,
        graph_id: str,
        agent_activities: List[Dict[str, Any]],
        round_num: int,
    ) -> None:
        """
        Sync simulation activities back to the knowledge graph.
        
        Args:
            graph_id: Target graph
            agent_activities: List of agent activity summaries
            round_num: Current simulation round
        """
        ...
    
    def get_agent_summary(self, agent_id: str) -> str:
        """Get a summary of an agent's memory/behavior."""
        ...
    
    def clear_agent_memories(self, agent_id: str) -> None:
        """Clear all memories for an agent."""
        ...
