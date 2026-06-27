# engine.backtest.monte_carlo

## Class: 

Result from Monte Carlo simulation.

*Line: 30*

---

## Class: 

Monte Carlo results across multiple metrics.

*Line: 48*

---

## Class: 

Information about a market regime segment.

*Line: 57*

---

## Class: 

Monte Carlo simulation for backtest confidence intervals.

Provides robust estimates of strategy performance by resampling
trade returns or equity curve returns thousands of times.

Supports:
- Trade shuffle simulation
- Bootstrap resampling (non-parametric)
- Parametric simulation (fitted distribution)
- Regime-aware simulation
- Multi-metric confidence intervals
- Price path simulation

Usage:
    simulator = MonteCarloSimulator(num_simulations=1000)
    result = simulator.simulate_trade_shuffle(trades, initial_capital)
    result = simulator.simulate_bootstrap(returns, initial_capital)
    result = simulator.simulate_parametric(returns, initial_capital)

**Methods:** __init__, simulate_trade_shuffle, simulate_bootstrap, simulate_return_resample, simulate_parametric, simulate_regime_aware, simulate_price_path, simulate_multi_metric, _calc_metric, _calc_equity_metric, compute_confidence_intervals, _detect_regimes, _estimate_transition_matrix, _block_bootstrap, _build_result, _empty_result

*Line: 67*

---

## Function: 

Initialize Monte Carlo simulator.

Args:
    num_simulations: Number of Monte Carlo simulations to run.
    random_seed: Optional seed for reproducibility.
    confidence_levels: List of confidence levels for CIs (default: [0.90, 0.95, 0.99]).

*Line: 88*

---

## Function: 

Simulate by shuffling trade P&L sequence.

Tests whether the strategy's performance depends on the
specific sequence of trades (it shouldn't for a robust strategy).

Args:
    trades_pnl: List of trade P&L values.
    initial_capital: Starting capital.
    metric: Metric to compute ('total_return', 'max_drawdown', 'sharpe',
           'sortino', 'calmar', 'win_rate').

Returns:
    MonteCarloResult with confidence intervals.

*Line: 105*

---

## Function: 

Simulate using bootstrap resampling (non-parametric).

Resamples returns with replacement to create alternative
equity paths. Supports block bootstrap for autocorrelated returns.

Args:
    returns: Series of per-bar returns.
    initial_capital: Starting capital.
    metric: Metric to compute.
    block_size: Optional block size for block bootstrap.
               If None, uses standard bootstrap (block_size=1).

Returns:
    MonteCarloResult with confidence intervals.

*Line: 142*

---

## Function: 

Simulate by bootstrap resampling returns.

This is an alias for simulate_bootstrap with block_size=None.

Args:
    returns: Series of per-bar returns.
    initial_capital: Starting capital.
    metric: Metric to compute.

Returns:
    MonteCarloResult with confidence intervals.

*Line: 200*

---

## Function: 

Simulate using parametric distribution fitting.

Fits a distribution to the returns and generates random paths
from the fitted distribution. Supports normal, student-t, and
skewed-normal distributions.

Args:
    returns: Series of per-bar returns to fit.
    initial_capital: Starting capital.
    metric: Metric to compute.
    distribution: Distribution type ('normal', 'student_t', 'skew_normal').
    n_bars: Number of bars per simulation. Defaults to length of returns.

Returns:
    MonteCarloResult with confidence intervals.

*Line: 220*

---

## Function: 

Simulate with regime-awareness.

Detects market regimes (e.g., bull/bear, high/low volatility)
and generates returns that respect regime transitions.

Args:
    returns: Series of per-bar returns.
    initial_capital: Starting capital.
    metric: Metric to compute.
    n_regimes: Number of regimes to detect.
    n_bars: Number of bars per simulation. Defaults to length of returns.

Returns:
    MonteCarloResult with confidence intervals.

*Line: 325*

---

## Function: 

Simulate by generating random price paths from a normal distribution.

Args:
    mean_return: Mean per-bar return.
    std_return: Std of per-bar returns.
    n_bars: Number of bars per simulation.
    initial_capital: Starting capital.
    metric: Metric to compute.

Returns:
    MonteCarloResult with confidence intervals.

*Line: 407*

---

## Function: 

Run Monte Carlo simulation for multiple metrics simultaneously.

Args:
    returns: Series of per-bar returns.
    initial_capital: Starting capital.
    metrics: List of metrics to compute. Defaults to all supported.
    method: Simulation method ('bootstrap', 'parametric', 'regime_aware').

Returns:
    MultiMetricMonteCarloResult with results for each metric.

*Line: 442*

---

## Function: 

Calculate a metric from a P&L array.

*Line: 489*

---

## Function: 

Calculate a metric from an equity curve.

*Line: 530*

---

## Function: 

Compute confidence intervals at specified levels.

Args:
    values: Array of simulated metric values.

Returns:
    Dict mapping confidence level to (lower, upper) bounds.

*Line: 574*

---

## Function: 

Detect market regimes using rolling volatility clustering.

Uses k-means-like clustering on rolling volatility to identify
distinct market regimes.

Args:
    returns: Array of per-bar returns.
    n_regimes: Number of regimes to detect.
    window: Rolling window for volatility calculation.

Returns:
    Array of regime labels (0 to n_regimes-1) for each bar.

*Line: 597*

---

## Function: 

Estimate Markov transition matrix from regime sequence.

Args:
    regimes: Array of regime labels.
    n_regimes: Number of regimes.

Returns:
    Transition probability matrix (n_regimes x n_regimes).

*Line: 646*

---

## Function: 

Generate a block bootstrap resample.

Args:
    rng: Random number generator.
    data: Original data array.
    block_size: Size of each block.
    total_length: Desired length of resample.

Returns:
    Resampled array of specified length.

*Line: 681*

---

## Function: 

Build MonteCarloResult from simulation results.

*Line: 709*

---

## Function: 

Return empty MonteCarloResult when no data is available.

*Line: 740*

---

