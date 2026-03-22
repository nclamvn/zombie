"""
Config Generator — Stage 4 of the MiroFish Pipeline

Uses LLM to automatically generate simulation parameters from:
- User requirement (what to predict)
- Knowledge graph info (entities, relationships)
- Domain context

Enhanced from MiroFish's SimulationConfigGenerator:
- Decoupled from OASIS-specific formats
- Multi-step generation (time → events → agents → platforms)
- Domain-extensible (social media, supply chain, financial, etc.)
"""

import json
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass

from ..interfaces.llm_provider import LLMProvider
from ..interfaces.graph_store import GraphStore
from ..models.simulation import (
    SimulationConfig,
    TimeConfig,
    EventConfig,
    PlatformConfig,
    PlatformType,
    AgentProfile,
)
from ..models.graph import Node, GraphInfo
from ..tools.logger import get_logger

logger = get_logger("mirofish.pipeline.config_gen")


# ─── Default activity patterns ────────────────────────────────────
DEFAULT_ACTIVITY_PATTERN = {
    h: (0.05 if h < 6 else
        0.2 if h < 8 else
        0.6 if h < 12 else
        0.5 if h < 14 else
        0.7 if h < 18 else
        1.0 if h < 22 else
        0.4 if h < 23 else
        0.1)
    for h in range(24)
}


CONFIG_SYSTEM_PROMPT = """You are an expert simulation designer. Based on the user's requirement and knowledge graph data, generate optimal simulation parameters.

Output ONLY valid JSON with this structure:
{
    "time_config": {
        "max_rounds": 10,
        "hours_per_round": 1,
        "start_hour": 8
    },
    "events": [
        {
            "event_id": "evt_001",
            "name": "Event name",
            "description": "What happens",
            "trigger_round": 3,
            "content": "Seed content for agents",
            "impact_type": "information"
        }
    ],
    "platforms": ["twitter", "reddit"],
    "agent_configs": [
        {
            "entity_name": "Name from graph",
            "activity_level": 0.7,
            "influence_score": 0.8,
            "stance": "Their position on the topic"
        }
    ],
    "reasoning": "Brief explanation of parameter choices"
}

Rules:
- max_rounds should be 5-50 based on complexity
- Events should be realistic and timed logically
- Agent configs should reference actual entities from the graph
- Consider real-world timing (working hours, peak social media times)
"""


class ConfigGenerator:
    """
    Generates simulation configuration using LLM analysis
    of the knowledge graph and user requirements.
    
    Multi-step generation strategy:
    1. Generate time config + events
    2. Generate per-agent behavior configs
    3. Generate platform configs
    """
    
    def __init__(
        self,
        llm: LLMProvider,
        graph_store: GraphStore,
    ):
        self.llm = llm
        self.graph_store = graph_store
    
    def generate(
        self,
        graph_id: str,
        requirement: str,
        target_agent_count: Optional[int] = None,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> SimulationConfig:
        """
        Generate complete simulation configuration.
        
        Args:
            graph_id: Knowledge graph ID
            requirement: What to predict/simulate
            target_agent_count: Optional target number of agents
            progress_callback: Progress callback
            
        Returns:
            Complete SimulationConfig
        """
        logger.info("Generating simulation config...")
        
        # Get graph info for context
        graph_info = self.graph_store.get_graph_info(graph_id)
        nodes = self.graph_store.get_nodes(graph_id)
        
        if progress_callback:
            progress_callback("Analyzing graph structure...", 0.1)
        
        # Build context from graph
        entities_summary = self._summarize_entities(nodes)
        
        if progress_callback:
            progress_callback("Generating simulation parameters...", 0.3)
        
        # Generate config via LLM
        raw_config = self._generate_config(
            requirement=requirement,
            entities_summary=entities_summary,
            graph_info=graph_info,
            target_agent_count=target_agent_count,
        )
        
        if progress_callback:
            progress_callback("Building configuration...", 0.7)
        
        # Build SimulationConfig from LLM output
        config = self._build_config(raw_config, nodes)
        
        if progress_callback:
            progress_callback("Config generation complete", 1.0)
        
        logger.info(
            f"Config generated: {config.time_config.max_rounds} rounds, "
            f"{len(config.events)} events, "
            f"{len(config.platforms)} platforms"
        )
        
        return config
    
    def _summarize_entities(self, nodes: List[Node]) -> str:
        """Build a text summary of graph entities for LLM context."""
        lines = []
        for node in nodes[:50]:  # Limit to top 50 nodes
            label = node.primary_label
            summary = node.summary[:100] if node.summary else ""
            lines.append(f"- [{label}] {node.name}: {summary}")
        return "\n".join(lines)
    
    def _generate_config(
        self,
        requirement: str,
        entities_summary: str,
        graph_info: GraphInfo,
        target_agent_count: Optional[int],
    ) -> Dict[str, Any]:
        """Call LLM to generate raw config."""
        user_msg = f"""## Requirement
{requirement}

## Knowledge Graph Info
- Nodes: {graph_info.node_count}
- Edges: {graph_info.edge_count}
- Entity types: {', '.join(graph_info.entity_types)}

## Entities in Graph
{entities_summary}

## Constraints
- Target agent count: {target_agent_count or 'auto (based on graph)'}

Generate the simulation configuration."""

        messages = [
            {"role": "system", "content": CONFIG_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ]
        
        return self.llm.chat_json(messages=messages, temperature=0.4, max_tokens=4096)
    
    def _build_config(
        self, raw: Dict[str, Any], nodes: List[Node]
    ) -> SimulationConfig:
        """Convert raw LLM output to SimulationConfig."""
        # Time config
        tc = raw.get("time_config", {})
        time_config = TimeConfig(
            max_rounds=tc.get("max_rounds", 10),
            hours_per_round=tc.get("hours_per_round", 1),
            start_hour=tc.get("start_hour", 8),
            activity_pattern=DEFAULT_ACTIVITY_PATTERN,
        )
        
        # Events
        events = []
        for i, evt in enumerate(raw.get("events", [])):
            events.append(EventConfig(
                event_id=evt.get("event_id", f"evt_{i:03d}"),
                name=evt.get("name", f"Event {i+1}"),
                description=evt.get("description", ""),
                trigger_round=evt.get("trigger_round", 1),
                content=evt.get("content", ""),
                impact_type=evt.get("impact_type", "information"),
            ))
        
        # Platforms
        platform_names = raw.get("platforms", ["twitter"])
        platforms = []
        for pn in platform_names:
            ptype = PlatformType.TWITTER if "twitter" in pn.lower() else (
                PlatformType.REDDIT if "reddit" in pn.lower() else PlatformType.CUSTOM
            )
            platforms.append(PlatformConfig(platform_type=ptype, enabled=True))
        
        return SimulationConfig(
            requirement=raw.get("requirement", ""),
            time_config=time_config,
            events=events,
            platforms=platforms,
            domain_config={
                "reasoning": raw.get("reasoning", ""),
                "agent_configs": raw.get("agent_configs", []),
            },
        )
