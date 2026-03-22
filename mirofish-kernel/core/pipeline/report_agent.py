"""
Report Agent — Stage 7 of the MiroFish Pipeline (Enhanced TIP-10)

ReACT (Reasoning + Acting) pattern for report generation:
1. Plan report outline from simulation results
2. For each section: Think → Act (multi-tool) → Observe → Write → Reflect
3. Fact-check claims against graph data
4. Interactive chat post-generation with tool access

Enhancements over v1:
- Multi-tool loop (up to 8 tool calls per section)
- Self-reflection: reviews own output, rewrites if insufficient
- Fact-checking: verifies claims against graph, marks confidence
- Agent interview: can "ask" simulated agents for qualitative insights
"""

import json
import re
from typing import Dict, Any, List, Optional, Callable

from ..interfaces.llm_provider import LLMProvider
from ..models.report import ReportOutline, ReportSection, ReportStatus
from .retrieval_tools import RetrievalTools
from ..tools.logger import get_logger

logger = get_logger("mirofish.pipeline.report_agent")


# ─── Prompts ──────────────────────────────────────────────────

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

Plan 5-8 sections that cover:
1. Executive summary / overview
2. Key findings from simulation
3. Agent behavior analysis (who did what, stance breakdown)
4. Trend/pattern analysis (sentiment shifts, activity patterns)
5. Verified predictions / forecasts
6. Risk factors and uncertainties
7. Recommendations (if applicable)
8. Methodology note (brief)
"""

SECTION_WRITER_PROMPT = """You are an expert analyst writing a section of a prediction report.

## Available Evidence
{evidence}

## Simulation Context
{sim_context}

## Instructions
Write section "{section_title}" for the report "{report_title}".
Section goal: {section_desc}

Requirements:
- Use markdown formatting
- Be analytical, not just descriptive
- Cite specific facts with [Source: graph] or [Source: simulation] tags
- Write 300-600 words
- Include specific numbers, percentages, and agent names where available
- Distinguish between verified findings and hypotheses
"""

REFLECTION_PROMPT = """Review this report section for quality. Does it:
1. Answer the section's stated goal?
2. Cite specific evidence (not vague claims)?
3. Distinguish verified facts from hypotheses?
4. Provide analytical insight (not just summary)?

Section goal: {section_desc}
Section content:
{content}

If the section is adequate, respond with: ADEQUATE
If it needs improvement, respond with specific suggestions starting with: IMPROVE: <suggestions>
"""

FACT_CHECK_PROMPT = """You are a fact-checker. Given a report section and evidence from the knowledge graph, verify each major claim.

## Section Content
{content}

## Available Evidence
{evidence}

Output ONLY valid JSON:
{
    "claims": [
        {
            "claim": "The exact claim text",
            "status": "verified" | "partially_verified" | "unverified",
            "evidence": "Supporting evidence or why unverified",
            "confidence": 0.0 to 1.0
        }
    ],
    "overall_confidence": 0.0 to 1.0
}
"""

INTERVIEW_PROMPT = """You are simulating agent "{agent_name}" ({agent_type}) in a multi-agent simulation.

Agent profile:
- Personality: {personality}
- Stance: {stance}
- Expertise: {expertise}

The analyst is interviewing you about: {question}

Respond in character as this agent would. Be specific about your motivations and reasoning. Keep response under 150 words.
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
    Enhanced ReACT-based report generation agent.

    Pipeline:
    1. plan_outline() — LLM generates report structure
    2. generate_section() — Multi-tool ReACT loop per section
    3. _reflect() — Self-review, rewrite if needed
    4. _fact_check() — Verify claims against graph
    5. generate_full_report() — End-to-end with all enhancements
    6. interview_agent() — "Ask" a simulated agent
    7. chat() — Interactive Q&A
    """

    def __init__(
        self,
        llm: LLMProvider,
        retrieval: RetrievalTools,
        max_tool_calls_per_section: int = 8,
        max_reflection_rounds: int = 1,
        enable_fact_check: bool = True,
    ):
        self.llm = llm
        self.retrieval = retrieval
        self.max_tool_calls = max_tool_calls_per_section
        self.max_reflections = max_reflection_rounds
        self.enable_fact_check = enable_fact_check
        # Agent profiles cache for interviews (set by orchestrator)
        self._agent_profiles: List[Dict[str, Any]] = []

    def set_agent_profiles(self, profiles: List[Dict[str, Any]]):
        """Cache agent profiles for interview tool."""
        self._agent_profiles = profiles

    # ═══ 1. Plan ══════════════════════════════════════════════

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
            {"role": "user", "content": f"## Requirement\n{requirement}\n\n## Simulation Results\n{summary_text}"},
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

    # ═══ 2. Generate Section (Enhanced ReACT) ════════════════

    def generate_section(
        self,
        section: ReportSection,
        outline: ReportOutline,
        graph_id: str,
        simulation_summary: Dict[str, Any],
    ) -> str:
        """
        Generate a section with multi-tool ReACT loop.

        Think → Search (multiple tools) → Interview agents → Write → Reflect → Fact-check
        """
        logger.info(f"Generating section: {section.title}")
        section.status = ReportStatus.GENERATING

        # Step 1: Multi-tool evidence gathering
        evidence = self._gather_evidence_multi(graph_id, section, outline.requirement)

        # Step 2: Optional agent interviews for qualitative insights
        interviews = self._interview_relevant_agents(section, outline.requirement)

        # Step 3: Build context and write
        sim_context = (
            f"- Total rounds: {simulation_summary.get('total_rounds', 'N/A')}\n"
            f"- Total actions: {simulation_summary.get('total_actions', 'N/A')}\n"
            f"- Active agents: {simulation_summary.get('total_agents', 'N/A')}\n"
            f"- Content created: {simulation_summary.get('content_created', 'N/A')}"
        )
        top_agents = simulation_summary.get("top_active_agents", [])
        if top_agents:
            sim_context += "\n- Most active: " + ", ".join(
                f"{a.get('name', '?')} ({a.get('actions', 0)} actions)" for a in top_agents[:5]
            )

        evidence_text = "\n".join(f"- {f}" for f in evidence[:20])
        if interviews:
            evidence_text += "\n\n### Agent Interviews:\n" + "\n".join(
                f"- [{iv['agent']}]: \"{iv['response'][:150]}\"" for iv in interviews
            )

        content = self.llm.chat(
            messages=[
                {"role": "system", "content": SECTION_WRITER_PROMPT.format(
                    evidence=evidence_text,
                    sim_context=sim_context,
                    section_title=section.title,
                    report_title=outline.title,
                    section_desc=section.description,
                )},
                {"role": "user", "content": "Write this section now."},
            ],
            temperature=0.5,
            max_tokens=2048,
        )

        # Step 4: Self-reflection
        for r in range(self.max_reflections):
            reflection = self._reflect(content, section.description)
            if reflection is None:
                break  # ADEQUATE
            logger.info(f"Section '{section.title}' reflection round {r+1}: improving")
            content = self.llm.chat(
                messages=[
                    {"role": "system", "content": f"Improve this report section based on feedback.\n\nFeedback: {reflection}\n\nEvidence:\n{evidence_text}"},
                    {"role": "user", "content": f"Original section:\n{content}\n\nRewrite with improvements."},
                ],
                temperature=0.4,
                max_tokens=2048,
            )

        # Step 5: Fact-check
        if self.enable_fact_check and evidence:
            fact_result = self._fact_check(content, evidence, graph_id)
            if fact_result:
                section.reflections.append(f"Fact-check: {fact_result.get('overall_confidence', 'N/A')} confidence")
                # Append confidence note if low
                confidence = fact_result.get("overall_confidence", 1.0)
                if confidence < 0.6:
                    content += f"\n\n> *Note: This section has moderate confidence ({confidence:.0%}). Some claims could not be fully verified against available data.*"

        section.content = content
        section.status = ReportStatus.COMPLETED
        section.tool_calls = [{"type": "evidence_gathered", "count": len(evidence)}]

        return content

    # ═══ 3. Full Report ══════════════════════════════════════

    def generate_full_report(
        self,
        requirement: str,
        graph_id: str,
        simulation_summary: Dict[str, Any],
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> str:
        """Generate complete report with all enhancements."""
        logger.info("Starting enhanced report generation...")

        if progress_callback:
            progress_callback("Planning report structure...", 0.05)

        outline = self.plan_outline(requirement, simulation_summary)

        all_content = [f"# {outline.title}\n\n{outline.summary}\n"]

        for i, section in enumerate(outline.sections):
            if progress_callback:
                pct = 0.10 + (i / max(len(outline.sections), 1)) * 0.80
                progress_callback(f"Writing: {section.title}", pct)

            content = self.generate_section(section, outline, graph_id, simulation_summary)
            all_content.append(f"\n## {section.title}\n\n{content}")

        full_report = "\n".join(all_content)

        if progress_callback:
            progress_callback("Report complete", 1.0)

        logger.info(f"Report generated: {len(full_report)} chars, {outline.total_sections} sections")
        return full_report

    # ═══ 4. Interview Agent ══════════════════════════════════

    def interview_agent(
        self,
        agent_profile: Dict[str, Any],
        question: str,
    ) -> str:
        """Interview a simulated agent for qualitative insights."""
        messages = [
            {"role": "system", "content": INTERVIEW_PROMPT.format(
                agent_name=agent_profile.get("name", "Agent"),
                agent_type=agent_profile.get("entity_type", "Unknown"),
                personality=agent_profile.get("personality", "neutral"),
                stance=agent_profile.get("stance", "no stated position"),
                expertise=", ".join(agent_profile.get("expertise", ["general"])),
                question=question,
            )},
            {"role": "user", "content": question},
        ]

        return self.llm.chat(messages=messages, temperature=0.6, max_tokens=512)

    # ═══ 5. Chat ═════════════════════════════════════════════

    def chat(
        self,
        message: str,
        report_content: str,
        graph_id: str,
    ) -> str:
        """Interactive chat about the generated report."""
        search_result = self.retrieval.quick_search(graph_id, message, limit=5)

        extra_context = ""
        if search_result.facts:
            extra_context = "\n## Additional Graph Data:\n" + "\n".join(
                f"- {f}" for f in search_result.facts
            )

        messages = [
            {"role": "system", "content": CHAT_PROMPT.format(report_content=report_content[:3000])},
            {"role": "user", "content": f"{message}{extra_context}"},
        ]

        return self.llm.chat(messages=messages, temperature=0.5, max_tokens=2048)

    # ═══ Internal Methods ════════════════════════════════════

    def _gather_evidence_multi(
        self,
        graph_id: str,
        section: ReportSection,
        requirement: str,
    ) -> List[str]:
        """Multi-tool evidence gathering (up to max_tool_calls searches)."""
        all_facts = []
        queries_used = set()

        # Tool 1: Search by section title
        r = self.retrieval.quick_search(graph_id, section.title, limit=5)
        all_facts.extend(r.facts)
        queries_used.add(section.title)

        # Tool 2: Search by section description
        if section.description and len(queries_used) < self.max_tool_calls:
            r = self.retrieval.quick_search(graph_id, section.description[:100], limit=5)
            all_facts.extend(r.facts)
            queries_used.add(section.description[:100])

        # Tool 3: Search by requirement
        if requirement and len(queries_used) < self.max_tool_calls:
            r = self.retrieval.quick_search(graph_id, requirement[:100], limit=5)
            all_facts.extend(r.facts)

        # Tool 4: Deep insight search if we don't have enough facts
        if len(all_facts) < 5 and len(queries_used) < self.max_tool_calls:
            try:
                insight = self.retrieval.insight_forge(
                    graph_id, f"{section.title}: {section.description[:80]}", max_sub_questions=2
                )
                for sr in insight.sub_results:
                    all_facts.extend(sr.facts)
                if insight.synthesis:
                    all_facts.append(f"[Synthesis] {insight.synthesis}")
            except Exception as e:
                logger.warning(f"Insight forge failed: {e}")

        # Tool 5: Panorama search for historical context
        if len(queries_used) < self.max_tool_calls:
            try:
                r = self.retrieval.panorama_search(graph_id, section.title, limit=5)
                all_facts.extend(f"[Historical] {f}" for f in r.facts if f not in all_facts)
            except Exception:
                pass

        # Deduplicate
        seen = set()
        unique = []
        for f in all_facts:
            if f not in seen:
                seen.add(f)
                unique.append(f)

        logger.info(f"Evidence gathered for '{section.title}': {len(unique)} facts from {len(queries_used)}+ searches")
        return unique

    def _interview_relevant_agents(
        self,
        section: ReportSection,
        requirement: str,
    ) -> List[Dict[str, str]]:
        """Interview 1-2 agents most relevant to the section topic."""
        if not self._agent_profiles:
            return []

        interviews = []
        question = f"What is your view on {section.title.lower()}? How does this relate to {requirement[:80]}?"

        # Pick top 2 agents by relevance (highest influence first)
        sorted_agents = sorted(
            self._agent_profiles,
            key=lambda a: a.get("influence_score", 0),
            reverse=True,
        )

        for agent in sorted_agents[:2]:
            try:
                response = self.interview_agent(agent, question)
                interviews.append({
                    "agent": agent.get("name", "Unknown"),
                    "response": response,
                })
            except Exception as e:
                logger.warning(f"Interview failed for {agent.get('name')}: {e}")

        return interviews

    def _reflect(self, content: str, section_desc: str) -> Optional[str]:
        """Self-reflect on generated content. Returns improvement suggestions or None if adequate."""
        try:
            response = self.llm.chat(
                messages=[
                    {"role": "system", "content": REFLECTION_PROMPT.format(
                        section_desc=section_desc,
                        content=content[:2000],
                    )},
                    {"role": "user", "content": "Review this section."},
                ],
                temperature=0.3,
                max_tokens=512,
            )

            if "ADEQUATE" in response.upper():
                return None
            if response.upper().startswith("IMPROVE:"):
                return response[8:].strip()
            return None  # Ambiguous response = treat as adequate
        except Exception:
            return None

    def _fact_check(
        self,
        content: str,
        evidence: List[str],
        graph_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Fact-check section claims against graph evidence."""
        if not evidence:
            return None

        evidence_text = "\n".join(f"- {f}" for f in evidence[:15])

        try:
            result = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": FACT_CHECK_PROMPT.format(
                        content=content[:2000],
                        evidence=evidence_text,
                    )},
                    {"role": "user", "content": "Fact-check this section."},
                ],
                temperature=0.2,
                max_tokens=2048,
            )
            return result
        except Exception as e:
            logger.warning(f"Fact-check failed: {e}")
            return None
