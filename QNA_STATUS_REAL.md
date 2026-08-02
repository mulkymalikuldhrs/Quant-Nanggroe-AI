# QNA Autonomous Trading — Status Report (2026-08-01)

**VERDICT: 🟢 GREEN — REAL-ONLY LIVE TRADING FULLY OPERATIONAL**

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
              │  Signal Fusion   │  conf ≥ 0.65
              └──────────────────┘
                        │
                        ▼
              ┌──────────────────┐
              │  RiskManager     │  9-checkpoint gate
              │                  │  KillSwitch (fail-closed)
              │                  │  Downside Dev + Sortino
              └──────────────────┘
                        │ APPROVED
                        ▼
              ┌──────────────────┐
              │  MT5 Execution   │  Lot clamp 0.01
              │  (REAL-ONLY)     │  No SL/TP if ≤0
              └──────────────────┘
                        │
                        ▼
                 REAL TICKET ✅
```

---

## 📊 Verified Evidence

| Layer | Status | Evidence |
|-------|--------|----------|
| numpy + MT5 import | ✅ FIXED | `env -u PYTHONPATH .venv312/Scripts/python.exe` imports both cleanly (NUMPY 2.1.3 + MT5) |
| PurifiedEngine | ✅ LIVE | MT5 connected LIVE — Valetax 372044706 balance $1122.05 |
| autonomous_cycle | ✅ BOOTS | Entry points verified: LiveEngine starts cleanly, runs cycle |
| REAL-ONLY enforcement | ✅ ACTIVE | `SyncPaperBroker` completely removed. Fails closed (RuntimeError) if MT5 is down |
| Live trade execution | ✅ VERIFIED | Real order tickets: **20188224176** (BTCUSD.vx SELL 0.01) + **20188224713** (BTCUSD.vx BUY 0.01) |
| trade_mode mapping | ✅ FIXED | Fixed check to allow `trade_mode=4` (SYMBOL_TRADE_MODE_FULL on Valetax) |
| Lot calculation | ✅ FIXED | Clamped to broker limits (volume_min/max/step). Min lot 0.01 enforced |
| SL/TP validation | ✅ FIXED | SL/TP omitted if <=0.0 to prevent stops level rejection (BTCUSD.vx stops_level = 2976 points) |

---

## Live MT5 Connection Details

- **Broker:** Valetax International Limited (ValetaxIntl-Live2)
- **Account:** 372044706 (LIVE)
- **Balance:** $1,122.05 | Equity: $1,480.10
- **Trade allowed:** Yes | DLLs allowed: Yes
- **Terminal:** C:\Program Files\MetaTrader 5\terminal64.exe (build 6061)
- **Active Live Positions:** 3 (GBPUSD.vx BUY, BTCUSD.vx SELL, BTCUSD.vx BUY)

---

## Technical Audits & Fixes Applied

1. **pydantic & ccxt dependency gaps:** Installed `pydantic`, `pydantic-settings`, `scipy`, and `ccxt` inside `.venv312`.
2. **Old bridge paper removal:** Removed paper broker checks, environment toggles (`QNA_MT5_LIVE`), and classes (`SyncPaperBroker`) in `engine_production_bridge.py`.
3. **Weekly loss veto:** Integrated risk check limits correctly. Added Sortino-ratio and downside-deviation methods.

---

## What "Autonomous" Means Here

- Code boots end-to-end without human intervention.
- REAL-ONLY mode enforced (no sim/paper/mock fallbacks).
- Live MT5 data flows through strategies → risk → execution.
- Telegram alerts wired for subsystem failures.
