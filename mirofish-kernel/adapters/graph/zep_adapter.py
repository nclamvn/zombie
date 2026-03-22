"""
Zep Graph Store Adapter — Implements GraphStore for Zep Cloud.

Wraps the Zep Cloud API for knowledge graph operations.
This is the current default graph backend for MiroFish.
"""

import time
import uuid
import warnings
from typing import Dict, Any, List, Optional, Callable

from zep_cloud.client import Zep
from zep_cloud import EpisodeData, EntityEdgeSourceTarget

from core.models.ontology import Ontology, EntityType, EdgeType
from core.models.graph import Node, Edge, GraphInfo
from core.tools.logger import get_logger

logger = get_logger("mirofish.adapter.zep")

# Zep reserved attribute names
RESERVED_NAMES = {"uuid", "name", "group_id", "name_embedding", "summary", "created_at"}


def _safe_attr_name(attr_name: str) -> str:
    """Convert reserved names to safe alternatives."""
    if attr_name.lower() in RESERVED_NAMES:
        return f"entity_{attr_name}"
    return attr_name


def _fetch_all_nodes(client: Zep, graph_id: str) -> list:
    """Fetch all nodes with pagination."""
    all_nodes = []
    cursor = None
    while True:
        kwargs = {"graph_id": graph_id, "limit": 100}
        if cursor:
            kwargs["cursor"] = cursor
        response = client.graph.node.get_by_graph(**kwargs)
        nodes = getattr(response, "results", response) if hasattr(response, "results") else response
        if isinstance(nodes, list):
            all_nodes.extend(nodes)
            if len(nodes) < 100:
                break
            cursor = getattr(nodes[-1], "uuid_", None)
            if not cursor:
                break
        else:
            break
    return all_nodes


def _fetch_all_edges(client: Zep, graph_id: str) -> list:
    """Fetch all edges with pagination."""
    all_edges = []
    cursor = None
    while True:
        kwargs = {"graph_id": graph_id, "limit": 100}
        if cursor:
            kwargs["cursor"] = cursor
        response = client.graph.edge.get_by_graph(**kwargs)
        edges = getattr(response, "results", response) if hasattr(response, "results") else response
        if isinstance(edges, list):
            all_edges.extend(edges)
            if len(edges) < 100:
                break
            cursor = getattr(edges[-1], "uuid_", None)
            if not cursor:
                break
        else:
            break
    return all_edges


class ZepGraphAdapter:
    """
    Zep Cloud adapter for GraphStore interface.
    
    Maps kernel graph operations to Zep Cloud API calls.
    """
    
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("ZEP_API_KEY is required")
        self.client = Zep(api_key=api_key)
    
    def create_graph(self, name: str, description: str = "") -> str:
        graph_id = f"mirofish_{uuid.uuid4().hex[:16]}"
        self.client.graph.create(
            graph_id=graph_id,
            name=name,
            description=description or "MiroFish Swarm Intelligence Graph",
        )
        logger.info(f"Created Zep graph: {graph_id}")
        return graph_id
    
    def set_ontology(self, graph_id: str, ontology: Ontology) -> None:
        from pydantic import Field
        from typing import Optional as Opt
        from zep_cloud.external_clients.ontology import EntityModel, EntityText, EdgeModel
        
        warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
        
        # Build entity type classes dynamically
        entity_types = {}
        for et in ontology.entity_types:
            attrs = {"__doc__": et.description}
            annotations = {}
            for attr in et.attributes:
                safe_name = _safe_attr_name(attr.name)
                attrs[safe_name] = Field(description=attr.description, default=None)
                annotations[safe_name] = Opt[EntityText]
            attrs["__annotations__"] = annotations
            entity_class = type(et.name, (EntityModel,), attrs)
            entity_class.__doc__ = et.description
            entity_types[et.name] = entity_class
        
        # Build edge type classes
        edge_definitions = {}
        for et in ontology.edge_types:
            attrs = {"__doc__": et.description}
            annotations = {}
            for attr in et.attributes:
                safe_name = _safe_attr_name(attr.name)
                attrs[safe_name] = Field(description=attr.description, default=None)
                annotations[safe_name] = Opt[EntityText]
            attrs["__annotations__"] = annotations
            
            class_name = "".join(w.capitalize() for w in et.name.split("_"))
            edge_class = type(class_name, (EdgeModel,), attrs)
            edge_class.__doc__ = et.description
            
            source_targets = [
                EntityEdgeSourceTarget(source=st.source, target=st.target)
                for st in et.source_targets
            ]
            if source_targets:
                edge_definitions[class_name] = (edge_class, source_targets)
        
        if entity_types or edge_definitions:
            self.client.graph.set_ontology(
                graph_ids=[graph_id],
                entities=entity_types or None,
                edges=edge_definitions or None,
            )
        
        logger.info(
            f"Set ontology: {len(entity_types)} entity types, "
            f"{len(edge_definitions)} edge types"
        )
    
    def add_episodes(
        self,
        graph_id: str,
        texts: List[str],
        batch_size: int = 3,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> List[str]:
        episode_uuids = []
        total = len(texts)
        
        for i in range(0, total, batch_size):
            batch = texts[i : i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total + batch_size - 1) // batch_size
            
            if progress_callback:
                pct = (i + len(batch)) / total
                progress_callback(
                    f"Batch {batch_num}/{total_batches} ({len(batch)} chunks)", pct
                )
            
            episodes = [EpisodeData(data=chunk, type="text") for chunk in batch]
            
            try:
                result = self.client.graph.add_batch(graph_id=graph_id, episodes=episodes)
                if result and isinstance(result, list):
                    for ep in result:
                        ep_uuid = getattr(ep, "uuid_", None) or getattr(ep, "uuid", None)
                        if ep_uuid:
                            episode_uuids.append(ep_uuid)
                time.sleep(1)  # Rate limiting
            except Exception as e:
                logger.error(f"Batch {batch_num} failed: {e}")
                raise
        
        return episode_uuids
    
    def wait_for_processing(
        self,
        episode_uuids: List[str],
        timeout: int = 600,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> None:
        if not episode_uuids:
            return
        
        start = time.time()
        pending = set(episode_uuids)
        completed = 0
        total = len(episode_uuids)
        
        while pending:
            if time.time() - start > timeout:
                logger.warning(f"Timeout: {completed}/{total} processed")
                break
            
            for ep_uuid in list(pending):
                try:
                    episode = self.client.graph.episode.get(uuid_=ep_uuid)
                    if getattr(episode, "processed", False):
                        pending.remove(ep_uuid)
                        completed += 1
                except Exception:
                    pass
            
            if progress_callback:
                pct = completed / total if total > 0 else 0
                elapsed = int(time.time() - start)
                progress_callback(
                    f"Processing: {completed}/{total} done ({elapsed}s)", pct
                )
            
            if pending:
                time.sleep(3)
    
    def get_graph_info(self, graph_id: str) -> GraphInfo:
        nodes = _fetch_all_nodes(self.client, graph_id)
        edges = _fetch_all_edges(self.client, graph_id)
        
        entity_types = set()
        for node in nodes:
            if node.labels:
                for label in node.labels:
                    if label not in ("Entity", "Node"):
                        entity_types.add(label)
        
        return GraphInfo(
            graph_id=graph_id,
            node_count=len(nodes),
            edge_count=len(edges),
            entity_types=list(entity_types),
        )
    
    def get_nodes(self, graph_id: str) -> List[Node]:
        raw_nodes = _fetch_all_nodes(self.client, graph_id)
        return [
            Node(
                uuid=n.uuid_,
                name=n.name or "",
                labels=n.labels or [],
                summary=n.summary or "",
                attributes=n.attributes or {},
                created_at=str(getattr(n, "created_at", "")) or None,
            )
            for n in raw_nodes
        ]
    
    def get_edges(self, graph_id: str) -> List[Edge]:
        raw_nodes = _fetch_all_nodes(self.client, graph_id)
        raw_edges = _fetch_all_edges(self.client, graph_id)
        
        # Build node name lookup
        node_names = {n.uuid_: (n.name or "") for n in raw_nodes}
        
        return [
            Edge(
                uuid=e.uuid_,
                name=e.name or "",
                fact=e.fact or "",
                fact_type=getattr(e, "fact_type", "") or e.name or "",
                source_node_uuid=e.source_node_uuid or "",
                target_node_uuid=e.target_node_uuid or "",
                source_node_name=node_names.get(e.source_node_uuid or "", ""),
                target_node_name=node_names.get(e.target_node_uuid or "", ""),
                attributes=e.attributes or {},
                created_at=str(getattr(e, "created_at", "")) or None,
                valid_at=str(getattr(e, "valid_at", "")) if getattr(e, "valid_at", None) else None,
                invalid_at=str(getattr(e, "invalid_at", "")) if getattr(e, "invalid_at", None) else None,
                expired_at=str(getattr(e, "expired_at", "")) if getattr(e, "expired_at", None) else None,
                episodes=[str(ep) for ep in (getattr(e, "episodes", None) or getattr(e, "episode_ids", None) or [])],
            )
            for e in raw_edges
        ]
    
    def search(
        self,
        graph_id: str,
        query: str,
        limit: int = 10,
        include_expired: bool = False,
    ) -> Dict[str, Any]:
        try:
            result = self.client.graph.search(
                graph_id=graph_id,
                query=query,
                limit=limit,
                scope="edges",
            )
            
            facts = []
            edges = []
            if result and hasattr(result, "edges") and result.edges:
                for edge in result.edges:
                    fact = getattr(edge, "fact", "") or ""
                    if fact:
                        # Skip expired unless requested
                        if not include_expired:
                            if getattr(edge, "expired_at", None) or getattr(edge, "invalid_at", None):
                                continue
                        facts.append(fact)
                        edges.append({
                            "fact": fact,
                            "name": getattr(edge, "name", ""),
                            "source": getattr(edge, "source_node_uuid", ""),
                            "target": getattr(edge, "target_node_uuid", ""),
                        })
            
            return {"facts": facts, "edges": edges, "nodes": []}
        
        except Exception as e:
            logger.warning(f"Zep search failed: {e}")
            return {"facts": [], "edges": [], "nodes": []}
    
    def delete_graph(self, graph_id: str) -> None:
        self.client.graph.delete(graph_id=graph_id)
        logger.info(f"Deleted graph: {graph_id}")
