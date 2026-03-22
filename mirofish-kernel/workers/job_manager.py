"""
Job Manager — Background pipeline execution with ThreadPoolExecutor.

Manages job submission, execution, progress tracking, and cancellation.
No external dependencies (no Redis, no Celery) — pure Python threading.
"""

import os
import uuid
import threading
import logging
from concurrent.futures import ThreadPoolExecutor, Future
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable

from core.storage.repository import JobRepository

logger = logging.getLogger("mirofish.jobs")

_job_repo = JobRepository()


class JobManager:
    """
    Manages background pipeline jobs using ThreadPoolExecutor.

    Usage:
        manager = JobManager(max_workers=2)
        job_id = manager.submit(project_id, "full_pipeline", run_fn, emit_fn)
        status = manager.get_status(job_id)
        manager.cancel(job_id)
        manager.shutdown()
    """

    def __init__(self, max_workers: int = None):
        self._max_workers = max_workers or int(os.environ.get("MAX_CONCURRENT_JOBS", "2"))
        self._executor = ThreadPoolExecutor(
            max_workers=self._max_workers,
            thread_name_prefix="mirofish-worker",
        )
        self._futures: Dict[str, Future] = {}
        self._cancelled: set = set()
        self._lock = threading.Lock()

        # On startup, mark any stale "running" jobs as failed
        stale = _job_repo.mark_stale_running_as_failed()
        if stale:
            logger.warning(f"Marked {stale} stale running jobs as failed on startup")

        logger.info(f"JobManager started — max_workers={self._max_workers}")

    def submit(
        self,
        project_id: str,
        job_type: str,
        run_fn: Callable[[str, str, Callable], None],
        emit_fn: Optional[Callable] = None,
    ) -> str:
        """
        Submit a background job.

        Args:
            project_id: Target project
            job_type: full_pipeline, simulate_only, report_only
            run_fn: Function(project_id, job_id, progress_callback) to execute
            emit_fn: Optional SSE emit function for this project

        Returns:
            job_id
        """
        job_id = f"job_{uuid.uuid4().hex[:12]}"

        # Persist job record
        _job_repo.create(job_id, project_id, job_type)

        def wrapped():
            # Mark running
            _job_repo.update(job_id,
                status="running",
                started_at=datetime.now(timezone.utc),
            )
            logger.info(f"Job {job_id} started — {job_type} for {project_id}")

            def progress_callback(stage: str, progress: float, message: str):
                if job_id in self._cancelled:
                    raise InterruptedError("Job cancelled")
                _job_repo.update(job_id,
                    progress=progress,
                    stage=stage,
                    message=message,
                )

            try:
                run_fn(project_id, job_id, progress_callback)

                _job_repo.update(job_id,
                    status="completed",
                    progress=1.0,
                    stage="done",
                    message="Pipeline complete",
                    completed_at=datetime.now(timezone.utc),
                )
                logger.info(f"Job {job_id} completed")

            except InterruptedError:
                _job_repo.update(job_id,
                    status="cancelled",
                    message="Cancelled by user",
                    completed_at=datetime.now(timezone.utc),
                )
                logger.info(f"Job {job_id} cancelled")

            except Exception as e:
                error_msg = str(e)
                _job_repo.update(job_id,
                    status="failed",
                    error=error_msg,
                    message=f"Failed: {error_msg[:100]}",
                    completed_at=datetime.now(timezone.utc),
                )
                logger.error(f"Job {job_id} failed: {e}")

            finally:
                with self._lock:
                    self._futures.pop(job_id, None)
                    self._cancelled.discard(job_id)

        future = self._executor.submit(wrapped)
        with self._lock:
            self._futures[job_id] = future

        return job_id

    def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status from DB."""
        return _job_repo.get(job_id)

    def get_project_jobs(self, project_id: str):
        """Get all jobs for a project."""
        return _job_repo.get_by_project(project_id)

    def cancel(self, job_id: str) -> bool:
        """Cancel a job. Returns True if cancellation was initiated."""
        job = _job_repo.get(job_id)
        if not job:
            return False

        if job["status"] == "queued":
            # Try to cancel future before it starts
            with self._lock:
                future = self._futures.get(job_id)
                if future and future.cancel():
                    self._futures.pop(job_id, None)
            _job_repo.update(job_id,
                status="cancelled",
                message="Cancelled before start",
                completed_at=datetime.now(timezone.utc),
            )
            return True

        if job["status"] == "running":
            # Signal the running job to stop
            self._cancelled.add(job_id)
            return True

        return False

    @property
    def active_count(self) -> int:
        with self._lock:
            return len(self._futures)

    def shutdown(self, wait: bool = True):
        """Graceful shutdown."""
        logger.info("JobManager shutting down...")
        self._executor.shutdown(wait=wait)
