# 🏛️ SYSTEM ARCHITECTURE: QUANT NANGGROE AI
### **Version 15.2.0 | Multi-Agent Decision Intelligence OS**

Quant Nanggroe AI is an advanced **Decision Intelligence Operating System** designed for quantitative research in financial markets. It focuses on eliminating psychological bias and AI hallucinations by enforcing a **Deterministic Agent Execution** framework.

---

## 1. Core Philosophy: Deterministic Reasoning
Unlike standard AI assistants that provide subjective advice, this system treats Large Language Models (LLMs) as **Logical Reasoning Engines** constrained by rigid contracts. 
- **No Subjective Opinions**: AI agents are forbidden from providing "vibes-based" analysis.
- **Data Grounding**: All reasoning must be anchored in raw numerical data (Layer 0).
- **Pressure-Based Output**: Agents output normalized "Pressure" variables (0.0 - 1.0) rather than direct trade signals.

---

## 2. Operational Hierarchy (The Stack)

### **Layer 0: Contextual Neural Grounding (Data Foundation)**
The foundation of the system. It harvests real-time L1/L2 data from:
- **Binance / CoinCap** (Crypto)
- **AlphaVantage / Polygon / Finnhub** (Stocks/Forex/Macro)
This data serves as the "truth source" for all agents.

### **Layer 1: Market Regime Engine (The Gatekeeper)**
Determines the global market condition:
- `TRENDING_UP` / `TRENDING_DOWN`
- `RANGE_BOUND`
- `RISK_OFF` / `PANIC`
If the regime is unsuitable (e.g., extreme volatility or low liquidity), the system enters `NO_TRADE` mode to protect capital.

### **Layer 2: Multi-Agent Sensors (The Eyes)**
Specialized agents operate in parallel as numerical sensors:
1. **QuantScanner**: Technical momentum, trend strength (ADX), and volatility.
2. **SMCAgent**: Market Structure (BOS, CHoCH), Order Blocks, and Liquidity zones.
3. **NewsSentinel**: Macroeconomic impact scoring with logarithmic time decay.
4. **FlowAgent**: Institutional "Whale" flow and COT positioning.

### **Layer 3: Pressure Normalization Engine (The Compiler)**
Aggregates raw sensor outputs into two primary vectors:
- `BUY_PRESSURE` (0.0 - 1.0)
- `SELL_PRESSURE` (0.0 - 1.0)

### **Layer 4: Decision Synthesis Engine (The Judge)**
The final authority. It uses a **Decision Matrix** to generate compressed execution outputs:
- **Entry Point**
- **Hard Stop Loss**
- **Tiered Take Profits (TP1, TP2, TP3)**

---

## 3. Risk Guardian (The Constitution)
Risk management is hard-coded and independent of AI logic to prevent "reasoning around" safety rules:
1. **Kill-Switch**: Automatic system lock if daily drawdown exceeds 4%.
2. **Correlation Monitor**: Blocks execution if the correlation between active assets exceeds 0.70.
3. **Reality Simulation**: Backtesting accounts for Dynamic Spread, Slippage, and 100-500ms Latency.

---

## 4. Darwinian Strategy Evolution
The system monitors every strategy's performance. If a strategy's **Expectancy** becomes negative over a statistically significant sample size, it is marked as `KILLED`, and the system automatically shifts resources to higher-performing variants.

---

## 5. Hybrid Storage Architecture
The **StorageManager** uses an **Adapter Pattern** to manage data:
1. **IndexedDB (Primary)**: High-capacity local storage for knowledge bases and market history.
2. **LocalStorage**: Fast-access for UI preferences and session state.
3. **Local File Sync**: Full system state backup/restore via `.json` files.
4. **Cloud-Ready**: Prepared for Supabase/PostgreSQL integration.

---

© 2026 Quant Nanggroe AI | Technical Reference v15.2.0

---

> **Contact:** Mulky Malikul Dhaher — [mulkymalikuldhaher@email.com](mailto:mulkymalikuldhaher@email.com)
>
> **Disclaimer:** This project is for Education Purpose only. Risiko apapun tidak kita tanggung. (We are not responsible for any risks or damages.)
