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
| **clawbot** (Tester) | profile-clawbot-test | ❌ False | 0 | PAUSED |
| **devbot** (Backend) | profile-devbot-qna | ❌ False | 0 | PAUSED |
| **fangbot** (Optimization) | profile-fangbot-opt | ❌ False | 0 | PAUSED |
| **hackerbot** (Security) | profile-hackerbot-audit | ✅ True | 0 | HEALTHY |
| **traderbot** (Quant) | profile-traderbot-quant | ❌ False | 0 | PAUSED |
| **researchbot** (Innovation) | profile-researchbot | ❌ False | 0 | PAUSED |

**Production Crons (QNA Core):**
- qna-hedge-fund-production: ✅ True, 0 errors
- self-evolution-daily: ✅ True, 0 errors (pinned: opencode-zen/hy3-free)
- gateway-health-watchdog: ✅ True, 0 errors

**Rule:** Any profile cron errors > 3x → REPORT ONLY, no auto-fix model/provider.

## Git Sync Status

| Remote | Status |
|--------|--------|
| Codeberg (primary) | ✅ Everything up-to-date |
| GitLab (secondary) | ✅ Everything up-to-date |
| GitHub (archived) | ❌ Auth failed (token expired) |

**Working tree:** 6 modified, 6 deleted files (audit temp files cleanup) — pushed.

## Version Lock

- **Tag v5.1.0:** Not present on HEAD (edc67275). Source of truth: `pre-consolidation-20260723-2135-116-gedc67275`
- **Constraint:** No version drift. All profiles must reference same commit/tag.
- **Action:** Tag v5.1.0 at edc67275 after validation.

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