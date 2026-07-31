# Changelog — Quant Nanggroe AI

## 2026-07-30 — Session 9-10: Massive Parallel Audit + Evolution Loop + Renaissance Blueprint

### Added
- Evolution loop: 8 files in `engine/evolution/` (journal, handler, scheduler, scanner, disabler, updater, config)
- Evolution API endpoint: `api/routes/evolution.py` (5 endpoints)
- Dashboard evolution page: 3 tabs (strategies, trades, config)
- Providers: `providers/hidden_regime_provider.py` (3-tier CFTC/hidden-regime)
- Providers: `providers/news_provider.py` (3-tier AlphaVantage/RSS)
- Strategy wiring: `hedge_fund/signals/engine_strategies.py` (77 engine + 992 mue-x + 10 core = 1079 providers)
- Deployment: `deploy/docker/scripts/entrypoint.sh`
- Documentation: `docs/research_quant_scoring.md`
- Documentation: `docs/STATUS.md` (doc contradictions map)
- Graphify: `graphify-out/code_map.md`
- Color palette: `--color-accent: #D9A441`, `--color-primary: #0F172A`

### Fixed
- FRED API key hardcoded → env var (3 files)
- Bare `except:` → `except Exception` with logging (12 locations)
- `engine/scoring/` duplikat → deleted (11 files)
- Confidence formula → `tanh(|score|/40)`
- Live engine broken import path
- Dual pipeline silent fallback → CRITICAL log
- `asyncio.iscoroutinefunction` → `inspect.iscoroutinefunction`
- CI Python version GitHub 3.11 → 3.12
- Nginx upstream `agentic-ai:5000` → `api:8000`
- `credentials.json` removed from git tracking
- Stale artifacts cleaned (6 files)
- qna.py pipeline bug: `asyncio.run()` → direct `pipeline.run()`, `.get()` → `getattr()`
- Evolution scheduler: time-based trigger + threshold gate
- CSS surface colors: `#050510` → `#0F172A`
- AGENTS.md v15.4.0: all Session 9 changes
- README.md: modernized with pipeline flowchart
- QNA_AGENT_STATE.md: updated scorecard

### Broken (known)
- Evolution loop 4 wiring bugs in `main.py:847-854` — scan_strategy, evaluate, disable, update_weights type mismatches
- `np` undefined in `main.py:715` — StressVaR can't run
- WeightEvolver vs WeightUpdater: duplicate weight management
- Silent error swallowing: 4x `except: pass` + 20x `log.debug()` in main.py
- CryptoScorer + NewsScorer: untested, unweighted, total weight 1.03
- `get_valid_pairs()` missing in `main.py:298`
- credentials.md.txt: 100+ secrets QUARANTINED — moved to `C:\Users\Hi\.qna-secrets\credentials.md.txt` (out of repo). Repo placeholder only.

## 2026-07-29 — Session 7-8: Core Pipeline + MTF + Evolution Foundation

### Added
- MTF engine: 4 frames + ConflictResolver
- Self-evolve loop: WeightEvolver + ScoreJournal
- SentimentScorer limit=180
- LLM Advisory layer (rule-based + 9router)
- Pair-class config (7 asset classes, 18 symbols)
- Dashboard branch extracted (v2-dashboard)
- FusionEngine wired to run_once() (Session 7)
- PositioningScorer from CFTC COT API
- TTLCache for Economic + Sentiment scorers
- mue-x dynamic discovery (760→51 lines)

### Fixed
- Pipeline refactored: 463→310 lines, 7 clean stages
- Test environment: numpy 2.5.1, httpx, scipy
- np.clip → _clamp() across all scoring files
- Weekly loss veto on Path-B
- Cherry-pick debris restored (8 directories)

## 2026-07-26 — Session 4-6: Initial Audit + Foundation

- Complete architecture graph
- Scoring engine code created (7 scorers)
- E:\ drive discovered and mapped
- github2 divergence documented (4141 files)
- 3 pre-existing test failures documented
- Canister docs updated (6/6 root + 7/7 canonical)


---

## 🎯 100/100/100 Roadmap — Dari OpenCode Audit (2026-07-30)

### Target Matrix: 3 Dimensi

| Score | Arti | Target | Estimasi Waktu |
|-------|------|--------|---------------|
| **A 100** | Bisa dinikmati — evolution jalan, error kedengeran, dashboard meaningful | ✅ Pipeline sehat, evolution beneran belajar, error gak silent | **1 hari** |
| **B 100** | Quant-grade — single source of truth, statistical rigor, no data corruption | ✅ Weight governance, signal/registry dedup, test coverage >80% | **3-4 hari** |
| **C 100** | Institutional — zero silent fail, audit trail, multi-account, SLA | ✅ Paper=production, alerting, replay, 80% coverage, multi-broker | **2-4 minggu** |
| **Total** | **300/300** | **Fully autonomous quant nation** | **~6 minggu** |

### Detail Gap per Score (Dari Audit 8 Task Agent)

#### A 100 — Enjoyable & Reliable

| # | Gap | Fix | Estimasi |
|---|-----|-----|----------|
| A1 | **Evolution loop dead** — 4 wiring bugs di `main.py:847-854` | scan_strategy→scan_all, evaluate() pake list | **2 jam** |
| A2 | **Silent error 20+ titik** — semua `log.debug()` | Upgrade ke `log.error` + propagate | **1 jam** |
| A3 | **`np` undefined** — StressVaR selalu throw NameError | `import numpy as np` di main.py | **5 menit** |
| A4 | **`get_valid_pairs` missing** — always throws AttributeError | Fix import atau remove dead call | **15 menit** |
| A5 | **Dashboard build stale + color config gak ada** | Rebuild + color picker | **2 jam** |
| A6 | **PnL attribution gak ada** — dashboard gak tampilin evolution journal | Wire dashboard API ke journal SQLite | **1 jam** |
| | **Total A fix** | | **~6 jam** |

#### B 100 — Quant-Grade

| # | Gap | Fix | Estimasi |
|---|-----|-----|----------|
| B1 | **WeightEvolver vs WeightUpdater fight** — beda data source, beda formula, gak sync | Eliminate satu. Rekomendasi: WeightEvolver (circuit breaker) | **3 jam** |
| B2 | **Weight total 1.03 + 2 scorers missing dari evolver** | Tambah CryptoScorer & NewsScorer ke DEFAULT, normalize | **30 menit** |
| B3 | **8 Signal classes, 3 field name conflicts** — signal_type vs direction vs side vs bias | Pilih canonical (`types/signals.py`), delete sisanya | **2 jam** |
| B4 | **3 registries gak sync** — StrategyRegistry vs AutoRegistry vs WalkForwardRegistry | StrategyRegistry = canonical, AutoRegistry delete for strategies | **2 jam** |
| B5 | **4/10 scorers untested** — Crypto, News, Positioning, Confluence | Tambah test class + mock external APIs | **3 jam** |
| B6 | **6/8 evolution modules untested** — config, handler, scanner, disabler, updater, evolver | Tambah test class | **4 jam** |
| | **Total B fix** | | **~14.5 jam** |

#### C 100 — Institutional/Hedge Fund

| # | Gap | Fix | Estimasi |
|---|-----|-----|----------|
| C1 | **Paper mode = dead risk** — PnL hardcoded 0.0, balance 1000 | Simulasi PnL real dari MT5/fallback | **2 jam** |
| C2 | **RiskLimits class unwired** — `limits.py:48` can_trade() zero callers | Wire ke `_pipeline_risk_check` | **1 jam** |
| C3 | **Audit trail write-only** — evolution journal nulis tapi gak dibaca | Dashboard timeline + PnL attribution | **4 jam** |
| C4 | **No alert system** — error silent total | Telegram alert on subsystem fail | **3 jam** |
| C5 | **Test coverage rendah** — estimasi 20-30% | Target 80%. Prioritaskan risk + scoring + evolution + pipeline | **3-4 hari** |
| C6 | **Multi-account MT5** — single session, gak bisa multi-broker | Multi-process architecture | **1 minggu** |
| C7 | **~15K lines dead code** — 10 REST clients, 453 alphas, RL stub, live_engine.py | Hapus/archive file terverifikasi | **3 jam** |
| C8 | **Data quality framework** — gak ada SLA monitoring, staleness detection | Data health check + status endpoint + dashboard | **2 hari** |
| | **Total C fix** | | **~6-10 hari** |

### Timeline Eksekusi

```
Hari 1:     A1 + A2 + A3 + A4 + B1 + B2          → Score A ~90, B ~60
Hari 2-3:   B3 + B4 + B5 + B6 + A5 + A6          → Score A 100, B ~90
Minggu 2:   C1 + C2 + C3 + C7 + C8               → Score C ~70
Minggu 3-4: C4 + C5 + C6                         → Score C ~90
Minggu 5-6: Last mile hardening                  → Score C 100
```

### Keputusan Arsitektur yang Perlu Diambil Mulky

| Keputusan | Opsi A | Opsi B | Rekomendasi |
|-----------|--------|--------|-------------|
| **Weight tuner** | WeightEvolver (circuit breaker, normalized) | WeightUpdater (Bayesian, SQLite) | **WeightEvolver** — safety circuit breaker |
| **Registry main** | StrategyRegistry (decorator-driven) | AutoRegistry (scan semua subclass) | **StrategyRegistry** — explicit > implicit |
| **Signal canonical** | `types/signals.py` (20 fields, BaseModel) | `pipeline/signal.py` (8 fields, dataclass) | **`types/signals.py`** — Pydantic validation |
| **Alerts** | Telegram | Email | **Telegram** — sudah ada bot |
| **Multi-account MT5** | Multi-process (1 per broker) | Docker containers | **Multi-process** — 16GB RAM cukup |

### Catatan Realistis

Estimasi 6 minggu tapi bisa molor karena:
1. **Testing time** — tiap perubahan perlu ruff + mypy + pytest. Kena typo = backtrack
2. **Refactor domino effect** — signal dedup → 8 file berubah → 5 file impor patah → fix lagi
3. **Mental energy** — baca 83 strategy files, 24 risk files, 20 provider files buat mastiin gak ada yang kehapus

**Realistis: 6-8 minggu** untuk 300/300.

---

## 🧬 E:\ Integration — 12-Agent Council Plan (2026-07-31)

**136 jam / 4-6 minggu** — Port TradeBobbyTerminal + OrderFlowMap ke QNA pipeline.

| Phase | Hours | Deliverable |
|-------|-------|-------------|
| Phase 0 — Pre-work | 8h | Delete dead code, dedup signal/registry/COT |
| Phase 1 — Week 1 | 24h | 5 Python providers + pipeline wiring |
| Phase 2 — Week 2 | 32h | 9 dashboard panels + risk gates + evolution |
| Phase 3 — Week 3 | 40h | 80% tests + alerts + data quality |
| Phase 4 — Future | 32h | Node sidecars + multi-account + backtest |

Lihat `docs/Rencana.md` untuk detail lengkap.
