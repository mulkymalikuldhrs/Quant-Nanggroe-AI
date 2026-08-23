# QNA War Plan — Phase 5: Parallel Profile Orchestration

**Version:** v5.1.0  
**Date:** 2026-08-24  
**Status:** ACTIVE  

---

## Objective
Coordinate all 7 Hermes profiles for autonomous QNA hedge fund operation. Zero conflicts, zero version drift.

---

## Profile Assignments

| Profile | Role | Cron Schedule | Skills | Status |
|---------|------|---------------|--------|--------|
| **autobot** | Orchestrator | `*/10 * * * *` | quant-engineering-os, ponytail, venture-os | ✅ Healthy |
| **devbot** | Backend Engineering | `*/30 * * * *` | quant-engineering-os, ponytail | ✅ Healthy |
| **traderbot** | Quant Trading | `*/20 * * * *` | quant-trading, quant-finance-audit | ✅ Healthy |
| **researchbot** | Research/Innovation | `0 */1 * * *` | quant-trading, ponytail | ✅ Healthy |
| **fangbot** | Optimization | `*/30 * * * *` | quant-engineering-os, ponytail | ✅ Healthy |
| **hackerbot** | Security Audit | `*/30 * * * *` | quant-finance-audit, ponytail | ✅ Healthy |
| **clawbot** | QA/Testing | `*/30 * * * *` | quant-engineering-os, ponytail | ❌ **Config Drift** |

---

## Critical Issues

### 1. WAR_PLAN.md was empty — NOW POPULATED
This file must exist and track phase progress.

### 2. clawbot cron (3d568383b72d) — 17 consecutive failures
**Root cause:** Config drift — global inference changed from `nous/tencent/hy3:free` to `opencode-zen/ox-alpha-free`, job unpinned.
**Fix required:** Pin the cron to stable model:
```bash
hermes cron edit 3d568383b72d --provider 9router --model nvidia/minimaxai/minimax-m2.7
```

### 3. 6 Profile Gateways Down
devbot, clawbot, hackerbot, researchbot, fangbot, traderbot — each has separate Hermes gateway not running.
**Action:** `hermes gateway install` in each profile, or run via default profile crons (current setup).

### 4. autobot-heartbeat (ed93e6ef260a) — 3 output truncation failures
Output exceeds limit. Reduce verbosity or increase limit.

---

## Sync Protocol

**On every coordination cycle:**
1. ✅ Verify all 7 profile crons healthy (≤3 errors max)
2. ✅ Commit any local changes in worktree
3. ✅ Push to Codeberg (primary) + GitLab + GitHub
4. ✅ Verify version stays v5.1.0

---

## Gate Status
- **Codeberg:** ✅ Synced (e9606458)
- **GitLab:** ✅ Synced (e9606458)
- **GitHub:** ✅ Synced (e9606458)
- **Version:** ✅ v5.1.0 locked in quant_nanggroe/__init__.py

---

## Next Actions (Priority)
1. Fix clawbot cron pin — blocker for QA profile
2. Start 6 profile gateways OR consolidate to default profile
3. Monitor autobot-heartbeat output size
4. Verify v5.1.0 holds across all remotes