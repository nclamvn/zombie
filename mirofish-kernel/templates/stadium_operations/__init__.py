"""
Stadium Operations Template Loader — MiroFish Kernel Integration

Loads the stadium_operations template and configures the MiroFish
pipeline for stadium command-and-control decision simulation.

Usage:
    from templates.stadium_operations import StadiumSimulation
    
    sim = StadiumSimulation(
        llm=OpenAIAdapter(api_key="..."),
        graph_store=ZepGraphAdapter(api_key="..."),
    )
    
    # Run all 12 scenarios × 3 configs
    results = sim.run_full_comparison(
        seed_text=open("my_dinh_stadium_seed.txt").read(),
        runs_per_scenario=50,
    )
    
    # Generate FIFA report
    report = sim.generate_fifa_report(results)
"""

import os
import json
import yaml
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from pathlib import Path


TEMPLATE_DIR = Path(__file__).parent
TEMPLATE_PATH = TEMPLATE_DIR / "template.yaml"
PROMPTS_DIR = TEMPLATE_DIR / "prompts"


@dataclass
class IncidentTimeline:
    """Timestamps for a single incident resolution."""
    scenario_id: str
    config_id: str          # BASELINE, TETHERED, FULL
    run_number: int
    t0_occurrence: float    # seconds from sim start
    t1_detection: float
    t2_voc_awareness: float
    t3_verification: float
    t4_decision: float
    t5_responder_arrival: float
    t6_resolution: float
    
    @property
    def detection_latency(self) -> float:
        return self.t1_detection - self.t0_occurrence
    
    @property
    def verification_time(self) -> float:
        return self.t3_verification - self.t1_detection
    
    @property
    def decision_time(self) -> float:
        return self.t4_decision - self.t3_verification
    
    @property
    def response_time(self) -> float:
        return self.t5_responder_arrival - self.t4_decision
    
    @property
    def total_resolution(self) -> float:
        return self.t6_resolution - self.t0_occurrence
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "config_id": self.config_id,
            "run_number": self.run_number,
            "timestamps": {
                "T0_occurrence": self.t0_occurrence,
                "T1_detection": self.t1_detection,
                "T2_voc_awareness": self.t2_voc_awareness,
                "T3_verification": self.t3_verification,
                "T4_decision": self.t4_decision,
                "T5_responder_arrival": self.t5_responder_arrival,
                "T6_resolution": self.t6_resolution,
            },
            "kpi": {
                "detection_latency_sec": round(self.detection_latency, 1),
                "verification_time_sec": round(self.verification_time, 1),
                "decision_time_sec": round(self.decision_time, 1),
                "response_time_sec": round(self.response_time, 1),
                "total_resolution_sec": round(self.total_resolution, 1),
            }
        }


@dataclass
class ScenarioComparison:
    """Comparison results for one scenario across configurations."""
    scenario_id: str
    scenario_name: str
    category: str
    timelines: Dict[str, List[IncidentTimeline]] = field(default_factory=dict)
    # config_id → list of timelines from multiple runs
    
    def get_kpi_stats(self, config_id: str, kpi_name: str) -> Dict[str, float]:
        """Calculate mean, std, min, max for a KPI across runs."""
        values = []
        for tl in self.timelines.get(config_id, []):
            values.append(getattr(tl, kpi_name))
        
        if not values:
            return {"mean": 0, "std": 0, "min": 0, "max": 0, "n": 0}
        
        n = len(values)
        mean = sum(values) / n
        variance = sum((v - mean) ** 2 for v in values) / max(n - 1, 1)
        std = variance ** 0.5
        
        return {
            "mean": round(mean, 1),
            "std": round(std, 1),
            "min": round(min(values), 1),
            "max": round(max(values), 1),
            "n": n,
        }
    
    def improvement_percent(self, kpi_name: str, baseline: str = "BASELINE", compare: str = "FULL") -> float:
        """Calculate percentage improvement from baseline to compare config."""
        base_stats = self.get_kpi_stats(baseline, kpi_name)
        comp_stats = self.get_kpi_stats(compare, kpi_name)
        
        if base_stats["mean"] == 0:
            return 0.0
        
        return round((1 - comp_stats["mean"] / base_stats["mean"]) * 100, 1)


def load_template() -> Dict[str, Any]:
    """Load the stadium_operations template YAML."""
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_prompt(name: str) -> str:
    """Load a prompt template by name."""
    path = PROMPTS_DIR / f"{name}.txt"
    if path.exists():
        return path.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Prompt not found: {path}")


class StadiumSimulation:
    """
    Orchestrates stadium operations simulation using MiroFish kernel.
    
    Runs each scenario under each configuration, collects KPIs,
    and generates FIFA-ready comparison reports.
    """
    
    def __init__(self, llm=None, graph_store=None, simulation_engine=None):
        """
        Args:
            llm: LLMProvider implementation (None = mock mode)
            graph_store: GraphStore implementation
            simulation_engine: Optional SimulationEngine (uses MockEngine if None)
        """
        self.llm = llm
        self.graph_store = graph_store
        self.simulation_engine = simulation_engine
        self.template = load_template()
        self.agent_decision_prompt = load_prompt("agent_decision")
        self.orchestrator_prompt = load_prompt("scenario_orchestrator")
        self.report_prompt = load_prompt("comparison_report")

        # TIP-18: LLM-powered agent engine (when LLM available)
        self._agent_engine = None
        self._scenario_orchestrator = None
        if llm is not None:
            try:
                from .agent_engine import AgentDecisionEngine
                from .scenario_orchestrator import ScenarioOrchestrator as ScOrc
                self._agent_engine = AgentDecisionEngine(llm)
                self._scenario_orchestrator = ScOrc(llm, self._agent_engine)
            except Exception as e:
                import logging
                logging.getLogger("mirofish.stadium").warning(f"LLM agent engine init failed: {e}")
    
    def run_full_comparison(
        self,
        seed_text: str,
        runs_per_scenario: int = 50,
        scenarios: Optional[List[str]] = None,
        progress_callback=None,
    ) -> Dict[str, ScenarioComparison]:
        """
        Run all scenarios across all configurations.
        
        Args:
            seed_text: Stadium operational profile (seed text)
            runs_per_scenario: How many randomized runs per scenario per config
            scenarios: Optional filter — list of scenario IDs to run
            progress_callback: Optional (message, progress) callback
            
        Returns:
            Dict of scenario_id → ScenarioComparison
        """
        # Import MiroFish kernel components
        from core.pipeline import (
            SeedProcessor, OntologyDesigner, GraphBuilder,
            ConfigGenerator, ProfileGenerator, RetrievalTools, ReportAgent,
        )
        
        all_scenarios = self.template["scenarios"]
        if scenarios:
            all_scenarios = [s for s in all_scenarios if s["id"] in scenarios]
        
        configs = self.template["comparison_configurations"]
        
        total_runs = len(all_scenarios) * len(configs) * runs_per_scenario
        completed = 0
        
        # Step 1: Build knowledge graph from seed text
        if progress_callback:
            progress_callback("Building stadium knowledge graph...", 0.0)
        
        seed_processor = SeedProcessor(chunk_size=500)
        seed_result = seed_processor.process_text(seed_text, requirement="Stadium operations simulation")
        
        ontology_designer = OntologyDesigner(
            self.llm,
            system_prompt=self.template["ontology_prompt"],
        )
        ontology = ontology_designer.design(
            document_texts=[seed_result["raw_text"]],
            requirement="Stadium VOC decision chain simulation with drone augmentation",
        )
        
        graph_builder = GraphBuilder(self.graph_store)
        graph_result = graph_builder.build(
            chunks=seed_result["chunks"],
            ontology=ontology,
            graph_name="Stadium Operations Graph",
        )
        
        if not graph_result.success:
            raise RuntimeError(f"Graph build failed: {graph_result.error}")
        
        if progress_callback:
            progress_callback(
                f"Graph built: {graph_result.graph_info.node_count} nodes, "
                f"{graph_result.graph_info.edge_count} edges",
                0.1,
            )
        
        # Step 2: Generate agent profiles
        profile_gen = ProfileGenerator(self.llm, self.graph_store)
        profiles = profile_gen.generate_profiles(
            graph_id=graph_result.graph_id,
            requirement="Stadium VOC command chain agents for safety simulation",
        )
        
        if progress_callback:
            progress_callback(f"Generated {len(profiles)} agent profiles", 0.15)
        
        # Step 3: Run scenarios
        results: Dict[str, ScenarioComparison] = {}
        
        for scenario in all_scenarios:
            comparison = ScenarioComparison(
                scenario_id=scenario["id"],
                scenario_name=scenario["name"],
                category=scenario["category"],
            )
            
            for config in configs:
                config_timelines = []
                
                for run in range(runs_per_scenario):
                    completed += 1
                    
                    if progress_callback:
                        pct = 0.15 + (completed / total_runs) * 0.75
                        progress_callback(
                            f"[{completed}/{total_runs}] {scenario['id']} × {config['id']} run {run+1}",
                            pct,
                        )
                    
                    # Simulate this scenario under this config
                    timeline = self._simulate_single_run(
                        scenario=scenario,
                        config=config,
                        graph_id=graph_result.graph_id,
                        profiles=profiles,
                        run_number=run,
                    )
                    config_timelines.append(timeline)
                
                comparison.timelines[config["id"]] = config_timelines
            
            results[scenario["id"]] = comparison
        
        if progress_callback:
            progress_callback("All scenarios complete", 0.90)
        
        return results
    
    def _simulate_single_run(
        self,
        scenario: Dict,
        config: Dict,
        graph_id: str,
        profiles: list,
        run_number: int,
    ) -> IncidentTimeline:
        """
        Simulate a single scenario run. TIP-18: uses LLM when available,
        falls back to mock random model otherwise.
        """
        if self._scenario_orchestrator is not None:
            return self._simulate_llm_run(scenario, config, run_number)
        return self._simulate_mock_run(scenario, config, run_number)

    def _simulate_llm_run(
        self,
        scenario: Dict,
        config: Dict,
        run_number: int,
    ) -> IncidentTimeline:
        """LLM-powered simulation run. TIP-18."""
        agent_profiles = self.template.get("agent_profiles", {})
        result = self._scenario_orchestrator.run_scenario(
            scenario=scenario,
            config=config,
            agent_profiles=agent_profiles,
            stadium_config=self.template.get("default_config", {}).get("stadium"),
        )
        ts = result["timestamps"]
        return IncidentTimeline(
            scenario_id=scenario["id"],
            config_id=config["id"],
            run_number=run_number,
            t0_occurrence=ts["T0"],
            t1_detection=ts["T1"],
            t2_voc_awareness=ts["T2"],
            t3_verification=ts["T3"],
            t4_decision=ts["T4"],
            t5_responder_arrival=ts["T5"],
            t6_resolution=ts["T6"],
        )

    def _simulate_mock_run(
        self,
        scenario: Dict,
        config: Dict,
        run_number: int,
    ) -> IncidentTimeline:
        """
        Mock simulation using random variance model. No LLM required.
        Original implementation preserved as fallback.
        """
        import random
        
        trigger_minute = scenario["trigger_minute"]
        config_id = config["id"]
        
        # Base detection time depends on configuration
        has_tethered = config.get("drone_config") and config["drone_config"].get("tethered", 0) > 0
        has_rapid = config.get("drone_config") and config["drone_config"].get("rapid_response", 0) > 0
        
        # Randomization: add realistic variance (± 20%)
        variance = lambda base: base * (0.8 + random.random() * 0.4)
        
        # T0: incident occurs
        t0 = trigger_minute * 60.0  # convert to seconds
        
        # T1: detection time depends on sensors available
        if has_tethered and scenario["category"] in ["crowd_safety", "operational"]:
            # Tethered drone may detect crowd/operational issues fast
            t1 = t0 + variance(12)  # 8-16 seconds
        elif has_tethered:
            t1 = t0 + variance(25)  # 20-30 seconds (not optimized for this type)
        else:
            # Baseline: steward notice or CCTV operator catch
            t1 = t0 + variance(60)  # 48-72 seconds
        
        # T2: VOC awareness (report reaches command)
        if has_tethered:
            t2 = t1 + variance(8)   # Direct feed already on monitor
        else:
            t2 = t1 + variance(25)  # Radio report + dispatcher relay
        
        # T3: verification complete
        if has_rapid and scenario["severity"] in ["critical", "high"]:
            # Deploy rapid drone for close verification
            t3 = t2 + variance(35)  # 28-42 seconds (deploy + arrive + assess)
        elif has_tethered:
            # Check tethered feed or reposition
            t3 = t2 + variance(20)  # 16-24 seconds
        else:
            # Send steward or find CCTV angle
            t3 = t2 + variance(150) # 120-180 seconds
        
        # T4: decision made
        severity_factor = {"critical": 1.2, "high": 1.0, "moderate": 0.8}.get(scenario["severity"], 1.0)
        if has_tethered:
            # Higher confidence → faster decision
            t4 = t3 + variance(20 * severity_factor)
        else:
            t4 = t3 + variance(45 * severity_factor)
        
        # T5: responder arrival
        base_travel = 120  # 2 minutes average travel in stadium
        if has_rapid:
            # Drone can guide optimal route
            t5 = t4 + variance(base_travel * 0.7)  # 30% faster routing
        else:
            t5 = t4 + variance(base_travel)
        
        # T6: resolution
        if scenario["severity"] == "critical":
            resolution_base = 600  # 10 minutes for critical
        elif scenario["severity"] == "high":
            resolution_base = 360  # 6 minutes
        else:
            resolution_base = 180  # 3 minutes
        
        # Drone augmentation improves resolution through better coordination
        if has_tethered and has_rapid:
            t6 = t5 + variance(resolution_base * 0.6)
        elif has_tethered:
            t6 = t5 + variance(resolution_base * 0.75)
        else:
            t6 = t5 + variance(resolution_base)
        
        return IncidentTimeline(
            scenario_id=scenario["id"],
            config_id=config_id,
            run_number=run_number,
            t0_occurrence=round(t0, 1),
            t1_detection=round(t1, 1),
            t2_voc_awareness=round(t2, 1),
            t3_verification=round(t3, 1),
            t4_decision=round(t4, 1),
            t5_responder_arrival=round(t5, 1),
            t6_resolution=round(t6, 1),
        )
    
    def generate_fifa_report(
        self,
        results: Dict[str, ScenarioComparison],
        progress_callback=None,
    ) -> str:
        """
        Generate FIFA-ready evidence report from simulation results.
        
        Uses MiroFish ReportAgent with comparison_report prompt.
        """
        from core.pipeline import RetrievalTools, ReportAgent
        
        if progress_callback:
            progress_callback("Preparing simulation data for report...", 0.0)
        
        # Build summary data for the report prompt
        summary = self._build_results_summary(results)
        
        if progress_callback:
            progress_callback("Generating FIFA evidence report...", 0.2)
        
        # Generate report via LLM
        messages = [
            {"role": "system", "content": self.report_prompt},
            {"role": "user", "content": json.dumps(summary, indent=2, ensure_ascii=False)},
        ]
        
        report = self.llm.chat(
            messages=messages,
            temperature=0.3,
            max_tokens=8192,
        )
        
        if progress_callback:
            progress_callback("Report complete", 1.0)
        
        return report
    
    def _build_results_summary(
        self, results: Dict[str, ScenarioComparison]
    ) -> Dict[str, Any]:
        """Build structured summary for the report LLM."""
        summary = {
            "total_scenarios": len(results),
            "configurations": ["BASELINE", "TETHERED", "FULL"],
            "scenario_results": [],
            "kpi_master_table": [],
        }
        
        for scenario_id, comparison in results.items():
            scenario_data = {
                "id": comparison.scenario_id,
                "name": comparison.scenario_name,
                "category": comparison.category,
                "kpi_comparison": {},
            }
            
            for kpi_name in [
                "detection_latency", "verification_time",
                "decision_time", "response_time", "total_resolution"
            ]:
                kpi_data = {}
                for config_id in ["BASELINE", "TETHERED", "FULL"]:
                    kpi_data[config_id] = comparison.get_kpi_stats(config_id, kpi_name)
                
                kpi_data["improvement_tethered_pct"] = comparison.improvement_percent(
                    kpi_name, "BASELINE", "TETHERED"
                )
                kpi_data["improvement_full_pct"] = comparison.improvement_percent(
                    kpi_name, "BASELINE", "FULL"
                )
                
                scenario_data["kpi_comparison"][kpi_name] = kpi_data
            
            summary["scenario_results"].append(scenario_data)
        
        # Build master KPI table
        for kpi_name in ["verification_time", "total_resolution"]:
            all_baselines = []
            all_fulls = []
            for comp in results.values():
                for tl in comp.timelines.get("BASELINE", []):
                    all_baselines.append(getattr(tl, kpi_name))
                for tl in comp.timelines.get("FULL", []):
                    all_fulls.append(getattr(tl, kpi_name))
            
            if all_baselines and all_fulls:
                baseline_mean = sum(all_baselines) / len(all_baselines)
                full_mean = sum(all_fulls) / len(all_fulls)
                improvement = round((1 - full_mean / baseline_mean) * 100, 1) if baseline_mean > 0 else 0
                
                summary["kpi_master_table"].append({
                    "kpi": kpi_name,
                    "baseline_mean_sec": round(baseline_mean, 1),
                    "full_mean_sec": round(full_mean, 1),
                    "improvement_pct": improvement,
                    "total_runs": len(all_baselines) + len(all_fulls),
                })
        
        return summary
    
    def export_raw_data(
        self,
        results: Dict[str, ScenarioComparison],
        output_path: str,
    ) -> None:
        """Export all raw timeline data as JSON for further analysis."""
        export = {}
        for scenario_id, comparison in results.items():
            export[scenario_id] = {
                "name": comparison.scenario_name,
                "category": comparison.category,
                "configs": {},
            }
            for config_id, timelines in comparison.timelines.items():
                export[scenario_id]["configs"][config_id] = [
                    tl.to_dict() for tl in timelines
                ]
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export, f, indent=2, ensure_ascii=False)
