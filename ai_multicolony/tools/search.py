"""SearchTool – web, local, and code search capabilities.

Autonomy level: **L0** (all operations are read-only).
"""

from __future__ import annotations

import logging
import os
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import MCPTool

logger = logging.getLogger(__name__)


class SearchResult:
    """A single search result."""

    __slots__ = ("title", "url", "snippet", "source", "relevance", "metadata")

    def __init__(
        self,
        title: str,
        url: str = "",
        snippet: str = "",
        source: str = "web",
        relevance: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.title = title
        self.url = url
        self.snippet = snippet
        self.source = source
        self.relevance = relevance
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source,
            "relevance": round(self.relevance, 3),
            "metadata": self.metadata,
        }


class SearchTool(MCPTool):
    """Web, local-file, and code search.

    Actions
    -------
    web     : search the web (simulated)
    local   : search local files by name/content
    code    : search code files with regex support
    """

    # ── MCPTool interface ────────────────────────────────────────

    def name(self) -> str:
        return "search.web"

    def category(self) -> str:
        return "knowledge"

    def autonomy_level(self) -> int:
        return 0

    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["action", "query"],
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["web", "local", "code"],
                    "description": "Search type",
                },
                "query": {
                    "type": "string",
                    "description": "Search query string",
                },
                "max_results": {
                    "type": "integer",
                    "default": 10,
                    "description": "Maximum results to return",
                },
                "provider": {
                    "type": "string",
                    "default": "duckduckgo",
                    "description": "Web search provider (simulated)",
                },
                "path": {
                    "type": "string",
                    "description": "Root path for local/code search",
                },
                "file_pattern": {
                    "type": "string",
                    "default": "*",
                    "description": "Glob pattern to filter files (local/code)",
                },
                "case_sensitive": {
                    "type": "boolean",
                    "default": False,
                    "description": "Case-sensitive search (code)",
                },
                "regex": {
                    "type": "boolean",
                    "default": False,
                    "description": "Treat query as regex (code)",
                },
            },
        }

    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "results": {"type": "array"},
                "total": {"type": "integer"},
                "action": {"type": "string"},
                "query": {"type": "string"},
            },
        }

    def error_codes(self) -> List[Dict[str, Any]]:
        return [
            {"code": 4001, "message": "Invalid search query"},
            {"code": 4002, "message": "Search path does not exist"},
            {"code": 4003, "message": "Regex compilation error"},
            {"code": 4004, "message": "Search timeout"},
        ]

    # ── Execute ──────────────────────────────────────────────────

    async def execute(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        action: str = params["action"]
        query: str = params["query"]

        if not query.strip():
            self.record_call(False)
            return {
                "results": [],
                "total": 0,
                "action": action,
                "query": query,
                "error": "Empty query",
            }

        start = time.monotonic()
        try:
            if action == "web":
                results = await self._web_search(params)
            elif action == "local":
                results = await self._local_search(params)
            elif action == "code":
                results = await self._code_search(params)
            else:
                results = []

            duration = (time.monotonic() - start) * 1000
            self.record_call(True, duration)

            return {
                "results": [r.to_dict() for r in results],
                "total": len(results),
                "action": action,
                "query": query,
                "duration_ms": round(duration, 2),
            }

        except re.error as exc:
            duration = (time.monotonic() - start) * 1000
            self.record_call(False, duration)
            return {
                "results": [],
                "total": 0,
                "action": action,
                "query": query,
                "error": f"Regex error: {exc}",
            }
        except Exception as exc:
            duration = (time.monotonic() - start) * 1000
            self.record_call(False, duration)
            return {
                "results": [],
                "total": 0,
                "action": action,
                "query": query,
                "error": str(exc),
            }

    # ── Web search (simulated) ───────────────────────────────────

    async def _web_search(self, params: Dict[str, Any]) -> List[SearchResult]:
        query: str = params["query"]
        max_results: int = params.get("max_results", 10)
        provider: str = params.get("provider", "duckduckgo")

        # Simulated web results
        results = []
        for i in range(min(max_results, 5)):
            results.append(SearchResult(
                title=f"Result {i + 1} for '{query}'",
                url=f"https://example.com/search/{i + 1}?q={query.replace(' ', '+')}",
                snippet=f"This is a simulated search result {i + 1} for the query '{query}'. "
                        f"Provider: {provider}.",
                source="web",
                relevance=1.0 - (i * 0.15),
                metadata={"provider": provider, "position": i + 1},
            ))
        return results

    # ── Local file search ────────────────────────────────────────

    async def _local_search(self, params: Dict[str, Any]) -> List[SearchResult]:
        query: str = params["query"]
        root: str = params.get("path", ".")
        max_results: int = params.get("max_results", 10)
        file_pattern: str = params.get("file_pattern", "*")

        if not os.path.isdir(root):
            return [SearchResult(
                title="Error", snippet=f"Path does not exist: {root}",
                source="local", relevance=0.0,
            )]

        results: List[SearchResult] = []
        q_lower = query.lower()

        for dirpath, dirnames, filenames in os.walk(root):
            for filename in filenames:
                if len(results) >= max_results:
                    break
                if not self._matches_glob(filename, file_pattern):
                    continue
                filepath = os.path.join(dirpath, filename)

                # Check filename match
                if q_lower in filename.lower():
                    results.append(SearchResult(
                        title=filename,
                        url=filepath,
                        snippet=f"File name matches '{query}'",
                        source="local",
                        relevance=0.9,
                        metadata={"type": "filename_match"},
                    ))
                    continue

                # Check content match (small files only)
                try:
                    if os.path.getsize(filepath) < 100_000:
                        with open(filepath, "r", errors="ignore") as f:
                            for line_num, line in enumerate(f, 1):
                                if q_lower in line.lower():
                                    results.append(SearchResult(
                                        title=filename,
                                        url=filepath,
                                        snippet=line.strip()[:200],
                                        source="local",
                                        relevance=0.7,
                                        metadata={
                                            "type": "content_match",
                                            "line": line_num,
                                        },
                                    ))
                                    break
                except (OSError, UnicodeDecodeError):
                    pass

            if len(results) >= max_results:
                break

        return results

    # ── Code search ──────────────────────────────────────────────

    async def _code_search(self, params: Dict[str, Any]) -> List[SearchResult]:
        query: str = params["query"]
        root: str = params.get("path", ".")
        max_results: int = params.get("max_results", 10)
        case_sensitive: bool = params.get("case_sensitive", False)
        use_regex: bool = params.get("regex", False)

        if not os.path.isdir(root):
            return [SearchResult(
                title="Error", snippet=f"Path does not exist: {root}",
                source="code", relevance=0.0,
            )]

        # Build pattern
        if use_regex:
            flags = 0 if case_sensitive else re.IGNORECASE
            try:
                pattern = re.compile(query, flags)
            except re.error as exc:
                raise re.error(f"Invalid regex: {exc}")
        else:
            escape = re.escape(query)
            flags = 0 if case_sensitive else re.IGNORECASE
            pattern = re.compile(escape, flags)

        # Code file extensions
        code_extensions = {
            ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java",
            ".c", ".cpp", ".h", ".hpp", ".rb", ".php", ".swift", ".kt",
            ".sh", ".bash", ".zsh", ".sql", ".html", ".css", ".yaml",
            ".yml", ".json", ".toml", ".cfg", ".ini", ".md", ".rst",
        }

        results: List[SearchResult] = []
        for dirpath, dirnames, filenames in os.walk(root):
            # Skip hidden / common non-code dirs
            dirnames[:] = [
                d for d in dirnames
                if not d.startswith(".") and d not in {"node_modules", "__pycache__", ".git", "venv", ".venv"}
            ]

            for filename in filenames:
                if len(results) >= max_results:
                    break
                ext = os.path.splitext(filename)[1].lower()
                if ext not in code_extensions:
                    continue

                filepath = os.path.join(dirpath, filename)
                try:
                    with open(filepath, "r", errors="ignore") as f:
                        for line_num, line in enumerate(f, 1):
                            match = pattern.search(line)
                            if match:
                                results.append(SearchResult(
                                    title=f"{filename}:{line_num}",
                                    url=filepath,
                                    snippet=line.strip()[:300],
                                    source="code",
                                    relevance=0.8,
                                    metadata={
                                        "file": filepath,
                                        "line": line_num,
                                        "match": match.group(0),
                                        "extension": ext,
                                    },
                                ))
                                if len(results) >= max_results:
                                    break
                except (OSError, UnicodeDecodeError):
                    pass

        return results

    # ── Helpers ──────────────────────────────────────────────────

    @staticmethod
    def _matches_glob(filename: str, pattern: str) -> bool:
        """Simple glob matching using fnmatch."""
        import fnmatch
        return fnmatch.fnmatch(filename, pattern)
