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

// ─── Step-by-step pipeline runner ────────────────────────────

/**
 * Run pipeline stages sequentially, calling onProgress after each.
 * Returns { projectId, error? }
 */
export async function runPipelineSteps(name, requirement, text, onProgress) {
  const stages = [
    { label: "Creating project...", fn: () => createProject(name, requirement, text) },
    { label: "Designing ontology...", fn: null }, // set after createProject
    { label: "Building knowledge graph...", fn: null },
    { label: "Running simulation...", fn: null },
    { label: "Generating report...", fn: null },
  ];

  // Stage 1: Create project
  onProgress?.(0, 5, stages[0].label);
  const r1 = await stages[0].fn();
  if (r1.status !== "ok") return { error: r1.error };
  const projectId = r1.data.project_id;

  // Stage 2: Ontology
  onProgress?.(1, 5, stages[1].label);
  const r2 = await triggerOntology(projectId);
  if (r2.status !== "ok") return { projectId, error: r2.error };

  // Stage 3: Graph
  onProgress?.(2, 5, stages[2].label);
  const r3 = await triggerGraph(projectId);
  if (r3.status !== "ok") return { projectId, error: r3.error };

  // Stage 4: Simulation
  onProgress?.(3, 5, stages[3].label);
  const r4 = await triggerSimulation(projectId);
  if (r4.status !== "ok") return { projectId, error: r4.error };

  // Stage 5: Report
  onProgress?.(4, 5, stages[4].label);
  const r5 = await triggerReport(projectId);
  if (r5.status !== "ok") return { projectId, error: r5.error };

  onProgress?.(5, 5, "Complete!");
  return { projectId };
}
