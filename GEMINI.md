# GEMINI.md — Quant Nanggroe AI v8.0.22 — CANONICAL SSOT

> **SSOT:** `CANONICAL.md` v8.0.22 — BAL $1,445, weekly 0 WIB, probe 0/32, CPCV 207, launch.bat 1, manager.py WIB

Canonical instructions in **AGENTS.md**. This is a quick reference.

**Single entry:** `python qna.py [daemon|api|status]` (hedge/unified/live legacy modes exist)

**Critical:**
- `PYTHONPATH=""` always — Hermes venv leak breaks `pydantic_core`
- **MT5 C-API not thread-safe** — `copy_rates_from_pos` must run in thread that called `mt5.initialize()`. Executor threads fail silently.
- **get_rates returns numpy** — do NOT call `list()` on MT5 rates; destroys dtype names. Use `np.asarray()` directly.
- Fail-closed: C5 KillSwitch cross-process shared state (`QNA_KILL_SWITCH_STATE_FILE`)
- ✅ **Candle Scheduler** — real-time M15/H1/H4/D1 candle-close analysis
- ✅ **Signal Aggregation** — one position per symbol, fixed 0.5% risk
- ✅ **Auto-Retrain** — hourly Bayesian re-tune + decay guard
- ✅ **Context Gate** — high-impact news blackout veto (±30 min, circuit breaker)
- **Weekly loss veto** hard-gated on Path-B
- Test counts: see CHANGELOG (pytest green as of v8.0.22 — CANONICAL SSOT)

**Commands:**
```bash
python qna.py daemon         # autonomous trading loop
python qna_tray.py           # system tray control
python qna.py api            # FastAPI on :8000
cd dashboard && npm run dev  # dashboard :3000
```

**Architecture:**
- Candle-close pipeline: scheduler (probe 0/32, 1s tick, M15/H1/H4/D1) → context gate → signal aggregation (CPCV 207) → 9-gate risk (manager.py WIB weekly 0) → execution gates → MT5 (BAL $1,445)
- FusionEngine wiring disputed between audits — verify core/scoring imports before relying
- **Live:** `launch.bat` single WIB launcher, ValetaxIntl-Live2 372044706 | **Skills:** see `docs/SKILLS.md` + `AGENTS.md` (41+41+29+7 MCP)

---

> **SSOT:** `CANONICAL.md` v8.0.22 — BAL $1,445, weekly 0 WIB, probe 0/32, CPCV 207, launch.bat 1, manager.py WIB

---

> **SSOT:** `CANONICAL.md` v8.0.22 — BAL $1,445, weekly 0 WIB, probe 0/32, CPCV 207, vector 6 modul live, risk per-symbol
