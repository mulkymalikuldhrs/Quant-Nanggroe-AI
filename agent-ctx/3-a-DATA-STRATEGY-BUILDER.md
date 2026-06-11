# Task 3-a: DATA-STRATEGY-BUILDER

## Task
Add missing data providers (FRED, SEC EDGAR, TwelveData) and YAML Strategy System to quant_nanggroe

## Work Completed

### New Data Providers (3 files)
1. `quant_nanggroe/data/providers/fred.py` — FRED macro-economic data provider
2. `quant_nanggroe/data/providers/sec_edgar.py` — SEC EDGAR filings/fundamentals provider  
3. `quant_nanggroe/data/providers/twelvedata.py` — TwelveData global equity/forex/crypto provider

### YAML Strategy System (4 files + init)
1. `quant_nanggroe/engine/strategy/__init__.py` — Module exports
2. `quant_nanggroe/engine/strategy/schema.py` — Pydantic v2 models (StrategyConfig, EntryRule, ExitRule, RiskRules, UniverseDefinition)
3. `quant_nanggroe/engine/strategy/parser.py` — YAML parser + code generator
4. `quant_nanggroe/engine/strategy/loader.py` — Strategy loader, registry, hot-reload
5. `quant_nanggroe/engine/strategy/backtest_adapter.py` — Strategy → backtest signal adapter

### Updated Files
- `quant_nanggroe/data/providers/__init__.py` — Added 3 new provider imports/exports

### Test Files (4 files, 217 tests)
1. `tests/test_data/test_fred_provider.py` — 37 tests
2. `tests/test_data/test_sec_edgar_provider.py` — 32 tests
3. `tests/test_data/test_twelvedata_provider.py` — 34 tests
4. `tests/test_engine/test_strategy.py` — 114 tests

## Test Results
- 217 new tests: ALL PASSING
- 1,068+ total tests across project: PASSING
- No regressions introduced
- All tests deterministic, no API keys needed, all external calls mocked
