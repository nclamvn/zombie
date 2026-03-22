"""
Graph Store Protocol
Abstracts the knowledge graph backend — Zep, Neo4j, NetworkX, etc.
"""

from typing import Protocol, Dict, Any, List, Optional, Callable, runtime_checkable
from ..models.ontology import Ontology
from ..models.graph import Node, Edge, GraphInfo


@runtime_checkable
class GraphStore(Protocol):
    """
    Abstract knowledge graph store interface.
    
    Decouples the kernel from any specific graph database.
    Current impl: Zep Cloud. Future: Neo4j, local NetworkX, etc.
    """
    
    def create_graph(self, name: str, description: str = "") -> str:
        """
        Create a new graph instance.
        
        Args:
            name: Human-readable graph name
            description: Optional description
            
        Returns:
            Graph ID (unique identifier)
        """
        ...
    
    def set_ontology(self, graph_id: str, ontology: Ontology) -> None:
        """
        Set the ontology (schema) for a graph.
        
        Args:
            graph_id: Target graph
            ontology: Entity types + edge types definition
        """
        ...
    
    def add_episodes(
        self,
        graph_id: str,
        texts: List[str],
        batch_size: int = 3,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> List[str]:
        """
        Add text episodes to the graph for entity/relation extraction.
        
        Args:
            graph_id: Target graph
            texts: List of text chunks
            batch_size: How many chunks per batch
            progress_callback: Optional (message, progress_0_to_1) callback
            
        Returns:
            List of episode UUIDs
        """
        ...
    
    def wait_for_processing(
        self,
        episode_uuids: List[str],
        timeout: int = 600,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> None:
        """
        Wait for all episodes to be processed.
        
        Args:
            episode_uuids: Episodes to wait for
            timeout: Max wait time in seconds
            progress_callback: Optional progress callback
        """
        ...
    
    def get_graph_info(self, graph_id: str) -> GraphInfo:
        """Get summary info about a graph (node/edge counts, entity types)."""
        ...
    
    def get_nodes(self, graph_id: str) -> List[Node]:
        """Get all nodes in a graph."""
        ...
    
    def get_edges(self, graph_id: str) -> List[Edge]:
        """Get all edges in a graph."""
        ...
    
    def search(
        self,
        graph_id: str,
        query: str,
        limit: int = 10,
        include_expired: bool = False,
    ) -> Dict[str, Any]:
        """
        Search the graph for facts/entities matching a query.
        
        Args:
            graph_id: Target graph
            query: Natural language search query
            limit: Max results
            include_expired: Whether to include temporally expired facts
            
        Returns:
            Dict with 'facts', 'edges', 'nodes' lists
        """
        ...
    
    def delete_graph(self, graph_id: str) -> None:
        """Delete a graph and all its data."""
        ...
