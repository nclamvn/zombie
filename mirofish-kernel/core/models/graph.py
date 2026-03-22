"""
Graph Models — Knowledge Graph Data Structures

Represents nodes, edges, and graph metadata.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class Node:
    """A node (entity) in the knowledge graph."""
    uuid: str
    name: str
    labels: List[str] = field(default_factory=list)   # Entity type labels
    summary: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "uuid": self.uuid,
            "name": self.name,
            "labels": self.labels,
            "summary": self.summary,
            "attributes": self.attributes,
            "created_at": self.created_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Node":
        return cls(
            uuid=data["uuid"],
            name=data["name"],
            labels=data.get("labels", []),
            summary=data.get("summary", ""),
            attributes=data.get("attributes", {}),
            created_at=data.get("created_at"),
        )
    
    @property
    def primary_label(self) -> str:
        """Get the most specific entity type label (skip generic 'Entity', 'Node')."""
        for label in self.labels:
            if label not in ("Entity", "Node"):
                return label
        return self.labels[0] if self.labels else "Unknown"


@dataclass
class Edge:
    """A relationship (edge/fact) in the knowledge graph."""
    uuid: str
    name: str                       # Relationship type
    fact: str = ""                  # Human-readable fact description
    fact_type: str = ""
    source_node_uuid: str = ""
    target_node_uuid: str = ""
    source_node_name: str = ""
    target_node_name: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None
    valid_at: Optional[str] = None
    invalid_at: Optional[str] = None
    expired_at: Optional[str] = None
    episodes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "uuid": self.uuid,
            "name": self.name,
            "fact": self.fact,
            "fact_type": self.fact_type,
            "source_node_uuid": self.source_node_uuid,
            "target_node_uuid": self.target_node_uuid,
            "source_node_name": self.source_node_name,
            "target_node_name": self.target_node_name,
            "attributes": self.attributes,
            "created_at": self.created_at,
            "valid_at": self.valid_at,
            "invalid_at": self.invalid_at,
            "expired_at": self.expired_at,
            "episodes": self.episodes,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Edge":
        return cls(
            uuid=data.get("uuid", ""),
            name=data.get("name", ""),
            fact=data.get("fact", ""),
            fact_type=data.get("fact_type", ""),
            source_node_uuid=data.get("source_node_uuid", ""),
            target_node_uuid=data.get("target_node_uuid", ""),
            source_node_name=data.get("source_node_name", ""),
            target_node_name=data.get("target_node_name", ""),
            attributes=data.get("attributes", {}),
            created_at=data.get("created_at"),
            valid_at=data.get("valid_at"),
            invalid_at=data.get("invalid_at"),
            expired_at=data.get("expired_at"),
            episodes=data.get("episodes", []),
        )
    
    @property
    def is_active(self) -> bool:
        """Check if this edge/fact is currently active (not expired)."""
        return self.expired_at is None and self.invalid_at is None


@dataclass
class GraphInfo:
    """Summary information about a knowledge graph."""
    graph_id: str
    node_count: int = 0
    edge_count: int = 0
    entity_types: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "entity_types": self.entity_types,
        }


@dataclass
class GraphData:
    """Complete graph data with all nodes and edges."""
    graph_id: str
    nodes: List[Node] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)
    
    @property
    def node_count(self) -> int:
        return len(self.nodes)
    
    @property
    def edge_count(self) -> int:
        return len(self.edges)
    
    @property
    def node_map(self) -> Dict[str, Node]:
        """UUID → Node mapping for quick lookups."""
        return {n.uuid: n for n in self.nodes}
    
    def get_node_by_name(self, name: str) -> Optional[Node]:
        """Find a node by name (case-insensitive)."""
        name_lower = name.lower()
        for node in self.nodes:
            if node.name.lower() == name_lower:
                return node
        return None
    
    def get_edges_for_node(self, node_uuid: str) -> List[Edge]:
        """Get all edges connected to a node."""
        return [
            e for e in self.edges
            if e.source_node_uuid == node_uuid or e.target_node_uuid == node_uuid
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "node_count": self.node_count,
            "edge_count": self.edge_count,
        }
