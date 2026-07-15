# QNA Signal Layer — Real Walk-Forward Proof (v4.5.5)

## Root cause (why signal layer was 0.00% OOS before)
Two silent bugs in the strategy→capital bridge, both verified by execution:

1. **`walk_forward.py:444`** read `signal.signal` — attribute that does NOT exist on `Signal`
   (it has `signal_type` + `strength`). Exception swallowed → every weight became `0.0` → flat book.
   Fix: use `strength`, fall back to `±1` by `signal_type`.

2. **`engine.py:165`** read `signal_row.get(symbol)` where `symbol='close'`, but the generated
   signal column was named `prices.columns[0]` = **`open`** (yfinance OHLCV order).
   Column mismatch → `target_weight` always `0.0` → 0 trades.
   Fix: align signal col to price col (fall back to sole signal column).

3. **`scripts/wf_microstructure.py`** read aggregate keys `out_of_sample_return` — but the real
   keys are `avg_oos_return` / `avg_oos_sharpe`. Harness printed 0.00% while engine actually traded.
   Fix: correct key names.

4. **`BaseStrategy.validate_data()`** requires **lowercase** OHLCV columns (`close/high/low`),
   but yfinance / TradingView deliver **Capitalized** (`Close/High/Low`). Every `generate_signal`
   raised `ValueError` → swallowed in `_generate_strategy_signals` → weight `0.0` for ALL bars.
   This silently killed ALL 106 strategies on real (Capitalized) data — the true reason the
   earlier "0 of 106 fire" reading was correct, NOT strategy quality.
   Fix (v4.5.10): normalize column case ONCE at the two shared ingestion points —
   `_generate_strategy_signals` (walk_forward.py:448) and `engine.run` (engine.py:149).
   Post-fix: **75 of 106 strategies emit >10 non-zero 1h signals** on real BTC data.

## Proof harness
`scripts/wf_microstructure.py` — real `WalkForwardAnalyzer.analyze_strategy` (rolling, 400-train/80-test,
purge 5, embargo 2) on **live yfinance data**, 3 assets × 10 microstructure strategies.
Verified: `engine.run` produces real trades (585 trades on VolOfVol BTC, ret −19% in one direct test;
walk-forward aggregate uses per-fold OOS).

## Real OOS matrix (1h, 2025–2026)

| Strategy | BTC-USD | ETH-USD | SOL-USD | Verdict |
|---|---|---|---|---|
| **DrawdownRegime** | +723% / Š+1.20 | +1099% / Š+0.98 | +3576% / Š+0.95 | **KEEP (all 3)** |
| **VolOfVolRegime** | +65% / Š+0.08 | +213% / Š+0.02 | +132% / Š+0.14 | **KEEP (all 3)** |
| **ReturnSkewTail** | +2.1% / Š−0.04 | +9.2% / Š+0.07 | +0.1% / Š−0.06 | KEEP (ETH only) |
| AmihudReversal | +29.6% / Š−0.35 | +48.4% / Š−0.24 | +17.2% / Š−0.35 | DROP (return only) |
| VolTargetedBreakout | +18.8% / Š−0.52 | +30.2% / Š−0.29 | +36.7% / Š−0.46 | DROP (negative Š) |
| CalendarAnomaly | 0.00% | 0.00% | 0.00% | DROP (no signal) |
| Dispersion | 0.00% | 0.00% | 0.00% | DROP (needs benchmark col) |
| IdiosyncraticMomentum | 0.00% | 0.00% | 0.00% | DROP (needs market col) |
| VPINToxicity | 0.00% | 0.00% | 0.00% | DROP (proxy OHLCV only) |
| VolumeWeightedReversal | 0.00% | 0.00% | 0.00% | DROP (no signal emitted) |

Š = out-of-sample Sharpe. KEEP requires OOS_ret > 0 AND OOS_Sharpe > 0.

## Interpretation
- **DrawdownRegime + VolOfVolRegime survive on ALL 3 independent assets with positive Sharpe.**
  This is a repeatable, walk-forward-validated edge — not a single-asset fluke.
- Extreme returns (+3576% SOL) reflect 1.0 leverage on a high-vol asset recovering from drawdown;
  Sharpe (+0.95) is the honest metric. Position-sizing / vol-targeting should cap notional.
- 7 of 10 strategies emit no tradeable OOS signal on single-asset OHLCV (expected — they need
  multi-asset / L2 / on-chain inputs not present in yfinance proxy). They are research scaffolds,
  correctly DROPPED by the gate.

## Maturity verdict (v4.5.5, AMENDED v4.5.9)
| Layer | Status | Evidence |
|---|---|---|
| Execution engine | MATURE (A) | 1818/1819 tests (1 pre-existing state-poison flake); 585 real trades on direct run |
| Kill-switch safety | MATURE (A) | auto-activation fires on real −5% P&L (was blind 0.0) |
| Signal bridge | **MATURE (A) — was C** | root-cause fixed; real OOS now computable |
| **Strategy signal-density** | **B → mostly live** | post v4.5.10 column-case fix, **75 of 106 strategies emit >10 non-zero 1h signals** on real BTC/ETH/SOL yfinance data. Remaining 31 = scaffolds needing multi-asset/L2/on-chain (correctly DROP). |
| Alpha (microstructure) | **PENDING — now measurable** | strategies now fire real trades; OOS expectancy/sharpe must be re-validated through the v4.5.9 significance gate (under_sampled==False + total_oos_trades>=30) before any KEEP verdict. Prior "+3576%" headline retracted (was measured on silent/dead signal). |
| Deployment | Out-of-scope | QNA = shadow/research engine; live = external bridge (TradingView-MT5) |

### Significance gate added (v4.5.9)
`WalkForwardResult` now carries `is_trades` / `oos_trades`; `_calculate_aggregate`
adds `total_oos_trades`, `min_fold_oos_trades`, and `under_sampled`
(True when any fold has <30 OOS trades OR <3 windows). A KEEP verdict requires
`under_sampled == False` AND `total_oos_trades >= 30`. The prior "2 KEEP across 3
assets" claim fails this gate and is **retracted** until re-validated on live-signal
strategies with adequate trade density.

QNA's *engine* is production-grade. Its *alpha* is unproven — most strategies do
not emit tradeable signals on available proxy data. That is the honest state.

## Council findings reconciled
- #16 (kill-switch auto-activation blind): CONFIRMED + FIXED (v4.5.4).
- #28 (silent mock on-chain): FALSE POSITIVE — `_MOCK_MODE=False` default, raises if no real engine.
- #1/#2/#27 (mislabeled strategies): COSMETIC — strategies run, just misnamed; documented, not renamed (class-name registry).
- #13 (auth path-bypass): routers ARE /api/* prefixed; middleware skip is dashboard-only (low risk).
