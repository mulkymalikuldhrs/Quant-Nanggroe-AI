# Production Deployment Checklist

## Pre-Flight (Before Any Real Money)

- [ ] All strategies backtested with >= 3 years daily data
- [ ] Walk-forward validated (not just in-sample)
- [ ] At least 3 months of paper trading with track record
- [ ] Kill switch tested (triggered and verified it blocks)
- [ ] Risk manager VETO tested (triggered and verified it blocks)
- [ ] All API keys in environment variables, NOT in code or config files
- [ ] Git history scrubbed of any credentials (git filter-branch or BFG)
- [ ] Dockerfile builds and runs cleanly
- [ ] Health check endpoint responds correctly
- [ ] Graceful shutdown tested (SIGTERM → stop accepting new orders, wait for fills)

## Secrets Management

```bash
# REQUIRED: All secrets via environment variables
QNAI_JWT_SECRET=<random-32-char>
QNAI_GROQ_API_KEY=<key>
QNAI_MT5_LOGIN=<login>        # NOT in config files committed to git
QNAI_MT5_PASSWORD=<password>    # NOT in config files committed to git
QNAI_MT5_SERVER=<server>       # NOT in config files committed to git
QNA_LIVE_TRADING=0             # Default OFF

# .gitignore MUST include:
# .env
# .env.local
# .env.*.local
# config/mt5_accounts.yaml      # (if it contains real credentials)
# .secrets-local/
# paper_state/
```

## Dockerfile Template

```dockerfile
# Multi-stage: builder → runtime
FROM python:3.12-slim AS builder
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir poetry && poetry config virtualenvs.in-project true
RUN poetry install --no-dev --no-interaction

FROM python:3.12-slim AS runtime
WORKDIR /app
COPY --from=builder /app/.venv .venv
COPY quant_nanggroe/ quant_nanggroe/
COPY config/ config/
COPY data/ data/
COPY qna.py qna.py
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
CMD ["python", "qna.py", "api"]
```

## Health Check Endpoint

```python
# GET /health → 200 OK
# Response:
{
  "status": "healthy",
  "uptime_seconds": 12345,
  "version": "4.5.0",
  "components": {
    "data_providers": {"available": 3, "total": 5},
    "kill_switch": {"active": false, "level": "normal"},
    "scheduler": {"running": true, "last_cycle": "2024-01-01T00:00:00Z"}
  }
}
```

## Alerting (Minimum Required)

1. **Kill switch activation** → Telegram/Slack message + email
2. **Daily P&L summary** → Daily at 00:00 UTC
3. **System error** → Any uncaught exception → immediate alert
4. **Data provider failure** → When all providers for a symbol fail
5. **Execution failure** → Order rejected or fill not confirmed

## Observability Stack

```
Logging: structured JSON (not plain text)
Metrics: Prometheus (request count, latency, P&L, fill rate)
Tracing: OpenTelemetry (trace from data fetch → signal → risk → execution → fill)
Alerting: Grafana Alertmanager or custom webhook → Telegram/Slack
Error tracking: Sentry or equivalent
```

## Monitoring Dashboard (Minimum Widgets)

1. Account equity over time (equity curve)
2. Current positions with unrealized P&L
3. Kill switch status (green/yellow/red)
4. Last 10 pipeline runs (signal, confidence, risk decision)
5. Daily P&L (today + last 30 days)
6. Strategy performance (per-strategy Sharpe, win rate, trades)
7. Data provider health (available/total, last error)
8. System health (CPU, memory, uptime)

---

> **SSOT:** `CANONICAL.md` v8.0.20 — BAL $1,445, weekly 0 WIB, probe 0/32, CPCV 207, launch.bat 1, vector 6 modul
