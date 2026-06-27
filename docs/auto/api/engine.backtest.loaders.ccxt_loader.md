# engine.backtest.loaders.ccxt_loader

## Class: 

CCXT-backed crypto OHLCV loader (100+ exchanges).

Uses the CCXT library to fetch OHLCV candles from any supported
exchange. Defaults to Binance; configurable via ``CCXT_EXCHANGE``
environment variable.

No API key required for public market data.

Environment variables:
  - ``CCXT_EXCHANGE``: Exchange to use (default: ``binance``).
  - ``CCXT_TIMEOUT_MS``: HTTP request timeout in ms (default: 15000).
  - ``CCXT_FETCH_BUDGET_S``: Wall-clock budget per symbol in seconds (default: 60).

**Methods:** is_available, _get_exchange, fetch, _fetch_one

*Line: 45*

---

## Function: 

Available if ccxt is installed.

*Line: 64*

---

## Function: 

Create exchange instance.

Returns:
    CCXT exchange instance.

Raises:
    ImportError: If ccxt is not installed.

*Line: 73*

---

## Function: 

Fetch crypto OHLCV via CCXT.

Args:
    codes: Symbols like ``["BTC-USDT", "ETH-USDT"]``.
    start_date: Start date (YYYY-MM-DD).
    end_date: End date (YYYY-MM-DD).
    interval: Bar size (1m/5m/15m/30m/1H/4H/1D).
    fields: Ignored.

Returns:
    Mapping symbol -> OHLCV DataFrame.

*Line: 93*

---

## Function: 

Paginated OHLCV fetch for one symbol.

Uses bounded retry with wall-clock budget to handle flaky API calls.

Args:
    exchange: CCXT exchange instance.
    symbol: Trading pair symbol (e.g. ``BTC/USDT``).
    timeframe: Candle timeframe string.
    since_ms: Start timestamp in milliseconds.
    end_ms: End timestamp in milliseconds.

Returns:
    OHLCV DataFrame or None if no data.

*Line: 145*

---

