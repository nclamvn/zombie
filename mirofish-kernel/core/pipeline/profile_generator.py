"""
Profile Generator — Stage 5 of the MiroFish Pipeline

Uses LLM to generate detailed agent personas from knowledge graph entities.
Each entity becomes an autonomous agent with personality, behavior rules, and stance.

Enhanced from MiroFish's OasisProfileGenerator:
- Decoupled from OASIS profile format
- Richer persona generation with personality traits
- Zep-enriched: uses graph search to gather context per entity
"""

import json
import random
from typing import Dict, Any, List, Optional, Callable

from ..interfaces.llm_provider import LLMProvider
from ..interfaces.graph_store import GraphStore
from ..models.simulation import AgentProfile
from ..models.graph import Node
from ..tools.logger import get_logger

logger = get_logger("mirofish.pipeline.profile_gen")


PROFILE_SYSTEM_PROMPT = """You are an expert character designer for multi-agent simulations. Given an entity from a knowledge graph, create a rich and realistic agent persona.

Output ONLY valid JSON:
{
    "name": "Display name",
    "bio": "1-2 sentence public bio",
    "personality": "3-5 personality traits (e.g., analytical, outspoken, cautious)",
    "stance": "Their position/opinion on the topic being simulated",
    "expertise": ["area1", "area2"],
    "activity_level": 0.7,
    "influence_score": 0.6,
    "emotional_volatility": 0.3,
    "initial_memories": ["Key fact 1 they would know", "Key fact 2"],
    "followers_count": 5000,
    "age": 35,
    "gender": "female",
    "mbti": "INTJ",
    "profession": "Data Scientist"
}

Rules:
- Personality should feel realistic and internally consistent
- Stance must be specific to the simulation topic
- Activity level: 0.0 (lurker) to 1.0 (extremely active poster)
- Influence score: 0.0 (nobody) to 1.0 (major opinion leader)
- Emotional volatility: 0.0 (stoic) to 1.0 (highly reactive)
- followers_count should reflect their real-world influence
- initial_memories should be things this entity would know based on their position
"""


class ProfileGenerator:
    """
    Generates agent profiles from knowledge graph entities.
    
    For each entity node in the graph, generates a rich persona
    with personality, behavioral parameters, and initial memories.
    """
    
    def __init__(
        self,
        llm: LLMProvider,
        graph_store: GraphStore,
    ):
        self.llm = llm
        self.graph_store = graph_store
    
    def generate_profiles(
        self,
        graph_id: str,
        requirement: str,
        agent_configs: Optional[List[Dict[str, Any]]] = None,
        max_agents: int = 30,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> List[AgentProfile]:
        """
        Generate agent profiles from graph entities.
        
        Args:
            graph_id: Knowledge graph ID
            requirement: Simulation requirement (for stance generation)
            agent_configs: Optional per-agent config overrides from ConfigGenerator
            max_agents: Maximum number of agents to generate
            progress_callback: Progress callback
            
        Returns:
            List of AgentProfile objects
        """
        logger.info("Generating agent profiles...")
        
        # Get entities from graph
        nodes = self.graph_store.get_nodes(graph_id)
        
        # Filter to actor-type entities (skip abstract nodes)
        actor_nodes = [n for n in nodes if self._is_actor_entity(n)][:max_agents]
        
        if progress_callback:
            progress_callback(f"Found {len(actor_nodes)} actor entities", 0.1)
        
        # Generate profiles
        profiles = []
        config_map = {}
        if agent_configs:
            config_map = {c.get("entity_name", ""): c for c in agent_configs}
        
        for i, node in enumerate(actor_nodes):
            if progress_callback:
                pct = 0.1 + (i / len(actor_nodes)) * 0.9
                progress_callback(f"Generating profile: {node.name}", pct)
            
            try:
                # Get context from graph for this entity
                context = self._get_entity_context(graph_id, node)
                
                # Get optional config override
                config_override = config_map.get(node.name, {})
                
                # Generate via LLM
                profile = self._generate_single_profile(
                    node=node,
                    context=context,
                    requirement=requirement,
                    agent_id=i,
                    config_override=config_override,
                )
                profiles.append(profile)
                
            except Exception as e:
                logger.warning(f"Failed to generate profile for {node.name}: {e}")
                # Create minimal fallback profile
                profiles.append(AgentProfile(
                    agent_id=i,
                    name=node.name,
                    entity_type=node.primary_label,
                    bio=node.summary or f"A {node.primary_label} entity",
                    personality="neutral, observant",
                    activity_level=0.3,
                ))
        
        logger.info(f"Generated {len(profiles)} agent profiles")
        return profiles
    
    def _is_actor_entity(self, node: Node) -> bool:
        """Check if a node represents an actor (can take actions)."""
        skip_labels = {"Entity", "Node", "Topic", "Theme", "Concept", "Event"}
        return not all(l in skip_labels for l in node.labels)
    
    def _get_entity_context(self, graph_id: str, node: Node) -> str:
        """Get contextual info about an entity from the graph."""
        try:
            result = self.graph_store.search(
                graph_id=graph_id,
                query=node.name,
                limit=5,
            )
            facts = result.get("facts", [])
            if facts:
                return "\n".join(f"- {f}" for f in facts[:5])
        except Exception:
            pass
        
        return node.summary or ""
    
    def _generate_single_profile(
        self,
        node: Node,
        context: str,
        requirement: str,
        agent_id: int,
        config_override: Dict[str, Any],
    ) -> AgentProfile:
        """Generate a single agent profile via LLM."""
        user_msg = f"""## Entity Info
Name: {node.name}
Type: {node.primary_label}
Summary: {node.summary or 'N/A'}
Attributes: {json.dumps(node.attributes, ensure_ascii=False) if node.attributes else 'N/A'}

## Context from Knowledge Graph
{context}

## Simulation Topic
{requirement}

Generate a detailed agent persona for this entity."""

        messages = [
            {"role": "system", "content": PROFILE_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ]
        
        raw = self.llm.chat_json(messages=messages, temperature=0.5, max_tokens=2048)
        
        # Build AgentProfile with LLM output + overrides
        return AgentProfile(
            agent_id=agent_id,
            name=raw.get("name", node.name),
            entity_type=node.primary_label,
            bio=raw.get("bio", node.summary or ""),
            personality=raw.get("personality", "neutral"),
            stance=config_override.get("stance", raw.get("stance", "")),
            expertise=raw.get("expertise", []),
            activity_level=config_override.get(
                "activity_level", raw.get("activity_level", 0.5)
            ),
            influence_score=config_override.get(
                "influence_score", raw.get("influence_score", 0.5)
            ),
            emotional_volatility=raw.get("emotional_volatility", 0.3),
            platforms=["twitter"],
            followers_count=raw.get("followers_count", 100),
            initial_memories=raw.get("initial_memories", []),
        )
