# DEVBOT STRUCTURAL AUDIT — QNA (`quant_nanggroe/`)

**Scope:** `D:\repositories\Quant-Nanggroe-AI-worktree`. Nucleus = `quant_nanggroe/` (658 `.py`, 155,329 LOC) + `dashboard/` (Next.js, 53 tsx, 9,472 LOC). Total source ≈ 165k LOC / ~711 files. Frontends: **single** (`dashboard/`, built via `qna.py`). The "3 frontend" hypothesis did not hold — `src` and `web_interface` do not exist.

**Method:** AST import-graph walk (`_audit_structure.py`) + statement-level grep for every duplicate layer. "Importers" = files importing the module by absolute dotted path; re-export shims (`execution.py`, `regime_detector.py`) are flagged SEPARATE, not dead.

---

## 1. DUPLICATE LAYER MATRIX

| Layer A | Layer B | Importers A | Importers B | Verdict |
|---|---|---|---|---|
| `backtest/` (4 f, 1,246 LOC) | `engine/backtest/` (35 f, 12,415 LOC) | **2** (`auto_aware.py`, `engine/backtest/auto_tune.py`) | **9** | `backtest/` is legacy shell. `engine/backtest/` is canonical. |
| `db/` (2 f, 102 LOC) | `database/` (8 f, 1,448 LOC) | **2** (`config/settings.py`, `engine/api/health.py`) | **1** (only `db/models.py` imports it) | `db/` is the OLD schema; `database/` is canonical (has alembic + init_db). |
| `bridge/` (2 f, 150 LOC) | — | **0** | — | **ORPHAN.** Zero importers anywhere. |
| `connectors/` (9 f, 827 LOC) | `exchange/` (32 f, 15,959 LOC) | 4 | 32 | Different concerns: `connectors/`=`LLM/Google/GitHub/audio/web3` glue; `exchange/`=brokerage. NOT a dup. |
| `providers/` (8 f, 979 LOC) | `data/providers/` (16 f, 4,665 LOC) | 3 | 8 | **DUP:** `providers/` re-implements 5 files `data/providers/` already has (`coingecko_provider`, `crypto_provider`, `finnhub_provider`, `macro_provider`, + `data_manager`). Self-labeled "backward-compat cached version". |
| `engine/strategies/` (11 f, 2,047 LOC) | `engine/strategy/strategies/` (109 f, 9,756 LOC) | 5 | 115 | **DUP:** old flat `strategies/` vs new `strategy/strategies/`. 2 name collisions (`__init__`, `smc_strategy`). |
| top-level `strategies/` (5 f, 342 LOC) | — | **1** (`live_engine.py`) | — | Third strategy location; tiny, only `live_engine.py` uses it. |

---

## 2. ORPHAN / DEAD TABLE (module → orphan? → file:line)

| Module | Orphan? | Evidence (file:line) |
|---|---|---|
| `quant_nanggroe/bridge/**` (data_bridge.py, __init__.py) | **YES (100%)** | 0 importers; grep `quant_nanggroe.bridge` outside pkg = empty |
| `quant_nanggroe/db/models.py` | **landmine** | `database/models.py` imports it (`:?`) → deleting `db/` breaks `database/`. Re-point, don't delete. |
| `quant_nanggroe/providers/{coingecko,crypto,finnhub,macro}_provider.py` + `data_manager.py` | **YES** | re-exports of `data/providers/*`; 3 importers (`exchange`, `connectors`, `data/manager`) |
| `quant_nanggroe/engine/strategies/*` (9 unique files) | **mostly** | 5 importers still on old path; `registry.py`/`base.py` re-defined vs `engine/strategy/` |
| `quant_nanggroe/engine/backtest/nautilus_adapter.py` (910 LOC) | **dead branch** | only `engine/backtest/__init__.py` imports it; `_run_nautilus()` raises `NotImplementedError` at `:854` → falls back, never executes |
| `quant_nanggroe/execution.py` | NO (shim) | re-exports `engine.execution` — keep |
| `quant_nanggroe/engine/regime_detector.py` | NO (shim) | re-exports `engine.regime` — keep |

---

## 3. DEAD-CODE MARKERS — `NotImplementedError` / TODO / placeholder (file:line)

**Hard `raise NotImplementedError` (genuine unimplemented):**
- `engine/backtest/nautilus_adapter.py:854` — `_run_nautilus()` (910-LOC adapter never wired)

**Stub-only files (docstring/import-only, 0 real defs) — 98 total, ~10 are non-`__init__` dead code:**
- `engine/colony/hands.py:1` "Stub: colony.hands"
- `engine/portfolio/manager.py:2` "Portfolio manager stub for wiring_compat"
- `engine/smc/engine.py:2` "SMC engine stub"
- `engine/smc/killzone.py:2` "SMC killzone stub"
- `engine/data/caching.py:2`, `cot_provider.py:2`, `economic_calendar.py:2`, `rate_limiter.py:2` — all "stub"
- `connectors/audio_stream.py`, `github_integration.py`, `google_integration.py`, `web3_plugin.py` — "Stub: optional dependency"

**Inline TODO/placeholder (sample, 82 total):** `api/routes/wiring_compat.py` (stub data at `:74,:75,:134`), `api/routes/channels.py:17`, `engine/model_registry.py:452/627/704/710` (XGBoost/Transformer stubs), `model_registry.py` XGBoost/Transformer/PyTorch stubs → real ML layer not implemented.

---

## 4. SAFE-TO-DELETE (won't break imports)

1. **`quant_nanggroe/bridge/`** — 0 importers. Delete entire dir.
2. **`quant_nanggroe/providers/coingecko_provider.py`, `crypto_provider.py`, `finnhub_provider.py`, `macro_provider.py`, `data_manager.py`** — re-exports. Re-point 3 importers (`exchange/*`, `connectors/*`, `data/manager.py`) to `data/providers/`, then delete. Keep `providers/__init__.py` + `proxy.py` + `warp.py` if used.
3. **`engine/backtest/nautilus_adapter.py`** — dead branch, raises NotImplementedError. **But** it is in `engine/backtest/__init__.py` `__all__`. Remove from `__init__` (`:14,:40`) + drop init line, then delete.
4. **`engine/strategies/`** (the 9 unique files) — consolidate into `engine/strategy/strategies/`, re-point the 5 importers (`live/adaptive_integration.py`, `shadow/codegen.py`, `strategy/loader.py`, `strategy/strategy_selector.py`, `engine_production_bridge.py`), then delete.
5. **Top-level `quant_nanggroe/strategies/`** — only `live_engine.py` uses it (1 importer). Fold into `engine/strategy/strategies/`.

**DO NOT DELETE without re-point:**
- `quant_nanggroe/db/` → `database/models.py:?` imports `db/models.py`. Re-point `database/models.py` to `database` classes first, then delete `db/`.
- `quant_nanggroe/backtest/` → 2 importers. Keep only if you want legacy compat; otherwise re-point `auto_aware.py` + `engine/backtest/auto_tune.py` to `engine.backtest`.
- `execution.py`, `regime_detector.py` → backward-compat shims, KEEP.

---

## 5. DECAPITATION SUMMARY (headline numbers)

- **Confirmed orphans:** `bridge/` (150 LOC) + `providers/` dupes (≈600 LOC) + `nautilus_adapter.py` (910 LOC) + `engine/strategies/` (2,047 LOC) + top-level `strategies/` (342 LOC) = **~4,050 LOC / ~42 files safely killable** with import re-points.
- **"3 frontends" = false.** One frontend (`dashboard/`). `src`/`web_interface` absent.
- **82 TODO/stub markers; 1 hard NotImplementedError.** Real ML models (`model_registry.py`) are stubs.
- **0 fully-orphan modules** at the AST level (everything is imported by *something*), but 5 modules are imported only by a single legacy caller or a package `__init__` → effectively dead.

**Ponytail call:** `bridge/` → delete now (0 risk). `providers/` dupes + `nautilus_adapter.py` → re-point (1-liner each) then delete. `engine/strategies/` + top-level `strategies/` → merge into `engine/strategy/strategies/`. `db/` → re-point `database/models.py` then drop. Skipped: actual code-merge diffs (say the word, I'll generate the re-point patch + deletes as one branch).
