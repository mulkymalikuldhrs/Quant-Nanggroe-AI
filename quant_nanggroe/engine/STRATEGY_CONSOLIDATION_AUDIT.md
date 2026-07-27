# Strategy Consolidation Audit Report

**Date:** 2026-07-25 (Updated 2026-07-27 — v6.2.0 Naming Fix)
**Scope:** Quant-Nanggroe-AI dual strategy directories
**Old Path:** `quant_nanggroe/engine/strategy/strategies/` (139 .py files)
**New Path:** `quant_nanggroe/engine/strategies/` (29 .py files)

---

## Bridge Architecture

The new path `__init__.py` loads strategies from **two sources**:
1. **Canonical (new path)** — 28 strategy files auto-discovered via `glob('*.py')`
2. **Legacy bridge** — Imports the remaining 110 files from the old path via a shim loop

The old path `__init__.py` is a backward-compat shim that re-exports from `quant_nanggroe.engine.strategies.*` and delegates `create_strategy()` to `StrategyRegistry.create()`.

**v6.2.0 update:** The walk-forward metadata store in `engine/strategy/registry.py` was renamed from `StrategyRegistry` to `WalkForwardRegistry` to eliminate the dual-class-name collision documented in previous audits. The class registry in `engine/strategies/registry.py` retains the `StrategyRegistry` name — the two are now distinct and self-documenting.

**Both paths work** in production — but the old-path strategies are bridged at import time, not migrated.

---

## Strategy Files: Cross-Reference Summary

| Category | Count | Details |
|---|---|---|
| In BOTH paths | 29 | All new-path files also exist in old path (some are stale copies) |
| Old-path ONLY | 104 | Valid legacy strategies pending migration |
| Old-path ONLY (non-strategy) | 6 | Can be archived (utility/standalone code) |
| New-path ONLY | 0 | No new-path files lack an old-path counterpart |
| **Total old-path** | **139** | |
| **Total new-path** | **29** | |

---

## 1. Files in BOTH paths (migrated — have new-path equivalents)

These 23 strategy files exist in both directories. The new-path versions use the new `Strategy` base class and `@StrategyRegistry.register` decorator. Old-path copies may be stale.

| # | File | Old Path Base | New Path Base | Size Diff |
|---|---|---|---|---|
| 1 | algebra.py | Strategy ✓ | Strategy ✓ | — |
| 2 | amdx.py | Strategy ✓ | Strategy ✓ | — |
| 3 | dhaher_system.py | Strategy ✓ | Strategy ✓ | — |
| 4 | ema_adx.py | Strategy ✓ | Strategy ✓ | — |
| 5 | fibonacci.py | Strategy ✓ | Strategy ✓ | — |
| 6 | fibo_strategy.py | Strategy ✓ | Strategy ✓ | — |
| 7 | ict.py | Strategy ✓ | Strategy ✓ | — |
| 8 | kronos_wrapper.py | Strategy ✓ | Strategy ✓ | — |
| 9 | market_profile.py | Strategy ✓ | Strategy ✓ | — |
| 10 | mean_reversion.py | BaseStrategy ✗ | Strategy ✓ | old +6918 bytes |
| 11 | msnr.py | Strategy ✓ | Strategy ✓ | — |
| 12 | multi_timeframe_strategy.py | Strategy ✓ | Strategy ✓ | — |
| 13 | pairs_trade_strategy.py | Strategy ✓ | Strategy ✓ | — |
| 14 | quarterly_theory.py | Strategy ✓ | Strategy ✓ | — |
| 15 | smc_strategy.py | BaseStrategy ✗ | Strategy ✓ | old -2467 bytes |
| 16 | smc_strategy_OLD.py | Strategy ✓ | Strategy ✓ | — |
| 17 | strategy_evolver.py | (utility) | (utility) | — |
| 18 | tradebobby_smc_scanner.py | Strategy ✓ | Strategy ✓ | — |
| 19 | trend_follow_strategy.py | Strategy ✓ | Strategy ✓ | — |
| 20 | tsmom_strategy.py | Strategy ✓ | Strategy ✓ | — |
| 21 | unified_retail.py | Strategy ✓ | Strategy ✓ | — |
| 22 | volume_delta.py | Strategy ✓ | Strategy ✓ | — |
| 23 | wyckoff.py | Strategy ✓ | Strategy ✓ | 0 bytes (identical) |

**Infrastructure files (both paths):** `__init__.py`, `base.py`, `registry.py`, `gene_loader.py`, `_df_signal_adapter.py`

**⚠ Stale old-path copies (need cleanup):** `mean_reversion.py`, `smc_strategy.py` — these old-path copies still import from old `base_strategy.BaseStrategy` while their new-path counterparts use new `Strategy`.

---

## 2. OLD-PATH ONLY — 104 Strategies Pending Migration

All 104 files below:
- Import from `quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy`
- Do **not** use `@StrategyRegistry.register`
- Extend old `BaseStrategy` (not new `Strategy`)
- Are fully bridged via the legacy shim but **not yet migrated**

### Pending Migration List

| # | File | Class | Notes |
|---|---|---|---|
| 1 | adaptive_moving_average.py | AdaptiveMovingAverageStrategy | |
| 2 | adx_strategy.py | ADXStrategy | |
| 3 | aroon_strategy.py | AroonStrategy | |
| 4 | atr_breakout.py | ATRBreakoutStrategy | |
| 5 | bayesian_ridge.py | BayesianRidgeStrategy | |
| 6 | bollinger_squeeze.py | BollingerSqueezeStrategy | |
| 7 | camarilla_pivot.py | CamarillaPivotStrategy | |
| 8 | carry_trade.py | CarryTradeStrategy | |
| 9 | cci_strategy.py | CCIStrategy | |
| 10 | choppiness_index.py | ChoppinessIndexStrategy | |
| 11 | commodity_trend.py | CommodityTrendStrategy | |
| 12 | cot_strategy.py | COTStrategy | |
| 13 | crypto_funding.py | CryptoFundingStrategy | |
| 14 | crypto_specific.py | CryptoSpecificStrategy | |
| 15 | dark_cloud.py | DarkCloudCoverStrategy | |
| 16 | dark_pool_flow.py | DarkPoolFlowStrategy | |
| 17 | dema_strategy.py | DEMAStrategy | |
| 18 | dmi_strategy.py | DMIStrategy | |
| 19 | doji_pattern.py | DojiPatternStrategy | |
| 20 | dxy_momentum.py | DXYMomentumStrategy | |
| 21 | elder_ray.py | ElderRayStrategy | |
| 22 | elder_triple_screen.py | ElderTripleScreenStrategy | |
| 23 | em_carry.py | EMCarryStrategy | |
| 24 | engulfing_pattern.py | EngulfingPatternStrategy | |
| 25 | entropy_strategy.py | EntropyStrategy | |
| 26 | evening_star.py | EveningStarStrategy | |
| 27 | ewma_vol.py | EWMAVolStrategy | |
| 28 | fibonacci_arc.py | FibonacciArcStrategy | |
| 29 | fibonacci_extension.py | FibonacciExtensionStrategy | |
| 30 | fibonacci_fan.py | FibonacciFanStrategy | |
| 31 | fibonacci_retracement.py | FibonacciRetracementStrategy | |
| 32 | fibonacci_time.py | FibonacciTimeStrategy | |
| 33 | fundamental_strategy.py | FundamentalStrategy | |
| 34 | garch_vol.py | GARCHVolStrategy | |
| 35 | gold_inflation.py | GoldInflationStrategy | |
| 36 | half_life_mean_reversion.py | HalfLifeMeanReversionStrategy | |
| 37 | hammer_pattern.py | HammerPatternStrategy | |
| 38 | harami_pattern.py | HaramiPatternStrategy | |
| 39 | hull_ma.py | HullMAStrategy | |
| 40 | hurst_exponent.py | HurstExponentStrategy | |
| 41 | ichimoku_cloud.py | IchimokuCloudStrategy | |
| 42 | ict_strategy.py | ICTStrategy | ⚠ naming variant of `ict.py` (already migrated) |
| 43 | inverted_hammer.py | InvertedHammerStrategy | |
| 44 | kalman_filter.py | KalmanFilterStrategy | |
| 45 | kaufman_ama.py | KaufmanAMAStrategy | |
| 46 | kelly_optimal.py | KellyOptimalStrategy | |
| 47 | keltner_squeeze.py | KeltnerSqueezeStrategy | |
| 48 | kmeans_regime.py | KMeansRegimeStrategy | |
| 49 | linear_regression_channel.py | LinearRegressionChannelStrategy | |
| 50 | macro_fx.py | MacroFXStrategy | |
| 51 | macro_rates.py | MacroRatesStrategy | |
| 52 | market_making.py | MarketMakingStrategy | |
| 53 | mean_reversion_stat.py | MeanReversionStatStrategy | |
| 54 | mfi_strategy.py | MFIStrategy | |
| 55 | momentum.py | MomentumStrategy | |
| 56 | momentum_crash_filter.py | MomentumCrashFilterStrategy | |
| 57 | momentum_factor.py | MomentumFactorStrategy | |
| 58 | monte_carlo_barrier.py | MonteCarloBarrierStrategy | |
| 59 | morning_star.py | MorningStarStrategy | |
| 60 | multi_indicator_voting.py | MultiIndicatorVotingStrategy | |
| 61 | obv_strategy.py | OBVStrategy | |
| 62 | on_chain_momentum.py | OnChainMomentumStrategy | |
| 63 | options_put_call.py | OptionsPutCallStrategy | |
| 64 | options_straddle.py | OptionsStraddleStrategy | |
| 65 | pairs_cointegration.py | PairsCointegrationStrategy | |
| 66 | pairs_trading.py | PairsTradingStrategy | ⚠ naming variant of `pairs_trade_strategy.py` |
| 67 | parabolic_sar.py | ParabolicSARStrategy | |
| 68 | particle_filter.py | ParticleFilterStrategy | |
| 69 | pca_strategy.py | PCAStrategy | |
| 70 | piercing_line.py | PiercingLineStrategy | |
| 71 | pivot_points.py | PivotPointsStrategy | |
| 72 | polynomial_regression.py | PolynomialRegressionStrategy | |
| 73 | quality_factor.py | QualityFactorStrategy | |
| 74 | regime_based.py | RegimeBasedStrategy | |
| 75 | regime_hmm.py | RegimeHMMStrategy | |
| 76 | relative_vigor.py | RelativeVigorStrategy | |
| 77 | risk_parity.py | RiskParityStrategy | |
| 78 | rsi_divergence_macd.py | RSIDivergenceMACDStrategy | |
| 79 | shooting_star.py | ShootingStarStrategy | |
| 80 | size_factor.py | SizeFactorStrategy | |
| 81 | social_sentiment.py | SocialSentimentStrategy | |
| 82 | stat_arb_zscore.py | StatArbZscoreStrategy | |
| 83 | statistical_arbitrage.py | StatisticalArbitrageStrategy | |
| 84 | stochastic_oscillator.py | StochasticOscillatorStrategy | |
| 85 | supply_demand_strategy.py | SupplyDemandStrategy | |
| 86 | support_resistance_strategy.py | SupportResistanceStrategy | |
| 87 | t3_strategy.py | T3Strategy | |
| 88 | tema_strategy.py | TEMAStrategy | |
| 89 | three_black_crows.py | ThreeBlackCrowsStrategy | |
| 90 | three_white_soldiers.py | ThreeWhiteSoldiersStrategy | |
| 91 | trend_follow.py | TrendFollowStrategy | ⚠ naming variant of `trend_follow_strategy.py` |
| 92 | trend_following_cta.py | TrendFollowingCTAStrategy | |
| 93 | trix_strategy.py | TRIXStrategy | |
| 94 | value_factor.py | ValueFactorStrategy | |
| 95 | vix_term_structure.py | VIXTermStructureStrategy | |
| 96 | vol_surface_arb.py | VolSurfaceArbStrategy | |
| 97 | volatility_arbitrage.py | VolatilityArbitrageStrategy | |
| 98 | volatility_regime.py | VolatilityRegimeStrategy | |
| 99 | volatility_selling.py | VolatilitySellingStrategy | |
| 100 | vortex_strategy.py | VortexStrategy | |
| 101 | williams_r.py | WilliamsRStrategy | |
| 102 | woodie_pivot.py | WoodiePivotStrategy | |
| 103 | wyckoff_strategy.py | WyckoffStrategy | ⚠ naming variant of `wyckoff.py` (already migrated) |
| 104 | yield_curve.py | YieldCurveStrategy | |

**Total: 104 strategies pending migration to `quant_nanggroe/engine/strategies/`**

---

## 3. OLD-PATH ONLY — 6 Files Eligible for Archival (Non-Strategy)

These are NOT valid strategy classes. They can be archived/deleted after the migration is complete.

### 3a. Standalone computation classes (superseded by migrated strategies)

| File | Class(es) | Reason to Archive |
|---|---|---|
| `pairs_trade.py` | `PairsTrade` | Plain class, not a BaseStrategy. Superseded by `pairs_trade_strategy.py` in new path |
| `xgboost_alpha.py` | `XGBoostAlpha` | Plain class, not a BaseStrategy. Superseded by `xgboost_alpha_strategy.py` in new path |
| `tsmom.py` | `TSMOM` | Plain class, not a BaseStrategy. Superseded by `tsmom_strategy.py` in new path |

These files contain utility computation logic that was either absorbed into or replaced by the corresponding `Strategy` subclass in the new path. They should not be migrated as-is.

### 3b. Non-strategy utilities

| File | Content | Reason to Archive |
|---|---|---|
| `self_finetune.py` | `SelfFineTuner`, `FineTuneConfig`, `FineTuneResult` | LLM self-finetuning utility, not a trading strategy. Lives in wrong directory |
| `new_proposals.py` | 10 experimental strategies (VPINToxicity, AmihudReversal, etc.) | Experimental/in-progress proposals all extending old `BaseStrategy`. These are draft strategies, not production-ready |
| `base_strategy.py` | `BaseStrategy` (ABC) | Old base class — replaced entirely by `base.py` in new path (`Strategy`, `StrategyParameters`, etc.) |

### 3c. Recommended disposition

- **`pairs_trade.py`, `xgboost_alpha.py`, `tsmom.py`** — Archive/suppress. Their logic was either folded into the migrated strategy or no longer needed.
- **`self_finetune.py`** — Move to a proper utility module (e.g., `quant_nanggroe/utils/` or `quant_nanggroe/ml/`).
- **`new_proposals.py`** — Keep as-is during migration (it's the only place these 10 experimental strategies live). After all standard strategies are done, either migrate these 10 or move to an `experimental/` directory.
- **`base_strategy.py`** — Delete after all 104 strategies are migrated (nothing will reference it).

---

## 4. Naming Variant Conflicts (4 pairs to resolve during migration)

These old-only files have the **same conceptual strategy** as an already-migrated file but under a different name:

| Old-only File | Class | Already Migrated As | Conflict |
|---|---|---|---|
| `trend_follow.py` | TrendFollowStrategy | `trend_follow_strategy.py` | Different file name, same class name |
| `ict_strategy.py` | ICTStrategy | `ict.py` | Different file name, same class name |
| `wyckoff_strategy.py` | WyckoffStrategy | `wyckoff.py` | Different file name, same class name |
| `pairs_trading.py` | PairsTradingStrategy | `pairs_trade_strategy.py` | Different file name, similar class name |

**Resolution:** For these 4, decide whether to:
- Copy the old implementation to a new file under the new path (keeping the already-migrated file), or
- Declare the old file as superseded by the already-migrated file and skip migration (if the migrated version covers the same logic)

---

## 5. Key Statistics

| Metric | Count |
|---|---|
| Old path .py files | 139 |
| New path .py files | 29 |
| Files in both paths | 29 |
| Files old-only | 110 |
| **Strategies pending migration** | **104** |
| Old-path stale copies needing cleanup | 2 (`mean_reversion.py`, `smc_strategy.py`) |
| Standalone utils superseded (can archive) | 3 (`pairs_trade`, `xgboost_alpha`, `tsmom`) |
| Non-strategy files (can archive) | 3 (`self_finetune`, `new_proposals`, `base_strategy`) |
| Naming variant conflicts to resolve | 4 |
| Experimental proposals | 10 (in `new_proposals.py`) |

---

## 6. Migration Priority Recommendations

**Phase 1 — High value / commonly used (20-30 strategies):**
Strategies frequently referenced in backtests or known to be actively used. Focus on: momentum.py, trend_follow.py, pairs_trading.py, statistical_arbitrage.py, mean_reversion_stat.py, market_making.py, fundamental_strategy.py, risk_parity.py, ichimoku_cloud.py, bollinger_squeeze.py.

**Phase 2 — Indicator-based / formulaic (50+ strategies):**
These are straightforward Kakushadze-style indicator strategies with minimal external deps: adx, aroon, atr, cci, dmi, dema, tema, t3, hull_ma, kaufman_ama, parabolic_sar, etc.

**Phase 3 — Domain-specific / complex (20-30 strategies):**
Option strategies, crypto-specific, macro strategies, ML-based: options_straddle, options_put_call, crypto_funding, on_chain_momentum, macro_fx, macro_rates, bayesian_ridge, kmeans_regime, garch_vol, particle_filter, kalman_filter, etc.

**Phase 4 — Naming variants and cleanup:**
Resolve the 4 naming conflicts. Remove old path stale copies. Archive utility files. Clean up `base_strategy.py`.
