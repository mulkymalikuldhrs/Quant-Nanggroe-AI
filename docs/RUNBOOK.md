# Runbook — Quant Nanggroe AI v1.0.0-rc.1

## System Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                     Client Layer                             │
│  CLI (qna / bh) · REST API · WebSocket · Dashboard          │
├──────────────────────────────────────────────────────────────┤
│                     API Gateway                              │
│  FastAPI + Uvicorn · CORS · Rate Limiting · Auth            │
├──────────────────────────────────────────────────────────────┤
│                   Agent Orchestration                        │
│  LangGraph · TradingGraph · Multi-Agent Pipeline             │
├──────────────────────────────────────────────────────────────┤
│                     Engine Layer                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │  Kelly   │ │  Regime  │ │  Stress  │ │ Backtest │       │
│  │ Criterion│ │ Detector │ │  Testing │ │  Engine  │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │   Risk   │ │ Decision │ │ Pressure │ │Execution │       │
│  │ Manager  │ │ Synthesis│ │   Norm   │ │  Almgren │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
├──────────────────────────────────────────────────────────────┤
│                    Data Layer                                │
│  12 Data Providers · Fallback Chain · Cache · AutoSwitch     │
├──────────────────────────────────────────────────────────────┤
│                  Infrastructure                              │
│  SQLite/PostgreSQL · Redis · Prometheus · E2B Sandbox        │
└──────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Purpose | Location |
|-----------|---------|----------|
| Kelly Criterion | Position sizing (10 methods) | `engine/kelly/` |
| Regime Detector | Market regime classification (HMM) | `engine/regime/` |
| Stress Testing | Monte Carlo, Historical, EWHS | `engine/stress_testing/` |
| Backtest Engine | Walk-forward, CPCV, Monte Carlo | `engine/backtest/` |
| Risk Manager | Constitutional limits, kill switch | `engine/risk/` |
| Decision Synthesis | Deterministic decision table | `engine/decision.py` |
| Data Providers | 12 providers with fallback chain | `engine/data/providers/` |
| API Server | FastAPI with health/metrics | `quant_nanggroe/api/` |
| Security | KeyVault, JWT, audit trail | `quant_nanggroe/security/` |

---

## Deployment Procedures

### Local Development

```bash
# 1. Clone and install
git clone <repo-url>
cd Quant-Nanggroe-AI
pip install -e ".[dev]"

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 3. Initialize database
python -c "from database.init_db import initialize_database; initialize_database()"

# 4. Run tests
pytest tests/ -v

# 5. Start API server
python -m quant_nanggroe.cli serve --port 8000
```

### Docker Deployment

```bash
# Build image
docker build -t quant-nanggroe-ai:1.0.0-rc.1 .

# Run container
docker run -d \
  --name qnai \
  -p 8000:8000 \
  --env-file .env \
  quant-nanggroe-ai:1.0.0-rc.1

# Or use docker compose
docker compose up -d
```

### E2B Sandbox

```bash
# Install E2B CLI
pip install e2b

# Start sandbox
e2b sandbox start --config e2b.toml

# Or from code
from e2b_code_interpreter import Sandbox
sandbox = Sandbox("quant-nanggroe-ai")
```

### Production (Kubernetes)

```bash
# Apply K8s manifests
kubectl apply -f k8s-deployment.yaml

# Check status
kubectl get pods -l app=quant-nanggroe-ai
kubectl logs -l app=quant-nanggroe-ai --tail=100
```

---

## Troubleshooting Guide

### Common Issues

#### 1. API Server Won't Start

```bash
# Check if port is in use
lsof -i :8000

# Check Python version (requires 3.11+)
python --version

# Check dependencies
pip install -e ".[dev]"

# Check for import errors
python -c "from quant_nanggroe.api import app"
```

#### 2. Database Connection Errors

```bash
# Check database file exists
ls -la data/quant_nanggroe.db

# Reinitialize if missing
python -c "from database.init_db import initialize_database; initialize_database()"

# Check SQLite
sqlite3 data/quant_nanggroe.db "SELECT COUNT(*) FROM sqlite_master;"
```

#### 3. Data Provider Failures

```bash
# Test individual providers
python -c "
import yfinance as yf
data = yf.download('BTC-USD', period='5d')
print(data.tail())
"

# Check API keys
python -c "
import os
for k in ['OPENAI_API_KEY', 'ALPHA_VANTAGE_KEY', 'POLYGON_API_KEY']:
    print(f'{k}: {\"set\" if os.environ.get(k) else \"MISSING\"}')"
```

#### 4. Kelly Engine Errors

```bash
# Test Kelly computation
python -c "
from quant_nanggroe.engine.kelly.base import KellyParameters, KellyMethod
from quant_nanggroe.engine.kelly.fractional import FractionalKelly
params = KellyParameters(win_rate=0.55, avg_win=0.03, avg_loss=0.02)
kelly = FractionalKelly()
result = kelly.compute(params)
print(f'Kelly fraction: {result.f_star:.4f}')"
```

#### 5. Memory Issues

```bash
# Check memory usage
python -c "
import psutil
proc = psutil.Process()
print(f'Memory: {proc.memory_info().rss / 1024 / 1024:.1f} MB')"

# Reduce Monte Carlo simulations
# In stress_testing config: n_simulations=1000 (instead of 10000)
```

#### 6. CLI Commands Not Found

```bash
# Ensure scripts are executable
chmod +x scripts/qna-cli.py scripts/bh-cli.py

# Or run via Python
python scripts/qna-cli.py health
python scripts/bh-cli.py status
```

---

## Rollback Procedures

### Rolling Back a Release

```bash
# 1. Stop current version
docker stop qnai

# 2. Pull previous version
docker pull quant-nanggroe-ai:0.2.0

# 3. Start previous version
docker run -d \
  --name qnai \
  -p 8000:8000 \
  --env-file .env \
  quant-nanggroe-ai:0.2.0
```

### Rolling Back Database

```bash
# If database migration caused issues
cp data/quant_nanggroe.db.bak data/quant_nanggroe.db

# Or reinitialize
python -c "from database.init_db import reset_database; reset_database()"
```

### Rolling Back Git

```bash
# Find the commit to rollback to
git log --oneline -10

# Reset to that commit
git reset --hard <commit-hash>

# Force push (if already pushed)
git push --force-with-lease origin main
```

### Emergency Kill Switch

```bash
# If system is misbehaving, force stop all trading
python -c "
from quant_nanggroe.engine.risk.kill_switch import KillSwitch
ks = KillSwitch()
ks.activate('Manual emergency stop')
print('Kill switch activated')
"

# Or via API
curl -X POST http://localhost:8000/api/risk/kill-switch \
  -H "Content-Type: application/json" \
  -d '{"reason": "emergency_stop"}'
```

---

## Monitoring & Alerting

### Key Metrics to Watch

| Metric | Threshold | Action |
|--------|-----------|--------|
| API response time | > 1s | Check database, restart if needed |
| Memory usage | > 512MB | Restart service, check for leaks |
| Error rate | > 5% | Check logs, investigate root cause |
| Data provider failures | > 3 consecutive | AutoSwitch should handle; check config |
| Daily P&L | < -1% | Kill switch should auto-activate |

### Health Check Commands

```bash
# Full health check
curl http://localhost:8000/health | python -m json.tool

# Readiness probe
curl http://localhost:8000/ready | python -m json.tool

# Liveness probe
curl http://localhost:8000/live | python -m json.tool

# Prometheus metrics
curl http://localhost:8000/metrics

# CLI health check
python scripts/qna-cli.py health
python scripts/bh-cli.py health
```

### Log Locations

| Service | Log Location |
|---------|-------------|
| API Server | stdout (docker logs) |
| Audit Trail | `data/audit.db` |
| Trade Journal | `data/journal.db` |
| Application | structured JSON via structlog |

---

## Contact Information

| Role | Responsibility |
|------|---------------|
| Lead Developer | Architecture, core engine, release management |
| DevOps | Deployment, infrastructure, monitoring |
| QA Engineer | Testing, quality gates, regression testing |
| Security | Audit, vulnerability assessment, credential management |

### Escalation Path

1. **P0 (System Down)**: Lead Developer → DevOps
2. **P1 (Degraded)**: On-call Engineer → Lead Developer
3. **P2 (Bug)**: QA Engineer → Lead Developer
4. **P3 (Enhancement)**: Feature Request → Backlog

---

## Appendix: Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes* | OpenAI API key for LLM agents |
| `ANTHROPIC_API_KEY` | No | Anthropic API key (alternative) |
| `GOOGLE_API_KEY` | No | Google AI API key (alternative) |
| `ALPHA_VANTAGE_KEY` | No | Alpha Vantage data provider |
| `POLYGON_API_KEY` | No | Polygon.io data provider |
| `BINANCE_API_KEY` | No | Binance exchange API key |
| `BINANCE_API_SECRET` | No | Binance exchange API secret |
| `DATABASE_URL` | No | PostgreSQL connection string |
| `REDIS_URL` | No | Redis connection string |
| `SECRET_KEY` | Yes | JWT signing key |

*At least one LLM provider key is required for full functionality.
