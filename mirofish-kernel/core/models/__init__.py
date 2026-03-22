"""
MiroFish Kernel — Domain Models
Pure dataclasses with zero external dependencies.
"""

from .ontology import EntityType, EdgeType, Ontology, OntologyAttribute
from .graph import Node, Edge, GraphInfo
from .simulation import (
    SimulationConfig,
    AgentProfile,
    AgentAction,
    SimulationRound,
    SimulationStatus,
    SimulationState,
    PlatformType,
    TimeConfig,
    EventConfig,
)
from .report import ReportOutline, ReportSection, ReportStatus
from .project import Project, ProjectStatus, ProjectPhase

__all__ = [
    "EntityType", "EdgeType", "Ontology", "OntologyAttribute",
    "Node", "Edge", "GraphInfo",
    "SimulationConfig", "AgentProfile", "AgentAction", "SimulationRound",
    "SimulationStatus", "SimulationState", "PlatformType", "TimeConfig", "EventConfig",
    "ReportOutline", "ReportSection", "ReportStatus",
    "Project", "ProjectStatus", "ProjectPhase",
]
