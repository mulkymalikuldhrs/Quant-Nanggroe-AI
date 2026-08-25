# QNA WAR PLAN — Phase 5: Parallel Profile Orchestration

> Version: v8.0.8 | Last updated: 2026-08-25
## 1. Profile Status Matrix
| Profile | Cron OK | Failures | Last Error |
|---------|---------|----------|------------|
| autobot | ⚠️ timeout | 0 | TERMINAL_CWD lock timeout 660s |
| clawbot | ❌ 404 | 47 | deepseek-v4-flash via 9router (404) |
| devbot | ⏳ pending | 0 | not started |
| fangbot | ❌ 502 | 51 | deepseek-v4-flash timeout (502) |
| hackerbot | ❌ 404 | 16 | deepseek-v4-flash via 9router (404) |
| researchbot | ❌ 410 | 4 | deepseek-v4-flash EOL (2026-08-07) |
| traderbot | ❌ 410 | 23 | deepseek-v4-flash EOL (2026-08-07) |

## 2. Action Items
- **clawbot/hackerbot**: 9router model 404 — model unavailable, NOT a code defect
- **fangbot/researchbot/traderbot**: `nvidia/deepseek-ai/deepseek-v4-flash` EOL (410) since 2026-08-07; fangbot also 502 timeout
- **devbot**: Not yet started — check scheduler
- **autobot**: TERMINAL_CWD lock timeout — schedule conflict with workdir writers
- **ALL**: Per directive, do NOT auto-fix model/provider. Report only.

## 3. Version Status
- pyproject.toml: 8.0.8 ✅
- quant_nanggroe/__init__.py: 8.0.8 ✅
- qna.py: 8.0.8 ✅
- No file spam (results/ removed from tracking, added to .gitignore).

## 4. Sync Status
- Codeberg: ✅ up-to-date
- GitLab: ✅ up-to-date
- GitHub: ✅ up-to-date

--- Phase 5 Sync (2026-08-25) ---
|- Profiles 7/7 alive: autobot/devbot/clawbot/fangbot/hackerbot/researchbot/traderbot
|- clawbot profile-clawbot-qna: status=error (model 404 deepseek-v4-flash via 9router) — REPORTED, NOT auto-fixed (directive)
|- devbot: started (profile-devbot-qna enabled, status=ok)
|- Version drift fixed: pyproject.toml 5.1.0 → 8.0.8 (match qna.py + __init__.py). All three files now v8.0.8.
|- File spam removed: results/ dir (18 files incl. gate_status.json with merge conflict markers) deleted + added to .gitignore.
|- Sync: codeberg/gitlab/github master pushed 288f1701.
|- Version: v8.0.8 enforced. No drift.
