# Debate Record: Theme 5 — Logging, Monitoring & Auto-Fix

**Date:** 2026-06-28
**Presiding:** Ops Manager (w: 0.8)
**Council:** Perf Analyst (w: 1.0), Risk Analyst (w: 1.0), Dev Lead (w: 1.5)
**Questions:** Q10, Q13

---

## Round 1: Initial Stances

### Ops Manager
- **Q10:** Execution editable via signed configs (versioned runbook commit), not hot-edits. 3-phase portfolio gate (paper→10% shadow→live) requiring 30d paper with Sharpe>0.5, DD<15%, DR drill pass.
- **Q13:** JSONL to paper_state/, 90d paper / 7yr live retention. Auto-fix: non-monetary only. NEVER positions/sizing/kill switch/risk params.
- **Requirements (10):** Runbooks, change management, IR, post-mortems, monitoring, recovery drills, backup, SLA, audit trail, exchange gate.

### Perf Analyst
- **Q10:** Trade-level P&L attribution must stream real-time. Current anomaly_reporter runs synthetic fallback — monitoring is theater.
- **Q13:** Every cycle must persist full attribution. Need OOS decay tracker (live vs backtest Sharpe). PSR evaluation weekly cron.
- **P0:** Wire real P&L attribution pipeline (stop synthetic). **P1:** OOS decay tracker. **P2:** Performance API routes.

### Risk Analyst
- **Q10:** Every execution risk-scored pre-trade and post-trade. Real portfolio needs: correlation matrix intraday, VaR 99%, concentration ratio, trailing stop-loss.
- **Q13:** Every risk decision immutable-logged. Auto-fix: disable on correlation >0.95, reduce exposure >20% NAV, close at -5% in 1h.
- **Priorities:** Corruption-proof risk gates, real-time correlation dashboard, trailing P&L auto-stop.

### Dev Lead
- **Q10:** Already have DataFreshnessMonitor, anomaly_reporter, TradeJournal. Add MonitorHub singleton (~150 lines), 3 FastAPI endpoints.
- **Q13:** Add AuditTrail (~200 lines): JSONL + ring buffer. No DB. Watchdog auto-restart (~50 lines). BrokerFactory ~250 lines (tier-2).
- **P1:** AuditTrail + MonitorHub. **P2:** Watchdog. **P3:** BrokerFactory + dashboard extension.

---

## Round 2: Ops Manager Final Decision

### Logging Scope
JSONL to paper_state/ (no DB). Every cycle: timestamp, strategy, symbol, signal, prices, PnL, regime_at_entry, factor_exposures, slippage_bps. Pre/post-trade risk scores inline. AuditTrail for money-touching actions (append-only JSONL + ring buffer, 1 endpoint). 90d retention paper phase.

### Monitoring Infrastructure
MonitorHub per Dev Lead (~150 lines, 7 metrics, 3 endpoints). Metrics: execution latency, error rate, signal freshness, PnL/cycle, risk scores, correlation snapshot, system health. No real-time dashboards — store to JSONL. OOS decay tracker = cron script, not MonitorHub feature.

### Auto-Fix Scope
**Non-monetary only for paper phase.** Approved: restart daemon, rotate stale data, re-enable feed after cooldown, clear stuck PIDs. Auto-disable on correlation >0.95 accepted (safety gate). **VETOED:** auto-reduce exposure, auto-close trailing loss — monetary auto-fix prohibited in paper phase.

### Ops Process (Paper Phase)
Keep 4 of 10 requirements:
1. Runbook per strategy (1-pager)
2. Signed configs + versioned commit for changes (light CAB)
3. MonitorHub as live monitoring
4. Audit trail on money actions

**Deferred to live gate:** full CAB, DR drills, formal post-mortems, SLA, 7yr retention, formal IR process.

### Priority Ranking
1. **P0:** AuditTrail + MonitorHub per Dev Lead (~350 lines)
2. **P1:** Wire real P&L attribution pipeline (stop synthetic, per-cycle JSONL with full attribution)
3. **P2:** Non-monetary auto-fix: watchdog restart + stale data rotation + PID cleanup (~50 lines)
4. **P3:** OOS decay tracker — cron script comparing live vs backtest Sharpe, weekly alert
5. **P4:** Strategy runbook for RegimeBased (1-pager) + signed config workflow
6. **P5:** Performance/risk FastAPI endpoints (read from JSONL, no DB) — defer post-paper
7. **P6:** Full ops procedures — gate to 10% shadow

### Vetoes
1. **VETO** Risk Analyst's auto-reduce/auto-close — monetary auto-fix prohibited in paper phase
2. **VETO** Database for logging — JSONL + ring buffer sufficient, no PostgreSQL/MongoDB until live gate
3. **VETO** Own 10-item ops requirements in full — 6 of 10 over-engineering for paper daemon
4. **VETO** Real-time streaming dashboard — store JSONL, Grafana can ingest later

---

**Status: COMPLETE**
**Next:** Theme 6 — Multi-Asset & Multi-TF Execution (Q70-Q72)
