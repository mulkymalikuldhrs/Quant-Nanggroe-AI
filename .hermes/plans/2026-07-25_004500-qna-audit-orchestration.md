# QNA v5.1.0 — Comprehensive Audit Plan

> **Orchestrator:** @dhaherautobot
> **Bot Team:** @dhaherdevbot · @dhaherhackerbot · @dhahertraderbot · @dhaherresearchbot · @dhaherfangbot
> **Communication Protocol:** Only @dhaherautobot may @mention other bots. Others only mention @dhaherautobot when task needs orchestration. No cross-bot @mentions.
> **Status:** 📋 Plan — awaiting approval

**Goal:** Conduct full adversarial audit of Quant-Nanggroe-AI v5.1.0 across 6 domains — architecture, code quality, security, execution, risk, documentation — producing a verified bill of health with all findings, severity, and remediation steps.

**Current State Snapshot:**
| Metric | Value |
|--------|-------|
| Version | v5.1.0 (git tag v15.3.0) |
| Python files | 756 in `quant_nanggroe/` |
| Test files | 167 in `tests/` |
| Exchange modules | 15 (MT5, Alpaca, IBKR, CCXT, Paper, Polymarket, Solana) |
| Strategy files | 147 total |
| Engine subdirs | 32 directories |
| Docs | 57 `.md` files |
| hedge_fund.py root | 13,684 lines |
| hedge_fund.py package | 7,036 lines (execution, portfolio, risk, signals, utils) |
| Claimed tests pass | 492/493 core, 112/112 risk, 94/94 fast |
| Known failures | 541 pre-existing in `test_factors.py` import cascade |

**Bot Roles:**
| Bot | Lens | Audit Domain |
|-----|------|-------------|
| @dhaherautobot | Orchestrator | Overall coordination, final report |
| @dhaherdevbot | Backend/Fullstack | Code quality, test suite, structure, duplication |
| @dhaherhackerbot | Security Analyst | Secrets, gates, fail-closed, attack surface |
| @dhahertraderbot | Quant Finance | Execution pipeline, risk gates, P&L, MT5 |
| @dhaherresearchbot | Research/Innovation | Architecture consistency, docs sync, strategy validity |
| @dhaherfangbot | OpenFang Specialist | Optimization, integration, bottlenecks |

---

## Phase 0 — Orchestration Setup

**Task 0.1** — Define bot communication protocol
- Protocol file: `docs/51_BOT_ORCHESTRATION.md`
- @dhaherautobot is sole orchestrator
- Tasks delivered as structured work orders (markdown)
- Each bot responds with: finding + evidence + recommendation
- No bot @mentions another bot directly

**Task 0.2** — Create audit tracking board
- `audit/` directory with per-domain worksheets
- Each finding gets: ID, domain, severity (CRITICAL/HIGH/MEDIUM/LOW/INFO), status, evidence file:line

**Task 0.3** — Establish reporting cadence
- Each bot reports findings back to @dhaherautobot
- Orchestrator consolidates into unified report
- Final deliverable: `AUDIT_QNA_v5.1.0_FINAL.md`

---

## Phase 1 — Architecture & Structure Audit

**Domain Lead:** @dhaherresearchbot
**Verification Lead:** @dhaherdevbot

### Scope:
1. **Entry point verification** — AGENTS.md claims `qna.py` is sole entry point. Verify: no other entry paths exist.
2. **Split-brain resolution** — Previous audit (v4.5.9) found `engine/` (177 files) nested inside `quant_nanggroe/`. Is this resolved or still present?
3. **Module dependency direction** — Verify no circular imports or upward dependency violations.
4. **Directory purpose mapping** — All 32 engine subdirs must have clear defined purpose. Flag zombie directories.
5. **File size audit** — Flag files > 1000 LOC for splitting. Known: `hedge_fund.py` (13,684 lines root + 6,536 lines package).
6. **Duplicate class detection** — Known: 10 overlapping classes (Signal×7, Position×6, StrategyType×5). Map all duplicates.
7. **AutoRegistry v3 validation** — Does it actually scan all 756 files? Verify registration completeness.

**Files to inspect:**
- `qna.py`, `quant_nanggroe/cli.py`, `quant_nanggroe/api/app.py`
- `quant_nanggroe/engine/` directory tree
- `quant_nanggroe/hedge_fund/` structure
- `strategy_registry.py`, `quant_nanggroe/engine/registry.py`

**Verification:**
- [ ] Entry point uncontested
- [ ] No circular imports in hot path
- [ ] All 32 engine dirs have `__init__.py`
- [ ] Duplicate class map complete
- [ ] AutoRegistry covers 100% of .py files

---

## Phase 2 — Code Quality & Test Audit

**Domain Lead:** @dhaherdevbot

### Scope:
1. **Test suite health** — Run full suite, count pass/fail/skip/error. Compare against claimed 492/493/94/112.
2. **test_factors.py investigation** — 541 pre-existing failures. Root cause analysis.
3. **Dead code detection** — Files with 0 imports from any other module. Stale audit reports.
4. **Ponytail audit** — Files that violate YAGNI: empty stubs, uninstantiated classes, unreachable branches.
5. **Large file triage** — Break down `hedge_fund.py` (13,684 lines) into modules.
6. **Legacy strategy audit** — 139 legacy strategies to archive vs 8 active. Verify classification.
7. **Import hygiene** — Wildcard imports, unused imports, missing `__all__`.
8. **Type coverage** — mypy strict mode coverage percentage.

**Files to inspect:**
- `tests/test_factors.py`
- `tests/` directory (167 files)
- `hedge_fund.py` (root, 13.6K lines)
- `quant_nanggroe/engine/strategy/strategies/` (legacy)
- `quant_nanggroe/engine/factors/`

**Verification:**
- [ ] Full test suite run with real numbers
- [ ] test_factors.py root cause documented
- [ ] Dead files identified
- [ ] hedge_fund.py split plan created
- [ ] Legacy vs active strategy classification verified

---

## Phase 3 — Security Audit

**Domain Lead:** @dhaherhackerbot

### Scope:
1. **Secrets detection** — grep for hardcoded passwords, API keys, private keys in all .py/.json/.yaml/.env files.
2. **Git history scrub** — Check if removed secrets still exist in git history (`.env`, `credentials.json`, MT5 passwords).
3. **JWT gate** — Verify `JWT_SECRET` sentinel actually blocks boot. Test without env var.
4. **Fail-closed verification** — Kill switch default state is ACTIVE (blocking). Verify `can_trade()` returns VETOED when no state file exists.
5. **Risk guard enforcement** — Weekly loss veto exists? (Previous gap: P1: WEEKLY veto ABSENT on both Path-A and Path-B).
6. **Supply chain** — Check `pyproject.toml` for pinned dependencies. No `>=` without upper bound.
7. **Environment variable coverage** — Every secret in `.env.example` is consumed in code. Every secret consumed in code is in `.env.example`.
8. **API authentication** — FastAPI endpoints require API key? Rate limiting?

**Files to inspect:**
- `.env.example`, `.env.template`, `config/`
- `quant_nanggroe/exchange/mt5_broker.py` (previously had hardcoded passwords)
- `quant_nanggroe/security/`
- `quant_nanggroe/api/app.py`
- `quant_nanggroe/exchange/guards.py`
- Git history (`git log -p --all -S "password"`)

**Verification:**
- [ ] Zero hardcoded secrets in current code
- [ ] Git history scrubbed or documented exceptions
- [ ] JWT sentinel blocks boot
- [ ] Kill switch defaults to FAIL-CLOSED
- [ ] Weekly loss veto exists and works
- [ ] Dependencies pinned
- [ ] Env var coverage complete

---

## Phase 4 — Execution & Quant Audit

**Domain Lead:** @dhahertraderbot

### Scope:
1. **MT5 broker connectivity** — Test `mt5_broker.py` connects to Valetax server. Account login works.
2. **Paper broker** — Run E2E paper trade: signal → risk → execution → fill → position tracking.
3. **Execution pipeline** — `worker.py` all 5 cycles wired? (signal gen, risk assess, execution, position monitor, portfolio snapshot — previously 2 were placeholder).
4. **Order types** — Verify MARKET, LIMIT, STOP, SL/TP orders all supported in broker abstraction.
5. **Slippage model** — Paper broker uses realistic slippage? Fill probability?
6. **Walk-forward analysis** — Strategy validation uses proper walk-forward? No lookahead bias?
7. **Risk gates** — All 9 checkpoints fire correctly. Test each gate individually.
8. **Kill switch integration** — Wire into execution loop. Test: set daily loss → trigger → verify block.
9. **Portfolio management** — Position sizing (Kelly), correlation limits, drawdown limits active.
10. **P&L reporting** — `pnl-report` cron job works. Numbers match MT5 actuals.

**Files to inspect:**
- `quant_nanggroe/worker.py` (490 lines)
- `quant_nanggroe/exchange/mt5_broker.py`, `paper_broker.py`, `base.py`
- `quant_nanggroe/hedge_fund/execution/`
- `quant_nanggroe/hedge_fund/risk/`
- `quant_nanggroe/engine/backtest/`
- `quant_nanggroe/engine/kelly/`
- `risk_guard.py`, `risk_module.py`

**Verification:**
- [ ] MT5 connection live (Valetax demo)
- [ ] E2E paper trade works from signal to fill
- [ ] All 5 worker cycles implemented (no placeholders)
- [ ] 9 risk gates all VETO correctly
- [ ] Kill switch blocks when triggered
- [ ] Kelly sizing produces rational bet sizes
- [ ] Walk-forward validation is clean (no lookahead)

---

## Phase 5 — Documentation & Governance Audit

**Domain Lead:** @dhaherresearchbot
**Verification Support:** @dhaherdevbot

### Scope:
1. **Docs vs code sync** — `AGENTS.md` claims `qna.py` sole entry point. Verify. Claims `make test-quick` works. Test it.
2. **CHANGELOG.md accuracy** — v5.0.0 claims 492/493 tests pass. v5.1.0 claims security sweep. Verify both.
3. **docs/ coverage** — 57 files. Which are stale? Which match current architecture?
4. **ADR completeness** — Architecture decisions documented? 4 ADRs found. Any silent decisions?
5. **README accuracy** — Build instructions work? `pip install -e .` succeeds?
6. **Zombie documentation** — Files referencing deleted code, old APIs, renamed modules.

**Files to inspect:**
- All 57 `docs/*.md` (sample: 00_VISION, 01_PRD, 02_ARCHITECTURE, 04_API, 07_SECURITY)
- `README.md`, `AGENTS.md`, `CHANGELOG.md`
- `docs/ADR-*.md` files
- `CLAUDE.md`, `COPILOT.md`, `CURSOR.md`, `GEMINI.md`

**Verification:**
- [ ] All doc claims verified against code
- [ ] Build instructions work end-to-end
- [ ] CHANGELOG entries match actual commits
- [ ] Silent decisions identified and ADR created
- [ ] Stale docs flagged for archive

---

## Phase 6 — Bot Ecosystem Audit

**Domain Lead:** @dhaherautobot

### Scope:
1. **Telegram gateway** — Verify @dhaherautobot is running, responding, and reachable.
2. **Gateway MCP** — Check Hermes MCP servers (memory, context, browser, github, self-aware, self-correction, auto-driven) are all active.
3. **Cron job health** — List all active cron jobs, verify they execute and deliver.
4. **Subagent readiness** — Can @dhaherdevbot, @dhaherhackerbot, @dhahertraderbot, @dhaherresearchbot, @dhaherfangbot be instantiated as Hermes subagents?
5. **Audit trail** — Session logging active? Decision ledger writing?
6. **Disaster recovery** — Can bot team recover from crash? State persistence?

---

## Deliverables

| # | Artifact | Owner | Due |
|---|----------|-------|-----|
| D1 | Bot orchestration protocol (`docs/51_BOT_ORCHESTRATION.md`) | @dhaherautobot | Phase 0 |
| D2 | Architecture audit worksheet | @dhaherresearchbot | Phase 1 |
| D3 | Code quality audit worksheet | @dhaherdevbot | Phase 2 |
| D4 | Security audit worksheet | @dhaherhackerbot | Phase 3 |
| D5 | Execution audit worksheet | @dhahertraderbot | Phase 4 |
| D6 | Documentation audit worksheet | @dhaherresearchbot | Phase 5 |
| D7 | Unified final report (`AUDIT_QNA_v5.1.0_FINAL.md`) | @dhaherautobot | All phases |

---

## Risks & Blockers

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Test suite takes > 30min to run | HIGH | MEDIUM | Use `make test-quick` for fast feedback |
| MT5 not installed/running | MEDIUM | HIGH | Document MT5 state first; fallback to paper broker audit |
| Git history cannot be fully scrubbed | HIGH | LOW | Document what remains and why |
| Bot subagents not yet configured | MEDIUM | HIGH | Create Hermes profiles for each bot role |
| hedge_fund.py (13.6K) unmanageable | HIGH | MEDIUM | Don't refactor during audit — just flag and plan split |

---

## Approval

**Status:** ⏳ Awaiting user approval

**Next action:** Once approved, @dhaherautobot will:
1. Create orchestration protocol
2. Dispatch Phase 1 tasks to appropriate bots
3. Begin parallel audit workstreams

---

*Plan generated: 2026-07-25 00:45 WIB | Orchestrator: @dhaherautobot | QNA v5.1.0*

---


---

> **SSOT:** `CANONICAL.md` v8.0.22 — BAL $1,445, weekly 0 WIB, probe 0/32, CPCV 207, vector 6 modul live
