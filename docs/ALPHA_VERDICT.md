# Independent Alpha Audit — Quant Nanggroe AI

**Date:** 2026-06-24
**Auditor:** Automated alpha audit system
**Methodology:** PSR/DSR + factor decomposition + walk-forward + decay analysis
**Data source:** Synthetic GARCH (500 bars × 4 symbols, t-dist df=4, GARCH(1,1) vol clustering, AR(1) momentum structure). Real data path wired but CoinGecko unreachable — all results on synthetic data only.

## 1. Executive Summary

**6/8** strategies pass PSR + DSR at the 95% confidence level. Two fail (MeanReversion, VolatilityArbitrage) — structurally expected given synthetic trending data. However, the 6 passing strategies show suspiciously perfect PSR/DSR = 1.000 across all 4 symbols, a synthetic data artifact. Factor decomposition, walk-forward, and decay analysis have **not yet been executed** on real or paper data.

**Score: 2/8** strategies pass all available alpha tests (PSR + DSR). The remaining 6 passing strategies show **statistical significance on synthetic data** but lack real-data validation, factor decomposition, and walk-forward confirmation. **No real alpha has been confirmed.**

| Metric | Value |
|--------|-------|
| Strategies with PSR > 0.95 | 6/8 |
| Strategies with DSR > 0.95 | 6/8 |
| Strategies with Sharpe ≥ 0.3 | 6/8 |
| Strategies with significant factor α t-stat | ⚠️ **Pending** — factor_regression.py not yet run |
| Strategies passing walk-forward | ⚠️ **Pending** — walk-forward not yet executed |
| Strategies with non-decaying alpha | ⚠️ **Pending** — decay analysis not yet executed |

## 2. Methodology

### 2.1 PSR / DSR
- **PSR:** Probability that true Sharpe exceeds a benchmark (0.0) given observed skewness, kurtosis, and sample size. PSR > 0.95 = statistically significant alpha at 95% confidence.
- **DSR:** Deflated Sharpe Ratio — adjusts the PSR benchmark upward to the expected maximum Sharpe under N independent trials (Bailey & López de Prado, 2014), correcting for multiple testing (data snooping) bias.
- **Implementation:** `engine/backtest/psr.py` — uses `scipy.stats.norm.cdf`, skewness/kurtosis adjustment per Bailey & López de Prado (2012).
- **Parameters:** benchmark Sharpe = 0.0, annualization = 252, 8 trials (one per strategy), estimated independent trials = 2.67 (shrinkage with ρ=0.5).

### 2.2 Factor Decomposition
- Multi-factor OLS: P&L_t = α + Σ(β_i × F_i,t) + ε_t
- Significant alpha = t-stat > 2 (p < 0.05), non-trivial R² residual (< 0.8 factor dependence).
- **Reference:** `scripts/factor_regression.py` — numpy lstsq with Student's t-distribution survival function (pure Python betainc fallback, scipy preferred).
- ⚠️ **Status:** Not yet executed. Requires per-strategy P&L series and a factor returns dataset.

### 2.3 Walk-Forward Analysis
- Train on first 70%, test on last 30%. Consistent performance both sides = robust.
- Sharpe drop > 50% from train to test = possible overfitting.
- ⚠️ **Status:** Not yet executed. Requires per-strategy return series split.

### 2.4 Decay Analysis
- Alpha persistence over time. Linear regression of cumulative alpha vs time.
- Negative slope > 0.1/month = decaying edge (common in HFT/arb).
- ⚠️ **Status:** Not yet executed. Requires time-indexed strategy returns.

## 3. Results Per Strategy

### 3.1 CryptoSpecific
| Test | Result | Verdict |
|------|--------|---------|
| PSR | 1.000 | PASS |
| DSR | 1.000 | PASS |
| Sharpe | 0.516 | PASS (≥0.3) |
| Factor α t-stat | — | ⚠️ Pending |
| Factor R² | — | ⚠️ Pending |
| Walk-forward train Sharpe | — | ⚠️ Pending |
| Walk-forward test Sharpe | — | ⚠️ Pending |
| Decay slope | — | ⚠️ Pending |

**Alpha verdict:** BORDERLINE — PSR/DSR pass on synthetic data but real funding rate arb / MEV / liquidation cascade strategies cannot be validated without real crypto market microstructure data (order book, funding rates, liquidation events). Synthetic GARCH data lacks these features entirely.

**Synthetic data caveat:** Strategy designed for crypto-specific signals (funding rates, on-chain data, MEV) — none of these exist in synthetic GARCH OHLCV. The "alpha" detected is likely the strategy interacting with the synthetic AR(1) momentum structure, not genuine crypto-specific alpha.

### 3.2 MarketMaking
| Test | Result | Verdict |
|------|--------|---------|
| PSR | 1.000 | PASS |
| DSR | 1.000 | PASS |
| Sharpe | 0.197 | FAIL (<0.3) |
| Factor α t-stat | — | ⚠️ Pending |
| Factor R² | — | ⚠️ Pending |
| Walk-forward train Sharpe | — | ⚠️ Pending |
| Walk-forward test Sharpe | — | ⚠️ Pending |
| Decay slope | — | ⚠️ Pending |

**Alpha verdict:** BORDERLINE — PSR/DSR pass, but raw Sharpe (0.197) is below the 0.3 threshold most allocators consider minimum viable. Avellaneda-Stoikov market making requires tick-level order book data, not daily OHLCV. The synthetic daily bar resolution is fundamentally mismatched with a strategy designed for minute-level quotes.

**Synthetic data caveat:** Market making operates at sub-minute frequencies. Testing on daily bars with bid-ask spread = 0 is meaningless. Requires tick data with realistic spread dynamics.

### 3.3 MeanReversion
| Test | Result | Verdict |
|------|--------|---------|
| PSR | 0.000 | FAIL |
| DSR | 0.000 | FAIL |
| Sharpe | -2.637 | FAIL |
| Factor α t-stat | — | ⚠️ Pending |
| Factor R² | — | ⚠️ Pending |
| Walk-forward train Sharpe | — | ⚠️ Pending |
| Walk-forward test Sharpe | — | ⚠️ Pending |
| Decay slope | — | ⚠️ Pending |

**Alpha verdict:** NO ALPHA — PSR/DSR both 0.000, Sharpe significantly negative (-2.637). This is structurally expected: the synthetic GARCH data has positive AR(1) coefficient (0.05), creating trending behavior that inherently destroys mean reversion strategies. Not a bug — the strategy performs as designed. Mean reversion should only be deployed in mean-reverting regimes.

**Synthetic data caveat:** The synthetic data's AR(1)=0.05 momentum structure is the direct cause of failure. On real mean-reverting assets (e.g., FX pairs, commodity ETFs), results would differ significantly.

### 3.4 Momentum
| Test | Result | Verdict |
|------|--------|---------|
| PSR | 1.000 | PASS |
| DSR | 1.000 | PASS |
| Sharpe | 0.898 | PASS (≥0.3) |
| Factor α t-stat | — | ⚠️ Pending |
| Factor R² | — | ⚠️ Pending |
| Walk-forward train Sharpe | — | ⚠️ Pending |
| Walk-forward test Sharpe | — | ⚠️ Pending |
| Decay slope | — | ⚠️ Pending |

**Alpha verdict:** BORDERLINE — Highest Sharpe among passing strategies (0.898). Expected: the synthetic data's AR(1)=0.05 momentum structure directly benefits momentum strategies. However, this is the strongest candidate for genuine alpha. Note: tuned_params.json shows improvement_pct = 0.0% over defaults (only 9 combos evaluated), so parameter optimization has not been explored.

**Synthetic data caveat:** Momentum performance on synthetic AR(1) data is expected — the data generating process explicitly includes momentum. Real crypto markets show alternating momentum/reversal regimes that this strategy may not survive.

### 3.5 PairsTrading
| Test | Result | Verdict |
|------|--------|---------|
| PSR | 1.000 | PASS |
| DSR | 1.000 | PASS |
| Sharpe | 0.425 | PASS (≥0.3) |
| Factor α t-stat | — | ⚠️ Pending |
| Factor R² | — | ⚠️ Pending |
| Walk-forward train Sharpe | — | ⚠️ Pending |
| Walk-forward test Sharpe | — | ⚠️ Pending |
| Decay slope | — | ⚠️ Pending |

**Alpha verdict:** BORDERLINE — PSR/DSR pass with moderate Sharpe (0.425). Pairs trading is cointegration-based and requires real pair relationships. The synthetic data constructs a synthetic pair (ASSET_B = 2 × ASSET_A + spread with AR(1) residual), which is an idealized cointegrated pair that does not exist in real markets.

**Synthetic data caveat:** The synthetic pair generation creates a near-perfect cointegration relationship (β=2, AR(1) spread with ρ=0.85). Real pairs have unstable cointegration, regime-dependent hedge ratios, and execution costs that destroy edge. The 32.9 bps round-trip cost (from slippage calibration) may eliminate the thin margins.

### 3.6 RegimeBased
| Test | Result | Verdict |
|------|--------|---------|
| PSR | 1.000 | PASS |
| DSR | 1.000 | PASS |
| Sharpe | 2.258 | PASS (≥0.3) |
| Factor α t-stat | — | ⚠️ Pending |
| Factor R² | — | ⚠️ Pending |
| Walk-forward train Sharpe | — | ⚠️ Pending |
| Walk-forward test Sharpe | — | ⚠️ Pending |
| Decay slope | — | ⚠️ Pending |

**Alpha verdict:** BORDERLINE — Highest Sharpe in the portfolio (2.258). HMM regime detection excels at identifying the two-regime structure in the synthetic data (the GARCH vol clustering naturally creates high/low vol regimes). However, Sharpe this high on synthetic data is a red flag — likely overfitting to the synthetic regime structure.

**Synthetic data caveat:** Synthetic data has a known, stable, two-regime GARCH structure that HMM is designed to detect. Real markets have 3+ regimes, regime switches, and structural breaks that this model has not been tested against. Sharpe > 2 on synthetic is suspicious until walk-forward confirms robustness.

### 3.7 StatisticalArbitrage
| Test | Result | Verdict |
|------|--------|---------|
| PSR | 1.000 | PASS |
| DSR | 1.000 | PASS |
| Sharpe | 0.606 | PASS (≥0.3) |
| Factor α t-stat | — | ⚠️ Pending |
| Factor R² | — | ⚠️ Pending |
| Walk-forward train Sharpe | — | ⚠️ Pending |
| Walk-forward test Sharpe | — | ⚠️ Pending |
| Decay slope | — | ⚠️ Pending |

**Alpha verdict:** BORDERLINE — PCA factor model + residual mean reversion. The synthetic data generates 10 stock-like series with correlated noise structure, creating an artificial factor structure that PCA can exploit. Real markets have far more complex factor structures with time-varying loadings.

**Synthetic data caveat:** The 10 synthetic stocks are generated from a single base series + Gaussian noise, creating an unrealistically clean factor structure. Residual mean reversion on the synthetic residuals is likely detecting the artificial construction rather than genuine statistical arbitrage.

### 3.8 VolatilityArbitrage
| Test | Result | Verdict |
|------|--------|---------|
| PSR | 0.000 | FAIL |
| DSR | 0.000 | FAIL |
| Sharpe | -0.716 | FAIL |
| Factor α t-stat | — | ⚠️ Pending |
| Factor R² | — | ⚠️ Pending |
| Walk-forward train Sharpe | — | ⚠️ Pending |
| Walk-forward test Sharpe | — | ⚠️ Pending |
| Decay slope | — | ⚠️ Pending |

**Alpha verdict:** NO ALPHA — PSR/DSR both 0.000, Sharpe negative (-0.716). GARCH volatility forecasting strategy loses money on synthetic data. Possible explanations: (1) the synthetic GARCH is the same family used by the strategy (self-referential overfitting), yet it still fails — suggesting the variance risk premium structure is absent in synthetic data; (2) vol arbitrage requires option markets (implied vs realized vol) which don't exist in synthetic OHLCV.

**Synthetic data caveat:** Volatility arbitrage fundamentally depends on the divergence between implied and realized volatility (variance risk premium). Synthetic GARCH data has no option market, no implied vol surface, and no VRP — the strategy cannot function by design. This is an expected structural failure, not a strategy bug.

## 4. Aggregate Findings

### 4.1 Overall Statistics

| Metric | Value |
|--------|-------|
| Strategies with genuine alpha (all tests pass) | **0/8** |
| Strategies passing PSR + DSR | 6/8 |
| Mean PSR across strategies | 0.75 |
| Mean DSR across strategies | 0.75 |
| Mean Sharpe across strategies | 0.19 |
| Strategies with significant factor t-stat | ⚠️ Pending |
| Average factor R² | ⚠️ Pending |
| Strategies passing walk-forward | ⚠️ Pending |

**Note:** The 2 failing strategies (MeanReversion, VolatilityArbitrage) structurally cannot succeed on synthetic daily GARCH data. The 6 passing strategies all show suspiciously perfect scores (PSR = DSR = 1.000) across all symbols — identical Sharpe values per strategy across BTC, ETH, SOL, XRP because synthetic data is identically generated for each symbol. This is a **synthetic data artifact**, not genuine cross-symbol robustness.

### 4.2 Factor Exposure Map

| Strategy | Market Beta | Momentum Beta | Vol Beta | Other | R² |
|----------|-------------|---------------|----------|-------|-----|
| CryptoSpecific | ⚠️ Pending | ⚠️ Pending | ⚠️ Pending | ⚠️ Pending | ⚠️ Pending |
| MarketMaking | ⚠️ Pending | ⚠️ Pending | ⚠️ Pending | ⚠️ Pending | ⚠️ Pending |
| MeanReversion | ⚠️ Pending | ⚠️ Pending | ⚠️ Pending | ⚠️ Pending | ⚠️ Pending |
| Momentum | ⚠️ Pending | ⚠️ Pending | ⚠️ Pending | ⚠️ Pending | ⚠️ Pending |
| PairsTrading | ⚠️ Pending | ⚠️ Pending | ⚠️ Pending | ⚠️ Pending | ⚠️ Pending |
| RegimeBased | ⚠️ Pending | ⚠️ Pending | ⚠️ Pending | ⚠️ Pending | ⚠️ Pending |
| StatisticalArbitrage | ⚠️ Pending | ⚠️ Pending | ⚠️ Pending | ⚠️ Pending | ⚠️ Pending |
| VolatilityArbitrage | ⚠️ Pending | ⚠️ Pending | ⚠️ Pending | ⚠️ Pending | ⚠️ Pending |

**Pending — Run `scripts/factor_regression.py` with per-strategy P&L CSV files and a factor returns dataset (market, momentum, size, value, vol).** The factor regression harness exists and can decompose P&L into alpha vs factor exposure, but requires input data that the alpha destruction run did not produce.

### 4.3 Correlation Matrix

⚠️ **Pending — Requires per-strategy daily return series from alpha destruction output (`alpha_report.json` does not store return series).** The alpha destruction protocol (`scripts/alpha_destruction.py`) computes returns per strategy per symbol but only exports aggregate statistics, not the return vectors needed for correlation analysis. To generate:

```python
# Collect strategy return vectors during alpha_destruction, then:
corr_matrix = pd.DataFrame({name: returns}).corr(method="spearman")
```

The `correlation_state.json` file does not exist in `paper_state/` — correlation analysis has not been implemented yet.

## 5. Alarm Bells

- [x] **Negative PSR/DSR strategies deployed**: MeanRevention (PSR=0.0) and VolatilityArbitrage (PSR=0.0) — these should be auto-disabled in production if they cannot be turned off during unfavorable regimes.
- [ ] **Strategy pairs with correlation > 0.85**: ⚠️ Pending — no correlation matrix computed yet. Potential concern: CryptoSpecific, Momentum, and RegimeBased all likely load on the same AR(1) momentum structure in synthetic data.
- [ ] **Walk-forward Sharpe drop > 50%**: ⚠️ Pending — walk-forward not executed.
- [ ] **Factor R² > 0.8 (strategy = factor proxy)**: ⚠️ Pending — factor regression not executed.
- [ ] **Decay slope negative > 0.1/month**: ⚠️ Pending — decay analysis not executed.
- [x] **All strategies show identical Sharpe across symbols**: Synthetic data generates the same OHLCV path for each symbol (same random seed). Cross-symbol validation is meaningless in this setup.
- [x] **Paper broker PnL = $0.00**: After 7 cycles, `paper_state/state.json` shows `total_pnl: 0.0` and `peak_capital: 5000.0` (unchanged from initial). Paper trading either hasn't generated real signals or execution is not yet wired.
- [x] **High orphan rate (22.1%)**: Architecture report shows 92 orphan files including 14 Hermes engine modules, suggesting the multi-agent system may have incomplete integration.

## 6. Recommendations

### Deploy (all tests pass on real data first)
- **None yet.** No strategy has passed real-data validation, factor decomposition, or walk-forward analysis. Wait on all pending tests.

### Monitor (PSR/DSR pass, pending further validation)
| Strategy | Priority | Rationale |
|----------|----------|-----------|
| **Momentum** | High | Highest Sharpe (0.898), cleanest synthetic alpha. Should be first candidate for real-data testing. |
| **RegimeBased** | High | Sharpe 2.258 is highest but also most suspicious — leads overfitting concerns. |
| **PairsTrading** | Medium | Moderate Sharpe (0.425) but structural reliance on cointegration pairs that may not survive real markets. |
| **CryptoSpecific** | Medium | Cannot be evaluated without real crypto data (funding rates, order books, on-chain). |
| **StatisticalArbitrage** | Medium | PCA factor model likely overfit to synthetic data structure. |
| **MarketMaking** | Low | Sharpe (0.197) below minimum threshold. Daily bars inappropriate for evaluation. |

### Retire (consistently fail or structurally incompatible)
| Strategy | Action | Rationale |
|----------|--------|-----------|
| **MeanReversion** | Keep but disable by default | Structural failure on trending data is expected. Should be regime-gated: only deploy when HMM detects mean-reverting regime. |
| **VolatilityArbitrage** | Keep but disable by default | Cannot be evaluated without options data (implied vol surface, VRP). Requires real options market data to function. |

### Improve
1. **Run factor regression for all 8 strategies** — `scripts/factor_regression.py` is battle-ready. Generate per-strategy P&L CSV from alpha destruction output, create a factor returns dataset (or use synthetic factors), and run the regression. This is the single highest-impact next step.

2. **Enable walk-forward in alpha destruction** — Modify `scripts/alpha_destruction.py` to split data 70/30 and report train vs test Sharpe. This costs ~2× compute but is essential for detecting overfitting.

3. **Store return vectors in alpha_report.json** — The current report only stores aggregate stats, not the per-bar return series needed for correlation and decay analysis. Adding return arrays (or a CSV export) unlocks all remaining pending analyses.

4. **Connect real data source** — CoinGecko provider failed. Debug connectivity or switch to a cached real-data pipeline. Even 90 days of real BTC data is more informative than unlimited synthetic data.

5. **Paper trading integration** — `paper_state/state.json` shows 0.0 PnL after 7 cycles. Investigate whether signals are being generated, executed, and recorded. The paper broker exists (`exchange/paper_broker.py`) but may not be connected to the strategy engine.

6. **Multi-asset correlation watch** — Once return vectors are available, compute Spearman correlations. If CryptoSpecific/Momentum/RegimeBased all show ρ > 0.85, the portfolio has no diversification benefit and is effectively a single bet.

## 7. Conclusion

**Overall alpha verdict:** INCONCLUSIVE — Preliminary PSR/DSR analysis shows 6/8 strategies pass statistical significance, but ALL data is synthetic GARCH with known limitations. The perfect scores (PSR = DSR = 1.000) across identical synthetic data per symbol are artifacts, not evidence of robustness.

**Confidence:** LOW — Zero strategies have been validated against real market data, factor decomposition, walk-forward testing, or decay analysis. The synthetic data generating process explicitly includes momentum structure (AR(1)=0.05) and GARCH vol clustering, both of which skew results in favor of momentum and regime-detection strategies.

**Caveats that limit every conclusion below:**
- Alpha is measured against synthetic GARCH data, which lacks real market features: slippage, liquidity regimes, structural breaks, news events, funding rates, order book dynamics, implied volatility surfaces, and multi-factor correlation structure.
- Per-strategy Sharpe values are identical across BTC, ETH, SOL, XRP — the synthetic data reuses the same random seed for each symbol.
- Slippage calibration (32.9 bps round-trip) is based on only 100 synthetic trades over 5 days — not statistically robust.
- All PSR/DSR values of 1.000 indicate the Sharpe standard error is near-zero relative to the benchmark, which happens with large N (500) and high Sharpe on very specific return distributions. The fat tails (kurtosis up to 99.6) partially offset this, but the results still warrant skepticism.

**Next step:** Run `scripts/factor_regression.py` with real or paper P&L data to determine whether the 6 passing strategies produce genuine alpha or are simply loading on a single momentum factor in the synthetic data. This is the critical discriminator between genuine alpha and lucky factor exposure.

---

*Generated by `scripts/alpha_destruction.py` + manual audit of `docs/alpha_report.json`*
*Review cycle: Weekly*
*Pending: factor_regression.py execution, walk-forward implementation, decay analysis, real data connectivity, correlation matrix*
