# Comprehensive Codebase Cleanup & Documentation Plan

## Executive Summary

**Objective**: Complete autonomous codebase organization, cleanup (archive-only, no deletion), and documentation update  
**Repository**: `d:\repositories\Quant-Nanggroe-AI-worktree`  
**Version**: v6.2.0 Autonomous  
**Date**: 2026-07-28  
**Status**: Ready for Execution

---

## Phase 1: Deep Audit & Analysis

### 1.1 File Inventory
**Total Files**: 70,000+ files  
**Total .md Files**: 2,331 documentation files  
**Total .py Files**: 23,986 Python files  
**Total .ts/.tsx Files**: 10,539 TypeScript files

### 1.2 Directory Structure Audit

#### Core Directories
- `quant_nanggroe/` - Main Python package (312 engine modules)
- `dashboard/` - Next.js frontend (30 pages)
- `tests/` - Test suite
- `docs/` - Documentation (58+ numbered docs)
- `config/` - Configuration files
- `scripts/` - Utility scripts (114 files)
- `data/` - Data storage (JSON, CSV, DB)
- `archive/` - Archived files (existing)

#### Audit Targets
1. **Root-level files** - Identify orphaned scripts, logs, temp files
2. **`__pycache__/`** - Python bytecode cache (safe to archive)
3. **`.pytest_cache/`** - Test cache (safe to archive)
4. **`.ruff_cache/`** - Linter cache (safe to archive)
5. **`*.log` files** - Log files (archive old logs)
6. **`*.pyc` files** - Compiled Python (archive)
7. **`node_modules/`** - Dependencies (keep, but verify)
8. **`.venv/`** - Virtual environment (keep)

### 1.3 Code Quality Issues

#### Identified Problems
1. **Console statements** - Already removed in previous session ✅
2. **Dead code** - Legacy shims, unused imports
3. **Duplicate implementations** - Multiple risk managers, overlapping strategies
4. **Orphaned files** - Files with no imports/exports
5. **Broken dependencies** - Missing modules, circular imports
6. **Inconsistent naming** - Mixed conventions (snake_case vs camelCase)
7. **Outdated configs** - Stale CircleCI, old package.json

### 1.4 Documentation Gaps

#### Missing Documentation
1. **Architecture diagrams** - Self-loop flow, component interactions
2. **API reference** - Complete endpoint documentation
3. **Deployment guide** - Step-by-step production deployment
4. **Troubleshooting guide** - Common issues and solutions
5. **Contributing guide** - How to add strategies, features
6. **Changelog** - Version history with features/fixes

---

## Phase 2: Archive Strategy (No Deletion)

### 2.1 Archive Directory Structure
```
archive/
├── 2026-07-28-cleanup/
│   ├── pycache/              # All __pycache__ directories
│   ├── pytest-cache/         # .pytest_cache
│   ├── ruff-cache/           # .ruff_cache
│   ├── old-logs/             # *.log files older than 30 days
│   ├── legacy-scripts/       # Obsolete scripts
│   ├── deprecated-modules/   # Deprecated Python modules
│   ├── old-docs/             # Superseded documentation
│   └── temp-files/           # Temporary files, backups
```

### 2.2 Files to Archive

#### Safe to Archive (No Impact)
1. **`__pycache__/`** - All Python bytecode caches
2. **`.pytest_cache/`** - Test cache
3. **`.ruff_cache/`** - Linter cache
4. **`*.pyc`** - Compiled Python files
5. **`*.log`** - Old log files (>30 days)
6. **`nul`** - Windows null file artifact
7. **`*.bak`** - Backup files
8. **`*.tmp`** - Temporary files

#### Review Before Archiving
1. **`archive/`** - Existing archive (verify contents)
2. **`backups/`** - Old backups (verify not needed)
3. **`docs/archive/`** - Already archived docs
4. **Legacy strategy files** - Check if referenced
5. **Old config files** - Verify not in use

#### Keep Active (Do Not Archive)
1. **`quant_nanggroe/`** - Main package
2. **`dashboard/`** - Frontend
3. **`tests/`** - Test suite
4. **`config/`** - Active configuration
5. **`scripts/`** - Active scripts
6. **`data/`** - Active data storage
7. **`.venv/`** - Virtual environment
8. **`node_modules/`** - Dependencies

### 2.3 Archive Execution

#### PowerShell Script
```powershell
# Create archive structure
$archiveBase = "archive\2026-07-28-cleanup"
New-Item -ItemType Directory -Path "$archiveBase\pycache" -Force
New-Item -ItemType Directory -Path "$archiveBase\pytest-cache" -Force
New-Item -ItemType Directory -Path "$archiveBase\ruff-cache" -Force
New-Item -ItemType Directory -Path "$archiveBase\old-logs" -Force
New-Item -ItemType Directory -Path "$archiveBase\temp-files" -Force

# Archive __pycache__ directories
Get-ChildItem -Recurse -Directory -Filter "__pycache__" | ForEach-Object {
    $dest = "$archiveBase\pycache\$($_.FullName.Replace(':', '').Replace('\', '_'))"
    Move-Item $_.FullName $dest -Force
}

# Archive .pytest_cache
if (Test-Path ".pytest_cache") {
    Move-Item ".pytest_cache" "$archiveBase\pytest-cache" -Force
}

# Archive .ruff_cache
if (Test-Path ".ruff_cache") {
    Move-Item ".ruff_cache" "$archiveBase\ruff-cache" -Force
}

# Archive old log files (>30 days)
Get-ChildItem -Filter "*.log" | Where-Object {
    $_.LastWriteTime -lt (Get-Date).AddDays(-30)
} | ForEach-Object {
    Move-Item $_.FullName "$archiveBase\old-logs\" -Force
}

# Archive temporary files
Get-ChildItem -Filter "*.tmp" | Move-Item -Destination "$archiveBase\temp-files\" -Force
Get-ChildItem -Filter "*.bak" | Move-Item -Destination "$archiveBase\temp-files\" -Force

# Archive nul file (Windows artifact)
if (Test-Path "nul") {
    Move-Item "nul" "$archiveBase\temp-files\" -Force
}
```

---

## Phase 3: Code Organization

### 3.1 Remove Dead Code

#### Targets
1. **Legacy strategy shim** - `quant_nanggroe/engine/strategy/strategies/` (keep only `__init__.py`)
2. **Unused imports** - Run `ruff check --select F401 --fix`
3. **Deprecated functions** - Mark with `@deprecated` decorator
4. **Commented-out code** - Remove or document why kept

#### Execution
```bash
# Remove unused imports
ruff check quant_nanggroe/ --select F401 --fix

# Check for dead code
ruff check quant_nanggroe/ --select F841  # Unused variables
```

### 3.2 Consolidate Duplicates

#### Identified Duplicates
1. **Risk managers** - Multiple implementations
2. **Strategy runners** - Overlapping functionality
3. **Config loaders** - Redundant parsing

#### Action
- Keep canonical implementation
- Archive duplicates with note
- Update imports to use canonical version

### 3.3 Fix Naming Conventions

#### Standards
- **Python**: snake_case (functions, variables, modules)
- **TypeScript**: camelCase (functions, variables), PascalCase (classes, components)
- **Files**: snake_case.py, kebab-case.tsx
- **Directories**: snake_case

#### Execution
```bash
# Check naming violations
ruff check quant_nanggroe/ --select N  # PEP8 naming
```

### 3.4 Fix Broken Dependencies

#### Audit
```bash
# Check for missing imports
ruff check quant_nanggroe/ --select F401,F811

# Check for circular imports
python -c "import quant_nanggroe"
```

#### Fix
- Add missing imports
- Break circular dependencies
- Update `__init__.py` exports

---

## Phase 4: Documentation Update

### 4.1 Core Documentation

#### README.md
**Sections to Add/Update**:
- ✅ Project overview (Autonomous Quant Hedge Fund)
- ✅ Features (self-loop, self-awareness, council debate)
- ✅ Installation guide (uv, npm)
- ✅ Quick start guide
- ✅ Architecture overview
- ✅ API endpoints summary
- ✅ Configuration guide
- ✅ Deployment instructions
- ✅ Contributing guide
- ✅ License

#### ARCHITECTURE.md
**Sections to Add**:
- ✅ System architecture diagram
- ✅ Component interactions
- ✅ Data flow
- ✅ Self-loop flow diagram
- ✅ Strategy registration flow
- ✅ Pipeline orchestration flow
- ✅ Risk management flow
- ✅ Execution flow

#### AGENTS.md
**Sections to Add**:
- ✅ AI agent instructions
- ✅ Entry points (qna.py)
- ✅ Commands (uv run, pytest, ruff)
- ✅ Architecture facts
- ✅ Testing quirks
- ✅ Toolchain config
- ✅ Gotchas
- ✅ What not to change

#### CHANGELOG.md
**Entries to Add**:
- ✅ v6.2.0 - Autonomous self-loop orchestrator
- ✅ v6.2.0 - Self-awareness module
- ✅ v6.2.0 - Council debate integration
- ✅ v6.2.0 - Dashboard autonomous page
- ✅ v6.2.0 - Walk-forward validation page
- ✅ v6.2.0 - Strategy infrastructure verification
- ✅ v6.2.0 - Production readiness 100/100

### 4.2 API Documentation

#### Create `docs/API_REFERENCE.md`
**Contents**:
- All 180+ API endpoints
- Request/response schemas
- Authentication guide
- Rate limiting info
- Error handling
- Examples (curl, Python, TypeScript)

### 4.3 Deployment Guide

#### Create `docs/DEPLOYMENT_GUIDE.md`
**Contents**:
- Prerequisites
- Docker deployment
- Bare metal deployment
- Environment configuration
- SSL/TLS setup
- Monitoring setup
- Backup strategy
- Disaster recovery

### 4.4 Troubleshooting Guide

#### Create `docs/TROUBLESHOOTING.md`
**Contents**:
- Common errors and solutions
- Debugging techniques
- Log file locations
- Health checks
- Performance tuning
- FAQ

### 4.5 Contributing Guide

#### Create `docs/CONTRIBUTING.md`
**Contents**:
- How to add a strategy
- How to add an API endpoint
- How to add a dashboard page
- Code style guide
- Testing requirements
- PR process

---

## Phase 5: Final Verification

### 5.1 Build Verification

#### Backend
```bash
# Run tests
PYTHONPATH="" uv run python -m pytest tests/ -v

# Lint
ruff check quant_nanggroe/

# Type check
mypy quant_nanggroe/
```

#### Frontend
```bash
cd dashboard
npm run build
# Expected: 30/30 pages compiled, zero errors
```

### 5.2 Integration Verification

#### Test Autonomous Loop
```bash
# Start API
uv run python qna.py api

# Test autonomous endpoint
curl http://localhost:8000/api/autonomous/status
```

#### Test Dashboard
```bash
cd dashboard
npm run dev
# Open http://localhost:3000/autonomous
```

### 5.3 Documentation Verification

#### Check All .md Files
- ✅ README.md - Complete
- ✅ ARCHITECTURE.md - Complete
- ✅ AGENTS.md - Complete
- ✅ CHANGELOG.md - Complete
- ✅ API_REFERENCE.md - Complete
- ✅ DEPLOYMENT_GUIDE.md - Complete
- ✅ TROUBLESHOOTING.md - Complete
- ✅ CONTRIBUTING.md - Complete

---

## Phase 6: Execution Timeline

### Day 1: Audit & Archive
- [ ] Complete file inventory
- [ ] Identify files to archive
- [ ] Execute archive script
- [ ] Verify archive structure

### Day 2: Code Organization
- [ ] Remove dead code
- [ ] Consolidate duplicates
- [ ] Fix naming conventions
- [ ] Fix broken dependencies

### Day 3: Documentation (Core)
- [ ] Update README.md
- [ ] Update ARCHITECTURE.md
- [ ] Update AGENTS.md
- [ ] Update CHANGELOG.md

### Day 4: Documentation (Extended)
- [ ] Create API_REFERENCE.md
- [ ] Create DEPLOYMENT_GUIDE.md
- [ ] Create TROUBLESHOOTING.md
- [ ] Create CONTRIBUTING.md

### Day 5: Verification
- [ ] Run backend tests
- [ ] Build frontend
- [ ] Test autonomous loop
- [ ] Verify documentation

---

## Phase 7: Success Criteria

### Archive Success
- [ ] All `__pycache__` archived
- [ ] All old logs archived
- [ ] All temp files archived
- [ ] Archive structure documented

### Code Quality Success
- [ ] Zero unused imports
- [ ] Zero dead code warnings
- [ ] Consistent naming conventions
- [ ] No broken dependencies

### Documentation Success
- [ ] All core .md files updated
- [ ] All extended docs created
- [ ] No broken links
- [ ] All examples tested

### Build Success
- [ ] Backend tests pass (100%)
- [ ] Frontend builds (30/30 pages)
- [ ] Autonomous loop works
- [ ] Dashboard loads

---

## Phase 8: Deliverables

### Files Created
1. `archive/2026-07-28-cleanup/` - Archive structure
2. `docs/API_REFERENCE.md` - Complete API docs
3. `docs/DEPLOYMENT_GUIDE.md` - Deployment guide
4. `docs/TROUBLESHOOTING.md` - Troubleshooting guide
5. `docs/CONTRIBUTING.md` - Contributing guide
6. `CLEANUP_REPORT.md` - Final cleanup report

### Files Updated
1. `README.md` - Complete overhaul
2. `ARCHITECTURE.md` - Add diagrams
3. `AGENTS.md` - Add instructions
4. `CHANGELOG.md` - Add v6.2.0 entries
5. All other outdated .md files

### Metrics
- **Files Archived**: ~10,000 (caches, logs, temp)
- **Dead Code Removed**: ~500 lines
- **Documentation Added**: ~5,000 lines
- **Build Time**: <15s (frontend)
- **Test Coverage**: >50% (CI requirement)

---

## Phase 9: Risk Mitigation

### Risks
1. **Archiving active files** - Mitigation: Review before archive
2. **Breaking dependencies** - Mitigation: Run tests after each change
3. **Documentation errors** - Mitigation: Test all code examples
4. **Build failures** - Mitigation: Verify after each phase

### Rollback Plan
- All archived files in `archive/2026-07-28-cleanup/`
- Can restore by moving back to original location
- Git history preserved

---

## Phase 10: Final Checklist

### Pre-Execution
- [ ] Backup repository (git commit)
- [ ] Review archive list
- [ ] Verify test suite passes
- [ ] Verify build succeeds

### During Execution
- [ ] Archive caches
- [ ] Archive old logs
- [ ] Remove dead code
- [ ] Update documentation
- [ ] Run tests after each phase
- [ ] Build after each phase

### Post-Execution
- [ ] Final test run
- [ ] Final build verification
- [ ] Documentation review
- [ ] Create cleanup report
- [ ] Commit changes

---

## Conclusion

This comprehensive cleanup and documentation plan will:
1. **Organize** the codebase (archive obsolete files)
2. **Improve** code quality (remove dead code, fix naming)
3. **Complete** documentation (all .md files updated)
4. **Verify** production readiness (100/100 score)
5. **Prepare** for autonomous operation (24/7 hedge fund)

**Status**: Ready for autonomous execution  
**Estimated Duration**: 5 days  
**Risk Level**: Low (archive-only, no deletion)  
**Final Outcome**: Production-ready Autonomous Quant Hedge Fund

---

**Plan Created**: 2026-07-28  
**Version**: v6.2.0 Autonomous  
**Status**: ✅ READY FOR EXECUTION
