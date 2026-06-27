# data.providers.crypto_provider

## Function: 

Parse ISO datetime string to millisecond timestamp (CCXT convention).

*Line: 31*

---

## Class: 

Multi-exchange crypto market data provider with auto-failover.

Tries Bybit first, then OKX, then Kraken. Uses CCXT for exchange
communication and handles rate limiting + retry internally.

Parameters
----------
api_keys:
    Optional dict mapping exchange name to its API credentials.
    Public endpoints work without keys (rate-limited).

**Methods:** __init__, _build_exchange_config, _get_exchange, _get_async_exchange, fetch_ohlcv_sync, get_exchanges

*Line: 43*

---

## Function: 

*Line: 56*

---

## Function: 

Build CCXT config dict, injecting API keys if provided.

*Line: 67*

---

## Function: 

Get or create a synchronous CCXT exchange instance.

*Line: 80*

---

## Function: 

Get or create an async CCXT exchange instance.

*Line: 91*

---

## Function: 

Synchronous convenience wrapper around :meth:`fetch_ohlcv`.

Handles both running-event-loop and no-loop environments.

*Line: 238*

---

## Function: 

Return list of configured exchange names in priority order.

*Line: 265*

---

