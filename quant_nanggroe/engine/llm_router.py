"""LLM Router — Multi-Provider Failover with Cost Tracking.

Provides intelligent routing across multiple LLM providers with
automatic failover, health monitoring, cooldown on failure,
cost tracking, and model selection (deep thinking vs quick).

Features
--------
* Multi-provider failover (OpenAI → Anthropic → Google → NVIDIA → local)
* Provider health monitoring with circuit breaker
* Cooldown on failure (exponential backoff)
* Cost tracking per provider and model
* Model selection (deep thinking vs quick response)
* Graceful fallback when providers are unavailable

Dependencies
------------
Uses langchain-openai, langchain-anthropic, langchain-google-genai
(packages already in the project dependencies).
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    NVIDIA = "nvidia"
    LOCAL = "local"
    NVIDIA_NIM = "nvidia_nim"


class ModelTier(str, Enum):
    """Model tier for request routing."""
    DEEP_THINKING = "deep_thinking"  # Most capable, slower
    STANDARD = "standard"           # Balanced
    QUICK = "quick"                 # Fast, cheaper


class ProviderHealthStatus(str, Enum):
    """Provider health status."""
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    COOLDOWN = "COOLDOWN"
    UNKNOWN = "UNKNOWN"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ProviderConfig(BaseModel):
    """Configuration for an LLM provider."""
    provider: LLMProvider = Field(..., description="Provider identifier")
    api_key: Optional[str] = Field(None, description="API key")
    base_url: Optional[str] = Field(None, description="Custom base URL")
    models: Dict[ModelTier, str] = Field(default_factory=dict, description="Model per tier")
    max_tokens: Dict[ModelTier, int] = Field(default_factory=dict)
    priority: int = Field(0, description="Priority (lower = higher priority)")
    enabled: bool = Field(True, description="Whether provider is enabled")
    rate_limit_rpm: int = Field(60, description="Rate limit in requests per minute")


class ProviderHealth(BaseModel):
    """Health status of an LLM provider."""
    provider: LLMProvider = Field(..., description="Provider identifier")
    status: ProviderHealthStatus = Field(ProviderHealthStatus.UNKNOWN)
    consecutive_failures: int = Field(0, description="Consecutive failure count")
    last_success_at: Optional[str] = Field(None)
    last_failure_at: Optional[str] = Field(None)
    cooldown_until: Optional[str] = Field(None, description="Cooldown expiry time")
    total_requests: int = Field(0, description="Total request count")
    total_failures: int = Field(0, description="Total failure count")
    avg_latency_ms: float = Field(0.0, description="Average latency in ms")
    success_rate: float = Field(0.0, description="Success rate (0-1)")


class CostRecord(BaseModel):
    """Cost tracking record for an LLM call."""
    record_id: str = Field("", description="Record identifier")
    provider: LLMProvider = Field(..., description="LLM provider")
    model: str = Field("", description="Model used")
    tier: ModelTier = Field(ModelTier.STANDARD, description="Model tier")
    input_tokens: int = Field(0, description="Input token count")
    output_tokens: int = Field(0, description="Output token count")
    cost_usd: float = Field(0.0, description="Cost in USD")
    latency_ms: float = Field(0.0, description="Request latency in ms")
    success: bool = Field(True, description="Whether request succeeded")
    timestamp: str = Field("")


class LLMResponse(BaseModel):
    """Response from an LLM call."""
    content: str = Field("", description="Response text content")
    provider: LLMProvider = Field(..., description="Provider that generated the response")
    model: str = Field("", description="Model used")
    tier: ModelTier = Field(ModelTier.STANDARD, description="Model tier")
    input_tokens: int = Field(0, description="Input tokens used")
    output_tokens: int = Field(0, description="Output tokens generated")
    cost_usd: float = Field(0.0, description="Cost in USD")
    latency_ms: float = Field(0.0, description="Total latency in ms")
    fallback_used: bool = Field(False, description="Whether fallback was used")
    timestamp: str = Field("")


# ---------------------------------------------------------------------------
# Default provider configurations
# ---------------------------------------------------------------------------

_DEFAULT_MODELS: Dict[LLMProvider, Dict[ModelTier, str]] = {
    LLMProvider.OPENAI: {
        ModelTier.DEEP_THINKING: "o3-mini",
        ModelTier.STANDARD: "gpt-4o",
        ModelTier.QUICK: "gpt-4o-mini",
    },
    LLMProvider.ANTHROPIC: {
        ModelTier.DEEP_THINKING: "claude-3-5-sonnet-20241022",
        ModelTier.STANDARD: "claude-3-5-sonnet-20241022",
        ModelTier.QUICK: "claude-3-haiku-20240307",
    },
    LLMProvider.GOOGLE: {
        ModelTier.DEEP_THINKING: "gemini-2.0-flash-thinking-exp",
        ModelTier.STANDARD: "gemini-2.0-flash",
        ModelTier.QUICK: "gemini-2.0-flash-lite",
    },
    LLMProvider.NVIDIA: {
        ModelTier.DEEP_THINKING: "meta/llama-3.1-405b-instruct",
        ModelTier.STANDARD: "meta/llama-3.1-70b-instruct",
        ModelTier.QUICK: "meta/llama-3.1-8b-instruct",
    },
    LLMProvider.LOCAL: {
        ModelTier.DEEP_THINKING: "llama3:70b",
        ModelTier.STANDARD: "llama3:8b",
        ModelTier.QUICK: "phi3:mini",
    },
    LLMProvider.NVIDIA_NIM: {
        ModelTier.DEEP_THINKING: "meta/llama-3.1-405b-instruct",
        ModelTier.STANDARD: "meta/llama-3.1-70b-instruct",
        ModelTier.QUICK: "google/gemma-2-27b-it",
    },
}

_DEFAULT_MAX_TOKENS: Dict[ModelTier, int] = {
    ModelTier.DEEP_THINKING: 16000,
    ModelTier.STANDARD: 4096,
    ModelTier.QUICK: 1024,
}

# Approximate cost per 1K tokens (USD)
_COST_PER_1K: Dict[str, Dict[str, float]] = {
    "openai": {"input": 0.005, "output": 0.015},
    "anthropic": {"input": 0.003, "output": 0.015},
    "google": {"input": 0.001, "output": 0.002},
    "nvidia": {"input": 0.002, "output": 0.006},
    "local": {"input": 0.0, "output": 0.0},
    "nvidia_nim": {"input": 0.003, "output": 0.008},
}


# ---------------------------------------------------------------------------
# LLM Router
# ---------------------------------------------------------------------------

class LLMRouter:
    """Multi-provider LLM router with failover and cost tracking.

    Routes LLM requests across multiple providers with automatic
    failover, health monitoring, cooldown on failure, and cost tracking.

    Usage::

        router = LLMRouter()
        router.add_provider(ProviderConfig(
            provider=LLMProvider.OPENAI,
            api_key="<placeholder>",
            priority=0,
        ))
        response = await router.chat("Explain market volatility", tier=ModelTier.QUICK)
        stats = router.get_cost_stats()
    """

    def __init__(self) -> None:
        self._providers: Dict[LLMProvider, ProviderConfig] = {}
        self._health: Dict[LLMProvider, ProviderHealth] = {}
        self._cost_records: List[CostRecord] = []
        self._max_consecutive_failures = 5
        self._base_cooldown_seconds = 30.0

    def add_provider(self, config: ProviderConfig) -> None:
        """Add an LLM provider configuration.

        Args:
            config: ProviderConfig with provider details.
        """
        # Fill in default models if not specified
        if not config.models:
            config.models = _DEFAULT_MODELS.get(config.provider, {})
        if not config.max_tokens:
            config.max_tokens = _DEFAULT_MAX_TOKENS

        self._providers[config.provider] = config
        self._health[config.provider] = ProviderHealth(provider=config.provider)
        logger.info("Added LLM provider: %s (priority=%d)", config.provider.value, config.priority)

    def remove_provider(self, provider: LLMProvider) -> None:
        """Remove an LLM provider.

        Args:
            provider: Provider to remove.
        """
        self._providers.pop(provider, None)
        self._health.pop(provider, None)

    async def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        tier: ModelTier = ModelTier.STANDARD,
        max_tokens: Optional[int] = None,
        preferred_provider: Optional[LLMProvider] = None,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Send a chat request to the LLM with automatic failover.

        Tries providers in priority order, falling back to the next
        provider on failure. Implements cooldown on repeated failures.

        Args:
            prompt: User message/prompt.
            system_prompt: Optional system prompt.
            tier: Model tier (deep_thinking, standard, quick).
            max_tokens: Maximum output tokens.
            preferred_provider: Optional preferred provider to try first.
            temperature: Sampling temperature.

        Returns:
            LLMResponse with the generated content and metadata.

        Raises:
            ExchangeError: If all providers fail.
        """
        start_time = time.monotonic()

        # Build provider order
        providers = self._get_provider_order(preferred_provider)

        last_error = None
        for provider_enum in providers:
            config = self._providers.get(provider_enum)
            if not config or not config.enabled:
                continue

            # Check cooldown
            health = self._health.get(provider_enum)
            if health and health.status == ProviderHealthStatus.COOLDOWN:
                if health.cooldown_until:
                    try:
                        cooldown_time = datetime.fromisoformat(health.cooldown_until)
                        if datetime.now(tz=timezone.utc) < cooldown_time:
                            logger.debug("Provider %s in cooldown, skipping", provider_enum.value)
                            continue
                        else:
                            health.status = ProviderHealthStatus.UNKNOWN
                    except (ValueError, TypeError):
                        pass

            # Get model name
            model = config.models.get(tier, "")
            if not model:
                continue

            # Try the request
            try:
                content, in_tokens, out_tokens = await self._call_provider(
                    config, prompt, system_prompt, model, max_tokens, temperature,
                )

                latency = (time.monotonic() - start_time) * 1000

                # Calculate cost
                cost = self._calculate_cost(provider_enum, in_tokens, out_tokens)

                # Update health
                self._record_success(provider_enum, latency)

                # Record cost
                cost_record = CostRecord(
                    record_id=str(uuid.uuid4())[:8],
                    provider=provider_enum,
                    model=model,
                    tier=tier,
                    input_tokens=in_tokens,
                    output_tokens=out_tokens,
                    cost_usd=cost,
                    latency_ms=round(latency, 2),
                    success=True,
                    timestamp=datetime.now(tz=timezone.utc).isoformat(),
                )
                self._cost_records.append(cost_record)

                return LLMResponse(
                    content=content,
                    provider=provider_enum,
                    model=model,
                    tier=tier,
                    input_tokens=in_tokens,
                    output_tokens=out_tokens,
                    cost_usd=cost,
                    latency_ms=round(latency, 2),
                    fallback_used=provider_enum != (preferred_provider or providers[0] if providers else None),
                    timestamp=datetime.now(tz=timezone.utc).isoformat(),
                )

            except Exception as exc:
                last_error = exc
                logger.warning(
                    "LLM provider %s failed: %s",
                    provider_enum.value, exc,
                )
                self._record_failure(provider_enum)
                continue

        # All providers failed
        raise RuntimeError(
            f"All LLM providers failed. Last error: {last_error}"
        )

    def get_provider_health(self) -> Dict[str, ProviderHealth]:
        """Get health status of all providers.

        Returns:
            Dict mapping provider name to health status.
        """
        return {p.value: h for p, h in self._health.items()}

    def get_cost_stats(self) -> Dict[str, Any]:
        """Get cost tracking statistics.

        Returns:
            Dict with cost statistics per provider and total.
        """
        if not self._cost_records:
            return {"total_cost_usd": 0.0, "total_requests": 0, "by_provider": {}}

        total_cost = sum(r.cost_usd for r in self._cost_records)
        by_provider: Dict[str, Dict[str, Any]] = {}

        for provider in LLMProvider:
            records = [r for r in self._cost_records if r.provider == provider]
            if records:
                by_provider[provider.value] = {
                    "total_cost_usd": round(sum(r.cost_usd for r in records), 6),
                    "total_requests": len(records),
                    "total_input_tokens": sum(r.input_tokens for r in records),
                    "total_output_tokens": sum(r.output_tokens for r in records),
                    "success_rate": round(
                        sum(1 for r in records if r.success) / len(records), 4
                    ),
                    "avg_latency_ms": round(
                        sum(r.latency_ms for r in records) / len(records), 2
                    ),
                }

        return {
            "total_cost_usd": round(total_cost, 6),
            "total_requests": len(self._cost_records),
            "by_provider": by_provider,
        }

    # ----- Internal helpers -----

    def _get_provider_order(
        self,
        preferred: Optional[LLMProvider] = None,
    ) -> List[LLMProvider]:
        """Get provider order for failover routing."""
        # Sort by priority (lower = higher priority)
        providers = sorted(
            [p for p in self._providers.keys() if self._providers[p].enabled],
            key=lambda p: self._providers[p].priority,
        )

        # Move preferred to front if specified
        if preferred and preferred in providers:
            providers.remove(preferred)
            providers.insert(0, preferred)

        return providers

    async def _call_provider(
        self,
        config: ProviderConfig,
        prompt: str,
        system_prompt: Optional[str],
        model: str,
        max_tokens: Optional[int],
        temperature: float,
    ) -> tuple[str, int, int]:
        """Call a specific LLM provider.

        Returns:
            Tuple of (content, input_tokens, output_tokens).
        """
        provider = config.provider
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        if provider == LLMProvider.OPENAI:
            return await self._call_openai(config, messages, model, max_tokens, temperature)
        elif provider == LLMProvider.ANTHROPIC:
            return await self._call_anthropic(config, messages, model, max_tokens, temperature)
        elif provider == LLMProvider.GOOGLE:
            return await self._call_google(config, messages, model, max_tokens, temperature)
        elif provider == LLMProvider.NVIDIA:
            return await self._call_nvidia(config, messages, model, max_tokens, temperature)
        elif provider == LLMProvider.LOCAL:
            return await self._call_local(config, messages, model, max_tokens, temperature)
        elif provider == LLMProvider.NVIDIA_NIM:
            return await self._call_nvidia_nim(config, messages, model, max_tokens, temperature)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    @staticmethod
    async def _call_openai(
        config: ProviderConfig,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: Optional[int],
        temperature: float,
    ) -> tuple[str, int, int]:
        """Call OpenAI API."""
        try:
            from langchain_openai import ChatOpenAI

            llm = ChatOpenAI(
                model=model,
                api_key=config.api_key or "",
                base_url=config.base_url,
                max_tokens=max_tokens or 4096,
                temperature=temperature,
            )
            from langchain_core.messages import HumanMessage, SystemMessage

            lc_messages = []
            for m in messages:
                if m["role"] == "system":
                    lc_messages.append(SystemMessage(content=m["content"]))
                else:
                    lc_messages.append(HumanMessage(content=m["content"]))

            result = await llm.ainvoke(lc_messages)
            content = result.content if hasattr(result, "content") else str(result)
            in_tokens = result.response_metadata.get("token_usage", {}).get("prompt_tokens", 0) if hasattr(result, "response_metadata") else 0
            out_tokens = result.response_metadata.get("token_usage", {}).get("completion_tokens", 0) if hasattr(result, "response_metadata") else 0
            return content, in_tokens, out_tokens
        except ImportError:
            raise ImportError("langchain-openai is required for OpenAI provider")

    @staticmethod
    async def _call_anthropic(
        config: ProviderConfig,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: Optional[int],
        temperature: float,
    ) -> tuple[str, int, int]:
        """Call Anthropic API."""
        try:
            from langchain_anthropic import ChatAnthropic

            llm = ChatAnthropic(
                model=model,
                api_key=config.api_key or "",
                max_tokens=max_tokens or 4096,
                temperature=temperature,
            )
            from langchain_core.messages import HumanMessage, SystemMessage

            lc_messages = []
            for m in messages:
                if m["role"] == "system":
                    lc_messages.append(SystemMessage(content=m["content"]))
                else:
                    lc_messages.append(HumanMessage(content=m["content"]))

            result = await llm.ainvoke(lc_messages)
            content = result.content if hasattr(result, "content") else str(result)
            in_tokens = result.response_metadata.get("usage", {}).get("input_tokens", 0) if hasattr(result, "response_metadata") else 0
            out_tokens = result.response_metadata.get("usage", {}).get("output_tokens", 0) if hasattr(result, "response_metadata") else 0
            return content, in_tokens, out_tokens
        except ImportError:
            raise ImportError("langchain-anthropic is required for Anthropic provider")

    @staticmethod
    async def _call_google(
        config: ProviderConfig,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: Optional[int],
        temperature: float,
    ) -> tuple[str, int, int]:
        """Call Google GenAI API."""
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            llm = ChatGoogleGenerativeAI(
                model=model,
                google_api_key=config.api_key or "",
                max_output_tokens=max_tokens or 4096,
                temperature=temperature,
            )
            from langchain_core.messages import HumanMessage, SystemMessage

            lc_messages = []
            for m in messages:
                if m["role"] == "system":
                    lc_messages.append(SystemMessage(content=m["content"]))
                else:
                    lc_messages.append(HumanMessage(content=m["content"]))

            result = await llm.ainvoke(lc_messages)
            content = result.content if hasattr(result, "content") else str(result)
            return content, 0, 0  # Google doesn't always provide token counts
        except ImportError:
            raise ImportError("langchain-google-genai is required for Google provider")

    @staticmethod
    async def _call_nvidia(
        config: ProviderConfig,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: Optional[int],
        temperature: float,
    ) -> tuple[str, int, int]:
        """Call NVIDIA NIM API (OpenAI-compatible).

        NVIDIA NIM provides OpenAI-compatible endpoints, so we reuse
        ChatOpenAI with a custom base_url pointing to the NIM API.
        """
        try:
            from langchain_openai import ChatOpenAI

            base_url = config.base_url or "https://integrate.api.nvidia.com/v1"
            llm = ChatOpenAI(
                model=model,
                api_key=config.api_key or "",
                base_url=base_url,
                max_tokens=max_tokens or 4096,
                temperature=temperature,
            )
            from langchain_core.messages import HumanMessage, SystemMessage

            lc_messages = []
            for m in messages:
                if m["role"] == "system":
                    lc_messages.append(SystemMessage(content=m["content"]))
                else:
                    lc_messages.append(HumanMessage(content=m["content"]))

            result = await llm.ainvoke(lc_messages)
            content = result.content if hasattr(result, "content") else str(result)
            in_tokens = result.response_metadata.get("token_usage", {}).get("prompt_tokens", 0) if hasattr(result, "response_metadata") else 0
            out_tokens = result.response_metadata.get("token_usage", {}).get("completion_tokens", 0) if hasattr(result, "response_metadata") else 0
            return content, in_tokens, out_tokens
        except ImportError:
            raise ImportError("langchain-openai is required for NVIDIA NIM provider")

    @staticmethod
    async def _call_local(
        config: ProviderConfig,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: Optional[int],
        temperature: float,
    ) -> tuple[str, int, int]:
        """Call local LLM via Ollama or similar."""
        try:
            import httpx

            base_url = config.base_url or "http://localhost:11434"
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{base_url}/api/chat",
                    json={
                        "model": model,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "num_predict": max_tokens or 4096,
                            "temperature": temperature,
                        },
                    },
                )
                data = response.json()
                content = data.get("message", {}).get("content", "")
                eval_count = data.get("eval_count", 0)
                prompt_eval_count = data.get("prompt_eval_count", 0)
                return content, prompt_eval_count, eval_count
        except ImportError:
            raise ImportError("httpx is required for local LLM provider")
        except Exception as exc:
            raise RuntimeError(f"Local LLM call failed: {exc}") from exc

    @staticmethod
    async def _call_nvidia_nim(
        config: ProviderConfig,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: Optional[int],
        temperature: float,
    ) -> tuple[str, int, int]:
        """Call NVIDIA NIM API using the NIMClient."""
        try:
            from quant_nanggroe.engine.nvidia_nim.client import NIMClient
            from quant_nanggroe.engine.nvidia_nim.models import NIMChatMessage, NIMRole

            nim_messages: list[NIMChatMessage] = []
            for m in messages:
                try:
                    role = NIMRole(m["role"])
                except ValueError:
                    role = NIMRole.USER
                nim_messages.append(NIMChatMessage(role=role, content=m["content"]))

            nim_config = None
            if config.api_key or config.base_url:
                from quant_nanggroe.engine.nvidia_nim.config import NIMConfig
                nim_config = NIMConfig(
                    nvidia_nim_api_key=config.api_key,
                    nvidia_nim_base_url=config.base_url or "https://integrate.api.nvidia.com/v1",
                )

            client = NIMClient(config=nim_config)
            try:
                response = await client.chat_with_messages(
                    nim_messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens or 4096,
                )
                return (
                    response.content,
                    response.usage.prompt_tokens,
                    response.usage.completion_tokens,
                )
            finally:
                await client.close()
        except ImportError:
            raise ImportError(
                "quant_nanggroe.engine.nvidia_nim is required for NVIDIA NIM provider"
            )

    def _record_success(self, provider: LLMProvider, latency_ms: float) -> None:
        """Record a successful provider call."""
        health = self._health.get(provider)
        if health:
            health.status = ProviderHealthStatus.HEALTHY
            health.consecutive_failures = 0
            health.last_success_at = datetime.now(tz=timezone.utc).isoformat()
            health.cooldown_until = None
            health.total_requests += 1

            # Update average latency
            if health.avg_latency_ms == 0:
                health.avg_latency_ms = latency_ms
            else:
                health.avg_latency_ms = (health.avg_latency_ms * 0.8) + (latency_ms * 0.2)

            health.success_rate = (
                (health.total_requests - health.total_failures) / health.total_requests
                if health.total_requests > 0 else 0.0
            )

    def _record_failure(self, provider: LLMProvider) -> None:
        """Record a failed provider call."""
        health = self._health.get(provider)
        if health:
            health.consecutive_failures += 1
            health.total_requests += 1
            health.total_failures += 1
            health.last_failure_at = datetime.now(tz=timezone.utc).isoformat()
            health.success_rate = (
                (health.total_requests - health.total_failures) / health.total_requests
                if health.total_requests > 0 else 0.0
            )

            # Update status
            if health.consecutive_failures >= self._max_consecutive_failures:
                health.status = ProviderHealthStatus.UNHEALTHY
            elif health.consecutive_failures >= 3:
                health.status = ProviderHealthStatus.DEGRADED

            # Set cooldown
            if health.consecutive_failures >= 2:
                cooldown_seconds = self._base_cooldown_seconds * (2 ** (health.consecutive_failures - 2))
                cooldown_seconds = min(cooldown_seconds, 600)  # Max 10 minutes
                from datetime import timedelta
                health.cooldown_until = (
                    datetime.now(tz=timezone.utc) + timedelta(seconds=cooldown_seconds)
                ).isoformat()
                health.status = ProviderHealthStatus.COOLDOWN

    @staticmethod
    def _calculate_cost(
        provider: LLMProvider,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Calculate approximate cost for an LLM call."""
        costs = _COST_PER_1K.get(provider.value, {"input": 0.0, "output": 0.0})
        input_cost = (input_tokens / 1000) * costs["input"]
        output_cost = (output_tokens / 1000) * costs["output"]
        return round(input_cost + output_cost, 6)


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------

_default_router: LLMRouter | None = None


def get_llm_router() -> LLMRouter:
    """Get or create the default LLMRouter instance."""
    global _default_router
    if _default_router is None:
        _default_router = LLMRouter()
    return _default_router


__all__ = [
    "LLMRouter",
    "LLMProvider",
    "ModelTier",
    "ProviderHealthStatus",
    "ProviderConfig",
    "ProviderHealth",
    "CostRecord",
    "LLMResponse",
    "get_llm_router",
]
