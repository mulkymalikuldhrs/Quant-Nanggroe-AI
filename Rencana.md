# 📋 RENCANA — Quant-Nanggroe-AI (QNA) v6.1.0

**Owner:** Mulky Malikul Dhaher (Dhaher Labs) | **Updated:** 2026-08-01
**Status:** 🟢 LIVE REAL-ONLY TRADING — Valetax 372044706 ($1122.05)

---

## 🏗️ CARA KERJA SISTEM (Architecture Flow)

```
┌─────────────────────────────────────────────────────────────┐
│                   QNA AUTONOMOUS CYCLE                       │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┴─────────────────────┐
        ▼                                           ▼
┌──────────────────┐                       ┌──────────────────┐
│  MARKET DATA     │                       │  STRATEGIES      │
│  (MT5 LIVE)      │                       │  77 registered   │
│  BTC/EUR/XAU.vx  │                       │  6 active:       │
└──────────────────┘                       │  SMC, Wyckoff,   │
        │                                  │  MeanRev,        │
        ▼                                  │  Dhaher, Kronos  │
┌──────────────────┐                       └──────────────────┘
│  INDICATORS      │                               │
│  ATR, RSI, MACD  │                               ▼
│  BB, VWAP        │                       ┌──────────────────┐
└──────────────────┘                       │  SIGNAL FUSION   │
        │                                  │  weighted vote   │
        └──────────────┬───────────────────▶│  conf ≥ 0.65    │
                       │                   └──────────────────┘
                       │                           │
                       │                           ▼
                       │                   ┌──────────────────┐
                       │                   │  RISK MANAGER    │
                       │                   │  9-checkpoint gate│
                       │                   │  KillSwitch       │
                       │                   │  Downside Dev     │
                       │                   │  Sortino          │
                       │                   └──────────────────┘
                       │                           │ APPROVED
                       │                           ▼
                       │                   ┌──────────────────┐
                       │                   │  EXECUTION       │
                       │                   │  MT5 LIVE ONLY   │
                       │                   │  Lot clamp       │
                       │                   │  No SL/TP if ≤0  │
                       │                   └──────────────────┘
                       │                           │
                       └──────────────────────────▶ REAL ORDER TICKET
```

---

## 🚀 ENTRY POINTS (Cara Menjalankan)

```bash
# 1. Purified engine (autonomous_cycle.py)
env -u PYTHONPATH PYTHONPATH=. QNAI_ENCRYPTION_KEY="..." \
  .venv312/Scripts/python.exe -m quant_nanggroe.autonomous_cycle

# 2. LiveEngine (qna.py live)
env -u PYTHONPATH PYTHONPATH=. QNAI_ENCRYPTION_KEY="..." \
  .venv312/Scripts/python.exe qna.py live
```

**Venv:** `.venv312` (Python 3.12.13) | **Deps:** `requirements_qna.txt`
**Broker:** ValetaxIntl-Live2 | **Account:** 372044706 | **Symbols:** `.vx` suffix

---

## ✅ SELESAI (2026-08-01)

| # | Item | Evidence |
|---|------|----------|
| 1 | REAL-ONLY enforcement | `SyncPaperBroker` deleted, fail-closed if MT5 down |
| 2 | Live order verified | Tickets 20188224176, 20188224713 (BTCUSD.vx) |
| 3 | trade_mode mapping fix | Mode 4 = FULL (not DISABLED) |
| 4 | Lot clamp to broker | Min 0.01, step 0.01 enforced |
| 5 | SL/TP omit when ≤0 | Avoids `trade_stops_level` rejection |
| 6 | Downside deviation + Sortino | `RiskManager` methods + unit test |
| 7 | Deps complete | pydantic-settings, scipy, ccxt, pandas |

---

## 📅 RENCANA KE DEPAN (Roadmap dari MASTER.md)

### FASE 1: FOUNDATION FIX (Hari 1-3)
- [ ] Evolution loop wiring (`main.py` scan→evaluate)
- [ ] Silent errors → `log.error` (20+ files)
- [ ] `get_valid_pairs` import fix
- [ ] Dashboard rebuild (npm + color config)
- [ ] Wire dashboard API → evolution journal SQLite

### FASE 2: QUANT-GRADE TOOLING (Hari 4-10)
- [ ] Alphalens adapter (IC/quantile/turnover)
- [ ] Polars migration (10x speedup data layer)
- [ ] HRP allocator (hierarchical risk parity)
- [ ] KMeans clustering (diversification)
- [ ] ffn analytics (performance stats)
- [ ] Pytimetk feature engine

### FASE 3: INSTITUTIONAL HARDENING (Hari 11-20)
- [ ] Data Quality Framework (staleness/gap/SLA)
- [ ] Telegram Alert Bot (critical/warning/info)
- [ ] Audit Trail Dashboard
- [ ] Test coverage 80%+

### FASE 4: ADVANCED QUANT (Hari 21-30)
- [ ] Autoencoder factor embeddings (PyTorch)
- [ ] DCC-GARCH + Copula (tail dependence)
- [ ] MACD as factor
- [ ] Multi-Account MT5 (account rotation)

---

## 📊 CURRENT STATE SNAPSHOT

| Metric | Value |
|--------|-------|
| Balance | $1,122.05 |
| Live positions | 3 (GBPUSD.vx, BTCUSD.vx ×2) |
| Strategies active | 6 |
| Risk per trade | 0.5% ($5.61) |
| Max daily loss | 5% (HARD veto) |
| Max weekly loss | 2.5% (HARD veto) |

---

## 🔗 LINKS
- [[QNA_AGENT_STATE]]
- [[Quant-Nanggroe-AI/Production-Status-2026-08-01]]
- [[Quant-Nanggroe-AI/Risk/Risk-Management-Framework]]
- [[Quant-Nanggroe-AI/Master-Index]]
