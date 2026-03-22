"""
Local Memory Store — File-based agent memory persistence.

Stores memories as JSON files on disk. Supports keyword search
and basic temporal filtering. Good for testing and small-scale use.
"""

import os
import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

from core.tools.logger import get_logger

logger = get_logger("mirofish.adapter.local_memory")


class LocalMemoryStore:
    """
    Local file-based memory store.
    
    Stores agent memories as JSON in a directory structure:
    base_dir/
      agents/
        {agent_id}.json  → list of memory entries
      graph_sync/
        round_{N}.json   → sync records
    """
    
    def __init__(self, base_dir: str = "/tmp/mirofish_memory"):
        self.base_dir = base_dir
        self._agents_dir = os.path.join(base_dir, "agents")
        self._sync_dir = os.path.join(base_dir, "graph_sync")
        os.makedirs(self._agents_dir, exist_ok=True)
        os.makedirs(self._sync_dir, exist_ok=True)
    
    def store_agent_memory(
        self,
        agent_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[str] = None,
    ) -> str:
        """Store a memory entry for an agent."""
        entry_id = f"mem_{uuid.uuid4().hex[:12]}"
        entry = {
            "id": entry_id,
            "content": content,
            "metadata": metadata or {},
            "timestamp": timestamp or datetime.now().isoformat(),
            "created_at": datetime.now().isoformat(),
        }
        
        memories = self._load_agent_memories(agent_id)
        memories.append(entry)
        self._save_agent_memories(agent_id, memories)
        
        return entry_id
    
    def retrieve_agent_memories(
        self,
        agent_id: str,
        query: Optional[str] = None,
        limit: int = 10,
        time_range: Optional[tuple] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve memories for an agent with optional keyword search."""
        memories = self._load_agent_memories(agent_id)
        
        # Filter by time range
        if time_range and len(time_range) == 2:
            start, end = time_range
            memories = [
                m for m in memories
                if start <= m.get("timestamp", "") <= end
            ]
        
        # Keyword search
        if query:
            query_lower = query.lower()
            keywords = query_lower.split()
            scored = []
            for m in memories:
                content_lower = m.get("content", "").lower()
                score = sum(1 for kw in keywords if kw in content_lower)
                if score > 0:
                    scored.append((score, m))
            scored.sort(key=lambda x: x[0], reverse=True)
            memories = [m for _, m in scored]
        
        return memories[:limit]
    
    def sync_to_graph(
        self,
        graph_id: str,
        agent_activities: List[Dict[str, Any]],
        round_num: int,
    ) -> None:
        """Save sync record (local implementation doesn't actually update a graph)."""
        sync_file = os.path.join(self._sync_dir, f"round_{round_num}.json")
        record = {
            "graph_id": graph_id,
            "round_num": round_num,
            "activities": agent_activities,
            "synced_at": datetime.now().isoformat(),
        }
        with open(sync_file, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        
        # Also store each activity as an agent memory
        for activity in agent_activities:
            agent_id = activity.get("agent_id", "unknown")
            content = (
                f"Round {round_num}: {activity.get('agent_name', agent_id)} "
                f"performed {activity.get('action_type', 'unknown')} "
                f"on {activity.get('platform', 'unknown')}"
            )
            if activity.get("content"):
                content += f" — {activity['content'][:200]}"
            
            self.store_agent_memory(
                agent_id=agent_id,
                content=content,
                metadata={"round": round_num, "source": "simulation"},
            )
        
        logger.info(f"Synced {len(agent_activities)} activities for round {round_num}")
    
    def get_agent_summary(self, agent_id: str) -> str:
        """Get a summary of an agent's memory."""
        memories = self._load_agent_memories(agent_id)
        if not memories:
            return f"No memories stored for agent {agent_id}"
        
        total = len(memories)
        latest = memories[-1]
        return (
            f"Agent {agent_id}: {total} memories. "
            f"Latest: {latest.get('content', '')[:100]}"
        )
    
    def clear_agent_memories(self, agent_id: str) -> None:
        """Clear all memories for an agent."""
        path = os.path.join(self._agents_dir, f"{agent_id}.json")
        if os.path.exists(path):
            os.remove(path)
    
    # ─── Internal helpers ──────────────────────────────────────
    
    def _load_agent_memories(self, agent_id: str) -> List[Dict[str, Any]]:
        path = os.path.join(self._agents_dir, f"{agent_id}.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []
    
    def _save_agent_memories(self, agent_id: str, memories: List[Dict[str, Any]]) -> None:
        path = os.path.join(self._agents_dir, f"{agent_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(memories, f, ensure_ascii=False, indent=2)
