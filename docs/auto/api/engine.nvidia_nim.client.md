# engine.nvidia_nim.client

## Class: 

Raised when the NIM rate limit is exceeded.

*Line: 79*

---

## Class: 

Raised when the NIM API returns an error response.

**Methods:** __init__

*Line: 83*

---

## Class: 

Async HTTP client for NVIDIA NIM inference microservices.

Supports chat completions (standard and streaming), embeddings,
reranking, health checks, and model listing.  Includes automatic
retry with exponential backoff and per-minute rate limiting.

Args:
    config: Optional NIMConfig instance.  If not provided, the
        global config from ``get_nim_config()`` is used.

Raises:
    ValueError: If the API key is not configured.

**Methods:** __init__, circuit_breaker, _check_rate_limit, _record_request, _cb_record_success, _cb_record_failure, estimate_cost, estimate_token_count, _parse_chat_response, _parse_stream_chunk, _parse_embedding_response, _parse_rerank_response

*Line: 92*

---

## Function: 

*Line: 86*

---

## Function: 

*Line: 107*

---

## Function: 

Access the circuit breaker for introspection or manual reset.

*Line: 129*

---

## Function: 

Enforce per-minute rate limit; raise if exceeded.

*Line: 177*

---

## Function: 

Record a request timestamp for rate-limit tracking.

*Line: 192*

---

## Function: 

Record a successful API call with the circuit breaker.

*Line: 314*

---

## Function: 

Record a failed API call with the circuit breaker.

*Line: 318*

---

## Function: 

Estimate the USD cost for a NIM API call.

Uses the built-in cost table.  Unknown models fall back to
the ``__default__`` rate.

Args:
    model: NIM model identifier.
    input_tokens: Number of input tokens consumed.
    output_tokens: Number of output tokens generated.

Returns:
    Estimated cost in USD.

*Line: 327*

---

## Function: 

Estimate token count for a text string.

Uses a simple heuristic of ~4 characters per token, which is
a reasonable approximation for English text with the BPE
tokenisers used by most NIM models.

Args:
    text: Input text.

Returns:
    Estimated token count.

*Line: 351*

---

## Function: 

Parse a chat completion JSON response into NIMChatResponse.

*Line: 787*

---

## Function: 

Parse a single SSE stream chunk into NIMStreamChunk.

*Line: 836*

---

## Function: 

Parse an embedding JSON response.

*Line: 872*

---

## Function: 

Parse a reranking JSON response.

*Line: 904*

---

