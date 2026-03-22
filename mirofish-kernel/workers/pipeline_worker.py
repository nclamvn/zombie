"""
Pipeline Worker — Runs pipeline stages in background thread.

Called by JobManager. Persists results at each stage.
Emits SSE events for real-time dashboard updates.
"""

import logging
from typing import Callable, Optional, Dict, Any

from core.models.project import ProjectPhase
from core.storage.repository import (
    ProjectRepository, OntologyRepository, GraphRepository,
    SimulationRepository, AgentRepository, ReportRepository,
)

logger = logging.getLogger("mirofish.worker")

_project_repo = ProjectRepository()
_ontology_repo = OntologyRepository()
_graph_repo = GraphRepository()
_sim_repo = SimulationRepository()
_agent_repo = AgentRepository()
_report_repo = ReportRepository()


def run_full_pipeline(
    project_id: str,
    job_id: str,
    progress_callback: Callable[[str, float, str], None],
    pipeline,  # PipelineOrchestrator instance
    project_states: dict,  # shared in-memory state
    emit_sse: Optional[Callable] = None,
    ws_broadcast: Optional[Callable] = None,  # WebSocket broadcast function
    ws_flags: Optional[Callable] = None,  # Get WS control flags
):
    """
    Run complete pipeline: seed → ontology → graph → config → profiles → sim → report.

    Args:
        project_id: Target project
        job_id: Job tracking ID
        progress_callback: Called with (stage, progress, message) — raises InterruptedError on cancel
        pipeline: PipelineOrchestrator instance
        project_states: Shared in-memory project_states dict
        emit_sse: Optional function(project_id, event_type, data) for SSE
    """
    def emit(event_type: str, data: dict):
        if emit_sse:
            emit_sse(project_id, event_type, data)
        if ws_broadcast:
            ws_broadcast(project_id, event_type, data)

    def progress(stage: str, pct: float, msg: str):
        progress_callback(stage, pct, msg)
        emit("progress", {"stage": stage, "step": _stage_num(stage), "total_steps": 5, "progress": pct, "message": msg})

    state = project_states.get(project_id)
    if not state:
        raise ValueError(f"Project {project_id} not in memory")

    p = pipeline

    # ── Stage 1: Ontology ──
    progress("ontology", 0.0, "Designing ontology...")
    ontology = p.ontology_designer.design(
        document_texts=[state.seed_result["raw_text"]],
        requirement=state.project.requirement,
    )
    state.ontology = ontology
    state.project.ontology = ontology.to_dict()
    state.project.advance_to(ProjectPhase.ONTOLOGY_DESIGNED)
    _persist_project_state(state)
    _ontology_repo.save(project_id, ontology.to_dict())
    emit("stage_complete", {"stage": "ontology", "entity_types": len(ontology.entity_types), "edge_types": len(ontology.edge_types)})

    progress_callback("ontology", 0.2, "Ontology complete")

    # ── Stage 2: Graph ──
    progress("graph", 0.2, "Building knowledge graph...")

    def graph_progress(msg, pct):
        progress("graph", 0.2 + pct * 0.2, msg)

    graph_result = p.graph_builder.build(
        chunks=state.seed_result["chunks"],
        ontology=ontology,
        progress_callback=graph_progress,
    )
    if not graph_result.success:
        raise RuntimeError(f"Graph build failed: {graph_result.error}")

    state.graph_result = graph_result
    state.project.graph_id = graph_result.graph_id
    state.project.graph_info = graph_result.graph_info.to_dict()
    state.project.advance_to(ProjectPhase.GRAPH_COMPLETED)
    _persist_project_state(state)
    _graph_repo.save(project_id, graph_result.graph_id, graph_result.graph_info.to_dict())
    emit("stage_complete", {"stage": "graph", "graph_id": graph_result.graph_id, "nodes": graph_result.graph_info.node_count, "edges": graph_result.graph_info.edge_count})

    progress_callback("graph", 0.4, "Graph complete")

    # ── Stage 3: Config + Profiles ──
    progress("simulation", 0.4, "Generating simulation config...")
    graph_id = graph_result.graph_id
    requirement = state.project.requirement

    sim_config = p.config_generator.generate(graph_id=graph_id, requirement=requirement)
    state.sim_config = sim_config
    state.project.simulation_config = sim_config.to_dict()
    state.project.advance_to(ProjectPhase.CONFIG_GENERATED)

    progress("simulation", 0.5, "Generating agent profiles...")
    agent_configs = sim_config.domain_config.get("agent_configs", [])
    profiles = p.profile_generator.generate_profiles(
        graph_id=graph_id, requirement=requirement,
        agent_configs=agent_configs if agent_configs else None,
    )
    state.profiles = profiles

    progress_callback("simulation", 0.55, f"{len(profiles)} profiles generated")

    # ── Stage 4: Simulation ──
    progress("simulation", 0.6, f"Running simulation with {len(profiles)} agents...")
    if p.sim_orchestrator:
        import time as _time

        def round_callback(round_data):
            # Emit round start
            emit("round_start", {
                "round_num": round_data.round_num,
                "simulated_hour": round_data.simulated_hour,
                "active_agents_count": len(round_data.active_agent_ids),
            })
            # Emit individual agent actions
            for action in round_data.actions:
                emit("agent_action", {
                    "agent_id": action.agent_id,
                    "agent_name": action.agent_name,
                    "action_type": action.action_type,
                    "content": (action.result or "")[:200],
                    "platform": action.platform,
                    "round_num": round_data.round_num,
                    "timestamp": action.timestamp,
                })
            # Emit round end
            emit("round_end", {
                "round_num": round_data.round_num,
                "stats": round_data.platform_stats,
                "actions_count": len(round_data.actions),
            })
            # Also emit as "round" for SSE compat
            emit("round", {
                "round_num": round_data.round_num,
                "actions_count": len(round_data.actions),
                "active_agents": len(round_data.active_agent_ids),
                "simulated_hour": round_data.simulated_hour,
            })

            # Check pause/speed flags
            if ws_flags:
                # Pause check
                while ws_flags(project_id, "paused", False):
                    _time.sleep(0.5)
                # Speed delay
                speed = ws_flags(project_id, "speed", 1)
                if speed and speed < 5:
                    _time.sleep(max(0, 1.0 / speed - 0.1))

        sim_state = p.sim_orchestrator.run_simulation(
            config=sim_config, agents=profiles, graph_id=graph_id,
            round_callback=round_callback,
        )
        state.sim_state = sim_state
        state.sim_summary = p.sim_orchestrator.get_simulation_summary(sim_state)
    else:
        state.sim_summary = p._build_mock_summary(profiles)

    state.project.simulation_summary = state.sim_summary
    state.project.advance_to(ProjectPhase.SIMULATION_COMPLETED)
    _persist_project_state(state)
    _sim_repo.save_simulation(project_id, {
        "sim_id": sim_config.sim_id or "", "config": sim_config.to_dict(),
        "summary": state.sim_summary, "status": "completed",
        "total_rounds": state.sim_summary.get("total_rounds", 0),
        "total_actions": state.sim_summary.get("total_actions", 0),
    })
    if state.sim_state:
        for r in state.sim_state.rounds:
            _sim_repo.save_round(project_id, r.to_dict())
    _agent_repo.save_profiles(project_id, [pr.to_dict() for pr in profiles])
    emit("stage_complete", {"stage": "simulation", "agents": len(profiles), "rounds": state.sim_summary.get("total_rounds", 0)})

    progress_callback("simulation", 0.8, "Simulation complete")

    # ── Stage 5: Report ──
    progress("report", 0.8, "Generating prediction report...")

    def report_progress(msg, pct):
        progress("report", 0.8 + pct * 0.2, msg)

    report = p.report_agent.generate_full_report(
        requirement=requirement,
        graph_id=graph_id,
        simulation_summary=state.sim_summary,
        progress_callback=report_progress,
    )
    state.report = report
    state.project.report_content = report
    state.project.advance_to(ProjectPhase.REPORT_COMPLETED)
    _persist_project_state(state)
    _report_repo.save(project_id, report)
    emit("stage_complete", {"stage": "report", "length": len(report)})

    # ── Done ──
    emit("complete", {"project_id": project_id, "report_available": True})
    logger.info(f"Pipeline complete for {project_id}")


def _persist_project_state(state):
    """Write project state to DB."""
    proj = state.project
    _project_repo.save({
        "project_id": proj.project_id,
        "name": proj.name,
        "phase": proj.phase.value if hasattr(proj.phase, "value") else proj.phase,
        "status": proj.status.value if hasattr(proj.status, "value") else proj.status,
        "requirement": proj.requirement,
        "raw_text": proj.raw_text or "",
        "created_at": proj.created_at,
    })


def _stage_num(stage: str) -> int:
    return {"ontology": 1, "graph": 2, "simulation": 3, "simulate": 4, "report": 5}.get(stage, 0)
