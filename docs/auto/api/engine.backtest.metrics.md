# engine.backtest.metrics

## Class: 

Container for all performance metrics.

*Line: 35*

---

## Class: 

Comprehensive performance metrics calculator.

Supports annualisation for different markets (252 for equities, 365 for crypto),
benchmark comparison, and risk-adjusted return metrics.

All ratios are properly annualized:
- Sharpe: (mean_return / std) * sqrt(bars_per_year)
- Sortino: (mean_return / downside_std) * sqrt(bars_per_year)
- Calmar: CAGR / abs(max_drawdown)
- Volatility: std * sqrt(bars_per_year)

**Methods:** __init__, calculate, _trade_statistics, _calc_max_drawdown_duration, _calc_ulcer_index, _empty_metrics, calc_bars_per_year

*Line: 65*

---

## Function: 

*Line: 78*

---

## Function: 

Calculate full set of performance metrics.

Args:
    equity_series: Equity curve (index=timestamp, values=equity).
    trades: List of completed trade records.
    initial_capital: Starting capital.
    benchmark_returns: Optional benchmark return series.

Returns:
    Dict of metric name -> value.

*Line: 81*

---

## Function: 

Calculate trade-level statistics.

Args:
    trades: List of completed trade records.

Returns:
    Dict of trade statistics.

*Line: 209*

---

## Function: 

Calculate maximum drawdown duration in bars.

The drawdown duration is the number of bars from a peak
until the equity recovers to or exceeds that peak.

Args:
    equity_series: Equity curve.

Returns:
    Maximum drawdown duration in bars.

*Line: 275*

---

## Function: 

Calculate the Ulcer Index.

The Ulcer Index measures the depth and duration of drawdowns:
UI = sqrt(mean(drawdown^2))

Args:
    drawdown: Drawdown series (negative values).

Returns:
    Ulcer Index value.

*Line: 310*

---

## Function: 

Return zero-valued metrics when no data is available.

*Line: 328*

---

## Function: 

Calculate bars per year for annualisation.

Args:
    interval: Bar size (1m, 5m, 15m, 30m, 1H, 4H, 1D).
    market: Market type (equity, crypto, forex, futures).

Returns:
    Number of bars per year.

*Line: 346*

---

