# agents.portfolio.tools

## Function: 

Lazy-load RiskParityOptimizer from engine.

*Line: 35*

---

## Function: 

Lazy-load MarketDataTool for real price data.

*Line: 45*

---

## Function: 

Optimize portfolio allocation using specified method.

PRODUCTION: Uses RiskParityOptimizer for real risk parity allocation
and MarketDataTool for real volatility estimation.
Falls back to mock data only in _MOCK_MODE.

Args:
    symbols: List of symbols to include
    expected_returns: Expected returns by symbol
    method: Optimization method (risk_parity, mean_variance, min_variance, max_sharpe)
    risk_free_rate: Risk-free rate for Sharpe calculation

Returns:
    JSON string with optimized allocation

*Line: 60*

---

## Function: 

Compute trades needed to reach target allocation.

This tool performs real arithmetic calculations (no mock data needed).
The logic is deterministic and was never mock — now annotated.

Args:
    current_positions: Current position values by symbol
    target_allocation: Target allocation weights by symbol (0-100%)
    total_value: Total portfolio value

Returns:
    JSON string with required trades

*Line: 224*

---

## Function: 

Determine if portfolio rebalancing is needed.

This tool performs real arithmetic calculations (no mock data needed).
The logic is deterministic and was never mock — now annotated.

Args:
    current_allocation: Current allocation weights by symbol
    target_allocation: Target allocation weights by symbol
    threshold_pct: Drift threshold to trigger rebalancing (default: 5%)

Returns:
    JSON string with rebalancing assessment

*Line: 269*

---

## Function: 

No-op fallback when langchain_core is not installed.

*Line: 19*

---

## Function: 

*Line: 23*

---

