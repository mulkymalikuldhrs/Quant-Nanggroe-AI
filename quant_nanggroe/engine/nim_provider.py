"""NVIDIA NIM Provider — Full Integration with Circuit Breaker and Fallback.

Implements a production-grade NVIDIA NIM provider supporting free-tier
models via the OpenAI-compatible API.  Features include:

* Model selection by task type (reasoning, analysis, quick, vision)
* Circuit breaker: 3 failures → 5 min cooldown
* Cost tracking per model
* Fallback chain: NIM → local Ollama → raise (REAL-ONLY, no mock)
* Async throughout using aiohttp
* Token usage tracking

Supported Free Models
---------------------
* deepseek-ai/deepseek-r1 (reasoning)
* meta/llama-3.3-70b-instruct (general)
* nvidia/llama-3.1-nemotron-70b-instruct (analysis)
* mistralai/mixtral-8x22b-instruct-v0.1 (quick)
* google/gemma-3-27b-it (multimodal)

Usage::

    from quant_nanggroe.engine.nim_provider import NIMProvider

    provider = NIMProvider(api_key="nvapi-...")
    response = await provider.chat("Analyze AAPL", task="analysis")
    print(response.content)

    # With fallback:
    response = await provider.chat("Quick analysis", task="quick")
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

# ── Optional aiohttp import ─────────────────────────────────────────────

try:
    import aiohttp

    _AIOHTTP_AVAILABLE = True
except ImportError:
    _AIOHTTP_AVAILABLE = False
    aiohttp = None  # type: ignore[assignment]


# ── Enums ───────────────────────────────────────────────────────────────


class TaskType(str, Enum):
    """Task type for model selection."""

    REASONING = "reasoning"
    ANALYSIS = "analysis"
    QUICK = "quick"
    VISION = "vision"
    GENERAL = "general"


class ProviderState(str, Enum):
    """NIM provider state."""

    AVAILABLE = "AVAILABLE"
    CIRCUIT_OPEN = "CIRCUIT_OPEN"
    COOLDOWN = "COOLDOWN"
    UNAVAILABLE = "UNAVAILABLE"
    MOCK = "MOCK"


# ── Model Configuration ─────────────────────────────────────────────────

# Free NVIDIA NIM models with their task specializations
NIM_MODELS: Dict[str, Dict[str, Any]] = {
    "deepseek-ai/deepseek-r1": {
        "task": TaskType.REASONING,
        "description": "Deep reasoning model",
        "max_tokens": 8192,
        "context_length": 65536,
    },
    "meta/llama-3.3-70b-instruct": {
        "task": TaskType.GENERAL,
        "description": "General purpose instruction following",
        "max_tokens": 4096,
        "context_length": 131072,
    },
    "nvidia/llama-3.1-nemotron-70b-instruct": {
        "task": TaskType.ANALYSIS,
        "description": "Analysis and structured reasoning",
        "max_tokens": 4096,
        "context_length": 131072,
    },
    "mistralai/mixtral-8x22b-instruct-v0.1": {
        "task": TaskType.QUICK,
        "description": "Fast inference for quick tasks",
        "max_tokens": 4096,
        "context_length": 65536,
    },
    "google/gemma-3-27b-it": {
        "task": TaskType.VISION,
        "description": "Multimodal (text + image)",
        "max_tokens": 4096,
        "context_length": 131072,
    },
}

# Task → model mapping (primary + fallbacks)
TASK_MODEL_MAP: Dict[TaskType, List[str]] = {
    TaskType.REASONING: [
        "deepseek-ai/deepseek-r1",
        "nvidia/llama-3.1-nemotron-70b-instruct",
        "meta/llama-3.3-70b-instruct",
    ],
    TaskType.ANALYSIS: [
        "nvidia/llama-3.1-nemotron-70b-instruct",
        "meta/llama-3.3-70b-instruct",
        "mistralai/mixtral-8x22b-instruct-v0.1",
    ],
    TaskType.QUICK: [
        "mistralai/mixtral-8x22b-instruct-v0.1",
        "meta/llama-3.3-70b-instruct",
    ],
    TaskType.VISION: [
        "google/gemma-3-27b-it",
        "meta/llama-3.3-70b-instruct",
    ],
    TaskType.GENERAL: [
        "meta/llama-3.3-70b-instruct",
        "mistralai/mixtral-8x22b-instruct-v0.1",
    ],
}


# ── Pydantic Models ─────────────────────────────────────────────────────


class NIMResponse(BaseModel):
    """Response from NIM provider.

    Attributes:
        content: Generated text content.
        model: Model used for generation.
        task_type: Task type that triggered the call.
        usage: Token usage dict.
        latency_ms: Request latency in milliseconds.
        cost_usd: Estimated cost in USD.
        source: Source of the response (nim/ollama/mock).
        is_mock: Whether this is a mock response.
    """

    model_config = ConfigDict(frozen=False)

    content: str = ""
    model: str = ""
    task_type: TaskType = TaskType.GENERAL
    usage: Dict[str, int] = Field(default_factory=lambda: {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    })
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    source: str = "mock"
    is_mock: bool = True

    def to_api_dict(self) -> Dict[str, Any]:
        """Convert to API-safe dictionary."""
        return {
            "content": self.content,
            "model": self.model,
            "task_type": self.task_type.value,
            "usage": self.usage,
            "latency_ms": round(self.latency_ms, 2),
            "cost_usd": round(self.cost_usd, 6),
            "source": self.source,
            "is_mock": self.is_mock,
        }


class ModelUsage(BaseModel):
    """Token usage tracking for a single model."""

    model_config = ConfigDict(frozen=False)

    model: str = ""
    total_requests: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_cost_usd: float = 0.0
    total_latency_ms: float = 0.0
    failures: int = 0


# ── Circuit Breaker ─────────────────────────────────────────────────────


@dataclass
class CircuitBreaker:
    """Circuit breaker for NIM API calls.

    Opens after ``failure_threshold`` consecutive failures,
    then enters cooldown for ``cooldown_seconds`` before
    allowing retry.

    Attributes:
        failure_threshold: Consecutive failures before opening.
        cooldown_seconds: Seconds to wait before retry.
        consecutive_failures: Current consecutive failure count.
        state: Current circuit state.
        last_failure_at: Timestamp of last failure.
    """

    failure_threshold: int = 3
    cooldown_seconds: float = 300.0  # 5 minutes
    consecutive_failures: int = 0
    state: ProviderState = ProviderState.AVAILABLE
    last_failure_at: float = 0.0

    def record_success(self) -> None:
        """Record a successful call — resets failure count."""
        self.consecutive_failures = 0
        self.state = ProviderState.AVAILABLE

    def record_failure(self) -> None:
        """Record a failed call — increments failure count."""
        self.consecutive_failures += 1
        self.last_failure_at = time.time()

        if self.consecutive_failures >= self.failure_threshold:
            self.state = ProviderState.CIRCUIT_OPEN
            logger.warning(
                "circuit_breaker_opened",
                extra={
                    "failures": self.consecutive_failures,
                    "cooldown": self.cooldown_seconds,
                },
            )

    @property
    def is_available(self) -> bool:
        """Check if the circuit allows requests."""
        if self.state == ProviderState.AVAILABLE:
            return True

        if self.state == ProviderState.CIRCUIT_OPEN:
            # Check if cooldown has elapsed
            elapsed = time.time() - self.last_failure_at
            if elapsed >= self.cooldown_seconds:
                self.state = ProviderState.COOLDOWN
                logger.info("circuit_breaker_half_open_retry_allowed")
                return True
            return False

        if self.state == ProviderState.COOLDOWN:
            return True

        return False


# ── NIM Provider ────────────────────────────────────────────────────────


class NIMProvider:
    """NVIDIA NIM provider with circuit breaker and fallback chain.

    Provides async access to NVIDIA NIM free-tier models with:
    * Model selection by task type
    * Circuit breaker pattern for resilience
    * Cost tracking per model
    * Fallback chain: NIM → Ollama → Mock

    Args:
        api_key: NVIDIA NIM API key (or set QNAI_NVIDIA_NIM_API_KEY env var).
        base_url: NIM API base URL.
        default_model: Default model when no task specified.
        timeout: Request timeout in seconds.
        max_retries: Maximum retry attempts.
        ollama_url: Local Ollama URL for fallback.

    Usage::

        provider = NIMProvider(api_key="nvapi-...")
        response = await provider.chat(
            "Analyze AAPL market conditions",
            task="analysis"
        )
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://integrate.api.nvidia.com/v1",
        default_model: str = "meta/llama-3.3-70b-instruct",
        timeout: int = 60,
        max_retries: int = 3,
        ollama_url: str = "http://localhost:11434",
    ) -> None:
        self.api_key = api_key or os.environ.get("QNAI_NVIDIA_NIM_API_KEY", "")
        self.base_url = base_url
        self.default_model = default_model
        self.timeout = timeout
        self.max_retries = max_retries
        self.ollama_url = ollama_url

        # Circuit breaker
        self._circuit = CircuitBreaker()

        # Usage tracking
        self._usage: Dict[str, ModelUsage] = defaultdict(
            lambda: ModelUsage(model="")
        )

        # Session management
        self._session: Optional[Any] = None

    # ── Core Chat Method ─────────────────────────────────────────────

    async def chat(
        self,
        prompt: str,
        system: Optional[str] = None,
        task: str = "general",
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> NIMResponse:
        """Send a chat completion request via the NIM API.

        Follows the fallback chain: NIM → Ollama → Mock.

        Args:
            prompt: User message content.
            system: Optional system message.
            task: Task type for model selection ("reasoning", "analysis",
                "quick", "vision", "general").
            model: Override model selection.
            temperature: Sampling temperature.
            max_tokens: Maximum output tokens.

        Returns:
            NIMResponse with generated content.
        """
        task_type = TaskType(task)

        # Build messages
        messages: List[Dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        # Select model
        selected_model = model or self._select_model(task_type)

        # Try NIM API first
        if self._circuit.is_available and self.api_key:
            response = await self._call_nim(
                messages=messages,
                model=selected_model,
                temperature=temperature,
                max_tokens=max_tokens,
                task_type=task_type,
            )
            if response is not None:
                return response

        # Try Ollama fallback
        ollama_response = await self._call_ollama(
            messages=messages,
            model=selected_model,
            temperature=temperature,
            task_type=task_type,
        )
        if ollama_response is not None:
            return ollama_response

        # All providers failed — raise, do not mock
        raise RuntimeError(
            f"NIM provider: all backends failed for model={selected_model} "
            f"task={task_type}. Set NVIDIA_API_KEY or start local Ollama."
        )

    # ── NIM API Call ─────────────────────────────────────────────────

    async def _call_nim(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        task_type: TaskType,
    ) -> Optional[NIMResponse]:
        """Call the NVIDIA NIM API.

        Args:
            messages: Chat messages.
            model: Model identifier.
            temperature: Sampling temperature.
            max_tokens: Maximum output tokens.
            task_type: Task type for the request.

        Returns:
            NIMResponse or None if call fails.
        """
        if not _AIOHTTP_AVAILABLE:
            logger.warning("aiohttp_not_available")
            return None

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        for attempt in range(self.max_retries):
            try:
                start_time = time.time()

                session = await self._get_session()
                async with session.post(
                    url, json=payload, headers=headers
                ) as resp:
                    latency_ms = (time.time() - start_time) * 1000

                    if resp.status == 200:
                        data = await resp.json()

                        content = ""
                        if data.get("choices"):
                            content = data["choices"][0].get("message", {}).get("content", "")

                        usage = data.get("usage", {})
                        prompt_tokens = usage.get("prompt_tokens", 0)
                        completion_tokens = usage.get("completion_tokens", 0)
                        total_tokens = usage.get("total_tokens", 0)

                        # Track usage
                        self._track_usage(
                            model=model,
                            prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens,
                            latency_ms=latency_ms,
                        )

                        self._circuit.record_success()

                        return NIMResponse(
                            content=content,
                            model=model,
                            task_type=task_type,
                            usage={
                                "prompt_tokens": prompt_tokens,
                                "completion_tokens": completion_tokens,
                                "total_tokens": total_tokens,
                            },
                            latency_ms=round(latency_ms, 2),
                            cost_usd=0.0,  # Free tier
                            source="nim",
                            is_mock=False,
                        )

                    elif resp.status == 429:
                        # Rate limited
                        retry_after = float(resp.headers.get("Retry-After", "5"))
                        logger.warning(
                            "nim_rate_limited",
                            extra={"retry_after": retry_after, "attempt": attempt},
                        )
                        await asyncio.sleep(retry_after)
                        continue

                    else:
                        error_text = await resp.text()
                        logger.warning(
                            "nim_api_error",
                            extra={
                                "status": resp.status,
                                "error": error_text[:200],
                                "attempt": attempt,
                            },
                        )
                        self._circuit.record_failure()

                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(2 ** attempt)
                            continue

            except asyncio.TimeoutError:
                logger.warning("nim_timeout", extra={"attempt": attempt})
                self._circuit.record_failure()

            except Exception as exc:
                logger.warning(
                    "nim_call_failed",
                    extra={"error": str(exc), "attempt": attempt},
                )
                self._circuit.record_failure()

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue

        return None

    # ── Ollama Fallback ──────────────────────────────────────────────

    async def _call_ollama(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        task_type: TaskType,
    ) -> Optional[NIMResponse]:
        """Try local Ollama as fallback.

        Args:
            messages: Chat messages.
            model: Model identifier (mapped to Ollama model).
            temperature: Sampling temperature.
            task_type: Task type.

        Returns:
            NIMResponse or None if Ollama unavailable.
        """
        if not _AIOHTTP_AVAILABLE:
            return None

        # Map NIM model names to Ollama equivalents
        ollama_model = self._map_to_ollama_model(model)
        url = f"{self.ollama_url}/api/chat"

        payload = {
            "model": ollama_model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }

        try:
            start_time = time.time()
            session = await self._get_session()
            async with session.post(
                url, json=payload, timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as resp:
                latency_ms = (time.time() - start_time) * 1000

                if resp.status == 200:
                    data = await resp.json()
                    content = data.get("message", {}).get("content", "")

                    self._track_usage(
                        model=f"ollama/{ollama_model}",
                        prompt_tokens=0,
                        completion_tokens=0,
                        latency_ms=latency_ms,
                    )

                    return NIMResponse(
                        content=content,
                        model=f"ollama/{ollama_model}",
                        task_type=task_type,
                        usage={
                            "prompt_tokens": 0,
                            "completion_tokens": 0,
                            "total_tokens": 0,
                        },
                        latency_ms=round(latency_ms, 2),
                        cost_usd=0.0,
                        source="ollama",
                        is_mock=False,
                    )

        except Exception as exc:
            logger.debug(
                "ollama_fallback_failed",
                extra={"error": str(exc)},
            )

        return None

    # ── Model Selection ──────────────────────────────────────────────

    def _select_model(self, task_type: TaskType) -> str:
        """Select the best model for a given task type.

        Args:
            task_type: Task type for model selection.

        Returns:
            Model identifier string.
        """
        models = TASK_MODEL_MAP.get(task_type, [self.default_model])
        return models[0] if models else self.default_model

    @staticmethod
    def _map_to_ollama_model(nim_model: str) -> str:
        """Map a NIM model name to an Ollama equivalent.

        Args:
            nim_model: NIM model identifier.

        Returns:
            Ollama model name.
        """
        mapping = {
            "deepseek-ai/deepseek-r1": "deepseek-r1:latest",
            "meta/llama-3.3-70b-instruct": "llama3.3:70b",
            "nvidia/llama-3.1-nemotron-70b-instruct": "llama3.1:70b",
            "mistralai/mixtral-8x22b-instruct-v0.1": "mixtral:8x22b",
            "google/gemma-3-27b-it": "gemma3:27b",
        }
        return mapping.get(nim_model, "llama3.3:70b")

    # ── Session Management ───────────────────────────────────────────

    async def _get_session(self) -> Any:
        """Get or create the aiohttp session."""
        if self._session is None or self._session.closed:
            if _AIOHTTP_AVAILABLE and aiohttp is not None:
                self._session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                )
        return self._session

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    # ── Usage Tracking ───────────────────────────────────────────────

    def _track_usage(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
    ) -> None:
        """Track token usage for a model.

        Args:
            model: Model identifier.
            prompt_tokens: Input token count.
            completion_tokens: Output token count.
            latency_ms: Request latency.
        """
        if model not in self._usage or self._usage[model].model == "":
            self._usage[model] = ModelUsage(model=model)

        usage = self._usage[model]
        usage.total_requests += 1
        usage.total_prompt_tokens += prompt_tokens
        usage.total_completion_tokens += completion_tokens
        usage.total_latency_ms += latency_ms

    # ── Health Check ─────────────────────────────────────────────────

    async def health_check(self) -> Dict[str, Any]:
        """Check NIM API health.

        Returns:
            Health status dictionary.
        """
        nim_available = False
        ollama_available = False

        # Check NIM
        if self._circuit.is_available and self.api_key and _AIOHTTP_AVAILABLE:
            try:
                session = await self._get_session()
                async with session.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    nim_available = resp.status == 200
            except Exception:
                nim_available = False

        # Check Ollama
        if _AIOHTTP_AVAILABLE:
            try:
                session = await self._get_session()
                async with session.get(
                    f"{self.ollama_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    ollama_available = resp.status == 200
            except Exception:
                ollama_available = False

        return {
            "nim_available": nim_available,
            "ollama_available": ollama_available,
            "circuit_state": self._circuit.state.value,
            "aiohttp_available": _AIOHTTP_AVAILABLE,
            "api_key_configured": bool(self.api_key),
        }

    # ── Properties ───────────────────────────────────────────────────

    @property
    def stats(self) -> Dict[str, Any]:
        """Provider statistics."""
        return {
            "circuit_state": self._circuit.state.value,
            "consecutive_failures": self._circuit.consecutive_failures,
            "total_requests": sum(u.total_requests for u in self._usage.values()),
            "total_prompt_tokens": sum(u.total_prompt_tokens for u in self._usage.values()),
            "total_completion_tokens": sum(u.total_completion_tokens for u in self._usage.values()),
            "per_model_usage": {
                model: usage.model_dump()
                for model, usage in self._usage.items()
            },
            "available_models": list(NIM_MODELS.keys()),
        }

    @property
    def available_models(self) -> List[str]:
        """List available NIM model identifiers."""
        return list(NIM_MODELS.keys())

    @property
    def circuit_state(self) -> ProviderState:
        """Current circuit breaker state."""
        return self._circuit.state


# ═══════════════════════════════════════════════════════════════════════
# Demo
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import asyncio

    async def demo():
        # Create provider (no API key -> chat() raises REAL-ONLY; no mock)
        provider = NIMProvider()

        print(f"Available models: {provider.available_models}")
        print(f"Circuit state: {provider.circuit_state.value}")
        print(f"Stats: {provider.stats}")

        # Test each task type
        for task in ["reasoning", "analysis", "quick", "vision", "general"]:
            response = await provider.chat(
                f"Perform {task} analysis of AAPL stock",
                task=task,
            )
            print(f"\n--- Task: {task} ---")
            print(f"Model: {response.model}")
            print(f"Source: {response.source}")
            print(f"Is mock: {response.is_mock}")
            print(f"Content: {response.content[:150]}...")

        # Health check
        health = await provider.health_check()
        print(f"\nHealth check: {health}")

        # Cleanup
        await provider.close()

    asyncio.run(demo())
