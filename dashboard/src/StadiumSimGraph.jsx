import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { THEMES } from "./theme.js";

// Dynamic palette — resolved per render from themeId prop
function getC(themeId) {
  const T = THEMES[themeId] || THEMES.dark;
  return {
    bg: T.bg0, bgCard: T.bg1, bgHover: T.bg2,
    border: T.border, borderActive: T.borderHi,
    amber: T.amber, amberDim: T.amberDim, amberGlow: T.amberGlow,
    green: T.green, greenDim: T.greenDim, greenGlow: T.greenGlow,
    red: T.red, redDim: T.redDim, redGlow: T.redGlow,
    blue: T.blue, blueDim: T.blueDim, blueGlow: T.blueGlow,
    cyan: T.cyan, cyanDim: T.cyanDim, cyanGlow: T.cyanGlow,
    purple: T.purple, purpleDim: T.purpleDim,
    text: T.text0, textDim: T.text2, textMid: T.text1,
    gridOpacity: T.gridOpacity, pitchFill: T.pitchFill,
  };
}
function getPHASE(C) { return { detect: C.amber, verify: C.blue, decide: C.cyan, respond: C.green, resolve: C.purple }; }
function getCAT(C) { return { crowd: C.amber, medical: C.red, security: C.blue, environmental: C.green, operational: C.textDim }; }

// Module-level refs updated by main component each render — allows sub-components to read current theme
let C = getC("dark");
let PHASE_COLORS = getPHASE(C);
let CAT_COLORS = getCAT(C);

// ─── Agent Definitions ───────────────────────────────────────
const AGENTS = [
  { id: "voc", label: "VOC", fullName: "Venue Operations Centre", x: 400, y: 180, color: C.amber, authority: 5 },
  { id: "police", label: "POLICE", fullName: "Police Commander", x: 220, y: 100, color: C.red, authority: 5 },
  { id: "safety", label: "SAFETY", fullName: "Safety Officer", x: 580, y: 100, color: C.green, authority: 4 },
  { id: "medical", label: "MEDICAL", fullName: "Medical Coordinator", x: 160, y: 280, color: C.cyan, authority: 3 },
  { id: "fire", label: "FIRE", fullName: "Fire Safety Cmdr", x: 640, y: 280, color: C.red, authority: 3 },
  { id: "drone", label: "DRONE", fullName: "Drone Operator", x: 400, y: 50, color: C.blue, authority: 2 },
  { id: "steward_n", label: "STW-N", fullName: "Steward North", x: 300, y: 360, color: C.purple, authority: 2 },
  { id: "steward_s", label: "STW-S", fullName: "Steward South", x: 500, y: 360, color: C.purple, authority: 2 },
  { id: "cctv", label: "CCTV", fullName: "CCTV Operator", x: 100, y: 180, color: C.textMid, authority: 1 },
];

const EDGES = [
  { from: "drone", to: "voc", type: "video" }, { from: "cctv", to: "voc", type: "video" },
  { from: "police", to: "voc", type: "command" }, { from: "voc", to: "safety", type: "command" },
  { from: "voc", to: "medical", type: "dispatch" }, { from: "voc", to: "fire", type: "command" },
  { from: "voc", to: "steward_n", type: "command" }, { from: "voc", to: "steward_s", type: "command" },
  { from: "steward_n", to: "voc", type: "report" }, { from: "steward_s", to: "voc", type: "report" },
  { from: "drone", to: "police", type: "video" },
  { from: "safety", to: "steward_n", type: "command" }, { from: "safety", to: "steward_s", type: "command" },
];

// ─── All 12 Scenarios ────────────────────────────────────────
const SCENARIOS = [
  {
    id: "CROWD-001", name: "Gate congestion — peak ingress", category: "crowd", severity: "high", color: C.amber,
    incidentPos: { x: 320, y: 440 }, incidentLabel: "Gate B congestion",
    chain: [
      { agent: "steward_s", action: "Reports crowding at Gate B", delay: 0, phase: "detect" },
      { agent: "cctv", action: "Camera 23 confirms density rising", delay: 1500, phase: "detect" },
      { agent: "voc", action: "Receives reports, checking feeds", delay: 3000, phase: "verify" },
      { agent: "drone", action: "Repositioning for overhead view", delay: 3500, phase: "verify", droneOnly: true },
      { agent: "voc", action: "Confirms 4.2 p/m² — AMBER", delay: 5000, phase: "decide" },
      { agent: "safety", action: "Orders redirect to Gate C", delay: 6500, phase: "decide" },
      { agent: "steward_s", action: "Executing crowd redirect", delay: 8000, phase: "respond" },
      { agent: "voc", action: "PA announcement: use Gate C", delay: 9000, phase: "respond" },
      { agent: "drone", action: "Monitoring density decrease", delay: 10500, phase: "resolve", droneOnly: true },
      { agent: "voc", action: "Situation resolved — GREEN", delay: 13000, phase: "resolve" },
    ],
  },
  {
    id: "CROWD-002", name: "Halftime concourse crush risk", category: "crowd", severity: "critical", color: C.amber,
    incidentPos: { x: 350, y: 380 }, incidentLabel: "North Concourse crush",
    chain: [
      { agent: "steward_n", action: "Reports crowd stalling near food kiosks", delay: 0, phase: "detect" },
      { agent: "steward_n", action: "Second report: crowd agitated", delay: 1200, phase: "detect" },
      { agent: "voc", action: "Two steward reports — checking CCTV", delay: 2500, phase: "verify" },
      { agent: "drone", action: "Repositioning to North Concourse", delay: 2800, phase: "verify", droneOnly: true },
      { agent: "drone", action: "Overhead: 5.0+ p/m² confirmed", delay: 4000, phase: "verify", droneOnly: true },
      { agent: "voc", action: "Classifies RED — crush risk", delay: 5500, phase: "decide" },
      { agent: "medical", action: "Medical team on standby", delay: 6000, phase: "decide" },
      { agent: "safety", action: "Partial section lockdown ordered", delay: 7000, phase: "decide" },
      { agent: "voc", action: "PA: redirect to South Concourse", delay: 8000, phase: "respond" },
      { agent: "steward_n", action: "Managing flow at chokepoint", delay: 9000, phase: "respond" },
      { agent: "drone", action: "Density dropping — 3.2 p/m²", delay: 11000, phase: "resolve", droneOnly: true },
      { agent: "voc", action: "Crush risk mitigated — AMBER", delay: 13000, phase: "resolve" },
    ],
  },
  {
    id: "CROWD-003", name: "Post-match egress bottleneck", category: "crowd", severity: "high", color: C.amber,
    incidentPos: { x: 480, y: 450 }, incidentLabel: "South exit bottleneck",
    chain: [
      { agent: "drone", action: "Tethered drone spots narrowing at South exit", delay: 0, phase: "detect", droneOnly: true },
      { agent: "steward_s", action: "Reports barrier blocking corridor", delay: 2500, phase: "detect" },
      { agent: "voc", action: "Checking South exit feeds", delay: 3500, phase: "verify" },
      { agent: "drone", action: "Confirms: barrier + 15K funneling", delay: 4000, phase: "verify", droneOnly: true },
      { agent: "voc", action: "Dispatches steward team to remove barrier", delay: 5500, phase: "decide" },
      { agent: "police", action: "Redirecting vehicle traffic from P3", delay: 6500, phase: "decide" },
      { agent: "steward_s", action: "Removing catering barrier", delay: 7500, phase: "respond" },
      { agent: "drone", action: "Monitoring P3 pedestrian-vehicle conflict", delay: 8500, phase: "respond", droneOnly: true },
      { agent: "voc", action: "Flow restored — monitoring", delay: 11000, phase: "resolve" },
    ],
  },
  {
    id: "MED-001", name: "Cardiac arrest in upper tier", category: "medical", severity: "critical", color: C.red,
    incidentPos: { x: 550, y: 440 }, incidentLabel: "East Upper — cardiac",
    chain: [
      { agent: "steward_n", action: "Spectators waving for help in East Upper", delay: 0, phase: "detect" },
      { agent: "drone", action: "Zooming to East Upper — person on ground", delay: 1200, phase: "detect", droneOnly: true },
      { agent: "voc", action: "Alert received — checking CCTV", delay: 2000, phase: "verify" },
      { agent: "voc", action: "Visual confirmed — RED classification", delay: 3500, phase: "verify" },
      { agent: "medical", action: "Paramedic team dispatched", delay: 4500, phase: "decide" },
      { agent: "drone", action: "Guiding medics: stairwell C clear", delay: 5500, phase: "decide", droneOnly: true },
      { agent: "safety", action: "Clearing access route via Gate D", delay: 6500, phase: "respond" },
      { agent: "medical", action: "Paramedic on scene, AED deployed", delay: 8000, phase: "respond" },
      { agent: "voc", action: "Ambulance staged at Gate D", delay: 10000, phase: "respond" },
      { agent: "medical", action: "Patient stabilized — transport ready", delay: 13000, phase: "resolve" },
      { agent: "voc", action: "Incident resolved — logging", delay: 15000, phase: "resolve" },
    ],
  },
  {
    id: "MED-002", name: "Multiple casualties — stand collapse", category: "medical", severity: "critical", color: C.red,
    incidentPos: { x: 460, y: 420 }, incidentLabel: "Stand collapse — MCI",
    chain: [
      { agent: "steward_s", action: "Reports structural distress in temp seating", delay: 0, phase: "detect" },
      { agent: "drone", action: "Immediate deployment for aerial assessment", delay: 800, phase: "detect", droneOnly: true },
      { agent: "voc", action: "Multiple casualty reports incoming", delay: 2000, phase: "verify" },
      { agent: "drone", action: "Confirms: 12 persons fell ~2m, injuries visible", delay: 3000, phase: "verify", droneOnly: true },
      { agent: "medical", action: "Activates MCI protocol", delay: 4000, phase: "decide" },
      { agent: "safety", action: "Evacuating adjacent sections", delay: 5000, phase: "decide" },
      { agent: "fire", action: "Assessing structural integrity", delay: 5500, phase: "decide" },
      { agent: "police", action: "Considering primacy transfer", delay: 6500, phase: "decide" },
      { agent: "medical", action: "Triage teams deployed to scene", delay: 7500, phase: "respond" },
      { agent: "voc", action: "Ambulance staging area activated at P2", delay: 9000, phase: "respond" },
      { agent: "safety", action: "Adjacent sections cleared", delay: 11000, phase: "respond" },
      { agent: "medical", action: "All patients triaged — 3 critical", delay: 14000, phase: "resolve" },
      { agent: "voc", action: "MCI under control — external support en route", delay: 16000, phase: "resolve" },
    ],
  },
  {
    id: "SEC-001", name: "Unauthorized perimeter breach", category: "security", severity: "high", color: C.blue,
    incidentPos: { x: 680, y: 400 }, incidentLabel: "East fence breach",
    chain: [
      { agent: "drone", action: "Tethered drone detects movement at East fence", delay: 0, phase: "detect", droneOnly: true },
      { agent: "cctv", action: "No camera coverage — blind spot", delay: 800, phase: "detect" },
      { agent: "voc", action: "Drone alert: 3 persons climbing fence", delay: 1500, phase: "verify" },
      { agent: "police", action: "Assessing threat level", delay: 2500, phase: "verify" },
      { agent: "drone", action: "Rapid-response drone deploying close-up", delay: 3000, phase: "verify", droneOnly: true },
      { agent: "police", action: "Classifies: trespass, not hostile", delay: 4500, phase: "decide" },
      { agent: "voc", action: "Dispatching police ground unit", delay: 5500, phase: "decide" },
      { agent: "steward_n", action: "Blocking internal access from East", delay: 6500, phase: "respond" },
      { agent: "police", action: "Ground unit intercepting", delay: 8000, phase: "respond" },
      { agent: "police", action: "3 persons detained — no threat", delay: 11000, phase: "resolve" },
      { agent: "voc", action: "Perimeter restored — GREEN", delay: 13000, phase: "resolve" },
    ],
  },
  {
    id: "SEC-002", name: "Unattended package — concourse", category: "security", severity: "critical", color: C.blue,
    incidentPos: { x: 250, y: 400 }, incidentLabel: "West Concourse — package",
    chain: [
      { agent: "steward_s", action: "Reports unattended backpack near food court", delay: 0, phase: "detect" },
      { agent: "voc", action: "Notifies Police Commander", delay: 1500, phase: "verify" },
      { agent: "drone", action: "Overhead view without alarming crowd", delay: 2500, phase: "verify", droneOnly: true },
      { agent: "police", action: "Assessing: EOD team alerted", delay: 3500, phase: "verify" },
      { agent: "steward_s", action: "Establishing 30m cordon discreetly", delay: 4500, phase: "decide" },
      { agent: "safety", action: "Preparing partial evacuation — West sector", delay: 5500, phase: "decide" },
      { agent: "police", action: "Decision: evacuate West, wait for EOD", delay: 7000, phase: "decide" },
      { agent: "voc", action: "PA: West sector please move to East", delay: 8000, phase: "respond" },
      { agent: "steward_s", action: "Guiding evacuation — West sector", delay: 9000, phase: "respond" },
      { agent: "police", action: "EOD assessing — item is harmless bag", delay: 13000, phase: "resolve" },
      { agent: "voc", action: "All clear — resuming normal ops", delay: 15000, phase: "resolve" },
    ],
  },
  {
    id: "SEC-003", name: "Unauthorized drone detected", category: "security", severity: "high", color: C.blue,
    incidentPos: { x: 500, y: 60 }, incidentLabel: "Unauthorized UAV",
    chain: [
      { agent: "voc", action: "RF scanner: unknown drone at 800m NE", delay: 0, phase: "detect" },
      { agent: "drone", action: "Authorized drones RTB — avoid misidentification", delay: 1200, phase: "detect", droneOnly: true },
      { agent: "police", action: "Counter-drone system classifying signal", delay: 2000, phase: "verify" },
      { agent: "voc", action: "Confirmed unauthorized — not in fleet", delay: 3000, phase: "verify" },
      { agent: "police", action: "Activating counter-drone response", delay: 4000, phase: "decide" },
      { agent: "voc", action: "Grounding all authorized drones", delay: 4500, phase: "decide" },
      { agent: "police", action: "RF jamming initiated", delay: 6000, phase: "respond" },
      { agent: "safety", action: "Standby: shelter-in-place if drone enters airspace", delay: 7000, phase: "respond" },
      { agent: "police", action: "Drone signal lost — jammed successfully", delay: 10000, phase: "resolve" },
      { agent: "voc", action: "Threat neutralized — resuming drone ops", delay: 12000, phase: "resolve" },
    ],
  },
  {
    id: "ENV-001", name: "Severe weather — lightning", category: "environmental", severity: "high", color: C.green,
    incidentPos: { x: 400, y: 300 }, incidentLabel: "Lightning warning",
    chain: [
      { agent: "voc", action: "Weather service: lightning within 15 min", delay: 0, phase: "detect" },
      { agent: "drone", action: "Grounding all drone units immediately", delay: 800, phase: "detect", droneOnly: true },
      { agent: "safety", action: "Activating weather contingency plan", delay: 2000, phase: "verify" },
      { agent: "voc", action: "Match referee consulted on suspension", delay: 3000, phase: "verify" },
      { agent: "voc", action: "Decision: shelter-in-place protocol", delay: 4500, phase: "decide" },
      { agent: "safety", action: "PA: move to covered concourses", delay: 5500, phase: "respond" },
      { agent: "steward_n", action: "Directing spectators to North concourse", delay: 6500, phase: "respond" },
      { agent: "steward_s", action: "Directing spectators to South concourse", delay: 6500, phase: "respond" },
      { agent: "medical", action: "Medical teams on standby", delay: 7500, phase: "respond" },
      { agent: "voc", action: "All sectors sheltered — monitoring weather", delay: 11000, phase: "resolve" },
    ],
  },
  {
    id: "ENV-002", name: "Power failure — partial blackout", category: "environmental", severity: "moderate", color: C.green,
    incidentPos: { x: 600, y: 350 }, incidentLabel: "East sector blackout",
    chain: [
      { agent: "voc", action: "East sector power loss detected", delay: 0, phase: "detect" },
      { agent: "cctv", action: "East sector cameras offline", delay: 500, phase: "detect" },
      { agent: "voc", action: "Emergency lighting active — CCTV blind", delay: 1500, phase: "verify" },
      { agent: "drone", action: "Repositioning to cover East blind spots", delay: 2000, phase: "verify", droneOnly: true },
      { agent: "fire", action: "Checking fire panel status", delay: 3000, phase: "verify" },
      { agent: "voc", action: "Dispatching generator team", delay: 4000, phase: "decide" },
      { agent: "steward_n", action: "Deploying with flashlights in East", delay: 5000, phase: "respond" },
      { agent: "drone", action: "Thermal camera covering East sector", delay: 5500, phase: "respond", droneOnly: true },
      { agent: "fire", action: "Fire panel on backup — operational", delay: 6500, phase: "respond" },
      { agent: "voc", action: "Power restored — CCTV back online", delay: 10000, phase: "resolve" },
    ],
  },
  {
    id: "OPS-001", name: "VIP motorcade arrival conflict", category: "operational", severity: "moderate", color: "#6b7280",
    incidentPos: { x: 420, y: 450 }, incidentLabel: "South Gate — VIP",
    chain: [
      { agent: "police", action: "VIP security requests South Gate closure", delay: 0, phase: "detect" },
      { agent: "voc", action: "Assessing crowd volume at South Gate", delay: 1500, phase: "verify" },
      { agent: "drone", action: "Real-time queue length: 3,000 queuing", delay: 2000, phase: "verify", droneOnly: true },
      { agent: "safety", action: "Negotiating: VIP via alternate route", delay: 3500, phase: "decide" },
      { agent: "voc", action: "Decision: redirect VIP to VIP Gate", delay: 5000, phase: "decide" },
      { agent: "police", action: "VIP security accepts alternate route", delay: 6000, phase: "respond" },
      { agent: "steward_s", action: "Managing queue expectations", delay: 7000, phase: "respond" },
      { agent: "voc", action: "South Gate uninterrupted — resolved", delay: 9000, phase: "resolve" },
    ],
  },
  {
    id: "OPS-002", name: "Pre-event sweep — suspicious vehicle", category: "operational", severity: "moderate", color: "#6b7280",
    incidentPos: { x: 280, y: 420 }, incidentLabel: "North loading dock",
    chain: [
      { agent: "drone", action: "Pre-event sweep: unregistered vehicle at North dock", delay: 0, phase: "detect", droneOnly: true },
      { agent: "cctv", action: "Checking loading dock cameras — poor lighting", delay: 1500, phase: "detect" },
      { agent: "voc", action: "Drone imagery received — running plates", delay: 2500, phase: "verify" },
      { agent: "police", action: "Dispatching ground unit to investigate", delay: 3500, phase: "verify" },
      { agent: "cctv", action: "Reviewing footage for arrival time", delay: 4500, phase: "verify" },
      { agent: "police", action: "Vehicle is catering delivery — logistics error", delay: 6000, phase: "decide" },
      { agent: "voc", action: "Requesting vehicle removal", delay: 7000, phase: "respond" },
      { agent: "police", action: "Vehicle removed and logged", delay: 9000, phase: "resolve" },
      { agent: "voc", action: "Sweep continues — area clear", delay: 10000, phase: "resolve" },
    ],
  },
];

// ─── Per-scenario real KPI data (from 1800 runs aggregation) ─
const SCENARIO_KPIS = {
  "CROWD-001": { det: { b: 60, d: 12 }, ver: { b: 176, d: 39 }, dec: { b: 46, d: 20 }, res: { b: 120, d: 84 }, tot: { b: 797, d: 400 } },
  "CROWD-002": { det: { b: 60, d: 25 }, ver: { b: 176, d: 55 }, dec: { b: 55, d: 24 }, res: { b: 120, d: 84 }, tot: { b: 1005, d: 504 } },
  "CROWD-003": { det: { b: 60, d: 12 }, ver: { b: 176, d: 39 }, dec: { b: 46, d: 20 }, res: { b: 120, d: 84 }, tot: { b: 700, d: 350 } },
  "MED-001": { det: { b: 60, d: 25 }, ver: { b: 176, d: 55 }, dec: { b: 55, d: 24 }, res: { b: 120, d: 84 }, tot: { b: 1005, d: 504 } },
  "MED-002": { det: { b: 60, d: 25 }, ver: { b: 176, d: 55 }, dec: { b: 55, d: 24 }, res: { b: 120, d: 84 }, tot: { b: 1070, d: 538 } },
  "SEC-001": { det: { b: 60, d: 25 }, ver: { b: 176, d: 55 }, dec: { b: 46, d: 20 }, res: { b: 120, d: 84 }, tot: { b: 700, d: 350 } },
  "SEC-002": { det: { b: 60, d: 25 }, ver: { b: 176, d: 55 }, dec: { b: 55, d: 24 }, res: { b: 120, d: 84 }, tot: { b: 1005, d: 504 } },
  "SEC-003": { det: { b: 60, d: 25 }, ver: { b: 176, d: 55 }, dec: { b: 46, d: 20 }, res: { b: 120, d: 84 }, tot: { b: 700, d: 350 } },
  "ENV-001": { det: { b: 60, d: 25 }, ver: { b: 176, d: 55 }, dec: { b: 46, d: 20 }, res: { b: 120, d: 84 }, tot: { b: 700, d: 350 } },
  "ENV-002": { det: { b: 60, d: 25 }, ver: { b: 176, d: 39 }, dec: { b: 36, d: 16 }, res: { b: 120, d: 84 }, tot: { b: 550, d: 290 } },
  "OPS-001": { det: { b: 60, d: 12 }, ver: { b: 176, d: 39 }, dec: { b: 36, d: 16 }, res: { b: 120, d: 84 }, tot: { b: 550, d: 290 } },
  "OPS-002": { det: { b: 60, d: 12 }, ver: { b: 176, d: 39 }, dec: { b: 36, d: 16 }, res: { b: 120, d: 84 }, tot: { b: 550, d: 290 } },
};

// ─── Sub-components ──────────────────────────────────────────

function Particle({ from, to, color, progress }) {
  const x = from.x + (to.x - from.x) * progress;
  const y = from.y + (to.y - from.y) * progress;
  return (
    <g>
      <circle cx={x} cy={y} r={6} fill={color} opacity={0.12} />
      <circle cx={x} cy={y} r={3} fill={color} opacity={0.4} />
      <circle cx={x} cy={y} r={2} fill={color} opacity={0.9} />
    </g>
  );
}

function AgentNode({ agent, isActive, pulseColor, statusText, dimmed }) {
  const glow = isActive ? (pulseColor || agent.color) : "transparent";
  const opacity = dimmed ? 0.15 : 1;
  return (
    <g style={{ opacity, transition: "opacity 0.4s" }}>
      <circle cx={agent.x} cy={agent.y} r={32} fill={glow} opacity={isActive ? 0.12 : 0} />
      <circle cx={agent.x} cy={agent.y} r={24} fill={C.bgCard} stroke={isActive ? glow : C.border} strokeWidth={isActive ? 2 : 1} />
      {isActive && <circle cx={agent.x} cy={agent.y} r={24} fill="none" stroke={glow} strokeWidth={2} opacity={0.6}>
        <animate attributeName="r" values="24;30;24" dur="1.5s" repeatCount="indefinite" />
        <animate attributeName="opacity" values="0.6;0.1;0.6" dur="1.5s" repeatCount="indefinite" />
      </circle>}
      <text x={agent.x} y={agent.y - 2} textAnchor="middle" dominantBaseline="central" fill={isActive ? "#fff" : C.textMid} fontSize={9} fontWeight={600} fontFamily="'JetBrains Mono',monospace" letterSpacing="0.5">{agent.label}</text>
      <text x={agent.x} y={agent.y + 10} textAnchor="middle" fill={C.textDim} fontSize={7} fontFamily="'JetBrains Mono',monospace">{`LV${agent.authority}`}</text>
      {statusText && (
        <g>
          <rect x={agent.x - 60} y={agent.y + 30} width={120} height={18} rx={4} fill={C.bgCard} stroke={glow} strokeWidth={0.5} opacity={0.95} />
          <text x={agent.x} y={agent.y + 41} textAnchor="middle" fill={glow} fontSize={7} fontFamily="'JetBrains Mono',monospace" opacity={0.9}>
            {statusText.length > 28 ? statusText.slice(0, 28) + "…" : statusText}
          </text>
        </g>
      )}
    </g>
  );
}

function IncidentMarker({ x, y, label, color, active }) {
  if (!active) return null;
  return (
    <g>
      <circle cx={x} cy={y} r={20} fill={color} opacity={0.08}>
        <animate attributeName="r" values="14;30;14" dur="2s" repeatCount="indefinite" />
        <animate attributeName="opacity" values="0.15;0.02;0.15" dur="2s" repeatCount="indefinite" />
      </circle>
      <polygon points={`${x},${y - 10} ${x + 8},${y + 5} ${x - 8},${y + 5}`} fill={color} opacity={0.8}>
        <animate attributeName="opacity" values="0.8;0.4;0.8" dur="1s" repeatCount="indefinite" />
      </polygon>
      <text x={x} y={y + 22} textAnchor="middle" fill={color} fontSize={8} fontFamily="'JetBrains Mono',monospace" fontWeight={600}>{label}</text>
    </g>
  );
}

function PhaseTimeline({ chain, currentStep, droneMode }) {
  const phases = ["detect", "verify", "decide", "respond", "resolve"];
  const filtered = chain.filter(c => droneMode || !c.droneOnly);
  const activePhase = currentStep >= 0 && currentStep < filtered.length ? filtered[currentStep]?.phase : null;
  return (
    <div style={{ display: "flex", gap: 2 }}>
      {phases.map(p => {
        const isActive = p === activePhase;
        const isPast = activePhase && phases.indexOf(p) < phases.indexOf(activePhase);
        return <div key={p} style={{ flex: 1, height: 4, borderRadius: 2, background: isPast ? PHASE_COLORS[p] : isActive ? PHASE_COLORS[p] : C.border, opacity: isPast ? 0.6 : isActive ? 1 : 0.3, transition: "all 0.5s" }} />;
      })}
    </div>
  );
}

// ─── Simulation Engine Hook ──────────────────────────────────
function useSimEngine(scenario, droneMode, speed) {
  const [step, setStep] = useState(-1);
  const [playing, setPlaying] = useState(false);
  const [particles, setParticles] = useState([]);
  const [finished, setFinished] = useState(false);
  const timerRef = useRef(null);
  const particleRef = useRef(null);

  const chain = useMemo(() => scenario.chain.filter(c => droneMode || !c.droneOnly), [scenario, droneMode]);

  const activeAgents = useMemo(() => {
    if (step < 0) return {};
    const map = {};
    for (let i = 0; i <= Math.min(step, chain.length - 1); i++) {
      const c = chain[i];
      map[c.agent] = { action: c.action, phase: c.phase, color: PHASE_COLORS[c.phase] };
    }
    return map;
  }, [step, chain]);

  const activeEdges = useMemo(() => {
    if (step < 0) return new Set();
    const set = new Set();
    for (let i = 0; i <= Math.min(step, chain.length - 1); i++) {
      const ag = chain[i].agent;
      EDGES.forEach(e => { if (e.from === ag || e.to === ag) set.add(`${e.from}-${e.to}`); });
    }
    return set;
  }, [step, chain]);

  const start = useCallback(() => {
    setStep(-1); setPlaying(true); setParticles([]); setFinished(false);
    let s = 0;
    const filtered = scenario.chain.filter(c => droneMode || !c.droneOnly);
    if (timerRef.current) clearTimeout(timerRef.current);
    const advance = () => {
      if (s >= filtered.length) { setPlaying(false); setFinished(true); return; }
      setStep(s);
      const curr = filtered[s];
      const nextDelay = s < filtered.length - 1 ? (filtered[s + 1].delay - curr.delay) / speed : 2000 / speed;
      const fromAgent = AGENTS.find(a => a.id === curr.agent);
      const voc = AGENTS.find(a => a.id === "voc");
      if (fromAgent && voc && fromAgent.id !== "voc") {
        const pid = Date.now() + Math.random();
        setParticles(prev => [...prev, { id: pid, from: fromAgent, to: voc, color: PHASE_COLORS[curr.phase], start: Date.now(), duration: 800 }]);
      }
      s++;
      timerRef.current = setTimeout(advance, Math.max(nextDelay, 400));
    };
    timerRef.current = setTimeout(advance, 500 / speed);
  }, [scenario, droneMode, speed]);

  const reset = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    setPlaying(false); setStep(-1); setParticles([]); setFinished(false);
  }, []);

  useEffect(() => {
    const anim = () => {
      setParticles(prev => prev.filter(p => Date.now() - p.start < p.duration));
      particleRef.current = requestAnimationFrame(anim);
    };
    particleRef.current = requestAnimationFrame(anim);
    return () => { cancelAnimationFrame(particleRef.current); if (timerRef.current) clearTimeout(timerRef.current); };
  }, []);

  // Reset when scenario changes
  useEffect(() => { reset(); }, [scenario.id]);

  return { step, playing, finished, particles, chain, activeAgents, activeEdges, start, reset };
}

// ─── Graph View (with zoom/pan) ──────────────────────────────
function GraphView({ scenario, droneMode, engine, label }) {
  const { step, particles, activeAgents, activeEdges } = engine;
  const containerRef = useRef(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const dragStart = useRef({ x: 0, y: 0, panX: 0, panY: 0 });

  const handleWheel = useCallback((e) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    setZoom(z => Math.max(0.5, Math.min(3, z * delta)));
  }, []);

  const handleMouseDown = useCallback((e) => {
    if (e.button !== 0) return;
    setDragging(true);
    dragStart.current = { x: e.clientX, y: e.clientY, panX: pan.x, panY: pan.y };
  }, [pan]);

  const handleMouseMove = useCallback((e) => {
    if (!dragging) return;
    setPan({ x: dragStart.current.panX + (e.clientX - dragStart.current.x), y: dragStart.current.panY + (e.clientY - dragStart.current.y) });
  }, [dragging]);

  const handleMouseUp = useCallback(() => setDragging(false), []);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    el.addEventListener("wheel", handleWheel, { passive: false });
    return () => el.removeEventListener("wheel", handleWheel);
  }, [handleWheel]);

  const resetView = () => { setZoom(1); setPan({ x: 0, y: 0 }); };

  return (
    <div ref={containerRef} style={{ position: "relative", width: "100%", height: "100%", overflow: "hidden", cursor: dragging ? "grabbing" : "grab" }}
      onMouseDown={handleMouseDown} onMouseMove={handleMouseMove} onMouseUp={handleMouseUp} onMouseLeave={handleMouseUp}>
      {/* Label + zoom controls */}
      <div style={{ position: "absolute", top: 4, left: 6, zIndex: 2, display: "flex", alignItems: "center", gap: 4 }}>
        {label && (
          <span style={{ fontSize: 9, fontWeight: 700, color: droneMode ? C.blue : C.textDim, letterSpacing: 1, background: C.bgCard + "ee", padding: "2px 6px", borderRadius: 3, border: `1px solid ${droneMode ? C.blue + "44" : C.border}` }}>
            {label}
          </span>
        )}
      </div>
      <div style={{ position: "absolute", top: 4, right: 6, zIndex: 2, display: "flex", gap: 2 }}>
        <button onClick={() => setZoom(z => Math.min(3, z * 1.2))} style={{ background: C.bgCard + "dd", border: `1px solid ${C.border}`, borderRadius: 3, width: 20, height: 20, color: C.textMid, fontSize: 11, cursor: "pointer", fontFamily: "inherit", display: "flex", alignItems: "center", justifyContent: "center" }}>+</button>
        <button onClick={() => setZoom(z => Math.max(0.5, z * 0.8))} style={{ background: C.bgCard + "dd", border: `1px solid ${C.border}`, borderRadius: 3, width: 20, height: 20, color: C.textMid, fontSize: 11, cursor: "pointer", fontFamily: "inherit", display: "flex", alignItems: "center", justifyContent: "center" }}>−</button>
        <button onClick={resetView} style={{ background: C.bgCard + "dd", border: `1px solid ${C.border}`, borderRadius: 3, height: 20, padding: "0 5px", color: C.textDim, fontSize: 7, cursor: "pointer", fontFamily: "inherit" }}>FIT</button>
      </div>
      <svg viewBox="0 0 800 480" style={{ width: "100%", height: "100%", display: "block", transform: `scale(${zoom}) translate(${pan.x / zoom}px, ${pan.y / zoom}px)`, transformOrigin: "center center", transition: dragging ? "none" : "transform 0.15s" }}>
        <defs>
          <pattern id={`grid-${label || "main"}`} width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke={C.border} strokeWidth="0.3" opacity="0.3" />
          </pattern>
        </defs>
        <rect width="800" height="480" fill={`url(#grid-${label || "main"})`} />
        <ellipse cx="400" cy="340" rx="160" ry="100" fill="none" stroke={C.border} strokeWidth={1} strokeDasharray="4 4" opacity={0.4} />
        <ellipse cx="400" cy="340" rx="80" ry="50" fill={C.greenDim} stroke={C.green} strokeWidth={0.5} opacity={0.3} />
        <text x="400" y="344" textAnchor="middle" fill={C.textDim} fontSize={8} fontFamily="'JetBrains Mono',monospace">PITCH</text>
        {[{ l: "GATE A", x: 250, y: 260 }, { l: "GATE B", x: 320, y: 438 }, { l: "GATE C", x: 480, y: 438 }, { l: "GATE D", x: 550, y: 260 }].map(g => (
          <text key={g.l} x={g.x} y={g.y} textAnchor="middle" fill={C.textDim} fontSize={7} fontFamily="'JetBrains Mono',monospace" opacity={0.5}>{g.l}</text>
        ))}
        {EDGES.map(e => {
          const key = `${e.from}-${e.to}`;
          const a = AGENTS.find(n => n.id === e.from), b = AGENTS.find(n => n.id === e.to);
          if (!a || !b) return null;
          const isActive = activeEdges.has(key);
          const aData = activeAgents[e.from] || activeAgents[e.to];
          return <line key={key} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke={isActive ? (aData?.color || C.textDim) : C.border} strokeWidth={isActive ? 1.5 : 0.5} opacity={isActive ? 0.6 : 0.2} strokeDasharray={isActive ? "none" : "3 6"} />;
        })}
        {particles.map(p => {
          const progress = Math.min((Date.now() - p.start) / p.duration, 1);
          return <Particle key={p.id} from={p.from} to={p.to} color={p.color} progress={progress} />;
        })}
        {AGENTS.map(a => {
          const data = activeAgents[a.id];
          if (a.id === "drone" && !droneMode) {
            return (
              <g key={a.id} opacity={0.15}>
                <circle cx={a.x} cy={a.y} r={24} fill={C.bgCard} stroke={C.border} strokeWidth={0.5} strokeDasharray="3 3" />
                <text x={a.x} y={a.y} textAnchor="middle" dominantBaseline="central" fill={C.textDim} fontSize={8} fontFamily="'JetBrains Mono',monospace">OFF</text>
              </g>
            );
          }
          return <AgentNode key={a.id} agent={a} isActive={!!data} pulseColor={data?.color} statusText={data?.action} />;
        })}
        <IncidentMarker x={scenario.incidentPos.x} y={scenario.incidentPos.y} label={scenario.incidentLabel} color={scenario.color} active={step >= 0} />
      </svg>
    </div>
  );
}

// ─── Main Component ──────────────────────────────────────────
export default function StadiumSimGraph({ comparisonData, themeId = "dark" }) {
  // Update module-level theme refs so sub-components see current theme
  C = getC(themeId);
  PHASE_COLORS = getPHASE(C);
  CAT_COLORS = getCAT(C);
  const [selectedScenario, setSelectedScenario] = useState(0);
  const [speed, setSpeed] = useState(1);
  const [splitMode, setSplitMode] = useState(false);

  const scenario = SCENARIOS[selectedScenario];

  // Engines: main (drone mode), baseline (no drone) for split view
  const droneEngine = useSimEngine(scenario, true, speed);
  const baselineEngine = useSimEngine(scenario, false, speed);

  // Single mode uses drone engine with toggle
  const [singleDroneMode, setSingleDroneMode] = useState(true);
  const singleEngine = useSimEngine(scenario, singleDroneMode, speed);

  const isPlaying = splitMode ? (droneEngine.playing || baselineEngine.playing) : singleEngine.playing;

  const startBoth = () => {
    if (splitMode) { droneEngine.start(); baselineEngine.start(); }
    else { singleEngine.start(); }
  };
  const resetBoth = () => {
    if (splitMode) { droneEngine.reset(); baselineEngine.reset(); }
    else { singleEngine.reset(); }
  };

  // Resolve KPIs: prefer live comparison data, fallback to static
  const kpis = useMemo(() => {
    if (comparisonData?.scenarios) {
      const sc = comparisonData.scenarios.find(s => s.id === scenario.id);
      if (sc?.configs?.BASELINE?.kpi && sc?.configs?.FULL?.kpi) {
        const b = sc.configs.BASELINE.kpi, f = sc.configs.FULL.kpi;
        return {
          det: { b: Math.round(b.detection_latency?.mean || 60), d: Math.round(f.detection_latency?.mean || 20) },
          ver: { b: Math.round(b.verification_time?.mean || 176), d: Math.round(f.verification_time?.mean || 39) },
          dec: { b: Math.round(b.decision_time?.mean || 46), d: Math.round(f.decision_time?.mean || 20) },
          res: { b: Math.round(b.response_time?.mean || 120), d: Math.round(f.response_time?.mean || 84) },
          tot: { b: Math.round(b.total_resolution?.mean || 797), d: Math.round(f.total_resolution?.mean || 400) },
        };
      }
    }
    return SCENARIO_KPIS[scenario.id] || SCENARIO_KPIS["CROWD-001"];
  }, [comparisonData, scenario.id]);

  const activeEngine = splitMode ? droneEngine : singleEngine;
  const currentAction = activeEngine.step >= 0 && activeEngine.step < activeEngine.chain.length ? activeEngine.chain[activeEngine.step] : null;
  const elapsed = currentAction ? (currentAction.delay / 1000).toFixed(1) : "0.0";

  return (
    <div style={{ fontFamily: "'JetBrains Mono', monospace", background: C.bg, color: C.text, display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 12px", borderBottom: `1px solid ${C.border}`, flexShrink: 0 }}>
        <div>
          <span style={{ color: C.amber, fontWeight: 700, fontSize: 12, letterSpacing: 2 }}>STADIUM OPS</span>
          <span style={{ color: C.textDim, fontSize: 10, marginLeft: 8 }}>LIVE SIMULATION</span>
        </div>
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          {/* Split mode toggle */}
          <button onClick={() => { resetBoth(); setSplitMode(!splitMode); }}
            style={{ background: splitMode ? C.cyanDim : C.bgCard, border: `1px solid ${splitMode ? C.cyan : C.border}`, borderRadius: 4, padding: "4px 10px", color: splitMode ? C.cyan : C.textDim, fontSize: 9, cursor: "pointer", fontFamily: "inherit", fontWeight: 600, letterSpacing: 0.5 }}>
            {splitMode ? "◫ SPLIT VIEW" : "◻ SINGLE VIEW"}
          </button>
          {/* Drone toggle (single mode only) */}
          {!splitMode && (
            <button onClick={() => { singleEngine.reset(); setSingleDroneMode(!singleDroneMode); }}
              style={{ background: singleDroneMode ? C.blueDim : C.bgCard, border: `1px solid ${singleDroneMode ? C.blue : C.border}`, borderRadius: 4, padding: "4px 10px", color: singleDroneMode ? C.blue : C.textDim, fontSize: 9, cursor: "pointer", fontFamily: "inherit", fontWeight: 600 }}>
              {singleDroneMode ? "◉ DRONE ON" : "○ BASELINE"}
            </button>
          )}
          <select value={speed} onChange={e => setSpeed(Number(e.target.value))}
            style={{ background: C.bgCard, border: `1px solid ${C.border}`, borderRadius: 4, padding: "4px 6px", color: C.textMid, fontSize: 9, fontFamily: "inherit", cursor: "pointer" }}>
            <option value={0.5}>0.5×</option><option value={1}>1×</option><option value={2}>2×</option><option value={4}>4×</option>
          </select>
        </div>
      </div>

      {/* Scenario Selector — scrollable horizontal */}
      <div style={{ display: "flex", gap: 3, padding: "6px 12px", borderBottom: `1px solid ${C.border}`, flexShrink: 0, overflowX: "auto", overflowY: "hidden" }}>
        {SCENARIOS.map((s, i) => (
          <button key={s.id} onClick={() => { resetBoth(); setSelectedScenario(i); }}
            style={{ background: selectedScenario === i ? (CAT_COLORS[s.category] || s.color) + "20" : "transparent",
              border: `1px solid ${selectedScenario === i ? (CAT_COLORS[s.category] || s.color) : C.border}`,
              borderRadius: 3, padding: "4px 8px", color: selectedScenario === i ? (CAT_COLORS[s.category] || s.color) : C.textDim,
              fontSize: 8, cursor: "pointer", fontFamily: "inherit", whiteSpace: "nowrap", flexShrink: 0, transition: "all 0.2s" }}>
            {s.id}
          </button>
        ))}
      </div>

      {/* Main content: Graph (left) + Sidebar (right) — fit viewport */}
      <div style={{ flex: 1, display: "flex", gap: 0, minHeight: 0, overflow: "hidden" }}>

        {/* Left: Graph area */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0, borderRight: `1px solid ${C.border}` }}>
          {/* KPI strip */}
          <div style={{ display: "flex", gap: 3, padding: "4px 8px", flexShrink: 0, borderBottom: `1px solid ${C.border}` }}>
            {[
              { label: "DET", b: kpis.det.b, d: kpis.det.d },
              { label: "VER", b: kpis.ver.b, d: kpis.ver.d },
              { label: "DEC", b: kpis.dec.b, d: kpis.dec.d },
              { label: "RSP", b: kpis.res.b, d: kpis.res.d },
              { label: "TOTAL", b: kpis.tot.b, d: kpis.tot.d },
            ].map(k => {
              const imp = k.b > 0 ? Math.round((1 - k.d / k.b) * 100) : 0;
              return (
                <div key={k.label} style={{ background: C.bgCard, border: `1px solid ${C.border}`, borderRadius: 3, padding: "4px 6px", flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 7, color: C.textDim, letterSpacing: 0.5 }}>{k.label}</div>
                  <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
                    <span style={{ fontSize: 14, fontWeight: 700, color: C.green }}>-{imp}%</span>
                    <span style={{ fontSize: 8, color: C.textDim }}>{k.b}→{k.d}s</span>
                  </div>
                </div>
              );
            })}
          </div>
          {/* Graph */}
          <div style={{ flex: 1, display: "flex", gap: 1, padding: 4, minHeight: 0, overflow: "hidden" }}>
            {splitMode ? (
              <>
                <div style={{ flex: 1, border: `1px solid ${C.border}`, borderRadius: 4, overflow: "hidden" }}>
                  <GraphView scenario={scenario} droneMode={false} engine={baselineEngine} label="BASELINE" />
                </div>
                <div style={{ flex: 1, border: `1px solid ${C.blue}33`, borderRadius: 4, overflow: "hidden" }}>
                  <GraphView scenario={scenario} droneMode={true} engine={droneEngine} label="DRONE" />
                </div>
              </>
            ) : (
              <div style={{ flex: 1, border: `1px solid ${C.border}`, borderRadius: 4, overflow: "hidden" }}>
                <GraphView scenario={scenario} droneMode={singleDroneMode} engine={singleEngine} />
              </div>
            )}
          </div>
        </div>

        {/* Right sidebar: Controls + Decision chain */}
        <div style={{ width: 260, flexShrink: 0, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          {/* Run button */}
          <div style={{ padding: 8, borderBottom: `1px solid ${C.border}` }}>
            <button onClick={isPlaying ? resetBoth : startBoth}
              style={{ width: "100%", background: isPlaying ? C.redDim : C.greenDim, border: `1px solid ${isPlaying ? C.red : C.green}`, borderRadius: 3, padding: "8px 0", color: isPlaying ? C.red : C.green, fontSize: 11, fontWeight: 700, cursor: "pointer", fontFamily: "inherit", letterSpacing: 1 }}>
              {isPlaying ? "■ STOP" : "▶ RUN SCENARIO"}
            </button>
            <div style={{ marginTop: 6 }}>
              <PhaseTimeline chain={scenario.chain} currentStep={activeEngine.step} droneMode={splitMode ? true : singleDroneMode} />
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 7, color: C.textDim, marginTop: 2 }}>
                <span>detect</span><span>verify</span><span>decide</span><span>respond</span><span>resolve</span>
              </div>
            </div>
          </div>
          {/* Status */}
          <div style={{ padding: 8, borderBottom: `1px solid ${C.border}`, fontSize: 9 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
              <span style={{ color: C.textDim }}>Elapsed</span>
              <span style={{ fontWeight: 700, color: C.amber }}>{elapsed}s</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
              <span style={{ color: C.textDim }}>Phase</span>
              <span style={{ fontWeight: 600, color: currentAction ? PHASE_COLORS[currentAction.phase] : C.textDim }}>{currentAction?.phase?.toUpperCase() || "STANDBY"}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
              <span style={{ color: C.textDim }}>Step</span>
              <span style={{ color: C.textMid }}>{activeEngine.step >= 0 ? `${activeEngine.step + 1}/${activeEngine.chain.length}` : "—"}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: C.textDim }}>Mode</span>
              <span style={{ color: splitMode ? C.cyan : singleDroneMode ? C.blue : C.textMid }}>
                {splitMode ? "SPLIT" : singleDroneMode ? "DRONE" : "BASELINE"}
              </span>
            </div>
            {splitMode && droneEngine.finished && baselineEngine.finished && (
              <div style={{ marginTop: 6, padding: "4px 6px", background: C.greenDim, borderRadius: 3, textAlign: "center" }}>
                <span style={{ fontSize: 8, color: C.green, fontWeight: 600 }}>
                  DRONE: {(droneEngine.chain[droneEngine.chain.length - 1]?.delay / 1000).toFixed(1)}s vs
                  BASELINE: {(baselineEngine.chain[baselineEngine.chain.length - 1]?.delay / 1000).toFixed(1)}s
                </span>
              </div>
            )}
          </div>
          {/* Decision chain */}
          <div style={{ flex: 1, overflow: "auto", padding: 8 }}>
            <div style={{ fontSize: 8, color: C.textDim, letterSpacing: 1, marginBottom: 6, display: "flex", justifyContent: "space-between" }}>
              <span>{scenario.id}</span>
              <span style={{ color: CAT_COLORS[scenario.category] || C.textDim }}>{scenario.category.toUpperCase()}</span>
            </div>
            <div style={{ fontSize: 9, color: C.textMid, marginBottom: 8 }}>{scenario.name}</div>
            {activeEngine.chain.map((c, i) => {
              const isActive = i === activeEngine.step;
              const isPast = i < activeEngine.step;
              const agent = AGENTS.find(a => a.id === c.agent);
              return (
                <div key={i} style={{ display: "flex", gap: 5, alignItems: "flex-start", padding: "2px 0", opacity: isPast ? 0.45 : isActive ? 1 : 0.15, transition: "opacity 0.4s" }}>
                  <span style={{ fontSize: 8, color: C.textDim, minWidth: 24, textAlign: "right" }}>{(c.delay / 1000).toFixed(1)}s</span>
                  <span style={{ width: 5, height: 5, borderRadius: "50%", background: PHASE_COLORS[c.phase], marginTop: 3, flexShrink: 0, boxShadow: isActive ? `0 0 6px ${PHASE_COLORS[c.phase]}` : "none" }} />
                  <span style={{ fontSize: 8, color: agent?.color || C.textMid, fontWeight: 600, minWidth: 36 }}>{agent?.label}</span>
                  <span style={{ fontSize: 8, color: isActive ? C.text : C.textMid }}>{c.action}{c.droneOnly ? " ✈" : ""}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Footer */}
      <div style={{ padding: "3px 12px", borderTop: `1px solid ${C.border}`, display: "flex", justifyContent: "space-between", fontSize: 8, color: C.textDim, flexShrink: 0 }}>
        <span>MiroFish × RTR — FIFA Stadium Ops · 12 scenarios · scroll to zoom · drag to pan</span>
        <span style={{ color: isPlaying ? C.green : C.textDim }}>{isPlaying ? "● LIVE" : "○ STANDBY"}</span>
      </div>
    </div>
  );
}
