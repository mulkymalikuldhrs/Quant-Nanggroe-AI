"""Comprehensive Tests for LLM Router — Multi-Provider Failover with Cost Tracking.

All tests use mocked LLM providers — no real API calls.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from quant_nanggroe.engine.llm_router import (
    LLMRouter,
    LLMProvider,
    ModelTier,
    ProviderHealthStatus,
    ProviderConfig,
    ProviderHealth,
    CostRecord,
    LLMResponse,
    get_llm_router,
    _DEFAULT_MODELS,
    _DEFAULT_MAX_TOKENS,
    _COST_PER_1K,
)


# ======================================================================
# Fixtures
# ======================================================================

@pytest.fixture
def router():
    """Create a fresh LLMRouter instance."""
    return LLMRouter()


@pytest.fixture
def openai_config():
    return ProviderConfig(
        provider=LLMProvider.OPENAI,
        api_key="sk-test-key",
        priority=0,
    )


@pytest.fixture
def anthropic_config():
    return ProviderConfig(
        provider=LLMProvider.ANTHROPIC,
        api_key="sk-ant-test",
        priority=1,
    )


@pytest.fixture
def google_config():
    return ProviderConfig(
        provider=LLMProvider.GOOGLE,
        api_key="google-test",
        priority=2,
    )


@pytest.fixture
def local_config():
    return ProviderConfig(
        provider=LLMProvider.LOCAL,
        base_url="http://localhost:11434",
        priority=3,
    )


@pytest.fixture
def router_with_providers(router, openai_config, anthropic_config):
    router.add_provider(openai_config)
    router.add_provider(anthropic_config)
    return router


@pytest.fixture
def router_with_all_providers(router, openai_config, anthropic_config, google_config, local_config):
    router.add_provider(openai_config)
    router.add_provider(anthropic_config)
    router.add_provider(google_config)
    router.add_provider(local_config)
    return router


# ======================================================================
# Enums
# ======================================================================

class TestLLMProvider:
    """Tests for LLMProvider enum."""

    def test_all_providers(self):
        assert LLMProvider.OPENAI == "openai"
        assert LLMProvider.ANTHROPIC == "anthropic"
        assert LLMProvider.GOOGLE == "google"
        assert LLMProvider.LOCAL == "local"

    def test_provider_count(self):
        assert len(LLMProvider) == 4

    def test_is_string_enum(self):
        assert isinstance(LLMProvider.OPENAI, str)


class TestModelTier:
    """Tests for ModelTier enum."""

    def test_all_tiers(self):
        assert ModelTier.DEEP_THINKING == "deep_thinking"
        assert ModelTier.STANDARD == "standard"
        assert ModelTier.QUICK == "quick"

    def test_tier_count(self):
        assert len(ModelTier) == 3


class TestProviderHealthStatus:
    """Tests for ProviderHealthStatus enum."""

    def test_all_statuses(self):
        assert ProviderHealthStatus.HEALTHY == "HEALTHY"
        assert ProviderHealthStatus.DEGRADED == "DEGRADED"
        assert ProviderHealthStatus.UNHEALTHY == "UNHEALTHY"
        assert ProviderHealthStatus.COOLDOWN == "COOLDOWN"
        assert ProviderHealthStatus.UNKNOWN == "UNKNOWN"

    def test_status_count(self):
        assert len(ProviderHealthStatus) == 5


# ======================================================================
# ProviderConfig Model
# ======================================================================

class TestProviderConfig:
    """Tests for ProviderConfig model."""

    def test_required_fields(self):
        config = ProviderConfig(provider=LLMProvider.OPENAI)
        assert config.provider == LLMProvider.OPENAI
        assert config.api_key is None
        assert config.priority == 0
        assert config.enabled is True
        assert config.base_url is None

    def test_custom_values(self):
        config = ProviderConfig(
            provider=LLMProvider.ANTHROPIC,
            api_key="sk-ant-test",
            priority=5,
            enabled=False,
            rate_limit_rpm=100,
            base_url="http://custom.api.com",
        )
        assert config.priority == 5
        assert config.enabled is False
        assert config.rate_limit_rpm == 100
        assert config.base_url == "http://custom.api.com"

    def test_models_default_empty(self):
        config = ProviderConfig(provider=LLMProvider.OPENAI)
        assert config.models == {}

    def test_max_tokens_default_empty(self):
        config = ProviderConfig(provider=LLMProvider.OPENAI)
        assert config.max_tokens == {}

    def test_serialization_round_trip(self):
        config = ProviderConfig(
            provider=LLMProvider.OPENAI,
            api_key="test-key",
            priority=1,
        )
        data = config.model_dump()
        config2 = ProviderConfig(**data)
        assert config2.provider == config.provider
        assert config2.api_key == config.api_key
        assert config2.priority == config.priority


# ======================================================================
# ProviderHealth Model
# ======================================================================

class TestProviderHealth:
    """Tests for ProviderHealth model."""

    def test_default_values(self):
        health = ProviderHealth(provider=LLMProvider.OPENAI)
        assert health.status == ProviderHealthStatus.UNKNOWN
        assert health.consecutive_failures == 0
        assert health.total_requests == 0
        assert health.avg_latency_ms == 0.0
        assert health.success_rate == 0.0
        assert health.last_success_at is None
        assert health.last_failure_at is None
        assert health.cooldown_until is None

    def test_with_data(self):
        health = ProviderHealth(
            provider=LLMProvider.OPENAI,
            status=ProviderHealthStatus.HEALTHY,
            consecutive_failures=0,
            total_requests=100,
            avg_latency_ms=250.0,
            success_rate=0.95,
            last_success_at="2025-01-01T00:00:00Z",
        )
        assert health.success_rate == 0.95
        assert health.total_requests == 100


# ======================================================================
# CostRecord Model
# ======================================================================

class TestCostRecord:
    """Tests for CostRecord model."""

    def test_default_values(self):
        record = CostRecord(provider=LLMProvider.OPENAI)
        assert record.input_tokens == 0
        assert record.output_tokens == 0
        assert record.cost_usd == 0.0
        assert record.success is True
        assert record.tier == ModelTier.STANDARD
        assert record.model == ""
        assert record.latency_ms == 0.0

    def test_with_data(self):
        record = CostRecord(
            provider=LLMProvider.OPENAI,
            model="gpt-4o",
            tier=ModelTier.STANDARD,
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.0125,
            latency_ms=1500.0,
        )
        assert record.cost_usd == 0.0125
        assert record.input_tokens == 1000
        assert record.output_tokens == 500

    def test_failed_record(self):
        record = CostRecord(
            provider=LLMProvider.ANTHROPIC,
            success=False,
        )
        assert record.success is False


# ======================================================================
# LLMResponse Model
# ======================================================================

class TestLLMResponse:
    """Tests for LLMResponse model."""

    def test_required_fields(self):
        response = LLMResponse(
            content="Market analysis indicates...",
            provider=LLMProvider.OPENAI,
        )
        assert response.content == "Market analysis indicates..."
        assert response.fallback_used is False
        assert response.tier == ModelTier.STANDARD

    def test_full_construction(self):
        response = LLMResponse(
            content="Analysis result",
            provider=LLMProvider.ANTHROPIC,
            model="claude-3-5-sonnet-20241022",
            tier=ModelTier.DEEP_THINKING,
            input_tokens=2000,
            output_tokens=1000,
            cost_usd=0.02,
            latency_ms=3000.0,
            fallback_used=True,
        )
        assert response.fallback_used is True
        assert response.cost_usd == 0.02
        assert response.input_tokens == 2000

    def test_default_values(self):
        response = LLMResponse(content="", provider=LLMProvider.OPENAI)
        assert response.model == ""
        assert response.input_tokens == 0
        assert response.output_tokens == 0
        assert response.cost_usd == 0.0
        assert response.latency_ms == 0.0


# ======================================================================
# Default Model Configuration
# ======================================================================

class TestDefaultModels:
    """Tests for default model configuration."""

    def test_openai_models(self):
        models = _DEFAULT_MODELS[LLMProvider.OPENAI]
        assert ModelTier.DEEP_THINKING in models
        assert ModelTier.STANDARD in models
        assert ModelTier.QUICK in models
        assert models[ModelTier.STANDARD] == "gpt-4o"

    def test_anthropic_models(self):
        models = _DEFAULT_MODELS[LLMProvider.ANTHROPIC]
        assert ModelTier.DEEP_THINKING in models
        assert ModelTier.QUICK in models

    def test_google_models(self):
        models = _DEFAULT_MODELS[LLMProvider.GOOGLE]
        assert ModelTier.STANDARD in models

    def test_local_models(self):
        models = _DEFAULT_MODELS[LLMProvider.LOCAL]
        assert ModelTier.STANDARD in models

    def test_default_max_tokens(self):
        assert _DEFAULT_MAX_TOKENS[ModelTier.DEEP_THINKING] > _DEFAULT_MAX_TOKENS[ModelTier.STANDARD]
        assert _DEFAULT_MAX_TOKENS[ModelTier.STANDARD] > _DEFAULT_MAX_TOKENS[ModelTier.QUICK]


class TestCostPer1K:
    """Tests for cost per 1K token configuration."""

    def test_local_is_free(self):
        assert _COST_PER_1K["local"]["input"] == 0.0
        assert _COST_PER_1K["local"]["output"] == 0.0

    def test_all_providers_have_costs(self):
        for provider in ["openai", "anthropic", "google", "local"]:
            assert provider in _COST_PER_1K
            assert "input" in _COST_PER_1K[provider]
            assert "output" in _COST_PER_1K[provider]

    def test_output_cost_higher_than_input(self):
        for provider in ["openai", "anthropic", "google"]:
            assert _COST_PER_1K[provider]["output"] >= _COST_PER_1K[provider]["input"]


# ======================================================================
# Router — Add/Remove Providers
# ======================================================================

class TestRouterProviderManagement:
    """Tests for adding and removing providers."""

    def test_add_provider(self, router, openai_config):
        router.add_provider(openai_config)
        assert LLMProvider.OPENAI in router._providers
        assert LLMProvider.OPENAI in router._health

    def test_add_provider_fills_default_models(self, router):
        config = ProviderConfig(provider=LLMProvider.OPENAI)
        router.add_provider(config)
        assert len(config.models) > 0
        assert ModelTier.STANDARD in config.models

    def test_add_provider_fills_default_max_tokens(self, router):
        config = ProviderConfig(provider=LLMProvider.OPENAI)
        router.add_provider(config)
        assert len(config.max_tokens) > 0
        assert ModelTier.STANDARD in config.max_tokens

    def test_add_provider_creates_health(self, router, openai_config):
        router.add_provider(openai_config)
        health = router._health[LLMProvider.OPENAI]
        assert isinstance(health, ProviderHealth)
        assert health.status == ProviderHealthStatus.UNKNOWN

    def test_remove_provider(self, router, openai_config):
        router.add_provider(openai_config)
        router.remove_provider(LLMProvider.OPENAI)
        assert LLMProvider.OPENAI not in router._providers
        assert LLMProvider.OPENAI not in router._health

    def test_remove_nonexistent(self, router):
        router.remove_provider(LLMProvider.LOCAL)  # Should not raise

    def test_add_multiple_providers(self, router_with_all_providers):
        assert len(router_with_all_providers._providers) == 4
        assert len(router_with_all_providers._health) == 4


# ======================================================================
# Router — Provider Health Monitoring
# ======================================================================

class TestRouterHealthMonitoring:
    """Tests for provider health monitoring."""

    def test_initial_health_unknown(self, router, openai_config):
        router.add_provider(openai_config)
        health = router._health[LLMProvider.OPENAI]
        assert health.status == ProviderHealthStatus.UNKNOWN

    def test_record_success(self, router, openai_config):
        router.add_provider(openai_config)
        router._record_success(LLMProvider.OPENAI, 500.0)
        health = router._health[LLMProvider.OPENAI]
        assert health.status == ProviderHealthStatus.HEALTHY
        assert health.consecutive_failures == 0
        assert health.total_requests == 1
        assert health.avg_latency_ms == 500.0

    def test_record_success_updates_latency(self, router, openai_config):
        router.add_provider(openai_config)
        router._record_success(LLMProvider.OPENAI, 500.0)
        router._record_success(LLMProvider.OPENAI, 300.0)
        health = router._health[LLMProvider.OPENAI]
        # EMA: 500 * 0.8 + 300 * 0.2 = 460
        assert health.avg_latency_ms == pytest.approx(460.0, abs=1.0)

    def test_record_success_updates_success_rate(self, router, openai_config):
        router.add_provider(openai_config)
        router._record_success(LLMProvider.OPENAI, 500.0)
        health = router._health[LLMProvider.OPENAI]
        assert health.success_rate == 1.0

    def test_record_success_sets_timestamp(self, router, openai_config):
        router.add_provider(openai_config)
        router._record_success(LLMProvider.OPENAI, 500.0)
        health = router._health[LLMProvider.OPENAI]
        assert health.last_success_at is not None

    def test_record_failure(self, router, openai_config):
        router.add_provider(openai_config)
        router._record_failure(LLMProvider.OPENAI)
        health = router._health[LLMProvider.OPENAI]
        assert health.consecutive_failures == 1
        assert health.total_failures == 1
        assert health.total_requests == 1

    def test_failure_sets_cooldown_after_two(self, router, openai_config):
        """After 2 failures, status becomes COOLDOWN (overrides DEGRADED)."""
        router.add_provider(openai_config)
        for _ in range(2):
            router._record_failure(LLMProvider.OPENAI)
        health = router._health[LLMProvider.OPENAI]
        assert health.status == ProviderHealthStatus.COOLDOWN

    def test_failure_consecutive_count(self, router, openai_config):
        """Consecutive failures are tracked correctly."""
        router.add_provider(openai_config)
        router._record_failure(LLMProvider.OPENAI)
        router._record_failure(LLMProvider.OPENAI)
        router._record_failure(LLMProvider.OPENAI)
        health = router._health[LLMProvider.OPENAI]
        assert health.consecutive_failures == 3

    def test_failure_sets_unhealthy_level(self, router, openai_config):
        """After 5 failures, the code tracks UNHEALTHY logic (but COOLDOWN overrides)."""
        router.add_provider(openai_config)
        for _ in range(5):
            router._record_failure(LLMProvider.OPENAI)
        health = router._health[LLMProvider.OPENAI]
        # COOLDOWN overrides UNHEALTHY in the current implementation
        assert health.status == ProviderHealthStatus.COOLDOWN
        assert health.consecutive_failures == 5
        assert health.total_failures == 5

    def test_failure_sets_cooldown(self, router, openai_config):
        router.add_provider(openai_config)
        router._record_failure(LLMProvider.OPENAI)
        router._record_failure(LLMProvider.OPENAI)
        health = router._health[LLMProvider.OPENAI]
        assert health.status == ProviderHealthStatus.COOLDOWN
        assert health.cooldown_until is not None

    def test_cooldown_exponential_backoff(self, router, openai_config):
        router.add_provider(openai_config)
        # 2 failures: 30s base cooldown
        router._record_failure(LLMProvider.OPENAI)
        router._record_failure(LLMProvider.OPENAI)
        h2 = router._health[LLMProvider.OPENAI]
        assert h2.cooldown_until is not None

        # 3 failures: 60s
        router._record_failure(LLMProvider.OPENAI)
        h3 = router._health[LLMProvider.OPENAI]
        assert h3.cooldown_until is not None

    def test_success_resets_failures(self, router, openai_config):
        router.add_provider(openai_config)
        router._record_failure(LLMProvider.OPENAI)
        router._record_failure(LLMProvider.OPENAI)
        router._record_success(LLMProvider.OPENAI, 100.0)
        health = router._health[LLMProvider.OPENAI]
        assert health.consecutive_failures == 0
        assert health.cooldown_until is None
        assert health.status == ProviderHealthStatus.HEALTHY

    def test_success_rate_mixed(self, router, openai_config):
        router.add_provider(openai_config)
        router._record_failure(LLMProvider.OPENAI)  # 0/1
        router._record_failure(LLMProvider.OPENAI)  # 0/2
        router._record_success(LLMProvider.OPENAI, 100.0)  # resets failures but not total_failures
        health = router._health[LLMProvider.OPENAI]
        # total_requests=3, total_failures=2, success_rate=1/3
        assert health.success_rate == pytest.approx(1/3, abs=0.01)

    def test_get_provider_health(self, router_with_providers):
        health = router_with_providers.get_provider_health()
        assert "openai" in health
        assert "anthropic" in health

    def test_failure_sets_timestamp(self, router, openai_config):
        router.add_provider(openai_config)
        router._record_failure(LLMProvider.OPENAI)
        health = router._health[LLMProvider.OPENAI]
        assert health.last_failure_at is not None


# ======================================================================
# Router — Failover Logic
# ======================================================================

class TestRouterFailover:
    """Tests for failover routing."""

    def test_provider_order_by_priority(self, router, openai_config, anthropic_config, google_config):
        openai_config.priority = 2
        anthropic_config.priority = 0
        google_config.priority = 1
        router.add_provider(openai_config)
        router.add_provider(anthropic_config)
        router.add_provider(google_config)

        order = router._get_provider_order()
        assert order[0] == LLMProvider.ANTHROPIC
        assert order[1] == LLMProvider.GOOGLE
        assert order[2] == LLMProvider.OPENAI

    def test_preferred_provider_first(self, router_with_providers):
        order = router_with_providers._get_provider_order(preferred=LLMProvider.ANTHROPIC)
        assert order[0] == LLMProvider.ANTHROPIC

    def test_preferred_provider_not_in_list(self, router, openai_config):
        router.add_provider(openai_config)
        # Preferred not in providers — should still work
        order = router._get_provider_order(preferred=LLMProvider.GOOGLE)
        assert LLMProvider.OPENAI in order

    def test_disabled_provider_excluded(self, router, openai_config, anthropic_config):
        openai_config.enabled = False
        router.add_provider(openai_config)
        router.add_provider(anthropic_config)

        order = router._get_provider_order()
        assert LLMProvider.OPENAI not in order

    def test_empty_provider_order(self, router):
        order = router._get_provider_order()
        assert order == []

    @pytest.mark.asyncio
    async def test_all_providers_fail(self, router_with_providers):
        """When all providers fail, should raise RuntimeError."""
        with patch.object(router_with_providers, "_call_provider", side_effect=Exception("API down")):
            with pytest.raises(RuntimeError, match="All LLM providers failed"):
                await router_with_providers.chat("Test prompt")

    @pytest.mark.asyncio
    async def test_failover_to_second_provider(self, router, openai_config, anthropic_config):
        router.add_provider(openai_config)
        router.add_provider(anthropic_config)

        async def mock_call(config, prompt, system, model, max_tokens, temp):
            if config.provider == LLMProvider.OPENAI:
                raise Exception("OpenAI down")
            return ("Response from Anthropic", 100, 50)

        with patch.object(router, "_call_provider", side_effect=mock_call):
            response = await router.chat("Test prompt")
            assert response.provider == LLMProvider.ANTHROPIC
            assert response.fallback_used is True

    @pytest.mark.asyncio
    async def test_failover_records_failure_for_first(self, router, openai_config, anthropic_config):
        router.add_provider(openai_config)
        router.add_provider(anthropic_config)

        async def mock_call(config, prompt, system, model, max_tokens, temp):
            if config.provider == LLMProvider.OPENAI:
                raise Exception("OpenAI down")
            return ("Response", 100, 50)

        with patch.object(router, "_call_provider", side_effect=mock_call):
            await router.chat("Test")
            assert router._health[LLMProvider.OPENAI].consecutive_failures == 1


# ======================================================================
# Router — Cost Tracking
# ======================================================================

class TestRouterCostTracking:
    """Tests for cost tracking."""

    def test_empty_cost_stats(self, router):
        stats = router.get_cost_stats()
        assert stats["total_cost_usd"] == 0.0
        assert stats["total_requests"] == 0
        assert stats["by_provider"] == {}

    def test_cost_stats_with_records(self, router):
        router._cost_records = [
            CostRecord(
                provider=LLMProvider.OPENAI,
                model="gpt-4o",
                input_tokens=1000,
                output_tokens=500,
                cost_usd=0.0125,
                latency_ms=1000.0,
                success=True,
            ),
            CostRecord(
                provider=LLMProvider.ANTHROPIC,
                model="claude-3-5-sonnet-20241022",
                input_tokens=2000,
                output_tokens=1000,
                cost_usd=0.021,
                latency_ms=2000.0,
                success=True,
            ),
        ]
        stats = router.get_cost_stats()
        assert stats["total_cost_usd"] == 0.0335
        assert stats["total_requests"] == 2
        assert "openai" in stats["by_provider"]
        assert "anthropic" in stats["by_provider"]

    def test_cost_stats_per_provider(self, router):
        router._cost_records = [
            CostRecord(
                provider=LLMProvider.OPENAI,
                input_tokens=1000,
                output_tokens=500,
                cost_usd=0.01,
                success=True,
            ),
            CostRecord(
                provider=LLMProvider.OPENAI,
                input_tokens=500,
                output_tokens=250,
                cost_usd=0.005,
                success=False,
            ),
        ]
        stats = router.get_cost_stats()
        openai_stats = stats["by_provider"]["openai"]
        assert openai_stats["total_requests"] == 2
        assert openai_stats["success_rate"] == 0.5
        assert openai_stats["total_input_tokens"] == 1500

    def test_cost_calculation(self, router):
        cost = router._calculate_cost(LLMProvider.OPENAI, 1000, 500)
        assert cost > 0.0
        assert isinstance(cost, float)

    def test_cost_local_is_zero(self, router):
        cost = router._calculate_cost(LLMProvider.LOCAL, 1000, 500)
        assert cost == 0.0

    def test_cost_calculation_formula(self, router):
        # OpenAI: input=$0.005/1K, output=$0.015/1K
        cost = router._calculate_cost(LLMProvider.OPENAI, 2000, 1000)
        expected = (2000 / 1000) * 0.005 + (1000 / 1000) * 0.015
        assert cost == pytest.approx(expected, abs=0.0001)

    def test_cost_google_lower_than_openai(self, router):
        cost_openai = router._calculate_cost(LLMProvider.OPENAI, 1000, 1000)
        cost_google = router._calculate_cost(LLMProvider.GOOGLE, 1000, 1000)
        assert cost_google < cost_openai


# ======================================================================
# Router — Chat with Mocked Provider
# ======================================================================

class TestRouterChat:
    """Tests for chat method with mocked providers."""

    @pytest.mark.asyncio
    async def test_chat_success(self, router, openai_config):
        router.add_provider(openai_config)

        async def mock_call(config, prompt, system, model, max_tokens, temp):
            return ("Market is bullish", 500, 200)

        with patch.object(router, "_call_provider", side_effect=mock_call):
            response = await router.chat("Analyze market")
            assert response.content == "Market is bullish"
            assert response.provider == LLMProvider.OPENAI
            assert response.input_tokens == 500
            assert response.output_tokens == 200

    @pytest.mark.asyncio
    async def test_chat_with_system_prompt(self, router, openai_config):
        router.add_provider(openai_config)

        prompts_received = []

        async def mock_call(config, prompt, system, model, max_tokens, temp):
            prompts_received.append({"prompt": prompt, "system": system})
            return ("Response", 100, 50)

        with patch.object(router, "_call_provider", side_effect=mock_call):
            await router.chat("Analyze", system_prompt="You are a trader")
            assert prompts_received[0]["system"] == "You are a trader"

    @pytest.mark.asyncio
    async def test_chat_tier_selection(self, router, openai_config):
        router.add_provider(openai_config)

        models_used = []

        async def mock_call(config, prompt, system, model, max_tokens, temp):
            models_used.append(model)
            return ("Deep analysis", 1000, 500)

        with patch.object(router, "_call_provider", side_effect=mock_call):
            await router.chat("Forecast", tier=ModelTier.DEEP_THINKING)
            assert models_used[0] in openai_config.models.get(ModelTier.DEEP_THINKING, "")

    @pytest.mark.asyncio
    async def test_chat_quick_tier(self, router, openai_config):
        router.add_provider(openai_config)

        models_used = []

        async def mock_call(config, prompt, system, model, max_tokens, temp):
            models_used.append(model)
            return ("Quick response", 100, 50)

        with patch.object(router, "_call_provider", side_effect=mock_call):
            await router.chat("Quick check", tier=ModelTier.QUICK)
            assert models_used[0] in openai_config.models.get(ModelTier.QUICK, "")

    @pytest.mark.asyncio
    async def test_chat_records_cost(self, router, openai_config):
        router.add_provider(openai_config)

        async def mock_call(config, prompt, system, model, max_tokens, temp):
            return ("Response", 100, 50)

        with patch.object(router, "_call_provider", side_effect=mock_call):
            await router.chat("Test")
            assert len(router._cost_records) == 1
            assert router._cost_records[0].success is True

    @pytest.mark.asyncio
    async def test_chat_records_failed_cost(self, router, openai_config, anthropic_config):
        router.add_provider(openai_config)
        router.add_provider(anthropic_config)

        async def mock_call(config, prompt, system, model, max_tokens, temp):
            if config.provider == LLMProvider.OPENAI:
                raise Exception("OpenAI down")
            return ("Response from Anthropic", 100, 50)

        with patch.object(router, "_call_provider", side_effect=mock_call):
            response = await router.chat("Test")
            assert response.provider == LLMProvider.ANTHROPIC
            # Cost record only for successful call
            assert len(router._cost_records) == 1

    @pytest.mark.asyncio
    async def test_chat_no_providers_raises(self, router):
        """Chat with no providers should raise RuntimeError."""
        with pytest.raises(RuntimeError, match="All LLM providers failed"):
            await router.chat("Test")

    @pytest.mark.asyncio
    async def test_chat_with_preferred_provider(self, router_with_providers):
        async def mock_call(config, prompt, system, model, max_tokens, temp):
            return (f"Response from {config.provider.value}", 100, 50)

        with patch.object(router_with_providers, "_call_provider", side_effect=mock_call):
            response = await router_with_providers.chat("Test", preferred_provider=LLMProvider.ANTHROPIC)
            assert response.provider == LLMProvider.ANTHROPIC

    @pytest.mark.asyncio
    async def test_chat_fallback_flag(self, router, openai_config, anthropic_config):
        openai_config.priority = 0
        anthropic_config.priority = 1
        router.add_provider(openai_config)
        router.add_provider(anthropic_config)

        async def mock_call(config, prompt, system, model, max_tokens, temp):
            if config.provider == LLMProvider.OPENAI:
                raise Exception("Down")
            return ("Response", 100, 50)

        with patch.object(router, "_call_provider", side_effect=mock_call):
            response = await router.chat("Test")
            assert response.fallback_used is True

    @pytest.mark.asyncio
    async def test_chat_no_fallback_flag(self, router, openai_config):
        router.add_provider(openai_config)

        async def mock_call(config, prompt, system, model, max_tokens, temp):
            return ("Response", 100, 50)

        with patch.object(router, "_call_provider", side_effect=mock_call):
            response = await router.chat("Test")
            assert response.fallback_used is False


# ======================================================================
# Router — Circuit Breaker / Cooldown
# ======================================================================

class TestRouterCircuitBreaker:
    """Tests for circuit breaker behavior."""

    def test_cooldown_exponential_backoff(self, router, openai_config):
        router.add_provider(openai_config)

        # First 2 failures: cooldown
        router._record_failure(LLMProvider.OPENAI)
        router._record_failure(LLMProvider.OPENAI)
        health = router._health[LLMProvider.OPENAI]
        assert health.status == ProviderHealthStatus.COOLDOWN

    def test_cooldown_max_cap(self, router, openai_config):
        """Cooldown should be capped at 600 seconds."""
        router.add_provider(openai_config)
        for _ in range(10):
            router._record_failure(LLMProvider.OPENAI)
        health = router._health[LLMProvider.OPENAI]
        if health.cooldown_until:
            # Parse cooldown time and verify it's not more than 600s in the future
            cooldown_time = datetime.fromisoformat(health.cooldown_until)
            now = datetime.now(tz=timezone.utc)
            diff = (cooldown_time - now).total_seconds()
            assert diff <= 610  # Small buffer for test execution time

    @pytest.mark.asyncio
    async def test_cooldown_skips_provider(self, router, openai_config, anthropic_config):
        router.add_provider(openai_config)
        router.add_provider(anthropic_config)

        # Force OpenAI into cooldown with far-future cooldown time
        health = router._health[LLMProvider.OPENAI]
        health.status = ProviderHealthStatus.COOLDOWN
        health.cooldown_until = (
            datetime.now(tz=timezone.utc) + timedelta(hours=1)
        ).isoformat()

        async def mock_call(config, prompt, system, model, max_tokens, temp):
            return ("Response", 100, 50)

        with patch.object(router, "_call_provider", side_effect=mock_call):
            response = await router.chat("Test")
            assert response.provider == LLMProvider.ANTHROPIC

    @pytest.mark.asyncio
    async def test_expired_cooldown_allows_retry(self, router, openai_config):
        router.add_provider(openai_config)

        # Set cooldown in the past
        health = router._health[LLMProvider.OPENAI]
        health.status = ProviderHealthStatus.COOLDOWN
        health.cooldown_until = (
            datetime.now(tz=timezone.utc) - timedelta(hours=1)
        ).isoformat()

        async def mock_call(config, prompt, system, model, max_tokens, temp):
            return ("Response", 100, 50)

        with patch.object(router, "_call_provider", side_effect=mock_call):
            response = await router.chat("Test")
            assert response.provider == LLMProvider.OPENAI

    @pytest.mark.asyncio
    async def test_degraded_provider_still_tried(self, router, openai_config):
        """DEGRADED providers are still tried (not skipped)."""
        router.add_provider(openai_config)

        # Set DEGRADED status
        health = router._health[LLMProvider.OPENAI]
        health.status = ProviderHealthStatus.DEGRADED
        health.consecutive_failures = 3

        async def mock_call(config, prompt, system, model, max_tokens, temp):
            return ("Response", 100, 50)

        with patch.object(router, "_call_provider", side_effect=mock_call):
            response = await router.chat("Test")
            assert response.provider == LLMProvider.OPENAI

    @pytest.mark.asyncio
    async def test_unhealthy_provider_still_tried(self, router, openai_config):
        """UNHEALTHY providers are still tried (not skipped, only COOLDOWN skips)."""
        router.add_provider(openai_config)

        # Set UNHEALTHY status
        health = router._health[LLMProvider.OPENAI]
        health.status = ProviderHealthStatus.UNHEALTHY
        health.consecutive_failures = 5

        async def mock_call(config, prompt, system, model, max_tokens, temp):
            return ("Response", 100, 50)

        with patch.object(router, "_call_provider", side_effect=mock_call):
            response = await router.chat("Test")
            assert response.provider == LLMProvider.OPENAI


# ======================================================================
# Router — Model Selection
# ======================================================================

class TestRouterModelSelection:
    """Tests for model tier selection."""

    def test_default_models_populated_on_add(self, router):
        config = ProviderConfig(provider=LLMProvider.OPENAI, api_key="test")
        router.add_provider(config)
        assert ModelTier.DEEP_THINKING in config.models
        assert ModelTier.STANDARD in config.models
        assert ModelTier.QUICK in config.models

    def test_custom_models_preserved(self, router):
        config = ProviderConfig(
            provider=LLMProvider.OPENAI,
            api_key="test",
            models={ModelTier.STANDARD: "gpt-3.5-turbo"},
        )
        router.add_provider(config)
        assert config.models[ModelTier.STANDARD] == "gpt-3.5-turbo"
        # Other tiers not set
        assert ModelTier.DEEP_THINKING not in config.models

    @pytest.mark.asyncio
    async def test_tier_with_no_model_skipped(self, router):
        config = ProviderConfig(
            provider=LLMProvider.OPENAI,
            api_key="test",
            models={ModelTier.STANDARD: "gpt-4o"},  # Only STANDARD
        )
        router.add_provider(config)

        async def mock_call(config, prompt, system, model, max_tokens, temp):
            return ("Response", 100, 50)

        with patch.object(router, "_call_provider", side_effect=mock_call):
            response = await router.chat("Test", tier=ModelTier.STANDARD)
            assert response.provider == LLMProvider.OPENAI

    @pytest.mark.asyncio
    async def test_deep_thinking_tier_model(self, router, openai_config):
        router.add_provider(openai_config)

        models_used = []

        async def mock_call(config, prompt, system, model, max_tokens, temp):
            models_used.append(model)
            return ("Deep thought", 2000, 1000)

        with patch.object(router, "_call_provider", side_effect=mock_call):
            await router.chat("Complex analysis", tier=ModelTier.DEEP_THINKING)
            assert models_used[0] == openai_config.models[ModelTier.DEEP_THINKING]


# ======================================================================
# Module-level convenience
# ======================================================================

class TestGetLLMRouter:
    """Tests for get_llm_router function."""

    def test_returns_router(self):
        r = get_llm_router()
        assert isinstance(r, LLMRouter)

    def test_returns_same_instance(self):
        r1 = get_llm_router()
        r2 = get_llm_router()
        assert r1 is r2
