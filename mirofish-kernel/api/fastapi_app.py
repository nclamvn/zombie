"""
MiroFish Kernel — Full REST API (TIP-01)

12 endpoints covering the complete pipeline lifecycle.
Thin adapter: all logic lives in the kernel, API is just HTTP mapping.

Usage:
    cd mirofish-kernel
    uvicorn api.fastapi_app:app --reload --port 5001
"""

import os
import threading
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
except ImportError:
    raise ImportError("FastAPI required: pip install mirofish-kernel[fastapi]")

from core import PipelineOrchestrator
from core.pipeline.seed_processor import SeedProcessor
from core.pipeline.ontology_designer import OntologyDesigner
from core.pipeline.graph_builder import GraphBuilder
from core.pipeline.config_generator import ConfigGenerator
from core.pipeline.profile_generator import ProfileGenerator
from core.pipeline.report_agent import ReportAgent
from core.pipeline.retrieval_tools import RetrievalTools
from core.pipeline.simulation_orchestrator import SimulationOrchestrator
from core.models.project import Project, ProjectPhase
from core.tools.logger import get_logger

logger = get_logger("mirofish.api")


# ─── Request/Response Models ──────────────────────────────────

class CreateProjectRequest(BaseModel):
    name: str = "MiroFish Analysis"
    requirement: str
    text: str

class ChatRequest(BaseModel):
    message: str

class RunPipelineRequest(BaseModel):
    """Run full pipeline in one shot."""
    name: str = "MiroFish Analysis"
    requirement: str
    text: str

class ApiResponse(BaseModel):
    status: str = "ok"
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ─── In-memory state (Phase 1 — replaced by PostgreSQL in TIP-04) ──

@dataclass
class ProjectState:
    """Extended project state tracking pipeline artifacts."""
    project: Project
    seed_result: Optional[Dict[str, Any]] = None
    ontology: Optional[Any] = None
    graph_result: Optional[Any] = None
    sim_config: Optional[Any] = None
    profiles: Optional[List[Any]] = None
    sim_state: Optional[Any] = None
    sim_summary: Optional[Dict[str, Any]] = None
    report: Optional[str] = None


# ─── App Setup ─────────────────────────────────────────────────

pipeline: Optional[PipelineOrchestrator] = None
project_states: Dict[str, ProjectState] = {}


def _get_pipeline() -> PipelineOrchestrator:
    if not pipeline:
        raise HTTPException(503, "Pipeline not initialized")
    return pipeline


def _get_state(project_id: str) -> ProjectState:
    if project_id not in project_states:
        raise HTTPException(404, f"Project {project_id} not found")
    return project_states[project_id]


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pipeline

    llm_key = os.environ.get("LLM_API_KEY")
    zep_key = os.environ.get("ZEP_API_KEY")

    if not llm_key:
        raise RuntimeError("LLM_API_KEY environment variable required")

    # LLM adapter — try Anthropic first, fallback to OpenAI
    llm_provider = os.environ.get("LLM_PROVIDER", "openai").lower()
    if llm_provider == "anthropic":
        from adapters.llm.anthropic_adapter import AnthropicAdapter
        llm = AnthropicAdapter(
            api_key=llm_key,
            model=os.environ.get("LLM_MODEL_NAME", "claude-sonnet-4-20250514"),
        )
    else:
        from adapters.llm.openai_adapter import OpenAIAdapter
        llm = OpenAIAdapter(
            api_key=llm_key,
            base_url=os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1"),
            model=os.environ.get("LLM_MODEL_NAME", "gpt-4o-mini"),
        )

    # Graph store — Zep if key provided, else mock
    if zep_key:
        from adapters.graph.zep_adapter import ZepGraphAdapter
        graph_store = ZepGraphAdapter(api_key=zep_key)
    else:
        logger.warning("ZEP_API_KEY not set — graph operations will fail")
        graph_store = None

    from adapters.simulation.mock_engine import MockSimulationEngine
    from adapters.memory.local_memory import LocalMemoryStore

    pipeline = PipelineOrchestrator(
        llm=llm,
        graph_store=graph_store,
        simulation_engine=MockSimulationEngine(),
        memory_store=LocalMemoryStore(),
    )

    logger.info(f"API started — LLM: {llm_provider}, Graph: {'zep' if zep_key else 'none'}")
    yield
    pipeline = None


app = FastAPI(
    title="MiroFish Kernel API",
    description="Swarm Intelligence Engine — Full Pipeline REST API",
    version="1.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Health ────────────────────────────────────────────────────

@app.get("/health")
def health():
    p = pipeline
    return {
        "status": "ok",
        "service": "MiroFish Kernel API",
        "pipeline": "ready" if p else "not initialized",
        "projects": len(project_states),
    }


# ═══════════════════════════════════════════════════════════════
# 1. PROJECT CRUD
# ═══════════════════════════════════════════════════════════════

@app.post("/api/projects")
async def create_project(req: CreateProjectRequest):
    """Create a new project and process seed text into chunks."""
    p = _get_pipeline()

    project = p.create_project(req.name, req.text, req.requirement)

    # Process seed immediately
    seed_result = p.seed_processor.process_text(req.text, req.requirement)
    project.raw_text = seed_result["raw_text"]

    state = ProjectState(project=project, seed_result=seed_result)
    project_states[project.project_id] = state

    return ApiResponse(data={
        "project_id": project.project_id,
        "name": project.name,
        "phase": project.phase.value,
        "chunks": len(seed_result["chunks"]),
        "stats": seed_result["stats"],
    })


@app.get("/api/projects")
async def list_projects():
    """List all projects, sorted by most recent first."""
    projects = sorted(
        project_states.values(),
        key=lambda s: s.project.updated_at,
        reverse=True,
    )
    return ApiResponse(data={
        "projects": [
            {
                "project_id": s.project.project_id,
                "name": s.project.name,
                "phase": s.project.phase.value,
                "status": s.project.status.value,
                "requirement": s.project.requirement,
                "created_at": s.project.created_at,
                "updated_at": s.project.updated_at,
                "has_report": s.report is not None,
                "agent_count": len(s.profiles) if s.profiles else 0,
            }
            for s in projects
        ],
        "total": len(projects),
    })


@app.get("/api/projects/{project_id}")
async def get_project(project_id: str):
    """Get full project detail including all artifacts."""
    state = _get_state(project_id)
    proj = state.project

    data = proj.to_dict()
    data["ontology"] = proj.ontology
    data["graph_info"] = proj.graph_info
    data["simulation_config"] = proj.simulation_config
    data["simulation_summary"] = state.sim_summary
    data["has_report"] = state.report is not None
    data["agent_count"] = len(state.profiles) if state.profiles else 0

    return ApiResponse(data=data)


# ═══════════════════════════════════════════════════════════════
# 2. PIPELINE STAGES (step-by-step)
# ═══════════════════════════════════════════════════════════════

@app.post("/api/projects/{project_id}/ontology")
async def design_ontology(project_id: str):
    """Stage 2: Design knowledge graph ontology from seed text."""
    p = _get_pipeline()
    state = _get_state(project_id)

    if not state.seed_result:
        raise HTTPException(400, "Seed not processed — create project first")

    try:
        ontology = p.ontology_designer.design(
            document_texts=[state.seed_result["raw_text"]],
            requirement=state.project.requirement,
        )
        state.ontology = ontology
        state.project.ontology = ontology.to_dict()
        state.project.advance_to(ProjectPhase.ONTOLOGY_DESIGNED)

        return ApiResponse(data={
            "entity_types": [et.to_dict() for et in ontology.entity_types],
            "edge_types": [et.to_dict() for et in ontology.edge_types],
            "analysis_summary": ontology.analysis_summary,
        })
    except Exception as e:
        logger.error(f"Ontology design failed: {e}")
        raise HTTPException(500, f"Ontology design failed: {e}")


@app.post("/api/projects/{project_id}/graph")
async def build_graph(project_id: str):
    """Stage 3: Build knowledge graph from ontology + chunks."""
    p = _get_pipeline()
    state = _get_state(project_id)

    if not state.ontology:
        raise HTTPException(400, "Ontology not designed — run /ontology first")
    if not state.seed_result:
        raise HTTPException(400, "No seed data")

    try:
        graph_result = p.graph_builder.build(
            chunks=state.seed_result["chunks"],
            ontology=state.ontology,
        )

        if not graph_result.success:
            raise HTTPException(500, f"Graph build failed: {graph_result.error}")

        state.graph_result = graph_result
        state.project.graph_id = graph_result.graph_id
        state.project.graph_info = graph_result.graph_info.to_dict()
        state.project.advance_to(ProjectPhase.GRAPH_COMPLETED)

        return ApiResponse(data={
            "graph_id": graph_result.graph_id,
            "graph_info": graph_result.graph_info.to_dict(),
            "chunks_processed": graph_result.chunks_processed,
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Graph build failed: {e}")
        raise HTTPException(500, f"Graph build failed: {e}")


@app.get("/api/projects/{project_id}/graph")
async def get_graph_data(project_id: str):
    """Get knowledge graph nodes and edges."""
    p = _get_pipeline()
    state = _get_state(project_id)

    if not state.project.graph_id:
        raise HTTPException(400, "Graph not built yet")

    graph_id = state.project.graph_id
    try:
        nodes = p.graph_store.get_nodes(graph_id)
        edges = p.graph_store.get_edges(graph_id)
        info = p.graph_store.get_graph_info(graph_id)

        return ApiResponse(data={
            "graph_id": graph_id,
            "nodes": [n.to_dict() for n in nodes],
            "edges": [e.to_dict() for e in edges],
            "info": info.to_dict(),
        })
    except Exception as e:
        logger.error(f"Graph data fetch failed: {e}")
        raise HTTPException(500, f"Failed to fetch graph data: {e}")


@app.post("/api/projects/{project_id}/simulate")
async def start_simulation(project_id: str):
    """Stage 4-6: Generate config, profiles, and run simulation."""
    p = _get_pipeline()
    state = _get_state(project_id)

    if not state.project.graph_id or not state.graph_result:
        raise HTTPException(400, "Graph not built — run /graph first")

    try:
        graph_id = state.project.graph_id
        requirement = state.project.requirement

        # Stage 4: Config
        sim_config = p.config_generator.generate(
            graph_id=graph_id,
            requirement=requirement,
        )
        state.sim_config = sim_config
        state.project.simulation_config = sim_config.to_dict()
        state.project.advance_to(ProjectPhase.CONFIG_GENERATED)

        # Stage 5: Profiles
        agent_configs = sim_config.domain_config.get("agent_configs", [])
        profiles = p.profile_generator.generate_profiles(
            graph_id=graph_id,
            requirement=requirement,
            agent_configs=agent_configs if agent_configs else None,
        )
        state.profiles = profiles

        # Stage 6: Simulation
        if p.sim_orchestrator:
            sim_state = p.sim_orchestrator.run_simulation(
                config=sim_config,
                agents=profiles,
                graph_id=graph_id,
            )
            state.sim_state = sim_state
            state.sim_summary = p.sim_orchestrator.get_simulation_summary(sim_state)
            state.project.simulation_summary = state.sim_summary
            state.project.advance_to(ProjectPhase.SIMULATION_COMPLETED)
        else:
            state.sim_summary = p._build_mock_summary(profiles)
            state.project.simulation_summary = state.sim_summary

        return ApiResponse(data={
            "agent_count": len(profiles),
            "agents": [pr.to_dict() for pr in profiles[:20]],
            "simulation": state.sim_summary,
            "config": sim_config.to_dict(),
        })
    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        raise HTTPException(500, f"Simulation failed: {e}")


@app.get("/api/projects/{project_id}/simulation")
async def get_simulation(project_id: str):
    """Get simulation state and round data."""
    state = _get_state(project_id)

    if not state.sim_summary:
        raise HTTPException(400, "Simulation not run yet")

    data = {
        "summary": state.sim_summary,
        "config": state.project.simulation_config,
    }

    if state.sim_state:
        data["state"] = state.sim_state.to_dict()
        data["rounds"] = [r.to_dict() for r in state.sim_state.rounds]

    return ApiResponse(data=data)


@app.get("/api/projects/{project_id}/agents")
async def get_agents(project_id: str):
    """Get all agent profiles and stats."""
    state = _get_state(project_id)

    if not state.profiles:
        raise HTTPException(400, "Profiles not generated — run /simulate first")

    agents = [p.to_dict() for p in state.profiles]

    # Enrich with simulation stats if available
    if state.sim_state:
        action_counts: Dict[str, int] = {}
        for r in state.sim_state.rounds:
            for a in r.actions:
                action_counts[a.agent_name] = action_counts.get(a.agent_name, 0) + 1

        for agent in agents:
            agent["total_actions"] = action_counts.get(agent["name"], 0)

    return ApiResponse(data={"agents": agents, "total": len(agents)})


# ═══════════════════════════════════════════════════════════════
# 3. REPORT & CHAT
# ═══════════════════════════════════════════════════════════════

@app.post("/api/projects/{project_id}/report")
async def generate_report(project_id: str):
    """Stage 7: Generate prediction report using ReACT agent."""
    p = _get_pipeline()
    state = _get_state(project_id)

    if not state.project.graph_id:
        raise HTTPException(400, "Graph not built")

    sim_summary = state.sim_summary or {"total_rounds": 0, "total_agents": 0, "note": "No simulation"}

    try:
        report = p.report_agent.generate_full_report(
            requirement=state.project.requirement,
            graph_id=state.project.graph_id,
            simulation_summary=sim_summary,
        )
        state.report = report
        state.project.report_content = report
        state.project.advance_to(ProjectPhase.REPORT_COMPLETED)

        return ApiResponse(data={
            "report": report,
            "length": len(report),
        })
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise HTTPException(500, f"Report generation failed: {e}")


@app.get("/api/projects/{project_id}/report")
async def get_report(project_id: str):
    """Get the generated report."""
    state = _get_state(project_id)

    if not state.report:
        raise HTTPException(400, "Report not generated yet — POST /report first")

    return ApiResponse(data={
        "report": state.report,
        "length": len(state.report),
        "project_name": state.project.name,
        "requirement": state.project.requirement,
    })


@app.post("/api/projects/{project_id}/chat")
async def chat_with_report(project_id: str, req: ChatRequest):
    """Chat with the ReportAgent about the generated report."""
    p = _get_pipeline()
    state = _get_state(project_id)

    if not state.report or not state.project.graph_id:
        raise HTTPException(400, "Report not generated — cannot chat")

    try:
        response = p.report_agent.chat(
            message=req.message,
            report_content=state.report,
            graph_id=state.project.graph_id,
        )
        return ApiResponse(data={"response": response, "message": req.message})
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        raise HTTPException(500, f"Chat failed: {e}")


# ═══════════════════════════════════════════════════════════════
# 4. FULL PIPELINE (one-shot)
# ═══════════════════════════════════════════════════════════════

@app.post("/api/predict")
async def predict(req: RunPipelineRequest):
    """Run the full pipeline end-to-end in one call."""
    p = _get_pipeline()

    try:
        result = p.run(
            requirement=req.requirement,
            text=req.text,
            project_name=req.name,
        )

        # Track state for subsequent queries
        project_id = result["project"]["project_id"]
        project = p.get_project(project_id)
        if project:
            state = ProjectState(project=project, report=result.get("report"))
            state.sim_summary = result.get("simulation_summary")
            project_states[project_id] = state

        return ApiResponse(data=result)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        raise HTTPException(500, f"Pipeline failed: {e}")
