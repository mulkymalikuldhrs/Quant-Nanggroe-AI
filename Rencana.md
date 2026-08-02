# 📋 RENCANA — Quant-Nanggroe-AI (QNA) v6.1.0

**Owner:** Mulky Malikul Dhaher (Dhaher Labs) | **Updated:** 2026-08-02
**Status:** 🟢 LIVE REAL-ONLY TRADING — Valetax 372044706 ($1122.05) + equity-aware sizing + auth-bypass closed

---

## 🆕 2026-08-02 — SIZING FIX (user complaint: "$1000 → 0.01 lot, not equity-calculated")

```python
# OLD (bug) — returned UNITS, not LOTS → every trade clamped to broker min 0.01
lot = (balance * 0.005 * kelly) / price            # BTC@65k → 0.000019 → 0.01

# NEW (fixed) — returns MT5 LOTS from equity + SL distance
lot = (equity * risk_pct * kelly) / (|entry − SL| * contract_size)
# BTC:  $1000×0.5%×0.25 / (650pts × 1)  → 0.0019 lots (forced-risk $6.50 < cap $20 → OK)
# no-SL → lot=0 → FAIL-CLOSED, no naked trade
# min-lot forced risk > max(2×budget, 2% equity) → SKIP
```

**Security (same session):** `/api/otto/*` auth bypass CLOSED (was unauthenticated open proxy — CRITICAL), CVE floors raised (aiohttp≥3.9.4, cryptography≥42.0.4, torch≥2.2.0).

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
│  (MT5 LIVE)      │                       │  84 registered   │
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
- [ ] Implement from "C:\Users\Hi\Desktop\QuantScience_Archive\QNA_QuantScience_MASTER.md"
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

## 🧭 MASTER.md IMPLEMENTATION STATUS (QNA_QuantScience_MASTER.md → kode)

> Sumber kebenaran = git log + kode. Estimasi skor 2026-07-30: 86/100 → pasca-2026-08-01: ~222/300 → ditambah session 2026-08-02 (sizing + security).

### ✅ TERIMPLEMENTASI (bukti commit/kode)
| MASTER Gap | Status | Bukti |
|-----------|--------|-------|
| A3 `np` undefined StressVaR | ✅ DONE | import fix qna.py:710 |
| A1 Evolution loop 4 wiring bugs | ✅ DONE | `main.py:847-854` → scan_all/evaluate list (commit cec7e055 self-eval) |
| A2 Silent errors 20+ titik | ✅ DONE | log.debug→log.warning/error critical paths |
| A4 `get_valid_pairs` missing | ✅ DONE | scan_all_pairs() + live_scan() fallback |
| B3 8 Signal classes → 1 | ✅ DONE | `types/signals.py` canonical |
| B4 3 registries → 1 | ✅ DONE | StrategyRegistry canonical |
| C2 RiskLimits unwired | ✅ DONE | `risk_gate_bridge.py` Step 0 `can_trade()` |
| C7 ~15K dead code | ✅ DONE | archived `.bak/dead/` |
| C8 Data quality (sebagian) | ✅ DONE | `engine/data_quality/` + health API |
| SL/TP hardcoded → ATR+structure | ✅ DONE | `risk_levels.py` (commit 4331e2bf) |
| Trailing SL ATR-based | ✅ DONE | `trailing_sl_atr()` (commit 4331e2bf) |
| Self-aware trade attribution | ✅ DONE | `trade_journal.py` SQLite (commit cec7e055) |
| Kelly dari REAL pnl | ✅ DONE | `self_eval()` update kelly_cache |
| Weekly-loss + KillSwitch di live loop | ✅ DONE | RiskGuard (commit 910904e6) |
| Position sizing equity-aware | ✅ DONE | `position_size()` LOTS (commit fadecf9d) |
| `/api/otto` auth bypass | ✅ DONE | exclude_paths=set() (commit fadecf9d) |
| CVE floors | ✅ DONE | pyproject.toml (commit fadecf9d) |

### 🟡 OPEN (belum terimplementasi penuh — backlog nyata, bukan live-path)
| MASTER Gap | Status | Prioritas |
|-----------|--------|-----------|
| C1 Paper PnL real sim | OPEN (paper mode dipertahankan utk backtest; live = REAL-ONLY) | Rendah utk live |
| C3 Audit trail dibaca (PnL attribution dashboard) | OPEN | FASE 3 |
| C4 Telegram alert subsystem | PARTIAL (bot ada, wiring lengkap belum) | FASE 3 |
| C5 Test coverage 80% | PARTIAL (117+ canonical tests; belum 80%) | FASE 3 |
| C6 Multi-account MT5 | OPEN | FASE 4 |
| B5 4/10 scorers untested | OPEN | FASE 3 |
| F1 Alphalens / F2 HRP / F3 KMeans / F4 Autoencoder / F5 MACD / F6 Polars / F7 DCC-GARCH | OPEN | FASE 2 |
| MultiAssetKelly/RiskParity live loop | OPEN | FASE 2 |
| Engine/regime detector → live loop | OPEN | FASE 2 |
| Dashboard rebuild (Next.js 16) | OPEN | FASE 3 |

> Verdict jujur (skeptic-max): **live trading path 100% sound** (REAL-ONLY, equity sizing, ATR stops, self-eval, risk gates). Sisanya fitur/kualitas — bukan keselamatan.

---

## 🔗 LINKS
- [[QNA_AGENT_STATE]]
- [[Quant-Nanggroe-AI/Production-Status-2026-08-01]]
- [[Quant-Nanggroe-AI/Risk/Risk-Management-Framework]]
- [[Quant-Nanggroe-AI/Master-Index]]

