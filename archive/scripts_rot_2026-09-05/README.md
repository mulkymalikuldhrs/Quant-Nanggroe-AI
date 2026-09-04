# Quarantined scripts — rot sweep 2026-09-05

Moved via `git mv` from `scripts/`. Each file below fails at import time
(stale module path, verified missing on disk) AND has zero live references
(grepped basename across `quant_nanggroe/`, `tests/`, `qna.py`,
`dashboard/src`, `.github/workflows` — no hits). Archive, never delete.

- backtest_dhaher.py — stale import `from backtest_pipeline import backtest, gate_decision, get_historical, walk_forward` (scripts/backtest_dhaher.py:22); no root-level `backtest_pipeline.py` exists (only `quant_nanggroe/backtest_pipeline.py`, which exports just `run_gate_check`); plus inserts nonexistent root `strategies/` dir (scripts/backtest_dhaher.py:25).
- test_dhaher_live.py — stale import `from multi_pair_scanner import scan_all_pairs, set_mock_mode` (scripts/test_dhaher_live.py:26); no top-level `multi_pair_scanner.py` exists (real module is `quant_nanggroe/hedge_fund/tools/multi_pair_scanner.py`, not on its `sys.path`).
- wf_microstructure.py — stale import `from quant_nanggroe.engine.strategy.strategies import new_proposals` (scripts/wf_microstructure.py:21); no `new_proposals` module exists anywhere (only `quant_nanggroe/engine/strategies/archive/archive_new_proposals.py` wrapper).
- optimize_dhaher_params.py — stale import `from quant_nanggroe.engine.strategy.backtest_adapter import BacktestConfig, backtest` (scripts/optimize_dhaher_params.py:19); no `backtest_adapter.py` exists anywhere in the repo.
- test_regime_strategy.py — stale import `from quant_nanggroe.engine.strategy.regime_strategy import RegimeAdaptiveStrategy` (scripts/test_regime_strategy.py:7); no `regime_strategy.py` exists anywhere in the repo.
- qna-paper-daemon.py — stale import `from quant_nanggroe.agents.compliance.agent import ComplianceAgent` (scripts/qna-paper-daemon.py:32); no `quant_nanggroe/agents/compliance/` package exists.
- validate_strategies.py — drifted singular-tree usage `pkg._NAME_MAP` (scripts/validate_strategies.py:44); verified absent on shim (`hasattr(_NAME_MAP)=False`, shim only re-exports `create_strategy`/`list_strategies`/`get_strategy`); zero live importers (only `_validate_strategies` method-name hits in `quant_nanggroe/engine/agentic/autonomous.py:159`, unrelated). Quarantined 2026-09-04 (PROMPT 2).

NOT quarantined (verified live or importable — do not re-add without new evidence):

- scripts/qna-toggle.py — LIVE: imported by `tests/test_scripts/test_toggle.py:15`.
- scripts/run_walkforward.py — LIVE: imported by `tests/test_walkforward.py:10,24` and `tests/test_walkforward_no_leak.py:27`.
- scripts/alpha_destruction.py, scripts/auto_rotate.py, scripts/auto_tune.py, scripts/regime_adaptive_execution.py, scripts/test_runner.py, scripts/validate_strategies.py, scripts/walkforward_runner.py, scripts/run_wf_validation.py, scripts/disaster_recovery_drill.py, scripts/ensemble_walk_forward.py, scripts/test_migrated_strategies.py — `quant_nanggroe.engine.strategy.strategies` / `.registry` imports resolve via the backward-compat shim at `quant_nanggroe/engine/strategy/strategies/__init__.py:1` (re-exports `create_strategy`, `list_strategies`, `get_strategy`); quarantining on the stale-import claim alone would be wrong.
- scripts/backtest_all.py, scripts/generate_strategies.py — hardcoded `D:\repositories\...` paths resolve on this machine (same pattern as protected `scripts/run_cpcv_validation.py` and `scripts/qna_autonomous_cycle.py`); `backtest_all.py` dynamically loads strategy files from the existing shim dir; needs-manual-review, not verified dead.

PROMPT 2 verdicts (2026-09-04, verified live — KEPT, no moves):
- ensemble_walk_forward.py, test_migrated_strategies.py — shim `create_strategy`/`list_strategies` resolve; zero live importers but no stale import → KEEP.
- walkforward_runner.py, run_wf_validation.py — canonical `engine.strategies.*` + `engine.strategy.registry` (`WalkForwardRegistry`/`WalkForwardResult` verified present); zero live importers → KEEP.
- alpha_destruction.py, auto_rotate.py, auto_tune.py, regime_adaptive_execution.py, test_runner.py, disaster_recovery_drill.py — live-referenced (`scripts/qnai`, `scripts/weekly_alpha_report.py:90`, `scripts/health_check.py:83`, `scripts/test_runner.py:300`) → KEEP. Note: `alpha_destruction.py:384` `_STRATEGY_REGISTRY`/`STRATEGY_REGISTRY` import is drifted but fail-soft inside try/except (`:433` logs "Walk-forward skipped"); walk-forward subpath only.
- backtest_all.py — 3 hardcoded `D:\...` paths replaced with `Path(__file__)`-anchored `_REPO_ROOT` (`scripts/backtest_all.py:18-20,228`); dynamically loads existing shim dir; zero live importers → KEEP (path-fixed, py_compile clean).
- generate_strategies.py — LEFT untouched for manual review: hardcoded `STRATEGIES_DIR` (`:12`) + `__init__`-patch markers (`'crypto_specific'`, `_NAME_MAP` at `:966-978`) no longer exist in shim `__init__` (would silently no-op while writing unregistered files into the shim dir).
- disaster_recovery_drill.py — LEFT: `--backup-dir` default `/tmp/qna-drill-backup` (`:65`) is Windows-wrong but user-overridable CLI default; changing defaults = behavior change → manual review.
