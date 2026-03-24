"""
RTR Simulator Portal — Generic Module Runner (TIP-20)

Runs ANY module's simulation by reading its template YAML.
Same timing model as stadium_operations/quick_validate.py.

Usage:
    from templates.module_runner import ModuleRunner
    runner = ModuleRunner("counter_uas")
    results = runner.run_mock(runs_per_scenario=50)
    runner.export_results(results, "outputs/counter_uas")
"""

import json
import random
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

import yaml

logger = logging.getLogger("mirofish.portal.runner")
TEMPLATES_DIR = Path(__file__).parent


def _variance(base):
    return base * (0.8 + random.random() * 0.4)


class ModuleRunner:
    """Generic runner for any portal module."""

    def __init__(self, module_id: str, llm=None):
        self.module_id = module_id
        self.llm = llm
        self.template_dir = TEMPLATES_DIR / module_id
        yaml_path = self.template_dir / "template.yaml"

        if not yaml_path.exists():
            raise FileNotFoundError(f"Template not found: {yaml_path}")

        with open(yaml_path, "r", encoding="utf-8") as f:
            self.template = yaml.safe_load(f)

        self.name = self.template.get("display_name", self.template.get("name", module_id))
        self.scenarios = self.template.get("scenarios", [])
        self.configs = self.template.get("comparison_configurations", [])
        self.agent_profiles = self.template.get("agent_profiles", {})

        # If no configs defined, create default BASELINE/DRONE
        if not self.configs:
            self.configs = [
                {"id": "BASELINE", "name": "No drone", "drone_config": None},
                {"id": "SINGLE_DRONE", "name": "Single drone", "drone_config": {"tethered": 1, "rapid_response": 0}},
                {"id": "FULL", "name": "Full drone system", "drone_config": {"tethered": 1, "rapid_response": 2}},
            ]

    def run_mock(self, runs_per_scenario: int = 50, progress_fn=None) -> Dict[str, Any]:
        """Run mock simulation — no LLM needed."""
        results = {}
        total = len(self.scenarios) * len(self.configs) * runs_per_scenario
        completed = 0

        for sc in self.scenarios:
            sc_id = sc.get("id", f"SC-{len(results)+1}")
            results[sc_id] = {
                "name": sc.get("name", sc_id),
                "category": sc.get("category", "general"),
                "configs": {},
            }

            for ci, cfg in enumerate(self.configs):
                timelines = []
                cfg_id = cfg.get("id", "BASELINE")
                drone_cfg = cfg.get("drone_config") or {}
                has_tethered = (drone_cfg.get("tethered", 0) > 0) if drone_cfg else False
                has_rapid = (drone_cfg.get("rapid_response", 0) > 0) if drone_cfg else False

                # Infer drone capability from config position if not explicit
                # First config = baseline (no drone), middle = partial, last = full
                if not has_tethered and not has_rapid and len(self.configs) >= 2:
                    if ci == 0:
                        has_tethered = False
                        has_rapid = False
                    elif ci == len(self.configs) - 1:
                        has_tethered = True
                        has_rapid = True
                    else:
                        has_tethered = True
                        has_rapid = False

                for run_num in range(runs_per_scenario):
                    completed += 1
                    tl = self._mock_run(sc, has_tethered, has_rapid)
                    timelines.append(tl)

                    if progress_fn and completed % 100 == 0:
                        progress_fn(completed, total, f"{sc_id} × {cfg_id}")

                results[sc_id]["configs"][cfg_id] = timelines

        return results

    def _mock_run(self, scenario: Dict, has_tethered: bool, has_rapid: bool) -> Dict:
        """Single mock run using random variance model."""
        trigger_minute = scenario.get("trigger_minute", 30)
        severity = scenario.get("severity", "high")
        category = scenario.get("category", "general")

        t0 = trigger_minute * 60.0

        # Detection — drone detects faster
        if has_tethered and category in ("crowd_safety", "operational", "public_safety", "industrial"):
            t1 = t0 + _variance(12)
        elif has_tethered:
            t1 = t0 + _variance(25)
        else:
            t1 = t0 + _variance(60)

        # VOC awareness
        t2 = t1 + (_variance(8) if has_tethered else _variance(25))

        # Verification
        if has_rapid and severity in ("critical", "high"):
            t3 = t2 + _variance(35)
        elif has_tethered:
            t3 = t2 + _variance(20)
        else:
            t3 = t2 + _variance(150)

        # Decision
        sf = {"critical": 1.2, "high": 1.0, "moderate": 0.8}.get(severity, 1.0)
        t4 = t3 + (_variance(20 * sf) if has_tethered else _variance(45 * sf))

        # Response
        base_travel = 120
        t5 = t4 + (_variance(base_travel * 0.7) if has_rapid else _variance(base_travel))

        # Resolution
        res_base = {"critical": 600, "high": 360, "moderate": 180}.get(severity, 300)
        if has_tethered and has_rapid:
            t6 = t5 + _variance(res_base * 0.6)
        elif has_tethered:
            t6 = t5 + _variance(res_base * 0.75)
        else:
            t6 = t5 + _variance(res_base)

        return {
            "timestamps": {f"T{i}": round(v, 1) for i, v in enumerate([t0, t1, t2, t3, t4, t5, t6])},
            "kpi": {
                "detection_latency": round(t1 - t0, 1),
                "verification_time": round(t3 - t1, 1),
                "decision_time": round(t4 - t3, 1),
                "response_time": round(t5 - t4, 1),
                "total_resolution": round(t6 - t0, 1),
            },
        }

    def get_summary(self, results: Dict) -> Dict[str, Any]:
        """Aggregate KPI summary from results."""
        master = {}
        for sc_id, sdata in results.items():
            for cfg_id, runs in sdata.get("configs", {}).items():
                for r in runs:
                    for k, v in r.get("kpi", {}).items():
                        master.setdefault(cfg_id, {}).setdefault(k, []).append(v)

        summary = {}
        for cfg_id, kpis in master.items():
            summary[cfg_id] = {}
            for k, vals in kpis.items():
                n = len(vals)
                mean = sum(vals) / n
                std = (sum((v - mean) ** 2 for v in vals) / max(n - 1, 1)) ** 0.5
                summary[cfg_id][k] = {"mean": round(mean, 1), "std": round(std, 1), "n": n}

        return summary

    def format_summary_text(self, results: Dict) -> str:
        """Format results as printable KPI table."""
        summary = self.get_summary(results)
        lines = [
            f"{'='*70}",
            f"  {self.name}",
            f"  {len(self.scenarios)} scenarios × {len(self.configs)} configs",
            f"{'='*70}",
            "",
        ]

        config_ids = list(summary.keys())
        header = f"{'KPI':<25}" + "".join(f"{c:>15}" for c in config_ids)
        lines.append(header)
        lines.append("-" * len(header))

        kpi_keys = ["detection_latency", "verification_time", "decision_time", "response_time", "total_resolution"]
        kpi_labels = {"detection_latency": "Detection", "verification_time": "Verification",
                      "decision_time": "Decision", "response_time": "Response", "total_resolution": "Total Resolution"}

        for kk in kpi_keys:
            row = f"{kpi_labels.get(kk, kk):<25}"
            for cfg_id in config_ids:
                kpi = summary.get(cfg_id, {}).get(kk, {})
                row += f"{kpi.get('mean', 0):>10.1f}s ±{kpi.get('std', 0):.0f}"
            lines.append(row)

        # Improvement (first config vs last config)
        if len(config_ids) >= 2:
            best = config_ids[-1]
            lines.append("")
            lines.append(f"Improvement ({config_ids[0]} → {best}):")
            for kk in kpi_keys:
                bm = summary[config_ids[0]].get(kk, {}).get("mean", 0)
                fm = summary[best].get(kk, {}).get("mean", 0)
                imp = round((1 - fm / bm) * 100) if bm > 0 else 0
                lines.append(f"  {kpi_labels.get(kk, kk):<23} -{imp}%")

        lines.append(f"\n{'='*70}")
        return "\n".join(lines)

    def export_results(self, results: Dict, output_dir: str):
        """Export results to JSON + summary text."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        with open(out / "mock_results.json", "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        summary_text = self.format_summary_text(results)
        with open(out / "mock_summary.txt", "w") as f:
            f.write(summary_text)

        return summary_text
