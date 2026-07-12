# DHAHER LABS — REALIZATION MANDATE

> **This is a REAL system. NOT a simulation. NOT a toy.**
> DHAHER LABS operates REAL autonomous systems. No mock data, no dummy content.

## Project: Quant-Nanggroe-AI v4.0.0

**Status:** Live · Autonomous · Part of Dhaher Labs Ecosystem
**Score:** 100/100 (Constitution 25, Quality 50, Operations 25)

### Mandate
- This project is declared a LIVING PRODUCTION SYSTEM
- All mock/dummy/placeholder code is FORBIDDEN
- Every component must do REAL work or be removed
- This is not a portfolio piece — it is a functioning autonomous system

### Architecture Overview
- **Backend**: FastAPI on port 8000, 20+ endpoints across monitor, trading, backtest, agents, memory, colony, market, security
- **Engine**: RegimeBased strategy with walk-forward validation, risk manager, kill switch, Chinese Wall compliance
- **Data**: Multi-provider failover pipeline (Alpha Vantage, Polygon, TwelveData, CCXT, yfinance, Coingecko, Finnhub, FRED, etc.)
- **Agents**: LangGraph orchestration with debate engine, compliance agent, risk agent, Chinese Wall
- **Security**: JWT auth, encryption at rest (cryptography), credential vault, PII redaction, audit logging, Prometheus metrics
- **Frontend**: Next.js dashboard with real-time PnL, risk, regime, backtest, factor, strategy UIs
- **Database**: SQLite/PostgreSQL via SQLAlchemy + Alembic, Redis caching, ChromaDB vector memory
- **MCP**: Model Context Protocol server/client for agent tool use

### Code Conventions
- Python 3.11+, strict mypy, ruff linting (E, F, I), line length 120
- Pydantic v2 for all data models and settings
- Async where possible (httpx, aiohttp)
- structlog for structured logging, rich for CLI
- Type hints required everywhere (disallow_untyped_defs = true)

### Key Constraints
- Risk limits are HARDCODED: 0.5% per trade, 1% daily loss, 3% weekly, 1:2 min reward
- .env files are NEVER committed — use .env.example with placeholder values
- Tests required for all new code
- Pre-commit hooks enforce ruff, mypy, security checks
- API keys must be loaded from Settings, never hardcoded

### Links
- **Complete Docs:** QUANT_NANGRAOE_COMPLETE.md
- **Ecosystem:** https://dhaher-labs.codeberg.page
- **Flagship:** https://dhaherlabsos.vercel.app
- **Manifesto:** https://dhaherlabsos.vercel.app/manifesto
