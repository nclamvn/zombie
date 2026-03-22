"""
Structured Logger — JSON-line logging for production observability.

Dual-mode: JSON (production) or text (dev).
Config via env: LOG_FORMAT, LOG_LEVEL, LOG_FILE.
"""

import os
import json
import time
import logging
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

_configured = False


def setup_structured_logging():
    """Configure root logger based on environment."""
    global _configured
    if _configured:
        return
    _configured = True

    log_format = os.environ.get("LOG_FORMAT", "text").lower()
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_file = os.environ.get("LOG_FILE", "")

    level = getattr(logging, log_level, logging.INFO)
    root = logging.getLogger()
    root.setLevel(level)

    # Remove existing handlers to avoid duplicates
    for h in root.handlers[:]:
        root.removeHandler(h)

    if log_format == "json":
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            "[%(asctime)s] %(name)s | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Stdout handler
    stdout = logging.StreamHandler(sys.stdout)
    stdout.setLevel(level)
    stdout.setFormatter(formatter)
    root.addHandler(stdout)

    # File handler (optional)
    if log_file:
        fh = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5)
        fh.setLevel(level)
        fh.setFormatter(formatter)
        root.addHandler(fh)


class JsonFormatter(logging.Formatter):
    """Outputs each log record as a single JSON line."""

    def format(self, record):
        data = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Include extra fields if present
        if hasattr(record, "event"):
            data["event"] = record.event
        if hasattr(record, "context") and isinstance(record.context, dict):
            data.update(record.context)
        if record.exc_info and record.exc_info[1]:
            data["error"] = str(record.exc_info[1])
        return json.dumps(data, ensure_ascii=False, default=str)


def log_event(logger_name: str, level: str, event: str, **context):
    """
    Emit a structured log event.

    Usage:
        log_event("mirofish.pipeline", "info", "pipeline.stage_complete",
                  project_id="proj_xxx", stage="ontology", duration_ms=2340)
    """
    logger = logging.getLogger(logger_name)
    lvl = getattr(logging, level.upper(), logging.INFO)
    record = logger.makeRecord(
        logger_name, lvl, "", 0,
        f"{event} {json.dumps(context, default=str) if context else ''}",
        args=(), exc_info=None,
    )
    record.event = event
    record.context = context
    logger.handle(record)
