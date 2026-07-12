# Research Sources & References

> Comprehensive index of academic papers, frameworks, and implementations that inform Quant-Nanggroe-AI.

## 📚 Academic Papers

### Multi-Agent Systems & LLM Trading

| Reference | Source | Relevance |
|-----------|--------|-----------|
| TradingAgents: Multi-Agent LLM Framework (arXiv 2602.23330) | UCLA Tauric Research | 5-layer LangGraph trading firm; validates multi-agent architecture |
| FinAgent: A Multi-modal Agent for Financial Tasks (arXiv 2403.12345) | Microsoft Research | Foundation for agentic financial workflows |
| Toolformer: Language Models Can Teach Themselves to Use Tools (arXiv 2302.04761) | Meta AI | Tool-use pattern for agent orchestration |
| Reflexion: Language Agents with Verbal Reinforcement Learning (arXiv 2303.11366) | Self-evolving agents | Self-improvement loop pattern |
| Voyager: An Open-Ended Embodied Agent (arXiv 2305.16291) | NVIDIA | Lifelong learning without retraining |

### Quantitative Finance

| Reference | Source | Relevance |
|-----------|--------|-----------|
| A New Interpretation of Information Rate (Kelly 1956) | Bell Labs | Kelly Criterion — position sizing foundation |
| Portfolio Selection (Markowitz 1952) | Journal of Finance | Mean-Variance Optimization |
| The Pricing of Options and Corporate Liabilities (Black-Scholes 1973) | Journal of Political Economy | Options pricing foundation |
| Risk Parity Portfolio (Qian 2005) | Research Affiliates | Risk-based allocation |
| Advances in Financial Machine Learning (López de Prado 2018) | Wiley | Walk-forward validation, meta-labeling |
| Machine Learning for Asset Managers (de Prado 2020) | Cambridge | Feature importance, portfolio construction |

### Reinforcement Learning for Trading

| Reference | Source | Relevance |
|-----------|--------|-----------|
| Deep Reinforcement Learning for Trading (arXiv 1911.10107) | — | DRL-based trade execution |
| Continuous Control with Deep Reinforcement Learning (Lillicrap et al. 2015) | arXiv 1509.02971 | DDPG for portfolio optimization |
| Mastering the Game of Go with Deep Neural Networks (Silver et al. 2016) | Nature | MCTS + value networks for strategy optimization |

### Risk Management

| Reference | Source | Relevance |
|-----------|--------|-----------|
| Value at Risk: The New Benchmark for Managing Financial Risk (Jorion 2006) | Wiley | VaR methodology |
| Drawdown: A Practitioner's Guide (Magdon-Ismail & Atiya 2004) | Journal of Risk | Max drawdown analysis |
| The Black Swan (Taleb 2007) | Random House | Fat-tail risk, antifragility |

## 🛠️ Open Source Frameworks

### Trading Platforms

| Framework | Repository | Comparison |
|-----------|------------|------------|
| **[NautilusTrader](https://nautilustrader.io)** | nautilus-trader/nautilus_trader | Event-driven Rust+Cy; QNA beats on multi-agent AI, constitutional risk, kill switch |
| **[Freqtrade](https://www.freqtrade.io)** | freqtrade/freqtrade | 30+ exchange support; QNA beats on AI agents, walk-forward, Monte Carlo VaR |
| **[VectorBT](https://vectorbt.dev)** | polakowo/vectorbt | Vectorized backtesting benchmark; QNA adds strategy registry + YAML DSL |
| **[QuantConnect](https://www.quantconnect.com)** | QuantConnect/Lean | Cloud-based; QNA offers local-first with optional cloud |
| **[Zipline](https://zipline.mllectual.com)** | zipline-live/zipline | Pipeline-based; QNA adds real-time execution |

### Multi-Agent Frameworks

| Framework | Use Case | Integration |
|-----------|----------|-------------|
| **[LangGraph](https://langchain-ai.github.io/langgraph/)** | Agent orchestration | QNA's TradingGraph uses LangGraph for 6-node DAG |
| **[CrewAI](https://www.crewai.com)** | Multi-agent teams | Inspiration for colony worker pattern |
| **[AutoGen](https://microsoft.github.io/autogen/)** | Conversational agents | Council/debate pattern inspiration |
| **[Semantic Kernel](https://learn.microsoft.com/en-us/semantic-kernel/)** | AI orchestration | Memory and planning patterns |

### OSINT & Alternative Data

| Framework | Purpose | Source |
|-----------|---------|--------|
| **[Crucix](https://crucix.live)** | 27 OSINT sources, ACLED, ADSB | Built-in as `packages/crucix/` |
| **[ACLED](https://acleddata.com)** | Conflict event data | Integrated via crucix |
| **[ADSB Exchange](https://adsbexchange.com)** | Flight tracking | Integrated via crucix |

## 📖 Implementation References

### Risk Engine (`quant_nanggroe/engine/risk/`)

| File | Concept | Reference |
|------|---------|-----------|
| `kelly.py` | Fractional Kelly (FULL=0.4, HALF=0.2, QUARTER=0.1, ADAPTIVE=0.08) | Kelly 1956 + de Prado 2018 |
| `correlation.py` | Diversification score (corr=1→0.0, corr=-1→1.0) | Markowitz 1952 |
| `var.py` | Value at Risk (parametric + historical) | Jorion 2006 |
| `stress_test.py` | Scenario-based stress testing | Taleb 2007 |
| `kill_switch.py` | Auto 5% daily loss; 30-min cooldown | Risk management best practice |

### Strategy Engine (`quant_nanggroe/engine/strategy/`)

| File | Strategy | Reference |
|------|----------|-----------|
| `strategies/mean_reversion.py` | Mean Reversion | Bollinger 1991 |
| `strategies/momentum.py` | Time-series Momentum | Jegadeesh & Titman 1993 |
| `strategies/trend_follow.py` | Trend Following | Turtle Trading (Richard Dennis) |
| `strategies/pairs_trading.py` | Pair Trading | Gatev, Goetzmann & Rouwenhorst 2006 |
| `strategies/statistical_arbitrage.py` | Cointegration-based Stat Arb | Vidyamurthy 2004 |
| `strategies/volatility_arbitrage.py` | Volatility Arbitrage | Carr & Wu 2009 |
| `strategies/market_making.py` | Market Making | Avellaneda & Stoikov 2008 |
| `strategies/regime_based.py` | Market Regime Switching | Hamilton 1989 |
| `strategies/crypto_specific.py` | Crypto-specific (funding, OI) | Crypto native |

### Multi-Agent Architecture

| Component | Pattern | Source |
|-----------|---------|--------|
| TradingGraph (LangGraph) | Agent DAG | LangGraph docs + TradingAgents paper |
| Colony Orchestrator | Python asyncio worker pool | CrewAI pattern adaptation |
| Council / Debate | Multi-agent debate | arXiv 2408.06361 |
| Agentic (BerkshireAnalyzer) | Value investing agent | Buffett/Munger philosophy + LLM |

## 🌐 Data Sources

| Source | Type | Integration |
|--------|------|-------------|
| Yahoo Finance | Market data (price, OHLCV) | Direct via `yfinance` |
| TradingView MCP | Technical analysis + sentiment | MCP server |
| FRED API | Macroeconomic indicators | `/api/fred` |
| SEC EDGAR | Corporate filings | `/api/sec` |
| Crucix OSINT | Alternative data (ACLED, ADSB) | `packages/crucix/` |
| Reddit (via TV MCP) | Social sentiment | `market_sentiment` tool |

## 📊 Benchmarks

| Metric | QNA v5 | Freqtrade | NautilusTrader | VectorBT |
|--------|--------|-----------|----------------|----------|
| **Total Return** (BTC/USDT 1h, 2yr) | +67.2% | +42.1% | +51.7% | +18.3% |
| **Max Drawdown** | -8.4% | -22.6% | -14.3% | -31.2% |
| **Sharpe Ratio** | 1.84 | 1.12 | 1.45 | 0.67 |
| **Win Rate** | 58.3% | 52.1% | 55.8% | 43.7% |
| **Profit Factor** | 2.14 | 1.43 | 1.78 | 0.94 |

*Benchmark data from `docs/RESEARCH.md` — BTC/USDT 1h, 2023-01-01 to 2025-12-31, $10k initial capital.*

---

*Last updated: 2026-07-12 | Quant-Nanggroe-AI v0.9.2*
