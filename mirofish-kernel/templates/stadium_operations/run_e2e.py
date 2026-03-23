#!/usr/bin/env python3
"""
Stadium Operations — End-to-End Pipeline Runner (TIP-19)

Runs the full 7-stage pipeline: seed → ontology → graph → profiles →
simulation → comparison → report.

Usage:
    export LLM_API_KEY=sk-...
    export LLM_PROVIDER=openai   # or anthropic
    python run_e2e.py --seed examples/my_dinh_stadium_seed.txt --runs 5

    # Quick test (3 scenarios only):
    python run_e2e.py --seed examples/my_dinh_stadium_seed.txt --runs 3 --scenarios CROWD-001,MED-001,SEC-003
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import yaml


def main():
    parser = argparse.ArgumentParser(description="Stadium Operations E2E Pipeline")
    parser.add_argument("--seed", type=str, default="examples/my_dinh_stadium_seed.txt",
                        help="Path to seed text file")
    parser.add_argument("--runs", type=int, default=5,
                        help="Runs per scenario per config (default 5)")
    parser.add_argument("--scenarios", type=str, default=None,
                        help="Comma-separated scenario IDs (default: all 12)")
    parser.add_argument("--output-dir", type=str, default="outputs",
                        help="Output directory for results")
    parser.add_argument("--mock", action="store_true",
                        help="Use mock mode (no LLM)")
    args = parser.parse_args()

    template_dir = Path(__file__).parent
    output_dir = template_dir / args.output_dir
    output_dir.mkdir(exist_ok=True)

    # ── Load seed text ──
    seed_path = template_dir / args.seed if not Path(args.seed).is_absolute() else Path(args.seed)
    if not seed_path.exists():
        print(f"Error: seed file not found: {seed_path}")
        return 1
    seed_text = seed_path.read_text(encoding="utf-8")
    print(f"Seed loaded: {len(seed_text)} chars from {seed_path.name}")

    # ── Load template ──
    with open(template_dir / "template.yaml") as f:
        template = yaml.safe_load(f)
    print(f"Template: {template['display_name']}")

    # ── Init LLM ──
    llm = None
    llm_key = os.environ.get("LLM_API_KEY")
    if llm_key and not args.mock:
        provider = os.environ.get("LLM_PROVIDER", "openai").lower()
        model = os.environ.get("LLM_MODEL_NAME", "gpt-4o-mini")
        try:
            if provider == "anthropic":
                from adapters.llm.anthropic_adapter import AnthropicAdapter
                llm = AnthropicAdapter(api_key=llm_key, model=model)
            else:
                from adapters.llm.openai_adapter import OpenAIAdapter
                base_url = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
                llm = OpenAIAdapter(api_key=llm_key, base_url=base_url, model=model)
            print(f"LLM: {provider} / {model}")
        except Exception as e:
            print(f"Warning: LLM init failed ({e}), falling back to mock mode")
    else:
        print("LLM: mock mode (no LLM_API_KEY or --mock flag)")

    # ── Init Graph Store ──
    graph_store_type = os.environ.get("GRAPH_STORE", "local")
    if graph_store_type == "zep":
        zep_key = os.environ.get("ZEP_API_KEY")
        if zep_key:
            from adapters.graph.zep_adapter import ZepGraphAdapter
            graph_store = ZepGraphAdapter(api_key=zep_key)
            print("Graph: Zep Cloud")
        else:
            print("Warning: ZEP_API_KEY not set, falling back to local graph")
            from adapters.graph.local_graph_store import LocalGraphStore
            graph_store = LocalGraphStore(llm=llm)
            print("Graph: LocalGraphStore (demo mode)")
    else:
        from adapters.graph.local_graph_store import LocalGraphStore
        graph_store = LocalGraphStore(llm=llm)
        print("Graph: LocalGraphStore (demo mode)")

    t_start = time.time()

    # ═══ STAGE 1: SEED PROCESSING ═══
    print("\n" + "=" * 60)
    print("STAGE 1/7: Processing seed text...")
    from core.pipeline.seed_processor import SeedProcessor
    sp = SeedProcessor(chunk_size=500)
    seed_result = sp.process_text(seed_text, requirement="Stadium operations simulation")
    chunks = seed_result["chunks"]
    print(f"  Chunks: {len(chunks)}")

    # ═══ STAGE 2: ONTOLOGY DESIGN ═══
    print("\nSTAGE 2/7: Designing ontology...")
    ontology = None
    ontology_dict = None
    if llm:
        try:
            from core.pipeline.ontology_designer import OntologyDesigner
            od = OntologyDesigner(llm, system_prompt=template.get("ontology_prompt", ""))
            ontology = od.design(
                document_texts=[seed_result["raw_text"]],
                requirement="Stadium VOC decision chain simulation with drone augmentation",
            )
            ontology_dict = ontology.to_dict()
            print(f"  Entity types: {len(ontology.entity_types)}")
            print(f"  Edge types: {len(ontology.edge_types)}")
            # Save
            with open(output_dir / "ontology.json", "w") as f:
                json.dump(ontology_dict, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"  Warning: ontology design failed ({e}), using template defaults")

    if not ontology_dict:
        # Use template ontology as fallback
        ontology_dict = {
            "entity_types": [{"name": t} for t in [
                "VenueOperationsCenter", "PoliceCommander", "SafetyOfficer",
                "StewardSupervisor", "MedicalCoordinator", "DroneOperator",
                "FireSafetyCommander", "CCTVOperator", "Person", "Organization",
            ]],
            "edge_types": [{"name": t} for t in [
                "COMMANDS", "REPORTS_TO", "FEEDS_VIDEO_TO", "DISPATCHES_TO",
                "MONITORS_ZONE", "ESCALATES_TO", "COORDINATES_WITH",
            ]],
        }
        print(f"  Using template defaults: {len(ontology_dict['entity_types'])} entity types")

    # ═══ STAGE 3: KNOWLEDGE GRAPH ═══
    print("\nSTAGE 3/7: Building knowledge graph...")
    from adapters.graph.local_graph_store import LocalGraphStore
    if isinstance(graph_store, LocalGraphStore):
        graph_result = graph_store.build(chunks=chunks, ontology=ontology or ontology_dict, graph_name="My Dinh Stadium")
    else:
        from core.pipeline.graph_builder import GraphBuilder
        gb = GraphBuilder(graph_store)
        graph_result = gb.build(chunks=chunks, ontology=ontology, graph_name="My Dinh Stadium")

    if graph_result.success:
        print(f"  Nodes: {graph_result.graph_info.node_count}")
        print(f"  Edges: {graph_result.graph_info.edge_count}")
        # Save graph
        if isinstance(graph_store, LocalGraphStore):
            nodes = [n.to_dict() for n in graph_store.get_nodes(graph_result.graph_id)]
            edges = [e.to_dict() for e in graph_store.get_edges(graph_result.graph_id)]
        else:
            nodes = [n.to_dict() for n in graph_store.get_nodes(graph_result.graph_id)]
            edges = [e.to_dict() for e in graph_store.get_edges(graph_result.graph_id)]
        with open(output_dir / "graph.json", "w") as f:
            json.dump({"nodes": nodes, "edges": edges}, f, indent=2, ensure_ascii=False)
    else:
        print(f"  Graph build failed: {graph_result.error}")

    # ═══ STAGE 4-5: PROFILES (from template) ═══
    print("\nSTAGE 4-5/7: Agent profiles (from template)...")
    agent_profiles = template.get("agent_profiles", {})
    print(f"  Agent types: {len(agent_profiles)}")

    # ═══ STAGE 6: SIMULATION COMPARISON ═══
    print("\nSTAGE 6/7: Running comparison simulation...")
    scenarios = template["scenarios"]
    if args.scenarios:
        ids = set(args.scenarios.split(","))
        scenarios = [s for s in scenarios if s["id"] in ids]

    configs = template["comparison_configurations"]
    total = len(scenarios) * len(configs) * args.runs
    print(f"  Scenarios: {len(scenarios)} × Configs: {len(configs)} × Runs: {args.runs} = {total} total")

    from templates.stadium_operations import StadiumSimulation
    sim = StadiumSimulation(llm=llm, graph_store=graph_store)

    # Use quick_validate model for comparison (works with or without LLM)
    import random
    results = {}
    completed = 0

    def variance(base):
        return base * (0.8 + random.random() * 0.4)

    all_decisions = []

    for sc in scenarios:
        results[sc["id"]] = {"name": sc["name"], "category": sc["category"], "configs": {}}
        for cfg in configs:
            timelines = []
            for run_num in range(args.runs):
                completed += 1
                if completed % 20 == 0 or completed == total:
                    print(f"  [{completed}/{total}] {sc['id']} × {cfg['id']} run {run_num + 1}")

                if llm and sim._scenario_orchestrator:
                    # LLM-powered run
                    try:
                        result = sim._scenario_orchestrator.run_scenario(
                            scenario=sc, config=cfg, agent_profiles=agent_profiles,
                        )
                        timelines.append({
                            "timestamps": result["timestamps"],
                            "kpi": result["kpi"],
                        })
                        if result.get("decisions"):
                            for d in result["decisions"]:
                                all_decisions.append({
                                    "scenario_id": sc["id"], "config_id": cfg["id"],
                                    "run": run_num, **d,
                                })
                        continue
                    except Exception as e:
                        print(f"    LLM run failed ({e}), using mock")

                # Mock fallback
                t0 = sc["trigger_minute"] * 60.0
                drone_cfg = cfg.get("drone_config") or {}
                has_t = (drone_cfg.get("tethered", 0) > 0) if drone_cfg else False
                has_r = (drone_cfg.get("rapid_response", 0) > 0) if drone_cfg else False
                sev, cat = sc["severity"], sc["category"]

                t1 = t0 + (variance(12) if has_t and cat in ("crowd_safety", "operational") else variance(25) if has_t else variance(60))
                t2 = t1 + (variance(8) if has_t else variance(25))
                t3 = t2 + (variance(35) if has_r and sev in ("critical", "high") else variance(20) if has_t else variance(150))
                sf = {"critical": 1.2, "high": 1.0, "moderate": 0.8}.get(sev, 1.0)
                t4 = t3 + (variance(20 * sf) if has_t else variance(45 * sf))
                t5 = t4 + (variance(84) if has_r else variance(120))
                rb = {"critical": 600, "high": 360, "moderate": 180}.get(sev, 300)
                t6 = t5 + (variance(rb * 0.6) if has_t and has_r else variance(rb * 0.75) if has_t else variance(rb))

                timelines.append({
                    "timestamps": {f"T{i}": round(v, 1) for i, v in enumerate([t0, t1, t2, t3, t4, t5, t6])},
                    "kpi": {
                        "detection_latency": round(t1 - t0, 1), "verification_time": round(t3 - t1, 1),
                        "decision_time": round(t4 - t3, 1), "response_time": round(t5 - t4, 1),
                        "total_resolution": round(t6 - t0, 1),
                    },
                })

            results[sc["id"]]["configs"][cfg["id"]] = timelines

    # Save comparison
    with open(output_dir / "comparison.json", "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Save decisions
    if all_decisions:
        with open(output_dir / "agent_decisions.json", "w") as f:
            json.dump(all_decisions, f, indent=2, ensure_ascii=False)
        print(f"  Agent decisions logged: {len(all_decisions)}")

    # ═══ STAGE 7: FIFA REPORT ═══
    print("\nSTAGE 7/7: Generating FIFA report...")
    if llm:
        try:
            report_prompt = (template_dir / "prompts" / "comparison_report.txt").read_text()
            # Build summary for report
            summary_data = json.dumps({
                "total_runs": total,
                "scenarios": len(scenarios),
                "configurations": [c["id"] for c in configs],
            }, indent=2)
            response = llm.chat(
                messages=[
                    {"role": "system", "content": report_prompt.replace("{simulation_results_json}", summary_data)},
                    {"role": "user", "content": json.dumps(results, ensure_ascii=False)[:8000]},
                ],
                temperature=0.3, max_tokens=4096,
            )
            with open(output_dir / "fifa_report.md", "w") as f:
                f.write(response)
            print(f"  Report: {len(response)} chars")
        except Exception as e:
            print(f"  Report generation failed: {e}")
    else:
        print("  Skipped (no LLM)")

    # ═══ SUMMARY ═══
    elapsed = time.time() - t_start
    print("\n" + "=" * 60)
    print(f"PIPELINE COMPLETE in {elapsed:.1f}s")
    print(f"  Output directory: {output_dir}")
    for f in sorted(output_dir.iterdir()):
        print(f"    {f.name} ({f.stat().st_size // 1024}KB)")
    print(f"  LLM mode: {'active' if llm else 'mock'}")
    print(f"  Total runs: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
