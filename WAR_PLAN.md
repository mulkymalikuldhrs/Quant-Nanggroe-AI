# QNA WAR PLAN — Phase 5: Parallel Profile Orchestration

**Version:** v5.1.0
**Date:** 2026-07-30
**Status:** ACTIVE — 7/7 profiles enabled, healthy, no drift.

## Objective
Coordinate all 7 Hermes profiles for QNA hedge fund autonomous operation. Zero conflicts, zero version drift, full sync across Codeberg/GitLab.

## Profile Cron Health

| Profile | Cron Job | Status |
|---------|----------|--------|
| autobot (Orchestrator) | profile-autobot-orch | ✅ HEALTHY |
| clawbot (Tester) | profile-clawbot-test | ✅ HEALTHY |
| devbot (Backend) | profile-devbot-qna | ✅ HEALTHY |
| fangbot (Optimization) | profile-fangbot-opt | ✅ HEALTHY |
| hackerbot (Security) | profile-hackerbot-audit | ✅ HEALTHY |
| traderbot (Quant) | profile-traderbot-quant | ✅ HEALTHY |
| researchbot (Innovation) | profile-researchbot | ✅ HEALTHY |

## Production Crons
- qna-hedge-fund-production: ✅ True
- self-evolution-daily: ✅ True (pinned: opencode-zen/hy3-free)
- gateway-health-watchdog: ✅ True
- hedge-fund-runner: ❌ Paused (legacy, replaced by qna-hedge-fund-production)

## Codebase Status (Session 9-10)
- Pipeline: 7-stage, evolution loop integrated
- Scoring: 8 scorers 100% wired + MTF engine + WeightEvolver
- Evolution: 8 files, journal → scheduler → scanner → disabler → weight_updater
- MT5: Live connected (Valetax demo $1,099)
- Testing: 173+ passing
- Docs: All *.md updated to reflect current state
