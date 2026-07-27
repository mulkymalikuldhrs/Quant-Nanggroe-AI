# GitHub Copilot Instructions — Quant Nanggroe AI v6.2.0

## Entry Point
Single entry: `python qna.py [unified|api|daemon|hedge|status|stop]`

## Suggested Ignore Patterns
- `paper_state/*.json` — auto-generated trading state.
- `data/*` — runtime data.
- `node_modules/` — JavaScript dependencies.
- `__pycache__/` — Python cache.
- `archive/` — Legacy files (do not edit).

## Commit Message Convention
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `refactor:` Code refactoring
- `test:` Test changes
- `chore:` Maintenance
- `audit:` Codebase audit
- `quant:` Quantitative engine addition

## Key Locations — Updated v6.2.0
- Strategies: `quant_nanggroe/engine/strategies/` (79+ registered, @StrategyRegistry.register)
- Strategy Registry: `quant_nanggroe/engine/strategies/registry.py` (StrategyRegistry — class registry, unchanged)
- Walk-Forward Metadata: `quant_nanggroe/engine/strategy/registry.py` (WalkForwardRegistry — renamed v6.2.0, was StrategyRegistry)
- Strategy Evolver: `quant_nanggroe/engine/strategies/strategy_evolver.py` (real WalkForwardAnalyzer)
- Risk: `quant_nanggroe/engine/risk/` (+ DCC-GARCH, unified PnL fractions)
- Causal: `quant_nanggroe/engine/causal/` (5 modules + CausalContext dataclass)
- HF Signals: `quant_nanggroe/hedge_fund/signals/core.py` (+ causal bias)
- Pipeline: `quant_nanggroe/pipeline/macro_context.py`
- Tests: `quant_nanggroe/tests/test_dcc_garch.py` (47 tests)
- Security: `QNAI_SSL_VERIFY` env guard, `.secrets-local/` deleted
- Docs: `docs/` (58 documents)
