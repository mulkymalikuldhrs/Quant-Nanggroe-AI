# GEMINI.md — Quant Nanggroe AI (Quant Nation)

Canonical instructions in **AGENTS.md**. This is a quick reference.

**Single entry:** `python qna.py [unified|api|daemon|hedge|status|stop]`

**Critical:**
- `PYTHONPATH=""` always — Hermes venv leak breaks `pydantic_core`
- Fail-closed: C5 KillSwitch cross-process shared state
- ✅ **Scoring FULLY WIRED** — FusionEngine + 8 scorers + MTFEngine (4-frame) + WeightEvolver + Evolution loop active. 173+ tests pass.
- **TTLCache** wired to EconomicScorer + SentimentScorer
- **mue-x 992 providers** dynamically discovered
- **Weekly loss veto** hard-gated on both paths
- **1079 providers** wired (77 engine + 992 mue-x + 10 core)
- **MT5 live** — Valetax demo connected, 29 closed trades
- **HiddenRegimeProvider** + **NewsProvider** (3-tier) wired to scoring
- 84 registered strategies, 10 exchange clients, 16 agents
- numpy 2.5.1 ✅ in .venv. Test environment fixed.

**Commands:**
```bash
launch.bat api              # FastAPI on :8000
ruff check quant_nanggroe/
uv sync
.venv/Scripts/python -m pytest tests/ -v
```

**Architecture:**
- 7-stage pipeline in `hedge_fund/portfolio/main.py:run_once()` (310 lines, refactored)
- FusionEngine + 8 scorers + MTFEngine + WeightEvolver — ALL WIRED
- Evolution loop: journal → scheduler → scanner → disabler → weight_updater
- 4 git remotes, github2 diverged (v2-dashboard branch extracted)
- E: hidden-regime COT, mue-x 992 providers, AI-Trader cache/TTL
