# QNA x QuantScience MASTER → Repo Integration & Cleanup Plan

> **Orchestrator:** @dhaherautobot (only this bot may @mention; no cross-bot @mentions)
> **Author (executor):** fangbot — OpenFang Specialist (optimize → integrate → scale)
> **Source:** `C:\Users\Hi\Desktop\QuantScience_Archive\QNA_QuantScience_MASTER.md` (679 KB, 2026-08-01)
> **Target repo:** `D:\repositories\Quant-Nanggroe-AI-worktree` (QNA v5.1.0+, entry `qna.py`)
> **Status:** 📋 Plan — awaiting approval

**Goal:** Close the *real* remaining gap between the QuantScience MASTER roadmap and the current QNA repo. The master's §4.0 status matrix is **stale** — verified code inspection shows ~60% of items it marks OPEN are already DONE. This plan re-baselines reality, then executes only what's genuinely missing, in impact/effort priority order.

---

## 0. VERIFIED STATE vs MASTER DOC (2026-08-02, code-inspection, not .md)

### DONE — master marks OPEN, repo already has it (DO NOT REBUILD)
| Master item | Verified repo evidence |
|-|-|
| Alphalens factor analysis (QS015) | `quant_nanggroe/engine/factors/alphalens_adapter.py` (472 lines) |
| HRP allocator (QS014) | `quant_nanggroe/engine/portfolio/hrp_allocator.py` (237 lines) |
| KMeans clustering | `quant_nanggroe/engine/portfolio/clustering.py` |
| Autoencoder factors | `quant_nanggroe/engine/ml/autoencoder_factors.py` |
| DCC-GARCH + correlation regime | `quant_nanggroe/engine/risk/dcc_garch.py`, `correlation_regime.py` |
| Data quality framework (C8) | `quant_nanggroe/engine/data_quality/quality.py` + `monitor.py` + `api.py` |
| Downside deviation + Sortino | `quant_nanggroe/engine/risk/manager.py:507-538` |
| Telegram alerting (C4) | `quant_nanggroe/notifier.py` + `quant_nanggroe/agents/telegram_bot.py` |
| Multi-account MT5 (C6) | `quant_nanggroe/exchange/mt5_multi.py` + `mt5_broker.py` |
| WeightEvolver (B1) | `quant_nanggroe/core/scoring/evolver.py` (class WeightEvolver) |
| Scorer set (B2 partial) | 10+ scorers in `core/scoring/`: crypto, sentiment, positioning, volatility, bond, economic, geo, macro, technical + fusion_engine + mtf_engine |
| ffn + torch deps | `pyproject.toml`: `ffn>=1.0`, `torch>=2.2.0` |

### GENUINELY MISSING — the actual work
| # | Component | Master ref | Target file | Impact |
|-|-|-|-|-|
| M1 | Pytimetk feature engine | QS012 | `engine/factors/feature_engine.py` | High (20x feature gen) |
| M2 | MACD-as-factor | QS013 | `engine/factors/macd_factor.py` | High (alpha factor, -0.237 corr) |
| M3 | ffn analytics adapter | QS020 | `engine/analytics/ffn_adapter.py` | High (tear-sheet reporting) |
| M4 | Polars provider pilot | QS018 | `engine/data/providers/yahoo_polars.py` | Medium (10x data speed) |
| M5 | Missing quantscience deps | §6.2 | `pyproject.toml` `[optional-dependencies]` | Enabler for M1-M4 |

### UNVERIFIED — flag before touching
| Item | Master ref | Action |
|-|-|-|
| A1 evolution loop wiring (4 bugs, `main.py:847-854`) | A1 | **Stale path** — no `main.py` in repo; entry is `qna.py`. Re-locate: check `qna.py` + `engine/evolution/` wiring. |
| `get_valid_pairs` missing | A4 | Grep timed out (huge repo). Verify with targeted search before assuming. |
| Dashboard rebuild (A5) | A5 | `dashboard/` exists; build state unverified. |
| Test coverage 80% (C5) | C5 | 103 items in `tests/`; coverage % unmeasured. |
| Weight total 1.03 (B2) | B2 | `evolver.py` exists; weight-sum normalization unverified. |

---

## 1. PHASE 0 — RE-BASELINE (15 min, read-only)

**Objective:** Confirm the 5 UNVERIFIED items so we don't work stale facts.

- [ ] 0.1 — Evolution loop: `read_file qna.py` lines around scan/evaluate; `ls quant_nanggroe/engine/evolution/`
- [ ] 0.2 — `grep -n "def get_valid_pairs" quant_nanggroe/` (narrow, file_glob `*.py`)
- [ ] 0.3 — Dashboard: `ls dashboard/src/pages/`, check build artifacts timestamp
- [ ] 0.4 — Coverage baseline: `.venv/Scripts/python -m pytest tests/ --cov=quant_nanggroe --cov-report=term -q` (bounded: `-x --timeout=60` if pytest-timeout available)
- [ ] 0.5 — Weight sum: `grep -n "sum\|normalize" quant_nanggroe/core/scoring/evolver.py`

**Exit criteria:** UNVERIFIED column resolved to DONE/OPEN. Plan §2-4 adjusted accordingly.

---

## 2. PHASE 1 — QUICK WINS (½–1 day)

### Task 1.1: Add quantscience optional deps (M5)
**Files:** `pyproject.toml`
```toml
[project.optional-dependencies]
quantscience = [
    "polars>=1.0",
    "pytimetk>=0.3",
    "alphalens-reloaded",
    "riskfolio-lib>=7.0",
    "skfolio",
    "ffn>=1.0",
    "torch>=2.2.0",
    "arch>=6.0",
    "copulas",
]
```
**Verify:** `uv pip install -e ".[quantscience]"` dry-run / `pip index versions pytimetk` (no full install needed if heavy).

### Task 1.2: MACD factor (M2) — TDD
**Files:**
- Create: `quant_nanggroe/engine/factors/macd_factor.py`
- Test: `tests/test_macd_factor.py`

**Step 1 — failing test:** compute 12-26-9 MACD histogram on synthetic OHLCV (100 bars, seeded), assert: column exists, histogram = macd_line - signal_line, finite values.
**Step 2 — run:** `.venv/Scripts/python -m pytest tests/test_macd_factor.py -v` → FAIL
**Step 3 — implement:** `macd_factor.py` — EMA12/EMA26 → macd_line, EMA9 of line → signal, histogram; rolling 30d corr vs forward 5d returns (mean ≈ -0.237 tolerance on real data; assert sign relationship only).
**Step 4 — run** → PASS. **Commit:** `feat(factors): add MACD histogram factor (QS013)`

### Task 1.3: ffn analytics adapter (M3)
**Files:**
- Create: `quant_nanggroe/engine/analytics/ffn_adapter.py`
- Test: `tests/test_ffn_adapter.py`

**Steps:** adapter wraps `ffn.calc_stats()` → dict with sharpe, sortino, calmar, max_drawdown, total_return, CAGR; monthly returns heatmap DataFrame. Test on synthetic returns series. TDD same cycle as 1.2.
**Commit:** `feat(analytics): add ffn tear-sheet adapter (QS020)`

---

## 3. PHASE 2 — STRATEGIC MOVES (2–4 days)

### Task 2.1: Pytimetk feature engine (M1)
**Files:**
- Create: `quant_nanggroe/engine/factors/feature_engine.py`
- Test: `tests/test_feature_engine.py`

**Spec (from master §FASE 2, Hari 10):**
- `augment_macd()` with polars backend
- `augment_bbands()` multiple periods [20, 40, 60]
- chain ops → 40+ features; integrate into StrategyEvolver for auto-feature-discovery
- graceful fallback to pandas if polars missing

### Task 2.2: Polars provider pilot (M4)
**Files:**
- Create: `quant_nanggroe/engine/data/providers/yahoo_polars.py`
- Test: `tests/test_yahoo_polars.py`

**Spec:** wide→long pivot, rolling 10/50-day MA for 25 symbols <10ms benchmark, rolling Sharpe by group, pandas fallback. Register in `provider_registry.py` behind flag `QNA_POLARS=1`.

### Task 2.3: Wire factors into FactorRegistry
**Files:** `quant_nanggroe/engine/factors/__init__.py` + alphalens_adapter registration
**Verify:** `alphalens_adapter` can ingest macd_factor + feature_engine outputs (IC + quantile + turnover). Add smoke test.

---

## 4. PHASE 3 — FOUNDATION HARDENING (depends on Phase 0 findings)

- [ ] 4.1 — Fix evolution loop if truly broken (A1 re-located)
- [ ] 4.2 — Weight sum normalization check (B2)
- [ ] 4.3 — Coverage blitz: risk > scoring > evolution > pipeline (C5)
- [ ] 4.4 — Dashboard rebuild + color config if stale (A5)

---

## 5. RISKS / TRADEOFFS

| Risk | Mitigation |
|-|-|
| Heavy deps (torch/alphalens/riskfolio) bloat install | Keep in `[optional-dependencies]`, lazy-import inside modules |
| Polars migration breaks pandas path | Graceful degradation + env flag; never replace pandas wholesale |
| Stale master paths (`main.py`) | Phase 0 re-baseline before any edit |
| Live trading system — changes touch prod paths | All new modules are additive; no edits to `qna.py`/`autonomous_cycle.py` unless Phase 0 proves a bug |
| pytest timeout on huge repo | Bounded test runs (`-x`, per-module targets) |

## 6. OPEN QUESTIONS
1. Approve `[optional-dependencies]` vs direct deps in main `dependencies`?
2. Run Phase 0 verification now, or trust the verified-DONE list and go straight to Phase 1?
3. Priority: MACD factor + ffn adapter first (fast, isolated), or feature_engine (bigger but 20x)?
