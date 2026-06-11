# Quant Nanggroe AI — Merge Plan

**Version 4.0.0 | Repository Consolidation Strategy**

> Per-repo analysis for 21 repositories with merge priority, strategy, what we keep, what we reject, and dependency resolution.

---

## Table of Contents

1. [Merge Priority Matrix](#1-merge-priority-matrix)
2. [Per-Repository Analysis](#2-per-repository-analysis)
3. [Dependency Conflict Resolution](#3-dependency-conflict-resolution)
4. [De-duplication Plan](#4-de-duplication-plan)
5. [Git Subtree Merge Procedures](#5-git-subtree-merge-procedures)
6. [Target Directory Structure](#6-target-directory-structure)
7. [Validation Checklist](#7-validation-checklist)

---

## 1. Merge Priority Matrix

| Priority | Repository | Reason | Merge Strategy |
|----------|-----------|--------|----------------|
| **P0** | quant-nanggroe-ai | Core monorepo base | Root |
| **P0** | langgraph-trading | Core trading graph | Direct integration → `agents/graph.py` |
| **P0** | risk-guardian | Constitutional risk engine | Direct integration → `engine/risk/` |
| **P0** | alpha-factors | 469 factor models | Direct integration → `engine/factors/` |
| **P0** | api-server | FastAPI backend | Direct integration → `api/` |
| **P1** | HermesQuantOS | Parent ecosystem | Extract backtest + risk → `engine/` |
| **P1** | market-data-pipeline | Market data ingestion | Extract → `exchange/` + `agents/tools/` |
| **P1** | execution-brokers | Exchange connectors | Extract → `exchange/` |
| **P1** | TradingAgents | Multi-debate agents | Extract council debate → `agents/council/` |
| **P1** | ai-hedge-fund | Risk + portfolio patterns | Extract risk → `engine/risk/` |
| **P2** | pressure-engine | Pressure normalization | Extract → `engine/pressure.py` |
| **P2** | decision-engine | Decision synthesis | Extract → `engine/decision.py` |
| **P2** | portfolio-optimizer | Portfolio optimization | Extract → `agents/portfolio/` |
| **P2** | Vibe-Trading | Sentiment + vibe factors | Extract → `engine/factors/academic.py` |
| **P2** | vector-memory | TF-IDF vector store | Extract → `memory/` |
| **P2** | shared-types | Type definitions | Merge → `agents/state.py` + TS interfaces |
| **P3** | SolSniperX | Solana sniper bot | Port SOR logic → `exchange/jupiter_broker.py` |
| **P3** | prediction-markets | Polymarket integration | Port → `exchange/polymarket_broker.py` |
| **P3** | Kronos | C++ execution engine | Build PyO3 bindings → `engine/execution/` |
| **P3** | dexter | Macro data scraping | Port → `agents/macro/tools.py` |
| **P3** | OpenAlice | Social listening | Port → `agents/researcher/tools.py` |
| **DEPRECATED** | FinceptTerminal | Legacy CLI | 🗑️ Freeze in `contrib/` |
| **DEPRECATED** | bloomberg-terminal | Legacy TUI | 🗑️ Freeze in `contrib/` |
| **DEPRECATED** | ai-trader | Legacy trading module | 🗑️ Extract useful patterns, freeze |
| **DEPRECATED** | crewai-agents | CrewAI workflows | 📋 Reference only |
| **DEPRECATED** | autogen-workflows | AutoGen workflows | 📋 Reference only |

---

## 2. Per-Repository Analysis

### 2.1 quant-nanggroe-ai (P0 — Root)

| Field | Detail |
|-------|--------|
| **Source** | Core monorepo |
| **Language** | Python 3.12 + TypeScript |
| **What We Keep** | Everything — this is the base |
| **What We Reject** | Legacy `vite.config.ts` key injection (fixed in v15.3.1) |
| **Merge Target** | `/` (root) |
| **Conflicts** | Import paths need normalization to `quant_nanggroe.xxx` |

### 2.2 langgraph-trading (P0 — Core Graph)

| Field | Detail |
|-------|--------|
| **Source** | github.com/mulkymalikuldhrs/langgraph-trading |
| **Language** | Python 3.12 |
| **What We Keep** | `TradingGraph` class, `AgentState` schema, conditional routing logic |
| **What We Reject** | Old `graph_v1.py` (superseded by current `graph.py`) |
| **Merge Target** | `quant_nanggroe/agents/graph.py`, `quant_nanggroe/agents/state.py` |
| **Conflicts** | `AgentState` may conflict with HermesQuantOS's state definition |
| **Resolution** | Current `AgentState(TypedDict)` is canonical; HermesQuantOS's `BaseModel` version is rejected |

### 2.3 risk-guardian (P0 — Risk Engine)

| Field | Detail |
|-------|--------|
| **Source** | github.com/mulkymalikuldhrs/risk-guardian |
| **Language** | Python 3.12 |
| **What We Keep** | `RiskManager`, `RiskCheckGate` (9-checkpoint), `KillSwitch`, `DrawdownMonitor`, `KellyCriterion`, `VaRCalculator`, `CorrelationMonitor`, `constants.py` |
| **What We Reject** | Old `config-based` risk limits (replaced by constitutional hardcoded limits) |
| **Merge Target** | `quant_nanggroe/engine/risk/` |
| **Conflicts** | `constants.py` values must match `agents/state.py` (same values, two files to avoid circular imports) |
| **Resolution** | `engine/risk/constants.py` is the single source of truth; `agents/state.py` mirrors it |

### 2.4 alpha-factors (P0 — Factor Engine)

| Field | Detail |
|-------|--------|
| **Source** | github.com/mulkymalikuldhrs/alpha-factors |
| **Language** | Python 3.12 |
| **What We Keep** | `FactorRegistry`, `FactorHandle`, `AlphaFactor` base class, all 7 zoo modules (alpha101, gtja191, barra, qlib158, technical, fundamental, academic) |
| **What We Reject** | Old `factor_list.py` (flat list, replaced by `FactorRegistry` with discovery) |
| **Merge Target** | `quant_nanggroe/engine/factors/` |
| **Conflicts** | TA-Lib C dependency in old `technical.py` |
| **Resolution** | Replaced with numpy-native implementations in current `technical.py` |

### 2.5 api-server (P0 — Backend API)

| Field | Detail |
|-------|--------|
| **Source** | github.com/mulkymalikuldhrs/api-server |
| **Language** | Python 3.12 |
| **What We Keep** | FastAPI app, all 6 route groups, WebSocket handler, lifespan management |
| **What We Reject** | Old Flask-based routes (replaced by FastAPI) |
| **Merge Target** | `quant_nanggroe/api/` |
| **Conflicts** | None — FastAPI is the standard |

### 2.6 HermesQuantOS (P1 — Parent Ecosystem)

| Field | Detail |
|-------|--------|
| **Source** | github.com/mulkymalikuldhrs/HermesQuantOS |
| **Language** | Python 3.11 → 3.12 upgrade needed |
| **What We Keep** | `RiskOfficerTool` (→ merged into `RiskCheckGate`), `BacktestEngine` patterns, `DrawdownMonitor`, stress test scenarios |
| **What We Reject** | `StateModel` (Pydantic v1 BaseModel — replaced by TypedDict `AgentState`), old `AutoSwitch` (rewritten) |
| **Merge Target** | `quant_nanggroe/engine/risk/`, `quant_nanggroe/engine/backtest/` |
| **Conflicts** | Pydantic v1 → v2 migration needed; SQLAlchemy 1.x → 2.x needed |

### 2.7 market-data-pipeline (P1 — Market Data)

| Field | Detail |
|-------|--------|
| **Source** | github.com/mulkymalikuldhrs/market-data-pipeline |
| **Language** | Python 3.11 |
| **What We Keep** | Provider adapters (Binance, Polygon, AlphaVantage, Finnhub), AutoSwitch failover logic, data normalization |
| **What We Reject** | Old `InfluxDB` storage adapter (replaced by TimescaleDB) |
| **Merge Target** | `quant_nanggroe/agents/tools/market_data.py`, `quant_nanggroe/exchange/` |
| **Conflicts** | Old `ccxt` 3.x → 4.4.x upgrade needed |

### 2.8 execution-brokers (P1 — Exchange Layer)

| Field | Detail |
|-------|--------|
| **Source** | github.com/mulkymalikuldhrs/execution-brokers |
| **Language** | Python 3.12 |
| **What We Keep** | `CCXTBroker`, `PaperExchangeBroker`, `ExchangeFactory`, `ExchangeCapabilities`, market type routing |
| **What We Reject** | Old `BinanceDirectBroker` (raw API, replaced by CCXT) |
| **Merge Target** | `quant_nanggroe/exchange/` |
| **Conflicts** | Old `ccxt` version → upgrade to latest |

### 2.9 TradingAgents (P1 — Council Debate)

| Field | Detail |
|-------|--------|
| **Source** | github.com/TauricResearch/TradingAgents |
| **Language** | Python 3.12 |
| **What We Keep** | Multi-debate architecture: Bull/Bear researcher debate, Conservative/Neutral/Aggressive risk debate, Judge decision templates, Weighted voting mechanism |
| **What We Reject** | Standalone runner (integrated into LangGraph as `council_debate` node), old `AgentState` definition |
| **Merge Target** | `quant_nanggroe/agents/council/debate.py`, `quant_nanggroe/agents/council/voting.py` |
| **Conflicts** | State format differences — adapted to our `AgentState` TypedDict |

### 2.10 ai-hedge-fund (P1 — Risk + Portfolio)

| Field | Detail |
|-------|--------|
| **Source** | github.com/virattt/ai-hedge-fund |
| **Language** | Python 3.11 |
| **What We Keep** | Stress testing framework (6 scenarios), Optimal-F position sizing, VaR-based position sizing |
| **What We Reject** | Standalone agent architecture (we integrate into LangGraph) |
| **Merge Target** | `quant_nanggroe/engine/risk/manager.py` (stress_test, optimal_f_position_size methods) |
| **Conflicts** | Python 3.11 → 3.12 upgrade |

### 2.11 pressure-engine (P2 — Pressure Normalization)

| Field | Detail |
|-------|--------|
| **Source** | Internal |
| **What We Keep** | Weighted sensor aggregation (4-sensor: QuantScanner 25%, SMCAgent 30%, NewsSentinel 20%, FlowAgent 25%) |
| **What We Reject** | Old 6-sensor model (consolidated to 4) |
| **Merge Target** | `quant_nanggroe/engine/pressure.py` |

### 2.12 decision-engine (P2 — Decision Synthesis)

| Field | Detail |
|-------|--------|
| **Source** | Internal |
| **What We Keep** | 7-rule decision table (DT001–DT007), ATR geometry calculation, entry parameter computation |
| **What We Reject** | Old LLM-based decision (replaced by deterministic table + LLM for nuance) |
| **Merge Target** | `quant_nanggroe/engine/decision.py` |

### 2.13 Vibe-Trading (P2 — Sentiment Factors)

| Field | Detail |
|-------|--------|
| **Source** | Internal |
| **What We Keep** | `__alpha_meta__` + `compute(panel)` function-based factor pattern, sentiment analysis factors, vibe-based indicators |
| **What We Reject** | TA-Lib C dependency (replaced with numpy-native) |
| **Merge Target** | `quant_nanggroe/engine/factors/academic.py` |
| **Conflicts** | TA-Lib dependency → numpy replacement |

### 2.14 SolSniperX (P3 — Solana)

| Field | Detail |
|-------|--------|
| **Source** | github.com/mulkymalikuldhrs/SolSniperX |
| **Language** | Rust |
| **What We Keep** | Smart order routing logic, MEV-aware transaction construction |
| **What We Reject** | Rust runtime (ported to Python), Solana-specific sniper features (out of scope) |
| **Merge Target** | `quant_nanggroe/exchange/jupiter_broker.py` (Python port of routing logic) |

### 2.15 Kronos (P3 — C++ Execution)

| Field | Detail |
|-------|--------|
| **Source** | github.com/mulkymalikuldhrs/Kronos |
| **Language** | C++ with PyO3 |
| **What We Keep** | Low-latency order book management, smart order routing, PyO3 Python bindings |
| **What We Reject** | Standalone binary (integrated as Python extension module) |
| **Merge Target** | `quant_nanggroe/engine/execution/` |
| **Conflicts** | C++ compilation complexity; fallback to ccxt when Kronos unavailable |

### 2.16 prediction-markets (P3 — Polymarket)

| Field | Detail |
|-------|--------|
| **Source** | Internal |
| **Language** | Python + Rust |
| **What We Keep** | CLOB API integration, EIP-712 order signing, market discovery (Gamma API) |
| **What We Reject** | Rust CLI (ported to Python broker) |
| **Merge Target** | `quant_nanggroe/exchange/polymarket_broker.py` |

---

## 3. Dependency Conflict Resolution

### 3.1 Known Conflicts

| Package | Repo A Version | Repo B Version | Resolution |
|---------|---------------|---------------|------------|
| `pydantic` | 1.10.x (HermesQuantOS) | 2.10.x (QNA) | Upgrade all to 2.10+ |
| `numpy` | 1.24.x (ai-trader) | 2.1.x (QNA) | Upgrade all to 2.1+ |
| `langchain` | 0.1.x (TradingAgents) | 0.3.x (QNA) | Upgrade all to 0.3+ |
| `ccxt` | 3.x (SolSniperX) | 4.4.x (QNA) | Upgrade all to 4.4+ |
| `fastapi` | 0.100.x (api-server) | 0.115.x (QNA) | Upgrade all to 0.115+ |
| `sqlalchemy` | 1.4.x (HermesQuantOS) | 2.0.x (QNA) | Upgrade all to 2.0+ |
| `pandas` | 1.5.x (alpha-factors) | 2.2.x (QNA) | Upgrade all to 2.2+ |
| `click` | 7.x (FinceptTerminal) | 8.1.x (QNA) | Upgrade all to 8.1+ |

### 3.2 Pydantic v1 → v2 Migration Patterns

```python
# OLD (v1)                          →  NEW (v2)
from pydantic import BaseModel      →  from pydantic import BaseModel
from pydantic import validator      →  from pydantic import field_validator
class Config:                       →  model_config = ConfigDict(...)
@validator("field")                 →  @field_validator("field")
def check(cls, v):                  →  @classmethod
    return v                        →  def check(cls, v): return v
from pydantic import BaseSettings   →  from pydantic_settings import BaseSettings
```

### 3.3 SQLAlchemy 1.x → 2.x Migration

```python
# OLD (1.x)                                  →  NEW (2.x)
session.query(Model).filter(                  →  session.execute(
    Model.field == value                      →      select(Model).where(
).all()                                       →          Model.field == value
                                              →      )
                                              →  ).scalars().all()
```

---

## 4. De-duplication Plan

| Duplicate | Repos | Keep | Reject |
|-----------|-------|------|--------|
| Market data fetching | AI-Trader, HermesQuantOS, market-data | `MarketDataTool` (current) | Per-repo implementations |
| Sentiment analysis | AI-Trader, OpenAlice | `SentimentTool` (current) | Duplicate implementations |
| Risk checks | HermesQuantOS, ai-hedge-fund | `RiskCheckGate` (9-checkpoint) | Old `RiskOfficerTool` |
| Exchange connectors | SolSniperX, execution-brokers, AI-Trader | `CCXTBroker` + `ExchangeFactory` | Per-repo ccxt wrappers |
| Config loading | All repos | Centralized `Settings` with sub-settings | Per-repo `config.py` |
| Logging setup | All repos | `structlog` from shared config | Per-repo `logging.basicConfig()` |
| Type definitions | shared-types, state.py | `AgentState` TypedDict + Pydantic models | Duplicate type classes |
| LLM router | AI-Trader (OpenAI-only), QNA (multi-provider) | `create_llm()` with 5 providers | Single-provider routers |
| Error types | Every repo | Unified `exceptions.py` | Per-repo exception classes |
| Docker configs | docker-infra, QNA | Single `docker-compose.yml` | Duplicate Dockerfiles |

---

## 5. Git Subtree Merge Procedures

### 5.1 Remote Setup

```bash
#!/bin/bash
REMOTES=(
  "hermes|https://github.com/mulkymalikuldhrs/HermesQuantOS.git"
  "langgraph-trading|https://github.com/mulkymalikuldhrs/langgraph-trading.git"
  "risk-guardian|https://github.com/mulkymalikuldhrs/risk-guardian.git"
  "alpha-factors|https://github.com/mulkymalikuldhrs/alpha-factors.git"
  "api-server|https://github.com/mulkymalikuldhrs/api-server.git"
  "market-data|https://github.com/mulkymalikuldhrs/market-data-pipeline.git"
  "execution-brokers|https://github.com/mulkymalikuldhrs/execution-brokers.git"
  "trading-agents|https://github.com/TauricResearch/TradingAgents.git"
  "ai-hedge-fund|https://github.com/virattt/ai-hedge-fund.git"
  "sol-sniper-x|https://github.com/mulkymalikuldhrs/SolSniperX.git"
  "kronos|https://github.com/mulkymalikuldhrs/Kronos.git"
  "prediction-markets|https://github.com/mulkymalikuldhrs/prediction-markets.git"
)

for entry in "${REMOTES[@]}"; do
  IFS='|' read -r name url <<< "$entry"
  git remote add "$name" "$url" 2>/dev/null || git remote set-url "$name" "$url"
done
```

### 5.2 Merge Execution Order

```bash
# P0 merges first (core dependencies)
git subtree add --prefix=contrib/langgraph-trading langgraph-trading main --squash
git subtree add --prefix=contrib/risk-guardian risk-guardian main --squash
git subtree add --prefix=contrib/alpha-factors alpha-factors main --squash
git subtree add --prefix=contrib/api-server api-server main --squash

# P1 merges (feature integration)
git subtree add --prefix=contrib/hermes hermes main --squash
git subtree add --prefix=contrib/market-data market-data main --squash
git subtree add --prefix=contrib/execution-brokers execution-brokers main --squash
git subtree add --prefix=contrib/trading-agents trading-agents main --squash
git subtree add --prefix=contrib/ai-hedge-fund ai-hedge-fund main --squash

# P2 merges (engine components)
git subtree add --prefix=contrib/pressure-engine pressure-engine main --squash
git subtree add --prefix=contrib/decision-engine decision-engine main --squash
git subtree add --prefix=contrib/vibe-trading vibe-trading main --squash
git subtree add --prefix=contrib/vector-memory vector-memory main --squash
git subtree add --prefix=contrib/shared-types shared-types main --squash

# P3 merges (optional/integration)
git subtree add --prefix=contrib/sol-sniper-x sol-sniper-x main --squash
git subtree add --prefix=contrib/kronos kronos main --squash
git subtree add --prefix=contrib/prediction-markets prediction-markets main --squash
git subtree add --prefix=contrib/dexter dexter main --squash
git subtree add --prefix=contrib/open-alice open-alice main --squash

# Deprecated (frozen, reference only)
git subtree add --prefix=contrib/fincept-terminal fincept-terminal main --squash
git subtree add --prefix=contrib/crewai-agents crewai-agents main --squash
git subtree add --prefix=contrib/autogen-workflows autogen-workflows main --squash
```

---

## 6. Target Directory Structure

```
quant_nanggroe/
├── agents/                          # 11-agent council + LangGraph
│   ├── graph.py                     # TradingGraph (LangGraph StateGraph)
│   ├── state.py                     # AgentState + all Pydantic models
│   ├── base.py                      # BaseAgent ABC + create_llm()
│   ├── registry.py                  # AgentRegistry + AgentFactory
│   ├── council/
│   │   ├── debate.py                # CouncilDebate (bull/bear + risk)
│   │   └── voting.py                # CouncilVoting (weighted votes)
│   ├── researcher/                  # Researcher agent
│   ├── macro/                       # Macro agent
│   ├── crypto/                      # Crypto agent
│   ├── forex/                       # Forex agent
│   ├── strategist/                  # Strategist agent
│   ├── risk/                        # Risk agent
│   ├── portfolio/                   # Portfolio agent
│   ├── trader/                      # Trader agent
│   ├── execution/                   # Execution agent
│   └── tools/                       # 13 shared tools
├── engine/
│   ├── factors/                     # 469 factors across 7 zoos
│   │   ├── base.py                  # AlphaFactor + FactorMeta
│   │   ├── registry.py              # FactorRegistry + FactorHandle
│   │   ├── alpha101.py              # 101 factors
│   │   ├── gtja191.py               # 191 factors
│   │   ├── barra.py                 # 38 factors
│   │   ├── qlib158.py               # 158 factors
│   │   ├── technical.py             # 25+ factors
│   │   ├── fundamental.py           # 20+ factors
│   │   └── academic.py              # 40+ factors
│   ├── risk/                        # Constitutional risk engine
│   │   ├── constants.py             # Single source of truth (12 limits)
│   │   ├── manager.py               # RiskManager
│   │   ├── checks.py                # RiskCheckGate (9 checkpoints)
│   │   ├── kill_switch.py           # KillSwitch
│   │   ├── drawdown.py              # DrawdownMonitor
│   │   ├── kelly.py                 # KellyCriterion
│   │   ├── var.py                   # VaRCalculator
│   │   ├── cvar.py                  # CVaR
│   │   ├── correlation.py           # CorrelationMonitor
│   │   └── portfolio_risk.py        # PortfolioRisk
│   ├── execution/                   # Kronos C++ (future)
│   ├── pressure.py                  # Pressure normalization
│   ├── decision.py                  # Decision synthesis
│   └── backtest/                    # 10 backtest engine implementations
├── exchange/                        # Exchange layer
│   ├── base.py                      # ExchangeInterface + ExchangeConfig
│   ├── factory.py                   # ExchangeFactory + ExchangeCapabilities
│   ├── ccxt_broker.py               # CCXTBroker (8 exchanges)
│   ├── paper_broker.py              # PaperExchangeBroker
│   ├── alpaca_broker.py             # US equity execution
│   ├── polymarket_broker.py         # Prediction markets
│   └── jupiter_broker.py            # Solana DEX
├── api/                             # FastAPI backend
│   ├── app.py                       # Application + lifespan
│   ├── routes/                      # 6 route groups
│   └── middleware.py                # Auth, CORS, rate limiting
├── memory/                          # Three-layer memory
│   ├── vector.py                    # TF-IDF vector store
│   ├── episodic.py                  # Trade episode recall
│   ├── pattern.py                   # Pattern matching
│   └── knowledge_graph.py           # Entity relationships
├── config.py                        # Pydantic Settings hierarchy
└── exceptions.py                    # Unified exceptions
```

---

## 7. Validation Checklist

### Per-Repository Validation

- [ ] `git subtree add` succeeds without conflicts
- [ ] All Python imports resolve: `from quant_nanggroe.xxx import ...`
- [ ] `poetry install` completes without errors
- [ ] `pytest` passes for the package's test suite
- [ ] `mypy src/` passes with no new errors
- [ ] `ruff check src/` passes with no new violations
- [ ] No duplicate type definitions with existing packages
- [ ] Docker build succeeds with new package included

### Cross-Package Validation

- [ ] Full `pytest` suite passes (all packages)
- [ ] `mypy --strict src/` passes
- [ ] `ruff check .` passes
- [ ] `docker-compose build` succeeds
- [ ] API health endpoint returns 200
- [ ] WebSocket connection establishes
- [ ] Frontend builds with `npm run build`
- [ ] No circular import dependencies (verified with `pydeps`)
- [ ] Total package count in poetry.lock is reasonable (< 300)

---

*© 2025-2026 Quant Nanggroe AI | Merge Plan v4.0.0*
