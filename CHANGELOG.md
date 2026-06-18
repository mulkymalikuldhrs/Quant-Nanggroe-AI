# Changelog — Quant Nanggroe AI

## [1.0.0] — 2026-06-18

### Added — Production Release

#### Deployment & Infrastructure
- **Multi-Target Deployment** (`deploy.sh`)
  - E2B sandbox deployment with health verification
  - VPS deployment (Ubuntu/Debian) with systemd service
  - Docker Compose deployment with health checks
  - Unified health check endpoint for all targets
- **E2B Configuration** (`e2b.toml`)
  - Production-ready sandbox configuration
  - Resource limits (2 CPU, 2GB RAM, 10GB disk)
  - Security permissions and network configuration
- **Monitoring Stack** (`docker-compose.monitoring.yml`)
  - Prometheus with 30-day retention and 10GB size limit
  - Grafana with auto-provisioned dashboards and datasources
  - Alertmanager for notification routing
  - Node Exporter for host system metrics
  - PostgreSQL and Redis exporters for database metrics
- **Prometheus Alert Rules** (`monitoring/prometheus/alert_rules.yml`)
  - High latency alert (P95 > 2s warning, > 5s critical)
  - High error rate alert (> 5% warning, > 15% critical)
  - Service down alerts (API, PostgreSQL, Redis, Prometheus)
  - Low disk space alert (> 85% warning, > 95% critical)
  - High memory/CPU usage alerts

#### Backup & Recovery
- **Automated Backup System** (`scripts/backup.sh`)
  - Database backup (PostgreSQL, SQLite, MySQL)
  - Configuration backup (env, config, docker-compose)
  - Log backup with journalctl integration
  - Rotation policy (7 daily, 4 weekly)
  - S3 upload with STANDARD_IA storage class
  - Structured backup reports

#### Load Testing
- **Load Test Framework** (`scripts/load_test.py`)
  - Concurrent request testing with configurable threads
  - Throughput measurement (req/s and MB/s)
  - Latency distribution (P50, P90, P95, P99)
  - Per-endpoint breakdown and error tracking
  - JSON report generation
  - Rate limiting support

#### Security Hardening
- **Environment Hardening** (`scripts/harden.sh`)
  - SSH hardening (disable root, key-only auth, strong ciphers)
  - UFW firewall configuration (SSH, HTTP, HTTPS, app ports)
  - Fail2Ban with SSH and API-specific jails
  - Automatic security updates (unattended-upgrades)
  - Kernel hardening (sysctl: anti-spoof, SYN flood, etc.)
  - Verification tooling

#### Documentation
- **User Guide** (`docs/USER_GUIDE_QNA.md`)
  - Installation guide (source, Docker, system deps)
  - Quick start with 4-step onboarding
  - Complete configuration reference
  - API reference with request/response examples
  - CLI reference for QNA and BH Colony CLIs
  - Troubleshooting guide (6 common issues)
  - FAQ covering general, data, trading, and deployment topics

### Changed
- Updated `CHANGELOG.md` with v1.0.0 release notes
- Updated `e2b.toml` with production configuration
- Updated `monitoring/prometheus.yml` with new scrape targets

### Deprecated
- None

### Removed
- None

### Fixed
- None (clean release)

### Security
- SSH root login disabled by default
- Password authentication disabled (key-only)
- Firewall configured with deny-by-default policy
- Automatic security updates enabled
- Kernel network stack hardened against common attacks

---

## [1.0.0-rc.1] — 2026-06-18

### Added — Release Candidate
- **CLI Tools** (`scripts/qna-cli.py`, `scripts/bh-cli.py`)
  - `qna kelly/regime/stress/backtest/health/serve` — production CLI with engine integration
  - `bh status/agents/mesh/radar/health` — BH Colony mesh management CLI
  - JSON output mode (`--json`) for all commands
  - Graceful fallback when engine modules are unavailable
- **Health & Monitoring Probes** (`engine/api/health.py`)
  - `GET /health` — Full system health (DB, data providers, LLM providers, engine modules)
  - `GET /metrics` — Prometheus-format metrics endpoint
  - `GET /ready` — Kubernetes readiness probe
  - `GET /live` — Kubernetes liveness probe
  - Component-level health checks with status degradation tracking
- **Security Audit Scanner** (`scripts/security_audit.py`)
  - Hardcoded API keys / secrets detection
  - Hardcoded passwords / credentials detection
  - Insecure import scanning (pickle, eval, exec, shell=True)
  - SQL injection pattern detection (string formatting in queries)
  - Debug / development leftover detection
  - JSON and human-readable report output
- **Pre-Release Checklist** (`docs/PRE_RELEASE_CHECKLIST.md`)
  - 8-section checklist: code quality, tests, security, docs, perf, deploy, deps, git
  - Sign-off table for team accountability
- **Runbook** (`docs/RUNBOOK.md`)
  - Full system architecture diagram
  - Deployment procedures (local, Docker, E2B, Kubernetes)
  - Troubleshooting guide (6 common issues with solutions)
  - Rollback procedures (Docker, database, git, kill switch)
  - Monitoring & alerting reference
  - Environment variables reference
- **E2B Sandbox Configuration** (`e2b.toml`)
  - E2B sandbox image, build, env, ports, startup, health check
  - Network permissions and mount configuration

### Added — Core Engine (pre-existing in rc.1)
- **12 Data Providers** (`engine/data/providers/`)
  - yfinance, Alpha Vantage, Polygon, Binance/CCXT, CoinGecko
  - FRED, Finnhub, Twelve Data, FMP, BLS, GDELT, World Bank
  - Unified BaseProvider with async fetch, retry, rate limiting
- **Data Fallback Chain** (`engine/data/fallback_chain.py`)
  - Priority-based provider fallback
  - Circuit breaker pattern (3-failure threshold, auto-reset)
  - Per-provider success/failure/skip statistics
- **Data Manager** (`engine/data/data_manager.py`)
  - Unified interface: get_ohlcv(), get_fundamentals(), get_economic()
  - In-memory + disk caching with TTL
  - Health check endpoint
- **Kelly→Backtest Integration** (`engine/kelly/backtest_integration.py`)
  - KellyBacktestBridge: auto-selects Fractional/Bayesian/Drawdown Kelly
  - StrategyKellyMixin for existing strategies
- **Regime→Strategy Selector** (`engine/regime/strategy_selector.py`)
  - 7 regime→strategy mappings with Kelly scaling
  - RegimeAdaptiveStrategy
- **Stress Testing Enhanced** (`engine/stress_testing/`)
  - Monte Carlo: GBM, jump-diffusion, regime-switching, correlated multi-asset
  - Historical: 5 crisis scenarios (2008, COVID, 2022, DotCom, Black Monday)
  - EWHS VaR/CVaR with configurable half-life
  - Sensitivity/what-if analysis (rates, vol, correlation)
- **Pattern Recorder Enhanced** (`engine/pattern_recorder/`)
  - Matrix Profile (STUMPY + numpy fallback)
  - DTW with Sakoe-Chiba band, DDTW, batch matching
  - Embedding similarity (26 statistical/spectral/shape features)
  - Recurrence Plot Analysis with RQA measures
- **Almgren-Chriss Full** (`engine/execution/almgren_chriss.py`)
  - TWAP, VWAP, IS, Adaptive strategies
  - ExecutionSimulator with Monte Carlo VaR
  - Convenience function: optimal_execution_schedule()
- **Visualization Dashboard** (`engine/visualization/`)
  - ChartFactory: OHLCV, line, bar, heatmap, equity, drawdown, distribution
  - QNADashboard: metrics computation (Sharpe, Sortino, VaR, etc.), HTML export
- **Unit Tests** — 187 tests across 35 test classes

### Enhanced
- All stress testing modules: rewritten with proper OOP, dataclass results
- All pattern recorder modules: rewritten with numpy fallbacks, robust typing
- Execution module: from minimal stub to full implementation
- Visualization: from stub to full Plotly dashboard

### Documentation
- README.md with full architecture overview
- docs/api.md with module-by-module API reference
- docs/PRE_RELEASE_CHECKLIST.md — pre-release quality gates
- docs/RUNBOOK.md — deployment, troubleshooting, rollback procedures
- CHANGELOG.md (this file)
- Test scripts in scripts/ directory

### Deployment
- E2B-ready: all dependencies documented, import-verified
- E2B sandbox configuration (`e2b.toml`)
- Integration with BH colony bridge via 11 quant capabilities

### Known Issues
- LLM API keys required for full agent pipeline (degrades gracefully to simulation)
- Some engine modules have optional dependencies (hmmlearn, stumpy) — degrade gracefully
- WebSocket reconnection not yet implemented for real-time streaming

### Migration Guide (from 0.2.0)
1. Run `pip install -e ".[dev]"` to update dependencies
2. Copy `.env.example` to `.env` and configure new keys
3. Run `python scripts/qna-cli.py health` to verify system
4. Run `python scripts/security_audit.py` to check for issues
5. API endpoints remain backward-compatible — no breaking changes
6. New health/metrics endpoints available at `/health`, `/metrics`, `/ready`, `/live`

## [0.1.0] — Pre-MVP
- Basic Kelly implementation
- HMM regime detection
- Initial stress testing stubs
- Basic data layer
