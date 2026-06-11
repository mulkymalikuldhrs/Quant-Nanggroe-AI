# 🛠️ SERVICES GUIDE: QUANT NANGGROE AI

This document provides a technical overview of the internal services that power the system.

---

## 👁️ SENSORS & AGENTS (Layer 2)

### `QuantScanner` (`services/quant_scanner.ts`)
- **Purpose**: Technical momentum and volatility analysis.
- **Logic**: Calculates ADX, RSI, SMA, and ATR. Outputs `TREND_STRENGTH` and `VOLATILITY_FACTOR`.

### `SMCAgent` (`services/smc_agent.ts`)
- **Purpose**: Smart Money Concepts (SMC) detection.
- **Logic**: Identifies Market Structure (BOS/CHoCH), Order Blocks (OB), and Fair Value Gaps (FVG).

### `NewsSentinel` (`services/news_sentinel.ts`)
- **Purpose**: Fundamental analysis.
- **Logic**: Scores macroeconomic news from Finnhub/AlphaVantage using a logarithmic decay function (older news has less impact).

### `FlowAgent` (`services/flow_agent.ts`)
- **Purpose**: Institutional order flow analysis.
- **Logic**: Tracks Whale alerts and COT (Commitment of Traders) reports.

---

## 🧠 CORE INTELLIGENCE

### `DecisionSynthesisEngine` (`services/decision_synthesis_engine.ts`)
- **Purpose**: Final decision logic.
- **Logic**: Compiles pressure variables into entry/exit coordinates.

### `PressureNormalizationEngine` (`services/pressure_normalization_engine.ts`)
- **Purpose**: Vector math.
- **Logic**: Normalizes diverse sensor outputs into a unified 0.0-1.0 scale.

### `MarketStateEngine` (`services/market_state_engine.ts`)
- **Purpose**: Regime detection.
- **Logic**: Determines if the current environment is safe for execution.

---

## 🛡️ RISK & GOVERNANCE

### `RiskManagement` (`services/risk_management.ts`)
- **Purpose**: Capital preservation.
- **Logic**: Position sizing, max drawdown enforcement, and equity protection.

### `CorrelationMonitor` (`services/correlation_monitor.ts`)
- **Purpose**: Portfolio diversity.
- **Logic**: Prevents over-exposure by calculating Pearson correlation between assets.

### `EntryRiskEngine` (`services/entry_risk_engine.ts`)
- **Purpose**: Pre-flight checks.
- **Logic**: Validates spread and slippage probability before signal dispatch.

---

## 💾 DATA & INFRASTRUCTURE

### `StorageManager` (`services/storage_manager.ts`)
- **Purpose**: Unified persistence.
- **Logic**: Manages adapters (IndexedDB, LocalStorage, Cloud) for data storage.

### `FileSystem` (`services/file_system.ts`)
- **Purpose**: Virtual file management.
- **Logic**: Provides a `BrowserFS` layer for the AI agents to "read/write" thoughts and logs.

### `BackupService` (`services/backup_service.ts`)
- **Purpose**: Data portability.
- **Logic**: Handles JSON serialization for system-wide state snapshots.

---

## 🧬 EVOLUTION & LEARNING

### `StrategyLifecycle` (`services/strategy_lifecycle.ts`)
- **Purpose**: Strategy management.
- **Logic**: Tracks the birth, incubation, and "killing" of quantitative strategies.

### `EvolutionMonitor` (`services/evolution_monitor.ts`)
- **Purpose**: Performance tracking.
- **Logic**: Monitors win-rate, profit-factor, and expectancy over time.

### `KnowledgeBase` (`services/knowledge_base.ts`)
- **Purpose**: Long-term memory.
- **Logic**: Graph-based storage for cross-correlated market insights.

---

© 2026 Quant Nanggroe AI | Services Guide v15.2.0

---

> **Contact:** Mulky Malikul Dhaher — [mulkymalikuldhaher@email.com](mailto:mulkymalikuldhaher@email.com)
>
> **Disclaimer:** This project is for Education Purpose only. Risiko apapun tidak kita tanggung. (We are not responsible for any risks or damages.)
