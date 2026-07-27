# Quant Nanggroe AI — Institutional Master TODO & Roadmap

Dokumen ini adalah **peta jalan resmi (Master TODO)** pengembangan platform **Quant-Nanggroe-AI** menuju sistem **Autonomous Quantitative Hedge Fund Institusional**.

---

## 🎯 Status Rilis Saat Ini: `v6.5.0 — Full Autonomous Wiring: All Mocks Eliminated, All APIs Mounted`

```
[ Entry Point ]         ██████████ 100% (Single: qna.py, unified mode default)
[ UnifiedPipeline ]     ██████████ 100% (pipeline/ module — auto mode-routing) 
[ Causal Engine Suite ] ██████████ 100% (5 modules: bias, MSI, COT, SMT, thesis drift + CausalContext) 
[ DCC-GARCH ]           ██████████ 100% (Dynamic correlation + auto-fit + 47 tests)
[ Causal Bias Filter ]  ██████████ 100% (All HF providers: boost/reduce/block + CausalContext dataclass)
[ Strategy Pipeline ]   ██████████ 100% (79+ registered via @WalkForwardRegistry, canonical path)
[ Kill Switch C5 ]      ██████████ 100% (Cross-process state, fail-closed, audit trail) 🆕 v6.3.0
[ Risk Engine ]         ██████████ 100% (9-Checkpoint Gate + DCC-GARCH + Thesis Drift + Circuit Breaker) 🆕 v6.3.0
[ PnL Unit Convention ] ██████████ 100% (Fractions 0-1, all layers agree, documented) 🆕 v6.3.0
[ hedge_fund ]          ██████████ 100% (Monolith split → real submodules + causal bias)
[ Execution Layer ]     ██████████ 100% (Public API seal, MT5 circuit breaker, deterministic paper) 🆕 v6.3.0
[ Backtest System ]     ██████████ 100% (CPCV default, annualization unified, broken imports fixed) 🆕 v6.4.0
[ Strategy Logger ]     ██████████ 100% (Trade result attribution + log_trade_result) 🆕 v6.4.0
[ Auto-Tuner ]          ██████████ 100% (Backtester adapter created, broken import fixed) 🆕 v6.4.0
[ AI Self-Evolution ]   ██████████ 100% (Self-Aware + Self-Evolve with real backtest)
[ Strategy Evolver ]    ██████████ 100% (Real WalkForwardAnalyzer — no mock, data cache added) 🆕 v6.4.0
[ API & Frontend UI ]   █████████░  95% (All mocks eliminated, pipeline/config routes mounted) 🆕 v6.5.0
[ Security ]            ██████████ 100% (+ mt5_accounts.yaml env-var interpolation, no plaintext) 🆕 v6.3.0
[ Exchange Clients ]    ██████████ 100% (10 REST clients lazy-wired)
[ Test Suite ]          ██████████  99% (+ DCC unit tests — 47 comprehensive)
[ Documentation ]       ██████████ 100% (All docs updated to v6.5.0) 🆕 v6.5.0
```

---

## ✅ Completed

- [x] **v6.2.0 P0 Deep Clean** — 8 P0 fixes: Security, Backtest, Architecture, PnL, Naming, Evolver, Execution, Causal
- [x] **P0 Security** — `.secrets-local/` deleted, `ssl.CERT_NONE` → `QNAI_SSL_VERIFY` across 10 files
- [x] **P0 Backtest** — `engine.py:183` NameError fixed, `portfolio.py:196` return None → return pos
- [x] **P0 Architecture** — `__getattr__` removed from `engine/__init__.py`, stale `standalone.py` deleted
- [x] **P0 PnL** — Unit convention unified to fractions (0-1), `/100.0` removed from RiskManager
- [x] **P0 Naming** — `StrategyRegistry` → `WalkForwardRegistry` in `engine/strategy/registry.py`
- [x] **P0 Evolver** — `_real_backtest()` uses `WalkForwardAnalyzer.analyze_strategy()` — no more mock
- [x] **P0 Execution** — `ExecutionManager.set_broker_handle()` public method, `builder.py` uses correct API
- [x] **P0 Causal** — `CausalContext` dataclass replaces env-var wiring for causal engine
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
- [x] **Self-Evolve** — `StrategyEvolver` with real walk-forward validation (v6.2.0)
- [x] **Auto-Registry v3** — Scans ENTIRE repo (1017+ files)
- [x] **Weekly Loss Veto** — Fail-closed, verified blocking
- [x] **Credentials Security** — All hardcoded secrets removed, env vars only, `.secrets-local/` deleted
- [x] **Dashboard API** — Risk parity, order slicing, config endpoints wired
- [x] **Phase 1 Audit** — 12 categories: COT redirect, colony workers, portfolio API, market pressure, TradingAdapter, PipelineSignal, credential stubs, daemon COT, indicators
- [x] **Phase 2A: Pipeline Self-Loop** — StrategyRegistry → SignalEngine, WalkForward → Strategy Selection, Scheduler → daemon, Self-evolution loop in AutonomousPipeline
- [x] **Phase 2B: Dashboard Wiring** — Pipeline/Strategies/Colony pages wired to live APIs, mock data eliminated
- [x] **Phase 2C: Dead Code Cleanup** — `colony_stub.py` deleted, scheduler docstring fixed, numpy strategies deprecated
- [x] **Phase 2D: Environment** — pandas/statsmodels compatibility fixed, ruff lint verified
- [x] **v6.5.0 Autonomous Wiring Audit** — Skeptical senior quant engineer audit identified and fixed 6 critical gaps:
  - 3 wrong import paths in autonomous_self_loop.py (PnLEvaluator, SelfAware, DebateEngine)
  - SelfAware API mismatch (reflect_self → reflect with state_provider)
  - 4 TODO stubs wired to real data sources (trades, performance, evolved strategies, signals)
  - ExecutionManager.set_strategy_allocations() phantom call removed
  - Duplicate autonomous router removed from app.py
  - Dashboard/API self-awareness interface aligned

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

## 📊 Audit Summary (2026-07-27)

| Component | Grade | Status |
|-----------|-------|--------|
| P0 Deep Clean (v6.2.0) | A+ | ✅ 8 P0 fixes: Security, Backtest, Architecture, PnL, Naming, Evolver, Execution, Causal |
| Execution & Risk Hardening (v6.3.0) | A+ | ✅ Private API seal, MT5 circuit breaker, SYMBOL_MAP, kill switch audit trail, env-var YAML creds |
| Security (SSL + Secrets) | A | ✅ QNAI_SSL_VERIFY env guard, .secrets-local/ deleted, env-var creds, mt5_accounts.yaml interpolated |
| PnL Unit Convention | A+ | ✅ Fractions (0-1) unified — RiskManager + KillSwitch + downstream consumers agree, documented at boundary |
| Strategy Registry Naming | A+ | ✅ StrategyRegistry → WalkForwardRegistry — no more dual-registry confusion |
| Strategy Evolver | A+ | ✅ Real WalkForwardAnalyzer — no mock jitter |
| Execution Bridge | A+ | ✅ Public API sealed (get_risk_manager, get_mt5_connector, set_broker_handle, get_brokers) |
| Kill Switch C5 | A+ | ✅ Cross-process fail-closed + force_deactivate emergency override + append-only audit trail |
| Causal Engine Suite | A+ | ✅ 5 modules (bias, MSI, COT, SMT, thesis drift) + CausalContext |
| DCC-GARCH | A+ | ✅ Dynamic correlation, auto-fit, 47 unit tests |
| Causal Bias → Signal Filter | A+ | ✅ All 200+ providers apply boost/reduce/block |
| Risk Engine | A+ | ✅ Unified constants + DCC-GARCH + Thesis Drift Guard + Circuit Breaker |
| Architecture | A+ | ✅ __getattr__ removed, standalone deleted, clean modular, private API sealed |
| MT5 Bridge | B | ✅ Circuit breaker + SYMBOL_MAP for symbol translation (terminal still manual) 🆕 v6.3.0 |
| hedge_fund | A+ | ✅ Submodules + causal bias on all providers |
| Exchange Clients | A | ✅ 10 REST clients lazy-wired |
| Documentation | A | ✅ All docs updated to v6.3.0 |
| Security | A | ✅ QNAI_SSL_VERIFY, .secrets-local/ deleted, env-var creds, mt5_accounts.yaml interpolated |
| Test Suite | B+ | ✅ Core tests + 47 DCC-GARCH tests |
| Dashboard | B | ✅ 18 pages wired, build pending |
| PYTHONPATH Isolation | A | ✅ launch.bat + README + AGENTS docs |

---

*Built with fury from Aceh, Indonesia 🇮🇩*
