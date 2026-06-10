# Branch Audit Report — quant-nanggroe-ai

**Audit Date:** 2026-03-04  
**Scope:** All git repositories under `/home/z/my-project/quant-nanggroe-ai/repos/`  
**Method:** READ-ONLY — no files were modified during this audit.

---

## Executive Summary

| Metric | Value |
|---|---|
| Total Repos Scanned | 59 |
| Total Git Repos | 59 |
| Non-Git Items | 1 (`clone_c1.sh` — shell script, not a repo) |
| Total Commits Across All Repos | 34,060 |
| Total Branch Entries (de-duped per repo) | 123 |
| Globally Unique Branch Names | 67 |
| Repos with Multiple Branches | 8 |
| Repos with Non-Standard Default Branch | 1 |
| Repos with `master` as Default | 11 |

### Critical Findings

1. **🔴 Trading-Plan-AI-Interactive** uses `mulky-ai-os-v1` as its default branch (not `main` or `master`). This repo also has **7 remote branches** containing v11.1.4 hardening/consolidation code NOT yet merged into the default branch.
2. **🔴 sim** has **23 branches** with significant unmerged feature code — including `feat/copilot-v3` (191 unmerged commits), `feat/copilot-autolayout` (84 unmerged commits), and `feat/microsoft-tools` (20 unmerged commits).
3. **🟡 SolSniperX** has **11 branches**, with 9 remote branches all containing v3.3.0 "Ultimate Intelligence Upgrade" code not merged to `master`.
4. **🟡 ai-manus** has **14 branches** with feature branches (`feat/auth`, `feat/user`, `feature/agent-file-oprate`) containing unique implementation code not in `main`.
5. **🟡 nanggroe-iot** has **13 branches** — 11 are `dependabot` branches with unmerged dependency upgrades.

---

## Complete Repository Branch Table

| # | Repository | Default Branch | Total Branches | Extra Remote Branches | Has Unmerged Code |
|---|---|---|---|---|---|
| 1 | 9drive | main | 1 | 0 | No |
| 2 | AI-Trader | main | 1 | 0 | No |
| 3 | Agentic-AI-System_OLD | main | 1 | 0 | No |
| 4 | AutoHedge | main | 1 | 0 | No |
| 5 | AutoTrader | main | 1 | 0 | No |
| 6 | Clipper-AI | main | 1 | 0 | No |
| 7 | CloakBrowser | main | 1 | 0 | No |
| 8 | Crucix | master | 1 | 0 | No |
| 9 | Dhaher-Corporation | main | 1 | 0 | No |
| 10 | FinceptTerminal | main | 1 | 0 | No |
| 11 | HermesQuantOS | main | 1 | 0 | No |
| 12 | Kronos | master | 1 | 0 | No |
| 13 | Misi-Screener | main | 1 | 0 | No |
| 14 | MoneyPrinterTurbo | main | 1 | 0 | No |
| 15 | Mycroft-Android | master | 1 | 0 | No |
| 16 | OpenAlice | master | 1 | 0 | No |
| 17 | Pentaract | main | 1 | 0 | No |
| 18 | PromptForgeAI | main | 1 | 0 | No |
| 19 | QuantDinger | main | 1 | 0 | No |
| 20 | QuantMuse | main | 1 | 0 | No |
| 21 | Retail-Agentic-Commerce | main | 1 | 0 | No |
| 22 | **SolSniperX** | **master** | **11** | **9** | **Yes** |
| 23 | **Trading-Plan-AI-Interactive** | **mulky-ai-os-v1** | **8** | **6** | **Yes** |
| 24 | TradingAgents | main | 1 | 0 | No |
| 25 | Vibe-Trading | main | 1 | 0 | No |
| 26 | ZeroInject | main | 1 | 0 | No |
| 27 | agentcloud | master | 1 | 0 | No |
| 28 | agenticSeek | main | 1 | 0 | No |
| 29 | ai-agents-for-trading | main | 1 | 0 | No |
| 30 | ai-engineering-hub | main | 1 | 0 | No |
| 31 | ai-financial-agent | main | 1 | 0 | No |
| 32 | ai-hedge-fund | main | 1 | 0 | No |
| 33 | **ai-manus** | **main** | **14** | **12** | **Yes** |
| 34 | aikit | main | 1 | 0 | No |
| 35 | autonomous-organism | main | 1 | 0 | No |
| 36 | awesome-quant | main | 1 | 0 | No |
| 37 | awesome-vibe-coding | main | 1 | 0 | No |
| 38 | bloomberg-terminal | main | 1 | 0 | No |
| 39 | cyber-shell-x-nexus | main | 1 | 0 | No |
| 40 | developer-portfolios | master | 1 | 0 | No |
| 41 | famlyzer-ai | main | 1 | 0 | No |
| 42 | founders-kit | main | 1 | 0 | No |
| 43 | free-AI-Project-Gallery | main | 1 | 0 | No |
| 44 | ghoststudio-ai | main | 1 | 0 | No |
| 45 | **mnemosyne** | **main** | **2** | **1** | **No (already merged)** |
| 46 | **nanggroe-iot** | **main** | **12** | **11** | **Yes (dependabot)** |
| 47 | nanocode | master | 1 | 0 | No |
| 48 | openhuman | main | 1 | 0 | No |
| 49 | **pase-fx** | **main** | **2** | **1** | **Yes** |
| 50 | polymarket-cli | main | 1 | 0 | No |
| 51 | project-nomad-offline | main | 1 | 0 | No |
| 52 | **quant-trading** | **master** | **2** | **1** | **No (docs only)** |
| 53 | rtk-reduce-tokenLLM | master | 1 | 0 | No |
| 54 | **sim** | **main** | **23** | **21** | **Yes** |
| 55 | skales | main | 1 | 0 | No |
| 56 | sled | main | 1 | 0 | No |
| 57 | suna | main | 1 | 0 | No |
| 58 | superpowers | main | 1 | 0 | No |
| 59 | yolobox | master | 1 | 0 | No |

---

## Repos with Multiple Branches — Detailed Analysis

### 1. sim (23 branches) — HIGHEST PRIORITY

The `sim` repository has the most branches with the most unmerged code.

| Branch | Unmerged Commits | Description |
|---|---|---|
| `feat/copilot-v3` | **191** | Major copilot v3 feature development |
| `feat/copilot-autolayout` | **84** | Copilot auto-layout feature |
| `feat/microsoft-tools` | **20** | Microsoft tools integration |
| `improvement/workflow-blocks` | **22** | Workflow blocks UI/UX improvements |
| `feat/aws-lambda` | **28** | AWS Lambda execution support |
| `feat/redtail` | **10** | Redtail CRM integration |
| `feat/execution-filesystem` | **12** | Filesystem execution support |
| `feat/files-support` | **8** | File type outputs / checkpoint files |
| `feat/copilot-billing-v1` | **5** | Copilot billing logic |
| `improvement/prompt-wand` | **7** | Prompt wand improvements |
| `improvement/ui-ux` | **6** | UI/UX enhancements (help modal, invite modal) |
| `improvement/copilot` | **4** | Copilot tests and fixes |
| `feat/text-to-workflow` | **3** | Text-to-workflow (early stage) |
| `improvement/workflow-block` | **3** | Workflow block state management |
| `improvement/templates` | **2** | Template rebuild fixes |
| `feat/hunterio` | **2** | Hunter.io integration |
| `feat/xai` | **2** | XAI live search for advanced mode |
| `fix/copilot-env-vars` | **2** | Copilot env var fixes |
| `fix/start-webhook` | **2** | Webhook badge fix |
| `fix/temp-logs` | **2** | Temporary logging |
| `fix/wand` | **2** | Wand shimmer/streaming fix |
| `fix/wb` | **2** | Read task fix |
| `blog` | **2** | Blog page scaffolding |
| `staging` | **1** | Staging (docs only) |

**Risk:** `feat/copilot-v3` with 191 unmerged commits is a significant divergence. Merging this later will likely cause major conflicts.

---

### 2. ai-manus (14 branches) — HIGH PRIORITY

| Branch | Unmerged Commits | Key Content |
|---|---|---|
| `feat/auth` | **5** | Auth feature + VSCode workspace config |
| `feature/agent-file-oprate` | **5+** | File upload/download for agent chat; fix for download failures |
| `feat/user` | **2** | User management feature (tmp commits) |
| `tmp` | **2** | Temporary work |
| `develop` | **1** | Docs only |
| `docs` | **0** | Already merged |
| `feat/baidu_search` | **1** | Docs only |
| `feat/file` | **1** | Docs only |
| `feature/take_over` | **1** | Docs only |
| `feature/tool_history` | **1** | Docs only |
| `hotfix` | **1** | Docs only |
| `refactor` | **1** | Docs only |

**Risk:** `feat/auth` and `feature/agent-file-oprate` contain real feature code that should be evaluated for merge.

---

### 3. SolSniperX (11 branches) — MEDIUM PRIORITY

All 9 extra remote branches appear to be automated/CI-generated branches containing variations of the "v3.3.0 Ultimate Intelligence Upgrade":

| Branch Pattern | Count | Description |
|---|---|---|
| `main-{hash}` | 6 | Auto-generated branches with v3.3.0 upgrade |
| `main-v3.3.0-consolidation-{hash}` | 1 | Consolidation branch |
| `v3.3.0-ultimate-intelligence-consolidation-final-{hash}` | 1 | Final consolidation |
| `v3.3.0-ultimate-intelligence-upgrade-final-{hash}` | 1 | Final upgrade |

**Risk:** These appear to be AI-agent generated branches. Each has only 1 commit ahead of master. The code should be reviewed and the best version merged, then the others cleaned up.

---

### 4. Trading-Plan-AI-Interactive (8 branches) — MEDIUM PRIORITY

**⚠️ Non-standard default branch: `mulky-ai-os-v1`**

| Branch | Unmerged Commits | Key Content |
|---|---|---|
| `main-11863369769482398312` | **1** | Consolidate and harden v11.1.4 |
| `main-17658784697420415567` | **1** | Consolidate and harden to v11.1.4 |
| `main-17985794924150187901` | **1** | Consolidate v11.1.4 + main baseline |
| `main-5212872703311542570` | **1** | Institutional hardening v11.1.4 |
| `main-6589143822304251475` | **1** | Consolidate and upgrade to v11.1.4 |
| `main-v11-1-4-hardening-11911187523459976589` | **1** | Harden production baseline to v11.1.4 |

**Risk:** Similar to SolSniperX — these appear to be AI-agent generated branches with the same goal. Should be consolidated and cleaned up. The non-standard default branch name is a concern for monorepo integration.

---

### 5. nanggroe-iot (13 branches) — LOW PRIORITY

All 11 extra branches are `dependabot/npm_and_yarn/*` branches:

| Branch | Package | Version |
|---|---|---|
| `dependabot/npm_and_yarn/date-fns` | date-fns | 4.4.0 |
| `dependabot/npm_and_yarn/eslint` | eslint | 10.4.1 |
| `dependabot/npm_and_yarn/prisma/client` | @prisma/client | 7.8.0 |
| `dependabot/npm_and_yarn/radix-ui/react-context-menu` | @radix-ui/react-context-menu | 2.3.0 |
| `dependabot/npm_and_yarn/radix-ui/react-dialog` | @radix-ui/react-dialog | 1.1.16 |
| `dependabot/npm_and_yarn/radix-ui/react-progress` | @radix-ui/react-progress | 1.1.9 |
| `dependabot/npm_and_yarn/radix-ui/react-toast` | @radix-ui/react-toast | 1.2.16 |
| `dependabot/npm_and_yarn/radix-ui/react-tooltip` | @radix-ui/react-tooltip | 1.2.9 |
| `dependabot/npm_and_yarn/reactuses/core` | @reactuses/core | 6.3.2 |
| `dependabot/npm_and_yarn/zod` | zod | 4.4.3 |

**Risk:** Low — these are automated dependency update PRs. Each has 1 unmerged commit. Should be reviewed and merged or closed.

---

### 6. mnemosyne (2 branches) — NO RISK

| Branch | Unmerged Commits | Status |
|---|---|---|
| `v3.0.0-universal-hub` | **0** | Already merged into main |

**Risk:** None — the remote branch is fully merged.

---

### 7. pase-fx (2 branches) — LOW PRIORITY

| Branch | Unmerged Commits | Key Content |
|---|---|---|
| `palette-bolt-improvements-6726346800395345506` | **1** | Accessibility and performance improvements |

**Risk:** Low — 1 commit with accessibility/performance improvements.

---

### 8. quant-trading (2 branches) — NO RISK

| Branch | Unmerged Commits | Key Content |
|---|---|---|
| `review` | **1** | Documentation standardization only |

**Risk:** None — only a docs commit.

---

## Repos with `master` as Default Branch

The following 11 repos use `master` instead of `main` as their default branch:

| Repository | Default Branch | Recent Activity |
|---|---|---|
| Crucix | master | Active (Discord bot, prediction markets) |
| Kronos | master | Active (ML training framework) |
| Mycroft-Android | master | Moderate (Android voice assistant) |
| OpenAlice | master | Active (Trading workspace) |
| SolSniperX | master | Active (Solana sniper bot) |
| agentcloud | master | Active (Agent platform) |
| developer-portfolios | master | Active (Community project) |
| nanocode | master | Moderate (Code editor) |
| quant-trading | master | Moderate (Trading strategies) |
| rtk-reduce-tokenLLM | master | Active (LLM token reduction) |
| yolobox | master | Moderate (Terminal tools) |

**Note:** These repos use `master` likely because they were forked from upstream projects that use `master`. No action needed unless standardizing to `main` is desired.

---

## Globally Unique Branch Names (67 total)

```
blog
dependabot/npm_and_yarn/date-fns-4.4.0
dependabot/npm_and_yarn/eslint-10.4.1
dependabot/npm_and_yarn/prisma/client-7.8.0
dependabot/npm_and_yarn/radix-ui/react-context-menu-2.3.0
dependabot/npm_and_yarn/radix-ui/react-dialog-1.1.16
dependabot/npm_and_yarn/radix-ui/react-progress-1.1.9
dependabot/npm_and_yarn/radix-ui/react-toast-1.2.16
dependabot/npm_and_yarn/radix-ui/react-tooltip-1.2.9
dependabot/npm_and_yarn/reactuses/core-6.3.2
dependabot/npm_and_yarn/zod-4.4.3
develop
docs
feat/auth
feat/aws-lambda
feat/baidu_search
feat/copilot-autolayout
feat/copilot-billing-v1
feat/copilot-v3
feat/execution-filesystem
feat/file
feat/files-support
feat/hunterio
feat/microsoft-tools
feat/redtail
feat/text-to-workflow
feat/user
feat/xai
feature/agent-file-oprate
feature/take_over
feature/tool_history
fix/copilot-env-vars
fix/start-webhook
fix/temp-logs
fix/wand
fix/wb
hotfix
improvement/copilot
improvement/prompt-wand
improvement/templates
improvement/ui-ux
improvement/workflow-block
improvement/workflow-blocks
main
main-11863369769482398312
main-12269301740141403769
main-14476976889621424379
main-17658784697420415567
main-17985794924150187901
main-2308915479949674474
main-3105955084473590888
main-5212872703311542570
main-6589143822304251475
main-7758995104174074679
main-904543946064562364
main-v11-1-4-hardening-11911187523459976589
main-v3.3.0-consolidation-12616142396767724627
master
mulky-ai-os-v1
palette-bolt-improvements-6726346800395345506
refactor
review
staging
tmp
v3.0.0-universal-hub
v3.3.0-ultimate-intelligence-consolidation-final-8528269385850248281
v3.3.0-ultimate-intelligence-upgrade-final-5104791438327581445
```

---

## Branches with Code NOT Yet Merged into Main Monorepo

The following branches contain code that has NOT been merged into their respective default branches and therefore would NOT be captured in a monorepo consolidation based solely on default branches:

### HIGH RISK — Significant Unmerged Feature Code

| Repo | Branch | Unmerged Commits | Code Content |
|---|---|---|---|
| **sim** | `feat/copilot-v3` | 191 | Copilot v3 major feature |
| **sim** | `feat/copilot-autolayout` | 84 | Auto-layout feature |
| **sim** | `feat/aws-lambda` | 28 | AWS Lambda execution |
| **sim** | `improvement/workflow-blocks` | 22 | Workflow block UI improvements |
| **sim** | `feat/microsoft-tools` | 20 | Microsoft tools integration |
| **ai-manus** | `feat/auth` | 5 | Authentication feature |
| **ai-manus** | `feature/agent-file-oprate` | 5 | Agent file upload/download |
| **ai-manus** | `feat/user` | 2 | User management feature |

### MEDIUM RISK — AI-Generated Consolidation Branches

| Repo | Branch | Unmerged Commits | Code Content |
|---|---|---|---|
| **SolSniperX** | 9 branches | 1 each | v3.3.0 Ultimate Intelligence Upgrade variants |
| **Trading-Plan-AI-Interactive** | 6 branches | 1 each | v11.1.4 production hardening variants |

### LOW RISK — Minor/Dependency Updates

| Repo | Branch | Unmerged Commits | Code Content |
|---|---|---|---|
| **nanggroe-iot** | 11 dependabot branches | 1 each | Dependency version upgrades |
| **pase-fx** | `palette-bolt-improvements-*` | 1 | Accessibility/performance |
| **quant-trading** | `review` | 1 | Documentation only |
| **sim** | Various `fix/*` branches | 2 each | Bug fixes |

---

## Recommendations

1. **Sim repo — merge or document decision on `feat/copilot-v3`**: 191 unmerged commits is a significant divergence. Decide whether to merge, rebase, or abandon this work.

2. **AI-manus — evaluate feature branches**: `feat/auth` and `feature/agent-file-oprate` contain real implementation code. Review and merge if viable.

3. **SolSniperX & Trading-Plan-AI-Interactive — clean up AI-generated branches**: Multiple auto-generated branches with the same goal. Pick the best version, merge it, delete the rest.

4. **Trading-Plan-AI-Interactive — rename default branch**: `mulky-ai-os-v1` is non-standard. Consider renaming to `main` for monorepo consistency.

5. **nanggroe-iot — review dependabot PRs**: 11 pending dependency updates. Review and merge or close.

6. **pase-fx — merge accessibility improvements**: Single commit with accessibility/performance fixes — low risk to merge.

7. **Branch hygiene**: Many branches contain only the "docs: standardize MD" commit which is already on the default branches. These can be safely deleted.

---

*Report generated by automated branch audit. No files were modified during this investigation.*
