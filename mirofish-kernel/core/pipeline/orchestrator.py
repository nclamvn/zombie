"""
Pipeline Orchestrator — Full MiroFish Kernel Pipeline

Ties all stages together into a single entry point:
Seed → Ontology → Graph → Config → Profiles → Simulation → Report

This is the main public API of the kernel.
"""

import uuid
from typing import Dict, Any, List, Optional, Callable

from ..interfaces.llm_provider import LLMProvider
from ..interfaces.graph_store import GraphStore
from ..interfaces.simulation_engine import SimulationEngine
from ..interfaces.memory_store import MemoryStore
from ..models.project import Project, ProjectPhase, ProjectStatus
from ..tools.logger import get_logger

from .seed_processor import SeedProcessor
from .ontology_designer import OntologyDesigner
from .graph_builder import GraphBuilder
from .config_generator import ConfigGenerator
from .profile_generator import ProfileGenerator
from .simulation_orchestrator import SimulationOrchestrator
from .report_agent import ReportAgent
from .retrieval_tools import RetrievalTools

logger = get_logger("mirofish.pipeline")


class PipelineOrchestrator:
    """
    MiroFish Kernel Pipeline Orchestrator.
    
    The main entry point. Composes all pipeline stages and 
    manages the full lifecycle from seed material to prediction report.
    
    Usage:
        pipeline = PipelineOrchestrator(
            llm=OpenAIAdapter(api_key="..."),
            graph_store=ZepAdapter(api_key="..."),
            simulation_engine=OasisAdapter(),
        )
        
        # Full pipeline
        result = pipeline.run(
            file_paths=["seed.pdf"],
            requirement="Predict public reaction to policy X",
        )
        
        # Or step-by-step
        project = pipeline.create_project("My Analysis", "seed text...", "Predict...")
        pipeline.design_ontology(project)
        pipeline.build_graph(project)
        pipeline.generate_config(project)
        pipeline.generate_profiles(project)
        pipeline.run_simulation(project)
        report = pipeline.generate_report(project)
    """
    
    def __init__(
        self,
        llm: LLMProvider,
        graph_store: GraphStore,
        simulation_engine: Optional[SimulationEngine] = None,
        memory_store: Optional[MemoryStore] = None,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        working_dir: str = "/tmp/mirofish",
    ):
        self.llm = llm
        self.graph_store = graph_store
        self.simulation_engine = simulation_engine
        self.memory_store = memory_store
        self.working_dir = working_dir
        
        # Initialize pipeline stages
        self.seed_processor = SeedProcessor(chunk_size, chunk_overlap)
        self.ontology_designer = OntologyDesigner(llm)
        self.graph_builder = GraphBuilder(graph_store)
        self.config_generator = ConfigGenerator(llm, graph_store)
        self.profile_generator = ProfileGenerator(llm, graph_store)
        self.retrieval_tools = RetrievalTools(llm, graph_store)
        self.report_agent = ReportAgent(llm, self.retrieval_tools)
        
        if simulation_engine:
            self.sim_orchestrator = SimulationOrchestrator(
                simulation_engine, memory_store, working_dir
            )
        else:
            self.sim_orchestrator = None
        
        # Active projects
        self._projects: Dict[str, Project] = {}
    
    # ─── Full Pipeline ────────────────────────────────────────────
    
    def run(
        self,
        requirement: str,
        file_paths: Optional[List[str]] = None,
        text: Optional[str] = None,
        project_name: str = "MiroFish Analysis",
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> Dict[str, Any]:
        """
        Run the full pipeline end-to-end.
        
        Args:
            requirement: What to predict/simulate
            file_paths: Seed document files
            text: Or raw seed text
            project_name: Project name
            progress_callback: Overall progress callback
            
        Returns:
            Complete result dict with project, graph, simulation, and report
        """
        def _progress(msg: str, pct: float):
            logger.info(f"[Pipeline {pct:.0%}] {msg}")
            if progress_callback:
                progress_callback(msg, pct)
        
        # Step 1: Process seed
        _progress("Processing seed material...", 0.00)
        project = self.create_project(project_name, text or "", requirement)
        
        if file_paths:
            seed_result = self.seed_processor.process_files(file_paths, requirement)
        elif text:
            seed_result = self.seed_processor.process_text(text, requirement)
        else:
            raise ValueError("Either file_paths or text must be provided")
        
        project.raw_text = seed_result["raw_text"]
        
        # Step 2: Design ontology
        _progress("Designing knowledge graph schema...", 0.10)
        ontology = self.ontology_designer.design(
            document_texts=[seed_result["raw_text"]],
            requirement=requirement,
        )
        project.ontology = ontology.to_dict()
        project.advance_to(ProjectPhase.ONTOLOGY_DESIGNED)
        
        # Step 3: Build graph
        _progress("Building knowledge graph...", 0.20)
        graph_result = self.graph_builder.build(
            chunks=seed_result["chunks"],
            ontology=ontology,
            progress_callback=lambda msg, pct: _progress(msg, 0.20 + pct * 0.20),
        )
        
        if not graph_result.success:
            project.fail(f"Graph build failed: {graph_result.error}")
            return {"project": project.to_dict(), "error": graph_result.error}
        
        project.graph_id = graph_result.graph_id
        project.graph_info = graph_result.graph_info.to_dict()
        project.advance_to(ProjectPhase.GRAPH_COMPLETED)
        
        # Step 4: Generate config
        _progress("Generating simulation config...", 0.40)
        sim_config = self.config_generator.generate(
            graph_id=graph_result.graph_id,
            requirement=requirement,
        )
        project.simulation_config = sim_config.to_dict()
        project.advance_to(ProjectPhase.CONFIG_GENERATED)
        
        # Step 5: Generate profiles
        _progress("Generating agent profiles...", 0.50)
        agent_configs = sim_config.domain_config.get("agent_configs", [])
        profiles = self.profile_generator.generate_profiles(
            graph_id=graph_result.graph_id,
            requirement=requirement,
            agent_configs=agent_configs if agent_configs else None,
            progress_callback=lambda msg, pct: _progress(msg, 0.50 + pct * 0.10),
        )
        
        # Step 6: Run simulation (if engine available)
        sim_summary = {}
        if self.sim_orchestrator:
            _progress("Running simulation...", 0.60)
            sim_state = self.sim_orchestrator.run_simulation(
                config=sim_config,
                agents=profiles,
                graph_id=graph_result.graph_id,
                progress_callback=lambda msg, pct: _progress(msg, 0.60 + pct * 0.20),
            )
            sim_summary = self.sim_orchestrator.get_simulation_summary(sim_state)
            project.simulation_summary = sim_summary
            project.advance_to(ProjectPhase.SIMULATION_COMPLETED)
        else:
            _progress("No simulation engine — skipping to report...", 0.60)
            sim_summary = self._build_mock_summary(profiles)
        
        # Step 7: Generate report
        _progress("Generating prediction report...", 0.80)
        report = self.report_agent.generate_full_report(
            requirement=requirement,
            graph_id=graph_result.graph_id,
            simulation_summary=sim_summary,
            progress_callback=lambda msg, pct: _progress(msg, 0.80 + pct * 0.18),
        )
        project.report_content = report
        project.advance_to(ProjectPhase.REPORT_COMPLETED)
        
        _progress("Pipeline complete!", 1.0)
        
        return {
            "project": project.to_dict(),
            "graph_id": graph_result.graph_id,
            "graph_info": graph_result.graph_info.to_dict(),
            "agent_count": len(profiles),
            "simulation_summary": sim_summary,
            "report": report,
        }
    
    # ─── Step-by-Step API ─────────────────────────────────────────
    
    def create_project(
        self, name: str, text: str, requirement: str
    ) -> Project:
        """Create a new project."""
        project = Project(
            project_id=f"proj_{uuid.uuid4().hex[:12]}",
            name=name,
            raw_text=text,
            requirement=requirement,
        )
        self._projects[project.project_id] = project
        return project
    
    def get_project(self, project_id: str) -> Optional[Project]:
        """Get a project by ID."""
        return self._projects.get(project_id)
    
    def chat_with_report(
        self, project_id: str, message: str
    ) -> str:
        """Chat with the report agent about a completed report."""
        project = self._projects.get(project_id)
        if not project or not project.report_content or not project.graph_id:
            raise ValueError("Project not found or report not generated")
        
        return self.report_agent.chat(
            message=message,
            report_content=project.report_content,
            graph_id=project.graph_id,
        )
    
    # ─── Helpers ──────────────────────────────────────────────────
    
    def _build_mock_summary(self, profiles) -> Dict[str, Any]:
        """Build a mock simulation summary when no engine is available."""
        return {
            "total_rounds": 0,
            "total_actions": 0,
            "total_agents": len(profiles),
            "action_type_distribution": {},
            "top_active_agents": [
                {"name": p.name, "actions": 0} for p in profiles[:5]
            ],
            "note": "No simulation engine configured — report based on graph analysis only",
        }
