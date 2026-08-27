# QNA WAR PLAN — Phase 5: Parallel Profile Orchestration (Coordinator)

> Version: 8.0.18 | Last updated: 2026-08-28 | Coordinator run

## 1. Profile Cron Status (live read 2026-08-28)
| Profile | Status | Failures | Last Error |
|---------|--------|----------|------------|
| autobot | ✅ ok | 0 | — |
| devbot | ✅ ok | 0 | — |
| traderbot | ✅ ok | 0 | — |
| autobot-heartbeat | ✅ ok | 0 | — |
| researchbot | ❌ lock | 6 | TERMINAL_CWD read lock timeout 660s |
| fangbot | ❌ lock | 9 | TERMINAL_CWD read lock timeout 660s |
| hackerbot | ❌ lock | 9 | TERMINAL_CWD read lock timeout 660s |
| clawbot | ❌ lock | 3 | TERMINAL_CWD read lock timeout 660s |

## 2. Findings
- **4 of 7 profiles erroring** — all `TERMINAL_CWD read lock timeout` (workdir contention), NOT model/provider. Previously assumed 404/502/410 model issues — those are resolved; residual failure is scheduling/resource lock.
- Errors > 3x on researchbot(6), fangbot(9), hackerbot(9) → REPORTED, not auto-fixed (directive). Root cause: concurrent workdir writers holding the read lock past the 660s inactivity limit.
- Model/provider: no model change made (directive respected).

## 3. Version Status
- pyproject.toml: **8.0.18** ✅
- quant_nanggroe/__init__.py: **8.0.18** ✅
- qna.py: **8.0.18** ✅
- Internal version drift: NONE — all three aligned. (WAR_PLAN previously stale at 8.0.10; corrected here.)

## 4. Sync Status
- origin/codeberg/gitlab/github: a4824e37 ✅ pushed
- gh_dhaherlabs (GitHub mirror): pushed to a4824e37 ✅
- Uncommitted local changes (NOT committed): `quant_nanggroe/data/account_ledger.json` — live trading ledger, excluded to avoid file spam.
- File spam: results/ remains in .gitignore. No new spam.

---
## Coordinator Notes
- Lock-timeout failures are schedule/resource contention, not code or model defects. Resolution requires staggering cron schedules or removing shared workdir — OUT OF SCOPE for this coordinator (no auto-config change).
- Next trigger: next profile cron run or explicit user directive to stagger schedules.
