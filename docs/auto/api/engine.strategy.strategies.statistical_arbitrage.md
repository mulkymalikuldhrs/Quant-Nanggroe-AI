# engine.strategy.strategies.statistical_arbitrage

## Class: 

Statistical arbitrage via PCA factor model and residual mean reversion.

Builds a universe of stocks, extracts common risk factors via PCA on
standardized returns, and trades stocks whose residual returns deviate
significantly from zero. The systematic factor exposure is hedged out,
leaving only the idiosyncratic (orphan) alpha to trade.

Parameters:
    lookback: Rolling window for PCA estimation (default 60).
    n_factors: Number of PCA factors to extract (default 3).
    entry_threshold: Z-score threshold to enter (default 2.0).
    exit_threshold: Z-score threshold to exit (default 0.5).
    return_lookback: Period for multi-period return computation (default 20).
    universe_size: Maximum number of stocks in the universe (default 20).
    transaction_cost_bps: Estimated transaction cost in basis points (default 10.0).
    min_trade_interval_bars: Minimum bars between trades (default 10).
    symbol: Primary trading symbol (default "ASSET").

**Methods:** __init__, required_columns, warmup_period, _compute_pca, _select_universe, generate_signal

*Line: 34*

---

## Function: 

*Line: 54*

---

## Function: 

*Line: 70*

---

## Function: 

*Line: 73*

---

## Function: 

PCA via SVD. Returns (factor_returns, factor_loadings).

Args:
    returns_matrix: Centered returns, shape (T, N).
    n_components: Number of principal components.

Returns:
    Tuple of (factors, loadings) where factors is (T, K)
    and loadings is (N, K).

*Line: 77*

---

## Function: 

Select the top stocks by average price for the trading universe.

*Line: 94*

---

## Function: 

Generate statistical arbitrage signal from PCA residuals.

Expects data["close"] to be a DataFrame with one column per stock
in the universe. Computes cross-sectional returns, runs PCA, and
trades the primary symbol's residual z-score.

Signal value (stored in evidence) ranges from -1.0 (short) to
+1.0 (long), with 0.0 meaning flat / no position.

Args:
    data: DataFrame with 'close' column (DataFrame of stock prices).

Returns:
    Signal if entry/exit condition met, None otherwise.

*Line: 100*

---

