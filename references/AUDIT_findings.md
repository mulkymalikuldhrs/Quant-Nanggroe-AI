Security Audit Findings Summary (QNA v15.3)

1. CRITICAL CREDENTIAL EXPOSURE
   - mt5_broker.py exposes raw parameters: login, password, server
   - Parameters should be injected from secure secret manager
   - FIX: Remove hardcoded params, implement env/.env loading

2. KILL SWITCH DESIGN FLAW
   - Dead code gate bypasses daily/weekly loss checks
   - MAX_DRAWDOWN disables early warning buffer
   - Current thresholds require manual reset before trading resumes
   - IMPACT: System shows VETOED but operates without protection

3. PHANTOM KILL SWITCH (P1-26 GAP)
   - Engine reads only realized P&L, ignores open position losses
   - During live crash, daily_pnl stays 0.0 → permanent passive veto forever
   - Fix requires injecting MT5 handle for mark-to-market updates

4. FULL AUDIT DOCUMENTATION:
   - File: references/live-trading-reachability.md
   - Covers:
     * MT5_PSUDO _liveness check
     * Pseudo MT5 API validation for secrets
     * Dead code detection patterns
     * Kill switch live-readiness verification

Standard: All findings limited to <5 lines in final report

---


---

> **SSOT:** `CANONICAL.md` v8.0.21 — BAL $1,445, weekly 0 WIB, probe 0/32, CPCV 207, vector 6 modul live
