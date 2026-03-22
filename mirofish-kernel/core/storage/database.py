"""
Database Connection — SQLAlchemy engine + session management.

Supports SQLite (dev, zero-config) and PostgreSQL (production).
Set DATABASE_URL env var to switch.
"""

import os
import logging
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .models import Base

logger = logging.getLogger("mirofish.storage")

_engine = None
_SessionFactory = None


def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        url = "sqlite:///./mirofish.db"
        logger.warning("DATABASE_URL not set — using SQLite (dev mode): ./mirofish.db")
    return url


def init_db(url: str = None) -> None:
    """Initialize database engine and create tables."""
    global _engine, _SessionFactory

    db_url = url or get_database_url()

    # SQLite needs check_same_thread=False for multi-threaded access
    connect_args = {}
    if db_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    _engine = create_engine(
        db_url,
        connect_args=connect_args,
        echo=False,
        pool_pre_ping=True,
    )
    _SessionFactory = sessionmaker(bind=_engine, expire_on_commit=False)

    # Create all tables
    Base.metadata.create_all(_engine)

    db_type = "SQLite" if "sqlite" in db_url else "PostgreSQL"
    logger.info(f"Database initialized: {db_type}")


def get_engine():
    if _engine is None:
        init_db()
    return _engine


@contextmanager
def get_session() -> Session:
    """Context manager for database sessions."""
    if _SessionFactory is None:
        init_db()
    session = _SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
