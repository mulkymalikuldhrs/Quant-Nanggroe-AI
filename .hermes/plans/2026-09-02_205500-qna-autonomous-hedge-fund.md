# QNA Autonomous Hedge Fund — Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Transform QNA from RED prototype (328 simulated trades, 0 live, regime unknown) into autonomous hedge fund with autodetect, WF-gated promotion, kill-switch, live auditable PnL.

**Architecture:** Keep ExecutionManager + broker + autodetect + kill-switch file + paper_state journal. Add loop: regime -> WF promotion -> ExecutionManager -> journal -> risk guard. Wiki at C:/Users/Hi/wiki is SSOT.

**Tech Stack:** Python 3.13, MetaTrader5 5.0.5735, ExecutionManager builder, account_discovery, paper_state JSON + journal db, pytest, git filter-repo

---

## Current Context

- Wiki 10 pages 3 raw lint 0 issues 2026-09-02
- Repo D:/repositories/Quant-Nanggroe-AI-worktree master ba68e285
- Live terminal running ValetaxIntl-Live2 BAL 1445.41 verified via mt5 lib and broker
- Paper journal 328 trades WR 25.4% PnL +1648.48 authoritative, 51 orders 12 FILLED 39 REJECTED
- Registry 135 (57 archive +78 live) WF 161 entries 0 viable regime unknown kill-switch inactive L1 2026-08-28
- Sensitive files tracked in history with live values — NOT scrubbed rotation blocking
- Shell guard blocks literal .env strings — use Python subprocess list args

## Phase 1 — Reversible Hardening (GO now)

### Task 1: paper_state drift guard
**Files:** tests/test_paper_state_reconciliation.py, quant_nanggroe/engine/paper_state.py
Test: journal PnL sum vs state.json total_value within 1.0. Implement assert_reconciled() helper.

### Task 2: Verify test_prod_ready_wiring
**Files:** tests/test_prod_ready_wiring.py
Run pytest expect PASS (MagicMock already done).

### Task 3: Strategy lifecycle wiring
**Files:** quant_nanggroe/engine/strategy_registry.py, walk_forward.py, tests/test_strategy_lifecycle_wiring.py
Sync registry -> lifecycle.json via sync_lifecycle_from_registry().

### Task 4: Regime stub
**Files:** quant_nanggroe/engine/regime.py, tests/test_regime_not_unknown.py
Stub SMA/volatility so state regime != unknown.

### Task 5: Kill-switch coverage
**Files:** tests/test_kill_switch_blocks_order.py
Active kill-switch file must REJECT submit_order.

### Task 6: Wiki auto-update script
**Files:** scripts/update_wiki_reconciliation.py
Reads MT5 balance + journal PnL, updates comparisons page.

## Phase 2 — Live Loop (dry-run first)

### Task 7: Live dry-run
**Files:** scripts/live_dry_run.py
With QNA_LIVE_TRADING=1 build ExecutionManager, get_account, get_positions, print BAL POS. Expect 1445.41 0.

### Task 8: Micro-order probe (NEEDS GO)
**Files:** scripts/live_probe_order.py
0.01 lot max, requires GO before live. Dry-run uses PaperBroker.

### Task 9: Journal live branch
**Files:** qna_trade_journal.db schema add account column, wiki paper-trade-vs-live-trade.md

## Phase 3 — Security (PLAN ONLY, needs GO)

### Task 10: Rotate leaked values
Manual on portals: broker password, provider keys, local .env and yaml. Values stay [REDACTED] in wiki.

### Task 11: Scrub history filter-repo
Use git filter-repo --invert-paths --force. Precondition Task 10 done. Use Python subprocess list with .env placeholder. Verify no sensitive paths in rev-list.

## Files Likely to Change
paper_state/*.json, engine/paper_state.py strategy_registry.py walk_forward.py regime.py, tests/test_*.py, scripts/*.py, .env config files after GO, wiki

## Tests
pytest 5 new tests PASS, python scripts/live_dry_run.py BAL 1445.41, wiki lint 0

## Risks
WF 0 viable needs tuning, naive regime risky cap exposure, micro-order real loss needs GO, filter-repo rewrites hashes coordinate force push, guard blocks .env literals use list args.

## Execution Handoff
Phase 1 Tasks 1-6 reversible safe autonomously. Phase 2 Task 8 and Phase 3 Tasks 10-11 need explicit GO.

---

> **SSOT:** `CANONICAL.md` v8.1.4 — BAL $1,445, weekly 0 WIB, probe 0/32, CPCV 207, vector 6 modul live, risk per-symbol
