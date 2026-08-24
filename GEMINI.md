# GEMINI.md — Quant Nanggroe AI (Quant Nation)

Canonical instructions in **AGENTS.md**. This is a quick reference.

**Single entry:** `python qna.py [daemon|api|status|stop]`

**Critical:**
- `PYTHONPATH=""` always — Hermes venv leak breaks `pydantic_core`
- Fail-closed: C5 KillSwitch cross-process shared state
- ✅ **Candle Scheduler** — real-time M15/H1/H4/D1 candle-close analysis
- ✅ **Signal Aggregation** — one position per symbol, fixed 0.5% risk
- ✅ **Trade History** — SQLite-backed unlimited persistence
- **TTLCache** wired to EconomicScorer + SentimentScorer
- **mue-x 992 providers** dynamically discovered (no more 760-line manual list)
- **Weekly loss veto** hard-gated on Path-B
- **np.clip → _clamp()** fixed across 8 scoring files (numpy 2.x compat)
- 84 registered strategies, 10 exchange clients, 16 agents
- numpy broken in .venv (Python 3.14 `np.clip` removed — scoring files fixed but other modules may still use numpy)
- pytest env broken (langsmith plugin)

**Commands:**
```bash
launch.bat api              # FastAPI on :8000
guardian_cli.py --once      # Guardian watchtower
ruff check quant_nanggroe/
uv sync
```

**Architecture:**
- 9-stage pipeline in `hedge_fund/portfolio/main.py:run_once()` (555 lines)
- Stage 8 (FusionEngine scoring) = **dead code** — not called
- 4 git remotes, github2 has 4141 diverged files (Next.js dashboard)
- E:\ drive: hidden-regime (COT), mue-x (992 evolved providers), AI-Trader (cache/TTL 1911 lines)
