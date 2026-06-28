# Debate Record: Theme 7 — Plenary: Sub-Agent Orchestration & 100/100 Gaps

**Date:** 2026-06-28
**Presiding:** CIO (w: 2.5, Veto ALL)
**Council:** ALL 12 ROLES (Full Plenary)
**Questions:** Q8, Q9, Q63

---

## Round 1: All 12 Role Inputs

### CIO
- **Q8 Workflow:** SURVEY → COUNCIL → VOTE → EXECUTE → REVIEW → REPORT. 6 functional clusters. Chinese Wall at every handoff.
- **Q9 Hierarchy:** Tier 0 CIO (w:2.5 veto ALL) → Tier 1 PM (w:2.0 veto STRATEGY) + CRO (w:2.0 veto HALT) → Tier 2 Compliance (w:1.0 veto BLOCK) → Tier 3 QR/QDev/DevLead/QT → Tier 4 RiskAnalyst/DataEng/PerfAnalyst/OpsMgr.
- **Q63 Gaps:** 42→100 = 58 points. Zero alpha with positive OOS (0/30). Zero live execution (0/20). Data coverage 62%. Council not wired. Security Chinese Wall absent. Dashboard static. Ops no 30-day run. **6 months of real-market work.**

### PM
- **Q63 Gaps:** Alpha 16→30 requires complete strategy stack rewrite. Abandon 7 failing TA strategies. Build ML pipeline (XGB/LightGBM ensemble). Add intraday frequency. Alternative data (exchange flow, on-chain, sentiment). Cross-asset factor model.

### QR
- **Q63 Gaps:** Alternative data pipeline, execution research, macro regime classifier, sentiment NLP for Indonesian market, experiment tracking (MLflow), factor risk model for IDX, data quality automation.

### QDev
- **Q63 Gaps:** ALPHA=0/30 confirmed. Exchange keys missing. Coverage 62%. ML blocked on aarch64. Dashboard static. 30-day run pending. **Core truth: alpha first, everything else is decoration.**

### CRO
- **Q63 Gaps:** 7 gaps (13→20): regime-adaptive sizing unwired, cost-aware budget not in RiskManager, concentration limits not enforced, auto-rotation missing, regime adaptation not wired, tuning pipeline broken, anomaly reporter standalone.

### Risk Analyst
- **Q63 Gaps:** Real-time correlation breakdown, liquidity regime classification, execution vs backtest slippage, model overfitting decay (walk-forward tracking).

### Compliance
- **Q63 Gaps:** 10 steps to 10/10: CI secret scanning, trade surveillance, concentration limits, cost-aware budget, encrypted journal, multi-sig LEVEL_3, JWT rotation, regime_state persistence, clean test keys, encryption at rest.

### Dev Lead
- **Q63 Gaps:** Code quality 12→15 via mypy strict + dead code deletion (+3 pts). Real gap is alpha, not infra. 69→100 requires alpha validation (30 pts).

### Data Engineer
- **Q63 Gaps:** 6 gaps: no WebSocket, no data warehouse (Parquet), no feature store, no data validation, no backfill, no L2 data.

### QT
- **Q63 Gaps:** 15 gaps listed. **Core truth: 69 is honest, 31 missing points are execution-blocked not architecture-blocked.**

### Ops Manager
- **Q63 Gaps:** 10 gaps: unexercised checklist, no alerting, no measured RTO/RPO, no CI/CD, no incident management, no resource monitoring, no config drift detection, no SLA, fragmented CLIs, static dashboard.

### Perf Analyst
- **Q63 Gaps:** 11 gaps: zero alpha, no perf warehouse, no real-time dashboard, no portfolio attribution, no execution analytics, no benchmark, no live risk analytics, no automated reports, no A/B testing, coverage 60%, no exchange keys.

---

## Round 2: CIO Final Master Execution Queue (47 Items)

### P0 — Blockade (Weeks 1-3, must finish before anything else)
1. Kill 7/8 strategies — keep only RegimeBased
2. Fix RegimeBased walk-forward OOS validation (target ≥3/8 pass)
3. Replace simulated DataProvider with real data pipeline
4. Implement ATR trailing stop (2.5x) — replace all HH/HL/breakeven
5. Deploy live risk management layer (stop-loss, position sizing, drawdown kill switch)
6. Wire live exchange API keys (Alpaca paper first)
7. Start 30-day uninterrupted paper run with RegimeBased

### P1 — Critical Path to 100/100 (Weeks 3-8, parallelized during paper run)
8. Deploy dedicated Risk Agent + Compliance Agent (7-agent formal structure)
9. Wire 12 sub-agent council into live decision loop
10. Build CI/CD pipeline with compliance sign-off gate
11. Implement agent-level Chinese Wall
12. Scale data coverage 60% → 90%+ (more symbols, WebSocket, L2)
13. Build data warehouse (Parquet, partitioned, versioned)
14. Wire real P&L attribution pipeline (stop synthetic)
15. Build AuditTrail + MonitorHub (~350 lines)
16. Performance dashboard (live P&L, drawdown, Sharpe)
17. Security hardening (secret scanning CI, multi-sig LEVEL_3, encryption at rest)
18. Clean 68 HIGH placeholder API keys in test files
19. Automated KYC/AML pipeline
20. Incident response runbook + health monitoring dashboard
21. AlpacaExecutor (config file, no UI) — after 30-day paper validation
22. Kill mock data — wire api-client to real WebSocket stream
23. Strategy on/off toggle + real-time P&L + exposure UI panels
24. Non-monetary auto-fix (watchdog, stale data rotation, PID cleanup)
25. OOS decay tracker (cron, live vs backtest Sharpe, weekly alert)
26. Establish per-asset risk budgets with hard stop at entry
27. Strategy registry with walk-forward framework
28. Factor regression framework + bootstrap CIs on Sharpe
29. Strategy runbook for RegimeBased (1-pager)
30. Aggregated portfolio view (top 5 ±P&L, concentration)
31. Implement 2 uncorrelated paper strategies from 151 catalog (momentum, mean reversion)
32. Enforce concentration limits + cost-aware budget in RiskManager

### P2 — Important Expansion (Weeks 8-12)
33. Performance/risk FastAPI endpoints (read from JSONL)
34. Full ops procedures (CAB, DR drills, SLA, formal IR)
35. Build correlation regime detector + cross-asset margin monitoring
36. Phase 2 multi-asset: second asset with per-asset budgets + 30-day paper
37. Penetration test sign-off
38. Paper completion gate (30-day clean run → live transition approval)
39. Fixed-grid layout with column visibility presets
40. Phase 2: second asset in separate sub-account

### P3 — Post-100 / Nice to Have (Weeks 12-16)
41. Pair-level drill-down + lightweight-charts integration
42. Phase 3: full multi-asset rollout
43. IC Markets executor (if forex strategies survive validation)
44. MT5/4 bridge (only if client contract requires)
45. ML pipeline + alternative data ingestion
46. Intraday frequency research (separate sub-account, 60-day validation)
47. CSV export

---

## Summary

| Metric | Value |
|--------|-------|
| Total items | 47 |
| P0 (blockade) | 7 |
| P1 (critical path) | 25 |
| P2 (expansion) | 7 |
| P3 (post-100) | 8 |
| Estimated duration | 12-16 weeks |
| Key milestone 1 | RegimeBased passes walk-forward + live API key (Week 3) |
| Key milestone 2 | Sub-agent council wired + AuditTrail live + CI/CD (Week 6) |
| Key milestone 3 | 30-day clean paper run completed (Week 8) |
| Key milestone 4 | 100/100 scorecard achieved (Week 12-16) |

---

**CIO Closing Statement:**
> "This is not a wishlist. This is the sequence. P0 is the blockade — nothing of value happens until RegimeBased survives walk-forward and a real API key touches a real exchange. P1 is the spine of the 100/100 score — every item removes a failure mode. P2 and P3 are decoration on a house that does not yet have a foundation. The council spoke. I listened. I vetoed the distractions. Now execute the queue in order."

**Status: COMPLETE — All 7 themes debated, master queue compiled.**
