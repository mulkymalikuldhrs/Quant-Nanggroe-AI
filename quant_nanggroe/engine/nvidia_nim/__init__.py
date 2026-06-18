"""NVIDIA NIM (NVIDIA Inference Microservices) integration.

Provides LLM inference through NVIDIA's cloud-hosted models,
optimized for financial analysis, strategy generation, and risk assessment.

Modules
-------
client
    Async HTTP client for the NIM API (chat, embeddings, reranking, streaming).
router
    Intelligent model router that maps task types to optimal models.
models
    Pydantic v2 data models for requests, responses, and metrics.
config
    Configuration with environment variable support (QNAI_ prefix).
prompts
    Financial prompt templates for market analysis, strategy, risk, etc.
"""

from quant_nanggroe.engine.nvidia_nim.client import NIMClient
from quant_nanggroe.engine.nvidia_nim.router import NIMModelRouter

__all__ = ["NIMClient", "NIMModelRouter"]
