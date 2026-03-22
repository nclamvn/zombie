"""
Database Models — SQLAlchemy 2.0 Declarative

Supports both SQLite (dev) and PostgreSQL (production).
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, Integer, Float, DateTime, JSON, ForeignKey,
    create_engine, Index,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class ProjectModel(Base):
    __tablename__ = "projects"

    id = Column(String(64), primary_key=True)
    name = Column(String(256), nullable=False)
    phase = Column(String(64), nullable=False, default="created")
    status = Column(String(32), nullable=False, default="active")
    requirement = Column(Text, nullable=False, default="")
    raw_text = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    ontology = relationship("OntologyModel", back_populates="project", uselist=False, cascade="all, delete-orphan")
    graph = relationship("GraphModel", back_populates="project", uselist=False, cascade="all, delete-orphan")
    simulation = relationship("SimulationModel", back_populates="project", uselist=False, cascade="all, delete-orphan")
    report = relationship("ReportModel", back_populates="project", uselist=False, cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessageModel", back_populates="project", cascade="all, delete-orphan",
                                 order_by="ChatMessageModel.created_at")

    __table_args__ = (
        Index("ix_projects_updated", "updated_at"),
    )


class OntologyModel(Base):
    __tablename__ = "ontologies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(64), ForeignKey("projects.id", ondelete="CASCADE"), unique=True, nullable=False)
    data_json = Column(JSON, nullable=False)
    analysis_summary = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("ProjectModel", back_populates="ontology")


class GraphModel(Base):
    __tablename__ = "graphs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(64), ForeignKey("projects.id", ondelete="CASCADE"), unique=True, nullable=False)
    graph_id = Column(String(128), nullable=False)
    node_count = Column(Integer, default=0)
    edge_count = Column(Integer, default=0)
    entity_types_json = Column(JSON, default=list)
    graph_data_json = Column(JSON, default=dict)  # cached nodes + edges
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("ProjectModel", back_populates="graph")


class SimulationModel(Base):
    __tablename__ = "simulations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(64), ForeignKey("projects.id", ondelete="CASCADE"), unique=True, nullable=False)
    sim_id = Column(String(128), unique=True)
    config_json = Column(JSON, default=dict)
    summary_json = Column(JSON, default=dict)
    status = Column(String(32), default="idle")
    current_round = Column(Integer, default=0)
    total_rounds = Column(Integer, default=0)
    total_actions = Column(Integer, default=0)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    project = relationship("ProjectModel", back_populates="simulation")
    rounds = relationship("SimulationRoundModel", back_populates="simulation", cascade="all, delete-orphan",
                          order_by="SimulationRoundModel.round_num")
    agents = relationship("AgentProfileModel", back_populates="simulation", cascade="all, delete-orphan")


class SimulationRoundModel(Base):
    __tablename__ = "simulation_rounds"

    id = Column(Integer, primary_key=True, autoincrement=True)
    simulation_id = Column(Integer, ForeignKey("simulations.id", ondelete="CASCADE"), nullable=False)
    round_num = Column(Integer, nullable=False)
    simulated_hour = Column(Integer, default=0)
    actions_json = Column(JSON, default=list)
    stats_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    simulation = relationship("SimulationModel", back_populates="rounds")

    __table_args__ = (
        Index("ix_rounds_sim_round", "simulation_id", "round_num"),
    )


class AgentProfileModel(Base):
    __tablename__ = "agent_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    simulation_id = Column(Integer, ForeignKey("simulations.id", ondelete="CASCADE"), nullable=False)
    agent_id = Column(Integer, nullable=False)
    name = Column(String(256), nullable=False)
    entity_type = Column(String(128), default="")
    profile_json = Column(JSON, default=dict)

    simulation = relationship("SimulationModel", back_populates="agents")


class ReportModel(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(64), ForeignKey("projects.id", ondelete="CASCADE"), unique=True, nullable=False)
    content_md = Column(Text, nullable=False)
    outline_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("ProjectModel", back_populates="report")


class ChatMessageModel(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(64), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(16), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("ProjectModel", back_populates="chat_messages")

    __table_args__ = (
        Index("ix_chat_project", "project_id", "created_at"),
    )
