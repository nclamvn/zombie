"""
Ontology Designer — Stage 2 of the MiroFish Pipeline

Uses LLM to analyze seed text and design a knowledge graph schema
(entity types + edge types) optimized for multi-agent simulation.

Enhanced from MiroFish's OntologyGenerator:
- Decoupled from Zep-specific constraints
- Externalized prompts (loadable from prompts/ directory)
- Domain-agnostic with pluggable prompt templates
- Stronger validation pipeline
"""

import json
import os
from typing import List, Dict, Any, Optional

from ..interfaces.llm_provider import LLMProvider
from ..models.ontology import Ontology, EntityType, EdgeType, OntologyAttribute, SourceTarget
from ..tools.logger import get_logger

logger = get_logger("mirofish.pipeline.ontology")

# Default prompt paths (relative to kernel root)
_PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "../../prompts/ontology")


def _load_prompt(filename: str, fallback: str = "") -> str:
    """Load a prompt template from the prompts directory."""
    path = os.path.join(_PROMPTS_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return fallback


# ─── Default System Prompt ────────────────────────────────────────────
DEFAULT_SYSTEM_PROMPT = """You are an expert knowledge graph ontology designer. Your task is to analyze the given text content and simulation requirement, then design entity types and relationship types suitable for multi-agent social simulation.

**You MUST output valid JSON only — no markdown, no explanation.**

## Core Task

We are building a **multi-agent simulation system**. In this system:
- Each entity is an autonomous agent that can interact, communicate, and influence others
- Entities have personas, memories, and behavioral logic
- We need to simulate how entities react and interact during events

Therefore, **entities MUST be real-world actors that can take actions**:

**Valid entity types**: Individuals (public figures, experts, ordinary people), Companies, Organizations (universities, NGOs), Government agencies, Media outlets, Social platforms, Group representatives

**Invalid**: Abstract concepts (trends, emotions), Topics/themes, Opinions/stances

## Output Format

```json
{
    "entity_types": [
        {
            "name": "EntityTypeName (PascalCase)",
            "description": "Short description (under 100 chars)",
            "attributes": [
                {"name": "attr_name (snake_case)", "type": "text", "description": "..."}
            ],
            "examples": ["Example1", "Example2"]
        }
    ],
    "edge_types": [
        {
            "name": "RELATIONSHIP_NAME (UPPER_SNAKE_CASE)",
            "description": "Short description (under 100 chars)",
            "source_targets": [{"source": "SourceType", "target": "TargetType"}],
            "attributes": []
        }
    ],
    "analysis_summary": "Brief analysis of the input text and domain"
}
```

## Design Rules

### Entity Types (exactly 10)
- 8 specific types based on text content
- 2 fallback types (MUST be last): `Person` (any individual) and `Organization` (any org)
- Attributes: 1-3 per type. RESERVED NAMES (cannot use): name, uuid, group_id, created_at, summary

### Edge Types (6-10)
- Reflect realistic interactions between entities
- source_targets must reference your defined entity types

### Reference Entity Types
**Individuals**: Student, Professor, Journalist, Celebrity, Executive, Official, Lawyer, Doctor
**Organizations**: University, Company, GovernmentAgency, MediaOutlet, Hospital, NGO

### Reference Edge Types
WORKS_FOR, STUDIES_AT, AFFILIATED_WITH, REPRESENTS, REGULATES, REPORTS_ON, 
COMMENTS_ON, RESPONDS_TO, SUPPORTS, OPPOSES, COLLABORATES_WITH, COMPETES_WITH
"""


class OntologyDesigner:
    """
    Designs knowledge graph ontology using LLM analysis of seed text.
    
    Pipeline: seed text + requirement → LLM → validated Ontology
    """
    
    MAX_TEXT_LENGTH = 50_000  # Max chars sent to LLM
    
    def __init__(
        self,
        llm: LLMProvider,
        system_prompt: Optional[str] = None,
    ):
        self.llm = llm
        self.system_prompt = system_prompt or _load_prompt(
            "system_prompt.txt", DEFAULT_SYSTEM_PROMPT
        )
    
    def design(
        self,
        document_texts: List[str],
        requirement: str,
        additional_context: Optional[str] = None,
        max_entity_types: int = 10,
        max_edge_types: int = 10,
    ) -> Ontology:
        """
        Design an ontology for the given seed material.
        
        Args:
            document_texts: List of document text strings
            requirement: What to predict/simulate
            additional_context: Optional domain hints
            max_entity_types: Max entity types (Zep limit = 10)
            max_edge_types: Max edge types (Zep limit = 10)
            
        Returns:
            Validated Ontology object
        """
        logger.info("Designing ontology from seed material...")
        
        # Build prompt
        user_message = self._build_user_message(
            document_texts, requirement, additional_context
        )
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message},
        ]
        
        # Call LLM
        raw_result = self.llm.chat_json(messages=messages, temperature=0.3, max_tokens=4096)
        
        # Validate and convert to domain model
        ontology = self._validate_and_build(raw_result, max_entity_types, max_edge_types)
        
        logger.info(
            f"Ontology designed: {len(ontology.entity_types)} entity types, "
            f"{len(ontology.edge_types)} edge types"
        )
        
        return ontology
    
    def _build_user_message(
        self,
        document_texts: List[str],
        requirement: str,
        additional_context: Optional[str],
    ) -> str:
        """Build the user prompt for ontology generation."""
        combined_text = "\n\n---\n\n".join(document_texts)
        original_length = len(combined_text)
        
        if len(combined_text) > self.MAX_TEXT_LENGTH:
            combined_text = combined_text[:self.MAX_TEXT_LENGTH]
            combined_text += (
                f"\n\n...(Original: {original_length} chars, "
                f"truncated to {self.MAX_TEXT_LENGTH} for analysis)..."
            )
        
        message = f"""## Simulation Requirement

{requirement}

## Document Content

{combined_text}
"""
        
        if additional_context:
            message += f"""
## Additional Context

{additional_context}
"""
        
        message += """
Design entity types and edge types based on the above content.

**Mandatory rules**:
1. Exactly 10 entity types
2. Last 2 MUST be fallback types: Person (individual fallback) and Organization (org fallback)
3. First 8 are specific types designed from text content
4. All entity types MUST be real-world actors, NOT abstract concepts
5. Attribute names CANNOT use reserved words: name, uuid, group_id, created_at, summary
"""
        return message
    
    def _validate_and_build(
        self,
        raw: Dict[str, Any],
        max_entity_types: int,
        max_edge_types: int,
    ) -> Ontology:
        """Validate LLM output and build Ontology model."""
        entity_dicts = raw.get("entity_types", [])
        edge_dicts = raw.get("edge_types", [])
        
        # Validate entity types
        RESERVED_ATTR_NAMES = {"name", "uuid", "group_id", "name_embedding", "summary", "created_at"}
        
        for e in entity_dicts:
            e.setdefault("attributes", [])
            e.setdefault("examples", [])
            if len(e.get("description", "")) > 100:
                e["description"] = e["description"][:97] + "..."
            # Filter reserved attribute names
            e["attributes"] = [
                {**a, "name": f"entity_{a['name']}"} if a.get("name", "").lower() in RESERVED_ATTR_NAMES else a
                for a in e["attributes"]
            ]
        
        # Validate edge types
        for e in edge_dicts:
            e.setdefault("source_targets", [])
            e.setdefault("attributes", [])
            if len(e.get("description", "")) > 100:
                e["description"] = e["description"][:97] + "..."
        
        # Ensure fallback types exist
        entity_names = {e["name"] for e in entity_dicts}
        
        if "Person" not in entity_names:
            entity_dicts.append({
                "name": "Person",
                "description": "Any individual not fitting other specific person types.",
                "attributes": [
                    {"name": "full_name", "type": "text", "description": "Full name"},
                    {"name": "role", "type": "text", "description": "Role or occupation"},
                ],
                "examples": ["ordinary citizen", "anonymous user"],
            })
        
        if "Organization" not in entity_names:
            entity_dicts.append({
                "name": "Organization",
                "description": "Any organization not fitting other specific org types.",
                "attributes": [
                    {"name": "org_name", "type": "text", "description": "Organization name"},
                    {"name": "org_type", "type": "text", "description": "Type of organization"},
                ],
                "examples": ["small business", "community group"],
            })
        
        # Enforce limits
        # Separate fallback types, keep them at end
        fallbacks = [e for e in entity_dicts if e["name"] in ("Person", "Organization")]
        specifics = [e for e in entity_dicts if e["name"] not in ("Person", "Organization")]
        max_specific = max_entity_types - len(fallbacks)
        entity_dicts = specifics[:max_specific] + fallbacks
        
        edge_dicts = edge_dicts[:max_edge_types]
        
        # Build domain models
        entity_types = [EntityType.from_dict(e) for e in entity_dicts]
        edge_types = [EdgeType.from_dict(e) for e in edge_dicts]
        
        return Ontology(
            entity_types=entity_types,
            edge_types=edge_types,
            analysis_summary=raw.get("analysis_summary", ""),
        )
