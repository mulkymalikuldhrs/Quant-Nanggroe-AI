# QNA WAR PLAN — Phase 5: Parallel Profile Orchestration

## Status
- **Active Profiles:** 7/7 (autobot, clawbot, fangbot, hackerbot, devbot, researchbot, traderbot)
- **Version:** v5.1.0 (locked — no drift)
- **Worktree:** D:/repositories/Quant-Nanggroe-AI-worktree

## Profile Cron Health
| Profile | Schedule | Status | Last Error |
|---|---|---|---|
| devbot | */15 * * * * | ✗ gateway down | Gateway not running |
| clawbot | */10 * * * * | ✗ model 404 | nvidia/deepseek-v4-flash 404 (47 failures) |
| hackerbot | */30 * * * * | ✗ model 404 | nvidia/deepseek-v4-flash 404 (16 failures) |
| researchbot | 0 */3 * * * | ✗ connection error | 10 failures (9Router SPOF) |
| autobot | */10 * * * * | ✗ timeout | TERMINAL_CWD lock 660s (workdir contention) |
| fangbot | */20 * * * * | ⚠ running | HTTP 502 timeout (51 failures) |
| traderbot | */20 * * * * | ✗ model 410 | model gone 410 (23 failures) |

## Action Items
1. **Gateway** — Start `hermes gateway install` (all profiles blocked)
2. **Model** — Switch all profile crons from `nvidia/deepseek-v4-flash` to `nvidia/minimaxai/minimax-m2.7` (stable per 9Router docs)
3. **Workdir** — Remove `Workdir: D:/repositories/Quant-Nanggroe-AI-worktree` from profile crons to fix autobot timeout (no workdir needed for audit tasks)
4. **Git** — Sync worktree to all 3 remotes (Codeberg/GitLab/GitHub)
5. **9Router** — Restart localhost:20128 to clear researchbot connection errors

## Coordination Notes
- No auto-fix per protocol (cron errors >3x) — reporting only
- Version lock v5.1.0 maintained across profile boundaries
- All profiles write to same worktree — stagger schedules to avoid lock contention
