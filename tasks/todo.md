# Quant-Nanggroe-AI — Code Review Remediation

## Phase 1: BLOCKERS

### Task 1: Regenerate .gitignore
**Description:** The `.gitignore` file (5.4KB) is in a mixed/binary encoding state. Regenerate as clean plaintext covering Python, virtualenvs, cache dirs, IDE files, and secrets.

**Acceptance criteria:**
- [ ] `.gitignore` is valid UTF-8 plaintext
- [ ] Covers: `__pycache__/`, `*.pyc`, `*.egg-info/`, `.venv/`, `venv/`, `.env`, `*.so`, `dist/`, `build/`, `backups/`, `node_modules/`, `.ruff_cache/`, `.pytest_cache/`, `.mypy_cache/`, context_cache/, `.vscode/`, `.idea/`
- [ ] `git check-ignore` correctly matches expected files
- [ ] No unintended side effects on files that should be tracked

**Verification:**
- [ ] `git status` shows no unexpected changes
- [ ] `git check-ignore __pycache__/` returns the path (confirming rule works)
- [ ] `git check-ignore .env` returns the path

**Dependencies:** None

**Files likely touched:**
- `.gitignore`

**Estimated scope:** Small (1 file)

---

### Task 2: Reconcile version numbers
**Description:** Version is 4.6.0 in code+config, 5.1.0 in README. Align to single source of truth.

**Acceptance criteria:**
- [ ] `quant_nanggroe/__init__.py` version matches `pyproject.toml` version
- [ ] `README.md` version matches code version
- [ ] All three files say the same version string

**Verification:**
- [ ] `grep -rn "4\.6\.0\|5\.1\.0" --include="*.py" --include="*.toml" --include="*.md"` shows consistent version
- [ ] No version mismatch across the 3 source locations

**Dependencies:** None

**Files likely touched:**
- `quant_nanggroe/__init__.py`
- `README.md`

**Estimated scope:** Small (2 files)

---

## Phase 2: SAFE CODE QUALITY FIXES

### Task 3: Fix docstring position in kill_switch.py
**Description:** `check_auto_activate()` in `kill_switch.py:444-464` has a line of code (`self._ensure_reconciled()`) before the docstring. Move the docstring above the code.

**Acceptance criteria:**
- [ ] Docstring is the first statement inside `check_auto_activate()`
- [ ] `self._ensure_reconciled()` follows after the docstring
- [ ] All docstring parameter documentation remains accurate
- [ ] No behavioral change

**Verification:**
- [ ] `pytest tests/test_kill_switch* tests/test_risk/*` passes
- [ ] Diff shows only the docstring moved up, no logic changes

**Dependencies:** None

**Files likely touched:**
- `quant_nanggroe/engine/risk/kill_switch.py`

**Estimated scope:** Small (1 file, 1 edit)

---

### Task 4: Fix proxy.py import and docstring
**Description:** `proxy.py` has `import requests` inside the function body (paying import overhead on every call) and a docstring that says SSL verification is disabled when the code actually uses `verify=True`.

**Acceptance criteria:**
- [ ] `import requests` moved to module top-level
- [ ] Docstring updated to accurately describe current behavior (verify=True)
- [ ] Remove the stale `# ponytail: fail-closed` comment since the code already does the right thing
- [ ] All existing callers unaffected

**Verification:**
- [ ] `python -c "from quant_nanggroe.proxy import get_json"` works without error
- [ ] No behavioral change (import being at top vs inside function changes nothing functionally)

**Dependencies:** None

**Files likely touched:**
- `quant_nanggroe/proxy.py`

**Estimated scope:** Small (1 file, 2 edits)

---

## Phase 3: GIT HYGIENE

### Task 5: Exclude dashboard/node_modules from tracking
**Description:** The dashboard's `node_modules/` directory has 38,391 files (500MB+). It must be gitignored. If already tracked, `git rm --cached` to stop tracking while keeping files on disk.

**Acceptance criteria:**
- [ ] `node_modules/` added to `.gitignore`
- [ ] `git check-ignore dashboard/node_modules/somefile.js` returns the path
- [ ] If node_modules was already tracked: `git rm --cached -r dashboard/node_modules/` executed
- [ ] `git status` shows no node_modules files as tracked

**Verification:**
- [ ] `git ls-files dashboard/node_modules/ | head -5` returns empty
- [ ] `git status --ignored dashboard/node_modules/` shows "ignored" or "??"

**Dependencies:** Task 1 (`.gitignore` must be valid first)

**Files likely touched:**
- `.gitignore`

**Estimated scope:** Small (1 file + git commands)

---

## Phase 4: ARCHITECTURAL DEBT — AUDIT ONLY

### Task 6: Strategy path consolidation audit
**Description:** Read-only audit of the 3-way strategy directory duplication. Map every strategy file, its location(s), and all import chains. No code changes.

**Acceptance criteria:**
- [ ] Full inventory of all files in all 3 directories
- [ ] Cross-reference showing which strategies exist in 1, 2, or 3 locations
- [ ] Complete import chain map (who imports from where)
- [ ] Yes/no recommendation: finish migration vs revert migration
- [ ] If "finish migration": list of strategies that need migration
- [ ] If "revert migration": list of files in new path to delete

**Verification:**
- [ ] Report saved to `tasks/strategy-consolidation-report.md`
- [ ] Report reviewed by human before any code changes

**Dependencies:** None

**Files likely touched:**
- `tasks/strategy-consolidation-report.md` (new file, read-only analysis)

**Estimated scope:** Large (read-only, 140+ files scanned)

---

## Completion Checkpoint

- [ ] All Phase 1-3 tasks complete
- [ ] Phase 4 report ready for review
- [ ] `ruff check` passes on changed files
- [ ] `pytest` passes (core test suite)
- [ ] All acceptance criteria met per task
