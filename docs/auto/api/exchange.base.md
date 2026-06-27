# exchange.base

## Class: 

Base exception for all exchange-related errors.

All concrete exchange errors inherit from this class so callers can
catch broadly or narrowly as needed.

**Methods:** __init__

*Line: 41*

---

## Class: 

Failed to connect, or connection was lost.

*Line: 54*

---

## Class: 

Order submission, cancellation, or validation failed.

**Methods:** __init__

*Line: 58*

---

## Class: 

Exchange rate-limit was hit.

Carries ``retry_after`` seconds when the exchange provides a hint.

**Methods:** __init__

*Line: 72*

---

## Class: 

API key / secret authentication failed.

*Line: 88*

---

## Class: 

Not enough balance to complete the requested operation.

*Line: 92*

---

## Class: 

Market data request failed or returned invalid data.

*Line: 96*

---

## Class: 

Configuration for an exchange connection.

Attributes:
    exchange_id: Unique identifier for this connection (e.g. ``"binance"``).
    api_key: Exchange API key.
    api_secret: Exchange API secret.
    passphrase: Optional passphrase (OKX, KuCoin).
    sandbox: Use sandbox/testnet mode.
    rate_limit: Maximum requests per second.
    timeout: HTTP request timeout in seconds.
    retries: Number of retries on transient errors.
    retry_delay: Base delay between retries (exponential backoff).
    options: Exchange-specific CCXT options dict.

*Line: 104*

---

## Class: 

Lifecycle state of an exchange connection.

*Line: 138*

---

## Class: 

Abstract exchange interface — unified across all brokers.

Every exchange implementation **must** implement all abstract methods.
The interface covers:

* **Connection lifecycle** — connect, disconnect, health checks
* **Account** — balance, positions, portfolio sync
* **Trading** — place / cancel / query orders
* **Market data** — OHLCV, tickers, order books, trades
* **Real-time** — WebSocket subscribe / unsubscribe
* **Position tracking** — local position book with P&L

Design principles
-----------------
* All methods are ``async`` — no blocking calls.
* Methods return Pydantic models from ``quant_nanggroe.types``.
* Errors are raised as typed exceptions (see error hierarchy above).
* Rate limiting and retries are built into implementations, not the caller.

**Methods:** is_connected, state, name

*Line: 162*

---

## Function: 

*Line: 48*

---

## Function: 

*Line: 61*

---

## Function: 

*Line: 78*

---

## Function: 

Whether the exchange is currently connected.

*Line: 202*

---

## Function: 

Current lifecycle state of the connection.

*Line: 207*

---

## Function: 

Human-readable exchange identifier (e.g. ``"binance"``).

*Line: 212*

---

