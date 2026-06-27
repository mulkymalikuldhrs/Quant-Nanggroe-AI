# engine.backtest.loaders.yfinance_loader

## Function: 

Convert project symbols into yfinance symbols.

Args:
    code: Project symbol, e.g. ``AAPL.US`` or ``700.HK``.

Returns:
    yfinance-compatible symbol.

*Line: 46*

---

## Function: 

Map project interval strings to yfinance interval strings.

Args:
    interval: Backtest interval such as ``1D`` or ``5m``.

Returns:
    yfinance interval string.

*Line: 65*

---

## Function: 

Download raw historical data via yfinance.

Args:
    tickers: One or more yfinance symbols.
    start_date: Inclusive start date string.
    end_date: End date string passed directly to yfinance.
    interval: yfinance interval string.

Returns:
    Raw dataframe from ``yf.download``.

*Line: 78*

---

## Function: 

Flatten any leftover multi-index columns after symbol selection.

Args:
    frame: Price dataframe.
    symbol: yfinance symbol used for column cleanup.

Returns:
    Dataframe with flat string columns.

*Line: 114*

---

## Function: 

Extract a single symbol slice from a raw yfinance dataframe.

Args:
    frame: Raw dataframe returned by ``yf.download``.
    symbol: yfinance symbol to extract.
    total_symbols: Number of unique symbols requested.

Returns:
    A single-symbol dataframe or an empty dataframe when unavailable.

*Line: 138*

---

## Function: 

Normalize raw yfinance data into the backtest OHLCV schema.

Args:
    frame: Raw or symbol-scoped yfinance dataframe.
    requested_interval: Original backtest interval.

Returns:
    Normalized OHLCV dataframe indexed by ``trade_date``.

*Line: 166*

---

## Class: 

Fetch HK/US equity bars from Yahoo Finance via yfinance.

No API key required. Supports US and HK equities.

**Methods:** is_available, fetch

*Line: 217*

---

## Function: 

Always available (free public data, no auth).

*Line: 227*

---

## Function: 

Fetch OHLCV history keyed by the original project symbols.

Args:
    codes: Project symbols such as ``AAPL.US`` and ``700.HK``.
    start_date: Start date in ``YYYY-MM-DD`` format.
    end_date: End date in ``YYYY-MM-DD`` format.
    interval: Backtest interval such as ``1D`` or ``1H``.
    fields: Ignored for yfinance; included for interface compatibility.

Returns:
    Mapping of input symbol to normalized OHLCV dataframe.

*Line: 231*

---

