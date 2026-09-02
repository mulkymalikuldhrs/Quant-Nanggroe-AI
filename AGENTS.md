# QNA Agent Notes

> **CANONICAL.md is the Single Source of Truth.** Verify every claim against `file:line`. This file is only the hard-earned shortcuts an agent would otherwise guess wrong.

## Setup — Env Is Fragile
- `uv sync` (not pip/poetry). Python `>=3.11`, ruff target `py311`, `uv.lock` is committed. CI installs via `pip install -e ".[dev,ml,data]"` on py3.12.
- **PYTHONPATH must be empty** before any `python` call — Hermes venv leaks `pydantic_core` and crashes imports. Use `launch.bat` / `qna.bat` / `QNA Launcher.bat` (they sanitize) or `set PYTHONPATH=` / `PYTHONPATH=""` in bash.
- `qna.py:27` calls `load_dotenv(".env")` **before** any `quant_nanggroe` import. Standalone scripts must do the same or `QNAI_JWT_SECRET`/`QNA_LIVE_TRADING`/`MT5_*` read as empty.
- `cp .env.example .env` then set `QNAI_JWT_SECRET`+`QNA_ADMIN_API_KEY` (api boot is fail-closed if missing/weak) and `MT5_LOGIN`/`MT5_PASSWORD`/`MT5_SERVER`. `QNA_LIVE_TRADING=0` default; `1` only for live MT5.
- `.env` is gitignored and holds secrets. `config/mt5_accounts.yaml` is also gitignored (local only, Valetax `server: ValetaxIntl-Live2`, `login ~211098748`).

## Commands — Exact
```bash
uv sync
python qna.py daemon        # CandleScheduler M15/H1/H4/D1, 1s tick — the live loop
python qna_tray.py          # Windows tray (qna_tray.bat) — start/stop daemon, open dashboard
python qna.py api           # FastAPI :8000 (needs QNAI_JWT_SECRET)
python qna.py status        # health check
cd dashboard && npm run dev # Next.js 16.2.9 + React 19 :3000
cd dashboard && npm run build && npm run test  # vitest
ruff check .                # line-length 120, select E,F,I
mypy quant_nanggroe/ --ignore-missing-imports  # strict=true in pyproject
pre-commit run --all-files  # ruff --fix + gitleaks + large-file(500kb) + private-key
```

Single test / focused run (use `PYTHONPATH=""`):
```bash
set PYTHONPATH= && python -m pytest tests/test_engine/test_foo.py::TestClass::test_name -q
set PYTHONPATH= && python -m pytest -k "test_candle" -q
set PYTHONPATH= && python -m pytest tests/test_engine/test_strategy_allocation.py tests/test_risk/test_trailing_stop_gate7.py tests/test_engine/test_analytics.py tests/test_engine/test_signal_aggregator.py tests/test_engine/test_ml.py tests/test_engine/test_candle_scheduler.py -q  # core battery
```

CI order (` .github/workflows/ci.yml`): `ruff check .` → `mypy` → `gitleaks` → `pytest tests/ --cov --cov-fail-under=60 -x` (ubuntu+windows, py3.12).

## Repo Boundaries — What Lives Where
- `qna.py` — **only** supported entry point (962 lines). All other entry points archived.
- `quant_nanggroe/` — core package (800+ .py, 228 tests). Key subdirs: `engine/{agentic,execution,risk,backtest,analytics,smc,strategy_allocation}` + `api/` + `connectors/` (MT5). `engine/strategies/` has 83 `@StrategyRegistry.register` strategies.
- `dashboard/` — Next.js 16.2.9 standalone app (`src/app/` 36 pages, 10 api routes). Own `package.json`/`vitest`/`eslint`.
- `tests/` + `quant_nanggroe/tests` — pytest `asyncio_mode=auto`, `testpaths = ["tests","quant_nanggroe/tests"]`.
- `data/` , `paper_state/` , `logs/` — runtime, gitignored. `archive/` — read-only orphan artifacts (never delete silently).
- `CANONICAL.md` — auto-generated SSOT; `README.md` is the human quick-start.

## Critical Gotchas — Will Break Silently
- **Symbols need `.vxc` suffix** on Valetax (bare `EURUSD` is `trade_mode=4`). FX/Commodity only — crypto/stocks eliminated per CANONICAL 15.8.
- **MT5 C-API not thread-safe** — `copy_rates_from_pos` must run in the thread that called `mt5.initialize()`. Executor threads return empty/fail silently. `get_rates` returns `numpy` structured array — never `list()` it (destroys dtype names); use `np.asarray()` directly.
- **Brokers `__init__.py`** — never `import paper` unconditionally; `quant_nanggroe/engine/execution/brokers/paper.py:10` raises `ImportError` when `QNA_ALLOW_PAPER != "1"` (REAL-ONLY default).
- **C5 KillSwitch** — cross-process via `QNA_KILL_SWITCH_STATE_FILE` (`data/kill_switch_state.json`). `L1` daily 0.8% auto-expires; `L2/L3` need manual `CONFIRM_RESET_AFTER_REVIEW`.
- **Signal Aggregation** — one position per symbol enforced at broker-truth level in `engine/execution/manager.py:execute_order()`; fixed 0.5% risk. Signal generation is in `engine/agentic/autonomous.py` (context_gate → aggregation → 9-gate risk).
- **numpy in .venv** — Python 3.14 removed `np.clip` usage here; use `max(min(x,100),-100)`.
- **pytest `langsmith` plugin** — crashes collection; `pip uninstall langsmith` if you see it.

## Key Modules (v8.0.22 — CANONICAL SSOT)
| Module | Purpose |
|--------|---------|
| `qna_tray.py` | Windows tray daemon control |
| `engine/candle_scheduler.py` | M15/H1/H4/D1 candle-close scheduler (1s tick, executor-safe MT5) |
| `engine/candle_events.py` | Thread→async bus → WS `candles` channel |
| `engine/agentic/context_gate.py` | High-impact news blackout veto |
| `engine/auto_retrain.py` | Bayesian re-tune loop + decay guard |
| `engine/trade_history.py` | SQLite unlimited trade history |
| `engine/execution/manager.py` | Guard pipeline → kill switch → risk veto → duplicate-position gate → fill-status gate |
| `engine/execution/signal_aggregator.py` | ONE position per symbol |
| `engine/strategy_allocation.py` | CPCV per-symbol admission |
| `engine/risk/trailing_stop.py` + `trading_profile.py` | Breakeven ratchet + ATR trail / scalp/day/swing SL-TP |
| `engine/committee/agents.py` | 5 specialist agents per pair (bull/bear/risk/macro/execution) |
| `engine/committee/vote_chamber.py` | Weighted consensus + RiskAgent VETO |
| `engine/strategy_evaluator.py` | Rolling Sharpe/win rate, auto-disable |
| `engine/data_pipeline.py` | Finnhub news, CFTC COT, sentiment cache |

## Skills Inventory (v8.0.22 — Hermes→Opencode Bridge 2026-09-02)

> **SSOT:** `CANONICAL.md` v8.0.22 — BAL $1,445, weekly 0 WIB, probe 0/32, CPCV 207, launch.bat 1, manager.py WIB
> Full inventory: `docs/SKILLS.md:1` | Bridge: 63 `hermes-*` copies at `C:\Users\Hi\.opencode\skill\hermes-*:1`

| Source | Expected (task) | Actual Verified | Path:line | Count Method |
|--------|-----------------|-----------------|-----------|--------------|
| D:\Obsidian\DhaherLabs | 40 | **41 SKILL.md** | `D:\Obsidian\DhaherLabs\skills:1` | `Get-ChildItem -Recurse -Filter SKILL.md` |
| E:\skills (mirror) | 41 | **41 SKILL.md** | `E:\skills\skills:1` | `Get-ChildItem -Recurse -Filter SKILL.md` — deduped |
| E:\ai-market-maker\src\agents | 14 | **0** | `E:\ai-market-maker\src\agents:1` | `Test-Path` → False — missing/archived |
| E:\AI-Trader\skills | 6 | **0** | `E:\AI-Trader\skills:1` | `Test-Path` → False — missing |
| D:\repositories\blackhornet\skills | 22 | **22** | `D:\repositories\blackhornet\skills:1` | `Get-ChildItem -Directory` |
| C:\Users\Hi\.opencode\skill | 22→29 | **92 (29 native + 63 hermes-*)** | `C:\Users\Hi\.opencode\skill:1` | `Get-ChildItem -Directory` |
| MCP | 7 | **15 (7 mandatory + 8 ext)** | `C:\Users\Hi\.config\opencode\opencode.jsonc:3` | `ConvertFrom-Json .mcp count` |

**Verification 2026-09-02 (bash timeout 15000):**
```bash
powershell -NoProfile -Command "Get-ChildItem -Path 'D:\Obsidian\DhaherLabs\skills' -Recurse -Filter 'SKILL.md' | Measure-Object | Select -Expand Count"
# → 41 — D:\Obsidian\DhaherLabs\skills:1
powershell -NoProfile -Command "Get-ChildItem -Path 'D:\repositories\blackhornet\skills' -Directory | Measure-Object | Select -Expand Count"
# → 22 — D:\repositories\blackhornet\skills:1
powershell -NoProfile -Command "Get-ChildItem -Path 'C:\Users\Hi\.opencode\skill' -Directory | Measure-Object | Select -Expand Count"
# → 92 — C:\Users\Hi\.opencode\skill:1 (29 native + 63 hermes-*)
powershell -NoProfile -Command "Get-ChildItem -Path 'C:\Users\Hi\.opencode\skill' -Directory | Where-Object { $_.Name -like 'hermes-*' } | Measure-Object | Select -Expand Count"
# → 63 — C:\Users\Hi\.opencode\skill\hermes-*:1
powershell -NoProfile -Command "(Get-Content 'C:\Users\Hi\.config\opencode\opencode.jsonc' -Raw | ConvertFrom-Json).mcp.PSObject.Properties.Count"
# → 15 — C:\Users\Hi\.config\opencode\opencode.jsonc:3
```
Bridge: `mklink /D` requires elevation (`You do not have sufficient privilege` at `C:\Users\Hi\.opencode\skill:1`) → fallback `Copy-Item -Recurse -Force` (4 batches, timeout 15000 each). Idempotent: re-run skips `EXISTS hermes-*`. All Hermes skills now usable by Opencode via `hermes-<name>` prefix. See `docs/SKILLS.md:1` for full file:line table.

**CANONICAL Sync (v8.0.22):**
- **BAL 1445:** ValetaxIntl-Live2 372044706 $1,445 — `CANONICAL.md:4,18`
- **weekly 0 WIB:** `launch.bat weekly-reset` → `data/weekly_override.json` 0 until 2026-09-01 WIB + `data/persistence/risk_COLON_weekly_pnl.json`
- **probe 0/32:** CandleScheduler `probe_empty=0/32` — `session.md:623`
- **CPCV 207:** `data/walk_forward_registry.json` 214 entries (207 WF-validated), `data/cpcv_registry.json` 10 CPCV
- **launch.bat 1:** Single WIB launcher `launch.bat` (198 lines, PYTHONPATH="", TZ=Asia/Jakarta) — legacy archived in `archive/bat_legacy/`
- **manager.py WIB:** `quant_nanggroe/engine/execution/manager.py:176` weekly_pnl_pct WIB handling, kill switch, risk veto

## Non-Negotiable Rules
1. Code is source of truth. Verify against `file:line`.
2. Fail-closed defaults. Phantom/unverifiable = STOP.
3. REAL-ONLY — no paper/sim/mock on live path.
4. Every risk guard must VETO, not just warn.
5. One position per symbol — enforced at broker truth.
6. Committee RiskAgent VETO is absolute — no override, no bypass.
7. Data pipeline returns None on failure (not empty), so committee treats it as unavailable, not neutral.
8. **CANONICAL.md is SSOT — never edit CANONICAL to match docs; edit docs to match CANONICAL v8.0.22**

---

> **SSOT:** `CANONICAL.md` v8.0.22 — BAL $1,445, weekly 0 WIB, probe 0/32, CPCV 207, launch.bat 1, manager.py WIB

---

> **SSOT:** `CANONICAL.md` v8.0.22 — BAL $1,445, weekly 0 WIB, probe 0/32, CPCV 207, vector 6 modul live, risk per-symbol
