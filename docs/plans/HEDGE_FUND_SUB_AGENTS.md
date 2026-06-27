# Hedge Fund Sub-Agent System — QNA 100/100 Plan

> **Goal:** Build 12 OpenCode sub-agents role-playing a complete hedge fund team,
> collaborating to push QNA from 45/100 → 100/100 on the autonomous scorecard.

---

## Team Structure

```
ORCHESTRATOR (main session)
├── EXECUTIVE     CIO, PM
├── QUANT         QR, QDev
├── RISK          CRO, Risk Analyst, Compliance
├── ENGINEERING   Dev Lead, Data Engineer
├── TRADING       QT
└── OPERATIONS    Ops Manager, Perf Analyst
```

## Lifecycle Per Cycle

```
SURVEY → COUNCIL → VOTE → EXECUTE → REVIEW → REPORT
```

## Voting Weights

| Role | Weight | Veto | Focus |
|------|--------|------|-------|
| CIO | 2.5 | ✅ All | Strategy, capital allocation |
| PM | 2.0 | ✅ Strategy | P&L, portfolio mix |
| QR | 1.5 | ❌ | Alpha, factors, backtest |
| QDev | 1.2 | ❌ | Implementation, pipeline |
| CRO | 2.0 | ✅ Halt | Systemic risk, VaR |
| Risk Analyst | 1.0 | ❌ | Correlation, monitoring |
| Compliance | 1.0 | ✅ Block | Security, credentials |
| Dev Lead | 1.5 | ❌ | Architecture, quality |
| Data Engineer | 1.0 | ❌ | Pipeline, real data |
| QT | 1.2 | ❌ | Execution, slippage |
| Ops Manager | 0.8 | ❌ | Procedures, DR |
| Perf Analyst | 1.0 | ❌ | P&L attribution, tracking |

## Phases

| Phase | Cycles | Target | Focus |
|-------|--------|:------:|-------|
| Foundation | 1-2 | 45→65 | Security, ops, audit, debug |
| Quick Wins | 3-4 | 65→80 | Walk-forward, orphans, correlation |
| Deep Work | 5-8 | 80→95 | Real data, fix strategies, CLI, coverage |
| Polish | 9-10 | 95→100 | mypy, capital policy, final |
