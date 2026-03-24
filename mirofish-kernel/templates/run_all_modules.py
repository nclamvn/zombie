#!/usr/bin/env python3
"""
RTR Simulator Portal — Batch Module Runner (TIP-20)

Usage:
    # Mock all modules (no LLM, fast)
    python run_all_modules.py --mode mock --runs 50

    # Mock single module
    python run_all_modules.py --mode mock --module counter_uas --runs 50

    # LLM single module (needs API key)
    python run_all_modules.py --mode llm --module counter_uas --runs 3

    # List all modules
    python run_all_modules.py --list
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from templates.module_runner import ModuleRunner, TEMPLATES_DIR


def get_all_module_ids():
    """Discover all modules with template.yaml."""
    modules = []
    for d in sorted(TEMPLATES_DIR.iterdir()):
        if d.is_dir() and (d / "template.yaml").exists():
            modules.append(d.name)
    return modules


def main():
    parser = argparse.ArgumentParser(description="RTR Portal — Batch Module Runner")
    parser.add_argument("--mode", choices=["mock", "llm"], default="mock")
    parser.add_argument("--module", type=str, default=None, help="Single module ID")
    parser.add_argument("--all", action="store_true", help="Run all modules")
    parser.add_argument("--runs", type=int, default=50, help="Runs per scenario per config")
    parser.add_argument("--output", type=str, default="outputs", help="Output base dir")
    parser.add_argument("--list", action="store_true", help="List all modules")
    args = parser.parse_args()

    all_modules = get_all_module_ids()

    if args.list:
        print(f"RTR Simulator Portal — {len(all_modules)} modules\n")
        for m in all_modules:
            try:
                runner = ModuleRunner(m)
                sc = len(runner.scenarios)
                cfg = len(runner.configs)
                print(f"  {m:30s} {sc:2d} scenarios  {cfg} configs  {runner.name}")
            except Exception as e:
                print(f"  {m:30s} ERROR: {e}")
        return 0

    # Determine which modules to run
    if args.module:
        modules = [args.module]
    elif args.all or not args.module:
        modules = all_modules
    else:
        modules = all_modules

    output_base = Path(args.output)
    t_start = time.time()
    total_runs = 0
    results_all = {}

    print(f"╔══════════════════════════════════════════════════════╗")
    print(f"║  RTR Simulator Portal — Batch Runner                ║")
    print(f"║  Mode: {args.mode:6s}  Modules: {len(modules):2d}  Runs/sc: {args.runs:4d}        ║")
    print(f"╚══════════════════════════════════════════════════════╝")
    print()

    for i, module_id in enumerate(modules):
        try:
            runner = ModuleRunner(module_id)
        except Exception as e:
            print(f"[{i+1}/{len(modules)}] {module_id}: SKIP — {e}")
            continue

        sc_count = len(runner.scenarios)
        cfg_count = len(runner.configs)
        expected = sc_count * cfg_count * args.runs

        print(f"[{i+1}/{len(modules)}] {module_id} — {runner.name}")
        print(f"         {sc_count} scenarios × {cfg_count} configs × {args.runs} runs = {expected}")

        t0 = time.time()

        if args.mode == "mock":
            results = runner.run_mock(
                runs_per_scenario=args.runs,
                progress_fn=lambda c, t, msg: print(f"         [{c}/{t}] {msg}") if c % 500 == 0 else None,
            )
        else:
            # LLM mode — TODO: wire via run_e2e pattern
            print(f"         LLM mode not yet batch-supported, falling back to mock")
            results = runner.run_mock(runs_per_scenario=args.runs)

        elapsed = time.time() - t0
        total_runs += expected

        # Export
        out_dir = output_base / module_id
        summary_text = runner.export_results(results, str(out_dir))
        results_all[module_id] = runner.get_summary(results)

        # Print compact summary
        summary = runner.get_summary(results)
        baseline = summary.get("BASELINE", {})
        best_id = [k for k in summary if k != "BASELINE"][-1] if len(summary) > 1 else "BASELINE"
        best = summary.get(best_id, {})
        total_b = baseline.get("total_resolution", {}).get("mean", 0)
        total_f = best.get("total_resolution", {}).get("mean", 0)
        imp = round((1 - total_f / total_b) * 100) if total_b > 0 else 0

        print(f"         ✓ {elapsed:.1f}s — Total: {total_b:.0f}s → {total_f:.0f}s (-{imp}%)")
        print()

    elapsed_total = time.time() - t_start

    print(f"{'='*60}")
    print(f"BATCH COMPLETE")
    print(f"  Modules: {len(modules)}")
    print(f"  Total runs: {total_runs:,}")
    print(f"  Time: {elapsed_total:.1f}s")
    print(f"  Output: {output_base}/")
    print(f"{'='*60}")

    # Export master summary
    import json
    master_path = output_base / "portal_summary.json"
    master_path.parent.mkdir(parents=True, exist_ok=True)
    with open(master_path, "w") as f:
        json.dump(results_all, f, indent=2, ensure_ascii=False)
    print(f"  Master summary: {master_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
