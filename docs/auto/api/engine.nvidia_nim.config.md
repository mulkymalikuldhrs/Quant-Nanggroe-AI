# engine.nvidia_nim.config

## Class: 

NVIDIA NIM connection and behaviour settings.

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

*Line: 14*

---

## Function: 

Return a cached NIMConfig instance.

The instance is created on first call and reused thereafter.
To force a refresh (e.g. after updating env vars), call ``reset_nim_config()``.

*Line: 75*

---

## Function: 

Reset the cached NIMConfig so the next ``get_nim_config()`` call creates a fresh one.

*Line: 87*

---

