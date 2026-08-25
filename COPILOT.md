# COPILOT.md — Quant Nanggroe AI (Quant Nation)

See **AGENTS.md** (canonical). Below is a quick reference.

**Entry:** `python qna.py [daemon|api|status]` (hedge/unified/live legacy modes exist)

**Key:**
- `PYTHONPATH=""` mandatory (Hermes venv leak)
- 84 strategies in `quant_nanggroe/engine/strategies/` via `@StrategyRegistry.register`
- Scoring engine wiring disputed between audits — verify core/scoring imports before relying (FusionEngine + 8 scorers + MTFEngine 4-frame overlay + WeightEvolver in `run_once()`)
- KillSwitch C5 in `quant_nanggroe/engine/risk/kill_switch.py`
- 4 git remotes, github2 diverged by 4141 files (full Next.js dashboard)
- E:\ has: hidden-regime COT, mue-x 992 evolved providers, AI-Trader cache/TTL
- 10 exchange clients, 16 agents, 9-stage pipeline
- `archive/` = read-only orphan artifacts

**Ignore:** `paper_state/*.json`, `data/*`, `node_modules/`, `__pycache__/`, `archive/`
**Package:** `uv` (not pip, not poetry)
**Test env broken:** `pip uninstall langsmith` first
