# Quant Nanggroe AI — Institutional Master TODO & Roadmap

Dokumen ini adalah **peta jalan resmi (Master TODO)** pengembangan platform **Quant-Nanggroe-AI** menuju sistem **Autonomous Quantitative Hedge Fund Institusional (v5.1.0)**.

---

## 🎯 Status Rilis Saat Ini: `v5.1.0 — Security Sweep + AutoRegistry v3`

```
[ Data Layer ]          ██████████ 100% (OHLCV, CCXT, MT5, Order Book Imbalance Ratio)
[ Strategy Engine ]     ██████████ 100% (152 Strategi via AutoRegistry v3)
[ Risk Engine ]         ██████████ 100% (9-Checkpoint Gate, Kill Switch, Weekly Veto)
[ Execution Layer ]     ██████████ 100% (TWAP/VWAP, Smart Router, Paper Broker)
[ AI Self-Evolution ]   ██████████ 100% (Self-Aware + Self-Evolve + Self-Fine-Tune)
[ API & Frontend UI ]   ████████░░  80% (FastAPI 174 endpoints, Dashboard partially wired)
[ Standalone Mode ]     ██████████ 100% (Zero-Hermes entry point)
[ Security ]            ██████████ 100% (Hardcoded secrets removed, env vars only)
[ Codebase Cleanup ]    ████████░░  80% (6 duplicate dirs removed, 139 legacy strategies remain)
```

---

## ✅ Completed (v5.1.0)

- [x] **Self-Aware Module** — `engine/self_aware.py` (142 LOC)
- [x] **Self-Evolve** — `StrategyEvolver` with real walk-forward validation
- [x] **Self-Fine-Tune** — `SelfFineTuner` with grid search optimization
- [x] **Auto-Registry v3** — Scans ENTIRE repo (1017+ files, 32 dirs)
- [x] **Standalone Mode** — `engine/standalone.py` runs without Hermes
- [x] **Weekly Loss Veto** — Verified working (3/3 test pass)
- [x] **Risk Guard Combined Path** — `daily_pnl_pct` parameter wired
- [x] **Credentials Security** — All hardcoded secrets removed, env vars only
- [x] **MT5 Password** — Removed from `qna_autonomous_cycle.py` and `hedge_fund.py`
- [x] **Duplicate Cleanup** — 6 duplicate dirs deleted (~400K+ freed)
- [x] **Dashboard API** — `getRiskParity`, `sliceOrder`, `configApi` wired
- [x] **Engine `__all__`** — 10 ghost references removed
- [x] **Debate Engine** — `summary` + `reasoning` fields added

---

## 🚀 In Progress (Phase 3)

- [ ] **9router Proxy Start** — Port 20128 EACCES, needs zombie process kill
- [ ] **MT5 Re-login** — User action needed (auth failed -6)
- [ ] **GitHub dhaher-labs Push** — Branch protection blocks direct push, needs PR
- [ ] **Fix 541 Pre-existing Test Failures** — `test_factors.py` import cascade

---

## 📋 Backlog (Phase 4)

- [ ] **Deduplicate 10 Overlapping Classes** — Signal×7, Position×6, StrategyType×5
- [ ] **Archive 139 Legacy Strategies** — Move `engine/strategy/strategies/` to archive
- [ ] **Split 15 Large Files** — Largest: `technical.py` (980 LOC)
- [ ] **Real-time CFTC COT Integration** — Direct feed from CFTC
- [ ] **Automated MT5 Reconnection** — Auto-reconnect daemon
- [ ] **L2/L3 Tick Stream Handler** — Sub-second WebSocket streaming
- [ ] **Online RL Fine-tuning** — PPO/SAC integration into execution loop
- [ ] **NLP Sentiment Processing** — SEC filings + FRED via LLM

---

## 📌 Operating Rules

1. **Single Entry Point**: `python qna.py status` or `python qna.py api`
2. **Fail-Closed Safety**: Never disable Risk Guard or Kill Switch in production
3. **Evidence-Based**: All strategies must be validated with backtest before live
4. **Self-Evolution**: Mutations validated via walk-forward, never blindly accepted
5. **No Hardcoded Secrets**: All credentials via env vars only

---

*v5.1.0 — Built with fury from Aceh, Indonesia 🇮🇩*

---

> **SSOT:** `CANONICAL.md` v8.0.19 — BAL $1,445, weekly 0 WIB, probe 0/32, CPCV 207, launch.bat 1, vector 6 modul
