# Quant Nanggroe AI

**Agentic Trading Intelligence OS** — Sovereign Autonomous Multi-Agent Trading Framework

Built by **Dhaher Labs** — Quant Nanggroe Hedge Fund

---

## Overview

Quant Nanggroe AI is a **unified, zero-fragmentation** multi-agent trading intelligence system. After a comprehensive integration cleanup, all previously disconnected components (legacy packages, orphan agents, dual engines, ghost skills) have been consolidated into a single cohesive structure.

### Core Capabilities
- **LangGraph** agent orchestration for complex trading workflows
- **FastAPI** backend with trading, risk, portfolio, and backtesting engines
- **Next.js 16** dashboard with real-time monitoring (React 19, Tailwind CSS v4)
- **Multi-Agent System** — 20+ agents including gold trader, debate engine, marketplace, and chinese wall
- **Risk Management** — Kelly sizing, VaR, drawdown, kill switch, pressure monitoring
- **Exchange Integration** — CCXT, Alpaca, yfinance, WebSocket streaming
- **ML/AI** — XGBoost, PyTorch, LangChain, OpenAI, Anthropic, Google GenAI
- **Paper Trading** — State dumps to `paper_state/` with full position tracking
- **Docker** deployment with Redis caching, Prometheus monitoring, health-checked services

---

## Project Structure (Post-Restructure — Zero Fragmentation)

```
D:\repositories\Quant-Nanggroe-AI-worktree/
│
├── quant_nanggroe/            ← SATU-SATUNYA PYTHON PACKAGE (24 subpackages, 542 .py files)
│   ├── agents/                ← Multi-agent system (20+ agents — unified from 2 systems)
│   │   ├── base.py            │   ├── gold_trader.py
│   │   ├── chinese_wall.py    │   ├── marketplace.py
│   │   ├── debate_engine.py   │   ├── registry.py
│   │   └── ...                │
│   ├── engine/                ← Trading, risk, backtest, ML engines (250 .py files)
│   │   ├── trading/           │   ├── risk/
│   │   ├── backtest/          │   ├── rl/
│   │   ├── ml/                │   ├── hermes_* (auditor, chart, decision, journal, etc.)
│   │   └── ...                │
│   ├── core/                  ← Memory bus, scheduler, AI selector, circuit breaker
│   ├── api/                   ← FastAPI routes & middleware
│   ├── security/              ← Credential management, encryption, keyvault, audit
│   ├── database/              ← SQLAlchemy models & Alembic migrations
│   ├── providers/             ← Data provider integrations (coingecko, finnhub, macro, proxy)
│   ├── strategies/            ← Trading strategies (pairs_trade, trend_follow, tsmom, xgboost)
│   ├── bridge/                ← Data bridge module (future live trading connector)
│   ├── data/                  ← Cache, warehouse, failover, survivorship
│   ├── exchange/              ← Exchange connector implementations
│   ├── llm/                   ← LLM integration layer
│   ├── mcp/                   ← Model Context Protocol
│   ├── memory/                ← Memory management
│   ├── backtest/              ← Backtesting engine
│   ├── connectors/            ← External connector integrations
│   ├── config/                ← Configuration management
│   ├── schemas/               ← Pydantic schemas
│   ├── types/                 ← Type definitions
│   ├── utils/                 ← Utility functions
│   ├── db/                    ← Database utilities
│   ├── skills/                ← Agent skills & plugins
│   ├── tests/                 ← Module-level tests
│   └── docs/                  ← Module-level documentation
│
├── dashboard/                 ← Next.js 16 React UI (Apple Liquid Glass × Bloomberg)
│   ├── src/app/               ← 15 App router pages
│   │   ├── page.tsx            ← Main dashboard (health, live prices, quick nav)
│   │   ├── trading/page.tsx    ← Multi-broker trading (MT5, Binance, IBKR, Paper)
│   │   ├── portfolio/page.tsx  ← Cross-broker portfolio aggregation
│   │   ├── agents/page.tsx     ← Agent council + LangGraph pipeline
│   │   ├── risk/page.tsx       ← VaR, Kelly, 9-checkpoint gate
│   │   ├── strategies/page.tsx ← Strategy lifecycle & schema
│   │   ├── backtest/page.tsx   ← Backtesting engine
│   │   ├── market/page.tsx     ← Market data & signals
│   │   ├── memory/page.tsx     ← Memory bus search
│   │   ├── colony/page.tsx     ← Agent colony mgmt
│   │   ├── factors/page.tsx    ← Alpha factor zoo explorer
│   │   ├── security/page.tsx   ← Security events & sandbox
│   │   ├── channels/page.tsx   ← Notification channels
│   │   ├── tools/page.tsx      ← Tool registry
│   │   └── settings/page.tsx   ← Full configuration UI
│   ├── src/components/
│   │   ├── layout/             ← AppLayout, Sidebar, Header (glass chrome)
│   │   ├── ui/                 ← Card, Button, Input, Select, Badge, Tabs, Switch, etc.
│   │   ├── shared/             ← StatusCard, ChartCard, DataTable, RiskGauge, LoadingSkeleton
│   │   └── providers/          ← ThemeProvider (auto day/night)
│   ├── src/lib/
│   │   ├── api-client.ts       ← Typed API client (retry, dedup, timeout, 30+ endpoints)
│   │   ├── websocket.ts        ← WebSocket hook (exponential backoff, 4 channels)
│   │   ├── store.ts            ← Zustand store (granular loading/error, WS integration)
│   │   └── utils.ts            ← Quant formatters (currency, percent, P&L color)
│   └── qnai_dashboard.html    ← Legacy HTML dashboard (paper trading)
│
├── docs/                      ← 49 documentation files (00-49)
│   ├── 00_VISION.md           ← Project north star & goals
│   ├── 01_PRD.md              ← Product requirements
│   ├── 02_ARCHITECTURE.md     ← System architecture
│   ├── 04_API.md              ← API reference
│   ├── 12_TASKS.md            ← Implementation gaps & sprint
│   ├── 48_REPOSITORY_AUDIT.md ← Wiring & gaps audit
│   └── ...                    ← 49 docs total (see index below)
│
├── scripts/                   ← Build & automation (84 files)
├── tests/                     ← Test suite (292 files, 154 .py)
├── skills/                    ← Core skills (pdf, pptx, xlsx — document processing for trading reports)
├── web_interface/             ← Flask web UI (legacy, port 5000)
├── config/                    ← YAML configuration files
├── data/                      ← Runtime data (logs, backups, cache)
├── deploy/                    ← Deployment configurations
├── docker/                    ← Docker configurations
├── connectors/                ← External connectors
├── alembic/                   ← Database migrations
├── templates/                 ← Jinja2 templates
├── reports/                   ← Generated reports
├── research/                  ← Research notes
├── examples/                  ← Usage examples
├── monitoring/                ← Prometheus/Grafana monitoring configs
├── tool-results/              ← Tool execution results
│
├── main.py                    ← System entry point (AgenticAISystem)
├── cli.py                     ← CLI interface (Click commands)
├── daemon_manager.py          ← Daemon process manager
├── pyproject.toml             ← Python project configuration
├── package.json               ← Dashboard Node.js config
├── Makefile                   ← Build, test, deploy targets
├── docker-compose.yml         ← Container orchestration
├── k8s-deployment.yaml        ← Kubernetes deployment
├── vercel.json                ← Vercel deployment
├── railway.json               ← Railway deployment
├── render.yaml                ← Render deployment
│
├── AGENTS.md                  ← How AI agents should read this repository
├── CLAUDE.md                  ← Claude-specific instructions
├── COPILOT.md                 ← Copilot-specific instructions
├── CURSOR.md                  ← Cursor-specific instructions
├── GEMINI.md                  ← Gemini-specific instructions
├── MASTER_SYSTEM_PROMPT.md    ← Master prompt for operating in this system
│
└── .gitignore                 ← Comprehensive exclusions (no backup/legacy in repo)
```

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+ (for dashboard)
- Docker & Docker Compose (for containerized deployment)

### Python Backend
```bash
# Install dependencies
pip install -e .[dev]

# Start the system
python main.py
# OR
python cli.py system start   # CLI interface
# OR
python daemon_manager.py start  # Daemon mode
```

### Dashboard (Next.js)
```bash
cd dashboard
npm install
npm run dev    # Development server on port 3000
```

### Docker Deployment
```bash
docker compose up -d --build
```

---

## Documentation Index

| Doc | Title | Description |
|-----|-------|-------------|
| 00 | VISION | Project north star, core beliefs, long-term goals |
| 01 | PRD | Product requirements, user needs, MVP scope |
| 02 | ARCHITECTURE | System layers, data flow, infrastructure |
| 03 | SPEC | Technical specifications, invariants, protocols |
| 04 | API | FastAPI endpoint reference |
| 05 | SDK | Developer tooling, CLI usage, Python SDK |
| 06 | RUNTIME | Execution model, startup flow, lifecycle |
| 07 | SECURITY | Trust model, credential management, encryption |
| 08 | STYLEGUIDE | Python & TypeScript naming, formatting |
| 09 | TESTING | Test layers, commands, coverage gaps |
| 10 | ROADMAP | Phases 1-4 development plan |
| 11 | DECISIONS | Architecture Decision Records (4 ADRs) |
| 12 | TASKS | Current sprint, backlog, implementation gaps |
| 13 | CHANGELOG | Version history |
| 14 | PROJECT_RULES | Mandatory rules, forbidden actions, governance |
| 15 | PROJECT_CONTEXT | Identity, vocabulary, strategic intent |
| 16 | AI_MEMORY | Stable facts, decisions, pitfalls |
| 17 | GLOSSARY | Domain terminology |
| 18 | DOMAIN_MODEL | Core entities, relationships, boundaries |
| 19 | RISK_REGISTER | Known risks, severity, mitigation |
| 20 | RELEASE_PLAN | Stages, gates, rollback policy |
| 21 | CONTRIBUTING | How to contribute, PR expectations |
|| 18-49 | Extended Docs | Requirements, validation, ADR process, etc. |
|| **Broker** | BROKER_SETUP | MT5 Exness setup, broker config guides |
|| **UI** | UI_GUIDE | Dashboard pages, components, design system |

---

|## Current State
|
|**Version:** v4.4.0 (July 2026)
|
[![Tests](https://img.shields.io/badge/tests-1766%2F1766%20passing-brightgreen)](#)
[![Strategies](https://img.shields.io/badge/strategies-106-green)](#)
[![API Routes](https://img.shields.io/badge/API%20Routes-30-blue)](#)
[![Brokers](https://img.shields.io/badge/brokers-7-blue)](#)
[![Test Files](https://img.shields.io/badge/test%20files-154-lightgrey)](#)
[![Dashboard Pages](https://img.shields.io/badge/dashboard%20pages-15-orange)](#)
|
|### ✅ Ready
|- **1766/1766 tests passing (100%)** — 154 test files, 106 strategies, 30 API routes, 7 brokers
|- Multi-agent orchestration (20+ agents in a unified system)
|- Risk management engine (Kelly, VaR, drawdown, kill switch)
|- Exchange API integrations (CCXT, Alpaca, yfinance, IBKR, MT5, Polymarket)
|- WebSocket real-time data streaming with auto-reconnect (4 channels)
|- Paper trading with state dumps to `paper_state/`
|- Docker Compose deployment
|- CLI, API, and daemon entry points
|- Complete documentation (49 docs + agent-specific .md files)
|- **Zero fragmentation** — all code lives in one unified structure
|- **No orphan modules** — all Python packages have proper `__init__.py`
|- **Apple macOS Liquid Glass Design System** — glassmorphism, blur effects, double-bezel cards
|- **Live Multi-Broker Trading UI** — MT5, Binance, IBKR, Paper, Polymarket with cross-broker aggregation
|- **15 Production-Ready Dashboard Pages** — all with real API, error handling, loading states
|- **Real-time WebSocket** — 4 channels (price, regime, risk, portfolio) with exponential backoff
|- **API Client** — retry logic, request dedup, timeout, 30+ typed endpoints
|- **Auto Day/Night Theme** — system preference + localStorage + manual override
|- **Bloomberg-Style Data Cells** — compact, color-coded, high-density financial UI
|
|### 🔄 In Progress
|- Backtesting engine enhancements
|- Reinforcement learning signal pipeline
|- Live trading bridge (planned for v5.x)
|- API routing unification (/api/ vs /api/v1/ mismatch)
|- Security hardening

### Tech Stack
- **Backend:** Python 3.11+, FastAPI, LangGraph, SQLAlchemy, Redis
- **Frontend:** Next.js 16, React 19, Tailwind CSS v4, Zustand v5, Recharts v2
- **ML/AI:** LangChain, OpenAI, Anthropic, Google GenAI, PyTorch, XGBoost
- **Infrastructure:** Docker, Prometheus, Alembic, Uvicorn
- **Data:** CCXT, yfinance, Alpaca, Polygon.io, ChromaDB
- **Container Scheduling:** Kubernetes, Docker Compose

---

## External Research Resources (D:\ Drive)

The following research and documentation directories on the `D:\` drive contain valuable resources that can be leveraged to upgrade this project:

| Resource | Path | Content | Potential Value |
|----------|------|---------|-----------------|
| AI Multicolony Docs | `D:\ai-multicolony-worktree\docs` | AGENT_ARCHITECTURE.md, MEMORY_ARCHITECTURE.md, BLUEPRINT.md | 🔥 Agent architecture patterns, decision logs |
| Deer Flow Backend | `D:\ai-multicolony-worktree\packages\deer-flow\backend\docs` | API.md, AUTH design, ARCHITECTURE docs | 🔥 Backend patterns, auth, encryption |
| Research Foundation | `D:\docs\research` | Research.md, bh-cyberbee-philosophy, DhaHer-Research-Queue | 🔥 Research methodology, philosophy, queue |
| Autonomous Organism | `D:\repositories\Autonomous-Organism\docs` | VISION, ARCHITECTURE, PRD | 🧠 Autonomous systems philosophy |
| Trading Plan AI | `D:\repositories\archived\Trading-Plan-AI-Interactive-worktree\docs` | Trading plan templates, advanced UI | 📊 Trading strategy references |
| Market Research Skills | `D:\ai-multicolony-worktree\skills\market-research-reports` | Market research automation | 📈 Automated market research |
| Academic Papers | `D:\ai-multicolony-worktree\skills\aminer-daily-paper` | Daily paper agent | 📚 Paper-based trading research |
| Charts References | `D:\ai-multicolony-worktree\skills\charts\references` | echarts, matplotlib, mermaid refs | 📊 Chart visualization for dashboard |

---

## External Backup

All removed/archived legacy code is stored at:
```
D:\_dhaher_backups\
├── _removed_legacy/                  ← 994 files (legacy packages, skills, etc.)
├── ai_multicolony/                   ← 252 files (agents already merged to quant_nanggroe/agents/)
├── graphify-out/                     ← 4,629 files (previous graph data)
├── agent-ctx/                        ← 9 files (builder context docs)
├── quant_nanggroe_engine_legacy/     ← 9 files (legacy engine from root)
├── packages_autonomous-organism/     ← 138 files
└── packages_crucix/                  ← 94 files
```

---

## AI Agent Entry Points

AI agents (Claude, Copilot, Cursor, Gemini) should read these files in order:
1. `AGENTS.md` — How to read this repository
2. `CLAUDE.md` / `COPILOT.md` / `CURSOR.md` / `GEMINI.md` — IDE-specific instructions
3. `MASTER_SYSTEM_PROMPT.md` — Master prompt for operating in this system
4. `docs/00_VISION.md` — Project north star
5. `docs/02_ARCHITECTURE.md` — System architecture
6. `docs/16_AI_MEMORY.md` — Stable facts and common pitfalls

---

|## Changelog (Recent)
|
|### v4.4.0 — Production-Grade Dashboard OS + Hedge Fund UI
|- ✅ **1766/1766 tests passing (100%)** — 106 strategy modules, 30 API routes, 7 brokers, 154 test files
|- ✅ **Recent Bug Fixes:** pandas 3.0 freq alias (H→h), OHLCV symbol field required, toggle script CamelCase→snake_case, scripts/__init__.py lazy importer, paper_broker BUY limit price, openbb_provider api_key passthrough, strategy registry normalize
- ✅ **Apple macOS Liquid Glass Design System** — glassmorphism backdrop-filter blur 24-40px, double-bezel card architecture, noise/grain overlay, Bloomberg-style data cells (`.bbg-cell`)
- ✅ **Design Tokens** — CSS custom properties for brand colors (emerald/amber/purple), surface layers (white/2% → 8%), semantic colors (profit/loss/bid/ask), 12+ animations (shimmer, slide-up, float, glow, ticker)
- ✅ **Auto Day/Night Theme** — `ThemeProvider` with system preference listener, localStorage persistence, DOM class toggle, flash prevention, 3 modes (system/dark/light)
- ✅ **Live Multi-Broker Trading Page** — 5 accounts (MT5 Live, MT5 Demo, Binance Futures, IBKR Pro, Paper Trading), account switching, cross-broker aggregation (total equity/balance/margin/positions), quick order entry (buy/sell, market/limit/stop/stop-limit/TWAP), open positions table per broker
- ✅ **Live Portfolio Page** — Cross-broker P&L aggregation, equity curve with drawdown toggle, asset allocation donut, ATR-based position sizing calculator, 10 performance metrics (Sharpe/Sortino/Calmar/Win Rate/Profit Factor)
- ✅ **WebSocket Real-Time** — `useWebSocket` hook with exponential backoff reconnection (1s→30s with jitter), subscription management, 4 channels (price, regime, risk, portfolio), auto-store integration via callbacks
- ✅ **API Client with Retry** — 3 retries with exponential backoff, request deduplication for GET, 30s timeout with AbortController, `ApiError` class with retryable flag, 30+ typed API endpoints
- ✅ **Granular Store** — Zustand store with per-endpoint loading/error states, WebSocket real-time data integration, notification system with cap
- ✅ **ErrorBoundary + LoadingSkeleton** — React ErrorBoundary with inline ErrorDisplay + retry button, 7 skeleton variants (StatusCard, ChartCard, Page, Table, AgentCard, DashboardGrid)
- ✅ **Hedge Fund Perspective Audit — 14 Critical Fixes:**
  - Fixed missing `useState` imports in strategies, risk, settings, factors pages
  - Fixed `mockStrategies` references → replaced with state variable (runtime error fix)
  - Fixed `GlassCard` → `Card` component (component didn't exist)
  - Fixed `realtimePortfolio` source (`useRealtimeData()` → `useAppStore()`)
  - Added `glow` prop to ChartCard (was used by 3 pages but missing from interface)
  - Added `trend` prop to StatusCard with rendered trend icon
  - Added `LoadingSkeleton` component with variant delegation
  - Added `"info"` variant to StatusCard variant union type
  - Connected all pages to real API endpoints with automatic fallback to mock data

### v4.3.4 — Zero Fragmentation Restructure
- ✅ Removed legacy packages: `packages/agentic-legacy`, `packages/hermes-quant`, `packages/autonomous-organism`, `packages/crucix`
- ✅ Removed orphan `ai_multicolony/` (agents merged to `quant_nanggroe/agents/`)
- ✅ Removed dual engine: root `engine/` archived (moved to external backup)
- ✅ Archived 60 non-essential skills (only pdf/pptx/xlsx retained for trading reports)
- ✅ Cleaned 3 `docs_backup_*` directories and runtime logs
- ✅ Removed `agent-ctx/`, `graphify-out/`, `_removed_legacy/` from worktree
- ✅ All external backups stored at `D:\_dhaher_backups\`
- ✅ Fixed `__all__` in all `__init__.py` (string literals instead of undefined identifiers)
- ✅ `.gitignore` updated — no backup/legacy artifacts in version control
- ✅ Single unified Python package: `quant_nanggroe/` (24 subpackages, 542+ .py files)

---

## License

MIT — Dhaher Labs / Quant Nanggroe Hedge Fund
