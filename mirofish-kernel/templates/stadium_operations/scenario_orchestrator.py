"""
Stadium Operations — Scenario Orchestrator (TIP-18)

Runs a single scenario through 6 phases, querying LLM agents
at each phase to produce realistic IncidentTimeline timestamps.
4-8 LLM calls per scenario run for cost control.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from .agent_engine import (
    AgentDecisionEngine, AgentDecision,
    DETECTION_AGENTS, VERIFICATION_AGENTS,
)

logger = logging.getLogger("mirofish.stadium.orchestrator")


@dataclass
class PhaseResult:
    """Result of one simulation phase."""
    phase: str
    timestamp: float  # seconds from scenario start
    decisions: List[AgentDecision] = field(default_factory=list)
    summary: str = ""


class ScenarioOrchestrator:
    """
    Runs a single scenario: injects incident, collects agent decisions
    round by round, tracks timestamps T0→T6, measures KPIs.

    Cost target: 4-8 LLM calls per scenario run.
    """

    def __init__(self, llm, agent_engine: AgentDecisionEngine):
        self.llm = llm
        self.engine = agent_engine

    def run_scenario(
        self,
        scenario: Dict[str, Any],
        config: Dict[str, Any],
        agent_profiles: Dict[str, Any],
        stadium_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Run one scenario under one configuration.

        Returns dict compatible with IncidentTimeline:
        {
            "timestamps": {"T0": ..., "T1": ..., ..., "T6": ...},
            "kpi": {"detection_latency": ..., ...},
            "decisions": [AgentDecision.to_dict(), ...],
        }
        """
        config_id = config.get("id", "BASELINE")
        trigger_minute = scenario.get("trigger_minute", 60)
        severity = scenario.get("severity", "high")
        category = scenario.get("category", "crowd_safety")

        all_decisions = []
        t0 = trigger_minute * 60.0  # T0: incident occurs

        # ── Phase 1: DETECTION ──────────────────────────────────
        # Query detection agents based on config
        detection_agents = DETECTION_AGENTS.get(config_id, ["StewardSupervisor"])
        det_results = []

        for agent_type in detection_agents:
            profile = agent_profiles.get(agent_type, {
                "role": agent_type,
                "authority_level": 2,
                "response_baseline_sec": 15,
            })
            decision = self.engine.get_decision(
                agent_profile=profile,
                scenario=scenario,
                config=config,
                current_minute=trigger_minute,
                known_information=[],
                available_resources=self._get_resources(config_id),
                phase="detect",
            )
            det_results.append(decision)
            all_decisions.append(decision)

        # T1: earliest detection
        t1 = t0 + min(d.estimated_total_seconds for d in det_results) if det_results else t0 + 60

        # ── Phase 2: VOC AWARENESS ─────────────────────────────
        # T2: report reaches VOC (radio relay)
        # Config-dependent: drone feeds directly to VOC (fast), steward radios (slower)
        has_drone = config_id in ("TETHERED", "FULL")
        t2 = t1 + (8 if has_drone else 25)

        # ── Phase 3: VERIFICATION ──────────────────────────────
        # Query VOC for verification decision
        voc_profile = agent_profiles.get("VenueOperationsCenter", {
            "role": "Venue Operations Centre — central command",
            "authority_level": 5,
            "response_baseline_sec": 30,
        })
        det_reports = [f"{d.agent_type}: {d.assessment}" for d in det_results]

        voc_verify = self.engine.get_decision(
            agent_profile=voc_profile,
            scenario=scenario,
            config=config,
            current_minute=trigger_minute + int((t2 - t0) / 60),
            known_information=det_reports,
            available_resources=self._get_resources(config_id),
            phase="verify",
        )
        all_decisions.append(voc_verify)
        t3 = t2 + voc_verify.estimated_total_seconds

        # ── Phase 4: DECISION ──────────────────────────────────
        # VOC classifies and decides response
        voc_decide = self.engine.get_decision(
            agent_profile=voc_profile,
            scenario=scenario,
            config=config,
            current_minute=trigger_minute + int((t3 - t0) / 60),
            known_information=det_reports + [f"Verification: {voc_verify.decision}"],
            available_resources=self._get_resources(config_id),
            phase="decide",
        )
        all_decisions.append(voc_decide)
        t4 = t3 + voc_decide.estimated_total_seconds

        # ── Phase 5: RESPONSE ──────────────────────────────────
        # Query appropriate responder
        responder_type = self._pick_responder(category)
        responder_profile = agent_profiles.get(responder_type, {
            "role": responder_type,
            "authority_level": 3,
            "response_baseline_sec": 60,
        })
        resp_info = det_reports + [
            f"VOC decision: {voc_decide.decision}",
            f"Your orders: respond to {scenario.get('name', 'incident')}",
        ]
        if has_drone and config_id == "FULL":
            resp_info.append("Drone providing route guidance to incident location")

        responder_decision = self.engine.get_decision(
            agent_profile=responder_profile,
            scenario=scenario,
            config=config,
            current_minute=trigger_minute + int((t4 - t0) / 60),
            known_information=resp_info,
            available_resources=self._get_resources(config_id),
            phase="respond",
        )
        all_decisions.append(responder_decision)
        t5 = t4 + responder_decision.estimated_total_seconds

        # ── Phase 6: RESOLUTION ────────────────────────────────
        # Estimate resolution based on severity
        severity_factor = {"critical": 1.5, "high": 1.0, "moderate": 0.7}.get(severity, 1.0)
        base_resolution = 180 * severity_factor
        # Drone improves coordination → faster resolution
        if config_id == "FULL":
            base_resolution *= 0.6
        elif config_id == "TETHERED":
            base_resolution *= 0.75

        t6 = t5 + base_resolution

        # ── Build result ───────────────────────────────────────
        return {
            "timestamps": {
                "T0": round(t0, 1), "T1": round(t1, 1), "T2": round(t2, 1),
                "T3": round(t3, 1), "T4": round(t4, 1), "T5": round(t5, 1),
                "T6": round(t6, 1),
            },
            "kpi": {
                "detection_latency": round(t1 - t0, 1),
                "verification_time": round(t3 - t1, 1),
                "decision_time": round(t4 - t3, 1),
                "response_time": round(t5 - t4, 1),
                "total_resolution": round(t6 - t0, 1),
            },
            "decisions": [d.to_dict() for d in all_decisions],
            "tokens_used": sum(d.tokens_used for d in all_decisions),
            "llm_calls": len(all_decisions),
        }

    def _pick_responder(self, category: str) -> str:
        """Pick the appropriate responder agent type for a category."""
        mapping = {
            "crowd_safety": "SafetyOfficer",
            "medical": "MedicalCoordinator",
            "security": "PoliceCommander",
            "environmental": "FireSafetyCommander",
            "operational": "SafetyOfficer",
        }
        return mapping.get(category, "SafetyOfficer")

    def _get_resources(self, config_id: str) -> Dict[str, Any]:
        """Resources available by configuration."""
        base = {
            "steward_teams": 4,
            "medical_teams": 12,
            "police_units": 120,
            "fire_team": 1,
            "cctv_cameras": 128,
            "pa_system": True,
            "ambulances": 2,
        }
        if config_id in ("TETHERED", "FULL"):
            base["tethered_drone"] = 1
            base["drone_feed_available"] = True
        if config_id == "FULL":
            base["rapid_response_drones"] = 2
            base["drone_deploy_time_sec"] = 45
        return base
