# COPILOT.md — Quant Nanggroe AI (Quant Nation)

See **AGENTS.md** (canonical). Below is a quick reference.

**Entry:** `python qna.py [unified|api|daemon|hedge|status|stop]`

**Key:**
- `PYTHONPATH=""` mandatory (Hermes venv leak)
- 1079 providers total: 77 engine + 992 mue-x + 10 core, all wired
- ✅ **Scoring FULLY WIRED** — FusionEngine + 8 scorers + MTFEngine (4-frame overlay) + WeightEvolver in `run_once()`. 173+ tests pass.
- ✅ **Evolution loop** — 8 files integrated: journal, scheduler, scanner, disabler, weight_updater
- ✅ **MT5 live** — Valetax demo, $1,099, 29 closed trades
- 4 git remotes, github2 diverged by 4141 files (v2-dashboard branch extracted)
- E:\ has: hidden-regime COT, mue-x 992 evolved providers, AI-Trader cache/TTL
- 10 exchange clients, 13 functional agents, 7-stage pipeline
- `archive/` = read-only orphan artifacts

**Ignore:** `paper_state/*.json`, `data/*`, `node_modules/`, `__pycache__/`, `archive/`
**Package:** `uv` (not pip, not poetry)
**Tests:** `pytest tests/ -v` — 173+ passing
