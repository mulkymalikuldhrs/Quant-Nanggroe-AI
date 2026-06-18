"""NVIDIA NIM configuration module.

Provides NIM-specific settings with environment variable support,
aligned with the project-wide QNAI_ prefix convention.
"""

from __future__ import annotations

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class NIMConfig(BaseSettings):
    """NVIDIA NIM connection and behaviour settings.

    All values are loaded from environment variables with the ``QNAI_`` prefix.
    For example, ``QNAI_NVIDIA_NIM_API_KEY`` maps to ``nvidia_nim_api_key``.

    Attributes:
        nvidia_nim_api_key: API key for NVIDIA NIM (from build.nvidia.com).
        nvidia_nim_base_url: Base URL for the NIM API.
        nvidia_nim_default_model: Default model for chat completions.
        nvidia_nim_max_tokens: Default max output tokens per request.
        nvidia_nim_temperature: Default sampling temperature.
        nvidia_nim_timeout: HTTP request timeout in seconds.
        nvidia_nim_max_retries: Maximum retry attempts on transient failures.
        nvidia_nim_rate_limit: Requests per minute (free-tier default: 60).
        nvidia_nim_retry_base_delay: Base delay (seconds) for exponential backoff.
        nvidia_nim_retry_max_delay: Maximum delay (seconds) between retries.
        nvidia_nim_embedding_model: Default embedding model identifier.
        nvidia_nim_rerank_model: Default reranking model identifier.
    """

    model_config = SettingsConfigDict(
        env_prefix="QNAI_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API authentication
    nvidia_nim_api_key: Optional[str] = None
    nvidia_nim_base_url: str = "https://integrate.api.nvidia.com/v1"

    # Model defaults
    nvidia_nim_default_model: str = "meta/llama-3.1-70b-instruct"
    nvidia_nim_max_tokens: int = 4096
    nvidia_nim_temperature: float = 0.1

    # Connection
    nvidia_nim_timeout: int = 60
    nvidia_nim_max_retries: int = 3

    # Rate limiting
    nvidia_nim_rate_limit: int = 60  # requests per minute (free tier)

    # Retry backoff
    nvidia_nim_retry_base_delay: float = 1.0
    nvidia_nim_retry_max_delay: float = 30.0

    # Specialized models
    nvidia_nim_embedding_model: str = "nvidia/nv-embedqa-e5-v5"
    nvidia_nim_rerank_model: str = "nvidia/nv-rerankqa-mistral-4b-v3"


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_nim_config: NIMConfig | None = None


def get_nim_config() -> NIMConfig:
    """Return a cached NIMConfig instance.

    The instance is created on first call and reused thereafter.
    To force a refresh (e.g. after updating env vars), call ``reset_nim_config()``.
    """
    global _nim_config
    if _nim_config is None:
        _nim_config = NIMConfig()
    return _nim_config


def reset_nim_config() -> None:
    """Reset the cached NIMConfig so the next ``get_nim_config()`` call creates a fresh one."""
    global _nim_config
    _nim_config = None


__all__ = ["NIMConfig", "get_nim_config", "reset_nim_config"]
