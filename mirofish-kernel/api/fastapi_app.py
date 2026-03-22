"""
MiroFish Kernel — Full REST API (TIP-01 + TIP-03 SSE)

14 endpoints + SSE stream covering the complete pipeline lifecycle.
Thin adapter: all logic lives in the kernel, API is just HTTP mapping.

Usage:
    cd mirofish-kernel
    uvicorn api.fastapi_app:app --reload --port 5001
"""

import os
import json
import asyncio
import threading
import time as _time_mod
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

try:
    import psutil as _psutil_mod
except ImportError:
    _psutil_mod = None

try:
    from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import StreamingResponse
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
from core.tools.structured_logger import setup_structured_logging

setup_structured_logging()
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


# ─── SSE Event Bus ─────────────────────────────────────────────

# Per-project event queues for SSE streaming
_event_queues: Dict[str, List[asyncio.Queue]] = {}


def _emit_sse(project_id: str, event_type: str, data: Dict[str, Any]):
    """Push an SSE event to all subscribers of a project."""
    if project_id not in _event_queues:
        return
    msg = f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
    dead = []
    for i, q in enumerate(_event_queues[project_id]):
        try:
            q.put_nowait(msg)
        except asyncio.QueueFull:
            dead.append(i)
    for i in reversed(dead):
        _event_queues[project_id].pop(i)


def _subscribe(project_id: str) -> asyncio.Queue:
    """Subscribe to SSE events for a project."""
    q = asyncio.Queue(maxsize=200)
    _event_queues.setdefault(project_id, []).append(q)
    return q


def _unsubscribe(project_id: str, q: asyncio.Queue):
    """Remove a subscriber."""
    if project_id in _event_queues:
        try:
            _event_queues[project_id].remove(q)
        except ValueError:
            pass
        if not _event_queues[project_id]:
            del _event_queues[project_id]


# ─── Repositories ──────────────────────────────────────────────

from core.storage.database import init_db
from core.storage.repository import (
    ProjectRepository, OntologyRepository, GraphRepository,
    SimulationRepository, AgentRepository, ReportRepository, ChatRepository,
    JobRepository,
)
from workers.job_manager import JobManager
from workers.pipeline_worker import run_full_pipeline
from api.ws_manager import ws_manager

project_repo = ProjectRepository()
ontology_repo = OntologyRepository()
graph_repo = GraphRepository()
sim_repo = SimulationRepository()
agent_repo = AgentRepository()
report_repo = ReportRepository()
chat_repo = ChatRepository()
job_repo = JobRepository()
job_manager: Optional[JobManager] = None


def _persist_project(state: ProjectState):
    """Write-through: persist current project state to DB."""
    proj = state.project
    project_repo.save({
        "project_id": proj.project_id,
        "name": proj.name,
        "phase": proj.phase.value if hasattr(proj.phase, 'value') else proj.phase,
        "status": proj.status.value if hasattr(proj.status, 'value') else proj.status,
        "requirement": proj.requirement,
        "raw_text": proj.raw_text or "",
        "created_at": proj.created_at,
    })


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


def _recover_projects():
    """Load all projects from DB into memory on startup."""
    rows = project_repo.list_all()
    for row in rows:
        pid = row["project_id"]
        # Rebuild minimal Project object
        from core.models.project import Project, ProjectPhase, ProjectStatus
        try:
            phase = ProjectPhase(row.get("phase", "created"))
        except ValueError:
            phase = ProjectPhase.CREATED
        try:
            status_val = ProjectStatus(row.get("status", "active"))
        except ValueError:
            status_val = ProjectStatus.ACTIVE

        project = Project(
            project_id=pid,
            name=row.get("name", ""),
            phase=phase,
            status=status_val,
            raw_text=row.get("raw_text", ""),
            requirement=row.get("requirement", ""),
            created_at=row.get("created_at", ""),
            updated_at=row.get("updated_at", ""),
        )

        state = ProjectState(project=project)

        # Restore ontology
        ont = ontology_repo.get(pid)
        if ont:
            project.ontology = ont

        # Restore graph info
        graph = graph_repo.get(pid)
        if graph:
            project.graph_id = graph.get("graph_id")
            project.graph_info = {
                "graph_id": graph.get("graph_id"),
                "node_count": graph.get("node_count", 0),
                "edge_count": graph.get("edge_count", 0),
                "entity_types": graph.get("entity_types", []),
            }

        # Restore simulation summary
        sim = sim_repo.get_simulation(pid)
        if sim:
            state.sim_summary = sim.get("summary")
            project.simulation_config = sim.get("config")
            project.simulation_summary = sim.get("summary")

        # Restore agent profiles
        profiles_data = agent_repo.get_profiles(pid)
        if profiles_data:
            state.profiles = profiles_data  # stored as list of dicts

        # Restore report
        report_data = report_repo.get(pid)
        if report_data:
            state.report = report_data.get("content")
            project.report_content = report_data.get("content")

        # Restore seed_result stub (we have raw_text)
        if project.raw_text:
            state.seed_result = {"raw_text": project.raw_text, "chunks": [], "stats": {}, "requirement": project.requirement}

        project_states[pid] = state

    logger.info(f"Recovered {len(rows)} projects from database")


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

    # Initialize database, recover state, start job manager
    init_db()
    _recover_projects()
    global job_manager
    job_manager = JobManager()

    logger.info(f"API started — LLM: {llm_provider}, Graph: {'zep' if zep_key else 'none'}")
    yield
    if job_manager:
        job_manager.shutdown(wait=False)
        job_manager = None
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

_startup_time = _time_mod.time()
_health_cache = {"data": None, "ts": 0}


@app.get("/health")
def health():
    """Deep health check with dependency status, latency, and resource usage."""
    now = _time_mod.time()

    # Cache for 10s to avoid hammering LLM
    if _health_cache["data"] and (now - _health_cache["ts"]) < 10:
        return _health_cache["data"]

    checks = {}
    overall = "ok"

    # Database check
    try:
        from core.storage.database import get_session
        from sqlalchemy import text as sa_text
        t0 = _time_mod.time()
        with get_session() as s:
            s.execute(sa_text("SELECT 1"))
        checks["database"] = {"status": "ok", "latency_ms": int((_time_mod.time() - t0) * 1000)}
    except Exception as e:
        checks["database"] = {"status": "error", "error": str(e)[:100]}
        overall = "error"

    # LLM check
    p = pipeline
    if p and hasattr(p.llm, "ping"):
        llm_result = p.llm.ping(timeout=5.0)
        checks["llm"] = {
            **llm_result,
            "provider": p.llm.provider_name,
            "model": p.llm.model_name,
        }
        if llm_result["status"] != "ok" and overall == "ok":
            overall = "degraded"
    elif p:
        checks["llm"] = {"status": "ok", "provider": getattr(p.llm, "provider_name", "unknown"), "model": getattr(p.llm, "model_name", "unknown")}
    else:
        checks["llm"] = {"status": "error", "error": "pipeline not initialized"}
        overall = "degraded"

    # Graph store check
    if p and p.graph_store:
        checks["graph_store"] = {"status": "ok", "type": "zep"}
    else:
        checks["graph_store"] = {"status": "not_configured", "type": "none"}

    # Job queue check
    jm = job_manager
    if jm:
        checks["job_queue"] = {
            "status": "ok",
            "active_jobs": jm.active_count,
            "max_workers": jm._max_workers,
        }
    else:
        checks["job_queue"] = {"status": "error", "error": "not initialized"}
        if overall == "ok":
            overall = "degraded"

    # Memory check
    rss = 0
    if _psutil_mod:
        try:
            rss = _psutil_mod.Process().memory_info().rss // (1024 * 1024)
        except Exception:
            pass
    checks["memory"] = {"rss_mb": rss, "projects_cached": len(project_states)}

    result = {
        "status": overall,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": int(now - _startup_time),
        "checks": checks,
        "version": "1.2.0",
    }

    _health_cache["data"] = result
    _health_cache["ts"] = now
    return result


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
    _persist_project(state)

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
        _persist_project(state)
        ontology_repo.save(project_id, ontology.to_dict())

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
        _persist_project(state)
        graph_repo.save(project_id, graph_result.graph_id, graph_result.graph_info.to_dict())

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

        _persist_project(state)
        sim_repo.save_simulation(project_id, {
            "sim_id": sim_config.sim_id or "",
            "config": sim_config.to_dict(),
            "summary": state.sim_summary,
            "status": "completed",
            "total_rounds": state.sim_summary.get("total_rounds", 0),
            "total_actions": state.sim_summary.get("total_actions", 0),
        })
        # Persist rounds
        if state.sim_state:
            for r in state.sim_state.rounds:
                sim_repo.save_round(project_id, r.to_dict())
        # Persist agent profiles
        agent_repo.save_profiles(project_id, [pr.to_dict() for pr in profiles])

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
        _persist_project(state)
        report_repo.save(project_id, report)

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
        chat_repo.save_message(project_id, "user", req.message)
        chat_repo.save_message(project_id, "agent", response)
        return ApiResponse(data={"response": response, "message": req.message})
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        raise HTTPException(500, f"Chat failed: {e}")


# ═══════════════════════════════════════════════════════════════
# 4. FULL PIPELINE (one-shot)
# ═══════════════════════════════════════════════════════════════

@app.get("/api/projects/{project_id}/chat")
async def get_chat_history(project_id: str):
    """Get chat history for a project (recovered from DB)."""
    history = chat_repo.get_history(project_id)
    return ApiResponse(data={"messages": history, "total": len(history)})


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


# ═══════════════════════════════════════════════════════════════
# 5. SSE STREAMING (TIP-03)
# ═══════════════════════════════════════════════════════════════

@app.get("/api/projects/{project_id}/stream")
async def stream_events(project_id: str):
    """
    SSE stream for real-time pipeline progress.

    Events:
      progress      — { stage, step, total_steps, progress, message }
      stage_complete — { stage, result_keys }
      round         — { round_num, actions_count, active_agents }
      complete      — { project_id, report_available }
      error         — { message, stage }
      ping          — {}
    """
    q = _subscribe(project_id)

    async def event_generator():
        try:
            # Send initial connection event
            yield f"event: connected\ndata: {json.dumps({'project_id': project_id})}\n\n"

            while True:
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield msg
                except asyncio.TimeoutError:
                    # Send keepalive ping every 15s
                    yield f"event: ping\ndata: {json.dumps({'ts': int(asyncio.get_event_loop().time())})}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            _unsubscribe(project_id, q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/projects/{project_id}/run-stream")
async def run_pipeline_with_stream(project_id: str):
    """
    Start the full pipeline as a background job, streaming progress via SSE.

    Prerequisites: project must exist (POST /api/projects first).
    Subscribe to GET /api/projects/{id}/stream to receive progress events.
    Returns immediately with 202 Accepted + job_id.
    """
    p = _get_pipeline()
    state = _get_state(project_id)

    if not state.seed_result:
        raise HTTPException(400, "Seed not processed — create project first")
    if not job_manager:
        raise HTTPException(503, "Job manager not initialized")

    def run_fn(pid, jid, progress_cb):
        run_full_pipeline(
            project_id=pid,
            job_id=jid,
            progress_callback=progress_cb,
            pipeline=p,
            project_states=project_states,
            emit_sse=_emit_sse,
            ws_broadcast=ws_manager.broadcast_sync,
            ws_flags=ws_manager.get_flag,
        )

    job_id = job_manager.submit(project_id, "full_pipeline", run_fn)

    return ApiResponse(data={
        "project_id": project_id,
        "job_id": job_id,
        "message": "Pipeline started — subscribe to /stream for progress",
    })


# ═══════════════════════════════════════════════════════════════
# 6. JOB MANAGEMENT (TIP-05)
# ═══════════════════════════════════════════════════════════════

@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    """Get job status and progress."""
    if not job_manager:
        raise HTTPException(503, "Job manager not initialized")
    job = job_manager.get_status(job_id)
    if not job:
        raise HTTPException(404, f"Job {job_id} not found")
    return ApiResponse(data=job)


@app.delete("/api/jobs/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a queued or running job."""
    if not job_manager:
        raise HTTPException(503, "Job manager not initialized")
    success = job_manager.cancel(job_id)
    if not success:
        raise HTTPException(400, "Job cannot be cancelled (already completed or not found)")
    return ApiResponse(data={"job_id": job_id, "status": "cancelled"})


@app.get("/api/jobs")
async def list_jobs(project_id: str = None):
    """List jobs, optionally filtered by project."""
    if not job_manager:
        raise HTTPException(503, "Job manager not initialized")
    if project_id:
        jobs = job_manager.get_project_jobs(project_id)
    else:
        jobs = job_repo.get_active()
    return ApiResponse(data={"jobs": jobs, "total": len(jobs)})


# ═══════════════════════════════════════════════════════════════
# 7. WEBSOCKET SIMULATION STREAM (TIP-07)
# ═══════════════════════════════════════════════════════════════

@app.websocket("/ws/simulation/{project_id}")
async def simulation_ws(websocket: WebSocket, project_id: str):
    """
    Bidirectional WebSocket for live simulation monitoring + control.

    Server → Client events: agent_action, round_start, round_end,
        event_fired, simulation_status, graph_update
    Client → Server commands: pause, resume, inject_event, set_speed, replay
    """
    # Validate project
    if project_id not in project_states:
        await websocket.close(code=4004, reason="Project not found")
        return

    await ws_manager.connect(project_id, websocket)

    # Attach async send queue for thread-safe broadcasting
    send_queue = asyncio.Queue(maxsize=500)
    websocket._send_queue = send_queue

    try:
        # Send initial status
        state = project_states.get(project_id)
        sim_summary = state.sim_summary if state else {}
        await websocket.send_json({
            "event": "connected",
            "data": {
                "project_id": project_id,
                "clients": ws_manager.client_count(project_id),
                "simulation_status": state.project.phase.value if state else "unknown",
                "paused": ws_manager.get_flag(project_id, "paused", False),
            },
            "ts": datetime.now(timezone.utc).isoformat(),
        })

        # Two concurrent tasks: receive commands + send events
        async def receiver():
            """Handle incoming commands from client."""
            while True:
                try:
                    raw = await websocket.receive_json()
                    cmd = raw.get("command", "")
                    await _handle_ws_command(project_id, cmd, raw, websocket)
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    logger.warning(f"WS receive error: {e}")
                    break

        async def sender():
            """Forward queued events to client."""
            while True:
                try:
                    msg = await asyncio.wait_for(send_queue.get(), timeout=15.0)
                    await websocket.send_json(msg)
                except asyncio.TimeoutError:
                    # Heartbeat ping
                    try:
                        await websocket.send_json({
                            "event": "ping",
                            "data": {},
                            "ts": datetime.now(timezone.utc).isoformat(),
                        })
                    except Exception:
                        break
                except Exception:
                    break

        # Run both tasks, cancel when either finishes
        recv_task = asyncio.create_task(receiver())
        send_task = asyncio.create_task(sender())
        done, pending = await asyncio.wait(
            [recv_task, send_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"WS error for {project_id}: {e}")
    finally:
        ws_manager.disconnect(project_id, websocket)


async def _handle_ws_command(project_id: str, cmd: str, data: dict, ws: WebSocket):
    """Process a client command."""
    if cmd == "pause":
        ws_manager.set_flag(project_id, "paused", True)
        await ws_manager.broadcast(project_id, "simulation_status", {"status": "paused"})
        logger.info(f"Simulation paused: {project_id}")

    elif cmd == "resume":
        ws_manager.set_flag(project_id, "paused", False)
        await ws_manager.broadcast(project_id, "simulation_status", {"status": "running"})
        logger.info(f"Simulation resumed: {project_id}")

    elif cmd == "inject_event":
        event_data = {
            "event_id": f"inj_{_time_mod.time_ns() % 100000}",
            "name": data.get("name", "Injected Event"),
            "content": data.get("content", ""),
            "affected_agent_ids": data.get("affected_agent_ids", []),
        }
        # Store for worker to pick up
        pending = ws_manager.get_flag(project_id, "pending_events") or []
        pending.append(event_data)
        ws_manager.set_flag(project_id, "pending_events", pending)
        await ws_manager.broadcast(project_id, "event_fired", event_data)
        logger.info(f"Event injected: {event_data['name']} into {project_id}")

    elif cmd == "set_speed":
        multiplier = data.get("multiplier", 1)
        ws_manager.set_flag(project_id, "speed", multiplier)
        await ws_manager.broadcast(project_id, "speed_changed", {"multiplier": multiplier})

    elif cmd == "replay":
        since = data.get("since_event_id", 0)
        events = ws_manager.get_replay(project_id, since)
        for evt in events:
            await ws.send_json(evt)

    else:
        await ws.send_json({"event": "error", "data": {"message": f"Unknown command: {cmd}"}})
