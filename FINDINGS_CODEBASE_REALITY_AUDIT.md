# FINDINGS — QNA Codebase Reality Audit (quant_nanggroe/)

Date: 2026-07-28 · Repo: D:\repositories\Quant-Nanggroe-AI-worktree · Scope: quant_nanggroe/ + root *.md + docs/
Method: static grep/import-graph analysis only (app not run). All claims below carry file:line evidence.

## One-line finding
The package is 716 .py files, of which **~161 modules (26%) are orphaned (never imported anywhere)**, the FastAPI app serves **seeded-random synthetic data as live API responses** (`api/routes/_data.py:10` `random.seed(42)`, wired at `api/app.py:383`), and multiple "verified" engines (ML signal generator, model registry transformers, colony hands, RL agents) are **explicit stubs returning zeros** — while root docs simultaneously claim "PRODUCTION READINESS: 100/100" and admit the 100/100 claim was disproved.

## 1) Structure (top modules by .py count, __pycache__ excluded — 716 total)
- engine/strategies: 84 · api/routes: 40 · engine/: 27 · engine/risk: 25 · agents/: 22
- data/providers: 20 · engine/backtest: 18 (+8 engines, +5 optimizers, +4 loaders) · exchange/: 15 (+12 clients, +6 solana)
- engine/causal: 14 · agents/tools: 14 · root pkg: 13 · engine/screener: 11 · engine/kelly: 10 · engine/factors: 10 · engine/execution: 10 (+4 guards, +3 brokers)
- ~60 further subpackages of 2–9 files (regime, stress_testing, agentic, colony, hedge_fund/*, memory, security, pipeline, mcp, daemons, …)
- Dirs with NO `__init__.py` (data dirs mostly, but note): `quant_nanggroe/indicators/pine`, `quant_nanggroe/docs/plans`, `quant_nanggroe/api/static`.
- Duplicate/parallel trees still present: `engine/strategies/` vs `engine/strategy/strategies/` (5 files), `quant_nanggroe/strategies/` (5 files), `exchange/mt5_broker.py` vs `connectors/mt5_broker.py` vs `engine/execution/brokers/` — known diverged-copy hazard.

## 2) Orphaned / dead files — 161 modules never imported by any .py in quant_nanggroe/, scripts/, or entrypoints
(leaf-name grep over the full union of import lines; strategies caveat below)

**Caveat:** `engine/registry.py:165-172` does `pkgutil.walk_packages` + dynamic import, so the ~76 "orphan" files under `engine/strategies/` MAY be auto-registered at runtime. All other orphans have no dynamic loader.

Hard orphans (no importer, no dynamic loader) — selected, full list reproducible via import-graph grep:
- **Whole agent personas dir dead**: `agents/personas/{warren_buffett,ray_dalio,michael_burry,peter_lynch,cathie_wood,stanley_druckenmiller}.py` — 0 importers.
- **Whole geopolitics agents dead**: `agents/geopolitics/{american_order,chinese_order,european_order,islamic_finance,multipolar}.py`.
- Dead agents: `agents/{browser,coder,debate_engine,gold_trader,manus,marketplace,planner,protocols,telegram_bot,voice}.py`.
- Dead agent tools: `agents/tools/{competition,emotional,forecast,geopolitical,intermarket,screener,skill}_tool.py`.
- Dead API routes (not mounted): `api/routes/{ecosystem,fred,otto_proxy,pipeline_status,qna_status,security_tools,wiring_compat,ws}.py`.
- **Whole stress_testing pkg dead**: `engine/stress_testing/{historical_scenarios,scenario_generator,sensitivity,stress_reporter}.py`.
- **engine/portfolio pkg dead**: `{confluence_scorer,covariance_risk,risk_budget,risk_parity_bridgewater}.py` — "Bridgewater risk parity" exists but nothing calls it.
- Regime pkg partially dead: `engine/regime/{macro_regime,regime_store,volatility_clustering}.py`.
- Risk modules dead: `engine/risk/{limits,quick_veto,tail_risk_hedge}.py`.
- Causal engine mostly dead: `engine/causal/{lead_lag,master_engine,smt_alert_system,thesis_guard}.py`.
- Execution: `engine/execution/{algo_execution,rl_execution}.py` dead.
- **ALL 10 exchange/clients/** (`binance_client.py` … `okx_client.py`) unimported by static code; only reachable via `exchange/factory.py:41` `AVAILABLE_CLIENTS` — the per-client files themselves have no direct importer, and `exchange/{polymarket_broker,quantdinger_factory,mt5_accounts,order_types}.py` are fully dead.
- Misc dead: `cli.py`, `data/correlation_provider.py`, `data/providers/{alpha_vantage,coingecko,fred,openbb_mcp}.py`, `engine/backtest/{nautilus_adapter,fama_french,report}.py`, `engine/{microstructure,correction}.py`, `engine/visualization/charts.py`, `engine/shadow/{account,codegen}.py`, `hedge_fund/{mtf,multipair}.py`, `indicators/{smart_volume,squeeze_breakout}.py`, `security/credential_inference.py`.

## 3) Mock / placeholder / stub / fake data (88 non-test hits for mock|placeholder|fake|dummy|stub; 200 bare `return []`/`return {}` sites; 24 TODO/not-implemented sites)

### CRITICAL — fabricated data served as live API output
- `api/routes/_data.py:1` — "Synthetic data providers for stub API modules"; `:10` `random.seed(42)`; `:216` `random.randint(1,20)`; hardcoded `_TOP_EVENTS`/`_SANCTIONS` lists (:12-25). **Wired into the live app** at `api/app.py:383` (`only _data.router is used`). Geopolitics/sanctions "data" the API returns is deterministic fiction.
- `engine/ml/signal_generator.py:92-102` — `predict()` docstring says "Returns mock predictions"; **actually `return np.zeros(len(X))`** and `predict_proba` returns constant 0.5. Any "ML signal" from this class is a flat zero.
- `engine/model_registry.py:451,628-700` — "XGBoost stub", "simplified feedforward stub, not a real transformer… Do not use for live trading". Registered models are admitted stubs.
- `engine/nim_provider.py:9,79,174,340` — LLM fallback chain ends in a MOCK provider (`source: str = "mock"` default). :387 claims "do not mock" on total failure, but mock is a normal chain member.
- `engine/colony/hands.py:1` — entire file is `"""Stub: colony.hands"""` (one line); `agents/colony.py:28-43` defines its own stub types to "at least import".
- `agents/browser.py:237` — screenshots are a fake PNG header + 1KB zero bytes ("mock PNG header").
- `agents/coder.py:169-185` — "code generation" emits `// TODO: implement {spec}` — the coder agent writes TODOs, not code.

### HIGH — placeholder/degenerate logic in live-adjacent paths
- `engine/live/adaptive_integration.py:534` — `_get_news_for_symbol` → `return []` (placeholder); :389-395 `update_pnl`/`add_position`/`remove_position` are `pass` no-ops; fallback position size is a magic formula `(balance*kelly*0.1)/price`.
- `agents/tools/flow_tool.py:146,168,249` — whale/flow tool returns placeholder low-confidence estimates; ":249 Placeholder - in production, connect to Whale Alert, Arkham".
- `agents/tools/sentiment.py:529-539` — sentiment is a "structured placeholder" derived from headline volume, not NLP.
- `engine/rl/agents.py:145-152` — RL agent `act()`/`update()` "not implemented — returning 0 / empty dict".
- `engine/factors/gtja191.py:2575` — factor computed as `signed_power(left,1.0) * 0  # placeholder` — a permanently-zero alpha factor.
- `agents/risk/agent.py:438` — PnL tracking "Stub for daemon integration; logs the values."
- `exchange/alpaca_broker.py:855,869`, `exchange/polymarket_broker.py:928-938`, `exchange/solana/broker.py:484` — subscriptions "not implemented" (log-and-return).
- `live_engine.py:166` — "TODO: Starting capital should come from config, not hardcoded".
- `security/credential_manager.py:76,126,135` — capabilities listed but "mocked in fallback chain" / "not implemented — pending".
- 200 sites of bare `return []` / `return {}` and ~243 `pass` bodies package-wide — many legitimate, but density in agents/tools and engine/live matches the placeholder pattern.
- Defensive-comment tell: dozens of "PRODUCTION: Real math (not mock)" annotations (`agents/risk/tools.py:177,248,315,404`; `agents/portfolio/tools.py:207-262`; `agents/macro/tools.py:236,270`) — code protesting its own realness, evidence of a prior mock purge; these particular sites do appear to be real arithmetic.

### Partially remediated (credit where due)
- `engine/autonomous_self_loop.py:377-520` — the 4 famous TODO stubs (`_get_recent_trades`, `_get_strategy_performance`, `_get_recently_evolved_strategies`, `_get_pending_signals`) are NO LONGER empty returns: they read CSV/JSON state files and (per :477 docstring, "FIX 2026-07-28") fetch real Binance tickers. Still fragile — sharpe/max_drawdown default to 0.0 in fallback (:440-445), and everything degrades silently to []/{}.
- `agents/hedge_fund_bridge.py:26`, `hedge_fund/utils/data.py:26`, `pipeline/signal.py:169` — genuine fail-closed "no mock/simulated" behavior.

## 4) Stale/self-contradictory markdown (root: 17 files; docs/: 62 files)
- `FULL_STACK_VERIFICATION_100_100.md` — internally contradictory: `:242` "PRODUCTION READINESS: 100/100" while `:7` admits "Previous Claim: '100/100 AUTONOMOUS' — DISPROVED (had wrong imports, TODO stubs, API mismatches)" and `:401-404` lists the four empty-return TODOs. Filename itself is a stale claim.
- `AUTONOMOUS_HEDGE_FUND_STATUS.md:8` — "⚠️ REQUIRES HONEST ASSESSMENT — Previous '100/100' claim disproved"; `:26` "Honest Score: 85/100 — Structurally complete, operationally unverified"; `:284` "78 strategies: All registered and verified" is unverifiable statically given the orphan tree above.
- `STRATEGY_INFRASTRUCTURE_VERIFICATION.md`, `QNA_FULL_VIEW_AND_GAP.md`, `CLEANUP_REPORT_FINAL.md`, `COMPREHENSIVE_CLEANUP_PLAN.md`, `COMPREHENSIVE_FILE_ENUMERATION_REPORT.md`, `EXPANSION_PLAN_v6.3.0.md`, `TODO.md`, `ARCHITECTURE.md`, `CHANGELOG.md`, plus AI-tool files (`CLAUDE.md`, `GEMINI.md`, `COPILOT.md`, `CURSOR.md`, `AGENTS.md`) — point-in-time snapshots; any of them describing "no dead code" or "cleanup complete" is falsified by the 161-orphan count.
- `docs/` — 52 numbered docs (00_VISION…51_BOT_ORCHESTRATION) + ADR-005/006/007 + `UI_GUIDE.md` (previously proven to document non-existent `/api/v1/...` endpoints — still stale), `STRATEGY_CATALOG.md`, and four audit docs (`QNA_AUDIT_INVENTORY_v6.2.md`, `QNA_DEEP_AUDIT_2026-07-26.md`, `QNA_MASTER_GAP.md`, `QNA_RESEARCH_EXTENSION.md`). The numbered scaffold docs are template-generated and cannot all reflect a codebase where whole subsystems (stress_testing, portfolio, personas, geopolitics) are unwired.

## Verdict
Real: core strategy registry + dynamic autoscan (`engine/registry.py:151-178`), risk/portfolio math in agents/tools, MT5/exchange broker plumbing, backtest core, the recently-fixed autonomous self-loop data getters.
Fake/stub despite claims: API-served synthetic geopolitics/sanctions data, ML signal generator (zeros), model-registry "transformer/XGBoost", RL agents, colony hands, coder/browser agents, sentiment/flow tools, and ~26% of the package that nothing imports at all. The "100/100" documentation is self-refuting by its own line 7.
