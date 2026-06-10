# C2 Branch Audit Report

**Task ID:** 7  
**Date:** 2026-03-04  
**Scope:** Deep audit of ALL branches in 22 target repos for unique code that must not be missed  

---

## Executive Summary

Audited all branches across 22 target repos in `/home/z/my-project/quant-nanggroe-ai/repos/`.  

**Key Findings:**
- **16 of 22 repos** have ONLY a main/master branch — zero code at risk
- **4 repos** have extra branches but contain no unique code worth merging
- **1 repo** (ai-manus) has **1 unmerged branch** with ~555 lines of unique Python code (user management system)
- **1 repo** (sim) has 21 extra branches but all trading-relevant code is already on main (already ported in Task 4-c)

**Total unique unmerged code: ~555 lines** (ai-manus feat/user branch only)

---

## Repo-by-Repo Audit Results

### Tier 1: NO Extra Branches (Code Safe — Only main/master)

| # | Repo | Default Branch | Extra Branches | Action |
|---|------|---------------|----------------|--------|
| 1 | agentcloud | master | 0 | None needed |
| 2 | agenticSeek | main | 0 | None needed |
| 3 | aikit | main | 0 | None needed |
| 4 | autonomous-organism | main | 0 | None needed |
| 5 | famlyzer-ai | main | 0 | None needed |
| 6 | ghoststudio-ai | main | 0 | None needed |
| 7 | sled | main | 0 | None needed |
| 8 | suna | main | 0 | None needed |
| 9 | superpowers | main | 0 | None needed |
| 10 | yolobox | master | 0 | None needed |
| 11 | PromptForgeAI | main | 0 | None needed |
| 12 | openhuman | main | 0 | None needed |
| 13 | rtk-reduce-tokenLLM | master | 0 | None needed |
| 14 | ai-engineering-hub | main | 0 | None needed |
| 15 | cyber-shell-x-nexus | main | 0 | None needed |
| 16 | project-nomad-offline | main | 0 | None needed |

---

### Tier 2: Extra Branches Exist — No Unique Code Worth Merging

#### mnemosyne
- **Extra branch:** `v3.0.0-universal-hub`
- **Unique commits vs main:** 0 (branch is fully contained in main)
- **Status:** v3.0.0 is an ancestor of main — main has 5 additional commits on top (v2.0.0 rewrite)
- **Action:** None needed — no unique code

#### nanggroe-iot
- **Extra branches:** 10 dependabot branches
  - `dependabot/npm_and_yarn/date-fns-4.4.0`
  - `dependabot/npm_and_yarn/eslint-10.4.1`
  - `dependabot/npm_and_yarn/prisma/client-7.8.0`
  - `dependabot/npm_and_yarn/radix-ui/react-context-menu-2.3.0`
  - `dependabot/npm_and_yarn/radix-ui/react-dialog-1.1.16`
  - `dependabot/npm_and_yarn/radix-ui/react-progress-1.1.9`
  - `dependabot/npm_and_yarn/radix-ui/react-toast-1.2.16`
  - `dependabot/npm_and_yarn/radix-ui/react-tooltip-1.2.9`
  - `dependabot/npm_and_yarn/reactuses/core-6.3.2`
  - `dependabot/npm_and_yarn/zod-4.4.3`
- **Unique code:** Each has 1 commit — npm dependency version bumps only
- **Files changed:** Only `package.json`, `package-lock.json`, and occasionally `README.md`
- **Action:** None needed — no application code changes

#### pase-fx
- **Extra branch:** `palette-bolt-improvements-6726346800395345506`
- **Unique commits:** 1 — "Accessibility and Performance improvements"
- **Files changed:** 4 files, +174/-107
  - `README.md` — Documentation updates
  - `components/Navbar.tsx` — Moved nav items from inline array to `NAV_ITEMS` constant
  - `components/calculators/ProfitCalculator.tsx` — Added `aria-label` attributes to BUY/SELL buttons
  - `package-lock.json` — Lockfile update
- **Trading value:** NONE — purely cosmetic accessibility fixes
- **Action:** None needed

---

### Tier 3: Extra Branches with Unique Code — Already Merged

#### ai-manus (partially merged — Task 3-d)
- **Total branches:** 13 (1 local main + 12 remote)
- **Already merged in Task 3-d:**

| Branch | Unique Commits | Lines Changed | Key Code Merged | Monorepo Location |
|--------|---------------|---------------|-----------------|-------------------|
| `feat/auth` | 5 | +1,609/-7,807 | JWT service, auth middleware | `api/auth.py` |
| `feature/agent-file-oprate` | 12 | +3,529/-17,097 | File ops, attachment service | `agents/tools/file_ops.py` |
| `tmp` | 2 | +2,218/-11,961 | Agent events, MCP config, response schemas | `agents/mcp_config.py` |

- **Branches with docs-only unique commits (NOT worth merging):**

| Branch | Unique Commits | Content |
|--------|---------------|---------|
| `develop` | 1 | docs: standardize MD |
| `docs` | 1 | docs: standardize MD |
| `feat/baidu_search` | 1 | docs: standardize MD |
| `feat/file` | 1 | docs: standardize MD |
| `feature/take_over` | 1 | docs: standardize MD |
| `feature/tool_history` | 1 | docs: standardize MD |
| `hotfix` | 1 | docs: standardize MD |
| `refactor` | 1 | docs: standardize MD |

> **Note:** These 8 branches show large Python diffs (57-97 files) but the diffs are due to branch divergence from an older main, not new code. The only unique commit on each is a documentation standardization. The actual code in these branches is a subset of what's already in feat/auth + feature/agent-file-oprate + tmp.

#### sim (partially merged — Task 4-c)
- **Total branches:** 22 (1 local main + 21 remote)
- **Already merged in Task 4-c:** Kalshi and Polymarket TypeScript tools → Python brokers

| Branch | Unique Commits | Trading-Relevant Changes |
|--------|---------------|------------------------|
| `feat/copilot-v3` | 191 | None — only .mdx docs for Kalshi/Polymarket |
| `feat/aws-lambda` | 28 | None — only .mdx docs |
| `feat/copilot-autolayout` | 84 | None — copilot UI changes |
| `feat/microsoft-tools` | 20 | None — only .mdx docs |
| `improvement/workflow-blocks` | 22 | None — workflow UI changes |
| `feat/files-support` | 8 | None — file upload feature |
| `feat/execution-filesystem` | 12 | None — filesystem execution |
| All other 14 branches | 2-10 each | None — docs, fixes, UI improvements |

- **Critical finding:** ALL 21 branches share identical Kalshi/Polymarket TypeScript code with main — no branch has unique trading tools
- **Branch content:** Copilot AI, workflow UI, AWS Lambda deploy, Microsoft integrations, Redtail CRM, Hunter.io, XAI models, UI/UX improvements — none trading-relevant
- **Action:** None needed — all trading code already on main, already ported

---

### Tier 4: Extra Branches with UNIQUE UNMERGED Code

#### ai-manus: `feat/user` branch — ⚠️ ACTION REQUIRED

- **Unique commits:** 2 (1 docs + 1 "tmp" with real code)
- **Status:** NOT YET MERGED into monorepo
- **Unique new files (not in feat/auth, feature/agent-file-oprate, or tmp):**

| File | Lines | Description |
|------|-------|-------------|
| `backend/app/application/services/user_service.py` | 191 | Full user management: register, login, temp users, token refresh, CRUD |
| `backend/app/infrastructure/external/auth/jwt_auth.py` | 67 | JWT auth using python-jose + bcrypt (differs from merged jwt.py using PBKDF2) |
| `backend/app/infrastructure/repositories/mongo_user_repository.py` | 100 | MongoDB user repository with full CRUD |
| `backend/app/interfaces/api/user_routes.py` | 127 | FastAPI user API routes (7 endpoints) |
| `backend/app/interfaces/schemas/user.py` | 70 | Pydantic user schemas (register, login, update, refresh, response) |
| `backend/USER_SYSTEM.md` | 227 | User system documentation |
| **Total** | **~555** | |

- **Key features in feat/user NOT in already-merged code:**
  1. **UserService** — Complete user lifecycle management (register, authenticate, update, delete, list, count)
  2. **Temporary user creation** — Auto-generated temp users with UUID usernames and random passwords
  3. **Token refresh flow** — Full refresh token rotation (verify → decode → create new pair)
  4. **User repository** — MongoDB-backed user CRUD with email/username lookup
  5. **User API routes** — 7 REST endpoints: register, login, temporary user, get current user, update user, refresh token, get user by ID
  6. **JWTAuth** — Uses `python-jose` + `bcrypt` (different from merged `jwt.py` which uses `PyJWT` + `PBKDF2-SHA256`)

- **Overlap with already-merged code:**
  - `middleware/auth.py` — feat/user has 63 lines vs feat/auth's 130 lines (feat/auth version is more complete)
  - `schemas/request.py` and `schemas/response.py` — Already merged from tmp branch
  - `Frontend components` — Vue.js, not relevant for Python monorepo

- **Recommended merge target:** `src/quant_nanggroe_ai/api/auth.py` — extend existing auth module with user management features

---

## Summary Table

| Repo | Extra Branches | Unique Unmerged Code | Trading/AI Value | Priority | Action |
|------|---------------|---------------------|-----------------|----------|--------|
| agentcloud | 0 | None | N/A | — | None |
| agenticSeek | 0 | None | N/A | — | None |
| **ai-manus** | **12** | **~555 lines (feat/user)** | **Medium** | **P2** | **Merge user management system** |
| aikit | 0 | None | N/A | — | None |
| autonomous-organism | 0 | None | N/A | — | None |
| famlyzer-ai | 0 | None | N/A | — | None |
| ghoststudio-ai | 0 | None | N/A | — | None |
| mnemosyne | 1 | 0 lines (already in main) | None | — | None |
| pase-fx | 1 | ~0 lines (accessibility only) | None | — | None |
| polymarket-cli | 0 | None | N/A | — | None |
| **sim** | **21** | **0 trading-relevant** | **None** | — | **Already merged (Task 4-c)** |
| sled | 0 | None | N/A | — | None |
| suna | 0 | None | N/A | — | None |
| superpowers | 0 | None | N/A | — | None |
| yolobox | 0 | None | N/A | — | None |
| PromptForgeAI | 0 | None | N/A | — | None |
| nanggroe-iot | 10 | 0 lines (dep bumps only) | None | — | None |
| openhuman | 0 | None | N/A | — | None |
| rtk-reduce-tokenLLM | 0 | None | N/A | — | None |
| ai-engineering-hub | 0 | None | N/A | — | None |
| cyber-shell-x-nexus | 0 | None | N/A | — | None |
| project-nomad-offline | 0 | None | N/A | — | None |

---

## Recommended Actions

### P2: Merge ai-manus feat/user branch

The `feat/user` branch contains a complete user management system (~555 lines) that extends the auth module already merged from `feat/auth`. Key adaptations needed:

1. **Create** `src/quant_nanggroe_ai/api/user_service.py` — Port user_service.py with:
   - Replace `app.domain.models.user` → `quant_nanggroe_ai.api.auth.UserModel`
   - Replace `app.infrastructure.external.auth.jwt_auth` → `quant_nanggroe_ai.api.auth.JWTManager`
   - Replace MongoDB repository → SQLAlchemy async (matching monorepo data layer)
   - Add TRADER role to user roles

2. **Extend** `src/quant_nanggroe_ai/api/auth.py` — Add user management endpoints:
   - `POST /auth/register` — User registration
   - `POST /auth/login` — User login with JWT pair
   - `POST /auth/temporary` — Temporary user creation
   - `GET /auth/me` — Current user info
   - `PUT /auth/me` — Update current user
   - `POST /auth/refresh` — Token refresh rotation

3. **Add dependency:** `python-jose[cryptography]` or continue using `PyJWT` (already in merged auth.py)

4. **Discard:** jwt_auth.py (feat/user uses python-jose+bcrypt vs already-merged PyJWT+PBKDF2 — keep existing approach)
5. **Discard:** mongo_user_repository.py (monorepo uses SQLAlchemy async, not MongoDB)
6. **Discard:** Frontend Vue.js components

### No Action Needed

All other repos and branches are either:
- Already fully merged (ai-manus feat/auth, feature/agent-file-oprate, tmp; sim Kalshi/Polymarket)
- Documentation-only changes (8 ai-manus branches)
- Dependency bumps only (nanggroe-iot dependabot branches)
- Accessibility fixes only (pase-fx palette-bolt)
- Already contained in main (mnemosyne v3.0.0)
- Single-branch repos with no extra branches (16 repos)

---

## Comparison with Prior Branch Audit (Task ID: Branch Audit)

This audit confirms and refines the findings from the prior branch audit:

| Prior Finding | This Audit | Status |
|--------------|-----------|--------|
| SolSniperX: 9 branches with v3.3.0 code | Outside scope (not in target 22) | Already merged (Task 3-c) |
| Trading-Plan-AI: 6 branches | Outside scope (not in target 22) | Already merged (Task 4-a) |
| ai-manus: 3 critical branches | Confirmed + found feat/user | 3 merged, 1 remaining |
| sim: 8 critical branches | Confirmed — all non-trading | Already merged (Task 4-c) |
| mnemosyne: 1 branch | Confirmed — 0 unique commits | No action needed |
| pase-fx: 1 branch | Confirmed — accessibility only | No action needed |
| nanggroe-iot: 10 branches | Confirmed — dep bumps only | No action needed |

---

*Audit completed by Task ID 7 agent — 2026-03-04*
