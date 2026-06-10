# Quant Nanggroe AI — Migration Plan

**Version 0.2.0 | From Individual Repos to Monorepo**

> This document provides the comprehensive migration guide for transitioning from individual repositories to the Quant Nanggroe AI monorepo. It covers breaking changes, configuration migration, data migration, API changes, deployment migration, and rollback procedures.

---

## Table of Contents

1. [Migration Overview](#1-migration-overview)
2. [From Individual Repos to Monorepo](#2-from-individual-repos-to-monorepo)
3. [Breaking Changes](#3-breaking-changes)
4. [Configuration Migration](#4-configuration-migration)
5. [Data Migration](#5-data-migration)
6. [API Changes](#6-api-changes)
7. [Deployment Migration](#7-deployment-migration)
8. [Rollback Procedures](#8-rollback-procedures)

---

## 1. Migration Overview

### 1.1 Migration Scope

The migration consolidates 20+ individual trading/quant repositories into a single Python monorepo (`quant-nanggroe-ai`). This affects:

- **Source code**: All Python modules, configuration files, and scripts
- **Dependencies**: Unified dependency tree replacing per-repo requirements
- **Configuration**: Centralized Pydantic Settings replacing scattered config files
- **Database**: Unified SQLAlchemy schema replacing per-repo data stores
- **API**: Single FastAPI server replacing multiple microservices
- **Deployment**: Single Docker image replacing per-repo containers

### 1.2 Migration Phases

| Phase | Description | Duration | Risk Level |
|-------|-------------|----------|------------|
| **Phase 1** | Foundation migration (core framework, agents, config) | 2 weeks | Low |
| **Phase 2** | Engine migration (factors, risk, backtest, execution) | 3 weeks | Medium |
| **Phase 3** | Integration migration (exchanges, memory, MCP) | 2 weeks | Medium |
| **Phase 4** | Data migration (database, cache, journal) | 1 week | High |
| **Phase 5** | Deployment migration (Docker, CI/CD, monitoring) | 1 week | Medium |

### 1.3 Pre-Migration Checklist

- [ ] Back up all existing databases and configuration files
- [ ] Document current API endpoints and their consumers
- [ ] Verify all API keys are available as environment variables
- [ ] Create migration test environment
- [ ] Establish rollback criteria and procedures
- [ ] Notify all downstream consumers of API changes

---

## 2. From Individual Repos to Monorepo

### 2.1 Repository Mapping

| Source Repo | Source Structure | Target Module | Target Structure |
|-------------|-----------------|---------------|-----------------|
| `ai-hedge-fund/` | Single `main.py` with all agents | `quant_nanggroe/agents/` | 9 agent modules with `agent.py`, `prompts.py`, `tools.py` |
| `alpha101/` | `factors.py` with all 101 alphas | `quant_nanggroe/engine/factors/alpha101.py` | 50+ `AlphaFactor` subclasses |
| `gtja191/` | `factors.py` with all 191 factors | `quant_nanggroe/engine/factors/gtja191.py` | 191 factor implementations |
| `trading-agents/` | `agents/` with debate logic | `quant_nanggroe/agents/council/` | `debate.py`, `voting.py` |
| `ccxt-trading/` | `exchange.py` with CCXT wrapper | `quant_nanggroe/exchange/` | Full exchange layer with base, CCXT, Alpaca, paper brokers |
| `risk-manager/` | `risk.py` with VaR/Kelly | `quant_nanggroe/engine/risk/` | 10 risk modules (var, kelly, drawdown, etc.) |
| `backtest-engine/` | `backtest.py` with engine | `quant_nanggroe/engine/backtest/` | 8 backtest modules |
| `portfolio-opt/` | `optimizer.py` | `quant_nanggroe/engine/risk/position_sizing.py`, `risk_parity.py` | Modular optimization |
| `data-providers/` | `providers.py` with multi-source | `quant_nanggroe/exchange/` + Settings | Unified via ExchangeInterface |
| `trade-journal/` | `journal.py` | `quant_nanggroe/memory/journal.py` | Enhanced journal with reflection |

### 2.2 Import Path Migration

| Old Import | New Import | Notes |
|-----------|-----------|-------|
| `from agents import ResearcherAgent` | `from quant_nanggroe.agents.researcher.agent import ResearcherAgent` | Full module path |
| `from factors import Alpha101` | `from quant_nanggroe.engine.factors.alpha101 import Alpha101_001` | Per-factor import |
| `from risk import RiskManager` | `from quant_nanggroe.engine.risk.manager import RiskManager` | Same class name |
| `from exchange import CCXTBroker` | `from quant_nanggroe.exchange.ccxt_broker import CCXTBroker` | Same class name |
| `from backtest import BacktestEngine` | `from quant_nanggroe.engine.backtest.engine import BacktestEngine` | Same class name |
| `from config import Settings` | `from quant_nanggroe.config.settings import get_settings` | Singleton pattern |
| `from journal import TradeJournal` | `from quant_nanggroe.memory.journal import TradeJournal` | Same class name |
| `from models import Trade` | `from quant_nanggroe.data.models import Trade` | ORM models |
| `from mcp import MCPServer` | `from quant_nanggroe.mcp.server import MCPServer` | Same class name |

### 2.3 Package Structure Migration

**Before (individual repos):**
```
ai-hedge-fund/
├── main.py
├── agents.py
└── requirements.txt

alpha101/
├── factors.py
└── requirements.txt

risk-manager/
├── risk.py
└── requirements.txt
```

**After (monorepo):**
```
quant-nanggroe-ai/
├── pyproject.toml
├── quant_nanggroe/
│   ├── __init__.py
│   ├── agents/
│   │   ├── graph.py
│   │   ├── state.py
│   │   ├── registry.py
│   │   ├── council/
│   │   ├── researcher/
│   │   ├── strategist/
│   │   ├── risk/
│   │   ├── trader/
│   │   ├── portfolio/
│   │   ├── execution/
│   │   ├── macro/
│   │   ├── crypto/
│   │   └── forex/
│   ├── engine/
│   │   ├── factors/
│   │   ├── risk/
│   │   ├── backtest/
│   │   ├── execution/
│   │   └── models/
│   ├── exchange/
│   ├── memory/
│   ├── mcp/
│   ├── security/
│   ├── config/
│   ├── data/
│   └── types/
└── docs/
```

---

## 3. Breaking Changes

### 3.1 API Breaking Changes

| Change | Before | After | Impact |
|--------|--------|-------|--------|
| **Agent creation** | `ResearcherAgent()` | `AgentFactory.create_agent("researcher")` | All agent instantiation code |
| **Settings access** | `Settings()` | `get_settings()` | All configuration access |
| **Exchange interface** | Broker-specific methods | `ExchangeInterface` abstract methods | All exchange interactions |
| **Risk assessment** | Simple pass/fail | 9-checkpoint `RiskAssessment` with verdicts | All risk checks |
| **Trade execution** | Direct broker calls | `ExecutionManager` with guard pipeline | All order placement |
| **Factor computation** | Function-based | `AlphaFactor.compute(df)` class-based | All factor usage |
| **State management** | Dict-based | `AgentState` TypedDict | All pipeline state |

### 3.2 Configuration Breaking Changes

| Setting | Before | After | Migration |
|---------|--------|-------|-----------|
| API keys in config files | `config.yaml` | Environment variables with `QNAI_` prefix | Move to `.env` or environment |
| Risk limits configurable | `risk.max_per_trade = 0.02` | Hardcoded constitutional limits | Accept hardcoded values |
| Exchange selection | `exchange = "binance"` | `ExchangeFactory.create("binance")` | Use factory pattern |
| LLM model selection | `model = "gpt-4"` | `deep_think_model` / `quick_think_model` | Separate deep/quick models |
| Paper trading flag | `paper = true` | `QNAI_ALPACA_PAPER=true` | Environment variable |

### 3.3 Data Model Breaking Changes

| Model | Before | After | Migration Action |
|-------|--------|-------|-----------------|
| Trade record | Dict with custom keys | `Trade` ORM model with typed columns | Rebuild from JSON exports |
| Position | Dict with float values | `Position` ORM model with P&L tracking | Rebuild from trade history |
| Portfolio | In-memory dict | `PortfolioSnapshot` ORM model with time series | Initialize from positions |
| Risk assessment | Simple boolean | `RiskAssessment` with 9 checkpoints, VaR, CVaR | Re-run assessments |
| Agent output | String | `AgentOutput` with confidence, tool calls, timing | Richer logging |

---

## 4. Configuration Migration

### 4.1 Environment Variable Mapping

| Old Config File | Old Key | New Environment Variable | Default |
|----------------|---------|-------------------------|---------|
| `config.yaml` | `openai_api_key` | `QNAI_OPENAI_API_KEY` | None (required) |
| `config.yaml` | `anthropic_api_key` | `QNAI_ANTHROPIC_API_KEY` | None |
| `config.yaml` | `binance_api_key` | `QNAI_BINANCE_API_KEY` | None |
| `config.yaml` | `binance_api_secret` | `QNAI_BINANCE_API_SECRET` | None |
| `config.yaml` | `alpaca_api_key` | `QNAI_ALPACA_API_KEY` | None |
| `config.yaml` | `alpaca_api_secret` | `QNAI_ALPACA_API_SECRET` | None |
| `config.yaml` | `database_url` | `QNAI_DATABASE_URL` | `sqlite:///quant_nanggroe.db` |
| `config.yaml` | `redis_url` | `QNAI_REDIS_URL` | None |
| `config.yaml` | `log_level` | `QNAI_LOG_LEVEL` | `INFO` |
| `config.yaml` | `paper_trading` | `QNAI_ALPACA_PAPER` | `true` |
| `config.yaml` | `default_model` | `QNAI_DEFAULT_LLM_MODEL` | `gpt-4o` |
| `secrets.env` | All API keys | Same variable names | None |

### 4.2 Configuration Migration Script

```bash
#!/bin/bash
# migrate_config.sh — Migrate from individual repo configs to monorepo

# 1. Create .env file from existing configs
cat > .env << EOF
# Quant Nanggroe AI Configuration
# Migrated from individual repo configs on $(date)

# LLM API Keys
QNAI_OPENAI_API_KEY=${OPENAI_API_KEY:-}
QNAI_ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}
QNAI_GOOGLE_API_KEY=${GOOGLE_API_KEY:-}

# Trading API Keys
QNAI_ALPACA_API_KEY=${ALPACA_API_KEY:-}
QNAI_ALPACA_API_SECRET=${ALPACA_API_SECRET:-}
QNAI_ALPACA_PAPER=true
QNAI_BINANCE_API_KEY=${BINANCE_API_KEY:-}
QNAI_BINANCE_API_SECRET=${BINANCE_API_SECRET:-}

# Data API Keys
QNAI_ALPHA_VANTAGE_API_KEY=${ALPHA_VANTAGE_API_KEY:-}
QNAI_POLYGON_API_KEY=${POLYGON_API_KEY:-}
QNAI_FRED_API_KEY=${FRED_API_KEY:-}
QNAI_COINGECKO_API_KEY=${COINGECKO_API_KEY:-}

# Database
QNAI_DATABASE_URL=sqlite:///quant_nanggroe.db

# Logging
QNAI_LOG_LEVEL=INFO
QNAI_LOG_FORMAT=json
EOF

echo "Configuration migrated to .env file"
```

### 4.3 Validation

After migration, verify configuration:

```python
from quant_nanggroe.config.settings import get_settings

settings = get_settings()
print(f"App: {settings.app_name} v{settings.version}")
print(f"LLM: {settings.default_llm_provider}/{settings.default_llm_model}")
print(f"Paper trading: {settings.alpaca_paper}")
print(f"Risk limits: {settings.risk_max_per_trade}% per trade, {settings.risk_max_daily_loss}% daily")
```

---

## 5. Data Migration

### 5.1 Database Schema Migration

The monorepo uses SQLAlchemy ORM with Alembic for schema migrations. The migration from individual repo databases follows this process:

**Step 1: Export existing data**

```bash
# From each source database
sqlite3 old_trading.db ".dump trades" > trades_export.sql
sqlite3 old_risk.db ".dump risk_events" > risk_export.sql
sqlite3 old_portfolio.db ".dump positions" > positions_export.sql
```

**Step 2: Create new database schema**

```bash
cd quant-nanggroe-ai
bun run db:push  # Push Prisma schema (if using)
# OR
alembic upgrade head  # Push SQLAlchemy schema
```

**Step 3: Transform and import data**

```python
# migrate_data.py
import json
from quant_nanggroe.data.models import Trade, Position, RiskEvent
from quant_nanggroe.config.settings import get_settings
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

engine = create_engine(get_settings().database_url)

# Transform old trade records to new Trade model
with Session(engine) as session:
    for old_trade in old_trades:
        new_trade = Trade(
            symbol=old_trade["symbol"],
            side=old_trade["side"],
            order_type=old_trade.get("order_type", "market"),
            quantity=old_trade["quantity"],
            price=old_trade["price"],
            status=old_trade.get("status", "closed"),
            risk_verdict=old_trade.get("risk_verdict"),
        )
        session.add(new_trade)
    session.commit()
```

### 5.2 Journal Migration

```python
# migrate_journal.py
from quant_nanggroe.memory.journal import TradeJournal

# Load old journal
old_journal = json.load(open("old_trades.json"))

# Create new journal
journal = TradeJournal(persist_path="data/journal.json")

for trade in old_journal["trades"]:
    trade_id = journal.record_entry(
        symbol=trade["symbol"],
        side=trade["side"],
        price=trade["entry_price"],
        quantity=trade["quantity"],
        agent_name=trade.get("agent_name"),
        strategy=trade.get("strategy"),
        reasoning=trade.get("reasoning"),
    )
    
    if trade.get("exit_price"):
        journal.record_exit(
            symbol=trade["symbol"],
            price=trade["exit_price"],
            pnl=trade.get("pnl"),
        )
    
    if trade.get("reflection"):
        journal.add_reflection(
            symbol=trade["symbol"],
            notes=trade["reflection"]["notes"],
            rating=trade["reflection"].get("rating"),
        )

journal.save()
```

### 5.3 Data Integrity Verification

After migration, verify:

```python
# Verify record counts
from sqlalchemy import func, Session
from quant_nanggroe.data.models import Trade, Position, RiskEvent

with Session(engine) as session:
    trade_count = session.query(func.count(Trade.id)).scalar()
    position_count = session.query(func.count(Position.id)).scalar()
    risk_count = session.query(func.count(RiskEvent.id)).scalar()
    
    print(f"Trades: {trade_count}")
    print(f"Positions: {position_count}")
    print(f"Risk Events: {risk_count}")
    
    # Verify PnL totals match
    total_pnl = session.query(func.sum(Trade.commission)).scalar()
    print(f"Total commission: {total_pnl}")
```

---

## 6. API Changes

### 6.1 Endpoint Migration

| Old Endpoint | New Endpoint | Method | Changes |
|-------------|-------------|--------|---------|
| `POST /trade` | `POST /api/v1/trade` | POST | New request/response models |
| `GET /portfolio` | `GET /api/v1/portfolio` | GET | Enhanced position tracking |
| `GET /agents` | `GET /api/v1/agents` | GET | 9 agents instead of 4 |
| `POST /backtest` | `POST /api/v1/backtest` | POST | New strategy types, metrics |
| `GET /risk/{symbol}` | `GET /api/v1/risk/{symbol}` | GET | 9-checkpoint assessment |
| `GET /health` | `GET /api/v1/health` | GET | Component-level health |
| — | `WS /ws/trading` | WS | New WebSocket endpoint |

### 6.2 Request/Response Model Changes

**Trade Request:**

| Field | Before | After | Notes |
|-------|--------|-------|-------|
| `symbols` | Array of strings | Array of strings | Same |
| `model` | Single model name | `deep_model` + `quick_model` | Dual-model architecture |
| `provider` | Not supported | LLM provider name | Multi-provider support |
| `paper` | Not supported | Boolean (default: true) | Paper/live toggle |
| `metadata` | Not supported | Optional dict | Pipeline metadata |

**Trade Response:**

| Field | Before | After | Notes |
|-------|--------|-------|-------|
| `decision` | Single string | Array of `decisions` | Multi-symbol decisions |
| `confidence` | Single float | Per-decision confidence | Granular confidence |
| `risk_verdict` | Not included | APPROVED/VETOED/KILL_SWITCH | Constitutional risk |
| `signals` | Not included | Array of signals | Pre-risk signals |
| `agent_outputs` | Not included | Dict of agent outputs | Full auditability |

### 6.3 WebSocket Protocol Changes

| Message Type | Before | After | Notes |
|-------------|--------|-------|-------|
| `trade_update` | Not supported | Full pipeline events | Real-time tracking |
| `risk_alert` | Not supported | Constitutional violations | Risk monitoring |
| `position_change` | Not supported | Real-time position updates | Portfolio tracking |
| `heartbeat` | Not supported | 30-second interval | Connection keep-alive |

---

## 7. Deployment Migration

### 7.1 Docker Migration

**Before (individual containers):**
```yaml
# docker-compose.old.yml
services:
  trading:
    build: ./ai-hedge-fund
    ports: ["8000:8000"]
  
  backtest:
    build: ./backtest-engine
    ports: ["8001:8000"]
  
  risk:
    build: ./risk-manager
    ports: ["8002:8000"]
```

**After (single monorepo container):**
```yaml
# docker-compose.yml
services:
  api:
    build: .
    ports: ["8000:8000"]
    environment:
      - QNAI_DATABASE_URL=sqlite:///quant_nanggroe.db
      - QNAI_OPENAI_API_KEY=${OPENAI_API_KEY}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  worker:
    build: .
    command: qnai worker
    environment:
      - QNAI_DATABASE_URL=sqlite:///quant_nanggroe.db
    depends_on:
      api:
        condition: service_healthy
```

### 7.2 CI/CD Migration

**Before**: Per-repo CI/CD pipelines with independent build/test/deploy cycles.

**After**: Unified CI/CD pipeline:

```yaml
# .github/workflows/ci.yml
name: Quant Nanggroe AI CI
on: [push, pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install ruff mypy
      - run: ruff check quant_nanggroe/
      - run: mypy quant_nanggroe/ --ignore-missing-imports

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -e ".[dev]"
      - run: pytest tests/ -v --tb=short

  build:
    needs: [lint, test]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t quant-nanggroe-ai .
```

### 7.3 Monitoring Migration

**Before**: Per-repo monitoring with fragmented logs.

**After**: Unified monitoring with structured JSON logging:

```python
# All components use structured logging
import structlog
logger = structlog.get_logger()

logger.info("trade_executed",
    symbol="BTC/USDT",
    action="BUY",
    quantity=0.1,
    confidence=0.85,
    risk_verdict="APPROVED",
    agent="trader",
    pipeline_run_id="run-123",
)
```

---

## 8. Rollback Procedures

### 8.1 Rollback Criteria

Initiate rollback if any of the following occur within 48 hours of migration:

| Criterion | Threshold | Action |
|-----------|-----------|--------|
| API error rate | > 5% | Rollback to previous API |
| Trade execution failures | > 1% | Switch to paper trading |
| Data inconsistency | Any detected | Stop pipeline, investigate |
| Performance degradation | > 2x latency increase | Scale up or rollback |
| Constitutional risk bypass | Any detected | Immediate rollback + audit |

### 8.2 Rollback Steps

**Step 1: Stop the monorepo pipeline**
```bash
# Stop all services
docker-compose down

# Or if running directly
pkill -f "uvicorn quant_nanggroe.api"
```

**Step 2: Restore previous database**
```bash
# Restore from backup
cp backup/quant_nanggroe.db.bak quant_nanggroe.db

# Or from SQL dump
sqlite3 quant_nanggroe.db < backup/quant_nanggroe_dump.sql
```

**Step 3: Restore previous configuration**
```bash
# Restore environment variables
cp backup/.env.bak .env

# Restore old docker-compose
cp backup/docker-compose.old.yml docker-compose.yml
```

**Step 4: Restart previous services**
```bash
# Start old services
docker-compose -f docker-compose.old.yml up -d

# Verify health
curl http://localhost:8000/health
```

**Step 5: Verify data integrity**
```bash
# Check trade records match
python verify_migration.py --compare-backup backup/pre_migration/

# Check portfolio values match
python verify_portfolio.py --expected backup/portfolio_snapshot.json
```

### 8.3 Partial Rollback

If only specific components need rollback:

| Component | Rollback Method |
|-----------|----------------|
| **Agent pipeline** | Switch to previous TradingGraph version via code rollback |
| **Risk engine** | Disable new 9-checkpoint gate; use simple pass/fail |
| **Exchange layer** | Switch to previous broker adapter |
| **Factor library** | Disable new factors; use only technical indicators |
| **API server** | Route traffic to previous API version via load balancer |

### 8.4 Data Recovery

If data is lost or corrupted during migration:

1. **Database backup**: Pre-migration database dump stored in `backup/`
2. **Journal backup**: Trade journal JSON files backed up before migration
3. **Configuration backup**: All config files and `.env` stored in `backup/`
4. **Exchange state**: Positions can be re-synced from exchange APIs
5. **Audit trail**: All migration actions logged with timestamps

### 8.5 Post-Rollback Actions

After a successful rollback:

1. Document the root cause of the rollback
2. Create a fix in a feature branch
3. Test the fix in the migration test environment
4. Re-attempt migration with the fix applied
5. Increase monitoring frequency for 72 hours post-migration

---

*© 2025-2026 Quant Nanggroe AI | Migration Plan v0.2.0*
