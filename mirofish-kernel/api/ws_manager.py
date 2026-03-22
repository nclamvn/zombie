"""
WebSocket Connection Manager — Per-project client management + event buffering.

Handles: connect/disconnect, broadcast to all clients, event replay on reconnect.
"""

import json
import logging
import asyncio
from collections import deque
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

logger = logging.getLogger("mirofish.ws")

try:
    from fastapi import WebSocket
except ImportError:
    WebSocket = None


class EventBuffer:
    """Ring buffer per project for reconnection replay."""

    def __init__(self, max_size: int = 200):
        self._max = max_size
        self._buffers: Dict[str, deque] = {}
        self._counters: Dict[str, int] = {}

    def push(self, project_id: str, event: dict) -> int:
        if project_id not in self._buffers:
            self._buffers[project_id] = deque(maxlen=self._max)
            self._counters[project_id] = 0
        self._counters[project_id] += 1
        eid = self._counters[project_id]
        event["_eid"] = eid
        self._buffers[project_id].append(event)
        return eid

    def get_since(self, project_id: str, since_eid: int) -> List[dict]:
        buf = self._buffers.get(project_id)
        if not buf:
            return []
        return [e for e in buf if e.get("_eid", 0) > since_eid]

    def clear(self, project_id: str):
        self._buffers.pop(project_id, None)
        self._counters.pop(project_id, None)


class ConnectionManager:
    """Manages WebSocket connections per project with broadcast and buffering."""

    def __init__(self):
        self._connections: Dict[str, List[WebSocket]] = {}
        self._buffer = EventBuffer()
        self._sim_flags: Dict[str, dict] = {}  # project_id → {paused, speed}

    async def connect(self, project_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.setdefault(project_id, []).append(ws)
        logger.info(f"WS connected: {project_id} ({self.client_count(project_id)} clients)")

    def disconnect(self, project_id: str, ws: WebSocket) -> None:
        if project_id in self._connections:
            try:
                self._connections[project_id].remove(ws)
            except ValueError:
                pass
            if not self._connections[project_id]:
                del self._connections[project_id]
        logger.info(f"WS disconnected: {project_id}")

    async def broadcast(self, project_id: str, event_type: str, data: dict) -> None:
        """Send event to all connected clients for a project."""
        msg = {
            "event": event_type,
            "data": data,
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        self._buffer.push(project_id, msg)

        dead = []
        for i, ws in enumerate(self._connections.get(project_id, [])):
            try:
                await ws.send_json(msg)
            except Exception:
                dead.append(i)
        # Remove dead connections
        for i in reversed(dead):
            try:
                self._connections[project_id].pop(i)
            except (IndexError, KeyError):
                pass

    def broadcast_sync(self, project_id: str, event_type: str, data: dict) -> None:
        """Thread-safe broadcast — pushes to buffer, async send handled by WS loop."""
        msg = {
            "event": event_type,
            "data": data,
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        self._buffer.push(project_id, msg)
        # Push to each client's send queue (set up in ws handler)
        for ws in self._connections.get(project_id, []):
            q = getattr(ws, "_send_queue", None)
            if q:
                try:
                    q.put_nowait(msg)
                except asyncio.QueueFull:
                    pass

    def client_count(self, project_id: str) -> int:
        return len(self._connections.get(project_id, []))

    def get_replay(self, project_id: str, since_eid: int) -> List[dict]:
        return self._buffer.get_since(project_id, since_eid)

    # ── Simulation control flags ──

    def set_flag(self, project_id: str, key: str, value: Any) -> None:
        self._sim_flags.setdefault(project_id, {})[key] = value

    def get_flag(self, project_id: str, key: str, default=None):
        return self._sim_flags.get(project_id, {}).get(key, default)

    def clear_flags(self, project_id: str):
        self._sim_flags.pop(project_id, None)


# Singleton
ws_manager = ConnectionManager()
