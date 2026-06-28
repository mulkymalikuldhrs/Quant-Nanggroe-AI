"""Tests for NIM Model Router — Routing logic, fallback chains, and metrics tracking."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from quant_nanggroe.engine.nvidia_nim.client import NIMAPIError, NIMClient, NIMRateLimitError
from quant_nanggroe.engine.nvidia_nim.config import NIMConfig
from quant_nanggroe.engine.nvidia_nim.models import (
    NIMChatResponse,
    NIMChoice,
    NIMChatMessage,
    NIMModelMetrics,
    NIMModelStatus,
    NIMRerankResponse,
    NIMRoutingDecision,
    NIMRole,
    NIMFinishReason,
    NIMUsage,
    TaskType,
)
from quant_nanggroe.engine.nvidia_nim.router import (
    NIMModelRouter,
    _TASK_MODEL_MAP,
    _COST_OPTIMISATION_THRESHOLD,
)


# ======================================================================
# Fixtures
# ======================================================================

@pytest.fixture
def nim_config():
    """Create a test NIMConfig."""
    return NIMConfig(
        nvidia_nim_api_key="<placeholder>",
        nvidia_nim_base_url="https://integrate.api.nvidia.com/v1",
    )


@pytest.fixture
def mock_client(nim_config):
    """Create a NIMClient with mocked internals."""
    client = NIMClient(config=nim_config)
    return client


@pytest.fixture
def router(mock_client):
    """Create a NIMModelRouter with mock client."""
    return NIMModelRouter(client=mock_client)


def _make_chat_response(
    content: str = "Test response",
    model: str = "meta/llama-3.1-70b-instruct",
    prompt_tokens: int = 100,
    completion_tokens: int = 50,
    latency_ms: float = 500.0,
) -> NIMChatResponse:
    """Helper to create a NIMChatResponse for testing."""
    return NIMChatResponse(
        id="test-id",
        model=model,
        choices=[
            NIMChoice(
                index=0,
                message=NIMChatMessage(role=NIMRole.ASSISTANT, content=content),
                finish_reason=NIMFinishReason.STOP,
            )
        ],
        usage=NIMUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost_usd=NIMClient.estimate_cost(model, prompt_tokens, completion_tokens),
            latency_ms=latency_ms,
        ),
    )


# ======================================================================
# Task Model Mapping
# ======================================================================

class TestTaskModelMapping:
    """Tests for the task-to-model mapping configuration."""

    def test_all_task_types_have_mapping(self):
        """Every TaskType should have a mapping entry."""
        for tt in TaskType:
            assert tt in _TASK_MODEL_MAP, f"Missing mapping for {tt}"

    def test_each_mapping_has_primary(self):
        """Every mapping should have a primary model."""
        for tt, cfg in _TASK_MODEL_MAP.items():
            assert "primary" in cfg, f"Missing primary for {tt}"
            assert cfg["primary"], f"Empty primary for {tt}"

    def test_each_mapping_has_fallbacks(self):
        """Every mapping should have at least one fallback."""
        for tt, cfg in _TASK_MODEL_MAP.items():
            assert "fallbacks" in cfg, f"Missing fallbacks for {tt}"
            assert len(cfg["fallbacks"]) >= 1, f"No fallbacks for {tt}"

    def test_each_mapping_has_temperature(self):
        """Every mapping should specify a temperature."""
        for tt, cfg in _TASK_MODEL_MAP.items():
            assert "temperature" in cfg, f"Missing temperature for {tt}"
            assert 0.0 <= cfg["temperature"] <= 2.0, f"Invalid temperature for {tt}"

    def test_each_mapping_has_max_tokens(self):
        """Every mapping should specify max_tokens."""
        for tt, cfg in _TASK_MODEL_MAP.items():
            assert "max_tokens" in cfg, f"Missing max_tokens for {tt}"
            assert cfg["max_tokens"] > 0, f"Invalid max_tokens for {tt}"

    def test_analysis_uses_70b(self):
        assert _TASK_MODEL_MAP[TaskType.ANALYSIS]["primary"] == "meta/llama-3.1-70b-instruct"

    def test_strategy_uses_405b(self):
        assert _TASK_MODEL_MAP[TaskType.STRATEGY]["primary"] == "meta/llama-3.1-405b-instruct"

    def test_risk_uses_mixtral(self):
        assert _TASK_MODEL_MAP[TaskType.RISK]["primary"] == "mistralai/mixtral-8x22b-instruct"

    def test_sentiment_uses_gemma(self):
        assert _TASK_MODEL_MAP[TaskType.SENTIMENT]["primary"] == "google/gemma-2-27b-it"

    def test_code_uses_phi(self):
        assert _TASK_MODEL_MAP[TaskType.CODE]["primary"] == "microsoft/phi-3-medium-128k-instruct"

    def test_reward_uses_nemotron(self):
        assert _TASK_MODEL_MAP[TaskType.REWARD]["primary"] == "nvidia/nemotron-4-340b-reward"


# ======================================================================
# Routing Decisions
# ======================================================================

class TestRouting:
    """Tests for routing decisions."""

    def test_route_analysis(self, router):
        """ANALYSIS task routes to llama-3.1-70b."""
        decision = router.route(TaskType.ANALYSIS)
        assert decision.primary_model == "meta/llama-3.1-70b-instruct"
        assert decision.selected_model == "meta/llama-3.1-70b-instruct"
        assert decision.task_type == TaskType.ANALYSIS

    def test_route_strategy(self, router):
        """STRATEGY task routes to llama-3.1-405b."""
        decision = router.route(TaskType.STRATEGY)
        assert decision.primary_model == "meta/llama-3.1-405b-instruct"

    def test_route_returns_fallback_chain(self, router):
        """Routing decision includes the fallback chain."""
        decision = router.route(TaskType.ANALYSIS)
        assert isinstance(decision.fallback_chain, list)
        assert len(decision.fallback_chain) > 0

    def test_route_with_unavailable_primary(self, router):
        """When primary is unavailable, router falls back."""
        primary = _TASK_MODEL_MAP[TaskType.ANALYSIS]["primary"]
        router._metrics[primary].status = NIMModelStatus.UNAVAILABLE

        decision = router.route(TaskType.ANALYSIS)
        assert decision.selected_model != primary
        assert "Fallback" in decision.reason

    def test_route_with_rate_limited_primary(self, router):
        """When primary is rate-limited, router falls back."""
        primary = _TASK_MODEL_MAP[TaskType.SENTIMENT]["primary"]
        router._metrics[primary].status = NIMModelStatus.RATE_LIMITED

        decision = router.route(TaskType.SENTIMENT)
        assert decision.selected_model != primary

    def test_route_all_unavailable_tries_primary(self, router):
        """When all models are unavailable, falls back to primary anyway."""
        for model_id in router._metrics:
            router._metrics[model_id].status = NIMModelStatus.UNAVAILABLE

        decision = router.route(TaskType.ANALYSIS)
        # Should still return the primary (exhausted fallback)
        assert decision.selected_model == decision.primary_model
        assert "exhausted" in decision.reason.lower()

    def test_route_cost_estimate(self, router):
        """Routing decision includes a cost estimate."""
        decision = router.route(TaskType.ANALYSIS)
        assert decision.cost_estimate_usd >= 0.0

    def test_route_latency_estimate(self, router):
        """Routing decision includes a latency estimate."""
        decision = router.route(TaskType.ANALYSIS)
        assert decision.estimated_latency_ms >= 0.0


# ======================================================================
# Cost Optimisation
# ======================================================================

class TestCostOptimisation:
    """Tests for cost-optimised routing."""

    def test_prefer_cheaper_no_data(self, router):
        """Without enough data, prefer_cheaper should still select primary."""
        decision = router.route(TaskType.ANALYSIS, prefer_cheaper=True)
        # With no request history (< 10 requests), should default to primary
        assert decision.selected_model == decision.primary_model

    def test_prefer_cheaper_with_data(self, router):
        """With enough data and close quality, cheaper model may be selected."""
        primary = _TASK_MODEL_MAP[TaskType.ANALYSIS]["primary"]
        fallback = _TASK_MODEL_MAP[TaskType.ANALYSIS]["fallbacks"][0]

        # Simulate enough data points
        for _ in range(15):
            router._metrics[primary].total_requests += 1
        router._metrics[primary].total_failures = 0  # 100% success

        for _ in range(15):
            router._metrics[fallback].total_requests += 1
        router._metrics[fallback].total_failures = 0  # 100% success

        decision = router.route(TaskType.ANALYSIS, prefer_cheaper=True)
        # If the fallback is cheaper and quality is close, it may be selected
        assert decision.selected_model in [primary, fallback]


# ======================================================================
# Chat with Routing
# ======================================================================

class TestChatWithRouting:
    """Tests for the chat method with automatic routing and fallback."""

    @pytest.mark.asyncio
    async def test_chat_primary_success(self, router, mock_client):
        """Chat routes to primary model and succeeds."""
        response = _make_chat_response(model="meta/llama-3.1-70b-instruct")
        mock_client.chat = AsyncMock(return_value=response)

        result = await router.chat(TaskType.ANALYSIS, "Analyze AAPL")

        assert result.content == "Test response"
        mock_client.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_primary_fails_fallback_succeeds(self, router, mock_client):
        """When primary fails, falls back to next model."""
        fallback_model = _TASK_MODEL_MAP[TaskType.ANALYSIS]["fallbacks"][0]
        fallback_response = _make_chat_response(model=fallback_model)

        call_count = 0

        async def mock_chat(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            model = kwargs.get("model")
            if model == _TASK_MODEL_MAP[TaskType.ANALYSIS]["primary"]:
                raise NIMAPIError(500, "Server error", model=model)
            return fallback_response

        mock_client.chat = AsyncMock(side_effect=mock_chat)

        result = await router.chat(TaskType.ANALYSIS, "Test")

        assert result.content == "Test response"
        assert call_count == 2  # Primary failed, fallback succeeded

    @pytest.mark.asyncio
    async def test_chat_all_models_fail(self, router, mock_client):
        """When all models fail, raises RuntimeError."""
        mock_client.chat = AsyncMock(side_effect=NIMAPIError(500, "Down", model="test"))

        with pytest.raises(RuntimeError, match="All NIM models failed"):
            await router.chat(TaskType.ANALYSIS, "Test")

    @pytest.mark.asyncio
    async def test_chat_with_system_prompt(self, router, mock_client):
        """Chat passes system_prompt through to client."""
        response = _make_chat_response()
        mock_client.chat = AsyncMock(return_value=response)

        await router.chat(TaskType.ANALYSIS, "Hello", system_prompt="You are a quant")

        call_kwargs = mock_client.chat.call_args
        assert call_kwargs.kwargs.get("system_prompt") == "You are a quant"

    @pytest.mark.asyncio
    async def test_chat_records_success_metrics(self, router, mock_client):
        """Successful chat updates model metrics."""
        response = _make_chat_response(latency_ms=300.0)
        mock_client.chat = AsyncMock(return_value=response)

        await router.chat(TaskType.ANALYSIS, "Test")

        model_id = _TASK_MODEL_MAP[TaskType.ANALYSIS]["primary"]
        metrics = router._metrics[model_id]
        assert metrics.total_requests >= 1
        assert metrics.consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_chat_records_failure_metrics(self, router, mock_client):
        """Failed chat updates model metrics."""
        mock_client.chat = AsyncMock(
            side_effect=NIMAPIError(500, "Down", model="test")
        )

        with pytest.raises(RuntimeError):
            await router.chat(TaskType.ANALYSIS, "Test")

        model_id = _TASK_MODEL_MAP[TaskType.ANALYSIS]["primary"]
        metrics = router._metrics[model_id]
        assert metrics.total_requests >= 1
        assert metrics.total_failures >= 1
        assert metrics.consecutive_failures >= 1


# ======================================================================
# Metrics Tracking
# ======================================================================

class TestMetricsTracking:
    """Tests for metrics tracking and retrieval."""

    def test_initial_metrics_populated(self, router):
        """Router should pre-populate metrics for all known models."""
        all_models: set[str] = set()
        for cfg in _TASK_MODEL_MAP.values():
            all_models.add(cfg["primary"])
            all_models.update(cfg["fallbacks"])

        for model_id in all_models:
            assert model_id in router._metrics

    def test_get_metrics_all(self, router):
        """Get metrics for all models."""
        metrics = router.get_metrics()
        assert isinstance(metrics, dict)
        assert len(metrics) > 0

    def test_get_metrics_specific(self, router):
        """Get metrics for a specific model."""
        model_id = "meta/llama-3.1-70b-instruct"
        metrics = router.get_metrics(model_id)
        assert "model_id" in metrics
        assert metrics["model_id"] == model_id

    def test_get_metrics_unknown_model(self, router):
        """Get metrics for an unknown model returns error."""
        metrics = router.get_metrics("nonexistent/model")
        assert "error" in metrics

    def test_mark_model_unavailable(self, router):
        """Mark a model as unavailable."""
        model_id = "meta/llama-3.1-70b-instruct"
        router.mark_model_unavailable(model_id, "Manual override")
        assert router._metrics[model_id].status == NIMModelStatus.UNAVAILABLE
        assert router._metrics[model_id].last_error == "Manual override"

    def test_mark_model_available(self, router):
        """Mark a model as available."""
        model_id = "meta/llama-3.1-70b-instruct"
        router.mark_model_unavailable(model_id, "Down")
        router.mark_model_available(model_id)
        assert router._metrics[model_id].status == NIMModelStatus.AVAILABLE
        assert router._metrics[model_id].consecutive_failures == 0
        assert router._metrics[model_id].last_error is None

    def test_mark_unknown_model_unavailable(self, router):
        """Marking an unknown model as unavailable should not crash."""
        router.mark_model_unavailable("unknown/model", "Test")
        # Should silently do nothing (model not in _metrics)

    def test_success_rate_tracking(self, router):
        """Verify success rate is calculated correctly from metrics."""
        model_id = "meta/llama-3.1-70b-instruct"
        m = router._metrics[model_id]
        m.total_requests = 100
        m.total_failures = 5
        assert m.success_rate == pytest.approx(0.95)


# ======================================================================
# Task Model Map API
# ======================================================================

class TestTaskModelMapAPI:
    """Tests for the get_task_model_map method."""

    def test_returns_all_task_types(self, router):
        """Should return mapping for all task types."""
        mapping = router.get_task_model_map()
        for tt in TaskType:
            assert tt.value in mapping

    def test_mapping_structure(self, router):
        """Each mapping should have primary, fallbacks, temperature, max_tokens."""
        mapping = router.get_task_model_map()
        for tt_value, cfg in mapping.items():
            assert "primary" in cfg
            assert "fallbacks" in cfg
            assert "temperature" in cfg
            assert "max_tokens" in cfg


# ======================================================================
# Internal: _record_success / _record_failure
# ======================================================================

class TestRecordSuccessFailure:
    """Tests for internal _record_success and _record_failure methods."""

    def test_record_success_updates_latency(self, router):
        """Recording success updates average latency."""
        model_id = "meta/llama-3.1-70b-instruct"
        router._record_success(model_id, latency_ms=500.0, tokens_in=100, tokens_out=50, cost_usd=0.01)
        assert router._metrics[model_id].avg_latency_ms == 500.0

        router._record_success(model_id, latency_ms=300.0, tokens_in=100, tokens_out=50, cost_usd=0.01)
        # EMA: 500 * 0.8 + 300 * 0.2 = 460
        assert router._metrics[model_id].avg_latency_ms == pytest.approx(460.0, abs=1.0)

    def test_record_success_updates_token_counts(self, router):
        """Recording success updates token counts."""
        model_id = "meta/llama-3.1-70b-instruct"
        router._record_success(model_id, latency_ms=100.0, tokens_in=200, tokens_out=100, cost_usd=0.005)
        assert router._metrics[model_id].total_tokens_in == 200
        assert router._metrics[model_id].total_tokens_out == 100

    def test_record_success_resets_consecutive_failures(self, router):
        """Recording success resets consecutive failures."""
        model_id = "meta/llama-3.1-70b-instruct"
        router._record_failure(model_id, "test error")
        assert router._metrics[model_id].consecutive_failures == 1
        router._record_success(model_id, latency_ms=100.0, tokens_in=10, tokens_out=10, cost_usd=0.001)
        assert router._metrics[model_id].consecutive_failures == 0

    def test_record_failure_increments_counters(self, router):
        """Recording failure increments failure counters."""
        model_id = "meta/llama-3.1-70b-instruct"
        router._record_failure(model_id, "API error")
        assert router._metrics[model_id].consecutive_failures == 1
        assert router._metrics[model_id].total_failures == 1

    def test_record_failure_sets_rate_limited_at_3(self, router):
        """After 3 consecutive failures, status becomes RATE_LIMITED."""
        model_id = "meta/llama-3.1-70b-instruct"
        for _ in range(3):
            router._record_failure(model_id, "Error")
        assert router._metrics[model_id].status == NIMModelStatus.RATE_LIMITED

    def test_record_failure_sets_unavailable_at_5(self, router):
        """After 5 consecutive failures, status becomes UNAVAILABLE."""
        model_id = "meta/llama-3.1-70b-instruct"
        for _ in range(5):
            router._record_failure(model_id, "Error")
        assert router._metrics[model_id].status == NIMModelStatus.UNAVAILABLE

    def test_record_success_creates_metrics_for_unknown_model(self, router):
        """Recording success for an unknown model creates metrics."""
        model_id = "some/new-model"
        router._record_success(model_id, latency_ms=200.0, tokens_in=50, tokens_out=25, cost_usd=0.002)
        assert model_id in router._metrics
        assert router._metrics[model_id].total_requests == 1

    def test_record_failure_creates_metrics_for_unknown_model(self, router):
        """Recording failure for an unknown model creates metrics."""
        model_id = "some/failed-model"
        router._record_failure(model_id, "Unknown model error")
        assert model_id in router._metrics
        assert router._metrics[model_id].total_failures == 1
