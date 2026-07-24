# Quant Nanggroe AI v5.1.0 — Autonomous Quant Hedge Fund

> **Autonomous Quantitative Hedge Fund — Institutional Grade**
> **Self-Aware · Self-Correct · Self-Evolve · Self-Fine-Tune · Self-Evaluate**
> *"Mesin uang autonomous, jalan tanpa Hermes, optionally assisted."* — Mulky Malikul Dhaher

---

## 🎯 What Is This?

QNA is a **fully autonomous quantitative hedge fund platform** that runs, evolves, and optimizes itself with zero human intervention. It's not a trading bot — it's a **living financial organism**.

### Core Capabilities

| Capability | Module | Status |
|---|---|---|
| **Self-Aware** | `engine/self_aware.py` | ✅ Reflects on every run |
| **Self-Correct** | `engine/correction.py` | ✅ Records + resolves errors |
| **Self-Evolve** | `engine/strategy/strategies/strategy_evolver.py` | ✅ Walk-forward validated mutations |
| **Self-Fine-Tune** | `engine/strategy/strategies/self_finetune.py` | ✅ Grid search + optimization |
| **Self-Evaluate** | `engine/strategy/strategies/strategy_evolver.py` | ✅ Accept/reject gate |
| **Auto-Registry** | `engine/registry.py` | ✅ Scans ENTIRE repo (1017+ files) |
| **Standalone** | `engine/standalone.py` | ✅ Runs without Hermes |

---

## 🚀 Quick Start

### 1. Install
```bash
git clone https://codeberg.org/Dhaher-Labs/Quant-Nanggroe-AI
cd Quant-Nanggroe-AI
uv sync
```

### 2. Configure
```bash
cp .env.example .env
# Required vars: MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, QNA_ADMIN_API_KEY
```

### 3. Run
```bash
# Standalone mode (no Hermes dependency)
uv run python -m quant_nanggroe.standalone --once --symbols EURUSD

# Full autonomous mode
uv run python qna.py status
uv run python qna.py api
```

---

## 🏗️ Architecture

```
qna.py (single entry point)
├── engine/
│   ├── agentic/autonomous.py    — Main pipeline (3,528 LOC)
│   ├── self_aware.py            — Self-reflection module
│   ├── registry.py              — Auto-discovery registry (ENTIRE repo)
│   ├── strategies/              — Active strategies + evolver + fine-tuner
│   ├── risk/                    — 9-checkpoint risk gate + kill switch
│   ├── backtest/                — Walk-forward + Monte Carlo + CPCV
│   ├── execution/               — TWAP/VWAP order slicing
│   ├── factors/                 — Alpha factor library (15K LOC)
│   └── 30+ subpackages
├── agents/                      — 7 AI agent personas
├── api/                         — 179 FastAPI endpoints
├── exchange/                    — 6 broker integrations
├── dashboard/                   — Next.js React UI
├── tests/                       — 135 tests
└── standalone.py                — Zero-Hermes entry point
```

---

## 📊 Codebase Metrics

| Metric | Value |
|---|---|
| Total files | 3,037 |
| Python LOC | 180,007 (pkg) + 57,014 (tests) |
| API endpoints | 174 |
| Strategies | 152 wired (auto-discovered) |
| Exchange brokers | 6 |
| Agent personas | 7 |
| Test pass rate | 94/94 (fast suite) |

---

## 🛡️ Risk Management

- **9-checkpoint constitutional gate** — Every trade validated
- **Kill switch** — Emergency halt all trading
- **Daily loss limit** — 2% max daily drawdown
- **Weekly loss limit** — 3% max weekly drawdown
- **Position sizing** — Max 10% per trade
- **TWAP/VWAP** — Smart order execution for large orders

---

## 🔄 Evolution Cycle

```
1. STRATEGY RUNS → produces signals
2. TRADES EXECUTED → PnL tracked
3. SELF-EVALUATE → win rate, Sharpe, drawdown analyzed
4. IF UNDERPERFORMING → trigger evolution
5. SELF-EVOLVE → mutate parameters (±30% jitter)
6. VALIDATE → walk-forward backtest on mutated params
7. SELF-FINE-TUNE → grid search optimization
8. PROMOTE → only if improved > 2% over baseline
9. REPEAT → continuously improving
```

---

## 🧪 Testing

```bash
# Fast suite (core modules)
uv run python -m pytest tests/ -v --tb=short

# Risk tests only
uv run python -m pytest tests/test_risk_checks.py tests/test_engine/test_risk.py -v

# Specific module
uv run python -m pytest tests/test_autonomous_pipeline.py -v
```

---

## 🔧 Configuration

All credentials use environment variables (never hardcoded):

| Variable | Description |
|---|---|
| `QNA_ADMIN_API_KEY` | Admin API key |
| `MT5_LOGIN` | MT5 account login |
| `MT5_PASSWORD` | MT5 account password |
| `MT5_SERVER` | MT5 broker server |
| `FREQTRADE_JWT_SECRET` | JWT secret for API server |
| `FREQTRADE_USERNAME` | API server username |
| `FREQTRADE_PASSWORD` | API server password |

---

## 📚 Documentation

| Doc | Description |
|---|---|
| `docs/00_VISION.md` | Project vision |
| `docs/01_PRD.md` | Product requirements |
| `docs/02_ARCHITECTURE.md` | Technical architecture |
| `docs/04_API.md` | API reference |
| `docs/07_SECURITY.md` | Security architecture |
| `docs/09_TESTING.md` | Testing guide |
| `docs/10_ROADMAP.md` | Development roadmap |
| `docs/19_RISK_REGISTER.md` | Risk management |
| `QNA_EXTREM_AUDIT_2026-07-24.md` | Latest deep audit |
| `session-QNA.md` | Session history |

---

## 📜 License

MIT — Dhaher Labs. See [LICENSE](LICENSE).

---

*v5.1.0 — Built with fury from Aceh, Indonesia 🇮🇩*
