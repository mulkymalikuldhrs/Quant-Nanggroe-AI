# QNA WAR PLAN — Phase 5: Parallel Profile Orchestration

> Version: v5.1.0 | Last updated: 2026-08-24

## 1. Profile Status Matrix

| Profile | Cron OK | Failures | Last Error |
|---------|---------|----------|------------|
| autobot | ✅ ok | 0 | — |
| clawbot | ❌ 404 | 47 | deepseek-v4-flash via 9router (404) |
| devbot | ⏳ pending | 0 | not started |
| fangbot | ❌ 410 | 23 | deepseek-v4-flash EOL (2026-08-07) |
| hackerbot | ❌ 404 | 16 | deepseek-v4-flash via 9router (404) |
| researchbot | ❌ 410 | 2 | deepseek-v4-flash EOL (2026-08-07) |
| traderbot | ❌ 410 | 23 | deepseek-v4-flash EOL (2026-08-07) |

## 2. Action Items

- **clawbot/hackerbot**: 9router model 404 — model unavailable, NOT a code defect
- **fangbot/researchbot/traderbot**: `nvidia/deepseek-ai/deepseek-v4-flash` EOL (410) since 2026-08-07
- **devbot**: Not yet started — check scheduler
- **ALL**: Per directive, do NOT auto-fix model/provider. Report only.

## 3. Version Status

- pyproject.toml: 5.1.0 ✅
- quant_nanggroe/__init__.py: 5.1.0 ✅
- qna.py: 5.1.0 ✅ (was 6.1.0, reverted)
- No file spam detected.

## 4. Sync Status

- Codeberg: ✅ up-to-date
- GitLab: ✅ up-to-date
- GitHub: ✅ up-to-date
