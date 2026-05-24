<!-- 🦅 QUANT NANGGROE AI — Professional README -->
<!-- Language: English -->

<a href="https://github.com/mulkymalikuldhrs/Quant-Nanggroe-AI">
  <img align="center" src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&weight=700&size=36&duration=3000&pause=1500&color=00D4AA&center=true&vCenter=true&multiline=true&repeat=true&width=800&height=120&lines=QUANT+NANGGROE+AI;Multi-Agent+Decision+Intelligence+OS" alt="Typing SVG" />
</a>

<div align="center">

[![Version](https://img.shields.io/badge/Version-15.2.0-gold?style=for-the-badge&logo=semver&logoColor=white)](https://github.com/mulkymalikuldhrs/Quant-Nanggroe-AI)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.8-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge&logo=open-source-initiative&logoColor=white)](./LICENSE)
[![Status](https://img.shields.io/badge/Status-Operational_Full-22C55E?style=for-the-badge&logo=checkmarx&logoColor=white)](https://github.com/mulkymalikuldhrs/Quant-Nanggroe-AI)

</div>

<div align="center">

**Language / Bahasa / 语言:**
[![English](https://img.shields.io/badge/EN-English-blue?style=flat-square)](./README.md)
[![Bahasa Indonesia](https://img.shields.io/badge/ID-Bahasa_Indonesia-red?style=flat-square)](./README_id.md)
[![中文](https://img.shields.io/badge/CN-中文-yellow?style=flat-square)](./README_zh.md)

</div>

---

## 🏛️ Overview

**Quant Nanggroe AI** is an advanced **Multi-Agent Decision Intelligence Operating System** engineered for quantitative research and systematic trading in financial markets. Built on the principle of **Deterministic Decision Intelligence**, this platform fundamentally rejects subjective AI narratives and psychological bias in favor of mathematically constrained reasoning over raw numerical data. The system treats Large Language Models not as advisors, but as **Logical Reasoning Engines** — each operating under strict contracts that forbid subjective opinions, mandate data grounding, and require pressure-based numerical outputs rather than direct trade signals.

At its core, Quant Nanggroe AI implements a **5-Layer Execution Stack** that processes market data from raw L1/L2 feeds through regime detection, multi-agent sensor analysis, pressure normalization, and ultimately decision synthesis with risk enforcement. The architecture is inspired by institutional quantitative trading desks, where every decision must be traceable, auditable, and defensible. The system employs a **Darwinian Strategy Lifecycle** that automatically kills underperforming strategies, an **Execution Reality Engine** that accounts for slippage, spread, and latency in backtesting, and a **Risk Guardian Constitution** that acts as an independent layer of hard-coded safety rules immune to AI reasoning.

The frontend is a desktop-OS-inspired interface built with React 19 and TypeScript, featuring draggable windows, a macOS-style dock, an AI-powered command center (OmniBar), and real-time visualization of the multi-agent swarm. It is designed to be a complete research and decision-support workstation — not just a dashboard, but an operating environment for quantitative intelligence.

> 🔗 **Part of the [HermesQuantOS](https://github.com/mulkymalikuldhrs/HermesQuantOS) Unified Project** — A full-stack quantitative intelligence ecosystem.

---

## 🏗️ Architecture

Quant Nanggroe AI is built on a **5-Layer Deterministic Execution Stack**, where each layer acts as a strict filter that either passes data forward or blocks it entirely. No layer can be bypassed, and no agent can override the constraints imposed by layers above it. This design ensures that every trading decision is the result of a fully auditable, deterministic pipeline — from raw market data ingestion to final execution parameters with risk clearance.

### Layer 0: Contextual Neural Grounding (Data Foundation)
The bedrock of the entire system. This layer harvests real-time L1/L2 market data from multiple providers — Binance, CoinCap, AlphaVantage, Polygon, and Finnhub — using the **AutoSwitch** engine for automatic failover and provider health monitoring. Every piece of data that enters the system is tagged with metadata including source, trust score (0.0–1.0), latency estimate, update frequency, and domain type. This metadata flows downstream, allowing every agent and engine to weight its confidence based on data quality. The **MarketService** orchestrates all data access, providing a unified API for price feeds, candle data, news, and technical indicators.

### Layer 1: Market Regime Engine (The Gatekeeper)
The **MarketStateEngine** sits above all agents and serves as the system's gatekeeper. It determines the global market condition — `TRENDING`, `RANGE`, `MEAN_REVERT`, `RISK_OFF`, `PANIC`, or `NO_TRADE` — using a combination of ADX trend strength, RSI extremes, and rapid price change detection. If the regime is `NO_TRADE` or `PANIC`, all downstream agents are forced into idle mode, protecting capital during unsuitable conditions. This is a hard constraint that cannot be overridden by any agent or LLM reasoning.

### Layer 2: Multi-Agent Sensors (The Eyes)
Four specialized agents operate in parallel as numerical sensors, each producing structured output types rather than subjective analysis:
- **QuantScanner** (`quant_scanner.ts`) — Technical momentum, ADX trend strength, volatility expansion, and structure state (BULL/BEAR/NEUTRAL).
- **SMCAgent** (`smc_agent.ts`) — Smart Money Concepts: liquidity sweeps, displacement strength, and Point of Interest validity.
- **NewsSentinel** (`news_sentinel.ts`) — Macroeconomic event classification (MACRO/SCHEDULED/SHOCK/NOISE) with logarithmic time decay and directional uncertainty scoring.
- **FlowAgent** (`flow_agent.ts`) — Institutional whale flow tracking, COT positioning bias (LONG/SHORT/NEUTRAL), and flow imbalance measurement.

### Layer 3: Pressure Normalization Engine (The Compiler)
The **PressureNormalizationEngine** aggregates raw sensor outputs from all four agents and compiles them into two primary vectors: `BUY_PRESSURE` (0.0–1.0) and `SELL_PRESSURE` (0.0–1.0), along with volatility risk classification, liquidity condition, and an overall confidence score. Each sensor contributes a weighted portion to the pressure calculation, with the specific weights derived from the Blueprint Final specification. This layer eliminates the problem of conflicting agent signals by reducing everything to a single, normalized pressure field.

### Layer 4: Decision Synthesis Engine (The Judge)
The **DecisionSynthesisEngine** is the final authority. It uses a **Decision Table** (machine-readable rules) to evaluate whether the current pressure state, regime, volatility, and confidence levels meet the criteria for entry. If confluence is achieved, the **EntryRiskEngine** calculates geometric entry parameters — entry price, structural stop loss (invalidation-based, not percentage-based), and tiered take profits (TP1: nearest liquidity, TP2: volatility extension, TP3: volatility extension ×2). Risk clearance is independently verified by the **RiskManagement** module, which enforces the Trading Constitution.

---

## ⚡ Key Features

### 🧠 Deterministic Multi-Agent Swarm
The system coordinates 5 default swarm agents — Alpha Prime (portfolio manager), Quant-Scanner (technical analyst), News-Sentinel (macro/sentiment), Risk-Guardian (risk control), and Strategy-Weaver (algorithm developer) — each with constrained reasoning scopes, explicit input domains, and hard constraints that prevent subjective analysis or hallucinated outputs. Agents communicate through structured contracts, not free-form text.

### 🛡️ Risk Guardian Constitution
Risk management is hard-coded and independent of AI logic. The Trading Constitution enforces: maximum daily drawdown limit with automatic kill-switch, maximum correlation between active positions (0.70 threshold), maximum exposure per asset, and structural invalidation-based stop losses that take precedence over risk-reward ratios. No agent can "reason around" these rules.

### 🧬 Darwinian Strategy Lifecycle
Every strategy is monitored for statistical significance. If a strategy's **expectancy** becomes negative over a sufficient sample size (minimum 20 trades), it is automatically marked as `KILLED` and resources shift to higher-performing variants. Strategies with drawdown exceeding 15% are placed in `HIBERNATING` status. This natural selection mechanism ensures the system continuously evolves toward profitability.

### 📊 Execution Reality Engine
Backtesting isn't fantasy. The **BacktestEngine** accounts for dynamic spread (volatility-adjusted), random slippage, partial fill probability (2–15% depending on volatility), order rejection simulation, and realistic latency (100–500ms). This ensures that backtested performance reflects real-world trading conditions rather than idealized assumptions.

### 🔍 Full Audit Trail
The **AuditLogger** records every event across all layers — Market, Sensor, Pressure, Decision, Risk, and Execution — with timestamps, structured data payloads, and severity levels. Every decision the system makes is fully traceable and reproducible, meeting institutional compliance requirements.

### 🔄 AutoSwitch API Failover
The **AutoSwitch** engine provides automatic provider failover with exponential backoff retry logic, health-based provider prioritization, cooldown mechanisms for failing providers, and real-time health reporting. This ensures uninterrupted data flow even when individual API providers experience outages or rate limits.

### 📚 Autonomous Research Agent
The **ResearchAgent** runs continuously on a configurable interval, harvesting intelligence from 8+ sources including global news, market snapshots, geopolitical data, social sentiment, institutional flows, and AI ecosystem updates. All harvested intelligence is persisted to the Knowledge Base for cross-referencing and historical analysis.

### 🧮 Institutional-Grade Math Engine
The **MathEngine** provides a comprehensive suite of pure mathematical indicators: RSI, SMA, EMA, MACD, Bollinger Bands, VWAP with bands, Volume Profile, Stochastic Oscillator, CCI, ADX, and ATR. Every calculation is 100% deterministic with zero AI involvement — eliminating hallucination risk from technical analysis.

---

## 🖥️ Component Descriptions

| Component | File | Description |
|---|---|---|
| **Launchpad** | `components/Launchpad.tsx` | macOS-style application launcher providing quick access to all system windows and tools. Displays all available applications in a grid layout with animated icons and labels. |
| **TradingTerminal** | `components/TradingTerminalWindow.tsx` | Professional trading terminal featuring real-time candlestick charts powered by Lightweight Charts v4.1, order placement interface, and live position tracking with equity/margin/PnL display. |
| **SwarmGraph** | `components/SwarmConfigModal.tsx` | Swarm intelligence configuration panel for managing agent capabilities, assigning tools, and monitoring the health and activity of each agent in the swarm. |
| **NexusWindow** | `components/NexusWindow.tsx` | Quantum Nexus visualization dashboard displaying system coherence metrics, active qubits, synaptic load, and operational status of the neural processing pipeline. |
| **MarketWindow** | `components/MarketWindow.tsx` | Real-time market data dashboard showing price tickers, 24h changes, volume, technical indicators, and market state classification for tracked assets. |
| **ResearchAgentWindow** | `components/ResearchAgentWindow.tsx` | Research intelligence console displaying autonomous research logs, harvested intelligence summaries, and source scanning status for all 8+ intelligence sources. |
| **KnowledgeBaseWindow** | `components/KnowledgeBaseWindow.tsx` | Knowledge management interface for browsing, searching, and managing research items, market analyses, and institutional intelligence stored in the persistent knowledge base. |
| **BrowserWindow** | `components/BrowserWindow.tsx` | Integrated web browser for navigating financial news sites, research papers, and market data sources directly within the Quant Nanggroe OS environment. |
| **PortfolioWindow** | `components/PortfolioWindow.tsx` | Portfolio management dashboard with real-time equity tracking, margin status, PnL calculations, asset allocation visualization, and position management. |
| **SystemArchitecture** | `components/SystemArchitecture.tsx` | Visual system architecture diagram showing the 5-layer execution stack, data flow between engines, and agent communication pathways. |
| **AgentHud** | `components/AgentHud.tsx` | Heads-Up Display for monitoring swarm agent states, including current action, emotion, thinking status, and active browser URL tracking. |
| **ControlCenter** | `components/ControlCenter.tsx` | System control panel with security matrix, risk guardian dashboard, theme toggle, and system configuration options. |
| **OmniBar** | `components/OmniBar.tsx` | Spotlight-style universal command bar for quick access to any system function, market scan commands (`/scan`), and AI-powered search. |
| **Taskbar** | `components/Taskbar.tsx` | macOS-inspired dock at the bottom of the screen providing window management, application launching, and system status indicators. |
| **WindowFrame** | `components/WindowFrame.tsx` | Draggable, resizable window container with title bar, minimize/close buttons, z-index management, and focus tracking for the desktop OS experience. |

---

## 🚀 Quick Start

### Prerequisites
- **Node.js** >= 18.0.0
- **npm** >= 9.0.0 (or yarn/pnpm)
- API Keys (optional but recommended):
  - **Google Gemini** — for LLM-powered swarm intelligence
  - **Finnhub** — for real-time market data
  - **AlphaVantage** — for stock/forex technical data

### Installation

```bash
# Clone the repository
git clone https://github.com/mulkymalikuldhrs/Quant-Nanggroe-AI.git

# Navigate to the project directory
cd Quant-Nanggroe-AI

# Install dependencies
npm install

# Start the development server
npm run dev
```

### Configuration

1. Launch the application with `npm run dev`
2. Open the **Settings** panel from the Control Center or Taskbar
3. Enter your API keys in the configuration section:
   - `Google API Key` — Required for Gemini-powered agent swarm
   - `Finnhub API Key` — For real-time market data feeds
   - `AlphaVantage API Key` — For stock technical indicators
4. The system will automatically initialize storage services (IndexedDB, BrowserFS, Memory Manager) on startup
5. The **ResearchAgent** will begin autonomous intelligence harvesting immediately

### Build for Production

```bash
# Create optimized production build
npm run build

# Preview the production build locally
npm run preview
```

---

## 📁 Project Structure

```
Quant-Nanggroe-AI/
├── 📄 App.tsx                          # Main application component with OS-style window management
├── 📄 index.tsx                         # Application entry point
├── 📄 types.ts                          # Core type definitions (MarketState, DecisionSynthesis, AgentContract, etc.)
├── 📄 index.html                        # HTML entry point
├── 📄 vite.config.ts                    # Vite build configuration
├── 📄 tsconfig.json                     # TypeScript configuration
├── 📄 package.json                      # Dependencies and scripts
├── 📄 metadata.json                     # System metadata (version, description)
├── 📄 CHANGELOG.md                      # Version history and release notes
│
├── 📂 components/                       # React UI components
│   ├── 📄 Launchpad.tsx                 # Application launcher
│   ├── 📄 TradingTerminalWindow.tsx     # Trading terminal with charts
│   ├── 📄 MarketWindow.tsx              # Market data dashboard
│   ├── 📄 PortfolioWindow.tsx           # Portfolio management
│   ├── 📄 ResearchAgentWindow.tsx       # Research intelligence console
│   ├── 📄 KnowledgeBaseWindow.tsx       # Knowledge base browser
│   ├── 📄 BrowserWindow.tsx             # Integrated web browser
│   ├── 📄 NexusWindow.tsx              # Quantum Nexus visualization
│   ├── 📄 SwarmConfigModal.tsx          # Swarm agent configuration
│   ├── 📄 SystemArchitecture.tsx        # Architecture diagram
│   ├── 📄 AgentHud.tsx                  # Agent HUD display
│   ├── 📄 ControlCenter.tsx             # System control panel
│   ├── 📄 OmniBar.tsx                   # Universal command bar
│   ├── 📄 Taskbar.tsx                   # Dock/taskbar
│   ├── 📄 WindowFrame.tsx              # Draggable window container
│   ├── 📄 ChatMessage.tsx              # Chat message component
│   ├── 📄 InputArea.tsx                # Message input area
│   ├── 📄 ArtifactWindow.tsx           # Artifact display window
│   ├── 📄 Avatar.tsx                   # User avatar component
│   ├── 📄 RealTimeChart.tsx            # Real-time chart component
│   ├── 📄 SystemUpdater.tsx            # System update checker
│   └── 📄 Icons.tsx                    # SVG icon library
│
├── 📂 services/                         # Core business logic and engines
│   ├── 📄 strategy_engine.ts           # Strategy evaluation (SMC, S/R, Retail TA)
│   ├── 📄 quantum_engine.ts            # Pressure normalization & decision synthesis
│   ├── 📄 decision_synthesis_engine.ts  # Decision table & synthesis logic
│   ├── 📄 pressure_normalization_engine.ts # Sensor-to-pressure compilation
│   ├── 📄 market_state_engine.ts       # Market regime detection (Layer 1)
│   ├── 📄 entry_risk_engine.ts         # Entry geometry & risk calculation
│   ├── 📄 smc_agent.ts                # Smart Money Concepts sensor
│   ├── 📄 news_sentinel.ts             # News & macro event classification
│   ├── 📄 flow_agent.ts               # Institutional flow tracking
│   ├── 📄 quant_scanner.ts            # Quantitative momentum scanner
│   ├── 📄 math_engine.ts              # Pure mathematical indicators
│   ├── 📄 ml_engine.ts                # Machine learning utilities
│   ├── 📄 backtest_engine.ts          # Backtesting with execution reality
│   ├── 📄 strategy_lifecycle.ts        # Darwinian strategy management
│   ├── 📄 audit_logger.ts             # Full audit trail system
│   ├── 📄 autoswitch.ts               # API failover engine
│   ├── 📄 research_agent.ts           # Autonomous research harvester
│   ├── 📄 knowledge_base.ts           # Persistent knowledge storage
│   ├── 📄 browser_core.ts             # Browser navigation controller
│   ├── 📄 llm_router.ts              # Multi-LLM routing engine
│   ├── 📄 gemini.ts                   # Google Gemini AI integration
│   ├── 📄 market.ts                   # Market data service (unified API)
│   ├── 📄 risk_management.ts          # Risk Guardian enforcement
│   ├── 📄 correlation_monitor.ts      # Asset correlation tracking
│   ├── 📄 memory_manager.ts           # Session memory management
│   ├── 📄 storage_manager.ts          # Hybrid storage orchestration
│   ├── 📄 storage_adapter.ts          # Storage adapter pattern
│   ├── 📄 file_system.ts             # Browser-based file system
│   ├── 📄 drive.ts                   # Virtual drive management
│   ├── 📄 adaptive_layout.ts          # Responsive layout engine
│   ├── 📄 evolution_monitor.ts        # Strategy evolution tracking
│   ├── 📄 backup_service.ts           # System backup & restore
│   └── 📄 desktop_intelligence.ts     # Desktop AI integration
│
└── 📂 docs/                            # Documentation
    ├── 📄 ARCHITECTURE.md              # System architecture reference
    ├── 📄 BLUEPRINT.md                 # Design blueprint
    ├── 📄 BUILD_PLAN.md               # Build roadmap
    ├── 📄 EVOLUTION_MANIFEST.md       # Strategy evolution philosophy
    ├── 📄 SERVICES_GUIDE.md           # Services documentation
    ├── 📄 STORAGE.md                  # Storage architecture
    ├── 📄 SYSTEM_AUDIT_LOG.md         # System audit reference
    └── 📄 USER_GUIDE.md              # User guide
```

---

## 🤝 Contributing

We welcome contributors from around the world! 🌎 Quant Nanggroe AI is an ambitious project that sits at the intersection of quantitative finance, artificial intelligence, and systems engineering. Whether you're a seasoned quant developer, a React/TypeScript specialist, a machine learning researcher, or simply someone passionate about building intelligent trading systems — there's a place for you here.

### How to Contribute

1. **Fork** the repository at [https://github.com/mulkymalikuldhrs/Quant-Nanggroe-AI](https://github.com/mulkymalikuldhrs/Quant-Nanggroe-AI)
2. **Create** a feature branch: `git checkout -b feature/your-feature-name`
3. **Commit** your changes with clear, descriptive messages
4. **Push** to your fork: `git push origin feature/your-feature-name`
5. **Open** a Pull Request with a detailed description of your changes

### Areas We Need Help With

- 🧪 **Testing** — Unit tests, integration tests, and end-to-end testing for all engines
- 📊 **Indicators** — Additional technical indicators for the MathEngine (Ichimoku, Fibonacci, Elliott Wave)
- 🔌 **Data Providers** — New API integrations (Yahoo Finance, CoinGecko, TradingView)
- 🎨 **UI/UX** — Component improvements, accessibility, mobile responsiveness
- 📖 **Documentation** — API docs, tutorials, and examples
- 🌐 **Internationalization** — Translations and localization support
- 🏗️ **Cloud Deployment** — Docker, Kubernetes, and cloud-native deployment configurations

### Development Guidelines

- All TypeScript code must pass strict type checking (`strict: true`)
- Follow the existing project structure and naming conventions
- Every new service must include audit logging via `AuditLogger`
- All financial calculations must be deterministic and testable
- UI components must support both light and dark themes

### Contact

For questions, suggestions, or collaboration inquiries, reach out to:

[![Email](https://img.shields.io/badge/Email-mulkymalikuldhaher@email.com-EA4335?style=flat-square&logo=gmail&logoColor=white)](mailto:mulkymalikuldhaher@email.com)
[![GitHub](https://img.shields.io/badge/GitHub-mulkymalikuldhrs-181717?style=flat-square&logo=github&logoColor=white)](https://github.com/mulkymalikuldhrs)

---

## 🔗 Related Projects

| Project | Description | Link |
|---|---|---|
| **HermesQuantOS** | Unified Quantitative Intelligence Ecosystem — the parent project integrating Quant Nanggroe AI with backend services | [https://github.com/mulkymalikuldhrs/HermesQuantOS](https://github.com/mulkymalikuldhrs/HermesQuantOS) |

---

## 📜 License

This project is licensed under the MIT License. See the [LICENSE](./LICENSE) file for details.

---

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:0D9488,50:065F46,100:020205&height=120&section=footer" width="100%" />
</p>

<p align="center">
  <strong>&copy; 2026 Quant Nanggroe AI</strong><br/>
  Built with 💎 by <a href="https://github.com/mulkymalikuldhrs">Mulky Malikul Dhaher</a><br/>
  <em>Waiting for Contributors from Around the World 🌎</em>
</p>
