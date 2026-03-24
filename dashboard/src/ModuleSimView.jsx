import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { THEMES } from "./theme.js";

/**
 * Generic Simulation Animation View for ANY portal module.
 * Reads scenario data and animates a decision chain with split view
 * (baseline slow vs drone fast).
 */

const PHASE_ORDER = ["detect", "verify", "decide", "respond", "resolve"];
const PHASE_VI = { detect: "PHÁT HIỆN", verify: "XÁC MINH", decide: "QUYẾT ĐỊNH", respond: "PHẢN ỨNG", resolve: "GIẢI QUYẾT" };
const PHASE_EN = { detect: "DETECT", verify: "VERIFY", decide: "DECIDE", respond: "RESPOND", resolve: "RESOLVE" };

// Generate decision chain from scenario timing data
function generateChain(scenario, configRuns, isBaseline) {
  const steps = [];
  const agents = ["CMD", "SENSOR", "RECON", "RESP-1", "RESP-2", "LOG"];
  const phases = PHASE_ORDER;

  // Use average KPIs to set phase durations
  const runs = configRuns || [];
  if (runs.length === 0) return steps;

  const avgKpi = {};
  for (const key of Object.keys(runs[0]?.kpi || {})) {
    avgKpi[key] = runs.reduce((s, r) => s + (r.kpi[key] || 0), 0) / runs.length;
  }

  const det = avgKpi.detection_latency || 60;
  const ver = avgKpi.verification_time || 150;
  const dec = avgKpi.decision_time || 40;
  const res = avgKpi.response_time || 120;
  const total = avgKpi.total_resolution || 600;

  // Build chain steps
  let t = 0;
  steps.push({ agent: "SENSOR", phase: "detect", delay: t, text: isBaseline ? "Phát hiện bất thường — đánh giá sơ bộ" : "🛸 Drone phát hiện tức thì — feed trực tiếp" });
  t += det * 0.5;
  steps.push({ agent: "CMD", phase: "detect", delay: t, text: isBaseline ? "Nhận báo cáo — kiểm tra thông tin" : "CMD nhận feed — đánh giá nhanh" });
  t += det * 0.5;
  steps.push({ agent: isBaseline ? "RESP-1" : "RECON", phase: "verify", delay: t, text: isBaseline ? "Gửi đội xác minh tại chỗ — ETA vài phút" : "🛸 Drone trinh sát xác minh — 30 giây" });
  t += ver * 0.5;
  steps.push({ agent: "CMD", phase: "verify", delay: t, text: isBaseline ? "Chờ xác minh... chưa có hình ảnh" : "Xác nhận bằng hình ảnh — phân loại sự cố" });
  t += ver * 0.5;
  steps.push({ agent: "CMD", phase: "decide", delay: t, text: isBaseline ? "Ra quyết định — thông tin hạn chế" : "⚡ Quyết định nhanh — dữ liệu đầy đủ" });
  t += dec * 0.5;
  steps.push({ agent: "RESP-1", phase: "decide", delay: t, text: isBaseline ? "Triển khai phương án — không có hướng dẫn" : "Triển khai theo hướng dẫn drone" });
  t += dec * 0.5;
  steps.push({ agent: "RESP-1", phase: "respond", delay: t, text: isBaseline ? "Đội phản ứng di chuyển — không rõ đường" : "🛸 Drone dẫn đường — đường tối ưu" });
  t += res * 0.5;
  steps.push({ agent: "RESP-2", phase: "respond", delay: t, text: isBaseline ? "Hỗ trợ — điều phối khó khăn" : "Hỗ trợ phối hợp qua drone feed" });
  t += res * 0.5;
  steps.push({ agent: "CMD", phase: "resolve", delay: t, text: isBaseline ? "⏳ Tình huống đang kiểm soát — chậm" : "✅ Tình huống được giải quyết nhanh" });
  t += (total - t) * 0.5 || 30;
  steps.push({ agent: "LOG", phase: "resolve", delay: t, text: isBaseline ? "Ghi nhận — phản ứng chậm" : "✅ Hoàn tất — ghi nhật ký" });

  return steps;
}

const AGENT_COLORS = { CMD: "#f0883e", SENSOR: "#8b949e", RECON: "#58a6ff", "RESP-1": "#3fb950", "RESP-2": "#bc8cff", LOG: "#39d2f5" };

function phaseColor(p) {
  return { detect: "#f0883e", verify: "#58a6ff", decide: "#39d2f5", respond: "#3fb950", resolve: "#bc8cff" }[p] || "#8b949e";
}

export default function ModuleSimView({ moduleData, moduleMeta, themeId = "light", langId = "vi" }) {
  const T = THEMES[themeId] || THEMES.light;
  const [scenarioIdx, setScenarioIdx] = useState(0);
  const [stepB, setStepB] = useState(-1);
  const [stepD, setStepD] = useState(-1);
  const [playing, setPlaying] = useState(false);
  const [radioLog, setRadioLog] = useState([]);
  const tB = useRef(null);
  const tD = useRef(null);
  const logRef = useRef(null);

  const scenarios = moduleData?.scenarios || [];
  const sc = scenarios[scenarioIdx];

  // Get first and last config for baseline vs drone
  const allConfigs = sc ? Object.keys(sc.configs || {}) : [];
  const baseConfig = allConfigs[0] || "BASELINE";
  const droneConfig = allConfigs[allConfigs.length - 1] || "FULL";

  const chainB = useMemo(() => sc ? generateChain(sc, sc.configs?.[baseConfig]?.runs ? Array(50).fill({ kpi: Object.fromEntries(Object.entries(sc.configs[baseConfig].kpi || {}).map(([k, v]) => [k, v.mean || 0])) }) : [], true) : [], [sc, baseConfig]);
  const chainD = useMemo(() => sc ? generateChain(sc, sc.configs?.[droneConfig]?.runs ? Array(50).fill({ kpi: Object.fromEntries(Object.entries(sc.configs[droneConfig].kpi || {}).map(([k, v]) => [k, v.mean || 0])) }) : [], false) : [], [sc, droneConfig]);

  const reset = useCallback(() => {
    clearTimeout(tB.current); clearTimeout(tD.current);
    setStepB(-1); setStepD(-1); setPlaying(false); setRadioLog([]);
  }, []);

  const run = useCallback(() => {
    reset();
    setPlaying(true);
    let bS = 0, dS = 0;
    const speed = 1.5;
    const advB = () => {
      if (bS >= chainB.length) return;
      setStepB(bS);
      setRadioLog(p => [...p, { ...chainB[bS], mode: "B" }]);
      const next = bS < chainB.length - 1 ? (chainB[bS + 1].delay - chainB[bS].delay) / speed : 2000;
      bS++; tB.current = setTimeout(advB, Math.max(next, 300));
    };
    const advD = () => {
      if (dS >= chainD.length) return;
      setStepD(dS);
      setRadioLog(p => [...p, { ...chainD[dS], mode: "D" }]);
      const next = dS < chainD.length - 1 ? (chainD[dS + 1].delay - chainD[dS].delay) / speed : 2000;
      dS++; tD.current = setTimeout(advD, Math.max(next, 300));
    };
    tB.current = setTimeout(advB, 400);
    tD.current = setTimeout(advD, 400);
  }, [chainB, chainD, reset]);

  useEffect(() => { reset(); }, [scenarioIdx]);
  useEffect(() => { if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight; }, [radioLog]);

  if (!sc) return <div style={{ color: T.dim, textAlign: "center", padding: 40 }}>No scenarios</div>;

  const curB = stepB >= 0 && stepB < chainB.length ? chainB[stepB] : null;
  const curD = stepD >= 0 && stepD < chainD.length ? chainD[stepD] : null;
  const phaseLabels = langId === "vi" ? PHASE_VI : PHASE_EN;

  // KPI from scenario
  const bKpi = sc.configs?.[baseConfig]?.kpi || {};
  const dKpi = sc.configs?.[droneConfig]?.kpi || {};
  const totalB = bKpi.total_resolution?.mean || 0;
  const totalD = dKpi.total_resolution?.mean || 0;
  const imp = totalB > 0 ? Math.round((1 - totalD / totalB) * 100) : 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", fontFamily: "'JetBrains Mono',monospace", fontSize: 10, background: T.bg0, color: T.text0 }}>
      {/* Scenario selector + controls */}
      <div style={{ display: "flex", alignItems: "center", gap: 4, padding: "4px 8px", borderBottom: `1px solid ${T.border}`, flexShrink: 0 }}>
        <span style={{ color: playing ? T.green : T.text2, fontSize: 9, fontWeight: 700 }}>{playing ? "●" : "○"}</span>
        {scenarios.map((s, i) => (
          <button key={s.id} onClick={() => { reset(); setScenarioIdx(i); }}
            style={{ padding: "2px 6px", fontSize: 8, border: `1px solid ${i === scenarioIdx ? T.amber : T.border}`,
              background: i === scenarioIdx ? T.amber + "18" : "transparent",
              color: i === scenarioIdx ? T.amber : T.text2, fontFamily: "inherit", cursor: "pointer", borderRadius: 2 }}>
            {s.id}
          </button>
        ))}
        <div style={{ flex: 1 }} />
        <button onClick={playing ? reset : run}
          style={{ padding: "3px 12px", fontSize: 9, fontWeight: 700, border: `1px solid ${playing ? T.red : T.green}`,
            background: playing ? T.redDim : T.greenDim, color: playing ? T.red : T.green,
            fontFamily: "inherit", cursor: "pointer", borderRadius: 2 }}>
          {playing ? (langId === "vi" ? "■ DỪNG" : "■ STOP") : (langId === "vi" ? "▶ CHẠY MÔ PHỎNG" : "▶ RUN SIM")}
        </button>
      </div>

      {/* KPI strip */}
      <div style={{ display: "flex", gap: 3, padding: "4px 8px", borderBottom: `1px solid ${T.border}`, flexShrink: 0 }}>
        <div style={{ flex: 1, fontSize: 9 }}><span style={{ color: T.text2 }}>{sc.name}</span></div>
        <span style={{ fontSize: 10, color: T.text2 }}>{baseConfig}: <b style={{ color: T.red }}>{(totalB||0).toFixed(0)}s</b></span>
        <span style={{ color: T.text2 }}>→</span>
        <span style={{ fontSize: 10, color: T.text2 }}>{droneConfig}: <b style={{ color: T.green }}>{(totalD||0).toFixed(0)}s</b></span>
        <span style={{ fontSize: 11, fontWeight: 800, color: T.green }}>-{imp}%</span>
      </div>

      {/* Main area: split animation + radio log */}
      <div style={{ flex: 1, display: "flex", gap: 1, padding: 4, minHeight: 0, overflow: "hidden" }}>

        {/* Left: Baseline chain */}
        <div style={{ flex: 1, background: T.bg1, border: `1px solid ${T.red}30`, borderRadius: 4, display: "flex", flexDirection: "column", minHeight: 0 }}>
          <div style={{ padding: "4px 8px", borderBottom: `1px solid ${T.border}`, fontSize: 10, fontWeight: 800, color: T.red, flexShrink: 0 }}>
            ■ {baseConfig}
          </div>
          <div style={{ flex: 1, overflow: "auto", padding: "4px 8px" }}>
            {chainB.map((c, i) => (
              <div key={i} style={{ display: "flex", gap: 5, padding: "3px 0", opacity: i < stepB ? 0.4 : i === stepB ? 1 : 0.1, transition: "opacity 0.4s" }}>
                <span style={{ color: T.text2, minWidth: 28, textAlign: "right", fontSize: 9 }}>{(c.delay||0).toFixed(0)}s</span>
                <span style={{ width: 6, height: 6, borderRadius: 2, background: phaseColor(c.phase), marginTop: 4, flexShrink: 0, boxShadow: i === stepB ? `0 0 6px ${phaseColor(c.phase)}` : "none" }} />
                <span style={{ color: AGENT_COLORS[c.agent] || T.text1, fontWeight: 700, fontSize: 9, minWidth: 40 }}>{c.agent}</span>
                <span style={{ color: i === stepB ? T.text0 : T.text2, fontSize: 9 }}>{c.text}</span>
              </div>
            ))}
          </div>
          <div style={{ padding: "4px 8px", borderTop: `1px solid ${T.border}`, fontSize: 10, flexShrink: 0, display: "flex", justifyContent: "space-between" }}>
            <span style={{ color: T.text2 }}>{curB ? phaseLabels[curB.phase] : "—"}</span>
            <span style={{ color: T.red, fontWeight: 700 }}>{curB ? `${(curB.delay||0).toFixed(0)}s` : "0s"}</span>
          </div>
        </div>

        {/* Right: Drone chain */}
        <div style={{ flex: 1, background: T.bg1, border: `1px solid ${T.green}30`, borderRadius: 4, display: "flex", flexDirection: "column", minHeight: 0 }}>
          <div style={{ padding: "4px 8px", borderBottom: `1px solid ${T.border}`, fontSize: 10, fontWeight: 800, color: T.green, flexShrink: 0 }}>
            ■ {droneConfig}
          </div>
          <div style={{ flex: 1, overflow: "auto", padding: "4px 8px" }}>
            {chainD.map((c, i) => (
              <div key={i} style={{ display: "flex", gap: 5, padding: "3px 0", opacity: i < stepD ? 0.4 : i === stepD ? 1 : 0.1, transition: "opacity 0.4s" }}>
                <span style={{ color: T.text2, minWidth: 28, textAlign: "right", fontSize: 9 }}>{(c.delay||0).toFixed(0)}s</span>
                <span style={{ width: 6, height: 6, borderRadius: 2, background: phaseColor(c.phase), marginTop: 4, flexShrink: 0, boxShadow: i === stepD ? `0 0 6px ${phaseColor(c.phase)}` : "none" }} />
                <span style={{ color: AGENT_COLORS[c.agent] || T.text1, fontWeight: 700, fontSize: 9, minWidth: 40 }}>{c.agent}</span>
                <span style={{ color: i === stepD ? T.text0 : T.text2, fontSize: 9 }}>{c.text}</span>
              </div>
            ))}
          </div>
          <div style={{ padding: "4px 8px", borderTop: `1px solid ${T.border}`, fontSize: 10, flexShrink: 0, display: "flex", justifyContent: "space-between" }}>
            <span style={{ color: T.text2 }}>{curD ? phaseLabels[curD.phase] : "—"}</span>
            <span style={{ color: T.green, fontWeight: 700 }}>{curD ? `${(curD.delay||0).toFixed(0)}s` : "0s"}</span>
          </div>
        </div>

        {/* Radio log */}
        <div style={{ width: 260, flexShrink: 0, background: T.bg1, border: `1px solid ${T.border}`, borderRadius: 4, display: "flex", flexDirection: "column", minHeight: 0 }}>
          <div style={{ padding: "4px 8px", borderBottom: `1px solid ${T.border}`, fontSize: 10, fontWeight: 800, color: T.cyan, flexShrink: 0 }}>
            {langId === "vi" ? "LIÊN LẠC" : "RADIO LOG"}
          </div>
          <div ref={logRef} style={{ flex: 1, overflow: "auto", padding: "4px 6px", position: "relative" }}>
            {radioLog.map((e, i) => (
              <div key={i} style={{ display: "flex", gap: 4, padding: "2px 0", opacity: i === radioLog.length - 1 ? 1 : 0.4, fontSize: 9 }}>
                <span style={{ color: T.text2, minWidth: 20, textAlign: "right" }}>{(e.delay||0).toFixed(0)}s</span>
                <span style={{ width: 4, height: 4, borderRadius: 1, background: phaseColor(e.phase), marginTop: 4, flexShrink: 0 }} />
                <span style={{ color: e.mode === "D" ? T.green : T.red, fontWeight: 600, minWidth: 14 }}>{e.mode === "D" ? "▲" : "▼"}</span>
                <span style={{ color: e.mode === "D" ? T.text0 : T.text2 }}>{e.text}</span>
              </div>
            ))}
            {radioLog.length === 0 && <div style={{ color: T.text2, textAlign: "center", marginTop: 20 }}>{langId === "vi" ? "Nhấn ▶ CHẠY MÔ PHỎNG" : "Press ▶ RUN SIM"}</div>}
          </div>
        </div>
      </div>

      {/* Phase progress bar */}
      <div style={{ display: "flex", gap: 2, padding: "4px 8px", borderTop: `1px solid ${T.border}`, flexShrink: 0 }}>
        {PHASE_ORDER.map(p => {
          const isActive = curD?.phase === p || curB?.phase === p;
          const isPast = curD && PHASE_ORDER.indexOf(p) < PHASE_ORDER.indexOf(curD.phase);
          return (
            <div key={p} style={{ flex: 1, textAlign: "center" }}>
              <div style={{ height: 3, borderRadius: 2, background: isPast ? phaseColor(p) : isActive ? phaseColor(p) : T.border, opacity: isPast ? 0.5 : isActive ? 1 : 0.2, transition: "all 0.4s" }} />
              <div style={{ fontSize: 7, color: isActive ? phaseColor(p) : T.text2, marginTop: 2, fontWeight: 600 }}>{phaseLabels[p]}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
