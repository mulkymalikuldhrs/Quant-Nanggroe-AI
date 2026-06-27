# agents.strategist.tools

## Function: 

Lazy-load TechnicalAnalysisTool from shared tools.

*Line: 37*

---

## Function: 

Lazy-load BacktestTool from shared tools.

*Line: 49*

---

## Function: 

Lazy-load PressureEngine from engine module.

*Line: 61*

---

## Function: 

Lazy-load DecisionEngine from engine module.

*Line: 71*

---

## Function: 

Return mock indicator data with a WARNING.

*Line: 83*

---

## Function: 

Return mock backtest data with a WARNING.

*Line: 111*

---

## Function: 

Return mock strategy evaluation with a WARNING.

*Line: 132*

---

## Function: 

Compute technical indicators for a symbol.

PRODUCTION: Uses TechnicalAnalysisTool from shared tools for real
indicator calculations. Falls back to mock data only in _MOCK_MODE.

Args:
    symbol: Trading symbol
    indicators: List of indicators to compute (RSI, MACD, BB, SMA, EMA, ATR, ADX, STOCH)
    timeframe: Chart timeframe (1m, 5m, 15m, 1H, 4H, 1D, 1W)

Returns:
    JSON string with computed indicator values

*Line: 155*

---

## Function: 

Run a backtest for a given symbol and strategy.

PRODUCTION: Uses BacktestTool from shared tools for real backtesting.
Falls back to mock data only in _MOCK_MODE.

Args:
    symbol: Trading symbol
    strategy: Strategy name/description
    period_days: Backtest period in days
    initial_capital: Starting capital

Returns:
    JSON string with backtest results

*Line: 214*

---

## Function: 

Evaluate a trading strategy's historical performance.

PRODUCTION: Uses PressureEngine + DecisionEngine for real evaluation.
Falls back to mock data only in _MOCK_MODE.

Args:
    strategy_name: Name of the strategy to evaluate
    metrics: Specific metrics to evaluate

Returns:
    JSON string with strategy evaluation

*Line: 276*

---

## Function: 

No-op fallback when langchain_core is not installed.

*Line: 19*

---

## Function: 

*Line: 23*

---

