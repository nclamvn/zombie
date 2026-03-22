/**
 * useSimulationWebSocket — React hook for live simulation events.
 *
 * Auto-connect, auto-reconnect, heartbeat, event buffering.
 * Returns: { connected, events, sendCommand, lastAction }
 */

import { useState, useEffect, useRef, useCallback } from "react";

const WS_BASE = (import.meta.env.VITE_API_URL || "http://localhost:5001").replace(/^http/, "ws");

export default function useSimulationWS(projectId, enabled = false) {
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState([]);
  const [lastAction, setLastAction] = useState(null);
  const [simStatus, setSimStatus] = useState(null);
  const wsRef = useRef(null);
  const retriesRef = useRef(0);
  const maxRetries = 5;

  const connect = useCallback(() => {
    if (!projectId || !enabled) return;

    const url = `${WS_BASE}/ws/simulation/${projectId}`;
    let ws;
    try {
      ws = new WebSocket(url);
    } catch {
      return;
    }
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      retriesRef.current = 0;
    };

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        const { event, data } = msg;

        if (event === "ping") return;

        // Track events (keep last 100)
        setEvents((prev) => {
          const next = [...prev, msg];
          return next.length > 100 ? next.slice(-100) : next;
        });

        if (event === "agent_action") {
          setLastAction(data);
        }
        if (event === "simulation_status" || event === "connected") {
          setSimStatus(data?.status || data?.simulation_status || null);
        }
      } catch {}
    };

    ws.onclose = () => {
      setConnected(false);
      wsRef.current = null;
      // Auto-reconnect
      if (enabled && retriesRef.current < maxRetries) {
        retriesRef.current++;
        setTimeout(connect, 2000 * retriesRef.current);
      }
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [projectId, enabled]);

  useEffect(() => {
    if (enabled && projectId) {
      connect();
    }
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [projectId, enabled, connect]);

  const sendCommand = useCallback((command, data = {}) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ command, ...data }));
    }
  }, []);

  return { connected, events, lastAction, simStatus, sendCommand };
}
