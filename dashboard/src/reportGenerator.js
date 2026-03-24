/**
 * RTR Simulator Portal — Bilingual Report Generator
 * Generates markdown reports (Vietnamese + English) from comparison data.
 * Works 100% offline — no backend required.
 */

import { MODULE_META, KPI_LABELS, CATEGORY_LABELS } from "./moduleMetadata.js";

const KPI_ORDER = ["detection_latency", "verification_time", "decision_time", "response_time", "total_resolution"];

function kpiLabel(key, lang) {
  return KPI_LABELS[key]?.[lang] || key.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

function imp(baseline, compare) {
  if (!baseline || baseline === 0) return 0;
  return Math.round((1 - compare / baseline) * 100);
}

function fmtNum(v) { return (v || 0).toFixed(0); }

// ═══════════════════════════════════════════════════════════
// METHODOLOGY TEXT — written once, used for all modules
// ═══════════════════════════════════════════════════════════

const METHODOLOGY = {
  vi: `### Phương pháp

Báo cáo này dựa trên kết quả của **RTR Simulator** — hệ thống mô phỏng chuỗi quyết định đa tác nhân (multi-agent decision chain simulation).

**Đây KHÔNG phải mô phỏng vật lý** (như mô phỏng dòng chảy đám đông hay quỹ đạo bay). RTR Simulator mô phỏng **QUÁ TRÌNH RA QUYẾT ĐỊNH** của con người trong chuỗi chỉ huy: ai thấy gì, ai báo cho ai, ai quyết định gì, và mất bao lâu để chuỗi phản ứng hoàn tất.

**Cách hoạt động:**
1. **Mỗi tác nhân** (chỉ huy, cảm biến, đội phản ứng) nhận thông tin theo vai trò và vị trí
2. **Cấu hình khác nhau** = thông tin khác nhau. Không có drone → phải gửi người kiểm tra bằng mắt. Có drone → hình ảnh trực tiếp từ trên cao
3. **Mỗi kịch bản** chạy nhiều lần (50 lần) với biến thiên ngẫu nhiên ±20% để tạo phân bố thống kê
4. **KPI** (chỉ số hiệu suất) đo thời gian từng giai đoạn: Phát hiện → Xác minh → Quyết định → Phản ứng → Giải quyết

**Các cấu hình so sánh:**
- **Cấu hình 1 (không drone):** Chỉ dùng cảm biến cố định, radio, và con người tuần tra
- **Cấu hình 2 (drone cơ bản):** Thêm 1 drone cố định cung cấp hình ảnh liên tục
- **Cấu hình 3 (hệ thống đầy đủ):** Drone cố định + drone phản ứng nhanh triển khai trong 45 giây

**Hạn chế:** Mô phỏng dựa trên mô hình thống kê, không phải quan sát thực địa. Khuyến nghị xác thực bằng diễn tập thực tế.`,

  en: `### Methodology

This report is based on results from the **RTR Simulator** — a multi-agent decision chain simulation system.

**This is NOT a physics simulation** (like crowd flow modeling or flight trajectory). RTR Simulator models the **DECISION-MAKING PROCESS** of humans in a command chain: who sees what, who tells whom, who decides what, and how long the response chain takes to resolve.

**How it works:**
1. **Each agent** (commander, sensor, response team) receives information based on their role and position
2. **Different configurations** = different information. No drone → must send personnel to visually verify. With drone → real-time aerial imagery
3. **Each scenario** runs multiple times (50 runs) with ±20% random variance to produce statistical distributions
4. **KPIs** (Key Performance Indicators) measure time for each phase: Detection → Verification → Decision → Response → Resolution

**Comparison configurations:**
- **Config 1 (no drone):** Fixed sensors, radio, and human patrols only
- **Config 2 (basic drone):** Add 1 tethered drone providing continuous overhead imagery
- **Config 3 (full system):** Tethered drone + rapid-response drones deployable in 45 seconds

**Limitations:** Simulation based on statistical models, not field observation. Recommend validation through live rehearsal.`
};

// ═══════════════════════════════════════════════════════════
// MAIN GENERATOR
// ═══════════════════════════════════════════════════════════

function generateSection(data, meta, lang) {
  const lines = [];
  const masterKpi = data.master_kpi || {};
  const configs = Object.keys(masterKpi);
  const firstCfg = configs[0] || "BASELINE";
  const lastCfg = configs[configs.length - 1] || "FULL";
  const scenarios = data.scenarios || [];
  const totalRuns = data.total_runs || 0;

  const isVi = lang === "vi";
  const moduleName = meta?.name?.[lang] || meta?.name?.en || "RTR Simulation";
  const moduleDesc = meta?.desc?.[lang] || meta?.desc?.en || "";

  // ── TITLE ──
  lines.push(`# ${moduleName}`);
  lines.push(`### ${isVi ? "Báo cáo Kết quả Mô phỏng" : "Simulation Evidence Report"}`);
  lines.push("");
  if (moduleDesc) lines.push(`> ${moduleDesc}`);
  lines.push("");

  // ── EXECUTIVE SUMMARY ──
  lines.push(`## ${isVi ? "1. Tóm tắt" : "1. Executive Summary"}`);
  lines.push("");

  const baseline = masterKpi[firstCfg] || {};
  const best = masterKpi[lastCfg] || {};

  lines.push(isVi
    ? `Qua **${totalRuns.toLocaleString()} lần mô phỏng** trên **${scenarios.length} kịch bản**, so sánh **${configs.length} cấu hình** (${configs.join(" / ")}), hệ thống drone cho thấy cải thiện đáng kể:`
    : `Across **${totalRuns.toLocaleString()} simulation runs** on **${scenarios.length} scenarios**, comparing **${configs.length} configurations** (${configs.join(" / ")}), drone augmentation demonstrates significant improvements:`
  );
  lines.push("");

  for (const kk of KPI_ORDER) {
    const bm = baseline[kk]?.mean || 0;
    const fm = best[kk]?.mean || 0;
    const improvement = imp(bm, fm);
    if (bm > 0) {
      lines.push(`- **${kpiLabel(kk, lang)}:** ${fmtNum(bm)}s → ${fmtNum(fm)}s (**-${improvement}%**)`);
    }
  }
  lines.push("");

  // ── METHODOLOGY ──
  lines.push(`## ${isVi ? "2. Phương pháp Mô phỏng" : "2. Simulation Methodology"}`);
  lines.push("");
  lines.push(METHODOLOGY[lang]);
  lines.push("");

  // ── RESULTS BY CATEGORY ──
  const categories = {};
  for (const sc of scenarios) {
    const cat = sc.category || "general";
    (categories[cat] = categories[cat] || []).push(sc);
  }

  let section = 3;
  for (const [catKey, catScenarios] of Object.entries(categories)) {
    const catLabel = CATEGORY_LABELS[catKey]?.[lang] || catKey;
    lines.push(`## ${section}. ${isVi ? "Kết quả — " : "Results — "}${catLabel}`);
    lines.push("");

    // Table header
    const header = `| ${isVi ? "Kịch bản" : "Scenario"} | ${configs.join(" | ")} | ${isVi ? "Cải thiện" : "Improvement"} |`;
    const sep = `|${"-".repeat(30)}|${configs.map(() => "-".repeat(12)).join("|")}|${"-".repeat(14)}|`;
    lines.push(header);
    lines.push(sep);

    for (const sc of catScenarios) {
      const vals = configs.map(c => sc.configs?.[c]?.kpi?.total_resolution?.mean || 0);
      const improvement = imp(vals[0], vals[vals.length - 1]);
      const row = `| ${sc.name?.slice(0, 28) || sc.id} | ${vals.map(v => `${fmtNum(v)}s`).join(" | ")} | **-${improvement}%** |`;
      lines.push(row);
    }
    lines.push("");
    section++;
  }

  // ── KPI MASTER TABLE ──
  lines.push(`## ${section}. ${isVi ? "Tổng hợp KPI" : "KPI Summary"}`);
  lines.push("");
  lines.push(`| KPI | ${firstCfg} | ${lastCfg} | ${isVi ? "Cải thiện" : "Improvement"} |`);
  lines.push(`|${"-".repeat(30)}|${"-".repeat(18)}|${"-".repeat(18)}|${"-".repeat(14)}|`);

  for (const kk of KPI_ORDER) {
    const bk = baseline[kk] || {};
    const fk = best[kk] || {};
    if ((bk.mean || 0) > 0) {
      const improvement = imp(bk.mean, fk.mean);
      lines.push(`| ${kpiLabel(kk, lang)} | ${fmtNum(bk.mean)}s ± ${fmtNum(bk.std)}s | ${fmtNum(fk.mean)}s ± ${fmtNum(fk.std)}s | **-${improvement}%** |`);
    }
  }
  lines.push("");
  section++;

  // ── RECOMMENDATION ──
  lines.push(`## ${section}. ${isVi ? "Khuyến nghị" : "Recommendation"}`);
  lines.push("");
  if (isVi) {
    lines.push("Kết quả mô phỏng **ủng hộ triển khai thử nghiệm thực tế**. Đề xuất 3 giai đoạn:");
    lines.push("");
    lines.push("1. **Giai đoạn 1 — Thiết kế trên bàn:** Diễn tập bàn giấy với đội vận hành sử dụng kết quả mô phỏng");
    lines.push("2. **Giai đoạn 2 — Diễn tập thực tế:** Triển khai drone trong sự kiện không chính thức để hiệu chỉnh");
    lines.push("3. **Giai đoạn 3 — Thử nghiệm trực tiếp:** Triển khai đầy đủ với đo lường KPI thực tế");
  } else {
    lines.push("Simulation evidence **supports proceeding to live pilot**. Proposed 3-phase approach:");
    lines.push("");
    lines.push("1. **Phase 1 — Desktop Design:** Tabletop exercise with operations team using simulation outputs");
    lines.push("2. **Phase 2 — Closed Rehearsal:** Drone deployment during non-critical event for calibration");
    lines.push("3. **Phase 3 — Live Pilot:** Full deployment with real KPI measurement");
  }
  lines.push("");

  return lines.join("\n");
}

/**
 * Generate bilingual report from comparison data.
 * @param {object} comparisonData — { master_kpi, scenarios, total_runs, total_scenarios }
 * @param {string} moduleId — module identifier (e.g. "counter_uas")
 * @param {string} lang — "vi", "en", or "both" (default)
 * @returns {string} — markdown report
 */
export function generateReport(comparisonData, moduleId, lang = "both") {
  const meta = MODULE_META[moduleId] || MODULE_META.stadium_operations;
  const parts = [];

  if (lang === "vi" || lang === "both") {
    parts.push(generateSection(comparisonData, meta, "vi"));
  }

  if (lang === "both") {
    parts.push("\n---\n\n");
  }

  if (lang === "en" || lang === "both") {
    parts.push(generateSection(comparisonData, meta, "en"));
  }

  // Footer
  const now = new Date().toISOString().slice(0, 19).replace("T", " ");
  parts.push(`\n---\n*Generated by RTR Simulator Portal — ${now}*\n`);

  return parts.join("");
}
