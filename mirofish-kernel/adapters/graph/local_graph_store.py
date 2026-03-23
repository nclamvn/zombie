"""
Local Graph Store — Lightweight in-memory graph (TIP-19)

Fallback when Zep API key is not available. Stores nodes + edges in JSON file.
Uses LLM to extract entities from text chunks.
Good for demo and development. Not for production scale.
"""

import json
import logging
import os
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("mirofish.graph.local")

DATA_DIR = Path(os.environ.get("MIROFISH_DATA_DIR", "/tmp/mirofish_graphs"))


@dataclass
class LocalNode:
    uuid: str
    name: str
    labels: List[str]
    summary: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return {"uuid": self.uuid, "name": self.name, "labels": self.labels,
                "summary": self.summary, "attributes": self.attributes}


@dataclass
class LocalEdge:
    source_node_uuid: str
    target_node_uuid: str
    relationship_type: str
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return {"source_node_uuid": self.source_node_uuid,
                "target_node_uuid": self.target_node_uuid,
                "relationship_type": self.relationship_type,
                "attributes": self.attributes}


@dataclass
class LocalGraphInfo:
    graph_id: str
    node_count: int = 0
    edge_count: int = 0
    entity_types: List[str] = field(default_factory=list)

    def to_dict(self):
        return {"graph_id": self.graph_id, "node_count": self.node_count,
                "edge_count": self.edge_count, "entity_types": self.entity_types}


@dataclass
class LocalGraphResult:
    success: bool
    graph_id: str
    graph_info: LocalGraphInfo
    chunks_processed: int = 0
    error: Optional[str] = None


ENTITY_EXTRACT_PROMPT = """Extract entities and relationships from this text.

Entity types to look for: {entity_types}
Relationship types: {edge_types}

Text:
{text}

Output valid JSON only:
{{
  "entities": [
    {{"name": "...", "type": "...", "summary": "..."}}
  ],
  "relationships": [
    {{"source": "entity name", "target": "entity name", "type": "..."}}
  ]
}}"""


class LocalGraphStore:
    """
    Lightweight in-memory graph using Python dicts.
    No external dependencies. Stores nodes + edges in JSON file.
    """

    def __init__(self, llm=None):
        self.llm = llm
        self._graphs: Dict[str, Dict[str, Any]] = {}
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    def build(self, chunks: List[Dict], ontology, graph_name: str = "default") -> LocalGraphResult:
        """Build graph from text chunks using LLM entity extraction."""
        graph_id = f"local_{uuid.uuid4().hex[:12]}"
        nodes: Dict[str, LocalNode] = {}
        edges: List[LocalEdge] = []

        # Get entity/edge type names from ontology
        entity_types = []
        edge_types = []
        if hasattr(ontology, "entity_types"):
            entity_types = [et.name for et in ontology.entity_types]
        elif isinstance(ontology, dict):
            entity_types = [et.get("name", "") for et in ontology.get("entity_types", [])]
        if hasattr(ontology, "edge_types"):
            edge_types = [et.name for et in ontology.edge_types]
        elif isinstance(ontology, dict):
            edge_types = [et.get("name", "") for et in ontology.get("edge_types", [])]

        entity_type_str = ", ".join(entity_types) if entity_types else "Person, Organization, Location, Event"
        edge_type_str = ", ".join(edge_types) if edge_types else "RELATED_TO, PART_OF, COMMANDS, REPORTS_TO"

        for i, chunk in enumerate(chunks):
            text = chunk.get("text", chunk) if isinstance(chunk, dict) else str(chunk)
            if not text.strip():
                continue

            if self.llm:
                extracted = self._extract_via_llm(text, entity_type_str, edge_type_str)
            else:
                extracted = self._extract_simple(text, entity_types)

            # Add entities as nodes
            for ent in extracted.get("entities", []):
                name = ent.get("name", "").strip()
                if not name:
                    continue
                if name not in nodes:
                    nodes[name] = LocalNode(
                        uuid=uuid.uuid4().hex[:16],
                        name=name,
                        labels=[ent.get("type", "Entity")],
                        summary=ent.get("summary", ""),
                    )

            # Add relationships as edges
            for rel in extracted.get("relationships", []):
                src = rel.get("source", "").strip()
                tgt = rel.get("target", "").strip()
                if src in nodes and tgt in nodes:
                    edges.append(LocalEdge(
                        source_node_uuid=nodes[src].uuid,
                        target_node_uuid=nodes[tgt].uuid,
                        relationship_type=rel.get("type", "RELATED_TO"),
                    ))

        # Store graph
        node_list = list(nodes.values())
        self._graphs[graph_id] = {
            "nodes": node_list,
            "edges": edges,
            "name": graph_name,
        }

        # Persist to file
        self._save(graph_id)

        all_types = list(set(label for n in node_list for label in n.labels))
        info = LocalGraphInfo(
            graph_id=graph_id,
            node_count=len(node_list),
            edge_count=len(edges),
            entity_types=all_types,
        )

        logger.info(f"Local graph built: {len(node_list)} nodes, {len(edges)} edges")
        return LocalGraphResult(
            success=True, graph_id=graph_id, graph_info=info,
            chunks_processed=len(chunks),
        )

    def get_nodes(self, graph_id: str) -> List[LocalNode]:
        g = self._graphs.get(graph_id)
        return g["nodes"] if g else []

    def get_edges(self, graph_id: str) -> List[LocalEdge]:
        g = self._graphs.get(graph_id)
        return g["edges"] if g else []

    def get_graph_info(self, graph_id: str) -> LocalGraphInfo:
        g = self._graphs.get(graph_id)
        if not g:
            return LocalGraphInfo(graph_id=graph_id)
        nodes = g["nodes"]
        return LocalGraphInfo(
            graph_id=graph_id,
            node_count=len(nodes),
            edge_count=len(g["edges"]),
            entity_types=list(set(l for n in nodes for l in n.labels)),
        )

    def search(self, graph_id: str, query: str, limit: int = 10) -> List[Dict]:
        """Simple keyword search over nodes."""
        g = self._graphs.get(graph_id)
        if not g:
            return []
        q = query.lower()
        results = []
        for node in g["nodes"]:
            score = 0
            if q in node.name.lower():
                score += 2
            if q in node.summary.lower():
                score += 1
            if score > 0:
                results.append({"node": node.to_dict(), "score": score})
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    def _extract_via_llm(self, text: str, entity_types: str, edge_types: str) -> Dict:
        """Use LLM to extract entities and relationships."""
        prompt = ENTITY_EXTRACT_PROMPT.format(
            entity_types=entity_types, edge_types=edge_types, text=text[:2000],
        )
        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2, max_tokens=1000,
            )
            text_r = response.strip()
            if text_r.startswith("```"):
                lines = text_r.split("\n")
                text_r = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            start = text_r.find("{")
            end = text_r.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text_r[start:end])
        except Exception as e:
            logger.warning(f"LLM entity extraction failed: {e}")
        return {"entities": [], "relationships": []}

    def _extract_simple(self, text: str, entity_types: List[str]) -> Dict:
        """Simple regex-based extraction fallback (no LLM)."""
        # Just extract capitalized multi-word phrases as entities
        import re
        entities = []
        seen = set()
        for match in re.finditer(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', text):
            name = match.group(0)
            if name not in seen and len(name) > 5:
                seen.add(name)
                entities.append({"name": name, "type": "Entity", "summary": ""})
        return {"entities": entities[:20], "relationships": []}

    def _save(self, graph_id: str):
        """Persist graph to JSON file."""
        g = self._graphs.get(graph_id)
        if not g:
            return
        path = DATA_DIR / f"{graph_id}.json"
        data = {
            "nodes": [n.to_dict() for n in g["nodes"]],
            "edges": [e.to_dict() for e in g["edges"]],
            "name": g.get("name", ""),
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def load(self, graph_id: str) -> bool:
        """Load graph from JSON file."""
        path = DATA_DIR / f"{graph_id}.json"
        if not path.exists():
            return False
        data = json.loads(path.read_text())
        nodes = [LocalNode(**n) for n in data.get("nodes", [])]
        edges = [LocalEdge(**e) for e in data.get("edges", [])]
        self._graphs[graph_id] = {"nodes": nodes, "edges": edges, "name": data.get("name", "")}
        return True
