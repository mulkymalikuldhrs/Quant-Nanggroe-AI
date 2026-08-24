# QNA Agent Notes

> Full documentation: **[CANONICAL.md](CANONICAL.md)** — Single Source of Truth.

## Critical Gotchas
- **PYTHONPATH must be empty** — use `launch.bat`, `qna.bat`, or `set PYTHONPATH=`
- **QNAI_JWT_SECRET** required for API boot (fail-closed)
- **Symbols need `.vxc` suffix** on Valetax broker
- **FX/Commodity only** — crypto/stocks eliminated per CANONICAL 15.8
- **Signal Aggregation active** — one position per symbol, fixed 0.5% risk
- **numpy broken** in .venv — Python 3.14 removed `np.clip`. Use `max(min(x,100),-100)`
- **pytest env broken** — `langsmith` plugin crashes. `pip uninstall langsmith`
- **C5 KillSwitch** — cross-process shared state via `QNA_KILL_SWITCH_STATE_FILE`

## Exact Commands
```bash
python qna.py daemon        # autonomous trading loop
python qna.py api           # FastAPI :8000
cd dashboard && npm run dev # dashboard :3000
python -m pytest tests/test_engine/test_strategy_allocation.py tests/test_risk/test_trailing_stop_gate7.py tests/test_engine/test_analytics.py tests/test_engine/test_signal_aggregator.py tests/test_engine/test_ml.py tests/test_engine/test_candle_scheduler.py -q  # 61 core regression tests
```

## Key Modules (v8.0.2)
| Module | Purpose |
|--------|---------|
| `engine/candle_scheduler.py` | Real-time M15/H1/H4/D1 candle-close scheduler |
| `engine/trade_history.py` | SQLite-backed unlimited trade history |
| `engine/journal_sync.py` | MT5→journal sync, real PnL |
| `engine/execution/signal_aggregator.py` | ONE position per symbol |
| `engine/strategy_allocation.py` | CPCV per-symbol admission + tuned params |
| `engine/analytics/trade_awareness.py` | what/why/how/lesson per trade |
| `engine/analytics/strategy_scorecard.py` | expectancy/PF/Sharpe from journal |
| `engine/risk/trailing_stop.py` | breakeven ratchet + ATR trail |
| `engine/risk/trading_profile.py` | scalp/day/swing SL-TP profiles |
| `engine/backtest/hyperopt.py` | Bayesian param optimization |
| `engine/smc/native_smc.py` | OrderBlock/FVG/BOS/Sweep native |

## Non-Negotiable Rules
1. Code is source of truth. Verify against `file:line`.
2. Fail-closed defaults. Phantom/unverifiable = STOP.
3. REAL-ONLY — no paper/sim/mock fallbacks on live path.
4. Every risk guard must VETO, not just warn.
5. One position per symbol. Fixed 0.5% risk per pair.
