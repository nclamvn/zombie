import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import * as api from "./api/client.js";
import useSimulationWS from "./api/useSimulationWS.js";
import StadiumSimGraph from "./StadiumSimGraph.jsx";
import VOCCommandCenter from "./VOCCommandCenter.jsx";
import ModuleSimView from "./ModuleSimView.jsx";
import { THEMES, LANG } from "./theme.js";

// Module-level theme refs — updated by main component each render
// Allows utility components (Badge, Panel, etc.) to access current theme
let C = THEMES.light;
let L = LANG.vi;

const PHASE_STATUS = {
  created: "queued", seed_uploaded: "queued", ontology_designed: "running",
  graph_building: "running", graph_completed: "running", config_generated: "running",
  simulating: "running", simulation_completed: "running", reporting: "running",
  report_completed: "completed", interactive: "completed", failed: "failed",
};

// ─── Utility Components ───────────────────────────────────────
const Badge = ({ children, color = C.amber, bg }) => (
  <span style={{ fontSize: 10, fontWeight: 600, letterSpacing: 1, textTransform: "uppercase",
    color, background: bg || color + "18", padding: "2px 6px", borderRadius: 2, fontFamily: "'JetBrains Mono', monospace" }}>
    {children}
  </span>
);

const StatusDot = ({ status }) => {
  const colors = { running: C.green, completed: C.blue, paused: C.amber, failed: C.red, queued: C.text2 };
  return (
    <span style={{ display: "inline-block", width: 7, height: 7, borderRadius: "50%",
      background: colors[status] || C.text2, marginRight: 6,
      boxShadow: status === "running" ? `0 0 6px ${C.green}` : "none" }} />
  );
};

const MiniBar = ({ value, max = 1, color = C.amber, w = 60 }) => (
  <div style={{ width: w, height: 4, background: C.bg0, borderRadius: 2, overflow: "hidden" }}>
    <div style={{ width: `${(value / max) * 100}%`, height: "100%", background: color, borderRadius: 2, transition: "width 0.3s" }} />
  </div>
);

const Sparkline = ({ data, color = C.green, w = 80, h = 20 }) => {
  if (!data || data.length < 2) return <svg width={w} height={h} />;
  const max = Math.max(...data), min = Math.min(...data), range = max - min || 1;
  const points = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - ((v - min) / range) * h}`).join(" ");
  return <svg width={w} height={h} style={{ display: "block" }}><polyline points={points} fill="none" stroke={color} strokeWidth={1.2} /></svg>;
};

const HealthDot = ({ label, check, extra }) => {
  if (!check) return null;
  const color = check.status === "ok" ? C.green : check.status === "degraded" || check.status === "not_configured" ? C.amber : C.red;
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 3 }}>
      <span style={{ width: 5, height: 5, borderRadius: "50%", background: color, display: "inline-block" }} />
      {label}{extra ? `: ${extra}` : ""}
    </span>
  );
};

const Loader = ({ text = "Loading..." }) => (
  <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: C.text2, fontSize: 10, gap: 8 }}>
    <span style={{ display: "inline-block", width: 8, height: 8, border: `2px solid ${C.amber}`, borderTopColor: "transparent", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
    {text}
    <style>{`
      @keyframes spin { to { transform: rotate(360deg) } }
      @keyframes slideIn { from { opacity: 0; transform: translateY(-8px); } to { opacity: 1; transform: translateY(0); } }
      @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }
    `}</style>
  </div>
);

const Panel = ({ title, badge, children, style, headerRight, noPad }) => (
  <div style={{ background: C.bg1, border: `1px solid ${C.border}`, borderRadius: 3, display: "flex", flexDirection: "column", overflow: "hidden", ...style }}>
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "6px 10px",
      background: C.bg2, borderBottom: `1px solid ${C.border}`, flexShrink: 0 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span style={{ fontSize: 11, fontWeight: 600, color: C.amber, letterSpacing: 1, textTransform: "uppercase",
          fontFamily: "'JetBrains Mono', monospace" }}>{title}</span>
        {badge && <Badge>{badge}</Badge>}
      </div>
      {headerRight}
    </div>
    <div style={{ flex: 1, overflow: "auto", padding: noPad ? 0 : "8px 10px" }}>{children}</div>
  </div>
);

// ─── New Simulation Modal ─────────────────────────────────────
function NewSimModal({ onClose, onComplete }) {
  const [name, setName] = useState("RTR Analysis");
  const [requirement, setRequirement] = useState("");
  const [text, setText] = useState("");
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [stageLabel, setStageLabel] = useState("");
  const [stageName, setStageName] = useState("");
  const [events, setEvents] = useState([]);
  const [error, setError] = useState(null);
  const closeRef = useRef(null);

  const handleSubmit = async () => {
    if (!requirement.trim() || !text.trim()) return;
    setRunning(true); setError(null); setEvents([]);

    const result = await api.runPipelineStreaming(name, requirement, text, (type, data) => {
      if (type === "progress") {
        setProgress(data.progress || 0);
        setStageLabel(data.message || "");
        setStageName(data.stage || "");
      } else if (type === "stage_complete") {
        setEvents(prev => [...prev, { type: "done", msg: `${data.stage} complete` }]);
      } else if (type === "round") {
        setEvents(prev => {
          const next = [...prev, { type: "round", msg: `Round ${data.round_num}: ${data.actions_count} actions` }];
          return next.slice(-8);
        });
      } else if (type === "complete") {
        setProgress(1);
        setStageLabel("Pipeline complete!");
        setTimeout(() => onComplete(data.project_id), 600);
      } else if (type === "error") {
        setError(data.message);
        setRunning(false);
      }
    });

    closeRef.current = result.close;
    if (result.error && !error) { setError(result.error); setRunning(false); }
  };

  useEffect(() => {
    return () => { closeRef.current?.(); };
  }, []);

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}
      onClick={e => e.target === e.currentTarget && !running && onClose()}>
      <div style={{ background: C.bg1, border: `1px solid ${C.border}`, borderRadius: 4, width: 560, maxHeight: "80vh", overflow: "auto" }}>
        <div style={{ padding: "12px 16px", borderBottom: `1px solid ${C.border}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ fontSize: 12, fontWeight: 700, color: C.amber, letterSpacing: 1 }}>NEW SIMULATION</span>
          {!running && <span style={{ color: C.text2, cursor: "pointer", fontSize: 14 }} onClick={onClose}>x</span>}
        </div>
        <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 12 }}>
          {!running ? <>
            <div>
              <div style={{ fontSize: 9, color: C.text2, letterSpacing: 1, marginBottom: 4 }}>PROJECT NAME</div>
              <input value={name} onChange={e => setName(e.target.value)}
                style={{ width: "100%", background: C.bg0, border: `1px solid ${C.border}`, borderRadius: 2, padding: "6px 8px", color: C.text0, fontFamily: "inherit", fontSize: 11 }} />
            </div>
            <div>
              <div style={{ fontSize: 9, color: C.text2, letterSpacing: 1, marginBottom: 4 }}>REQUIREMENT *</div>
              <textarea value={requirement} onChange={e => setRequirement(e.target.value)} rows={3} placeholder="What do you want to predict or simulate?"
                style={{ width: "100%", background: C.bg0, border: `1px solid ${C.border}`, borderRadius: 2, padding: "6px 8px", color: C.text0, fontFamily: "inherit", fontSize: 11, resize: "vertical" }} />
            </div>
            <div>
              <div style={{ fontSize: 9, color: C.text2, letterSpacing: 1, marginBottom: 4 }}>SEED TEXT *</div>
              <textarea value={text} onChange={e => setText(e.target.value)} rows={6} placeholder="Paste your source material here..."
                style={{ width: "100%", background: C.bg0, border: `1px solid ${C.border}`, borderRadius: 2, padding: "6px 8px", color: C.text0, fontFamily: "inherit", fontSize: 11, resize: "vertical" }} />
            </div>
            {error && <div style={{ color: C.red, fontSize: 10, padding: "6px 8px", background: C.redDim, borderRadius: 2 }}>{error}</div>}
            <button onClick={handleSubmit} disabled={!requirement.trim() || !text.trim()}
              style={{ background: C.amber, color: C.bg0, border: "none", borderRadius: 2, padding: "8px 16px", fontFamily: "inherit", fontSize: 11, fontWeight: 700, cursor: "pointer", letterSpacing: 1, opacity: (!requirement.trim() || !text.trim()) ? 0.4 : 1 }}>
              RUN SIMULATION
            </button>
          </> : <>
            <div style={{ padding: "12px 0" }}>
              {/* Stage indicator */}
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                <span style={{ display: "inline-block", width: 8, height: 8, border: `2px solid ${C.amber}`, borderTopColor: "transparent", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
                <span style={{ fontSize: 12, color: C.text0 }}>{stageLabel}</span>
                <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
              </div>
              {/* Progress bar */}
              <div style={{ width: "100%", height: 6, background: C.bg0, borderRadius: 3, overflow: "hidden", marginBottom: 8 }}>
                <div style={{ width: `${progress * 100}%`, height: "100%", background: `linear-gradient(90deg, ${C.green}, ${C.amber})`, borderRadius: 3, transition: "width 0.3s" }} />
              </div>
              <div style={{ fontSize: 10, color: C.text2, marginBottom: 12 }}>{Math.round(progress * 100)}% — {stageName || "initializing"}</div>
              {/* Live event feed */}
              {events.length > 0 && (
                <div style={{ background: C.bg0, borderRadius: 2, padding: "6px 8px", maxHeight: 120, overflow: "auto" }}>
                  {events.map((evt, i) => (
                    <div key={i} style={{ fontSize: 9, color: evt.type === "done" ? C.green : C.text2, lineHeight: 1.8 }}>
                      {evt.type === "done" ? "+" : ">"} {evt.msg}
                    </div>
                  ))}
                </div>
              )}
              {error && <div style={{ color: C.red, fontSize: 10, marginTop: 12, padding: "6px 8px", background: C.redDim, borderRadius: 2 }}>{error}</div>}
            </div>
          </>}
        </div>
      </div>
    </div>
  );
}

// ─── Graph Visualization Helper ───────────────────────────────
function layoutNodes(nodes) {
  if (!nodes || !nodes.length) return [];
  const w = 600, h = 400;
  const entityColors = { Person: C.text1, Organization: C.blue, Executive: C.red, MediaOutlet: C.cyan, GovernmentAgency: C.green, Professor: C.purple };
  return nodes.map((n, i) => {
    const angle = (i / nodes.length) * Math.PI * 2;
    const radius = 120 + (i % 3) * 40;
    const label = (n.labels || []).find(l => l !== "Entity" && l !== "Node") || n.name?.slice(0, 6) || "?";
    return {
      x: w / 2 + Math.cos(angle) * radius,
      y: h / 2 + Math.sin(angle) * radius,
      r: Math.max(6, Math.min(16, 8 + (n.summary?.length || 0) / 30)),
      label: n.name?.slice(0, 10) || label,
      color: entityColors[label] || C.text2,
      uuid: n.uuid,
    };
  });
}

function buildEdgeLines(nodes, edges, layoutMap) {
  if (!edges || !layoutMap) return [];
  const uuidIdx = {};
  layoutMap.forEach((n, i) => { uuidIdx[n.uuid] = i; });
  return edges.filter(e => uuidIdx[e.source_node_uuid] !== undefined && uuidIdx[e.target_node_uuid] !== undefined)
    .map(e => [uuidIdx[e.source_node_uuid], uuidIdx[e.target_node_uuid]]);
}

// ─── Main Dashboard ───────────────────────────────────────────
export default function MiroFishDashboard() {
  // ── State ──
  const [themeId, setThemeId] = useState("light");
  const [langId, setLangId] = useState("vi");
  // Update module-level refs so utility components see current theme
  C = THEMES[themeId];
  L = LANG[langId];

  const [projects, setProjects] = useState([]);
  const [activeProjectId, setActiveProjectId] = useState(null);
  const [projectData, setProjectData] = useState(null);
  const [agents, setAgents] = useState([]);
  const [graphData, setGraphData] = useState(null);
  const [simData, setSimData] = useState(null);
  const [loading, setLoading] = useState({});
  const [connected, setConnected] = useState(true);
  const [showNewSim, setShowNewSim] = useState(false);
  const [tick, setTick] = useState(0);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [cmdInput, setCmdInput] = useState("");
  const [chatMsgs, setChatMsgs] = useState([
    { role: "system", text: "RTR ReportAgent ready. Ask about simulation results, agent behavior, or predictions." },
  ]);
  const [chatLoading, setChatLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("portal");
  const [healthData, setHealthData] = useState(null);
  const [simSpeed, setSimSpeed] = useState(1);
  const [showInjectModal, setShowInjectModal] = useState(false);
  const [liveRound, setLiveRound] = useState(0);
  const [recentAgentIds, setRecentAgentIds] = useState(new Set());
  const [comparisonData, setComparisonData] = useState(null);
  const [compareConfig, setCompareConfig] = useState("FULL"); // TETHERED or FULL vs BASELINE
  const [expandedScenario, setExpandedScenario] = useState(null);
  const [comparisonLoading, setComparisonLoading] = useState(false);
  const [fifaView, setFifaView] = useState("command"); // "data" | "sim" | "command"
  const [portalModule, setPortalModule] = useState(null); // active module ID when viewing from portal
  const [portalModuleData, setPortalModuleData] = useState(null); // loaded module comparison data
  const [portalDetailView, setPortalDetailView] = useState("sim"); // "data" | "sim" — default to sim for impact
  const chatEndRef = useRef(null);

  // ── Derived (must be before wsEnabled) ──
  const status = projectData ? (PHASE_STATUS[projectData.phase] || projectData.status || "queued") : "queued";

  // ── WebSocket for live simulation ──
  const wsEnabled = status === "running" && !!activeProjectId;
  const ws = useSimulationWS(activeProjectId, wsEnabled);

  // ── Derived (continued) ──
  const simSummary = simData?.summary || projectData?.simulation_summary || {};
  const totalRounds = simSummary.total_rounds || 0;
  const maxRounds = simData?.config?.time_config?.max_rounds || totalRounds || 1;
  const agentCount = agents.length || projectData?.agent_count || 0;
  const nodeCount = graphData?.info?.node_count || projectData?.graph_info?.node_count || 0;
  const edgeCount = graphData?.info?.edge_count || projectData?.graph_info?.edge_count || 0;

  // ── Sync body bg with theme ──
  useEffect(() => {
    document.body.style.background = C.bg0;
    document.body.style.color = C.text0;
  }, [themeId]);

  // ── Tick ──
  useEffect(() => {
    const interval = setInterval(() => setTick(t => t + 1), 2000);
    return () => clearInterval(interval);
  }, []);

  // ── Chat scroll ──
  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [chatMsgs]);

  // ── Track live round + recent agents from WS ──
  useEffect(() => {
    if (!ws.events.length) return;
    const last = ws.events[ws.events.length - 1];
    if (last?.event === "round_start" || last?.event === "round_end") {
      setLiveRound(last.data?.round_num || liveRound);
    }
    if (last?.event === "agent_action") {
      const aid = last.data?.agent_name;
      if (aid) {
        setRecentAgentIds(prev => {
          const next = new Set(prev);
          next.add(aid);
          // Clear after 3s
          setTimeout(() => setRecentAgentIds(p => { const n = new Set(p); n.delete(aid); return n; }), 3000);
          return next;
        });
      }
    }
  }, [ws.events.length]);

  // ── Load projects on mount + health polling (silent when no backend) ──
  useEffect(() => {
    loadProjects();
    const pollHealth = () => {
      api.checkHealth().then(r => {
        if (r.status === "ok") {
          setConnected(true);
          setHealthData(r.data?.checks ? r.data : r);
        }
      }).catch(() => {});
    };
    pollHealth();
    const hInterval = setInterval(pollHealth, 60000); // 60s instead of 30s
    return () => clearInterval(hInterval);
  }, []);

  // ── Poll active project if running ──
  useEffect(() => {
    if (!activeProjectId || status !== "running") return;
    const interval = setInterval(() => loadProjectData(activeProjectId), 5000);
    return () => clearInterval(interval);
  }, [activeProjectId, status]);

  // ── Load tab data when switching ──
  useEffect(() => {
    if (!activeProjectId) return;
    if (activeTab === "agents" && agents.length === 0) loadAgents(activeProjectId);
    if (activeTab === "graph" && !graphData) loadGraph(activeProjectId);
    if ((activeTab === "overview" || activeTab === "events") && !simData) loadSimulation(activeProjectId);
    if (activeTab === "fifa" && !comparisonData) {
      // Auto-load: try static file directly, then API
      (async () => {
        setComparisonLoading(true);
        try {
          const res = await fetch("/comparison.json");
          if (res.ok) {
            const raw = await res.json();
            await handleImportComparison(raw);
            return;
          }
        } catch {}
        if (activeProjectId) loadComparison(activeProjectId);
        else setComparisonLoading(false);
      })();
    }
  }, [activeTab, activeProjectId]);

  // ── Data loaders ──
  async function loadProjects() {
    const r = await api.listProjects();
    if (r.status === "ok" && r.data?.projects) {
      setProjects(r.data.projects);
      setConnected(true);
      if (!activeProjectId && r.data.projects.length > 0) {
        selectProject(r.data.projects[0].project_id);
      }
    } else {
      setConnected(false);
    }
  }

  async function selectProject(id) {
    setActiveProjectId(id);
    setGraphData(null); setAgents([]); setSimData(null); setComparisonData(null);
    setChatMsgs([{ role: "system", text: "ReportAgent ready. Ask about this simulation." }]);
    loadProjectData(id);
  }

  async function loadProjectData(id) {
    setLoading(l => ({ ...l, project: true }));
    const r = await api.getProject(id);
    if (r.status === "ok") setProjectData(r.data);
    setLoading(l => ({ ...l, project: false }));
  }

  async function loadAgents(id) {
    setLoading(l => ({ ...l, agents: true }));
    const r = await api.getAgents(id);
    if (r.status === "ok" && r.data?.agents) setAgents(r.data.agents);
    setLoading(l => ({ ...l, agents: false }));
  }

  async function loadGraph(id) {
    setLoading(l => ({ ...l, graph: true }));
    const r = await api.getGraph(id);
    if (r.status === "ok") setGraphData(r.data);
    setLoading(l => ({ ...l, graph: false }));
  }

  async function loadSimulation(id) {
    setLoading(l => ({ ...l, sim: true }));
    const r = await api.getSimulation(id);
    if (r.status === "ok") setSimData(r.data);
    setLoading(l => ({ ...l, sim: false }));
  }

  async function loadComparison(id) {
    setComparisonLoading(true);
    // Try API first (only if real project)
    if (id && id !== "_default") {
      const r = await api.getComparison(id);
      if (r.status === "ok" && r.data?.summary) {
        setComparisonData(r.data.summary);
        setComparisonLoading(false);
        return;
      }
    }
    // Fallback: load pre-computed static file
    try {
      const res = await fetch("/comparison.json");
      if (res.ok) {
        const raw = await res.json();
        await handleImportComparison(raw);
        return;
      }
    } catch (e) { console.warn("Static comparison load failed:", e); }
    setComparisonLoading(false);
  }

  async function handleImportComparison(jsonData) {
    setComparisonLoading(true);
    // Client-side aggregation — works without backend
    try {
      const scenarios = [];
      const masterKpi = {};
      for (const [scenarioId, sdata] of Object.entries(jsonData)) {
        const configs = sdata.configs || {};
        const entry = { id: scenarioId, name: sdata.name || scenarioId, category: sdata.category || "unknown", configs: {} };
        for (const [cfgId, runs] of Object.entries(configs)) {
          const kpiAgg = {};
          if (runs.length > 0) {
            for (const key of Object.keys(runs[0].kpi || {})) {
              const vals = runs.map(r => r.kpi[key]).filter(v => v != null);
              const n = vals.length, mean = vals.reduce((a, b) => a + b, 0) / n;
              const std = Math.sqrt(vals.reduce((a, v) => a + (v - mean) ** 2, 0) / Math.max(n - 1, 1));
              kpiAgg[key] = { mean: +mean.toFixed(1), std: +std.toFixed(1), min: +Math.min(...vals).toFixed(1), max: +Math.max(...vals).toFixed(1), n };
              masterKpi[cfgId] = masterKpi[cfgId] || {};
              masterKpi[cfgId][key] = masterKpi[cfgId][key] || [];
              masterKpi[cfgId][key].push(...vals);
            }
          }
          entry.configs[cfgId] = { runs: runs.length, kpi: kpiAgg };
        }
        scenarios.push(entry);
      }
      // Aggregate master KPI
      const masterSummary = {};
      for (const [cfgId, kpis] of Object.entries(masterKpi)) {
        masterSummary[cfgId] = {};
        for (const [k, vals] of Object.entries(kpis)) {
          const n = vals.length, mean = vals.reduce((a, b) => a + b, 0) / n;
          const std = Math.sqrt(vals.reduce((a, v) => a + (v - mean) ** 2, 0) / Math.max(n - 1, 1));
          masterSummary[cfgId][k] = { mean: +mean.toFixed(1), std: +std.toFixed(1), min: +Math.min(...vals).toFixed(1), max: +Math.max(...vals).toFixed(1), n };
        }
      }
      const totalRuns = Object.values(jsonData).reduce((sum, s) => sum + Object.values(s.configs || {}).reduce((s2, runs) => s2 + runs.length, 0), 0);
      setComparisonData({ scenarios, master_kpi: masterSummary, total_scenarios: scenarios.length, total_runs: totalRuns });
    } catch (e) { console.error("Import failed:", e); }
    // Also try backend if connected
    if (activeProjectId) {
      api.importComparison(activeProjectId, jsonData).catch(() => {});
    }
    setComparisonLoading(false);
  }

  async function handleRunComparison() {
    if (!activeProjectId) return;
    setComparisonLoading(true);
    const r = await api.runComparison(activeProjectId);
    if (r.status === "ok") {
      // Poll for completion
      const poll = setInterval(async () => {
        const cr = await api.getComparison(activeProjectId);
        if (cr.status === "ok" && cr.data?.summary) {
          setComparisonData(cr.data.summary);
          setComparisonLoading(false);
          clearInterval(poll);
        }
      }, 3000);
    } else {
      setComparisonLoading(false);
    }
  }

  // ── Chat handler ──
  const handleCmd = useCallback(async () => {
    if (!cmdInput.trim() || !activeProjectId || chatLoading) return;
    const msg = cmdInput;
    setCmdInput("");
    setChatMsgs(prev => [...prev, { role: "user", text: msg }]);
    setChatLoading(true);
    const r = await api.chat(activeProjectId, msg);
    setChatLoading(false);
    if (r.status === "ok") {
      setChatMsgs(prev => [...prev, { role: "agent", text: r.data.response }]);
    } else {
      setChatMsgs(prev => [...prev, { role: "agent", text: `Error: ${r.error}` }]);
    }
  }, [cmdInput, activeProjectId, chatLoading]);

  // ── New simulation complete ──
  const handleNewSimComplete = async (projectId) => {
    setShowNewSim(false);
    await loadProjects();
    selectProject(projectId);
  };

  // ── Graph layout ──
  const graphNodes = useMemo(() => layoutNodes(graphData?.nodes || []), [graphData?.nodes]);
  const graphEdges = useMemo(() => buildEdgeLines(graphData?.nodes, graphData?.edges, graphNodes), [graphData, graphNodes]);

  // ── Event feed from simulation rounds + live WS events ──
  const eventFeed = useMemo(() => {
    const events = [];
    // Live WS events first (newest on top)
    for (const wsEvt of [...ws.events].reverse().slice(0, 20)) {
      const d = wsEvt.data || {};
      if (wsEvt.event === "agent_action") {
        events.push({ time: `R${d.round_num || "?"}`, type: "ACTION", msg: `${d.agent_name} → ${d.action_type}${d.content ? ": " + d.content.slice(0, 60) : ""}`, live: true });
      } else if (wsEvt.event === "round_end") {
        events.push({ time: `R${d.round_num}`, type: "SYSTEM", msg: `Round ${d.round_num}: ${d.actions_count || 0} actions`, live: true });
      } else if (wsEvt.event === "event_fired") {
        events.push({ time: "INJ", type: "EVENT", msg: d.name || "Event injected", live: true });
      }
    }
    // Fallback to stored rounds if no live events
    if (events.length === 0 && simData?.rounds) {
      for (const round of (simData.rounds || []).slice(-10).reverse()) {
        events.push({ time: `R${round.round_num}`, type: "SYSTEM", msg: `Round ${round.round_num}: ${round.actions_count || 0} actions` });
        for (const a of (round.actions || []).slice(0, 3)) {
          events.push({ time: `R${round.round_num}`, type: "ACTION", msg: `${a.agent_name} → ${a.action_type}${a.result ? ": " + a.result.slice(0, 60) : ""}` });
        }
      }
    }
    return events.slice(0, 20);
  }, [simData, ws.events]);

  // ── Timeline from rounds + live WS round_end events ──
  const timelineData = useMemo(() => {
    const stored = (simData?.rounds || []).map(r => ({
      round: r.round_num,
      actions: r.actions_count || (r.actions || []).length,
      activeAgents: (r.active_agent_ids || []).length,
    }));
    // Append live rounds from WS
    const liveRounds = ws.events
      .filter(e => e.event === "round_end")
      .map(e => ({ round: e.data.round_num, actions: e.data.actions_count || 0, activeAgents: 0 }));
    // Merge: stored first, then any live rounds not in stored
    const storedNums = new Set(stored.map(r => r.round));
    const merged = [...stored, ...liveRounds.filter(r => !storedNums.has(r.round))];
    return merged.sort((a, b) => a.round - b.round);
  }, [simData, ws.events]);

  // ── Entity distribution from graph ──
  const entityDist = useMemo(() => {
    if (!graphData?.nodes) return [];
    const counts = {};
    for (const n of graphData.nodes) {
      const label = (n.labels || []).find(l => l !== "Entity" && l !== "Node") || "Other";
      counts[label] = (counts[label] || 0) + 1;
    }
    return Object.entries(counts).sort((a, b) => b[1] - a[1]).map(([label, count]) => ({ label, count }));
  }, [graphData]);

  // ── Ontology from project ──
  const ontologyEdges = useMemo(() => {
    if (!projectData?.ontology?.edge_types) return [];
    return projectData.ontology.edge_types.map(et => ({
      name: et.name,
      sources: (et.source_targets || []).map(st => `${st.source} → ${et.name} → ${st.target}`),
    }));
  }, [projectData]);

  const tabs = [
    { id: "portal", label: "PORTAL" },
    { id: "overview", label: L.overview },
    { id: "agents", label: L.agentsTab },
    { id: "graph", label: L.kGraph },
    { id: "events", label: L.events },
    { id: "fifa", label: L.fifa },
  ];

  const simName = projectData?.name || L.noProject;
  const simId = projectData?.project_id || "—";

  return (
    <div style={{ background: C.bg0, color: C.text0, fontFamily: "'JetBrains Mono', 'SF Mono', 'Fira Code', monospace",
      fontSize: 11, minHeight: "100vh", display: "flex", flexDirection: "column" }}>

      {/* Connection banner — hidden in demo mode (no backend needed) */}

      {/* ═══ TOP BAR ═══ */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "6px 12px", background: C.bg1, borderBottom: `1px solid ${C.border}`, flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 14, fontWeight: 700, color: C.amber, letterSpacing: 2 }}>RTR SIMULATOR</span>
          <span style={{ color: C.text2, fontSize: 10 }}>{L.title}</span>
          <span style={{ color: C.text2 }}>|</span>
          <span style={{ color: connected ? C.green : C.red, fontSize: 10 }}>{connected ? L.connected : L.disconnected}</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ color: C.text2, fontSize: 10 }}>{L.agents}: {agentCount}</span>
          <span style={{ color: C.text2, fontSize: 10 }}>{L.projects}: {projects.length}</span>
          <span style={{ color: C.text1, fontSize: 10 }}>{new Date().toLocaleTimeString("en-US", { hour12: false })}</span>
          <button onClick={() => setLangId(l => l === "vi" ? "en" : "vi")}
            style={{ background: C.bg2, border: `1px solid ${C.border}`, borderRadius: 3, padding: "2px 8px", color: C.text1,
              cursor: "pointer", fontFamily: "inherit", fontSize: 9, fontWeight: 600 }}>
            {langId === "vi" ? "VI 🇻🇳" : "EN 🇬🇧"}
          </button>
          <button onClick={() => setThemeId(t => t === "light" ? "dark" : "light")}
            style={{ background: C.bg2, border: `1px solid ${C.border}`, borderRadius: 3, padding: "2px 8px", color: C.text1,
              cursor: "pointer", fontFamily: "inherit", fontSize: 9 }}>
            {themeId === "light" ? "☀" : "◐"}
          </button>
          <button onClick={() => setShowNewSim(true)}
            style={{ background: C.amber + "18", border: `1px solid ${C.amber}44`, borderRadius: 2, padding: "2px 10px", color: C.amber,
              cursor: "pointer", fontFamily: "inherit", fontSize: 9, fontWeight: 700, letterSpacing: 1 }}>
            {L.newProject}
          </button>
        </div>
      </div>

      {/* ═══ SCENARIO STRIP (hidden when no projects) ═══ */}
      {projects.length > 0 && (
        <div style={{ display: "flex", gap: 1, borderBottom: `1px solid ${C.border}`, flexShrink: 0, overflow: "auto" }}>
          {projects.map((s) => (
            <button key={s.project_id} onClick={() => selectProject(s.project_id)}
              style={{ flex: "0 0 auto", padding: "6px 14px", background: s.project_id === activeProjectId ? C.bg2 : "transparent",
                border: "none", borderBottom: s.project_id === activeProjectId ? `2px solid ${C.amber}` : "2px solid transparent",
                color: s.project_id === activeProjectId ? C.text0 : C.text2, cursor: "pointer", fontFamily: "inherit", fontSize: 10,
                display: "flex", alignItems: "center", gap: 6, transition: "all 0.15s", whiteSpace: "nowrap" }}>
              <StatusDot status={PHASE_STATUS[s.phase] || s.status} />
              <span>{s.project_id.slice(0, 12)}</span>
              <span style={{ color: s.project_id === activeProjectId ? C.text1 : C.text2, maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis" }}>{s.name}</span>
            </button>
          ))}
        </div>
      )}

      {/* ═══ SIMULATION HEADER (hidden on FIFA tab when no project) ═══ */}
      {(activeProjectId || (activeTab !== "fifa" && activeTab !== "portal")) && <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "6px 12px", background: C.bg1, borderBottom: `1px solid ${C.border}`, flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: C.text0 }}>{simName}</div>
          {agentCount > 0 && <span style={{ fontSize: 9, color: C.text2 }}>{agentCount} agents</span>}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: 10, color: C.text2 }}>ROUND</div>
            <div style={{ fontSize: 16, fontWeight: 700, color: C.amber }}>{liveRound || totalRounds}<span style={{ color: C.text2, fontSize: 11 }}>/{maxRounds}</span></div>
          </div>
          <div style={{ width: 120, height: 6, background: C.bg0, borderRadius: 3, overflow: "hidden" }}>
            <div style={{ width: `${maxRounds > 0 ? (totalRounds / maxRounds) * 100 : 0}%`,
              height: "100%", background: status === "running" ? C.green : status === "completed" ? C.blue : C.amber,
              borderRadius: 3, transition: "width 0.5s" }} />
          </div>
          <Badge color={status === "running" ? C.green : status === "completed" ? C.blue : status === "failed" ? C.red : C.amber}>
            {ws.simStatus || status}
          </Badge>
          {/* Simulation controls */}
          {ws.connected && (status === "running" || ws.simStatus === "paused") && (
            <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
              {ws.simStatus === "paused" ? (
                <button onClick={() => ws.sendCommand("resume")}
                  style={{ background: C.green, color: C.bg0, border: "none", borderRadius: 2, padding: "3px 8px", fontFamily: "inherit", fontSize: 9, fontWeight: 700, cursor: "pointer" }}>
                  RESUME
                </button>
              ) : (
                <button onClick={() => ws.sendCommand("pause")}
                  style={{ background: C.amber, color: C.bg0, border: "none", borderRadius: 2, padding: "3px 8px", fontFamily: "inherit", fontSize: 9, fontWeight: 700, cursor: "pointer" }}>
                  PAUSE
                </button>
              )}
              <select value={simSpeed} onChange={e => { const v = Number(e.target.value); setSimSpeed(v); ws.sendCommand("set_speed", { multiplier: v }); }}
                style={{ background: C.bg0, color: C.text1, border: `1px solid ${C.border}`, borderRadius: 2, padding: "2px 4px", fontFamily: "inherit", fontSize: 9 }}>
                <option value={1}>1x</option><option value={2}>2x</option><option value={5}>5x</option><option value={10}>10x</option>
              </select>
              <button onClick={() => setShowInjectModal(true)}
                style={{ background: C.bg2, color: C.cyan, border: `1px solid ${C.border}`, borderRadius: 2, padding: "3px 8px", fontFamily: "inherit", fontSize: 9, fontWeight: 600, cursor: "pointer" }}>
                INJECT
              </button>
            </div>
          )}
        </div>
      </div>}

      {/* ═══ TAB BAR ═══ */}
      <div style={{ display: "flex", gap: 0, borderBottom: `1px solid ${C.border}`, flexShrink: 0 }}>
        {tabs.map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            style={{ padding: "6px 16px", background: "transparent", border: "none",
              borderBottom: activeTab === tab.id ? `2px solid ${C.amber}` : "2px solid transparent",
              color: activeTab === tab.id ? C.amber : C.text2, cursor: "pointer", fontFamily: "inherit",
              fontSize: 10, letterSpacing: 1, fontWeight: 600, transition: "all 0.15s" }}>
            {tab.label}
          </button>
        ))}
      </div>

      {/* ═══ MAIN CONTENT ═══ */}
      <div style={{ flex: 1, display: "grid",
        gridTemplateColumns: (activeTab === "agents" || activeTab === "fifa" || activeTab === "portal") ? "1fr" : "1fr 320px",
        gridTemplateRows: "1fr 1fr", minHeight: 0,
        gap: 1, padding: 1, minHeight: 0, overflow: "hidden" }}>

        {/* ═══ PORTAL TAB ═══ */}
        {activeTab === "portal" && (
          <div style={{ gridColumn: "1 / -1", gridRow: "1 / -1", overflow: "auto", padding: 16, minHeight: 0 }}>

            {/* ── Module Detail View ── */}
            {portalModule && (
              <div>
                <button onClick={() => { setPortalModule(null); setPortalModuleData(null); }}
                  style={{ background: C.bg2, border: `1px solid ${C.border}`, borderRadius: 3, padding: "4px 12px", color: C.text1, fontSize: 10, cursor: "pointer", fontFamily: "inherit", marginBottom: 12 }}>
                  ← {langId === "vi" ? "Quay lại Portal" : "Back to Portal"}
                </button>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
                  <div>
                    <div style={{ fontSize: 16, fontWeight: 800, color: C.text0 }}>{portalModule[langId] || portalModule.en}</div>
                    <div style={{ fontSize: 10, color: C.text2, marginTop: 2 }}>{portalModule.id} · {portalModule.sc} {langId === "vi" ? "kịch bản" : "scenarios"} · {portalModule.runs} runs · -{portalModule.imp}%</div>
                  </div>
                  <div style={{ display: "flex", gap: 0 }}>
                    {[{ id: "sim", label: langId === "vi" ? "MÔ PHỎNG" : "SIMULATION" }, { id: "data", label: langId === "vi" ? "DỮ LIỆU" : "DATA" }].map(v => (
                      <button key={v.id} onClick={() => setPortalDetailView(v.id)}
                        style={{ padding: "4px 12px", background: "transparent", border: "none",
                          borderBottom: portalDetailView === v.id ? `2px solid ${C.cyan}` : "2px solid transparent",
                          color: portalDetailView === v.id ? C.cyan : C.text2, cursor: "pointer", fontFamily: "inherit",
                          fontSize: 10, fontWeight: 700, letterSpacing: 1 }}>
                        {v.label}
                      </button>
                    ))}
                  </div>
                </div>
                {portalDetailView === "sim" && portalModuleData ? (
                  <div style={{ height: "calc(100vh - 220px)", minHeight: 400 }}>
                    <ModuleSimView moduleData={portalModuleData} moduleMeta={portalModule} themeId={themeId} langId={langId} />
                  </div>
                ) : portalDetailView === "data" && portalModuleData ? (
                  <FifaComparisonTab
                    data={portalModuleData}
                    loading={false}
                    compareConfig={compareConfig}
                    setCompareConfig={setCompareConfig}
                    expandedScenario={expandedScenario}
                    setExpandedScenario={setExpandedScenario}
                    onImport={() => {}}
                    onRunComparison={() => {}}
                    onExportReport={() => {}}
                    C={C} L={L}
                  />
                ) : (
                  <div style={{ color: C.text2, textAlign: "center", padding: 40 }}>
                    {langId === "vi" ? "Đang tải dữ liệu..." : "Loading data..."}
                  </div>
                )}
              </div>
            )}

            {/* ── Portal Grid ── */}
            {!portalModule && <>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
              <div>
                <div style={{ fontSize: 18, fontWeight: 800, color: C.text0, letterSpacing: 1 }}>RTR SIMULATOR PORTAL</div>
                <div style={{ fontSize: 11, color: C.text2, marginTop: 2 }}>
                  {langId === "vi" ? "17 modules mô phỏng · 87 kịch bản · 4 lĩnh vực" : "17 simulation modules · 87 scenarios · 4 domains"}
                </div>
              </div>
            </div>
            {[
              { cat: "defense", label: langId === "vi" ? "QUỐC PHÒNG" : "DEFENSE", color: C.red, icon: "⚔" },
              { cat: "public_safety", label: langId === "vi" ? "AN TOÀN CÔNG CỘNG" : "PUBLIC SAFETY", color: C.amber, icon: "🛡" },
              { cat: "emergency", label: langId === "vi" ? "CỨU HỘ KHẨN CẤP" : "EMERGENCY RESPONSE", color: C.blue, icon: "🚨" },
              { cat: "industrial", label: langId === "vi" ? "CÔNG NGHIỆP" : "INDUSTRIAL", color: C.green, icon: "⚙" },
              { cat: "general", label: langId === "vi" ? "KHÁC" : "OTHER", color: C.text2, icon: "●" },
            ].map(group => {
              const PORTAL_MODULES = {
                stadium_operations: { vi: "Sân vận động FIFA", en: "Stadium Ops (FIFA)", cat: "public_safety", sc: 12, runs: 1800, imp: 50 },
                counter_uas: { vi: "Chống Drone", en: "Counter-UAS", cat: "defense", sc: 6, runs: 900, imp: 49 },
                isr_surveillance: { vi: "Trinh sát ISR", en: "ISR Surveillance", cat: "defense", sc: 6, runs: 900, imp: 51 },
                swarm_tactics: { vi: "Bay đàn 200 drone", en: "Swarm Tactics", cat: "defense", sc: 6, runs: 900, imp: 49 },
                border_patrol: { vi: "Tuần tra biên giới", en: "Border Patrol", cat: "defense", sc: 6, runs: 900, imp: 50 },
                perimeter_defense: { vi: "Bảo vệ căn cứ", en: "Perimeter Defense", cat: "defense", sc: 5, runs: 750, imp: 49 },
                concert_festival: { vi: "Concert / Lễ hội", en: "Concert & Festival", cat: "public_safety", sc: 5, runs: 750, imp: 48 },
                traffic_management: { vi: "Giao thông TPHCM", en: "Traffic Management", cat: "public_safety", sc: 5, runs: 750, imp: 49 },
                crowd_management: { vi: "Quản lý đám đông", en: "Crowd Management", cat: "public_safety", sc: 4, runs: 600, imp: 49 },
                search_rescue: { vi: "Tìm kiếm cứu nạn", en: "Search & Rescue", cat: "emergency", sc: 6, runs: 900, imp: 47 },
                fire_response: { vi: "Cháy rừng / Tòa nhà", en: "Fire Response", cat: "emergency", sc: 6, runs: 900, imp: 50 },
                flood_disaster: { vi: "Lũ lụt thiên tai", en: "Flood & Disaster", cat: "emergency", sc: 5, runs: 750, imp: 48 },
                hazmat_response: { vi: "Hóa chất phóng xạ", en: "HAZMAT Response", cat: "emergency", sc: 4, runs: 600, imp: 48 },
                infrastructure_inspection: { vi: "Kiểm tra hạ tầng", en: "Infrastructure", cat: "industrial", sc: 5, runs: 750, imp: 49 },
                agriculture: { vi: "Nông nghiệp 500ha", en: "Agriculture", cat: "industrial", sc: 4, runs: 600, imp: 51 },
                mapping_survey: { vi: "Đo đạc 3D", en: "Mapping & Survey", cat: "industrial", sc: 4, runs: 600, imp: 53 },
                delivery_logistics: { vi: "Logistics đảo", en: "Drone Delivery", cat: "industrial", sc: 5, runs: 750, imp: 50 },
              };
              const mods = Object.entries(PORTAL_MODULES).filter(([_, m]) => m.cat === group.cat);
              if (mods.length === 0) return null;
              return (
                <div key={group.cat} style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: 11, fontWeight: 800, color: group.color, letterSpacing: 2, marginBottom: 8, display: "flex", alignItems: "center", gap: 6 }}>
                    <span>{group.icon}</span> {group.label}
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 8 }}>
                    {mods.map(([id, meta]) => {
                      const isStadium = id === "stadium_operations";
                      const dataFile = isStadium ? "/comparison.json" : `/data_${id}.json`;
                      return (
                        <div key={id} onClick={async () => {
                            if (isStadium) {
                              setActiveTab("fifa"); setFifaView("command");
                            } else {
                              // Load this module's data and show detail view
                              setPortalModule({ id, ...meta });
                              setPortalModuleData(null);
                              try {
                                const res = await fetch(dataFile);
                                if (res.ok) {
                                  const raw = await res.json();
                                  // Client-side aggregate
                                  const scenarios = []; const masterKpi = {};
                                  for (const [sid, sd] of Object.entries(raw)) {
                                    const entry = { id: sid, name: sd.name || sid, category: sd.category || "general", configs: {} };
                                    for (const [cid, runs] of Object.entries(sd.configs || {})) {
                                      const kpiAgg = {};
                                      if (runs.length > 0) {
                                        for (const key of Object.keys(runs[0].kpi || {})) {
                                          const vals = runs.map(r => r.kpi[key]).filter(v => v != null);
                                          const n = vals.length, mean = vals.reduce((a,b) => a+b, 0) / n;
                                          const std = Math.sqrt(vals.reduce((a,v) => a+(v-mean)**2, 0) / Math.max(n-1,1));
                                          kpiAgg[key] = { mean: +mean.toFixed(1), std: +std.toFixed(1), n };
                                          masterKpi[cid] = masterKpi[cid] || {}; masterKpi[cid][key] = masterKpi[cid][key] || [];
                                          masterKpi[cid][key].push(...vals);
                                        }
                                      }
                                      entry.configs[cid] = { runs: runs.length, kpi: kpiAgg };
                                    }
                                    scenarios.push(entry);
                                  }
                                  const ms = {}; for (const [cid, kpis] of Object.entries(masterKpi)) { ms[cid] = {}; for (const [k, vals] of Object.entries(kpis)) { const n=vals.length, mean=vals.reduce((a,b)=>a+b,0)/n; const std=Math.sqrt(vals.reduce((a,v)=>a+(v-mean)**2,0)/Math.max(n-1,1)); ms[cid][k]={mean:+mean.toFixed(1),std:+std.toFixed(1),n}; } }
                                  const totalRuns = Object.values(raw).reduce((s, sd) => s + Object.values(sd.configs||{}).reduce((s2,r) => s2+r.length, 0), 0);
                                  setPortalModuleData({ scenarios, master_kpi: ms, total_scenarios: scenarios.length, total_runs: totalRuns });
                                }
                              } catch {}
                            }
                          }}
                          style={{ background: C.bg2, border: `1px solid ${group.color}40`, borderRadius: 6,
                            padding: "12px 14px", cursor: "pointer",
                            borderLeft: `3px solid ${group.color}`, transition: "all 0.2s" }}>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                            <span style={{ fontSize: 12, fontWeight: 700, color: C.text0 }}>{meta[langId] || meta.en}</span>
                            <span style={{ fontSize: 9, fontWeight: 700, color: C.green }}>-{meta.imp}%</span>
                          </div>
                          <div style={{ fontSize: 9, color: C.text2, marginBottom: 6 }}>{id}</div>
                          <div style={{ display: "flex", gap: 6, fontSize: 9 }}>
                            <span style={{ color: C.text1 }}>{meta.sc} {langId === "vi" ? "kịch bản" : "scenarios"}</span>
                            <span style={{ color: C.text2 }}>·</span>
                            <span style={{ color: C.text1 }}>{meta.runs.toLocaleString()} runs</span>
                            {isStadium && <><span style={{ color: C.text2 }}>·</span><span style={{ color: C.green }}>102 LLM</span></>}
                          </div>
                          <div style={{ marginTop: 6, height: 3, background: C.border, borderRadius: 2, overflow: "hidden" }}>
                            <div style={{ height: "100%", width: `${meta.imp}%`, background: group.color, borderRadius: 2 }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
            </>}
          </div>
        )}

        {activeTab === "overview" && <>
          {/* ── Metrics + Timeline ── */}
          <Panel title="SIMULATION METRICS" badge={status === "running" ? "LIVE" : status.toUpperCase()} style={{ gridColumn: "1", gridRow: "1" }}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 8, marginBottom: 12 }}>
              {[
                { label: "TOTAL ACTIONS", value: (simSummary.total_actions || 0).toLocaleString() },
                { label: "TOTAL ROUNDS", value: totalRounds.toString() },
                { label: "TOTAL AGENTS", value: agentCount.toString() },
                { label: "CONTENT CREATED", value: (simSummary.content_created || 0).toString() },
                { label: "GRAPH NODES", value: nodeCount.toString() },
                { label: "GRAPH EDGES", value: edgeCount.toLocaleString() },
              ].map((kpi, i) => (
                <div key={i} style={{ background: C.bg0, borderRadius: 2, padding: "8px 10px", border: `1px solid ${C.border}` }}>
                  <div style={{ fontSize: 9, color: C.text2, letterSpacing: 1, marginBottom: 4 }}>{kpi.label}</div>
                  <div style={{ fontSize: 16, fontWeight: 700, color: C.text0 }}>{kpi.value}</div>
                </div>
              ))}
            </div>
            {timelineData.length > 0 ? <>
              <div style={{ fontSize: 9, color: C.text2, marginBottom: 4, letterSpacing: 1 }}>ACTIVITY BY ROUND ({timelineData.length} rounds)</div>
              <div style={{ height: 90, display: "flex", alignItems: "flex-end", gap: 1, padding: "0 2px" }}>
                {timelineData.map((d, i) => {
                  const maxA = Math.max(...timelineData.map(t => t.actions)) || 1;
                  const h = (d.actions / maxA) * 85;
                  return (
                    <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 1 }}>
                      <div style={{ width: "100%", height: Math.max(h, 2), background: i === timelineData.length - 1 ? C.amber : C.blue + "70",
                        borderRadius: "1px 1px 0 0", transition: "height 0.3s" }} />
                      {timelineData.length <= 30 && i % Math.max(1, Math.floor(timelineData.length / 10)) === 0 && (
                        <span style={{ fontSize: 8, color: C.text2 }}>R{d.round}</span>
                      )}
                    </div>
                  );
                })}
              </div>
            </> : (
              <div style={{ color: C.text2, fontSize: 10, textAlign: "center", padding: 20 }}>No simulation data yet</div>
            )}
          </Panel>

          {/* ── Event Feed ── */}
          <Panel title="EVENT FEED" badge={ws.connected ? "LIVE" : `${eventFeed.length}`}
            style={{ gridColumn: "2", gridRow: "1" }} noPad>
            {eventFeed.length > 0 ? eventFeed.map((evt, i) => {
              const typeColors = { EVENT: C.amber, ACTION: C.blue, SYSTEM: C.text2, ALERT: C.red };
              return (
                <div key={i} style={{ padding: "5px 10px", borderBottom: `1px solid ${C.border}`,
                  display: "flex", gap: 8, alignItems: "flex-start", fontSize: 10,
                  animation: evt.live && i < 3 ? "slideIn 0.3s ease-out" : "none",
                  background: evt.live && i === 0 ? C.bg2 : "transparent" }}>
                  <span style={{ color: C.text2, flexShrink: 0, width: 36 }}>{evt.time}</span>
                  <span style={{ color: typeColors[evt.type] || C.text2, fontWeight: 600, flexShrink: 0, width: 50 }}>{evt.type}</span>
                  <span style={{ color: C.text1, lineHeight: 1.4 }}>{evt.msg}</span>
                  {evt.live && i === 0 && <span style={{ color: C.green, fontSize: 8, animation: "pulse 1s infinite" }}>LIVE</span>}
                </div>
              );
            }) : <div style={{ padding: 16, color: C.text2, fontSize: 10 }}>No events yet — run a simulation</div>}
          </Panel>

          {/* ── Knowledge Graph Mini ── */}
          <Panel title="KNOWLEDGE GRAPH" badge={`${nodeCount}N ${edgeCount}E`}
            style={{ gridColumn: "1", gridRow: "2" }}
            headerRight={<span style={{ fontSize: 9, color: C.text2, cursor: "pointer" }} onClick={() => setActiveTab("graph")}>EXPAND</span>}>
            <div style={{ display: "flex", gap: 12 }}>
              {graphNodes.length > 0 ? (
                <svg viewBox="0 0 600 400" style={{ flex: 1, maxHeight: 200 }}>
                  {graphEdges.map(([a, b], i) => (
                    <line key={i} x1={graphNodes[a]?.x} y1={graphNodes[a]?.y} x2={graphNodes[b]?.x} y2={graphNodes[b]?.y}
                      stroke={C.border} strokeWidth={0.5} opacity={0.6} />
                  ))}
                  {graphNodes.map((n, i) => (
                    <g key={i}>
                      <circle cx={n.x} cy={n.y} r={n.r} fill={n.color + "30"} stroke={n.color} strokeWidth={1} />
                      <text x={n.x} y={n.y + 3} textAnchor="middle" fill={n.color} fontSize={7} fontFamily="inherit">{n.label}</text>
                    </g>
                  ))}
                </svg>
              ) : (
                <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: C.text2, fontSize: 10, height: 150 }}>
                  {loading.graph ? <Loader text="Loading graph..." /> : "No graph data"}
                </div>
              )}
              <div style={{ width: 160, display: "flex", flexDirection: "column", gap: 4 }}>
                <div style={{ fontSize: 9, color: C.text2, letterSpacing: 1, marginBottom: 4 }}>ENTITY DISTRIBUTION</div>
                {entityDist.slice(0, 7).map((e, i) => (
                  <div key={i} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 10 }}>
                    <span style={{ width: 6, height: 6, borderRadius: 1, background: C.text1, flexShrink: 0 }} />
                    <span style={{ color: C.text1, flex: 1 }}>{e.label}</span>
                    <span style={{ color: C.text2 }}>{e.count}</span>
                    <MiniBar value={e.count} max={entityDist[0]?.count || 1} color={C.blue} w={40} />
                  </div>
                ))}
                {entityDist.length === 0 && <div style={{ color: C.text2, fontSize: 9 }}>No data</div>}
              </div>
            </div>
          </Panel>

          {/* ── Report Agent Chat ── */}
          <Panel title="REPORT AGENT" badge="ReACT" style={{ gridColumn: "2", gridRow: "2" }}>
            <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
              <div style={{ flex: 1, overflow: "auto", display: "flex", flexDirection: "column", gap: 6, marginBottom: 8 }}>
                {chatMsgs.map((msg, i) => (
                  <div key={i} style={{ fontSize: 10, lineHeight: 1.5,
                    color: msg.role === "system" ? C.text2 : msg.role === "user" ? C.cyan : C.text1,
                    background: msg.role === "agent" ? C.bg0 : "transparent",
                    padding: msg.role === "agent" ? "6px 8px" : "0",
                    borderRadius: 2, borderLeft: msg.role === "agent" ? `2px solid ${C.amber}` : "none",
                    whiteSpace: "pre-wrap" }}>
                    {msg.role === "user" && <span style={{ color: C.cyan }}>&#9656; </span>}
                    {msg.text}
                  </div>
                ))}
                {chatLoading && <Loader text="ReportAgent thinking..." />}
                <div ref={chatEndRef} />
              </div>
              <div style={{ display: "flex", gap: 4, flexShrink: 0 }}>
                <input value={cmdInput} onChange={e => setCmdInput(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && handleCmd()}
                  placeholder="Ask the ReportAgent..."
                  style={{ flex: 1, background: C.bg0, border: `1px solid ${C.border}`, borderRadius: 2,
                    padding: "6px 8px", color: C.text0, fontFamily: "inherit", fontSize: 11, outline: "none" }} />
                <button onClick={handleCmd} disabled={chatLoading}
                  style={{ background: C.amber, color: C.bg0, border: "none", borderRadius: 2,
                    padding: "6px 12px", fontFamily: "inherit", fontSize: 10, fontWeight: 700,
                    cursor: "pointer", letterSpacing: 1, opacity: chatLoading ? 0.5 : 1 }}>
                  SEND
                </button>
              </div>
            </div>
          </Panel>
        </>}

        {activeTab === "agents" && (
          <Panel title="AGENT POPULATION MONITOR" badge={`${agents.length} TRACKED`}
            style={{ gridColumn: "1 / -1", gridRow: "1 / -1" }} noPad>
            {loading.agents ? <Loader text="Loading agents..." /> : agents.length > 0 ? (
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 10 }}>
                  <thead>
                    <tr style={{ background: C.bg2 }}>
                      {["ID","NAME","TYPE","STANCE","PLATFORM","ACTIVITY","INFLUENCE","ACTIONS","TREND"].map(h => (
                        <th key={h} style={{ padding: "6px 10px", textAlign: "left", color: C.text2,
                          fontSize: 9, letterSpacing: 1, borderBottom: `1px solid ${C.border}`, fontWeight: 600, whiteSpace: "nowrap" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {agents.map((agent, i) => (
                      <tr key={agent.agent_id} onClick={() => setSelectedAgent(selectedAgent === i ? null : i)}
                        style={{ background: selectedAgent === i ? C.bg3 : i % 2 === 0 ? "transparent" : C.bg0 + "60",
                          cursor: "pointer", transition: "background 0.15s" }}>
                        <td style={{ padding: "8px 10px", color: C.text2, borderBottom: `1px solid ${C.border}` }}>{agent.agent_id}</td>
                        <td style={{ padding: "8px 10px", color: C.text0, fontWeight: 600, borderBottom: `1px solid ${C.border}` }}>
                          {recentAgentIds.has(agent.name) && (
                            <span style={{ display: "inline-block", width: 6, height: 6, borderRadius: "50%", background: C.green, marginRight: 4, boxShadow: `0 0 6px ${C.green}`, animation: "pulse 1s infinite" }} />
                          )}
                          <span style={{ color: C.amber }}>@</span>{agent.name}
                        </td>
                        <td style={{ padding: "8px 10px", borderBottom: `1px solid ${C.border}` }}>
                          <Badge color={C.text1} bg={C.bg3}>{agent.entity_type}</Badge>
                        </td>
                        <td style={{ padding: "8px 10px", color: (agent.stance || "").includes("oppos") ? C.red : (agent.stance || "").includes("support") ? C.green : C.text1,
                          borderBottom: `1px solid ${C.border}`, fontSize: 10 }}>{agent.stance || "—"}</td>
                        <td style={{ padding: "8px 10px", borderBottom: `1px solid ${C.border}` }}>
                          <Badge color={C.blue} bg={C.blueDim}>{(agent.platforms || ["—"])[0]}</Badge>
                        </td>
                        <td style={{ padding: "8px 10px", borderBottom: `1px solid ${C.border}` }}>
                          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                            <MiniBar value={agent.activity_level || 0} color={(agent.activity_level || 0) > 0.8 ? C.green : C.amber} />
                            <span style={{ color: C.text1, width: 28, textAlign: "right" }}>{((agent.activity_level || 0) * 100).toFixed(0)}%</span>
                          </div>
                        </td>
                        <td style={{ padding: "8px 10px", borderBottom: `1px solid ${C.border}` }}>
                          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                            <MiniBar value={agent.influence_score || 0} color={C.purple} />
                            <span style={{ color: C.text1, width: 28, textAlign: "right" }}>{((agent.influence_score || 0) * 100).toFixed(0)}%</span>
                          </div>
                        </td>
                        <td style={{ padding: "8px 10px", color: C.text0, fontWeight: 600, borderBottom: `1px solid ${C.border}`, textAlign: "right" }}>
                          {(agent.total_actions || 0).toLocaleString()}
                        </td>
                        <td style={{ padding: "8px 10px", borderBottom: `1px solid ${C.border}` }}>
                          <Sparkline data={Array.from({length: 10}, () => Math.random() * (agent.activity_level || 0.5))}
                            color={C.green} w={60} h={16} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : <div style={{ padding: 20, color: C.text2, fontSize: 10, textAlign: "center" }}>No agents — run a simulation first</div>}
            {selectedAgent !== null && agents[selectedAgent] && (
              <div style={{ padding: "12px 16px", background: C.bg2, borderTop: `1px solid ${C.amber}40`,
                display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16 }}>
                <div>
                  <div style={{ fontSize: 9, color: C.text2, letterSpacing: 1 }}>AGENT PROFILE</div>
                  <div style={{ fontSize: 13, color: C.amber, fontWeight: 700, marginTop: 4 }}>@{agents[selectedAgent].name}</div>
                  <div style={{ fontSize: 10, color: C.text1, marginTop: 2 }}>{agents[selectedAgent].entity_type}</div>
                </div>
                <div>
                  <div style={{ fontSize: 9, color: C.text2, letterSpacing: 1 }}>BIO</div>
                  <div style={{ fontSize: 10, color: C.text1, marginTop: 4, lineHeight: 1.6 }}>{agents[selectedAgent].bio || "N/A"}</div>
                </div>
                <div>
                  <div style={{ fontSize: 9, color: C.text2, letterSpacing: 1 }}>PERSONALITY</div>
                  <div style={{ fontSize: 10, color: C.text1, marginTop: 4, lineHeight: 1.6 }}>{agents[selectedAgent].personality || "N/A"}</div>
                </div>
                <div>
                  <div style={{ fontSize: 9, color: C.text2, letterSpacing: 1 }}>EXPERTISE</div>
                  <div style={{ fontSize: 10, color: C.text1, marginTop: 4, lineHeight: 1.6 }}>{(agents[selectedAgent].expertise || []).join(", ") || "N/A"}</div>
                </div>
              </div>
            )}
          </Panel>
        )}

        {activeTab === "graph" && <>
          <Panel title="KNOWLEDGE GRAPH EXPLORER" badge={`${nodeCount} NODES · ${edgeCount} EDGES`}
            style={{ gridColumn: "1", gridRow: "1 / -1" }}>
            {loading.graph ? <Loader text="Loading graph..." /> : graphNodes.length > 0 ? (
              <svg viewBox="0 0 600 400" style={{ width: "100%", height: "100%" }}>
                {graphEdges.map(([a, b], i) => (
                  <line key={i} x1={graphNodes[a]?.x} y1={graphNodes[a]?.y} x2={graphNodes[b]?.x} y2={graphNodes[b]?.y}
                    stroke={C.borderHi} strokeWidth={0.8} opacity={0.5} />
                ))}
                {graphNodes.map((n, i) => (
                  <g key={i} style={{ cursor: "pointer" }}>
                    <circle cx={n.x} cy={n.y} r={n.r * 1.5} fill={n.color + "15"} stroke={n.color} strokeWidth={1.2} />
                    <circle cx={n.x} cy={n.y} r={3} fill={n.color} />
                    <text x={n.x} y={n.y - n.r * 1.5 - 6} textAnchor="middle" fill={n.color} fontSize={9} fontFamily="inherit" fontWeight="600">{n.label}</text>
                  </g>
                ))}
              </svg>
            ) : <div style={{ color: C.text2, fontSize: 10, textAlign: "center", padding: 40 }}>No graph data — build a graph first</div>}
          </Panel>
          <Panel title="GRAPH METRICS" style={{ gridColumn: "2", gridRow: "1" }}>
            {[
              { label: "Total Nodes", value: nodeCount, color: C.amber },
              { label: "Total Edges", value: edgeCount, color: C.blue },
              { label: "Entity Types", value: entityDist.length, color: C.green },
              { label: "Avg Degree", value: nodeCount > 0 ? ((edgeCount * 2) / nodeCount).toFixed(1) : "0", color: C.text1 },
            ].map((m, i) => (
              <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center",
                padding: "6px 0", borderBottom: `1px solid ${C.border}` }}>
                <span style={{ color: C.text2, fontSize: 10 }}>{m.label}</span>
                <span style={{ color: m.color, fontSize: 13, fontWeight: 700 }}>{m.value}</span>
              </div>
            ))}
          </Panel>
          <Panel title="ONTOLOGY SCHEMA" style={{ gridColumn: "2", gridRow: "2" }}>
            <div style={{ fontSize: 10, color: C.text1, lineHeight: 2 }}>
              {ontologyEdges.length > 0 ? ontologyEdges.map((et, i) => (
                et.sources.map((s, j) => (
                  <div key={`${i}-${j}`} style={{ padding: "2px 0", borderBottom: `1px solid ${C.bg0}` }}>
                    <span style={{ color: C.green }}>{s.split(" → ")[0]}</span>
                    <span style={{ color: C.text2 }}> → </span>
                    <span style={{ color: C.amber }}>{s.split(" → ")[1]}</span>
                    <span style={{ color: C.text2 }}> → </span>
                    <span style={{ color: C.blue }}>{s.split(" → ")[2]}</span>
                  </div>
                ))
              )) : <div style={{ color: C.text2 }}>No ontology data</div>}
            </div>
          </Panel>
        </>}

        {activeTab === "events" && <>
          <Panel title="SIMULATION ROUNDS" badge={`${totalRounds} ROUNDS`}
            style={{ gridColumn: "1", gridRow: "1" }}>
            {simData?.rounds && simData.rounds.length > 0 ? (
              <div style={{ overflowY: "auto", maxHeight: "100%" }}>
                {simData.rounds.slice(-20).reverse().map((r, i) => (
                  <div key={i} style={{ padding: "6px 10px", borderBottom: `1px solid ${C.border}`, display: "flex", gap: 12, fontSize: 10, alignItems: "center" }}>
                    <span style={{ color: C.amber, fontWeight: 700, width: 36 }}>R{r.round_num}</span>
                    <span style={{ color: C.text1 }}>{r.actions_count || (r.actions || []).length} actions</span>
                    <span style={{ color: C.text2 }}>{(r.active_agent_ids || []).length} active</span>
                    <span style={{ color: C.text2 }}>H{r.simulated_hour || 0}</span>
                  </div>
                ))}
              </div>
            ) : <div style={{ color: C.text2, fontSize: 10, textAlign: "center", padding: 20 }}>No rounds yet</div>}
          </Panel>
          <Panel title="SIMULATION CONFIG" style={{ gridColumn: "2", gridRow: "1" }}>
            {simData?.config ? (
              <div style={{ fontSize: 10, color: C.text1, lineHeight: 2 }}>
                <div>Max Rounds: <span style={{ color: C.amber }}>{simData.config.time_config?.max_rounds || "—"}</span></div>
                <div>Hours/Round: <span style={{ color: C.amber }}>{simData.config.time_config?.hours_per_round || "—"}</span></div>
                <div>Start Hour: <span style={{ color: C.amber }}>{simData.config.time_config?.start_hour || "—"}</span></div>
                <div>Events: <span style={{ color: C.amber }}>{(simData.config.events || []).length}</span></div>
                <div>Platforms: <span style={{ color: C.amber }}>{(simData.config.platforms || []).map(p => p.platform_type).join(", ") || "—"}</span></div>
              </div>
            ) : <div style={{ color: C.text2, fontSize: 10 }}>No config</div>}
          </Panel>
          <Panel title="ACTION DISTRIBUTION" style={{ gridColumn: "1 / -1", gridRow: "2" }}>
            {simSummary.action_type_distribution ? (
              <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
                {Object.entries(simSummary.action_type_distribution).sort((a, b) => b[1] - a[1]).map(([type, count], i) => (
                  <div key={i} style={{ background: C.bg0, border: `1px solid ${C.border}`, borderRadius: 2, padding: "8px 12px", minWidth: 120 }}>
                    <div style={{ fontSize: 9, color: C.text2, letterSpacing: 1 }}>{type}</div>
                    <div style={{ fontSize: 16, fontWeight: 700, color: C.amber, marginTop: 4 }}>{count}</div>
                  </div>
                ))}
              </div>
            ) : <div style={{ color: C.text2, fontSize: 10, textAlign: "center", padding: 20 }}>No distribution data</div>}
          </Panel>
        </>}

        {/* ═══ FIFA TAB — TIP-17 ═══ */}
        {activeTab === "fifa" && (
          <div style={{ gridColumn: "1 / -1", gridRow: "1 / -1", display: "flex", flexDirection: "column", overflow: "hidden", minHeight: 0 }}>
            {/* View toggle bar */}
            <div style={{ display: "flex", gap: 0, borderBottom: `1px solid ${C.border}`, flexShrink: 0 }}>
              {[{ id: "command", label: L.commandCenter }, { id: "data", label: L.kpiData }, { id: "sim", label: L.liveSim }].map(v => (
                <button key={v.id} onClick={() => setFifaView(v.id)}
                  style={{ padding: "5px 14px", background: "transparent", border: "none",
                    borderBottom: fifaView === v.id ? `2px solid ${C.cyan}` : "2px solid transparent",
                    color: fifaView === v.id ? C.cyan : C.text2, cursor: "pointer", fontFamily: "inherit",
                    fontSize: 9, letterSpacing: 1, fontWeight: 600, transition: "all 0.15s" }}>
                  {v.label}
                </button>
              ))}
            </div>
            {/* Content */}
            <div style={{ flex: 1, overflow: "hidden", minHeight: 0 }}>
              {fifaView === "command" ? (
                <VOCCommandCenter embedded defaultTheme={themeId} defaultLang={langId} />
              ) : fifaView === "data" ? (
                <FifaComparisonTab
                  data={comparisonData}
                  loading={comparisonLoading}
                  compareConfig={compareConfig}
                  setCompareConfig={setCompareConfig}
                  expandedScenario={expandedScenario}
                  setExpandedScenario={setExpandedScenario}
                  onImport={handleImportComparison}
                  onRunComparison={handleRunComparison}
                  C={C} L={L}
                  onExportReport={async () => {
                    if (!activeProjectId) return;
                    const r = await api.generateFifaReport(activeProjectId);
                    if (r.status === "ok" && r.data?.report) {
                      const blob = new Blob([r.data.report], { type: "text/markdown" });
                      const url = URL.createObjectURL(blob);
                      const a = document.createElement("a");
                      a.href = url; a.download = `fifa_report_${activeProjectId.slice(0, 8)}.md`;
                      a.click(); URL.revokeObjectURL(url);
                    }
                  }}
                />
              ) : (
                <StadiumSimGraph comparisonData={comparisonData} themeId={themeId} />
              )}
            </div>
          </div>
        )}
      </div>

      {/* ═══ STATUS BAR ═══ */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "4px 12px", background: C.bg1, borderTop: `1px solid ${C.border}`, flexShrink: 0 }}>
        <div style={{ display: "flex", gap: 12, color: C.text2, fontSize: 9, alignItems: "center" }}>
          <span>v1.2</span>
          {healthData?.checks ? <>
            <HealthDot label="DB" check={healthData.checks.database} />
            <HealthDot label="LLM" check={healthData.checks.llm} />
            <HealthDot label="JOBS" check={healthData.checks.job_queue} extra={healthData.checks.job_queue?.active_jobs != null ? `${healthData.checks.job_queue.active_jobs}/${healthData.checks.job_queue.max_workers}` : null} />
            {healthData.checks.memory?.rss_mb > 0 && <span>MEM: {healthData.checks.memory.rss_mb}MB</span>}
            {wsEnabled && <span style={{ color: ws.connected ? C.green : C.amber }}>WS: {ws.connected ? "LIVE" : "..."}</span>}
          </> : <span>API: {connected ? "CONNECTED" : "DISCONNECTED"}</span>}
          {healthData?.uptime_seconds > 0 && <span>UP: {Math.floor(healthData.uptime_seconds / 3600)}h{Math.floor((healthData.uptime_seconds % 3600) / 60)}m</span>}
        </div>
        <div style={{ color: C.text2, fontSize: 9 }}>
          <span style={{ color: C.amber }}>{L.engine}</span>
        </div>
      </div>

      {/* ═══ NEW SIMULATION MODAL ═══ */}
      {showNewSim && <NewSimModal onClose={() => setShowNewSim(false)} onComplete={handleNewSimComplete} />}

      {/* ═══ EVENT INJECTION MODAL ═══ */}
      {showInjectModal && (
        <InjectEventModal
          onClose={() => setShowInjectModal(false)}
          onInject={(name, content) => {
            ws.sendCommand("inject_event", { name, content });
            setShowInjectModal(false);
          }}
        />
      )}
    </div>
  );
}

// ─── FIFA Comparison Tab — TIP-17 ─────────────────────────────
const KPI_ORDER = ["detection_latency", "verification_time", "decision_time", "response_time", "total_resolution"];

function FifaComparisonTab({ data, loading, compareConfig, setCompareConfig, expandedScenario, setExpandedScenario, onImport, onRunComparison, onExportReport, C, L }) {
  const CAT_COLORS = { crowd_safety: C.amber, medical: C.red, security: C.blue, environmental: C.green, operational: C.text2 };
  const KPI_LABELS = {
    detection_latency: L.detectionLatency, verification_time: L.verificationTime,
    decision_time: L.decisionTime, response_time: L.responseTime, total_resolution: L.totalResolution,
  };
  const fileRef = useRef(null);

  if (loading) {
    return (
      <div style={{ gridColumn: "1 / -1", gridRow: "1 / -1", display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 12 }}>
        <Loader text="Loading comparison data..." />
      </div>
    );
  }

  if (!data) {
    return (
      <div style={{ gridColumn: "1 / -1", gridRow: "1 / -1", display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 16, padding: 40 }}>
        <div style={{ fontSize: 32, color: C.text2 }}>&#9958;</div>
        <div style={{ fontSize: 13, color: C.text1, textAlign: "center" }}>{L.noComparison}</div>
        <div style={{ fontSize: 10, color: C.text2, textAlign: "center", maxWidth: 400 }}>
          {L.noComparisonDesc}
        </div>
        <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
          <input type="file" ref={fileRef} accept=".json" style={{ display: "none" }}
            onChange={e => {
              const file = e.target.files?.[0];
              if (!file) return;
              const reader = new FileReader();
              reader.onload = ev => {
                try { onImport(JSON.parse(ev.target.result)); } catch {}
              };
              reader.readAsText(file);
            }} />
          <button onClick={() => fileRef.current?.click()}
            style={{ background: C.amber, color: C.bg0, border: "none", borderRadius: 2, padding: "8px 16px", fontFamily: "inherit", fontSize: 11, fontWeight: 700, cursor: "pointer", letterSpacing: 1 }}>
            {L.importJson}
          </button>
          <button onClick={onRunComparison}
            style={{ background: C.bg2, color: C.green, border: `1px solid ${C.border}`, borderRadius: 2, padding: "8px 16px", fontFamily: "inherit", fontSize: 11, fontWeight: 600, cursor: "pointer", letterSpacing: 1 }}>
            {L.runComparison}
          </button>
        </div>
      </div>
    );
  }

  const masterKpi = data.master_kpi || {};
  const allConfigs = Object.keys(masterKpi);
  const firstCfg = allConfigs[0] || "BASELINE";
  const lastCfg = allConfigs[allConfigs.length - 1] || "FULL";
  const effectiveCompare = allConfigs.includes(compareConfig) ? compareConfig : lastCfg;
  const baselineKpi = masterKpi[firstCfg] || {};
  const compareKpi = masterKpi[effectiveCompare] || {};
  const scenarios = data.scenarios || [];

  // Compute improvement for a KPI
  const improvement = (kpiKey) => {
    const bm = baselineKpi[kpiKey]?.mean;
    const cm = compareKpi[kpiKey]?.mean;
    if (!bm || bm === 0) return 0;
    return Math.round((1 - cm / bm) * 100);
  };

  return (
    <div style={{ gridColumn: "1 / -1", gridRow: "1 / -1", overflow: "auto", padding: 12, display: "flex", flexDirection: "column", gap: 12 }}>

      {/* ── Section D: Config Selector + Controls ── */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", gap: 4 }}>
          {allConfigs.slice(1).map(cfg => (
            <button key={cfg} onClick={() => setCompareConfig(cfg)}
              style={{ padding: "5px 14px", background: effectiveCompare === cfg ? C.amber + "22" : "transparent",
                border: `1px solid ${effectiveCompare === cfg ? C.amber : C.border}`, borderRadius: 2,
                color: effectiveCompare === cfg ? C.amber : C.text2, fontFamily: "inherit", fontSize: 10,
                fontWeight: 600, cursor: "pointer", letterSpacing: 1 }}>
              {firstCfg} vs {cfg}
            </button>
          ))}
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <Badge color={C.green}>{data.total_runs?.toLocaleString() || 0} RUNS</Badge>
          <Badge color={C.blue}>{data.total_scenarios || 0} SCENARIOS</Badge>
          <button onClick={onExportReport}
            style={{ background: C.bg2, color: C.cyan, border: `1px solid ${C.border}`, borderRadius: 2,
              padding: "5px 12px", fontFamily: "inherit", fontSize: 10, fontWeight: 600, cursor: "pointer", letterSpacing: 1 }}>
            {L.exportReport}
          </button>
        </div>
      </div>

      {/* ── Section A: KPI Summary Cards ── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 8 }}>
        {KPI_ORDER.map(kpiKey => {
          const bm = baselineKpi[kpiKey]?.mean || 0;
          const cm = compareKpi[kpiKey]?.mean || 0;
          const imp = improvement(kpiKey);
          const impColor = imp > 0 ? C.green : imp < 0 ? C.red : C.text2;
          return (
            <div key={kpiKey} style={{ background: C.bg1, border: `1px solid ${C.border}`, borderRadius: 3, padding: "12px 14px",
              borderLeft: `3px solid ${imp > 50 ? C.green : imp > 20 ? C.amber : C.text2}` }}>
              <div style={{ fontSize: 9, color: C.text2, letterSpacing: 1, marginBottom: 8 }}>{KPI_LABELS[kpiKey]}</div>
              <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
                <span style={{ fontSize: 22, fontWeight: 700, color: impColor }}>{imp > 0 ? "-" : "+"}{Math.abs(imp)}%</span>
              </div>
              <div style={{ fontSize: 10, color: C.text2, marginTop: 6, display: "flex", gap: 8 }}>
                <span>{bm.toFixed(0)}s</span>
                <span style={{ color: C.text2 }}>→</span>
                <span style={{ color: C.text1 }}>{cm.toFixed(0)}s</span>
              </div>
              <div style={{ fontSize: 9, color: C.text2, marginTop: 2 }}>
                ±{compareKpi[kpiKey]?.std?.toFixed(0) || 0}s
              </div>
            </div>
          );
        })}
      </div>

      {/* ── Section B: Scenario Comparison Table ── */}
      <div style={{ background: C.bg1, border: `1px solid ${C.border}`, borderRadius: 3, overflow: "hidden", flex: 1, minHeight: 0 }}>
        <div style={{ padding: "8px 12px", borderBottom: `1px solid ${C.border}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: C.text0, letterSpacing: 1 }}>{L.scenarioComparison}</span>
          <span style={{ fontSize: 9, color: C.text2 }}>{scenarios.length} scenarios · {firstCfg} vs {effectiveCompare}</span>
        </div>
        <div style={{ overflowY: "auto", maxHeight: 380 }}>
          {/* Header */}
          <div style={{ display: "grid", gridTemplateColumns: `200px 80px repeat(${allConfigs.length}, 90px) 80px`, gap: 0,
            padding: "6px 12px", borderBottom: `1px solid ${C.border}`, fontSize: 9, color: C.text2, letterSpacing: 1, position: "sticky", top: 0, background: C.bg2, zIndex: 1 }}>
            <span>{L.scenario}</span><span>{L.category}</span>
            {allConfigs.map(c => <span key={c} style={{ textAlign: "right" }}>{c}</span>)}
            <span style={{ textAlign: "right" }}>{L.improve}</span>
          </div>
          {/* Rows */}
          {scenarios.map(sc => {
            const catColor = CAT_COLORS[sc.category] || C.text2;
            const catLabel = L[sc.category] || sc.category?.toUpperCase();
            const cfgTotals = allConfigs.map(c => sc.configs?.[c]?.kpi?.total_resolution?.mean || 0);
            const bTotal = cfgTotals[0] || 0;
            const lastTotal = cfgTotals[cfgTotals.length - 1] || 0;
            const imp = bTotal > 0 ? Math.round((1 - lastTotal / bTotal) * 100) : 0;
            const isExpanded = expandedScenario === sc.id;

            return (
              <div key={sc.id}>
                <div onClick={() => setExpandedScenario(isExpanded ? null : sc.id)}
                  style={{ display: "grid", gridTemplateColumns: `200px 80px repeat(${allConfigs.length}, 90px) 80px`, gap: 0,
                    padding: "8px 12px", borderBottom: `1px solid ${C.border}`, cursor: "pointer",
                    background: isExpanded ? C.bg2 : "transparent", transition: "background 0.15s" }}>
                  <span style={{ fontSize: 10, color: C.text0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    <span style={{ color: C.amber, marginRight: 6 }}>{isExpanded ? "▾" : "▸"}</span>
                    {sc.name}
                  </span>
                  <span><Badge color={catColor}>{catLabel}</Badge></span>
                  {cfgTotals.map((t, i) => <span key={i} style={{ fontSize: 10, color: C.text1, textAlign: "right" }}>{t.toFixed(0)}s</span>)}
                  <span style={{ fontSize: 10, fontWeight: 700, color: imp > 0 ? C.green : C.text2, textAlign: "right" }}>
                    {imp > 0 ? `-${imp}%` : `${imp}%`}
                  </span>
                </div>
                {/* Expanded: decision chain timeline */}
                {isExpanded && (
                  <div style={{ padding: "12px 16px", background: C.bg0, borderBottom: `1px solid ${C.border}` }}>
                    <div style={{ fontSize: 9, color: C.text2, letterSpacing: 1, marginBottom: 8 }}>DECISION CHAIN — T0 → T6</div>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
                      {allConfigs.map(cfgId => {
                        const cfgKpi = sc.configs?.[cfgId]?.kpi || {};
                        const cfgColor = cfgId === "BASELINE" ? C.text2 : cfgId === "TETHERED" ? C.amber : C.green;
                        return (
                          <div key={cfgId} style={{ background: C.bg1, borderRadius: 3, padding: 10, border: `1px solid ${C.border}` }}>
                            <div style={{ fontSize: 10, fontWeight: 700, color: cfgColor, marginBottom: 8 }}>{cfgId}</div>
                            {KPI_ORDER.map(kk => {
                              const val = cfgKpi[kk]?.mean || 0;
                              const std = cfgKpi[kk]?.std || 0;
                              const maxVal = sc.configs?.[firstCfg]?.kpi?.[kk]?.mean || 1;
                              const pct = Math.min((val / maxVal) * 100, 100);
                              return (
                                <div key={kk} style={{ marginBottom: 6 }}>
                                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 9, color: C.text2, marginBottom: 2 }}>
                                    <span>{KPI_LABELS[kk]}</span>
                                    <span style={{ color: C.text1 }}>{val.toFixed(0)}s ±{std.toFixed(0)}</span>
                                  </div>
                                  <div style={{ height: 4, background: C.bg0, borderRadius: 2, overflow: "hidden" }}>
                                    <div style={{ width: `${pct}%`, height: "100%", background: cfgColor, borderRadius: 2, transition: "width 0.3s" }} />
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Section C: KPI Phase Breakdown Bars ── */}
      <div style={{ background: C.bg1, border: `1px solid ${C.border}`, borderRadius: 3, padding: 14 }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: C.text0, letterSpacing: 1, marginBottom: 12 }}>{L.kpiPhaseBreakdown} — {firstCfg} vs {effectiveCompare}</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {KPI_ORDER.slice(0, 4).map(kpiKey => {
            const bm = baselineKpi[kpiKey]?.mean || 1;
            const cm = compareKpi[kpiKey]?.mean || 0;
            const imp = improvement(kpiKey);
            const pct = Math.min((cm / bm) * 100, 100);
            return (
              <div key={kpiKey}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, marginBottom: 4 }}>
                  <span style={{ color: C.text1 }}>{KPI_LABELS[kpiKey]}</span>
                  <span style={{ color: imp > 0 ? C.green : C.text2, fontWeight: 700 }}>
                    {imp > 0 ? `-${imp}%` : `${imp}%`}
                    <span style={{ color: C.text2, fontWeight: 400, marginLeft: 8 }}>{bm.toFixed(0)}s → {cm.toFixed(0)}s</span>
                  </span>
                </div>
                <div style={{ position: "relative", height: 16, background: C.bg0, borderRadius: 3, overflow: "hidden" }}>
                  {/* Baseline (full width reference) */}
                  <div style={{ position: "absolute", inset: 0, background: C.text2 + "20", borderRadius: 3 }} />
                  {/* Compare config bar */}
                  <div style={{ position: "absolute", top: 0, left: 0, bottom: 0, width: `${pct}%`,
                    background: imp > 50 ? C.green + "55" : imp > 20 ? C.amber + "55" : C.text2 + "40",
                    borderRadius: 3, transition: "width 0.4s" }} />
                  {/* Baseline marker at 100% */}
                  <div style={{ position: "absolute", top: 0, right: 0, bottom: 0, width: 2, background: C.text2 + "60" }} />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}


// ─── Event Injection Modal ────────────────────────────────────
function InjectEventModal({ onClose, onInject }) {
  const [eventName, setEventName] = useState("");
  const [eventContent, setEventContent] = useState("");

  const presets = [
    { icon: "!", title: "Breaking News", desc: "Major announcement or leak", content: "A major policy announcement has been made, causing widespread reaction across all sectors." },
    { icon: "$", title: "Market Shock", desc: "Economic indicator shift", content: "A sudden shift in economic indicators has rattled market confidence and triggered uncertainty." },
    { icon: "~", title: "Narrative Shift", desc: "Counter-narrative emerges", content: "A credible counter-narrative has emerged, challenging the dominant viewpoint with new evidence." },
    { icon: "+", title: "Coalition Forms", desc: "Group alignment event", content: "Multiple key stakeholders have announced a formal coalition to coordinate their response." },
    { icon: "#", title: "Viral Content", desc: "High-impact post", content: "A post has gone viral, rapidly spreading and influencing public opinion across platforms." },
    { icon: "*", title: "Deadline Event", desc: "Time-pressure trigger", content: "A critical deadline is approaching, forcing stakeholders to accelerate their decision-making." },
  ];

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}
      onClick={e => e.target === e.currentTarget && onClose()}>
      <div style={{ background: C.bg1, border: `1px solid ${C.border}`, borderRadius: 4, width: 520 }}>
        <div style={{ padding: "12px 16px", borderBottom: `1px solid ${C.border}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ fontSize: 12, fontWeight: 700, color: C.cyan, letterSpacing: 1 }}>INJECT EVENT</span>
          <span style={{ color: C.text2, cursor: "pointer", fontSize: 14 }} onClick={onClose}>x</span>
        </div>
        <div style={{ padding: 16 }}>
          <div style={{ fontSize: 9, color: C.text2, letterSpacing: 1, marginBottom: 8 }}>QUICK PRESETS</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 6, marginBottom: 16 }}>
            {presets.map((p, i) => (
              <div key={i} onClick={() => { setEventName(p.title); setEventContent(p.content); }}
                style={{ background: C.bg0, border: `1px solid ${eventName === p.title ? C.cyan : C.border}`, borderRadius: 3,
                  padding: "8px 10px", cursor: "pointer", borderLeft: `3px solid ${eventName === p.title ? C.cyan : C.border}` }}>
                <div style={{ fontSize: 11, color: C.cyan, marginBottom: 2 }}>{p.icon} {p.title}</div>
                <div style={{ fontSize: 9, color: C.text2 }}>{p.desc}</div>
              </div>
            ))}
          </div>
          <div style={{ marginBottom: 8 }}>
            <div style={{ fontSize: 9, color: C.text2, letterSpacing: 1, marginBottom: 4 }}>EVENT NAME</div>
            <input value={eventName} onChange={e => setEventName(e.target.value)} placeholder="Event name"
              style={{ width: "100%", background: C.bg0, border: `1px solid ${C.border}`, borderRadius: 2, padding: "6px 8px", color: C.text0, fontFamily: "inherit", fontSize: 11 }} />
          </div>
          <div style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 9, color: C.text2, letterSpacing: 1, marginBottom: 4 }}>EVENT CONTENT</div>
            <textarea value={eventContent} onChange={e => setEventContent(e.target.value)} rows={3} placeholder="Describe what happens..."
              style={{ width: "100%", background: C.bg0, border: `1px solid ${C.border}`, borderRadius: 2, padding: "6px 8px", color: C.text0, fontFamily: "inherit", fontSize: 11, resize: "vertical" }} />
          </div>
          <button onClick={() => eventName && onInject(eventName, eventContent)} disabled={!eventName}
            style={{ background: C.cyan, color: C.bg0, border: "none", borderRadius: 2, padding: "8px 16px", fontFamily: "inherit", fontSize: 11, fontWeight: 700, cursor: "pointer", letterSpacing: 1, opacity: eventName ? 1 : 0.4 }}>
            INJECT EVENT
          </button>
        </div>
      </div>
    </div>
  );
}
