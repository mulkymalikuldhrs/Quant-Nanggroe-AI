# Quant Nanggroe AI — Institutional Master TODO & Roadmap

Dokumen ini adalah **peta jalan resmi (Master TODO)** pengembangan platform **Quant-Nanggroe-AI** menuju sistem **Autonomous Quantitative Hedge Fund Institusional**.

---

## 🎯 Status Rilis Saat Ini: `v6.0.0 — Production Readiness Audit + UnifiedPipeline + Monolith Split`

```
[ Entry Point ]         ██████████ 100% (Single: qna.py, unified mode default)
[ UnifiedPipeline ]     ██████████ 100% (pipeline/ module — auto mode-routing) 🆕
[ Strategy Pipeline ]   ██████████ 100% (79+ registered via @StrategyRegistry, canonical path)
[ Kill Switch C5 ]      ██████████ 100% (Cross-process shared state, fail-closed)
[ Risk Engine ]         ██████████ 100% (9-Checkpoint Gate, Kill Switch, Weekly Veto, unified constants)
[ hedge_fund ]          ██████████ 100% (Monolith split → real submodules) 🆕
[ Execution Layer ]     ██████████ 100% (TWAP/VWAP, Smart Router, Paper Broker)
[ AI Self-Evolution ]   ██████████ 100% (Self-Aware + Self-Evolve + Self-Fine-Tune)
[ API & Frontend UI ]   ████████░░  80% (FastAPI 181 endpoints, Dashboard needs build)
[ Security ]            ██████████  97% (+ Telegram config validation, secrets rotation pending)
[ Exchange Clients ]    ██████████ 100% (10 REST clients lazy-wired) 🆕
[ Test Suite ]          ██████████  99% (107/108 pass — 1 ccxt skip remains) 🆕
[ Documentation ]       ██████████ 100% (50+ docs filled + graphify)
```

---

## ✅ Completed

- [x] **v6.0.0 Production Readiness Audit** — Full audit disproved "0% live" suspicion; codebase confirmed production-viable
- [x] **UnifiedPipeline Module** — `quant_nanggroe/pipeline/` with auto mode-routing (hedge/crypto/agentic)
- [x] **hedge_fund Monolith Split** — ~6600 lines → utils/, signals/ (4 active + 237 experimental), risk/, execution/, portfolio/ + backward-compat shim
- [x] **Risk Unification** — KillSwitch thresholds now reference `constants.py` single source of truth (0.8% daily, 2.5% weekly); threshold mismatch fixed
- [x] **Exchange REST Lazy Wiring** — 10 orphaned clients wired into ExchangeFactory; ccxt import failure isolated via lazy proxy
- [x] **Telegram Config Validation** — `validate_telegram_config()` + `ensure_telegram()` fail-closed
- [x] **qna.py v6.0.0** — unified mode is default; cli/web deprecated
- [x] **Test Consolidation** — 107/108 tests pass; dual test discovery in pyproject.toml
- [x] **Single Entry Point** — `python qna.py [unified|api|daemon|hedge|status|stop]`
- [x] **All Legacy Entry Points Archived** — main.py, cli.py, daemon_manager.py → archive/
- [x] **Kill Switch C5 Convergence** — Cross-process shared state file for all KillSwitch instances
- [x] **hedge_fund Subpackage** — Multi-provider aggregator with voting engine
- [x] **StrategyConsolidationGate** — Canonical vs. legacy strategy paths consolidated
- [x] **109 Duplicate Strategies Removed** — archive/ cleaned
- [x] **Auto-Open Browser** — `api`/`web` modes auto-open (`--no-browser` / `QNA_AUTO_OPEN=0`)
- [x] **Full Forensic Audit** — Risk engine, C5 kill switch, strategy pipeline audited
- [x] **Self-Aware Module** — `engine/self_aware.py`
- [x] **Self-Evolve** — `StrategyEvolver` with walk-forward validation
- [x] **Self-Fine-Tune** — `SelfFineTuner` with grid search optimization
- [x] **Auto-Registry v3** — Scans ENTIRE repo (1017+ files)
- [x] **Weekly Loss Veto** — Fail-closed, verified blocking
- [x] **Credentials Security** — All hardcoded secrets removed, env vars only
- [x] **Duplicate Cleanup** — 6 duplicate dirs deleted (~400K+ freed)
- [x] **Dashboard API** — Risk parity, order slicing, config endpoints wired
- [x] **Engine `__all__`** — Ghost references removed

---

## 🚀 In Progress (User Action Needed)

- [ ] **MT5 Terminal Running** — User opens MT5 terminal → bridge auto-connects
- [ ] **Dashboard Build** — `cd dashboard && npm run build` to build Next.js static output

---

## 📋 Backlog

- [ ] **Real-time CFTC COT Integration** — Direct feed from CFTC
- [ ] **Automated MT5 Reconnection** — Auto-reconnect daemon for terminal drops
- [ ] **L2/L3 Tick Stream Handler** — Sub-second WebSocket streaming
- [ ] **Online RL Fine-tuning** — PPO/SAC integration into execution loop
- [ ] **NLP Sentiment Processing** — SEC filings + FRED via LLM
- [ ] **Walkforward All Strategies** — Batch walk-forward validation
- [ ] **Grid Search Fine-Tune** — SelfFineTuner run on all strategies
- [ ] **C5 Kill Switch Dashboard** — Visual status of cross-process kill switch state
- [ ] **hedge_fund Backtest Mode** — Backtest multi-provider voting strategy
- [ ] **Git History Purge** — Force-push to remove stale credentials from git history

---

## 📌 Operating Rules

1. **Single Entry Point**: `python qna.py` (unified mode default) or `python qna.py api`
2. **Fail-Closed Safety**: Never disable Risk Guard, Kill Switch, or C5 convergence in production
3. **Evidence-Based**: All strategies must be validated with backtest before live
4. **Self-Evolution**: Mutations validated via walk-forward, never blindly accepted
5. **No Hardcoded Secrets**: All credentials via env vars only
6. **No Root-Level Entry Points**: `qna.py` is the ONLY launcher

---

## 📊 Audit Summary (2026-07-25)

| Component | Grade | Status |
|-----------|-------|--------|
| Risk Engine | A+ | ✅ Unified constants, KillSwitch references constants.py, threshold mismatch fixed |
| UnifiedPipeline | A | ✅ `quant_nanggroe/pipeline/` — auto mode-routing |
| Kill Switch C5 | A | ✅ Cross-process shared state, fail-closed, Path-A + Path-B |
| Strategies (Canonical) | A | ✅ 79+ registered via @StrategyRegistry, full signal gen |
| Architecture | A | ✅ Clean modular, single entry point, unified pipeline |
| hedge_fund | A+ | ✅ Monolith split into real submodules (utils/signals/risk/execution/portfolio) |
| Exchange Clients | A | ✅ 10 REST clients lazy-wired, ccxt import failure isolated |
| Documentation | A- | ✅ 50+ docs filled + graphify |
| Security | B+ | ✅ backup_env archived, Telegram config validation added, 15 findings logged (2 CRITICAL git purge pending) |
| Walk-forward Engine | A | ✅ CPCV/rolling/anchored, synthetic smoke test |
| Test Suite | B+ | ✅ 107/108 pass — 1 ccxt skip remains |
| MT5 Bridge | C | ⚠️ Terminal must run manually, no cron-to-live wiring |
| Dashboard | B | ✅ 18 pages wired, Next.js API proxy, build pending |
| PYTHONPATH Isolation | A | ✅ launch.bat + README + AGENTS docs |

---

*Built with fury from Aceh, Indonesia 🇮🇩*
