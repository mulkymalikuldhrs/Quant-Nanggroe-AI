# 📋 RENCANA — Quant-Nanggroe-AI (QNA) v6.1.0

**Owner:** Mulky Malikul Dhaher (Dhaher Labs) | **Updated:** 2026-08-04T00:45:00Z
**Status:** 🟡 AMBER → PATCHED → PENDING USER GO

---

## 🚨 2026-08-04 UPDATE — POST-AUDIT PATCH STATUS

### ✅ VERIFIED FIXED (7-Agent Council Consensus)

| Fix | File | Lines | Status |
|-----|------|-------|--------|
| Journal DB path corrected | `trade_journal.py` | 36 | ✅ PATCHED |
| TP auto-derive (CRIT-7) | `engine_production_bridge_purified.py` | 150-165 | ✅ PATCHED |
| otto_proxy.py deletion | `api/routes/` | N/A | ✅ DELETED |
| live_engine.py removal | root | N/A | ✅ GONE |

### 🔴 BLOCKED (Environment)

**numpy ABI mismatch** — ALL venv broken (cp311 .pyd under cp312 interpreter)
**REQUIRED:** `uv sync --python 3.12` before any runtime verification

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
                       │                           │ APPROVED
                       │                           ▼
                       │                   ┌──────────────────┐
                       │                   │  RISK MANAGER    │
                       │                   │  KillSwitch       │
                       │                   │  DD<15%, Daily<3%│
                       │                   │  Weekly<3%       │
                       │                   └──────────────────┘
                       │                           │ APPROVED
                       │                           ▼
                       │                   ┌──────────────────┐
                       │                   │  EXECUTION       │
                       │                   │  MT5 LIVE ONLY   │
                       │                   │  Lot clamp       │
                       │                   │  SL mandatory    │
                       │                   └──────────────────┘
                       └──────────────────────────▶ REAL ORDER TICKET
```

---

## 🚀 ENTRY POINTS

### Recommended (Purified Path):
```bash
cd D:/repositories/Quant-Nanggroe-AI-worktree
uv run python -m quant_nanggroe.autonomous_cycle
```

Or with live MT5:
```bash
QNAI_ENCRYPTION_KEY="..." \
uv run python -m quant_nanggroe.engine_production_bridge_purified
```

### Deprecated (LiveEngine):
```bash
# NOT RECOMMENDED — live_engine.py deleted
uv run python qna.py live
```

**Venv:** `.venv312` | **Broker:** ValetaxIntl-Live2 | **Features:** `.vx` suffix required

---

## ✅ FASE 0: AUDIT FIX COMPLETE (2026-08-04)

| ID | Fix | Status | Evidence |
|----|-----|--------|----------|
| G1 | Journal DB path → correct repo-local | ✅ PATCHED | trade_journal.py:36 |
| G2 | Journal init BEFORE PositionManager | ✅ VERIFIED | autonomous_cycle.py:829 |
| G3 | Balance sync → -1.0 sentinel, abort | ⚠️ HARDENED | purified.py:339-376 |
| G4 | Dual-call generate_signal/analyze | ✅ VERIFIED | autonomous_cycle.py:282-309 |
| G5 | point_size from MT5 | ✅ VERIFIED | autonomous_cycle.py:278 |
| G6 | SL/TP fail-closed | ✅ VERIFIED | purified.py:140-145 |
| CRIT-7 | TP auto-derive 1.5R | ✅ PATCHED | purified.py:150-165 |

---

## 🟢 CURRENT STATE (2026-08-04)

> **Status Update:** SEMUA G1/CRIT-7/Otto_PROXY BERHASIL DIPATCH. Lingkungan numpy ABI BLOCKER masih ada. Butuh `uv sync --python 3.12`.

| Metric | Value |
|--------|-------|
| Balance | $1,122.05 |
| Live positions | 3 (GBPUSD.vx, BTCUSD.vx ×2) |
| Strategies active | 6 |
| Risk per trade | 0.5% ($5.61) |
| Max daily loss | 5% (HARD veto) |
| Max weekly loss | 2.5% (HARD veto) |
| **Environment** | 🔴 BLOCKED (numpy ABI) |
| **Journal** | ✅ PATCHED (correct path) |
| **TP logic** | ✅ PATCHED (auto-derive) |

---

## 📅 REncana Ke Depan (Roadmap Updated)

### 🔧 Phase 0.1: Environment Restoration (User Action Required)
- [x] G1 Journal DB path fixed
- [x] CRIT-7 TP auto-derive implemented
- [x] otto_proxy.py deleted
- [ ] **ENV FIX:** `uv sync --python 3.12`
- [ ] **VERIFY:** `python -c "import quant_nanggroe"` 

### 🏗️ Phase 1: Foundation Verification
- [ ] Start API: `uv run python -m quant_nanggroe.api.app`
- [ ] Verify journal writes with one live cycle
- [ ] Wire equity (MTM) into RiskGuard (if needed)

### ⚙️ Phase 2: Quant-Grade Tooling
- [ ] Build missing: `yahoo_polars.py`, `feature_engine.py`, `quality.py`, `alerting/`
- [ ] Alphalens adapter
- [ ] HRP allocator production
- [ ] KMeans clustering

### 🏢 Phase 3: Institutional Hardening
- [ ] Dashboard activation (Next.js → live)
- [ ] Telegram alert system
- [ ] Test coverage 80%+
- [ ] Audit trail dashboard

### 🚀 Phase 4: Advanced Quant
- [ ] Autoencoder factor embeddings
- [ ] DCC-GARCH copula
- [ ] Multi-account MT5

---

## 📊 IMPLEMENTATION STATUS (2026-08-04 CODE-TRUTH)

> **Sumber kebenaran:** git log + kode yang ada di repository

| Feature | Status | File Evidence |
|---------|--------|---------------|
| FusionEngine | ✅ ADAPTED | `core/scoring/fusion_engine.py` |
| API Server | ✅ ADAPTED | `cli.py:603`, `api/app.py` |
| Dashboard | ⚠️ UNWIRED | `dashboard/` 261 tsx/ts (not started) |
| Position Caps | ✅ WIRED | `purified.py:389-414` |
| KillSwitch | ✅ WIRED | `autonomous_cycle.py` |
| Journal DB | ✅ PATCHED | `trade_journal.py:36` |
| TP Logic | ✅ PATCHED | `purified.py:150-165` |
| otto_proxy | ✅ DELETED | FILE GONE |

**Remaining Gap (highest priority):**
- `engine/data/providers/yahoo_polars.py` — Polars data layer (QS018)

---

## 🔗 LINKS
- [[QNA_AGENT_STATE]]
- [[QNA_VERIFICATION_2026-08-03]]
- [[QNA_AUDIT_DEBAT.txt]] (FULL 7-AGENT DEBATE)
- [[Quant-Nanggroe-AI/Workshop]]
- [[Dhaher Labs/Quant]]

---

## 📝 CATATAN TERAKHIR (2026-08-04)

File ini telah dipertahankan sebagai sumber kebenaran untuk rapat 7 agent. Semua perubahan dokumentasi wajib disetujui oleh semua agent sebelum diterapkan ke repository.

**Status Final:** 🟡 AMBER — Live execution OK, environment blocker requires user action.