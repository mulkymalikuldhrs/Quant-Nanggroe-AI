# Quant Nanggroe AI — Institutional Master TODO & Roadmap

Dokumen ini adalah **peta jalan resmi (Master TODO)** pengembangan platform **Quant-Nanggroe-AI** menuju sistem **Autonomous Quantitative Hedge Fund Institusional (v5.0.0)**.

---

## 🎯 Status Rilis Saat Ini: `v5.0.0 — Institutional Quant Autonomous Grade`

```
[ Data Layer ]          ██████████ 100% (OHLCV, CCXT, MT5, Order Book Imbalance Ratio)
[ Strategy Engine ]     ██████████ 100% (141 Strategi via AutoRegistry)
[ Risk Engine ]         ██████████ 100% (9-Checkpoint Gate, Kill Switch, Weekly Veto)
[ Execution Layer ]     ██████████ 100% (TWAP/VWAP, Smart Router, Paper Broker)
[ AI Self-Evolution ]   ██████████ 100% (Self-Aware + Self-Evolve + Self-Fine-Tune)
[ API & Frontend UI ]   ████████░░  80% (FastAPI 179 endpoints, Dashboard needs wiring)
[ Standalone Mode ]     ██████████ 100% (Zero-Hermes entry point)
```

---

## ✅ Completed (v5.0.0)

- [x] **Self-Aware Module** — `engine/self_aware.py` (142 LOC)
- [x] **Self-Evolve** — `StrategyEvolver` with walk-forward validation
- [x] **Self-Fine-Tune** — `SelfFineTuner` with grid search optimization
- [x] **Auto-Registry** — Auto-discovers 24 strategies without manual imports
- [x] **Standalone Mode** — `engine/standalone.py` runs without Hermes
- [x] **Weekly Loss Veto** — Verified working (3/3 test pass)
- [x] **Risk Guard Combined Path** — `daily_pnl_pct` parameter wired
- [x] **Credentials Security** — Plaintext secrets replaced with env vars
- [x] **Engine `__all__`** — 10 ghost references removed
- [x] **Debate Engine** — `summary` + `reasoning` fields added
- [x] **Full Test Suite** — 492/493 pass (99.8%)

---

## 🚀 In Progress (Phase 3)

- [ ] **Dashboard UI Wiring** — Connect `/api/trading/slice-order`, `/api/portfolio/risk-parity`, `/api/config` to Next.js Dashboard
- [ ] **Real MT5 Data → Backtest** — Feed live OHLCV into StrategyEvolver (needs MT5 re-login)
- [ ] **Graphify Re-scan** — Re-index all files, verify no orphan modules

---

## 📋 Backlog (Phase 4)

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

---

*v5.0.0 — Built with fury from Aceh, Indonesia 🇮🇩*
