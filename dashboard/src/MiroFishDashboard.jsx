import { useState, useEffect, useRef, useCallback } from "react";

// ─── Bloomberg-inspired color system ──────────────────────────
const C = {
  bg0: "#0a0e17",      // deepest background
  bg1: "#0f1521",      // panel background
  bg2: "#151d2e",      // elevated surface
  bg3: "#1c2640",      // hover/active
  border: "#1e2a42",   // subtle borders
  borderHi: "#2a3a5c", // highlighted borders
  text0: "#e8ecf1",    // primary text
  text1: "#8b9dc3",    // secondary text
  text2: "#4a5f8a",    // tertiary/muted
  amber: "#ff9e1b",    // Bloomberg orange - primary accent
  amberDim: "#c47a12", // dimmed amber
  green: "#00d26a",    // positive/running
  greenDim: "#0a5c30",
  red: "#ff3b5c",      // alert/error
  redDim: "#5c1525",
  blue: "#3e8eff",     // info/links
  blueDim: "#162d54",
  cyan: "#00e5ff",     // secondary accent
  purple: "#a78bfa",   // agent-related
  white: "#ffffff",
};

// ─── Mock Data ────────────────────────────────────────────────
const SCENARIOS = [
  { id: "SIM-2026-0847", name: "AI Regulation Impact — SEA Markets", status: "running", agents: 2400, rounds: 127, maxRounds: 500, domain: "policy" },
  { id: "SIM-2026-0846", name: "TSMC Supply Chain Disruption", status: "completed", agents: 890, rounds: 200, maxRounds: 200, domain: "supply_chain" },
  { id: "SIM-2026-0845", name: "BĐS HCM Q2 Demand Forecast", status: "paused", agents: 1200, rounds: 89, maxRounds: 300, domain: "real_estate" },
  { id: "SIM-2026-0844", name: "Crypto Sentiment — BTC Halving", status: "completed", agents: 5000, rounds: 1000, maxRounds: 1000, domain: "finance" },
  { id: "SIM-2026-0843", name: "RTR Drone Market Entry — India", status: "queued", agents: 3200, rounds: 0, maxRounds: 400, domain: "market" },
];

const AGENTS_DATA = [
  { id: 1, name: "Gov_Regulator_VN", type: "GovernmentAgency", stance: "pro-regulation", activity: 0.92, influence: 0.95, actions: 342, sentiment: 0.2, platform: "twitter" },
  { id: 2, name: "TechCEO_Alpha", type: "Executive", stance: "anti-regulation", activity: 0.88, influence: 0.87, actions: 289, sentiment: -0.4, platform: "twitter" },
  { id: 3, name: "MediaOutlet_VNE", type: "MediaOutlet", stance: "neutral", activity: 0.95, influence: 0.78, actions: 456, sentiment: 0.1, platform: "reddit" },
  { id: 4, name: "Professor_CS_HN", type: "Professor", stance: "cautious-support", activity: 0.65, influence: 0.72, actions: 178, sentiment: 0.3, platform: "twitter" },
  { id: 5, name: "Startup_Founder_SG", type: "Executive", stance: "strong-oppose", activity: 0.91, influence: 0.68, actions: 312, sentiment: -0.6, platform: "twitter" },
  { id: 6, name: "NGO_DigitalRights", type: "Organization", stance: "conditional-support", activity: 0.73, influence: 0.61, actions: 201, sentiment: 0.15, platform: "reddit" },
  { id: 7, name: "PublicSentiment_Bot", type: "Person", stance: "mixed", activity: 0.45, influence: 0.35, actions: 89, sentiment: -0.1, platform: "twitter" },
  { id: 8, name: "InvestorGroup_VC", type: "Organization", stance: "oppose", activity: 0.82, influence: 0.88, actions: 267, sentiment: -0.5, platform: "twitter" },
];

const TIMELINE_DATA = Array.from({ length: 48 }, (_, i) => ({
  hour: i, posts: Math.floor(Math.random() * 80 + 20 + (i > 20 && i < 35 ? 60 : 0)),
  likes: Math.floor(Math.random() * 200 + 50), sentiment: (Math.random() - 0.45) * 2,
  activeAgents: Math.floor(Math.random() * 800 + 400 + (i > 15 && i < 40 ? 600 : 0)),
}));

const EVENTS_LOG = [
  { time: "14:23:07", type: "EVENT", msg: "Policy draft leaked to press — agents reacting" },
  { time: "14:22:51", type: "ACTION", msg: "TechCEO_Alpha posted opposition thread (2.4K impressions)" },
  { time: "14:22:34", type: "SYSTEM", msg: "Round 127 completed — 89 actions recorded" },
  { time: "14:21:58", type: "ACTION", msg: "Gov_Regulator_VN official statement released" },
  { time: "14:21:12", type: "ALERT", msg: "Sentiment shift detected: -0.3 → -0.6 in tech sector" },
  { time: "14:20:45", type: "ACTION", msg: "MediaOutlet_VNE published analysis article" },
  { time: "14:19:33", type: "SYSTEM", msg: "Knowledge graph updated: +12 edges, +3 nodes" },
  { time: "14:18:22", type: "EVENT", msg: "Scheduled event: Industry coalition forms" },
  { time: "14:17:01", type: "ACTION", msg: "NGO_DigitalRights published position paper" },
  { time: "14:16:15", type: "ALERT", msg: "Agent convergence detected: 67% opposing regulation" },
];

const KG_STATS = { nodes: 847, edges: 2341, entityTypes: 10, communities: 12, density: 0.034 };

const GRAPH_NODES_SAMPLE = [
  { x: 340, y: 120, r: 18, label: "Gov", color: C.green, edges: 34 },
  { x: 200, y: 80, r: 14, label: "CEO", color: C.red, edges: 28 },
  { x: 460, y: 160, r: 16, label: "Media", color: C.blue, edges: 31 },
  { x: 280, y: 200, r: 12, label: "Prof", color: C.purple, edges: 18 },
  { x: 420, y: 70, r: 10, label: "NGO", color: C.cyan, edges: 15 },
  { x: 150, y: 170, r: 15, label: "VC", color: C.amber, edges: 26 },
  { x: 380, y: 240, r: 8, label: "User", color: C.text2, edges: 9 },
  { x: 500, y: 230, r: 11, label: "Startup", color: C.red, edges: 20 },
  { x: 120, y: 260, r: 9, label: "Law", color: C.green, edges: 12 },
  { x: 300, y: 50, r: 13, label: "Bank", color: C.amber, edges: 22 },
];

const GRAPH_EDGES = [
  [0,1],[0,2],[0,3],[0,5],[1,2],[1,4],[1,5],[1,7],[2,3],[2,4],[2,6],[3,4],[3,8],[4,6],[5,7],[5,9],[6,7],[7,8],[8,9],[0,9],[2,9],[3,7],[1,9],[4,8]
];

// ─── Utility Components ───────────────────────────────────────
const Badge = ({ children, color = C.amber, bg }) => (
  <span style={{ fontSize: 10, fontWeight: 600, letterSpacing: 1, textTransform: "uppercase",
    color, background: bg || color + "18", padding: "2px 6px", borderRadius: 2, fontFamily: "'JetBrains Mono', monospace" }}>
    {children}
  </span>
);

const StatusDot = ({ status }) => {
  const colors = { running: C.green, completed: C.blue, paused: C.amber, failed: C.red, queued: C.text2 };
  const pulseStatuses = ["running"];
  return (
    <span style={{ display: "inline-block", width: 7, height: 7, borderRadius: "50%",
      background: colors[status] || C.text2, marginRight: 6, boxShadow: pulseStatuses.includes(status) ? `0 0 6px ${colors[status]}` : "none" }} />
  );
};

const MiniBar = ({ value, max = 1, color = C.amber, w = 60 }) => (
  <div style={{ width: w, height: 4, background: C.bg0, borderRadius: 2, overflow: "hidden" }}>
    <div style={{ width: `${(value / max) * 100}%`, height: "100%", background: color, borderRadius: 2, transition: "width 0.3s" }} />
  </div>
);

const Sparkline = ({ data, color = C.green, w = 80, h = 20 }) => {
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const points = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - ((v - min) / range) * h}`).join(" ");
  return (
    <svg width={w} height={h} style={{ display: "block" }}>
      <polyline points={points} fill="none" stroke={color} strokeWidth={1.2} />
    </svg>
  );
};

// ─── Panel Component ──────────────────────────────────────────
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

// ─── Main Dashboard ───────────────────────────────────────────
export default function MiroFishDashboard() {
  const [activeScenario, setActiveScenario] = useState(0);
  const [tick, setTick] = useState(0);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [cmdInput, setCmdInput] = useState("");
  const [chatMsgs, setChatMsgs] = useState([
    { role: "system", text: "MiroFish ReportAgent ready. Ask about simulation results, agent behavior, or predictions." },
  ]);
  const [activeTab, setActiveTab] = useState("overview");
  const chatEndRef = useRef(null);

  useEffect(() => {
    const interval = setInterval(() => setTick(t => t + 1), 2000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMsgs]);

  const sim = SCENARIOS[activeScenario];
  const progress = sim.rounds / sim.maxRounds;
  const currentRound = sim.rounds + (sim.status === "running" ? Math.floor(tick / 2) : 0);

  const handleCmd = useCallback(() => {
    if (!cmdInput.trim()) return;
    setChatMsgs(prev => [...prev,
      { role: "user", text: cmdInput },
      { role: "agent", text: `[ReACT] Searching knowledge graph for "${cmdInput.slice(0, 40)}..."
→ Found 12 relevant facts across 4 entities
→ Synthesizing analysis...

Based on the simulation data: The current sentiment trend shows ${Math.random() > 0.5 ? "increasing opposition" : "growing support"} from ${AGENTS_DATA[Math.floor(Math.random() * 4)].name}. Key inflection point detected at round ${Math.floor(Math.random() * 100 + 50)} when the policy draft was leaked. Recommend monitoring the ${["tech sector coalition", "media narrative shift", "regulatory timeline"][Math.floor(Math.random() * 3)]} closely.` }
    ]);
    setCmdInput("");
  }, [cmdInput]);

  const tabs = [
    { id: "overview", label: "OVERVIEW" },
    { id: "agents", label: "AGENTS" },
    { id: "graph", label: "K-GRAPH" },
    { id: "events", label: "EVENTS" },
  ];

  return (
    <div style={{ background: C.bg0, color: C.text0, fontFamily: "'JetBrains Mono', 'SF Mono', 'Fira Code', monospace",
      fontSize: 11, minHeight: "100vh", display: "flex", flexDirection: "column" }}>

      {/* ═══ TOP BAR ═══ */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "6px 12px", background: C.bg1, borderBottom: `1px solid ${C.border}`, flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 14, fontWeight: 700, color: C.amber, letterSpacing: 2 }}>MIROFISH</span>
          <span style={{ color: C.text2, fontSize: 10 }}>SWARM INTELLIGENCE TERMINAL</span>
          <span style={{ color: C.text2 }}>│</span>
          <span style={{ color: C.green, fontSize: 10 }}>● CONNECTED</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <span style={{ color: C.text2, fontSize: 10 }}>GPU: 4×A100</span>
          <span style={{ color: C.text2, fontSize: 10 }}>MEM: 67%</span>
          <span style={{ color: C.text2, fontSize: 10 }}>AGENTS: {sim.agents.toLocaleString()}</span>
          <span style={{ color: C.text1, fontSize: 10 }}>
            {new Date().toLocaleTimeString("en-US", { hour12: false })} UTC+7
          </span>
        </div>
      </div>

      {/* ═══ SCENARIO STRIP ═══ */}
      <div style={{ display: "flex", gap: 1, padding: "0", borderBottom: `1px solid ${C.border}`, flexShrink: 0, overflow: "auto" }}>
        {SCENARIOS.map((s, i) => (
          <button key={s.id} onClick={() => setActiveScenario(i)}
            style={{ flex: "0 0 auto", padding: "6px 14px", background: i === activeScenario ? C.bg2 : "transparent",
              border: "none", borderBottom: i === activeScenario ? `2px solid ${C.amber}` : "2px solid transparent",
              color: i === activeScenario ? C.text0 : C.text2, cursor: "pointer", fontFamily: "inherit", fontSize: 10,
              display: "flex", alignItems: "center", gap: 6, transition: "all 0.15s", whiteSpace: "nowrap" }}>
            <StatusDot status={s.status} />
            <span>{s.id}</span>
            <span style={{ color: i === activeScenario ? C.text1 : C.text2, maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis" }}>{s.name}</span>
          </button>
        ))}
      </div>

      {/* ═══ SIMULATION HEADER ═══ */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "8px 12px", background: C.bg1, borderBottom: `1px solid ${C.border}`, flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, color: C.text0 }}>{sim.name}</div>
            <div style={{ fontSize: 10, color: C.text2, marginTop: 2 }}>{sim.id} · {sim.domain.toUpperCase()} · {sim.agents.toLocaleString()} agents</div>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: 10, color: C.text2 }}>ROUND</div>
            <div style={{ fontSize: 16, fontWeight: 700, color: C.amber }}>{currentRound}<span style={{ color: C.text2, fontSize: 11 }}>/{sim.maxRounds}</span></div>
          </div>
          <div style={{ width: 120, height: 6, background: C.bg0, borderRadius: 3, overflow: "hidden" }}>
            <div style={{ width: `${Math.min(progress * 100 + (sim.status === "running" ? tick * 0.2 : 0), 100)}%`,
              height: "100%", background: sim.status === "running" ? C.green : sim.status === "completed" ? C.blue : C.amber,
              borderRadius: 3, transition: "width 0.5s" }} />
          </div>
          <Badge color={sim.status === "running" ? C.green : sim.status === "completed" ? C.blue : C.amber}>
            {sim.status}
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
          <Panel title="SIMULATION METRICS" badge="LIVE" style={{ gridColumn: "1", gridRow: "1" }}>
            {/* KPI Row */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 8, marginBottom: 12 }}>
              {[
                { label: "TOTAL ACTIONS", value: "12,847", delta: "+342", up: true },
                { label: "POSTS CREATED", value: "3,291", delta: "+89", up: true },
                { label: "AVG SENTIMENT", value: "-0.23", delta: "-0.08", up: false },
                { label: "ACTIVE AGENTS", value: `${Math.floor(sim.agents * 0.72)}`, delta: "+12%", up: true },
                { label: "GRAPH NODES", value: KG_STATS.nodes.toString(), delta: "+3", up: true },
                { label: "GRAPH EDGES", value: KG_STATS.edges.toLocaleString(), delta: "+12", up: true },
              ].map((kpi, i) => (
                <div key={i} style={{ background: C.bg0, borderRadius: 2, padding: "8px 10px", border: `1px solid ${C.border}` }}>
                  <div style={{ fontSize: 9, color: C.text2, letterSpacing: 1, marginBottom: 4 }}>{kpi.label}</div>
                  <div style={{ fontSize: 16, fontWeight: 700, color: C.text0 }}>{kpi.value}</div>
                  <div style={{ fontSize: 10, color: kpi.up ? C.green : C.red, marginTop: 2 }}>{kpi.delta}</div>
                </div>
              ))}
            </div>
            {/* Timeline Chart */}
            <div style={{ fontSize: 9, color: C.text2, marginBottom: 4, letterSpacing: 1 }}>AGENT ACTIVITY TIMELINE (48H)</div>
            <div style={{ height: 90, display: "flex", alignItems: "flex-end", gap: 1, padding: "0 2px" }}>
              {TIMELINE_DATA.map((d, i) => {
                const maxP = Math.max(...TIMELINE_DATA.map(t => t.activeAgents));
                const h = (d.activeAgents / maxP) * 85;
                const isCurrentHour = i === 24 + (tick % 24);
                return (
                  <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 1 }}>
                    <div style={{ width: "100%", height: h, background: isCurrentHour ? C.amber :
                      d.sentiment > 0 ? C.green + "80" : d.sentiment < -0.3 ? C.red + "60" : C.blue + "50",
                      borderRadius: "1px 1px 0 0", transition: "height 0.3s", minHeight: 2 }} />
                    {i % 6 === 0 && <span style={{ fontSize: 8, color: C.text2 }}>{i}h</span>}
                  </div>
                );
              })}
            </div>
            <div style={{ display: "flex", gap: 16, marginTop: 6 }}>
              <span style={{ fontSize: 9, color: C.text2 }}><span style={{ display: "inline-block", width: 8, height: 4, background: C.green + "80", marginRight: 4 }} />Positive</span>
              <span style={{ fontSize: 9, color: C.text2 }}><span style={{ display: "inline-block", width: 8, height: 4, background: C.blue + "50", marginRight: 4 }} />Neutral</span>
              <span style={{ fontSize: 9, color: C.text2 }}><span style={{ display: "inline-block", width: 8, height: 4, background: C.red + "60", marginRight: 4 }} />Negative</span>
              <span style={{ fontSize: 9, color: C.text2 }}><span style={{ display: "inline-block", width: 8, height: 4, background: C.amber, marginRight: 4 }} />Current</span>
            </div>
          </Panel>

          {/* ── Event Feed ── */}
          <Panel title="EVENT FEED" badge={`${EVENTS_LOG.length}`} style={{ gridColumn: "2", gridRow: "1" }} noPad>
            {EVENTS_LOG.map((evt, i) => {
              const typeColors = { EVENT: C.amber, ACTION: C.blue, SYSTEM: C.text2, ALERT: C.red };
              return (
                <div key={i} style={{ padding: "5px 10px", borderBottom: `1px solid ${C.border}`,
                  display: "flex", gap: 8, alignItems: "flex-start", fontSize: 10,
                  background: i === 0 && tick % 2 === 0 ? C.bg2 : "transparent", transition: "background 0.3s" }}>
                  <span style={{ color: C.text2, flexShrink: 0, width: 52 }}>{evt.time}</span>
                  <span style={{ color: typeColors[evt.type], fontWeight: 600, flexShrink: 0, width: 44 }}>{evt.type}</span>
                  <span style={{ color: C.text1, lineHeight: 1.4 }}>{evt.msg}</span>
                </div>
              );
            })}
          </Panel>

          {/* ── Knowledge Graph Mini ── */}
          <Panel title="KNOWLEDGE GRAPH" badge={`${KG_STATS.nodes}N ${KG_STATS.edges}E`}
            style={{ gridColumn: "1", gridRow: "2" }}
            headerRight={<span style={{ fontSize: 9, color: C.text2, cursor: "pointer" }} onClick={() => setActiveTab("graph")}>EXPAND →</span>}>
            <div style={{ display: "flex", gap: 12 }}>
              <svg viewBox="0 0 600 300" style={{ flex: 1, maxHeight: 200 }}>
                {GRAPH_EDGES.map(([a, b], i) => (
                  <line key={i} x1={GRAPH_NODES_SAMPLE[a].x} y1={GRAPH_NODES_SAMPLE[a].y}
                    x2={GRAPH_NODES_SAMPLE[b].x} y2={GRAPH_NODES_SAMPLE[b].y}
                    stroke={C.border} strokeWidth={0.5} opacity={0.6} />
                ))}
                {GRAPH_NODES_SAMPLE.map((n, i) => (
                  <g key={i}>
                    <circle cx={n.x} cy={n.y} r={n.r} fill={n.color + "30"} stroke={n.color} strokeWidth={1} />
                    <text x={n.x} y={n.y + 3} textAnchor="middle" fill={n.color} fontSize={8} fontFamily="inherit">{n.label}</text>
                  </g>
                ))}
              </svg>
              <div style={{ width: 160, display: "flex", flexDirection: "column", gap: 4 }}>
                <div style={{ fontSize: 9, color: C.text2, letterSpacing: 1, marginBottom: 4 }}>ENTITY DISTRIBUTION</div>
                {[
                  { label: "Person", count: 312, color: C.text1 },
                  { label: "Organization", count: 186, color: C.blue },
                  { label: "Executive", count: 89, color: C.red },
                  { label: "MediaOutlet", count: 67, color: C.cyan },
                  { label: "Government", count: 45, color: C.green },
                  { label: "Professor", count: 38, color: C.purple },
                  { label: "Other", count: 110, color: C.text2 },
                ].map((e, i) => (
                  <div key={i} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 10 }}>
                    <span style={{ width: 6, height: 6, borderRadius: 1, background: e.color, flexShrink: 0 }} />
                    <span style={{ color: C.text1, flex: 1 }}>{e.label}</span>
                    <span style={{ color: C.text2 }}>{e.count}</span>
                    <MiniBar value={e.count} max={312} color={e.color} w={40} />
                  </div>
                ))}
              </div>
            </div>
          </Panel>

          {/* ── Report Agent Chat ── */}
          <Panel title="REPORT AGENT" badge="ReACT"
            style={{ gridColumn: "2", gridRow: "2" }}>
            <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
              <div style={{ flex: 1, overflow: "auto", display: "flex", flexDirection: "column", gap: 6, marginBottom: 8 }}>
                {chatMsgs.map((msg, i) => (
                  <div key={i} style={{ fontSize: 10, lineHeight: 1.5,
                    color: msg.role === "system" ? C.text2 : msg.role === "user" ? C.cyan : C.text1,
                    background: msg.role === "agent" ? C.bg0 : "transparent",
                    padding: msg.role === "agent" ? "6px 8px" : "0",
                    borderRadius: 2, borderLeft: msg.role === "agent" ? `2px solid ${C.amber}` : "none",
                    whiteSpace: "pre-wrap" }}>
                    {msg.role === "user" && <span style={{ color: C.cyan }}>▸ </span>}
                    {msg.text}
                  </div>
                ))}
                <div ref={chatEndRef} />
              </div>
              <div style={{ display: "flex", gap: 4, flexShrink: 0 }}>
                <input value={cmdInput} onChange={e => setCmdInput(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && handleCmd()}
                  placeholder="Ask the ReportAgent..."
                  style={{ flex: 1, background: C.bg0, border: `1px solid ${C.border}`, borderRadius: 2,
                    padding: "6px 8px", color: C.text0, fontFamily: "inherit", fontSize: 11, outline: "none" }} />
                <button onClick={handleCmd}
                  style={{ background: C.amber, color: C.bg0, border: "none", borderRadius: 2,
                    padding: "6px 12px", fontFamily: "inherit", fontSize: 10, fontWeight: 700,
                    cursor: "pointer", letterSpacing: 1 }}>
                  SEND
                </button>
              </div>
            </div>
          </Panel>
        </>}

        {activeTab === "agents" && (
          <Panel title="AGENT POPULATION MONITOR" badge={`${AGENTS_DATA.length} TRACKED`}
            style={{ gridColumn: "1 / -1", gridRow: "1 / -1" }} noPad>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 10 }}>
                <thead>
                  <tr style={{ background: C.bg2 }}>
                    {["ID","NAME","TYPE","STANCE","PLATFORM","ACTIVITY","INFLUENCE","ACTIONS","SENTIMENT","TREND"].map(h => (
                      <th key={h} style={{ padding: "6px 10px", textAlign: "left", color: C.text2,
                        fontSize: 9, letterSpacing: 1, borderBottom: `1px solid ${C.border}`, fontWeight: 600, whiteSpace: "nowrap" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {AGENTS_DATA.map((agent, i) => (
                    <tr key={agent.id} onClick={() => setSelectedAgent(selectedAgent === i ? null : i)}
                      style={{ background: selectedAgent === i ? C.bg3 : i % 2 === 0 ? "transparent" : C.bg0 + "60",
                        cursor: "pointer", transition: "background 0.15s" }}>
                      <td style={{ padding: "8px 10px", color: C.text2, borderBottom: `1px solid ${C.border}` }}>{agent.id}</td>
                      <td style={{ padding: "8px 10px", color: C.text0, fontWeight: 600, borderBottom: `1px solid ${C.border}` }}>
                        <span style={{ color: C.amber }}>@</span>{agent.name}
                      </td>
                      <td style={{ padding: "8px 10px", borderBottom: `1px solid ${C.border}` }}>
                        <Badge color={C.text1} bg={C.bg3}>{agent.type}</Badge>
                      </td>
                      <td style={{ padding: "8px 10px", color: agent.stance.includes("oppose") || agent.stance.includes("anti") ? C.red : agent.stance.includes("pro") || agent.stance.includes("support") ? C.green : C.text1,
                        borderBottom: `1px solid ${C.border}`, fontSize: 10 }}>{agent.stance}</td>
                      <td style={{ padding: "8px 10px", borderBottom: `1px solid ${C.border}` }}>
                        <Badge color={C.blue} bg={C.blueDim}>{agent.platform}</Badge>
                      </td>
                      <td style={{ padding: "8px 10px", borderBottom: `1px solid ${C.border}` }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          <MiniBar value={agent.activity} color={agent.activity > 0.8 ? C.green : C.amber} />
                          <span style={{ color: C.text1, width: 28, textAlign: "right" }}>{(agent.activity * 100).toFixed(0)}%</span>
                        </div>
                      </td>
                      <td style={{ padding: "8px 10px", borderBottom: `1px solid ${C.border}` }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          <MiniBar value={agent.influence} color={C.purple} />
                          <span style={{ color: C.text1, width: 28, textAlign: "right" }}>{(agent.influence * 100).toFixed(0)}%</span>
                        </div>
                      </td>
                      <td style={{ padding: "8px 10px", color: C.text0, fontWeight: 600, borderBottom: `1px solid ${C.border}`, textAlign: "right" }}>
                        {agent.actions.toLocaleString()}
                      </td>
                      <td style={{ padding: "8px 10px", borderBottom: `1px solid ${C.border}`,
                        color: agent.sentiment > 0 ? C.green : agent.sentiment < -0.3 ? C.red : C.text1, fontWeight: 600, textAlign: "right" }}>
                        {agent.sentiment > 0 ? "+" : ""}{agent.sentiment.toFixed(2)}
                      </td>
                      <td style={{ padding: "8px 10px", borderBottom: `1px solid ${C.border}` }}>
                        <Sparkline data={Array.from({length: 20}, () => Math.random() * 0.5 + agent.activity * 0.5)}
                          color={agent.sentiment > 0 ? C.green : C.red} w={60} h={16} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {selectedAgent !== null && (
              <div style={{ padding: "12px 16px", background: C.bg2, borderTop: `1px solid ${C.amber}40`,
                display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16 }}>
                <div>
                  <div style={{ fontSize: 9, color: C.text2, letterSpacing: 1 }}>AGENT PROFILE</div>
                  <div style={{ fontSize: 13, color: C.amber, fontWeight: 700, marginTop: 4 }}>@{AGENTS_DATA[selectedAgent].name}</div>
                  <div style={{ fontSize: 10, color: C.text1, marginTop: 2 }}>{AGENTS_DATA[selectedAgent].type} · {AGENTS_DATA[selectedAgent].platform}</div>
                </div>
                <div>
                  <div style={{ fontSize: 9, color: C.text2, letterSpacing: 1 }}>BEHAVIOR ANALYSIS</div>
                  <div style={{ fontSize: 10, color: C.text1, marginTop: 4, lineHeight: 1.6 }}>
                    Activity pattern: <span style={{ color: C.green }}>Peak hours 19-22</span><br/>
                    Content style: <span style={{ color: C.blue }}>Analytical, data-driven</span><br/>
                    Network position: <span style={{ color: C.purple }}>Bridge connector</span>
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 9, color: C.text2, letterSpacing: 1 }}>INFLUENCE NETWORK</div>
                  <div style={{ fontSize: 10, color: C.text1, marginTop: 4, lineHeight: 1.6 }}>
                    Direct reach: <span style={{ color: C.amber }}>{(AGENTS_DATA[selectedAgent].influence * 5000).toFixed(0)} agents</span><br/>
                    Repost rate: <span style={{ color: C.green }}>23.4%</span><br/>
                    Avg engagement: <span style={{ color: C.cyan }}>847/post</span>
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 9, color: C.text2, letterSpacing: 1 }}>RECENT ACTIONS</div>
                  <div style={{ fontSize: 10, color: C.text1, marginTop: 4, lineHeight: 1.6 }}>
                    <span style={{ color: C.blue }}>CREATE_POST</span> — 3 min ago<br/>
                    <span style={{ color: C.green }}>LIKE_POST</span> — 7 min ago<br/>
                    <span style={{ color: C.purple }}>REPOST</span> — 12 min ago
                  </div>
                </div>
              </div>
            )}
          </Panel>
        )}

        {activeTab === "graph" && <>
          <Panel title="KNOWLEDGE GRAPH EXPLORER" badge={`${KG_STATS.nodes} NODES · ${KG_STATS.edges} EDGES`}
            style={{ gridColumn: "1", gridRow: "1 / -1" }}>
            <svg viewBox="0 0 600 500" style={{ width: "100%", height: "100%" }}>
              {/* Edges */}
              {GRAPH_EDGES.map(([a, b], i) => {
                const na = GRAPH_NODES_SAMPLE[a], nb = GRAPH_NODES_SAMPLE[b];
                return <line key={i} x1={na.x} y1={na.y * 1.6} x2={nb.x} y2={nb.y * 1.6}
                  stroke={C.borderHi} strokeWidth={0.8} opacity={0.5} />;
              })}
              {/* Nodes */}
              {GRAPH_NODES_SAMPLE.map((n, i) => (
                <g key={i} style={{ cursor: "pointer" }}>
                  <circle cx={n.x} cy={n.y * 1.6} r={n.r * 1.5} fill={n.color + "15"} stroke={n.color} strokeWidth={1.2} />
                  <circle cx={n.x} cy={n.y * 1.6} r={3} fill={n.color} />
                  <text x={n.x} y={n.y * 1.6 - n.r * 1.5 - 6} textAnchor="middle"
                    fill={n.color} fontSize={10} fontFamily="inherit" fontWeight="600">{n.label}</text>
                  <text x={n.x} y={n.y * 1.6 + n.r * 1.5 + 12} textAnchor="middle"
                    fill={C.text2} fontSize={8} fontFamily="inherit">{n.edges} edges</text>
                </g>
              ))}
            </svg>
          </Panel>
          <Panel title="GRAPH METRICS" style={{ gridColumn: "2", gridRow: "1" }}>
            {[
              { label: "Total Nodes", value: KG_STATS.nodes, color: C.amber },
              { label: "Total Edges", value: KG_STATS.edges, color: C.blue },
              { label: "Entity Types", value: KG_STATS.entityTypes, color: C.green },
              { label: "Communities", value: KG_STATS.communities, color: C.purple },
              { label: "Graph Density", value: KG_STATS.density.toFixed(3), color: C.cyan },
              { label: "Avg Degree", value: (KG_STATS.edges * 2 / KG_STATS.nodes).toFixed(1), color: C.text1 },
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
              {["Person → WORKS_FOR → Organization", "Executive → LEADS → Company",
                "MediaOutlet → REPORTS_ON → Event", "Professor → AFFILIATED_WITH → University",
                "GovernmentAgency → REGULATES → Company", "NGO → OPPOSES → Policy",
                "Person → SUPPORTS → Person", "Organization → COLLABORATES → Organization"
              ].map((r, i) => (
                <div key={i} style={{ padding: "2px 0", borderBottom: `1px solid ${C.bg0}` }}>
                  <span style={{ color: C.green }}>{r.split(" → ")[0]}</span>
                  <span style={{ color: C.text2 }}> → </span>
                  <span style={{ color: C.amber }}>{r.split(" → ")[1]}</span>
                  <span style={{ color: C.text2 }}> → </span>
                  <span style={{ color: C.blue }}>{r.split(" → ")[2]}</span>
                </div>
              ))}
            </div>
          </Panel>
        </>}

        {activeTab === "events" && <>
          <Panel title="EVENT INJECTION CONSOLE" badge="SCENARIO CONTROL"
            style={{ gridColumn: "1", gridRow: "1" }}>
            <div style={{ fontSize: 10, color: C.text2, marginBottom: 10, letterSpacing: 0.5 }}>
              Inject events into the running simulation to test scenarios. Events trigger agent reactions in real-time.
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8 }}>
              {[
                { icon: "⚡", title: "Breaking News", desc: "Major policy announcement", color: C.red },
                { icon: "📊", title: "Market Shock", desc: "Economic indicator shift", color: C.amber },
                { icon: "🔄", title: "Narrative Shift", desc: "Counter-narrative emerges", color: C.blue },
                { icon: "👥", title: "Coalition Forms", desc: "Group alignment event", color: C.green },
                { icon: "📱", title: "Viral Content", desc: "High-impact post injection", color: C.purple },
                { icon: "⏰", title: "Deadline Event", desc: "Time-pressure trigger", color: C.cyan },
              ].map((evt, i) => (
                <div key={i} style={{ background: C.bg0, border: `1px solid ${C.border}`, borderRadius: 3,
                  padding: "10px 12px", cursor: "pointer", transition: "all 0.15s",
                  borderLeft: `3px solid ${evt.color}` }}
                  onMouseOver={e => { e.currentTarget.style.borderColor = evt.color; e.currentTarget.style.background = C.bg2; }}
                  onMouseOut={e => { e.currentTarget.style.borderColor = C.border; e.currentTarget.style.background = C.bg0; }}>
                  <div style={{ fontSize: 12, marginBottom: 4 }}>{evt.icon}</div>
                  <div style={{ fontSize: 11, fontWeight: 600, color: C.text0 }}>{evt.title}</div>
                  <div style={{ fontSize: 9, color: C.text2, marginTop: 2 }}>{evt.desc}</div>
                </div>
              ))}
            </div>
          </Panel>
          <Panel title="SCHEDULED EVENTS" style={{ gridColumn: "2", gridRow: "1" }}>
            {[
              { round: 150, name: "Policy Draft v2 Release", status: "pending" },
              { round: 200, name: "Public Comment Period Opens", status: "pending" },
              { round: 100, name: "Industry Report Published", status: "fired" },
              { round: 50, name: "Initial Leak to Media", status: "fired" },
            ].map((evt, i) => (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 0",
                borderBottom: `1px solid ${C.border}`, opacity: evt.status === "fired" ? 0.5 : 1 }}>
                <span style={{ color: C.text2, fontSize: 10, width: 48 }}>R{evt.round}</span>
                <span style={{ flex: 1, color: C.text1, fontSize: 10 }}>{evt.name}</span>
                <Badge color={evt.status === "fired" ? C.text2 : C.amber}>{evt.status}</Badge>
              </div>
            ))}
          </Panel>
          <Panel title="SIMULATION TIMELINE" style={{ gridColumn: "1 / -1", gridRow: "2" }}>
            <div style={{ position: "relative", height: 60, margin: "20px 0" }}>
              {/* Timeline bar */}
              <div style={{ position: "absolute", top: 28, left: 0, right: 0, height: 4, background: C.bg0, borderRadius: 2 }}>
                <div style={{ width: `${progress * 100}%`, height: "100%", background: `linear-gradient(90deg, ${C.green}, ${C.amber})`,
                  borderRadius: 2 }} />
              </div>
              {/* Event markers */}
              {[
                { pos: 10, label: "Leak", color: C.red },
                { pos: 20, label: "Report", color: C.blue },
                { pos: 25.4, label: "NOW", color: C.amber },
                { pos: 30, label: "Draft v2", color: C.green },
                { pos: 40, label: "Comment", color: C.purple },
              ].map((m, i) => (
                <div key={i} style={{ position: "absolute", left: `${m.pos}%`, top: 0, display: "flex", flexDirection: "column",
                  alignItems: "center", transform: "translateX(-50%)" }}>
                  <span style={{ fontSize: 8, color: m.color, marginBottom: 4, whiteSpace: "nowrap" }}>{m.label}</span>
                  <div style={{ width: 2, height: 16, background: m.color, borderRadius: 1 }} />
                  <div style={{ width: 8, height: 8, borderRadius: "50%", background: m.color, marginTop: -2,
                    boxShadow: m.label === "NOW" ? `0 0 8px ${m.color}` : "none" }} />
                </div>
              ))}
              {/* Scale */}
              <div style={{ position: "absolute", top: 44, left: 0, right: 0, display: "flex", justifyContent: "space-between" }}>
                {[0, 100, 200, 300, 400, 500].map(r => (
                  <span key={r} style={{ fontSize: 8, color: C.text2 }}>R{r}</span>
                ))}
              </div>
            </div>
          </Panel>
        </>}
      </div>

      {/* ═══ STATUS BAR ═══ */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "4px 12px", background: C.bg1, borderTop: `1px solid ${C.border}`, flexShrink: 0 }}>
        <div style={{ display: "flex", gap: 16, color: C.text2, fontSize: 9 }}>
          <span>KERNEL v1.2</span>
          <span>PIPELINE: 7-STAGE</span>
          <span>LLM: Claude Opus 4.6</span>
          <span>GRAPH: Zep Cloud</span>
        </div>
        <div style={{ display: "flex", gap: 16, color: C.text2, fontSize: 9 }}>
          <span>LATENCY: <span style={{ color: C.green }}>23ms</span></span>
          <span>THROUGHPUT: <span style={{ color: C.green }}>1.2K acts/s</span></span>
          <span style={{ color: C.amber }}>MiroFish Kernel — Swarm Intelligence Engine</span>
        </div>
      </div>
    </div>
  );
}
