# BRANCH AUDIT COMPLETE - Quant-Nanggroe-AI Consolidation

**Audit Date:** 2025-08-15
**Auditor:** Task ID 1
**Scope:** All 25 C1 repos + 34 additional repos = 59 total repositories

---

## EXECUTIVE SUMMARY

| Metric | Count |
|--------|-------|
| Total repos audited | 59 |
| Repos with ONLY main/master branch | 42 |
| Repos with extra branches | 8 |
| Total extra branches across all repos | 62 |
| Extra branches with UNIQUE code (not in main) | 56 |
| Extra branches with NO unique code | 6 |
| **CRITICAL: Branches with unique implementation code** | **8 repos, 56 branches** |

### Priority Classification for Consolidation

| Priority | Repos | Action Required |
|----------|-------|-----------------|
| **P0 - CRITICAL** | SolSniperX, Trading-Plan-AI-Interactive | Multiple branches with unique v3.3.0/v11.1.4 code NOT in main |
| **P1 - HIGH** | ai-manus, sim | Many feature branches with substantial unique code (auth, copilot, AWS Lambda, etc.) |
| **P2 - MEDIUM** | pase-fx, quant-trading, nanggroe-iot | Minor unique changes in non-main branches |
| **P3 - LOW** | mnemosyne | Branch exists but has 0 unique commits (already merged) |

---

## SECTION 1: C1 REPOS (25 repos that merge into Quant-Nanggroe-AI)

### 1.1 C1 Repos with NO Extra Branches (17 repos)

These repos have ONLY `main` or `master` — no code is at risk of being missed.

| # | Repo | Default Branch | Extra Branches | Unique Code Risk |
|---|------|---------------|----------------|-----------------|
| 1 | AI-Trader | main | 0 | NONE |
| 2 | Vibe-Trading | main | 0 | NONE |
| 3 | HermesQuantOS | main | 0 | NONE |
| 4 | TradingAgents | main | 0 | NONE |
| 5 | ai-hedge-fund | main | 0 | NONE |
| 6 | AutoHedge | main | 0 | NONE |
| 7 | AutoTrader | main | 0 | NONE |
| 8 | Clipper-AI | main | 0 | NONE |
| 9 | FinceptTerminal | main | 0 | NONE |
| 10 | QuantDinger | main | 0 | NONE |
| 11 | QuantMuse | main | 0 | NONE |
| 12 | Dhaher-Corporation | main | 0 | NONE |
| 13 | Misi-Screener | main | 0 | NONE |
| 14 | MoneyPrinterTurbo | main | 0 | NONE |
| 15 | Pentaract | main | 0 | NONE |
| 16 | ZeroInject | main | 0 | NONE |
| 17 | CloakBrowser | main | 0 | NONE |

### 1.2 C1 Repos with master-only (2 repos)

| # | Repo | Default Branch | Extra Branches | Unique Code Risk |
|---|------|---------------|----------------|-----------------|
| 1 | OpenAlice | master | 0 | NONE |
| 2 | Crucix | master | 0 | NONE |

### 1.3 C1 Repos with master-only (additional 2 repos)

| # | Repo | Default Branch | Extra Branches | Unique Code Risk |
|---|------|---------------|----------------|-----------------|
| 1 | Kronos | master | 0 | NONE |
| 2 | Mycroft-Android | master | 0 | NONE |

### 1.4 C1 Repos with Extra Branches - CRITICAL (2 repos)

---

#### **SolSniperX** [P0 - CRITICAL]
- **Default Branch:** master
- **Extra Branches:** 9 (all remote)
- **Risk:** ALL 9 branches contain v3.3.0 "Ultimate Intelligence Upgrade" code NOT in master

| Branch | Commits Ahead | Unique Code Description |
|--------|--------------|------------------------|
| `remotes/origin/main-12269301740141403769` | 1 | v3.3.0 consolidation - 29 files, +351/-337 lines. Frontend changes (Sidebar, TradingPage), verify_v3_3_0.py |
| `remotes/origin/main-14476976889621424379` | 1 | v3.3.0 upgrade - 24 files, +280/-264 lines. App.jsx, TradingPage changes |
| `remotes/origin/main-2308915479949674474` | 1 | v3.3.0 consolidation/finalize - 29 files, +351/-337 lines. Similar to main-1226930 |
| `remotes/origin/main-3105955084473590888` | 1 | v3.3.0 consolidation/finalize - 30 files, +351/-381 lines. Removed verify_consolidated.py, added verify_v3_3_0.py |
| `remotes/origin/main-7758995104174074679` | 1 | v3.3.0 consolidation/verify - 29 files, +351/-337 lines |
| `remotes/origin/main-904543946064562364` | 1 | v3.3.0 consolidation/upgrade - 29 files, +351/-337 lines |
| `remotes/origin/main-v3.3.0-consolidation-12616142396767724627` | 1 | v3.3.0 consolidation/finalize - 29 files, +351/-337 lines |
| `remotes/origin/v3.3.0-ultimate-intelligence-consolidation-final-8528269385850248281` | 1 | v3.3.0 consolidation/upgrade - 29 files, +351/-337 lines |
| `remotes/origin/v3.3.0-ultimate-intelligence-upgrade-final-5104791438327581445` | 1 | v3.3.0 finalize - 29 files, +349/-338 lines |

**ASSESSMENT:** These appear to be iterative AI-generated consolidation attempts. The `main-3105955084473590888` branch is the most mature (removes old verify script). The core unique code across all branches is: v3.3.0 frontend upgrades (Sidebar.jsx, TradingPage.jsx, App.jsx, package.json) + verify_v3_3_0.py. Recommend merging `main-3105955084473590888` (most evolved) or `main-14476976889621424379` (leanest at 24 files).

---

#### **Trading-Plan-AI-Interactive** [P0 - CRITICAL]
- **Default Branch:** mulky-ai-os-v1 (NOT main/master!)
- **Extra Branches:** 6 (all remote)
- **Risk:** ALL 6 branches contain v11.1.4 "Production Hardened" code NOT in mulky-ai-os-v1

| Branch | Commits Ahead | Unique Code Description |
|--------|--------------|------------------------|
| `remotes/origin/main-11863369769482398312` | 1 | v11.1.4 consolidation/hardening - 45 files, +902/-811 lines. flutter_app/web/manifest.json, api_integrations.gs, whatsapp_bot/index.js |
| `remotes/origin/main-17658784697420415567` | 1 | v11.1.4 consolidation/hardening - 46 files, +868/-304 lines. Heavier whatsapp_bot changes |
| `remotes/origin/main-17985794924150187901` | 1 | v11.1.4 consolidation/baseline - 25 files, +882/-462 lines. Largest whatsapp_bot package-lock changes |
| `remotes/origin/main-5212872703311542570` | 1 | v11.1.4 institutional hardening - 27 files, +637/-436 lines |
| `remotes/origin/main-6589143822304251475` | 1 | v11.1.4 Consolidate/Upgrade - 45 files, +611/-290 lines. Includes python_client changes |
| `remotes/origin/main-v11-1-4-hardening-11911187523459976589` | 1 | v11.1.4 harden production baseline - 26 files, +415/-130 lines. Leanest branch |

**ASSESSMENT:** All branches are v11.1.4 hardening iterations. `main-11863369769482398312` has the most files changed (45) and most substantial diff (+902/-811). `main-6589143822304251475` uniquely includes python_client changes. `main-v11-1-4-hardening-11911187523459976589` is the leanest. Recommend merging `main-11863369769482398312` (most complete) with review of python_client from `main-6589143822304251475`.

### 1.5 C1 Repo with main-only (no extra branches)

| # | Repo | Default Branch | Extra Branches |
|---|------|---------------|----------------|
| 1 | 9drive | main | 0 |
| 2 | Retail-Agentic-Commerce | main | 0 |

---

## SECTION 2: ADDITIONAL REPOS (34 repos)

### 2.1 Additional Repos with NO Extra Branches (24 repos)

| # | Repo | Default Branch | Extra Branches | Unique Code Risk |
|---|------|---------------|----------------|-----------------|
| 1 | aikit | main | 0 | NONE |
| 2 | autonomous-organism | main | 0 | NONE |
| 3 | awesome-quant | main | 0 | NONE |
| 4 | awesome-vibe-coding | main | 0 | NONE |
| 5 | cyber-shell-x-nexus | main | 0 | NONE |
| 6 | sled | main | 0 | NONE |
| 7 | PromptForgeAI | main | 0 | NONE |
| 8 | nanocode | master | 0 | NONE |
| 9 | Agentic-AI-System_OLD | main | 0 | NONE |
| 10 | ai-agents-for-trading | main | 0 | NONE |
| 11 | ai-engineering-hub | main | 0 | NONE |
| 12 | ai-financial-agent | main | 0 | NONE |
| 13 | bloomberg-terminal | main | 0 | NONE |
| 14 | developer-portfolios | master | 0 | NONE |
| 15 | famlyzer-ai | main | 0 | NONE |
| 16 | founders-kit | main | 0 | NONE |
| 17 | free-AI-Project-Gallery | main | 0 | NONE |
| 18 | ghoststudio-ai | main | 0 | NONE |
| 19 | openhuman | main | 0 | NONE |
| 20 | polymarket-cli | main | 0 | NONE |
| 21 | project-nomad-offline | main | 0 | NONE |
| 22 | rtk-reduce-tokenLLM | master | 0 | NONE |
| 23 | skales | main | 0 | NONE |
| 24 | suna | main | 0 | NONE |
| 25 | superpowers | main | 0 | NONE |
| 26 | yolobox | master | 0 | NONE |
| 27 | agentcloud | master | 0 | NONE |
| 28 | agenticSeek | main | 0 | NONE |

### 2.2 Additional Repos with Extra Branches - CRITICAL (6 repos)

---

#### **ai-manus** [P1 - HIGH]
- **Default Branch:** main
- **Extra Branches:** 11 (all remote)
- **Risk:** Multiple feature branches with substantial unique code

| Branch | Commits Ahead | Unique Code Description |
|--------|--------------|------------------------|
| `remotes/origin/develop` | 1 | Standardized MD docs - 15 files, +185/-8 lines |
| `remotes/origin/docs` | 0 | NO unique commits (fully merged) |
| `remotes/origin/feat/auth` | 5 | **AUTH system** - 80 files, +4018/-398 lines. frontend/src/utils/auth.ts (146 new lines), dom.ts, vite.config.ts |
| `remotes/origin/feat/baidu_search` | 1 | Doc standardization - 8 files, +157/-2 lines |
| `remotes/origin/feat/file` | 1 | Doc standardization - 8 files, +157/-2 lines |
| `remotes/origin/feat/user` | 2 | **User features** - 25 files, +1155/-8 lines. Dockerfile, requirements changes |
| `remotes/origin/feature/agent-file-oprate` | 12 | **FILE OPERATIONS** - 42 files, +1857/-225 lines. sandbox file upload/download/delete (479-line file.py), chat attachment binding |
| `remotes/origin/feature/take_over` | 1 | Doc standardization - 8 files, +157/-2 lines |
| `remotes/origin/feature/tool_history` | 1 | Doc standardization - 8 files, +157/-2 lines |
| `remotes/origin/hotfix` | 1 | Doc standardization - 8 files, +157/-2 lines |
| `remotes/origin/refactor` | 1 | Refactoring + doc standardization - 15 files, +185/-8 lines |
| `remotes/origin/tmp` | 2 | **MCP config + tools** - 47 files, +1196/-85 lines. mcp.json.example (43 lines), tool constants, update_doc.sh |

**ASSESSMENT:** Three branches have critical unique code: `feat/auth` (authentication system), `feature/agent-file-oprate` (file operations in sandbox), and `tmp` (MCP config). The rest are primarily doc standardization already in main. **Must merge:** `feat/auth`, `feature/agent-file-oprate`, `tmp`.

---

#### **sim** [P1 - HIGH]
- **Default Branch:** main
- **Extra Branches:** 22 (all remote)
- **Risk:** MASSIVE amount of unique code in feature branches

| Branch | Commits Ahead | Unique Code Description |
|--------|--------------|------------------------|
| `remotes/origin/blog` | 2 | Blog page scaffolding - 18 files, +779/-77. layout.tsx, page.tsx for blogs |
| `remotes/origin/feat/aws-lambda` | 28 | **AWS LAMBDA DEPLOYMENT** - 22 files, +23,243/-48 lines. Full lambda creation/deployment, registry.ts, package-lock |
| `remotes/origin/feat/copilot-autolayout` | 84 | **COPILOT AUTOLAYOUT** - 90 files, +11,253/-2,642 lines. Auto-layout, diff engine, targeted updates, copilot tools |
| `remotes/origin/feat/copilot-billing-v1` | 5 | **COPILOT BILLING** - 10 files, +355/-3 lines. billing/update-cost route (214 lines) |
| `remotes/origin/feat/copilot-v3` | 191 | **COPILOT V3** - 158 files, +24,177/-10,098 lines. Complete copilot rewrite with chat, run workflow, interrupt, streaming, YAML service |
| `remotes/origin/feat/execution-filesystem` | 12 | **EXECUTION FILESYSTEM** - 58 files, +8,208/-153 lines. Remote execution filesystem, storage provider detection, file redaction |
| `remotes/origin/feat/files-support` | 8 | **FILES BETWEEN BLOCKS** - 55 files, +7,986/-259 lines. Presigned URLs, file type outputs, starter block file upload |
| `remotes/origin/feat/hunterio` | 2 | **HUNTER.IO TOOL** - 14 files, +259/-1. Hunter search/leads integration |
| `remotes/origin/feat/microsoft-tools` | 20 | **MICROSOFT TOOLS** - 39 files, +4,077/-37. SharePoint (read_page 450 lines, read_site 143 lines), OneDrive |
| `remotes/origin/feat/redtail` | 10 | **REDTAIL CRM** - 24 files, +2,529/-2. Redtail write_contact (398 lines), write_note (166 lines) |
| `remotes/origin/feat/text-to-workflow` | 3 | **TEXT TO WORKFLOW** - 13 files, +863/-3. import-export.ts (381 lines), create-menu, control-bar |
| `remotes/origin/feat/xai` | 2 | **XAI LIVESEARCH** - 14 files, +180/-10. xAI provider with liveSearch in advanced mode |
| `remotes/origin/fix/copilot-env-vars` | 2 | Copilot env var fix - 14 files, +149/-12 |
| `remotes/origin/fix/start-webhook` | 2 | Remove active webhook badge - 8 files, +139/-4 |
| `remotes/origin/fix/temp-logs` | 2 | Temp log fix - 9 files, +138/-20 |
| `remotes/origin/fix/wand` | 2 | Wand shimmer + prompt fix - 9 files, +241/-71 |
| `remotes/origin/fix/wb` | 2 | Wealthbox read task fix - 8 files, +138/-6 |
| `remotes/origin/improvement/copilot` | 4 | **COPILOT REFACTOR + TESTS** - 54 files, +4,080/-531. Code hygiene, tests, tools/utils.ts, types.ts |
| `remotes/origin/improvement/prompt-wand` | 7 | **PROMPT WAND** - 12 files, +403/-124. System prompt generation wand feature |
| `remotes/origin/improvement/templates` | 2 | Template rebuild + tests - 12 files, +773/-93 |
| `remotes/origin/improvement/ui-ux` | 6 | **UI/UX OVERHAUL** - 56 files, +3,332/-3,242. Workspace header/selector, search modal, invite modal |
| `remotes/origin/improvement/workflow-block` | 3 | Workflow block improvements - 21 files, +787/-242. Active execution state, simplified block |
| `remotes/origin/improvement/workflow-blocks` | 22 | **MAJOR UI REWORK** - 107 files, +25,252/-7,881. Console, chat UI, control bar, panel tabs, audio UI |
| `remotes/origin/staging` | 1 | Doc standardization - 7 files, +136/-1 |

**ASSESSMENT:** This is the most complex repo for consolidation. The `feat/copilot-v3` branch contains 191 unique commits with +24,177/-10,098 lines (the complete copilot v3 system). `improvement/workflow-blocks` has +25,252/-7,881 lines of UI rework. **Critical branches to merge:** `feat/copilot-v3`, `improvement/workflow-blocks`, `feat/aws-lambda`, `feat/execution-filesystem`, `feat/files-support`, `feat/microsoft-tools`, `feat/redtail`, `feat/text-to-workflow`.

---

#### **nanggroe-iot** [P2 - MEDIUM]
- **Default Branch:** main
- **Extra Branches:** 10 (all remote, all dependabot)
- **Risk:** Dependency updates only

| Branch | Commits Ahead | Unique Code Description |
|--------|--------------|------------------------|
| `remotes/origin/dependabot/npm_and_yarn/date-fns-4.4.0` | 1 | Bump date-fns 4.1.0 → 4.4.0 |
| `remotes/origin/dependabot/npm_and_yarn/eslint-10.4.1` | 1 | Bump eslint 9.39.2 → 10.4.1 |
| `remotes/origin/dependabot/npm_and_yarn/prisma/client-7.8.0` | 1 | Bump @prisma/client 6.19.2 → 7.8.0 |
| `remotes/origin/dependabot/npm_and_yarn/radix-ui/react-context-menu-2.3.0` | 1 | Bump radix context-menu |
| `remotes/origin/dependabot/npm_and_yarn/radix-ui/react-dialog-1.1.16` | 1 | Bump radix dialog |
| `remotes/origin/dependabot/npm_and_yarn/radix-ui/react-progress-1.1.9` | 1 | Bump radix progress |
| `remotes/origin/dependabot/npm_and_yarn/radix-ui/react-toast-1.2.16` | 1 | Bump radix toast |
| `remotes/origin/dependabot/npm_and_yarn/radix-ui/react-tooltip-1.2.9` | 1 | Bump radix tooltip |
| `remotes/origin/dependabot/npm_and_yarn/reactuses/core-6.3.2` | 1 | Bump @reactuses/core 6.1.9 → 6.3.2 |
| `remotes/origin/dependabot/npm_and_yarn/zod-4.4.3` | 1 | Bump zod 4.3.5 → 4.4.3 |

**ASSESSMENT:** All branches are Dependabot dependency bumps. No unique application code. **Low risk.** The Prisma 6→7 and eslint 9→10 bumps may have breaking changes worth reviewing before merging.

---

#### **pase-fx** [P2 - MEDIUM]
- **Default Branch:** main
- **Extra Branches:** 1 (remote)

| Branch | Commits Ahead | Unique Code Description |
|--------|--------------|------------------------|
| `remotes/origin/palette-bolt-improvements-6726346800395345506` | 1 | Accessibility & performance improvements - 3 files, +17/-14. Navbar.tsx, ProfitCalculator.tsx |

**ASSESSMENT:** Minor UI improvements. **Low risk but should merge** for accessibility fixes.

---

#### **quant-trading** [P2 - MEDIUM]
- **Default Branch:** master
- **Extra Branches:** 1 (remote)

| Branch | Commits Ahead | Unique Code Description |
|--------|--------------|------------------------|
| `remotes/origin/review` | 1 | Doc standardization - 3 files, +119 lines. CHANGELOG.md, CONTRIBUTING.md, README.md |

**ASSESSMENT:** Documentation only. **No unique application code.** Safe to skip for consolidation.

---

#### **mnemosyne** [P3 - LOW]
- **Default Branch:** main
- **Extra Branches:** 1 (remote)

| Branch | Commits Ahead | Unique Code Description |
|--------|--------------|------------------------|
| `remotes/origin/v3.0.0-universal-hub` | 0 | **NO unique commits** - already merged |

**ASSESSMENT:** Branch is fully merged. **No risk.** Can be deleted.

---

## SECTION 3: CONSOLIDATION ACTION PLAN

### Must Merge Before Consolidation (Code exists ONLY in branches)

| Priority | Repo | Branch to Merge | Unique Code | Method |
|----------|------|----------------|-------------|--------|
| P0 | SolSniperX | `main-3105955084473590888` | v3.3.0 Ultimate Intelligence Upgrade (most evolved: 30 files) | Cherry-pick or merge, then delete other 8 branches |
| P0 | Trading-Plan-AI-Interactive | `main-11863369769482398312` | v11.1.4 hardening (most complete: 45 files, +902/-811) | Cherry-pick or merge; also review python_client from `main-6589143822304251475` |
| P1 | ai-manus | `feat/auth` | Auth system (80 files, +4018 lines) | Merge branch |
| P1 | ai-manus | `feature/agent-file-oprate` | File operations (42 files, +1857 lines) | Merge branch |
| P1 | ai-manus | `tmp` | MCP config + tools (47 files, +1196 lines) | Merge branch |
| P1 | sim | `feat/copilot-v3` | Copilot v3 complete rewrite (158 files, +24177/-10098) | **LARGEST BRANCH** - Merge with careful testing |
| P1 | sim | `improvement/workflow-blocks` | Major UI rework (107 files, +25252/-7881) | Merge with UI regression testing |
| P1 | sim | `feat/aws-lambda` | AWS Lambda deployment (22 files, +23243 lines) | Merge branch |
| P1 | sim | `feat/execution-filesystem` | Execution filesystem (58 files, +8208 lines) | Merge branch |
| P1 | sim | `feat/files-support` | Files between blocks (55 files, +7986 lines) | Merge branch |
| P1 | sim | `feat/microsoft-tools` | SharePoint + OneDrive (39 files, +4077 lines) | Merge branch |
| P1 | sim | `feat/redtail` | Redtail CRM (24 files, +2529 lines) | Merge branch |
| P1 | sim | `feat/text-to-workflow` | Text to workflow (13 files, +863 lines) | Merge branch |
| P2 | pase-fx | `palette-bolt-improvements-6726346800395345506` | Accessibility fixes (3 files) | Merge branch |

### Can Skip (No unique application code)

| Repo | Branch(es) | Reason |
|------|-----------|--------|
| ai-manus | docs, feat/baidu_search, feat/file, feat/take_over, feature/tool_history, hotfix | Only doc standardization (already in main via other commits) |
| quant-trading | review | Only doc changes |
| nanggroe-iot | All 10 dependabot branches | Dependency bumps only; run `npm audit fix` on main instead |
| mnemosyne | v3.0.0-universal-hub | Already fully merged (0 unique commits) |
| sim | staging, fix/* branches | Doc changes + minor fixes already superseded by feat branches |

### Can Delete After Merge (Redundant branches)

| Repo | Branches to Delete After Merge |
|------|-------------------------------|
| SolSniperX | 8 of 9 branches (all v3.3.0 iterations; keep only `main-3105955084473590888` until merged) |
| Trading-Plan-AI-Interactive | 5 of 6 branches (all v11.1.4 iterations; keep only `main-11863369769482398312` until merged) |
| mnemosyne | `v3.0.0-universal-hub` (already merged) |

---

## SECTION 4: BRANCH COUNT SUMMARY BY REPO

| Repo | Local Branches | Remote Branches | Total Extra | Has Unique Code |
|------|---------------|-----------------|-------------|----------------|
| AI-Trader | 1 (main) | 1 | 0 | No |
| Vibe-Trading | 1 (main) | 1 | 0 | No |
| OpenAlice | 1 (master) | 1 | 0 | No |
| HermesQuantOS | 1 (main) | 1 | 0 | No |
| **SolSniperX** | **1 (master)** | **10** | **9** | **YES - v3.3.0 code** |
| Kronos | 1 (master) | 1 | 0 | No |
| TradingAgents | 1 (main) | 1 | 0 | No |
| ai-hedge-fund | 1 (main) | 1 | 0 | No |
| AutoHedge | 1 (main) | 1 | 0 | No |
| AutoTrader | 1 (main) | 1 | 0 | No |
| Clipper-AI | 1 (main) | 1 | 0 | No |
| Crucix | 1 (master) | 1 | 0 | No |
| FinceptTerminal | 1 (main) | 1 | 0 | No |
| QuantDinger | 1 (main) | 1 | 0 | No |
| QuantMuse | 1 (main) | 1 | 0 | No |
| Dhaher-Corporation | 1 (main) | 1 | 0 | No |
| Misi-Screener | 1 (main) | 1 | 0 | No |
| MoneyPrinterTurbo | 1 (main) | 1 | 0 | No |
| Pentaract | 1 (main) | 1 | 0 | No |
| ZeroInject | 1 (main) | 1 | 0 | No |
| CloakBrowser | 1 (main) | 1 | 0 | No |
| 9drive | 1 (main) | 1 | 0 | No |
| Mycroft-Android | 1 (master) | 1 | 0 | No |
| **Trading-Plan-AI-Interactive** | **1 (mulky-ai-os-v1)** | **7** | **6** | **YES - v11.1.4 code** |
| Retail-Agentic-Commerce | 1 (main) | 1 | 0 | No |
| **ai-manus** | **1 (main)** | **13** | **11** | **YES - auth, files, MCP** |
| aikit | 1 (main) | 1 | 0 | No |
| autonomous-organism | 1 (main) | 1 | 0 | No |
| awesome-quant | 1 (main) | 1 | 0 | No |
| awesome-vibe-coding | 1 (main) | 1 | 0 | No |
| cyber-shell-x-nexus | 1 (main) | 1 | 0 | No |
| sled | 1 (main) | 1 | 0 | No |
| **sim** | **1 (main)** | **23** | **22** | **YES - copilot, AWS, MS tools** |
| PromptForgeAI | 1 (main) | 1 | 0 | No |
| nanocode | 1 (master) | 1 | 0 | No |
| Agentic-AI-System_OLD | 1 (main) | 1 | 0 | No |
| ai-agents-for-trading | 1 (main) | 1 | 0 | No |
| **quant-trading** | **1 (master)** | **2** | **1** | **Docs only** |
| ai-engineering-hub | 1 (main) | 1 | 0 | No |
| ai-financial-agent | 1 (main) | 1 | 0 | No |
| bloomberg-terminal | 1 (main) | 1 | 0 | No |
| developer-portfolios | 1 (master) | 1 | 0 | No |
| famlyzer-ai | 1 (main) | 1 | 0 | No |
| founders-kit | 1 (main) | 1 | 0 | No |
| free-AI-Project-Gallery | 1 (main) | 1 | 0 | No |
| ghoststudio-ai | 1 (main) | 1 | 0 | No |
| **mnemosyne** | **1 (main)** | **2** | **1** | **No (0 unique)** |
| **nanggroe-iot** | **1 (main)** | **11** | **10** | **Dependabot only** |
| openhuman | 1 (main) | 1 | 0 | No |
| **pase-fx** | **1 (main)** | **2** | **1** | **YES - accessibility** |
| polymarket-cli | 1 (main) | 1 | 0 | No |
| project-nomad-offline | 1 (main) | 1 | 0 | No |
| rtk-reduce-tokenLLM | 1 (master) | 1 | 0 | No |
| skales | 1 (main) | 1 | 0 | No |
| suna | 1 (main) | 1 | 0 | No |
| superpowers | 1 (main) | 1 | 0 | No |
| yolobox | 1 (master) | 1 | 0 | No |
| agentcloud | 1 (master) | 1 | 0 | No |
| agenticSeek | 1 (main) | 1 | 0 | No |

---

## SECTION 5: ESTIMATED UNIQUE LINES OF CODE AT RISK

| Repo | Total Unique Lines (additions) | Critical Branches |
|------|-------------------------------|-------------------|
| sim | ~88,000+ | feat/copilot-v3, improvement/workflow-blocks, feat/aws-lambda |
| ai-manus | ~7,000+ | feat/auth, feature/agent-file-oprate, tmp |
| SolSniperX | ~350 | v3.3.0 upgrade (frontend) |
| Trading-Plan-AI-Interactive | ~900 | v11.1.4 hardening |
| pase-fx | ~17 | Accessibility fixes |
| **TOTAL AT RISK** | **~96,000+ lines** | |

---

*End of Branch Audit Report*
