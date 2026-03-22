"""
Report Agent — Stage 7 of the MiroFish Pipeline

ReACT (Reasoning + Acting) pattern for report generation:
1. Plan report outline from simulation results
2. For each section: Think → Act (search) → Observe → Write
3. Reflect and refine
4. Interactive chat post-generation

Enhanced from MiroFish's report_agent.py:
- Decoupled from Zep-specific tools
- Uses RetrievalTools interface
- Externalized prompt templates
- Cleaner ReACT loop
"""

import json
from typing import Dict, Any, List, Optional, Callable

from ..interfaces.llm_provider import LLMProvider
from ..models.report import ReportOutline, ReportSection, ReportStatus
from .retrieval_tools import RetrievalTools
from ..tools.logger import get_logger

logger = get_logger("mirofish.pipeline.report_agent")


PLANNER_PROMPT = """You are a report planning expert. Based on the simulation requirement and results summary, plan a comprehensive report structure.

Output ONLY valid JSON:
{
    "title": "Report title",
    "summary": "1-2 sentence executive summary",
    "sections": [
        {
            "title": "Section Title",
            "description": "What this section should analyze and cover"
        }
    ]
}

Plan 4-8 sections that cover:
1. Executive summary / overview
2. Key findings from simulation
3. Agent behavior analysis
4. Trend/pattern analysis
5. Predictions / forecasts
6. Recommendations (if applicable)
7. Methodology note (brief)
"""

SECTION_WRITER_PROMPT = """You are an expert analyst writing a section of a prediction report. 
You have access to tools to search the knowledge graph for evidence.

## Available Tools
{tools_description}

## Instructions
Write this section using the ReACT pattern:
1. THINK about what information you need
2. Call tools to gather evidence
3. Write the section based on evidence

Use markdown formatting. Be data-driven and cite specific facts from the simulation.
Write 200-500 words per section. Be analytical, not just descriptive.
"""

CHAT_PROMPT = """You are the MiroFish Report Agent. You generated a prediction report and the user has follow-up questions.

## Report Context
{report_content}

## Available Tools
You can search the knowledge graph for additional information.

Answer the user's question based on the report and graph data. Be specific and data-driven.
"""


class ReportAgent:
    """
    ReACT-based report generation agent.
    
    Pipeline:
    1. plan_outline() — LLM generates report structure
    2. generate_section() — Per-section ReACT loop (Think → Act → Write)
    3. generate_full_report() — End-to-end generation
    4. chat() — Interactive Q&A about the report
    """
    
    def __init__(
        self,
        llm: LLMProvider,
        retrieval: RetrievalTools,
        max_tool_calls_per_section: int = 5,
        max_reflection_rounds: int = 2,
    ):
        self.llm = llm
        self.retrieval = retrieval
        self.max_tool_calls = max_tool_calls_per_section
        self.max_reflections = max_reflection_rounds
    
    def plan_outline(
        self,
        requirement: str,
        simulation_summary: Dict[str, Any],
    ) -> ReportOutline:
        """Plan the report structure."""
        logger.info("Planning report outline...")
        
        summary_text = json.dumps(simulation_summary, indent=2, ensure_ascii=False)
        
        messages = [
            {"role": "system", "content": PLANNER_PROMPT},
            {
                "role": "user",
                "content": f"## Requirement\n{requirement}\n\n## Simulation Results\n{summary_text}",
            },
        ]
        
        raw = self.llm.chat_json(messages=messages, temperature=0.4, max_tokens=2048)
        
        sections = [
            ReportSection(
                index=i,
                title=s.get("title", f"Section {i+1}"),
                description=s.get("description", ""),
            )
            for i, s in enumerate(raw.get("sections", []))
        ]
        
        outline = ReportOutline(
            title=raw.get("title", "Prediction Report"),
            summary=raw.get("summary", ""),
            sections=sections,
            requirement=requirement,
        )
        
        logger.info(f"Outline planned: {outline.total_sections} sections")
        return outline
    
    def generate_section(
        self,
        section: ReportSection,
        outline: ReportOutline,
        graph_id: str,
        simulation_summary: Dict[str, Any],
    ) -> str:
        """
        Generate a single section using ReACT pattern.
        
        Think → Search → Observe → Write → (optional Reflect)
        """
        logger.info(f"Generating section: {section.title}")
        section.status = ReportStatus.GENERATING
        
        # Gather evidence via retrieval tools
        evidence = self._gather_evidence(graph_id, section, outline.requirement)
        
        # Write section with evidence
        tools_desc = "\n".join(
            f"- {t['name']}: {t['description']}"
            for t in self.retrieval.get_available_tools()
        )
        
        evidence_text = "\n".join(
            f"- {f}" for f in evidence[:15]
        )
        
        messages = [
            {
                "role": "system",
                "content": SECTION_WRITER_PROMPT.format(tools_description=tools_desc),
            },
            {
                "role": "user",
                "content": (
                    f"## Report: {outline.title}\n"
                    f"## Section: {section.title}\n"
                    f"## Section Goal: {section.description}\n\n"
                    f"## Evidence from Knowledge Graph:\n{evidence_text}\n\n"
                    f"## Simulation Stats:\n"
                    f"- Total rounds: {simulation_summary.get('total_rounds', 'N/A')}\n"
                    f"- Total actions: {simulation_summary.get('total_actions', 'N/A')}\n"
                    f"- Active agents: {simulation_summary.get('total_agents', 'N/A')}\n\n"
                    f"Write this section now. Use markdown. Be analytical."
                ),
            },
        ]
        
        content = self.llm.chat(messages=messages, temperature=0.5, max_tokens=2048)
        
        section.content = content
        section.status = ReportStatus.COMPLETED
        
        return content
    
    def generate_full_report(
        self,
        requirement: str,
        graph_id: str,
        simulation_summary: Dict[str, Any],
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> str:
        """Generate the complete report end-to-end."""
        logger.info("Starting full report generation...")
        
        # Step 1: Plan
        if progress_callback:
            progress_callback("Planning report structure...", 0.05)
        
        outline = self.plan_outline(requirement, simulation_summary)
        
        # Step 2: Generate each section
        all_content = [f"# {outline.title}\n\n{outline.summary}\n"]
        
        for i, section in enumerate(outline.sections):
            if progress_callback:
                pct = 0.10 + (i / len(outline.sections)) * 0.85
                progress_callback(f"Writing: {section.title}", pct)
            
            content = self.generate_section(
                section, outline, graph_id, simulation_summary
            )
            all_content.append(f"\n## {section.title}\n\n{content}")
        
        full_report = "\n".join(all_content)
        
        if progress_callback:
            progress_callback("Report complete", 1.0)
        
        logger.info(f"Report generated: {len(full_report)} chars, {outline.total_sections} sections")
        return full_report
    
    def chat(
        self,
        message: str,
        report_content: str,
        graph_id: str,
    ) -> str:
        """Interactive chat about the generated report."""
        # Search for relevant context
        search_result = self.retrieval.quick_search(graph_id, message, limit=5)
        
        extra_context = ""
        if search_result.facts:
            extra_context = "\n## Additional Graph Data:\n" + "\n".join(
                f"- {f}" for f in search_result.facts
            )
        
        messages = [
            {
                "role": "system",
                "content": CHAT_PROMPT.format(
                    report_content=report_content[:3000]
                ),
            },
            {
                "role": "user",
                "content": f"{message}{extra_context}",
            },
        ]
        
        return self.llm.chat(messages=messages, temperature=0.5, max_tokens=2048)
    
    def _gather_evidence(
        self,
        graph_id: str,
        section: ReportSection,
        requirement: str,
    ) -> List[str]:
        """Gather evidence from the knowledge graph for a section."""
        all_facts = []
        
        # Search by section title
        r1 = self.retrieval.quick_search(graph_id, section.title, limit=5)
        all_facts.extend(r1.facts)
        
        # Search by section description
        if section.description:
            r2 = self.retrieval.quick_search(
                graph_id, section.description[:100], limit=5
            )
            all_facts.extend(r2.facts)
        
        # Deduplicate
        seen = set()
        unique_facts = []
        for f in all_facts:
            if f not in seen:
                seen.add(f)
                unique_facts.append(f)
        
        return unique_facts
