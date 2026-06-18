# ╔══════════════════════════════════════════════════════════════════════╗
# ║      Quant-Nanggroe-AI  —  User Guide                              ║
# ║      Production-Ready Documentation for v1.0.0                     ║
# ╚══════════════════════════════════════════════════════════════════════╝

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [CLI Reference](#cli-reference)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)

---

## Installation

### Prerequisites

- Python 3.10 or later (3.12 recommended)
- PostgreSQL 14+ (recommended) or SQLite
- Redis 7+
- Node.js 18+ (for dashboard frontend)

### From Source

```bash
# Clone the repository
git clone https://codeberg.org/Dhaher-Labs/Quant-Nanggroe-AI.git
cd quant-nanggroe-ai

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -e ".[dev]"

# Copy environment configuration
cp .env.example .env
# Edit .env with your API keys
```

### With Docker

```bash
# Clone and start all services
git clone https://codeberg.org/Dhaher-Labs/Quant-Nanggroe-AI.git
cd quant-nanggroe-ai

# Start the full stack
docker-compose up -d

# Check health
curl http://localhost:8000/health
```

### System Dependencies

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install -y \
    python3.12 python3.12-venv python3-pip \
    postgresql redis-server \
    build-essential libpq-dev

# macOS (Homebrew)
brew install python@3.12 postgresql@16 redis
brew services start postgresql@16
brew services start redis
```

---

## Quick Start

### 1. Configure API Keys

Edit `.env` and add at least one LLM provider key:

```bash
QNAI_LLM_PROVIDER=openai
QNAI_OPENAI_API_KEY=sk-your-key-here
```

### 2. Start the System

```bash
# Option A: Direct
python -m uvicorn quant_nanggroe_ai.api.app:create_app \
    --factory --host 0.0.0.0 --port 8000

# Option B: Docker
docker-compose up -d

# Option C: Production (systemd)
sudo systemctl start quant-nanggroe-ai
```

### 3. Verify

```bash
# Health check
curl http://localhost:8000/health

# Run CLI
python scripts/qna-cli.py health
```

### 4. First Analysis

```bash
# Get Kelly criterion for a stock
python scripts/qna-cli.py kelly --symbol AAPL --capital 100000

# Check market regime
python scripts/qna-cli.py regime --symbol SPY

# Run stress test
python scripts/qna-cli.py stress --portfolio '{"AAPL": 0.5, "GOOGL": 0.5}'
```

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `QNAI_LLM_PROVIDER` | No | `openai` | LLM provider: openai, anthropic, google, ollama |
| `QNAI_OPENAI_API_KEY` | Yes* | — | OpenAI API key |
| `QNAI_ANTHROPIC_API_KEY` | Yes* | — | Anthropic API key |
| `QNAI_DATABASE_URL` | No | `sqlite:///data/quant.db` | Database connection URL |
| `QNAI_REDIS_URL` | No | `redis://localhost:6379/0` | Redis connection URL |
| `QNAI_ENV` | No | `development` | Environment: development, staging, production |
| `QNAI_LOG_LEVEL` | No | `INFO` | Log level: DEBUG, INFO, WARNING, ERROR |
| `QNAI_DEBUG` | No | `false` | Enable debug mode |
| `QNAI_API_HOST` | No | `0.0.0.0` | API listen host |
| `QNAI_API_PORT` | No | `8000` | API listen port |

*At least one LLM provider key is required for live agent execution.

### Database Configuration

**SQLite (default — development):**
```bash
QNAI_DATABASE_URL=sqlite:///data/quant.db
```

**PostgreSQL (recommended — production):**
```bash
QNAI_DATABASE_URL=postgresql+asyncpg://qna:password@localhost:5432/quant_nanggroe
```

### Redis Configuration

```bash
QNAI_REDIS_URL=redis://localhost:6379/0
# With authentication:
QNAI_REDIS_URL=redis://:password@localhost:6379/0
```

### Data Provider Keys

| Provider | Variable | Free Tier |
|----------|----------|-----------|
| Alpaca | `QNAI_ALPACA_API_KEY` | Yes |
| Polygon | `QNAI_POLYGON_API_KEY` | Limited |
| TwelveData | `QNAI_TWELVEDATA_API_KEY` | Limited |
| Binance | `QNAI_BINANCE_API_KEY` | Yes |
| Finnhub | `QNAI_FINNHUB_API_KEY` | Yes |

### Configuration Files

| File | Purpose |
|------|---------|
| `.env` | Environment variables (never commit) |
| `config/system_config.yaml` | System-wide configuration |
| `config/prompts.yaml` | Agent prompt templates |
| `e2b.toml` | E2B sandbox configuration |
| `docker-compose.yml` | Docker services definition |
| `alembic.ini` | Database migration configuration |

---

## API Reference

### Base URL

```
http://localhost:8000
```

### Authentication

All API requests require an API key in the header:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" http://localhost:8000/api/v1/health
```

### Endpoints

#### Health & Monitoring

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Full system health check |
| `GET` | `/ready` | Kubernetes readiness probe |
| `GET` | `/live` | Kubernetes liveness probe |
| `GET` | `/metrics` | Prometheus-format metrics |

#### Kelly Criterion

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/kelly/calculate` | Calculate Kelly fraction |
| `POST` | `/api/v1/kelly/backtest` | Backtest Kelly strategy |

**Request:**
```json
{
  "symbol": "AAPL",
  "capital": 100000,
  "method": "fractional",
  "risk_factor": 0.25
}
```

**Response:**
```json
{
  "symbol": "AAPL",
  "kelly_fraction": 0.15,
  "recommended_allocation": 15000,
  "edge": 0.08,
  "win_rate": 0.62,
  "method": "fractional"
}
```

#### Regime Detection

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/regime/detect` | Detect current market regime |
| `GET` | `/api/v1/regime/history` | Get regime history |

**Response:**
```json
{
  "symbol": "SPY",
  "regime": "bull_low_vol",
  "confidence": 0.87,
  "strategy_recommendation": "momentum_growth",
  "kelly_scale": 1.2
}
```

#### Stress Testing

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/stress/monte-carlo` | Monte Carlo simulation |
| `POST` | `/api/v1/stress/historical` | Historical scenario analysis |
| `POST` | `/api/v1/stress/sensitivity` | Sensitivity analysis |

**Request:**
```json
{
  "portfolio": {"AAPL": 0.4, "GOOGL": 0.3, "MSFT": 0.3},
  "scenarios": 10000,
  "horizon_days": 252,
  "confidence_level": 0.95
}
```

#### Market Data

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/data/ohlcv/{symbol}` | Get OHLCV data |
| `GET` | `/api/v1/data/fundamentals/{symbol}` | Get fundamentals |
| `GET` | `/api/v1/data/providers` | List available providers |

### Error Format

```json
{
  "error": {
    "type": "validation_error",
    "code": "INVALID_SYMBOL",
    "message": "The provided symbol 'XYZ' is not a valid ticker",
    "param": "symbol"
  }
}
```

### Rate Limiting

| Tier | Requests/min | Burst |
|------|-------------|-------|
| Free | 60 | 10 |
| Pro | 600 | 100 |
| Enterprise | 6000 | 1000 |

Rate limit headers:
- `X-RateLimit-Limit`: Maximum requests per window
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Window reset timestamp

---

## CLI Reference

### QNA CLI (`scripts/qna-cli.py`)

```bash
# Kelly criterion calculation
python scripts/qna-cli.py kelly --symbol AAPL --capital 100000

# Market regime detection
python scripts/qna-cli.py regime --symbol SPY

# Stress testing
python scripts/qna-cli.py stress --portfolio '{"AAPL": 0.5}'

# Backtest
python scripts/qna-cli.py backtest --strategy kelly --symbol AAPL --period 1y

# System health
python scripts/qna-cli.py health

# Start API server
python scripts/qna-cli.py serve --port 8000

# JSON output mode
python scripts/qna-cli.py health --json
```

### BH Colony CLI (`scripts/bh-cli.py`)

```bash
# Colony status
python scripts/bh-cli.py status

# Agent management
python scripts/bh-cli.py agents list
python scripts/bh-cli.py agents start <agent-name>

# Mesh network
python scripts/bh-cli.py mesh status

# Health check
python scripts/bh-cli.py health
```

### Security Audit

```bash
python scripts/security_audit.py
# Outputs JSON report + human-readable summary
```

---

## Troubleshooting

### Common Issues

#### 1. "ModuleNotFoundError: No module named 'quant_nanggroe_ai'"

**Cause:** Package not installed in development mode.

**Fix:**
```bash
pip install -e ".[dev]"
# Or set PYTHONPATH:
export PYTHONPATH=$(pwd)/src
```

#### 2. "Connection refused" to PostgreSQL

**Cause:** PostgreSQL not running or wrong credentials.

**Fix:**
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Verify credentials
psql -h localhost -U qna -d quant_nanggroe

# Reset password
sudo -u postgres psql -c "ALTER USER qna WITH PASSWORD 'new_password';"
```

#### 3. "Redis connection error"

**Cause:** Redis not running.

**Fix:**
```bash
sudo systemctl start redis
redis-cli ping  # Should return PONG
```

#### 4. High memory usage

**Cause:** Large datasets or too many concurrent analyses.

**Fix:**
```bash
# Reduce worker count
python -m uvicorn ... --workers 2

# Limit cache size in config/system_config.yaml:
# cache:
#   max_size_mb: 256
```

#### 5. API key errors

**Cause:** Missing or invalid API key.

**Fix:**
```bash
# Verify key is set
echo $QNAI_OPENAI_API_KEY

# Test key directly
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $QNAI_OPENAI_API_KEY"
```

#### 6. "Permission denied" on backup script

**Cause:** Script not executable.

**Fix:**
```bash
chmod +x scripts/backup.sh
```

### Logs

```bash
# Application logs
journalctl -u quant-nanggroe-ai -f

# Docker logs
docker-compose logs -f api

# Nginx access logs
tail -f /var/log/nginx/qna_access.log

# Prometheus logs
docker logs qna-prometheus
```

### Health Check Commands

```bash
# Full system health
curl http://localhost:8000/health | python -m json.tool

# Readiness
curl http://localhost:8000/ready

# Liveness
curl http://localhost:8000/live

# CLI health
python scripts/qna-cli.py health
```

---

## FAQ

### General

**Q: What markets does QNAI support?**
A: US equities (NYSE, NASDAQ), cryptocurrencies (Binance, Bybit), and forex (via TwelveData). Economic data via FRED and World Bank.

**Q: Can I use QNAI without API keys?**
A: Yes, QNAI runs in simulation mode without LLM keys. You'll get rule-based recommendations instead of AI-powered analysis.

**Q: What is the minimum hardware requirement?**
A: 2 CPU cores, 4GB RAM, 10GB disk. For production with PostgreSQL and Redis, 4 cores and 8GB RAM recommended.

### Data

**Q: How is market data fetched?**
A: Through a fallback chain of 12 providers. If the primary provider fails, QNAI automatically falls back to the next provider with circuit breaker protection.

**Q: Is historical data cached?**
A: Yes, in-memory and on-disk caching with configurable TTL. Default TTL is 24 hours for OHLCV data.

### Trading

**Q: Does QNAI execute trades?**
A: QNAI provides analysis and recommendations only. Trade execution is handled by your broker integration. Use the Almgren-Chriss module for execution scheduling.

**Q: What is the Kelly Criterion?**
A: A formula for optimal bet sizing that maximizes long-term growth rate. QNAI supports fractional Kelly (safer) and Bayesian Kelly variants.

**Q: How accurate are the regime detections?**
A: Regime detection uses Hidden Markov Models with 7 regime types. Historical accuracy is approximately 85% on US equity data. Always use alongside other analysis.

### Deployment

**Q: Should I use Docker or bare metal?**
A: Docker is recommended for ease of deployment and isolation. Bare metal is fine for single-server setups where you want maximum control.

**Q: Can I run QNAI on a VPS?**
A: Yes. A $5-10/month VPS (2 vCPU, 4GB RAM) handles moderate load. See the deployment scripts in `deploy.sh`.

**Q: How do I set up monitoring?**
A: Run `docker-compose -f docker-compose.monitoring.yml up -d` for Prometheus, Grafana, and Alertmanager. See `monitoring/` directory for configuration.

### Support

**Q: Where do I report bugs?**
A: Open an issue on GitHub with the `bug_report` template. Include logs and reproduction steps.

**Q: Is there a community Discord?**
A: Join via the link in the README. Community support is available for general questions.

---

*Last updated: 2026-06-18 | Version: 1.0.0*
