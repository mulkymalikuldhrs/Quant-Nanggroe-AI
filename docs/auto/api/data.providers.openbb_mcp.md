# data.providers.openbb_mcp

## Class: 

*Line: 22*

---

## Class: 

OpenBB MCP-based market data provider.

Fetches OHLCV data via the OpenBB platform. Tries the OpenBB
Python SDK first; falls back to the OpenBB Hub REST API.

Parameters
----------
api_key:
    OpenBB personal access token. Falls back to
    ``OPENBB_API_KEY`` or ``QNAI_OPENBB_API_KEY`` env vars.
base_url:
    OpenBB Hub API base URL.

**Methods:** __init__, _get_cache, _set_cache, _init_sdk, fetch_ohlcv, _timeframe_to_interval, _fetch_via_sdk, _fetch_via_rest

*Line: 27*

---

## Function: 

*Line: 45*

---

## Function: 

*Line: 60*

---

## Function: 

*Line: 69*

---

## Function: 

Try to initialise the OpenBB Python SDK.

*Line: 79*

---

## Function: 

Fetch OHLCV market data.

Parameters
----------
symbol:
    Ticker symbol, *e.g.* ``"AAPL"``.
timeframe:
    Candle resolution string (*e.g.* ``"D1"``, ``"H1"``, ``"M1"``).
start:
    Start datetime (inclusive).
end:
    End datetime (inclusive).

Returns
-------
pd.DataFrame
    Columns: ``timestamp``, ``open``, ``high``, ``low``,
    ``close``, ``volume``.  Empty DataFrame on error or no data.

*Line: 103*

---

## Function: 

*Line: 152*

---

## Function: 

Fetch data via the OpenBB Python SDK.

*Line: 162*

---

## Function: 

Fetch data via the OpenBB Hub REST API.

*Line: 193*

---

