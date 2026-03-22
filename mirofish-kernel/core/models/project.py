"""
Project Models — Pipeline State Machine

Tracks the state of a MiroFish pipeline run from seed to report.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime


class ProjectPhase(str, Enum):
    """Pipeline phases in order."""
    CREATED = "created"
    SEED_UPLOADED = "seed_uploaded"
    ONTOLOGY_DESIGNED = "ontology_designed"
    GRAPH_BUILDING = "graph_building"
    GRAPH_COMPLETED = "graph_completed"
    CONFIG_GENERATED = "config_generated"
    SIMULATING = "simulating"
    SIMULATION_COMPLETED = "simulation_completed"
    REPORTING = "reporting"
    REPORT_COMPLETED = "report_completed"
    INTERACTIVE = "interactive"
    FAILED = "failed"


class ProjectStatus(str, Enum):
    """High-level project status."""
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


@dataclass
class ProjectFile:
    """An uploaded seed file."""
    filename: str
    path: str
    size: int = 0
    mime_type: str = ""


@dataclass
class Project:
    """
    Complete project state.
    
    Tracks the full lifecycle of a MiroFish pipeline run.
    Persists to JSON for recovery.
    """
    project_id: str
    name: str
    phase: ProjectPhase = ProjectPhase.CREATED
    status: ProjectStatus = ProjectStatus.ACTIVE
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Seed data
    files: List[ProjectFile] = field(default_factory=list)
    raw_text: str = ""
    requirement: str = ""       # What to predict/simulate
    
    # Pipeline artifacts (populated as phases complete)
    ontology: Optional[Dict[str, Any]] = None
    graph_id: Optional[str] = None
    graph_info: Optional[Dict[str, Any]] = None
    simulation_config: Optional[Dict[str, Any]] = None
    simulation_id: Optional[str] = None
    simulation_summary: Optional[Dict[str, Any]] = None
    report_id: Optional[str] = None
    report_content: Optional[str] = None
    
    # Error tracking
    error_message: Optional[str] = None
    error_phase: Optional[str] = None
    
    def advance_to(self, phase: ProjectPhase) -> None:
        """Advance to the next phase."""
        self.phase = phase
        self.updated_at = datetime.now().isoformat()
    
    def fail(self, message: str) -> None:
        """Mark project as failed."""
        self.error_message = message
        self.error_phase = self.phase.value
        self.phase = ProjectPhase.FAILED
        self.status = ProjectStatus.FAILED
        self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "name": self.name,
            "phase": self.phase.value,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "requirement": self.requirement,
            "graph_id": self.graph_id,
            "graph_info": self.graph_info,
            "simulation_id": self.simulation_id,
            "report_id": self.report_id,
            "error_message": self.error_message,
            "error_phase": self.error_phase,
            "files_count": len(self.files),
        }
