# Quant Nanggroe AI — Institutional Master TODO & Roadmap

Dokumen ini adalah **peta jalan resmi (Master TODO)** pengembangan platform **Quant-Nanggroe-AI** menuju sistem **Autonomous Quantitative Hedge Fund Institusional**.

---

## 🎯 Status Rilis Saat Ini: `v6.1.0 — Quantitative Alpha Engines + Production Audit v2 + Docs Sync`

```
[ Entry Point ]         ██████████ 100% (Single: qna.py, unified mode default)
[ UnifiedPipeline ]     ██████████ 100% (pipeline/ module — auto mode-routing) 
[ Causal Engine Suite ] ██████████ 100% (5 modules: bias, MSI, COT, SMT, thesis drift) 🆕 v6.1.0
[ DCC-GARCH ]           ██████████ 100% (Dynamic correlation + auto-fit + 47 tests) 🆕 v6.1.0
[ Causal Bias Filter ]  ██████████ 100% (All HF providers: boost/reduce/block) 🆕 v6.1.0
[ Strategy Pipeline ]   ██████████ 100% (79+ registered via @StrategyRegistry, canonical path)
[ Kill Switch C5 ]      ██████████ 100% (Cross-process shared state, fail-closed)
[ Risk Engine ]         ██████████ 100% (9-Checkpoint Gate + DCC-GARCH + Thesis Drift)
[ hedge_fund ]          ██████████ 100% (Monolith split → real submodules + causal bias)
[ Execution Layer ]     ██████████ 100% (TWAP/VWAP, Smart Router, MT5 live default, paper opt-in)
[ AI Self-Evolution ]   ██████████ 100% (Self-Aware + Self-Evolve + Self-Fine-Tune)
[ API & Frontend UI ]   ████████░░  80% (FastAPI 181 endpoints, Dashboard needs build)
[ Security ]            ██████████  97% (+ Telegram config validation)
[ Exchange Clients ]    ██████████ 100% (10 REST clients lazy-wired)
[ Test Suite ]          ██████████  99% (+ DCC unit tests — 47 comprehensive)
[ Documentation ]       ██████████ 100% (All docs updated to v6.1.0)
```

---

## ✅ Completed

- [x] **v6.0.0 Production Readiness Audit** — Full audit disproved "0% live" suspicion; codebase confirmed production-viable
- [x] **v6.1.0 Quantitative Alpha Engines** — DCC-GARCH, Causal Macro, COT, MSI, SMT, Thesis Drift, Causal Bias Filter
- [x] **UnifiedPipeline Module** — `quant_nanggroe/pipeline/` with auto mode-routing (hedge/crypto/agentic)
- [x] **hedge_fund Monolith Split** — ~6600 lines → submodules + backward-compat shim
- [x] **Risk Unification** — KillSwitch thresholds now reference `constants.py` single source of truth
- [x] **Exchange REST Lazy Wiring** — 10 orphaned clients wired into ExchangeFactory
- [x] **Telegram Config Validation** — `validate_telegram_config()` + `ensure_telegram()` fail-closed
- [x] **DCC-GARCH Module** — `engine/risk/dcc_garch.py` with 47 unit tests
- [x] **Causal Bias → Signal Filter** — All HF providers apply 3-level bias (boost/reduce/block)
- [x] **Macro Surprise Index** — FRED API, |MSI| > 1.5σ triggers bias revision
- [x] **COT Tracker** — CFTC via `cot_reports`, percentile-based extreme positioning
- [x] **SMT Divergence** — Engle-Granger cointegration breakdown detection
- [x] **Thesis Drift Guard** — 3-stage circuit breaker (monitor → warn → hard exit)
- [x] **DCC Auto-fit in live_engine.py** — `_update_dcc_garch()` every N cycles
- [x] **Pre-filter DCC env vars** — qna.py passes returns to `evaluate_full_pipeline()`
- [x] **Production Defaults** — MT5 live default, paper opt-in, `QNA_TRADING_ENABLED=true`
- [x] **qna.py v6.0.0** — unified mode is default; cli/web deprecated
- [x] **Test Consolidation** — Core tests pass + DCC-GARCH 47 tests
- [x] **Single Entry Point** — `python qna.py [unified|api|daemon|hedge|status|stop]`
- [x] **All Legacy Entry Points Archived** — main.py, cli.py, daemon_manager.py → archive/
- [x] **Kill Switch C5 Convergence** — Cross-process shared state file
- [x] **StrategyConsolidationGate** — Canonical vs. legacy strategy paths consolidated
- [x] **Self-Aware Module** — `engine/self_aware.py`
- [x] **Self-Evolve** — `StrategyEvolver` with walk-forward validation
- [x] **Auto-Registry v3** — Scans ENTIRE repo (1017+ files)
- [x] **Weekly Loss Veto** — Fail-closed, verified blocking
- [x] **Credentials Security** — All hardcoded secrets removed, env vars only
- [x] **Dashboard API** — Risk parity, order slicing, config endpoints wired

---

## 🚀 In Progress (User Action Needed)

- [ ] **MT5 Terminal Running** — User opens MT5 terminal → bridge auto-connects
- [ ] **Dashboard Build** — `cd dashboard && npm run build` to build Next.js static output
- [ ] **Live Trade Execution** — Cron-to-live-trade wiring with real MT5

---

## 📋 Backlog

- [ ] **Automated MT5 Reconnection** — Auto-reconnect daemon for terminal drops
- [ ] **L2/L3 Tick Stream Handler** — Sub-second WebSocket streaming
- [ ] **Online RL Fine-tuning** — PPO/SAC integration into execution loop
- [ ] **NLP Sentiment Processing** — SEC filings + FRED via LLM
- [ ] **Walkforward All Strategies** — Batch walk-forward validation
- [ ] **Grid Search Fine-Tune** — SelfFineTuner run on all strategies
- [ ] **C5 Kill Switch Dashboard** — Visual status of cross-process kill switch state
- [ ] **hedge_fund Backtest Mode** — Backtest multi-provider voting strategy
- [ ] **Git History Purge** — Force-push to remove stale credentials from git history
- [ ] **Live COT + MSI auto-fetch** — Cron-based FRED/COT data refresh
- [ ] **DCC-GARCH regime shift alerting** — Telegram notification on correlation regime change

---

## 📌 Operating Rules

1. **Single Entry Point**: `python qna.py` (unified mode default) or `python qna.py api`
2. **Fail-Closed Safety**: Never disable Risk Guard, Kill Switch, or C5 convergence in production
3. **Evidence-Based**: All strategies must be validated with backtest before live
4. **Self-Evolution**: Mutations validated via walk-forward, never blindly accepted
5. **No Hardcoded Secrets**: All credentials via env vars only
6. **No Root-Level Entry Points**: `qna.py` is the ONLY launcher

---

## 📊 Audit Summary (2026-07-26)

| Component | Grade | Status |
|-----------|-------|--------|
| Causal Engine Suite | A+ | ✅ 5 modules (bias, MSI, COT, SMT, thesis drift) — all production-grade |
| DCC-GARCH | A+ | ✅ Dynamic correlation, auto-fit, 47 unit tests |
| Causal Bias → Signal Filter | A+ | ✅ All 200+ providers apply boost/reduce/block |
| Risk Engine | A+ | ✅ Unified constants + DCC-GARCH + Thesis Drift Guard |
| Kill Switch C5 | A | ✅ Cross-process shared state, fail-closed |
| Strategies (Canonical) | A | ✅ 79+ registered via @StrategyRegistry |
| Architecture | A | ✅ Clean modular, single entry point, unified pipeline |
| hedge_fund | A+ | ✅ Submodules + causal bias on all providers |
| Exchange Clients | A | ✅ 10 REST clients lazy-wired |
| Documentation | A | ✅ All docs updated to v6.1.0 |
| Security | B+ | ✅ 15 findings logged (git purge pending) |
| Test Suite | B+ | ✅ Core tests + 47 DCC-GARCH tests |
| MT5 Bridge | C | ⚠️ Terminal must run manually |
| Dashboard | B | ✅ 18 pages wired, build pending |
| PYTHONPATH Isolation | A | ✅ launch.bat + README + AGENTS docs |

---

*Built with fury from Aceh, Indonesia 🇮🇩*
