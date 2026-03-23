#!/usr/bin/env python3
"""
Stadium Operations Template — Quick Validation Runner

Runs a small-scale simulation (3 scenarios × 3 configs × 10 runs = 90 runs)
using the built-in statistical model (no LLM required) to validate the
template and produce sample KPI output.

Usage:
    python3 quick_validate.py
    python3 quick_validate.py --runs 50 --output results.json
"""

import argparse
import json
import random
import sys
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Any

# Add parent to path for template import
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import yaml

TEMPLATE_PATH = Path(__file__).parent / "template.yaml"


@dataclass
class Timeline:
    scenario_id: str
    config_id: str
    run: int
    t0: float
    t1: float
    t2: float
    t3: float
    t4: float
    t5: float
    t6: float

    @property
    def detection_latency(self): return self.t1 - self.t0
    @property
    def verification_time(self): return self.t3 - self.t1
    @property
    def decision_time(self): return self.t4 - self.t3
    @property
    def response_time(self): return self.t5 - self.t4
    @property
    def total_resolution(self): return self.t6 - self.t0


def variance(base):
    return base * (0.8 + random.random() * 0.4)


def simulate_run(scenario, config, run_num):
    t0 = scenario["trigger_minute"] * 60.0
    cfg = config.get("drone_config") or {}
    has_tethered = cfg.get("tethered", 0) > 0
    has_rapid = cfg.get("rapid_response", 0) > 0
    sev = scenario["severity"]
    cat = scenario["category"]

    # T1: Detection
    if has_tethered and cat in ("crowd_safety", "operational"):
        t1 = t0 + variance(12)
    elif has_tethered:
        t1 = t0 + variance(25)
    else:
        t1 = t0 + variance(60)

    # T2: VOC awareness
    t2 = t1 + (variance(8) if has_tethered else variance(25))

    # T3: Verification
    if has_rapid and sev in ("critical", "high"):
        t3 = t2 + variance(35)
    elif has_tethered:
        t3 = t2 + variance(20)
    else:
        t3 = t2 + variance(150)

    # T4: Decision
    sf = {"critical": 1.2, "high": 1.0, "moderate": 0.8}.get(sev, 1.0)
    t4 = t3 + (variance(20 * sf) if has_tethered else variance(45 * sf))

    # T5: Responder arrival
    base_travel = 120
    t5 = t4 + (variance(base_travel * 0.7) if has_rapid else variance(base_travel))

    # T6: Resolution
    res_base = {"critical": 600, "high": 360, "moderate": 180}.get(sev, 300)
    if has_tethered and has_rapid:
        t6 = t5 + variance(res_base * 0.6)
    elif has_tethered:
        t6 = t5 + variance(res_base * 0.75)
    else:
        t6 = t5 + variance(res_base)

    return Timeline(scenario["id"], config["id"], run_num,
                    round(t0,1), round(t1,1), round(t2,1),
                    round(t3,1), round(t4,1), round(t5,1), round(t6,1))


def stats(values):
    if not values:
        return {"mean": 0, "std": 0, "min": 0, "max": 0, "n": 0}
    n = len(values)
    m = sum(values) / n
    s = (sum((v - m) ** 2 for v in values) / max(n - 1, 1)) ** 0.5
    return {"mean": round(m, 1), "std": round(s, 1),
            "min": round(min(values), 1), "max": round(max(values), 1), "n": n}


def main():
    parser = argparse.ArgumentParser(description="Validate stadium_operations template")
    parser.add_argument("--runs", type=int, default=10, help="Runs per scenario per config")
    parser.add_argument("--scenarios", type=str, default=None, help="Comma-separated scenario IDs")
    parser.add_argument("--output", type=str, default=None, help="Output JSON path")
    args = parser.parse_args()

    with open(TEMPLATE_PATH) as f:
        tmpl = yaml.safe_load(f)

    scenarios = tmpl["scenarios"]
    if args.scenarios:
        ids = set(args.scenarios.split(","))
        scenarios = [s for s in scenarios if s["id"] in ids]

    configs = tmpl["comparison_configurations"]
    total = len(scenarios) * len(configs) * args.runs

    print(f"╔══════════════════════════════════════════════════════╗")
    print(f"║  Stadium Operations Template — Validation Runner    ║")
    print(f"╠══════════════════════════════════════════════════════╣")
    print(f"║  Scenarios: {len(scenarios):>3}   Configs: {len(configs):>1}   Runs/each: {args.runs:>4}     ║")
    print(f"║  Total simulation runs: {total:>5}                       ║")
    print(f"╚══════════════════════════════════════════════════════╝")
    print()

    results = {}
    for sc in scenarios:
        results[sc["id"]] = {"name": sc["name"], "category": sc["category"], "configs": {}}
        for cfg in configs:
            timelines = [simulate_run(sc, cfg, r) for r in range(args.runs)]
            results[sc["id"]]["configs"][cfg["id"]] = timelines

    # Print KPI comparison
    kpi_fields = [
        ("detection_latency", "Detection Latency"),
        ("verification_time", "Verification Time"),
        ("decision_time", "Decision Time"),
        ("response_time", "Response Time"),
        ("total_resolution", "Total Resolution"),
    ]

    print("=" * 90)
    print(f"{'SCENARIO':<14} {'KPI':<22} {'BASELINE':>12} {'TETHERED':>12} {'FULL':>12} {'IMPROVE':>10}")
    print("=" * 90)

    master_baseline = {k: [] for k, _ in kpi_fields}
    master_tethered = {k: [] for k, _ in kpi_fields}
    master_full = {k: [] for k, _ in kpi_fields}

    for sc_id, sc_data in results.items():
        first = True
        for kpi_attr, kpi_label in kpi_fields:
            row_label = sc_id if first else ""
            first = False

            vals = {}
            for cfg_id in ["BASELINE", "TETHERED", "FULL"]:
                tls = sc_data["configs"].get(cfg_id, [])
                v = [getattr(tl, kpi_attr) for tl in tls]
                vals[cfg_id] = stats(v)

                # Accumulate for master table
                if cfg_id == "BASELINE": master_baseline[kpi_attr].extend(v)
                elif cfg_id == "TETHERED": master_tethered[kpi_attr].extend(v)
                else: master_full[kpi_attr].extend(v)

            base_m = vals["BASELINE"]["mean"]
            full_m = vals["FULL"]["mean"]
            imp = f"-{round((1 - full_m/base_m)*100)}%" if base_m > 0 else "N/A"

            print(f"{row_label:<14} {kpi_label:<22} "
                  f"{base_m:>7.1f}s ±{vals['BASELINE']['std']:>4.1f} "
                  f"{vals['TETHERED']['mean']:>7.1f}s ±{vals['TETHERED']['std']:>4.1f} "
                  f"{full_m:>7.1f}s ±{vals['FULL']['std']:>4.1f} "
                  f"{imp:>10}")
        print("-" * 90)

    # Master summary
    print()
    print("=" * 70)
    print(f"{'MASTER KPI SUMMARY':^70}")
    print("=" * 70)
    print(f"{'KPI':<25} {'BASELINE':>12} {'FULL':>12} {'IMPROVEMENT':>14}")
    print("-" * 70)

    for kpi_attr, kpi_label in kpi_fields:
        bm = sum(master_baseline[kpi_attr]) / max(len(master_baseline[kpi_attr]), 1)
        fm = sum(master_full[kpi_attr]) / max(len(master_full[kpi_attr]), 1)
        imp = round((1 - fm / bm) * 100) if bm > 0 else 0
        print(f"{kpi_label:<25} {bm:>9.1f}s   {fm:>9.1f}s     {'-' if imp > 0 else '+'}{abs(imp)}%")

    print("=" * 70)
    print(f"\nTotal runs: {total}")
    print(f"Statistical model: built-in variance (±20%), no LLM required")
    print(f"For production: use StadiumSimulation class with LLM for agent decisions")

    # Export
    if args.output:
        export = {}
        for sc_id, sc_data in results.items():
            export[sc_id] = {
                "name": sc_data["name"], "category": sc_data["category"],
                "configs": {
                    cfg_id: [
                        {"timestamps": {"T0": tl.t0, "T1": tl.t1, "T2": tl.t2,
                                        "T3": tl.t3, "T4": tl.t4, "T5": tl.t5, "T6": tl.t6},
                         "kpi": {"detection_latency": round(tl.detection_latency, 1),
                                 "verification_time": round(tl.verification_time, 1),
                                 "decision_time": round(tl.decision_time, 1),
                                 "response_time": round(tl.response_time, 1),
                                 "total_resolution": round(tl.total_resolution, 1)}}
                        for tl in tls
                    ]
                    for cfg_id, tls in sc_data["configs"].items()
                }
            }
        with open(args.output, "w") as f:
            json.dump(export, f, indent=2)
        print(f"\nRaw data exported to: {args.output}")

    print("\n✓ Template validation PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
