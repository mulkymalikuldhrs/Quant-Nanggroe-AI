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

> **⚠️ KOREKSI 2026-08-02 PM (clawbot 3-agent audit):** klaim "live trading path 100% sound" = **overclaim**. Self-eval/attribution = **dead code** (G1+G2), RiskGuard = **phantom $10k** (G3), registry strategies **tidak pernah trade** di autonomous loop (G4). Lihat FASE 0 di bawah — ini WAJIB sebelum live path bisa dipercaya.

### 🚨 FASE 0: AUDIT FIX (2026-08-02 PM — dari 3 report findings)
| ID | Fix | File | Status |
|----|-----|------|--------|
| G1 | Fix DB path `dirname(x3)` → repo root; startup assertion + alert kalau journal 0 rows | `trade_journal.py:29-32` | ✅ DONE (verified: DB_PATH di repo) |
| G2 | Move `self.journal = TradeJournal()` SEBELUM `PositionManager(...)` | `autonomous_cycle.py:659/665` | ✅ DONE (verified: self-eval PASS) |
| G3 | Sync `mt5.account_info().balance/equity` tiap cycle ke RiskGuard; panggil `update_pnl` dari deal history | `autonomous_cycle.py:648`; `engine_production_bridge_purified.py` | ✅ DONE (sudah ter-wiring oleh session pagi) |
| G4 | Panggil `generate_signal()` (bukan `analyze()`) utk registry strategies; pakai StrategySignal sl/tp per strategi | `autonomous_cycle.py:262`; `engine/strategies/base.py:129` | ✅ DONE (dual-call: generate_signal + fallback analyze) |
| G5 | `point_size` dari `mt5.symbol_info().point` (fallback per symbol) | `autonomous_cycle.py:278` | ✅ DONE (real point dari broker) |
| G6 | Fail-closed: sl/tp ≤0 → REJECT/turunkan dari ATR (never naked); TP=0 fail-closed juga | `engine_production_bridge_purified.py:123-124`; `connectors/mt5_broker.py:90-93` | ✅ DONE (SL wajib — reject kalau ≤0) |
| G7 | Enforce `MAX_POSITIONS_PER_SYMBOL=1` / `MAX_TOTAL_POSITIONS=5` di `PurifiedEngine.cycle` | `autonomous_cycle.py:94-95` (defined, unused) | ✅ DONE (positions_get + cap check) |
| G8 | Single-instance lock utk autonomous_cycle (PID/socket) — 4+ proses pernah jalan bareng | `autonomous_cycle.py` | ✅ DONE (OS file lock, verified ada di code) |
| G9 | Fix `_kelly_cache` typo → `kelly_cache`; panggil `record_trade`/`self_eval` setelah close | `autonomous_cycle.py:611` | ✅ DONE (typo fixed + verified) |
| G10 | Log HOLD dengan reason; jangan log "CLOSED" kalau retcode != DONE | `autonomous_cycle.py` | ✅ DONE (HOLD per symbol + HOLD ALL) |
| G11 | Breakeven + structure-based trailing (SMC swing, invalidate on BOS) | `risk_levels.py:101-125` | ✅ DONE (breakeven_sl + trailing_sl_structure, unit-tested PASS) |
| G12 | Tambah `strategy`+`comment` di `Order`/`place_order` LiveEngine path | `engine_production_bridge.py:426-433`; `mt5_broker.py:80-93` | ✅ DONE (strategy_name+notes → broker comment) |

**FASE 0 COMPLETE — 2026-08-02 (commit `804a716f` G1-G10, `a49d6704` G11-G12). Semua 12 gap live-path ditutup.**

### 🏛️ KEPUTUSAN DEBAT ROUND 1 (2026-08-02, 3 kubu: PRO/CONTRA/OPERATOR) → HYBRID GO-LIVE MONDAY
- **Prioritas #1:** CLOSE 3 legacy positions (20178543987, 20188224176, 20188224713) di tick pertama open — kode pre-fix, mungkin NAKED (SL=0), risiko Monday gap terbesar.
- Boot SATU instance (lock G8 aktif). Protokol verifikasi 11 langkah + hard-abort ada di `DEBATE_ROUND1_2026-08-02.md`.
- Risk bounded: caps 1/symbol+5 total, SL mandatory, min-conf 0.6, daily-loss 3% auto-block, worst ~$32.
- G11 trailing observasi 1-2 minggu (unbacktested) → fallback ATR sudah di kode.
- Floor $1.000: equity < itu → halt + alert. Self-eval gate: N≥20 closed trades → disable strategi negative.
- Status: ajukan ke @dhaherautobot utk koordinasi final.

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

> Verdict jujur (skeptic-max): **live trading path 100% sound** — ❌ **SALAH / OVERCLAIM, dikoreksi 2026-08-02 PM.** Eksekusi live nyata (Valetax, tickets asli) ✅, tapi **self-eval/attribution = dead code (G1+G2), risk gates = phantom $10k (G3), strategi registry tidak pernah trade (G4)**. Fix order: FASE 0 G1→G12 di atas. Sisanya (backtest/dashboard/agent) fitur/kualitas — bukan keselamatan.

---

## 🔗 LINKS
- [[QNA_AGENT_STATE]]
- [[Quant-Nanggroe-AI/Production-Status-2026-08-01]]
- [[Quant-Nanggroe-AI/Risk/Risk-Management-Framework]]
- [[Quant-Nanggroe-AI/Master-Index]]

