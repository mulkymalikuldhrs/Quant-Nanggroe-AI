"""NVIDIA NIM API Client — Async HTTP client for NIM inference microservices.

Provides a production-grade async client for the NVIDIA NIM API, supporting
chat completions, embeddings, reranking, streaming, health checks, and
model listing.  Implements exponential-backoff retries, rate limiting,
token counting, and cost estimation.

Usage::

    from quant_nanggroe.engine.nvidia_nim import NIMClient

    client = NIMClient()
    response = await client.chat("Analyze AAPL market conditions")
    print(response.content)
    await client.close()
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx
import structlog

from quant_nanggroe.engine.nvidia_nim.config import NIMConfig, get_nim_config
from quant_nanggroe.engine.nvidia_nim.models import (
    NIMChatMessage,
    NIMChatRequest,
    NIMChatResponse,
    NIMChoice,
    NIMEmbeddingRequest,
    NIMEmbeddingResponse,
    NIMEmbeddingData,
    NIMFinishReason,
    NIMModelInfo,
    NIMModelList,
    NIMModelStatus,
    NIMRerankRequest,
    NIMRerankResponse,
    NIMRole,
    NIMStreamChunk,
    NIMStreamChoice,
    NIMStreamDelta,
    NIMUsage,
)
from quant_nanggroe.engine.observability import get_observability, traced

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Approximate cost table (USD per 1K tokens) — NVIDIA NIM pricing as of 2025
# ---------------------------------------------------------------------------

_NIM_COST_TABLE: Dict[str, Dict[str, float]] = {
    "meta/llama-3.1-405b-instruct": {"input": 0.008, "output": 0.024},
    "meta/llama-3.1-70b-instruct": {"input": 0.003, "output": 0.008},
    "mistralai/mixtral-8x22b-instruct": {"input": 0.004, "output": 0.012},
    "nvidia/nemotron-4-340b-reward": {"input": 0.006, "output": 0.018},
    "google/gemma-2-27b-it": {"input": 0.002, "output": 0.005},
    "microsoft/phi-3-medium-128k-instruct": {"input": 0.001, "output": 0.003},
    # Default for unknown models
    "__default__": {"input": 0.003, "output": 0.008},
}


class NIMRateLimitError(Exception):
    """Raised when the NIM rate limit is exceeded."""


class NIMAPIError(Exception):
    """Raised when the NIM API returns an error response."""

    def __init__(self, status_code: int, message: str, model: str = "") -> None:
        self.status_code = status_code
        self.model = model
        super().__init__(f"NIM API error {status_code}: {message} (model={model})")


class NIMClient:
    """Async HTTP client for NVIDIA NIM inference microservices.

    Supports chat completions (standard and streaming), embeddings,
    reranking, health checks, and model listing.  Includes automatic
    retry with exponential backoff and per-minute rate limiting.

    Args:
        config: Optional NIMConfig instance.  If not provided, the
            global config from ``get_nim_config()`` is used.

    Raises:
        ValueError: If the API key is not configured.
    """

    def __init__(self, config: Optional[NIMConfig] = None) -> None:
        self._config = config or get_nim_config()
        self._base_url = self._config.nvidia_nim_base_url.rstrip("/")
        self._api_key = self._config.nvidia_nim_api_key
        self._timeout = self._config.nvidia_nim_timeout
        self._max_retries = self._config.nvidia_nim_max_retries
        self._rate_limit = self._config.nvidia_nim_rate_limit

        # Rate-limit tracking: timestamps of recent requests within the window
        self._request_timestamps: deque[float] = deque()

        # httpx client (lazy-initialised)
        self._client: httpx.AsyncClient | None = None

        # Model cache
        self._models_cache: Optional[NIMModelList] = None
        self._models_cache_time: float = 0.0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Create the httpx client if not already alive."""
        if self._client is None or self._client.is_closed:
            headers: Dict[str, str] = {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            if self._api_key:
                headers["Authorization"] = f"Bearer {self._api_key}"

            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers=headers,
                timeout=httpx.Timeout(
                    connect=10.0,
                    read=float(self._timeout),
                    write=10.0,
                    pool=10.0,
                ),
            )
        return self._client

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
            logger.debug("nim_client_closed")

    async def __aenter__(self) -> NIMClient:
        await self._ensure_client()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------

    def _check_rate_limit(self) -> None:
        """Enforce per-minute rate limit; raise if exceeded."""
        now = time.monotonic()
        window = 60.0  # 1-minute sliding window

        # Prune timestamps outside the window
        while self._request_timestamps and self._request_timestamps[0] < now - window:
            self._request_timestamps.popleft()

        if len(self._request_timestamps) >= self._rate_limit:
            raise NIMRateLimitError(
                f"Rate limit exceeded: {self._rate_limit} requests/minute. "
                f"Retry after {window - (now - self._request_timestamps[0]):.1f}s."
            )

    def _record_request(self) -> None:
        """Record a request timestamp for rate-limit tracking."""
        self._request_timestamps.append(time.monotonic())

    # ------------------------------------------------------------------
    # Retry logic
    # ------------------------------------------------------------------

    async def _request_with_retry(
        self,
        method: str,
        path: str,
        json_payload: Optional[Dict[str, Any]] = None,
        *,
        model: str = "",
    ) -> httpx.Response:
        """Send an HTTP request with exponential-backoff retries.

        Retries on transient errors (429, 500, 502, 503, 504) up to
        ``nvidia_nim_max_retries`` attempts.

        Args:
            method: HTTP method (GET, POST, etc.).
            path: URL path relative to ``base_url``.
            json_payload: Optional JSON body.
            model: Model name (for error context).

        Returns:
            The httpx Response.

        Raises:
            NIMAPIError: On non-retryable HTTP errors.
            NIMRateLimitError: If rate limit exceeded even after retries.
        """
        client = await self._ensure_client()
        retryable_statuses = {429, 500, 502, 503, 504}
        last_exc: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                self._check_rate_limit()
                self._record_request()

                response = await client.request(
                    method,
                    path,
                    json=json_payload,
                )

                if response.status_code in retryable_statuses and attempt < self._max_retries:
                    delay = min(
                        self._config.nvidia_nim_retry_base_delay * (2 ** (attempt - 1)),
                        self._config.nvidia_nim_retry_max_delay,
                    )
                    logger.warning(
                        "nim_retry",
                        attempt=attempt,
                        status=response.status_code,
                        delay_s=delay,
                        model=model,
                    )
                    await asyncio.sleep(delay)
                    continue

                if response.status_code >= 400:
                    body = response.text[:500]
                    raise NIMAPIError(
                        status_code=response.status_code,
                        message=body,
                        model=model,
                    )

                return response

            except NIMAPIError:
                raise
            except NIMRateLimitError:
                if attempt < self._max_retries:
                    delay = min(
                        self._config.nvidia_nim_retry_base_delay * (2 ** (attempt - 1)),
                        self._config.nvidia_nim_retry_max_delay,
                    )
                    logger.warning("nim_rate_limited_retry", attempt=attempt, delay_s=delay)
                    await asyncio.sleep(delay)
                    continue
                raise
            except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    delay = min(
                        self._config.nvidia_nim_retry_base_delay * (2 ** (attempt - 1)),
                        self._config.nvidia_nim_retry_max_delay,
                    )
                    logger.warning(
                        "nim_request_error_retry",
                        attempt=attempt,
                        error=str(exc),
                        delay_s=delay,
                    )
                    await asyncio.sleep(delay)
                    continue

        raise RuntimeError(
            f"NIM request failed after {self._max_retries} retries: {last_exc}"
        )

    # ------------------------------------------------------------------
    # Cost estimation
    # ------------------------------------------------------------------

    @staticmethod
    def estimate_cost(
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Estimate the USD cost for a NIM API call.

        Uses the built-in cost table.  Unknown models fall back to
        the ``__default__`` rate.

        Args:
            model: NIM model identifier.
            input_tokens: Number of input tokens consumed.
            output_tokens: Number of output tokens generated.

        Returns:
            Estimated cost in USD.
        """
        rates = _NIM_COST_TABLE.get(model, _NIM_COST_TABLE["__default__"])
        input_cost = (input_tokens / 1000.0) * rates["input"]
        output_cost = (output_tokens / 1000.0) * rates["output"]
        return round(input_cost + output_cost, 8)

    @staticmethod
    def estimate_token_count(text: str) -> int:
        """Estimate token count for a text string.

        Uses a simple heuristic of ~4 characters per token, which is
        a reasonable approximation for English text with the BPE
        tokenisers used by most NIM models.

        Args:
            text: Input text.

        Returns:
            Estimated token count.
        """
        return max(1, len(text) // 4)

    # ------------------------------------------------------------------
    # Chat completions
    # ------------------------------------------------------------------

    @traced("nim_chat", attributes={"component": "nvidia_nim", "operation": "chat"})
    async def chat(
        self,
        prompt: str,
        *,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: float = 1.0,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
        seed: Optional[int] = None,
    ) -> NIMChatResponse:
        """Send a chat completion request to NVIDIA NIM.

        Args:
            prompt: User message text.
            system_prompt: Optional system message.
            model: NIM model identifier (defaults to config default).
            temperature: Sampling temperature (defaults to config default).
            top_p: Nucleus sampling threshold.
            max_tokens: Maximum output tokens.
            stop: Stop sequences.
            seed: Random seed for reproducibility.

        Returns:
            NIMChatResponse with the generated content and usage data.

        Raises:
            NIMAPIError: On API errors.
            NIMRateLimitError: If rate limit exceeded.
        """
        model = model or self._config.nvidia_nim_default_model
        temperature = temperature if temperature is not None else self._config.nvidia_nim_temperature
        max_tokens = max_tokens or self._config.nvidia_nim_max_tokens

        messages: list[NIMChatMessage] = []
        if system_prompt:
            messages.append(NIMChatMessage(role=NIMRole.SYSTEM, content=system_prompt))
        messages.append(NIMChatMessage(role=NIMRole.USER, content=prompt))

        request = NIMChatRequest(
            model=model,
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            stream=False,
            stop=stop,
            seed=seed,
        )

        obs = get_observability()
        start = time.monotonic()
        response = await self._request_with_retry(
            "POST",
            "/chat/completions",
            json_payload=request.model_dump(exclude_none=True),
            model=model,
        )
        latency_ms = (time.monotonic() - start) * 1000.0

        data = response.json()
        nim_response = self._parse_chat_response(data, latency_ms)

        # Record observability metrics
        obs.metrics.api_request_duration_seconds.record(
            latency_ms / 1000.0,
            {"provider": "nvidia_nim", "model": model, "operation": "chat"},
        )
        obs.metrics.llm_tokens_total.add(
            nim_response.usage.prompt_tokens,
            {"model": model, "token_type": "input"},
        )
        obs.metrics.llm_tokens_total.add(
            nim_response.usage.completion_tokens,
            {"model": model, "token_type": "output"},
        )

        logger.info(
            "nim_chat_complete",
            model=model,
            latency_ms=round(latency_ms, 1),
            input_tokens=nim_response.usage.prompt_tokens,
            output_tokens=nim_response.usage.completion_tokens,
            cost_usd=nim_response.usage.cost_usd,
        )

        return nim_response

    async def chat_with_messages(
        self,
        messages: List[NIMChatMessage],
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: float = 1.0,
        max_tokens: Optional[int] = None,
    ) -> NIMChatResponse:
        """Send a multi-turn chat completion request.

        Args:
            messages: Full conversation history.
            model: NIM model identifier.
            temperature: Sampling temperature.
            top_p: Nucleus sampling threshold.
            max_tokens: Maximum output tokens.

        Returns:
            NIMChatResponse with the generated content.
        """
        model = model or self._config.nvidia_nim_default_model
        temperature = temperature if temperature is not None else self._config.nvidia_nim_temperature
        max_tokens = max_tokens or self._config.nvidia_nim_max_tokens

        request = NIMChatRequest(
            model=model,
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            stream=False,
        )

        start = time.monotonic()
        response = await self._request_with_retry(
            "POST",
            "/chat/completions",
            json_payload=request.model_dump(exclude_none=True),
            model=model,
        )
        latency_ms = (time.monotonic() - start) * 1000.0
        data = response.json()
        return self._parse_chat_response(data, latency_ms)

    # ------------------------------------------------------------------
    # Streaming
    # ------------------------------------------------------------------

    async def chat_stream(
        self,
        prompt: str,
        *,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: float = 1.0,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[NIMStreamChunk]:
        """Stream chat completion tokens from NVIDIA NIM.

        Yields NIMStreamChunk objects as they arrive from the API.

        Args:
            prompt: User message text.
            system_prompt: Optional system message.
            model: NIM model identifier.
            temperature: Sampling temperature.
            top_p: Nucleus sampling threshold.
            max_tokens: Maximum output tokens.

        Yields:
            NIMStreamChunk for each streamed token/fragment.
        """
        model = model or self._config.nvidia_nim_default_model
        temperature = temperature if temperature is not None else self._config.nvidia_nim_temperature
        max_tokens = max_tokens or self._config.nvidia_nim_max_tokens

        messages: list[NIMChatMessage] = []
        if system_prompt:
            messages.append(NIMChatMessage(role=NIMRole.SYSTEM, content=system_prompt))
        messages.append(NIMChatMessage(role=NIMRole.USER, content=prompt))

        request = NIMChatRequest(
            model=model,
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            stream=True,
        )

        client = await self._ensure_client()
        self._check_rate_limit()
        self._record_request()

        logger.debug("nim_stream_start", model=model)

        async with client.stream(
            "POST",
            "/chat/completions",
            json=request.model_dump(exclude_none=True),
        ) as stream:
            async for line in stream.aiter_lines():
                line = line.strip()
                if not line or not line.startswith("data: "):
                    continue
                payload = line[6:]  # strip "data: " prefix
                if payload == "[DONE]":
                    break
                try:
                    import json
                    chunk_data = json.loads(payload)
                    chunk = self._parse_stream_chunk(chunk_data)
                    if chunk is not None:
                        yield chunk
                except Exception:
                    logger.warning("nim_stream_parse_error", line=line[:100])

    # ------------------------------------------------------------------
    # Embeddings
    # ------------------------------------------------------------------

    async def embed(
        self,
        texts: List[str],
        *,
        model: Optional[str] = None,
        input_type: str = "query",
    ) -> NIMEmbeddingResponse:
        """Generate embeddings for a list of texts.

        Args:
            texts: Text strings to embed.
            model: Embedding model identifier.
            input_type: Either 'query' or 'passage'.

        Returns:
            NIMEmbeddingResponse with embedding vectors.
        """
        model = model or self._config.nvidia_nim_embedding_model

        request = NIMEmbeddingRequest(
            model=model,
            input=texts,
            input_type=input_type,
        )

        start = time.monotonic()
        response = await self._request_with_retry(
            "POST",
            "/embeddings",
            json_payload=request.model_dump(exclude_none=True),
            model=model,
        )
        latency_ms = (time.monotonic() - start) * 1000.0

        data = response.json()
        nim_response = self._parse_embedding_response(data, latency_ms)

        logger.info(
            "nim_embed_complete",
            model=model,
            count=len(texts),
            latency_ms=round(latency_ms, 1),
        )

        return nim_response

    # ------------------------------------------------------------------
    # Reranking
    # ------------------------------------------------------------------

    async def rerank(
        self,
        query: str,
        documents: List[str],
        *,
        top_n: Optional[int] = None,
        model: Optional[str] = None,
    ) -> NIMRerankResponse:
        """Rerank documents by relevance to a query.

        Args:
            query: Query text.
            documents: Documents to rank.
            top_n: Number of top results to return.
            model: Reranking model identifier.

        Returns:
            NIMRerankResponse with ranked results.
        """
        model = model or self._config.nvidia_nim_rerank_model
        top_n = top_n or len(documents)

        request = NIMRerankRequest(
            model=model,
            query=query,
            documents=documents,
            top_n=top_n,
        )

        start = time.monotonic()
        response = await self._request_with_retry(
            "POST",
            "/rankings",
            json_payload=request.model_dump(exclude_none=True),
            model=model,
        )
        latency_ms = (time.monotonic() - start) * 1000.0

        data = response.json()
        nim_response = self._parse_rerank_response(data, latency_ms)

        logger.info(
            "nim_rerank_complete",
            model=model,
            num_documents=len(documents),
            latency_ms=round(latency_ms, 1),
        )

        return nim_response

    # ------------------------------------------------------------------
    # Health check & model listing
    # ------------------------------------------------------------------

    async def health_check(self) -> Dict[str, Any]:
        """Check NIM API health.

        Returns:
            Dict with 'healthy' (bool), 'latency_ms' (float), and
            optional 'error' (str) if unhealthy.
        """
        start = time.monotonic()
        try:
            client = await self._ensure_client()
            self._check_rate_limit()
            self._record_request()
            response = await client.get("/models")
            latency_ms = (time.monotonic() - start) * 1000.0

            if response.status_code == 200:
                return {
                    "healthy": True,
                    "latency_ms": round(latency_ms, 1),
                    "status_code": response.status_code,
                }
            return {
                "healthy": False,
                "latency_ms": round(latency_ms, 1),
                "status_code": response.status_code,
                "error": response.text[:200],
            }
        except Exception as exc:
            latency_ms = (time.monotonic() - start) * 1000.0
            return {
                "healthy": False,
                "latency_ms": round(latency_ms, 1),
                "error": str(exc),
            }

    async def list_models(self, *, force_refresh: bool = False) -> NIMModelList:
        """List available NIM models.

        Results are cached for 5 minutes unless ``force_refresh`` is True.

        Args:
            force_refresh: Bypass cache and fetch from API.

        Returns:
            NIMModelList with available model metadata.
        """
        cache_ttl = 300.0  # 5 minutes
        now = time.monotonic()

        if (
            not force_refresh
            and self._models_cache is not None
            and (now - self._models_cache_time) < cache_ttl
        ):
            return self._models_cache

        response = await self._request_with_retry("GET", "/models")
        data = response.json()

        models: list[NIMModelInfo] = []
        for raw in data.get("data", []):
            model_info = NIMModelInfo(
                id=raw.get("id", ""),
                owned_by=raw.get("owned_by", ""),
                object=raw.get("object", "model"),
                created=raw.get("created", 0),
                context_length=raw.get("context_length"),
                input_modalities=raw.get("input_modalities", ["text"]),
                output_modalities=raw.get("output_modalities", ["text"]),
                status=NIMModelStatus.AVAILABLE,
                cost_per_1k_input=_NIM_COST_TABLE.get(
                    raw.get("id", ""), _NIM_COST_TABLE["__default__"]
                )["input"],
                cost_per_1k_output=_NIM_COST_TABLE.get(
                    raw.get("id", ""), _NIM_COST_TABLE["__default__"]
                )["output"],
            )
            models.append(model_info)

        self._models_cache = NIMModelList(data=models)
        self._models_cache_time = now

        logger.info("nim_models_listed", count=len(models))
        return self._models_cache

    # ------------------------------------------------------------------
    # Internal: response parsers
    # ------------------------------------------------------------------

    def _parse_chat_response(
        self, data: Dict[str, Any], latency_ms: float
    ) -> NIMChatResponse:
        """Parse a chat completion JSON response into NIMChatResponse."""
        usage_data = data.get("usage", {})
        prompt_tokens = usage_data.get("prompt_tokens", 0)
        completion_tokens = usage_data.get("completion_tokens", 0)
        total_tokens = usage_data.get("total_tokens", prompt_tokens + completion_tokens)
        model_name = data.get("model", "")

        cost_usd = self.estimate_cost(model_name, prompt_tokens, completion_tokens)

        usage = NIMUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
        )

        choices: list[NIMChoice] = []
        for raw_choice in data.get("choices", []):
            msg_data = raw_choice.get("message", {})
            finish_raw = raw_choice.get("finish_reason", "stop")
            try:
                finish_reason = NIMFinishReason(finish_raw)
            except ValueError:
                finish_reason = NIMFinishReason.STOP

            choice = NIMChoice(
                index=raw_choice.get("index", 0),
                message=NIMChatMessage(
                    role=NIMRole(msg_data.get("role", "assistant")),
                    content=msg_data.get("content", ""),
                ),
                finish_reason=finish_reason,
            )
            choices.append(choice)

        return NIMChatResponse(
            id=data.get("id", ""),
            object=data.get("object", "chat.completion"),
            created=data.get("created", int(datetime.now(tz=timezone.utc).timestamp())),
            model=model_name,
            choices=choices,
            usage=usage,
        )

    @staticmethod
    def _parse_stream_chunk(data: Dict[str, Any]) -> Optional[NIMStreamChunk]:
        """Parse a single SSE stream chunk into NIMStreamChunk."""
        choices: list[NIMStreamChoice] = []
        for raw in data.get("choices", []):
            delta_data = raw.get("delta", {})
            finish_raw = raw.get("finish_reason")
            finish_reason = None
            if finish_raw:
                try:
                    finish_reason = NIMFinishReason(finish_raw)
                except ValueError:
                    finish_reason = None

            role = None
            if delta_data.get("role"):
                try:
                    role = NIMRole(delta_data["role"])
                except ValueError:
                    role = None

            choices.append(NIMStreamChoice(
                index=raw.get("index", 0),
                delta=NIMStreamDelta(
                    role=role,
                    content=delta_data.get("content"),
                ),
                finish_reason=finish_reason,
            ))

        return NIMStreamChunk(
            id=data.get("id", ""),
            model=data.get("model", ""),
            created=data.get("created", 0),
            choices=choices,
        )

    def _parse_embedding_response(
        self, data: Dict[str, Any], latency_ms: float
    ) -> NIMEmbeddingResponse:
        """Parse an embedding JSON response."""
        usage_data = data.get("usage", {})
        prompt_tokens = usage_data.get("prompt_tokens", 0)
        total_tokens = usage_data.get("total_tokens", prompt_tokens)
        model_name = data.get("model", "")

        cost_usd = self.estimate_cost(model_name, prompt_tokens, 0)

        embedding_data: list[NIMEmbeddingData] = []
        for raw in data.get("data", []):
            embedding_data.append(NIMEmbeddingData(
                index=raw.get("index", 0),
                embedding=raw.get("embedding", []),
                object=raw.get("object", "embedding"),
            ))

        return NIMEmbeddingResponse(
            id=data.get("id", ""),
            model=model_name,
            data=embedding_data,
            usage=NIMUsage(
                prompt_tokens=prompt_tokens,
                total_tokens=total_tokens,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
            ),
        )

    @staticmethod
    def _parse_rerank_response(
        data: Dict[str, Any], latency_ms: float
    ) -> NIMRerankResponse:
        """Parse a reranking JSON response."""
        from quant_nanggroe.engine.nvidia_nim.models import NIMRerankResult

        results: list[NIMRerankResult] = []
        for raw in data.get("rankings", data.get("results", [])):
            results.append(NIMRerankResult(
                index=raw.get("index", 0),
                relevance_score=raw.get("relevance_score", raw.get("logit", 0.0)),
                document=raw.get("document"),
            ))

        usage_data = data.get("usage", {})
        return NIMRerankResponse(
            id=data.get("id", ""),
            model=data.get("model", ""),
            results=results,
            usage=NIMUsage(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
                latency_ms=latency_ms,
            ),
        )


__all__ = [
    "NIMClient",
    "NIMAPIError",
    "NIMRateLimitError",
]
