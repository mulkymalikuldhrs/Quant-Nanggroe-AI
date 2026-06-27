# agents.forex.tools

## Function: 

Lazy-load MarketDataTool for real price data.

*Line: 35*

---

## Function: 

Lazy-load MacroAnalysisEngine from engine.screener.

*Line: 45*

---

## Function: 

*Line: 57*

---

## Function: 

*Line: 78*

---

## Function: 

*Line: 103*

---

## Function: 

Fetch forex market data for a currency pair.

PRODUCTION: Uses MarketDataTool for real forex price data via yfinance.
Falls back to mock data only in _MOCK_MODE.

Args:
    pair: Currency pair (e.g., EURUSD, GBPUSD, USDJPY)
    timeframe: Chart timeframe
    lookback_days: Number of days to look back

Returns:
    JSON string with forex data

*Line: 135*

---

## Function: 

Analyze carry trade opportunity between two currencies.

PRODUCTION: Uses real interest rate data from FRED/central bank sources
when available. Falls back to known rates otherwise.
Falls back to mock data only in _MOCK_MODE.

Args:
    base_currency: Base currency (borrowed)
    quote_currency: Quote currency (invested)
    account_size: Account size in USD

Returns:
    JSON string with carry trade analysis

*Line: 248*

---

## Function: 

Monitor central bank policy and upcoming meetings.

PRODUCTION: Uses MacroAnalysisEngine for real central bank data.
Falls back to mock data only in _MOCK_MODE.

Args:
    central_bank: Central bank code (FED, ECB, BOJ, BOE, RBA, BOC, SNB, RBNZ)
    upcoming_only: Only show upcoming meetings/events

Returns:
    JSON string with central bank monitoring data

*Line: 320*

---

## Function: 

No-op fallback when langchain_core is not installed.

*Line: 19*

---

## Function: 

*Line: 23*

---

