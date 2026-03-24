"""
Domain Template Registry — TIP-14

Pre-built templates for common simulation domains.
Each template provides: ontology prompt, default config, sample events, metrics.

Usage:
    from templates.registry import TemplateRegistry
    registry = TemplateRegistry()
    template = registry.get("supply_chain")
    # Use template.ontology_prompt with OntologyDesigner
    # Use template.default_config for SimulationConfig defaults
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

import yaml

logger = logging.getLogger("mirofish.templates")


@dataclass
class DomainTemplate:
    """A pre-built domain template for simulation."""
    id: str
    name: str
    description: str
    icon: str = ""
    category: str = "general"
    ontology_prompt: str = ""
    default_config: Dict[str, Any] = field(default_factory=dict)
    sample_events: List[Dict[str, Any]] = field(default_factory=list)
    evaluation_metrics: List[str] = field(default_factory=list)
    sample_seed_text: str = ""
    scenarios: List[Dict[str, Any]] = field(default_factory=list)
    agent_profiles: Dict[str, Any] = field(default_factory=dict)
    kpi: Dict[str, Any] = field(default_factory=dict)
    comparison_configurations: List[Dict[str, Any]] = field(default_factory=list)
    report_template: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "category": self.category,
            "has_ontology_prompt": bool(self.ontology_prompt),
            "default_config": self.default_config,
            "sample_events": self.sample_events,
            "evaluation_metrics": self.evaluation_metrics,
            "has_sample_seed": bool(self.sample_seed_text),
            "has_scenarios": bool(self.scenarios),
            "has_comparison": bool(self.comparison_configurations),
            "scenario_count": len(self.scenarios),
            "comparison_config_count": len(self.comparison_configurations),
        }


# ─── Built-in Templates ──────────────────────────────────────

TEMPLATES: List[DomainTemplate] = [
    DomainTemplate(
        id="social_media",
        name="Social Media Prediction",
        description="Simulate public discourse on social platforms. Predict sentiment, virality, and opinion formation.",
        icon="$",
        ontology_prompt="""Design entity types for social media simulation.
Entity types: PublicFigure, MediaOutlet, Company, GovernmentAgency, Influencer, Journalist, Citizen, NGO.
Edge types: FOLLOWS, OPPOSES, SUPPORTS, REPORTS_ON, RESPONDS_TO, AFFILIATED_WITH, COMMENTS_ON.
Focus on actors who create/share content and influence public opinion.""",
        default_config={"max_rounds": 50, "hours_per_round": 1, "platforms": ["twitter", "reddit"]},
        sample_events=[
            {"name": "Breaking News", "trigger_round": 10, "content": "Major announcement"},
            {"name": "Viral Post", "trigger_round": 25, "content": "Content goes viral"},
        ],
        evaluation_metrics=["sentiment_shift", "engagement_rate", "opinion_convergence", "influencer_reach"],
    ),
    DomainTemplate(
        id="supply_chain",
        name="Supply Chain Simulation",
        description="Model supply chain disruptions, logistics, and sourcing strategies. Predict lead times and costs.",
        icon="!",
        ontology_prompt="""Design entity types for supply chain simulation.
Entity types: Supplier, Manufacturer, Distributor, Retailer, RawMaterial, Component, Product, Warehouse.
Edge types: SUPPLIES_TO, MANUFACTURES, STORES_AT, TRANSPORTS_VIA, DEPENDS_ON, CONTRACTS_WITH, COMPETES_WITH.
Focus on entities in the manufacturing and distribution pipeline.""",
        default_config={"max_rounds": 200, "hours_per_round": 4, "platforms": ["custom"]},
        sample_events=[
            {"name": "Supplier Disruption", "trigger_round": 50, "content": "Key supplier capacity reduced 30%"},
            {"name": "Demand Surge", "trigger_round": 100, "content": "Unexpected demand increase"},
        ],
        evaluation_metrics=["lead_time_impact", "cost_increase_pct", "inventory_days", "alternative_sourcing_score"],
    ),
    DomainTemplate(
        id="financial",
        name="Financial Market Simulation",
        description="Model market reactions, investor behavior, and economic indicators. Predict price movements.",
        icon="#",
        ontology_prompt="""Design entity types for financial market simulation.
Entity types: Investor, Bank, Regulator, Company, Analyst, FundManager, MarketMaker, CentralBank.
Edge types: INVESTS_IN, REGULATES, ANALYZES, TRADES_WITH, COMPETES_WITH, ADVISES, INFLUENCES.
Focus on financial actors and their market-moving behaviors.""",
        default_config={"max_rounds": 100, "hours_per_round": 1, "platforms": ["custom"]},
        sample_events=[
            {"name": "Rate Decision", "trigger_round": 30, "content": "Central bank rate change"},
            {"name": "Earnings Report", "trigger_round": 60, "content": "Major company earnings surprise"},
        ],
        evaluation_metrics=["price_volatility", "sentiment_index", "trading_volume", "risk_score"],
    ),
    DomainTemplate(
        id="real_estate",
        name="Real Estate Market Simulation",
        description="Model property markets, buyer/seller dynamics, and pricing trends. Predict match rates.",
        icon="~",
        ontology_prompt="""Design entity types for real estate simulation.
Entity types: Buyer, Seller, Agent, Developer, Bank, GovernmentAgency, Property, Location.
Edge types: LISTS, SEARCHES_FOR, MATCHES_WITH, FINANCES, REGULATES, DEVELOPS, LOCATED_IN.
Focus on marketplace dynamics between supply and demand.""",
        default_config={"max_rounds": 150, "hours_per_round": 8, "platforms": ["custom"]},
        sample_events=[
            {"name": "Policy Change", "trigger_round": 50, "content": "New housing policy announced"},
            {"name": "Interest Rate Change", "trigger_round": 100, "content": "Mortgage rates shift"},
        ],
        evaluation_metrics=["match_rate", "time_to_match", "price_index", "inventory_levels"],
    ),
    DomainTemplate(
        id="public_policy",
        name="Public Policy Impact",
        description="Simulate stakeholder reactions to policy proposals. Predict support/opposition dynamics.",
        icon="*",
        ontology_prompt="""Design entity types for public policy simulation.
Entity types: Politician, GovernmentAgency, Lobbyist, MediaOutlet, CitizenGroup, Corporation, NGO, AcademicExpert.
Edge types: PROPOSES, SUPPORTS, OPPOSES, LOBBIES, REPORTS_ON, REPRESENTS, REGULATES, ADVISES.
Focus on policy stakeholders and their influence on decision-making.""",
        default_config={"max_rounds": 100, "hours_per_round": 2, "platforms": ["twitter"]},
        sample_events=[
            {"name": "Draft Released", "trigger_round": 20, "content": "Policy draft made public"},
            {"name": "Public Comment Period", "trigger_round": 60, "content": "Comment period opens"},
        ],
        evaluation_metrics=["support_pct", "opposition_pct", "media_coverage", "stakeholder_alignment"],
    ),
    DomainTemplate(
        id="custom",
        name="Custom Domain",
        description="Start from scratch. Define your own ontology, events, and metrics.",
        icon="+",
        ontology_prompt="",
        default_config={"max_rounds": 50, "hours_per_round": 1, "platforms": ["twitter"]},
        sample_events=[],
        evaluation_metrics=[],
    ),
]


def _load_yaml_template(template_id: str) -> Optional[DomainTemplate]:
    """Load a template from its YAML file in templates/{id}/template.yaml."""
    template_dir = Path(__file__).parent / template_id
    yaml_path = template_dir / "template.yaml"

    if not yaml_path.exists():
        return None

    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            tmpl = yaml.safe_load(f)

        # Find seed example (first .txt in examples/)
        seed_text = ""
        examples_dir = template_dir / "examples"
        if examples_dir.exists():
            for txt_file in sorted(examples_dir.glob("*.txt")):
                seed_text = txt_file.read_text(encoding="utf-8")
                break

        # Extract evaluation metric names
        eval_metrics = []
        for m in tmpl.get("evaluation_metrics", []):
            if isinstance(m, dict):
                eval_metrics.append(m.get("name", ""))
            elif isinstance(m, str):
                eval_metrics.append(m)

        return DomainTemplate(
            id=template_id,
            name=tmpl.get("display_name", tmpl.get("name", template_id)),
            description=tmpl.get("description", ""),
            icon=tmpl.get("icon", "●"),
            category=tmpl.get("category", "general"),
            ontology_prompt=tmpl.get("ontology_prompt", ""),
            default_config=tmpl.get("default_config", {}),
            sample_events=[],
            evaluation_metrics=eval_metrics,
            sample_seed_text=seed_text,
            scenarios=tmpl.get("scenarios", []),
            agent_profiles=tmpl.get("agent_profiles", {}),
            kpi=tmpl.get("kpi", {}),
            comparison_configurations=tmpl.get("comparison_configurations", []),
            report_template=tmpl.get("report_template", {}),
        )
    except Exception as e:
        logger.error(f"Failed to load template {template_id}: {e}")
        return None


# Auto-discover and load all YAML templates from templates/*/template.yaml
_templates_root = Path(__file__).parent
for _dir in sorted(_templates_root.iterdir()):
    if _dir.is_dir() and (_dir / "template.yaml").exists():
        _tmpl = _load_yaml_template(_dir.name)
        if _tmpl:
            TEMPLATES.append(_tmpl)
            logger.info(f"Loaded template: {_dir.name} ({_tmpl.name})")


class TemplateRegistry:
    """Registry of domain templates."""

    def __init__(self):
        self._templates = {t.id: t for t in TEMPLATES}

    def list_all(self) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in TEMPLATES]

    def get(self, template_id: str) -> Optional[DomainTemplate]:
        return self._templates.get(template_id)

    def get_ontology_prompt(self, template_id: str) -> str:
        t = self._templates.get(template_id)
        return t.ontology_prompt if t else ""
