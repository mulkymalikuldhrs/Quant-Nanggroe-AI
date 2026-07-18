# Quant Nanggroe AI — Agent Instructions

## How to Read This Repo
Read in this order before making changes:
```
README → 00_VISION → 01_PRD → 02_ARCHITECTURE → 15_CONTEXT → 16_MEMORY
→ 04_API → 12_TASKS → 48_AUDIT → 17_GLOSSARY → 14_RULES
```
`48_REPOSITORY_AUDIT.md` is the single most important doc for an agent — it documents exactly which API routes the frontend expects but the backend doesn't provide.

## Entry Points
- **Primary**: `qna.py` — unified launcher (modes: `cli`, `api`, `daemon`, `web`, `status`, `stop`). The ONLY root entry point. All others have been deleted.
- **CLI**: `qnai` command via `quant_nanggroe/cli.py:main` (registered in `pyproject.toml` as `[project.scripts] qnai`).
- **API**: `quant_nanggroe/api/app.py:create_app()` — FastAPI factory. `bootstrap_env()` and `load_dotenv()` run at import time.
- **Engine**: `quant_nanggroe/engine/agentic/autonomous.py:AutonomousPipeline` — `run()` / `run_batch()` / `load_strategies()`. Singleton via `get_autonomous_pipeline()`.
- **Windows**: `launch.bat` boots both backend (uvicorn) + frontend (Next.js dashboard).

## What Not to Change Without Approval
- API contract (response envelope, endpoint paths).
- Risk engine logic (`engine/risk/` — Kelly, VaR, drawdown limits, sector limits, kill switch thresholds).
- State file format in `paper_state/`.
- Agent registration in `qna.py` (`DEFAULT_AGENTS` dict).

## How to Update Docs
- `docs/` has 32 active files (numbered 00-49, minus archived). Stale docs are in `archive/docs/`.
- Doc changes in same PR as code changes (`14_RULES` rule 3, `16_MEMORY` pitfalls 1-2).
- Use ADR format for architecture decisions (`11_DECISIONS.md`).

## Commands
```sh
# Test (quick)
make test-quick                          # skip slow/integration
poetry run pytest tests/ -x -q           # fast fail, quiet
poetry run pytest tests/path/to_test.py  # single file

# Lint → typecheck → test (CI order)
make lint          # ruff check quant_nanggroe/ tests/
make typecheck     # mypy quant_nanggroe/ (strict, no untyped defs)
make test-cov      # pytest + coverage

# Run
make run           # uvicorn dev server on :8000
make run-dashboard # Next.js dev server in dashboard/
poetry run qnai    # CLI mode

# Miscellaneous
poetry run pytest tests/ -x -q            # ~70s, 420+ tests
```

## Architecture Pitfalls
- **`RiskCheckGate` is an alias** for `ConstitutionalRiskGuard` (line 425 of `checks.py`). Both names refer to the same class.
- **Kill switch unit mismatch**: RiskManager passes P&L as percentages (0-100), but KillSwitch expects fractions (0-1). `ExecutionManager.execute_order()` converts via `/100.0` at the boundary.
- **Strategy auto-discovery**: Engine scans `engine/strategy/strategies/` for any `.py` file exporting a class ending in `Strategy`.
- **`conftest.py` overrides `DATABASE_URL`** at import time to `sqlite+aiosqlite:///test_qna.db` with test-only JWT/secret keys.
- **JWT_SECRET sentinel**: Default `__UNSET_QNAI_JWT_SECRET__` causes boot refusal. Set `QNAI_JWT_SECRET=dev` for local dev.
- **Risk limits**: Single source of truth is `engine/risk/constants.py`. Some limits are env-driven via `QNAI_*` (per-trade, daily/weekly loss), others are hardcoded Final (leverage, position size, sector exposure, daily trades).
- **Constitutional risk is 3-layer**: settings → constants → checks/manager. All imports must come from `constants.py`, not settings directly.

## Constraints
- `asyncio_mode = "auto"` for pytest (no need for `@pytest.mark.asyncio` on async tests).
- mypy: `strict = true`, `disallow_untyped_defs = true`. Every function must be typed.
- ruff: line length 120, select `E,F,I`, ignore `E501`.
