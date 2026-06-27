# agents.tools.technical

## Function: 

Simple Moving Average.

*Line: 47*

---

## Function: 

Exponential Moving Average.

*Line: 58*

---

## Function: 

Relative Strength Index.

*Line: 75*

---

## Function: 

MACD indicator.

*Line: 108*

---

## Function: 

Average Directional Index.

*Line: 148*

---

## Function: 

Bollinger Bands.

*Line: 223*

---

## Function: 

Stochastic Oscillator.

*Line: 252*

---

## Function: 

Average True Range.

*Line: 285*

---

## Function: 

Compute all technical indicators from OHLCV data.

*Line: 315*

---

## Function: 

On-Balance Volume.

*Line: 383*

---

## Function: 

Volume Weighted Average Price (simplified).

*Line: 396*

---

## Class: 

Smart Money Concepts detector — BOS & CHoCH from swing pivots.

This is a deterministic implementation that identifies:
  - Break of Structure (BOS): Price breaks a previous swing in the
    direction of the prevailing trend → trend continuation signal.
  - Change of Character (CHoCH): Price breaks a previous swing
    *against* the prevailing trend → trend reversal signal.

**Methods:** detect

*Line: 411*

---

## Class: 

Support and resistance level detection using swing pivot clustering.

Groups nearby swing levels into zones and ranks them by the number
of times price has reacted from each zone.

**Methods:** detect, _cluster_levels

*Line: 545*

---

## Class: 

Full technical analysis tool for agent consumption.

Combines deterministic indicator calculations with Smart Money
Concepts detection, trend classification, support/resistance
levels, and computed derivative fields.

Usage::

    tool = TechnicalAnalysisTool(market_data_tool=mdt)
    result = await tool.analyze("AAPL", "1d")
    print(result["trend"]["direction"])  # "BULL" | "BEAR" | "NEUTRAL"

**Methods:** __init__, analyze_raw, _classify_trend, _compute_derived

*Line: 658*

---

## Function: 

Get or create the default TechnicalAnalysisTool instance.

*Line: 937*

---

## Function: 

Detect SMC signals from OHLC data.

Args:
    highs: High price series.
    lows: Low price series.
    closes: Close price series.
    lookback: Swing pivot lookback period (default 5).

Returns:
    Dict with 'signals' list, 'latest_signal', 'structure_state'.

*Line: 423*

---

## Function: 

Detect support and resistance levels.

Args:
    highs: High price series.
    lows: Low price series.
    closes: Close price series.
    lookback: Pivot lookback period.
    tolerance_pct: Clustering tolerance as percentage.

Returns:
    Dict with 'support_levels', 'resistance_levels',
    'nearest_support', 'nearest_resistance'.

*Line: 554*

---

## Function: 

Cluster nearby price levels into zones.

*Line: 625*

---

## Function: 

Initialize the TechnicalAnalysisTool.

Args:
    market_data_tool: Optional MarketDataTool instance for
        auto-fetching data. If None, raw data must be provided.

*Line: 673*

---

## Function: 

Run full technical analysis on raw price arrays.

This is the synchronous path — useful when data is already available.

Args:
    closes: Close price series (minimum 50 bars).
    highs: High price series (defaults to closes).
    lows: Low price series (defaults to closes).
    volumes: Volume series (defaults to flat 1.0).
    symbol: Symbol label for the result dict.
    timeframe: Timeframe label for the result dict.

Returns:
    Comprehensive analysis dict.

*Line: 735*

---

## Function: 

Classify trend direction and strength from EMA alignment + ADX.

EMA trend logic:
  - BULL: EMA9 > EMA20 > EMA50 (aligned bullish)
  - BEAR: EMA9 < EMA20 < EMA50 (aligned bearish)
  - NEUTRAL: EMAs are not aligned

Strength:
  - ADX > 25: strong trend
  - ADX 20-25: moderate trend
  - ADX < 20: weak / no trend

*Line: 798*

---

## Function: 

Compute derived fields: price changes, volume ratio.

Args:
    closes: Close price series.
    volumes: Volume series.

Returns:
    Dict with price_change_1d, price_change_5d, volume_ratio.

*Line: 873*

---

## Function: 

No-op fallback when langchain_core is not installed.

*Line: 26*

---

## Function: 

*Line: 30*

---

