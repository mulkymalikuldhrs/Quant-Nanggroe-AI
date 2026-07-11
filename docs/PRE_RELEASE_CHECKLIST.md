# Pre-Release Checklist — Quant Nanggroe AI v1.0.0-rc.1

## 1. Code Quality

- [ ] `ruff check .` passes with zero errors
- [ ] `ruff format --check .` confirms formatting
- [ ] `mypy quant_nanggroe/` passes with zero errors (or only known ignores)
- [ ] No `# type: ignore` without accompanying comment
- [ ] No unused imports (`ruff check --select F401`)
- [ ] No bare `except Exception` without logging
- [ ] All public functions have docstrings
- [ ] All type hints are present on public API surface

## 2. Test Coverage

- [ ] `pytest tests/ -v --tb=short` — all tests pass
- [ ] `pytest tests/ --cov=quant_nanggroe --cov-report=term-missing` — coverage ≥ 80%
- [ ] Critical paths have tests: kelly, regime, stress_testing, backtest, risk
- [ ] API endpoint tests pass (health, metrics, readiness, liveness)
- [ ] CLI commands smoke-test (qna kelly, qna regime, qna health, bh status)

## 3. Security Audit

- [ ] `python scripts/security_audit.py` — zero critical/high findings
- [ ] No hardcoded secrets in source (verify with audit script)
- [ ] `.env` file is in `.gitignore`
- [ ] No `shell=True` in subprocess calls
- [ ] No `eval()` / `exec()` in production code paths
- [ ] SQL queries use parameterized statements
- [ ] API authentication middleware is enabled (or documented as optional)
- [ ] CORS origins are explicitly configured (no `["*"]` with credentials)

## 4. Documentation

- [ ] README.md is up to date with installation and usage instructions
- [ ] ARCHITECTURE.md reflects current system design
- [ ] CHANGELOG.md includes v1.0.0-rc.1 entry
- [ ] All public API functions are documented
- [ ] CLI help text is accurate (`qna --help`, `bh --help`)
- [ ] docs/PRE_RELEASE_CHECKLIST.md exists (this file)
- [ ] docs/RUNBOOK.md exists
- [ ] CONTRIBUTING.md is current

## 5. Performance Benchmarks

- [ ] Kelly computation < 100ms for single symbol
- [ ] Regime detection < 500ms for 252 data points
- [ ] Stress test (10k sims) < 5s
- [ ] Backtest engine initializes < 1s
- [ ] Health endpoint responds < 200ms
- [ ] API server starts < 5s
- [ ] Memory usage stable under 512MB for typical workload

## 6. Deployment Validation

- [ ] `docker build -t quant-nanggroe-ai .` succeeds
- [ ] `docker compose up` starts all services
- [ ] Health endpoint returns `{"status": "healthy"}`
- [ ] Metrics endpoint returns Prometheus format
- [ ] Readiness probe returns correct status
- [ ] Liveness probe responds correctly
- [ ] E2B sandbox configuration is valid (`e2b.toml`)
- [ ] All environment variables documented in `.env.example`

## 7. Dependencies

- [ ] `pip install -e .` succeeds cleanly
- [ ] No dependency version conflicts
- [ ] Optional dependencies documented in `pyproject.toml`
- [ ] Lock file is up to date (if applicable)
- [ ] No known critical CVEs in dependencies

## 8. Git & Release

- [ ] All changes committed (no uncommitted files)
- [ ] Commit history is clean (no WIP commits on main)
- [ ] Tag created: `git tag v1.0.0-rc.1`
- [ ] CHANGELOG.md includes date and version
- [ ] No secrets committed (run `git log --all --full-history -p | grep -i "api_key\|secret\|password"`)

## Sign-Off

| Role | Name | Date | Status |
|------|------|------|--------|
| Lead Developer | | | |
| QA Engineer | | | |
| Security Reviewer | | | |
| DevOps | | | |
