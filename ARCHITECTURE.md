# Architecture: Quant Nanggroe AI

**Version 2.0.0 | Multi-Agent Decision Intelligence Operating System**

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

**Konstitusi Risk (NON-NEGOTIABLE):**
```python
MAX_RISK_PER_TRADE = 0.005   # 0.5%
MAX_DAILY_LOSS = 0.01        # 1.0%
MAX_WEEKLY_LOSS = 0.03       # 3.0%
MIN_RISK_REWARD = 2.0        # 1:2 minimum
```

---

## 3. Execution Layer — 5 Brokers

| Broker | Pasar | Auth | Fitur Utama |
|--------|-------|------|-------------|
| **Paper** | Universal | N/A | In-memory order book, SL/TP, partial fills |
| **Alpaca** | US Equities | API Key | REST API, rate limiting, position management |
| **Jupiter** | Solana DEX | Private Key | V6 swap API, JITO tips, transaction signing |
| **Polymarket** | Prediction Markets | API Key | Gamma + CLOB + Data API, order management |
| **Kalshi** | Event Contracts | RSA-PSS | Full order lifecycle, market data, account queries |

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

## 4. Factor Library — 456+ Alpha Factors

### Struktur

```
factors/
├── zoo/
│   ├── alpha101/     # 101 WorldQuant Alpha101 factors
│   ├── qlib158/      # 154 Microsoft Qlib factors
│   └── academic/     # 7 Fama-French + Carhart factors
├── registry.py       # Factor registry & auto-discovery
├── registry_vt.py    # Virtual trading registry
├── factor_analysis_core.py  # IC/IR analysis engine
├── fama_french.py    # Fama-French model
└── technical.py      # Technical indicator factors
```

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
| **Persistent** | `memory_persistent/persistent.py` | Cross-session persistent storage |

---

## 9. Integrations

### WhatsApp Bot
`integrations/whatsapp_bot.py` — Command parsing, message formatting, notification sending via WhatsApp Business API.

### Trading Plan Tool
`agents/tools/trading_plan.py` — CFTC commitment-of-traders data, trade journal with validation, emotional lockout periods, weekly analysis generation.

### File Operations
`agents/tools/file_ops.py` — Local file storage + MongoDB GridFS, attachment service, file operation factory pattern.

### MCP Configuration
`agents/mcp_config.py` — 5 default MCP servers for trading platform, transport configuration, tool event definitions.

### Solana Scanner
`solana_scanner/` — Mempool monitoring, RugCheck integration, auto-sniper with new-token callbacks, SQLite database for trades/positions/limit_orders.

---

## 10. Risk Module

| Module | Metode | Deskripsi |
|--------|--------|-----------|
| **VaR** | Parametric, Historical, Monte Carlo | Value at Risk calculation |
| **CVaR** | Conditional VaR | Expected Shortfall beyond VaR threshold |
| **Drawdown** | Maximum drawdown, recovery time | Peak-to-trough analysis |
| **Position Sizing** | Kelly criterion, fixed-fractional | Optimal position size calculation |
| **Portfolio Risk** | Correlation, beta, tracking error | Portfolio-level risk metrics |

Plus the engine-level `ConstitutionalRiskGuard` with 9-checkpoint VETO system yang TIDAK DAPAT di-override oleh agent manapun.

---

## 11. Frontend Architecture

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

## 12. Data Flow Summary

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

## 13. Service Dependency Graph

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
    ├── 9 Agent Nodes
    ├── 7 Agent Tools
    ├── 2 Council Debates
    ├── MCP Protocol
    └── A2A Protocol

Engine Layer (Deterministic)
    ├── RiskGuard ←── StrategyLifecycle
    ├── DecisionEngine ←── PressureEngine
    ├── PressureEngine ←── MarketStateEngine
    └── MarketStateEngine ←── MathLib

Execution Layer
    ├── PaperBroker (in-memory)
    ├── AlpacaBroker (REST API)
    ├── JupiterBroker (Solana V6)
    ├── PolymarketBroker (CLOB + Gamma + Data)
    └── KalshiBroker (RSA-PSS Auth)

Factor Library
    ├── 101 Alpha101 factors
    ├── 154 Qlib158 factors
    ├── 7 Academic factors
    └── Registry + Analysis Engine

Storage Layer
    ├── PostgreSQL (SQLAlchemy 2.0 async)
    ├── QuestDB (time-series)
    ├── Redis (cache)
    └── Alembic (migrations)
```

---

## 14. Monorepo Consolidation

Sistem ini adalah hasil konsolidasi dari **25+ repositori** ke dalam satu monorepo. Lihat [CLUSTER1_CONSOLIDATION_REPORT.md](./CLUSTER1_CONSOLIDATION_REPORT.md) untuk detail lengkap tentang repo mana yang digabungkan, kode apa yang diekstrak, dan apa yang dibuang.

---

© 2025-2026 Quant Nanggroe AI | Technical Architecture Reference v2.0.0
