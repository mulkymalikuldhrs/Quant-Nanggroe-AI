# AI Agent Frameworks untuk Trading & Finance — Laporan Lengkap

**Dikompilasi:** 19 Juli 2026  
**Metode:** GitHub API, browser, Hermes skill inventory  
**Note:** Web search (Firecrawl) tidak tersedia karena billing issue — data dikumpulkan via GitHub API dan ekstraksi langsung.

---

## Ringkasan

| # | Framework / Tool | Stars | Tipe | Finance-Specific |
|---|---|---|---|---|
| 1 | **AutoGPT** | 185k+ | General Agent Platform | ❌ (generic, bisa diadaptasi) |
| 2 | **CrewAI** | 55k+ | Multi-Agent Orchestration | ⚠️ (punya stock analysis contoh) |
| 3 | **LangGraph (LangChain)** | 37k+ | Agent Orchestration | ⚠️ (punya trading use case docs) |
| 4 | **Microsoft AutoGen** | 59k+ | Multi-Agent Conversation | ❌ (generic) |
| 5 | **BabyAGI** | 22k+ | Task Planning Agent | ❌ (generic) |
| 6 | **FinRL (AI4Finance)** | ~17k+ | RL Trading Agents | ✅ |
| 7 | **FinGPT (AI4Finance)** | ~13k+ | Financial LLM | ✅ |
| 8 | **Microsoft Qlib** | 45k+ | AI Quant Platform | ✅ |
| 9 | **AI Hedge Fund (virattt)** | 62k+ | Multi-Agent Stock Analysis | ✅ |
| 10 | **Freqtrade** | 32k+ | Crypto Trading Bot | ✅ |
| 11 | **TradingAgents** | 2.4k+ | Multi-Agent Trading | ✅ |
| 12 | **Swapper Toolkit** | 827 | DeFi Agent Toolkit | ✅ |
| 13 | **RD-Agent (Microsoft)** | ~3k+ | Auto Strategy R&D | ✅ |
| 14 | **Vibe-Trading** | ~2k+ | Multi-Agent Trading Research | ✅ |
| 15 | **Hidden-Regime** | ~1k+ | HMM Market Regime MCP | ✅ |
| 16 | **Hermes Vibe-Trading Plugin** | — | Hermes Plugin | ✅ |
| 17 | **Hermes Stock Research Plugin** | — | Hermes Plugin/Skill | ✅ |
| 18 | **Hermes Autonomous Trading OS** | — | Hermes Skill Suite | ✅ |
| 19 | **Hermes Quant Trading (MCP-based)** | — | Hermes Skill | ✅ |
| 20 | **TradingView MCP** | ~500+ | MCP Server (Market Data) | ✅ |
| 21 | **MetaTrader 5 MCP** | ~500+ | MCP Server (Execution) | ✅ |
| 22 | **CCXT MCP** | — | MCP Server (Crypto Exchange) | ✅ |
| 23+ | **Hermes Research Skills (30+)** | — | Hermes Skills | ✅ |

---

## A. GENERAL AGENT FRAMEWORKS (Bisa Diadaptasi untuk Finance)

### 1. AutoGPT
- **URL:** https://github.com/Significant-Gravitas/AutoGPT
- **Stars:** 185,000+ | **Stack:** Python
- **Deskripsi:** Platform open-source untuk membangun, deploy, dan menjalankan AI agents. Platform cloud-hosted dengan visual builder, AutoPilot (chat-to-agent), marketplace.
- **Integrasi ke Pipeline Hedge Fund:**
  - Bisa dibuat agent khusus untuk trading via Marketplace agents
  - REST API untuk trigger agent secara schedule
  - Self-host option: `docker compose up`
  - Agent bisa diberi tools: web search, data analysis, API calls
  - **Cara:** Buat agent di platform.agpt.co → deskripsikan tugas trading → AutoGPT build agent → schedule tiap hari
  - **Limitation:** Tidak finance-specific — perlu prompt engineering untuk trading logic

### 2. CrewAI
- **URL:** https://github.com/crewAIInc/crewAI
- **Stars:** 55,738 | **Stack:** Python
- **Deskripsi:** Framework multi-agent orchestration dengan role-based agents, task delegation, dan collaborative intelligence. Juga punya Flows untuk event-driven workflows.
- **Integrasi ke Pipeline Hedge Fund:**
  - **Stock Analysis Example (built-in):** CrewAI punya contoh `stock_analysis` — Analyst Agent + Trader Agent bekerja sama
  - Bikin Crew khusus: `DataAgent → SignalAgent → RiskAgent → ExecutionAgent`
  - Bisa integrasi dengan tools: `yfinance`, `ccxt`, `MetaTrader5`, API broker
  - **Multi-agent debate:** Agents dengan role berbeda (Buffett, Graham, Taleb) berdebat soal posisi
  - **Cara:** `pip install crewai` → definisikan Agent roles → beri tools → `Crew(kickoff())` → hasil sinyal trading
  - **Contoh pipeline:**
    ```python
    researcher = Agent(role='Market Analyst', tools=[yfinance_tool])
    trader = Agent(role='Risk-Aware Trader')
    task = Task(description='Analisa BTC dan rekomendasi', agent=researcher)
    crew = Crew(agents=[researcher, trader], tasks=[task])
    result = crew.kickoff()
    ```

### 3. LangGraph (LangChain)
- **URL:** https://github.com/langchain-ai/langgraph
- **Stars:** 37,566 | **Stack:** Python / TypeScript
- **Deskripsi:** Low-level orchestration framework untuk stateful agents dengan durable execution, human-in-the-loop, comprehensive memory, debugging via LangSmith.
- **Integrasi ke Pipeline Hedge Fund:**
  - **Trading Use Case (official):** LangChain docs punya trading use case — `python.langchain.com/docs/use_cases/trading/`
  - **Stateful agents:** Agent bisa maintain portfolio state, order history, posisi terbuka
  - **Durable execution:** Agent survive restart/crash — penting untuk 24/7 trading
  - **Human-in-the-loop:** Setiap order butuh approval manusia sebelum eksekusi
  - **Cara:** `pip install langgraph` → `StateGraph` → nodes: `analyze → decide → execute → monitor` → `compile()` → stream execution
  - **Contoh pipeline:**
    ```python
    from langgraph.graph import StateGraph
    graph = StateGraph(TradingState)
    graph.add_node("analyze", analyze_market)
    graph.add_node("decide", make_decision)
    graph.add_node("execute", place_order)
    graph.set_entry_point("analyze")
    graph.add_edge("analyze", "decide")
    graph.add_conditional_edges("decide", should_execute, {True: "execute", False: "monitor"})
    ```

### 4. Microsoft AutoGen
- **URL:** https://github.com/microsoft/autogen
- **Stars:** 59,811 | **Stack:** Python
- **Deskripsi:** Programming framework untuk agentic AI — multi-agent conversations, code generation, tool use. Diskontinu untuk v0.1.x — v0.8+ adalah versi terbaru.
- **Integrasi ke Pipeline Hedge Fund:**
  - **Multi-agent debate:** Agents saling chat untuk analisa saham/finance
  - **Code generation:** Agent bisa generate backtest code, strategy code
  - **Tool integration:** Bisa dikasih tools finance (yfinance, pandas, numpy)
  - **Cara:** `pip install autogen-agentchat` → `AssistantAgent` + `UserProxyAgent` → beri tools finance → `initiate_chat()`
  - **Contoh:** Bikin agents: `FundamentalsAnalyst`, `TechnicalAnalyst`, `RiskManager` → mereka chat sampai konsensus → output trading decision

### 5. BabyAGI
- **URL:** https://github.com/yoheinakajima/babyagi
- **Stars:** 22,335 | **Stack:** Python
- **Deskripsi:** Experimental framework untuk self-building autonomous agent. Versi baru menggunakan function-based framework (functionz) untuk menyimpan dan mengeksekusi functions dari database.
- **Integrasi ke Pipeline Hedge Fund:**
  - **Task-driven:** BabyAGI bisa diberi task "analisa market tiap jam" → self-create subtasks
  - **Function registry:** Register function trading, backtest, analisa → biarkan agent panggil sesuai kebutuhan
  - **Dashboard:** Built-in dashboard untuk monitoring
  - **Cara:** `pip install babyagi` → register functions trading → `babyagi.create_app()` → task loop
  - **Limitation:** Experimental — tidak untuk production. Lebih cocok untuk prototyping ide agent workflow

---

## B. FINANCE-SPECIFIC AGENT FRAMEWORKS

### 6. FinRL — Deep Reinforcement Learning untuk Trading
- **URL:** https://github.com/AI4Finance-Foundation/FinRL
- **Stars:** ~17,000+ | **Stack:** Python (PyTorch, Stable-Baselines3)
- **Deskripsi:** Framework Deep RL untuk financial trading — menyediakan environment trading (Stock, Crypto, Forex, Portfolio), agent RL (PPO, DQN, A2C, SAC, TD3), dan backtesting.
- **Integrasi ke Pipeline:**
  - **Library:** `pip install finrl`
  - **Cara:** `StockTradingEnv` → `PPO` agent → `train()` → `test()` → `trade()`
  - **Pipeline:** Data (yfinance) → Feature Engineering → RL Environment → DRL Agent → Trade Signal
  - **Output:** Agent PPO yang sudah trained bisa kasih sinyal BUY/SELL/hold
  - **Versi baru:** FinRL-X (modular architecture, arXiv:2603.21330)
  - **Keterbatasan:** Butuh GPU untuk training; RL agent perlu waktu training berminggu-minggu

### 7. FinGPT — Financial Large Language Model
- **URL:** https://github.com/AI4Finance-Foundation/FinGPT
- **Stars:** ~13,000+ | **Stack:** Python
- **Deskripsi:** Open-source LLM untuk finance — sentiment analysis, financial report summarization, stock movement prediction, financial Q&A. Fine-tuning di data finansial.
- **Integrasi ke Pipeline:**
  - **Data pipeline:** Fetch financial news → FinGPT sentiment → signal generator
  - **Cara:** Load model FinGPT → prompt untuk analisa earnings call / SEC filing → ekstrak sentiment score
  - **Bisa jalan sebagai:** Microservice REST API yang dipanggil agent framework (CrewAI, LangGraph)
  - **Use case:** Sentiment analysis dari berita → input ke RL agent → trading decision

### 8. Microsoft Qlib — AI Quant Platform
- **URL:** https://github.com/microsoft/qlib
- **Stars:** 45,000+ | **Stack:** Python
- **Deskripsi:** Platform AI untuk quantitative investment — end-to-end dari data processing, factor mining, model training, backtesting, portfolio optimization, execution.
- **Integrasi ke Pipeline:**
  - **Full pipeline:** Data → Alpha Factors → ML Model → Portfolio → Execution
  - **Model support:** LSTM, GRU, Transformer, GATs, TabNet
  - **Cara:** `pip install qlib` → `qlib.init()` → download data → train model → `backtest()` → report
  - **Untuk agent:** Qlib model output (predicted returns) bisa jadi signal input untuk agent pipeline
  - **Portfolio optimizer:** Built-in risk parity, mean-variance, equal-weight optimization
  - **Status:** Cloned di `E:/qlib/` (Dhaher Labs setup)

### 9. AI Hedge Fund (virattt) — Multi-Agent Stock Analysis
- **URL:** https://github.com/virattt/ai-hedge-fund
- **Stars:** 62,000+ | **Stack:** Python
- **Deskripsi:** Multi-agent hedge fund dengan 15 famous investor agents (Buffett, Graham, Munger, Taleb, Lynch, dll) + Valuation, Fundamentals, Tech, Sentiment agents + Risk Manager + Portfolio Manager. Ada backtester, CLI, Web UI.
- **Integrasi ke Pipeline:**
  - **Cara:** `git clone` → pip install → `python src/main.py --ticker AAPL`
  - **Output:** BUY/SELL/HOLD dengan reasoning dari setiap agent
  - **MCP Server (untuk Hermes):** Ada `mcp_server.py` yang expose tools: `analyze_ticker`, `backtest_strategy`, `multi_agent_debate`
  - **15 agents debate:** Setiap agent vote → weighted consensus → final decision
  - **Stock adapter:** Support `symbol.JK` untuk saham Indonesia via yfinance
  - **Status:** Cloned di `E:/ai-hedge-fund/`, MCP server tersedia

### 10. Freqtrade — Crypto Trading Bot Framework
- **URL:** https://github.com/freqtrade/freqtrade
- **Stars:** 32,000+ | **Stack:** Python
- **Deskripsi:** Framework open-source untuk crypto trading bot — backtesting, live trading, Web UI, 100+ exchange via ccxt, strategi Python custom, stop loss / TP / trailing.
- **Integrasi ke Pipeline:**
  - **MCP Server:** `kukapay/freqtrade-mcp` expose 17 tools via MCP: `fetch_market_data`, `fetch_profit`, `place_trade`, `start_bot`, dll
  - **Cara:** Freqtrade standalone untuk execution; MCP server untuk query/trade dari agent
  - **Pipeline:** TradingView MCP scan → AIHF signal → Freqtrade MCP execute
  - **Status:** Cloned di `E:/freqtrade/` + `E:/freqtrade-mcp/`
  - **Config credentials:** `FREQTRADE_API_URL`, `FREQTRADE_USERNAME`, `FREQTRADE_PASSWORD`

### 11. TradingAgents — Multi-Agent Trading Framework
- **URL:** https://github.com/simonlin1212/TradingAgents-astock (A-share) | https://github.com/TradingGoose/TradingGoose.github.io
- **Stars:** 2,477 (A-stock variant)
- **Deskripsi:** Multi-agent investment research framework — 7 AI analysts bull/bear debate, risk assessment. Adaptasi untuk A-share (China) market.
- **Integrasi ke Pipeline:**
  - **Arsitektur:** 7 agent analysts → debate → consensus → risk check → trade decision
  - **Data sources:** A-share data (top traders, restricted shares)
  - **Cara:** `pip install tradingagents` → konfigurasi agents → `tradingagents run --symbol BTC`
  - **Limitation:** Heavy langchain dependencies; perlu `env -u PYTHONPATH` di Windows (pydantic version conflict)

### 12. Swapper Finance Toolkit — DeFi Agent Toolkit
- **URL:** https://github.com/swapperfinance/swapper-toolkit
- **Stars:** 827 | **Stack:** Node.js / MCP
- **Deskripsi:** DeFi toolkit untuk AI agents — deposit funds, swap tokens, manage crypto wallets. Works with Claude Code, Cursor, CrewAI, AutoGPT. Powered by Chainlink CRE, CCIP, Mastercard.
- **Integrasi ke Pipeline:**
  - **Agent Skill:** `npx skills add swapperfinance/swapper-toolkit`
  - **Tools:** `/swapper-deposit` (deposit/bridge funds), `/swapper-trade` (token swap), `/swapper-wallet` (wallet management)
  - **Support:** Ethereum, Base, Arbitrum, Optimism, Polygon, Solana, BNB Chain, Avalanche
  - **Cara:** Install via npx → agent triggers tool → deposit/trade link generated
  - **Fiat on-ramp:** Mastercard, Visa, Apple Pay, Google Pay (170+ countries)

### 13. RD-Agent (Microsoft) — Auto R&D Agent
- **URL:** https://github.com/microsoft/RD-Agent
- **Stars:** ~3,000+ | **Stack:** Python
- **Deskripsi:** Automated R&D agent untuk quantitative finance — secara otomatis menghasilkan faktor strategi baru, backtest, validasi, dan iterasi. Paper: arXiv:2409.06289.
- **Integrasi ke Pipeline:**
  - **Cara:** `pip install rd-agent` → define search space → agent generate strategies → validate → report
  - **Output:** Faktor strategi baru + backtest results
  - **Pipeline:** RD-Agent generate → Qlib validate → Freqtrade execute
  - **Status:** Cloned di `E:/RD-Agent/`

### 14. Vibe-Trading — Multi-Agent Trading Research
- **URL:** https://github.com/HKUDS/Vibe-Trading
- **Stars:** ~2,000+ | **Stack:** Python
- **Deskripsi:** Multi-agent swarm untuk trading research — agents dengan roles berbeda untuk market analysis, fund flow, news, risk assessment.
- **Integrasi ke Pipeline:**
  - **REST API:** Berjalan di `localhost:8899` dengan endpoints: `POST /v1/chat`, `POST /swarm/run`
  - **Cara:** Start API server → agent framework panggil API untuk research task
  - **Hermes Plugin:** Tersedia plugin Hermes Agent (lihat bagian Hermes di bawah)
  - **Tools:** Finance research tools, A-share analysis via AKShare

### 15. Hidden-Regime — HMM Market Regime MCP
- **URL:** https://github.com/hidden-regime/hidden-regime
- **Stars:** ~1,000+ | **Stack:** Python
- **Deskripsi:** Market regime detection via Hidden Markov Model — MCP server untuk expose regime detection sebagai tool agent.
- **Integrasi ke Pipeline:**
  - **MCP Server:** 3 tools — regime detection, transition probability, regime stats
  - **Cara:** `pip install hidden-regime` → register MCP → agent call `detect_regime(symbol)`
  - **Output:** Regime (Bull/Bear/Sideways/High Vol) + confidence score
  - **Pipeline:** Hidden-Regime → regime-aware position sizing → execution
  - **Status:** Cloned di `E:/hidden-regime/`
  - **Note:** `pip install` mungkin gagal (setuptools-scm issue) — fallback: `sys.path.insert(0, source_dir)`

---

## C. HERMES AGENT PLUGINS & SKILLS UNTUK FINANCE

### 16. Hermes Vibe-Trading Plugin
- **URL:** https://github.com/sjiangtao2024/hermes-vibe-trading-plugin
- **Tipe:** Hermes Plugin (custom)
- **Deskripsi:** Hermes plugin yang bridge Hermes Agent ke Vibe-Trading API service. Forward natural-language finance research requests ke Vibe-Trading Agent, return report ke chat channel.
- **Tools yang disediakan:**
  - `vibe_ask` — General finance/trading research question
  - `vibe_ask_ashare` — A-share research (AKShare-first)
  - `vibe_health` — API health check
  - `vibe_list_skills` — List finance skills
  - `vibe_list_swarm_presets` — List swarm presets
  - `vibe_run_swarm` — Start multi-agent swarm run
  - `vibe_get_swarm_run` / `vibe_create_session` / `vibe_send_message` — Session management
- **Instalasi:**
  ```bash
  mkdir -p ~/.hermes/plugins
  cp -R plugins/vibe-trading ~/.hermes/plugins/vibe-trading
  # Enable in config.yaml:
  # plugins:
  #   enabled:
  #     - vibe-trading
  export VIBE_TRADING_BASE_URL="http://localhost:8899"
  ```

### 17. Hermes Explainable Stock Research Plugin
- **URL:** https://github.com/sehhong318/hermes-stock-research-plugin
- **Tipe:** Hermes Plugin + Skill
- **Deskripsi:** Hermes skill untuk designing dan verifying non-personalized stock research dashboards dengan transparent scoring.
- **Fitur:**
  - Explicit research horizon, risk profile, universe
  - Deterministic screen scores, source freshness validation
  - Technical evidence, contextual evidence, downside risks separation
  - Adversarial tests, visual review, deployment gates
- **Instalasi:**
  ```bash
  hermes plugins install https://github.com/sehhong318/hermes-stock-research-plugin.git
  hermes plugins enable stock-research
  # Load skill:
  /skill stock-research:explainable-market-research-dashboards
  ```

### 18. Hermes Autonomous Trading Ecosystem Skill
- **Kategori:** `dhaher-labs` | **File:** `dhaher-labs/autonomous-trading-ecosystem/SKILL.md`
- **Deskripsi:** Skill yang mendefinisikan pipeline lengkap hedge fund — Data → Signal → Risk → Execution → Monitor. Mencakup ecosystem discovery, pipeline architecture, broker connectors.
- **Pipeline yang di-cover:**
  ```
  Market Regime Detector ← Hidden-Regime MCP (HMM)
      ↓
  Data Layer ← TradingView MCP · Qlib data · Yahoo
      ↓
  Signal Layer ← AIHF · RD-Agent · AgentQuant · FinRL
      ↓
  Portfolio Manager ← Qlib portfolio · risk parity · drawdown
      ↓
  Execution Layer ← MetaTrader-MCP → broker · CCXT MCP → crypto
      ↓
  Monitor ← Qlib dashboard · P&L · trade journal
  ```
- **Integrasi:** Langsung pakai dari Hermes session — `/skill autonomous-trading-ecosystem`

### 19. Hermes Quant Trading Skill (MCP-based)
- **Kategori:** `mlops` | **File:** `mlops/quant-trading/SKILL.md`
- **Deskripsi:** Tools dan workflows untuk quant trading menggunakan TradingView MCP (35 tools) + MetaTrader 5 MCP (22 tools) + Freqtrade MCP (17 tools) + AIHF MCP (3 tools).
- **Tools MCP yang digunakan:**
  - **TradingView MCP:** Market scan, technical analysis, backtest 9 strategies, screener
  - **MetaTrader 5 MCP:** Account info, market data, positions, pending orders, **execution** (place market/pending order, close positions, modify SL/TP)
  - **Freqtrade MCP:** Crypto perp/futures execution — fetch data, place trade, start/stop bot
  - **AIHF MCP:** 15-agent stock analysis, backtest, multi-agent debate
- **Integrasi:**
  ```bash
  hermes mcp add tradingview --command tradingview-mcp --args "stdio"
  hermes mcp add metatrader --command custom-mt5-mcp.py --args "--login ... --server ..."
  # Load skill:
  /skill quant-trading
  ```

### 20. Hermes Quant Finance Audit Skill
- **Kategori:** `software-development` | **File:** `software-development/quant-finance-audit/SKILL.md`
- **Deskripsi:** Domain-specific audit methodology untuk quant finance / algorithmic trading codebases. 55+ pitfall patterns, layer-by-layer checklists untuk backtest engines, risk models, execution.
- **Use case:** Audit kode Quant-Nanggroe / hedge fund engine untuk production readiness

### 21. Hermes Quant Engineering OS
- **Kategori:** `software-development` | **File:** `software-development/quant-engineering-os/SKILL.md`
- **Deskripsi:** Complete Quant Hedge Fund organization — 15 roles, 10 phases, self-evolution engine, quality gates. Orbital command untuk Quant-Nanggroe-AI project.

### 22. Hermes Research Skills (30+ Skills untuk Finance Data)
Semua skill di kategori `research` langsung available di Hermes:

| Skill | Fungsi |
|-------|--------|
| `fred-data` | FRED economic data (GDP, inflation, interest rates) |
| `trading-economics` | 20M+ economic indicators for 196 countries |
| `barchart` | Futures, options, forex, stocks data |
| `bloomberg-terminal` | Bloomberg function equivalents |
| `cme-group` | CME futures/options, FedWatch |
| `forexfactory` | Economic calendar |
| `coinglass` | Crypto derivatives analytics |
| `dexscreener` | DEX trading data |
| `birdeye` | On-chain token analytics |
| `gmgn-ai` | Smart money tracking, whale wallets |
| `options-flow` | Unusual options activity |
| `fear-greed-index` | Market sentiment |
| `onchain-analytics` | Blockchain data analysis |
| `polymarket` | Prediction markets |
| `quant-science` | Statistical arbitrage, factor investing |
| `quantitative-analysis` | Risk metrics, portfolio optimization |
| `hedge-fund-operations` | Risk frameworks, compliance |
| `correlation-matrix` | Cross-asset correlations |
| `currency-strength-meter` | Forex strength |
| `liquidity-heatmap` | Order book depth |
| `orderflow-analysis` | Bid/ask volume, delta |
| `market-structure` | Order blocks, FVG, liquidity sweeps |
| `footprint-charts` | Volume at price level |
| `go-charting` | Advanced crypto charting |
| `broker-summary` | Broker position distribution |
| `commitment-of-traders` | CFTC COT data |
| `hawkish-dovish` | Central bank sentiment |
| `worldmonitor-app` | Global economic monitoring |
| `fincept-terminal` | Multi-asset trading terminal |
| `web-scraping-ingest` | Custom data scraping |

---

## D. MCP SERVERS UNTUK TRADING (Kompatibel dengan Hermes Agent)

| MCP Server | Untuk | Tools | URL |
|---|---|---|---|
| **TradingView MCP** | Market data, TA, screener, backtest | 35 | github.com/atilaahmettaner/tradingview-mcp |
| **MetaTrader-MCP** (ariadng) | MT5 broker execution | 22+ | github.com/ariadng/metatrader-mcp-server |
| **Freqtrade MCP** (kukapay) | Crypto perp/futures | 17 | github.com/kukapay/freqtrade-mcp |
| **AIHF MCP** (virattt) | 15-agent stock analysis | 3 | github.com/virattt/ai-hedge-fund (mcp_server.py) |
| **CCXT MCP** | 100+ crypto exchanges | ~10 | github.com/lazy-dinosaur/ccxt-mcp |
| **Alpaca MCP** | US stocks/options/crypto | ~10 | github.com/alpacahq/alpaca-mcp-server |
| **IBKR MCP** | Interactive Brokers | ~10 | github.com/gpolydatas/ibkr-mcp-server |
| **Hidden-Regime MCP** | Market regime detection (HMM) | 3 | github.com/hidden-regime/hidden-regime |

---

## E. MATRIKS INTEGRASI: Framework → Pipeline Hedge Fund

| Framework | Data Layer | Signal Layer | Risk Layer | Execution | Monitor | Cocok untuk |
|---|---|---|---|---|---|---|
| **CrewAI** | ✅ (tools) | ✅ (agents) | ⚠️ (manual) | ⚠️ (via tools) | ❌ | Multi-agent signal generation |
| **LangGraph** | ✅ | ✅ | ✅ (state) | ⚠️ (via nodes) | ✅ (LangSmith) | Stateful trading agent workflow |
| **AutoGen** | ✅ | ✅ (debate) | ⚠️ | ⚠️ | ❌ | Agent debate & consensus |
| **FinRL** | ✅ | ✅ (RL) | ❌ | ❌ | ❌ | RL trading signal generation |
| **FinGPT** | ✅ (news) | ✅ (sentiment) | ❌ | ❌ | ❌ | Sentiment signal |
| **Qlib** | ✅ | ✅ (AI) | ✅ (portfolio) | ❌ | ✅ | End-to-end quant research |
| **AI Hedge Fund** | ✅ | ✅ (15 agents) | ✅ | ❌ | ❌ | Stock analysis |
| **Freqtrade** | ✅ | ✅ (strategies) | ✅ (SL/TP) | ✅ (live) | ✅ (Web UI) | Crypto execution engine |
| **Vibe-Trading** | ✅ | ✅ (swarm) | ⚠️ | ❌ | ❌ | Multi-agent research |
| **Hermes + MCPs** | ✅ | ✅ | ✅ | ✅ | ✅ | **Full pipeline orchestration** |

---

## F. PRIORITAS INTEGRASI (untuk Hedge Fund Pipeline)

### Immediate (Week 1-2):
1. **Hermes Quant Trading Skill** — sudah terintegrasi dengan TV MCP + MT5 MCP
2. **AI Hedge Fund MCP** — 15 agents untuk stock analysis, panggil via Hermes
3. **TradingView MCP** — 35 tools market data & backtest
4. **Freqtrade MCP** — 17 tools crypto execution

### Short-term (Week 3-4):
5. **CrewAI + Finance Tools** — Crew khusus: Data → Signal → Risk → Execution
6. **LangGraph Trading Agent** — Stateful agent dengan human-in-the-loop
7. **Hidden-Regime MCP** — Market regime detection sebagai input sizing
8. **RD-Agent** — Auto generate faktor strategi baru

### Medium-term (Month 2):
9. **FinRL agent** — RL-based signal generator (butuh GPU)
10. **Qlib portfolio optimizer** — Risk parity dan portfolio optimization
11. **Microsoft AutoGen** — Multi-agent debate untuk konfirmasi sinyal

### Long-term (Month 3+):
12. **FinGPT** — Sentiment analysis pipeline
13. **Cross-exchange execution** — CCXT MCP untuk multi-exchange crypto
14. **Full autonomous pipeline** — Semua layer terintegrasi via Hermes cron

---

## G. NOTES & CONSTRAINTS

- **Windows compatibility:** Semua framework Python bisa jalan di Windows via MSYS/git-bash
- **Python version:** Gunakan Python 3.11 untuk kompatibilitas wheels (numpy, scipy, torch)
- **GPU requirement:** Hanya FinRL/RL agents yang butuh GPU — sisanya CPU-friendly
- **MT5 dependency:** Execution layer butuh MetaTrader 5 terminal berjalan di Windows
- **API keys needed:** Broker (MT5 login), Exchange (Binance/Bybit API key), FRED, NewsAPI, dll.
- **Firecrawl web search tidak tersedia** — penelitian ini dilakukan via GitHub API + browser langsung

---

*Report generated by Hermes Agent subagent — 19 July 2026*
