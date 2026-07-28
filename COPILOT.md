# COPILOT.md — Quant Nanggroe AI

See **AGENTS.md** (canonical). Below is a quick reference.

**Entry:** `python qna.py [unified|api|daemon|hedge|status|stop]`

**Key:**
- `PYTHONPATH=""` mandatory (Hermes venv leak)
- 77 strategies in `quant_nanggroe/engine/strategies/` via `@StrategyRegistry.register`
- KillSwitch C5 in `quant_nanggroe/engine/risk/kill_switch.py`
- 9-stage pipeline in `hedge_fund/portfolio/main.py:run_once()`
- 10 exchange clients in `quant_nanggroe/exchange/clients/`
- 16 agents (5 geopolitics) in `quant_nanggroe/agents/`
- `archive/` = read-only orphan artifacts

**Ignore:** `paper_state/*.json`, `data/*`, `node_modules/`, `__pycache__/`, `archive/`
**Package:** `uv` (not pip, not poetry)
**Test:** `.venv/Scripts/python -m pytest tests/ -v --tb=short`