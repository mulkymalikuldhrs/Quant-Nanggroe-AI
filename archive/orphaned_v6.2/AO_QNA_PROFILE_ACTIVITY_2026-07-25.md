# Profile Cron Activity — 2026-07-25 (QNA Pollution Incident)

## What Happened

Multiple Hermes profiles ran autonomous audits on QNA repo (D:\repositories\Quant-Nanggroe-AI-worktree)
between 01:00-08:00 on 2026-07-25, causing version drift + file spam:

| Profile | Session Time | Size | What They Did | Damage |
|---------|-------------|------|---------------|--------|
| **devbot** | 07:02 | 174msgs/126tools | "Update ALL .md to v5.2.0" | Bumped version to v5.2.0 (code is v5.1.0) |
| **fangbot** | 07:01 | 164msgs | "Migrate 50 old strategies to new path" | Created 141 untracked junk strategy files |
| **hackerbot** | 07:11 | 144msgs | "Update ALL .md to match real architecture" | Rewrote README/CHANGELOG/AGENTS — conflicting |
| **clawbot** | 01:08 | 107msgs | "Audit QNA Orchestrasi" | Read-only (safe) |
| **researchbot** | 01:03 | 154msgs | "Research cycle" | Read-only (safe) |

## Fixes Applied

1. **git clean -fd** → removed all 141 untracked junk files
2. **Reverted v5.2.0 → v5.1.0** in CHANGELOG.md, CLAUDE.md, COPILOT.md, CURSOR.md
3. **Committed** as `afd747a` + pushed to Codeberg
4. **Paused 4 pollution crons** (DO NOT resume without user OK):
   - `profile-devbot-qna` (e4a3ce9bae58)
   - `profile-clawbot-test` (ed96a2a48c9d)
   - `profile-autobot-orch` (ccac29837f6e)
   - `profile-researchbot` (1f9bc09539e9)

## Current State (18:45)

- QNA repo: CLEAN, v5.1.0, HEAD = afd747a (matches code __version__)
- AutoRegistry intact (registry.py + strategies/registry.py)
- All profile crons that modify QNA: PAUSED
- AO: fully wired (separate repo, no pollution)

## Lesson

Profile crons with write access to QNA cause drift. Keep them PAUSED unless
user explicitly asks for autonomous QNA work. When user says "QNA hanya"
or "fokus QNA", do NOT let profile crons interfere.

---


---

> **SSOT:** `CANONICAL.md` v8.0.21 — BAL $1,445, weekly 0 WIB, probe 0/32, CPCV 207, vector 6 modul live
