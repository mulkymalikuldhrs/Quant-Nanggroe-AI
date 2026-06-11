# Architecture: Quant Nanggroe AI

**Version 2.1.0 | Multi-Agent Decision Intelligence Operating System**

Dokumen ini menyediakan referensi teknis komprehensif untuk arsitektur Quant Nanggroe AI. Mencakup model eksekusi berlapis, alur data, interaksi layanan, hubungan komponen, dan framework penalaran deterministik yang mengatur semua proses pengambilan keputusan.

> Bagian dari [HermesQuantOS](https://github.com/mulkymalikuldhrs/HermesQuantOS) Unified Project.

---

## 1. Filosofi Desain

### Penalaran Deterministik di Atas AI Subjektif

Quant Nanggroe AI dibangun di atas premis yang berbeda secara fundamental dari alat bantu trading berbasis AI konvensional. Sistem memperlakukan Large Language Model sebagai **Logical Reasoning Engines** yang beroperasi di bawah kontrak ketat:

1. **Tidak Ada Opini Subjektif** — Agent dilarang menghasilkan analisis "berbasis perasaan", narasi sentimen, atau penilaian kualitatif. Setiap output harus berdasar pada data numerik yang dapat diamati.
2. **Grounding Data Wajib** — Semua penalaran harus berasal dari data Layer 0. Agent tidak dapat menalar tentang kondisi pasar tanpa menerima data kontekstual terlebih dahulu.
3. **Output Berbasis Tekanan** — Agent tidak pernah menghasilkan sinyal trade langsung (BUY/SELL). Mereka menghasilkan nilai tekanan ternormalisasi (0.0–1.0) yang mengalir ke Pressure Normalization Engine.

---

## 2. Arsitektur Sistem Utama

### 2.0 Arsitektur Consolidated Monorepo

Setelah konsolidasi penuh dari 25 C1 repos, semua branch implementasi (cl1-agent-1, cl1-agent-3, cl1-agent-4, Julecl1-session) telah di-merge ke branch Julecl1. Package `quant_nanggroe/` (154 files) telah dikonsolidasikan ke dalam `src/quant_nanggroe_ai/`, menambahkan 7 unique Python modules: execution node, prediction_market node, event_bus, models, regime, simulation, types.

Modul baru yang ditambahkan selama konsolidasi:
- **MCP** (`mcp/`) — Model Context Protocol client/server/tools
- **Exchange** (`exchange/`) — Exchange abstraction layer dengan factory pattern dan Solana submodule
- **Engine Strategy** (`engine/strategy/`) — Strategy schema, loader, parser, backtest adapter
- **Engine Risk** (`engine/risk/`) — Constitutional rules, risk checks, position sizing, VaR, drawdown, correlation
- **Security** (`security/`) — Auth, audit, keyvault, credential inference, scanner
- **Memory** (`memory/`) — Expanded: knowledge, knowledge_graph, journal, session, compression, paging
- **MultiColony** (`multicolony/`) — C2 AI MultiColony Ecosystem (22 files, 6,613 lines)

### 2.1 4-Layer Agent Stack

Sistem menggunakan 4 framework agent yang berlapis, masing-masing dengan tanggung jawab spesifik:

```
┌─────────────────────────────────────────────────┐
│  Layer 1: LangGraph (Orchestration)             │
│  State graph, conditional routing, council       │
│  debates, 9 agent nodes                          │
├─────────────────────────────────────────────────┤
│  Layer 2: CrewAI (Team Coordination)             │
│  Multi-agent collaboration, task delegation,      │
│  role-based agent assignment                      │
├─────────────────────────────────────────────────┤
│  Layer 3: PydanticAI (Validation)                │
│  Schema validation, structured output,            │
│  type-safe agent responses                        │
├─────────────────────────────────────────────────┤
│  Layer 4: DSPy (Optimization)                    │
│  Prompt optimization, performance tuning,          │
│  automatic prompt engineering                      │
└─────────────────────────────────────────────────┘
```

### 2.2 LangGraph Agent Graph (9 Nodes)

```
                    ┌─────────────┐
                    │  Researcher │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Analyst   │
                    └──────┬──────┘
                           │
               ┌───────────┼───────────┐
               │           │           │
        ┌──────▼──────┐    │    ┌──────▼──────┐
        │  Strategist │    │    │    Macro    │
        └──────┬──────┘    │    └─────────────┘
               │           │
        ┌──────▼──────┐    │
        │ Risk Manager│◄───┘
        │   (VETO)    │
        └──────┬──────┘
               │
        ┌──────▼──────┐
        │   Trader    │
        └──────┬──────┘
               │
        ┌──────▼──────┐
        │  Portfolio  │
        │  (Final Gate)│
        └──────┬──────┘
               │
        ┌──────▼──────┐
        │   Crypto    │
        └──────┬──────┘
               │
        ┌──────▼──────┐
        │    Forex    │
        └─────────────┘
```

**Council Debates (Adversarial):**
- **Bull/Bear Debate** — Argumen opposing untuk validasi sinyal
- **Risk Debate** — Tantangan terhadap analisis risk manager

**Protocols:**
- **MCP (Model Context Protocol)** — Standar komunikasi agent-ke-tools dengan transport configuration dan server definitions
- **A2A (Agent-to-Agent)** — Standar komunikasi antar-agent dengan message passing dan capability discovery

### 2.3 Engine Layer (Deterministic — Tidak Ada AI)

Engine layer adalah **100% deterministik** — tidak ada panggilan LLM, tidak ada AI, tidak ada randomness (kecuali seeded Monte Carlo):

| Engine | File | Fungsi |
|--------|------|--------|
| **ConstitutionalRiskGuard** | `engine/risk_guard.py` | 9-checkpoint VETO system dengan limit hardcoded |
| **DecisionEngine** | `engine/decision.py` | Decision table: regime + pressure + confidence → ALLOW/NO_TRADE/WATCH |
| **PressureEngine** | `engine/pressure.py` | BUY/SELL pressure normalization (0.0-1.0) |
| **MarketStateEngine** | `engine/market_state.py` | Regime: TRENDING/RANGE/MEAN_REVERT/RISK_OFF/PANIC/NO_TRADE |
| **KillSwitch** | `engine/kill_switch.py` | Emergency halt, auto-trigger on limit breach |
| **MathLib** | `engine/math_lib.py` | RSI, SMA, EMA, MACD, Bollinger, VWAP, ADX, ATR, CCI, Stochastic |
| **StrategyLifecycle** | `engine/strategy_lifecycle.py` | Darwinian evolution — auto-KILL negative expectancy |
| **NautilusAdapter** | `engine/nautilus_adapter.py` | NautilusTrader backtesting integration |
| **AutoSwitch** | `engine/autoswitch.py` | LLM/data provider failover |
| **EventBus** | `engine/event_bus.py` | Event-driven message bus untuk inter-module communication |
| **AuditEngine** | `engine/audit.py` | Full audit trail logging untuk decision provenance |
| **SimulationEngine** | `engine/simulation.py` | Monte Carlo simulation untuk risk scenarios |
| **RegimeEngine** | `engine/regime.py` | Advanced regime detection dari branch consolidation |
| **EngineModels** | `engine/models.py` | Shared engine model definitions (dari quant_nanggroe/ package) |

#### Engine Risk Submodule (`engine/risk/`)

| Module | File | Fungsi |
|--------|------|--------|
| **ConstitutionalConstants** | `engine/risk/constants.py` | Hardcoded constitutional rules (NON-NEGOTIABLE) |
| **RiskChecks** | `engine/risk/checks.py` | Individual risk checkpoint implementations |
| **RiskManager** | `engine/risk/manager.py` | Risk manager coordination layer |
| **PositionSizing** | `engine/risk/position_sizing.py` | Position sizing algorithms |
| **KellyCriterion** | `engine/risk/kelly.py` | Kelly criterion implementation |
| **ValueAtRisk** | `engine/risk/var.py` | Value at Risk calculations |
| **DrawdownMonitor** | `engine/risk/drawdown.py` | Drawdown calculations and monitoring |
| **CorrelationMonitor** | `engine/risk/correlation.py` | Position correlation monitoring |
| **RiskParity** | `engine/risk/risk_parity.py` | Risk parity allocation |
| **EmotionalLockout** | `engine/risk/emotional_lockout.py` | Emotional trading lockout periods |
| **RiskKillSwitch** | `engine/risk/kill_switch.py` | Risk-level emergency kill switch |

#### Engine Strategy Submodule (`engine/strategy/`)

| Module | File | Fungsi |
|--------|------|--------|
| **StrategySchema** | `engine/strategy/schema.py` | Strategy schema definitions |
| **StrategyLoader** | `engine/strategy/loader.py` | Dynamic strategy loading |
| **StrategyParser** | `engine/strategy/parser.py` | Strategy parameter parsing |
| **BacktestAdapter** | `engine/strategy/backtest_adapter.py` | Strategy-to-backtest bridge |

**Konstitusi Risk (NON-NEGOTIABLE) — hardcoded di `engine/risk/constants.py`:**
```python
MAX_RISK_PER_TRADE = 0.005   # 0.5%
MAX_DAILY_LOSS = 0.01        # 1.0%
MAX_WEEKLY_LOSS = 0.03       # 3.0%
MIN_RISK_REWARD = 2.0        # 1:2 minimum
```

---

## 3. Execution Layer — 5 Brokers + Exchange Abstraction

### 3.1 Legacy Execution Module (`execution/`)

| Broker | Pasar | Auth | Fitur Utama |
|--------|-------|------|-------------|
| **Paper** | Universal | N/A | In-memory order book, SL/TP, partial fills |
| **Alpaca** | US Equities | API Key | REST API, rate limiting, position management |
| **Jupiter** | Solana DEX | Private Key | V6 swap API, JITO tips, transaction signing |
| **Polymarket** | Prediction Markets | API Key | Gamma + CLOB + Data API, order management |
| **Kalshi** | Event Contracts | RSA-PSS | Full order lifecycle, market data, account queries |

### 3.2 Exchange Abstraction Layer (`exchange/`)

Modul exchange baru menyediakan abstraction layer terpadu untuk semua broker:

| Component | File | Fungsi |
|-----------|------|--------|
| **BaseExchange** | `exchange/base.py` | Abstract base exchange interface |
| **ExchangeFactory** | `exchange/factory.py` | Factory pattern untuk broker instantiation |
| **ExchangeManager** | `exchange/manager.py` | Exchange lifecycle dan connection management |
| **ExchangeGuards** | `exchange/guards.py` | Pre-trade guard rails dan validation |
| **OrderTypes** | `exchange/order_types.py` | Order type definitions dan enums |
| **PaperBroker** | `exchange/paper_broker.py` | Paper trading via exchange interface |
| **AlpacaBroker** | `exchange/alpaca_broker.py` | Alpaca via exchange interface |
| **CCXTBroker** | `exchange/ccxt_broker.py` | CCXT (100+ crypto exchanges) via exchange interface |

#### Solana Exchange Submodule (`exchange/solana/`)

| Component | File | Fungsi |
|-----------|------|--------|
| **JupiterExchange** | `exchange/solana/jupiter.py` | Jupiter V6 swap integration |
| **RugCheck** | `exchange/solana/rugcheck.py` | Token safety verification |
| **MempoolMonitor** | `exchange/solana/mempool.py` | Solana mempool monitoring |
| **SolanaWallet** | `exchange/solana/wallet.py` | Solana wallet management |
| **SolanaBroker** | `exchange/solana/broker.py` | Solana broker via exchange interface |

### Broker Registry Pattern

```python
BROKER_REGISTRY: dict[str, type[BaseBroker]] = {
    "paper": PaperBroker,
    "alpaca": AlpacaBroker,
    "jupiter": JupiterBroker,
    "polymarket": PolymarketBroker,
    "kalshi": KalshiBroker,
}
BrokerType = type[PaperBroker | AlpacaBroker | JupiterBroker | PolymarketBroker | KalshiBroker]
```

---

## 4. Factor Library — 452 Alpha Factors

### Struktur

```
factors/
├── zoo/
│   ├── alpha101/     # 101 WorldQuant Alpha101 factors
│   ├── qlib158/      # 154 Microsoft Qlib factors
│   └── academic/     # 7 Fama-French 5-Factor + Carhart factors
├── registry.py       # Factor registry & auto-discovery
├── registry_vt.py    # Virtual trading registry
├── factor_analysis_core.py  # IC/IR analysis engine
├── fama_french.py    # Fama-French 5-factor model
└── technical.py      # Technical indicator factors
```

### Factor Breakdown

| Kategori | Jumlah | Sumber |
|----------|--------|--------|
| Alpha101 | 101 | WorldQuant Alpha101 (Kakushadze 2015) |
| Qlib158 | 154 | Microsoft Qlib Alpha158 |
| GTJA191 | 191 | Guotai Junan 191 |
| Academic | 7 | Fama-French 5-Factor + Carhart Momentum |
| **Total** | **452** | |

### Factor Metadata

Setiap factor memiliki `__alpha_meta__` dengan:
- Nama formula dan deskripsi
- Parameters yang dibutuhkan
- Category dan domain
- Reference paper

### Infrastructure

- **Registry** — Central factor registry dengan auto-discovery
- **Analysis Engine** — IC (Information Coefficient), IR (Information Ratio), turnover analysis
- **Bench Runner** — Factor benchmarking terhadap dataset historis

---

## 5. Backtest System — 9 Engines

### Engine Hierarchy

```
BaseEngine (Abstract)
├── ChinaAEngine       # A-share: T+1, no short, 10%/20% price limits
├── GlobalEquityEngine # US/HK standard equity
├── CryptoEngine       # 24/7, funding fees, liquidation
├── ForexEngine        # Spread, swap, high leverage
├── ChinaFuturesEngine # CFFEX/SHFE/DCE/ZCE/INE
├── GlobalFuturesEngine # CME/ICE/Eurex
├── CompositeEngine    # Cross-market shared capital pool
└── OptionsPortfolio   # Black-Scholes, IV smile
```

### NautilusTrader Integration

`nautilus_adapter.py` menyediakan adapter ke NautilusTrader backtesting framework untuk institutional-grade backtesting:

- Bar-by-bar execution simulation
- Realistic fill modeling
- Multi-asset portfolio backtesting
- Walk-forward optimization support

### Portfolio Optimizers (4)

| Optimizer | Metode |
|-----------|--------|
| Mean Variance | Markowitz efficient frontier |
| Risk Parity | Equal risk contribution |
| Max Diversification | Diversification ratio maximization |
| Equal Volatility | Inverse volatility weighting |

### Data Loaders (8)

| Loader | Sumber Data |
|--------|-------------|
| YFinance | Global equities (Yahoo Finance) |
| CCXT | Crypto exchanges (100+ via CCXT) |
| OKX | OKX exchange |
| Futu | Futu OpenD (HK/CN) |
| Tushare | Chinese A-share |
| Tushare Fundamentals | Financial statements |
| AKShare | Chinese market data |
| Registry | Auto-loader selection |

---

## 6. API Layer — FastAPI + WebSocket

### Route Modules

| Router | Endpoints | Deskripsi |
|--------|-----------|-----------|
| `/api/agents` | Agent graph execution | Run agent pipeline, get status |
| `/api/market` | Market data | Prices, candles, news |
| `/api/portfolio` | Portfolio management | Positions, equity, PnL |
| `/api/trading` | Order execution | Place, cancel, modify orders |
| `/api/backtest` | Backtesting | Run backtests, get results |
| `/api/auth` | Authentication | JWT login, register, RBAC |
| `/ws` | WebSocket | Real-time streaming |

### Authentication (JWT + RBAC)

- **JWTManager** — Token generation, validation, refresh
- **AuthService** — User management, password hashing (PBKDF2-SHA256, 100K rounds)
- **AuthMiddleware** — Request-level auth enforcement
- **Roles** — ADMIN, TRADER, VIEWER (hierarchical permissions)

### Shared Singletons

Semua route modules menggunakan shared singleton instances:
```python
# services.py
kill_switch = KillSwitch()
risk_guard = RiskGuard()
market_engine = MarketEngine()
decision_engine = DecisionEngine()
```

---

## 7. Storage Layer

### Database Schema (7 Tables)

| Table | Purpose |
|-------|---------|
| `users` | User accounts with auth fields |
| `strategies` | Strategy lifecycle with performance metrics |
| `trades` | Full trade records with risk context |
| `positions` | Open position tracking |
| `portfolio_snapshots` | Time-series portfolio state |
| `risk_events` | Risk veto/warning audit log |
| `agent_logs` | Agent execution trace with LLM token tracking |

### Storage Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Relational | PostgreSQL 16+ | Users, trades, positions, strategies |
| Time-Series | QuestDB | Portfolio snapshots, market data ticks |
| Cache | Redis 7+ | Session data, rate limiting, API cache |
| ORM | SQLAlchemy 2.0 (async) | Database access layer |
| Migrations | Alembic | Schema version management |

### Data Flow

```
Application Code
       │
       ▼
SQLAlchemy 2.0 (async sessions)
       │
       ├──► PostgreSQL (relational data)
       ├──► QuestDB (time-series data)
       └──► Redis (cache layer)
              │
              ▼
       Alembic (migrations)
```

---

## 8. Memory & Knowledge System

| Module | File | Deskripsi |
|--------|------|-----------|
| **Vector Memory** | `memory/vector.py` | TF-IDF embeddings, cosine similarity, metadata filtering |
| **Conversation** | `memory/conversation.py` | Chat history management, context windowing |
| **Research** | `memory/research.py` | Research note storage and retrieval |
| **Knowledge** | `memory/knowledge.py` | Knowledge base storage |
| **Knowledge Graph** | `memory/knowledge_graph.py` | Knowledge graph traversal and queries |
| **Journal** | `memory/journal.py` | Trading journal dengan emotional tracking |
| **Session** | `memory/session.py` | Session-scoped memory |
| **Compression** | `memory/compression.py` | TokenJuice-style memory compression |
| **Paging** | `memory/paging.py` | Memory paging dan overflow management |
| **Persistent** | `memory_persistent/persistent.py` | Cross-session persistent storage |

---

## 9. MCP Module (`mcp/`)

Model Context Protocol diimplementasikan sebagai modul standalone:

| Component | File | Deskripsi |
|-----------|------|-----------|
| **MCP Client** | `mcp/client.py` | MCP client untuk koneksi ke MCP servers |
| **MCP Server** | `mcp/server.py` | MCP server implementation |
| **MCP Protocol** | `mcp/protocol.py` | Protocol definitions dan message types |
| **MCP Tools** | `mcp/tools.py` | MCP tool registry dan invocation |

Ditambah: `agents/mcp_config.py` — 5 default MCP servers untuk trading platform, transport configuration, tool event definitions.

## 10. Security Module (`security/`)

| Component | File | Deskripsi |
|-----------|------|-----------|
| **AuthService** | `security/auth.py` | Authentication service (JWT + RBAC) |
| **SecurityScanner** | `security/scanner.py` | Security vulnerability scanning |
| **SecurityAudit** | `security/audit.py` | Security audit logging dan trail |
| **KeyVault** | `security/keyvault.py` | Key vault dan secret management |
| **CredentialInference** | `security/credential_inference.py` | Credential inference dan leak detection |

## 11. Integrations

### WhatsApp Bot
`integrations/whatsapp_bot.py` — Command parsing, message formatting, notification sending via WhatsApp Business API.

### Trading Plan Tool
`agents/tools/trading_plan.py` — CFTC commitment-of-traders data, trade journal with validation, emotional lockout periods, weekly analysis generation.

### File Operations
`agents/tools/file_ops.py` — Local file storage + MongoDB GridFS, attachment service, file operation factory pattern.

### Solana Scanner
`solana_scanner/` — Mempool monitoring, RugCheck integration, auto-sniper with new-token callbacks, SQLite database for trades/positions/limit_orders.

---

## 12. Risk Module

| Module | Metode | Deskripsi |
|--------|--------|-----------|
| **VaR** | Parametric, Historical, Monte Carlo | Value at Risk calculation |
| **CVaR** | Conditional VaR | Expected Shortfall beyond VaR threshold |
| **Drawdown** | Maximum drawdown, recovery time | Peak-to-trough analysis |
| **Position Sizing** | Kelly criterion, fixed-fractional | Optimal position size calculation |
| **Portfolio Risk** | Correlation, beta, tracking error | Portfolio-level risk metrics |

Plus the engine-level `ConstitutionalRiskGuard` with 9-checkpoint VETO system yang TIDAK DAPAT di-override oleh agent manapun.

---

## 13. Frontend Architecture

Frontend dibangun sebagai antarmuka desktop-OS menggunakan React 19 dan TypeScript:

```
App.tsx (Root)
 ├── Taskbar (Dock)
 ├── OmniBar (Spotlight Search)
 ├── ControlCenter (System Panel)
 └── WindowFrame (Container) × N
      ├── TradingTerminalWindow
      ├── MarketWindow
      ├── PortfolioWindow
      ├── ResearchAgentWindow
      ├── KnowledgeBaseWindow
      ├── BrowserWindow
      ├── NexusWindow
      ├── SwarmConfigModal
      ├── SystemArchitecture
      ├── AgentHud
      └── SolSniperX (Sidebar + TradingPage)
```

> **Status:** Frontend saat ini DISCONNECTED dari Python backend. 33 TypeScript service stubs belum memiliki API client.

---

## 14. Data Flow Summary

```
[Market Data Providers]
        │
        ▼
[AutoSwitch Engine] ──► Provider Failover & Health
        │
        ▼
[MarketStateEngine] ──► Regime Detection
        │
        ├── If NO_TRADE/PANIC ──► System Idle
        │
        ▼ (Regime Compatible)
[9 Agent Nodes via LangGraph]
   │     │     │     │     │     │     │     │     │
   │     │     │     │     │     │     │     │     └── Crypto
   │     │     │     │     │     │     │     └── Forex
   │     │     │     │     │     │     └── Portfolio (Final Gate)
   │     │     │     │     │     └── Trader
   │     │     │     │     └── Risk Manager (VETO)
   │     │     │     └── Macro
   │     │     └── Strategist
   │     └── Analyst
   └── Researcher
        │
        ▼
[Pressure Engine] ──► BUY/SELL Pressure Vectors
        │
        ▼
[Decision Engine] ──► Decision Table Evaluation
        │
        ▼
[Risk Guard] ──► Constitutional Rule Verification
        │
        ├── If Violation ──► Trade VETOED
        │
        ▼ (Risk Cleared)
[Execution Layer] ──► Paper | Alpaca | Jupiter | Polymarket | Kalshi
        │
        ▼
[Audit Logger] ──► Full Decision Trail Recorded
```

---

## 15. Service Dependency Graph

```
FastAPI App
    ├── Auth Middleware (JWT)
    ├── WebSocket Handler
    └── Route Modules (6)
         ├── agents → LangGraph Graph → 9 Nodes
         ├── market → MarketService → AutoSwitch
         ├── portfolio → RiskGuard → DecisionEngine
         ├── trading → ExecutionBroker → 5 Brokers
         ├── backtest → BacktestEngine → 9 Market Engines
         └── auth → AuthService → JWTManager

LangGraph Graph
    ├── 9 Agent Nodes (Researcher, Trader, Strategist, Risk, Portfolio, Execution, Macro, Crypto, Forex)
    ├── 11 Agent Tools
    ├── 2 Council Debates
    ├── MCP Protocol (mcp/ module)
    └── A2A Protocol

Engine Layer (Deterministic)
    ├── RiskGuard ←── StrategyLifecycle
    ├── DecisionEngine ←── PressureEngine
    ├── PressureEngine ←── MarketStateEngine
    ├── MarketStateEngine ←── MathLib
    ├── EventBus ←── inter-module communication
    ├── SimulationEngine ←── Monte Carlo
    ├── RegimeEngine ←── advanced regime detection
    └── engine/risk/ ←── constants, checks, kelly, var, drawdown, correlation

Engine Strategy (engine/strategy/)
    ├── StrategySchema ←── strategy definitions
    ├── StrategyLoader ←── dynamic loading
    ├── StrategyParser ←── parameter parsing
    └── BacktestAdapter ←── strategy-to-backtest bridge

Exchange Layer
    ├── BaseExchange (abstract interface)
    ├── ExchangeFactory (broker instantiation)
    ├── PaperBroker (in-memory)
    ├── AlpacaBroker (REST API)
    ├── CCXTBroker (100+ crypto exchanges)
    └── Solana/ (Jupiter, RugCheck, Mempool, Wallet, Broker)

Execution Layer (legacy)
    ├── PaperBroker (in-memory)
    ├── AlpacaBroker (REST API)
    ├── JupiterBroker (Solana V6)
    ├── PolymarketBroker (CLOB + Gamma + Data)
    └── KalshiBroker (RSA-PSS Auth)

MCP Module
    ├── MCPClient ←── external server connections
    ├── MCPServer ←── server implementation
    ├── MCPProtocol ←── message types
    └── MCPTools ←── tool registry

Security Module
    ├── AuthService (JWT + RBAC)
    ├── SecurityScanner (vulnerability scanning)
    ├── SecurityAudit (audit logging)
    ├── KeyVault (secret management)
    └── CredentialInference (leak detection)

Factor Library
    ├── 101 Alpha101 factors
    ├── 154 Qlib158 factors
    ├── 191 GTJA191 factors
    ├── 7 Academic factors (Fama-French 5-Factor + Carhart)
    └── Registry + Analysis Engine

Memory System
    ├── Vector Memory (TF-IDF)
    ├── Conversation, Research, Knowledge, Knowledge Graph
    ├── Journal, Session, Compression, Paging
    └── Persistent storage

Storage Layer
    ├── PostgreSQL (SQLAlchemy 2.0 async)
    ├── QuestDB (time-series)
    ├── Redis (cache)
    └── Alembic (migrations)
```

---

## 16. Monorepo Consolidation

Sistem ini adalah hasil konsolidasi dari **25 repositori** ke dalam satu monorepo. Semua branch implementasi (cl1-agent-1, cl1-agent-3, cl1-agent-4, Julecl1-session) telah di-merge ke branch Julecl1. Package `quant_nanggroe/` (154 files) telah dikonsolidasikan ke dalam `src/quant_nanggroe_ai/`, menambahkan 7 unique Python modules: execution node, prediction_market node, event_bus, models, regime, simulation, types.

**766+ tests passing** | **452 alpha factors** | **9-agent trading council** | **4-layer agent stack**

Lihat [CLUSTER1_CONSOLIDATION_REPORT.md](./CLUSTER1_CONSOLIDATION_REPORT.md) untuk detail lengkap tentang repo mana yang digabungkan, kode apa yang diekstrak, dan apa yang dibuang.

---

© 2025-2026 Quant Nanggroe AI | Technical Architecture Reference v2.1.0
