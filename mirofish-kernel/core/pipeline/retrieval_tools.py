"""
Retrieval Tools — Graph-Powered Search for Report Agent

Three retrieval modes (extracted and enhanced from MiroFish's zep_tools):
1. InsightForge — Deep hybrid retrieval with auto-generated sub-questions
2. PanoramaSearch — Broad search including expired/historical facts
3. QuickSearch — Fast simple search

These tools are used by the ReportAgent during ReACT reasoning.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from ..interfaces.llm_provider import LLMProvider
from ..interfaces.graph_store import GraphStore
from ..tools.logger import get_logger

logger = get_logger("mirofish.pipeline.retrieval")


@dataclass
class SearchResult:
    """Standard search result."""
    facts: List[str] = field(default_factory=list)
    edges: List[Dict[str, Any]] = field(default_factory=list)
    nodes: List[Dict[str, Any]] = field(default_factory=list)
    query: str = ""
    total_count: int = 0
    
    def to_text(self) -> str:
        """Convert to text for LLM consumption."""
        parts = [f"Query: {self.query}", f"Found {self.total_count} results"]
        if self.facts:
            parts.append("\n### Relevant Facts:")
            for i, fact in enumerate(self.facts, 1):
                parts.append(f"{i}. {fact}")
        return "\n".join(parts)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "facts": self.facts,
            "edges": self.edges,
            "nodes": self.nodes,
            "query": self.query,
            "total_count": self.total_count,
        }


@dataclass
class InsightForgeResult:
    """Result from deep hybrid retrieval."""
    sub_questions: List[str] = field(default_factory=list)
    sub_results: List[SearchResult] = field(default_factory=list)
    synthesis: str = ""
    
    def to_text(self) -> str:
        parts = ["## Deep Insight Analysis"]
        for i, (q, r) in enumerate(zip(self.sub_questions, self.sub_results)):
            parts.append(f"\n### Sub-question {i+1}: {q}")
            parts.append(r.to_text())
        if self.synthesis:
            parts.append(f"\n### Synthesis: {self.synthesis}")
        return "\n".join(parts)


class RetrievalTools:
    """
    Graph-powered retrieval tools for the report agent.
    
    Provides three search modes with increasing depth:
    - quick_search: Fast, simple search
    - panorama_search: Broad search including historical data
    - insight_forge: Deep multi-question hybrid search
    """
    
    def __init__(self, llm: LLMProvider, graph_store: GraphStore):
        self.llm = llm
        self.graph_store = graph_store
    
    def quick_search(
        self, graph_id: str, query: str, limit: int = 10
    ) -> SearchResult:
        """
        Fast simple search.
        Best for: specific fact lookup, entity queries.
        """
        try:
            raw = self.graph_store.search(
                graph_id=graph_id, query=query, limit=limit
            )
            return SearchResult(
                facts=raw.get("facts", []),
                edges=raw.get("edges", []),
                nodes=raw.get("nodes", []),
                query=query,
                total_count=len(raw.get("facts", [])),
            )
        except Exception as e:
            logger.warning(f"Quick search failed: {e}")
            return SearchResult(query=query)
    
    def panorama_search(
        self, graph_id: str, query: str, limit: int = 20
    ) -> SearchResult:
        """
        Broad search including expired/historical facts.
        Best for: getting full picture, understanding evolution over time.
        """
        try:
            raw = self.graph_store.search(
                graph_id=graph_id, query=query, 
                limit=limit, include_expired=True
            )
            return SearchResult(
                facts=raw.get("facts", []),
                edges=raw.get("edges", []),
                nodes=raw.get("nodes", []),
                query=query,
                total_count=len(raw.get("facts", [])),
            )
        except Exception as e:
            logger.warning(f"Panorama search failed: {e}")
            return SearchResult(query=query)
    
    def insight_forge(
        self,
        graph_id: str,
        question: str,
        max_sub_questions: int = 3,
    ) -> InsightForgeResult:
        """
        Deep hybrid retrieval with LLM-generated sub-questions.
        
        Strategy:
        1. LLM decomposes the question into sub-questions
        2. Each sub-question is searched in the graph
        3. Results are synthesized into a coherent answer
        
        Best for: complex analysis, multi-faceted questions.
        """
        # Step 1: Generate sub-questions
        sub_questions = self._generate_sub_questions(question, max_sub_questions)
        
        # Step 2: Search for each sub-question
        sub_results = []
        for sq in sub_questions:
            result = self.quick_search(graph_id, sq, limit=5)
            sub_results.append(result)
        
        # Step 3: Also search the original question
        main_result = self.quick_search(graph_id, question, limit=10)
        sub_questions.insert(0, question)
        sub_results.insert(0, main_result)
        
        # Step 4: Synthesize
        all_facts = []
        for r in sub_results:
            all_facts.extend(r.facts)
        
        synthesis = ""
        if all_facts:
            synthesis = self._synthesize(question, all_facts)
        
        return InsightForgeResult(
            sub_questions=sub_questions,
            sub_results=sub_results,
            synthesis=synthesis,
        )
    
    def _generate_sub_questions(self, question: str, max_count: int) -> List[str]:
        """Use LLM to decompose a complex question."""
        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "Decompose the user's question into 2-3 specific sub-questions "
                        "that would help answer it comprehensively. "
                        "Output ONLY a JSON array of strings."
                    ),
                },
                {"role": "user", "content": question},
            ]
            result = self.llm.chat_json(
                messages=messages, temperature=0.3, max_tokens=512
            )
            
            if isinstance(result, list):
                return result[:max_count]
            if isinstance(result, dict) and "questions" in result:
                return result["questions"][:max_count]
            
        except Exception as e:
            logger.warning(f"Sub-question generation failed: {e}")
        
        return []
    
    def _synthesize(self, question: str, facts: List[str]) -> str:
        """Synthesize collected facts into a coherent answer."""
        try:
            facts_text = "\n".join(f"- {f}" for f in facts[:20])
            messages = [
                {
                    "role": "system",
                    "content": (
                        "Based on the collected facts, provide a concise synthesis "
                        "that answers the question. Be factual and cite specific data."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Question: {question}\n\nFacts:\n{facts_text}",
                },
            ]
            return self.llm.chat(messages=messages, temperature=0.3, max_tokens=1024)
        except Exception as e:
            logger.warning(f"Synthesis failed: {e}")
            return ""
    
    def get_available_tools(self) -> List[Dict[str, str]]:
        """Return tool descriptions for the report agent."""
        return [
            {
                "name": "quick_search",
                "description": "Fast search for specific facts or entities in the knowledge graph",
                "usage": "quick_search(query='search terms')",
            },
            {
                "name": "panorama_search", 
                "description": "Broad search including historical/expired facts for full picture",
                "usage": "panorama_search(query='search terms')",
            },
            {
                "name": "insight_forge",
                "description": "Deep analysis: auto-decomposes question, multi-search, and synthesizes",
                "usage": "insight_forge(question='complex question')",
            },
        ]
