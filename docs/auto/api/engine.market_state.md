# engine.market_state

## Class: 

Detected market regime.

*Line: 28*

---

## Class: 

Confidence level of regime detection.

*Line: 39*

---

## Class: 

Result from a regime detection analysis.

**Methods:** is_stressed

*Line: 49*

---

## Class: 

Configuration for regime detection.

*Line: 68*

---

## Class: 

Detects the current market regime from price data.

Uses a combination of statistical indicators:
* Price trend (linear regression slope)
* Volatility (standard deviation of returns)
* Average Directional Index (ADX) approximation
* Volume profile analysis

Usage::

    detector = MarketRegimeDetector()
    result = detector.detect(closes=[100, 101, 102, ...], volumes=[...])
    print(result.regime, result.confidence)

**Methods:** __init__, detect, _classify_regime, _compute_transitions, _compute_returns, _compute_slope, _compute_volatility, _compute_adx_approx, _compute_max_daily_move, _compute_volume_ratio, history, current_regime, config, stats

*Line: 84*

---

## Function: 

True if market is in a stressed regime.

*Line: 63*

---

## Function: 

*Line: 100*

---

## Function: 

Detect the current market regime from price data.

Parameters
----------
closes:
    List of closing prices (most recent last).
volumes:
    Optional list of volume data.
symbol:
    Symbol being analyzed.

Returns
-------
RegimeResult
    Detected regime with confidence and indicators.

*Line: 104*

---

## Function: 

Classify the market regime based on indicators.

*Line: 184*

---

## Function: 

Compute rough transition probabilities to other regimes.

*Line: 222*

---

## Function: 

Compute daily returns from closing prices.

*Line: 277*

---

## Function: 

Compute linear regression slope of prices.

*Line: 288*

---

## Function: 

Compute standard deviation of returns (volatility).

*Line: 302*

---

## Function: 

Compute a simplified ADX approximation.

Real ADX is complex; this approximation uses directional
movement ratio over the lookback period.

*Line: 311*

---

## Function: 

Compute the maximum absolute daily return.

*Line: 338*

---

## Function: 

Compute recent vs. average volume ratio.

*Line: 345*

---

## Function: 

*Line: 358*

---

## Function: 

Most recently detected regime.

*Line: 362*

---

## Function: 

*Line: 369*

---

## Function: 

Detector statistics.

*Line: 373*

---

