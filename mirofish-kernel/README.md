# MiroFish Kernel 🐟⚡

**A reusable Swarm Intelligence Engine for multi-agent simulation and prediction.**

Extracted and enhanced from [MiroFish](https://github.com/666ghj/MiroFish) (32K+ ⭐) — the open-source swarm intelligence engine. This kernel distills the core logic into a clean, pluggable library that can power **any domain** requiring multi-agent simulation: social media prediction, supply chain modeling, financial forecasting, marketplace matching, and more.

## Architecture

```
                    ┌─────────────────────────────────────────┐
                    │          PipelineOrchestrator            │
                    │  (Full seed-to-report in one call)       │
                    └────┬────┬────┬────┬────┬────┬────┬──────┘
                         │    │    │    │    │    │    │
            ┌────────────┘    │    │    │    │    │    └────────────┐
            ▼                 ▼    ▼    ▼    ▼    ▼                ▼
    ┌──────────────┐  ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐  ┌──────────────┐
    │ SeedProcessor│  │Onto│ │Graph│ │Conf│ │Prof│ │ Sim│  │ ReportAgent  │
    │              │  │logy│ │Buil│ │ Gen│ │ Gen│ │Orch│  │ (ReACT)      │
    │ files→chunks │  │Desi│ │der │ │    │ │    │ │estr│  │ plan→write   │
    └──────────────┘  │gner│ │    │ │    │ │    │ │ator│  │ →reflect     │
                      └────┘ └────┘ └────┘ └────┘ └────┘  └──────────────┘
                         │       │              │    │            │
                    ┌────┴───────┴──────────────┴────┴────────────┘
                    │              INTERFACES (Protocols)
                    ├── LLMProvider      → OpenAI, Anthropic, Ollama...
                    ├── GraphStore       → Zep Cloud, Neo4j, NetworkX...
                    ├── SimulationEngine → OASIS, Custom engines...
                    ├── MemoryStore      → Zep Memory, Redis, JSON...
                    └── ReportGenerator  → ReACT Agent, Custom...
                    │
                    │              ADAPTERS (Pluggable)
                    ├── adapters/llm/openai_adapter.py
                    ├── adapters/graph/zep_adapter.py
                    └── adapters/simulation/oasis_adapter.py (extend)
```

## Key Design Principles

| Principle | Description |
|-----------|-------------|
| **Protocol-first** | All external deps go through abstract `Protocol` interfaces |
| **Zero-framework core** | `core/` has NO Flask, FastAPI, or framework imports |
| **Adapter pattern** | Swap Zep→Neo4j, OpenAI→Anthropic, OASIS→custom without touching core |
| **Prompt externalization** | LLM prompts live in `prompts/` — swap languages, customize domains |
| **Pipeline composable** | Run full pipeline or individual stages |
| **Domain-agnostic** | Same kernel for social media, supply chain, finance, marketplace |

## Quick Start

### Install

```bash
pip install mirofish-kernel[openai,zep,files]
```

### Full Pipeline (3 lines)

```python
from core import PipelineOrchestrator
from adapters.llm.openai_adapter import OpenAIAdapter
from adapters.graph.zep_adapter import ZepGraphAdapter

pipeline = PipelineOrchestrator(
    llm=OpenAIAdapter(api_key="sk-...", model="gpt-4o-mini"),
    graph_store=ZepGraphAdapter(api_key="z_..."),
)

result = pipeline.run(
    requirement="Predict public reaction to new AI regulation",
    text="The government announced a new AI regulation framework...",
)

print(result["report"])
```

### Step-by-Step

```python
from core.pipeline import (
    SeedProcessor, OntologyDesigner, GraphBuilder,
    ConfigGenerator, ProfileGenerator, ReportAgent, RetrievalTools,
)

# Process seed material
seed = SeedProcessor(chunk_size=500)
data = seed.process_text("Your text...", requirement="Predict...")

# Design knowledge graph schema
ontology = OntologyDesigner(llm).design([data["raw_text"]], data["requirement"])

# Build knowledge graph
graph = GraphBuilder(graph_store).build(data["chunks"], ontology)

# Generate simulation config + agent profiles
config = ConfigGenerator(llm, graph_store).generate(graph.graph_id, data["requirement"])
profiles = ProfileGenerator(llm, graph_store).generate_profiles(graph.graph_id, data["requirement"])

# Generate report (with or without simulation)
retrieval = RetrievalTools(llm, graph_store)
report = ReportAgent(llm, retrieval).generate_full_report(
    requirement=data["requirement"],
    graph_id=graph.graph_id,
    simulation_summary={"total_agents": len(profiles)},
)
```

## Pipeline Stages

```
SEED → ONTOLOGY → GRAPH → CONFIG → PROFILES → SIMULATION → REPORT → CHAT
 │        │          │        │         │           │           │        │
 S1       S2         S3       S4        S5          S6          S7       S8
```

| Stage | Module | Input → Output |
|-------|--------|----------------|
| S1 | `SeedProcessor` | Files/text → cleaned chunks |
| S2 | `OntologyDesigner` | Chunks + requirement → entity/edge schema |
| S3 | `GraphBuilder` | Schema + chunks → knowledge graph |
| S4 | `ConfigGenerator` | Graph + requirement → simulation params |
| S5 | `ProfileGenerator` | Graph entities → agent personas |
| S6 | `SimulationOrchestrator` | Config + agents → simulation results |
| S7 | `ReportAgent` | Graph + results → prediction report (ReACT) |
| S8 | `ReportAgent.chat()` | Report + question → interactive answer |

## Custom Domains

The kernel is domain-agnostic. Customize by:

1. **Custom ontology prompts** — swap `prompts/ontology/system_prompt.txt`
2. **Custom simulation engine** — implement `SimulationEngine` protocol
3. **Custom graph backend** — implement `GraphStore` protocol

```python
# Supply chain domain
designer = OntologyDesigner(llm, system_prompt=SUPPLY_CHAIN_PROMPT)
pipeline.ontology_designer = designer

# Social matching domain  
designer = OntologyDesigner(llm, system_prompt=MARKETPLACE_PROMPT)
```

See `examples/custom_domain.py` for complete supply chain and marketplace examples.

## Project Structure

```
mirofish-kernel/
├── core/                        # 🔴 PURE KERNEL (zero framework deps)
│   ├── interfaces/              # Abstract protocols
│   │   ├── llm_provider.py      # LLMProvider protocol
│   │   ├── graph_store.py       # GraphStore protocol
│   │   ├── simulation_engine.py # SimulationEngine protocol
│   │   ├── memory_store.py      # MemoryStore protocol
│   │   └── report_generator.py  # ReportGenerator protocol
│   ├── pipeline/                # Pipeline stages
│   │   ├── orchestrator.py      # Full pipeline coordinator
│   │   ├── seed_processor.py    # Stage 1: file/text → chunks
│   │   ├── ontology_designer.py # Stage 2: LLM → schema
│   │   ├── graph_builder.py     # Stage 3: schema + chunks → graph
│   │   ├── config_generator.py  # Stage 4: LLM → simulation config
│   │   ├── profile_generator.py # Stage 5: entities → agent personas
│   │   ├── simulation_orchestrator.py # Stage 6: run simulation
│   │   ├── report_agent.py      # Stage 7: ReACT report generation
│   │   └── retrieval_tools.py   # Graph search tools for ReACT
│   ├── models/                  # Pure dataclasses
│   │   ├── ontology.py          # EntityType, EdgeType, Ontology
│   │   ├── graph.py             # Node, Edge, GraphInfo, GraphData
│   │   ├── simulation.py        # SimConfig, AgentProfile, Round, Action
│   │   ├── report.py            # ReportOutline, ReportSection
│   │   └── project.py           # Project state machine
│   └── tools/                   # Reusable utilities
│       ├── text_processor.py    # File parsing + chunking
│       ├── retry.py             # Smart retry with backoff
│       └── logger.py            # Structured logging
├── adapters/                    # 🟡 PLUGGABLE IMPLEMENTATIONS
│   ├── llm/
│   │   └── openai_adapter.py    # OpenAI SDK adapter
│   ├── graph/
│   │   └── zep_adapter.py       # Zep Cloud adapter
│   ├── simulation/              # (extend with OASIS, custom)
│   └── memory/                  # (extend with Zep memory, Redis)
├── prompts/                     # 📝 EXTERNALIZED LLM PROMPTS
│   └── ontology/
│       └── system_prompt.txt    # Default ontology design prompt
├── examples/                    # 📚 USAGE EXAMPLES
│   ├── quick_start.py           # Full pipeline demo
│   └── custom_domain.py         # Supply chain, marketplace
├── pyproject.toml               # Package config
└── README.md                    # This file
```

## Comparison with Original MiroFish

| Aspect | Original MiroFish | MiroFish Kernel |
|--------|-------------------|-----------------|
| Architecture | Monolith Flask app | Pluggable kernel + adapters |
| LLM coupling | Direct OpenAI import | `LLMProvider` protocol |
| Graph coupling | Zep-only | `GraphStore` protocol (swap Neo4j, etc.) |
| Sim coupling | OASIS-only | `SimulationEngine` protocol |
| Prompts | Hardcoded Chinese | Externalized, multilingual |
| API | Flask 2700-LOC routes | Thin API layer (or none) |
| Domain | Social media only | Any domain via custom prompts |
| Frontend | Vue 3 (coupled) | Stripped (bring your own UI) |
| Lines of code | ~17K backend | ~3K kernel core |

## Credits

- [MiroFish](https://github.com/666ghj/MiroFish) — Original swarm intelligence engine by 666ghj
- [OASIS](https://github.com/camel-ai/oasis) — Social simulation framework by CAMEL-AI
- [Zep](https://www.getzep.com/) — Knowledge graph memory platform
- **Vibecode Kit v6.0** — Development methodology by Lâm @ RTR

## License

AGPL-3.0 (same as original MiroFish)
