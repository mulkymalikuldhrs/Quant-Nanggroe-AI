# GEMINI.md — Quant Nanggroe AI

Canonical instructions in **AGENTS.md**. This is a quick reference.

**Single entry:** `python qna.py [unified|api|daemon|hedge|status|stop]`

**Critical:**
- `PYTHONPATH=""` always — Hermes venv leak breaks `pydantic_core`
- Fail-closed: C5 KillSwitch cross-process shared state
- 77 registered strategies, 10 exchange clients, 16 agents (5 geopolitics)

**Commands:**
```bash
launch.bat api              # FastAPI on :8000
launch.bat test             # Full test suite
.venv/Scripts/python -m pytest tests/test_kill_switch.py -v
.venv/Scripts/python -m pytest tests/test_risk_checks.py -v
ruff check quant_nanggroe/
uv sync
```

**Architecture:**
- 9-stage pipeline in `hedge_fund/portfolio/main.py:run_once()`
- Wired: ScreenerOrchestrator, ConfluenceScorer, RiskParityAllocator, StressVaR, MatrixProfileDetector
- Orphans: `archive/orphaned_v6.2/` (read-only)