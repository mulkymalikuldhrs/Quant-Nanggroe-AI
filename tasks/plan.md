# Implementation Plan: Quant-Nanggroe-AI — Code Review Remediation

## Overview

Fix the 6 structural issues identified in the Five-Axis Code Review of Quant-Nanggroe-AI v4.6.0. Work is structured into 4 phases: blockers first, then safe fixes, then git hygiene, then architectural debt. Phase 4 (strategy consolidation) is flagged as high-effort and requires a separate planning cycle.

## Architecture Decisions

- **Change as few files as possible.** Each task touches the minimum files needed for its fix.
- **Phase 4 deferred.** The 3-way strategy directory duplication affects 140+ files and has active imports — consolidating it is a separate project, not a quick fix.
- **No behavioral changes.** Every fix preserves existing behavior unless the behavior is a bug (version drift, docstring position).
- **Fix `check_auto_activate` docstring by simply moving it above the code.** Not by restructuring the method.

## Dependency Graph

```
Task 1 (.gitignore)      — independent
Task 2 (version drift)   — independent
Task 3 (docstring)       — independent
Task 4 (proxy.py)        — independent
Task 5 (node_modules)    — depends on Task 1 being correct
Task 6 (strategy audit)  — independent, read-only
```

All Phase 1-3 tasks are independent and can be parallelized. Phase 4 is a read-only audit that feeds a future plan.

## Task List

### Phase 1: BLOCKERS (Must fix immediately — prevents clean git workflow)

- [ ] Task 1: Regenerate `.gitignore` — file is binary/corrupt (5.4KB of mixed encoding). Rewrite as plaintext with proper Python/gitignore rules.
- [ ] Task 2: Reconcile version numbers — `quant_nanggroe/__init__.py` says 4.6.0, `pyproject.toml` says 4.6.0, `README.md` says 5.1.0. Pick 4.6.0 and update README.

### Checkpoint: Phase 1
- [ ] `.gitignore` is valid plaintext, git detects it correctly
- [ ] `grep -r "5.1.0"` returns zero matches (except possibly version history)
- [ ] No version drift between `__init__.py`, `pyproject.toml`, `README.md`

### Phase 2: SAFE CODE QUALITY FIXES (No behavior change)

- [ ] Task 3: Fix docstring position in `kill_switch.py:444-464` — move the docstring ABOVE `self._ensure_reconciled()` so it precedes the code it documents.
- [ ] Task 4: Fix `proxy.py` — move `import requests` to module top-level, update docstring to match actual code (verify=True matches the comment; remove stale comment about fail-closed that contradicts reality).

### Checkpoint: Phase 2
- [ ] `ruff check quant_nanggroe/engine/risk/kill_switch.py quant_nanggroe/proxy.py` passes
- [ ] All existing tests pass
- [ ] Logic is identical before and after (verified via diff)

### Phase 3: GIT HYGIENE (Repository maintainability)

- [ ] Task 5: Git-ignore `dashboard/node_modules/` — add to `.gitignore`, instruct git to stop tracking it (if already tracked), or add as submodule.

### Checkpoint: Phase 3
- [ ] `node_modules/` no longer appears in `git status`
- [ ] Clean `git diff --stat` shows only intended changes

### Phase 4: ARCHITECTURAL DEBT (Read-only audit — no code changes)

- [ ] Task 6: Strategy path consolidation audit — map exact state of 3 directories:
  - `quant_nanggroe/strategies/` (7 files)
  - `quant_nanggroe/engine/strategy/strategies/` (140 files, 133+ real strategy impls)
  - `quant_nanggroe/engine/strategies/` (30 files, incomplete migration target)
  - Document which strategies exist ONLY in old path, which have been migrated, and which import chains exist.
  - Output: `tasks/strategy-consolidation-report.md`

### Checkpoint: Phase 4
- [ ] Report lists every strategy file and its location(s)
- [ ] Report identifies any strategies that exist in all 3, 2, or only 1 location
- [ ] Report documents all import chains that would break if old path is removed
- [ ] Report recommends consolidation strategy (whether to finish the migration or revert)

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| `.gitignore` re-creation might miss edge-case entries | Med | Compare with `git status --ignored` after regenerating |
| Version drift in README is intentional (README reflects aspirational version) | Low | Confirm with human — if 5.1.0 is intentional, update code to match |
| `node_modules/` is already tracked by git | Med | Use `git rm --cached` — will change historical index |
| Strategy consolidation is XL effort | High | Phase 4 is read-only audit only. Execution is separate project. |
| `quant_nanggroe/engine/strategy/strategies/__init__.py` re-exports from new path, but individual strategy files import from old path | High | Means migration is half done — all consumers broke or use old path directly. Need full audit before any changes. |

## Open Questions

1. **README says v5.1.0, code says v4.6.0** — which is the intended truth? README was written after code, so 5.1.0 might be the actual version.
2. **Is `node_modules/` currently tracked in git?** Needs `git ls-files dashboard/node_modules/ | head -5` to check.
3. **Strategy consolidation** — should we finish the migration to the new path or revert the incomplete migration and delete the new path? Requires human decision after Phase 4 audit.

---


---

> **SSOT:** `CANONICAL.md` v8.0.22 — BAL $1,445, weekly 0 WIB, probe 0/32, CPCV 207, vector 6 modul live
