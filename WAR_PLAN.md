# QNA WAR PLAN — Phase 5: Parallel Profile Orchestration

**Version:** v5.1.0 (tag at f6f2ecff — HEAD)
**Date:** 2026-07-30
**Status:** ACTIVE — all profiles enabled, synced, no drift

## Objective
Coordinate all 7 Hermes profiles for QNA hedge fund autonomous operation. Zero conflicts, zero version drift, full sync across Codeberg/GitLab.

## Profile Cron Health (Phase 5 coordinator check)

| Profile | Cron Job | Enabled | Status |
|---------|----------|---------|--------|
| **autobot** (Orchestrator) | profile-autobot-orch | ✅ True | HEALTHY |
| **clawbot** (Tester) | profile-clawbot-test | ✅ True | HEALTHY |
| **devbot** (Backend) | profile-devbot-qna | ✅ True | HEALTHY |
| **fangbot** (Optimization) | profile-fangbot-opt | ✅ True | HEALTHY |
| **hackerbot** (Security) | profile-hackerbot-audit | ✅ True | HEALTHY |
| **traderbot** (Quant) | profile-traderbot-quant | ✅ True | HEALTHY |
| **researchbot** (Innovation) | profile-researchbot | ✅ True | HEALTHY |

**Result: 7/7 profiles enabled and healthy.**

**Production Crons:**
- qna-hedge-fund-production: ✅ True
- self-evolution-daily: ✅ True (pinned: opencode-zen/hy3-free)
- gateway-health-watchdog: ✅ True
- hedge-fund-runner: ❌ Paused (legacy, replaced by qna-hedge-fund-production)

**Rule:** Any profile cron errors > 3x → REPORT ONLY, no auto-fix model/provider.

## Git Sync Status

| Remote | Status |
|--------|--------|
| Codeberg (primary) | ✅ Everything up-to-date |
| GitLab (secondary) | ✅ Everything up-to-date |

Working tree: clean. No untracked files. No version drift.

## Version Lock

- **Tag v5.1.0:** Present at HEAD (f6f2ecff). Pushed to both Codeberg and GitLab.
- **Tag hash:** 769bdceac6910b97e8259df1633562629eab0435
- **Tag is ancestor of HEAD:** ✅ Confirmed
- **Constraint:** No version drift. All profiles reference same commit/tag.

## No-File-Spam Check

Working tree clean (git status --short = empty). No temp files, no audit artifacts.

## Cross-Profile Guardrails

1. **No profile modifies another's cron model/provider** — cron-doctor is READ-ONLY.
2. **Self-evolution-daily pinned** to `opencode-zen/hy3-free` (9router).
3. **Autobot orchestrates; others execute and report via vault_connector.py**.
4. **SOS Protocol:** Profile silent >15 min → another profile takes over last task.
