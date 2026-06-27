# engine.backtest.benchmarks

## Class: 

Result from benchmark comparison.

*Line: 17*

---

## Class: 

Manages benchmark data for backtest comparison.

Provides methods for:
- Resolving benchmark tickers from strategy symbols
- Computing benchmark return series
- Comparing strategy vs benchmark performance

**Methods:** resolve_benchmark, compute_benchmark_returns, compare

*Line: 35*

---

## Function: 

Resolve benchmark ticker.

Args:
    strategy_codes: List of strategy instrument codes.
    market: Market type.
    explicit: Explicit benchmark ticker override.

Returns:
    Benchmark ticker string.

*Line: 45*

---

## Function: 

Compute benchmark return series from price data.

Args:
    prices: Benchmark price series.

Returns:
    BenchmarkResult with returns and total return.

*Line: 65*

---

## Function: 

Compare strategy vs benchmark performance.

Args:
    strategy_returns: Strategy per-bar returns.
    benchmark_returns: Benchmark per-bar returns.
    risk_free_rate: Annual risk-free rate.
    bars_per_year: Bars per year for annualisation.

Returns:
    Dict of comparison metrics.

*Line: 85*

---

