# QNA WAR PLAN — Phase 5: Parallel Profile Orchestration

## Status (2026-08-28 coordinator run — RTK verified)
- **Cron Reality:** 7/7 profiles have jobs.json at `profiles/<name>/cron/jobs.json`. All crons registered + enabled.
  - `autobot` `profile-autobot-orch` ✓ healthy (streak 0)
  - `devbot` `profile-devbot-qna` ✓ healthy (streak 0)
  - `clawbot` `profile-clawbot-qna` ✗ error (streak 47) — **ABOVE 3x threshold** → report, do NOT auto-fix
  - `hackerbot` `profile-hackerbot-qna` ✗ error (streak 16) — **ABOVE 3x threshold** → report, do NOT auto-fix
  - `researchbot` `profile-researchbot-qna` ✗ error (streak 10) — **ABOVE 3x threshold** → report, do NOT auto-fix
  - `fangbot` `profile-fangbot-qna` ✗ error (streak 51) — **ABOVE 3x threshold** → report, do NOT auto-fix
  - `traderbot` `profile-traderbot-quant` ✗ error (streak 23) — **ABOVE 3x threshold** → report, do NOT auto-fix
- **Root cause:** All 5 erroring profiles share same provider: `nvidia/deepseek-ai/deepseek-v4-flash` → HTTP 404/410/502. Provider/model unavailable. NOT a code bug.
- **Version:** v5.1.0 confirmed (quant_nanggroe/__init__.py + pyproject.toml). No drift.
- **Sync:** codeberg + gitlab + github all up-to-date (Everything up-to-date — clean tree).
- **Worktree:** D:/repositories/Quant-Nanggroe-AI-worktree (branch master) — clean.
- **Protocol:** 5 profiles erroring > 3x → report only. Do NOT auto-fix model/provider per protocol.
- **Hermes terminal cache:** `/c/Users/Hi/AppData/Local/hermes/cache/terminal` recreated (was missing → mktemp noise).

## Profile Cron Health (RTK 2026-08-28 08:00)
| Profile | Schedule | Status | Runs | Failure Streak | Last Error |
|---|---|---|---|---|---|
| autobot | */10 * * * * | ✓ healthy | 667 | 0 | none |
| devbot | */15 * * * * | ✓ healthy | 0 | 0 | none |
| clawbot | */10 * * * * | ✗ error | 0 | 47 | HTTP 404: nvidia/deepseek-v4-flash |
| hackerbot | */30 * * * * | ✗ error | 0 | 16 | HTTP 404: nvidia/deepseek-v4-flash |
| researchbot | 0 */3 * * * | ✗ error | 0 | 10 | Connection error |
| fangbot | */20 * * * * | ✗ error | 0 | 51 | HTTP 502: nvidia/deepseek-v4-flash |
| traderbot | */20 * * * * | ✗ error | 0 | 23 | HTTP 410: nvidia/deepseek-v4-flash |

## Coordination Notes
- 5 profiles erroring > 3x threshold. Root cause = provider (`nvidia/deepseek-v4-flash`) returning 404/410/502. Not code bug.
- Per protocol: report only. Do NOT auto-fix model/provider without explicit direction.
- Version drift: none. v5.1.0 locked in `quant_nanggroe/__init__.py:4` + `pyproject.toml:1`.
- Git worktree: clean. All remotes (codeberg, github, gitlab, gh_dhaherlabs, gh_mulky, gh_mulky2) up-to-date.
- autobot has 5 crons registered (orch + 4 misc). devbot has 1 QNA cron. Other profiles have 1 QNA cron each.
- 2026-08-28 04:12 mass-failure cluster historical, recovered.
