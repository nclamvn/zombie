"""
Report Generator Protocol
Abstracts the ReACT-based report generation pipeline.
"""

from typing import Protocol, Dict, Any, List, Optional, Callable, runtime_checkable
from ..models.report import ReportOutline, ReportSection


@runtime_checkable
class ReportGenerator(Protocol):
    """
    Abstract report generator interface.
    
    Implements ReACT (Reasoning + Acting) pattern:
    1. Plan report outline based on simulation results
    2. Generate each section with tool-augmented reasoning
    3. Reflect and refine
    """
    
    def plan_outline(
        self,
        requirement: str,
        simulation_summary: Dict[str, Any],
    ) -> ReportOutline:
        """Plan the report structure."""
        ...
    
    def generate_section(
        self,
        section: ReportSection,
        outline: ReportOutline,
        graph_id: str,
        simulation_summary: Dict[str, Any],
    ) -> str:
        """Generate a single report section using ReACT."""
        ...
    
    def generate_full_report(
        self,
        requirement: str,
        graph_id: str,
        simulation_summary: Dict[str, Any],
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> str:
        """Generate the complete report end-to-end."""
        ...
    
    def chat(
        self,
        message: str,
        report_content: str,
        graph_id: str,
    ) -> str:
        """Interactive chat about the report (post-generation)."""
        ...
