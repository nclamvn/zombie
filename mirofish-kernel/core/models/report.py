"""
Report Models — ReACT Report Generation Data Structures
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class ReportStatus(str, Enum):
    """Report generation status."""
    PLANNING = "planning"
    GENERATING = "generating"
    REFLECTING = "reflecting"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ReportSection:
    """A single section of a report."""
    index: int
    title: str
    description: str = ""       # What this section should cover
    content: str = ""           # Generated content (markdown)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)  # Tools used
    reflections: List[str] = field(default_factory=list)
    status: ReportStatus = ReportStatus.PLANNING
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "title": self.title,
            "description": self.description,
            "content": self.content,
            "tool_calls_count": len(self.tool_calls),
            "reflections_count": len(self.reflections),
            "status": self.status.value,
        }


@dataclass
class ReportOutline:
    """Planned structure for a report."""
    title: str
    summary: str = ""
    sections: List[ReportSection] = field(default_factory=list)
    requirement: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "summary": self.summary,
            "sections": [s.to_dict() for s in self.sections],
            "requirement": self.requirement,
        }
    
    @property
    def total_sections(self) -> int:
        return len(self.sections)
    
    @property
    def completed_sections(self) -> int:
        return sum(1 for s in self.sections if s.status == ReportStatus.COMPLETED)
