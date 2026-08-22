# QNA WAR PLAN — Phase 5: Parallel Profile Orchestration

**Version:** v5.1.0 (commit edc67275)
**Date:** 2026-07-30
**Status:** ACTIVE

## Objective
Coordinate all 7 Hermes profiles for QNA hedge fund autonomous operation. Zero conflicts, zero version drift, full sync across Codeberg/GitLab/GitHub.

## Profile Cron Health (34 total jobs, 7 enabled)

| Profile | Cron Job | Enabled | Errors | Status |
|---------|----------|---------|--------|--------|
| **autobot** (Orchestrator) | profile-autobot-orch | ✅ True | 0 | HEALTHY |
| **devbot** (Backend) | profile-devbot-qna | ✅ True | 0 | HEALTHY |
| **fangbot** (Optimization) | profile-fangbot-opt | ✅ True | 0 | HEALTHY |
| **hackerbot** (Security) | profile-hackerbot-audit | ✅ True | 0 | HEALTHY |
| **traderbot** (Quant) | profile-traderbot-quant | ✅ True | 0 | HEALTHY |
| **researchbot** (Innovation) | profile-researchbot | ✅ True | 0 | HEALTHY |
| **clawbot** (Tester) | profile-clawbot-test | ✅ True | 0 | HEALTHY |

**Production Crons (QNA Core):**
- qna-hedge-fund-production: ✅ True, 0 errors
- qna-pnl-report: ✅ True, 0 errors
- self-evolution-daily: ✅ True, 0 errors (pinned: opencode-zen/hy3-free)
- gateway-health-watchdog: ✅ True, 0 errors
- whv-462-reminder: ✅ True

**Rule:** Any profile cron errors > 3x → REPORT ONLY, no auto-fix model/provider.

## Git Sync Status

| Remote | Status |
|--------|--------|
| Codeberg (primary) | ✅ Everything up-to-date |
| GitLab (secondary) | ❌ Auth failed (token expired) |
| GitHub (archived) | ❌ Auth failed (token expired) |

**Working tree:** Clean (no modified/deleted files). HEAD at v5.1.0-23-g71230e6b (23 commits ahead of v5.1.0 tag).

## Version Lock

- **Tag v5.1.0:** Exists on remotes, but HEAD is 23 commits ahead (v5.1.0-23-g71230e6b)
- **Constraint:** No version drift. All profiles must reference same commit/tag.
- **Action:** Tag v5.1.1 at current HEAD (71230e6b) after validation.

## No-File-Spam Check

- Deleted 6 audit/temp files this session (_audit_*.py, scan_qna.cjs, session.md, optimize_params*.py, backtest_grid_results.csv, ALL_SOURCE_FILES.txt)
- No new untracked files added by profiles.

## Cross-Profile Guardrails

1. **No profile modifies another's cron model/provider** — cron-doctor is READ-ONLY.
2. **Self-evolution-daily pinned** to `opencode-zen/hy3-free` (9router).
3. **Autobot orchestrates; others execute and report via vault_connector.py**.
4. **SOS Protocol:** Profile silent >15 min → another profile takes over last task.

## Next Actions

1. Resume 5 paused profile crons (clawbot, devbot, fangbot, traderbot, researchbot) when scope defined.
2. Fix GitHub auth or remove as archived remote.
3. Tag v5.1.0 after QNA production cycle validation.
# OPTIMIZATION NOTE — 2026-08-22 03:52
Phase 5 (fangbot): Params optimized. Best verified: DhaherSystem v1.1 (lookback=20, atr_mult=1.2, rr_min=2.5, min_conf=2, kelly=0.25). Full 6480-combo grid interrupted (signal-gen bottleneck). Current BEST_STRATEGIES[0] holds verified best. Version: v5.1.0.
mktemp: failed to create file via template '/c/Users/Hi/AppData/Local/hermes/cache/terminal/hermes-snap-089637466ea5.sh.tmp.XXXXXXXXXX': No such file or directory
