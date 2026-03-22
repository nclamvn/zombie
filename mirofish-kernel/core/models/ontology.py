"""
Ontology Models — Knowledge Graph Schema Definition

Defines entity types, edge types, and their attributes.
Domain-agnostic: works for social simulation, supply chain, financial, etc.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class OntologyAttribute:
    """A single attribute of an entity or edge type."""
    name: str           # snake_case attribute name
    type: str = "text"  # Attribute type (text, number, boolean, etc.)
    description: str = ""
    required: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "required": self.required,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OntologyAttribute":
        return cls(
            name=data["name"],
            type=data.get("type", "text"),
            description=data.get("description", ""),
            required=data.get("required", False),
        )


@dataclass
class EntityType:
    """An entity type in the ontology (e.g., Person, Organization, MediaOutlet)."""
    name: str               # PascalCase type name
    description: str = ""
    attributes: List[OntologyAttribute] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "attributes": [a.to_dict() for a in self.attributes],
            "examples": self.examples,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EntityType":
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            attributes=[OntologyAttribute.from_dict(a) for a in data.get("attributes", [])],
            examples=data.get("examples", []),
        )


@dataclass
class SourceTarget:
    """Defines which entity types can be connected by an edge type."""
    source: str  # Source entity type name
    target: str  # Target entity type name
    
    def to_dict(self) -> Dict[str, Any]:
        return {"source": self.source, "target": self.target}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SourceTarget":
        return cls(source=data.get("source", "Entity"), target=data.get("target", "Entity"))


@dataclass
class EdgeType:
    """A relationship type in the ontology (e.g., WORKS_AT, FOLLOWS, OPPOSES)."""
    name: str               # UPPER_SNAKE_CASE or descriptive name
    description: str = ""
    attributes: List[OntologyAttribute] = field(default_factory=list)
    source_targets: List[SourceTarget] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "attributes": [a.to_dict() for a in self.attributes],
            "source_targets": [st.to_dict() for st in self.source_targets],
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EdgeType":
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            attributes=[OntologyAttribute.from_dict(a) for a in data.get("attributes", [])],
            source_targets=[SourceTarget.from_dict(st) for st in data.get("source_targets", [])],
        )


@dataclass
class Ontology:
    """
    Complete ontology definition for a knowledge graph.
    
    This is the schema that guides how entities and relationships
    are extracted from seed text and structured in the graph.
    """
    entity_types: List[EntityType] = field(default_factory=list)
    edge_types: List[EdgeType] = field(default_factory=list)
    domain: str = ""          # Domain hint (e.g., "social_media", "supply_chain")
    analysis_summary: str = ""  # LLM's analysis of the input text
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_types": [e.to_dict() for e in self.entity_types],
            "edge_types": [e.to_dict() for e in self.edge_types],
            "domain": self.domain,
            "analysis_summary": self.analysis_summary,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Ontology":
        return cls(
            entity_types=[EntityType.from_dict(e) for e in data.get("entity_types", [])],
            edge_types=[EdgeType.from_dict(e) for e in data.get("edge_types", [])],
            domain=data.get("domain", ""),
            analysis_summary=data.get("analysis_summary", ""),
        )
    
    @property
    def entity_type_names(self) -> List[str]:
        return [e.name for e in self.entity_types]
    
    @property
    def edge_type_names(self) -> List[str]:
        return [e.name for e in self.edge_types]
