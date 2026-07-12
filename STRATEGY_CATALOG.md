# Strategy Catalog — Quant Nanggroe AI

> Comprehensive documentation of all 16 trading strategies available in the Quant Nanggroe AI engine.
> Last updated: 2026-07-12

---

## Table of Contents

1. [Strategy Overview](#strategy-overview)
2. [Statistical / Mean-Reversion](#1-statistical--mean-reversion)
3. [Momentum / Trend](#2-momentum--trend)
4. [Market Structure](#3-market-structure)
5. [Crypto](#4-crypto)
6. [Price Action](#5-price-action)
7. [Fundamental / Sentiment](#6-fundamental--sentiment)
8. [Performance Reference](#performance-reference)

---

## Strategy Overview

| # | Strategy | Type | Key Parameters | RR | Winrate | Profit Factor | Best Market | Status |
|---|----------|------|---------------|-----|---------|--------------|-------------|--------|
| 1 | **MeanReversion** | Mean Reversion | lookback=20, entry_z=2.0 | 1:1.5 | 55–65% | 1.3–2.0 | Range-bound, choppy | ✅ |
| 2 | **PairsTrading** | Pairs Trading | lookback=60, entry_z=2.0, hr_lookback=252 | 1:2 | 60–70% | 1.5–2.5 | Correlated pairs, neutral | ✅ |
| 3 | **StatisticalArbitrage** | Stat Arb (PCA) | lookback=60, n_factors=3, entry_z=2.0 | 1:1.5–2 | 55–65% | 1.3–2.0 | Cross-sectional equity | ✅ |
| 4 | **VolatilityArbitrage** | Vol Arb | lookback=20/60, entry_z=2.0 | 1:2 | 50–60% | 1.2–2.0 | Vol mean-reversion | ✅ |
| 5 | **Momentum** | Momentum | lookback=126, fast=20, slow=50 | 1:2–3 | 40–50% | 1.5–2.5 | Strong trending | ✅ |
| 6 | **TrendFollow** | Trend Follow | fast=50, slow=200, ADX=14 | 1:3 | 35–45% | 1.5–2.5 | Strong trending | ✅ |
| 7 | **MarketMaking** | Market Making | gamma=0.1, kappa=1.5, sigma=0.02 | N/A | N/A | N/A (fee-based) | Liquid, low-spread | ✅ |
| 8 | **RegimeBased** | Regime Adaptive | n_regimes=3, hmm_lookback=252 | 1:2 | 50–60% | 1.3–2.0 | All (adaptive) | ✅ |
| 9 | **CryptoSpecific** | Crypto | mode=funding_rate_arb, lookback=24 | 1:2 | 45–65% | 1.2–2.5 | Crypto-specific | ✅ |
| 10 | **Wyckoff** | Price Action | lookback=50, vol_surge=2.0 | 1:4 | 40–50% | 1.5–2.5 | Cyclical, accumulation | ⚪ |
| 11 | **SupportResistance** | S/R Levels | pivot=5, zone=0.5%, min_touches=2 | 1:2 | 50–60% | 1.3–2.0 | Range with clear levels | ⚪ |
| 12 | **SupplyDemand** | S&D Zones | zone_lookback=5, zone=0.3%, strength=2 | 1:2 | 45–55% | 1.2–1.8 | Range, institutional flow | ⚪ |
| 13 | **SMC** | Smart Money | min_confluence=2, SL=1.5x ATR | 1:3 | 40–50% | 1.3–2.0 | Trending, liquidity sweeps | ⚪ |
| 14 | **ICT** | ICT Concepts | disp_ATR=1.5, OTE=0.618–0.702 | 1:3 | 40–50% | 1.3–2.0 | Trending, displacement | ⚪ |
| 15 | **Fundamental** | Macro/Fund | event_proximity=24h, vol_mult=2.0 | 1:2 | 45–55% | 1.2–1.8 | Event-driven, macro | ⚪ |
| 16 | **COT** | Sentiment | COT extreme thresholds 20/80 | 1:2 | 50–60% | 1.3–2.0 | Futures, extremes | ⚪ |

> **Status:** ✅ = Registered and active in the factory. ⚪ = Available but not yet registered via `_STRATEGY_REGISTRY`.

---

## 1. Statistical / Mean-Reversion

### MeanReversionStrategy

Three mean-reversion variants in one class.

- **File:** `strategies/mean_reversion.py`
- **Type:** Mean Reversion / Statistical Arbitrage
- **Registry name:** `"MeanReversion"`

**Variants:**
| Variant | Method | Entry | Exit |
|---------|--------|-------|------|
| `zscore` | Rolling z-score | \|z\| > entry_threshold (2.0) | \|z\| < exit_threshold (0.5) |
| `bollinger` | Bollinger Bands | Price outside bands | Price inside bands |
| `ou` | Ornstein-Uhlenbeck half-life | \|z\| > entry, sized by half-life | Same as zscore |

**Parameters:**
| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| strategy_type | `"zscore"` | zscore / bollinger / ou | Variant selector |
| lookback | 20 | 10–100 | Rolling window |
| entry_threshold | 2.0 | 1.0–3.0 | Entry z-score / band mult |
| exit_threshold | 0.5 | 0.1–1.0 | Exit z-score |
| atr_stop_mult | 1.5 | 1.0–3.0 | ATR stop multiplier |
| min_trade_interval_bars | 5 | 1–20 | Frequency gate |

**Performance:**
- **RR:** ~1:1.5 (ATR-based, 1.5x ATR stop / no fixed TP — mean reversion exits when z-score reverts)
- **Winrate:** 55–65% (higher on range-bound, lower on trending)
- **Profit Factor:** 1.3–2.0
- **Best Market Conditions:** Range-bound, choppy, mean-reverting. Struggles in strong trends.
- **Asset Classes:** Stocks, forex, crypto
- **Timeframes:** 1h, 4h, 1d

**References:** Kakushadze (2015), Avellaneda & Lee (2010), De Prado (2018)

---

### PairsTradingStrategy

Cointegration-based pairs trading with OLS hedge ratio estimation.

- **File:** `strategies/pairs_trading.py`
- **Type:** Pairs Trading / Statistical Arbitrage
- **Registry name:** `"PairsTrading"`

**How it works:**
1. Estimate hedge ratio via OLS on training window (default 252 bars)
2. Compute spread = price_B − hedge_ratio × price_A
3. Z-score the spread over lookback window
4. Enter when \|z\| > entry_z, exit when \|z\| < exit_z

**Parameters:**
| Parameter | Default | Description |
|-----------|---------|-------------|
| lookback | 60 | Spread z-score window |
| entry_z | 2.0 | Entry threshold |
| exit_z | 0.5 | Exit threshold |
| hedge_ratio_lookback | 252 | OLS estimation window |
| transaction_cost_bps | 10.0 | One-way cost |
| min_trade_interval_bars | 5 | Frequency gate |

**Performance:**
- **RR:** ~1:2 (spread mean reversion)
- **Winrate:** 60–70% (highest among all strategies on good pairs)
- **Profit Factor:** 1.5–2.5
- **Best Market Conditions:** Pairs with high cointegration, neutral/range-bound. Degrades when cointegration breaks.
- **Asset Classes:** Stocks, crypto

**References:** Engle & Granger (1987), Avellaneda & Lee (2010)

---

### StatisticalArbitrageStrategy

PCA-based factor model with residual mean reversion (orphan alpha).

- **File:** `strategies/statistical_arbitrage.py`
- **Type:** Statistical Arbitrage
- **Registry name:** `"StatisticalArbitrage"`

**How it works:**
1. Build cross-sectional universe of stocks
2. Extract top K principal components via SVD
3. Compute residuals = actual returns − factor-model predicted returns
4. Z-score residuals and trade on divergence

**Parameters:**
| Parameter | Default | Description |
|-----------|---------|-------------|
| lookback | 60 | PCA estimation window |
| n_factors | 3 | Number of PCA factors |
| entry_threshold | 2.0 | Residual z-score entry |
| exit_threshold | 0.5 | Residual z-score exit |
| return_lookback | 20 | Multi-period return window |
| universe_size | 20 | Max stocks in universe |
| min_trade_interval_bars | 10 | Frequency gate |

**Performance:**
- **RR:** ~1:1.5–2
- **Winrate:** 55–65%
- **Profit Factor:** 1.3–2.0
- **Best Market Conditions:** Large cross-sectional universe with common factors. Struggles in small universes.
- **Asset Classes:** Stocks, crypto

**References:** Avellaneda & Lee (2010), Chamberlain & Rothschild (1983)

---

### VolatilityArbitrageStrategy

Vol-ratio z-score strategy with three volatility estimation methods.

- **File:** `strategies/volatility_arbitrage.py`
- **Type:** Volatility Arbitrage
- **Registry name:** `"VolatilityArbitrage"`

**How it works:**
1. Estimate short-term vol via historical/EWMA/GARCH(1,1)
2. Compare to long-term vol via ratio
3. Z-score the vol ratio; short vol when z > entry, long vol when z < -entry

**Parameters:**
| Parameter | Default | Description |
|-----------|---------|-------------|
| vol_lookback | 20 | Short-term vol window |
| vol_long_lookback | 60 | Long-term vol window |
| entry_threshold | 2.0 | Z-score entry |
| exit_threshold | 0.5 | Z-score exit |
| vol_estimation | `"ewma"` | historical / ewma / garch |
| min_trade_interval_bars | 5 | Frequency gate |

**Performance:**
- **RR:** ~1:2
- **Winrate:** 50–60%
- **Profit Factor:** 1.2–2.0
- **Best Market Conditions:** Volatility mean-reversion. GARCH variant works best on daily data.
- **Asset Classes:** Stocks, futures, options

**References:** Bollerslev (1986), J.P. Morgan RiskMetrics (1996)

---

## 2. Momentum / Trend

### MomentumStrategy

Four momentum variants with signal smoothing and cost controls.

- **File:** `strategies/momentum.py`
- **Type:** Momentum
- **Registry name:** `"Momentum"`

**Variants:**
| Variant | Reference | Mechanics |
|---------|-----------|-----------|
| `ts_momentum` | Moskowitz et al. (2012) | Buy when return over lookback > threshold |
| `dual_momentum` | Antonacci (2014) | Requires both absolute + relative alignment |
| `ma_crossover` | Classic | Buy when fast MA > slow MA |
| `macd` | Classic | Signal direction from MACD histogram |

**Parameters:**
| Parameter | Default | Description |
|-----------|---------|-------------|
| lookback | 126 | TS momentum window |
| fast_lookback | 20 | Fast MA period |
| slow_lookback | 50 | Slow MA period |
| entry_threshold | 0.05 | Minimum return to enter |
| signal_smoothing | 3 | SMA on raw signal |
| min_trade_interval_bars | 5 | Frequency gate |

**Performance:**
- **RR:** ~1:2–3 (trend continuation)
- **Winrate:** 40–50% (lower winrate, higher RR — classic trend-following profile)
- **Profit Factor:** 1.5–2.5
- **Best Market Conditions:** Strong trending markets (bull/bear). Suffers in choppy/range-bound.
- **Asset Classes:** Stocks, forex, crypto, futures

**References:** Jegadeesh & Titman (1993), Moskowitz et al. (2012), Antonacci (2014)

---

### TrendFollowStrategy

Dual SMA crossover + ADX trend strength confirmation + trailing ATR stop.

- **File:** `strategies/trend_follow.py`
- **Type:** Trend Following
- **Registry name:** `"TrendFollow"`

**Parameters:**
| Parameter | Default | Description |
|-----------|---------|-------------|
| fast_period | 50 | Fast SMA |
| slow_period | 200 | Slow SMA |
| adx_period | 14 | ADX lookback |
| adx_threshold | 25 | Min ADX for trend confirmation |
| atr_period | 14 | ATR lookback for trailing stop |
| atr_stop_mult | 3.0 | Stop distance multiplier |
| entry_threshold | 0.1 | Min signal to enter |

**Performance:**
- **RR:** ~1:3 (3x ATR trailing stop vs. trend capture)
- **Winrate:** 35–45% (lowest winrate, highest RR)
- **Profit Factor:** 1.5–2.5
- **Best Market Conditions:** Strong secular trends with ADX > 25. Breaks down in range-bound markets.
- **Asset Classes:** Stocks, forex, crypto, futures

**References:** Kakushadze (2015, #31), Wilder (1978)

---

## 3. Market Structure

### MarketMakingStrategy

Avellaneda-Stoikov optimal quoting with inventory management.

- **File:** `strategies/market_making.py`
- **Type:** Market Making
- **Registry name:** `"MarketMaking"`

**Parameters:**
| Parameter | Default | Description |
|-----------|---------|-------------|
| gamma | 0.1 | Risk aversion coefficient |
| kappa | 1.5 | Order arrival rate |
| sigma | 0.02 | Volatility estimate |
| inventory_target | 0.0 | Desired inventory |
| max_inventory | 100.0 | Max absolute position |
| order_size | 1.0 | Base quote size |
| num_levels | 1 | Quote depth |
| spread_multiplier | 1.0 | Spread scale factor |

**Performance:**
- **RR:** N/A (not directional — captures bid-ask spread)
- **Winrate:** N/A (profit from fee/rebate + spread capture)
- **Profit Factor:** N/A (market making is fee-based, not PF-measured)
- **Best Market Conditions:** Highly liquid assets with tight spreads and high order flow
- **Asset Classes:** Crypto, forex

**References:** Avellaneda & Stoikov (2008)

---

### RegimeBasedStrategy

HMM-driven regime detection with per-regime strategy switching.

- **File:** `strategies/regime_based.py`
- **Type:** Regime Adaptive
- **Registry name:** `"RegimeBased"`

**Regimes:**
| # | Label | Default Strategy |
|---|-------|-----------------|
| 0 | Bull | Momentum |
| 1 | Bear | Defensive (reduce) |
| 2 | Range-bound | Mean reversion |
| 3 | High volatility | Reduce exposure |

**Parameters:**
| Parameter | Default | Description |
|-----------|---------|-------------|
| n_regimes | 3 | 2–4 regimes |
| hmm_lookback | 252 | Training window |
| covariance_type | `"full"` | HMM covariance |
| regime_stability_bars | 5 | Min bars before regime switch |
| volatility_threshold | 1.5 | High-vol detection multiplier |

**Performance:**
- **RR:** ~1:2
- **Winrate:** 50–60%
- **Profit Factor:** 1.3–2.0
- **Best Market Conditions:** All — adapts to current regime. Performance depends on regime detection accuracy.
- **Asset Classes:** Stocks, forex, crypto

**References:** Hamilton (1989), Rabiner (1989)

---

## 4. Crypto

### CryptoSpecificStrategy

Five crypto-specific sub-strategies in one class.

- **File:** `strategies/crypto_specific.py`
- **Type:** Crypto
- **Registry name:** `"CryptoSpecific"`

**Modes:**
| Mode | Signal | Data Required |
|------|--------|---------------|
| `funding_rate_arb` | Short when FR > threshold, long when FR < -threshold | close, volume, funding_rate |
| `liquidation_cascade` | Buy cascade dips, sell cascade spikes | close, volume |
| `on_chain` | Bullish on outflows + whale accumulation | exchange_inflow/outflow, whale_tx_count |
| `dex_arb` | Buy DEX / sell CEX when spread > fees | dex_price, cex_price |
| `mev_aware` | HOLD in high-MEV, execute in low-MEV | solana_tip, priority_fee |

**Parameters:**
| Parameter | Default | Description |
|-----------|---------|-------------|
| mode | `"funding_rate_arb"` | Sub-strategy selector |
| lookback | 24 | Rolling window |
| entry_threshold (FR) | 0.0003 | Funding rate entry |
| cascade_z_threshold | 2.5 | Z-score for cascade detection |
| stop_loss_pct | 0.05 | Stop loss fraction |
| take_profit_pct | 0.10 | Take profit fraction |

**Performance (by mode):**
| Mode | RR | Winrate | Profit Factor |
|------|----|---------|--------------|
| funding_rate_arb | 1:2 | 60–65% | 1.5–2.5 |
| liquidation_cascade | 1:2 | 45–55% | 1.2–2.0 |
| on_chain | 1:2 | 50–60% | 1.3–1.8 |
| dex_arb | 1:2 | 55–65% | 1.5–2.5 |
| mev_aware | 1:2 | N/A (execution quality) | N/A |

- **Best Market Conditions:** Crypto-specific — each mode targets distinct crypto market inefficiencies
- **Asset Classes:** Crypto only

**References:** Alexander & Dakos (2020), Harvey et al. (2021), Daian et al. (2020), Baur & Dimpfl (2018)

---

## 5. Price Action

### WyckoffStrategy

Wyckoff accumulation/distribution phase detection.

- **File:** `strategies/wyckoff_strategy.py`
- **Type:** Price Action / Wyckoff Method
- **Registry name:** `"Wyckoff"`

**Detection Phases:**
- **Accumulation:** Preliminary Support → Selling Climax → Automatic Rally → Secondary Test → Spring
- **Distribution:** Preliminary Supply → Buying Climax → Automatic Decline → Secondary Test → Upthrust

**Parameters:**
| Parameter | Default | Description |
|-----------|---------|-------------|
| lookback | 50 | Phase detection window |
| vol_surge_mult | 2.0 | Volume surge multiplier for climax |
| spring_atr_mult | 1.5 | ATR multiplier for spring depth |
| min_phase_bars | 5 | Min bars to confirm phase |

**Performance:**
- **RR:** ~1:4 (4x ATR TP, 1x ATR SL)
- **Winrate:** 40–50%
- **Profit Factor:** 1.5–2.5
- **Best Market Conditions:** Cyclical markets with clear accumulation/distribution patterns. Works on daily+ timeframes.
- **Asset Classes:** Stocks, crypto, futures

**Status:** ⚪ Available but not registered in factory.

---

### SupportResistanceStrategy

Swing point detection with zone clustering, bounce/breakout signals.

- **File:** `strategies/support_resistance_strategy.py`
- **Type:** Price Action / S/R Levels
- **Registry name:** `"SupportResistance"`

**Parameters:**
| Parameter | Default | Description |
|-----------|---------|-------------|
| pivot_window | 5 | Lookback for swing highs/lows |
| zone_pct | 0.005 | Zone merge distance (% of price) |
| min_touches | 2 | Min touches for valid level |
| breakout_pct | 0.003 | % beyond level to confirm breakout |
| use_volume | True | Volume confirmation required |

**Performance:**
- **RR:** ~1:2 (1.5x ATR SL, 3x ATR TP)
- **Winrate:** 50–60%
- **Profit Factor:** 1.3–2.0
- **Best Market Conditions:** Range-bound markets with clear, tested S/R levels. Degrades in strong trends.
- **Asset Classes:** Stocks, forex, crypto, futures

**Status:** ⚪ Available but not registered in factory.

---

### SupplyDemandStrategy

Institutional supply/demand zone detection with strength scoring.

- **File:** `strategies/supply_demand_strategy.py`
- **Type:** Price Action / S&D Zones
- **Registry name:** `"SupplyDemand"`

**Parameters:**
| Parameter | Default | Description |
|-----------|---------|-------------|
| zone_lookback | 5 | Lookback for base detection |
| zone_pct | 0.003 | Zone thickness (% of price) |
| min_strength | 2 | Min touches for valid zone |
| max_zone_age | 100 | Max bars before zone expires |
| require_volume | True | Volume confirmation at creation |

**Performance:**
- **RR:** ~1:2
- **Winrate:** 45–55%
- **Profit Factor:** 1.2–1.8
- **Best Market Conditions:** Range-bound markets with institutional order flow patterns.
- **Asset Classes:** Stocks, forex, crypto, futures

**Status:** ⚪ Available but not registered in factory.

---

### SMCStrategy

Smart Money Concepts: order blocks, liquidity sweeps, FVGs, market structure.

- **File:** `strategies/smc_strategy.py`
- **Type:** Price Action / SMC
- **Registry name:** `"SMC"`

**Confluence Patterns:**
- Order blocks (buy/sell)
- Liquidity sweeps of swing highs/lows
- Fair Value Gaps (bullish/bearish)
- Market structure shifts

**Parameters:**
| Parameter | Default | Description |
|-----------|---------|-------------|
| min_confluence | 2 | Min patterns required for signal |
| sl_atr_mult | 1.5 | Stop loss ATR multiplier |
| tp_atr_mult | 3.0 | Take profit ATR multiplier |

**Performance:**
- **RR:** ~1:3 (1.5x ATR SL, 3x ATR TP)
- **Winrate:** 40–50%
- **Profit Factor:** 1.3–2.0
- **Best Market Conditions:** Trending markets with liquidity sweeps at key levels.
- **Asset Classes:** Stocks, forex, crypto

**Status:** ⚪ Available but not registered in factory.

---

### ICTStrategy

Inner Circle Trader concepts: displacement, FVG, OTE, order blocks, kill zones.

- **File:** `strategies/ict_strategy.py`
- **Type:** Price Action / ICT
- **Registry name:** `"ICT"`

**Concepts:**
- Displacement (>1.5x ATR directional candle)
- Fair Value Gaps (price inefficiency)
- Optimal Trade Entry (61.8%–70.2% retracement)
- Order blocks
- Kill zone time filters (London, NY, Asian)

**Parameters:**
| Parameter | Default | Description |
|-----------|---------|-------------|
| displacement_atr_mult | 1.5 | Min ATR mult for displacement |
| ote_min | 0.618 | Min OTE retracement |
| ote_max | 0.702 | Max OTE retracement |
| require_killzone | False | Require kill zone filter |

**Performance:**
- **RR:** ~1:3
- **Winrate:** 40–50%
- **Profit Factor:** 1.3–2.0
- **Best Market Conditions:** Trending markets with clear displacement and retracement into OTE zones.
- **Asset Classes:** Forex, crypto

**Status:** ⚪ Available but not registered in factory.

---

## 6. Fundamental / Sentiment

### FundamentalStrategy

Economic calendar events, macro surprises, central bank policy, sentiment.

- **File:** `strategies/fundamental_strategy.py`
- **Type:** Fundamental / Macro
- **Registry name:** `"Fundamental"`

**Inputs:**
- Economic calendar (high-impact events)
- Recent surprises (deviation from consensus)
- Market risk assessment
- Technical sentiment (20-day Sharpe)

**Parameters:**
| Parameter | Default | Description |
|-----------|---------|-------------|
| event_proximity_hours | 24 | Hours before event to reduce risk |
| surprise_threshold | 0.3 | Min absolute surprise to act on |
| vol_mult | 2.0 | ATR multiplier for SL/TP |
| risk_reduction_pct | 0.5 | Position size reduction before events |

**Performance:**
- **RR:** ~1:2 (2x ATR SL, 4x ATR TP)
- **Winrate:** 45–55%
- **Profit Factor:** 1.2–1.8
- **Best Market Conditions:** Event-driven periods with clear macro surprises.
- **Asset Classes:** Forex, stocks, futures

**Status:** ⚪ Available but not registered in factory.

---

### COTStrategy

Commitment of Traders positioning extremes and divergence.

- **File:** `strategies/cot_strategy.py`
- **Type:** Sentiment / COT
- **Registry name:** `"COT"`

**How it works:**
1. Load COT data via COTProvider + COTAnalyzer
2. Detect extreme positioning (>80 or <20 on COT index)
3. Trade mean-reversion on extremes with divergence confirmation

**Parameters:**
| Parameter | Default | Description |
|-----------|---------|-------------|
| extreme_buy_threshold | 20 | COT index below → buy |
| extreme_sell_threshold | 80 | COT index above → sell |
| divergence_period | 10 | Lookback for divergence detection |

**Performance:**
- **RR:** ~1:2 (2x ATR SL, 4x ATR TP)
- **Winrate:** 50–60%
- **Profit Factor:** 1.3–2.0
- **Best Market Conditions:** Futures markets with clear COT data. Best on weekly timeframe.
- **Asset Classes:** Futures (requires COT data, e.g. ES, currencies)

**Status:** ⚪ Available but not registered in factory.

---

## Performance Reference

> The following table provides typical strategy metrics based on academic literature and
> backtesting conventions. Actual results depend on market conditions, parameter
> optimization, and execution quality.

### Summary by Performance Type

| Profile | Strategies | Typical Winrate | Typical RR |
|---------|-----------|-----------------|------------|
| **High winrate, low RR** | MeanReversion, PairsTrading, StatArb | 55–70% | 1:1.5–2 |
| **Low winrate, high RR** | TrendFollow, Momentum, Wyckoff | 35–50% | 1:2–4 |
| **Balanced** | RegimeBased, VolArb, S/R, ICT, SMC | 50–60% | 1:2–3 |

### Strategy Selection Guide

| Market Condition | Recommended Strategies |
|-----------------|----------------------|
| Strong uptrend | Momentum (ts/dual), TrendFollow |
| Strong downtrend | Momentum (ts/dual), TrendFollow |
| Range-bound / Choppy | MeanReversion, PairsTrading, VolArb |
| High volatility | VolArb, RegimeBased (high_vol), Fundamental (HOLD) |
| Low volatility | MarketMaking, MeanReversion |
| Event-driven | Fundamental, COT |
| Crypto-specific | CryptoSpecific (all modes) |
| Clear S/R levels | SupportResistance, SupplyDemand, SMC, ICT |
| Cyclical / Accumulation | Wyckoff |

### Notes

- **RR (Risk/Reward):** Estimated from the strategy's default stop-loss and take-profit logic.
  Actual RR varies with market conditions and parameter tuning.
- **Winrate:** Percentage of profitable trades. Higher winrate ≠ better strategy — must be
  evaluated alongside RR for expected value.
- **Profit Factor:** Gross profit / gross loss. > 1.0 is profitable. > 2.0 is exceptional.
- **Sharpe Ratio:** Not systematically computed here. Most strategies target > 1.0 annualized.
- All strategies include transaction cost modeling (default 10 bps one-way) and trade
  frequency gates to prevent over-trading.
