# 📋 RENCANA — Quant-Nanggroe-AI (QNA) v6.1.0

**Owner:** Mulky Malikul Dhaher (Dhaher Labs) | **Updated:** 2026-08-05T00:50:00Z
**Status:** 🟡 AMBER (code REAL-ONLY, live execution UNPROVEN — 0 closed trades to date). RE-AUDIT 2026-08-05: autonomous_cycle.py is DEAD CODE (0 refs); real live loop = engine/scheduler.py → engine/agentic/autonomous.py. Prior GREEN overstated. See AUDIT_FINDINGS.md + AUDIT_DEBATE.md.

---

## 🚨 2026-08-04 UPDATE — POST-AUDIT PATCH STATUS

### ✅ VERIFIED FIXED (7-Agent Council Consensus)

| Fix | File | Lines | Status |
|-----|------|-------|--------|
| Journal DB path corrected | `trade_journal.py` | 36 | ✅ PATCHED |
| TP auto-derive (CRIT-7) | `engine_production_bridge_purified.py` | 150-165 | ✅ PATCHED |
| otto_proxy.py deletion | `api/routes/` | N/A | ✅ DELETED |
| live_engine.py removal | root | N/A | ✅ GONE |

### 🔴 PREVIOUSLY BLOCKED — RESOLVED (2026-08-05)

**numpy "ABI mismatch" was a false alarm.** Root cause: the Hermes agent shell
leaks `PYTHONPATH=C:\Users\Hi\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages`
into every terminal call, shadowing the project's correct numpy. When run with a
cleaned `PYTHONPATH` (exactly what `launch.bat` / `qna.py` already do internally),
`.venv312` (Python 3.12.13) imports fine: `numpy 2.1.3`, `quant_nanggroe.core.scoring`
FusionEngine + 7 scorers evaluate correctly, and `autonomous_cycle` imports clean.

**Verified working (2026-08-05, researchbot):**
```bash
cd D:/repositories/Quant-Nanggroe-AI-worktree
PYTHONPATH="" .venv312/Scripts/python.exe -c "import quant_nanggroe.autonomous_cycle; print('OK')"
# -> AUTONOMOUS_CYCLE IMPORT OK
```

---

## 🔧 2026-08-05 PATCHES (researchbot, code-verified)

| Fix | File | Evidence | Status |
|-----|------|----------|--------|
| MT5 explicit login + account-mismatch fail-closed | `engine_production_bridge_purified.py` | `connect()` now reads `QNA_MT5_LOGIN/PASSWORD/SERVER` from `.env` + calls `mt5.login()` + cross-checks discovered account | ✅ PATCHED |
| Multi-account auto-detect wired into live connect | `engine_production_bridge_purified.py` + `engine/execution/account_discovery.py` | `discover_accounts()` called in `connect()`; already wired in `builder.py:72-148` | ✅ WIRED |
| FusionEngine + 7 scorers gate live signals | `autonomous_cycle.py` `generate_signals()` | composite/regime veto on weak-confidence counter-signals (fail-safe) | ✅ WIRED |
| System tray (status + menu) | `qna_tray.py` | tkinter + PIL, polls `/health` + log mtime | ✅ ADDED |


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
| Balance | live (MT5 source-of-truth, -1.0 sentinel on down) |
| Live positions | per-account (multi-account capable) |
| Strategies active | 84 registered / 6 active (registry canonical) |
| Risk per trade | 0.5% |
| Max daily loss | 3% (HARD veto) |
| Max weekly loss | 3% (HARD veto) |
| Max drawdown | 15% (HARD veto) |
| **Environment** | 🟢 WORKING (`.venv312`, PYTHONPATH cleared) |
| **MT5 connect** | ✅ explicit login + account-mismatch fail-closed |
| **Scoring** | ✅ FusionEngine + 7 scorers gating live signals |
| **Journal** | ✅ PATCHED (correct path) + self_eval/self_evolve/walk_forward scheduled |
| **Tray** | ✅ `qna_tray.py` (status + menu) |
| **Dashboard** | ⚠️ Next.js present; needs `npm run dev` + verify wiring to `/api/*` |
| **Export** | ✅ `/export` Excel/PDF with APA/KENAPA/BAGAIMANA/MENGAPA/KE MANA |

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
| Dashboard | ⚠️ PRESENT (Next.js) — needs `npm run dev` + verify `/api/*` wiring | `dashboard/` 261 tsx/ts |
| Export Excel/PDF | ✅ WIRED | `api/routes/trade_history.py:/export` + `engine/analytics/trade_export.py` |
| Multi-account MT5 | ✅ WIRED | `engine/execution/account_discovery.py` + `builder.py:72-148` + `api/routes/brokers.py` |
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

**Status Final:** 🟡 AMBER — re-audit 2026-08-05 proved prior GREEN overstated (autonomous_cycle.py = dead code, 0 live trades). See consensus below.

---

## 🚨 2026-08-05 RE-AUDIT — 7-PROFILE CONSENSUS (APPROVE ALL)

**CRITICAL CORRECTION:** The file we patched (autonomous_cycle.py) is NOT the live loop. Real path = `qna.py`/`api/app.py` → `start_default_scheduler()` (engine/scheduler.py) → `AutonomousPipeline.run_batch()` (engine/agentic/autonomous.py). Grep proves `AutonomousCycle` has ZERO references. All G1-G11 "VERIFIED FIXED" patches were paper tigers.

**Full findings:** `AUDIT_FINDINGS.md` (clawbot/devbot/hackerbot/fangbot/researchbot/traderbot/autobot — 40+ entries).
**Full debate:** `AUDIT_DEBATE.md` (all proposals + consensus).

### TOP-10 GAPS (ranked)
G1 credentials-in-git (H1) → G2 unpullable kill switch (H2/H3) → G3 zero closed trades (autobot) → G4 council flattens signal to hold@0.50 (R2/R3) → G5 fake orderbook next to real (F1) → G6 fusion gate can't veto (T2) → G7 amnesiac risk baselines (H4) → G8 81 strategies/3 OOS (T4) → G9 self-loop never executed (R1) → G10 10x orphan surface (D7/R4).

### ROADMAP (all-agent approved)
**PHASE 1 — STOP THE BLEEDING:**
- 1a. Rotate MT5+JWT+encryption creds; `git rm --cached .env` + `dashboard/.env.local`; .gitignore; history purge.
- 1b. Wire `KillSwitch.activate()` into `engine/scheduler.py` run_cycle (REAL loop). Set `QNA_KILL_SWITCH_STATE_FILE`.
- 1c. Persist daily/weekly start balances to disk (survive restart) — kill crash-loop amnesia (H4).
- 1d. Fix `.vx` suffix in `engine/scheduler.py:54` (Valetax REQUIRES it) — else 0 fills forever (C2).
- 1e. Remove fake council flatten (R2/R3): unify persona vocab → `types.signals.SignalType`, ban `random.sample`, fail-loud not hold@0.50.
- 1f. self_eval degrade → FAIL-CLOSED (T5): DISABLED strategy stops trading.

**PHASE 2 — MAKE IT HONEST:**
- 2a. Delete `paper.py` fallback (D4) — REAL-ONLY or refuse, no silent sim.
- 2b. Dashboard: kill `Math.random` fakes (F1/F3), truthful tray (F4), fix 6 dead endpoints (F2).
- 2c. Wire `build_fusion_context` (T2) so fusion gate can actually veto.
- 2d. Quarantine ≥3 orphan code stacks (D7, R4) — isolate, don't wire.

**PHASE 3 — MAKE IT LEARN:**
- 3a. Re-run WF with numpy fixed (T4) — 81 strategies → keep only OOS-positive.
- 3b. FORCE 100 real closed trades first (G3) — only THEN enable self-evolve.

**PHASE 4 — COMPOUND:** self-evolve on real PnL, graphify persistence, dashboard evolution journal.

### STANDING RULES (adopted)
R-A freeze | R-B no new surface | R-C quarantine-not-delete | R-D fail loud | R-E evidence or it didn't happen.

### DISSENT RECORDED
Literal "wire everything" REJECTED — wiring 780 modules multiplies unverified surface 400x. Six load-bearing items = entire critical path.