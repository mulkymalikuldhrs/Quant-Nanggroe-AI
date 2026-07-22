# QNA Forensic Code Audit — Deep Map & Wiring Verification

> Repo: `D:/repositories/Quant-Nanggroe-AI-worktree` (worktree)
> Scope: ENTIRE repo map, wired-vs-dead/stub classification, inconsistencies, production-readiness.
> Method: every claim below is backed by `file:line` evidence gathered via `terminal find` / `search_files` / `read_file`. **No files were modified.**

---

## 0. Executive Summary (harsh & precise)

QNA is a **large, aggressively accreted monorepo** (~4,200-line root `hedge_fund.py`, 111 canonical strategy files, 21 legacy strategy files, 140 external MUE-X gene modules). It *does* trade live to MT5 (the `build_execution_manager()` path is real, fail-closed, and well-commented). However the codebase is **two codebases bolted together** with an unresolved identity crisis:

1. **Two parallel strategy systems** with the *same class name* `StrategyRegistry` in two modules — only the **legacy** one (`engine/strategies/registry.py`) is wired; the **canonical** one (`engine/strategy/registry.py`, walk-forward) is imported **only by tests + one script**.
2. **The MUE-X gene-store (the "evolved" strategies) is consumed ONLY by the legacy root `hedge_fund.py`** via a hard-coded `E:/mue-x/genes/qna_strategies` sys.path insertion. It **bypasses BOTH registries entirely.** Genes never reach the canonical `StrategyRegistry` and never reach `engine.strategies.registry`. This is the central "bypass" the brief asked about — **confirmed**.
3. **The "single hedge fund" maturation target is not actually wired** — the canonical/strategy trees are not imported at package load; the live heartbeat runs through `live_engine.py` + `engine_production_bridge.py`, which load *legacy* `engine.strategies.registry`.
4. **The `/api/strategy/registry` endpoint returns HARD-CODED FAKE data** (`strategy.py:14-24`) — the dashboard's strategy list is theatre.
5. **Phantom route collisions** exist (e.g. `/api/security/events` defined in 3 routers).
6. **Dashboard conflict is real**: root `dashboard.py` (FastAPI, port **5050**, stub) vs `dashboard/` (Next.js, proxies to port **8000**). Both are launched by the `.bat` launchers; the Next.js app is the real UI, the `dashboard.py` is a legacy throwaway.

**Verdict:** Live-trading core is production-credible (fail-closed MT5, real risk manager). Everything *above* the execution layer — registries, API strategy endpoints, the "evolved gene" pipeline, and the dashboard — is a patchwork of prototype + stub + duplicate code that will mislead anyone who trusts the interface names.

---

## 1. Repository Tree Map (high level)

Top-level package: `quant_nanggroe/` plus many root-level legacy scripts (`hedge_fund.py`, `live_engine.py` lives *inside* `quant_nanggroe/`, `trading_loop.py`, `risk_guard.py`, `strategy_registry.py`, `dashboard.py`, etc.).

Key subtrees:

| Path | Role | Status |
|---|---|---|
| `quant_nanggroe/engine/strategy/` | **Canonical** tree: `registry.py` (walk-forward), `loader.py`, `parser.py`, `schema.py`, `strategy_selector.py`, `strategies/` (111 strategy classes) | Mostly **ORPHANED** — `registry.py` not wired to runtime |
| `quant_nanggroe/engine/strategies/` | **Legacy** tree: `registry.py` (class-based), `base.py`, 21 strategy files, `__init__.py` auto-loads all | **WIRED** (live path) |
| `quant_nanggroe/engine/execution/` | `builder.py`, `brokers/mt5_adapter.py`, `manager.py`, `base.py`, `brokers/paper.py` | **WIRED + production-grade** |
| `quant_nanggroe/connectors/mt5_broker.py` | Live MT5 connector (fail-closed) | **WIRED** |
| `quant_nanggroe/engine/risk/manager.py` | Risk manager, 1049 lines | **WIRED + substantial** |
| `quant_nanggroe/api/` | FastAPI app + 30+ routers | Wired, but **stub/compat routers present** |
| `dashboard/` | Next.js UI (real) | Prototype-grade (build_err.log present) |
| `hedge_fund.py` (root) | 4,244-line legacy monolith, the **actual live HF entry** | **LEGACY / live but sprawling** |
| `E:/mue-x/genes/qna_strategies/` (outside repo) | 140 MUE-X evolved gene modules | Consumed only by `hedge_fund.py` |

> Note: root `quant_nanggroe/engine/strategy/__init__.py` **does** import `registry` (so the canonical registry module loads *if* the package imports `quant_nanggroe.engine.strategy`), but **no runtime entrypoint imports `engine.strategy` for strategy registration** — only `loader`, `parser`, `multi_timeframe`, `backtest_adapter` are referenced (adaptive_integration.py:73,180; backtest/auto_tune.py:23; agentic/adapters.py:172). The canonical `registry.StrategyRegistry` class is never populated at runtime.

---

## 2. (a) Strategy Registry Interface — VERIFIED

### Two registries, same class name, divergent shape

**Canonical** — `quant_nanggroe/engine/strategy/registry.py`
- `class StrategyRegistry:` at `:120`. It is a **metadata/performance store** (`StrategyMetadata`, `WalkForwardResult`). Its `register()` signature is `register(name, display_name, description, params_schema, timeframe, asset_classes, status)` — it stores metadata dicts, **not strategy classes** (`:126-146`). It is **NOT** a class registry and has **no `generate_signal` method at all**.
- Wired? **NO.** Only imported by: `scripts/alpha_destruction.py:383`, `tests/test_engine/test_factors.py:22`, `tests/test_strategy/test_registry.py:11`. Not imported by any runtime module.

**Legacy / HF** — `quant_nanggroe/engine/strategies/registry.py`
- `class StrategyRegistry:` at `:15`. A **class registry**: `register(strategy_class)` stores `Type[Strategy]` keyed by `strategy_class.name` (`:22-34`), with `create()`, `create_all()`, `get()`, `count()`.
- Wired? **YES.** Imported by 21 strategy modules via `@StrategyRegistry.register` decorator (e.g. `algebra.py:17`, `wyckoff.py:15`, `smc_strategy.py:15`, `mean_reversion.py:17`, `msnr.py:22`) and consumed by `engine_production_bridge.py:101`, `engine/live/adaptive_integration.py:74`, `engine/strategy/strategy_selector.py:20`, `engine/strategy/loader.py:70`.

**Interface method name — the brief's hypothesis is WRONG, corrected here:**
- The brief claimed canonical uses `generate_signal` and legacy/HF uses `generate_signals`. In reality **BOTH base classes define `generate_signal` (singular):**
  - Legacy base `engine/strategies/base.py`: `@abstractmethod def generate_signal(self, data, **kwargs) -> StrategySignal` at `:109-110`.
  - Canonical base `engine/strategy/strategies/base_strategy.py`: `@abstractmethod def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]` at `:46-47`.
- `generate_signals` (**plural**) exists in **neither** registry base. It appears only in **legacy/adapter strategy bodies** that are NOT part of the canonical interface:
  - `engine/strategies/dhaher_system.py:202`, `engine/strategies/smc_strategy_OLD.py:20`, `engine/strategies/kronos_wrapper.py:148,256`, `engine/strategies/tradebobby_smc_scanner.py:461,506`, `engine/strategy/backtest_adapter.py:96,155`, plus the HF monolith's `generate_signals` methods (`engine_production_bridge.py:122`, `engine/live/adaptive_integration.py:122`, `engine/strategy/strategy_selector.py:300`, `engine/models/signal_generator.py:84`, `backtest/strategy_factory.py:28`).
  - These are a **parallel signalling convention** (return a DataFrame/list) used by the legacy `live_engine` aggregate path, **not** the registry contract.

### Class-name collisions — CONFIRMED (duplicate class names across the two trees)

Files present in BOTH `engine/strategies/` and `engine/strategy/strategies/` with the **identical class name** but different base classes:

| Class | Legacy (`engine/strategies/…`) | Canonical (`engine/strategy/strategies/…`) |
|---|---|---|
| `WyckoffStrategy` | `wyckoff.py:21` (extends `Strategy`) | `wyckoff_strategy.py:41` (extends `BaseStrategy`) |
| `MeanReversionStrategy` | `mean_reversion.py:23` (extends `Strategy`) | `mean_reversion.py:34` (extends `BaseStrategy`) |
| `SMCStrategy` | `smc_strategy.py:21` (extends `Strategy`) | `smc_strategy.py:34` (extends `BaseStrategy`) |

Additional collisions surfaced: `DhaherSystem`, `ICTStrategy`, `KronosEnsembleStrategy`, `KronosSignalProvider`, `_FallbackKronosPredictor` exist in both trees (grep `^class` across both dirs). And **`live_engine.py` re-declares `SMCStrategy` (`live_engine.py:176`) and `MeanReversionStrategy` (`live_engine.py:217`)** — a *third* copy, with a **different method name** (`analyze(candles)` returning `"buy"/"sell"/"hold"` strings, NOT `generate_signal`). So there are effectively **3 competing definitions** of `SMCStrategy`/`MeanReversionStrategy`.

> **Impact:** Any code importing `from quant_nanggroe.engine.strategies.smc_strategy import SMCStrategy` vs `from quant_nanggroe.engine.strategy.strategies.smc_strategy import SMCStrategy` gets a structurally different object (different base, different signal method, different `Signal` type). This is a latent landmine for the "single HF" consolidation.

---

## 3. (b) Live MT5 Execution Path — VERIFIED (production-credible)

The execution path is the **most coherent part** of the repo. Chain:

1. **`engine/execution/builder.py`** — `build_execution_manager(allow_live=None)` (`:30`) is the single source of truth. Fail-closed: `allow_live` defaults to `QNA_LIVE_TRADING=1` env (`:52-53`). Builds `ExecutionManager`, attaches `KillSwitch` + `RiskManager` BEFORE live wiring (`:44-47`), adds `PaperBroker` as safe fallback (`:49-50`), then for each MT5 account calls `MT5Broker(...).connect()` and adds `MT5ExecutionBroker(mt5)` with `primary=is_live` (`:68-84`). Critically, sets `em._risk_manager.set_broker_handle(mt5)` so the risk veto reads REALIZED PnL (`:82`).
2. **`connectors/mt5_broker.py`** — `class MT5Broker(BrokerConnector)` (`:20`). Fail-closed: missing lib raises (`:32-33`); `connect()` retries 3× with timeout, raises on IPC failure — **no silent paper fallback** (`:42-65`). `place_order()` carries SL/TP into the MT5 request (`:91-94`) — closes the "naked position" bug. Also exposes `history_deals_get()` (`:116`) so RiskManager can read realized PnL.
3. **`engine/execution/brokers/mt5_adapter.py`** — `class MT5ExecutionBroker(Broker)` (`:31`) bridges the `connectors.BrokerConnector` (sync) ABC to `engine.execution.base.Broker` (async) (docstring `:1-5`). `submit_order()` maps the engine `Order` → connector `ConnOrder` carrying SL/TP (`:74-99`). `get_account()` reads REAL equity/balance (`:56-72`).

**Verdict:** Wired, fail-closed, SL/TP carried end-to-end, kill-switch shared-state configured in `app.py:208-212`. This is the part you can trust. (Note: MT5 symbol casing edge-case `Valetax .vx` handled at `connectors/mt5_broker.py:9-17`.)

---

## 4. (c) Risk Manager — VERIFIED (substantial, wired)

`engine/risk/manager.py` — `class RiskManager:` at `:85`, **1049 lines**. Real constitutional limits (MAX_RISK_PER_TRADE, MAX_DAILY_LOSS, MAX_WEEKLY_LOSS, MAX_DRAWDOWN) imported from `risk/constants.py` (`:32-47`). 9-checkpoint gate via `RiskCheckGate` (`check_trade()` `:182-298`). Kelly + VaR + drawdown + correlation-regime monitors instantiated (`:111-119`).

**Key P0 fix (phantom-veto hole):** `_sync_realized_pnl()` (`:152-179`) pulls today's + this-week's realized PnL from the live MT5 handle via `history_deals_get`, so the daily/weekly-loss veto sees real numbers instead of `0.0` forever. Handle attached by the builder at `builder.py:82` (`set_broker_handle`). `set_broker_handle()` at `:144-150`. `_mt5_handle` default `None` (`:141`).

**Verdict:** Wired and meaningful. Minor: `check_trade` still accepts `daily_pnl_pct`/`weekly_pnl_pct` args (`:191-192`) but those are overridden by the live `_sync_realized_pnl` path — the args are effectively dead in the live flow (documentation drift, not a bug).

---

## 5. (d) API `app.py` Routes — VERIFIED (phantom route collisions)

`api/app.py` `create_app()` wires **38 routers** (`:302-379`). No single router var is `include_router`'d twice (verified `uniq -c` → all count 1). **BUT** five routers share the **bare `/api` prefix** (`ecosystem`, `colony`, `security`, `tools`, `qna_status` at `app.py:349,350,370,371,379`), and their sub-paths **collide**:

- **`/api/security/events` defined in THREE places:**
  - `api/routes/security.py:33`
  - `api/routes/ecosystem.py:45`
  - `api/routes/security_tools_stub.py:14`
- **`/api/tools/list` and `/api/tools/{tool_id}/execute` defined TWICE:**
  - `api/routes/tools.py:35,53`
  - `api/routes/security_tools_stub.py:20,26`
- **`/api/list`** is defined in 9 routers (`backtest.py:278`, `channels.py:17`, `colony_stub.py:14`, `council.py:17`, `debate.py:23`, `memory_stub.py:32`, `personas.py:17`, `signal_generator.py:25`, `strategies.py:149`) — distinct prefixes make these non-fatal, but the bare-`/api` collisions above are **genuine FastAPI route-shadowing** (last registered wins; the real `security.py` `/security/events` is shadowed by `ecosystem.py:45` because ecosystem is included first at `app.py:349` vs security at `:370` — order-dependent behavior).

**Stub/compat routers present in the live app** (the brief's "dead/stub" flag): `wiring_compat.router` (`:372`), `memory_stub.router` (`:374`), `colony_stub.router` (`:375`), `security_tools_stub.router` (`:376`). `wiring_compat.py` openly returns `"status": "not_implemented"` stubs (`:22-27`, `:34-41`, `:45-52`) and **hard-coded fake trades** when the broker is unavailable (`:79-82`). `memory_stub`, `colony_stub`, `security_tools_stub` are pure stubs (routes at `memory_stub.py:14-32`, `colony_stub.py:14-32`, `security_tools_stub.py:14-44`).

**Fake strategy registry endpoint:** `api/routes/strategy.py:14-24` — `/api/strategy/registry` returns **hard-coded** strategy list (`sharpe: 1.8`, etc.) with comment "ponytail: wire to backend loader once strategy registry parsing is active." The dashboard that calls this shows **invented Sharpes**.

---

## 6. (e) Dashboard Conflict — VERIFIED

**Two dashboards, two ports, both launched:**

1. **Root `dashboard.py`** — FastAPI stub. Title "Dhaher Hedge Fund Dashboard v5.0.0" (`dashboard.py:13`). Reads a local `data/hedge_fund_trades.csv` and renders hard-coded strategy rows (Wyckoff/MeanRev/SMC "Live", `dashboard.py:40-47`). Launched on **port 5050** by `start-dashboard.bat:6`, `launch-hedgefund.bat:28`, `autonomous-loop.bat:22` (`uvicorn dashboard:app --host 127.0.0.1 --port 5050`). This is a **stub / throwaway** — it does not read live engine state.
2. **`dashboard/` (Next.js)** — the real UI. `package.json` (Next 16.2.9, React 19). `next.config.ts:9-19` proxies `/api/:path*` and `/health` to `NEXT_PUBLIC_API_URL` or **`http://localhost:8000`** (the FastAPI app's port). So the real frontend expects the API on 8000; the legacy `dashboard.py` is a separate 5050 stub that nothing in the Next app uses.

**Conflict:** The `.bat` launchers start BOTH an API (implicitly on 8000) AND the 5050 `dashboard.py` stub. The Next.js dashboard (dev `next dev`, default 3000) is the intended UI and talks to 8000. The 5050 stub is **legacy cruft** that will confuse operators ("which dashboard is real?"). `dashboard/build_err.log` exists → the Next build has a known error (prototype-grade).

---

## 7. (f) MUE-X Genes Bypass — VERIFIED (genes reach NEITHER registry)

**Genes live OUTSIDE the repo** at `E:/mue-x/genes/qna_strategies/` — **140 modules** (`ls` count = 140, e.g. `qna_AlgebraStrategy_mut_01a09333.py`).

**Gene shape** (`qna_AlgebraStrategy_mut_01a09333.py`): each defines `STRATEGY_NAME`, `PARAMS`, and `def generate_signal(df)` returning a DataFrame with an `entry` column (`:14-54`). They are **plain modules** — they do **NOT** import `StrategyRegistry`, do **NOT** use `@StrategyRegistry.register`, and are not classes. (Verified: `grep -rln "StrategyRegistry\|@StrategyRegistry" E:/mue-x/genes/...` → **0 matches**.)

**How genes are consumed:** ONLY by the legacy root `hedge_fund.py` (4,244 lines). For each gene, `hedge_fund.py` defines a `signal_qna_*()` wrapper that does `sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")` then `from qna_XXX_mut_HASH import generate_signal, PARAMS` (e.g. `hedge_fund.py:328-347`, `1000-1020`). These wrappers are listed in `QNA_EVOLVED_PROVIDERS` (`:3680-3719`) and aggregated into the vote via `CORE_PROVIDERS` + `QNA_EVOLVED_PROVIDERS` (`:3665-3719`).

**Bypass confirmed:**
- Genes are **never** added to `engine.strategies.registry.StrategyRegistry` (the legacy class registry) — they're free functions, not `@register`-ed classes.
- Genes are **never** added to `engine.strategy.registry.StrategyRegistry` (the canonical metadata registry) — that module isn't even imported by `hedge_fund.py`.
- So the "evolved" strategies that the brief says should feed the canonical `StrategyRegistry` instead **feed a legacy vote-aggregator in a 4,200-line monolith that is not the package's own engine.** The canonical registry is bypassed entirely; the genes are a parallel signalling universe.

**Adjacent risk:** `hedge_fund.py` also hard-codes `SRC = Path(r'E:/trading')` (`:31`), `CREDS = {"login": 372044706, ...}` (`:38`), and requires `MT5_PASSWORD` env (`:35-37`). It is **environment-locked to one Windows box** (`E:/`, `C:\Program Files\MetaTrader 5`). Not portable; not the "single HF" the roadmap wants.

---

## 8. Wired vs Dead/Stub Inventory (selected)

**WIRED / production-credible**
- `engine/execution/builder.py`, `engine/execution/brokers/mt5_adapter.py`, `connectors/mt5_broker.py`, `engine/execution/manager.py`, `brokers/paper.py`
- `engine/risk/manager.py` + `risk/constants.py`, `kill_switch.py`, `checks.py`
- `engine/strategies/registry.py` (legacy class registry) + its 21 strategies
- `engine_production_bridge.py` (live wiring), `engine_bridge.py`
- `api/app.py` core routers (market, trading, brokers, backtest, portfolio, agents, etc.)

**DEAD / ORPHANED**
- `engine/strategy/registry.py` (canonical walk-forward `StrategyRegistry`) — imported only by tests + 1 script
- `engine/strategy/strategies/` (111 canonical strategy classes) — referenced only by `loader`/`parser`/`multi_timeframe`, never auto-registered for live trading
- Root `strategy_registry.py`, `trading_loop.py`, `risk_guard.py`, `strategy_fixes.py`, `test_fixes.py` — root-level legacy scripts, unclear wiring
- `archive/` (web_interface/app.py etc.) — archived
- `quant_nanggroe/strategies/`, `quant_nanggroe/strategies/*` (root `strategies/` dir) — duplicate of `engine/strategies`? separate copy

**STUB / THEATRE**
- `dashboard.py` (5050) — stub
- `api/routes/strategy.py` `/registry` — hard-coded fake data
- `api/routes/wiring_compat.py`, `memory_stub.py`, `colony_stub.py`, `security_tools_stub.py` — explicit stubs
- `engine/strategy/backtest_adapter.py` `generate_signals` (parallel convention, not on canonical path)

**DUPLICATE / COLLISION**
- Two `StrategyRegistry` classes (canonical vs legacy)
- `WyckoffStrategy`/`MeanReversionStrategy`/`SMCStrategy` in both trees (+ a 3rd copy in `live_engine.py`)
- API route collisions: `/api/security/events` ×3, `/api/tools/list` ×2, `/api/tools/{tool_id}/execute` ×2
- Two dashboards (5050 stub vs 8000/3000 Next.js)

---

## 9. Production-Ready vs Prototype (per subsystem)

| Subsystem | Readiness | Why |
|---|---|---|
| MT5 live execution | **PROD** | fail-closed, SL/TP carried, kill-switch shared state, real PnL sync |
| Risk manager | **PROD** | 1049 lines, constitutional limits, realized-PnL veto |
| Legacy strategy registry + 21 strategies | **PROD-ish** | actually wired & traded |
| Canonical `engine/strategy/*` | **PROTOTYPE** | orphaned, not imported by runtime |
| 111 canonical strategies | **PROTOTYPE** | never registered for live use |
| MUE-X gene pipeline | **PROTOTYPE/LEGACY** | outside repo, consumed only by 4,200-line monolith, bypasses registries |
| API server | **MIXED** | real core routers + 4 stub routers + fake `/registry` |
| Dashboard | **PROTOTYPE** | 5050 stub + Next.js with build_err.log; proxies to 8000 |

---

## 10. Recommended Remediation (priority order)

1. **Pick ONE registry.** Delete or formally deprecate `engine/strategy/registry.py` (canonical walk-forward) OR promote it and migrate `@register` calls. Today both `StrategyRegistry` names coexist and only one is live — a maintenance trap. Decide the single-HF target and delete the other.
2. **Wire genes into the chosen registry**, not `hedge_fund.py`'s `sys.path.insert`. Either make genes `@register`-able classes or add a loader that imports `E:/mue-x/genes/...` and registers them. Until then the "evolved" strategies are invisible to the engine's own selector (`strategy_selector.py` reads `list_strategies()` from the legacy registry only).
3. **Fix API route collisions.** Move `ecosystem.py:45` `/security/events` out (or namespace it), and delete `security_tools_stub.py`'s duplicate `/tools/*` routes (they shadow `tools.py:35,53`). Verify with a FastAPI route-table dump in CI.
4. **Replace fake `/api/strategy/registry`** (`strategy.py:14-24`) with a real read from the live registry. The dashboard currently shows invented Sharpes.
5. **Kill the 5050 `dashboard.py` stub** or clearly mark it deprecated; document that the Next.js `dashboard/` (→ 8000) is the UI. Remove from `.bat` launchers.
6. **Collapse `live_engine.py`'s inline `SMCStrategy`/`MeanReversionStrategy`** (`:176`,`:217`) into the single registry; they use a different convention (`analyze()` → strings) and are a 3rd implementation.
7. **De-duplicate** the `engine/strategies/` vs root `quant_nanggroe/strategies/` copies; confirm which is authoritative.

---

## Appendix A — Evidence index (file:line)

- Canonical registry class: `engine/strategy/registry.py:120`; never runtime-imported (grep: only `scripts/alpha_destruction.py:383`, `tests/.../test_factors.py:22`, `tests/.../test_registry.py:11`).
- Legacy registry class: `engine/strategies/registry.py:15`; imported by 21 strategy modules + `engine_production_bridge.py:101`, `engine/live/adaptive_integration.py:74`, `engine/strategy/strategy_selector.py:20`, `engine/strategy/loader.py:70`.
- `generate_signal` (singular) in both bases: `engine/strategies/base.py:109-110`; `engine/strategy/strategies/base_strategy.py:46-47`.
- `generate_signals` (plural) legacy/adapter only: `engine/strategies/dhaher_system.py:202`, `smc_strategy_OLD.py:20`, `kronos_wrapper.py:148,256`, `tradebobby_smc_scanner.py:461,506`, `engine/strategy/backtest_adapter.py:96,155`.
- Class collisions: `engine/strategies/wyckoff.py:21` vs `engine/strategy/strategies/wyckoff_strategy.py:41`; `engine/strategies/mean_reversion.py:23` vs `engine/strategy/strategies/mean_reversion.py:34`; `engine/strategies/smc_strategy.py:21` vs `engine/strategy/strategies/smc_strategy.py:34`; `live_engine.py:176,217`.
- Execution builder: `engine/execution/builder.py:30,52-84,82`.
- MT5 connector: `connectors/mt5_broker.py:20,32-33,42-65,91-94,116`.
- MT5 adapter: `engine/execution/brokers/mt5_adapter.py:31,74-99,56-72`.
- Risk manager: `engine/risk/manager.py:85,152-179,144-150,182-298`.
- App routers: `api/app.py:302-379`; collisions `security.py:33`, `ecosystem.py:45`, `security_tools_stub.py:14`, `tools.py:35,53`, `security_tools_stub.py:20,26`.
- Fake registry endpoint: `api/routes/strategy.py:14-24`.
- Stub routers: `wiring_compat.py:22-52,79-82`; `memory_stub.py:14-32`; `colony_stub.py:14-32`; `security_tools_stub.py:14-44`.
- Dashboards: `dashboard.py:13,40-47`; launched `start-dashboard.bat:6`, `launch-hedgefund.bat:28`, `autonomous-loop.bat:22` (port 5050). Next.js: `dashboard/package.json`, `dashboard/next.config.ts:9-19` (→ 8000). `dashboard/build_err.log` present.
- Genes: `E:/mue-x/genes/qna_strategies/` (140 modules); gene shape `qna_AlgebraStrategy_mut_01a09333.py:14-54`; consumed by `hedge_fund.py:328-347,1000-1020,3665-3719`; `sys.path.insert` to genes at `hedge_fund.py:332,356,...`; genes do NOT register (grep → 0 matches for StrategyRegistry in gene dir).

## Appendix B — Repo size sanity

- Package `quant_nanggroe/`: 100s of `.py` modules across `engine/`, `agents/`, `api/`, `exchange/`, `memory/`, `security/`, `mcp/`, `hedge_fund/`, `connectors/`.
- `engine/strategy/strategies/` = 111 strategy files (canonical, mostly orphaned).
- `engine/strategies/` = 21 strategy files (legacy, wired).
- Root legacy scripts: `hedge_fund.py` (4,244 lines), `live_engine.py` (1,272 lines, inside pkg), `trading_loop.py`, `risk_guard.py`, `strategy_registry.py`.
- External gene store: 140 modules (outside repo, on `E:/`).

*End of audit. No source files were modified; report is read-only forensics.*
