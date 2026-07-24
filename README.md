# Quant Nanggroe AI v5.1.0 — Autonomous Quantitative Hedge Fund

Autonomous quantitative hedge fund platform with multi-strategy execution, constitutional risk management, and self-evolving pipelines. Runs without human intervention across forex, crypto, and equities.

---

## Overview

Quant Nanggroe AI (QNA) is a production-grade quantitative hedge fund system. It combines institutional risk controls with AI-driven strategy evolution — strategies are automatically discovered, executed, evaluated, mutated, and promoted based on live performance. The system operates standalone or as part of the broader Dhaher Labs ecosystem.

---

## Architecture

```
qna.py (entry point)
├── engine/                  Core pipeline orchestration
│   ├── agentic/             Autonomous trading pipeline
│   ├── risk/                9-checkpoint constitutional risk gate
│   ├── strategies/          Active strategies + evolver + fine-tuner
│   ├── backtest/            Walk-forward, Monte Carlo, CPCV
│   ├── execution/           TWAP/VWAP order slicing
│   ├── factors/             Alpha factor library
│   ├── self_aware.py        Self-reflection on every run
│   ├── correction.py        Error recording and resolution
│   ├── registry.py          Auto-discovery component registry
│   └── standalone.py        Zero-dependency entry point
├── agents/                  7 AI agent personas
├── api/                     179 FastAPI endpoints
├── exchange/                6 broker integrations (MT5, CCXT, etc.)
├── dashboard/               React monitoring UI
└── tests/                   135+ test files (51 new in v5.1.0)
```

### Key Components

- **Autonomous Pipeline** — End-to-end trading loop: data → signal → risk check → execution → PnL tracking → self-evaluation → evolution
- **Risk Engine** — 9-checkpoint constitutional gate with daily/weekly loss vetoes, kill switch, position sizing limits, and TWAP/VWAP smart execution
- **Strategy Pipeline** — 152 auto-discovered strategies with walk-forward validated mutation, grid search fine-tuning, and accept/reject promotion gates
- **Correction Module** — Records errors, resolves them, and prevents recurrence through lesson-based learning
- **Self-Correct System** — Self-awareness reflection on every pipeline run, anomaly detection, and automated recovery
- **Correlation Monitoring** — Real-time cross-asset correlation tracking to manage portfolio heat and concentration risk
- **Alpha Decay Detection** — Continuous monitoring of strategy performance degradation with automatic evolution triggers
- **CI/CD Pipeline** — CircleCI automation with linting, type checking, security scanning, and multi-suite test execution

---

## Key Features

- **Multi-Strategy Execution** — 152 strategies across SMC/ICT, Wyckoff, Mean Reversion, Momentum, and statistical arbitrage
- **Institutional Risk Management** — 9-checkpoint constitutional gate, daily 2% / weekly 3% loss limits, fail-closed kill switch
- **MT5 & Broker Integration** — Live MT5 bridge via MetaTrader5 terminal, CCXT for crypto exchanges, paper trading mode
- **Async Pipeline** — Fully asynchronous event-driven architecture with LangGraph orchestration
- **Self-Evolution** — Strategies continuously mutate, backtest, and improve via walk-forward validated evolution
- **Standalone Mode** — Full autonomous operation without Hermes or external AI orchestrators
- **7 Agent Personas** — Autobot, Clawbot, Devbot, Fangbot, Hackerbot, Traderbot, Researchbot — each with specialized roles
- **50-Agent Council** — Multi-model debate engine for strategic trading decisions

---

## Quick Start

### Install

```bash
git clone https://codeberg.org/Dhaher-Labs/Quant-Nanggroe-AI
cd Quant-Nanggroe-AI
uv sync
```

### Configure

```bash
cp .env.example .env
# Required: MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, QNA_ADMIN_API_KEY
```

### Run

```bash
# Standalone mode (no external dependencies)
uv run python -m quant_nanggroe.standalone --once --symbols EURUSD

# Full autonomous pipeline
uv run python qna.py status
uv run python qna.py api

# Run tests
uv run python -m pytest tests/ -v --tb=short
```

---

## Documentation

Full documentation is in `docs/` (50 documents covering all aspects of the system):

| Document | Description |
|----------|-------------|
| `docs/00_VISION.md` | Project vision and objectives |
| `docs/01_PRD.md` | Product requirements |
| `docs/02_ARCHITECTURE.md` | Technical architecture |
| `docs/04_API.md` | API reference (179 endpoints) |
| `docs/07_SECURITY.md` | Security architecture and threat model |
| `docs/09_TESTING.md` | Testing guide and suite results |
| `docs/10_ROADMAP.md` | Development roadmap |
| `docs/19_RISK_REGISTER.md` | Risk management and register |
| `docs/35_CI_CD.md` | CI/CD pipeline configuration |
| `docs/50_AGENT_COUNCIL.md` | Multi-agent council protocol |

See `docs/` for the complete set.

---

## Current Status

| Metric | Value |
|--------|-------|
| Version | 5.1.0 |
| Architecture Health | 8/10 (was 5/10) |
| Test Files | 135+ (51 new in v5.1.0) |
| Issues Resolved | 45 of 47 |
| Python | 3.14+ |
| Strategies | 152 auto-discovered |
| Broker Integrations | 6 |
| API Endpoints | 179 |

### Recent Improvements (v5.1.0)

- **Correction module** — Systematic error recording and resolution with lesson-based prevention
- **Self-correct system** — Self-awareness reflection, anomaly detection, and automated recovery
- **Correlation monitoring** — Real-time cross-asset correlation tracking
- **Alpha decay detection** — Continuous performance degradation monitoring
- **CI/CD pipeline** — CircleCI automation with linting, type-checking, security scanning
- **51 new tests** — Expanded coverage across risk, execution, and strategy modules
- **45/47 issues resolved** — Security vulnerabilities, architectural debt, and test gaps closed
- **Architecture health improved** — 5/10 to 8/10 through systematic audit and remediation

---

## License

MIT — Dhaher Labs. See [LICENSE](LICENSE).

---

v5.1.0 — Built with fury from Aceh, Indonesia