"""
Graph Builder — Stage 3 of the MiroFish Pipeline

Orchestrates knowledge graph construction:
Ontology + Text Chunks → GraphStore → Knowledge Graph

Decoupled from Zep — works with any GraphStore adapter.
"""

import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass

from ..interfaces.graph_store import GraphStore
from ..models.ontology import Ontology
from ..models.graph import GraphInfo
from ..tools.logger import get_logger

logger = get_logger("mirofish.pipeline.graph_builder")


@dataclass
class GraphBuildResult:
    """Result of a graph build operation."""
    graph_id: str
    graph_info: GraphInfo
    chunks_processed: int
    success: bool = True
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "graph_info": self.graph_info.to_dict(),
            "chunks_processed": self.chunks_processed,
            "success": self.success,
            "error": self.error,
        }


class GraphBuilder:
    """
    Builds a knowledge graph from seed text and ontology.
    
    Pipeline:
    1. Create graph instance in GraphStore
    2. Set ontology (entity types + edge types)
    3. Send text chunks in batches
    4. Wait for entity/relation extraction to complete
    5. Return graph info
    """
    
    def __init__(
        self,
        graph_store: GraphStore,
        batch_size: int = 3,
    ):
        self.graph_store = graph_store
        self.batch_size = batch_size
    
    def build(
        self,
        chunks: List[str],
        ontology: Ontology,
        graph_name: str = "MiroFish Graph",
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> GraphBuildResult:
        """
        Build a knowledge graph synchronously.
        
        Args:
            chunks: Text chunks from SeedProcessor
            ontology: Designed ontology from OntologyDesigner
            graph_name: Human-readable name
            progress_callback: Optional (message, progress_0_to_1) callback
            
        Returns:
            GraphBuildResult with graph ID and info
        """
        try:
            return self._build_impl(chunks, ontology, graph_name, progress_callback)
        except Exception as e:
            logger.error(f"Graph build failed: {e}")
            return GraphBuildResult(
                graph_id="",
                graph_info=GraphInfo(graph_id=""),
                chunks_processed=0,
                success=False,
                error=str(e),
            )
    
    def build_async(
        self,
        chunks: List[str],
        ontology: Ontology,
        graph_name: str = "MiroFish Graph",
        progress_callback: Optional[Callable[[str, float], None]] = None,
        completion_callback: Optional[Callable[[GraphBuildResult], None]] = None,
    ) -> threading.Thread:
        """
        Build a knowledge graph asynchronously in a background thread.
        
        Returns:
            The background thread (already started)
        """
        def worker():
            result = self.build(chunks, ontology, graph_name, progress_callback)
            if completion_callback:
                completion_callback(result)
        
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        return thread
    
    def _build_impl(
        self,
        chunks: List[str],
        ontology: Ontology,
        graph_name: str,
        progress_callback: Optional[Callable[[str, float], None]],
    ) -> GraphBuildResult:
        """Internal build implementation."""
        
        def _progress(msg: str, pct: float):
            logger.info(f"[{pct:.0%}] {msg}")
            if progress_callback:
                progress_callback(msg, pct)
        
        # 1. Create graph
        _progress("Creating graph...", 0.05)
        graph_id = self.graph_store.create_graph(
            name=graph_name,
            description="MiroFish Swarm Intelligence Graph",
        )
        _progress(f"Graph created: {graph_id}", 0.10)
        
        # 2. Set ontology
        _progress("Setting ontology...", 0.15)
        self.graph_store.set_ontology(graph_id, ontology)
        _progress("Ontology configured", 0.20)
        
        # 3. Add text chunks
        _progress(f"Sending {len(chunks)} text chunks...", 0.20)
        
        def batch_progress(msg: str, batch_pct: float):
            # Map batch progress (0→1) to overall (0.20→0.60)
            overall_pct = 0.20 + batch_pct * 0.40
            _progress(msg, overall_pct)
        
        episode_uuids = self.graph_store.add_episodes(
            graph_id=graph_id,
            texts=chunks,
            batch_size=self.batch_size,
            progress_callback=batch_progress,
        )
        
        # 4. Wait for processing
        _progress("Waiting for entity extraction...", 0.60)
        
        def wait_progress(msg: str, wait_pct: float):
            overall_pct = 0.60 + wait_pct * 0.30
            _progress(msg, overall_pct)
        
        self.graph_store.wait_for_processing(
            episode_uuids=episode_uuids,
            progress_callback=wait_progress,
        )
        
        # 5. Get graph info
        _progress("Retrieving graph info...", 0.90)
        graph_info = self.graph_store.get_graph_info(graph_id)
        
        _progress(
            f"Graph complete: {graph_info.node_count} nodes, "
            f"{graph_info.edge_count} edges",
            1.0,
        )
        
        return GraphBuildResult(
            graph_id=graph_id,
            graph_info=graph_info,
            chunks_processed=len(chunks),
        )
