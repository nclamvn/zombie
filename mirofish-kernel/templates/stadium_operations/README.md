# Stadium Operations — Drone-Augmented Safety Simulation

**MiroFish Domain Template v1.0.0 | Production-grade — FIFA Pilot Program**

## What This Is

A complete domain template for the MiroFish Kernel that simulates the **command-and-control decision chain** inside a stadium Venue Operations Centre (VOC). It measures how drone-provided aerial awareness affects response time, decision accuracy, and inter-agency coordination.

**This is NOT a crowd physics simulator.** Tools like Vissim, Pathfinder, and MassMotion already model pedestrian flow and density. This template simulates the *decisions* that safety officers, police commanders, stewards, medical coordinators, and drone operators make — and how those decisions change when drone data is available.

## Alignment with FIFA Standards

Every component maps to published FIFA guidelines:

| Template Component | FIFA Reference |
|---|---|
| VOC structure and authority | Section 5.4.3 — Venue Operations Centre |
| Integrated command chain | Section 4.7.1 — Safety, Security, Service |
| Emergency evacuation routing | Section 5.4.2 — Emergency Evacuation |
| Fire safety integration | Section 5.4.1 — Fire Safety |
| Medical facilities | Section 5.4.5 — Medical Facilities |
| Contingency planning | Section 4.7 — Safety & Security Operations |
| Primacy transfer protocol | FIFA Stadium Safety & Security Regulations |

## Contents

```
stadium_operations/
├── template.yaml                     # Master configuration (660+ lines)
│   ├── ontology_prompt               # Entity/edge schema for stadium ops
│   ├── default_config                # Stadium, drone, counter-drone configs
│   ├── scenarios (12)                # Pre-defined incident scenarios
│   ├── agent_profiles (8)            # Decision-making behavior definitions
│   ├── kpi (14)                      # KPI framework in 4 categories
│   ├── comparison_configurations (3) # BASELINE / TETHERED / FULL
│   └── report_template (10 sections) # FIFA evidence report structure
├── prompts/
│   ├── agent_decision.txt            # Agent decision-making prompt
│   ├── scenario_orchestrator.txt     # Incident progression + KPI measurement
│   └── comparison_report.txt         # FIFA report generation prompt
├── examples/
│   └── my_dinh_stadium_seed.txt      # Complete seed: My Dinh Stadium, Vietnam
├── __init__.py                       # Python loader + StadiumSimulation class
└── README.md                         # This file
```

## 12 Incident Scenarios

| ID | Name | Category | Severity |
|---|---|---|---|
| CROWD-001 | Gate congestion — peak ingress | Crowd Safety | High |
| CROWD-002 | Halftime concourse crush risk | Crowd Safety | Critical |
| CROWD-003 | Post-match egress bottleneck | Crowd Safety | High |
| MED-001 | Cardiac arrest in upper tier | Medical | Critical |
| MED-002 | Multiple casualties — stand collapse | Medical | Critical |
| SEC-001 | Unauthorized perimeter breach | Security | High |
| SEC-002 | Unattended package — concourse | Security | Critical |
| SEC-003 | Unauthorized drone detected | Security | High |
| ENV-001 | Severe weather — lightning warning | Environmental | High |
| ENV-002 | Power failure — partial blackout | Environmental | Moderate |
| OPS-001 | VIP motorcade arrival conflict | Operational | Moderate |
| OPS-002 | Pre-event sweep — suspicious finding | Operational | Moderate |

## 3 Comparison Configurations

| Config | Sensors Available |
|---|---|
| **BASELINE** | CCTV (120 cameras) + Radio + Steward ground reports + Fire panel |
| **TETHERED** | Baseline + 1× tethered drone (continuous 6h overwatch at 40m) |
| **FULL** | Tethered + 2× rapid-response drones (25 min flight, 45s deploy) |

## 14 KPIs in 4 Categories

**Operational** (4): Drone deployment time, live feed integration, system uptime, blind spot coverage

**Safety** (4): Incident verification time, medical dispatch accuracy, early congestion detection, evacuation route assessment time

**Governance** (3): Contingency plan integration, after-action review quality, inter-agency acceptance

**Legal/Social** (3): Flight compliance, privacy incidents, counter-drone response time

## 8 Agent Types

VOC, Police Commander, Safety Officer, Steward Supervisor, Medical Coordinator, Drone Operator, Fire Safety Commander, CCTV Operator — each with defined authority levels, decision styles, baseline response times, and drone augmentation effects.

## Quick Start

```python
from templates.stadium_operations import StadiumSimulation

sim = StadiumSimulation(
    llm=your_llm_adapter,
    graph_store=your_graph_store,
)

# Load your stadium's operational profile
with open("examples/my_dinh_stadium_seed.txt") as f:
    seed = f.read()

# Run comparison: 12 scenarios × 3 configs × 50 runs = 1,800 simulations
results = sim.run_full_comparison(seed_text=seed, runs_per_scenario=50)

# Generate FIFA evidence report
report = sim.generate_fifa_report(results)

# Export raw data for analysis
sim.export_raw_data(results, "stadium_simulation_raw.json")
```

## Integration with RTR Drone Hardware

The template is designed to pair with Real-Time Robotics (RTR) drone platforms:

| Template Config | RTR Hardware |
|---|---|
| Tethered drone | HERA-T — 105 TOPS AI edge computing, 6h+ endurance, 4K + thermal |
| Rapid-response drone | Vega-R — 25 min flight, 30× zoom, speaker, spotlight, thermal |
| Counter-drone | RF scanner + net-capture drone integrated with VOC |

## Output: FIFA Pilot Evidence Report

The simulation generates a structured report with:
- KPI comparison tables (baseline vs tethered vs full, with confidence intervals)
- Decision chain timelines for each scenario category
- Statistical evidence from 1,800 simulation runs
- Integration mapping to FIFA VOC framework
- Proposed 3-phase pilot design (desktop → rehearsal → live)
