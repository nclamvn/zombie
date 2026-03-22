"""
Scenario Comparison Engine — TIP-11

Fork simulations, run variants, compare outcomes.
"What if regulation is lighter?" "What if we have 2 policy options?"

Features:
1. Fork: clone project → modify config → run as new scenario
2. Compare: side-by-side metrics between 2+ scenarios
3. Divergence detection: find where scenarios diverge
4. Comparative report: LLM generates analysis of differences
"""

import json
import uuid
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field

from ..interfaces.llm_provider import LLMProvider
from ..tools.logger import get_logger

logger = get_logger("mirofish.pipeline.scenario")


@dataclass
class ScenarioResult:
    """Summary of a single scenario's simulation outcome."""
    scenario_id: str
    scenario_name: str
    project_id: str
    total_rounds: int = 0
    total_actions: int = 0
    total_agents: int = 0
    action_distribution: Dict[str, int] = field(default_factory=dict)
    top_agents: List[Dict[str, Any]] = field(default_factory=list)
    content_created: int = 0
    config_overrides: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "project_id": self.project_id,
            "total_rounds": self.total_rounds,
            "total_actions": self.total_actions,
            "total_agents": self.total_agents,
            "action_distribution": self.action_distribution,
            "top_agents": self.top_agents,
            "content_created": self.content_created,
            "config_overrides": self.config_overrides,
        }


@dataclass
class ComparisonResult:
    """Result of comparing 2+ scenarios."""
    scenarios: List[ScenarioResult]
    divergence_points: List[Dict[str, Any]] = field(default_factory=list)
    comparative_analysis: str = ""
    recommendation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenarios": [s.to_dict() for s in self.scenarios],
            "divergence_points": self.divergence_points,
            "comparative_analysis": self.comparative_analysis,
            "recommendation": self.recommendation,
        }


COMPARE_PROMPT = """You are an expert analyst comparing multiple simulation scenarios.

## Scenarios
{scenarios_json}

## Requirement
{requirement}

Analyze the differences between these scenarios and provide:
1. **Key Differences**: What changed between scenarios and how it affected outcomes
2. **Divergence Points**: At what point did the scenarios start producing different results, and why
3. **Sensitivity Analysis**: Which parameters had the most impact on outcomes
4. **Recommendation**: Based on the comparison, which scenario is most favorable and why

Be specific with numbers. Reference agent names and action counts.
Write 400-800 words in markdown format.
"""


class ScenarioEngine:
    """
    Manages scenario forking, comparison, and comparative analysis.

    Usage:
        engine = ScenarioEngine(llm)

        # Create scenario results from simulation summaries
        s1 = engine.create_result("baseline", project_id, sim_summary)
        s2 = engine.create_result("light_regulation", project_id2, sim_summary2)

        # Compare
        comparison = engine.compare([s1, s2], requirement="...")
    """

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def create_result(
        self,
        scenario_name: str,
        project_id: str,
        simulation_summary: Dict[str, Any],
        config_overrides: Dict[str, Any] = None,
    ) -> ScenarioResult:
        """Create a ScenarioResult from a simulation summary."""
        return ScenarioResult(
            scenario_id=f"scn_{uuid.uuid4().hex[:8]}",
            scenario_name=scenario_name,
            project_id=project_id,
            total_rounds=simulation_summary.get("total_rounds", 0),
            total_actions=simulation_summary.get("total_actions", 0),
            total_agents=simulation_summary.get("total_agents", 0),
            action_distribution=simulation_summary.get("action_type_distribution", {}),
            top_agents=simulation_summary.get("top_active_agents", []),
            content_created=simulation_summary.get("content_created", 0),
            config_overrides=config_overrides or {},
        )

    def compare(
        self,
        scenarios: List[ScenarioResult],
        requirement: str = "",
        rounds_data: Optional[Dict[str, List[Dict]]] = None,
    ) -> ComparisonResult:
        """
        Compare 2+ scenario results.

        Args:
            scenarios: List of ScenarioResult objects
            requirement: Original simulation requirement
            rounds_data: Optional {scenario_id: [round_dicts]} for divergence detection
        """
        if len(scenarios) < 2:
            return ComparisonResult(scenarios=scenarios, comparative_analysis="Need at least 2 scenarios to compare.")

        # Detect divergence points if rounds data available
        divergence = []
        if rounds_data and len(rounds_data) >= 2:
            divergence = self._detect_divergence(scenarios, rounds_data)

        # Generate comparative analysis via LLM
        scenarios_json = json.dumps([s.to_dict() for s in scenarios], indent=2, ensure_ascii=False)

        try:
            analysis = self.llm.chat(
                messages=[
                    {"role": "system", "content": COMPARE_PROMPT.format(
                        scenarios_json=scenarios_json,
                        requirement=requirement,
                    )},
                    {"role": "user", "content": "Compare these scenarios and provide your analysis."},
                ],
                temperature=0.4,
                max_tokens=3000,
            )
        except Exception as e:
            logger.error(f"Comparative analysis failed: {e}")
            analysis = f"Comparative analysis generation failed: {e}"

        # Extract recommendation
        recommendation = ""
        if "recommendation" in analysis.lower():
            parts = analysis.split("Recommendation")
            if len(parts) > 1:
                recommendation = parts[-1][:500].strip().lstrip(":").lstrip("*").strip()

        return ComparisonResult(
            scenarios=scenarios,
            divergence_points=divergence,
            comparative_analysis=analysis,
            recommendation=recommendation,
        )

    def generate_sensitivity_matrix(
        self,
        scenarios: List[ScenarioResult],
    ) -> Dict[str, Any]:
        """Generate a simple sensitivity analysis matrix."""
        if len(scenarios) < 2:
            return {"parameters": [], "impacts": []}

        baseline = scenarios[0]
        impacts = []

        for s in scenarios[1:]:
            diff = {
                "scenario": s.scenario_name,
                "vs_baseline": baseline.scenario_name,
                "overrides": s.config_overrides,
                "delta_actions": s.total_actions - baseline.total_actions,
                "delta_actions_pct": (
                    ((s.total_actions - baseline.total_actions) / max(baseline.total_actions, 1)) * 100
                ),
                "delta_content": s.content_created - baseline.content_created,
            }

            # Compare action distributions
            all_types = set(list(baseline.action_distribution.keys()) + list(s.action_distribution.keys()))
            dist_changes = {}
            for at in all_types:
                base_count = baseline.action_distribution.get(at, 0)
                scn_count = s.action_distribution.get(at, 0)
                if base_count or scn_count:
                    dist_changes[at] = {
                        "baseline": base_count,
                        "scenario": scn_count,
                        "delta": scn_count - base_count,
                    }
            diff["action_changes"] = dist_changes
            impacts.append(diff)

        return {
            "baseline": baseline.scenario_name,
            "impacts": impacts,
        }

    def _detect_divergence(
        self,
        scenarios: List[ScenarioResult],
        rounds_data: Dict[str, List[Dict]],
    ) -> List[Dict[str, Any]]:
        """Detect rounds where scenarios diverge significantly."""
        divergence = []
        ids = [s.scenario_id for s in scenarios if s.scenario_id in rounds_data]
        if len(ids) < 2:
            return []

        r1 = rounds_data[ids[0]]
        r2 = rounds_data[ids[1]]
        min_rounds = min(len(r1), len(r2))

        for i in range(min_rounds):
            a1 = r1[i].get("actions_count", 0) if isinstance(r1[i], dict) else 0
            a2 = r2[i].get("actions_count", 0) if isinstance(r2[i], dict) else 0
            diff = abs(a1 - a2)

            if diff > max(a1, a2, 1) * 0.5 and diff > 3:
                divergence.append({
                    "round": i + 1,
                    "scenario_a": {"id": ids[0], "actions": a1},
                    "scenario_b": {"id": ids[1], "actions": a2},
                    "delta": diff,
                    "significance": "high" if diff > max(a1, a2, 1) * 0.8 else "moderate",
                })

        return divergence
