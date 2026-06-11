"""Researcher agent – web search, document analysis, and RAG.

Provides web search, document/codebase analysis, knowledge base queries,
and research report generation with Retrieval-Augmented Generation (RAG).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .base import BaseAgent
from ..types import AgentSpec, AgentType, Task, TaskResult

logger = logging.getLogger(__name__)


class ResearchDocument:
    """Represents a research document or search result."""

    def __init__(
        self,
        doc_id: str = "",
        title: str = "",
        source: str = "",
        content: str = "",
        url: str = "",
        relevance_score: float = 0.0,
    ):
        self.doc_id = doc_id or f"doc-{uuid.uuid4().hex[:8]}"
        self.title = title
        self.source = source
        self.content = content
        self.url = url
        self.relevance_score = relevance_score
        self.retrieved_at = datetime.now(timezone.utc)
        self.metadata: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "source": self.source,
            "url": self.url,
            "relevance_score": self.relevance_score,
            "content_length": len(self.content),
            "retrieved_at": self.retrieved_at.isoformat(),
        }


class ResearchReport:
    """Structured research report."""

    def __init__(self, report_id: str = "", topic: str = ""):
        self.report_id = report_id or f"rpt-{uuid.uuid4().hex[:8]}"
        self.topic = topic
        self.summary: str = ""
        self.findings: List[Dict[str, Any]] = []
        self.sources: List[Dict[str, Any]] = []
        self.recommendations: List[str] = []
        self.confidence: float = 0.0
        self.created_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "topic": self.topic,
            "summary": self.summary,
            "findings_count": len(self.findings),
            "sources_count": len(self.sources),
            "recommendations": self.recommendations,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
        }


class ResearcherAgent(BaseAgent):
    """Research agent for web search, codebase search, and RAG.

    Features
    --------
    * **Web search** – search the web for information.
    * **Document analysis** – analyze and extract information from documents.
    * **Knowledge base queries** – query local/embedded knowledge bases.
    * **Research report generation** – synthesize findings into reports.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.RESEARCHER, autonomy_level=1)
        if spec.agent_type != AgentType.RESEARCHER:
            spec.agent_type = AgentType.RESEARCHER
        super().__init__(spec=spec, **kwargs)
        self._search_results: List[Dict] = []
        self._documents: Dict[str, ResearchDocument] = {}
        self._reports: Dict[str, ResearchReport] = {}
        self._knowledge_base: Dict[str, Dict[str, Any]] = {}

    # ── Abstract hook implementations ──

    async def on_task(self, task: Task) -> Any:
        """Execute research task based on ``payload.action``."""
        action = task.payload.get("action", "web_search")
        if action == "web_search":
            return await self._web_search(task)
        elif action == "codebase_search":
            return await self._codebase_search(task)
        elif action == "api_search":
            return await self._api_search(task)
        elif action == "summarize":
            return await self._summarize(task)
        elif action == "document_analysis":
            return await self._document_analysis(task)
        elif action == "knowledge_query":
            return await self._knowledge_query(task)
        elif action == "generate_report":
            return await self._generate_report(task)
        else:
            return {"action": action, "result": f"Unknown research action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        """Handle A2A messages for research operations."""
        msg_type = message.get("message_type", "")
        if msg_type == "search_request":
            query = message.get("payload", {}).get("query", "")
            return {"query": query, "results": [], "total": 0}
        elif msg_type == "knowledge_query":
            query = message.get("payload", {}).get("query", "")
            return self._query_knowledge_base(query)
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        """Declare research capabilities."""
        return [
            "web_search", "document_analysis", "knowledge_base_query",
            "codebase_search", "summarization", "report_generation", "rag",
        ]

    # ── Web search ──

    async def _web_search(self, task: Task) -> Dict[str, Any]:
        """Search the web for information.

        Payload fields:
        * ``query`` – search query string.
        * ``max_results`` – maximum number of results (default 10).
        * ``search_type`` – ``"general"``, ``"academic"``, ``"news"``.
        """
        query = task.payload.get("query", "")
        max_results = task.payload.get("max_results", 10)
        search_type = task.payload.get("search_type", "general")

        # Simulate web search results
        results: List[Dict[str, Any]] = []
        for i in range(min(3, max_results)):
            doc = ResearchDocument(
                title=f"Result {i+1} for: {query}",
                source="web",
                content=f"Detailed information about {query}. This result covers relevant aspects of the query.",
                url=f"https://example.com/result/{i+1}",
                relevance_score=0.95 - (i * 0.1),
            )
            self._documents[doc.doc_id] = doc
            results.append(doc.to_dict())

        self._search_results.extend(results)

        return {
            "action": "web_search",
            "query": query,
            "search_type": search_type,
            "results": results,
            "total": len(results),
        }

    # ── Codebase search ──

    async def _codebase_search(self, task: Task) -> Dict[str, Any]:
        """Search the codebase for relevant code.

        Payload fields:
        * ``query`` – search query string.
        * ``file_patterns`` – glob patterns to include.
        * ``max_results`` – maximum number of matches.
        """
        query = task.payload.get("query", "")
        file_patterns = task.payload.get("file_patterns", ["**/*.py"])
        max_results = task.payload.get("max_results", 20)

        # Simulate codebase search
        matches: List[Dict[str, Any]] = []

        return {
            "action": "codebase_search",
            "query": query,
            "file_patterns": file_patterns,
            "matches": matches,
            "total": len(matches),
        }

    # ── API search ──

    async def _api_search(self, task: Task) -> Dict[str, Any]:
        """Search for relevant APIs.

        Payload fields:
        * ``category`` – API category (e.g., ``"payment"``, ``"auth"``).
        * ``query`` – search query.
        """
        category = task.payload.get("category", "")
        query = task.payload.get("query", "")

        return {
            "action": "api_search",
            "category": category,
            "query": query,
            "apis": [],
            "total": 0,
        }

    # ── Document analysis ──

    async def _document_analysis(self, task: Task) -> Dict[str, Any]:
        """Analyze a document for key information.

        Payload fields:
        * ``content`` – document content.
        * ``document_type`` – ``"text"``, ``"html"``, ``"pdf"``, ``"code"``.
        * ``extract_type`` – ``"summary"``, ``"entities"``, ``"key_facts"``.
        """
        content = task.payload.get("content", "")
        document_type = task.payload.get("document_type", "text")
        extract_type = task.payload.get("extract_type", "summary")

        # Simulate document analysis
        key_facts: List[str] = []
        entities: List[str] = []

        if content:
            words = content.split()
            # Extract potential entities (capitalized words)
            entities = list(set(w for w in words if w[0].isupper() and len(w) > 2))[:10]
            # Extract key sentences
            sentences = content.split(".")
            key_facts = [s.strip() for s in sentences[:5] if len(s.strip()) > 20]

        doc = ResearchDocument(
            title="Analyzed document",
            source=document_type,
            content=content,
        )
        self._documents[doc.doc_id] = doc

        result: Dict[str, Any] = {
            "action": "document_analysis",
            "doc_id": doc.doc_id,
            "document_type": document_type,
        }

        if extract_type == "summary":
            result["summary"] = content[:200] if content else "Empty document"
            result["word_count"] = len(content.split()) if content else 0
        elif extract_type == "entities":
            result["entities"] = entities
        elif extract_type == "key_facts":
            result["key_facts"] = key_facts
        else:
            result.update({
                "summary": content[:200] if content else "",
                "entities": entities,
                "key_facts": key_facts,
            })

        return result

    # ── Knowledge base queries ──

    async def _knowledge_query(self, task: Task) -> Dict[str, Any]:
        """Query the local knowledge base using RAG.

        Payload fields:
        * ``query`` – natural-language query.
        * ``top_k`` – number of results to return.
        * ``min_relevance`` – minimum relevance score threshold.
        """
        query = task.payload.get("query", "")
        top_k = task.payload.get("top_k", 5)
        min_relevance = task.payload.get("min_relevance", 0.5)

        results = self._query_knowledge_base(query)

        # Filter by relevance
        filtered = [r for r in results if r.get("relevance", 0) >= min_relevance]
        filtered = filtered[:top_k]

        return {
            "action": "knowledge_query",
            "query": query,
            "results": filtered,
            "total": len(filtered),
        }

    def _query_knowledge_base(self, query: str) -> List[Dict[str, Any]]:
        """Search the knowledge base for relevant entries."""
        results: List[Dict[str, Any]] = []
        query_lower = query.lower()

        for key, entry in self._knowledge_base.items():
            # Simple relevance scoring based on keyword overlap
            content = str(entry.get("content", "")).lower()
            overlap = sum(1 for word in query_lower.split() if word in content)
            relevance = min(1.0, overlap / max(1, len(query_lower.split())))
            if relevance > 0:
                results.append({
                    "key": key,
                    "content": entry.get("content", ""),
                    "relevance": relevance,
                })

        results.sort(key=lambda r: r["relevance"], reverse=True)
        return results

    def add_to_knowledge_base(self, key: str, content: str, metadata: Optional[Dict] = None) -> None:
        """Add an entry to the local knowledge base."""
        self._knowledge_base[key] = {
            "content": content,
            "metadata": metadata or {},
            "added_at": datetime.now(timezone.utc).isoformat(),
        }

    # ── Summarization ──

    async def _summarize(self, task: Task) -> Dict[str, Any]:
        """Summarize content.

        Payload fields:
        * ``content`` – text content to summarize.
        * ``max_length`` – maximum summary length in words.
        """
        content = task.payload.get("content", "")
        max_length = task.payload.get("max_length", 100)

        # Simple extractive summarization
        sentences = content.split(".") if content else []
        summary_sentences = sentences[:max(1, len(sentences) // 3)]
        summary = ". ".join(s.strip() for s in summary_sentences if s.strip())

        return {
            "action": "summarize",
            "summary": summary[:max_length * 10],  # rough word-to-char
            "original_length": len(content),
            "summary_length": len(summary),
            "compression_ratio": len(summary) / max(1, len(content)),
        }

    # ── Report generation ──

    async def _generate_report(self, task: Task) -> Dict[str, Any]:
        """Generate a structured research report.

        Payload fields:
        * ``topic`` – research topic.
        * ``query`` – search query for the report.
        * ``sources`` – optional list of pre-gathered sources.
        """
        topic = task.payload.get("topic", task.payload.get("query", ""))
        query = task.payload.get("query", topic)
        sources = task.payload.get("sources", [])

        # Gather sources if not provided
        if not sources:
            search_result = await self._web_search(Task(
                description=query,
                payload={"query": query, "max_results": 5},
            ))
            sources = search_result.get("results", [])

        report = ResearchReport(topic=topic)
        report.summary = f"Research report on: {topic}"
        report.findings = [
            {"title": f"Finding {i+1}", "content": s.get("title", ""), "source": s.get("url", "")}
            for i, s in enumerate(sources)
        ]
        report.sources = sources
        report.recommendations = [
            f"Gather more information about {topic}",
            "Verify findings with multiple sources",
            "Consider alternative perspectives",
        ]
        report.confidence = 0.75

        self._reports[report.report_id] = report

        return {
            "action": "generate_report",
            **report.to_dict(),
            "findings": report.findings,
            "sources": report.sources,
            "summary": report.summary,
        }

    # ── Accessors ──

    @property
    def search_results(self) -> List[Dict]:
        """All accumulated search results."""
        return list(self._search_results)

    @property
    def document_count(self) -> int:
        """Number of indexed documents."""
        return len(self._documents)
