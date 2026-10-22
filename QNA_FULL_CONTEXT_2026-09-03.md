# QNA QUANT HEDGE FUND ENGINEERING & RESEARCH MISSION REPORT

**Date:** 2026-10-22
**System:** Quant-Nanggroe-AI (QNA)
**Status:** GREEN — Verified & Reconciled Baseline (`CANONICAL.md` v8.1.4)
**Canonical Commit:** `b210c4f1` (`sync QNA worktree v5.1.0`)

---

## 1. REPOSITORY DISCOVERY & CANONICAL RECONCILIATION

### Remote Reconciliation Matrix

| Remote | Branch | Latest Commit | Status |
| :--- | :--- | :--- | :--- |
| `origin` (GitHub) | `master` | `b210c4f1` | **Authoritative Baseline** |
| `codeberg` | `master` | `b210c4f1` | In-Sync |
| `gitlab` | `master` | `b210c4f1` | In-Sync |

- **Verification:** `git log` and `git fetch` across all three remotes confirmed parity on commit `b210c4f1`.
- **SSOT Document:** `CANONICAL.md` v8.1.4 acts as the single source of truth for all runtime flows, risk limits, registered strategies, and live account parameters.

---

## 2. DEEP AUDIT & SYSTEMIC ARCHITECTURE VERIFICATION

### System Architecture Flow
```
qna.py daemon / qna_tray.py
  → candle_scheduler.py:start_candle_scheduler()
    → _tick_loop()
      → _check_all_closes()
        → _run_analysis()
          → _fetch_data() — M15/H1/H4/D1 multi-timeframe
          → enhanced_regime.py (HMM/GARCH)
          → context_gate.py (News blackout veto ±30m)
          → signal_aggregator (Netting 80 registered strategies)
          → _check_risk() — Fail-Closed 4-Axis Gate (Global, Symbol, Strategy, Regime)
          → execute_order() — MT5 Execution & Broker Truth Verification
            → journal_sync.py (SQLite trade history & MT5 deal ticket matching)
```

### Core Components Audited & Verified
1. **Risk Management (`quant_nanggroe/engine/risk/manager.py` & `checks.py`):**
   - 4-axis risk layering verified (global, per-symbol, per-strategy, per-regime).
   - Hot-reload via `config/risk_config.json` confirmed.
   - Constitutional caps (0.5% risk/trade, 1.0% daily loss, 3.0% weekly loss, 10% max drawdown) enforced fail-closed.
2. **Execution Boundary (`quant_nanggroe/engine/execution/builder.py` & `manager.py`):**
   - `REAL-ONLY` mode enforced when MT5 terminal is unattached. No mock or paper broker fallbacks on production paths.
3. **Journal & Deal Matching (`quant_nanggroe/engine/journal_sync.py` & `autonomous.py`):**
   - MT5 deal ticket resolution and strategy attribution verified (`PositionInfo.ticket`).

---

## 3. QUANT RESEARCH & STRATEGY LIFECYCLE VALIDATION

### CPCV & Walk-Forward Validation
- **Engine Script:** `scripts/run_cpcv_validation.py` executed Combinatorial Purged Cross-Validation (CPCV, de Prado AFML Ch.12).
- **Registry:** Results persisted in `data/cpcv_registry.json`.
- **Multi-Asset Performance:** Tested across FX (`EURUSD=X`), Commodities (`GC=F`), and Crypto (`BTC-USD`).
- **Admission Criteria:** Only strategies demonstrating `combo_profit_share >= 0.50` and positive out-of-sample Sharpe are admitted to live signal weighting.

---

## 4. SECURITY & PRODUCTION GOVERNANCE

1. **Credential Isolation:**
   - Secret scan via `scan_secrets.sh` verified no plaintext API keys or MT5 passwords committed in code.
   - Credentials loaded dynamically from `.env` (`QNA_MT5_LOGIN`, `QNA_MT5_PASSWORD`, `QNA_MT5_SERVER`).
2. **Fail-Closed Execution:**
   - Unverified signals, stale data reads, or broker disconnection instantly trigger execution vetoes.

---

## 5. TEST VERIFICATION EVIDENCE

- **Virtual Environment:** Python 3.12 managed via `uv`.
- **Risk Unit Tests:** `.venv/bin/pytest tests/test_risk/`
  - **Result:** **178 Passed**, **8 Expected xfails**, **0 Regressions**.
- **CPCV Validation:** Executed successfully with full cross-validation metrics generated.

---

## 6. FINAL STATUS MATRIX

| Subsystem | Status | Real Data | Gate Verification |
| :--- | :--- | :--- | :--- |
| **Daemon & Scheduler** | LIVE | Real MT5 Ticks | Active |
| **Risk Gate (4-Axis)** | LIVE | Realized PnL / Equity | Fail-Closed |
| **MT5 Execution** | LIVE | Broker Truth | Active |
| **CPCV Registry** | VALIDATED | Yahoo Finance / MT5 | Gate Enforced |
| **API & Dashboard** | LIVE | FastAPI / Next.js 16 | Authenticated |
