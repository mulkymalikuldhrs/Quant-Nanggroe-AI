# Quant Nanggroe AI — Institutional Master TODO & Roadmap

Dokumen ini adalah **peta jalan resmi (Master TODO)** pengembangan platform **Quant-Nanggroe-AI** menuju sistem **Autonomous Quantitative Hedge Fund Institusional**.

---

## 🎯 Status Rilis Saat Ini: `v5.1.0 — Security Sweep + Kill Switch C5 + hedge_fund Subpackage`

```
[ Entry Point ]         ██████████ 100% (Single: qna.py, all legacy archived)
[ Strategy Pipeline ]   ██████████ 100% (9 registered via @StrategyRegistry, canonical path)
[ Kill Switch C5 ]      ██████████ 100% (Cross-process shared state, fail-closed)
[ Risk Engine ]         ██████████ 100% (9-Checkpoint Gate, Kill Switch, Weekly Veto)
[ hedge_fund ]          ██████████ 100% (Multi-provider aggregator subpackage)
[ Execution Layer ]     ██████████ 100% (TWAP/VWAP, Smart Router, Paper Broker)
[ AI Self-Evolution ]   ██████████ 100% (Self-Aware + Self-Evolve + Self-Fine-Tune)
[ API & Frontend UI ]   ████████░░  80% (FastAPI 181 endpoints, Dashboard needs build)
[ Security ]            ██████████  96% (backup_env archived, secrets rotation pending git history purge)
[ Codebase Cleanup ]    ██████████ 100% (All entry points archived, single qna.py)
[ PYTHONPATH Isolation ]██████████ 100% (launch.bat + README + AGENTS docs)
[ Documentation ]       ██████████ 100% (50+ docs filled)
```

---

## ✅ Completed

- [x] **Single Entry Point** — `python qna.py [cli|api|daemon|web|status|stop|hedge]` is the ONE entry point
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
- [ ] **PYTHONPATH Isolation** — Permanent launcher script for clean boot
- [ ] **Test Suite Environment** — Fix pytest env to clear 431 cached failures

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

1. **Single Entry Point**: `python qna.py status` or `python qna.py api`
2. **Fail-Closed Safety**: Never disable Risk Guard, Kill Switch, or C5 convergence in production
3. **Evidence-Based**: All strategies must be validated with backtest before live
4. **Self-Evolution**: Mutations validated via walk-forward, never blindly accepted
5. **No Hardcoded Secrets**: All credentials via env vars only
6. **No Root-Level Entry Points**: `qna.py` is the ONLY launcher

---

## 📊 Audit Summary (2026-07-25)

| Component | Grade | Status |
|-----------|-------|--------|
| Risk Engine | A | ✅ 9-checkpoint gate, fail-closed, weekly veto, KillSwitch C5 |
| Kill Switch C5 | A | ✅ Cross-process shared state, fail-closed, Path-A + Path-B |
| Strategies (Canonical) | A | ✅ 9 registered via @StrategyRegistry, full signal gen |
| Architecture | A | ✅ Clean modular, single entry point, 2,189 .py files |
| hedge_fund | A | ✅ Multi-provider aggregator with voting engine |
| Documentation | A- | ✅ 50+ docs filled |
| Security | B+ | ✅ backup_env archived, 15 findings logged (2 CRITICAL git purge pending) |
| Walk-forward Engine | A | ✅ CPCV/rolling/anchored, synthetic smoke test |
| Test Suite | C | ⚠️ 431 cached failures, pytest env needs setup |
| MT5 Bridge | C | ⚠️ Terminal must run manually, no cron-to-live wiring |
| Dashboard | B | ✅ 18 pages wired, Next.js API proxy, build pending |
| PYTHONPATH Isolation | A | ✅ launch.bat + README + AGENTS docs |

---

*Built with fury from Aceh, Indonesia 🇮🇩*
