# Debate Record: Theme 1 — Hedge Fund Structure & Organization

**Date:** 2026-06-28
**Presiding:** CIO (w: 2.5)
**Council:** PM (w: 2.0), Ops Manager (w: 0.8), Compliance (w: 1.0)
**Questions:** Q1-Q4 from `/root/qna-debat.txt`

---

## Round 1: Initial Stances

### CIO
- **Q1:** Hedge fund kecil butuh 5-7 orang. QNA terlalu ramping — kekurangan risk dan execution. RegimeBased Sharpe 3.704 tidak bisa dimonetisasi tanpa eksekusi live.
- **Q2:** RenTech 300+ orang, 90 PhD. QNA punya 0/8 strategy profitable OOS. Kita butuh 1 orang fokus RegimeBased.
- **Q3:** Ritel trader = user. Tugas: masuk modal, set risk tolerance, nonton dashboard. QNA harus auto-deploy, auto-rebalance, auto-report.
- **Q4:** Developer prioritas: pipeline data, execution engine, monitoring. QNA punya 18.816 rows dari 7 simbol — perlu 50+ simbol dan coverage 90%+.
- **Priorities:** Produksikan RegimeBased, rekrut risk/ops person, fix coverage 62%→85%.
- **Veto concerns:** Veto strategi baru sebelum RegimeBased running 30 hari. Veto refactor tanpa alasan. Veto ensemble semua strategi sama rata.

### PM
- **Q1:** 15-50 orang. QNA has 0 people — all agents. Edge but bottleneck.
- **Q2:** RenTech ~300, 100+ PhDs. They'd kill 7 of 8 QNA strategies.
- **Q3:** Ritel trader has no research pipeline, no risk system, no edge.
- **Q4:** QNA has 2 providers, 7 symbols, 60% coverage — one Citadel dev handles more.
- **Priorities:** Kill 7/8 strategies, scale data 60→90%+, build multi-asset execution infra.
- **Veto:** New strategies without 12-month OOS Sharpe >1.0. Multi-asset before single-asset bulletproof.

### Ops Manager
- **Q1:** 10-15 peran inti. Separation of duties critical.
- **Q2:** RenTech ~300 — very lean. Documentation and process > headcount.
- **Q3:** Ritel trader = one person doing ALL roles — dangerous. No separation of duties, no runbook, no audit trail.
- **Q4:** Developer covers system dev, data, research platform, monitoring, ops automation. Must enforce code review, staging, canary, rollback.
- **Priorities:** Automate OPS checklist into CI/CD. Build incident response runbook. Add health checks + alerting dashboard.
- **Gaps:** Paper daemon lacking recovery procedures. No formal change management. No post-mortem process.

### Compliance
- **Q1:** 15-50 orang. QNA missing dedicated risk officer + ops.
- **Q2:** RenTech ~300, ~90 PhDs, ~50 SWE. Each team has compliance liaison — we don't.
- **Q3:** Ritel trader = LPs. Must ensure qualified investors, KYC/AML, sanctions screening.
- **Q4:** Dev must be isolated from strategy (Chinese Wall). Code must not log credentials.
- **Priorities:** Hire dedicated risk officer + ops. Implement Chinese Wall. Automated KYC/AML.
- **Block:** Deployment without CI/CD sign-off. Hardcoded credentials. Sharing strategy code without access logs.

---

## Round 2: CIO Final Decision (Weight 2.5, Veto All)

### Org Structure Decision
Formalize **7 agent roles** with strict isolation boundaries:
1. **PM Agent** — strategy selection, portfolio construction
2. **Quant Research Agent** cluster — agents isolated from each other (Chinese Wall)
3. **Quant Developer Agent** — CI/CD, infra, monitoring
4. **Execution/Trading Agent** — order routing
5. **Risk Agent** — independent from PM/Research (NEW)
6. **Compliance Agent** — KYC/AML, access logs, policy enforcement (NEW)
7. **Data Pipeline Agent** — coverage, cleaning, normalization

QNA's agent-based model is a structural advantage for separation of duties IF formalized. No human hires — deploy agent instances.

### Strategy Policy
- **Kill all 8 active strategies from the live book.** Zero exceptions.
- Keep ONE incubation track (paper-only, max 2 strategies) with hard gate: **12-month OOS Sharpe >1.0** or automatic termination.
- Surviving strategies may replace weakest performer in live book.

### Priority Ranking
1. Kill 7/8 strategies — free compute, data, attention bandwidth
2. Deploy dedicated Risk Agent + Compliance Agent
3. Scale data coverage 60% → 90%+
4. Build CI/CD pipeline with compliance sign-off gate
5. Implement agent-level Chinese Wall (agent isolation, access logs)
6. Build incident response runbook + health monitoring dashboard
7. Automated KYC/AML pipeline
8. Multi-asset execution infra — STRICTLY gated behind single-asset proof

### Vetoes (Non-Negotiable)
1. **VETO:** Multi-asset execution before single-asset books prove 12-month OOS Sharpe >1.0
2. **VETO:** Hardcoded credentials in any code, any environment — zero tolerance, instant rollback
3. **VETO:** Deployment without CI/CD pipeline sign-off — no hotfix exception

---

**Status: COMPLETE** — decisions recorded, actionable items defined.
**Next:** Theme 2 — Strategy Research & Alpha (Q15-Q19)
