# CLAUDE.md — Quant Nanggroe AI

Short version. Canonical agent instructions in **AGENTS.md** (read it first).

**Single entry:** `python qna.py [unified|api|daemon|hedge|status|stop]`

**Critical:**
- `PYTHONPATH=""` mandatory (Hermes venv leak → `pydantic_core` crash)
- `QNAI_JWT_SECRET` required for API boot
- C5 KillSwitch cross-process shared state
- i7-10th gen, 16GB, no GPU, Windows

**Key facts (verified):**
- 699+ .py files, 77 strategies via `@StrategyRegistry.register`
- 16 agents registered (5 geopolitics), 10 REST exchange clients
- 66/66 kill_switch + risk_checks tests pass
- 9-stage pipeline in `hedge_fund/portfolio/main.py:run_once()`
- `archive/` has orphaned v6.2 artifacts (read-only)

**Commands:**
```
launch.bat api              # API on :8000
launch.bat test             # Tests
.venv/Scripts/python -m pytest tests/test_kill_switch.py -v
.venv/Scripts/python -m pytest tests/test_risk_checks.py -v
ruff check quant_nanggroe/
uv sync
```

See AGENTS.md for full instructions.