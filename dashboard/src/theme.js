/* ═══════════════════════════════════════════════════════════════
   Global Theme + i18n — Unified across entire dashboard
   Default: Light + Vietnamese
   ═══════════════════════════════════════════════════════════════ */

export const THEMES = {
  light: {
    id: "light",
    bg0: "#f0f2f5", bg1: "#ffffff", bg2: "#f7f8fa", bg3: "#eef1f5",
    border: "#d0d7de", borderHi: "#afb8c1",
    text0: "#1f2328", text1: "#424a53", text2: "#656d76",
    amber: "#bf6a02", amberDim: "rgba(191,106,2,.06)",
    green: "#1a7f37", greenDim: "rgba(26,127,55,.06)",
    red: "#cf222e", redDim: "rgba(207,34,46,.06)",
    blue: "#0969da", blueDim: "rgba(9,105,218,.06)",
    cyan: "#0a7a85", cyanDim: "rgba(10,122,133,.05)",
    purple: "#8250df", purpleDim: "rgba(130,80,223,.06)",
    white: "#ffffff",
    // SimGraph extras
    amberGlow: "rgba(191,106,2,.3)", greenGlow: "rgba(26,127,55,.3)",
    redGlow: "rgba(207,34,46,.3)", blueGlow: "rgba(9,105,218,.3)",
    cyanGlow: "rgba(10,122,133,.3)",
    gridOpacity: .12, pitchFill: "rgba(26,127,55,.06)",
  },
  dark: {
    id: "dark",
    bg0: "#010409", bg1: "#0d1117", bg2: "#161b22", bg3: "#21262d",
    border: "#30363d", borderHi: "#484f58",
    text0: "#f0f6fc", text1: "#d2d8de", text2: "#8b949e",
    amber: "#f0883e", amberDim: "rgba(240,136,62,.12)",
    green: "#3fb950", greenDim: "rgba(63,185,80,.1)",
    red: "#ff7b72", redDim: "rgba(255,123,114,.1)",
    blue: "#58a6ff", blueDim: "rgba(88,166,255,.1)",
    cyan: "#39d2f5", cyanDim: "rgba(57,210,245,.08)",
    purple: "#bc8cff", purpleDim: "rgba(188,140,255,.1)",
    white: "#ffffff",
    // SimGraph extras
    amberGlow: "rgba(240,136,62,.4)", greenGlow: "rgba(63,185,80,.5)",
    redGlow: "rgba(255,123,114,.4)", blueGlow: "rgba(88,166,255,.4)",
    cyanGlow: "rgba(57,210,245,.4)",
    gridOpacity: .3, pitchFill: "rgba(63,185,80,.08)",
  },
};

export const LANG = {
  vi: {
    // Top bar
    title: "TRUNG TÂM MÔ PHỎNG THỰC TẾ",
    connected: "KẾT NỐI", disconnected: "MẤT KẾT NỐI",
    agents: "ĐƠN VỊ", projects: "DỰ ÁN",
    newProject: "+ MỚI",
    backendDown: "Mất kết nối backend — đang thử lại mỗi 5 giây...",

    // Tabs
    overview: "TỔNG QUAN", agentsTab: "ĐƠN VỊ", kGraph: "ĐỒ THỊ TT", events: "SỰ KIỆN", fifa: "FIFA",

    // Sub-tabs FIFA
    commandCenter: "TRUNG TÂM CHỈ HUY", kpiData: "DỮ LIỆU KPI", liveSim: "MÔ PHỎNG",

    // Overview
    simMetrics: "CHỈ SỐ MÔ PHỎNG",
    totalActions: "TỔNG HÀNH ĐỘNG", totalRounds: "TỔNG VÒNG", totalAgents: "TỔNG ĐƠN VỊ",
    contentCreated: "NỘI DUNG", graphNodes: "NÚT ĐỒ THỊ", graphEdges: "CẠNH ĐỒ THỊ",
    eventFeed: "LUỒNG SỰ KIỆN", noEvents: "Chưa có sự kiện — chạy mô phỏng",
    knowledgeGraph: "ĐỒ THỊ TRI THỨC", expand: "MỞ RỘNG",
    entityDist: "PHÂN BỐ THỰC THỂ", noData: "Chưa có dữ liệu",
    noGraphData: "Chưa có đồ thị",
    reportAgent: "TRỢ LÝ BÁO CÁO", react: "REACT",
    askReport: "Hỏi trợ lý...", send: "GỬI",

    // Agents tab
    agentPopulation: "DANH SÁCH ĐƠN VỊ",

    // Events tab
    simRounds: "CÁC VÒNG MÔ PHỎNG", simConfig: "CẤU HÌNH", actionDist: "PHÂN BỐ HÀNH ĐỘNG",
    noRounds: "Chưa có vòng nào", noConfig: "Chưa cấu hình", noDist: "Chưa có dữ liệu",

    // Simulation header
    noProject: "Chưa Chọn Dự Án", round: "VÒNG",

    // FIFA KPI Data
    noComparison: "Chưa có dữ liệu so sánh",
    noComparisonDesc: "Import dữ liệu 1.800 lần chạy hoặc chạy so sánh mới.",
    importJson: "IMPORT JSON", runComparison: "CHẠY SO SÁNH",
    scenarioComparison: "SO SÁNH TÌNH HUỐNG", scenarios: "tình huống",
    exportReport: "XUẤT BÁO CÁO", runs: "LẦN CHẠY",
    kpiPhaseBreakdown: "PHÂN TÍCH GIAI ĐOẠN KPI",
    scenario: "TÌNH HUỐNG", category: "PHÂN LOẠI", improve: "CẢI THIỆN",

    // KPI labels
    detectionLatency: "Phát hiện", verificationTime: "Xác minh",
    decisionTime: "Quyết định", responseTime: "Phản ứng", totalResolution: "Tổng giải quyết",

    // Category labels
    crowd_safety: "ĐÁM ĐÔNG", medical: "Y TẾ", security: "AN NINH",
    environmental: "MÔI TRƯỜNG", operational: "VẬN HÀNH",

    // Status bar
    version: "v1.2", engine: "RTR Simulator — Trung tâm Mô phỏng Thực tế",

    // Controls
    pause: "TẠM DỪNG", resume: "TIẾP TỤC", inject: "TIÊM SỰ KIỆN",

    // Inject modal
    injectEvent: "TIÊM SỰ KIỆN", quickPresets: "MẪU NHANH", eventName: "TÊN SỰ KIỆN",
    eventContent: "NỘI DUNG SỰ KIỆN",
  },
  en: {
    title: "REAL-TIME SIMULATION CENTER",
    connected: "CONNECTED", disconnected: "DISCONNECTED",
    agents: "AGENTS", projects: "PROJECTS",
    newProject: "+ NEW",
    backendDown: "Backend disconnected — retrying every 5s...",

    overview: "OVERVIEW", agentsTab: "AGENTS", kGraph: "K-GRAPH", events: "EVENTS", fifa: "FIFA",

    commandCenter: "COMMAND CENTER", kpiData: "KPI DATA", liveSim: "LIVE SIM",

    simMetrics: "SIMULATION METRICS",
    totalActions: "TOTAL ACTIONS", totalRounds: "TOTAL ROUNDS", totalAgents: "TOTAL AGENTS",
    contentCreated: "CONTENT CREATED", graphNodes: "GRAPH NODES", graphEdges: "GRAPH EDGES",
    eventFeed: "EVENT FEED", noEvents: "No events yet — run a simulation",
    knowledgeGraph: "KNOWLEDGE GRAPH", expand: "EXPAND",
    entityDist: "ENTITY DISTRIBUTION", noData: "No data",
    noGraphData: "No graph data",
    reportAgent: "REPORT AGENT", react: "REACT",
    askReport: "Ask the ReportAgent...", send: "SEND",

    agentPopulation: "AGENT POPULATION",

    simRounds: "SIMULATION ROUNDS", simConfig: "SIMULATION CONFIG", actionDist: "ACTION DISTRIBUTION",
    noRounds: "No rounds yet", noConfig: "No config", noDist: "No distribution data",

    noProject: "No Project Selected", round: "ROUND",

    noComparison: "No comparison data available",
    noComparisonDesc: "Import pre-computed 1,800 runs data or run a new stadium comparison.",
    importJson: "IMPORT JSON", runComparison: "RUN COMPARISON",
    scenarioComparison: "SCENARIO COMPARISON", scenarios: "scenarios",
    exportReport: "EXPORT REPORT", runs: "RUNS",
    kpiPhaseBreakdown: "KPI PHASE BREAKDOWN",
    scenario: "SCENARIO", category: "CATEGORY", improve: "IMPROVE",

    detectionLatency: "Detection Latency", verificationTime: "Verification Time",
    decisionTime: "Decision Time", responseTime: "Response Time", totalResolution: "Total Resolution",

    crowd_safety: "CROWD", medical: "MEDICAL", security: "SECURITY",
    environmental: "ENV", operational: "OPS",

    version: "v1.2", engine: "RTR Simulator — Real-Time Simulation Center",

    pause: "PAUSE", resume: "RESUME", inject: "INJECT",

    injectEvent: "INJECT EVENT", quickPresets: "QUICK PRESETS", eventName: "EVENT NAME",
    eventContent: "EVENT CONTENT",
  },
};
