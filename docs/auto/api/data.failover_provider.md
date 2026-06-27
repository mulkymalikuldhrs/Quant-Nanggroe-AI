# data.failover_provider

## Class: 

All registered providers failed to return data.

**Methods:** __init__

*Line: 42*

---

## Class: 

**Methods:** __init__, is_cooling

*Line: 55*

---

## Class: 

**Methods:** __init__, record_failure, record_success, is_open

*Line: 78*

---

## Class: 

Wraps multiple data providers. On failure, falls through to next.

Each provider must expose a ``fetch_ohlcv(symbol, days, interval)``
method. Providers are tried in order. If one raises an exception,
the next is tried. After 3 consecutive failures, a provider enters
a 60-second cooldown before being retried.

If CircuitBreaker is available (``quant_nanggroe.engine.core.circuit_breaker``),
each provider is wrapped in its own circuit breaker. Otherwise a
lightweight 10-line fallback breaker is used.

Args:
    providers: List of provider instances with ``fetch_ohlcv``.
    state_path: Optional path to JSON file for state persistence.

**Methods:** __init__, fetch_ohlcv, get_status, _cb_allow, _save_state, _load_state

*Line: 102*

---

## Function: 

*Line: 45*

---

## Function: 

*Line: 61*

---

## Function: 

*Line: 71*

---

## Function: 

*Line: 81*

---

## Function: 

*Line: 85*

---

## Function: 

*Line: 90*

---

## Function: 

*Line: 95*

---

## Function: 

*Line: 119*

---

## Function: 

Fetch OHLCV data with automatic failover.

Args:
    symbol: Trading pair or ticker symbol.
    days: Number of days of historical data.
    interval: Candle interval (e.g. ``"1h"``, ``"1d"``).

Returns:
    Data from the first successful provider.

Raises:
    AllProvidersFailedError: If every provider failed.

*Line: 151*

---

## Function: 

Return current failover provider status.

*Line: 221*

---

## Function: 

*Line: 260*

---

## Function: 

*Line: 269*

---

## Function: 

*Line: 286*

---

