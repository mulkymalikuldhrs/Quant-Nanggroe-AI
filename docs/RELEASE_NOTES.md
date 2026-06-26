# ╔══════════════════════════════════════════════════════════════════════╗
# ║      Quant-Nanggroe-AI  —  Release Notes v1.0.0                    ║
# ║      Production Release                                            ║
# ╚══════════════════════════════════════════════════════════════════════╝

**Release Date:** 2026-06-18
**Version:** 1.0.0
**Status:** Stable

---

## What's New in v1.0.0

Quant Nanggroe AI v1.0.0 is the first production-ready release of the Agentic Trading Intelligence OS. This release transforms the research prototype into a deployable, observable, and secure trading intelligence platform.

---

## Features

### Core Engine

- **12 Data Providers** — yfinance, Alpha Vantage, Polygon, Binance/CCXT, CoinGecko, FRED, Finnhub, Twelve Data, FMP, BLS, GDELT, World Bank
- **Data Fallback Chain** — Priority-based provider switching with circuit breaker pattern
- **Kelly Criterion Engine** — Fractional Kelly, Bayesian Kelly, and Drawdown Kelly with backtest integration
- **Regime Detection** — Hidden Markov Model with 7 regime→strategy mappings
- **Stress Testing** — Monte Carlo (GBM, jump-diffusion, regime-switching), Historical (5 crisis scenarios), EWHS VaR/CVaR
- **Pattern Recorder** — Matrix Profile, DTW, embedding similarity, recurrence plot analysis
- **Execution Engine** — Almgren-Chriss optimal execution (TWAP, VWAP, IS, Adaptive)
- **Visualization Dashboard** — OHLCV charts, equity curves, drawdown analysis, metrics computation

### Infrastructure

- **Multi-Target Deployment** — E2B sandbox, VPS (Ubuntu/Debian), Docker Compose
- **Monitoring Stack** — Prometheus, Grafana, Alertmanager, Node Exporter
- **Alert Rules** — High latency, error rate, service down, low disk space, high memory/CPU
- **Automated Backups** — Database, config, logs with 7-day/4-week rotation and S3 upload
- **Load Testing** — Concurrent request testing with latency distribution and throughput measurement

### Security

- **Environment Hardening** — SSH hardening, UFW firewall, Fail2Ban, auto security updates
- **Kernel Hardening** — SYN flood protection, anti-spoof, ICMP redirect blocking
- **Security Audit Scanner** — Detects hardcoded secrets, insecure imports, SQL injection patterns

### CLI Tools

- `qna-cli.py` — Kelly, regime, stress, backtest, health, serve
- `bh-cli.py` — Colony status, agents, mesh, radar, health
- JSON output mode (`--json`) for all commands

### Documentation

- **User Guide** — Installation, quick start, configuration, API reference, troubleshooting, FAQ
- **API Reference** — Full endpoint documentation with request/response examples
- **Runbook** — Deployment procedures, troubleshooting, rollback

---

## Bug Fixes

- Fixed data provider fallback not resetting circuit breaker after timeout
- Fixed Kelly backtest integration using stale market data
- Fixed regime detector confidence calculation for low-data symbols
- Fixed pattern recorder memory leak in batch matching mode
- Fixed visualization dashboard not rendering drawdown curves correctly

---

## Breaking Changes

None. v1.0.0 is backward-compatible with v1.0.0-rc.1. All API endpoints, CLI commands, and configuration files remain unchanged.

---

## Migration Guide

### From v1.0.0-rc.1 to v1.0.0

1. **Update dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

2. **Pull latest code:**
   ```bash
   git pull origin main
   ```

3. **Run health check:**
   ```bash
   python scripts/qna-cli.py health
   ```

4. **Verify monitoring (optional):**
   ```bash
   docker-compose -f docker-compose.monitoring.yml up -d
   curl http://localhost:9090/-/healthy
   ```

5. **Run security audit:**
   ```bash
   python scripts/security_audit.py
   ```

### From v0.2.0 to v1.0.0

1. Run `pip install -e ".[dev]"` to update dependencies
2. Copy `.env.example` to `.env` and configure new keys
3. Run `python scripts/qna-cli.py health` to verify system
4. Run `python scripts/security_audit.py` to check for issues
5. API endpoints remain backward-compatible — no breaking changes
6. New health/metrics endpoints available at `/health`, `/metrics`, `/ready`, `/live`

---

## Known Issues

| Issue | Severity | Workaround |
|-------|----------|------------|
| LLM API keys required for full agent pipeline | Medium | System degrades gracefully to simulation mode without keys |
| Some engine modules have optional dependencies (hmmlearn, stumpy) | Low | System degrades gracefully with numpy fallbacks |
| WebSocket reconnection not implemented for real-time streaming | Medium | Refresh connection manually; reconnection support planned for v1.1.0 |
| Monitoring stack requires Docker Compose v2+ | Low | Use `docker compose` (v2) instead of `docker-compose` (v1) |

---

## Upgrade Path

| Version | Status | End of Support |
|---------|--------|----------------|
| v1.0.0 | Current | 2027-06-18 |
| v1.0.0-rc.1 | Superseded | 2026-09-18 |
| v0.2.0 | Deprecated | 2026-12-18 |
| v0.1.0 | End of Life | 2026-06-18 |

---

## Dependencies

### Python
- Python 3.10+ (3.12 recommended)
- FastAPI/Flask, SQLAlchemy, Redis, pandas, numpy, scipy, scikit-learn
- OpenTelemetry, structlog, uvicorn

### Infrastructure
- PostgreSQL 14+ (recommended)
- Redis 7+
- Docker 24+ (for container deployment)
- Node.js 18+ (for dashboard frontend)

### Full list: see `requirements.txt` and `pyproject.toml`

---

## Acknowledgments

Built with dedication by the Quant Nanggroe AI team in Indonesia.

Special thanks to the open-source projects that power this system:
- Python, FastAPI, SQLAlchemy, Redis
- Prometheus, Grafana, Alertmanager
- PostgreSQL, Docker, Nginx

---

## Support

- **Documentation:** `docs/USER_GUIDE_QNA.md`, `docs/RUNBOOK.md`
- **Issues:** GitHub Issues with `bug_report` template
- **Community:** Discord server (link in README)

---

*Released: 2026-06-18 | Hash: $(git rev-parse --short HEAD 2>/dev/null || echo "unknown")*
