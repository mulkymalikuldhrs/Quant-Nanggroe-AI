"""Pydantic v2 models for NVIDIA NIM API request/response structures.

Defines all data models used by the NIM client, router, and integrations,
including chat messages, embedding requests/responses, model metadata,
usage tracking, and task-type routing enums.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TaskType(str, Enum):
    """Task types for intelligent model routing.

    Each task type maps to an optimal NIM model via the NIMModelRouter.
    """

    ANALYSIS = "analysis"          # Financial analysis → llama-3.1-70b
    STRATEGY = "strategy"          # Strategy generation → llama-3.1-405b
    RISK = "risk"                  # Risk assessment → mixtral-8x22b
    SENTIMENT = "sentiment"        # Sentiment analysis → gemma-2-27b
    CODE = "code"                  # Code generation → phi-3-medium-128k
    REWARD = "reward"              # Reward scoring → nemotron-4-340b


class NIMRole(str, Enum):
    """Chat message roles compatible with NIM chat completions API."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class NIMFinishReason(str, Enum):
    """Reason for completion in a chat response."""

    STOP = "stop"
    LENGTH = "length"
    TOOL_CALLS = "tool_calls"
    CONTENT_FILTER = "content_filter"


class NIMModelStatus(str, Enum):
    """Status of a NIM model endpoint."""

    AVAILABLE = "available"
    RATE_LIMITED = "rate_limited"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Chat Models
# ---------------------------------------------------------------------------

class NIMChatMessage(BaseModel):
    """A single chat message in a NIM conversation.

    Follows the OpenAI-compatible chat format used by NVIDIA NIM.
    """

    role: NIMRole = Field(..., description="Message role (system, user, assistant, tool)")
    content: str = Field(..., description="Message text content")
    name: Optional[str] = Field(None, description="Optional name for the participant")
    tool_call_id: Optional[str] = Field(None, description="Tool call ID for tool responses")

    model_config = {"frozen": False}


class NIMChatRequest(BaseModel):
    """Request payload for NIM chat completion endpoint.

    Compatible with the OpenAI-format chat completions API at
    ``https://integrate.api.nvidia.com/v1/chat/completions``.
    """

    model: str = Field(
        "meta/llama-3.1-70b-instruct",
        description="NIM model identifier (e.g. 'meta/llama-3.1-70b-instruct')",
    )
    messages: List[NIMChatMessage] = Field(
        ..., min_length=1, description="Conversation messages",
    )
    temperature: float = Field(
        0.1, ge=0.0, le=2.0, description="Sampling temperature",
    )
    top_p: float = Field(
        1.0, ge=0.0, le=1.0, description="Nucleus sampling threshold",
    )
    max_tokens: int = Field(
        4096, ge=1, le=65536, description="Maximum tokens to generate",
    )
    stream: bool = Field(
        False, description="Enable streaming response",
    )
    frequency_penalty: float = Field(
        0.0, ge=-2.0, le=2.0, description="Frequency penalty",
    )
    presence_penalty: float = Field(
        0.0, ge=-2.0, le=2.0, description="Presence penalty",
    )
    seed: Optional[int] = Field(
        None, description="Random seed for reproducibility",
    )
    stop: Optional[List[str]] = Field(
        None, description="Stop sequences",
    )

    @field_validator("messages")
    @classmethod
    def validate_messages(cls, v: List[NIMChatMessage]) -> List[NIMChatMessage]:
        """Ensure at least one user message is present."""
        if not any(m.role == NIMRole.USER for m in v):
            raise ValueError("At least one user message is required")
        return v


class NIMChoice(BaseModel):
    """A single choice in a chat completion response."""

    index: int = Field(0, description="Choice index")
    message: NIMChatMessage = Field(..., description="Generated message")
    finish_reason: NIMFinishReason = Field(
        NIMFinishReason.STOP, description="Reason for completion",
    )


class NIMUsage(BaseModel):
    """Token usage and cost tracking for a NIM API call."""

    prompt_tokens: int = Field(0, description="Input token count")
    completion_tokens: int = Field(0, description="Output token count")
    total_tokens: int = Field(0, description="Total tokens (prompt + completion)")
    cost_usd: float = Field(
        0.0, ge=0.0, description="Estimated cost in USD",
    )
    latency_ms: float = Field(
        0.0, ge=0.0, description="Request latency in milliseconds",
    )

    @property
    def tokens_per_second(self) -> float:
        """Calculate tokens per second throughput."""
        if self.latency_ms <= 0 or self.completion_tokens <= 0:
            return 0.0
        return self.completion_tokens / (self.latency_ms / 1000.0)


class NIMChatResponse(BaseModel):
    """Response from a NIM chat completion request."""

    id: str = Field("", description="Response ID from NIM API")
    object: str = Field("chat.completion", description="Object type")
    created: int = Field(
        default_factory=lambda: int(datetime.now(tz=timezone.utc).timestamp()),
        description="Unix timestamp of creation",
    )
    model: str = Field("", description="Model used for generation")
    choices: List[NIMChoice] = Field(
        default_factory=list, description="Generated choices",
    )
    usage: NIMUsage = Field(
        default_factory=NIMUsage, description="Token usage statistics",
    )

    @property
    def content(self) -> str:
        """Extract the first choice's message content."""
        if self.choices:
            return self.choices[0].message.content
        return ""

    @property
    def finish_reason(self) -> Optional[NIMFinishReason]:
        """Extract the first choice's finish reason."""
        if self.choices:
            return self.choices[0].finish_reason
        return None


# ---------------------------------------------------------------------------
# Streaming Models
# ---------------------------------------------------------------------------

class NIMStreamDelta(BaseModel):
    """Delta content in a streaming chunk."""

    role: Optional[NIMRole] = Field(None, description="Message role (only in first chunk)")
    content: Optional[str] = Field(None, description="Delta text content")


class NIMStreamChoice(BaseModel):
    """A single choice in a streaming chunk."""

    index: int = Field(0, description="Choice index")
    delta: NIMStreamDelta = Field(..., description="Delta content")
    finish_reason: Optional[NIMFinishReason] = Field(None, description="Finish reason")


class NIMStreamChunk(BaseModel):
    """A single chunk in a streaming chat completion response."""

    id: str = Field("", description="Chunk ID")
    object: str = Field("chat.completion.chunk", description="Object type")
    created: int = Field(
        default_factory=lambda: int(datetime.now(tz=timezone.utc).timestamp()),
        description="Unix timestamp",
    )
    model: str = Field("", description="Model used")
    choices: List[NIMStreamChoice] = Field(
        default_factory=list, description="Stream choices",
    )

    @property
    def delta_content(self) -> str:
        """Extract the delta text content from the first choice."""
        if self.choices and self.choices[0].delta.content:
            return self.choices[0].delta.content
        return ""


# ---------------------------------------------------------------------------
# Embedding Models
# ---------------------------------------------------------------------------

class NIMEmbeddingRequest(BaseModel):
    """Request payload for NIM embeddings endpoint."""

    model: str = Field(
        "nvidia/nv-embedqa-e5-v5",
        description="Embedding model identifier",
    )
    input: List[str] = Field(
        ..., min_length=1, description="Texts to embed",
    )
    input_type: str = Field(
        "query",
        description="Input type: 'query' or 'passage'",
    )
    encoding_format: str = Field(
        "float", description="Encoding format: 'float' or 'base64'",
    )
    truncate: str = Field(
        "END", description="Truncation strategy: 'NONE', 'START', or 'END'",
    )


class NIMEmbeddingData(BaseModel):
    """A single embedding vector in the response."""

    index: int = Field(..., description="Embedding index")
    embedding: List[float] = Field(..., description="Embedding vector")
    object: str = Field("embedding", description="Object type")


class NIMEmbeddingResponse(BaseModel):
    """Response from a NIM embeddings request."""

    id: str = Field("", description="Response ID")
    object: str = Field("list", description="Object type")
    model: str = Field("", description="Model used")
    data: List[NIMEmbeddingData] = Field(
        default_factory=list, description="Embedding vectors",
    )
    usage: NIMUsage = Field(
        default_factory=NIMUsage, description="Token usage",
    )


# ---------------------------------------------------------------------------
# Reranking Models
# ---------------------------------------------------------------------------

class NIMRerankRequest(BaseModel):
    """Request payload for NIM reranking endpoint."""

    model: str = Field(
        "nvidia/nv-rerankqa-mistral-4b-v3",
        description="Reranking model identifier",
    )
    query: str = Field(..., description="Query text")
    documents: List[str] = Field(
        ..., min_length=1, description="Documents to rank",
    )
    top_n: int = Field(
        ..., ge=1, description="Number of top results to return",
    )


class NIMRerankResult(BaseModel):
    """A single reranking result."""

    index: int = Field(..., description="Document index")
    relevance_score: float = Field(
        ..., ge=0.0, le=1.0, description="Relevance score",
    )
    document: Optional[Dict[str, Any]] = Field(
        None, description="Document text and metadata",
    )


class NIMRerankResponse(BaseModel):
    """Response from a NIM reranking request."""

    id: str = Field("", description="Response ID")
    model: str = Field("", description="Model used")
    results: List[NIMRerankResult] = Field(
        default_factory=list, description="Ranked results",
    )
    usage: NIMUsage = Field(
        default_factory=NIMUsage, description="Token usage",
    )


# ---------------------------------------------------------------------------
# Model Info / Listing
# ---------------------------------------------------------------------------

class NIMModelInfo(BaseModel):
    """Metadata for an available NIM model."""

    id: str = Field(..., description="Model identifier (e.g. 'meta/llama-3.1-70b-instruct')")
    owned_by: str = Field("", description="Model owner")
    object: str = Field("model", description="Object type")
    created: int = Field(0, description="Creation timestamp")
    context_length: Optional[int] = Field(None, description="Maximum context length")
    input_modalities: List[str] = Field(
        default_factory=lambda: ["text"],
        description="Supported input modalities",
    )
    output_modalities: List[str] = Field(
        default_factory=lambda: ["text"],
        description="Supported output modalities",
    )
    status: NIMModelStatus = Field(
        NIMModelStatus.UNKNOWN, description="Current model availability status",
    )
    cost_per_1k_input: float = Field(
        0.0, ge=0.0, description="Cost per 1K input tokens in USD",
    )
    cost_per_1k_output: float = Field(
        0.0, ge=0.0, description="Cost per 1K output tokens in USD",
    )


class NIMModelList(BaseModel):
    """List of available NIM models."""

    object: str = Field("list", description="Object type")
    data: List[NIMModelInfo] = Field(
        default_factory=list, description="Available models",
    )

    @property
    def model_ids(self) -> List[str]:
        """Extract all model IDs."""
        return [m.id for m in self.data]

    def get_model(self, model_id: str) -> Optional[NIMModelInfo]:
        """Find a model by its ID."""
        for m in self.data:
            if m.id == model_id:
                return m
        return None


# ---------------------------------------------------------------------------
# Router Metrics
# ---------------------------------------------------------------------------

class NIMModelMetrics(BaseModel):
    """Performance metrics tracked per NIM model by the router."""

    model_id: str = Field(..., description="Model identifier")
    total_requests: int = Field(0, description="Total requests sent")
    total_failures: int = Field(0, description="Total failed requests")
    total_tokens_in: int = Field(0, description="Total input tokens consumed")
    total_tokens_out: int = Field(0, description="Total output tokens generated")
    total_cost_usd: float = Field(0.0, description="Total cost in USD")
    avg_latency_ms: float = Field(0.0, description="Average latency in ms")
    min_latency_ms: float = Field(float("inf"), description="Minimum latency in ms")
    max_latency_ms: float = Field(0.0, description="Maximum latency in ms")
    last_used_at: Optional[str] = Field(None, description="ISO timestamp of last use")
    last_error: Optional[str] = Field(None, description="Last error message")
    consecutive_failures: int = Field(0, description="Current consecutive failures")
    status: NIMModelStatus = Field(
        NIMModelStatus.UNKNOWN, description="Current model status",
    )

    @property
    def success_rate(self) -> float:
        """Calculate success rate (0.0-1.0)."""
        if self.total_requests == 0:
            return 0.0
        return (self.total_requests - self.total_failures) / self.total_requests

    @property
    def avg_tokens_per_second(self) -> float:
        """Calculate average output throughput."""
        if self.avg_latency_ms <= 0 or self.total_tokens_out <= 0:
            return 0.0
        return self.total_tokens_out / (self.avg_latency_ms / 1000.0)


class NIMRoutingDecision(BaseModel):
    """Result of a model routing decision by NIMModelRouter."""

    task_type: TaskType = Field(..., description="Task type that triggered routing")
    primary_model: str = Field(..., description="Primary model selected")
    fallback_chain: List[str] = Field(
        default_factory=list, description="Fallback model chain",
    )
    selected_model: str = Field(..., description="Actually selected model (may differ from primary)")
    reason: str = Field("", description="Reason for model selection")
    cost_estimate_usd: float = Field(
        0.0, ge=0.0, description="Estimated cost in USD",
    )
    estimated_latency_ms: float = Field(
        0.0, ge=0.0, description="Estimated latency in ms",
    )


__all__ = [
    "TaskType",
    "NIMRole",
    "NIMFinishReason",
    "NIMModelStatus",
    "NIMChatMessage",
    "NIMChatRequest",
    "NIMChoice",
    "NIMUsage",
    "NIMChatResponse",
    "NIMStreamDelta",
    "NIMStreamChoice",
    "NIMStreamChunk",
    "NIMEmbeddingRequest",
    "NIMEmbeddingData",
    "NIMEmbeddingResponse",
    "NIMRerankRequest",
    "NIMRerankResult",
    "NIMRerankResponse",
    "NIMModelInfo",
    "NIMModelList",
    "NIMModelMetrics",
    "NIMRoutingDecision",
]
