"""Researcher agent - from OpenHands + AgentCloud RAG patterns.

Specializes in information gathering, analysis, synthesis,
RAG-enhanced queries, fact-checking, and document analysis.
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional

from ai_multicolony.config.logging_config import get_logger
from ai_multicolony.core.base_agent import BaseAgent
from ai_multicolony.types.agent import AgentCapabilities, AgentConfig, AgentRole, AgentState
from ai_multicolony.types.memory import MemoryType
from ai_multicolony.types.messages import Message, MessageRole
from ai_multicolony.agents.researcher.prompts import (
    RESEARCHER_SYSTEM_PROMPT,
    RESEARCH_QUERY_PROMPT,
    RESEARCH_REPORT_PROMPT,
    RESEARCH_RAG_PROMPT,
    RESEARCH_FACT_CHECK_PROMPT,
    RESEARCH_COMPARATIVE_PROMPT,
    RESEARCH_DOCUMENT_ANALYSIS_PROMPT,
)

logger = get_logger(__name__)


class ResearcherAgent(BaseAgent):
    """Researcher agent for information gathering and analysis.

    From OpenHands research patterns and AgentCloud RAG. Searches,
    analyzes, and synthesizes information from multiple sources using
    a RAG-enhanced pipeline.

    State-specific behavior:
    - IDLE: Ready for research tasks
    - RUNNING: Actively searching, browsing, or analyzing
    - THINKING: Synthesizing findings or evaluating sources
    - WAITING: Waiting for search results or page loads
    - PAUSED: Research paused, resumable
    - ERROR: Research error, attempts recovery with simpler queries
    """

    # Track research history
    _research_log: list[dict[str, Any]]
    _sources_found: int = 0
    _queries_made: int = 0

    def __init__(self, config: Optional[AgentConfig] = None, **kwargs: Any) -> None:
        if config is None:
            config = AgentConfig(
                role=AgentRole.RESEARCHER,
                name="researcher-agent",
                description="Information gathering, analysis, and research specialist",
                tools=["search", "browser", "file", "memory"],
                system_prompt=RESEARCHER_SYSTEM_PROMPT,
                temperature=0.2,
                max_iterations=20,  # More iterations for multi-source research
                capabilities=AgentCapabilities(
                    research=True,
                    web_browsing=True,
                    web_search=True,
                    file_operations=True,
                    memory_management=True,
                ),
            )
        else:
            if not config.system_prompt:
                config.system_prompt = RESEARCHER_SYSTEM_PROMPT
            if not config.tools:
                config.tools = ["search", "browser", "file", "memory"]

        super().__init__(config=config, **kwargs)
        self._research_log = []
        self._sources_found = 0
        self._queries_made = 0

    # ------------------------------------------------------------------
    # Required tools
    # ------------------------------------------------------------------

    @classmethod
    def get_required_tools(cls) -> list[str]:
        """Return the list of tool names ResearcherAgent requires.

        Returns:
            Tools needed for research operations.
        """
        return ["search", "browser", "file", "memory"]

    # ------------------------------------------------------------------
    # System prompt
    # ------------------------------------------------------------------

    def get_system_prompt(self) -> str:
        """Get the system prompt for the Researcher agent."""
        return self.config.system_prompt or RESEARCHER_SYSTEM_PROMPT

    # ------------------------------------------------------------------
    # State-specific behavior
    # ------------------------------------------------------------------

    def _on_enter_running(self) -> None:
        """Hook called when entering RUNNING state."""
        logger.info(
            "researcher_agent_running",
            agent_id=self.agent_id,
            queries=self._queries_made,
            sources=self._sources_found,
        )

    def _on_enter_error(self) -> None:
        """Hook called when entering ERROR state."""
        logger.warning(
            "researcher_agent_error",
            agent_id=self.agent_id,
            error_count=self.error_count,
        )
        # Store error in research log
        self._research_log.append({
            "type": "error",
            "error_count": self.error_count,
        })

    def _on_enter_waiting(self) -> None:
        """Hook called when entering WAITING state."""
        logger.debug("researcher_agent_waiting", agent_id=self.agent_id)

    # ------------------------------------------------------------------
    # Core research methods
    # ------------------------------------------------------------------

    async def research(self, topic: str, depth: str = "medium", focus: str = "general") -> str:
        """Research a topic.

        Args:
            topic: The topic to research.
            depth: Research depth (quick, medium, deep).
            focus: Research focus area.

        Returns:
            Research findings.
        """
        prompt = RESEARCH_QUERY_PROMPT.format(topic=topic, depth=depth, focus=focus)
        result = await self.run(prompt)

        self._research_log.append({
            "type": "research",
            "topic": topic[:100],
            "depth": depth,
            "focus": focus,
            "result_preview": result[:200],
        })

        # Store in memory
        memory = self._get_memory_manager()
        memory.add_entry(
            agent_id=self.agent_id,
            content=f"Research on '{topic}': {result[:200]}",
            memory_type=MemoryType.LONG_TERM,
            importance=0.6,
            source="research",
        )

        return result

    async def create_report(self, topic: str, findings: str) -> str:
        """Create a research report from findings.

        Args:
            topic: The research topic.
            findings: The raw findings to synthesize.

        Returns:
            Formatted research report.
        """
        prompt = RESEARCH_REPORT_PROMPT.format(topic=topic, findings=findings)
        result = await self.run(prompt)

        self._research_log.append({
            "type": "report",
            "topic": topic[:100],
            "findings_length": len(findings),
        })

        return result

    async def fact_check(self, claim: str) -> str:
        """Fact-check a claim.

        Args:
            claim: The claim to verify.

        Returns:
            Fact-check results with evidence.
        """
        prompt = RESEARCH_FACT_CHECK_PROMPT.format(claim=claim)
        result = await self.run(prompt)

        self._research_log.append({
            "type": "fact_check",
            "claim": claim[:100],
            "result_preview": result[:200],
        })

        return result

    async def rag_query(self, query: str, context: str) -> str:
        """Perform a RAG-enhanced query.

        Uses retrieved context to augment the response generation,
        following the AgentCloud RAG pattern.

        Args:
            query: The research query.
            context: Pre-retrieved context documents.

        Returns:
            RAG-enhanced answer with citations.
        """
        prompt = RESEARCH_RAG_PROMPT.format(query=query, context=context)
        result = await self.run(prompt)

        self._research_log.append({
            "type": "rag_query",
            "query": query[:100],
            "context_length": len(context),
            "result_preview": result[:200],
        })

        return result

    async def comparative_analysis(
        self,
        subjects: str,
        criteria: str,
    ) -> str:
        """Perform a comparative analysis.

        Args:
            subjects: The subjects to compare (comma-separated).
            criteria: The comparison criteria (comma-separated).

        Returns:
            Comparative analysis results.
        """
        prompt = RESEARCH_COMPARATIVE_PROMPT.format(subjects=subjects, criteria=criteria)
        result = await self.run(prompt)

        self._research_log.append({
            "type": "comparative",
            "subjects": subjects[:100],
            "criteria": criteria[:100],
        })

        return result

    async def analyze_document(self, document: str) -> str:
        """Analyze a document.

        Args:
            document: The document text to analyze.

        Returns:
            Document analysis results.
        """
        prompt = RESEARCH_DOCUMENT_ANALYSIS_PROMPT.format(document=document)
        result = await self.run(prompt)

        self._research_log.append({
            "type": "document_analysis",
            "document_length": len(document),
            "result_preview": result[:200],
        })

        return result

    # ------------------------------------------------------------------
    # Research statistics
    # ------------------------------------------------------------------

    def get_research_log(self) -> list[dict[str, Any]]:
        """Get the research activity log.

        Returns:
            List of research log entries.
        """
        return list(self._research_log)

    def get_stats(self) -> dict[str, Any]:
        """Get research statistics.

        Returns:
            Dictionary with research metrics.
        """
        return {
            "queries_made": self._queries_made,
            "sources_found": self._sources_found,
            "research_tasks": len(self._research_log),
            "iterations": self.iteration_count,
        }

    def clear_research_log(self) -> None:
        """Clear the research activity log."""
        self._research_log.clear()
        self._sources_found = 0
        self._queries_made = 0
