# GEMINI.md — Quant Nanggroe AI (Quant Nation)

Canonical instructions in **AGENTS.md**. This is a quick reference.

**Single entry:** `python qna.py [daemon|api|status]` (hedge/unified/live legacy modes exist)

**Critical:**
- `PYTHONPATH=""` always — Hermes venv leak breaks `pydantic_core`
- Fail-closed: C5 KillSwitch cross-process shared state (`QNA_KILL_SWITCH_STATE_FILE`)
- ✅ **Candle Scheduler** — real-time M15/H1/H4/D1 candle-close analysis
- ✅ **Signal Aggregation** — one position per symbol, fixed 0.5% risk
- ✅ **Auto-Retrain** — hourly Bayesian re-tune + decay guard
- ✅ **Context Gate** — high-impact news blackout veto (±30 min, circuit breaker)
- **Weekly loss veto** hard-gated on Path-B
- Test counts: see CHANGELOG (pytest green as of v8.0.9)

**Commands:**
```bash
python qna.py daemon         # autonomous trading loop
python qna_tray.py           # system tray control
python qna.py api            # FastAPI on :8000
cd dashboard && npm run dev  # dashboard :3000
```

**Architecture:**
- Candle-close pipeline: scheduler → context gate → signal aggregation → 9-gate risk → execution gates → MT5
- FusionEngine wiring disputed between audits — verify core/scoring imports before relying
