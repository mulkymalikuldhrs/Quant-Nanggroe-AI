# agents.smc.enhanced

## Class: 

Represents a swing point in market structure.

*Line: 46*

---

## Class: 

Institutional order block.

*Line: 56*

---

## Class: 

Fair Value Gap / Imbalance.

*Line: 68*

---

## Class: 

Liquidity pool at key price level.

*Line: 79*

---

## Class: 

Complete SMC trade setup.

*Line: 89*

---

## Function: 

Detect Smart Money Concepts patterns in market data.

Args:
    symbol: Trading symbol
    timeframe: Chart timeframe
    pattern_types: Optional comma-separated pattern types to detect

Returns:
    JSON string with detected SMC patterns

*Line: 108*

---

## Function: 

Detect liquidity sweep events.

Args:
    symbol: Trading symbol
    direction: Sweep direction (buy_side, sell_side, both)
    lookback_periods: Number of periods to look back

Returns:
    JSON string with liquidity sweep data

*Line: 142*

---

## Function: 

Analyze institutional footprint in market data.

Args:
    symbol: Trading symbol
    analysis_type: Type of analysis (order_flow, accumulation, distribution)

Returns:
    JSON string with institutional footprint analysis

*Line: 173*

---

## Class: 

Detects institutional order blocks with volume confirmation.

**Methods:** detect

*Line: 208*

---

## Class: 

Detects Fair Value Gaps (3-candle imbalances).

**Methods:** detect

*Line: 246*

---

## Class: 

Detects liquidity pools at key price levels.

**Methods:** detect

*Line: 274*

---

## Class: 

Enhanced Smart Money Concepts agent.

Features:
- Full ICT methodology (BOS, CHoCH, OB, FVG, Liquidity, OTE)
- OrderBlockDetector, FairValueGapDetector, LiquidityLevelDetector
- Tools: smc_pattern_detector, liquidity_sweep, institutional_footprint
- Multi-timeframe analysis capability

**Methods:** __init__, run, analyze_data, _determine_trend, _assess_confidence

*Line: 331*

---

## Function: 

Detect order blocks from OHLCV data.

*Line: 211*

---

## Function: 

Detect fair value gaps from OHLCV data.

*Line: 249*

---

## Function: 

Detect liquidity levels from OHLCV data.

*Line: 277*

---

## Function: 

*Line: 347*

---

## Function: 

Execute SMC analysis.

Args:
    state: Current agent state

Returns:
    State updates with SMC analysis

*Line: 364*

---

## Function: 

Direct SMC analysis on OHLCV data without LLM.

Args:
    data: List of OHLCV dictionaries
    symbol: Trading symbol

Returns:
    SMC analysis results

*Line: 422*

---

## Function: 

Determine trend from data.

*Line: 458*

---

## Function: 

Assess confidence of SMC analysis output.

*Line: 476*

---

## Function: 

No-op fallback when langchain_core is not installed.

*Line: 26*

---

## Function: 

*Line: 30*

---

