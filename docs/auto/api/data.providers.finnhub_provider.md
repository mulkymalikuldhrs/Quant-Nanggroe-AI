# data.providers.finnhub_provider

## Class: 

Token bucket rate limiter (class-level, shared across instances).

**Methods:** __init__, _refill

*Line: 23*

---

## Class: 

*Line: 50*

---

## Class: 

Stock & market data provider using the Finnhub REST API.

Rate-limited to 60 calls/minute (free tier). Responses are cached
in-memory with configurable TTL (default 300 s). Failed requests
are retried up to 3 times with exponential backoff.

**Methods:** __init__, _http, _get_cache, _set_cache

*Line: 55*

---

## Function: 

*Line: 26*

---

## Function: 

*Line: 42*

---

## Function: 

*Line: 70*

---

## Function: 

*Line: 79*

---

## Function: 

*Line: 88*

---

## Function: 

*Line: 97*

---

