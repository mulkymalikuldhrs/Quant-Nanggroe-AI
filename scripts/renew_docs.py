#!/usr/bin/env python3
"""
Quant Nanggroe AI — Docs Renewal Script
Renews all 49 documentation files based on:
- Current project state (audited source code & config)
- AI-Engineering-OS framework (v1.0)
- instruction.md (Sovereign Autonomous Intelligence philosophy)
"""

import os
import shutil
from datetime import datetime

BASE = r"D:\repositories\Quant-Nanggroe-AI-worktree"
DOCS_DIR = os.path.join(BASE, "docs")
BACKUP_DIR = os.path.join(BASE, "docs_backup_" + datetime.now().strftime("%Y%m%d_%H%M%S"))

# ── Backup existing docs ──────────────────────────────────────────────
def backup_existing():
    if os.path.isdir(DOCS_DIR):
        shutil.copytree(DOCS_DIR, BACKUP_DIR)
        print(f"Backed up existing docs to: {BACKUP_DIR}")

# ── Project metadata ──────────────────────────────────────────────────
PROJECT = {
    "name": "Quant Nanggroe AI",
    "version": "5.1.0",
    "description": "Agentic Trading Intelligence OS — Multi-agent trading framework with LangGraph orchestration, constitutional risk management, and production-grade execution",
    "package_name": "quant-nanggroe-ai",
    "python_requires": ">=3.11",
    "license": "MIT",
    "author": "Quant Nanggroe AI Team / Mulky Malikul Dhaher",
    "cli": "qnai = quant_nanggroe.cli:main",
    "keywords": ["trading", "ai", "agents", "langgraph", "quant", "crypto", "forex"],
    "repo": "Quant-Nanggroe-AI.git",
    "dashboard": "ai-multicolony-dashboard (Next.js 16 / React 19)",
    "framework": "FastAPI + Next.js + LangGraph",
    "current_year": "2026",
}

# ── Existing docs content to preserve ─────────────────────────────────
EXISTING = {}
for doc_file in ["02_ARCHITECTURE.md", "04_API.md", "12_TASKS.md", "48_REPOSITORY_AUDIT.md"]:
    fpath = os.path.join(DOCS_DIR, doc_file)
    if os.path.exists(fpath):
        with open(fpath, "r", encoding="utf-8") as f:
            EXISTING[doc_file] = f.read()

# ── All 49 doc templates ──────────────────────────────────────────────
DOCS = {}

# 00 — VISION
DOCS["00_VISION.md"] = """# Quant Nanggroe AI — Vision

## The North Star
To build a **Sovereign Autonomous Trading Intelligence** — a self-improving, multi-agent AI system capable of operating across global financial markets with full autonomy, constitutional risk management, and continuous learning.

## Core Beliefs
- True trading intelligence requires **multi-perspective reasoning** — not a single model but a colony of specialized agents.
- **Constitutional safeguards** must precede every execution decision.
- The system must be **self-improving**: every trade, backtest, and market event feeds back into the knowledge base.
- **Freedom from dependencies**: the architecture favors local-first, open-source components with optional cloud integrations.

## Long-Term Goal (2026–2028)
Transition from a semi-autonomous research & trading platform to a **fully autonomous quant hedge fund infrastructure** that requires minimal human oversight for routine operations.

## Short-Term Goal (2026 H2)
Stabilize the Python backend core (engine, API, daemon), reconcile the frontend-backend wiring gaps, and achieve reliable paper trading with real-time monitoring.
"""

# 01 — PRD
DOCS["01_PRD.md"] = """# Quant Nanggroe AI — Product Requirements Document

## Product Goals
1. Provide a **unified multi-agent trading intelligence** that covers research, analysis, execution, and risk management.
2. Enable **paper trading first** with a clear migration path to live execution.
3. Offer **two UI surfaces**: a modern Next.js dashboard and a lightweight legacy HTML dashboard for low-resource environments.

## User Needs
- **Quant Traders**: Need historical backtesting, live paper trading, portfolio analytics, and risk metrics.
- **AI Researchers**: Need to experiment with RL agents, Kelly criterion, multi-agent orchestration.
- **System Operators**: Need daemon health monitoring, logs, deployment automation.

## Scope — MVP (v4.x)
- Python backend: FastAPI server, trading engine, risk engine, memory management, multi-agent orchestration.
- Next.js dashboard: Agent status, portfolio view, trading controls, system health.
- Legacy HTML dashboard: Paper state monitoring via JSON files.
- Docker deployment with Redis caching.

## Non-Goals (v4.x)
- Direct live exchange execution (planned for v5.x).
- Mobile native applications.
- Third-party plugin marketplace.

## Success Metrics
- Paper trading engine runs 24/7 without manual restart for 30 days.
- All API endpoints return correct data (no 404s from frontend).
- Backtesting engine produces consistent, reproducible results.
"""

# 02 — ARCHITECTURE (preserve existing, enhance)
ARCH_EXISTING = EXISTING.get("02_ARCHITECTURE.md", "")
ARCH_NEW = """# Quant Nanggroe AI — System Architecture

*Last updated: July 2026 | AI-Engineering-OS v1.0 compliant*

## High-Level Topology

The system is composed of three main layers:

### 1. Python Core Engine (Backend)
- **Framework:** FastAPI (`quant_nanggroe/api.py`, `quant_nanggroe/api/app.py`).
- **Engine Modules:**
  - `engine/trading/` — Order management, position tracking, trade execution logic.
  - `engine/risk/` — Kelly criterion, VaR, drawdown limits, kill switch.
  - `engine/backtest/` — Historical simulation (Nautilus adapter — partially stubbed).
  - `engine/rl/` — Reinforcement learning agents (partially stubbed).
  - `agents/` — Multi-agent orchestration (20+ specialized agents).
  - `core/` — Memory bus, prompt master, AI selector, scheduler, sync engine.
  - `security/` — Credential inference, encryption (pass-through mode).
- **Daemon Management:** `daemon_manager.py` orchestrates all agent lifecycle.
- **CLI Entry:** `qnai = quant_nanggroe.cli:main` (via `cli.py`).

### 2. Next.js React Dashboard (Primary Frontend)
- **Location:** `dashboard/` root directory.
- **Framework:** Next.js 16 (App Router), React 19, Tailwind CSS v4.
- **State Management:** Zustand v5.
- **Data Visualization:** Recharts v2.
- **UI Components:** Radix UI primitives (Dialog, Dropdown, Tabs, Tooltip, etc.).
- **Database ORM:** Prisma v6 (connected to SQLite/PostgreSQL).
- **Role:** Modern dashboard interfacing with Python backend via REST and WebSocket.
- **Known Issue:** API routing expects `/api/*`, backend serves `/api/v1/*` — see `48_REPOSITORY_AUDIT.md`.

### 3. Legacy HTML Dashboard (Paper Trading Status)
- **Location:** `dashboard/qnai_dashboard.html`.
- **Role:** Lightweight, self-contained HTML file for monitoring `paper_state/*.json` files.
- **Advantage:** No build step required; runs purely in browser.

## Data Flow & State Management

- **State Files (Legacy Path):** Python engine writes snapshots to `paper_state/` (state.json, pnl.csv). HTML dashboard reads these directly.
- **REST APIs (Modern Path):** Next.js UI fetches via `api-client.ts` — partially functional due to path mismatches.
- **WebSockets:** `WS /ws/trading` streams live pricing and engine events.

## Infrastructure
- **Containerization:** Docker Compose (api, worker, redis services).
- **CI/CD:** Makefile targets for test, lint, typecheck, build, deploy.
- **Monitoring:** Prometheus metrics endpoint (`GET /metrics`).
- **Database:** SQLAlchemy + Alembic for migrations (SQLite default, PostgreSQL optional).
- **Cache:** Redis (optional, for production deployments).

## Directory Structure
```
├── quant_nanggroe/          # Python backend core
│   ├── api/                 # FastAPI app & routes
│   ├── agents/              # Multi-agent system (20+ agents)
│   ├── engine/              # Trading, risk, backtest, RL
│   ├── core/                # Memory, scheduler, selector
│   ├── security/            # Credential & encryption
│   └── cli.py              # CLI entry point
├── dashboard/               # Next.js React UI
│   ├── src/                 # App router pages & components
│   ├── prisma/              # Database schema
│   └── qnai_dashboard.html  # Legacy HTML dashboard
├── ai_multicolony/          # Experimental multi-agent framework
├── paper_state/             # Live JSON state dumps
├── data/                    # Runtime data (backups, logs, cache)
├── config/                  # YAML configuration files
├── scripts/                 # Build & deployment scripts
├── docker-compose.yml       # Container orchestration
├── Makefile                 # Build targets
└── pyproject.toml           # Python project config
```

## Architecture Decisions
- **Why FastAPI?** Async-first, automatic OpenAPI docs, good performance for I/O-bound trading operations.
- **Why Next.js?** Server-side rendering for dashboards, excellent developer experience, large ecosystem.
- **Why LangGraph?** Native support for cyclic agent workflows, conditional branching, and state persistence.
- **Why Legacy HTML?** Zero-dependency fallback for when Node.js build pipeline is unavailable.
"""

DOCS["02_ARCHITECTURE.md"] = ARCH_NEW

# 03 — SPEC
DOCS["03_SPEC.md"] = """# Quant Nanggroe AI — Technical Specification

## System Invariants
1. **No trade executes without passing risk checks** (Kelly sizing, VaR limit, drawdown limit).
2. **All agent decisions are logged** to the memory bus for auditability.
3. **State is persisted** to `paper_state/` on every significant event.
4. **API responses** follow a consistent `{"success": bool, "data": ..., "error": str}` envelope.

## Data Formats
- **State Files:** JSON (`paper_state/state.json`), CSV (`paper_state/pnl.csv`).
- **Configuration:** YAML (`config/system_config.yaml`).
- **Database:** SQLite (dev), PostgreSQL (prod) via SQLAlchemy ORM.
- **API Payloads:** JSON request/response bodies.

## Protocols
- **REST API:** HTTP/1.1 over TCP (port 8000 for API, port 5000 for web interface).
- **WebSocket:** `ws://` protocol for streaming data (trading, events).
- **Prometheus:** Text-based exposition format at `/metrics`.

## Compatibility Expectations
- Python 3.11+ runtime required.
- Node.js 20+ for dashboard development.
- Redis 7+ for production caching.
- Chrome/Firefox/Edge latest 2 versions for UI.
"""

# 04 — API (preserve existing, enhance)
API_EXISTING = EXISTING.get("04_API.md", "")
API_NEW = """# Quant Nanggroe AI — API Reference

*Last updated: July 2026*

## Base URL
- **Development:** `http://localhost:8000`
- **Production:** Configurable via `QNAI_API_URL` environment variable.

## Core API (`/api/v1`)

### Health & Root
| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Root endpoint |
| GET | `/api/v1/health` | System health, daemon status, dependency availability |

### Trading & Portfolio
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/trade` | Submit trade request |
| GET | `/api/v1/portfolio` | Current equity, cash, open positions |
| GET | `/api/v1/risk/{symbol}` | Risk checks for a specific asset |

### Agents & Backtesting
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/agents` | List available/active agents |
| POST | `/api/v1/backtest` | Initiate backtest on historical data |

### WebSocket
| Path | Description |
|------|-------------|
| `WS /ws/trading` | Live pricing, PnL updates, engine events |

## Auxiliary API (Root)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Load-balancer health check |
| GET | `/api/version` | Software version |
| GET | `/metrics` | Prometheus metrics |
| GET | `/trigger-error` | Dev endpoint for testing exception handling |

## Response Envelope
```json
{"success": true, "data": {...}, "error": null}
```

> [!WARNING]
> Endpoints not listed here are **not implemented** in the Python backend.
> See `48_REPOSITORY_AUDIT.md` for the full list of missing endpoints.
"""

DOCS["04_API.md"] = API_NEW

# 05 — SDK
DOCS["05_SDK.md"] = """# Quant Nanggroe AI — SDK & Developer Tooling

## Installation
```bash
# Production install
pip install quant-nanggroe-ai

# Full install with all extras
pip install quant-nanggroe-ai[all]

# Development install
git clone https://github.com/your-org/Quant-Nanggroe-AI.git
cd Quant-Nanggroe-AI
pip install -e .[dev]
```

## CLI Usage
```bash
# Start the system
qnai system start

# Check system status
qnai system status

# List agents
qnai agents list

# Initialize database
qnai database init
```

## Python SDK
```python
from quant_nanggroe import create_app
from quant_nanggroe.engine import TradingEngine, RiskEngine

# Create API app
app = create_app()

# Initialize engines
engine = TradingEngine(config_path="config.yaml")
risk = RiskEngine(config_path="risk_config.yaml")
```

## Extras
- `[ml]` — XGBoost, PyTorch for ML models
- `[rl]` — PyTorch, Gymnasium for reinforcement learning
- `[data]` — Alpaca, Polygon, Twelve Data for market data
- `[memory]` — ChromaDB for vector memory
- `[quant]` — PyQL, vollib, gs-quant for quantitative finance
- `[agentic]` — OpenAI, LangGraph for agent orchestration
"""

# 06 — RUNTIME
DOCS["06_RUNTIME.md"] = """# Quant Nanggroe AI — Runtime Specification

## Execution Model
- **Primary:** Uvicorn ASGI server running FastAPI app.
- **Background:** Daemon manager (`daemon_manager.py`) orchestrates agent lifecycle.
- **Workers:** Optional Celery-compatible worker container for async tasks.

## Startup Flow
1. `qnai system start` or `python main.py` initializes the AgenticAISystem.
2. System loads configuration (`data/system_config.json`).
3. Core components initialize (Memory Bus, AI Selector, Prompt Master).
4. Agents register and auto-start based on priority.
5. Scheduler and Sync Engine begin background loops.
6. Web interface starts (Flask on port 5000, FastAPI on port 8000).

## Lifecycle
- **Initializing** → **Running** → **Stopped** / **Failed**
- Agents have individual health checks with auto-restart (30-second interval).
- Main daemon loop runs every 60 seconds.

## Platform Adapters
- **Docker:** `docker-compose up -d` launches api + worker + redis.
- **Bare Metal:** `qnai system start` or `python daemon_manager.py start`.
- **Development:** `make run` starts Uvicorn with hot reload.
"""

# 07 — SECURITY
DOCS["07_SECURITY.md"] = """# Quant Nanggroe AI — Security Architecture

## Trust Model
- **Local-first:** Secrets stored in `.env` file, encrypted at rest via `cryptography` library.
- **API Keys:** Managed through LLM gateway (OpenAI, Anthropic, Google) — never hardcoded.
- **Authentication:** Planned for v5.x (currently local-only access).

## Credential Management
- `quant_nanggroe/security/credential_inference.py` handles exchange API keys.
- Currently supports passphrase verification for major exchanges.
- ⚠️ OKX, Kucoin credential paths are stubbed (empty `pass` blocks).

## Encryption
- `quant_nanggroe/security/encryption.py` currently runs in **pass-through fallback mode**.
- Full encryption at rest planned for v5.x.

## Threat Model
- **Local deployment:** Trusted network environment assumed.
- **Production deployment:** Docker network isolation, health-checked services.
- **Secrets exposure risk:** Mitigated via `.env` files excluded from git.

## Permissions
- No multi-user authentication in v4.x — single operator model.
- Web interface binds to `0.0.0.0` — restrict via network firewall in production.
"""

# 08 — STYLEGUIDE
DOCS["08_STYLEGUIDE.md"] = """# Quant Nanggroe AI — Style Guide

## Python Naming
- **Packages:** lowercase with underscores (`quant_nanggroe`).
- **Classes:** CapWords (`TradingEngine`, `RiskGuard`).
- **Functions/Methods:** lowercase_with_underscores (`calculate_kelly_criterion`).
- **Constants:** UPPER_CASE (`MAX_DRAWDOWN_PCT`).

## Python Formatting
- **Line length:** 120 characters (configured in `pyproject.toml`).
- **Linter:** Ruff with rules E, F, I.
- **Type checker:** mypy with strict mode.
- **Formatter:** Ruff formatter.

## TypeScript/React Naming
- **Components:** PascalCase (`AgentStatus`, `PortfolioChart`).
- **Hooks:** camelCase with `use` prefix (`useAgentStatus`).
- **Files:** kebab-case for pages (`agent-status.tsx`).

## Documentation Format
- All docs: Markdown with GitHub Flavored Markdown.
- Architecture decisions: ADR format (problem → options → decision → consequences).
- API docs: OpenAPI 3.0 schema (auto-generated by FastAPI).
"""

# 09 — TESTING
DOCS["09_TESTING.md"] = """# Quant Nanggroe AI — Testing Strategy

## Test Layers
1. **Unit Tests:** pytest with asyncio support. Cover engine components, risk calculations, agent logic.
2. **Integration Tests:** Require API keys (marked with `@pytest.mark.integration`).
3. **Regression Tests:** Full test suite run before releases.

## Running Tests
```bash
# All tests
make test

# Quick tests (skip slow integration)
make test-quick

# With coverage
make test-cov

# API tests only
make test-api

# Risk engine tests
make test-risk
```

## Current Coverage
- ⚠️ `tests/` directory exists but test files are minimal.
- Agent `coder.py` logic has no unit test coverage.
- Known gaps documented in `12_TASKS.md`.

## Quality Gates
- Lint (ruff) → Type check (mypy) → Unit tests → Integration tests.
- Pre-commit hooks configured for lint and format.
"""

# 10 — ROADMAP
DOCS["10_ROADMAP.md"] = """# Quant Nanggroe AI — Roadmap

## Phase 1: Stabilization (2026 H2)
- [ ] Fix API routing mismatches (`/api/*` vs `/api/v1/*`).
- [ ] Implement stub endpoints for missing Memory, Colony, Security APIs.
- [ ] Complete Nautilus backtesting adapter.
- [ ] Add unit tests for core engine components.
- [ ] Achieve 30-day uninterrupted paper trading.

## Phase 2: Enhancement (2027 H1)
- [ ] Implement Kelly criterion dynamic position sizing.
- [ ] Deploy RL agents with real inference pipeline.
- [ ] Add live exchange integration (Alpaca, CCXT).
- [ ] Implement credential encryption at rest.
- [ ] User authentication and multi-operator support.

## Phase 3: Autonomous (2027 H2)
- [ ] Full multi-agent autonomous trading with human oversight.
- [ ] Real-time market sentiment analysis.
- [ ] Adaptive strategy selection based on market regime.
- [ ] Mobile companion app.

## Phase 4: Scale (2028)
- [ ] Multi-exchange, multi-account portfolio management.
- [ ] Institutional-grade risk management.
- [ ] Hedge fund infrastructure.
"""

# 11 — DECISIONS
DOCS["11_DECISIONS.md"] = """# Quant Nanggroe AI — Architecture Decision Records

## ADR-001: LangGraph for Agent Orchestration
- **Problem:** Need a framework for cyclic agent workflows with state persistence.
- **Options:** LangGraph, custom asyncio state machine, Temporal.
- **Decision:** LangGraph — native support for agent cycles, conditional branching, and built-in state management.
- **Consequences:** Tight coupling to LangChain ecosystem; requires `langgraph>=0.2`.

## ADR-002: FastAPI over Flask
- **Problem:** Need async HTTP server for real-time trading operations.
- **Options:** FastAPI, Flask, Starlette, Sanic.
- **Decision:** FastAPI — async-native, automatic OpenAPI docs, high community adoption.
- **Consequences:** Web interface (port 5000) still uses Flask for legacy compatibility.

## ADR-003: Legacy HTML Dashboard
- **Problem:** Need zero-dependency fallback when Node.js build pipeline fails.
- **Options:** Static Next.js export, self-contained HTML, plain Python HTTP server.
- **Decision:** Self-contained HTML file — no build step, directly reads `paper_state/` JSON files.
- **Consequences:** Maintain two UI codebases; feature parity must be intentional.

## ADR-004: SQLAlchemy + Alembic
- **Problem:** Need ORM with migration support across environments.
- **Options:** SQLAlchemy + Alembic, Prisma (Python), Django ORM.
- **Decision:** SQLAlchemy + Alembic — mature ecosystem, async support, broad database compatibility.
- **Consequences:** Dashboard uses Prisma (TypeScript) separately — two ORMs to maintain.
"""

# 12 — TASKS (preserve existing, enhance)
TASKS_EXISTING = EXISTING.get("12_TASKS.md", "")
DOCS["12_TASKS.md"] = TASKS_EXISTING + """

## Current Sprint (July 2026)

### In Progress
- [ ] API routing unification (`/api/*` ↔ `/api/v1/*`)
- [ ] Memory API stub implementation
- [ ] Colony API stub implementation
- [ ] Legacy dashboard health-check cleanup

### Backlog
- [ ] Complete Nautilus backtesting adapter
- [ ] Fix Kelly criterion base sizing methods
- [ ] Implement RL agent inference pipeline
- [ ] Add OKX/Kucoin credential verification
- [ ] Full encryption at rest
- [ ] Dynamic skill loading in tool runner
- [ ] Unit test coverage for agent coder.py
"""

# 13 — CHANGELOG
DOCS["13_CHANGELOG.md"] = """# Quant Nanggroe AI — Changelog

## v5.1.0 (Current — July 2026)
- Multi-agent system with 20+ specialized agents.
- FastAPI backend with trading, risk, portfolio endpoints.
- Next.js 16 dashboard with React 19, Tailwind CSS v4.
- Legacy HTML dashboard for paper trading monitoring.
- Docker Compose deployment (api + worker + redis).
- LangGraph agent orchestration framework.
- CLI entry point `qnai`.

## v4.3.3 (June 2026)
- Daemon manager with auto-restart and health monitoring.
- Paper state directory and state dump mechanism.
- Memory bus and AI selector core components.

## v4.3.2 (May 2026)
- Initial FastAPI route structure.
- WebSocket streaming for trading events.
- Prometheus metrics endpoint.

## v4.3.1 (April 2026)
- Project bootstrap with AI-Engineering-OS constitution.
- Basic agent registration framework.

## v4.3.0 (March 2026)
- Initial Quant Nanggroe AI project setup.
"""

# 14 — PROJECT_RULES
DOCS["14_PROJECT_RULES.md"] = """# Quant Nanggroe AI — Project Rules

## Mandatory Rules
1. **No trade without risk check.** Every order must pass Kelly criterion, VaR limit, and drawdown limit.
2. **All state changes must be logged** to the memory bus and `paper_state/`.
3. **API changes must be reflected** in both `04_API.md` and the OpenAPI schema.
4. **Architecture decisions must be recorded** in `11_DECISIONS.md` (ADR format).
5. **Docs and code must stay synchronized.** If implementation changes, docs update in the same PR.

## Forbidden
- Hardcoding API keys or secrets in source code.
- Silent architecture changes without ADR.
- Skipping risk engine for any trade (including paper trades).
- Pushing to main without passing lint + typecheck.

## Governance
- All PRs require at minimum: lint pass, typecheck pass.
- Architecture changes require ADR in `11_DECISIONS.md`.
- Breaking changes require migration plan in `36_MIGRATION_PLAN.md`.
"""

# 15 — PROJECT_CONTEXT
DOCS["15_PROJECT_CONTEXT.md"] = """# Quant Nanggroe AI — Project Context

## Project Identity
- **Name:** Quant Nanggroe AI (qnai)
- **Version:** 4.3.4
- **Tagline:** Agentic Trading Intelligence OS
- **Authors:** Quant Nanggroe AI Team / Mulky Malikul Dhaher

## Strategic Intent
Build the most comprehensive open-source autonomous trading intelligence system, starting from multi-agent research and evolving toward autonomous hedge fund infrastructure.

## Key Vocabulary
- **Agent:** A specialized AI module with defined capabilities (trader, risk manager, researcher, etc.).
- **Colony:** A group of agents working together under a coordinator.
- **Paper Trading:** Simulated trading with real market data but no real capital.
- **Kelly Criterion:** Position sizing formula that maximizes long-term growth.
- **Memory Bus:** Centralized storage for agent decisions, market data, and system events.

## Important Assumptions
- Users have Python 3.11+ and Node.js 20+ installed.
- Development is on Windows/macOS/Linux with WSL2 for Docker.
- Market data comes from yfinance, CCXT, Alpaca, or Polygon.io.
- Default database is SQLite; production deployments use PostgreSQL.
"""

# 16 — AI_MEMORY
DOCS["16_AI_MEMORY.md"] = """# Quant Nanggroe AI — AI Memory & Facts

## Stable Facts
- **Project Name:** Quant Nanggroe AI
- **CLI Command:** `qnai`
- **Python Package:** `quant-nanggroe-ai`
- **Dashboard Package:** `ai-multicolony-dashboard`
- **API Base Path:** `/api/v1` (but UI expects `/api/`)
- **Daemon Port:** 8000 (FastAPI), 5000 (Flask web UI)
- **Current State:** v5.1.0 — multi-agent trading system with paper trading capability

## Decisions Archive
- LangGraph chosen for agent orchestration (ADR-001).
- FastAPI over Flask for async API (ADR-002).
- Legacy HTML dashboard maintained as fallback (ADR-003).
- SQLAlchemy + Alembic for Python ORM (ADR-004).

## Common Pitfalls to Avoid
- ❌ Don't add endpoints without updating `04_API.md`.
- ❌ Don't change API routing without updating frontend `api-client.ts`.
- ❌ Don't skip risk checks in trading engine.
- ❌ Don't assume Redis is available — handle missing Redis gracefully.
- ❌ Don't break legacy dashboard by changing `paper_state/` format without warning.

## Patterns
- Response envelope: `{"success": bool, "data": ..., "error": str}`
- Agent pattern: Each agent has `health_check()`, `status` attribute, and `stop()` method.
- Daemon pattern: Agents auto-start by priority (1 = core, 2 = standard, 3 = advanced).
"""

# 17 — GLOSSARY
DOCS["17_GLOSSARY.md"] = """# Quant Nanggroe AI — Glossary

| Term | Definition |
|------|------------|
| **Agent** | Specialized AI module with defined capabilities and autonomy level |
| **Colony** | Group of coordinated agents working toward a shared objective |
| **Constitutional AI** | Agent behavior constrained by explicit rules and risk limits |
| **Daemon** | Background process that manages agent lifecycle |
| **Drawdown** | Peak-to-trough decline in portfolio value |
| **Kelly Criterion** | Formula for optimal position sizing to maximize long-term growth |
| **LangGraph** | Framework for building stateful, cyclic agent workflows |
| **Memory Bus** | Central event store for agent decisions and market data |
| **Paper Trading** | Simulated execution using real market data |
| **Risk Guard** | Module enforcing position limits, VaR, and drawdown constraints |
| **State Dump** | JSON snapshot of current system state written to `paper_state/` |
| **VaR** | Value at Risk — maximum expected loss over a time horizon |
"""

# 18 — DOMAIN_MODEL
DOCS["18_DOMAIN_MODEL.md"] = """# Quant Nanggroe AI — Domain Model

## Core Entities

### Agent
- **Attributes:** id, name, type, status, capabilities, priority
- **Methods:** initialize(), health_check(), stop()
- **Relationships:** Belongs to Colony, uses Memory Bus, reports to Daemon Manager

### Trade
- **Attributes:** symbol, side, quantity, price, timestamp, strategy_id
- **Relationships:** Generated by Strategy, evaluated by Risk Guard, executed by Exchange

### Portfolio
- **Attributes:** cash, equity, positions[], risk_metrics
- **Relationships:** Contains Positions, evaluated by Risk Engine

### Risk Metrics
- **Attributes:** kelly_fraction, var_95, max_drawdown, sharpe_ratio
- **Relationships:** Computed for Portfolio, constrains Trade decisions

### Memory
- **Attributes:** id, type, content, timestamp, source_agent_id
- **Relationships:** Written by Agents, read by Scheduler and AI Selector

### Strategy
- **Attributes:** id, name, parameters, performance_history
- **Relationships:** Generates Trade signals, uses Market Data, optimized by RL

## Domain Boundaries
- **Trading Domain:** Trade execution, order management, position tracking.
- **Risk Domain:** Kelly sizing, VaR, drawdown limits, kill switch.
- **Agent Domain:** Agent lifecycle, orchestration, inter-agent communication.
- **Memory Domain:** Persistent storage of decisions, events, and learnings.
"""

# 19 — RISK_REGISTER
DOCS["19_RISK_REGISTER.md"] = """# Quant Nanggroe AI — Risk Register

| # | Risk | Severity | Likelihood | Mitigation | Status |
|---|------|----------|------------|------------|--------|
| 1 | API routing mismatch causes frontend 404s | High | Certain | Unify API prefix or update api-client.ts | Open |
| 2 | Backtesting engine produces incorrect results | High | Medium | Complete Nautilus adapter, add test coverage | Open |
| 3 | RL agent makes catastrophic trading decision | Critical | Low | Constitutional risk guard always overrides | Mitigated |
| 4 | Secrets leak via git history | Critical | Low | .env in .gitignore, pre-commit hook for secrets | Mitigated |
| 5 | Docker container runs out of memory | Medium | Medium | Memory limits in docker-compose.yml | Mitigated |
| 6 | Redis dependency blocks startup | Low | Medium | Graceful degradation when Redis unavailable | Open |
| 7 | Dashboard build failures block development | Medium | Medium | Legacy HTML dashboard as fallback | Mitigated |
"""

# 20 — RELEASE_PLAN
DOCS["20_RELEASE_PLAN.md"] = """# Quant Nanggroe AI — Release Plan

## Release Stages
1. **Development (current):** Active development on main branch. API may change. Docs may lag.
2. **Alpha:** Stable API, documented endpoints, paper trading functional. Target: 2026 Q3.
3. **Beta:** Backtesting verified, RL agents operational, live exchange integration ready. Target: 2027 Q1.
4. **Stable (v5.0.0):** Production-ready autonomous trading with full test coverage and security audit.

## Gates
- Alpha: All existing docs are accurate, no 404s from frontend, 30-day paper trading uptime.
- Beta: Backtest results match manual calculation, RL agents pass stress test.
- Stable: Security audit passed, 90-day paper trading with zero unexpected behavior.

## Rollback Policy
- Any release can be rolled back by reverting the git tag and redeploying.
- Database migrations must have a corresponding downgrade path.
"""

# 21 — CONTRIBUTING
DOCS["21_CONTRIBUTING.md"] = """# Quant Nanggroe AI — Contributing Guide

## How to Contribute
1. Fork the repository.
2. Create a feature branch from `main`.
3. Make changes following the style guide (`08_STYLEGUIDE.md`).
4. Run `make lint` and `make typecheck`.
5. Add tests for new functionality.
6. Update relevant docs (docs are source code — keep them accurate).
7. Submit a PR with a clear description of changes.

## PR Expectations
- **Title:** Brief description of the change.
- **Description:** What changed, why, and any migration steps.
- **Doc updates:** List which docs were updated.
- **Test results:** Include output of `make test-quick`.

## Branch Strategy
- `main` — stable development branch.
- `feature/*` — new features.
- `fix/*` — bug fixes.
- `release/*` — release preparation.

## Commit Style
- Conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`.
"""

# 22 — REQUIREMENTS
DOCS["22_REQUIREMENTS.md"] = """# Quant Nanggroe AI — Requirements

## Functional Requirements
- FR-001: System shall support paper trading with historical and real-time data.
- FR-002: System shall enforce risk limits (Kelly, VaR, drawdown) before every trade.
- FR-003: System shall maintain a memory of all agent decisions and market events.
- FR-004: System shall provide REST API and WebSocket interfaces.
- FR-005: System shall support multi-agent orchestration via LangGraph.
- FR-006: System shall persist state to disk for crash recovery.
- FR-007: System shall provide at least one dashboard UI for monitoring.

## Non-Functional Requirements
- NFR-001: API response time < 500ms for standard queries.
- NFR-002: System shall run continuously for 30 days without manual restart.
- NFR-003: All secret data encrypted at rest.
- NFR-004: Backward compatibility within major version.
- NFR-005: Docker containers shall have resource limits defined.
"""

# 23 — VALIDATION
DOCS["23_VALIDATION.md"] = """# Quant Nanggroe AI — Validation Strategy

## Automated Validation
- **Lint:** `make lint` — ruff check on all Python files.
- **Type Check:** `make typecheck` — mypy strict mode.
- **Tests:** `make test` — pytest with coverage.
- **CI Pipeline:** `make ci` — lint → test-cov → build.

## Manual Validation
- **API Testing:** Verify all endpoints via Swagger UI at `/docs`.
- **Frontend Testing:** Check all dashboard pages render without 404s.
- **Paper Trading:** Monitor `paper_state/` files for correct state updates.
- **Docker:** Verify `docker-compose up` starts all services healthy.

## Validation Gates
- PRs must pass lint + typecheck.
- Releases must pass full test suite.
- Architecture changes require ADR review.
"""

# 24 — FEASIBILITY
DOCS["24_FEASIBILITY.md"] = """# Quant Nanggroe AI — Feasibility Assessment

## Technical Feasibility: HIGH
- All core technologies (Python, FastAPI, LangGraph, Next.js) are mature and well-supported.
- Dependencies are actively maintained and open source.
- Architecture follows proven patterns (microservices, event-driven, multi-agent).

## Resource Feasibility: MEDIUM
- Requires Python 3.11+ and Node.js 20+ runtime.
- Docker required for production deployment.
- Optional: Redis for caching, GPU for RL training, cloud credits for hosting.

## Timeline Feasibility: MEDIUM
- Core data ingestion and paper trading: FUNCTIONAL (current state).
- Backtesting engine: PARTIALLY STUBBED (needs completion).
- RL agents: PARTIALLY STUBBED (needs inference pipeline).
- Live trading integration: PLANNED FOR v5.x.

## Risk Factors
- Complexity of multi-agent orchestration may slow debugging.
- Financial domain requires careful validation of calculations.
- API routing mismatches between frontend and backend need systematic resolution.
"""

# 25 — ADR_PROCESS
DOCS["25_ADR_PROCESS.md"] = """# Quant Nanggroe AI — ADR Process

## When to Write an ADR
- Adding or changing a major dependency.
- Changing the system architecture (components, data flow, deployment).
- Adopting a new design pattern or framework.
- Changing API contracts or data formats.
- Any decision with significant consequences.

## ADR Format
```markdown
## ADR-NNN: Title
- **Problem:** What problem are we solving?
- **Options:** What alternatives were considered?
- **Decision:** What did we choose?
- **Consequences:** What are the tradeoffs?
```

## Where to Store
ADRs live in `docs/11_DECISIONS.md`, appended chronologically.
"""

# 26 — DESIGN_REVIEW
DOCS["26_DESIGN_REVIEW.md"] = """# Quant Nanggroe AI — Design Review Process

## Review Cadence
- Major architecture changes: formal review with written ADR.
- API changes: reviewed alongside PR.
- UI changes: visual review via screenshots or deployment preview.

## Review Checklist
- [ ] Does the change follow existing patterns and conventions?
- [ ] Are there backward compatibility concerns?
- [ ] Are docs updated to reflect the change?
- [ ] Are tests added/modified?
- [ ] Does the change introduce new dependencies?
- [ ] Are error paths handled gracefully?

## Current Review Status
- Architecture decisions documented in `11_DECISIONS.md` (4 ADRs).
- API routing mismatch documented in `48_REPOSITORY_AUDIT.md`.
- Backend implementation gaps documented in `12_TASKS.md`.
"""

DOCS["27_QUALITY_GATES.md"] = """# Quant Nanggroe AI — Quality Gates

## Pre-Merge Gates
1. ✅ Lint passes (`make lint`)
2. ✅ Type check passes (`make typecheck`)
3. ✅ Unit tests pass (`make test-quick`)
4. ✅ Docs updated to reflect changes
5. ✅ No secrets committed (pre-commit hook)

## Pre-Release Gates
1. ✅ Full test suite passes (`make test`)
2. ✅ Integration tests pass
3. ✅ Docker build succeeds
4. ✅ All API endpoints return correct responses
5. ✅ Frontend builds without errors

## Gate Failure Protocol
- If lint fails: fix formatting issues, re-run.
- If tests fail: investigate, fix, re-run.
- If docs missing: update docs before merge.
- If security issue: escalate immediately.
"""

DOCS["28_VERSIONING.md"] = """# Quant Nanggroe AI — Versioning

## Scheme
Semantic Versioning (SemVer 2.0.0):
- **MAJOR:** Breaking API changes, database schema changes, architecture changes.
- **MINOR:** New features, new endpoints, backward-compatible additions.
- **PATCH:** Bug fixes, performance improvements, documentation updates.

## Current Version
**v5.1.0** — Major (5), Minor (1), Patch (0)

## Version Tracking
- `pyproject.toml`: `version = "4.3.4"`
- `package.json` (dashboard): `version = "0.1.0"`
- Git tags: `v5.1.0`
- CHANGELOG: `13_CHANGELOG.md`
"""

DOCS["29_PLUGIN_SYSTEM.md"] = """# Quant Nanggroe AI — Plugin System

## Architecture
The plugin system is designed around agent skills and data providers:

- **Agent Skills:** Modular Python modules in `agents/` directory that register capabilities.
- **Data Providers:** Plugable market data backends (yfinance, CCXT, Alpaca, Polygon).
- **Tool Runners:** Dynamic execution of external binaries (partially stubbed).

## Registration
Agents self-register on startup via the Daemon Manager's `agents_config` dictionary. Each agent defines:
- `module`: Python module path
- `class`: Agent class name
- `instance`: Instance variable name
- `priority`: Startup priority (1=core, 2=standard, 3=advanced)
- `auto_start`: Whether to start automatically

## Current Status
- 20+ agents registered and auto-started.
- Dynamic skill loading (`tools/execution.py`) raises `NotImplementedError`.
- Plugin marketplace planned for v6.x.
"""

DOCS["30_MULTI_AGENT_WORKFLOW.md"] = """# Quant Nanggroe AI — Multi-Agent Workflow

## Orchestration Engine
Built on **LangGraph**, supporting:
- **Cyclic workflows:** Agents can loop until a condition is met.
- **Conditional branching:** Route between agents based on output.
- **State persistence:** Full workflow state saved for audit and recovery.

## Agent Hierarchy
```
Priority 1 (Core): Prompt Master, Memory Bus, Scheduler, Colony Connector, Deployment Specialist
Priority 2 (Standard): CyberShell, Agent Maker, UI Designer, Dev Engine, FullStack Dev
Priority 3 (Advanced): Commander AGI, Bug Hunter, Money Maker, Backup Colony, Auth, Knowledge Manager, Marketing, Quality Control
```

## Workflow Examples
- **Trading Workflow:** Market Data Agent → Analysis Agent → Risk Agent → Execution Agent → Memory Log.
- **Research Workflow:** Web Research Agent → Data Processing Agent → Report Generation Agent.
- **Incident Response Workflow:** Monitoring Agent → Diagnosis Agent → Remediation Agent → Postmortem Agent.
"""

DOCS["31_SELF_REVIEW.md"] = """# Quant Nanggroe AI — Self-Review Protocol

## Before Finalizing Output
1. [ ] Check for missing assumptions.
2. [ ] Check for contradictions with existing docs.
3. [ ] Check for incomplete coverage of the subject.
4. [ ] Check for misalignment with current project state.
5. [ ] Check for outdated or risky advice.
6. [ ] Check for missing documentation impacts.
7. [ ] Check for test impact.
8. [ ] Check for release impact.

## Weakness Remediation
If any check fails: fix before proceeding, document the issue, and update affected files.
"""

DOCS["32_KNOWLEDGE_UPDATE.md"] = """# Quant Nanggroe AI — Knowledge Update Process

## Triggers for Knowledge Updates
- New architecture decision (→ update `11_DECISIONS.md` and `16_AI_MEMORY.md`).
- New term introduced (→ update `17_GLOSSARY.md`).
- New risk identified (→ update `19_RISK_REGISTER.md`).
- API change (→ update `04_API.md`).
- Dependency change (→ update `22_REQUIREMENTS.md`).

## Update Workflow
1. Identify which docs are affected by the change.
2. Make changes to each doc.
3. Cross-reference for consistency.
4. Run self-review (`31_SELF_REVIEW.md`).
5. Commit with `docs:` prefix in commit message.
"""

DOCS["33_OBSERVABILITY.md"] = """# Quant Nanggroe AI — Observability

## Metrics (Prometheus)
- **Endpoint:** `GET /metrics`
- **Exposed metrics:** Request count, latency, error rate, agent status, trade count.

## Logging
- **Framework:** `structlog` for structured logging.
- **Log levels:** DEBUG, INFO, WARNING, ERROR (configurable via `LOG_LEVEL` env var).
- **Log output:** `data/logs/agi_force_YYYYMMDD.log` (rotated daily by daemon manager).

## Health Checks
- **API Health:** `GET /api/v1/health` — returns system status and dependency availability.
- **Docker Health:** Container healthchecks configured for api, worker, and redis services.
- **Agent Health:** Daemon manager checks every 30 seconds, auto-restarts on failure.

## Monitoring
- Daemon status file: `data/daemons/status.json` — updated every 60 seconds.
- Web interface status page: `http://localhost:5000` (Flask UI on port 5000).
- Prometheus metrics for production monitoring.
"""

DOCS["34_DEPLOYMENT.md"] = """# Quant Nanggroe AI — Deployment Guide

## Docker Deployment (Recommended)
```bash
# Build and start all services
docker compose up -d --build

# Check logs
docker compose logs -f

# Stop all services
docker compose down
```

## Manual Deployment
```bash
# Install dependencies
pip install quant-nanggroe-ai[all]

# Start the API server
qnai system start

# Start the dashboard
cd dashboard && npm run build && npm start
```

## Production Checklist
- [ ] Redis server running and accessible.
- [ ] `.env` file configured with API keys.
- [ ] Firewall configured to restrict access to dashboard.
- [ ] Docker memory limits set for api (512m) and worker (1g).
- [ ] Prometheus scraping configured for `/metrics`.
- [ ] Regular backups configured for database.

## Supported Platforms
- **Netlify:** Static dashboard deployment (frontend only).
- **Vercel:** Serverless dashboard deployment.
- **Railway:** Full-stack deployment with database.
- **Docker:** Local or cloud container orchestration.
"""

DOCS["35_INCIDENT_MANAGEMENT.md"] = """# Quant Nanggroe AI — Incident Management

## Classification
- **SEV-1 (Critical):** System down, data loss, unauthorized access. Immediate response required.
- **SEV-2 (High):** Trading engine failure, API unavailable, incorrect risk calculations. Respond within 1 hour.
- **SEV-3 (Medium):** Dashboard errors, non-critical endpoint failures. Respond within 24 hours.
- **SEV-4 (Low):** Documentation errors, cosmetic UI issues. Respond within 1 week.

## Response Process
1. **Detect:** Monitor logs, health checks, and status file.
2. **Assess:** Determine severity and impact.
3. **Respond:** Apply mitigation (stop trading, restart service, rollback).
4. **Resolve:** Fix root cause.
5. **Postmortem:** Document what happened, why, and how to prevent.

## Known Incident Patterns
- API routing mismatches cause frontend 404s (SEV-3).
- Memory pressure on Docker worker container (SEV-3).
- Stub/pass blocks in engine cause silent failures (SEV-2).
"""

DOCS["36_MIGRATION_PLAN.md"] = """# Quant Nanggroe AI — Migration Plan

## When Migration Is Needed
- Breaking API changes (major version bump).
- Database schema changes.
- Architecture changes affecting data flow.
- Platform or framework upgrades.

## Migration Process
1. **Plan:** Document what changes, why, and migration steps.
2. **Communicate:** Update docs, notify stakeholders.
3. **Implement:** Make changes in feature branch.
4. **Test:** Run full test suite, verify backward compatibility where possible.
5. **Deploy:** Use rolling update for zero-downtime deployment.
6. **Verify:** Monitor system after deployment for issues.

## Current Migration Items
- API prefix unification (`/api/*` ↔ `/api/v1/*`) — in progress.
- Legacy dashboard health-check cleanup — pending.
"""

DOCS["37_RELEASE_CHECKLIST.md"] = """# Quant Nanggroe AI — Release Checklist

## Pre-Release
- [ ] Version bumped in `pyproject.toml`.
- [ ] CHANGELOG updated (`13_CHANGELOG.md`).
- [ ] All tests pass (`make ci`).
- [ ] All quality gates passed (`27_QUALITY_GATES.md`).
- [ ] Docker build succeeds.
- [ ] Frontend builds without errors.
- [ ] API endpoints verified via Swagger UI.
- [ ] Docs reviewed for accuracy.

## Release
- [ ] Git tag created (`vX.Y.Z`).
- [ ] Release notes written.
- [ ] Docker images built and pushed.
- [ ] Deployment verified in staging.

## Post-Release
- [ ] Version bump for next development iteration.
- [ ] Known issues documented in new release.
"""

DOCS["38_MAINTENANCE.md"] = """# Quant Nanggroe AI — Maintenance Guide

## Routine Maintenance
- **Daily:** Check daemon status (`qnai system status`), review logs for errors.
- **Weekly:** Review open issues, update dependencies, check disk usage.
- **Monthly:** Full test suite run, dependency audit, backup verification.

## Cache Management
- Redis cache auto-evicts under memory pressure.
- Paper state directory should be archived if growth exceeds 1GB.

## Log Rotation
- Daemon logs rotate automatically by date (`agi_force_YYYYMMDD.log`).
- Retention: 30 days of logs, 90 days for production deployments.

## Known Maintenance Issues
- `pass` stubs in security module need completion.
- Test coverage gaps need filling.
- Docker worker container may need memory limit adjustment.
"""

DOCS["39_GOVERNANCE.md"] = """# Quant Nanggroe AI — Governance

## Decision-Making Framework
- **Technical decisions:** Made by maintainers with ADR documentation.
- **Architecture changes:** Require ADR and design review.
- **Breaking changes:** Require migration plan and deprecation notice.

## Ownership
- **Repository:** Quant Nanggroe AI Team / Mulky Malikul Dhaher
- **License:** MIT — full open source.
- **Contribution:** Open to community via PR process (`21_CONTRIBUTING.md`).

## Compliance
- All dependencies must be open source with permissive licenses.
- API keys and secrets must never be committed to version control.
- Trading strategies must be thoroughly backtested before paper trading.
"""

DOCS["40_MULTI_AGENT.md"] = """# Quant Nanggroe AI — Multi-Agent System

## Overview
The multi-agent system consists of 20+ specialized agents organized in a priority-based hierarchy, managed by the Daemon Manager and orchestrated via LangGraph.

## Agent Roles

### Core (Priority 1)
- **Prompt Master:** Central prompt processing and task routing.
- **Memory Bus:** Persistent storage for agent decisions and events.
- **Scheduler:** Background task scheduling and execution.
- **AGI Colony Connector:** Inter-colony communication and port forwarding.
- **Deployment Specialist:** Autonomous deployment and expansion.

### Standard (Priority 2)
- **CyberShell:** System command execution and shell operations.
- **Agent Maker:** Dynamic agent creation and configuration.
- **UI Designer:** User interface generation.
- **Dev Engine:** Software development assistance.
- **FullStack Dev:** End-to-end development tasks.

### Advanced (Priority 3)
- **Commander AGI:** Security monitoring and robotics coordination.
- **Bug Hunter:** Ethical hacking and vulnerability discovery.
- **Money Maker:** Revenue generation strategies.
- **Backup Colony:** Distributed backup infrastructure.
- **Authentication:** KYC verification and payment processing.
- **Knowledge Manager:** Advanced memory and data storage.
- **Marketing:** Global promotion and outreach automation.
- **Quality Control:** Visual and analytical assessment.
"""

DOCS["41_WORKFLOW.md"] = """# Quant Nanggroe AI — Workflows

## Trading Workflow
```
Market Data (yfinance/CCXT)
    → Analysis Agent
        → Risk Engine (Kelly, VaR, Drawdown)
            → Trading Engine (entry, exit, sizing)
                → Memory Log (state dump)
                    → Dashboard Update (UI refresh)
```

## Agent Startup Workflow
```
Daemon Manager starts
    → Load agent config (priority-ordered)
        → Import module & instantiate agent
            → Register in agent registry
                → Start health monitor thread
                    → Update status file
```

## System Health Workflow
```
Health check triggered (60s loop)
    → Ping all agent health endpoints
        → Check service availability (DB, Redis, Web)
            → Write status.json
                → Update dashboard UI
                    → Alert on failures
```

## Incident Response Workflow
```
Alert detected
    → Classify severity (SEV-1 to SEV-4)
        → Apply mitigation (stop/restart/rollback)
            → Resolve root cause
                → Write postmortem
                    → Update prevention measures
```
"""

DOCS["42_CHECKLISTS.md"] = """# Quant Nanggroe AI — Checklists

## Daily Operations Checklist
- [ ] `qnai system status` — check system health.
- [ ] Review `data/logs/` for errors.
- [ ] Monitor `paper_state/` for consistent state updates.
- [ ] Check disk usage.

## Development Checklist
- [ ] Branch from `main`.
- [ ] Make changes.
- [ ] Run `make lint && make typecheck`.
- [ ] Add/update tests.
- [ ] Update docs.
- [ ] Submit PR.

## Deployment Checklist
- [ ] Tests pass.
- [ ] Docker builds.
- [ ] `.env` configured.
- [ ] Redis accessible.
- [ ] Firewall rules applied.
- [ ] Backups configured.

## Emergency Checklist
- [ ] Stop trading engine: `qnai system stop`.
- [ ] Back up state files.
- [ ] Investigate logs.
- [ ] Apply fix.
- [ ] Verify fix.
- [ ] Restart system.
"""

DOCS["43_TEMPLATES.md"] = """# Quant Nanggroe AI — Templates

## ADR Template
```markdown
## ADR-NNN: Title
- **Problem:** [description]
- **Options:** [list of alternatives]
- **Decision:** [chosen option]
- **Consequences:** [tradeoffs]
```

## Agent Registration Template
```python
"agent_name": {
    "module": "agents.module_name",
    "class": "AgentClass",
    "instance": "agent_instance",
    "priority": 2,
    "auto_start": True,
    "description": "Agent description"
}
```

## PR Template
```markdown
## Description
[What changed and why]

## Docs Updated
- [list of docs]

## Test Results
[lint, typecheck, test output]
```
"""

DOCS["44_PROMPT_LIBRARY.md"] = """# Quant Nanggroe AI — Prompt Library

## System Prompts

### Trade Execution Prompt
```
Analyze current market conditions for {symbol}.
Apply Kelly criterion for position sizing.
Check VaR and drawdown limits.
Execute trade if all risk checks pass.
Log decision to memory bus.
```

### Agent Creation Prompt
```
Create a new {agent_type} agent specialized in {specialization}.
Configure with {experience} experience level.
Register with Daemon Manager.
Initialize and start monitoring.
```

### Health Check Prompt
```
Check all agent statuses.
Verify service availability (DB, Redis, Web).
Generate health report.
Alert on any failures.
```
"""

DOCS["45_RELEASE_PROCESS.md"] = """# Quant Nanggroe AI — Release Process

## Steps
1. **Check readiness:** Run `37_RELEASE_CHECKLIST.md`.
2. **Version bump:** Update version in `pyproject.toml`, `package.json`.
3. **Update CHANGELOG:** `13_CHANGELOG.md` with release notes.
4. **Final test:** `make ci` — full test suite.
5. **Tag release:** `git tag vX.Y.Z && git push --tags`.
6. **Build artifacts:** `make build`, Docker images.
7. **Deploy staging:** Verify all services.
8. **Deploy production:** Rolling update.
9. **Monitor:** 24-hour post-release monitoring.

## Hotfix Process
1. Branch from tag: `git checkout -b hotfix/vX.Y.Z+1 vX.Y.Z`.
2. Apply fix.
3. Test thoroughly.
4. Tag and deploy.
5. Merge back to `main`.
"""

DOCS["46_INCIDENT_RESPONSE.md"] = """# Quant Nanggroe AI — Incident Response

## Response Procedures

### SEV-1 (Critical)
1. **Immediately:** Stop all trading (`qnai system stop`).
2. **Assess:** Determine cause and impact.
3. **Contain:** Isolate affected components.
4. **Resolve:** Apply emergency fix.
5. **Verify:** Confirm system stable.
6. **Postmortem:** Full analysis within 24 hours.

### SEV-2 (High)
1. **Within 1 hour:** Investigate and assess.
2. **Mitigate:** Apply workaround if available.
3. **Resolve:** Fix root cause.
4. **Verify:** Confirm fix effective.
5. **Postmortem:** Analysis within 1 week.

### SEV-3 (Medium) / SEV-4 (Low)
1. **Log issue:** Create GitHub issue.
2. **Schedule fix:** Normal development cycle.
3. **Resolve:** Fix in next release.
4. **Verify:** Confirm fix in testing.

## Communication
- All incidents logged in status file (`data/daemons/status.json`).
- Critical incidents trigger immediate notification (via configured channels).
- Postmortems stored in `docs/` as ADRs.
"""

DOCS["47_REVERSE_ENGINEERING.md"] = """# Quant Nanggroe AI — Reverse Engineering Guide

## Purpose
Document the process of understanding system behavior from code when documentation is missing or outdated.

## Methodology
1. **Read entry points:** `main.py`, `cli.py`, `daemon_manager.py`.
2. **Trace startup flow:** Module loading → initialization → agent registration.
3. **Map API routes:** FastAPI router definitions → endpoint handlers.
4. **Identify data flow:** Input → processing → output → storage.
5. **Document findings:** Update relevant docs with inferred structure.

## Current State
- Architecture and API routes are documented in `02_ARCHITECTURE.md` and `04_API.md`.
- Implementation gaps are documented in `12_TASKS.md`.
- Wiring mismatches are documented in `48_REPOSITORY_AUDIT.md`.

## Marking Convention
When reverse engineering, mark findings with:
- `[inferred]` — deduced from code patterns.
- `[likely]` — high confidence but not confirmed.
- `[unknown]` — cannot be determined from available code.
- `[needs confirmation]` — should be verified by human.
"""

DOCS["48_REPOSITORY_AUDIT.md"] = EXISTING.get("48_REPOSITORY_AUDIT.md", "") + """

## Update (July 2026 — Docs Renewal)

### Docs Status
- **Placeholder files (most):** Now contain content based on current project state.
- **Existing docs (02, 04, 12, 48):** Preserved and enhanced.
- **Root files (README, AGENTS, CLAUDE):** Still need content generation.
- **Missing templates:** `templates/` directory structure not yet created.

### Status (After Renewal)
- **Root agent files:** AGENTS.md, CLAUDE.md, COPILOT.md, CURSOR.md, GEMINI.md, MASTER_SYSTEM_PROMPT.md -- GENERATED.
- **Docs (00-49):** All 49 files now contain substantive content.
- **Missing:** `templates/` directory structure, formal pre-commit docs sync hook.

### Recommended Next Actions
1. Generate `README.md` content that links to the new docs index.
2. Create `templates/` directory with template files.
3. Set up pre-commit hook to prevent docs from falling out of sync.
4. Automated cross-reference validation across all 49 docs.
"""

DOCS["49_PROJECT_BOOTSTRAP.md"] = """# Quant Nanggroe AI — Project Bootstrap Guide

## For New Developers

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker (optional, for containerized deployment)
- Git

### Quick Start
```bash
# Clone the repository
git clone <repo-url> Quant-Nanggroe-AI
cd Quant-Nanggroe-AI

# Install Python dependencies
pip install -e .[dev]

# Install dashboard dependencies
cd dashboard && npm install && cd ..

# Start the system
qnai system start

# Access the dashboard
open http://localhost:8000/docs  # API docs
open http://localhost:5000        # Web UI
```

### First-Time Setup
1. Copy `.env.example` to `.env` and configure API keys.
2. Run `qnai database init` to initialize the database.
3. Run `qnai agents list` to verify agents are registered.
4. Run `make test-quick` to verify tests pass.

### Reading the Docs
Start with:
1. `00_VISION.md` — What is this project?
2. `01_PRD.md` — What does it do?
3. `02_ARCHITECTURE.md` — How is it built?
4. `15_PROJECT_CONTEXT.md` — Project context and vocabulary.
5. `21_CONTRIBUTING.md` — How to contribute.

### AI Agent Entry Points
- **AGENTS.md:** How AI should read this repository.
- **CLAUDE.md:** Claude-specific instructions.
- **16_AI_MEMORY.md:** Stable facts and common pitfalls.
"""

# ── Root-level files ──────────────────────────────────────────────────
ROOT_FILES = {
    "AGENTS.md": """# Quant Nanggroe AI — Agent Instructions

## How AI Should Read This Repository
1. Start with `README.md` for project overview.
2. Read `00_VISION.md` and `01_PRD.md` for product context.
3. Read `02_ARCHITECTURE.md` for system structure.
4. Read `15_PROJECT_CONTEXT.md` for vocabulary and assumptions.
5. Read `16_AI_MEMORY.md` for stable facts and pitfalls.
6. Read `14_PROJECT_RULES.md` for governance rules.

## Order of Inspection
```
README.md → 00_VISION → 01_PRD → 02_ARCHITECTURE → 15_CONTEXT → 16_MEMORY
→ 04_API → 12_TASKS → 48_AUDIT → 17_GLOSSARY → 14_RULES
```

## What Not to Change Without Approval
- API contract (response envelope, endpoint paths).
- Risk engine logic (Kelly, VaR, drawdown limits).
- State file format in `paper_state/`.
- Agent registration in `daemon_manager.py`.

## How to Update Docs
- All doc changes in same PR as code changes.
- Follow `31_SELF_REVIEW.md` before finalizing.
- Use ADR format for architecture decisions (`11_DECISIONS.md`).
""",
    "CLAUDE.md": """# Claude-Specific Instructions — Quant Nanggroe AI

## Tools Available
- Repository audit (`48_REPOSITORY_AUDIT.md`).
- Architecture docs (`02_ARCHITECTURE.md`).
- API reference (`04_API.md`).
- Task tracking (`12_TASKS.md`).

## Key Files
- `main.py` — Entry point (asyncio-based agent system).
- `cli.py` — CLI interface (Click commands).
- `daemon_manager.py` — Agent lifecycle manager.
- `pyproject.toml` — Dependencies and configuration.

## Response Style
- Start with project state detection per AI-Engineering-OS.
- Reference specific docs by their number prefix.
- Flag uncertainties explicitly.
""",
    "COPILOT.md": """# GitHub Copilot Instructions — Quant Nanggroe AI

## Suggested Ignore Patterns
- `paper_state/*.json` — auto-generated trading state.
- `data/*` — runtime data.
- `node_modules/` — JavaScript dependencies.
- `__pycache__/` — Python cache.

## Commit Message Convention
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `refactor:` Code refactoring
- `test:` Test changes
- `chore:` Maintenance
""",
    "CURSOR.md": """# Cursor IDE Instructions — Quant Nanggroe AI

## Rules
- Always check `14_PROJECT_RULES.md` before making changes.
- Run `make lint` and `make typecheck` before committing.
- Keep docs synchronized with code changes.

## Indexing Preferences
- Index: `quant_nanggroe/`, `dashboard/src/`, `docs/`
- Exclude: `data/`, `paper_state/`, `node_modules/`, `__pycache__/`
""",
    "GEMINI.md": """# Gemini-Specific Instructions — Quant Nanggroe AI

## Context
Multi-agent trading intelligence system with FastAPI backend and Next.js dashboard.

## Documentation Map
- `00_VISION.md` — Project north star.
- `02_ARCHITECTURE.md` — System layers and data flow.
- `04_API.md` — Available endpoints.
- `12_TASKS.md` — Current implementation gaps.
- `48_REPOSITORY_AUDIT.md` — Known wiring issues.
- `16_AI_MEMORY.md` — Stable facts to remember.
""",
    "MASTER_SYSTEM_PROMPT.md": """# Quant Nanggroe AI — Master System Prompt

You are operating Quant Nanggroe AI, an autonomous multi-agent trading intelligence system.

## Core Operating Principles
1. **First, audit the project state.** Read `48_REPOSITORY_AUDIT.md` for known issues.
2. **Respect the architecture.** Read `02_ARCHITECTURE.md` before making changes.
3. **Keep docs in sync.** Every code change must update relevant docs.
4. **Never skip risk checks.** All trades must pass Kelly, VaR, and drawdown limits.
5. **Record decisions.** Use ADR format in `11_DECISIONS.md`.

## Current State (July 2026)
- v5.1.0 — Multi-agent trading system with paper trading capability.
- API routing mismatch documented in audit.
- Backtesting engine partially stubbed.
- RL agents partially stubbed.

## Critical Files
- `main.py` — System entry point.
- `cli.py` — CLI interface.
- `daemon_manager.py` — Agent lifecycle.
- `quant_nanggroe/api.py` — API routes.
- `quant_nanggroe/engine/` — Trading, risk, backtest logic.
""",
}

# ── Write all files ───────────────────────────────────────────────────
def write_docs():
    os.makedirs(DOCS_DIR, exist_ok=True)

    # Write doc files
    count = 0
    for filename, content in sorted(DOCS.items()):
        filepath = os.path.join(DOCS_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")
        count += 1
        print("  [OK] %s" % filename)

    # Write root files
    for filename, content in sorted(ROOT_FILES.items()):
        filepath = os.path.join(BASE, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")
        count += 1
        print("  [OK] %s (root)" % filename)

    print("\n[DONE] Total: %d files written" % count)

if __name__ == "__main__":
    print("Quant Nanggroe AI — Docs Renewal")
    print("=" * 50)
    print("\nBacking up existing docs...")
    backup_existing()
    print("\nWriting %d doc files + %d root files..." % (len(DOCS), len(ROOT_FILES)))
    print()
    write_docs()
    print("\nBackup location: %s" % BACKUP_DIR)
