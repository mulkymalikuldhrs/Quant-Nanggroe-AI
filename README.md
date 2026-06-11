<!-- 🦅 QUANT NANGGROE AI — Professional README -->
<!-- Language: English -->

<a href="https://github.com/mulkymalikuldhrs/Quant-Nanggroe-AI">
  <img align="center" src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&weight=700&size=36&duration=3000&pause=1500&color=00D4AA&center=true&vCenter=true&multiline=true&repeat=true&width=800&height=120&lines=QUANT+NANGGROE+AI;Multi-Agent+Decision+Intelligence+OS" alt="Typing SVG" />
</a>

<div align="center">

[![Version](https://img.shields.io/badge/Version-2.0.0-gold?style=for-the-badge&logo=semver&logoColor=white)](https://github.com/mulkymalikuldhrs/Quant-Nanggroe-AI)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.8-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge&logo=open-source-initiative&logoColor=white)](./LICENSE)

</div>

<div align="center">

**Language / Bahasa / 语言:**
[![English](https://img.shields.io/badge/EN-English-blue?style=flat-square)](./README.md)
[![Bahasa Indonesia](https://img.shields.io/badge/ID-Bahasa_Indonesia-red?style=flat-square)](./README_id.md)
[![中文](https://img.shields.io/badge/CN-中文-yellow?style=flat-square)](./README_zh.md)

</div>

---

## 🏛️ Overview

**Quant Nanggroe AI** adalah **Multi-Agent Decision Intelligence Operating System** yang dirancang untuk riset kuantitatif dan trading sistematis di pasar keuangan. Dibangun di atas prinsip **Deterministic Decision Intelligence**, platform ini menolak narasi AI subjektif dan bias psikologis, dan menggantikannya dengan penalaran matematis terbatas pada data numerik mentah. Sistem memperlakukan Large Language Model bukan sebagai penasihat, tetapi sebagai **Logical Reasoning Engines** — masing-masing beroperasi di bawah kontrak ketat yang melarang opini subjektif, mewajibkan grounding data, dan mengharuskan output berbasis tekanan numerik.

Platform ini mengkonsolidasikan kode dari **25 repositori** ke dalam satu monorepo terpadu, menghasilkan sistem trading kuantitatif komprehensif dengan **9 agent nodes**, **452 alpha factors**, **9 backtest engines**, **5 execution brokers**, **NautilusTrader integration**, dan **4-layer agent stack**. Semua branch implementasi dari C1 repos telah di-merge, dan package `quant_nanggroe/` (154 files) telah dikonsolidasikan ke dalam `src/quant_nanggroe_ai/`.

> 🔗 **Part of the [HermesQuantOS](https://github.com/mulkymalikuldhrs/HermesQuantOS) Unified Project** — A full-stack quantitative intelligence ecosystem.

---

## ⚡ Key Features

### 🧠 9-Agent Council dengan LangGraph Graph
Sistem mengoordinasikan **9 node agent** melalui LangGraph StateGraph:
- **Researcher** — OHLCV + sentimen + konteks makro
- **Analyst** — Analisis teknikal + deteksi regime
- **Strategist** — Normalisasi tekanan + sintesis keputusan
- **Risk Manager** — Sistem VETO 9-checkpoint (NON-NEGOTIABLE)
- **Trader** — Routing eksekusi order
- **Portfolio Manager** — Gerbang persetujuan final
- **Macro** — Analisis ekonomi makro
- **Forex** — Analisis pasar FX
- **Crypto** — Analisis pasar crypto

Dua council debates (Bull/Bear, Risk Debate) menyediakan perspektif adversarial.

### 🔢 452 Alpha Factors
| Kategori | Jumlah | Sumber |
|----------|--------|--------|
| Alpha101 | 101 | WorldQuant Alpha101 |
| Qlib158 | 154 | Microsoft Qlib |
| GTJA191 | 191 | Guotai Junan 191 |
| Academic (Fama-French 5-Factor/Carhart) | 7 | Fama-French + Carhart |

### 📊 9 Backtest Engines + NautilusTrader
| Engine | Pasar | Fitur |
|--------|-------|-------|
| ChinaAEngine | A-share | T+1, no short, price limits |
| GlobalEquityEngine | US/HK | Standard equity rules |
| CryptoEngine | Crypto | Funding fees, liquidation, 24/7 |
| ForexEngine | FX | Spread, swap, high leverage |
| ChinaFuturesEngine | CN Futures | CFFEX/SHFE/DCE/ZCE/INE |
| GlobalFuturesEngine | Global Futures | CME/ICE/Eurex |
| CompositeEngine | Cross-market | Shared capital pool |
| OptionsPortfolio | Options | Black-Scholes, IV smile |
| NautilusTrader | Universal | Institutional-grade adapter |

Plus: 4 Portfolio Optimizers (Mean-Variance, Risk Parity, Max Diversification, Equal Volatility) dan 8 Data Loaders (yfinance, CCXT, OKX, Futu, Tushare, AKShare, dll).

### 🔌 5 Execution Brokers
| Broker | Pasar | Fitur |
|--------|-------|-------|
| Paper | Semua | In-memory order book, SL/TP |
| Alpaca | US Equities | REST API, rate limiting, retry |
| Jupiter | Solana DEX | V6 swap, signing, JITO tips |
| Polymarket | Prediction Markets | Gamma + CLOB + Data API |
| Kalshi | Event Contracts | RSA-PSS auth, full order lifecycle |

### 🛡️ Risk Guardian Constitution
Risk management hard-coded dan independen dari logika AI:
- Maximum daily drawdown: 4% dengan automatic kill-switch
- Maximum position correlation: 0.70
- Maximum exposure per asset: 10% (configurable)
- Structural invalidation-based stop losses
- Minimum risk-reward ratio: 1:1.5

### 🧬 4-Layer Agent Stack
| Layer | Framework | Peran |
|-------|-----------|-------|
| Orchestration | LangGraph | State graph, conditional routing, council debates |
| Team Coordination | CrewAI | Multi-agent collaboration, task delegation |
| Validation | PydanticAI | Schema validation, structured output |
| Optimization | DSPy | Prompt optimization, performance tuning |

### 🔄 Protocols
- **MCP (Model Context Protocol)** — Standar komunikasi agent-ke-tools
- **A2A (Agent-to-Agent)** — Standar komunikasi antar-agent

### 📚 Integrasi Lainnya
- **WhatsApp Bot** — Notifikasi dan kontrol trading via WhatsApp
- **Trading Plan Tool** — Journal, CFTC data, trade validation, emotional lockout
- **Auth System** — JWT + RBAC (dari ai-manus merge)
- **File Operations** — Local + MongoDB GridFS storage
- **Solana Scanner** — Mempool monitoring, RugCheck, auto-sniper

---

## 🏗️ Architecture

Quant Nanggroe AI menggunakan arsitektur **multi-layer** dengan strict separation of concerns:

```
┌──────────────────────────────────────────────────────────┐
│  Frontend: React 19 + TypeScript (Desktop-OS UI)        │
│  25 components | 33 services | OmniBar | Trading Terminal│
├──────────────────────────────────────────────────────────┤
│  API Layer: FastAPI + WebSocket                          │
│  6 routers | JWT Auth | CORS | Health Check              │
├──────────────────────────────────────────────────────────┤
│  4-Layer Agent Stack                                     │
│  LangGraph → CrewAI → PydanticAI → DSPy                  │
│  9 Nodes | 7 Tools | 2 Council Debates | MCP + A2A       │
├──────────────────────────────────────────────────────────┤
│  Engine Layer (Deterministic — No AI)                     │
│  Risk Guard | Decision | Pressure | Market State          │
│  Kill Switch | Math Lib | Strategy Lifecycle              │
├──────────────────────────────────────────────────────────┤
│  Execution Layer                                         │
│  Paper | Alpaca | Jupiter | Polymarket | Kalshi          │
├──────────────────────────────────────────────────────────┤
│  Data & Storage Layer                                    │
│  PostgreSQL | QuestDB | Redis | SQLAlchemy 2.0 | Alembic  │
├──────────────────────────────────────────────────────────┤
│  Factor Library                                          │
│  452 factors (alpha101 + qlib158 + gtja191 + academic) | 9 backtest engines | 8 data loaders      │
└──────────────────────────────────────────────────────────┘
```

> Lihat [ARCHITECTURE.md](./ARCHITECTURE.md) untuk detail lengkap.

---

## 🚀 Quick Start

### Prerequisites

| Stack | Requirement |
|---|---|
| **Python Backend** | Python >= 3.12, [Poetry](https://python-poetry.org/) >= 1.8 |
| **Node.js Frontend** | Node.js >= 18.0.0, npm >= 9.0.0 |
| **External** | PostgreSQL 16+, Redis 7+, QuestDB (optional) |

### 1. Clone the Repository

```bash
git clone https://github.com/mulkymalikuldhrs/Quant-Nanggroe-AI.git
cd Quant-Nanggroe-AI
git checkout Julecl1
```

### 2. Python Backend Setup

```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Copy environment template
cp .env.example .env
# Edit .env with your API keys and database URLs

# Run database migrations
poetry run alembic upgrade head

# Start the FastAPI server
poetry run uvicorn quant_nanggroe_ai.main:app --reload --port 8000
```

### 3. Node.js Frontend Setup

```bash
# Install Node.js dependencies
npm install

# Start the development server
npm run dev
```

### 4. Docker Setup (Recommended)

```bash
# Start all services (API, Worker, Postgres, Redis, QuestDB)
docker-compose up -d

# Run migrations against the Docker database
docker-compose exec api poetry run alembic upgrade head
```

### 5. Configuration

Set environment variables in `.env`:

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `REDIS_URL` | Yes | Redis connection string |
| `ALPACA_API_KEY` | No | Alpaca broker API key |
| `ALPACA_SECRET_KEY` | No | Alpaca broker secret |
| `SOLANA_PRIVATE_KEY` | No | Solana wallet private key (Jupiter) |
| `POLYMARKET_API_KEY` | No | Polymarket CLOB API key |
| `KALSHI_API_KEY` | No | Kalshi API key |
| `KALSHI_PRIVATE_KEY` | No | Kalshi RSA private key path |

---

## 📁 Project Structure

```
Quant-Nanggroe-AI/
├── src/quant_nanggroe_ai/           # Python backend (27+ packages)
│   ├── agents/                      # 9-node LangGraph agent system
│   │   ├── nodes/                   # researcher, analyst, strategist, risk_manager, trader, portfolio, macro, forex, crypto, execution, prediction_market
│   │   ├── tools/                   # market_data, technical, sentiment, execution, backtest, trading_plan, file_ops, financial_data, portfolio_simulator, query_router, token_reducer
│   │   ├── council/                 # bull_bear, risk_debate, trading_council
│   │   ├── skills/                  # market_research, decision_tracker, stock_analysis, finance_skills
│   │   ├── agentpress/              # AgentPress framework (tool_registry, mcp_client, context_manager, sandbox)
│   │   ├── memory/                  # Agent memory (extraction, memory_store)
│   │   ├── graph.py                 # LangGraph StateGraph orchestration
│   │   ├── mcp_protocol.py          # Model Context Protocol
│   │   ├── a2a_protocol.py          # Agent-to-Agent Protocol
│   │   ├── dspy_optimizer.py        # DSPy prompt optimization
│   │   ├── pydantic_validator.py    # PydanticAI validation
│   │   ├── scheduler.py             # Agent scheduling
│   │   ├── sandbox.py               # Agent sandboxing
│   │   └── failsafe.py              # Agent failover
│   ├── api/                         # FastAPI server
│   │   ├── routes/                  # agents, backtest, market, portfolio, trading, auth, users, ws
│   │   ├── auth.py                  # JWT + RBAC authentication
│   │   ├── middleware.py             # API middleware
│   │   ├── client.py                # TradingPlan API client
│   │   ├── schemas/                 # Pydantic request/response models (market, user)
│   │   └── user_service.py          # User management service
│   ├── backtest/                    # 9 backtest engines
│   │   ├── engines/                 # china_a, global_equity, crypto, forex, china_futures, global_futures, composite, options_portfolio
│   │   ├── loaders/                 # yfinance, ccxt, okx, futu, tushare, akshare
│   │   ├── optimizers/              # mean_variance, risk_parity, max_diversification, equal_volatility
│   │   ├── benchmark.py             # Benchmark engine
│   │   ├── walk_forward.py          # Walk-forward optimization
│   │   └── validation.py            # Result validation
│   ├── data/                        # Database + Cache layer
│   │   ├── database.py              # SQLAlchemy 2.0 async
│   │   ├── cache.py                 # Redis cache
│   │   ├── models.py                # 7 ORM models
│   │   └── worker.py                # 5-async-loop trading worker
│   ├── engine/                      # Deterministic engine (NO AI)
│   │   ├── risk_guard.py            # 9-checkpoint constitutional guard
│   │   ├── decision.py              # Decision synthesis engine
│   │   ├── pressure.py              # Pressure normalization
│   │   ├── market_state.py          # Regime detection
│   │   ├── kill_switch.py           # Emergency halt
│   │   ├── math_lib.py              # Pure math indicators
│   │   ├── nautilus_adapter.py      # NautilusTrader adapter
│   │   ├── strategy_lifecycle.py    # Darwinian strategy evolution
│   │   ├── event_bus.py             # Event-driven message bus
│   │   ├── audit.py                 # Audit trail logging
│   │   ├── simulation.py            # Monte Carlo simulation
│   │   ├── regime.py                # Advanced regime detection
│   │   ├── models.py                # Shared engine models
│   │   ├── autoswitch.py            # LLM/data provider failover
│   │   ├── risk/                    # Risk submodule
│   │   │   ├── constants.py         # Constitutional rules (NON-NEGOTIABLE)
│   │   │   ├── checks.py            # Risk checkpoint implementations
│   │   │   ├── manager.py           # Risk manager coordination
│   │   │   ├── position_sizing.py   # Position sizing algorithms
│   │   │   ├── kelly.py             # Kelly criterion
│   │   │   ├── var.py               # Value at Risk
│   │   │   ├── drawdown.py          # Drawdown calculations
│   │   │   ├── correlation.py       # Correlation monitoring
│   │   │   ├── risk_parity.py       # Risk parity allocation
│   │   │   ├── emotional_lockout.py # Emotional trading lockout
│   │   │   └── kill_switch.py       # Emergency kill switch
│   │   └── strategy/                # Strategy submodule
│   │       ├── schema.py            # Strategy schema definitions
│   │       ├── loader.py            # Strategy loading
│   │       ├── parser.py            # Strategy parsing
│   │       └── backtest_adapter.py  # Strategy backtest adapter
│   ├── exchange/                    # Exchange abstraction layer
│   │   ├── base.py                  # Base exchange interface
│   │   ├── factory.py               # Exchange factory pattern
│   │   ├── manager.py               # Exchange manager
│   │   ├── guards.py                # Exchange guard rails
│   │   ├── order_types.py           # Order type definitions
│   │   ├── paper_broker.py          # Paper trading broker
│   │   ├── alpaca_broker.py         # Alpaca (US Equities)
│   │   ├── ccxt_broker.py           # CCXT (100+ crypto exchanges)
│   │   └── solana/                  # Solana exchange submodule
│   │       ├── jupiter.py           # Jupiter (Solana DEX)
│   │       ├── rugcheck.py          # RugCheck integration
│   │       ├── mempool.py           # Mempool monitoring
│   │       ├── wallet.py            # Solana wallet
│   │       └── broker.py            # Solana broker
│   ├── execution/                   # 5 execution brokers (legacy)
│   │   ├── paper.py                 # Paper trading
│   │   ├── alpaca_broker.py         # Alpaca (US Equities)
│   │   ├── jupiter.py               # Jupiter (Solana DEX)
│   │   ├── polymarket.py            # Polymarket (Prediction Markets)
│   │   └── kalshi.py                # Kalshi (Event Contracts)
│   ├── factors/                     # 452 alpha factors
│   │   ├── zoo/alpha101/            # 101 WorldQuant factors
│   │   ├── zoo/qlib158/             # 154 Microsoft Qlib factors
│   │   ├── zoo/academic/            # 7 Fama-French 5-Factor + Carhart
│   │   ├── registry.py              # Factor registry
│   │   ├── fama_french.py           # Fama-French 5-factor model
│   │   └── factor_analysis_core.py  # IC/IR analysis
│   ├── hedge_fund/                  # AI Hedge Fund subsystem
│   │   ├── agents/                  # Buffett, Ackman, Wood, Lynch, Munger, Graham, Fisher, Burry, etc.
│   │   ├── tools/                   # Multi-asset API, data providers
│   │   ├── options/                 # Options pricing
│   │   ├── risk/                    # Kelly, risk parity, VaR
│   │   ├── strategies/              # Quantitative, Wyckoff, legendary investors
│   │   ├── backtesting/             # Strategy backtesting
│   │   ├── integrations/            # fincept_terminal (50+ wrappers)
│   │   └── llm/                     # LLM routing and models
│   ├── integrations/                # External integrations
│   │   └── whatsapp_bot.py          # WhatsApp trading bot
│   ├── mcp/                         # Model Context Protocol
│   │   ├── client.py                # MCP client implementation
│   │   ├── server.py                # MCP server implementation
│   │   ├── protocol.py              # MCP protocol definitions
│   │   └── tools.py                 # MCP tool registry
│   ├── memory/                      # Knowledge & memory system
│   │   ├── vector.py                # TF-IDF vector search
│   │   ├── conversation.py          # Chat history
│   │   ├── research.py              # Research notes
│   │   ├── knowledge.py             # Knowledge base
│   │   ├── knowledge_graph.py       # Knowledge graph
│   │   ├── journal.py               # Trading journal
│   │   ├── session.py               # Session memory
│   │   ├── compression.py           # Memory compression (TokenJuice-style)
│   │   └── paging.py                # Memory paging/overflow
│   ├── ml_models/                   # ML models
│   │   ├── kronos/                  # BSQuantizer financial model
│   │   └── kronos_finetune/         # Fine-tuning pipeline
│   ├── multicolony/                 # AI MultiColony Ecosystem (C2)
│   │   ├── colony/                  # Colony lifecycle, config, routing
│   │   ├── runtime/                 # Agent pool, health monitoring
│   │   ├── skills/                  # Skill registry, dynamic loading
│   │   ├── tools/                   # Browser, code execution, registry
│   │   ├── memory/                  # Episodic, semantic, procedural
│   │   └── knowledge/               # Document ingestion, RAG retrieval
│   ├── risk/                        # Risk calculations
│   │   ├── var.py                   # VaR (Parametric, Historical, Monte Carlo)
│   │   ├── cvar.py                  # CVaR (Expected Shortfall)
│   │   ├── drawdown.py              # Maximum drawdown
│   │   ├── position_sizing.py       # Kelly criterion
│   │   └── portfolio_risk.py        # Portfolio risk metrics
│   ├── security/                    # Security module
│   │   ├── auth.py                  # Authentication service
│   │   ├── scanner.py               # Security scanner
│   │   ├── audit.py                 # Security audit logging
│   │   ├── keyvault.py              # Key vault / secret management
│   │   └── credential_inference.py  # Credential inference detection
│   ├── session/                     # Session management
│   ├── shadow_account/              # Paper trading account
│   ├── solana_scanner/              # Solana on-chain scanner
│   ├── trading_agents/              # TradingAgents framework
│   ├── trading_server/              # Gamification server
│   └── tools/                       # 22 engine tools
│
├── components/                      # React 19 UI (25 components)
├── services/                        # TypeScript services (33 files)
├── tests/                           # 30+ test files (766+ tests)
├── alembic/                         # Database migrations (7 tables)
├── docs/                            # Documentation
├── repos/                           # 59 cloned source repos
└── scripts/                         # Dev setup scripts
```

---

## 🧪 Testing

```bash
# Run all tests
poetry run pytest

# Run specific test suites
poetry run pytest tests/test_engine/      # Engine tests
poetry run pytest tests/test_agents/      # Agent tests
poetry run pytest tests/test_factors/     # Factor tests
poetry run pytest tests/test_risk/        # Risk tests
poetry run pytest tests/test_backtest/    # Backtest tests
poetry run pytest tests/test_api/         # API tests

# Run with coverage
poetry run pytest --cov=quant_nanggroe_ai --cov-report=html
```

**Test Status:** 766+ tests passing across 7 test directories.

---

## 🔗 Related Projects

| Project | Description | Link |
|---|---|---|
| **HermesQuantOS** | Unified Quantitative Intelligence Ecosystem | [GitHub](https://github.com/mulkymalikuldhrs/HermesQuantOS) |

---

## 📜 License

This project is licensed under the MIT License. See the [LICENSE](./LICENSE) file for details.

---

## ⚠️ Current Limitations

| Fitur | Status | Detail |
|-------|--------|--------|
| Frontend-Backend Integration | ⚠️ Partial | TypeScript services belum terhubung ke FastAPI backend |
| hedge_fund imports | ⚠️ Fixed | Semua `from src.*` sudah diperbaiki ke `quant_nanggroe_ai.*` |
| fincept_terminal | ⚠️ Stubs | ~50 file wrapper dengan NotImplementedError |
| Kalshi Broker | ⚠️ New | Memerlukan `cryptography>=41.0.0` dependency |
| CI Pipeline | ⚠️ Missing | Makefile ada tapi belum ada GitHub Actions config |
| Auth Middleware | ⚠️ New | JWT + RBAC implemented, perlu wiring ke semua routes |

---

## 🤝 Contributors Welcome

Kami menyambut kontribusi dari developer, analis kuantitatif, risk engineer, dan AI researcher!

1. **Fork** the repository
2. Create a **feature branch** (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'feat: add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. Open a **Pull Request**

Lihat [CONTRIBUTING.md](./CONTRIBUTING.md) untuk panduan lengkap.

**Contact:** mulkymalikuldhaher@email.com | Mulky Malikul Dhaher

---

## 📬 Contact

**Mulky Malikul Dhaher** — [mulkymalikuldhaher@email.com](mailto:mulkymalikuldhaher@email.com)

GitHub: [https://github.com/mulkymalikuldhrs](https://github.com/mulkymalikuldhrs)

---

## ⚠️ Disclaimer

**EN:** For Education Purpose Only. This project is provided strictly for educational and research purposes. The authors and contributors assume no responsibility or liability for any damages, losses, or risks arising from the use of this software.

**ID (Bahasa Indonesia):** Untuk Tujuan Pendidikan Saja. Proyek ini disediakan secara ketat untuk tujuan pendidikan dan penelitian. Penulis dan kontributor tidak menanggung tanggung jawab atau risiko atas kerusakan, kerugian, atau risiko yang timbul dari penggunaan perangkat lunak ini.

**CN (中文):** 仅供教育目的。本项目严格用于教育和研究目的。作者和贡献者对因使用本软件而产生的任何损害、损失或风险不承担任何责任。

---

Copyright © 2025-2026 Mulky Malikul Dhaher. All rights reserved.
