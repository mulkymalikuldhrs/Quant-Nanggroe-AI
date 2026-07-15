# Multi-Agent Council — Wave 2 Report (AI/ML Eng #11-18 + Software Eng #19-26)

**Date:** 2026-07-15
**Scope:** codegen.py (AST allowlist / sandbox), middleware.py (auth fail-closed), api/app.py (router wiring), worker.py (kill-switch monitor), new_proposals.py (strategy quality)
**Repo:** D:/repositories/Quant-Nanggroe-AI-worktree (worktree)
**Method:** Direct file read + grep of actual source. One concrete finding per agent, with `file:line` evidence.

---

## AI/ML Engineering (#11-18)

### #11 — Strategy CodeGen: sandbox allowlist contradicts the validator
`quant_nanggroe/engine/shadow/codegen.py`
- `codegen.py:23` — `_ALLOWED_IMPORT_ROOTS = ("numpy", "np", "pandas", "pd", "quant_nanggroe")`. The `"np"`/`"pd"` entries are **not valid import roots** (`import np` does not work — it is `import numpy as np`), so those allowlist entries are dead/misleading. The `"quant_nanggroe"` root permits `from quant_nanggroe.engine... import <anything>`, which is the whole package (incl. FS/network modules).
- `codegen.py:255-256` — the executor deliberately keeps `"__import__"` and `"__build_class__"` in `safe_builtins`, while `codegen.py:27` lists `"__import__"` as **forbidden** in `_FORBIDDEN_CALLS`. The only thing stopping a generated strategy from doing `__import__('os')` is the AST name check at `codegen.py:226`; any obfuscated/indirect invocation reaches the kept builtin.
- **Finding:** The "safe" sandbox is contradictory and over-broad — the validator and the executor disagree, and the import allowlist is both incorrect (`np`/`pd`) and too permissive (`quant_nanggroe`). Net: generated/LLM strategy code can import and instantiate arbitrary package code.

### #12 — Auth Middleware: fails CLOSED (verified, no defect)
`quant_nanggroe/api/middleware.py`
- `middleware.py:41-56` — `__init__` derives `_dev_mode = (not bool(QNAI_API_KEY)) and QNAI_ALLOW_INSECURE_DEV`. Bypass requires BOTH no API key AND explicit `QNAI_ALLOW_INSECURE_DEV=true` opt-in. Otherwise auth is enforced and a warning is logged.
- **Finding:** `AuthMiddleware` is correctly fail-closed by design. PASS. (Residual risk is the broad non-`/api/` pass-through at `middleware.py:70-71`, exploited by #13.)

### #13 — Router wiring: 14 routers bypass auth entirely
`quant_nanggroe/api/app.py` + `quant_nanggroe/api/middleware.py` + `quant_nanggroe/api/routes/council.py`
- `app.py:253-259, 264-272` — 14 routers are `include_router(...)` **without a prefix**: `credentials, council, debate, fred, geopolitics, personas, sec_edgar, signal_generator, options, rl, analytics, agentic, autonomous, wiring_compat`.
- `middleware.py:70-71` — `if not path.startswith("/api/"): return await call_next(request)` blanket-allows every non-`/api/` path.
- `council.py:17,28,34` — routes `/list`, `/{id}`, `/vote/{session_id}` are mounted at root → not under `/api/` → **no authentication**.
- **Finding:** All routes on the 14 unprefixed routers are served without auth. Council/debate/sec_edgar/analytics/etc. endpoints are fully unauthenticated in production.

### #14 — Version string inconsistency across the codebase
- `quant_nanggroe/api/app.py:148` — `FastAPI(..., version="1.0.0", ...)` (hardcoded `1.0.0`).
- `quant_nanggroe/__init__.py:28` — `__version__ = "4.3.4"`.
- `quant_nanggroe/engine/strategy/strategies/new_proposals.py:1` — docstring claims `QNA v4.5.3`.
- **Finding:** Three different version identifiers in one tree (`1.0.0` vs `4.3.4` vs `4.5.3`). `/api/version` reports `4.3.4` while the OpenAPI `version` field says `1.0.0`; docstrings claim `4.5.3`. No single source of truth is actually rendered.

### #15 — BackgroundWorker default tasks are no-ops
`quant_nanggroe/engine/worker.py`
- `worker.py:602-614` — `_task_price_fetch`, `_task_rebalance_check`, `_task_strategy_health` are `@staticmethod` stubs that only `logger.debug(...)` and do nothing. They are the default tasks registered at `worker.py:358-377`.
- **Finding:** The feature-rich `BackgroundWorker` (singleton lock, retry/backoff, metrics) is wired to run tasks that fetch zero prices, rebalance nothing, and check no strategy health. The worker loop is inert despite the machinery around it.

### #16 — Kill-switch monitor feeds zeroed PnL/drawdown → auto-activation is dead
`quant_nanggroe/worker.py`
- `worker.py:307-310` — `_kill_switch_monitor_loop` calls `self._kill_switch.check_auto_activate(daily_pnl_pct=getattr(self, "_last_daily_pnl_pct", 0.0), max_drawdown_pct=getattr(self, "_last_drawdown_pct", 0.0))`.
- Grep across the repo: `_last_daily_pnl_pct` and `_last_drawdown_pct` are **never assigned anywhere** (only read via `getattr` default `0.0`). No code path populates them.
- `kill_switch.py:336-372` — auto-activation only fires when `daily_pnl_pct`/`max_drawdown_pct`/`volatility_pct` exceed thresholds; with inputs pinned at `0.0` they never will.
- **Finding:** The kill switch's auto-activation path is permanently disabled — it can only ever be triggered manually (`KillSwitch.activate`), never by loss/drawdown. The monitor claims to be "LIVE, not inert" (`worker.py:302`) but is effectively inert for auto-triggering.

### #17 — new_proposals.py violates its own "no crash, just no signal" contract
`quant_nanggroe/engine/strategy/strategies/new_proposals.py` + `quant_nanggroe/engine/strategy/strategies/base_strategy.py`
- `new_proposals.py:10-11` — docstring promises strategies "guard on column presence (no crash, just no signal when absent)".
- `base_strategy.py:93-97` — `validate_data` **raises `ValueError`** when a required column is missing (it does not return `None` for that case; it only returns `False` for empty/short data).
- `new_proposals.py:110` and `:183` — `DispersionStrategy` / `IdiosyncraticMomentumStrategy` add `or "benchmark_close" not in data.columns` / `or "market_close" not in data.columns` guards. These are **dead code**: if the column is missing, `validate_data` (called first at `:109`/`:182`) raises before the guard is reached.
- **Finding:** When `benchmark_close`/`market_close` are absent, `generate_signal` propagates a `ValueError` instead of returning `None`, directly contradicting the module's stated contract. The extra guards are unreachable.

### #18 — Colony "concrete" workers are hardcoded stubs
`quant_nanggroe/engine/colony/worker.py`
- `worker.py:58-61` — `StrategyWorker.execute` returns `{"signal": "hold", "confidence": 0.5}` after `asyncio.sleep(0.01)`.
- `worker.py:67-69, 75-77, 83-85` — `RiskWorker`, `DataWorker`, `ExecutionWorker` likewise return fixed literal dicts; none call any engine.
- **Finding:** The colony multi-agent execution layer performs no real work — every "concrete" worker is a stub that fakes a result. The `run()` wrapper (`worker.py:32-49`) isolates failures, but there is nothing to fail; the colony is non-functional for actual trading/risk/data tasks.

---

## Software Engineering (#19-26)

### #19 — /trigger-error diagnostic reachable in no-API-key deployments
`quant_nanggroe/api/app.py`
- `app.py:288-291` — `if not os.environ.get("QNAI_API_KEY"):` registers `GET /trigger-error` that raises `RuntimeError`. The check is only "no API key set", which is exactly the default/forgotten-config state; many dev/staging boxes run without `QNAI_API_KEY`.
- **Finding:** A route whose sole purpose is to exercise the 500 handler is auto-exposed whenever no API key is configured — i.e. in any environment that hasn't set one (the same condition that #12's warning says is "DO NOT USE IN PRODUCTION"). It is reachable without auth (root path, see #13) and exists only to surface stack traces.

### #20 — Lifespan silently downgrades on startup failure
`quant_nanggroe/api/app.py`
- `app.py:74-78` — `_background_init` wraps `init_all_services` + exchange connect in a bare `except Exception` that only logs `"startup_services_unavailable ... running without persistence"`.
- **Finding:** Any DB/exchange/connection failure during startup is swallowed into a benign log line and the app continues serving with no services. Operators get no hard failure and may run a half-initialized API believing it is healthy (`/health` still returns `healthy`).

### #21 — Rate limiter is per-process and client-id spoofable
`quant_nanggroe/api/middleware.py`
- `middleware.py:149` — `self.requests: dict[str, list[float]] = {}` is an in-process dict.
- `middleware.py:152` — `client_id = request.client.host` (TCP peer), ignoring `X-Forwarded-For`.
- **Finding:** Behind any proxy/load-balancer or multi-worker/uWSGI deployment, rate limiting (a) does not aggregate across processes/replicas and (b) keys on the proxy's IP, not the real client. Either makes the limiter trivially bypassable or globally blocks behind a shared proxy.

### #22 — compile_strategy returns the FIRST class ending in "Strategy"
`quant_nanggroe/engine/shadow/codegen.py`
- `codegen.py:266-268` — after `exec`, it iterates `namespace.items()` and returns the first `obj` that is a type whose name `endswith("Strategy")`.
- **Finding:** If the generated code or any imported `quant_nanggroe` submodule in the namespace defines another `...Strategy` class (likely, given #11 imports the whole package), the wrong class can be returned — and if none match, it returns `None` silently (`codegen.py:270`). Selection is by name-suffix, not by the intended generated class.

### #23 — new_proposals confidence/threshold heuristics are unscaled and inconsistent
`quant_nanggroe/engine/strategy/strategies/new_proposals.py`
- `new_proposals.py:53` — `VPINToxicityStrategy`: `confidence=min(vpin, 1.0)`; `vpin` is a normalized ratio frequently <1 but the scaling is arbitrary.
- `new_proposals.py:341` — `DrawdownRegimeStrategy` BUY branch hardcodes `confidence=0.5` regardless of recovery magnitude (contrast SELL branch `min(abs(dd)/max_dd, 1.0)` at `:336`).
- `new_proposals.py:119` — `DispersionStrategy` uses a hardcoded 20-bar lookback (`data["close"].iloc[-20]`) instead of `self.window`, so "momentum" ignores the configured window.
- **Finding:** Signal-confidence math is ad hoc: one strategy ignores its own window, another hardcodes a constant, others divide by 3.0 as a magic scaler. These are not crashes but produce inconsistent, unvalidated confidence values fed into position sizing/aggregation.

### #24 — Duplicate/ambiguous route namespaces mounted side-by-side
`quant_nanggroe/api/app.py`
- `app.py:261-262` — both `strategy.router` (prefix `/api/strategy`) and `strategies.router` (prefix `/api/strategies`) are mounted; `wiring_compat.router` (`:272`, no prefix) exists alongside the real routers.
- **Finding:** `wiring_compat` (by name, a backward-compat shim) is mounted at root next to the canonical routers. Compat shims mounted alongside real endpoints risk silently shadowing or duplicating routes and are a maintenance landmine; the two `strategy`/`strategies` routers invite path collisions.

### #25 — Top-level worker position/snapshot loops are placeholders
`quant_nanggroe/worker.py`
- `worker.py:267-272` — `_update_all_positions` only `logger.debug("positions_update_checked")`; `worker.py:292-297` — `_take_portfolio_snapshot` only `logger.debug("portfolio_snapshot_taken")`.
- **Finding:** Despite the module docstring claiming the worker "monitors open positions" and "records portfolio snapshots," both loops are no-ops. Unrealized PnL is never updated and no equity-curve snapshots are ever written — the position monitor and snapshotter do nothing.

### #26 — Two worker implementations, neither wired into the app
`quant_nanggroe/api/app.py` + `quant_nanggroe/worker.py` + `quant_nanggroe/engine/worker.py`
- `app.py` imports `middleware`, `config`, `security.auth` — **no import of `worker` or `engine.worker` anywhere** (grep confirms no worker reference in `app.py`).
- `quant_nanggroe/worker.py` defines `TradingWorker`; `quant_nanggroe/engine/worker.py` defines `BackgroundWorker`. Both are full implementations; neither is started by the FastAPI app.
- **Finding:** There are two parallel, mutually exclusive "main" worker designs and the running API process starts neither. The autonomous trading loop's actual entrypoint is undefined — whatever is supposed to drive graphs/positions/kill-switch at runtime is not launched by `create_app()`.

---

## Summary table (file:line evidence)

| # | Area | Finding | Evidence |
|---|------|---------|----------|
| 11 | AI/ML | codegen sandbox allowlist contradiction + over-broad import root | `codegen.py:23,27,255-256` |
| 12 | AI/ML | Auth middleware correctly fail-closed | `middleware.py:41-56` (PASS) |
| 13 | AI/ML | 14 unprefixed routers bypass auth | `app.py:253-259,264-272`; `middleware.py:70-71`; `council.py:17,28,34` |
| 14 | AI/ML | Version string inconsistency | `app.py:148`; `__init__.py:28`; `new_proposals.py:1` |
| 15 | AI/ML | BackgroundWorker default tasks are no-ops | `engine/worker.py:602-614` |
| 16 | AI/ML | Kill-switch auto-activation dead (zeroed inputs) | `worker.py:307-310`; `kill_switch.py:336-372` |
| 17 | AI/ML | new_proposals missing-column contract violation | `base_strategy.py:93-97`; `new_proposals.py:10-11,109-110,182-183` |
| 18 | AI/ML | Colony workers hardcoded stubs | `engine/colony/worker.py:58-85` |
| 19 | SW | /trigger-error exposed without API key | `app.py:288-291` |
| 20 | SW | Lifespan swallows startup failures | `app.py:74-78` |
| 21 | SW | Rate limiter per-process + spoofable client id | `middleware.py:149,152,158` |
| 22 | SW | compile_strategy returns first *Strategy class | `codegen.py:266-268` |
| 23 | SW | Strategy confidence heuristics unscaled/inconsistent | `new_proposals.py:53,119,336,341` |
| 24 | SW | Duplicate/ambiguous route namespaces | `app.py:261-262,272` |
| 25 | SW | Position/snapshot loops are placeholders | `worker.py:267-272,292-297` |
| 26 | SW | Two workers, neither launched by app | `app.py` (no worker import); `worker.py`; `engine/worker.py` |
