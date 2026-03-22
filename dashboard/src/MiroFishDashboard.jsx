import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import * as api from "./api/client.js";

// ─── Bloomberg-inspired color system ──────────────────────────
const C = {
  bg0: "#0a0e17", bg1: "#0f1521", bg2: "#151d2e", bg3: "#1c2640",
  border: "#1e2a42", borderHi: "#2a3a5c",
  text0: "#e8ecf1", text1: "#8b9dc3", text2: "#4a5f8a",
  amber: "#ff9e1b", amberDim: "#c47a12",
  green: "#00d26a", greenDim: "#0a5c30",
  red: "#ff3b5c", redDim: "#5c1525",
  blue: "#3e8eff", blueDim: "#162d54",
  cyan: "#00e5ff", purple: "#a78bfa", white: "#ffffff",
};

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

const Loader = ({ text = "Loading..." }) => (
  <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: C.text2, fontSize: 10, gap: 8 }}>
    <span style={{ display: "inline-block", width: 8, height: 8, border: `2px solid ${C.amber}`, borderTopColor: "transparent", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
    {text}
    <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
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
  const [name, setName] = useState("MiroFish Analysis");
  const [requirement, setRequirement] = useState("");
  const [text, setText] = useState("");
  const [running, setRunning] = useState(false);
  const [stage, setStage] = useState(0);
  const [total] = useState(5);
  const [stageLabel, setStageLabel] = useState("");
  const [error, setError] = useState(null);

  const handleSubmit = async () => {
    if (!requirement.trim() || !text.trim()) return;
    setRunning(true); setError(null);
    const result = await api.runPipelineSteps(name, requirement, text, (s, t, label) => {
      setStage(s); setStageLabel(label);
    });
    if (result.error) { setError(result.error); setRunning(false); return; }
    onComplete(result.projectId);
  };

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
            <div style={{ textAlign: "center", padding: "20px 0" }}>
              <div style={{ fontSize: 12, color: C.text0, marginBottom: 12 }}>{stageLabel}</div>
              <div style={{ width: "100%", height: 6, background: C.bg0, borderRadius: 3, overflow: "hidden", marginBottom: 8 }}>
                <div style={{ width: `${(stage / total) * 100}%`, height: "100%", background: C.amber, borderRadius: 3, transition: "width 0.5s" }} />
              </div>
              <div style={{ fontSize: 10, color: C.text2 }}>Stage {stage}/{total}</div>
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
    { role: "system", text: "MiroFish ReportAgent ready. Ask about simulation results, agent behavior, or predictions." },
  ]);
  const [chatLoading, setChatLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("overview");
  const chatEndRef = useRef(null);

  // ── Derived ──
  const status = projectData ? (PHASE_STATUS[projectData.phase] || projectData.status || "queued") : "queued";
  const simSummary = simData?.summary || projectData?.simulation_summary || {};
  const totalRounds = simSummary.total_rounds || 0;
  const maxRounds = simData?.config?.time_config?.max_rounds || totalRounds || 1;
  const agentCount = agents.length || projectData?.agent_count || 0;
  const nodeCount = graphData?.info?.node_count || projectData?.graph_info?.node_count || 0;
  const edgeCount = graphData?.info?.edge_count || projectData?.graph_info?.edge_count || 0;

  // ── Tick ──
  useEffect(() => {
    const interval = setInterval(() => setTick(t => t + 1), 2000);
    return () => clearInterval(interval);
  }, []);

  // ── Chat scroll ──
  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [chatMsgs]);

  // ── Load projects on mount ──
  useEffect(() => {
    loadProjects();
    api.checkHealth().then(r => setConnected(r.status === "ok")).catch(() => setConnected(false));
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
    setGraphData(null); setAgents([]); setSimData(null);
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

  // ── Event feed from simulation rounds ──
  const eventFeed = useMemo(() => {
    if (!simData?.rounds) return [];
    const events = [];
    for (const round of (simData.rounds || []).slice(-10).reverse()) {
      events.push({ time: `R${round.round_num}`, type: "SYSTEM", msg: `Round ${round.round_num}: ${round.actions_count || 0} actions` });
      for (const a of (round.actions || []).slice(0, 3)) {
        events.push({ time: `R${round.round_num}`, type: "ACTION", msg: `${a.agent_name} → ${a.action_type}${a.result ? ': ' + a.result.slice(0, 60) : ''}` });
      }
    }
    return events.slice(0, 15);
  }, [simData]);

  // ── Timeline from rounds ──
  const timelineData = useMemo(() => {
    if (!simData?.rounds) return [];
    return (simData.rounds || []).map(r => ({
      round: r.round_num,
      actions: r.actions_count || (r.actions || []).length,
      activeAgents: (r.active_agent_ids || []).length,
    }));
  }, [simData]);

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
    { id: "overview", label: "OVERVIEW" },
    { id: "agents", label: "AGENTS" },
    { id: "graph", label: "K-GRAPH" },
    { id: "events", label: "EVENTS" },
  ];

  const simName = projectData?.name || "No Project Selected";
  const simId = projectData?.project_id || "—";

  return (
    <div style={{ background: C.bg0, color: C.text0, fontFamily: "'JetBrains Mono', 'SF Mono', 'Fira Code', monospace",
      fontSize: 11, minHeight: "100vh", display: "flex", flexDirection: "column" }}>

      {/* Connection banner */}
      {!connected && (
        <div style={{ background: C.redDim, color: C.red, padding: "4px 12px", fontSize: 10, textAlign: "center", flexShrink: 0 }}>
          Backend disconnected — retrying every 5s...
        </div>
      )}

      {/* ═══ TOP BAR ═══ */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "6px 12px", background: C.bg1, borderBottom: `1px solid ${C.border}`, flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 14, fontWeight: 700, color: C.amber, letterSpacing: 2 }}>MIROFISH</span>
          <span style={{ color: C.text2, fontSize: 10 }}>SWARM INTELLIGENCE TERMINAL</span>
          <span style={{ color: C.text2 }}>|</span>
          <span style={{ color: connected ? C.green : C.red, fontSize: 10 }}>{connected ? "CONNECTED" : "DISCONNECTED"}</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <span style={{ color: C.text2, fontSize: 10 }}>AGENTS: {agentCount}</span>
          <span style={{ color: C.text2, fontSize: 10 }}>PROJECTS: {projects.length}</span>
          <span style={{ color: C.text1, fontSize: 10 }}>{new Date().toLocaleTimeString("en-US", { hour12: false })}</span>
        </div>
      </div>

      {/* ═══ SCENARIO STRIP ═══ */}
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
        <button onClick={() => setShowNewSim(true)}
          style={{ flex: "0 0 auto", padding: "6px 14px", background: "transparent", border: "none", color: C.amber,
            cursor: "pointer", fontFamily: "inherit", fontSize: 10, fontWeight: 700, letterSpacing: 1 }}>
          + NEW
        </button>
      </div>

      {/* ═══ SIMULATION HEADER ═══ */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "8px 12px", background: C.bg1, borderBottom: `1px solid ${C.border}`, flexShrink: 0 }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, color: C.text0 }}>{simName}</div>
          <div style={{ fontSize: 10, color: C.text2, marginTop: 2 }}>{simId} {agentCount > 0 ? `· ${agentCount} agents` : ""}</div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: 10, color: C.text2 }}>ROUND</div>
            <div style={{ fontSize: 16, fontWeight: 700, color: C.amber }}>{totalRounds}<span style={{ color: C.text2, fontSize: 11 }}>/{maxRounds}</span></div>
          </div>
          <div style={{ width: 120, height: 6, background: C.bg0, borderRadius: 3, overflow: "hidden" }}>
            <div style={{ width: `${maxRounds > 0 ? (totalRounds / maxRounds) * 100 : 0}%`,
              height: "100%", background: status === "running" ? C.green : status === "completed" ? C.blue : C.amber,
              borderRadius: 3, transition: "width 0.5s" }} />
          </div>
          <Badge color={status === "running" ? C.green : status === "completed" ? C.blue : status === "failed" ? C.red : C.amber}>
            {status}
          </Badge>
        </div>
      </div>

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
        gridTemplateColumns: activeTab === "agents" ? "1fr" : "1fr 320px",
        gridTemplateRows: "1fr 1fr",
        gap: 1, padding: 1, minHeight: 0, overflow: "hidden" }}>

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
          <Panel title="EVENT FEED" badge={`${eventFeed.length}`} style={{ gridColumn: "2", gridRow: "1" }} noPad>
            {eventFeed.length > 0 ? eventFeed.map((evt, i) => {
              const typeColors = { EVENT: C.amber, ACTION: C.blue, SYSTEM: C.text2, ALERT: C.red };
              return (
                <div key={i} style={{ padding: "5px 10px", borderBottom: `1px solid ${C.border}`,
                  display: "flex", gap: 8, alignItems: "flex-start", fontSize: 10 }}>
                  <span style={{ color: C.text2, flexShrink: 0, width: 36 }}>{evt.time}</span>
                  <span style={{ color: typeColors[evt.type] || C.text2, fontWeight: 600, flexShrink: 0, width: 50 }}>{evt.type}</span>
                  <span style={{ color: C.text1, lineHeight: 1.4 }}>{evt.msg}</span>
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
      </div>

      {/* ═══ STATUS BAR ═══ */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "4px 12px", background: C.bg1, borderTop: `1px solid ${C.border}`, flexShrink: 0 }}>
        <div style={{ display: "flex", gap: 16, color: C.text2, fontSize: 9 }}>
          <span>KERNEL v1.2</span>
          <span>PIPELINE: 7-STAGE</span>
          <span>API: {connected ? "CONNECTED" : "DISCONNECTED"}</span>
        </div>
        <div style={{ color: C.text2, fontSize: 9 }}>
          <span style={{ color: C.amber }}>MiroFish Kernel — Swarm Intelligence Engine</span>
        </div>
      </div>

      {/* ═══ NEW SIMULATION MODAL ═══ */}
      {showNewSim && <NewSimModal onClose={() => setShowNewSim(false)} onComplete={handleNewSimComplete} />}
    </div>
  );
}
