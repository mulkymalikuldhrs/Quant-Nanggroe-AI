# Quant Nanggroe AI v5 — Autonomous Hedge Fund OS

**DHAHER LABS — REALIZATION MANDATE** — Real production system. Real market capability. Autonomous alpha generation.

85 API routes | Live paper trading daemon | Multi-agent AI council | Full-stack quant platform

## Architecture

```
FastAPI Backend (port 8000)
├── Market Data     — price, OHLCV, regime, sentiment (multi-provider failover)
├── Trading Engine  — orders, positions, risk checks, kill switch
├── Portfolio       — PnL, risk, performance, stress-test
├── Backtest        — run, list, results, strategy registry
├── Options         — chain, Greeks, vol surface, multi-leg strategies
├── Signals         — generate, list, active signals
├── ML/RL           — RL train/inference, XGBoost, PyTorch, scikit-learn
├── Data Providers  — FRED, SEC EDGAR, geopolitics
├── AI Agents       — LangGraph orchestration, BerkshireAnalyzer, ConsensusEngine
├── Governance      — council voting, debate, investor personas
├── Monitoring      — health, metrics, PnL attribution, risk, audit, regime
├── Memory          — knowledge graph storage & retrieval
└── Dashboard       — Next.js SPA in /dashboard (served on :3000)
```

## Quick Start

```bash
# Dev install
pip install -e ".[dev]"

# Backend
uvicorn quant_nanggroe.api.app:app --host 0.0.0.0 --port 8000

# Frontend (dashboard)
cd dashboard && npm install && npm run build && npx next start -p 3000

# Or boot BOTH with one click:
launch.bat        # Windows: starts backend + frontend, opens http://localhost:3000

# Paper trading daemon
python scripts/qna-paper-daemon.py --interval 3600

# Tests
make test

# Docker
docker-compose -f deploy/docker/docker-compose.yml up -d
```

## Features

| Domain | Capabilities |
|--------|-------------|
| **Strategies** | RegimeBased, MeanReversion, TrendFollow, 151+ catalog |
| **Risk** | 0.5% max per trade, 1% daily loss limit, 3% weekly |
| **Execution** | Paper broker, Alpaca, Binance, Bybit, IBKR, CCXT |
| **Data** | 12 providers auto-failover, SQLite/PostgreSQL, Redis cache |
| **OSINT** | Crucix package — 27 intelligence sources, ACLED conflict, ADSB tracking |
| **Security** | JWT auth, encryption at rest, audit log, Chinese Wall |
| **ML** | XGBoost, PyTorch, scikit-learn, GARCH synthetic data |
| **DRL** | PPO, DQN, SAC agents — numpy-only, no GPU |
| **Options** | SABR vol surface, straddle/spread/butterfly, Greeks |
| **Analytics** | Sharpe, Sortino, Calmar, drawdown, benchmark comparison |

## API (85 routes)

```
/api/market/*        — price, OHLCV, regime, sentiment, pressure
/api/trading/*       — orders, positions, trades, risk-check
/api/portfolio/*     — summary, performance, risk, stress-test
/api/backtest/*      — run, list, result, strategies
/api/options/*       — chain, analyze, strategy, vol-surface
/api/signals/*       — generate, list, active
/api/rl/*            — train, inference, agents
/api/analytics/*     — metrics, compare
/api/strategy/*      — registry
/api/fred/*          — series, search
/api/sec/*           — EDGAR filings, company, search
/api/geopolitics/*   — regions, sanctions, list
/api/agents/*        — status, run, kill-switch
/api/agentic/*       — berkshire, consensus
/api/council/*       — list, vote, detail
/api/debate/*        — list, new, detail
/api/personas/*      — list, types
/api/monitor/*       — health, metrics, PnL, risk, audit
/api/memory/*        — store, search
/api/channels/*      — list
/api/colony/*        — list, agents, status
/health              — health check
/metrics             — Prometheus metrics
```

## Project Structure

```
quant_nanggroe/
├── api/              — FastAPI app, routes, middleware, static dashboard
├── agents/           — Personas, registry, agentic engine
├── engine/           — Trading, strategy, execution, risk
├── services/         — Monitor, data, providers
├── config/           — Settings, credentials
├── database/         — SQLAlchemy models, migrations (Alembic)
├── connectors/       — Exchange connectors (CCXT, Alpaca, etc.)
├── docker/           — Docker Compose, Dockerfiles
├── nginx/            — Production reverse proxy config
├── scripts/          — Paper daemon, launcher, utilities
├── docs/             — Architecture, API reference, runbooks, reports
└── tests/            — 26 test directories, 468+ tests

ai_multicolony/       — Multi-agent swarm framework (delegated)
packages/crucix/      — OSINT intelligence: 27 sources, ACLED, ADSB, briefing system
packages/agentic-legacy/ — Archived multi-agent reference
```

## Test Suite

- **468+ tests** across 26 test directories
- Hedge-fund critical: 265 tests, 0 failed
- Coverage: engine, agents, API, data, exchange, risk
- CI: GitHub Actions + GitLab CI pipelines

## Documentation

| Document | Description |
|----------|-------------|
| `ARCHITECTURE.md` | Full 27K system architecture (merged from home clone) |
| `QUANT_NANGRAOE_COMPLETE.md` | Complete API reference |
| `DHAHER_LABS_MANDATE.md` | Constitutional mandate |
| `AGENTS.md` | AI-Engineering-OS constitution |
| `docs/API.md` | API documentation |
| `docs/RUNBOOK.md` | Operations runbook |
| `docs/OPS_CHECKLIST.md` | Deployment checklist |
| `docs/CHANGELOG.md` | Release history |
| `docs/SECURITY.md` | Security policies |

## Status

- **Server**: Up, 85 routes, auth protected
- **Dashboard**: Next.js SPA in `dashboard/` served on :3000 (build: `cd dashboard && npm install && npm run build && npx next start -p 3000`, or use `launch.bat`)
- **Single Launcher**: `launch.bat` boots backend + frontend + opens browser
- **Paper Trading**: Autonomous daemon running
- **Memory**: Graphify'd, Hermes memory saved
- **Graph**: `graphify-out/graph.json` (regenerated via `graphify update .`)
- **Graphify commands**: `graphify query "?"`, `graphify path "A" "B"`, `graphify update .`

## Ecosystem

- [DhaHer Labs](https://dhaher-labs.codeberg.page) — Ecosystem home
- [Crucix — OSINT intelligence terminal](https://crucix.live)
- [Autonomous Organism Manifesto](https://dhaherlabsos.vercel.app/manifesto)
- [System Status](https://dhaherlabsos.vercel.app/status)
- [GitHub: dhaher-labs](https://github.com/dhaher-labs)
- [Codeberg: Dhaher-Labs](https://codeberg.org/Dhaher-Labs)

## License

MIT — DhaHer Labs / Quant Nanggroe AI Team
