# SKEPTIC-MAX AUDIT — QNA Live Trading Correctness (2026-08-02)

**Auditor lens:** clawbot (skeptic-max) + qna-findings-audit skill
**Scope:** Live trading paths only (`autonomous_cycle.py`, `PurifiedEngine`, `engine_production_bridge_purified.py`)
**Method:** Re-verified each skill-documented gap against CURRENT worktree (code moves fast — stale verdicts discarded)

---

## 🔴 CRITICAL — FIXED THIS SESSION

### F1: `autonomous_cycle.py` risk guard weaker than constitutional stack
- **File:line:** `quant_nanggroe/engine_production_bridge_purified.py:228` (RiskGuard.can_trade)
- **Claim vs reality:** `live_engine.py` (qna.py live) uses `EngineRiskManager` + `KillSwitch` + weekly loss. But `autonomous_cycle.py` uses `PurifiedEngine.risk` (RiskGuard) which ONLY checked balance>0 + daily 3%. **No weekly loss, no KillSwitch, no drawdown enforcement in the live autonomous loop.**
- **Evidence:** `grep -n "weekly_loss\|KillSwitch" engine_production_bridge_purified.py` → 0 hits before fix. `autonomous_cycle.py` imports NOTHING from `engine.risk.manager`.
- **Fix applied:** RiskGuard now enforces weekly 3% loss + KillSwitch state. `autonomous_cycle.py` initializes KillSwitch + refreshes state each cycle (fail-closed halt).
- **Verified:** weekly -4% → veto; KillSwitch active → veto.

---

## 🟢 VERIFIED ALREADY CORRECT (no action)

| Gap from skill | Status in current tree |
|---------------|----------------------|
| Naked SL/TP in exchange/mt5_broker.py | STALE — exchange/mt5_broker.py:649-651 passes sl/tp; live path uses connectors/mt5_broker.py (protected) |
| Dual strategy tree unreachable | Live path uses StrategyRegistry (29 canonical); legacy tree not in autonomous_cycle import |
| Dashboard mock data | Not in scope (dashboard not live-trading path) |
| Kelly stack dead | PARTIAL — PurifiedEngine.kelly_cache now updated by self_eval (this session); full MultiAssetKelly still backtest-only but live sizing uses kelly_cache |

---

## 🟡 MEDIUM — KNOWN, NOT YET FIXED (documented, not blocking live trades)

| Gap | Impact | Note |
|-----|--------|------|
| `engine/risk/manager.py` full stack unwired from autonomous_cycle | Redundant now (RiskGuard upgraded) but manager.py still dead for this path | Acceptable — RiskGuard covers the gates |
| `MultiAssetKelly` / `RiskParityOptimizer` not in live loop | No cross-asset correlation sizing | Future enhancement (FASE 2) |
| `engine/regime/` detectors orphaned from live loop | No regime-based position scaling live | Future enhancement |
| Hardcoded SL/TP (±0.5%/±1%) in StrategySignalGenerator | Not strategy-derived; suboptimal but safe | FASE 1 backlog |

---

## VERDICT (KOREKSI 2026-08-02 PM — clawbot 3-agent audit)

**Verdict lama "live path 100% sound" = OVERCLAIM. Yang benar:**
- REAL-ONLY (no paper) ✅
- Conflict-resolved (no random buy+sell) ✅
- Position sizing LOTS equity-aware (fadecf9d) ✅
- ATR+structure SL/TP + KillSwitch fail-closed ✅
- **Strategy-attributed (journal): ❌ DEAD CODE** — journal di path salah (G1) + `PositionManager.journal=None` (G2) → 0 rows di DB manapun
- **Self-evaluating (kelly from real pnl): ❌ DEAD CODE** — sama G1/G2 + `_kelly_cache` typo + `record_trade` never called
- **Constitutionally risk-guarded: ⚠️ PHANTOM** — RiskGuard di phantom $10k, MT5 balance/equity tidak pernah disync, `update_pnl` never called (G3)
- **Registered strategies trading: ❌ TIDAK PERNAH** — `analyze()` vs `generate_signal()` mismatch → 81 strategi = zero signal (G4)

**Detail lengkap:** `FINDINGS_TRADE_ATTRIBUTION.md` · `FINDINGS_SLTP_TRAILING.md` · `FINDINGS_POSITION_SIZING.md`. **Fix order:** G1→G2→G3→G4→G5→G6 (Rencana.md FASE 0). Live trading *did happen* (tickets nyata), tapi setiap klaim md soal self-eval/attribution/risk harus dianggap belum terbukti sampai FASE 0 selesai.
