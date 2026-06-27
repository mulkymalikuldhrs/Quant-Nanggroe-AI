# data.providers.macro_provider

## Class: 

*Line: 26*

---

## Class: 

Simple token bucket rate limiter (class-level, shared across instances).

**Methods:** __init__, _refill

*Line: 31*

---

## Class: 

Macro-economic data provider via the FRED API.

Fetches US economic indicators (GDP, CPI, unemployment, federal funds rate,
treasury yields) from the Federal Reserve Economic Data API.

The API key is read from the ``QNAI_FRED_API_KEY`` environment variable.

Rate-limited to 120 calls/minute (FRED free tier limit) using a shared
token bucket. Responses are cached in-memory with a default TTL of 3600s.

Usage::

    provider = MacroProvider()
    gdp = await provider.get_gdp()
    cpi = await provider.get_inflation()
    unemp = await provider.get_unemployment()
    await provider.close()

**Methods:** __init__, _http, _get_cache, _set_cache, _parse_observations

*Line: 58*

---

## Function: 

*Line: 34*

---

## Function: 

*Line: 51*

---

## Function: 

*Line: 85*

---

## Function: 

*Line: 97*

---

## Function: 

*Line: 106*

---

## Function: 

*Line: 115*

---

## Function: 

Parse FRED API JSON response into a (date, value) DataFrame.

Filters out observations where the value is ``"."``  (FRED's
sentinel for missing data).

*Line: 303*

---

