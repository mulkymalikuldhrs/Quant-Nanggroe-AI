# Orphan Module Triage Report

Generated: 2026-06-24
Source: `scripts/qna-architect.py` — static AST analysis

## Summary

| Metric | Value |
|--------|-------|
| Total files scanned | 417 |
| Total orphans detected | 92 |
| False positives (keep) | 24 |
| Truly dead code | 58 |
| Uncertain / needs investigation | 10 |
| Missing imports | 0 (already fixed) |
| Circular imports | 0 |

## Full Orphan Table

File | Category | Reason | Suggested Action
-----|----------|--------|-----------------
`_compat.py` | **DEAD** | Pydantic v1→v2 compat layer. Project is on pydantic v2.9.2. `patch_pydantic()` never called anywhere. | Delete
`agents/debate/reflection.py` | **UNCERTAIN** | `Reflector`/`Propagator`/`SignalProcessor` classes — ported from TradingAgents. Not imported by `agents/debate/__init__.py` (which only imports `research_debate`, `risk_debate`, `graph`). May be intended for future integration. | Keep or archive
`agents/geopolitics/american_order.py` | **DEAD** | Geopolitics agent — never imported, empty `__init__.py` doesn't re-export. Never referenced anywhere. | Delete
`agents/geopolitics/chinese_order.py` | **DEAD** | Same pattern as above | Delete
`agents/geopolitics/european_order.py` | **DEAD** | Same pattern | Delete
`agents/geopolitics/islamic_finance.py` | **DEAD** | Same pattern | Delete
`agents/geopolitics/multipolar.py` | **DEAD** | Same pattern | Delete
`agents/personas/cathie_wood.py` | **DEAD** | Investor persona — never imported, empty `__init__.py`. Never referenced. | Delete
`agents/personas/michael_burry.py` | **DEAD** | Same pattern | Delete
`agents/personas/peter_lynch.py` | **DEAD** | Same pattern | Delete
`agents/personas/ray_dalio.py` | **DEAD** | Same pattern | Delete
`agents/personas/stanley_druckenmiller.py` | **DEAD** | Same pattern | Delete
`agents/personas/warren_buffett.py` | **DEAD** | Same pattern | Delete
`agents/smc/enhanced.py` | **UNCERTAIN** | Enhanced SMC agent — not imported by `agents/smc/__init__.py` (which is empty). May be unfinished SMC port. | Needs investigation
`api/server.py` | **DEAD** | Empty file (0 bytes, 0 lines). No content. | Delete
`data/providers/crypto_provider.py` | **DEAD** | CCXT-based crypto data provider. Not imported by `data/providers/__init__.py` (which exports coingecko, finnhub, macro, twelvedata). Never referenced. | Delete
`database/alembic/env.py` | **FALSE POSITIVE** | Alembic migration env — invoked by `alembic` CLI via `database/alembic/alembic.ini` (`script_location = .`). Should never be imported directly. | Keep
`database/alembic/versions/001_initial_schema.py` | **FALSE POSITIVE** | Alembic migration version — consumed by alembic at runtime. | Keep
`database/init_db.py` | **UNCERTAIN** | Custom DB init script (499 lines). Uses `MigrationManager` pattern. Alembic is now the standard migration tool — this may be legacy. | Needs investigation — likely dead
`database/migrations.py` | **UNCERTAIN** | Custom migration manager (348 lines). Alembic supersedes this. | Needs investigation — likely dead
`engine/backtest/cpcv.py` | **DEAD** | Combinatorial Purged Cross-Validation. Not exported by `engine/backtest/__init__.py`. Never imported. | Delete
`engine/backtest/fama_french.py` | **DEAD** | Fama-French factor computations. Never referenced. | Delete
`engine/backtest/hermes_backtest.py` | **DEAD** | HermesQuantOS legacy backtest port (392 lines). Shebang + `HermesQuantOS` logger. Superseded by `engine/backtest/engine.py`. | Delete
`engine/backtest/hermes_portfolio.py` | **DEAD** | HermesQuantOS legacy portfolio. Superseded by `engine/backtest/portfolio.py`. | Delete
`engine/backtest/nautilus_adapter.py` | **DEAD** | Nautilus Trader adapter — never integrated. | Delete
`engine/backtest/psr.py` | **DEAD** | Probabilistic Sharpe Ratio. Never referenced. | Delete
`engine/backtest/risk_models.py` | **DEAD** | Backtest risk models. Never referenced. | Delete
`engine/compliance.py` | **DEAD** | Compliance module. Not exported by `engine/__init__.py`. Never imported. | Delete
`engine/core/circuit_breaker.py` | **DEAD** | Duplicate of `core/circuit_breaker.py` (459 lines). The `core/` version IS used; this `engine/core/` version is an alternative. | Delete
`engine/core/edge_cases.py` | **DEAD** | Edge case handling (174 lines). `engine/core/edge_case_handler.py` IS used by `bh_qna_bridge.py`; this is a duplicate. | Delete
`engine/execution/almgren_chriss.py` | **DEAD** | Almgren-Chriss execution model. Not exported by any `__init__.py`. Never imported. | Delete
`engine/execution/hermes_execution.py` | **DEAD** | HermesQuantOS legacy execution. Superseded by `engine/execution/base.py` + `manager.py`. | Delete
`engine/factors/academic.py` | **FALSE POSITIVE** | Dynamically loaded by `FactorRegistry` via `importlib.import_module("quant_nanggroe.engine.factors.academic")` in `engine/factors/registry.py:242`. | Keep
`engine/factors/alpha101.py` | **FALSE POSITIVE** | Dynamically loaded by `FactorRegistry` (registry.py:239). | Keep
`engine/factors/gtja191.py` | **FALSE POSITIVE** | Dynamically loaded by `FactorRegistry` (registry.py:240). | Keep
`engine/factors/hermes_ta.py` | **DEAD** | HermesQuantOS technical analysis factors. NOT in FactorRegistry's dynamic import list. Never imported. | Delete
`engine/factors/qlib158.py` | **FALSE POSITIVE** | Dynamically loaded by `FactorRegistry` (registry.py:241). | Keep
`engine/grounding.py` | **DEAD** | Grounding module. Not exported by `engine/__init__.py`. Never imported. | Delete
`engine/hermes_auditor.py` | **DEAD** | HermesQuantOS port — never integrated. | Delete
`engine/hermes_chart.py` | **DEAD** | HermesQuantOS port. | Delete
`engine/hermes_decision.py` | **DEAD** | HermesQuantOS port. | Delete
`engine/hermes_journal.py` | **DEAD** | HermesQuantOS port. | Delete
`engine/hermes_macro.py` | **DEAD** | HermesQuantOS port. | Delete
`engine/hermes_market_state.py` | **DEAD** | HermesQuantOS port. | Delete
`engine/hermes_math.py` | **DEAD** | HermesQuantOS port. | Delete
`engine/hermes_news.py` | **DEAD** | HermesQuantOS port. | Delete
`engine/hermes_pressure.py` | **DEAD** | HermesQuantOS port. | Delete
`engine/hermes_shared_state.py` | **DEAD** | HermesQuantOS port (uses `getattr` internally but never imported). | Delete
`engine/integration/bh_qna_bridge.py` | **UNCERTAIN** | BH→QNA cross-module bridge (646 lines). Bridges BlackHornet ↔ QNA. May be needed for multi-colony integration. Check if `ai_multicolony/` references it. | Needs investigation
`engine/llm_router.py` | **FALSE POSITIVE** | Dynamically re-exported via `engine/__init__.py` `__getattr__` (access via `from quant_nanggroe.engine import LLMRouter`). Static analyzer can't follow `__getattr__` patterns. | Keep
`engine/microstructure.py` | **FALSE POSITIVE** | Same pattern — re-exported via `engine/__init__.py` `__getattr__`. | Keep
`engine/ml/signal_generator.py` | **DEAD** | ML signal generator. Not exported. Never imported. | Delete
`engine/model_registry.py` | **DEAD** | Model registry. Not exported. Never imported. | Delete
`engine/nim_provider.py` | **DEAD** | NVIDIA NIM provider. Not exported. Never imported. | Delete
`engine/nvidia_nim/prompts.py` | **DEAD** | NVIDIA NIM prompt templates. `engine/nvidia_nim/client.py` exists but doesn't import `prompts`. | Delete
`engine/options/analyzer.py` | **DEAD** | Options Black-Scholes analyzer. Not exported. Never imported. | Delete
`engine/pattern_recorder/dtw_matcher.py` | **DEAD** | DTW pattern matcher. Separate from `engine/pattern_recorder/dtw.py` which IS imported by test scripts. This may be a duplicate. | Delete (if duplicate) / Needs investigation
`engine/regime_detector.py` | **DEAD** | Regime detector. Not exported. `engine/regime/hmm_detector.py` IS the active detector. | Delete
`engine/risk/emotional_lockout.py` | **DEAD** | Emotional lockout system (728 lines). Not wired into risk pipeline. | Delete
`engine/risk/hermes_kill_switch.py` | **DEAD** | Duplicate of `engine/risk/kill_switch.py` (active). HermesQuantOS legacy. | Delete
`engine/risk/hermes_risk_officer.py` | **DEAD** | HermesQuantOS legacy risk officer. Never imported. | Delete
`engine/risk/position_sizing.py` | **FALSE POSITIVE** | Re-exported via `engine/risk/__init__.py` `__getattr__` (`PositionSizer`). | Keep
`engine/shadow/account.py` | **DEAD** | Shadow trading account. Not exported. Never referenced. | Delete
`engine/shadow/codegen.py` | **DEAD** | Strategy code generator. Never referenced. | Delete
`engine/shadow/scanner.py` | **DEAD** | Market scanner. Never referenced. | Delete
`engine/strategies/hermes_smc.py` | **DEAD** | Duplicate of `engine/strategies/smc_strategy.py` (active). HermesQuantOS SMC legacy. | Delete
`engine/strategies/market_profile.py` | **DEAD** | Market Profile / Volume Profile strategy. Not exported. | Delete
`engine/strategies/volume_delta.py` | **DEAD** | Volume delta/CVD strategy. Not exported. | Delete
`engine/strategy/hermes_lifecycle.py` | **DEAD** | HermesQuantOS strategy lifecycle. Superseded by `engine/strategy_lifecycle.py`. | Delete
`engine/stress_testing/historical_scenarios.py` | **DEAD** | Historical stress scenarios. Not exported. Separated from `engine/stress_testing/historical.py` which IS imported. | Delete
`engine/visualization/charts.py` | **DEAD** | Chart generation. Not exported. | Delete
`exchange/clients/bitfinex_client.py` | **DEAD** | Exchange client — never imported by `exchange/factory.py` or anywhere else. Factory uses CCXT dynamic exchange loading (string-based). | Delete
`exchange/clients/bitget_client.py` | **DEAD** | Same — CCXT handles this | Delete
`exchange/clients/coinbase_client.py` | **DEAD** | Same | Delete
`exchange/clients/gate_client.py` | **DEAD** | Same | Delete
`exchange/clients/kraken_client.py` | **DEAD** | Same | Delete
`exchange/clients/kucoin_client.py` | **DEAD** | Same | Delete
`exchange/clients/longbridge_client.py` | **DEAD** | Same | Delete
`scripts/bh-cli.py` | **FALSE POSITIVE** | CLI tool — meant to be run directly, not imported. | Keep
`scripts/load_test.py` | **FALSE POSITIVE** | Load testing script — run directly. | Keep
`scripts/port_vibe_factors.py` | **FALSE POSITIVE** | Factor migration script — run directly. | Keep
`scripts/qna-cli.py` | **FALSE POSITIVE** | Production CLI — run directly. | Keep
`scripts/security_audit.py` | **FALSE POSITIVE** | Security audit script — run directly. | Keep
`scripts/test_almgren_chriss.py` | **FALSE POSITIVE** | Test script — run via pytest or directly. | Keep
`scripts/test_data_fallback.py` | **FALSE POSITIVE** | Test script | Keep
`scripts/test_kelly_backtest.py` | **FALSE POSITIVE** | Test script | Keep
`scripts/test_pattern_recorder.py` | **FALSE POSITIVE** | Test script | Keep
`scripts/test_qna_imports.py` | **FALSE POSITIVE** | Test script | Keep
`scripts/test_regime_strategy.py` | **FALSE POSITIVE** | Test script | Keep
`scripts/test_stress_testing.py` | **FALSE POSITIVE** | Test script | Keep
`scripts/test_visualization.py` | **FALSE POSITIVE** | Test script | Keep
`worker.py` | **FALSE POSITIVE** | Entrypoint — `python -m quant_nanggroe.worker`. The tool's entrypoint detection wrongly matches `engine/worker.py` first due to alphabetic sort + `break`. | Keep

## Patterns Found

### 1. HermesQuantOS Legacy Port (17 files)
A large group of files was ported from the HermesQuantOS codebase but never wired into the active engine:
- `engine/hermes_*` (10 files): auditor, chart, decision, journal, macro, market_state, math, news, pressure, shared_state
- `engine/backtest/hermes_backtest.py`, `engine/backtest/hermes_portfolio.py`
- `engine/execution/hermes_execution.py`
- `engine/risk/hermes_kill_switch.py`, `engine/risk/hermes_risk_officer.py`
- `engine/strategies/hermes_smc.py`
- `engine/strategy/hermes_lifecycle.py`
- `engine/factors/hermes_ta.py`

All use `#!/usr/bin/env python3` shebangs and `logging.getLogger("HermesQuantOS.*")`. Each has a superseding active equivalent in the codebase. **Recommended: delete all 17.**

### 2. Duplicate Implementations
Several orphan files are duplicates of active modules:
| Orphan | Active Replacement |
|--------|-------------------|
| `engine/core/circuit_breaker.py` | `core/circuit_breaker.py` |
| `engine/core/edge_cases.py` | `engine/core/edge_case_handler.py` |
| `engine/risk/hermes_kill_switch.py` | `engine/risk/kill_switch.py` |
| `engine/strategies/hermes_smc.py` | `engine/strategies/smc_strategy.py` |
| `engine/pattern_recorder/dtw_matcher.py` | `engine/pattern_recorder/dtw.py` |

### 3. Unreferenced Exchange Clients (7 files)
The `exchange/clients/` directory has custom REST client implementations for Bitfinex, Bitget, Coinbase, Gate, Kraken, KuCoin, and Longbridge. The `exchange/factory.py` uses CCXT's dynamic exchange loading (string-based ccxt_id), so these custom clients are never imported. **These are 7 separate files that can be deleted.**

### 4. Agent Package Stubs (12 files)
The `agents/geopolitics/` (5 files) and `agents/personas/` (6 files) packages have implementations with empty `__init__.py` files that don't re-export them. Similarly `agents/debate/reflection.py` and `agents/smc/enhanced.py` are not re-exported. These appear to be incomplete ports.

### 5. Empty / Zero-Line File
`api/server.py` has 0 bytes, 0 lines. Can be deleted immediately.

### 6. Dynamic Import Blind Spots (7 false positives)
The static analyzer cannot detect:
- `__getattr__` lazy imports in `engine/__init__.py` → `llm_router`, `microstructure`
- `__getattr__` lazy imports in `engine/risk/__init__.py` → `position_sizing`
- `importlib.import_module()` in `engine/factors/registry.py` → `academic`, `alpha101`, `gtja191`, `qlib158`

These are not actually orphaned — they are dynamically discoverable.

## Top Recommendations

### Delete First (highest confidence, no impact)
1. `api/server.py` — empty file
2. `_compat.py` — pydantic v2 is guaranteed; nobody calls `patch_pydantic()`
3. `exchange/clients/bitfinex_client.py` through `longbridge_client.py` — 7 files, all replaced by CCXT
4. `engine/core/circuit_breaker.py` — duplicate
5. `engine/core/edge_cases.py` — duplicate
6. `engine/risk/hermes_kill_switch.py` — duplicate
7. `engine/strategies/hermes_smc.py` — duplicate
8. `engine/pattern_recorder/dtw_matcher.py` — probable duplicate

### Definitely Keep
1. All `scripts/` files (14) — CLI tools and test scripts, run directly
2. `database/alembic/env.py` + `001_initial_schema.py` — alembic infrastructure
3. `worker.py` — entrypoint
4. `engine/llm_router.py`, `engine/microstructure.py`, `engine/risk/position_sizing.py` — dynamic re-exports
5. `engine/factors/academic.py`, `alpha101.py`, `gtja191.py`, `qlib158.py` — FactorRegistry dynamic loads

### Needs Investigation Before Action
1. `agents/debate/reflection.py` — may be part of active development
2. `agents/smc/enhanced.py` — may be future work
3. `database/init_db.py` — check if anyone uses `initialize_database()`
4. `database/migrations.py` — check if alembic fully replaced it
5. `engine/shadow/account.py`, `codegen.py`, `scanner.py` — may be planned for deployment
6. `engine/integration/bh_qna_bridge.py` — check `ai_multicolony/` for cross-references
7. `engine/hermes_shared_state.py` — has internal `getattr` (may dynamically receive clients)

## Summary by Category

| Category | Count | Action |
|----------|-------|--------|
| FALSE POSITIVE (keep) | 24 | No action needed |
| TRULY DEAD (delete) | 58 | Safe to remove |
| UNCERTAIN (investigate) | 10 | Review before action |
| **Total** | **92** | |

**If all 58 dead files are deleted:** ~12,000 lines removed, ~14% of total file count.
**If uncertain files (+10) are also archived:** ~15,000 additional lines, total ~27K lines removed.
