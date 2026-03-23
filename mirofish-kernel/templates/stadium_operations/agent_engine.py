"""
Stadium Operations — LLM-Powered Agent Decision Engine (TIP-18)

Each agent receives scenario context filtered by their role and config,
then returns a structured decision via LLM reasoning.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("mirofish.stadium.agent_engine")

PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.txt"
    return path.read_text(encoding="utf-8") if path.exists() else ""


MATCH_PHASES = [
    (0, 30, "ingress_early"), (30, 60, "ingress_peak"),
    (60, 90, "match_first_half"), (90, 105, "halftime_surge"),
    (105, 115, "match_second_half"), (115, 120, "egress"),
]


def _get_match_phase(minute: int) -> str:
    for lo, hi, name in MATCH_PHASES:
        if lo <= minute < hi:
            return name
    return "post_match"


# Agents that can detect incidents by config
DETECTION_AGENTS = {
    "BASELINE": ["StewardSupervisor", "CCTVOperator"],
    "TETHERED": ["StewardSupervisor", "CCTVOperator", "DroneOperator"],
    "FULL": ["StewardSupervisor", "CCTVOperator", "DroneOperator"],
}

# Agents involved in verification by config
VERIFICATION_AGENTS = {
    "BASELINE": ["VenueOperationsCenter", "CCTVOperator", "StewardSupervisor"],
    "TETHERED": ["VenueOperationsCenter", "CCTVOperator", "DroneOperator"],
    "FULL": ["VenueOperationsCenter", "DroneOperator"],
}


@dataclass
class AgentDecision:
    """Structured output from an LLM agent decision."""
    agent_type: str
    assessment: str = ""
    decision: str = ""
    actions: List[Dict[str, Any]] = field(default_factory=list)
    communications: List[Dict[str, Any]] = field(default_factory=list)
    resource_requests: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.5
    reasoning: str = ""
    estimated_total_seconds: float = 30.0
    raw_json: Dict[str, Any] = field(default_factory=dict)
    tokens_used: int = 0
    latency_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_type": self.agent_type,
            "assessment": self.assessment,
            "decision": self.decision,
            "actions": self.actions,
            "communications": self.communications,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "estimated_total_seconds": self.estimated_total_seconds,
        }


class AgentDecisionEngine:
    """
    Sends scenario context to LLM, receives agent decision as JSON.
    Each agent has different information based on configuration.
    """

    def __init__(self, llm):
        self.llm = llm
        self.agent_prompt_template = _load_prompt("agent_decision")

    def get_decision(
        self,
        agent_profile: Dict[str, Any],
        scenario: Dict[str, Any],
        config: Dict[str, Any],
        current_minute: int,
        known_information: List[str],
        available_resources: Dict[str, Any],
        phase: str = "detect",
    ) -> AgentDecision:
        """Query LLM for an agent decision given the current context."""
        import time

        agent_type = agent_profile.get("role", "Unknown")
        config_id = config.get("id", "BASELINE")

        # Build config description for prompt
        if config_id == "BASELINE":
            config_desc = (
                "BASELINE: No drone data available. You rely on CCTV feeds "
                "(which have blind spots), radio reports from stewards, and fire detection panels."
            )
        elif config_id == "TETHERED":
            config_desc = (
                "TETHERED: VOC has continuous aerial feed from one tethered drone "
                "positioned over the south parking area. Cannot reposition."
            )
        else:
            config_desc = (
                "FULL: VOC has tethered drone feed PLUS two rapid-response drones "
                "deployable to any location within 45 seconds."
            )

        # Fill prompt template
        prompt = self.agent_prompt_template
        replacements = {
            "{agent_role}": agent_type,
            "{authority_level}": str(agent_profile.get("authority_level", 3)),
            "{zone_assignment}": agent_profile.get("zone_assignment", "All sectors"),
            "{radio_channel}": agent_profile.get("radio_channel", "VOC Main"),
            "{simulation_config}": config_desc,
            "{current_minute}": str(current_minute),
            "{match_phase}": _get_match_phase(current_minute),
            "{attendance}": "37,400",
            "{capacity}": "40,192",
            "{active_incidents}": scenario.get("name", "Unknown incident"),
            "{available_resources}": json.dumps(available_resources, ensure_ascii=False),
            "{incident_description}": scenario.get("description", ""),
        }
        for key, val in replacements.items():
            prompt = prompt.replace(key, val)

        # Add phase-specific instruction
        prompt += f"\n\nCurrent phase: {phase.upper()}. Focus your response on this phase."
        prompt += "\nRespond with valid JSON only. No markdown code blocks."

        # Call LLM
        t0 = time.time()
        try:
            response = self.llm.chat(
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"Incident: {scenario.get('name', '')}. "
                     f"Information available to you: {'; '.join(known_information) if known_information else 'No reports yet — you observe directly.'}"},
                ],
                temperature=0.4,
                max_tokens=800,
            )
            latency = int((time.time() - t0) * 1000)
        except Exception as e:
            logger.warning(f"LLM call failed for {agent_type}: {e}")
            return self._fallback_decision(agent_type, phase)

        # Parse JSON response
        decision = self._parse_response(response, agent_type, phase)
        decision.latency_ms = latency
        # Estimate token count (~4 chars per token)
        decision.tokens_used = (len(prompt) + len(response)) // 4
        return decision

    def _parse_response(self, response: str, agent_type: str, phase: str) -> AgentDecision:
        """Parse LLM JSON response into AgentDecision."""
        # Try to extract JSON from response
        text = response.strip()
        # Remove markdown code blocks if present
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON object in text
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    data = json.loads(text[start:end])
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse JSON from {agent_type}")
                    return self._fallback_decision(agent_type, phase)
            else:
                return self._fallback_decision(agent_type, phase)

        # Extract estimated_seconds from actions
        total_seconds = 30.0
        actions = data.get("actions", [])
        if actions:
            total_seconds = sum(a.get("estimated_seconds", 15) for a in actions)

        return AgentDecision(
            agent_type=agent_type,
            assessment=data.get("assessment", ""),
            decision=data.get("decision", ""),
            actions=actions,
            communications=data.get("communications", []),
            resource_requests=data.get("resource_requests", []),
            confidence=min(1.0, max(0.0, float(data.get("confidence", 0.5)))),
            reasoning=data.get("reasoning", ""),
            estimated_total_seconds=total_seconds,
            raw_json=data,
        )

    def _fallback_decision(self, agent_type: str, phase: str) -> AgentDecision:
        """Fallback when LLM fails — return reasonable defaults."""
        defaults = {
            "detect": {"seconds": 15, "decision": "Observing and reporting to VOC"},
            "verify": {"seconds": 30, "decision": "Verifying incident via available means"},
            "decide": {"seconds": 20, "decision": "Classifying severity and planning response"},
            "respond": {"seconds": 60, "decision": "Executing response protocol"},
            "resolve": {"seconds": 30, "decision": "Confirming situation resolved"},
        }
        d = defaults.get(phase, defaults["detect"])
        return AgentDecision(
            agent_type=agent_type,
            assessment=f"Phase: {phase}",
            decision=d["decision"],
            confidence=0.3,
            reasoning="Fallback decision — LLM unavailable",
            estimated_total_seconds=d["seconds"],
        )
