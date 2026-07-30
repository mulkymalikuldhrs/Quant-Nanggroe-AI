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

## 🧬 E:\ Integration — 12-Agent Council Plan (2026-07-31)

**136 jam / 4-6 minggu** — Port TradeBobbyTerminal + OrderFlowMap ke QNA pipeline.

| Phase | Hours | Deliverable |
|-------|-------|-------------|
| Phase 0 — Pre-work | 8h | Delete dead code, dedup signal/registry/COT |
| Phase 1 — Week 1 | 24h | 5 Python providers + pipeline wiring |
| Phase 2 — Week 2 | 32h | 9 dashboard panels + risk gates + evolution |
| Phase 3 — Week 3 | 40h | 80% tests + alerts + data quality |
| Phase 4 — Future | 32h | Node sidecars + multi-account + backtest |

Lihat `docs/Rencana.md` untuk detail lengkap.