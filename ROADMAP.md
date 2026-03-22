# MiroFish Kernel — Enterprise Roadmap v2.0
## 16 TIPs · 6 Phases · Mỗi phase ship = chạy được

---

## Nguyên tắc thiết kế lộ trình

```
PHASE 1: NỐI DÂY    → UI gọi API gọi Kernel gọi LLM → kết quả hiện lên UI
PHASE 2: CHẠY THẬT  → PostgreSQL lưu state, background job chạy sim, không mất data khi restart
PHASE 3: REAL-TIME   → WebSocket stream từng action, dashboard live update
PHASE 4: THÔNG MINH  → Memory 3 tầng, ReACT nâng cao, so sánh kịch bản
PHASE 5: QUY MÔ      → Ray distributed actors, 10K+ agents, multi-GPU
PHASE 6: DOANH NGHIỆP → Audit trail, multi-tenant, domain templates
```

**Quy tắc vàng**: TIP N+1 chỉ bắt đầu khi TIP N đã chạy được trên production.
Không có code "treo" — mỗi TIP tạo giá trị vận hành ngay lập tức.

---

## PHASE 1: NỐI DÂY (Wire It Up)
### Mục tiêu: User mở dashboard → nhập text → nhấn Run → thấy report
### Kết quả: Full vertical slice hoạt động end-to-end

---

### TIP-01: Backend API Hoàn Chỉnh
**Depends on:** Kernel v1.2 (done)
**Priority:** P0
**Effort:** ~60 min Claude Code

**Lý do đi đầu:** Dashboard hiện dùng mock data. Không có API đầy đủ thì dashboard chỉ là demo tĩnh. API là xương sống nối tất cả.

**Task:**
Mở rộng FastAPI app từ 3 endpoints → 12 endpoints phủ toàn bộ pipeline:

```
POST   /api/projects                    → Tạo project mới (upload text/file)
GET    /api/projects                    → List all projects
GET    /api/projects/{id}               → Project detail + status
POST   /api/projects/{id}/ontology      → Trigger ontology design
POST   /api/projects/{id}/graph         → Trigger graph build
GET    /api/projects/{id}/graph         → Get graph data (nodes, edges)
POST   /api/projects/{id}/simulate      → Start simulation
GET    /api/projects/{id}/simulation    → Get simulation state + rounds
POST   /api/projects/{id}/report        → Generate report
GET    /api/projects/{id}/report        → Get report content
POST   /api/projects/{id}/chat          → Chat with ReportAgent
GET    /api/projects/{id}/agents        → List agent profiles + stats
```

**Spec:**
- Mỗi endpoint map 1:1 vào PipelineOrchestrator method hoặc pipeline stage
- Response format chuẩn: `{ "status": "ok", "data": {...}, "error": null }`
- Error handling: try/catch mọi endpoint, trả HTTP status code đúng
- CORS enabled cho localhost:5173 (dashboard)
- Swagger docs auto-generate tại /docs

**Acceptance Criteria:**
```
Given: API server running ở port 5001
When: curl POST /api/projects với text="Hello world" requirement="test"
Then: 200 OK, project_id returned

Given: project đã tạo
When: curl POST /api/projects/{id}/ontology
Then: 200 OK, ontology JSON returned với entity_types và edge_types

Given: toàn bộ pipeline hoàn tất
When: curl GET /api/projects/{id}/report
Then: 200 OK, markdown report content returned
```

---

### TIP-02: Dashboard ↔ API Integration
**Depends on:** TIP-01
**Priority:** P0
**Effort:** ~90 min Claude Code

**Lý do:** Khi API xong, dashboard phải gọi API thật thay vì dùng mock data. Đây là bước biến demo thành product thật.

**Task:**
1. Tạo `dashboard/src/api/client.js` — API client layer:
   - Base URL configurable (env var VITE_API_URL)
   - Auto-retry on 5xx (exponential backoff)
   - Error normalization (mọi error thành `{ message, status }`)

2. Thay thế mock data trong 4 tabs:
   - **OVERVIEW tab**: Gọi GET /projects/{id} + GET /simulation → populate KPIs, timeline
   - **AGENTS tab**: Gọi GET /agents → populate agent table
   - **K-GRAPH tab**: Gọi GET /graph → render nodes/edges thật
   - **EVENTS tab**: Gọi GET /simulation → show real event log

3. Tạo "New Simulation" flow trong dashboard:
   - Form: nhập requirement + paste/upload text
   - Submit → POST /projects → POST /ontology → POST /graph → POST /simulate → POST /report
   - Progress bar update theo API response

4. Wire ReportAgent chat:
   - Input box gọi POST /chat → hiện response thật

**Acceptance Criteria:**
```
Given: Backend chạy ở :5001, Dashboard chạy ở :5173
When: User nhập requirement + text, nhấn "RUN SIMULATION"
Then: Pipeline chạy tuần tự, progress hiện trên UI, report hiện khi xong

Given: Report đã generate
When: User type "What were the key findings?" trong chat box
Then: ReportAgent response thật (không phải mock) hiện ra
```

---

### TIP-03: Pipeline Progress Streaming (SSE)
**Depends on:** TIP-02
**Priority:** P1
**Effort:** ~45 min Claude Code

**Lý do:** Pipeline chạy 2-10 phút. Không có progress feedback = user nghĩ app treo. SSE (Server-Sent Events) đơn giản hơn WebSocket, đủ cho progress.

**Task:**
1. Thêm SSE endpoint: `GET /api/projects/{id}/stream`
   - Stream progress events: `{ "stage": "ontology", "progress": 0.3, "message": "Designing schema..." }`
   - Mỗi pipeline stage callback → emit SSE event
   
2. Dashboard subscribe SSE khi pipeline đang chạy:
   - EventSource API (built-in browser, không cần lib)
   - Update progress bar + stage indicator real-time
   - Auto-reconnect on disconnect

3. Event types:
   ```
   event: progress   → { stage, progress, message }
   event: round      → { round_num, actions_count, active_agents }  
   event: complete   → { project_id, report_available }
   event: error      → { message, stage }
   ```

**Acceptance Criteria:**
```
Given: User nhấn "RUN SIMULATION"
When: Pipeline đang chạy ontology design
Then: Dashboard hiện "Stage 2/7: Designing ontology... 30%" real-time

Given: Simulation đang chạy round 15/50
When: Round 15 complete
Then: Dashboard nhận SSE event, update round counter + action count live
```

**PHASE 1 CHECKPOINT:**
```
□ User mở dashboard → thấy danh sách projects
□ User tạo simulation mới → pipeline chạy với progress real-time
□ Pipeline xong → report hiện trên dashboard
□ User chat với ReportAgent → nhận response thật
□ Tắt server, bật lại → projects vẫn còn (in-memory OK cho phase 1)
```

---

## PHASE 2: CHẠY THẬT (Production Solid)
### Mục tiêu: Server restart không mất data, long-running sim không block API
### Kết quả: Có thể deploy lên VPS và chạy 24/7

---

### TIP-04: PostgreSQL Persistence Layer
**Depends on:** TIP-03 (Phase 1 complete)
**Priority:** P0
**Effort:** ~60 min Claude Code

**Lý do:** Hiện tại mọi thứ in-memory — restart server = mất hết. PostgreSQL là bước tối thiểu để production.

**Task:**
1. Tạo `core/storage/database.py` — SQLAlchemy models:
   ```
   Table projects:     id, name, phase, status, requirement, raw_text, created_at, updated_at
   Table ontologies:   id, project_id, data_json, created_at
   Table simulations:  id, project_id, config_json, status, current_round, total_rounds
   Table sim_rounds:   id, simulation_id, round_num, actions_json, stats_json
   Table reports:      id, project_id, content_md, outline_json, created_at
   Table chat_history: id, project_id, role, content, created_at
   ```

2. Tạo `core/storage/repository.py` — Repository pattern:
   - `ProjectRepository.save(project)`, `.get(id)`, `.list()`
   - `SimulationRepository.save_round(round)`, `.get_state(sim_id)`
   - Abstraction: core code gọi repository, không import SQLAlchemy trực tiếp

3. Migration: `alembic init` + initial migration script

4. Cập nhật PipelineOrchestrator: persist sau mỗi phase completion

**Acceptance Criteria:**
```
Given: Pipeline chạy xong, server restart
When: User mở dashboard
Then: Projects + reports + simulation data vẫn hiện đầy đủ

Given: 10 projects đã chạy
When: GET /api/projects
Then: Trả về list 10 projects với status, sorted by updated_at DESC
```

---

### TIP-05: Background Job Queue (Celery/ARQ)
**Depends on:** TIP-04
**Priority:** P0
**Effort:** ~60 min Claude Code

**Lý do:** Pipeline chạy 2-10+ phút. Nếu chạy trong API request handler → timeout, block mọi request khác. Job queue là bước bắt buộc cho production.

**Task:**
1. Chọn ARQ (lightweight, async, Redis-backed) hoặc Celery:
   - ARQ nếu muốn nhẹ + Python async native
   - Celery nếu cần mature ecosystem + monitoring

2. Tạo `workers/simulation_worker.py`:
   ```python
   async def run_pipeline_job(project_id: str, requirement: str, text: str):
       pipeline = get_pipeline()  # singleton
       result = pipeline.run(requirement=requirement, text=text,
           progress_callback=lambda msg, pct: update_job_progress(project_id, msg, pct))
       save_result(project_id, result)
   ```

3. API endpoint thay đổi:
   - `POST /api/projects/{id}/simulate` → enqueue job, return job_id immediately
   - `GET /api/projects/{id}/status` → poll job progress
   - SSE stream từ TIP-03 đọc progress từ Redis pubsub

4. Worker chạy riêng process: `arq workers.simulation_worker.WorkerSettings`

**Acceptance Criteria:**
```
Given: User submit simulation
When: POST /api/projects/{id}/simulate
Then: API trả 202 Accepted + job_id trong < 1 giây (không block)

Given: Worker đang chạy pipeline
When: User gửi thêm 2 simulation khác
Then: Queue nhận 2 job mới, process tuần tự (hoặc parallel nếu nhiều worker)

Given: Worker crash giữa chừng
When: Worker restart
Then: Job failed → status = "failed" trong DB, user thấy error message
```

---

### TIP-06: Health Monitoring & Error Recovery
**Depends on:** TIP-05
**Priority:** P1
**Effort:** ~30 min Claude Code

**Lý do:** Production cần biết: server có sống không, worker có chạy không, LLM API có response không. Không có monitoring = "nó hỏng mà không ai biết".

**Task:**
1. Enhanced health endpoint:
   ```json
   GET /health → {
     "api": "ok",
     "database": "ok" | "error: connection refused",
     "redis": "ok" | "error: timeout",
     "worker": "ok (2 active)" | "error: no workers",
     "llm": "ok (latency: 230ms)" | "error: 429 rate limited",
     "graph_store": "ok" | "error: auth failed",
     "uptime": "4d 12h 33m",
     "active_jobs": 2,
     "completed_today": 15
   }
   ```

2. Structured logging (JSON format):
   - Mỗi pipeline stage log: start, end, duration, success/error
   - Log vào file + stdout (cho Docker log collection)

3. LLM retry wrapper:
   - Rate limit (429) → exponential backoff + queue
   - Timeout → retry 2x
   - Invalid JSON response → retry 1x with adjusted prompt
   
4. Graceful degradation:
   - Zep down → graph operations return cached data or error gracefully
   - LLM timeout → partial result + "generation incomplete" message

**PHASE 2 CHECKPOINT:**
```
□ Server restart → tất cả data recovered từ PostgreSQL
□ Submit 5 simulations liên tiếp → queue xử lý tuần tự, không block API
□ Kill worker process → restart → failed jobs hiện error, mới jobs tiếp tục
□ GET /health → toàn bộ dependency status hiện rõ
□ LLM rate limit → auto-retry, user thấy "retrying..." thay vì crash
□ Có thể deploy Docker Compose (api + worker + postgres + redis) lên VPS
```

---

## PHASE 3: REAL-TIME (Live Simulation Monitoring)
### Mục tiêu: Xem agent actions live như Bloomberg ticker
### Kết quả: Dashboard update real-time khi simulation chạy

---

### TIP-07: WebSocket Event Stream
**Depends on:** Phase 2 complete
**Priority:** P0
**Effort:** ~60 min Claude Code

**Lý do:** SSE từ Phase 1 chỉ đủ cho progress bar. Để xem agent actions live (ai đăng gì, ai like gì, sentiment đổi) cần WebSocket bidirectional — dashboard gửi lệnh (pause/inject event), server push events.

**Task:**
1. WebSocket endpoint: `WS /ws/simulation/{project_id}`
   - Server → Client events:
     ```
     agent_action:  { agent_id, agent_name, action_type, content, timestamp }
     round_start:   { round_num, simulated_hour, active_agents_count }
     round_end:     { round_num, stats: { posts, likes, sentiment_avg } }
     event_fired:   { event_id, name, affected_agents }
     graph_update:  { new_nodes, new_edges, updated_nodes }
     alert:         { type, message, severity }
     ```
   - Client → Server commands:
     ```
     pause:         { }
     resume:        { }
     inject_event:  { name, content, affected_agent_ids }
     set_speed:     { multiplier: 1|2|5|10 }
     ```

2. Redis Pub/Sub bridge:
   - Worker publish events → Redis channel `sim:{project_id}:events`
   - API WebSocket handler subscribe → forward to client
   - Cho phép nhiều dashboard clients subscribe cùng simulation

3. Event buffering:
   - Buffer 100 events nếu client disconnect tạm
   - Reconnect → replay buffered events

**Acceptance Criteria:**
```
Given: Simulation đang chạy với 50 agents
When: Agent "TechCEO_Alpha" tạo post mới
Then: Dashboard nhận WebSocket event trong < 500ms, hiện action trong Event Feed

Given: User nhấn "PAUSE" trên dashboard
When: WebSocket gửi pause command
Then: Simulation pause, round counter dừng, status đổi thành PAUSED

Given: User inject "Breaking News" event
When: WebSocket gửi inject_event
Then: Agents phản ứng trong round tiếp theo, dashboard hiện actions mới
```

---

### TIP-08: Dashboard Real-Time Mode
**Depends on:** TIP-07
**Priority:** P0
**Effort:** ~60 min Claude Code

**Lý do:** WebSocket backend xong nhưng dashboard cần UI update: live event feed, animated timeline, agent activity indicators, play/pause controls.

**Task:**
1. **Live Event Feed** (OVERVIEW tab):
   - New events prepend với animation (slide-in from top)
   - Color-code: ACTION=blue, EVENT=amber, ALERT=red, SYSTEM=gray
   - Max 200 events in view, older events archived

2. **Real-time Timeline Chart**:
   - Bar chart grows as new rounds complete
   - Current round highlighted with pulse animation
   - Tooltip on hover: round details

3. **Agent Activity Indicators** (AGENTS tab):
   - Green dot pulse khi agent đang active
   - Last action time real-time update
   - Sentiment sparkline append new data point mỗi round

4. **Simulation Controls**:
   - Play / Pause / Stop buttons
   - Speed selector: 1x, 2x, 5x, 10x
   - Event injection modal (pick event type → inject)
   - Round scrubber: drag to review past rounds

5. **Connection Status**:
   - WebSocket indicator: 🟢 Connected / 🟡 Reconnecting / 🔴 Disconnected
   - Auto-reconnect with visual feedback

**PHASE 3 CHECKPOINT:**
```
□ Simulation chạy → dashboard hiện agent actions trong < 1 giây
□ 50+ agents posting → event feed smooth, không lag
□ Nhấn Pause → simulation dừng ngay, nhấn Resume → tiếp
□ Inject "Breaking News" → agents phản ứng, dashboard hiện
□ Disconnect WiFi 10 giây → reconnect → buffered events replay
□ Mở 3 browser tabs cùng sim → tất cả đều sync real-time
```

---

## PHASE 4: THÔNG MINH (Smarter Simulation)
### Mục tiêu: Chất lượng mô phỏng enterprise-grade
### Kết quả: Agent nhớ dài hạn, report sâu hơn, so sánh kịch bản

---

### TIP-09: Tiered Memory Architecture
**Depends on:** Phase 3 complete
**Priority:** P0
**Effort:** ~90 min Claude Code

**Lý do:** LocalMemoryStore hiện tại ghi JSON file — không search được semantic, không có temporal decay, không scale. Enterprise simulation cần memory 3 tầng.

**Task:**
1. **Ephemeral Memory (Redis)**:
   - Lưu context window hiện tại của agent (last 10 actions)
   - TTL: tự expire sau simulation kết thúc
   - Dùng cho: quick lookups trong round processing
   
2. **Persistent Knowledge (Vector DB — pgvector hoặc Qdrant)**:
   - Lưu agent memories dưới dạng embeddings
   - Semantic search: "What does this agent know about policy X?"
   - Dùng cho: agent decision-making (retrieve relevant memories)
   
3. **Decision Trace (Structured Logs — PostgreSQL)**:
   - Mỗi LLM call: prompt, response, latency, tokens, decision
   - Mỗi agent action: context → reasoning → action → result
   - Dùng cho: audit, debugging, report generation

4. Interface: `TieredMemoryStore` implements `MemoryStore` protocol
   - `store()` → write to all 3 tiers simultaneously  
   - `retrieve(query)` → ephemeral first, then vector search, then decision trace
   - `get_decision_chain(agent_id, round)` → full reasoning trace

**Acceptance Criteria:**
```
Given: Agent "TechCEO" hành động ở round 50
When: Round 100, agent cần quyết định phản ứng với event mới
Then: Retrieve relevant memories từ round 50 (semantic search), agent nhớ và hành xử consistent

Given: Admin muốn debug tại sao agent X có stance bất ngờ
When: Truy vấn decision trace cho agent X round 75
Then: Hiện full chain: context → LLM prompt → LLM response → action chosen → result
```

---

### TIP-10: Enhanced ReACT Agent
**Depends on:** TIP-09
**Priority:** P1
**Effort:** ~60 min Claude Code

**Lý do:** ReportAgent hiện chỉ search 1-2 lần rồi viết. Enterprise report cần: multi-tool reasoning, self-correction, fact-checking, structured argumentation.

**Task:**
1. **Multi-tool Loop** (max 8 tool calls per section):
   - Think → Pick tool → Execute → Observe → Decide: enough or need more?
   - Tools: quick_search, panorama_search, insight_forge, decision_trace_lookup, agent_interview
   
2. **Agent Interview Tool**:
   - ReportAgent có thể "phỏng vấn" agent trong simulation
   - `interview(agent_id, question)` → LLM generates response as that agent
   - Dùng cho: qualitative insights, quotes trong report
   
3. **Self-Reflection**:
   - Sau khi viết section → tự review: "Does this answer the requirement?"
   - Nếu chưa đủ → thêm 1 round search + rewrite
   
4. **Fact-Checking Pipeline**:
   - Mỗi claim trong report → verify against graph
   - Flag unverified claims: "[low confidence]"
   - Separate "Verified Findings" vs "Hypotheses" sections

**Acceptance Criteria:**
```
Given: Report requirement "Predict tech sector reaction to regulation"
When: ReportAgent generates section about TechCEO's stance
Then: Agent thực hiện: search graph → interview TechCEO → cross-check with 2 other agents → write with citations

Given: Report contains claim "67% of agents oppose regulation"
When: Fact-checking pipeline runs
Then: Claim verified against actual simulation data, marked [verified: 67.3% based on 847 actions]
```

---

### TIP-11: Scenario Comparison Engine
**Depends on:** TIP-10
**Priority:** P1
**Effort:** ~60 min Claude Code

**Lý do:** Giá trị thực sự của simulation: chạy NHIỀU kịch bản, so sánh outcomes. "Nếu regulation nhẹ hơn thì sao?" "Nếu có 2 policy options?"

**Task:**
1. **Scenario Fork**:
   - Từ 1 project, fork thành 2-5 scenarios với params khác nhau
   - Share cùng knowledge graph + agents, chỉ khác events/config
   - `POST /api/projects/{id}/fork` → new scenario_id
   
2. **Comparison Dashboard Tab** (new tab: COMPARE):
   - Side-by-side: Scenario A vs Scenario B
   - Metrics overlay: sentiment, activity, action distribution
   - Divergence point detection: "Scenarios diverge at round 34"
   
3. **Comparative Report**:
   - ReportAgent nhận input: 2+ scenario results
   - Output: "Under Scenario A (strict regulation), 67% oppose. Under Scenario B (light regulation), only 34% oppose. Key divergence factor: tech coalition formation in round 34."

4. **Sensitivity Analysis**:
   - Auto-generate 5 scenarios varying 1 parameter
   - Heatmap: parameter value → outcome metric

**PHASE 4 CHECKPOINT:**
```
□ Agent ở round 100 nhớ được event ở round 20 (semantic memory working)
□ Report có citations từ graph, interviews, verified claims
□ Fork scenario → chạy 2 variants → compare report hiện divergence
□ Decision trace: click vào bất kỳ agent action → thấy full reasoning chain
□ Report quality: đọc như analyst report thật, không như AI summary
```

---

## PHASE 5: QUY MÔ (Scale to 10K+ Agents)
### Mục tiêu: Chạy simulation quy mô lớn trên multi-GPU
### Kết quả: 10,000+ agents, <5min per round, distributed execution

---

### TIP-12: Distributed Agent Execution (Ray)
**Depends on:** Phase 4 complete
**Priority:** P0
**Effort:** ~120 min Claude Code

**Lý do:** Hiện tại simulation chạy sequential — 1 agent tại 1 thời điểm. 2,400 agents × LLM call = 2,400 serial API calls = hàng giờ/round. Ray cho phép parallel execution.

**Task:**
1. **RaySimulationEngine** adapter implements `SimulationEngine` protocol:
   ```python
   @ray.remote
   class AgentActor:
       def __init__(self, profile: AgentProfile, llm_config: dict):
           self.profile = profile
           self.llm = create_llm(llm_config)
           self.memory = []
       
       def decide_action(self, context: dict) -> AgentAction:
           # LLM call to decide what this agent does
           ...
   ```

2. **Round execution pattern**:
   - Mỗi round: fan-out → tất cả agents quyết định song song → fan-in collect actions
   - Environment update: tất cả actions applied → new state
   - Memory sync: batch update
   
3. **Invocation Distance Optimization** (from ScaleSim paper):
   - Inactive agents (DO_NOTHING) → skip LLM call
   - Activity pattern predict → pre-warm actors sắp active
   - GPU memory: chỉ load agent context khi active

4. **Scaling knobs**:
   - `num_workers`: how many Ray workers
   - `batch_size`: how many agents per LLM batch call
   - `gpu_fraction`: GPU memory per worker

**Acceptance Criteria:**
```
Given: Simulation config với 2,000 agents
When: Start simulation trên 4-GPU machine
Then: Round processing time < 60 giây (vs 30+ phút sequential)

Given: 10,000 agents configured
When: Start simulation
Then: Ray auto-distributes actors, simulation runs stable, < 5 min/round
```

---

### TIP-13: LLM Batch Optimization
**Depends on:** TIP-12
**Priority:** P0
**Effort:** ~45 min Claude Code

**Lý do:** Dù Ray parallelize, mỗi agent vẫn gọi 1 LLM call. 2,000 parallel calls = rate limit + expensive. Batch API (Anthropic, OpenAI) giảm 50% cost + bypass rate limits.

**Task:**
1. **Batch LLM Provider** adapter:
   - Collect N agent decisions → 1 batch API call → distribute results
   - OpenAI Batch API / Anthropic Batch → async results
   
2. **Smart Batching Strategy**:
   - Group agents by similar context → shared prefix caching
   - Active agents batch first, passive agents skip
   - Fallback: if batch API unavailable → parallel individual calls

3. **Cost tracking**:
   - Log tokens per round, per agent, per project
   - Dashboard widget: "This simulation costs $X.XX so far"
   - Budget limit: auto-pause khi exceed threshold

**PHASE 5 CHECKPOINT:**
```
□ 2,000 agents chạy < 60s/round trên 4×A100
□ 10,000 agents chạy stable (< 5 min/round)
□ Cost tracking: biết chính xác bao nhiêu $/simulation
□ Rate limit handling: auto-batch, no 429 errors
□ GPU utilization > 70% khi simulation chạy
```

---

## PHASE 6: DOANH NGHIỆP (Enterprise Ready)
### Mục tiêu: Bán được cho doanh nghiệp lớn
### Kết quả: Multi-tenant, audit trail, domain templates, security

---

### TIP-14: Domain Template System
**Depends on:** Phase 5 complete
**Priority:** P1
**Effort:** ~60 min Claude Code

**Lý do:** Mỗi ngành cần ontology khác, agent behavior khác, metrics khác. Templates giúp: chọn "Supply Chain" → auto-configure mọi thứ.

**Task:**
1. **Template Registry**: `templates/` directory:
   ```
   templates/
   ├── social_media/     → ontology_prompt, activity_patterns, metrics, sample_report
   ├── supply_chain/     → ontology_prompt, BOM_rules, disruption_events
   ├── financial/        → ontology_prompt, market_patterns, risk_metrics
   ├── real_estate/      → ontology_prompt, location_factors, pricing_model
   ├── public_policy/    → ontology_prompt, stakeholder_map, impact_metrics
   └── custom/           → blank template, user fills in
   ```

2. **Template format** (YAML):
   ```yaml
   name: supply_chain
   display_name: "Supply Chain Simulation"
   ontology_prompt: |
     Design entity types for supply chain: Supplier, Manufacturer, ...
   default_config:
     max_rounds: 200
     platforms: [custom]
     activity_pattern: industrial_24_7
   sample_events:
     - { name: "Supplier Disruption", trigger_round: 50 }
   evaluation_metrics:
     - lead_time_impact
     - cost_increase_pct
     - alternative_sourcing_score
   ```

3. **Dashboard "New Project" flow** enhanced:
   - Step 1: Pick template (cards with icons + descriptions)
   - Step 2: Upload seed data
   - Step 3: Customize params (pre-filled from template)
   - Step 4: Run

---

### TIP-15: Compliance & Audit Layer
**Depends on:** TIP-14
**Priority:** P1
**Effort:** ~60 min Claude Code

**Lý do:** Enterprise customers (banks, government, big corp) cần: ai chạy simulation gì, khi nào, data gì, kết quả gì. Không có audit = không mua.

**Task:**
1. **Audit Trail** (immutable log):
   - Every API call logged: who, when, what, from where
   - Every LLM call logged: prompt hash, response hash, model, tokens, cost
   - Every agent decision logged: input context → output action
   
2. **PII Masking**:
   - Auto-detect PII in seed text (names, emails, phones)
   - Mask in logs, keep original only in encrypted storage
   - Config: masking_level = none | basic | strict

3. **Export Compliance Package**:
   - One-click export: simulation config + all decisions + report + audit log
   - Format: ZIP with structured JSON + markdown report
   - Timestamp + hash chain for tamper detection

---

### TIP-16: Multi-Tenant & RBAC
**Depends on:** TIP-15
**Priority:** P2
**Effort:** ~90 min Claude Code

**Lý do:** Bước cuối để SaaS-ready. Nhiều org dùng chung platform, mỗi org chỉ thấy data của mình.

**Task:**
1. **Tenant isolation**: 
   - Each org has own projects, simulations, reports
   - Database: `tenant_id` column on all tables
   - API: tenant extracted from JWT token

2. **Roles**:
   - Admin: full access, manage users, see billing
   - Analyst: create/run simulations, view reports
   - Viewer: read-only access to reports

3. **API Key management**:
   - Each tenant brings own LLM API key (stored encrypted)
   - Or use platform pool (metered billing)

**PHASE 6 CHECKPOINT:**
```
□ New user picks "Supply Chain" template → simulation runs with pre-configured ontology
□ Audit log exports as tamper-proof ZIP
□ 2 organizations on same server → completely isolated data
□ Analyst can run sims, Viewer can only read reports
□ PII in seed text auto-masked in logs
```

---

## Tổng kết Lộ trình

```
PHASE  │ TIPs    │ Effort    │ Output                          │ Deploy?
───────┼─────────┼───────────┼─────────────────────────────────┼────────
   1   │ 01-03   │ ~4h CC    │ Full UI↔API↔Kernel loop         │ ✅ Demo
   2   │ 04-06   │ ~3h CC    │ PostgreSQL + Job Queue + Health  │ ✅ VPS
   3   │ 07-08   │ ~2h CC    │ WebSocket live monitoring        │ ✅ Beta
   4   │ 09-11   │ ~3.5h CC  │ Smart memory + scenarios         │ ✅ Pilot
   5   │ 12-13   │ ~3h CC    │ 10K+ agents, distributed        │ ✅ Scale
   6   │ 14-16   │ ~3.5h CC  │ Templates + Audit + Multi-tenant │ ✅ SaaS
───────┼─────────┼───────────┼─────────────────────────────────┼────────
TOTAL  │ 16 TIPs │ ~19h CC   │ Enterprise Simulation Platform  │
```

CC = Claude Code estimated time

**Khuyến nghị bắt đầu:** Phase 1 (TIP-01 → TIP-03) là critical path. Xong Phase 1, anh đã có product demo được cho khách hàng. Phase 2 biến demo thành production. Phase 3-6 là growth.
