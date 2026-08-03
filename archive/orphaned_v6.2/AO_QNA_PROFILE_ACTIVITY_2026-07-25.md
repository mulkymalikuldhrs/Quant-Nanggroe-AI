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


<!-- CODE-TRUTH STATUS FOOTER — appended 2026-08-03 23:43:45 by autobot (QNA audit 2026-08-03) -->
<!-- Method: append-only. Source of truth = code, not prior .md claims. -->
## 🔍 CODE-TRUTH STATUS (2026-08-03 audit)
- **FusionEngine**: EXISTS — `quant_nanggroe/core/scoring/fusion_engine.py:27` (prior claim "false" RETRACTED).
- **API server**: EXISTS + startable — `quant_nanggroe/cli.py:603` uvicorn :8000; `launch.bat api`; 223 routes wired.
- **Dashboard**: UNWIRED only because server not started; UI code present (`dashboard/`, 261 tsx+ts).
- **Phantom-equity ($1M default)**: MITIGATED — P1b fail-CLOSED `_resolve_equity()` floor $1000 in `risk_gate_bridge.py` (ctor:145, evaluate:194, evaluate_from_state:449). Live path uses `evaluate_from_state` -> real MT5 equity.
- **Polars**: NOT imported anywhere (`import polars`=0) -> `engine/data/providers/yahoo_polars.py` genuinely MISSING (archive gap real).
- **Secrets**: 0 hardcoded (grep `sk-`/`AKIA`=0). `eval`/`pickle`: 0 live vulns (only security-linter strings).
- **ENV BLOCKER**: all venv numpy ABI broken (cp311 `.pyd` under cp312) -> runtime import unverified until `uv sync`. Patch syntax+logic verified standalone.
- **Archive upgrade**: 8/11 new modules ALREADY in code; 4 missing (quality.py, yahoo_polars.py, feature_engine.py, alerting/).
- **Audit trail**: `C:/Users/Hi/Desktop/QNA_AUDIT_DEBAT.txt` | inventory `QNA_FILE_INVENTORY.txt` | `QNA_EXTENSION_LEDGER.txt`.
<!-- END CODE-TRUTH FOOTER -->
