"""
LLM Cost Tracker — TIP-13

Tracks token usage and estimated costs per project/simulation.
Thread-safe. Configurable pricing.
"""

import os
import logging
import threading
from typing import Dict, Any, Optional
from collections import defaultdict
from dataclasses import dataclass, field

logger = logging.getLogger("mirofish.cost")

# Default pricing (USD per 1K tokens) — configurable via env
DEFAULT_PRICING = {
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4": {"input": 0.03, "output": 0.06},
    "claude-sonnet-4-20250514": {"input": 0.003, "output": 0.015},
    "claude-opus-4-20250514": {"input": 0.015, "output": 0.075},
    "claude-haiku-4-5-20251001": {"input": 0.001, "output": 0.005},
}


@dataclass
class UsageRecord:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    calls: int = 0
    estimated_cost_usd: float = 0.0
    latency_ms_total: int = 0

    @property
    def avg_latency_ms(self) -> int:
        return self.latency_ms_total // max(self.calls, 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "calls": self.calls,
            "estimated_cost_usd": round(self.estimated_cost_usd, 4),
            "avg_latency_ms": self.avg_latency_ms,
        }


class CostTracker:
    """
    Thread-safe LLM cost tracker.

    Usage:
        tracker = CostTracker()
        tracker.record("proj_abc", "gpt-4o-mini", 500, 100, 230)
        stats = tracker.get_project_stats("proj_abc")
        # → { prompt_tokens: 500, completion_tokens: 100, estimated_cost_usd: 0.0001, ... }
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._projects: Dict[str, UsageRecord] = defaultdict(UsageRecord)
        self._global = UsageRecord()

        # Load custom pricing from env if available
        self._pricing = dict(DEFAULT_PRICING)
        custom = os.environ.get("LLM_PRICING")
        if custom:
            try:
                import json
                self._pricing.update(json.loads(custom))
            except Exception:
                pass

        # Budget limit (0 = unlimited)
        self._budget_limit = float(os.environ.get("LLM_BUDGET_LIMIT", "0"))

    def record(
        self,
        project_id: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: int = 0,
    ) -> Dict[str, Any]:
        """Record a single LLM call. Returns current project stats."""
        total = prompt_tokens + completion_tokens
        cost = self._estimate_cost(model, prompt_tokens, completion_tokens)

        with self._lock:
            for rec in [self._projects[project_id], self._global]:
                rec.prompt_tokens += prompt_tokens
                rec.completion_tokens += completion_tokens
                rec.total_tokens += total
                rec.calls += 1
                rec.estimated_cost_usd += cost
                rec.latency_ms_total += latency_ms

        # Budget check
        if self._budget_limit > 0:
            proj_cost = self._projects[project_id].estimated_cost_usd
            if proj_cost > self._budget_limit:
                logger.warning(
                    f"Project {project_id} exceeded budget: ${proj_cost:.4f} > ${self._budget_limit:.4f}"
                )

        return self.get_project_stats(project_id)

    def get_project_stats(self, project_id: str) -> Dict[str, Any]:
        with self._lock:
            rec = self._projects.get(project_id)
            if not rec:
                return UsageRecord().to_dict()
            return rec.to_dict()

    def get_global_stats(self) -> Dict[str, Any]:
        with self._lock:
            return self._global.to_dict()

    def is_over_budget(self, project_id: str) -> bool:
        if self._budget_limit <= 0:
            return False
        with self._lock:
            return self._projects.get(project_id, UsageRecord()).estimated_cost_usd > self._budget_limit

    def _estimate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        pricing = self._pricing.get(model)
        if not pricing:
            # Try partial match
            for key, p in self._pricing.items():
                if key in model or model in key:
                    pricing = p
                    break
        if not pricing:
            pricing = {"input": 0.001, "output": 0.002}  # conservative default

        cost = (prompt_tokens / 1000 * pricing["input"]) + (completion_tokens / 1000 * pricing["output"])
        return cost


# Global singleton
cost_tracker = CostTracker()
