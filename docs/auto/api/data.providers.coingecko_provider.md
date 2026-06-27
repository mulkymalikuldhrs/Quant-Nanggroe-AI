# data.providers.coingecko_provider

## Class: 

Simple token bucket rate limiter (class-level, shared).

**Methods:** __init__, _refill

*Line: 21*

---

## Class: 

*Line: 49*

---

## Class: 

Cryptocurrency market data provider using CoinGecko public API.

Rate-limited to 20 calls/minute with a token bucket.
Caches price data for 300s and coin list for 3600s.
Retries failed requests up to 3 times with exponential backoff.

**Methods:** __init__, _http, _get_cache, _set_cache

*Line: 54*

---

## Function: 

*Line: 24*

---

## Function: 

*Line: 41*

---

## Function: 

*Line: 68*

---

## Function: 

*Line: 76*

---

## Function: 

*Line: 83*

---

## Function: 

*Line: 92*

---

