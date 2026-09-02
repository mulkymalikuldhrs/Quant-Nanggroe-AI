# Architecture Audit: Quant-Nanggroe-AI v5.1.0 (tag v15.3.0)
**Lens:** Research/Innovation — @dhaherresearchbot  
**Report to:** @dhaherautobot  
**Date:** 2026-07-25

---

### Finding 1: Entry Point Proliferation — qna.py Is NOT the Sole Entry Point
**Severity:** HIGH  
**Files:** Multiple

**Evidence:** AGENTS.md states: "`qna.py` — unified launcher. The ONLY root entry point. All others have been deleted."

This is factually incorrect. At least **4 distinct entry paths exist**:

| Entry Path | Mechanism | Bypasses qna.py? |
|---|---|---|
| `python qna.py` | Direct launcher (argparse) | No (the primary) |
| `qnai` CLI command | `pyproject.toml` → `[project.scripts] qnai = "quant_nanggroe.cli:main"` | **YES** |
| `qna-standalone` | `pyproject.toml` → `[project.scripts] qna-standalone = "quant_nanggroe.standalone:main"` | **YES** |
| `launch.bat` | Boots uvicorn directly: `uvicorn quant_nanggroe.api.app:app` | **YES** |

Additionally, `quant_nanggroe/engine/standalone.py` is a 1-line re-export (`from quant_nanggroe.standalone import *`), acting as a 5th latent entry point.

**Root Cause:** Multiple development phases added their own entry mechanisms without updating the central documentation or consolidating entry points.

**Recommendation:** Either delete pyproject.toml's `[project.scripts]`, normalize all entry through qna.py, or update AGENTS.md to accurately describe all 4 entry points and their purpose.

---

### Finding 2: File Count Delta — AGENTS.md Claims 177, Actual 406 (+129%)
**Severity:** HIGH  
**File:** `AGENTS.md`

**Evidence:** AGENTS.md references "177 files in engine/". Actual file counts:
- `quant_nanggroe/engine/` — **406 Python files** (vs. claimed 177)
- `quant_nanggroe/` total — **756 Python files** (no documented number exists)

**Per-directory breakdown of engine/:**
```
strategy/       148   ← single largest subdirectory (36% of engine)
backtest/        33
strategies/      29   ← parallel, overlapping strategy hierarchy
risk/            19
execution/       16
screener/        11
factors/         10
kelly/           10
agentic/          9
regime/           9
stress_testing/   9
pattern_recorder/ 7
colony/           6
analytics/        6
nvidia_nim/       6
data/             5
models/           5
shadow/           5
core/             4
fundamental/      4
ml/               4
options/          4
visualization/    4
analysis/         3
integration/      2       ← thin
live/             2       ← thin
portfolio/        2       ← thin
rl/               2       ← thin
scanner/          2       ← thin
api/              2       ← thin
simulation/       1       ← ghost wrapper
```

**Delta:** +229 files (129% more than documented). Internal docs are **4.3x outdated**.

**Root Cause:** No automated file-count validation. Docs were written for an earlier snapshot and never updated.

**Recommendation:** Add a `make filecount` target that generates the count from `find`, and embed the mechanic in CI/doc validation. Update AGENTS.md with actual numbers.

---

### Finding 3: 139 Duplicate Class Names — Critical Name Collision Risk
**Severity:** CRITICAL  
**Files:** Throughout `quant_nanggroe/`

**Evidence:** 139 distinct class names appear 2+ times across the codebase. Key overlaps:

| Class Name | Occurrences | Notable Locations |
|---|---|---|
| `StrategyType` | 5 | autoswitch.py, backtest/engine.py, strategies/base.py, strategy/strategies/base.py, strategy/schema.py |
| `StrategyRegistry` | 4 | strategies/registry.py, strategy/registry.py, strategy/loader.py, strategy/strategies/registry.py |
| `Position` | 7+ | connectors/broker_base.py, backtest/engines/base_engine.py, backtest/portfolio.py, shadow/account.py, schemas/positions.py, types/positions.py, execution/base.py |
| `StrategySignal` | 3 | strategies/base.py, strategy/strategies/base.py, agentic/final_decider.py |
| `SignalDirection` | 4 | agents/state.py, engine/ml/signal_generator.py, strategies/base.py, strategy/strategies/base.py |
| `PerformanceMetrics` | 4 | analytics/metrics.py, backtest/metrics.py, risk/enhanced_analytics.py, shadow/account.py |
| `KellyResult` | 3 | kelly/base.py, risk/enhanced_analytics.py, risk/kelly.py |
| `VaRResult` | 3 | backtest/risk_models.py, risk/var.py, stress_testing/var_cvar.py + types/risk.py |
| `CircuitBreaker` | 4 | core/circuit_breaker.py, engine/core/circuit_breaker.py, engine/nim_provider.py, exchange/alpaca_broker.py + engine/data/fallback_chain.py |
| `RiskManager` | 3 | agents/debate/engine.py, agents/debate_engine.py, engine/risk/manager.py |
| `WalkForwardResult` | 2 | backtest/walk_forward.py, strategy/registry.py |
| `MonteCarloResult` | 3 | backtest/monte_carlo.py, risk/enhanced_analytics.py, stress_testing/monte_carlo.py |
| `StrategyEvolver` | 2 | strategies/strategy_evolver.py, strategy/strategies/strategy_evolver.py |
| `SignalStrength` | 3 | strategies/base.py, strategy/strategies/base.py, schemas/signals.py, types/signals.py |
| `TaskType` | 3 | colony/tasks.py, nim_provider.py, nvidia_nim/models.py |
| `PositionSide` | 4 | shadow/account.py, schemas/positions.py, types/positions.py, options/strategies.py |

**Impact:** Import ambiguity (which `Position` are you using?), serialization conflicts, shadowing bugs, and inability to have a coherent type system. The AutoRegistry `health_check()` can never properly resolve these collisions.

**Root Cause:** Organic code growth with no namespace governance. Multiple developers on multiple branches independently defined the same domain classes.

**Recommendation:** Phase 1: Merge duplicate `types/` schemas as single-source-of-truth pydantic models. Phase 2: Eliminate parallel `strategies/` vs `strategy/strategies/` hierarchy. Phase 3: Run `grep -rn "^class " | sort | uniq -d` in CI to gate any new duplicate.

---

### Finding 4: Parallel Strategy Hierarchies — `strategies/` vs `strategy/strategies/`
**Severity:** CRITICAL  
**Files:** `engine/strategies/` (29 files) vs `engine/strategy/strategies/` (139 files)

**Evidence:** Two completely independent strategy implementation trees exist side-by-side:
- `engine/strategies/` (old hierarchy, 29 files)
- `engine/strategy/strategies/` (new hierarchy, 139 files)

These are **near-identical duplicates**:
- `base.py` in each is byte-for-byte identical (diff produced no output)
- `registry.py` in each differs only in `__all__` export (one exports `["StrategyRegistry"]`, the other adds convenience functions)
- Both export `StrategyType`, `SignalDirection`, `SignalStrength`, `SignalAction`, `StrategySignal`, `StrategyParameters`
- At least 12 strategies exist in BOTH trees (algebra, amdx, dhaher_system, ema_adx, fibo_strategy, fibonacci, gene_loader, ict, market_profile, mean_reversion, msnr, multi_timeframe_strategy, pairs_trade_strategy, quarterly_theory, smc_strategy, smc_strategy_OLD, tradebobby_smc_scanner, trend_follow_strategy, tsmom_strategy, unified_retail, volume_delta, wyckoff, xgboost_alpha_strategy, kronos_wrapper)

The `strategy/loader.py` (line 70) imports from `engine/strategies.registry` (the old hierarchy), while `strategy/strategies/` (the new hierarchy) has its own registry — creating **circular import risk**.

**Root Cause:** During a refactor to expand the strategy library, the new `engine/strategy/strategies/` tree was created without removing the old `engine/strategies/` tree.

**Recommendation:** Deprecate and delete `engine/strategies/` (29 files). Move any strategies unique to that tree into `engine/strategy/strategies/`. Fix `loader.py` to import from the canonical location.

---

### Finding 5: AutoRegistry v3 — Superficial Scanning, Not 756-File Registration
**Severity:** MEDIUM  
**File:** `quant_nanggroe/engine/registry.py`

**Evidence:** `AutoRegistry.discover_all()` scans dirs with `rglob("*.py")` and registers **every class found**, keyed case-insensitively by `.lower()`. However:

1. **Key collision by design**: `StrategyType.lower()` from 5 different files will overwrite each other in the registry dict — the last one wins silently. With 139 duplicate class names, the registry is **non-deterministic**.
2. **No module dedup**: Each `.py` file is imported by filename stem (`mod_name = py_file.stem`). If two files have the same stem (e.g., `strategies/base.py` and `strategy/strategies/base.py`), they collide.
3. **Import-level failure is non-fatal**: If `importlib` fails for any file, it's swallowed silently (`logger.debug`).
4. **No cross-version validation**: The registry's `health_check()` only checks file existence (stale entries), not that registered classes actually load correctly.

**Registration Completeness Check:** The `discover_from_dir` scans ALL `.py` files but only registers classes whose `__module__` matches the loaded module name. It registers an unbounded number of classes — potentially including utility classes, enums, and internal types that shouldn't be in a queryable registry.

**Root Cause:** The AutoRegistry was designed as a "scan everything" catch-all, but 139 duplicate names make its output unreliable. The registry's design assumes a flat namespace that doesn't exist.

**Recommendation:** (a) Add duplicate-name detection in `health_check()` and flag it. (b) Consider using fully qualified names (module.path.ClassName) instead of lowercased class names. (c) Add a `_skip_classes` filter or explicit `__all__`-based registration for production use.

---

### Finding 6: Registry Fragmentation — 7 Registry Implementations
**Severity:** HIGH  
**Files:** 7 registry files across the codebase

**Evidence:** There are **7 distinct registry implementations**, each with different APIs:
1. `engine/registry.py` — `AutoRegistry` (hash-based, scans entire repo, keyed by lowercase)
2. `engine/strategy/registry.py` — `StrategyRegistry` (walk-forward framework, JSON serialization, `StrategyMetadata` dataclass)
3. `engine/strategies/registry.py` — `StrategyRegistry` (decorator-based, module-level `_registry` dict, `Type[Strategy]`)
4. `engine/strategy/strategies/registry.py` — `StrategyRegistry` (nearly identical to #3, differs only in `__all__`)
5. `engine/factors/registry.py` — `FactorRegistry` (AlphaFactor handles, lazy instantiation, zoo/theme/universe filtering)
6. `engine/pattern_recorder/registry.py` — `PatternRegistry` (cosine-similarity search, performance tracking)
7. `hedge_fund/signals/registry.py` — Passive re-export of `CORE_PROVIDERS`, `QNA_EVOLVED_PROVIDERS`, `ALL_PROVIDERS` from `hedge_fund.py`

Three of these (`#2`, `#3`, `#4`) are all called `StrategyRegistry` but have **completely different APIs and purposes**.

**Root Cause:** Each domain team built its own registry without coordination. No central registry architecture was established.

**Recommendation:** Consolidate all strategy registries (#2, #3, #4) into a single `StrategyRegistry` in `engine/strategy/registry.py`. Move the FactorRegistry and PatternRegistry under a unified `engine/registry/` package. Eliminate the duplicate in `engine/strategy/strategies/registry.py` and the hedge_fund passive re-export.

---

### Finding 7: Zombie/Ghost Subdirectories in Engine
**Severity:** LOW  
**Files:** Multiple

**Evidence:** Several engine subdirectories contain minimal or no meaningful code:

| Directory | Files | Real Content? |
|---|---|---|
| `engine/simulation/` | 1 | **Ghost** — `__init__.py` just re-exports from `engine/backtest/monte_carlo.py`. No unique code. |
| `engine/standalone.py` | 1 | **Stub** — 1-line `from quant_nanggroe.standalone import *` |
| `engine/integration/` | 2 | **Thin** — unclear integration purpose |
| `engine/live/` | 2 | **Thin** — only 2 files for "live trading" concept |
| `engine/portfolio/` | 2 | **Thin** — only 2 files in the portfolio module |
| `engine/api/` | 2 | **Thin** — only 2 API-related files |
| `engine/scanner/` | 2 | **Thin** — market scanning in only 2 files |
| `engine/rl/` | 2 | **Minimal** — RL module started but not grown |
| `engine/core/` | 4 | **Minimal** — core circuit_breaker.py duplicated elsewhere |

Meanwhile, `engine/strategy/` has **148 files** (36% of engine), representing a massive asymmetry.

**Root Cause:** Organic growth with no refactoring discipline. Some modules were started but abandoned; others (strategy) exploded in scope.

**Recommendation:** Audit each thin directory for whether it should be (a) merged into a related module, (b) expanded with planned code, or (c) deleted. Measure module size ratios and flag >5x asymmetry in CI.

---

### Finding 8: Hedge Fund Layer Duplicates Core Engine
**Severity:** MEDIUM  
**Files:** `quant_nanggroe/hedge_fund/` (28 files)

**Evidence:** The `hedge_fund/` package duplicates structure from `engine/`:

| hedge_fund subdir | Engine equivalent | Overlap |
|---|---|---|
| `hedge_fund/execution/` | `engine/execution/` | Duplicate order management |
| `hedge_fund/portfolio/` | `engine/portfolio/` | Duplicate portfolio logic |
| `hedge_fund/risk/` | `engine/risk/` | Duplicate risk guards/gates |
| `hedge_fund/signals/` | `engine/strategies/` + `engine/factors/` | Duplicate signal aggregation |
| `hedge_fund/utils/config.py` | `engine/core/` or top-level `config/` | Duplicate config |

The `hedge_fund/runner.py`, `mtf.py`, and `multipair.py` add unique orchestration logic that arguably should live inside the engine, not in a parallel package.

**Root Cause:** The hedge_fund was developed as a standalone system that was later merged into the monorepo without integration.

**Recommendation:** Determine whether `hedge_fund/` should be (a) refactored to call engine directly (eliminating duplicates), (b) remain as an orchestration layer that imports engine code, or (c) remain separate with documented rationale. Current half-in/half-out state is worst of both worlds.

---

### Finding 9: `strategy/loader.py` Imports Across Hierarchy Boundary — Circular Import Risk
**Severity:** MEDIUM  
**File:** `quant_nanggroe/engine/strategy/loader.py:70`

**Evidence:** `loader.py` (line 70) imports from the old strategy hierarchy:
```python
from quant_nanggroe.engine.strategies.registry import StrategyRegistry as _Reg
```

Meanwhile, the new hierarchy (`engine/strategy/strategies/`) has its own near-identical `registry.py`. This creates a **bidirectional dependency risk** between the two parallel hierarchies. If any file in the old `strategies/` tree imports from `engine/strategy/`, a circular import would result.

No circular import was detected at runtime in the current codebase, but this creates an **extremely fragile dependency** — adding any `from engine.strategy` import on the `strategies/` side would immediately deadlock.

**Root Cause:** The two trees were never fully separated. `loader.py` was updated to use the new tree's functionality but retained old imports.

**Recommendation:** Eliminate the old `engine/strategies/` tree (see Finding 4). Change `loader.py` to import from `engine.strategy.registry` instead of `engine.strategies.registry`.

---

### Finding 10: AGENTS.md Architecture Documentation Lags Reality
**Severity:** MEDIUM  
**File:** `AGENTS.md`

**Evidence:** Multiple discrepancies beyond file counts:
- Claims "all other entry points have been deleted" → 3 other entry points exist
- Claims "32 active files" in docs/ → Only 10 doc files exist in `docs/`
- Listed reading order references documents (00_VISION, 01_PRD, 02_ARCHITECTURE, 15_CONTEXT, etc.) that **do not exist** in the documented format
- References `48_REPOSITORY_AUDIT.md` as "single most important doc" → Not found in repository

**Root Cause:** AGENTS.md was written for an idealized architecture that wasn't maintained as code evolved.

**Recommendation:** Rewrite AGENTS.md to reflect the actual architecture. Remove references to non-existent documents. Add automated README/AGENTS.md validation that cross-checks documented file counts against `find` output.

---

## Executive Summary

| # | Finding | Severity | Impact |
|---|---|---|---|
| 1 | Entry point proliferation (4 instead of 1) | HIGH | Security, confusion, bypass of unified config |
| 2 | File count 406 vs claimed 177 (+129%) | HIGH | Docs 4.3x outdated, no CI guard |
| 3 | **139 duplicate class names** | **CRITICAL** | Name collisions, broken registry, import ambiguity |
| 4 | **Parallel strategy hierarchies** | **CRITICAL** | 29 + 139 files doing the same thing, circular import risk |
| 5 | AutoRegistry v3 non-deterministic | MEDIUM | Key collisions from 139 duplicates make registry unreliable |
| 6 | 7 registry implementations | HIGH | Fragmented API, 3x `StrategyRegistry` collision |
| 7 | Zombie/ghost subdirectories | LOW | Dead weight, misleading structure |
| 8 | Hedge fund duplicates engine | MEDIUM | Parallel execution/portfolio/risk/signals |
| 9 | Cross-hierarchy import risk | MEDIUM | Fragile dependency, potential circular deadlock |
| 10 | AGENTS.md reality gap | MEDIUM | Missing docs, wrong counts, phantom references |

**Top 3 Actions:**
1. **Eliminate parallel strategy hierarchies** (`strategies/` vs `strategy/strategies/`) — biggest single source of duplication (29 + 139 overlapping files)
2. **Resolve 139 duplicate class names** — start with domain types (Position, Signal, StrategyType, RiskManager) via `types/` schemas
3. **Normalize entry points** — either delete `[project.scripts]` or update docs; eliminate qna.py bypasses

---

*End of Phase 1 — Architecture & Structure Audit. Proceeding to Phase 2 (Data Flow & Dependency Audit) on request.*

---


---

> **SSOT:** `CANONICAL.md` v8.0.22 — BAL $1,445, weekly 0 WIB, probe 0/32, CPCV 207, vector 6 modul live
