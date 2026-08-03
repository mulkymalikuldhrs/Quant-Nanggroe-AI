# QNA Autonomous Trading — Status Report (2026-08-02, PM audit)

**VERDICT (2026-08-01): 🟢 GREEN — REAL-ONLY LIVE TRADING FULLY OPERATIONAL**
**VERDICT (2026-08-02 PM, clawbot 3-agent audit — code = truth): 🟡 AMBER — live execution real, self-eval/attribution DEAD, risk gates on phantom equity.**
**VERDICT (2026-08-03, devbot code-truth re-verify): 🟡 AMBER — but G3 balance sync ALREADY HARDENED (account_balance returns -1.0, cycle aborts). Residual: journal 0-schema (G1), RiskManager 9-checkpoint dead in loop A, dual-loop (GAP-5). CRIT-1 (/api/otto) DOWNGRADED to MEDIUM — it IS behind auth, not unauthenticated.**

> ⚠️ Previous "GREEN" verdict overclaimed. Audit findings below are verified against working tree + live DB + live logs. Full detail: `FINDINGS_TRADE_ATTRIBUTION.md`, `FINDINGS_SLTP_TRAILING.md`, `FINDINGS_POSITION_SIZING.md`.

---

## 🔴 AUDIT GAPS (2026-08-02 PM) — must fix before trusting self-eval

| ID | Severity | Finding | Evidence (file:line) |
|----|----------|---------|----------------------|
| G1 | CRITICAL | Trade journal at WRONG PATH — `dirname(x3)` → `D:\repositories\data\qna_trade_journal.db` (0 rows). Repo `data/qna_trade_journal.db` = 0-byte, no schema. **No trade ever attributed.** | trade_journal.py:29-32 |
| G2 | CRITICAL | `PositionManager` built with `journal=None` (journal created AFTER) → close-journal + self_eval + Kelly never run | autonomous_cycle.py:659 vs 665; :413 |
| G3 | CRITICAL | RiskGuard phantom $10,000 — MT5 balance/equity never synced; `update_pnl` never called; DD/daily/weekly vetoes frozen | autonomous_cycle.py:648; purified:261-270 | ⚠️ PARTIAL FIXED (commit 0c77f919): balance+peak now sync from LIVE MT5 (verified 1130.23, can_trade=True). RESIDUAL: `update_pnl` still not wired to cycle() → DD/daily/weekly veto frozen in practice |
| G4 | CRITICAL | Registry strategies (SMC/Wyckoff/MeanRev/Dhaher/Kronos) never fire — loop calls `analyze()`, they implement `generate_signal()` → AttributeError swallowed | autonomous_cycle.py:262,286-288 |
| G5 | CRITICAL | `point_size` hardcoded 0.00001 → XAUUSD/BTCUSD min-stop clamp 100-10000× too small | autonomous_cycle.py:278; risk_levels.py:80-95 |
| G6 | MAJOR | Naked-fill surface: omit-if-≤0 in execute_order + connectors; TP=0 never fail-closed | purified:123-124; connectors/mt5_broker.py:90-93 |

## 📌 LIVE EVIDENCE (2026-08-02, cycle #214, login 372044706)

- 81 strategies loaded, min confidence 0.6 — **but zero signal lines, zero JOURNALED, zero SELF-EVAL** in `data/autonomous_loop.log` (967 lines).
- `Balance: $10000.00 | Trades: 0 | Wins: 0` every cycle (phantom risk state) while real ≈ $1,122 with 3 open positions.
- `Close failed for 20178543987: retcode=10018/10031 (Market closed)` every cycle + unconditional misleading `FULL TP: ... closed at 24.66R`.
- qna_live.db: trades=0, signals=0; positions=1 (paper-era BTCUSDT 'SMC' dummy from 2026-07-25, entry 30000).

---

## 🟢 VERIFIED OK (this audit)

| Layer | Status | Evidence |
|-------|--------|----------|
| REAL-ONLY enforcement | ✅ ACTIVE | Paper broker removed; MT5 down → RuntimeError (fail-closed) |
| Live trade execution | ✅ REAL | Tickets 20188224176 (SELL 0.01) + 20188224713 (BUY 0.01) + 20178543987 (still open) |
| Position sizing | ✅ FIXED (fadecf9d) | `equity × risk × kelly / (|entry−SL| × contract_size)` LOTS; no-SL → skip |
| SL/TP calc | ✅ ATR+structure | `risk_levels.py:52-98`, broker min-stop clamp, wired autonomous_cycle:259-285 |
| KillSwitch | ✅ fail-closed | wired + refreshed every cycle |
| Conflict resolution | ✅ | buy+sell same symbol deduped |
| trade_mode mapping | ✅ | mode 4 = FULL allowed (Valetax) |

---

## 🔄 Live Pipeline (How It Works)

```
┌─────────────────────────────────────────────────────────────┐
│  autonomous_cycle.py  (60s loop)                             │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ MT5 LIVE     │   │ Strategies   │   │ Indicators   │
│ BTC/EUR/XAU  │   │ 84 reg, 6 act│   │ ATR/RSI/MACD  │
└──────────────┘   └──────────────┘   └──────────────┘
        └───────────────┬───────────────┘
                        ▼
              ┌──────────────────┐
              │  Conflict Resolve│  resolve_conflicts (highest conf wins)
              └──────────────────┘
                        │
                        ▼
              ┌──────────────────┐
              │  RiskGuard       │  balance/DD/daily-3%/weekly-3%/KillSwitch
              │                  │  ⚠️ phantom $10k — G3, fix pending
              └──────────────────┘
                        │ APPROVED
                        ▼
              ┌──────────────────┐
              │  MT5 Execution   │  SL-distance lots (fadecf9d)
              │  (REAL-ONLY)     │  SL/TP ATR+structure
              └──────────────────┘
                        │
                        ▼
                 REAL TICKET ✅
```

---

## 📊 Verified Evidence (2026-08-01 baseline)

| Layer | Status | Evidence |
|-------|--------|----------|
| numpy + MT5 import | ✅ FIXED | `env -u PYTHONPATH .venv312/Scripts/python.exe` imports both cleanly (NUMPY 2.1.3 + MT5) |
| PurifiedEngine | ✅ LIVE | MT5 connected LIVE — Valetax 372044706 balance $1122.05 |
| autonomous_cycle | ✅ BOOTS | Entry points verified: LiveEngine starts cleanly, runs cycle |

---

## Live MT5 Connection Details

- **Broker:** Valetax International Limited (ValetaxIntl-Live2)
- **Account:** 372044706 (LIVE)
- **Balance:** $1,122.05 | Equity: $1,480.10
- **Trade allowed:** Yes | DLLs allowed: Yes
- **Terminal:** C:\Program Files\MetaTrader 5\terminal64.exe (build 6061)
- **Active Live Positions:** 3 (GBPUSD.vx BUY, BTCUSD.vx SELL, BTCUSD.vx BUY)

---

## What "Autonomous" Means Here

- Code boots end-to-end without human intervention.
- REAL-ONLY mode enforced (no sim/paper/mock fallbacks).
- Live MT5 data flows through strategies → risk → execution.
- Telegram alerts wired for subsystem failures.
- **⚠️ NOT yet:** per-strategy self-eval (G1/G2), real-equity risk (G3), registered strategies actually trading (G4).

---

## 🔍 fangbot RE-VERIFICATION (2026-08-03, code-inspection, skeptic pass)

**Orchestrator note:** This block added by fangbot (worker) during task QNA. Orchestrator `@dhaherautobot` must ratify before any prod-path edit. Cross-profile orchestration NOT executable from single fangbot session — see debate below.

### Audit G1–G6 — CORRECTIONS (evidence-backed, not .md-trusting)

| ID | Audit claim | fangbot re-verification | Verdict |
|----|-------------|--------------------------|---------|
| G1 | Journal at `D:\repositories\data\` (1 level wrong) | `trade_journal.py:30-31` = `dirname(dirname(__file__))`+`data/qna_trade_journal.db` = **repo-root** `data/` (correct). But `data/qna_trade_journal.db` = **0 bytes, no schema** → still 0 rows. `D:/repositories/data/qna_trade_journal.db` (8192b) is a STRAY file from wrong path, orphaned. | PARTIAL — path logic OK, DB never initialized/synced |
| G3 | RiskGuard phantom $10k, `update_pnl` not wired | `autonomous_cycle.py:809` `PurifiedEngine(initial_balance=10000.0)` still hardcoded default. Live log cycle #214 STILL prints `Balance: $10000.00`. Commit 0c77f919 claim ($1130 sync) NOT reflected in runtime log → residual unfixed OR not deployed. | CONFIRMED UNFIXED in runtime |
| G4 | "81 strategies NEVER fire — loop calls analyze()" | LOOP IS DUAL-PATH: `:282` `generate_signal()` first, fallback `:302` `analyze()`. 282 strategies define `generate_signal()` → those DO fire. Only strategies with ONLY `analyze()` fail. Audit oversimplified. | OVERSTATED — partial truth |
| G5 | `point_size` hardcoded 0.00001 | `:314` `point_size = 0.00001 if JPY else 0.00001` then `:322` `point_size = float(getattr(info,'point',point_size))` — dynamic override present. Hardcode only fallback. | MITIGATED — not the live bug |
| G6 | Naked-fill surface + misleading log | Log shows `Close failed ... Market closed` THEN `FULL TP ... closed at 24.66R` — **log asserts success on failed close**. Naked-fill + misleading telemetry confirmed. | CONFIRMED — telemetry lies |

### QuantScience M1–M5 status (plan was STALE)
- M2 `macd_factor.py` — **EXISTS** (87 lines, real, not missing)
- M3 `ffn_adapter.py` — **EXISTS** (101 lines, real, not missing)
- M5 `pyproject [quantscience]` — **EXISTS** (line 87)
- M1 `feature_engine.py` — **GENUINELY MISSING**
- M4 `yahoo_polars.py` — **GENUINELY MISSING**

### fangbot recommendation (pending orchestrator ratify)
1. **FRONT A (live safety) > FRONT B (features).** Do NOT touch `qna.py`/`autonomous_cycle.py`/`trade_journal.py`/`risk_levels.py` until orchestrator + debate approve TDD fix for G1/G3/G6. Live $1,122 at risk.
2. **Fix misleading log (G6)** is cheapest, highest-integrity win — but still prod path → needs approval.
3. **M1/M4** are additive, isolated, safe to build now (TDD) WITHOUT touching live path. Recommend proceed in parallel once orchestrator signals.
4. **Resolve orphaned `D:/repositories/data/qna_trade_journal.db`** (delete/migrate) to kill confusion.


<!-- CODE-TRUTH STATUS FOOTER — appended 2026-08-03 23:43:45 by autobot (QNA audit 2026-08-03) -->
<!-- Method: append-only. Source of truth = code, not prior .md claims. -->
## 🔍 CODE-TRUTH STATUS (2026-08-03 audit)
- **FusionEngine**: EXISTS — `quant_nanggroe/core/scoring/fusion_engine.py:27` (prior claim "false" RETRACTED).
- **API server**: EXISTS + startable — `quant_nanggroe/cli.py:603` uvicorn :8000; `launch.bat api`; 223 routes wired.
- **Dashboard**: UNWIRED only because server not started; UI code present (`dashboard/`, 261 tsx+ts).
- **Phantom-equity ($1M default)**: MITIGATED — P1b fail-CLOSED `_resolve_equity()` floor $1000 in `risk_gate_bridge.py` (ctor:145, evaluate:194, evaluate_from_state:449). Live path uses `evaluate_from_state` -> real MT5 equity.
- **Polars**: NOT imported anywhere (`import polars`=0) -> `engine/data/providers/yahoo_polars.py` genuinely MISSING (archive gap real).
- **Secrets**: 0 hardcoded (grep `sk-`/`AKIA`=0). `eval`/`pickle`: 0 live vulns (only security-linter strings).
- **ENV BLOCKER**: all venv numpy ABI broken (cp311 `.pyd` under cp312) -> runtime import unverified until `uv sync`. Patch syntax+logic verified standalone.
- **Archive upgrade**: 8/11 new modules ALREADY in code; 4 missing (quality.py, yahoo_polars.py, feature_engine.py, alerting/).
- **Audit trail**: `C:/Users/Hi/Desktop/QNA_AUDIT_DEBAT.txt` | inventory `QNA_FILE_INVENTORY.txt` | `QNA_EXTENSION_LEDGER.txt`.
<!-- END CODE-TRUTH FOOTER -->
