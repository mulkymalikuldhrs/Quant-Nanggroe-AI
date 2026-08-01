# QNA Autonomous Loop Goal — Evidence-Based

**Created:** 2026-08-01 | **Author:** DHAHER OS (autobot, non-yesman mode)
**Principle:** NO CLAIM WITHOUT EVIDENCE. Verify every layer before declaring autonomous.

---

## VERIFIED FACTS (from direct execution, not agent summaries)

| Layer | Status | Evidence |
|-------|--------|----------|
| Import root | ✅ OK | `import quant_nanggroe` → IMPORT_OK |
| ExecutionManager | ✅ OK | `from engine.execution.manager import ExecutionManager` → MGR_OK |
| autonomous_cycle | ✅ FIXED | Was NameError `log` + missing `initialize()` → now CYCLE_OK, run_cycle() works |
| api/app | ✅ OK | `from api.app import app` → APP_OK (slow ~25s load) |
| 1 cycle (paper) | ✅ OK | Cycle #1: Engine PAPER, balance $10000, risk OK |
| Forced trade | ✅ OK | ticket 690369 EURUSD buy lot 11.36 mode=paper |
| MT5 terminal | ⚠️ DETECTED | `C:\Program Files\MetaTrader 5\terminal64.exe` (auto-path works) |
| Live connect | ❌ NOT TESTED | No credentials, no saldo, mode=PAPER only |
| EncryptedStore | ⚠️ DISABLED | Plaintext persistence (security gap for live) |
| AuthManager | ⚠️ NOT WIRED | `AuthManager not available` at boot |

---

## SUB-GOALS (prioritized, evidence-gated)

### SG-1: Live MT5 Connect (BLOCKER for real trading)
- **Current:** mode=PAPER, terminal detected but not connected
- **Action:** Wire MT5 login from `config/mt5_accounts.yaml` (credentials quarantined at `C:\Users\Hi\.qna-secrets\`)
- **Verify:** `engine.mt5._initialized == True` + real tick from `symbol_info_tick('EURUSD')`
- **Evidence required:** Live tick data, not simulated

### SG-2: Encryption at Rest (SECURITY)
- **Current:** EncryptedStore DISABLED, plaintext persistence
- **Action:** Set `QNAI_ENCRYPTION_KEY`, enable EncryptedStore
- **Verify:** persistence files encrypted, not plaintext JSON
- **Evidence required:** `grep -L 'ENCRYPTED' data/persistence/*.json` returns nothing

### SG-3: Auth Manager (SECURITY)
- **Current:** AuthManager not available
- **Action:** Wire AuthManager ke API routes (JWT sentinel already exists per council)
- **Verify:** `/api/trading/*` requires valid token
- **Evidence required:** 401 without token, 200 with token

### SG-4: Real Signal Flow (FUNCTIONAL)
- **Current:** 0 trades from synthetic data (expected — no real market structure)
- **Action:** Connect live MT5 → real candles → strategies generate real signals
- **Verify:** `run_cycle()` produces ≥1 real signal in 10 cycles on live data
- **Evidence required:** Real signal log, not forced

### SG-5: Kill-Switch + SL/TP Live Verify (SAFETY)
- **Current:** Wired (manager.py pull PnL, mt5_broker attach SL/TP) but NOT tested on live
- **Action:** Dry-run on MT5 demo: execute 1 trade, confirm SL/TP attached, confirm kill-switch trips on simulated loss
- **Verify:** `order.sl != 0.0` in MT5 terminal, kill-switch `can_trade()==False` after loss
- **Evidence required:** MT5 terminal screenshot / deal history

### SG-6: Continuous Loop + Monitoring (AUTONOMY)
- **Current:** `run()` exists but gak di-test long-running
- **Action:** Run `autonomous_cycle.run()` 1 hour on demo, monitor Telegram alerts
- **Verify:** No crash, Telegram alert on any subsystem fail
- **Evidence required:** 1h uptime log + Telegram message received

---

## LOOP GOAL (autobot cron, every 30 min)

```
LOOP QNA-AUTONOMOUS-VERIFY:
1. Import check: quant_nanggroe + autonomous_cycle + api.app → all OK?
2. If import fails → fix + commit + alert
3. Run 1 paper cycle → components init? trade logic alive?
4. If cycle fails → read error, fix, commit, alert
5. Check MT5 live connect (if credentials present) → real tick?
6. If live: verify SL/TP + kill-switch on 1 demo trade
7. Graphify: record state
8. Report: status (GREEN/YELLOW/RED) + evidence
```

**Exit criteria for "AUTONOMOUS":**
- ✅ All imports OK
- ✅ 1 cycle runs without exception
- ✅ ≥1 real trade on demo with SL/TP attached
- ✅ Kill-switch trips on simulated loss
- ✅ Telegram alert fires on subsystem fail
- ✅ Encryption + Auth enabled

**Current verdict:** 🟡 YELLOW — code autonomous-ready (paper), but live path UNVERIFIED. Not "tinggal isi saldo" — needs SG-1/2/3 before live.

---

## ANTI-YESMAN NOTES
- "100/100 GREEN" claim was PREMATURE — autonomous_cycle was BROKEN (NameError + missing init).
- Agents reported "wired Telegram alert" but autonomous_cycle couldn't even import.
- Real verification (this session) found + fixed 2 critical bugs in entry point.
- Live trading requires SG-1 (credentials) which needs USER action (saldo + MT5 login).
- Gue gak bisa declare GREEN sampai SG-1/2/3 verified dengan evidence nyata.
