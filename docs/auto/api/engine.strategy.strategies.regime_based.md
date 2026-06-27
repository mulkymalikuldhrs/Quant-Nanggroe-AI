# engine.strategy.strategies.regime_based

## Class: 

HMM-driven regime detection with per-regime switching and cost controls.

Signal: float in [-1, 1] -> SignalType + confidence. >0 = BUY, <0 = SELL, 0 = flat.

Parameters:
    n_regimes: 2-4 (default 3). hmm_lookback: training window (default 252).
    covariance_type: HMM cov type (default "full").
    regime_stability_bars: min bars before regime switch acted on (default 5).
    bull_strategy/bear_strategy/range_strategy/high_vol_strategy: per-regime behavior.
    max_position: max |position| in [-1,1] (default 1.0).
    transaction_cost_bps: one-way cost bps (default 10.0).
    min_trade_interval_bars: min bars between trades (default 3).
    symbol: for Signal (default "ASSET").

**Methods:** __init__, required_columns, warmup_period, generate_signal, detect_regime, _detect_hmm, _detect_fallback, _compute_features, _fit_hmm, _label_regimes, _regime_signal, _exit_signal

*Line: 37*

---

## Function: 

*Line: 53*

---

## Function: 

*Line: 75*

---

## Function: 

*Line: 78*

---

## Function: 

*Line: 81*

---

## Function: 

*Line: 119*

---

## Function: 

*Line: 135*

---

## Function: 

*Line: 150*

---

## Function: 

*Line: 169*

---

## Function: 

*Line: 179*

---

## Function: 

Map HMM states to semantic regimes by sorting on mean return.

*Line: 209*

---

## Function: 

*Line: 229*

---

## Function: 

*Line: 254*

---

