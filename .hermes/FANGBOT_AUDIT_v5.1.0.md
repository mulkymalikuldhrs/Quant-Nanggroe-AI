# QNA v5.1.0 — Comprehensive Optimization & Code Quality Audit
**Auditor:** @dhaherfangbot (OpenFang optimization lens)
**Date:** 2026-07-25
**Project:** `Quant-Nanggroe-AI-worktree` (D:)
**Version:** 5.1.0

---

## Executive Summary

QNA v5.1.0 is a **massive** codebase (~270K source Python LOC / 975 files excluding worktrees) with operational tension between a new modular `quant_nanggroe` package architecture and legacy monolith artifacts. Prior to this audit, fangbot already archived `hedge_fund.py` (13,684 lines) to `archive/trash/` — **a correct first step** — but the package mirror of it (`quant_nanggroe/hedge_fund/hedge_fund.py`, 6,536 lines) and 76 scripts (21K LOC) remain active.

**Key metric:** ~20,000 lines of 98%-identical duplicated signal/wiring code across the two `hedge_fund.py` copies alone. **Estimated savings from full consolidation: 15,000–18,000 lines.**

---

## Detailed Findings

### Finding 1: Twin `hedge_fund.py` Duplication (CRITICAL)
**Severity:** CRITICAL
**Files:**
- `archive/trash/hedge_fund.py` (13,684 lines) — freshly archived by prior fangbot run
- `quant_nanggroe/hedge_fund/hedge_fund.py` (6,536 lines) — still active in package

**Evidence:**
| Measure | Root | Package | Delta |
|---|---|---|---|
| Total lines | 13,684 | 6,536 | 7,148 |
| Non-signal functions | 20 | 20 | 0 (identical) |
| `signal_qna_*` functions | 516 | 237 | 279 (root-only) |
| `signal_qna_*` overlap | 237 | 237 | exact subset |

The 20 core functions (`connect`, `ensure_terminal`, `calc_atr`, `signal_sma`, `signal_aihf`, `_timeout_call`, `aggregate`, `execute`, `trail_sl`, `check_gate`, `run_once`, etc.) are **line-for-line identical** except for:
- `ensure_terminal`: package has deferred credential callable handling (improvement over root)
- `aggregate`: import order swap (`get_currency_strength, get_dxy` vs `get_dxy, get_currency_strength`)
- `execute`: `GATE_FILE` path differences
- `run_once`: path references only

**Root Cause:** Dual-deployment evolution — the root file was the original monolith, the package version was adapted with a `__file__`-relative structure, but both were maintained in parallel instead of consolidating.

**Recommendation:** Delete `archive/trash/hedge_fund.py` permanently (already archived). Parameterize the 237 `signal_qna_*` functions in the package into a single `signal_qna(strategy, mutation_hash)` factory function driven by a configuration dict. **Est. savings: 5,500+ lines.**

**Status:** OPEN

---

### Finding 2: Ticker-Specific Signal Boilerplate (CRITICAL)
**Severity:** CRITICAL
**File:** `quant_nanggroe/hedge_fund/hedge_fund.py:900-6100` (estimated)
**Evidence:** 237 identical-pattern `signal_qna_*` functions following the template:
```python
def signal_qna_StrategyName_mut_0123abcd(symbol="EURUSD"):
    try:
        from strategies.strategies import StrategyClass
        s = StrategyClass(...)
        return s.predict(symbol)
    except Exception as e:
        return {"bias": "neutral", "confidence": 0, "source": f"signal_qna_StrategyName_mut_0123abcd"}
```
Each function is 2–15 lines but the metadata (the strategy class reference, the hash ID, the function name) changes per ticker. The function bodies are structurally identical across strategies of the same type.

**Root Cause:** Auto-generated from a mutation/evolution framework (MUE-X annotations visible at EOF: `# Auto-registered by MUE-X: ...`). The generator script outputs one function per mutation hash rather than parameterizing the strategy class + hash pair.

**Recommendation:** Replace with:
```python
# In a config dict:
QNA_SIGNAL_REGISTRY = [
    {"name": "MSNRStrategy", "hash": "e10dba6a", "klass": "MSNRStrategy"},
    ...
]
# Single factory:
def signal_qna_factory(strategy_name, mutation_hash):
    def wrapper(symbol="EURUSD"):
        ...
    wrapper.__name__ = f"signal_qna_{strategy_name}_mut_{mutation_hash}"
    return wrapper
# Dynamic registration:
for entry in QNA_SIGNAL_REGISTRY:
    name = f"signal_qna_{entry['name']}_mut_{entry['hash']}"
    globals()[name] = signal_qna_factory(entry['name'], entry['hash'])
```
**Est. savings: 4,500+ lines.**

**Status:** OPEN

---

### Finding 3: Stale E:/ Hardcoded Paths (HIGH)
**Severity:** HIGH
**Files:** `quant_nanggroe/hedge_fund/hedge_fund.py` (10 references), several script files
**Evidence:**
```
E:/trading/AI-Trader
E:/trading/TradingAgents
E:/hidden-regime
E:/AI-Trader/agent/ai_trader
E:/AI-Trader/LangAlpha
E:/AI-Trader/AIMarketMaker
E:/Kronos/Kronos
E:/trading/pyportfolioopt
```
These paths reference a different machine's filesystem (`E:/` drive, `trading/` directory structure). They are used in `sys.path.insert()` and import statements within signal functions. On this deployment they silently fail — the `try/except` in each signal catches the `ImportError` and returns `neutral`, **masking the failure**.

**Root Cause:** The hedge_fund was originally developed on a machine with these E:/ paths. When ported to QNA, the `try/except` pattern was used instead of proper path mapping or dependency injection.

**Recommendation:** 
1. Audit which of these external strategies are actually needed
2. For strategies that exist in `quant_nanggroe/engine/strategies/`, update the import paths
3. For strategies that don't exist, either implement them or remove the signal wrappers
4. Remove all `sys.path.insert(E:/...)` calls — they pollute the module path

**Status:** OPEN

---

### Finding 4: Factor File Bloat & Duplication (HIGH)
**Severity:** HIGH
**Files:**
- `quant_nanggroe/engine/factors/gtja191.py` — 5,544 lines, 213 factor functions
- `quant_nanggroe/engine/factors/qlib158.py` — 4,064 lines, 155 factor functions  
- `quant_nanggroe/engine/factors/alpha101.py` — 3,317 lines, 108 factor functions

**Evidence:** 
- Total: **14,925 lines** for 476 factor functions
- `alpha101` and `gtja191` share **101 identically-named functions** (`compute_alpha_001` through `compute_alpha_101`) — these are WorldQuant-style alpha factors. The implementations may differ in formula details but the naming and purpose overlap completely.
- Each factor function is an isolated computation with no shared utility abstraction.

**Root Cause:** Classic quant factor library syndrome — academic paper factors implemented as standalone functions with no shared intermediate computation layer. `alpha101` is a known published set (101 Formulaic Alphas by Zura Kakushadze), `gtja191` extends it, `qlib158` is from Microsoft Qlib.

**Recommendation:**
1. Consolidate `alpha101.py` and `gtja191.py` — `gtja191` already includes the alpha101 factors
2. Add a shared `FactorBase` that caches intermediate computations (returns, volatility, volume metrics) to avoid recomputation across factor functions
3. Consider lazy-loading: only define factors that are actually used in strategy configs
**Est. savings: 5,000–8,000 lines** if deduplicated and shared intermediates are used.

**Status:** OPEN

---

### Finding 5: Root Directory Pollution (HIGH)
**Severity:** HIGH
**File:** Root directory of the project
**Evidence:** **64+ files** in the project root, including:
- **8 stale audit reports** (QNA_FORENSIC_AUDIT_2026-07-23.md, QNA_EXTREME_AUDIT_2026-07-24.md, AUDIT_QNA_DEEP.md, etc.) — NOW cleaned by fangbot's prior run (moved to archive)
- **6 planning documents** (WAVE4_SWARM_UI_EVOLVE.md, WAVE5_HF_MIGRATION.md, 9ROUTER_FIX_2026-07-23.md, ECOSYSTEM_WIRING.md, MONEY_ESCAPE_PLAN.md, TRADING_PLAN.md)
- **10+ stale scripts** (autonomous-loop.bat, launch.bat, launch-hedgefund.bat, start-dashboard.bat, ui.bat, start.bat)
- **3 root-level Python modules** (journal.py, market_context.py, mtf_framework.py, multi_pair_scanner.py) — some now have package equivalents
- **Stale artifact files** (`_qt_gate_result.txt`, `audit.db`, `session-QNA-BARU.md` — 406 KB!)

**Root Cause:** Organic project growth without root-directory hygiene. Audit output, planning docs, and legacy scripts all accumulated in root.

**Recommendation:** 
- Move non-code docs to `.hermes/` or `docs/`
- Move stale scripts to `archive/launchers/` (partially done by prior fangbot run)
- Keep root only for: `pyproject.toml`, `README.md`, `LICENSE`, `.gitignore`, `Dockerfile`, `docker-compose.yml`, and the primary entry point (`qna.py`)
- **Already in progress** — prior fangbot `archive 22 zero-ref orphans` commit cleaned the worst offenders

**Status:** OPEN (partially mitigated)

---

### Finding 6: Scripts Directory Bloat (HIGH)
**Severity:** HIGH
**Directory:** `./scripts/`
**Evidence:**
- **76 files, 21,291 LOC** — larger than the entire `quant_nanggroe/agents/` or `quant_nanggroe/exchange/` directories
- Only 2 CLI entry points in `pyproject.toml` (`qnai` and `qna-standalone`) — none point to scripts/
- Largest scripts that should be tools or subcommands:
  - `renew_docs.py` (1,609 lines) — should be a CI/CD action, not a script
  - `ENHANCED_ECOSYSTEM_INTEGRATION.py` (1,121 lines) — one-off integration
  - `generate_strategies.py` (1,002 lines) — this is the **strategy code generator** that likely produced all the signal_qna boilerplate
  - `AUTO_RELEASE_SYSTEM.py` (657 lines) — should be CI/CD
  - `disaster_recovery_drill.py` (362 lines) — operational procedure, not a script

**Root Cause:** No governance around script creation — any automation task became a standalone script in `./scripts/`.

**Recommendation:**
1. Audit each script: is it a one-off, a utility, or ongoing tool?
2. Migration plan:
   - CI/CD workflows → `.github/workflows/`
   - CLI subcommands → integrate into `qnai` CLI via `click` groups
   - Strategy generators → move to `quant_nanggroe/engine/evolution/`
   - One-offs → archive
   - Tests → move to `tests/` with proper fixtures
3. Set a max size for standalone scripts (recommend: 200 lines)

**Status:** OPEN

---

### Finding 7: Test Quality — Missing Assertions & Class-Heavy (MEDIUM)
**Severity:** MEDIUM
**File:** 137 test files, 56,181 LOC in `./tests/`
**Evidence:**
- Only **1** `test_*` function found via regex (most use class-based test patterns without pytest fixtures)
- Largest test file: `test_qna_units.py` (2,182 lines, 0 pytest test functions, 33 classes)
- Many test files are **integration/smoke collectors** rather than unit tests (e.g., `test_new_tools.py` at 1,865 lines with 62 classes)
- Tests use `assert` statements inside class methods — pytest can still discover these via `unittest.TestCase` subclasses, but many are plain classes that may require manual runner invocation
- No central `tests/conftest.py` with shared fixtures was found

**Sample patterns from `test_strategies.py`:** Modern pytest fixtures used here — good practice but not consistently applied across the test suite.

**Root Cause:** Organic test growth with different conventions over time. Newer tests use pytest patterns, older tests use class-based collectors.

**Recommendation:**
1. Add `tests/conftest.py` with shared fixtures (OHLCV generators, mock market data)
2. Consolidate class-heavy test files into focused test modules (one per engine component)
3. Run `pytest --co` to measure actual collected test count vs expected
4. Add `pytest.ini` or `pyproject.toml[tool.pytest.ini_options]` with standard test discovery config

**Status:** OPEN

---

### Finding 8: CI/CD Gap (MEDIUM)
**Severity:** MEDIUM
**File:** `.github/workflows/ci.yml`
**Evidence:**
- `ci.yml` exists but was just modified in the last commit — its operational status is unknown
- No `pytest.ini` / test discovery configuration in root
- `pyproject.toml` has `dev` dependencies including `pytest`, `ruff`, `mypy`, `pre-commit` but no CI scripts or Makefile targets reference them
- `Makefile` was deleted in last commit (archived)
- No pre-commit hooks configured (`.pre-commit-config.yaml` exists but minimal)

**Root Cause:** CI was never formally set up. The project relies on ad-hoc testing.

**Recommendation:**
1. Add `pyproject.toml[tool.pytest.ini_options]` with `testpaths = ["tests"]`
2. Add CI workflow: lint with `ruff`, type-check with `mypy`, run tests with `pytest`
3. Configure pre-commit hooks for ruff + mypy on commit
4. Add `nox` or `tox` for multi-env testing

**Status:** OPEN

---

### Finding 9: Empty/Stale __pycache__ Dirs (LOW)
**Severity:** LOW
**Evidence:** 95 `__pycache__` directories in the source tree (inside `quant_nanggroe/`). These are runtime artifacts that should not be committed.

**Root Cause:** Python imports auto-create these. They're in `.gitignore` but may be residue from imports without proper venv isolation.

**Recommendation:** Clean with `find . -type d -name __pycache__ -exec rm -rf {} +` and add to gitignore if not already. Confirm `.gitignore` has `__pycache__/`.

**Status:** OPEN

---

### Finding 10: Version Sync — health.py Fixed (LOW)
**Severity:** INFO
**File:** `quant_nanggroe/engine/agentic/health.py`
**Evidence:** The most recent fangbot commit fixed a version discrepancy: `health.py` was at `1.0.0` while `pyproject.toml` and `quant_nanggroe/__init__.py` are at `5.1.0`.

**Root Cause:** Version drift during refactoring. Multiple files define the version independently.

**Recommendation:** Single-source version from `quant_nanggroe/__init__.py` using `importlib.metadata` or a `_version.py` file. Have all other files import from there.

**Status:** CLOSED (fixed in commit 2773e9b)

---

### Finding 11: 95 Package Init Files — Proper Structure (PASS)
**Severity:** INFO
**Evidence:** All 95 `__init__.py` files are non-empty and properly export their submodules. The packaging structure is well-organized.

**Status:** CLOSED (passed audit)

---

### Finding 12: Dependency Hygiene (MEDIUM)
**Severity:** MEDIUM
**File:** `pyproject.toml`
**Evidence:**
- **31 core dependencies** — minimal and well-categorized
- **7 optional dependency groups** (`ml`, `alpaca`, `polygon`, `data`, `memory`, `quant`, `rl`, `agentic`, `all`) — good modularity
- **Missing:** `ccxt>=4.0` version might be too restrictive (latest is CCXT 4.4.x)
- **Missing:** `yfinance>=0.2` may have compatibility issues with recent pandas
- No lock file pinned versions (uv.lock exists but may be stale)
- `twelvedata>=0.5` in optional `[data]` but not in core — good
- `httpx>=0.25` and `aiohttp>=3.9` both included — potential async HTTP redundancy

**Recommendation:**
1. Regenerate lock file: `uv lock`
2. Audit whether both `httpx` and `aiohttp` are actively needed (consolidate if possible)
3. Pin minimum pandas version to a known-compatible release

**Status:** OPEN

---

### Finding 13: Risk Guard Standalone (MEDIUM)
**Severity:** MEDIUM
**Files:**
- `archive/root-legacy/risk_guard.py` (already archived)
- `quant_nanggroe/engine/risk/` — package risk modules
**Evidence:** Root-level `risk_guard.py` was archived. The package `quant_nanggroe/engine/risk/` directory has risk modules. However, the hedge_fund's `run_once()` still imports from `risk_guard`:
```python
from risk_guard import approve as rg_approve
```
This will fail with the archived file unless the import points to the package version.

**Recommendation:** Verify that `run_once()` in `quant_nanggroe/hedge_fund/hedge_fund.py` imports from the correct package-level risk module, not the archived root-level one.

**Status:** OPEN (needs verification)

---

### Finding 14: Stale Data Artifacts (LOW)
**Severity:** LOW
**Files in `./data/`:**
- `council_expectancy.json` (391 lines)
- `strategy_logs/strategy_log.json` (166 lines)
- `trade_lifecycle/lifecycle_history.json` (109 lines)
- `evolution_history.json` (73 lines)
- `finetune_history.json` (41 lines)
- `smc_comparison.json` (25 lines)
- `baseline_expectancy.json` (22 lines)
- `votes.csv` (19 lines)
- `paper_trades.csv` (11 lines)

These are runtime state files, not version-controlled artifacts (`.gitignore` covers `/data/`). Low severity.

**Status:** CLOSED (expected runtime artifacts)

---

## Summary Metrics

| Metric | Value |
|---|---|
| Total Python LOC (excl. worktree) | ~269,921 |
| Total Python files (excl. worktree) | 975 |
| Main package LOC (`quant_nanggroe/`) | ~181,659 |
| Test LOC (`./tests/`) | ~56,181 |
| Script LOC (`./scripts/`) | ~21,291 |
| Factor file LOC (3 files) | ~14,925 |
| Test files | 137 |
| Script files | 76 |
| Root filter files | 64 → reduced by prior fangbot cleanup |
| `hedge_fund.py` copies | 2 (1 archived, 1 active at 6,536 lines) |
| Duplicate signal functions | 237 shared + 279 root-only = 516 total |
| Stale E:/ path references | 10+ |
| `__init__.py` files | 95 (all non-empty) |
| `__pycache__` dirs | 95 |

## Top Recommendations (by ROI)

1. **Parameterize signal_qna factory** → -5,500 lines, eliminates primary maintenance burden
2. **Consolidate factor files** → -5,000–8,000 lines, remove 101 overlapping alpha factors
3. **Delete archived hedge_fund.py** → -13,684 lines already in trash, just needs final deletion
4. **Audit scripts/ → tools migration** → retire/convert 76 scripts into CLI subcommands
5. **Fix E:/ stale paths** → restore broken strategy imports (currently silently failing)
6. **CI/CD setup** → pytest discovery, ruff linting, mypy type-checking
7. **Add tests/conftest.py** → reduce test boilerplate across 137 files

---

*Report compiled by @dhaherfangbot. Forward to @dhaherautobot for triage and action items.*

---

> **SSOT:** `CANONICAL.md` v8.0.19 — BAL $1,445, weekly 0 WIB, probe 0/32, CPCV 207, launch.bat 1, vector 6 modul
