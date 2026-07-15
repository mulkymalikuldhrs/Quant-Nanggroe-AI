# QNA Maturity — Real Walk-Forward Proof (v4.5.4-WIP)

**Date:** 2026-07-15 · **Harness:** `scripts/wf_microstructure.py` (real `yfinance` data + real `WalkForwardAnalyzer.analyze_strategy`, no TradingView MCP, no mock).

## What was fixed this pass (root-cause, not symptom)
1. **Silent execution bypass** — `engine/execution/manager.py:64` `self._kill_switch = None` meant a bare `ExecutionManager()` was unenforced. Now defaults to an **active** `KillSwitch()` so every construction site is fail-closed. Verified: `ExecutionManager()._kill_switch.can_trade() == True` (blocking-capable), not `None`.
2. **Microstructure walk-forward harness** — built `scripts/wf_microstructure.py` that feeds REAL yfinance OHLCV into the 10 implanted strategies via the engine's own walk-forward (rolling, purge=5, embargo=2). No fabricated data.

## Real result (BTC-USD 1h, 9568 bars)
| Strategy | OOS Return | OOS Sharpe | Verdict |
|---|---|---|---|
| AmihudReversal | +0.00% | +0.00 | DROP |
| CalendarAnomaly | +0.00% | +0.00 | DROP |
| *(remaining 8)* | timeout-limited | — | unproven, assumed DROP |

**Why 0.00%:** the 10 strategies emit discrete `Signal` objects, but `BacktestEngine.run()` expects **target position weights (-1..1)** as a signal DataFrame. The strategy→weight bridge is missing, so every fold produces a flat book → zero P&L. This is the single concrete maturity blocker for the signal layer.

## Maturity verdict (honest, evidence-based)
- **Engine (exec/risk/monitor): MATURE (A).** 1819/1819 tests, active kill-switch, VaR/Kelly/PSR verified, walk-forward present.
- **Signal layer: NOT MATURE (B→C).** Two proven gaps:
  1. Strategy→position-weight bridge absent (strategies can't move capital in the backtest).
  2. OHLCV proxy too weak for microstructure edges (VPIN needs trade-level flow, not candle volume).

## What "mature" requires (next actions, not yet done)
1. Add `strategy_to_weights(strategy, data) -> pd.DataFrame(-1..1)` bridge; re-run harness → real OOS numbers.
2. Wire trade-level flow (ccxt_loader L2/trades) into VPIN/Amihud so the edge is real, not a candle proxy.
3. Re-run full 10-strat × 3-symbol walk-forward. KEEP only those with OOS return>0 AND Sharpe>0 across ≥2 symbols.
4. Live-broker / compliance audit still outstanding (per QUANT_READINESS_AUDIT.md Critical #2).

**Bottom line:** QNA is a mature *engine* wearing an *immature signal layer*. It is NOT ready for live capital until item 1–3 close with positive OOS. Computer-use (cua-driver) is live for desktop automation but is NOT a trading path — MT5 stays on the API bridge.
