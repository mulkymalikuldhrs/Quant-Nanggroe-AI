# Hedge Fund Council Debate — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use godmode:delegated-execution to implement this plan task-by-task.

**Goal:** Deploy 12 OpenCode sub-agents role-playing a complete hedge fund team to debate 72 questions from `/root/qna-debat.txt`, produce ranked priority decisions, and implement top-priority outcomes to push QNA from 69/100 → 100/100.

**Architecture:** Sequential theme councils (3-5 relevant roles per theme) → Full plenary weighted vote → Priority-ranked execution queue. Each theme produces a `.md` decision record. Execution uses delegated sub-agents per decision item.

**Tech Stack:** OpenCode Task sub-agents (role-playing hedge fund positions). Source: `/sdcard/dhaherlabs/repositories/Quant-Nanggroe-AI-worktree`. Records: `docs/debates/`.

**State:** v4.3.4 — 1642/1642 tests pass (100%), Composite 69/100. 0/8 strategies have positive OOS Sharpe.

---

## Phase 0: Arena Setup (before any debate)

**Goal:** Prepare the debate infrastructure — persona briefs, theme grouping, record templates.

### Step 1: Create debate records directory

```bash
mkdir -p /sdcard/dhaherlabs/repositories/Quant-Nanggroe-AI-worktree/docs/debates/
```

### Step 2: Create 12 persona brief files

Each persona gets a `.md` file defining:
- Role, weight, veto power
- Key metrics they care about
- Their "personality" (skeptical, ambitious, conservative, etc.)
- What questions to prioritize
- Their known stance based on current QNA state

Files: `docs/debates/persona-{role}.md` for all 12 roles.

### Step 3: Group 72 questions into 7 themes

The 72 questions from `/root/qna-debat.txt` grouped into coherent themes:

| # | Theme | Questions | Lead | Support |
|---|-------|-----------|------|---------|
| 1 | **Hedge Fund Structure & Org** | Q1-4 — posisi, tugas, peran | CIO | PM, Ops, Compliance |
| 2 | **Strategy Research & Alpha** | Q15-19 — arxiv, holy grail, research.md | QR | QDev, PM, CIO |
| 3 | **UI Architecture & Visualization** | Q5-7, Q14, Q43-61 — wiring, dragable, toggle, all pairs | Dev Lead | QT, DE, PM |
| 4 | **Broker API & MT5/4 Bridge** | Q11 — broker integration, EA bridge | Dev Lead | DE, QT, Compliance |
| 5 | **Logging, Monitoring & Auto-Fix** | Q10, Q13 — track record, eval, auto-fix | Ops Mgr | Perf Anal, Risk Anal |
| 6 | **Multi-Asset & Multi-TF Execution** | Q70-72 — forex/crypto/saham, swing/intraday/scalping, trailing | PM | QT, QR, CRO |
| 7 | **Sub-Agent Orchestration** | Q8-9, Q63 — overall workflow, keputusan, 100/100 gaps | CIO | All roles |

### Step 4: Create vote recording template

```markdown
## Decision Record: [Theme]
**Date:** 2026-06-28
**Presiding:** [Lead Role]

### Question: [Question text]

**Positions:**
- [Role]: [pro/con + reasoning]
- [Role]: [pro/con + reasoning]

**Counter-arguments:**
- [Role]: [rebuttal]

**Vote:**
- For: [roles, total weighted score]
- Against: [roles, total weighted score]
- Veto: [if applicable]

**Decision:** [PASS/FAIL/BLOCKED]
**Priority:** [HIGH/MEDIUM/LOW]

**Action items:**
1. [ ]
2. [ ]
```

---

## Phase 1: Theme Councils (7 sequential debates)

Each theme is one debate session with a subset of 3-5 relevant sub-agents.

### Debate Protocol Per Theme

```
┌─────────────────────────────────────────────┐
│ 1. BRIEF    — Present question(s) to council │
│ 2. STANCE   — Each role states initial view  │
│ 3. DEBATE   — Pro/con exchange (min 2 rds)   │
│ 4. REBUT    — Cross-examine counter-args      │
│ 5. VOTE     — Weighted roll call              │
│ 6. RECORD   — Decision + action items         │
└─────────────────────────────────────────────┘
```

### Theme 1: Hedge Fund Structure & Org

**Sub-agents:** CIO (lead), PM, Ops Manager, Compliance
**Questions:** Q1-Q4
**Output:** `docs/debates/01-structure-and-org.md`

Key debate points:
- Q1: Berapa orang dan posisi di hedge fund / quant?
- Q2: Perusahaan seperti Renaissance — berapa posisi?
- Q3: Ritel trader — peran dan tugas?
- Q4: Developer hedge fund — tim dan tugas?

**Decision output:** Updated role definitions for QNA sub-agents. Org chart finalization.

### Theme 2: Strategy Research & Alpha

**Sub-agents:** QR (lead), QDev, PM, CIO
**Questions:** Q15-Q19
**Output:** `docs/debates/02-strategy-research.md`

Key debate points:
- Q15: `/sdcard/dhaherlabs/docs/research/quant.md` — apa isinya, apa yang bisa diambil?
- Q16: Cari strategy nyata yang dipakai quant / hedge fund
- Q17: Arxiv research → backtest → fine-tune → buang yang jelek
- Q18: Generate holy grail strategy — pattern recognition, ML, super strategy
- Q19: Lain-lain?

**Decision output:** Research pipeline, strategy candidates, holy grail approach. Priority ranking.

### Theme 3: UI Architecture & Visualization

**Sub-agents:** Dev Lead (lead), QT, Data Engineer, PM
**Questions:** Q5-Q7, Q14, Q43-Q61
**Output:** `docs/debates/03-ui-architecture.md`

Key debate points:
- Q5: Wiring di UI — bagaimana?
- Q6: Dragable UI — perlu?
- Q7: Semua implementasi ada di UI?
- Q14: Semua pair di UI (saham, crypto, forex positions)?
- Q43-Q61: Keseluruhan usulan UI — chart, indikator, toggle, sumber data, API, LLM, custom URL, broker connections, MCP, export, dsb.

**Decision output:** UI architecture decisions, component priority, wiring plan.

### Theme 4: Broker API & MT5/4 Bridge

**Sub-agents:** Dev Lead (lead), Data Engineer, QT, Compliance
**Questions:** Q11
**Output:** `docs/debates/04-broker-api.md`

Key debate points:
- Q11: Integrasi broker API lewat UI? Configurable? Bridge ke MT5/4 via EA?
- Security implications (Compliance)
- Execution latency (QT)
- Data pipeline (Data Engineer)

**Decision output:** Broker integration approach, MT5/4 bridge architecture, security requirements.

### Theme 5: Logging, Monitoring & Auto-Fix

**Sub-agents:** Ops Manager (lead), Perf Analyst, Risk Analyst, Dev Lead
**Questions:** Q10, Q13
**Output:** `docs/debates/05-logging-monitoring.md`

Key debate points:
- Q10: Eksekusi editable? Monitored? Tersambung real portfolio?
- Q13: Semua tercatat untuk evaluasi? Visible di UI? Auto-fix?

**Decision output:** Logging architecture, monitoring dashboard, auto-fix protocol.

### Theme 6: Multi-Asset & Multi-TF Execution

**Sub-agents:** PM (lead), QT, QR, CRO
**Questions:** Q70-Q72
**Output:** `docs/debates/06-multi-asset-execution.md`

Key debate points:
- Q70: Trading multi-asset — forex, crypto, saham bersamaan?
- Q71: Swing, investing, intraday, scalping — how to combine?
- Q72: Break even, trailing stop based on structure (HH/HL) or ATR?

**Decision output:** Multi-asset architecture, timeframe orchestration, stop management.

### Theme 7: Sub-Agent Orchestration & 100/100

**Sub-agents:** CIO (lead), ALL ROLES (plenary)
**Questions:** Q8, Q9, Q63
**Output:** `docs/debates/07-orchestration.md`

Key debate points:
- Q8: Cara kerja keseluruhan — bagaimana workflow?
- Q9: Setelah semua sub-agent punya peran — keputusan apa yang tepat?
- Q63: Apa yang kurang untuk 100/100 dari semua aspek?

**Decision output:** Final orchestration model, decision hierarchy, gap analysis for 100/100.

---

## Phase 2: Plenary Vote & Priority Ranking

After all 7 themes produce decisions, convene the **Full Council** (all 12 roles) to:

1. Review all decisions from all themes
2. Vote on **priority ranking** of all action items
3. Resolve any cross-theme conflicts
4. Produce final **execution queue**

### Priority Ranking Formula

```
Score = (Strategic Value × 0.3) + (Urgency × 0.25) + (Feasibility × 0.2) + (Impact on 100/100 × 0.25)

Where each dimension is scored 1-10 by each sub-agent.
Weighted average by role weight.
```

### Output: Execution Queue

```markdown
## Execution Queue — Ranked Priority

| Rank | Item | Theme | Score | Assigned To | Est. Effort |
|------|------|-------|-------|-------------|-------------|
| 1    | ...  | ...   | ...   | ...         | ...         |
| 2    | ...  | ...   | ...   | ...         | ...         |
```

File: `docs/debates/execution-queue.md`

---

## Phase 3: Execution (per priority item)

Each item in the execution queue follows the standard lifecycle:

```
TASK BRIEF → SUB-AGENT → IMPLEMENT → REVIEW → COMMIT
```

Using delegated execution (open code Task sub-agents) per item.

### Verification

Each execution step must:
1. Run relevant tests (`pytest tests/...`)
2. Update scorecard (`docs/100_100_AUTONOMOUS.md`)
3. Commit (`git commit -m "feat: ..."`)

---

## Timeline Estimate

| Phase | Est. Agent Calls | Est. Tokens | Est. Time |
|-------|-----------------|-------------|-----------|
| Arena Setup | 0 | ~2K | 5 min |
| Theme 1: Structure | 4 | ~15K | 10 min |
| Theme 2: Strategy | 4 | ~20K | 15 min |
| Theme 3: UI | 4 | ~25K | 15 min |
| Theme 4: Broker | 4 | ~15K | 10 min |
| Theme 5: Logging | 4 | ~15K | 10 min |
| Theme 6: Multi-Asset | 4 | ~15K | 10 min |
| Theme 7: Plenary | 12 | ~30K | 20 min |
| Priority Ranking | 12 | ~20K | 10 min |
| Execution (per item) | 1-3 each | ~10-50K each | 10-30 min each |

**Total: ~48+ sub-agent calls, ~170K+ tokens for debate phase**

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Token limits hit mid-debate | Each theme is independent; breakpoints natural |
| Agents contradict prior decisions | All prior `.md` records loaded as context |
| Debate stalls on deadlock | CIO has veto (2.5), can force decision |
| Too many action items | Priority ranking filters to top 3-5 per theme |
| Sub-agent context drift | Each call is fresh — persona brief reloaded |
