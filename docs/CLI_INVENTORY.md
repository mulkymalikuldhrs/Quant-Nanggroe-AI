# QNA CLI Inventory Report

Generated: 2026-06-24
Scope: All CLI commands across Quant-Nanggroe-AI codebase

---

## 1. Complete Inventory Table

| # | Command | Source File | Type | Framework | Description | Arguments |
|---|---------|------------|------|-----------|-------------|-----------|
| 1 | `qnai run` | `quant_nanggroe/cli.py:40` | click group | Click+Rich | Run trading pipeline | `--symbols/-s` (default BTC/USDT), `--provider/-p` (openai/anthropic/google/ollama/openrouter), `--deep-model`, `--quick-model`, `--paper`, `--live`, `--trade-date` |
| 2 | `qnai backtest` | `quant_nanggroe/cli.py:229` | click command | Click+Rich | Run backtest | `--strategy/-st` (momentum/mean_reversion/breakout/scalping/swing/all), `--symbols/-s`, `--period` (1M/3M/6M/1Y/2Y), `--capital/-c`, `--commission`, `--market` (equity/crypto/forex) |
| 3 | `qnai agents list` | `quant_nanggroe/cli.py:326` | click subcommand | Click+Rich | List available agents | (none) |
| 4 | `qnai portfolio status` | `quant_nanggroe/cli.py:396` | click subcommand | Click+Rich | Show portfolio status | (none) |
| 5 | `qnai risk check <SYMBOL>` | `quant_nanggroe/cli.py:501` | click command | Click+Rich | Run risk assessment | `SYMBOL` (positional argument) |
| 6 | `qnai serve` | `quant_nanggroe/cli.py:599` | click command | Click+Rich | Start API server | `--host` (default 0.0.0.0), `--port` (default 8000), `--reload` |
| 7 | `qnai memory stats` | `quant_nanggroe/cli.py:632` | click subcommand | Click+Rich | Memory system stats | (none) |
| 8 | `qnai memory graph-stats` | `quant_nanggroe/cli.py:678` | click subcommand | Click+Rich | Knowledge graph stats | (none) |
| 9 | `qna kelly` | `quant_nanggroe/scripts/qna-cli.py:74` | argparse subcommand | argparse | Kelly criterion analysis | `--symbol/-s` (required), `--capital/-c`, `--win-rate`, `--avg-win`, `--avg-loss`, `--fraction` |
| 10 | `qna regime` | `quant_nanggroe/scripts/qna-cli.py:131` | argparse subcommand | argparse | Market regime detection | `--symbol/-s` (required) |
| 11 | `qna stress` | `quant_nanggroe/scripts/qna-cli.py:176` | argparse subcommand | argparse | Portfolio stress test | `--symbol/-s` (required), `--confidence` |
| 12 | `qna backtest` | `quant_nanggroe/scripts/qna-cli.py:219` | argparse subcommand | argparse | Strategy backtest | `--strategy` (required), `--start` (required), `--end`, `--capital`, `--commission` |
| 13 | `qna health` | `quant_nanggroe/scripts/qna-cli.py:262` | argparse subcommand | argparse | System health check | (none, plus global `--json`) |
| 14 | `qna serve` | `quant_nanggroe/scripts/qna-cli.py:333` | argparse subcommand | argparse | Start API server | `--host`, `--port` (default 8080), `--reload`, `--log-level` |
| 15 | `qna` (global) | `quant_nanggroe/scripts/qna-cli.py:361` | argparse root | argparse | (shared) | `--json` (output as JSON) |
| 16 | `bh status` | `quant_nanggroe/scripts/bh-cli.py:149` | argparse subcommand | argparse | BH colony status | (none) |
| 17 | `bh agents list` | `quant_nanggroe/scripts/bh-cli.py:180` | argparse subcommand | argparse | List BH agents | (none) |
| 18 | `bh agents status --id` | `quant_nanggroe/scripts/bh-cli.py:216` | argparse subcommand | argparse | Agent status | `--id` (required) |
| 19 | `bh mesh status` | `quant_nanggroe/scripts/bh-cli.py:252` | argparse subcommand | argparse | Mesh network status | (none) |
| 20 | `bh radar` | `quant_nanggroe/scripts/bh-cli.py:304` | argparse subcommand | argparse | Peer discovery | (none) |
| 21 | `bh health` | `quant_nanggroe/scripts/bh-cli.py:337` | argparse subcommand | argparse | System health | (none, plus global `--json`) |
| 22 | `bh` (global) | `quant_nanggroe/scripts/bh-cli.py:408` | argparse root | argparse | (shared) | `--json` |
| 23 | `python scripts/alpha_destruction.py` | `scripts/alpha_destruction.py:353` | standalone | argparse | Alpha destruction protocol | `--symbols` (default BTC,ETH,SOL,XRP), `--n`, `--real`, `--export` |
| 24 | `python scripts/qna-architect.py` | `scripts/qna-architect.py:665` | standalone | argparse | Codebase architect | `--json`, `--mermaid`, `--check`, `--focus` |
| 25 | `python scripts/test_runner.py` | `scripts/test_runner.py:398` | standalone | argparse | Test runner | `--json`, `--verbose` |
| 26 | `python -m quant_nanggroe.scripts.load_test` | `quant_nanggroe/scripts/load_test.py:306` | standalone | argparse | Load testing tool | `--url`, `--concurrent/-c`, `--duration/-d`, `--endpoints/-e`, `--timeout/-t`, `--rate-limit/-r`, `--report/-o` |
| 27 | `python -m quant_nanggroe.scripts.security_audit` | `quant_nanggroe/scripts/security_audit.py:341` | standalone | argparse | Security audit | `--path`, `--json`, `--no-info` |
| 28 | `python -m quant_nanggroe.worker` | `quant_nanggroe/worker.py:353` | standalone | none | Background trading worker | (none — hardcoded config) |

### FastAPI Routes (CLI-accessible via curl)

| # | Method | Route | Source | Description |
|---|--------|-------|--------|-------------|
| 29 | GET | `/` | `quant_nanggroe/api.py:292` | Root API info |
| 30 | GET | `/api/v1/health` | `quant_nanggroe/api.py:307` | Health check |
| 31 | POST | `/api/v1/trade` | `quant_nanggroe/api.py:327` | Execute trading pipeline |
| 32 | GET | `/api/v1/portfolio` | `quant_nanggroe/api.py:393` | Portfolio status |
| 33 | GET | `/api/v1/agents` | `quant_nanggroe/api.py:449` | List agents |
| 34 | POST | `/api/v1/backtest` | `quant_nanggroe/api.py:472` | Run backtest |
| 35 | GET | `/api/v1/risk/{symbol}` | `quant_nanggroe/api.py:543` | Risk assessment |
| 36 | WS | `/ws/trading` | `quant_nanggroe/api.py:615` | Real-time trading updates |

### Shell Scripts with Subcommand Systems

| # | Script | Subcommands | Description |
|---|--------|-------------|-------------|
| 37 | `deploy/run.sh` | `start`, `stop`, `restart`, `status`, `install`, `check`, `logs`, `clean`, `help` | Legacy system startup (Flask-based) |
| 38 | `deploy/deploy.sh` | `e2b`, `vps`, `docker`, `health`, `all`, `help` | Multi-target deployment |
| 39 | `deploy/start_production.sh` | (none — single purpose) | Gunicorn production startup |
| 40 | `deploy/start.sh` | (none — single purpose) | Flask dev startup |
| 41 | `deploy/scripts/entrypoint.sh` | (none — single purpose) | Docker entrypoint (migrations + exec) |
| 42 | `quant_nanggroe/scripts/backup.sh` | `all`, `db`, `config`, `logs`, `rotate`, `upload`, `report`, `help` | Automated backup |
| 43 | `quant_nanggroe/scripts/harden.sh` | `all`, `ssh`, `firewall`, `fail2ban`, `updates`, `verify`, `help` | Environment hardening |
| 44 | `quant_nanggroe/scripts/setup.sh` | (none — single purpose) | Environment setup |
| 45 | `quant_nanggroe/scripts/setup_dev.sh` | (none — single purpose) | Dev environment setup |
| 46 | `quant_nanggroe/scripts/test-all.sh` | `--python-only`, `--js-only` | Multi-workspace test runner |
| 47 | `quant_nanggroe/scripts/entrypoint.sh` | (none — single purpose) | Docker entrypoint (QNA-specific) |

### Makefile Targets (de facto CLI entry points)

| # | Command | Description | Depends On |
|---|---------|-------------|------------|
| 48 | `make install` | Install production deps | poetry |
| 49 | `make dev` | Install all deps + pre-commit | poetry |
| 50 | `make test` | Run all tests | pytest |
| 51 | `make test-engine` | Engine tests | pytest |
| 52 | `make test-agents` | Agent tests | pytest |
| 53 | `make test-cov` | Tests with coverage | pytest-cov |
| 54 | `make test-slow` | Slow tests | pytest |
| 55 | `make lint` | Ruff lint | ruff |
| 56 | `make format` | Auto-format | ruff |
| 57 | `make typecheck` | mypy type check | mypy |
| 58 | `make security` | Bandit security scan | bandit |
| 59 | `make check` | Lint + typecheck + test | lint, typecheck, test |
| 60 | `make db-push` | Push DB schema | alembic |
| 61 | `make db-migrate` | Create migration | alembic |
| 62 | `make db-rollback` | Rollback migration | alembic |
| 63 | `make run` | Start API server | uvicorn |
| 64 | `make run-worker` | Start worker | python worker |
| 65 | `make docker-build` | Build Docker images | docker compose |
| 66 | `make docker-up` | Start Docker services | docker compose |
| 67 | `make docker-down` | Stop Docker services | docker compose |
| 68 | `make docker-logs` | Follow Docker logs | docker compose |
| 69 | `make docker-dev` | Start dev Docker stack | docker compose |
| 70 | `make clean` | Remove build artifacts | shell |
| 71 | `make ci` | Full CI pipeline | format, lint, typecheck, security, test |

---

## 2. Gap Analysis

| Gap | Severity | Description |
|-----|----------|-------------|
| No unified entry point | HIGH | Three CLIs (`qnai`, `qna`, `bh`) with different frameworks, conventions, and arg styles — user confusion |
| `alpha_destruction` not in main CLI | MEDIUM | Alpha destruction protocol is only runnable via `scripts/alpha_destruction.py` path — no `qnai alpha` command |
| `qna-architect` not in main CLI | LOW | Codebase analysis tool only available via raw path |
| `security_audit` not in main CLI | MEDIUM | Security audit only accessible via internal script path |
| `load_test` not in main CLI | LOW | Load testing only accessible via internal script path |
| No data provider management | MEDIUM | No CLI command to list/configure/test data providers |
| No strategy management | MEDIUM | No CLI command to list strategies, inspect params, or register new ones |
| No backup/restore from main CLI | LOW | Backup script exists but is not wired into any main CLI |
| No kill switch CLI command | LOW | KillSwitch exists in API and engine but no direct CLI toggle |
| No config management | LOW | No `qnai config get/set/show` — .env editing required |
| No log tailing | LOW | No `qnai logs` — must use `docker logs` or `make docker-logs` |
| No shell completion | LOW | Click supports auto-completion but no `qnai completion` command wired |

---

## 3. Redundancies Found

| # | Redundant Items | Problem |
|---|----------------|---------|
| 1 | `qnai backtest` (Click) vs `qna backtest` (argparse) vs `POST /api/v1/backtest` | Three different backtest interfaces with different args — which is canonical? |
| 2 | `qnai serve` (Click) vs `qna serve` (argparse) vs `make run` vs `deploy/start.sh` vs `deploy/start_production.sh` | Five ways to start a server, pointing to different ports (8000 vs 8080 vs 5000) |
| 3 | `qna health` vs `bh health` | Two health checks with overlapping module checks |
| 4 | Two `entrypoint.sh` files | `deploy/scripts/entrypoint.sh` and `quant_nanggroe/scripts/entrypoint.sh` — similar purpose, different locations |
| 5 | `qnai agents list` (hardcoded) vs `GET /api/v1/agents` (hardcoded) vs `bh agents list` (file-based registry) | Agent data duplicated in 3 places — no single source of truth |
| 6 | `Makefile` `check` target does lint+typecheck+test, but `test` target does not run `lint` first | Inconsistent pipeline — CI runs lint and test as separate jobs |
| 7 | `setup.sh` and `setup_dev.sh` | Two setup scripts with different approaches (venv vs poetry) |

---

## 4. Recommendations

1. **Consolidate to one CLI**: Make `qnai` the single canonical CLI. Merge `qna` subcommands (kelly, regime, stress, health) into `qnai` as `qnai kelly`, `qnai regime`, `qnai stress`.

2. **Move `bh` into `qnai`**: The BH Colony commands should be under `qnai colony status|agents|mesh|radar`.

3. **Standardize server startup**: `qnai serve` on port 8000 is canonical. Remove `qna serve`, document `make run` as dev alternative, and delete the legacy `deploy/start.sh` (Flask-based, no longer relevant).

4. **Add missing commands to `qnai`**:
   - `qnai alpha` — run alpha destruction
   - `qnai audit security` — run security audit
   - `qnai load-test` — run load testing
   - `qnai architect` — run codebase analysis
   - `qnai backup` — trigger backup
   - `qnai config get/set/show` — config management
   - `qnai completion` — shell auto-completion

5. **Deprecate `scripts/` root scripts**: Move `alpha_destruction.py`, `qna-architect.py`, `test_runner.py` into `quant_nanggroe/scripts/` and expose them via the main CLI.

6. **Deduplicate agents data**: Use the agent registry file (`agent-ctx/agent_registry.json`) as the single source of truth, imported by `cli.py`, `api.py`, and `bh-cli.py`.

7. **Unify backtest interface**: Choose `qnai backtest` as canonical and redirect API/v2 to use the same arg names.

8. **Wire shell scripts into Makefile**: `make backup`, `make harden`, `make deploy` as documented shortcuts.
