"""
Repository Layer — Clean interface between API and database.

All methods accept/return plain dicts. No SQLAlchemy models leak out.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from .database import get_session
from .models import (
    ProjectModel, OntologyModel, GraphModel,
    SimulationModel, SimulationRoundModel, AgentProfileModel,
    ReportModel, ChatMessageModel, JobModel,
)


def _now():
    return datetime.now(timezone.utc)


# ═══════════════════════════════════════════════════════════════
# ProjectRepository
# ═══════════════════════════════════════════════════════════════

class ProjectRepository:
    """CRUD for projects and their pipeline state."""

    def save(self, data: Dict[str, Any]) -> None:
        """Upsert a project. data must have 'project_id'."""
        with get_session() as s:
            existing = s.query(ProjectModel).filter_by(id=data["project_id"]).first()
            if existing:
                existing.name = data.get("name", existing.name)
                existing.phase = data.get("phase", existing.phase)
                existing.status = data.get("status", existing.status)
                existing.requirement = data.get("requirement", existing.requirement)
                existing.raw_text = data.get("raw_text", existing.raw_text)
                existing.updated_at = _now()
            else:
                s.add(ProjectModel(
                    id=data["project_id"],
                    name=data.get("name", ""),
                    phase=data.get("phase", "created"),
                    status=data.get("status", "active"),
                    requirement=data.get("requirement", ""),
                    raw_text=data.get("raw_text", ""),
                    created_at=_parse_dt(data.get("created_at")),
                    updated_at=_now(),
                ))

    def get(self, project_id: str) -> Optional[Dict[str, Any]]:
        with get_session() as s:
            p = s.query(ProjectModel).filter_by(id=project_id).first()
            if not p:
                return None
            return _project_to_dict(p)

    def list_all(self) -> List[Dict[str, Any]]:
        with get_session() as s:
            projects = s.query(ProjectModel).order_by(ProjectModel.updated_at.desc()).all()
            return [_project_to_dict(p) for p in projects]

    def delete(self, project_id: str) -> None:
        with get_session() as s:
            p = s.query(ProjectModel).filter_by(id=project_id).first()
            if p:
                s.delete(p)


def _project_to_dict(p: ProjectModel) -> Dict[str, Any]:
    return {
        "project_id": p.id,
        "name": p.name,
        "phase": p.phase,
        "status": p.status,
        "requirement": p.requirement,
        "raw_text": p.raw_text,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


def _parse_dt(val) -> datetime:
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val)
        except (ValueError, TypeError):
            pass
    return _now()


# ═══════════════════════════════════════════════════════════════
# OntologyRepository
# ═══════════════════════════════════════════════════════════════

class OntologyRepository:

    def save(self, project_id: str, ontology_dict: Dict[str, Any]) -> None:
        with get_session() as s:
            existing = s.query(OntologyModel).filter_by(project_id=project_id).first()
            if existing:
                existing.data_json = ontology_dict
                existing.analysis_summary = ontology_dict.get("analysis_summary", "")
            else:
                s.add(OntologyModel(
                    project_id=project_id,
                    data_json=ontology_dict,
                    analysis_summary=ontology_dict.get("analysis_summary", ""),
                ))

    def get(self, project_id: str) -> Optional[Dict[str, Any]]:
        with get_session() as s:
            o = s.query(OntologyModel).filter_by(project_id=project_id).first()
            return o.data_json if o else None


# ═══════════════════════════════════════════════════════════════
# GraphRepository
# ═══════════════════════════════════════════════════════════════

class GraphRepository:

    def save(self, project_id: str, graph_id: str, info: Dict[str, Any],
             graph_data: Optional[Dict[str, Any]] = None) -> None:
        with get_session() as s:
            existing = s.query(GraphModel).filter_by(project_id=project_id).first()
            if existing:
                existing.graph_id = graph_id
                existing.node_count = info.get("node_count", 0)
                existing.edge_count = info.get("edge_count", 0)
                existing.entity_types_json = info.get("entity_types", [])
                if graph_data:
                    existing.graph_data_json = graph_data
            else:
                s.add(GraphModel(
                    project_id=project_id,
                    graph_id=graph_id,
                    node_count=info.get("node_count", 0),
                    edge_count=info.get("edge_count", 0),
                    entity_types_json=info.get("entity_types", []),
                    graph_data_json=graph_data or {},
                ))

    def get(self, project_id: str) -> Optional[Dict[str, Any]]:
        with get_session() as s:
            g = s.query(GraphModel).filter_by(project_id=project_id).first()
            if not g:
                return None
            return {
                "graph_id": g.graph_id,
                "node_count": g.node_count,
                "edge_count": g.edge_count,
                "entity_types": g.entity_types_json,
                "graph_data": g.graph_data_json,
            }


# ═══════════════════════════════════════════════════════════════
# SimulationRepository
# ═══════════════════════════════════════════════════════════════

class SimulationRepository:

    def save_simulation(self, project_id: str, sim_data: Dict[str, Any]) -> None:
        with get_session() as s:
            existing = s.query(SimulationModel).filter_by(project_id=project_id).first()
            if existing:
                existing.sim_id = sim_data.get("sim_id", existing.sim_id)
                existing.config_json = sim_data.get("config", existing.config_json)
                existing.summary_json = sim_data.get("summary", existing.summary_json)
                existing.status = sim_data.get("status", existing.status)
                existing.current_round = sim_data.get("current_round", existing.current_round)
                existing.total_rounds = sim_data.get("total_rounds", existing.total_rounds)
                existing.total_actions = sim_data.get("total_actions", existing.total_actions)
                existing.completed_at = _now() if sim_data.get("status") == "completed" else existing.completed_at
            else:
                s.add(SimulationModel(
                    project_id=project_id,
                    sim_id=sim_data.get("sim_id", ""),
                    config_json=sim_data.get("config", {}),
                    summary_json=sim_data.get("summary", {}),
                    status=sim_data.get("status", "idle"),
                    current_round=sim_data.get("current_round", 0),
                    total_rounds=sim_data.get("total_rounds", 0),
                    total_actions=sim_data.get("total_actions", 0),
                    started_at=_now(),
                ))

    def save_round(self, project_id: str, round_data: Dict[str, Any]) -> None:
        with get_session() as s:
            sim = s.query(SimulationModel).filter_by(project_id=project_id).first()
            if not sim:
                return
            s.add(SimulationRoundModel(
                simulation_id=sim.id,
                round_num=round_data.get("round_num", 0),
                simulated_hour=round_data.get("simulated_hour", 0),
                actions_json=round_data.get("actions", []),
                stats_json=round_data.get("platform_stats", {}),
            ))

    def get_simulation(self, project_id: str) -> Optional[Dict[str, Any]]:
        with get_session() as s:
            sim = s.query(SimulationModel).filter_by(project_id=project_id).first()
            if not sim:
                return None
            return {
                "sim_id": sim.sim_id,
                "config": sim.config_json,
                "summary": sim.summary_json,
                "status": sim.status,
                "current_round": sim.current_round,
                "total_rounds": sim.total_rounds,
                "total_actions": sim.total_actions,
            }

    def get_rounds(self, project_id: str) -> List[Dict[str, Any]]:
        with get_session() as s:
            sim = s.query(SimulationModel).filter_by(project_id=project_id).first()
            if not sim:
                return []
            rounds = s.query(SimulationRoundModel).filter_by(
                simulation_id=sim.id
            ).order_by(SimulationRoundModel.round_num).all()
            return [
                {
                    "round_num": r.round_num,
                    "simulated_hour": r.simulated_hour,
                    "actions": r.actions_json,
                    "actions_count": len(r.actions_json) if isinstance(r.actions_json, list) else 0,
                    "platform_stats": r.stats_json,
                }
                for r in rounds
            ]


# ═══════════════════════════════════════════════════════════════
# AgentRepository
# ═══════════════════════════════════════════════════════════════

class AgentRepository:

    def save_profiles(self, project_id: str, profiles: List[Dict[str, Any]]) -> None:
        with get_session() as s:
            sim = s.query(SimulationModel).filter_by(project_id=project_id).first()
            if not sim:
                return
            # Clear existing
            s.query(AgentProfileModel).filter_by(simulation_id=sim.id).delete()
            for p in profiles:
                s.add(AgentProfileModel(
                    simulation_id=sim.id,
                    agent_id=p.get("agent_id", 0),
                    name=p.get("name", ""),
                    entity_type=p.get("entity_type", ""),
                    profile_json=p,
                ))

    def get_profiles(self, project_id: str) -> List[Dict[str, Any]]:
        with get_session() as s:
            sim = s.query(SimulationModel).filter_by(project_id=project_id).first()
            if not sim:
                return []
            agents = s.query(AgentProfileModel).filter_by(simulation_id=sim.id).all()
            return [a.profile_json for a in agents]


# ═══════════════════════════════════════════════════════════════
# ReportRepository
# ═══════════════════════════════════════════════════════════════

class ReportRepository:

    def save(self, project_id: str, content: str, outline: Dict[str, Any] = None) -> None:
        with get_session() as s:
            existing = s.query(ReportModel).filter_by(project_id=project_id).first()
            if existing:
                existing.content_md = content
                existing.outline_json = outline or {}
            else:
                s.add(ReportModel(
                    project_id=project_id,
                    content_md=content,
                    outline_json=outline or {},
                ))

    def get(self, project_id: str) -> Optional[Dict[str, Any]]:
        with get_session() as s:
            r = s.query(ReportModel).filter_by(project_id=project_id).first()
            if not r:
                return None
            return {
                "content": r.content_md,
                "outline": r.outline_json,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }


# ═══════════════════════════════════════════════════════════════
# ChatRepository
# ═══════════════════════════════════════════════════════════════

class ChatRepository:

    def save_message(self, project_id: str, role: str, content: str) -> None:
        with get_session() as s:
            s.add(ChatMessageModel(
                project_id=project_id,
                role=role,
                content=content,
            ))

    def get_history(self, project_id: str) -> List[Dict[str, Any]]:
        with get_session() as s:
            msgs = s.query(ChatMessageModel).filter_by(
                project_id=project_id
            ).order_by(ChatMessageModel.created_at).all()
            return [
                {"role": m.role, "content": m.content, "created_at": m.created_at.isoformat() if m.created_at else None}
                for m in msgs
            ]


# ═══════════════════════════════════════════════════════════════
# JobRepository
# ═══════════════════════════════════════════════════════════════

class JobRepository:

    def create(self, job_id: str, project_id: str, job_type: str) -> None:
        with get_session() as s:
            s.add(JobModel(
                id=job_id,
                project_id=project_id,
                job_type=job_type,
                status="queued",
            ))

    def update(self, job_id: str, **fields) -> None:
        with get_session() as s:
            job = s.query(JobModel).filter_by(id=job_id).first()
            if not job:
                return
            for k, v in fields.items():
                if hasattr(job, k):
                    setattr(job, k, v)

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        with get_session() as s:
            j = s.query(JobModel).filter_by(id=job_id).first()
            if not j:
                return None
            return _job_to_dict(j)

    def get_by_project(self, project_id: str) -> List[Dict[str, Any]]:
        with get_session() as s:
            jobs = s.query(JobModel).filter_by(project_id=project_id).order_by(JobModel.submitted_at.desc()).all()
            return [_job_to_dict(j) for j in jobs]

    def get_active(self) -> List[Dict[str, Any]]:
        with get_session() as s:
            jobs = s.query(JobModel).filter(JobModel.status.in_(["queued", "running"])).all()
            return [_job_to_dict(j) for j in jobs]

    def mark_stale_running_as_failed(self) -> int:
        """On startup, mark any 'running' jobs as failed (they didn't finish before shutdown)."""
        with get_session() as s:
            stale = s.query(JobModel).filter_by(status="running").all()
            for j in stale:
                j.status = "failed"
                j.error = "Server restarted while job was running"
                j.completed_at = _now()
            return len(stale)


def _job_to_dict(j: JobModel) -> Dict[str, Any]:
    return {
        "job_id": j.id,
        "project_id": j.project_id,
        "job_type": j.job_type,
        "status": j.status,
        "progress": j.progress,
        "stage": j.stage,
        "message": j.message,
        "error": j.error,
        "submitted_at": j.submitted_at.isoformat() if j.submitted_at else None,
        "started_at": j.started_at.isoformat() if j.started_at else None,
        "completed_at": j.completed_at.isoformat() if j.completed_at else None,
    }
