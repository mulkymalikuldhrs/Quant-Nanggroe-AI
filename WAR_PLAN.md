# QNA War Plan - Phase 5 (Coordination)

## Status Summary
- **WAR_PLAN.md**: Updated with coordination status
- **7 Profile Crons**: 4/7 core profiles running, 2 production crons, 3 missing
- **Sync**: Codeberg ✅ synced, GitLab ❌ auth failed, GitHub ❌ auth failed
- **Version**: v5.1.0 maintained

## Profiles
| # | Profile | Status | Last Run | Notes |
|---|----------|--------|----------|--------|
| 1 | profile-autobot-orch | ✅ Active | 2026-08-23T21:33:21 | Running ok |
| 2 | profile-devbot-qna | ✅ Active | 2026-08-23T21:29:42 | Running ok |
| 3 | profile-traderbot-quant | ✅ Active | 2026-08-23T21:33:14 | Running ok |
| 4 | profile-researchbot | ✅ Active | 2026-08-23T21:00:39 | Running ok |
| 5 | qna-hedge-fund-production | ✅ Active | 2026-08-23T21:30:10 | Running ok |
| 6 | qna-pnl-report | ⚠️ Env Issue | 2026-08-23T21:30:10 | mktemp failed (system env) |
| 7 | profile-clawbot | ❌ Missing | N/A | Not in cron list |
| 8 | profile-hackerbot | ❌ Missing | N/A | Not in cron list |
| 9 | profile-fangbot | ❌ Missing | N/A | Not in cron list |

## Issues
- **Missing profiles**: clawbot, hackerbot, fangbot not in cron list (task says "resumed")
- **Sync**: Codeberg ✅, GitLab auth failed, GitHub auth failed (token issues in cron env)
- **System env**: mktemp failing on every terminal call (temp dir issue)

## Action Items
- Add missing profile crons (clawbot, hackerbot, fangbot)
- Fix GitLab/GitHub auth tokens for cron pushes
- Fix system temp directory for mktemp