# Quant-Nanggroe-AI — Master Remediation Task List

## Phase 0: HOTFIXES — ✅ COMPLETE

- [x] **0.1** — `__init__.py` version 4.6.0 → 5.1.0
- [x] **0.2** — `pyproject.toml` version 4.6.0 → 5.1.0
- [x] **0.3** — `qna.py:39`, `cli.py:35,41` hardcoded versions → 5.1.0
- [x] **0.4** — `dashboard.py:13` version 5.0.0 → 5.1.0
- [x] **0.5** — `README.md:169` "Proprietary" → "MIT"
- [x] **0.6** — `kill_switch.py:444` docstring moved above code
- [x] **0.7** — `proxy.py` import moved to top, docstring fixed

## Phase 1: CLOSE IMPLEMENTATION GAPS

### 1.1 Create engine/correction.py
- [ ] Create `quant_nanggroe/engine/correction.py` with:
  - [ ] `SelfCorrect` class — `record_lesson()`, `search_lessons()`, `auto_evolve()`
  - [ ] `RetryStrategy` — exponential backoff, max_retries, circuit breaker
  - [ ] `FallbackResolver` — alternative approach on failure
- [ ] Wire into `AutonomousPipeline` — auto-load on init, expose `self.correction`
- [ ] Verify: `python -c "from quant_nanggroe.engine.correction import SelfCorrect"` works

### 1.2 Add weekly loss veto to kill_switch.py
- [ ] Add `WEEKLY_LOSS_LIMIT = -3.0` to `constants.py`
- [ ] Add cumulative weekly PnL tracker (auto-resets Monday)
- [ ] Add veto in `check_trade()` if weekly loss exceeded
- [ ] Add `weekly_pnl_pct` parameter to kill switch check path

### 1.3 Complete NautilusTrader adapter or remove stub
- [ ] Verify NautilusTrader is actually used by any code path
- [ ] If unused: replace NotImplementedError with docstring and `pass`
- [ ] If used: complete the implementation

### 1.4 RL agent act()/update()
- [ ] Implement minimal `act()` returning random action
- [ ] Implement minimal `update()` as no-op with log
- [ ] Or: remove stubs and mark as future work

### 1.5 WebSocket subscriptions
- [ ] `polymarket_broker.py`: Implement WS subscription or document as limitation
- [ ] `alpaca_broker.py`: Implement WS subscription or document as limitation

### 1.6 Full encryption at rest
- [ ] Wire AES-256 encrypt/decrypt in `security/encryption.py`
- [ ] Verify no plaintext secrets persist to disk without encryption

### 1.7 COT provider
- [ ] Implement COT data ingestion from CFTC weekly reports
- [ ] Wire into `engine/data/providers/`
- [ ] Add COT-based strategy signals

## Phase 2: ARCHITECTURAL WIRING

### 2.1 Strategy directory consolidation (HIGH RISK — coordinate with data flow)
- [ ] Audit all imports from old path (`engine.strategy.strategies`)
- [ ] Migrate each strategy to new path (`engine.strategies`)
- [ ] Update `__init__.py` shim to emit deprecation warning
- [ ] After migration complete: delete old path directory
- [ ] Verify all tests pass

### 2.2 Database defaults consolidation
- [ ] Pick single canonical connection string (recommend: `sqlite:///data/agentic.db`)
- [ ] Update `config/settings.py` default
- [ ] Update `database/models.py` to use settings
- [ ] Remove hardcoded defaults in other files

### 2.3 Main loop consolidation
- [ ] Add deprecation warning to `trading_loop.run_cycle()`
- [ ] Create adapter that routes `run_cycle()` calls through `AutonomousPipeline`
- [ ] Verify no production code calls `run_cycle()` directly

### 2.4 Telegram bot unification
- [ ] Create `engine/telegram.py` with single `TelegramNotifier` class
- [ ] Both `notifier.py` and `agents/telegram_bot.py` delegate to it
- [ ] Bot rotation logic from notifier.py preserved

### 2.5 Import degradation hardening
- [ ] Audit all try/except ImportError blocks
- [ ] Add `_verify_components()` to AutonomousPipeline init
- [ ] Log WARNING for each degraded component

### 2.6 Signal persistence consolidation
- [ ] Create single `Signal` SQLAlchemy model
- [ ] Migrate JSON file store to DB
- [ ] Migrate raw sqlite3 stores to DB
- [ ] Remove old storage paths

### 2.7 Configuration consolidation
- [ ] Add all YAML/JSON config fields to Pydantic `Settings`
- [ ] Create migration utility to read legacy config files
- [ ] Add deprecation warning for non-Pydantic config paths

### 2.8 Async/sync standardization
- [ ] Audit all entry points for async conformity
- [ ] Wrap sync callers in `asyncio.to_thread()` where needed
- [ ] Single `run_async()` entry for all modes

### 2.9 hedge_fund.py split
- [ ] Extract signals/ module
- [ ] Extract risk/ module
- [ ] Extract execution/ module
- [ ] Extract portfolio/ module
- [ ] Original file becomes thin orchestrator

### 2.10 Standalone path fix
- [ ] README: fix path reference
- [ ] Or: create `engine/standalone.py` as import alias

### 2.11 .gitignore cleanup
- [ ] Remove duplicate `node_modules/` at line 132
- [ ] Remove `dashboard/nul` artifact if present

## Phase 3: DOCUMENTATION

### 3.1 Fill missing docs
- [ ] 06_GLOSSARY.md — term definitions
- [ ] 22_PIPELINE.md — data flow documentation
- [ ] 23_ADR.md — architecture decision records (migrate from inline)
- [ ] 24_API_CHANGELOG.md — API version history
- [ ] 25_* through 27_*
- [ ] 30_* through 32_*
- [ ] 35_* through 37_*
- [ ] 39_*
- [ ] 43_* through 47_*

### 3.2 Strategy catalog
- [ ] Scan all 168+ strategy files
- [ ] Extract class name, description, parameters
- [ ] Write to `docs/STRATEGY_CATALOG.md`

### 3.3 Subpackage READMEs
- [ ] Add one-line docstring to each `__init__.py` in 43 subpackages

### 3.4 Changelog consolidation
- [ ] Merge `docs/13_CHANGELOG.md` into root `CHANGELOG.md`
- [ ] Remove `docs/13_CHANGELOG.md`

### 3.5 OpenAPI schema export
- [ ] Add build-time script to export `openapi.json` from FastAPI app

### 3.6 Examples directory
- [ ] Create `examples/basic_usage.py`
- [ ] Create `examples/backtest.py`
- [ ] Create `examples/custom_strategy.py`

### 3.7 README test count fix
- [ ] Audit actual test count
- [ ] Update README with accurate figure

### 3.8 Version consistency sweep
- [ ] Check `engine/audit.py` v15.2.0 reference
- [ ] Check `scripts/council_expectancy_scan.py` v4.5.9
- [ ] Check `scripts/launch_full.py` v4.6.0

## Phase 4: TESTS & CI

### 4.1 Risk module tests
- [ ] `test_atr_sl.py`
- [ ] `test_constants.py`
- [ ] `test_correlation.py`
- [ ] `test_drawdown.py`
- [ ] `test_kelly.py`
- [ ] `test_kill_switch.py` (migrate from root tests/)
- [ ] `test_position_sizing.py`
- [ ] `test_quick_veto.py`
- [ ] `test_risk_parity.py`
- [ ] `test_var.py`
- [ ] `test_trailing_stop.py`

### 4.2 Agent tests
- [ ] Smoke test for each of 21 agent files + 17 agent subdirectories
- [ ] Test agent API shape (not implementation)

### 4.3 Clean empty test directories
- [ ] `test_browser/` — remove or populate
- [ ] `test_channels/` — remove or populate
- [ ] `test_colony/` — remove or populate
- [ ] `test_core/` — remove or populate
- [ ] `test_finance/` — remove or populate
- [ ] `test_harness/` — remove or populate
- [ ] `test_organism/` — remove or populate
- [ ] `test_sandbox/` — remove or populate
- [ ] `test_sources/` — remove or populate
- [ ] `test_tools/` — remove or populate

### 4.4 Coverage enforcement
- [ ] Add `--cov-fail-under=40` to pytest config in `pyproject.toml`
- [ ] Add coverage badge to README

### 4.5 Stub detection
- [ ] Add pre-commit hook for `pass` in non-abstract methods
- [ ] Or: custom ruff rule

### 4.6 Dependency scanning
- [ ] Add `pip-audit` to CI workflow
- [ ] Add `npm audit` for dashboard/

### 4.7 Integration test
- [ ] Signal flow E2E: Signal → Risk → Execution → Fill

## Phase 5: QUANT HARDENING

### 5.1 Weekly loss veto (overlaps with 1.2)
- [ ] Coordinate with 1.2 implementation

### 5.2 Cross-asset correlation
- [ ] Wire `engine/risk/correlation.py` into execution path
- [ ] Add veto if new position increases portfolio correlation above threshold

### 5.3 Signal persistence (overlaps with 2.6)
- [ ] Coordinate with 2.6

### 5.4 Strategy PnL tracking
- [ ] Add `StrategyPnl` model (strategy_id, date, pnl, sharpe, trades)
- [ ] Add daily snapshot in `trade_lifecycle.py`

### 5.5 Shadow trading
- [ ] `ShadowTrader` class that mirrors signals to paper broker
- [ ] Results stored for comparison

### 5.6 Alpha decay monitoring
- [ ] Wire `engine/analytics/alpha_decay.py` into post-trade lifecycle
- [ ] Add decay rate metric to Prometheus

### 5.7 Factor attribution
- [ ] Add factor return decomposition to backtest reports
- [ ] Wire into `engine/backtest/report.py`

## Phase 6: 50-AGENT COUNCIL

### 6.1 Wave 1 — Quant/Trading
- [ ] Run 10 quant agents on risk framework, alpha, execution, portfolio
- [ ] Document findings as ADR-005

### 6.2 Wave 2 — Engineering
- [ ] Run 16 engineering agents on API, security, DB, deploy
- [ ] Document findings as ADR-006 through ADR-008

### 6.3 Wave 3 — Strategy/Business
- [ ] Run 18 agents on compliance, roadmap, dead code, documentation
- [ ] Document findings as ADR-009 through ADR-010

## OVERALL COMPLETION CHECKLIST

- [ ] Phase 0: All hotfixes verified (✅)
- [ ] Phase 1: Zero NotImplementedError in critical paths, weekly veto active
- [ ] Phase 2: Single strategy path, single DB, single main loop
- [ ] Phase 3: All 49 docs slots filled, strategy catalog published
- [ ] Phase 4: CI enforces coverage, stub detection active, dep scanning active
- [ ] Phase 5: Weekly veto, correlation gate, alpha decay monitored
- [ ] Phase 6: 50-agent council complete, ADRs published
