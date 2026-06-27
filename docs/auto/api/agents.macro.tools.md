# agents.macro.tools

## Function: 

Lazy-load MarketStateEngine from engine.market_state.

*Line: 36*

---

## Function: 

Lazy-load CorrelationMonitor from engine.risk.correlation.

*Line: 46*

---

## Function: 

Lazy-load MarketDataTool for real price data.

*Line: 56*

---

## Function: 

*Line: 68*

---

## Function: 

*Line: 95*

---

## Function: 

*Line: 124*

---

## Function: 

Fetch macroeconomic data and indicators.

PRODUCTION: Uses MarketDataTool for real market data (VIX, DXY, yields)
and FRED API for macro indicators when API key is configured.
Falls back to mock data only in _MOCK_MODE.

Args:
    indicators: Specific indicators to fetch (GDP, CPI, NFP, FFR, PMI, YIELD)
    region: Geographic region (US, EU, JP, CN, GLOBAL)

Returns:
    JSON string with macro data

*Line: 151*

---

## Function: 

Detect the current market regime based on macro indicators.

PRODUCTION: Uses MarketStateEngine for real regime classification
with multi-timeframe analysis and NO_TRADE detection.
Falls back to in-file calculation if engine unavailable.

Args:
    equity_trend: Equity market trend (rising, falling, neutral)
    bond_yields_trend: Bond yields trend (rising, falling, stable)
    vix_level: Current VIX level
    credit_spread: Current credit spread (percentage)

Returns:
    JSON string with regime classification

*Line: 262*

---

## Function: 

Analyze intermarket correlations between symbols.

PRODUCTION: Uses CorrelationMonitor for real rolling correlation
analysis with stress detection and regime change alerts.
Falls back to MarketDataTool for real price-based correlations.

Args:
    symbols: List of symbols to analyze
    lookback_days: Lookback period in days

Returns:
    JSON string with correlation analysis

*Line: 376*

---

## Function: 

No-op fallback for langchain_core.tools.tool when langchain_core is not installed.

*Line: 20*

---

## Function: 

*Line: 24*

---

