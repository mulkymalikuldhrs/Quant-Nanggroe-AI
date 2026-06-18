"""Multi-engine web search tool for the AI MultiColony Ecosystem.

Supports Google, Bing, DuckDuckGo, and SearXNG search engines with
result ranking, deduplication, rate limiting per engine, and automatic
fallback on failure.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
import time
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import quote_plus, urljoin

from ai_multicolony.config.logging_config import get_logger
from ai_multicolony.core.tool_base import BaseTool
from ai_multicolony.exceptions import ToolExecutionError
from ai_multicolony.types.tools import ToolCall, ToolDefinition, ToolParameter, ToolResult, ToolType

logger = get_logger(__name__)


@dataclass
class SearchResult:
    """A single search result entry."""

    title: str
    url: str
    snippet: str
    source_engine: str
    rank: int = 0
    score: float = 0.0

    @property
    def dedup_key(self) -> str:
        """Key used for deduplication (normalized URL)."""
        # Strip trailing slash, query params for dedup
        normalized = self.url.rstrip("/")
        # Remove common tracking params
        normalized = re.sub(r"[?&](utm_[^&=]+|ref=[^&=]+|source=[^&=]+)", "", normalized)
        return normalized.lower()


@dataclass
class _RateLimiter:
    """Simple per-engine rate limiter."""

    min_interval: float = 1.0  # seconds between requests
    _last_request: float = 0.0

    async def acquire(self) -> None:
        """Wait until the rate limit allows a new request."""
        now = time.monotonic()
        elapsed = now - self._last_request
        if elapsed < self.min_interval:
            await asyncio.sleep(self.min_interval - elapsed)
        self._last_request = time.monotonic()


class SearchTool(BaseTool):
    """Multi-engine web search tool.

    Features:
    - Multiple search engines (Google, Bing, DuckDuckGo, SearXNG)
    - Result ranking and deduplication
    - Rate limiting per engine
    - Automatic fallback on failure
    - Configurable result count and time filtering
    """

    def __init__(self, config: Optional[dict[str, Any]] = None) -> None:
        super().__init__(config)
        self._default_engine = self._config.get("engine", "duckduckgo")
        self._searxng_url = self._config.get("searxng_url", "http://localhost:8080")
        self._max_results = self._config.get("max_results", 10)

        # Rate limiters per engine
        self._rate_limiters: dict[str, _RateLimiter] = {
            "google": _RateLimiter(min_interval=self._config.get("google_rate_limit", 2.0)),
            "bing": _RateLimiter(min_interval=self._config.get("bing_rate_limit", 2.0)),
            "duckduckgo": _RateLimiter(min_interval=self._config.get("ddg_rate_limit", 1.5)),
            "searxng": _RateLimiter(min_interval=self._config.get("searxng_rate_limit", 0.5)),
        }

        # Fallback order when the primary engine fails
        self._fallback_order: list[str] = self._config.get(
            "fallback_order", ["duckduckgo", "searxng", "google", "bing"]
        )

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="search",
            description="Search the web using multiple search engines with dedup and fallback",
            tool_type=ToolType.SEARCH,
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="Search query",
                    required=True,
                ),
                ToolParameter(
                    name="engine",
                    type="string",
                    description="Primary search engine to use",
                    required=False,
                    default=self._default_engine,
                    enum=["google", "bing", "searxng", "duckduckgo"],
                ),
                ToolParameter(
                    name="max_results",
                    type="integer",
                    description="Maximum number of results",
                    required=False,
                    default=self._max_results,
                ),
                ToolParameter(
                    name="time_range",
                    type="string",
                    description="Time range filter: day, week, month, year",
                    required=False,
                    enum=["day", "week", "month", "year"],
                ),
                ToolParameter(
                    name="fallback",
                    type="boolean",
                    description="Whether to fall back to other engines on failure",
                    required=False,
                    default=True,
                ),
            ],
            tags=["search", "web", "information"],
            requires_permission="search.use",
        )

    # ------------------------------------------------------------------
    # Main execution
    # ------------------------------------------------------------------

    async def execute(self, tool_call: ToolCall) -> ToolResult:
        """Execute a web search.

        Args:
            tool_call: The tool call with search arguments.

        Returns:
            ToolResult with search results.
        """
        query = tool_call.arguments.get("query", "")
        engine = tool_call.arguments.get("engine", self._default_engine)
        max_results = tool_call.arguments.get("max_results", self._max_results)
        time_range = tool_call.arguments.get("time_range")
        use_fallback = tool_call.arguments.get("fallback", True)

        if not query:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="search",
                success=False, error="No search query specified",
            )

        try:
            import httpx
        except ImportError:
            raise ToolExecutionError(
                "httpx not installed. Install with: pip install httpx",
                tool_name="search",
            )

        # Try primary engine first
        results = await self._search_with_engine(
            httpx, query, engine, max_results, time_range
        )

        # Fallback to other engines if primary failed
        if not results and use_fallback:
            for fallback_engine in self._fallback_order:
                if fallback_engine == engine:
                    continue
                logger.info("search_fallback", from_engine=engine, to_engine=fallback_engine)
                results = await self._search_with_engine(
                    httpx, query, fallback_engine, max_results, time_range
                )
                if results:
                    break

        if not results:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="search",
                success=True, output="No results found",
                metadata={"query": query, "engine": engine},
            )

        # Deduplicate and rank
        results = self._deduplicate(results)
        results = self._rank_results(results, query)
        results = results[:max_results]

        # Format output
        formatted = self._format_results(results)
        return ToolResult(
            tool_call_id=tool_call.id, tool_name="search",
            success=True, output=formatted,
            metadata={
                "query": query,
                "engine": engine,
                "result_count": len(results),
                "engines_used": list({r.source_engine for r in results}),
            },
        )

    # ------------------------------------------------------------------
    # Engine implementations
    # ------------------------------------------------------------------

    async def _search_with_engine(
        self,
        httpx_module: Any,
        query: str,
        engine: str,
        max_results: int,
        time_range: Optional[str] = None,
    ) -> list[SearchResult]:
        """Search using a specific engine with rate limiting.

        Args:
            httpx_module: The httpx module.
            query: Search query.
            engine: Engine name.
            max_results: Max results.
            time_range: Optional time filter.

        Returns:
            List of SearchResult objects.
        """
        limiter = self._rate_limiters.get(engine, _RateLimiter())
        await limiter.acquire()

        try:
            async with httpx_module.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                if engine == "searxng":
                    return await self._search_searxng(client, query, max_results, time_range)
                elif engine == "duckduckgo":
                    return await self._search_duckduckgo(client, query, max_results)
                elif engine == "google":
                    return await self._search_google(client, query, max_results)
                elif engine == "bing":
                    return await self._search_bing(client, query, max_results)
                else:
                    logger.warning("unknown_engine", engine=engine)
                    return []
        except Exception as e:
            logger.warning("search_engine_error", engine=engine, error=str(e))
            return []

    async def _search_searxng(
        self,
        client: Any,
        query: str,
        max_results: int,
        time_range: Optional[str] = None,
    ) -> list[SearchResult]:
        """Search using SearXNG."""
        params: dict[str, Any] = {
            "q": query,
            "format": "json",
            "limit": max_results,
        }
        if time_range:
            params["time_range"] = time_range

        response = await client.get(f"{self._searxng_url}/search", params=params)
        data = response.json()

        results: list[SearchResult] = []
        for item in data.get("results", [])[:max_results]:
            results.append(SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("content", ""),
                source_engine="searxng",
            ))
        return results

    async def _search_duckduckgo(
        self,
        client: Any,
        query: str,
        max_results: int,
    ) -> list[SearchResult]:
        """Search using DuckDuckGo HTML version."""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        }
        response = await client.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers=headers,
        )

        results: list[SearchResult] = []
        html = response.text

        # Parse DuckDuckGo HTML results
        # Result links are in <a class="result__a"> elements
        result_pattern = re.compile(
            r'<a[^>]+class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
            re.DOTALL,
        )
        snippet_pattern = re.compile(
            r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
            re.DOTALL,
        )

        result_matches = result_pattern.findall(html)
        snippet_matches = snippet_pattern.findall(html)

        for i, (url, title) in enumerate(result_matches[:max_results]):
            # Clean HTML from title
            clean_title = re.sub(r"<[^>]+>", "", title).strip()
            # DuckDuckGo uses redirect URLs; extract actual URL
            if "//duckduckgo.com/l/" in url:
                # Try to extract from uddg parameter
                uddg_match = re.search(r"uddg=([^&]+)", url)
                if uddg_match:
                    from urllib.parse import unquote
                    url = unquote(uddg_match.group(1))

            snippet = ""
            if i < len(snippet_matches):
                snippet = re.sub(r"<[^>]+>", "", snippet_matches[i]).strip()

            results.append(SearchResult(
                title=clean_title,
                url=url,
                snippet=snippet[:500],
                source_engine="duckduckgo",
            ))

        return results

    async def _search_google(
        self,
        client: Any,
        query: str,
        max_results: int,
    ) -> list[SearchResult]:
        """Search using Google Custom Search API (if configured) or HTML fallback."""
        api_key = self._config.get("google_api_key")
        cx = self._config.get("google_cx")

        if api_key and cx:
            # Use the official Custom Search API
            response = await client.get(
                "https://www.googleapis.com/customsearch/v1",
                params={
                    "key": api_key,
                    "cx": cx,
                    "q": query,
                    "num": min(max_results, 10),
                },
            )
            data = response.json()
            results: list[SearchResult] = []
            for item in data.get("items", []):
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    source_engine="google",
                ))
            return results
        else:
            # HTML scrape fallback (fragile but works without API key)
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            }
            response = await client.get(
                "https://www.google.com/search",
                params={"q": query, "num": min(max_results, 10)},
                headers=headers,
            )
            html = response.text
            results = []

            # Extract results from Google HTML
            link_pattern = re.compile(r'<a[^>]+href="/url\?q=([^&"]+)&[^"]*"[^>]*>(.*?)</a>', re.DOTALL)
            for url, title in link_pattern.findall(html)[:max_results]:
                clean_title = re.sub(r"<[^>]+>", "", title).strip()
                if not clean_title or clean_title.startswith("http"):
                    continue
                results.append(SearchResult(
                    title=clean_title,
                    url=url,
                    snippet="",
                    source_engine="google",
                ))
            return results

    async def _search_bing(
        self,
        client: Any,
        query: str,
        max_results: int,
    ) -> list[SearchResult]:
        """Search using Bing (HTML scrape fallback)."""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        }
        response = await client.get(
            "https://www.bing.com/search",
            params={"q": query, "count": min(max_results, 10)},
            headers=headers,
        )
        html = response.text
        results: list[SearchResult] = []

        # Extract Bing results
        link_pattern = re.compile(r'<li class="b_algo"[^>]*>.*?<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.DOTALL)
        snippet_pattern = re.compile(r'<div class="b_caption"[^>]*>.*?<p>(.*?)</p>', re.DOTALL)

        link_matches = link_pattern.findall(html)
        snippet_matches = snippet_pattern.findall(html)

        for i, (url, title) in enumerate(link_matches[:max_results]):
            clean_title = re.sub(r"<[^>]+>", "", title).strip()
            snippet = ""
            if i < len(snippet_matches):
                snippet = re.sub(r"<[^>]+>", "", snippet_matches[i]).strip()[:500]
            results.append(SearchResult(
                title=clean_title,
                url=url,
                snippet=snippet,
                source_engine="bing",
            ))

        return results

    # ------------------------------------------------------------------
    # Post-processing
    # ------------------------------------------------------------------

    def _deduplicate(self, results: list[SearchResult]) -> list[SearchResult]:
        """Remove duplicate results based on normalized URL.

        When duplicates are found, keep the one with the higher score
        or the one from the earlier (preferred) engine.

        Args:
            results: Raw search results.

        Returns:
            Deduplicated results.
        """
        seen: dict[str, SearchResult] = {}
        engine_order = {e: i for i, e in enumerate(self._fallback_order)}

        for result in results:
            key = result.dedup_key
            if key in seen:
                existing = seen[key]
                # Keep the one from the more preferred engine
                if engine_order.get(result.source_engine, 99) < engine_order.get(existing.source_engine, 99):
                    seen[key] = result
            else:
                seen[key] = result

        return list(seen.values())

    def _rank_results(self, results: list[SearchResult], query: str) -> list[SearchResult]:
        """Rank and score search results.

        Scoring factors:
        - Query term presence in title/snippet
        - Source engine preference
        - URL quality heuristics

        Args:
            results: Deduplicated results.
            query: The original query.

        Returns:
            Ranked results with scores.
        """
        query_terms = set(query.lower().split())
        engine_weights = {"google": 1.0, "bing": 0.9, "duckduckgo": 0.95, "searxng": 0.85}

        for result in results:
            score = 0.0

            # Query term matching in title
            title_terms = set(result.title.lower().split())
            title_overlap = len(query_terms & title_terms) / max(len(query_terms), 1)
            score += title_overlap * 3.0

            # Query term matching in snippet
            snippet_terms = set(result.snippet.lower().split())
            snippet_overlap = len(query_terms & snippet_terms) / max(len(query_terms), 1)
            score += snippet_overlap * 1.0

            # Engine weight
            score += engine_weights.get(result.source_engine, 0.5) * 0.5

            # URL quality (prefer HTTPS, penalize very long URLs)
            if result.url.startswith("https://"):
                score += 0.1
            if len(result.url) > 200:
                score -= 0.2

            result.score = score

        results.sort(key=lambda r: r.score, reverse=True)

        # Assign ranks
        for i, result in enumerate(results):
            result.rank = i + 1

        return results

    def _format_results(self, results: list[SearchResult]) -> str:
        """Format search results as readable text.

        Args:
            results: Ranked search results.

        Returns:
            Formatted string.
        """
        lines: list[str] = []
        for r in results:
            lines.append(
                f"[{r.rank}] {r.title}\n"
                f"    URL: {r.url}\n"
                f"    {r.snippet[:300]}\n"
                f"    (engine: {r.source_engine}, score: {r.score:.2f})"
            )
        return "\n\n".join(lines)
