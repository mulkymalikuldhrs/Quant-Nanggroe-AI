# Quant Nanggroe AI — AI-Engineering-OS Constitution

## Project State: A (Production Live)
- **Purpose:** Quant Nanggroe AI v4.0.0 — Autonomous Alpha Destruction OS. Regime-based trading strategy with paper trading daemon and live alpha validation.
- **Language:** Python 3.11+
- **Framework:** FastAPI backend, Next.js dashboard, LangGraph agent orchestration
- **Entry points:** `scripts/launch_qna.bat`, `uvicorn quant_nanggroe.api.app:app`

## Key Files
- `README.md` — Project overview, architecture, quick start
- `QUANT_NANGRAOE_COMPLETE.md` — Full documentation, API reference, architecture
- `DHAHER_LABS_MANDATE.md` — Constitutional mandate
- `CLAUDE.md` — AI agent instructions
- `SECURITY.md` — Security policies and vulnerability reporting
- `pyproject.toml` — Project config, dependencies, tool settings
- `Makefile` — Test, lint, clean commands
- `install.sh` — One-command installer
- `deploy/` — Docker, docker-compose, startup scripts
- `.github/workflows/` — CI/CD pipelines (ci.yml, security-scan.yml, etc.)
- `.gitlab-ci.yml` — GitLab CI pipeline

## Commands
```bash
# Install
pip install -e ".[dev]"        # Dev install with test/lint deps
bash install.sh                  # One-command production install

# Dev
make lint                        # Ruff check
make test                        # Run all tests (1513+)
python3 -m uvicorn quant_nanggroe.api.app:app --host 0.0.0.0 --port 8000

# Paper trading
scripts/launch_qna.bat             # One-click launcher
python scripts/qna-paper-daemon.py --interval 3600  # Manual daemon start
```

## Test Suite
- **1513+ tests** across 65 test directories (collection: 5244)
- Run via: `make test`
- CI runs: `pytest tests/ --cov=quant_nanggroe --cov-report=term --cov-report=xml`
- Markers: `slow`, `integration`

## Agent Rules
- AI-Engineering-OS v1.0 applies: Understand before changing. Never invent requirements.
- Ponytail: stdlib first, YAGNI, min code.
- Update this file if you add significant commands or change the project structure.
- NEVER commit real API keys or secrets. Use `.env.example` with placeholder values.
- Run `make lint && make test` before any commit affecting Python code.

## REALIZATION MANDATE

This repository is part of the **DHAHER LABS** autonomous ecosystem.
It is a **REAL production system** — not a simulation, not a toy, not a placeholder.

See the [Autonomous-Organism Manifesto](https://dhaherlabsos.vercel.app/manifesto) for the full declaration.
See [System Status](https://dhaherlabsos.vercel.app/status) for live health checks.

---

