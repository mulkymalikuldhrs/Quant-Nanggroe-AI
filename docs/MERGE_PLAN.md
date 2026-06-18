# Merge Plan: Quant Nanggroe AI Monorepo

**Version 15.3.0 | Repository Consolidation Strategy**

This document describes the plan for merging 23 independent repositories into a single monorepo under the Quant Nanggroe AI project. It covers the repository inventory, git subtree merge procedures, dependency conflict resolution, and de-duplication strategy.

---

## 1. Repository Inventory

### 1.1 All 23 Repositories with Target Directories

| # | Source Repository | Target Directory | Language | Description |
|---|---|---|---|---|
| 1 | quant-nanggroe-ai | `/` (root) | TypeScript + Python | Core monorepo — frontend + backend |
| 2 | HermesQuantOS | `/hermes` | Python | Parent project: unified intelligence ecosystem |
| 3 | FinceptTerminal | `/packages/fincept-terminal` | Python | Legacy CLI terminal (DEC-001: deprecated) |
| 4 | bloomberg-terminal | `/packages/bloomberg-tui` | Python | Legacy TUI terminal (DEC-001: deprecated) |
| 5 | SolSniperX | `/packages/sol-sniper-x` | Rust | Solana sniper bot (DEC-002: deprecated) |
| 6 | Kronos | `/packages/kronos` | C++ | High-frequency execution engine (DEC-002: active) |
| 7 | ai-trader | `/packages/ai-trader` | Python | Legacy AI trading module (DEC-002: deprecated) |
| 8 | langgraph-trading | `/packages/langgraph-trading` | Python | LangGraph trading graph (DEC-003: active) |
| 9 | crewai-agents | `/packages/crewai-agents` | Python | CrewAI agent workflows (DEC-003: research only) |
| 10 | autogen-workflows | `/packages/autogen-workflows` | Python | AutoGen conversation workflows (DEC-003: research only) |
| 11 | quant-backtest | `/packages/quant-backtest` | Python | Backtesting engine and metrics |
| 12 | risk-guardian | `/packages/risk-guardian` | Python | Constitutional risk management |
| 13 | market-data-pipeline | `/packages/market-data` | Python | Market data ingestion and normalization |
| 14 | pressure-engine | `/packages/pressure-engine` | Python | Pressure normalization engine |
| 15 | decision-engine | `/packages/decision-engine` | Python | Decision synthesis engine |
| 16 | alpha-factors | `/packages/alpha-factors` | Python | Alpha101 and GTJA191 factors |
| 17 | vector-memory | `/packages/vector-memory` | Python | TF-IDF vector store |
| 18 | web-terminal | `/packages/web-terminal` | TypeScript | React frontend (merged into root) |
| 19 | execution-brokers | `/packages/execution-brokers` | Python | Broker integrations (Binance, Alpaca, Polymarket) |
| 20 | prediction-markets | `/packages/prediction-markets` | Python | Polymarket integration |
| 21 | docker-infra | `/infra` | YAML | Docker Compose, Dockerfile, CI/CD |
| 22 | api-server | `/packages/api-server` | Python | FastAPI REST + WebSocket server |
| 23 | shared-types | `/packages/shared-types` | Python + TypeScript | Shared type definitions (Pydantic + TS interfaces) |

### 1.2 Classification

```
ACTIVE (merged into core):
  ├── quant-nanggroe-ai     → root
  ├── Kronos                → /packages/kronos
  ├── langgraph-trading     → /packages/langgraph-trading
  ├── quant-backtest        → /packages/quant-backtest
  ├── risk-guardian         → /packages/risk-guardian
  ├── market-data-pipeline  → /packages/market-data
  ├── pressure-engine       → /packages/pressure-engine
  ├── decision-engine       → /packages/decision-engine
  ├── alpha-factors         → /packages/alpha-factors
  ├── vector-memory         → /packages/vector-memory
  ├── execution-brokers     → /packages/execution-brokers
  ├── prediction-markets    → /packages/prediction-markets
  ├── api-server            → /packages/api-server
  └── shared-types          → /packages/shared-types

RESEARCH (retained for reference):
  ├── crewai-agents         → /packages/crewai-agents
  └── autogen-workflows     → /packages/autogen-workflows

DEPRECATED (frozen, no active development):
  ├── FinceptTerminal       → /packages/fincept-terminal
  ├── bloomberg-terminal    → /packages/bloomberg-tui
  ├── SolSniperX            → /packages/sol-sniper-x
  ├── ai-trader             → /packages/ai-trader
  └── web-terminal          → /packages/web-terminal (merged into root)

INFRASTRUCTURE:
  └── docker-infra          → /infra
```

---

## 2. Git Subtree Merge Script

### 2.1 Prerequisites

```bash
# Ensure git-subtree is available
git subtree --version

# Set up remotes for all source repositories
# Replace URLs with actual repository locations
```

### 2.2 Remote Setup

```bash
#!/bin/bash
# scripts/setup_merge_remotes.sh

REMOTES=(
  "quant-nanggroe-ai|https://github.com/mulkymalikuldhrs/quant-nanggroe-ai.git"
  "hermes|https://github.com/mulkymalikuldhrs/HermesQuantOS.git"
  "fincept-terminal|https://github.com/mulkymalikuldhrs/FinceptTerminal.git"
  "bloomberg-tui|https://github.com/mulkymalikuldhrs/bloomberg-terminal.git"
  "sol-sniper-x|https://github.com/mulkymalikuldhrs/SolSniperX.git"
  "kronos|https://github.com/mulkymalikuldhrs/Kronos.git"
  "ai-trader|https://github.com/mulkymalikuldhrs/ai-trader.git"
  "langgraph-trading|https://github.com/mulkymalikuldhrs/langgraph-trading.git"
  "crewai-agents|https://github.com/mulkymalikuldhrs/crewai-agents.git"
  "autogen-workflows|https://github.com/mulkymalikuldhrs/autogen-workflows.git"
  "quant-backtest|https://github.com/mulkymalikuldhrs/quant-backtest.git"
  "risk-guardian|https://github.com/mulkymalikuldhrs/risk-guardian.git"
  "market-data|https://github.com/mulkymalikuldhrs/market-data-pipeline.git"
  "pressure-engine|https://github.com/mulkymalikuldhrs/pressure-engine.git"
  "decision-engine|https://github.com/mulkymalikuldhrs/decision-engine.git"
  "alpha-factors|https://github.com/mulkymalikuldhrs/alpha-factors.git"
  "vector-memory|https://github.com/mulkymalikuldhrs/vector-memory.git"
  "web-terminal|https://github.com/mulkymalikuldhrs/web-terminal.git"
  "execution-brokers|https://github.com/mulkymalikuldhrs/execution-brokers.git"
  "prediction-markets|https://github.com/mulkymalikuldhrs/prediction-markets.git"
  "docker-infra|https://github.com/mulkymalikuldhrs/docker-infra.git"
  "api-server|https://github.com/mulkymalikuldhrs/api-server.git"
  "shared-types|https://github.com/mulkymalikuldhrs/shared-types.git"
)

for entry in "${REMOTES[@]}"; do
  IFS='|' read -r name url <<< "$entry"
  git remote add "$name" "$url" 2>/dev/null || git remote set-url "$name" "$url"
  echo "Remote added: $name → $url"
done

echo "All remotes configured. Run fetch_all.sh next."
```

### 2.3 Subtree Merge Execution

```bash
#!/bin/bash
# scripts/execute_merges.sh
# Execute git subtree add for each repository

set -euo pipefail

MERGES=(
  # "remote_name|branch|target_prefix"
  "hermes|main|hermes"
  "fincept-terminal|main|packages/fincept-terminal"
  "bloomberg-tui|main|packages/bloomberg-tui"
  "sol-sniper-x|main|packages/sol-sniper-x"
  "kronos|main|packages/kronos"
  "ai-trader|main|packages/ai-trader"
  "langgraph-trading|main|packages/langgraph-trading"
  "crewai-agents|main|packages/crewai-agents"
  "autogen-workflows|main|packages/autogen-workflows"
  "quant-backtest|main|packages/quant-backtest"
  "risk-guardian|main|packages/risk-guardian"
  "market-data|main|packages/market-data"
  "pressure-engine|main|packages/pressure-engine"
  "decision-engine|main|packages/decision-engine"
  "alpha-factors|main|packages/alpha-factors"
  "vector-memory|main|packages/vector-memory"
  "web-terminal|main|packages/web-terminal"
  "execution-brokers|main|packages/execution-brokers"
  "prediction-markets|main|packages/prediction-markets"
  "docker-infra|main|infra"
  "api-server|main|packages/api-server"
  "shared-types|main|packages/shared-types"
)

for entry in "${MERGES[@]}"; do
  IFS='|' read -r remote branch prefix <<< "$entry"

  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "Merging: $remote ($branch) → $prefix"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  # Fetch the remote
  git fetch "$remote" "$branch"

  # Add as subtree
  git subtree add \
    --prefix="$prefix" \
    "$remote/$branch" \
    --squash \
    --message="merge($remote): subtree add $remote/$branch → $prefix"

  echo "✓ Merged: $remote → $prefix"
  echo ""
done

echo "All subtree merges complete."
```

### 2.4 Subtree Pull (Future Updates)

```bash
#!/bin/bash
# scripts/update_subtrees.sh
# Pull latest changes from each subtree remote

MERGES=(
  "hermes|main|hermes"
  "kronos|main|packages/kronos"
  "langgraph-trading|main|packages/langgraph-trading"
  # ... (same list as execute_merges.sh)
)

for entry in "${MERGES[@]}"; do
  IFS='|' read -r remote branch prefix <<< "$entry"
  echo "Updating: $remote → $prefix"
  git subtree pull \
    --prefix="$prefix" \
    "$remote" "$branch" \
    --squash
done
```

---

## 3. Dependency Conflict Resolution Strategy

### 3.1 Known Conflicts

| Package | Repo A Version | Repo B Version | Resolution |
|---|---|---|---|
| `pydantic` | 1.10.x (FinceptTerminal) | 2.10.x (QNA) | Upgrade all to 2.10+ (breaking but required) |
| `numpy` | 1.24.x (ai-trader) | 2.1.x (QNA) | Upgrade all to 2.1+ |
| `langchain` | 0.1.x (crewai-agents) | 0.3.x (langgraph-trading) | Upgrade all to 0.3+ |
| `ccxt` | 3.x (SolSniperX) | 4.4.x (QNA) | Upgrade all to 4.4+ |
| `fastapi` | 0.100.x (api-server) | 0.115.x (QNA) | Upgrade all to 0.115+ |
| `sqlalchemy` | 1.4.x (risk-guardian) | 2.0.x (QNA) | Upgrade all to 2.0+ |
| `pandas` | 1.5.x (alpha-factors) | 2.2.x (QNA) | Upgrade all to 2.2+ |
| `click` | 7.x (FinceptTerminal) | 8.1.x (QNA) | Upgrade all to 8.1+ |

### 3.2 Resolution Process

```
Step 1: AUDIT
  ├── Run `pipdeptree` on each repo to get full dependency tree
  ├── Run `pip-audit` for security vulnerabilities
  └── Identify minimum version requirements for each package

Step 2: UPGRADE
  ├── Update all repos to QNA's versions (the newest)
  ├── Fix breaking changes (Pydantic v1→v2, SQLAlchemy 1→2)
  └── Run test suites for each repo after upgrade

Step 3: CONSOLIDATE
  ├── Merge all pyproject.toml into single root pyproject.toml
  ├── Use optional dependency groups for package-specific needs
  └── Pin exact versions in poetry.lock

Step 4: VALIDATE
  ├── `poetry install` in clean environment
  ├── `poetry run pytest` across all test suites
  └── `poetry run mypy src/` for type checking
```

### 3.3 Pydantic v1 → v2 Migration

The most significant breaking change. Key patterns:

```python
# Pydantic v1 (OLD)
from pydantic import BaseModel, validator

class Config:
    env_prefix = "APP_"

@validator("field")
def check_field(cls, v):
    return v

# Pydantic v2 (NEW)
from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_")

    @field_validator("field")
    @classmethod
    def check_field(cls, v):
        return v
```

### 3.4 SQLAlchemy 1.x → 2.x Migration

```python
# SQLAlchemy 1.x (OLD)
from sqlalchemy.orm import Session
session = Session()
results = session.query(Model).filter(Model.field == value).all()

# SQLAlchemy 2.x (NEW)
from sqlalchemy import select
from sqlalchemy.orm import Session
session = Session()
results = session.execute(select(Model).where(Model.field == value)).scalars().all()
```

---

## 4. De-duplication Plan

### 4.1 Identified Duplications

| Component | Duplicated In | Action |
|---|---|---|
| Market data types | quant-nanggroe-ai, market-data-pipeline, shared-types | Consolidate into `shared-types` → import from single source |
| Risk validation logic | risk-guardian, quant-nanggroe-ai (TS), ai-trader | Keep Python `ConstitutionalRiskGuard` as canonical; remove TS risk logic |
| Technical indicators | quant-nanggroe-ai (MathEngine.ts), alpha-factors (Python) | Keep Python `TechnicalAnalysisTool` + `MathEngine`; remove TS MathEngine |
| OHLCV data models | market-data-pipeline, quant-backtest, execution-brokers | Consolidate into `shared-types` `CandleData` model |
| Logging setup | Every repo has its own `logging.basicConfig()` | Use `structlog` from `quant_nanggroe_ai/logging.py` everywhere |
| Configuration loading | Multiple `config.py` with overlapping settings | Single `Settings` class in `config.py` with sub-settings |
| LLM router | quant-nanggroe-ai (Gemini-only), ai-trader (OpenAI-only) | Consolidate into `LLMRouter` with multi-provider support |
| Exchange connectors | SolSniperX (Solana), execution-brokers (ccxt), ai-trader (ccxt) | Consolidate into `execution-brokers` with CCXT + Polymarket + Kronos |
| Error types | Each repo defines its own exceptions | Consolidate into `exceptions.py` |
| Docker configurations | docker-infra, quant-nanggroe-ai | Single `docker-compose.yml` at root |

### 4.2 De-duplication Execution Order

```
Phase 1: Type System Unification
  ├── Merge all type definitions into /packages/shared-types
  ├── Python: Pydantic models in types.py
  ├── TypeScript: Interfaces in types.ts
  └── All other packages import from shared-types

Phase 2: Engine Consolidation
  ├── Keep Python engines (pressure, decision, risk, market-state)
  ├── Remove TypeScript engine duplicates
  ├── Verify test parity between Python and TS implementations
  └── Update all imports

Phase 3: Infrastructure Unification
  ├── Single docker-compose.yml
  ├── Single Dockerfile with multi-stage build
  ├── Single pyproject.toml
  ├── Single package.json
  └── Remove all duplicate CI/CD configs

Phase 4: Code Cleanup
  ├── Remove deprecated packages (FinceptTerminal, bloomberg-tui, SolSniperX, ai-trader)
  ├── Add DEPRECATED.md in each deprecated package
  ├── Run ruff --fix across entire codebase
  └── Run mypy in strict mode
```

### 4.3 Target Directory Structure (Post-Merge)

```
quant-nanggroe-ai/
├── src/
│   └── quant_nanggroe_ai/
│       ├── __init__.py
│       ├── config.py              # Consolidated settings
│       ├── types.py               # Shared Pydantic models
│       ├── exceptions.py          # Unified exceptions
│       ├── logging.py             # Structured logging setup
│       ├── agents/
│       │   ├── graph.py           # LangGraph trading graph
│       │   ├── state.py           # AgentState schema
│       │   ├── nodes/             # Agent node implementations
│       │   ├── tools/             # MCP tool registry
│       │   └── council/           # Bull/bear debate, risk debate
│       ├── engine/
│       │   ├── market_state.py    # MarketStateEngine
│       │   ├── pressure.py        # PressureNormalizationEngine
│       │   ├── decision.py        # DecisionSynthesisEngine
│       │   ├── risk_guard.py      # ConstitutionalRiskGuard
│       │   ├── kill_switch.py     # Emergency kill switch
│       │   ├── audit.py           # Audit logging
│       │   ├── math_lib.py        # Deterministic math
│       │   ├── autoswitch.py      # Provider failover
│       │   └── strategy_lifecycle.py  # Darwinian evolution
│       ├── factors/
│       │   ├── alpha101.py        # WorldQuant Alpha101 factors
│       │   ├── technical.py       # Technical indicators
│       │   └── registry.py        # Factor registry
│       ├── risk/
│       │   ├── var.py             # Value at Risk
│       │   ├── cvar.py            # Conditional VaR
│       │   ├── drawdown.py        # Drawdown calculations
│       │   ├── position_sizing.py # Kelly + Risk Parity
│       │   └── portfolio_risk.py  # Portfolio-level risk
│       ├── execution/
│       │   ├── alpaca_broker.py   # US equity execution
│       │   ├── polymarket.py      # Prediction market execution
│       │   ├── jupiter.py         # Solana DEX execution
│       │   └── paper.py           # Paper trading
│       ├── memory/
│       │   ├── vector.py          # TF-IDF vector store
│       │   ├── research.py        # Research memory
│       │   └── conversation.py    # Conversation condenser
│       ├── backtest/
│       │   ├── engine.py          # Backtesting engine
│       │   ├── metrics.py         # Performance metrics
│       │   └── walk_forward.py    # Walk-forward validation
│       ├── api/
│       │   ├── app.py             # FastAPI application
│       │   ├── middleware.py      # Auth, CORS, rate limiting
│       │   ├── schemas.py         # API request/response schemas
│       │   └── routes/            # API route handlers
│       └── worker.py              # Background task worker
├── services/                       # TypeScript frontend services
├── components/                     # React UI components
├── packages/
│   ├── kronos/                    # C++ execution engine
│   ├── langgraph-trading/         # LangGraph trading graph
│   ├── crewai-agents/             # CrewAI workflows (research)
│   ├── autogen-workflows/         # AutoGen workflows (research)
│   ├── fincept-terminal/          # DEPRECATED
│   ├── bloomberg-tui/             # DEPRECATED
│   ├── sol-sniper-x/              # DEPRECATED
│   ├── ai-trader/                 # DEPRECATED
│   └── ...
├── infra/                         # Docker, CI/CD
├── tests/                         # Python test suite
├── docs/                          # Documentation
├── pyproject.toml                 # Python dependencies
├── package.json                   # Node.js dependencies
├── docker-compose.yml             # Full stack
├── Dockerfile                     # Multi-stage build
└── Makefile                       # Build automation
```

---

## 5. Merge Validation Checklist

### 5.1 Per-Repository Validation

For each repository being merged:

- [ ] `git subtree add` succeeds without conflicts
- [ ] All Python imports resolve correctly
- [ ] `poetry install` completes without errors
- [ ] `pytest` passes for the package's test suite
- [ ] `mypy src/` passes with no new errors
- [ ] `ruff check src/` passes with no new violations
- [ ] No duplicate type definitions with existing packages
- [ ] Docker build succeeds with new package included

### 5.2 Cross-Package Validation

After all merges:

- [ ] Full `pytest` suite passes (all packages)
- [ ] `mypy --strict src/` passes
- [ ] `ruff check .` passes
- [ ] `docker-compose build` succeeds
- [ ] `docker-compose up` starts all services
- [ ] API health endpoint returns 200
- [ ] WebSocket connection establishes
- [ ] Frontend builds with `npm run build`
- [ ] No circular import dependencies
- [ ] Total package count in poetry.lock is reasonable (< 300)

### 5.3 Rollback Plan

If a merge introduces unresolvable conflicts:

1. `git revert` the subtree merge commit
2. Fix conflicts in a separate branch
3. Re-run `git subtree add` with conflict resolution
4. Validate before merging to main

---

© 2025-2026 Quant Nanggroe AI | Merge Plan v15.3.0
