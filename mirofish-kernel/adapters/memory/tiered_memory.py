"""
Tiered Memory Store — 3-layer agent memory architecture.

Tier 1: Ephemeral (in-memory, TTL) — fast context window for current round
Tier 2: Persistent (SQLAlchemy) — keyword-searchable long-term memory
Tier 3: Decision Trace (SQLAlchemy) — full reasoning audit trail

Implements MemoryStore protocol. Zero external dependencies beyond SQLAlchemy.
"""

import hashlib
import logging
import threading
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("mirofish.memory.tiered")


class EphemeralMemory:
    """
    Tier 1: In-memory ring buffer with TTL.

    Fast reads for current simulation context. Each agent keeps last N entries.
    Auto-expires after TTL (default: 1 hour).
    Thread-safe.
    """

    def __init__(self, max_per_agent: int = 20, ttl_seconds: int = 3600):
        self._max = max_per_agent
        self._ttl = ttl_seconds
        self._store: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_per_agent))
        self._lock = threading.Lock()

    def store(self, agent_id: str, content: str, metadata: dict = None) -> str:
        entry_id = f"eph_{uuid.uuid4().hex[:8]}"
        entry = {
            "id": entry_id,
            "content": content,
            "metadata": metadata or {},
            "ts": time.time(),
        }
        with self._lock:
            self._store[agent_id].append(entry)
        return entry_id

    def retrieve(self, agent_id: str, query: str = None, limit: int = 10) -> List[Dict]:
        now = time.time()
        with self._lock:
            entries = list(self._store.get(agent_id, []))
        # Filter expired
        entries = [e for e in entries if (now - e["ts"]) < self._ttl]
        # Keyword match if query
        if query:
            q = query.lower()
            entries = sorted(entries, key=lambda e: _keyword_score(e["content"], q), reverse=True)
        return entries[:limit]

    def clear(self, agent_id: str):
        with self._lock:
            self._store.pop(agent_id, None)

    def clear_all(self):
        with self._lock:
            self._store.clear()


class PersistentMemory:
    """
    Tier 2: SQLAlchemy-backed persistent memory with keyword search.

    Long-term memory that survives restarts. Keyword-ranked retrieval.
    Future: plug in vector embeddings for semantic search.
    """

    def store(self, agent_id: str, project_id: str, content: str,
              metadata: dict = None, round_num: int = None,
              importance: float = 0.5, timestamp: str = "") -> str:
        from core.storage.database import get_session
        from core.storage.models import AgentMemoryModel

        with get_session() as s:
            mem = AgentMemoryModel(
                agent_id=agent_id,
                project_id=project_id,
                content=content,
                metadata_json=metadata or {},
                round_num=round_num,
                importance=importance,
                timestamp=timestamp,
            )
            s.add(mem)
            s.flush()
            return f"pm_{mem.id}"

    def retrieve(self, agent_id: str, project_id: str,
                 query: str = None, limit: int = 10,
                 time_range: Tuple = None) -> List[Dict]:
        from core.storage.database import get_session
        from core.storage.models import AgentMemoryModel

        with get_session() as s:
            q = s.query(AgentMemoryModel).filter_by(
                agent_id=agent_id, project_id=project_id
            )
            if time_range and len(time_range) == 2:
                q = q.filter(AgentMemoryModel.round_num >= time_range[0],
                             AgentMemoryModel.round_num <= time_range[1])

            results = q.order_by(AgentMemoryModel.created_at.desc()).limit(limit * 3).all()

            entries = [{
                "id": f"pm_{r.id}",
                "content": r.content,
                "metadata": r.metadata_json,
                "round_num": r.round_num,
                "importance": r.importance,
                "timestamp": r.timestamp,
            } for r in results]

        # Keyword rank if query
        if query and entries:
            q_lower = query.lower()
            entries.sort(key=lambda e: _keyword_score(e["content"], q_lower) + e.get("importance", 0), reverse=True)

        return entries[:limit]

    def get_summary(self, agent_id: str, project_id: str) -> str:
        from core.storage.database import get_session
        from core.storage.models import AgentMemoryModel

        with get_session() as s:
            count = s.query(AgentMemoryModel).filter_by(
                agent_id=agent_id, project_id=project_id
            ).count()
            latest = s.query(AgentMemoryModel).filter_by(
                agent_id=agent_id, project_id=project_id
            ).order_by(AgentMemoryModel.created_at.desc()).first()

        if not count:
            return f"Agent {agent_id} has no stored memories."
        latest_text = latest.content[:100] if latest else ""
        return f"Agent {agent_id}: {count} memories. Latest: {latest_text}"

    def clear(self, agent_id: str, project_id: str):
        from core.storage.database import get_session
        from core.storage.models import AgentMemoryModel

        with get_session() as s:
            s.query(AgentMemoryModel).filter_by(
                agent_id=agent_id, project_id=project_id
            ).delete()


class DecisionTrace:
    """
    Tier 3: Structured decision logging for audit and debugging.

    Records every agent decision with full context chain:
    context → prompt → LLM response → action → result
    """

    def record(self, project_id: str, agent_id: str, agent_name: str,
               round_num: int, action_type: str, action_result: str = "",
               context: dict = None, reasoning: str = "",
               llm_model: str = "", prompt_tokens: int = 0,
               completion_tokens: int = 0, latency_ms: int = 0,
               prompt_text: str = "") -> int:
        from core.storage.database import get_session
        from core.storage.models import DecisionTraceModel

        prompt_hash = hashlib.md5(prompt_text.encode()).hexdigest()[:16] if prompt_text else ""

        with get_session() as s:
            trace = DecisionTraceModel(
                project_id=project_id,
                agent_id=agent_id,
                agent_name=agent_name,
                round_num=round_num,
                context_json=context or {},
                prompt_hash=prompt_hash,
                llm_model=llm_model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=latency_ms,
                action_type=action_type,
                action_result=action_result[:500] if action_result else "",
                reasoning=reasoning,
            )
            s.add(trace)
            s.flush()
            return trace.id

    def get_chain(self, project_id: str, agent_id: str, round_num: int = None) -> List[Dict]:
        from core.storage.database import get_session
        from core.storage.models import DecisionTraceModel

        with get_session() as s:
            q = s.query(DecisionTraceModel).filter_by(
                project_id=project_id, agent_id=agent_id
            )
            if round_num is not None:
                q = q.filter_by(round_num=round_num)
            traces = q.order_by(DecisionTraceModel.round_num, DecisionTraceModel.created_at).all()

        return [{
            "id": t.id,
            "round_num": t.round_num,
            "agent_name": t.agent_name,
            "action_type": t.action_type,
            "action_result": t.action_result,
            "reasoning": t.reasoning,
            "context": t.context_json,
            "llm_model": t.llm_model,
            "tokens": t.prompt_tokens + t.completion_tokens,
            "latency_ms": t.latency_ms,
        } for t in traces]

    def get_project_stats(self, project_id: str) -> Dict:
        from core.storage.database import get_session
        from core.storage.models import DecisionTraceModel
        from sqlalchemy import func

        with get_session() as s:
            total = s.query(func.count(DecisionTraceModel.id)).filter_by(project_id=project_id).scalar()
            total_tokens = s.query(
                func.sum(DecisionTraceModel.prompt_tokens + DecisionTraceModel.completion_tokens)
            ).filter_by(project_id=project_id).scalar()
            avg_latency = s.query(func.avg(DecisionTraceModel.latency_ms)).filter_by(project_id=project_id).scalar()

        return {
            "total_decisions": total or 0,
            "total_tokens": total_tokens or 0,
            "avg_latency_ms": round(avg_latency or 0, 1),
        }


# ═══════════════════════════════════════════════════════════════
# TieredMemoryStore — Unified interface implementing MemoryStore
# ═══════════════════════════════════════════════════════════════

class TieredMemoryStore:
    """
    3-tier memory system implementing MemoryStore protocol.

    store() → writes to all 3 tiers simultaneously
    retrieve() → ephemeral first, then persistent, merged + deduped
    get_decision_chain() → from decision trace tier

    Usage:
        memory = TieredMemoryStore(project_id="proj_xxx")
        memory.store_agent_memory("agent_1", "Created post about AI policy")
        memories = memory.retrieve_agent_memories("agent_1", query="AI policy")
        chain = memory.get_decision_chain("agent_1", round_num=15)
    """

    def __init__(self, project_id: str = "", ephemeral_size: int = 20, ephemeral_ttl: int = 3600):
        self.project_id = project_id
        self.ephemeral = EphemeralMemory(max_per_agent=ephemeral_size, ttl_seconds=ephemeral_ttl)
        self.persistent = PersistentMemory()
        self.trace = DecisionTrace()

    def store_agent_memory(
        self,
        agent_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[str] = None,
    ) -> str:
        """Store to all tiers simultaneously."""
        meta = metadata or {}
        round_num = meta.get("round_num") or meta.get("round")

        # Tier 1: Ephemeral
        self.ephemeral.store(agent_id, content, meta)

        # Tier 2: Persistent
        importance = _estimate_importance(content, meta)
        mem_id = self.persistent.store(
            agent_id=agent_id,
            project_id=self.project_id,
            content=content,
            metadata=meta,
            round_num=round_num,
            importance=importance,
            timestamp=timestamp or "",
        )

        return mem_id

    def retrieve_agent_memories(
        self,
        agent_id: str,
        query: Optional[str] = None,
        limit: int = 10,
        time_range: Optional[tuple] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve from ephemeral first, then persistent, merged."""
        # Tier 1: Fast ephemeral lookup
        eph = self.ephemeral.retrieve(agent_id, query, limit)

        # Tier 2: Persistent deep search
        persist = self.persistent.retrieve(
            agent_id, self.project_id, query, limit, time_range
        )

        # Merge + deduplicate by content
        seen = set()
        merged = []
        for entry in eph + persist:
            key = entry["content"][:100]
            if key not in seen:
                seen.add(key)
                merged.append(entry)

        # Re-rank if query
        if query:
            q = query.lower()
            merged.sort(key=lambda e: _keyword_score(e["content"], q) + e.get("importance", 0), reverse=True)

        return merged[:limit]

    def sync_to_graph(
        self,
        graph_id: str,
        agent_activities: List[Dict[str, Any]],
        round_num: int,
    ) -> None:
        """Sync activities to memory + record decision traces."""
        for activity in agent_activities:
            agent_id = str(activity.get("agent_id", ""))
            content = (
                f"Round {round_num}: {activity.get('agent_name', agent_id)} "
                f"performed {activity.get('action_type', 'ACTION')} "
                f"on {activity.get('platform', 'unknown')}"
            )
            if activity.get("content"):
                content += f" — {activity['content'][:200]}"

            self.store_agent_memory(
                agent_id=agent_id,
                content=content,
                metadata={
                    "round_num": round_num,
                    "graph_id": graph_id,
                    "action_type": activity.get("action_type", ""),
                    "platform": activity.get("platform", ""),
                },
            )

            # Tier 3: Decision trace
            self.trace.record(
                project_id=self.project_id,
                agent_id=agent_id,
                agent_name=activity.get("agent_name", ""),
                round_num=round_num,
                action_type=activity.get("action_type", ""),
                action_result=activity.get("content", ""),
            )

    def get_agent_summary(self, agent_id: str) -> str:
        return self.persistent.get_summary(agent_id, self.project_id)

    def clear_agent_memories(self, agent_id: str) -> None:
        self.ephemeral.clear(agent_id)
        self.persistent.clear(agent_id, self.project_id)

    # ── Extended methods (beyond MemoryStore protocol) ──

    def get_decision_chain(self, agent_id: str, round_num: int = None) -> List[Dict]:
        """Get full reasoning trace for an agent."""
        return self.trace.get_chain(self.project_id, agent_id, round_num)

    def get_trace_stats(self) -> Dict:
        """Get project-level decision trace statistics."""
        return self.trace.get_project_stats(self.project_id)

    def record_decision(self, agent_id: str, agent_name: str, round_num: int,
                        action_type: str, **kwargs) -> int:
        """Record a decision trace entry directly."""
        return self.trace.record(
            project_id=self.project_id,
            agent_id=agent_id,
            agent_name=agent_name,
            round_num=round_num,
            action_type=action_type,
            **kwargs,
        )


# ─── Utilities ────────────────────────────────────────────────

def _keyword_score(text: str, query: str) -> float:
    """Simple keyword matching score."""
    words = query.split()
    text_lower = text.lower()
    matches = sum(1 for w in words if w in text_lower)
    return matches / max(len(words), 1)


def _estimate_importance(content: str, metadata: dict) -> float:
    """Estimate memory importance for retrieval ranking."""
    score = 0.5
    action = metadata.get("action_type", "")
    # Content creation is more important
    if action in ("CREATE_POST", "QUOTE_POST", "CREATE_COMMENT"):
        score += 0.2
    # Events are important
    if metadata.get("event"):
        score += 0.15
    # Longer content = more substance
    if len(content) > 100:
        score += 0.1
    return min(score, 1.0)
