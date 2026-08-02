# QNA Autonomous Trading — Status Report (2026-08-02, PM audit)

**VERDICT (2026-08-01): 🟢 GREEN — REAL-ONLY LIVE TRADING FULLY OPERATIONAL**
**VERDICT (2026-08-02 PM, clawbot 3-agent audit — code = truth): 🟡 AMBER — live execution real, self-eval/attribution DEAD, risk gates on phantom equity.**

> ⚠️ Previous "GREEN" verdict overclaimed. Audit findings below are verified against working tree + live DB + live logs. Full detail: `FINDINGS_TRADE_ATTRIBUTION.md`, `FINDINGS_SLTP_TRAILING.md`, `FINDINGS_POSITION_SIZING.md`.

---

## 🔴 AUDIT GAPS (2026-08-02 PM) — must fix before trusting self-eval

| ID | Severity | Finding | Evidence (file:line) |
|----|----------|---------|----------------------|
| G1 | CRITICAL | Trade journal at WRONG PATH — `dirname(x3)` → `D:\repositories\data\qna_trade_journal.db` (0 rows). Repo `data/qna_trade_journal.db` = 0-byte, no schema. **No trade ever attributed.** | trade_journal.py:29-32 |
| G2 | CRITICAL | `PositionManager` built with `journal=None` (journal created AFTER) → close-journal + self_eval + Kelly never run | autonomous_cycle.py:659 vs 665; :413 |
| G3 | CRITICAL | RiskGuard phantom $10,000 — MT5 balance/equity never synced; `update_pnl` never called; DD/daily/weekly vetoes frozen | autonomous_cycle.py:648; purified:261-270 |
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
