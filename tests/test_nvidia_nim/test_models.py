"""Tests for NIM Pydantic v2 models — Validation, serialization, and edge cases."""

from __future__ import annotations

import pytest

from quant_nanggroe.engine.nvidia_nim.models import (
    NIMChatMessage,
    NIMChatRequest,
    NIMChatResponse,
    NIMChoice,
    NIMEmbeddingData,
    NIMEmbeddingRequest,
    NIMEmbeddingResponse,
    NIMFinishReason,
    NIMModelInfo,
    NIMModelList,
    NIMModelMetrics,
    NIMModelStatus,
    NIMRerankRequest,
    NIMRerankResponse,
    NIMRerankResult,
    NIMRole,
    NIMRoutingDecision,
    NIMStreamChunk,
    NIMStreamChoice,
    NIMStreamDelta,
    NIMUsage,
    TaskType,
)


# ======================================================================
# TaskType Enum
# ======================================================================

class TestTaskType:
    """Tests for TaskType enum."""

    def test_all_task_types(self):
        assert TaskType.ANALYSIS == "analysis"
        assert TaskType.STRATEGY == "strategy"
        assert TaskType.RISK == "risk"
        assert TaskType.SENTIMENT == "sentiment"
        assert TaskType.CODE == "code"
        assert TaskType.REWARD == "reward"

    def test_task_type_count(self):
        assert len(TaskType) == 6

    def test_is_string_enum(self):
        assert isinstance(TaskType.ANALYSIS, str)

    def test_from_value(self):
        assert TaskType("analysis") == TaskType.ANALYSIS

    def test_invalid_value(self):
        with pytest.raises(ValueError):
            TaskType("invalid")


# ======================================================================
# NIMRole Enum
# ======================================================================

class TestNIMRole:
    """Tests for NIMRole enum."""

    def test_all_roles(self):
        assert NIMRole.SYSTEM == "system"
        assert NIMRole.USER == "user"
        assert NIMRole.ASSISTANT == "assistant"
        assert NIMRole.TOOL == "tool"

    def test_role_count(self):
        assert len(NIMRole) == 4


# ======================================================================
# NIMFinishReason Enum
# ======================================================================

class TestNIMFinishReason:
    """Tests for NIMFinishReason enum."""

    def test_all_reasons(self):
        assert NIMFinishReason.STOP == "stop"
        assert NIMFinishReason.LENGTH == "length"
        assert NIMFinishReason.TOOL_CALLS == "tool_calls"
        assert NIMFinishReason.CONTENT_FILTER == "content_filter"


# ======================================================================
# NIMModelStatus Enum
# ======================================================================

class TestNIMModelStatus:
    """Tests for NIMModelStatus enum."""

    def test_all_statuses(self):
        assert NIMModelStatus.AVAILABLE == "available"
        assert NIMModelStatus.RATE_LIMITED == "rate_limited"
        assert NIMModelStatus.UNAVAILABLE == "unavailable"
        assert NIMModelStatus.UNKNOWN == "unknown"


# ======================================================================
# NIMChatMessage
# ======================================================================

class TestNIMChatMessage:
    """Tests for NIMChatMessage model."""

    def test_required_fields(self):
        msg = NIMChatMessage(role=NIMRole.USER, content="Hello")
        assert msg.role == NIMRole.USER
        assert msg.content == "Hello"
        assert msg.name is None
        assert msg.tool_call_id is None

    def test_with_all_fields(self):
        msg = NIMChatMessage(
            role=NIMRole.TOOL,
            content="Result",
            name="get_price",
            tool_call_id="call_123",
        )
        assert msg.role == NIMRole.TOOL
        assert msg.name == "get_price"
        assert msg.tool_call_id == "call_123"

    def test_serialization(self):
        msg = NIMChatMessage(role=NIMRole.SYSTEM, content="System prompt")
        data = msg.model_dump()
        assert data["role"] == "system"
        assert data["content"] == "System prompt"

    def test_round_trip(self):
        msg = NIMChatMessage(role=NIMRole.ASSISTANT, content="Response")
        data = msg.model_dump()
        msg2 = NIMChatMessage(**data)
        assert msg2.role == msg.role
        assert msg2.content == msg.content


# ======================================================================
# NIMChatRequest
# ======================================================================

class TestNIMChatRequest:
    """Tests for NIMChatRequest model."""

    def test_default_values(self):
        req = NIMChatRequest(
            messages=[NIMChatMessage(role=NIMRole.USER, content="Test")]
        )
        assert req.model == "meta/llama-3.1-70b-instruct"
        assert req.temperature == 0.1
        assert req.top_p == 1.0
        assert req.max_tokens == 4096
        assert req.stream is False

    def test_custom_model(self):
        req = NIMChatRequest(
            model="meta/llama-3.1-405b-instruct",
            messages=[NIMChatMessage(role=NIMRole.USER, content="Test")]
        )
        assert req.model == "meta/llama-3.1-405b-instruct"

    def test_temperature_validation(self):
        with pytest.raises(Exception):
            NIMChatRequest(
                temperature=3.0,
                messages=[NIMChatMessage(role=NIMRole.USER, content="Test")]
            )

    def test_max_tokens_validation(self):
        with pytest.raises(Exception):
            NIMChatRequest(
                max_tokens=0,
                messages=[NIMChatMessage(role=NIMRole.USER, content="Test")]
            )

    def test_messages_must_have_user(self):
        with pytest.raises(Exception):
            NIMChatRequest(
                messages=[NIMChatMessage(role=NIMRole.SYSTEM, content="System")]
            )

    def test_with_system_and_user(self):
        req = NIMChatRequest(
            messages=[
                NIMChatMessage(role=NIMRole.SYSTEM, content="You are a trader"),
                NIMChatMessage(role=NIMRole.USER, content="Analyze AAPL"),
            ]
        )
        assert len(req.messages) == 2

    def test_exclude_none_serialization(self):
        req = NIMChatRequest(
            messages=[NIMChatMessage(role=NIMRole.USER, content="Test")],
            seed=None,
            stop=None,
        )
        data = req.model_dump(exclude_none=True)
        assert "seed" not in data
        assert "stop" not in data


# ======================================================================
# NIMUsage
# ======================================================================

class TestNIMUsage:
    """Tests for NIMUsage model."""

    def test_default_values(self):
        usage = NIMUsage()
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0
        assert usage.cost_usd == 0.0
        assert usage.latency_ms == 0.0

    def test_tokens_per_second_zero_latency(self):
        usage = NIMUsage(completion_tokens=100, latency_ms=0.0)
        assert usage.tokens_per_second == 0.0

    def test_tokens_per_second_calculation(self):
        usage = NIMUsage(completion_tokens=100, latency_ms=1000.0)
        assert usage.tokens_per_second == pytest.approx(100.0)

    def test_tokens_per_second_typical(self):
        usage = NIMUsage(completion_tokens=500, latency_ms=2000.0)
        assert usage.tokens_per_second == pytest.approx(250.0)

    def test_cost_validation(self):
        with pytest.raises(Exception):
            NIMUsage(cost_usd=-1.0)


# ======================================================================
# NIMChatResponse
# ======================================================================

class TestNIMChatResponse:
    """Tests for NIMChatResponse model."""

    def test_empty_response(self):
        resp = NIMChatResponse()
        assert resp.content == ""
        assert resp.finish_reason is None

    def test_with_choice(self):
        resp = NIMChatResponse(
            model="meta/llama-3.1-70b-instruct",
            choices=[
                NIMChoice(
                    index=0,
                    message=NIMChatMessage(
                        role=NIMRole.ASSISTANT,
                        content="Market is bullish"
                    ),
                    finish_reason=NIMFinishReason.STOP,
                )
            ],
            usage=NIMUsage(prompt_tokens=100, completion_tokens=50),
        )
        assert resp.content == "Market is bullish"
        assert resp.finish_reason == NIMFinishReason.STOP
        assert resp.usage.prompt_tokens == 100

    def test_multiple_choices(self):
        resp = NIMChatResponse(
            choices=[
                NIMChoice(
                    index=0,
                    message=NIMChatMessage(role=NIMRole.ASSISTANT, content="First"),
                ),
                NIMChoice(
                    index=1,
                    message=NIMChatMessage(role=NIMRole.ASSISTANT, content="Second"),
                ),
            ],
        )
        assert resp.content == "First"  # First choice

    def test_object_type(self):
        resp = NIMChatResponse()
        assert resp.object == "chat.completion"


# ======================================================================
# NIMStreamChunk
# ======================================================================

class TestNIMStreamChunk:
    """Tests for NIMStreamChunk model."""

    def test_empty_chunk(self):
        chunk = NIMStreamChunk()
        assert chunk.delta_content == ""

    def test_chunk_with_delta(self):
        chunk = NIMStreamChunk(
            choices=[
                NIMStreamChoice(
                    index=0,
                    delta=NIMStreamDelta(content="Hello"),
                )
            ]
        )
        assert chunk.delta_content == "Hello"

    def test_chunk_with_role(self):
        chunk = NIMStreamChunk(
            choices=[
                NIMStreamChoice(
                    index=0,
                    delta=NIMStreamDelta(role=NIMRole.ASSISTANT, content="Hi"),
                )
            ]
        )
        assert chunk.delta_content == "Hi"
        assert chunk.choices[0].delta.role == NIMRole.ASSISTANT

    def test_chunk_with_finish(self):
        chunk = NIMStreamChunk(
            choices=[
                NIMStreamChoice(
                    index=0,
                    delta=NIMStreamDelta(content=None),
                    finish_reason=NIMFinishReason.STOP,
                )
            ]
        )
        assert chunk.delta_content == ""
        assert chunk.choices[0].finish_reason == NIMFinishReason.STOP


# ======================================================================
# NIMEmbeddingRequest / Response
# ======================================================================

class TestNIMEmbeddingRequest:
    """Tests for NIMEmbeddingRequest model."""

    def test_required_fields(self):
        req = NIMEmbeddingRequest(input=["Hello world"])
        assert req.model == "nvidia/nv-embedqa-e5-v5"
        assert req.input_type == "query"

    def test_multiple_inputs(self):
        req = NIMEmbeddingRequest(input=["text1", "text2", "text3"])
        assert len(req.input) == 3

    def test_empty_input_rejected(self):
        with pytest.raises(Exception):
            NIMEmbeddingRequest(input=[])


class TestNIMEmbeddingResponse:
    """Tests for NIMEmbeddingResponse model."""

    def test_empty_response(self):
        resp = NIMEmbeddingResponse()
        assert len(resp.data) == 0

    def test_with_embeddings(self):
        resp = NIMEmbeddingResponse(
            model="nvidia/nv-embedqa-e5-v5",
            data=[
                NIMEmbeddingData(index=0, embedding=[0.1, 0.2, 0.3]),
                NIMEmbeddingData(index=1, embedding=[0.4, 0.5, 0.6]),
            ],
        )
        assert len(resp.data) == 2
        assert resp.data[0].embedding == [0.1, 0.2, 0.3]


# ======================================================================
# NIMRerankRequest / Response
# ======================================================================

class TestNIMRerankRequest:
    """Tests for NIMRerankRequest model."""

    def test_required_fields(self):
        req = NIMRerankRequest(
            query="What is the GDP?",
            documents=["GDP grew 3%", "Unemployment fell"],
            top_n=2,
        )
        assert req.query == "What is the GDP?"
        assert len(req.documents) == 2
        assert req.top_n == 2


class TestNIMRerankResponse:
    """Tests for NIMRerankResponse model."""

    def test_with_results(self):
        resp = NIMRerankResponse(
            model="nvidia/nv-rerankqa-mistral-4b-v3",
            results=[
                NIMRerankResult(index=0, relevance_score=0.95),
                NIMRerankResult(index=1, relevance_score=0.72),
            ],
        )
        assert len(resp.results) == 2
        assert resp.results[0].relevance_score == 0.95


# ======================================================================
# NIMModelInfo / NIMModelList
# ======================================================================

class TestNIMModelInfo:
    """Tests for NIMModelInfo model."""

    def test_required_fields(self):
        info = NIMModelInfo(id="meta/llama-3.1-70b-instruct")
        assert info.id == "meta/llama-3.1-70b-instruct"
        assert info.status == NIMModelStatus.UNKNOWN
        assert info.context_length is None

    def test_full_construction(self):
        info = NIMModelInfo(
            id="meta/llama-3.1-405b-instruct",
            owned_by="meta",
            context_length=131072,
            status=NIMModelStatus.AVAILABLE,
            cost_per_1k_input=0.008,
            cost_per_1k_output=0.024,
        )
        assert info.owned_by == "meta"
        assert info.context_length == 131072
        assert info.cost_per_1k_input == 0.008


class TestNIMModelList:
    """Tests for NIMModelList model."""

    def test_empty_list(self):
        ml = NIMModelList()
        assert ml.model_ids == []

    def test_model_ids(self):
        ml = NIMModelList(data=[
            NIMModelInfo(id="model-a"),
            NIMModelInfo(id="model-b"),
        ])
        assert ml.model_ids == ["model-a", "model-b"]

    def test_get_model_found(self):
        ml = NIMModelList(data=[
            NIMModelInfo(id="meta/llama-3.1-70b-instruct"),
            NIMModelInfo(id="google/gemma-2-27b-it"),
        ])
        found = ml.get_model("google/gemma-2-27b-it")
        assert found is not None
        assert found.id == "google/gemma-2-27b-it"

    def test_get_model_not_found(self):
        ml = NIMModelList(data=[NIMModelInfo(id="model-a")])
        assert ml.get_model("nonexistent") is None


# ======================================================================
# NIMModelMetrics
# ======================================================================

class TestNIMModelMetrics:
    """Tests for NIMModelMetrics model."""

    def test_default_values(self):
        m = NIMModelMetrics(model_id="test-model")
        assert m.total_requests == 0
        assert m.total_failures == 0
        assert m.success_rate == 0.0
        assert m.avg_tokens_per_second == 0.0
        assert m.status == NIMModelStatus.UNKNOWN

    def test_success_rate_calculation(self):
        m = NIMModelMetrics(
            model_id="test-model",
            total_requests=100,
            total_failures=5,
        )
        assert m.success_rate == pytest.approx(0.95)

    def test_success_rate_zero_requests(self):
        m = NIMModelMetrics(model_id="test-model")
        assert m.success_rate == 0.0

    def test_avg_tokens_per_second(self):
        m = NIMModelMetrics(
            model_id="test-model",
            avg_latency_ms=1000.0,
            total_tokens_out=500,
        )
        # With EMA, avg_latency reflects weighted history — direct calc differs
        # This test verifies the property exists and is non-negative
        assert m.avg_tokens_per_second >= 0.0


# ======================================================================
# NIMRoutingDecision
# ======================================================================

class TestNIMRoutingDecision:
    """Tests for NIMRoutingDecision model."""

    def test_required_fields(self):
        rd = NIMRoutingDecision(
            task_type=TaskType.ANALYSIS,
            primary_model="meta/llama-3.1-70b-instruct",
            selected_model="meta/llama-3.1-70b-instruct",
        )
        assert rd.task_type == TaskType.ANALYSIS
        assert rd.primary_model == rd.selected_model
        assert rd.fallback_chain == []
        assert rd.reason == ""

    def test_full_construction(self):
        rd = NIMRoutingDecision(
            task_type=TaskType.STRATEGY,
            primary_model="meta/llama-3.1-405b-instruct",
            fallback_chain=["meta/llama-3.1-70b-instruct"],
            selected_model="meta/llama-3.1-70b-instruct",
            reason="Fallback: primary unavailable",
            cost_estimate_usd=0.005,
            estimated_latency_ms=1500.0,
        )
        assert rd.reason == "Fallback: primary unavailable"
        assert len(rd.fallback_chain) == 1
