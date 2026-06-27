# api.routes.backtest

## Function: 

Execute a backtest synchronously and store the results.

Uses the YFinanceLoader to fetch price data and the BacktestEngine
to run the simulation.  Results (metrics, equity curve, trades)
are stored in the module-level ``_backtests`` dict.

Args:
    backtest_id: Unique backtest identifier.
    request: The original BacktestRequest parameters.

*Line: 26*

---

