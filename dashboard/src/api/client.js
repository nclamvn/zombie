/**
 * MiroFish API Client
 *
 * Wraps all 14 backend endpoints with auto-retry, error normalization,
 * and consistent response handling.
 */

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:5001";

// ─── Core fetch wrapper ──────────────────────────────────────

async function apiCall(method, path, body = null, retries = 2) {
  const url = `${BASE_URL}${path}`;
  const opts = {
    method,
    headers: { "Content-Type": "application/json" },
  };
  if (body) opts.body = JSON.stringify(body);

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const res = await fetch(url, opts);
      const json = await res.json().catch(() => null);

      if (!res.ok) {
        const msg = json?.detail || json?.error || json?.message || `HTTP ${res.status}`;
        if (res.status >= 500 && attempt < retries) {
          await sleep(1000 * Math.pow(3, attempt));
          continue;
        }
        return { status: "error", data: null, error: msg };
      }

      // API returns { status, data, error } — pass through
      if (json && json.status === "ok") return json;
      // Fallback: wrap raw response
      return { status: "ok", data: json, error: null };
    } catch (err) {
      if (attempt < retries) {
        await sleep(1000 * Math.pow(3, attempt));
        continue;
      }
      return { status: "error", data: null, error: err.message || "Network error" };
    }
  }
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

// ─── Health ──────────────────────────────────────────────────

export async function checkHealth() {
  return apiCall("GET", "/health");
}

// ─── Project CRUD ────────────────────────────────────────────

export async function createProject(name, requirement, text) {
  return apiCall("POST", "/api/projects", { name, requirement, text });
}

export async function listProjects() {
  return apiCall("GET", "/api/projects");
}

export async function getProject(projectId) {
  return apiCall("GET", `/api/projects/${projectId}`);
}

// ─── Pipeline Stages ─────────────────────────────────────────

export async function triggerOntology(projectId) {
  return apiCall("POST", `/api/projects/${projectId}/ontology`);
}

export async function triggerGraph(projectId) {
  return apiCall("POST", `/api/projects/${projectId}/graph`);
}

export async function getGraph(projectId) {
  return apiCall("GET", `/api/projects/${projectId}/graph`);
}

export async function triggerSimulation(projectId) {
  return apiCall("POST", `/api/projects/${projectId}/simulate`);
}

export async function getSimulation(projectId) {
  return apiCall("GET", `/api/projects/${projectId}/simulation`);
}

export async function getAgents(projectId) {
  return apiCall("GET", `/api/projects/${projectId}/agents`);
}

// ─── Report & Chat ───────────────────────────────────────────

export async function triggerReport(projectId) {
  return apiCall("POST", `/api/projects/${projectId}/report`);
}

export async function getReport(projectId) {
  return apiCall("GET", `/api/projects/${projectId}/report`);
}

export async function chat(projectId, message) {
  return apiCall("POST", `/api/projects/${projectId}/chat`, { message });
}

// ─── Full Pipeline ───────────────────────────────────────────

export async function runFullPipeline(name, requirement, text) {
  return apiCall("POST", "/api/predict", { name, requirement, text });
}

// ─── Streaming Pipeline (SSE) ────────────────────────────────

/**
 * Start pipeline via SSE streaming endpoint.
 * 1. Create project
 * 2. POST /run-stream to start pipeline in background
 * 3. Subscribe to GET /stream for real-time progress
 *
 * onEvent(type, data) called for every SSE event.
 * Returns { projectId, close() }
 */
export async function runPipelineStreaming(name, requirement, text, onEvent) {
  // Step 1: Create project
  onEvent?.("progress", { stage: "seed", step: 0, total_steps: 5, progress: 0, message: "Creating project..." });
  const r1 = await createProject(name, requirement, text);
  if (r1.status !== "ok") {
    onEvent?.("error", { message: r1.error, stage: "seed" });
    return { error: r1.error };
  }
  const projectId = r1.data.project_id;

  // Step 2: Subscribe to SSE stream
  const streamUrl = `${BASE_URL}/api/projects/${projectId}/stream`;
  let es = null;

  try {
    es = new EventSource(streamUrl);
  } catch (err) {
    // EventSource not supported or URL issue — fall back to sequential
    return runPipelineStepsFallback(projectId, onEvent);
  }

  const closeStream = () => {
    if (es) { es.close(); es = null; }
  };

  // Set up SSE event listeners
  const eventTypes = ["progress", "stage_complete", "round", "complete", "error", "connected", "ping"];
  for (const type of eventTypes) {
    es.addEventListener(type, (e) => {
      try {
        const data = JSON.parse(e.data);
        onEvent?.(type, data);
      } catch {}
    });
  }
  es.onerror = () => {
    // EventSource auto-reconnects, but notify UI
    onEvent?.("error", { message: "Stream connection lost — reconnecting...", stage: "stream" });
  };

  // Step 3: Trigger the streaming pipeline
  const r2 = await apiCall("POST", `/api/projects/${projectId}/run-stream`);
  if (r2.status !== "ok") {
    closeStream();
    onEvent?.("error", { message: r2.error, stage: "start" });
    return { projectId, error: r2.error, close: closeStream };
  }

  return { projectId, close: closeStream };
}

/**
 * Fallback: run pipeline stages sequentially (no SSE).
 * Used when EventSource is not available.
 */
async function runPipelineStepsFallback(projectId, onEvent) {
  const stages = [
    { label: "Designing ontology...", fn: () => triggerOntology(projectId) },
    { label: "Building knowledge graph...", fn: () => triggerGraph(projectId) },
    { label: "Running simulation...", fn: () => triggerSimulation(projectId) },
    { label: "Generating report...", fn: () => triggerReport(projectId) },
  ];

  for (let i = 0; i < stages.length; i++) {
    onEvent?.("progress", { stage: stages[i].label, step: i + 1, total_steps: 5, progress: (i + 1) / 5, message: stages[i].label });
    const r = await stages[i].fn();
    if (r.status !== "ok") {
      onEvent?.("error", { message: r.error, stage: stages[i].label });
      return { projectId, error: r.error };
    }
    onEvent?.("stage_complete", { stage: stages[i].label });
  }

  onEvent?.("complete", { project_id: projectId, report_available: true });
  return { projectId, close: () => {} };
}

// ─── Legacy step-by-step (kept for backward compat) ──────────

export async function runPipelineSteps(name, requirement, text, onProgress) {
  return runPipelineStreaming(name, requirement, text, (type, data) => {
    if (type === "progress") {
      onProgress?.(data.step || 0, data.total_steps || 5, data.message || "");
    } else if (type === "complete") {
      onProgress?.(5, 5, "Complete!");
    }
  });
}
