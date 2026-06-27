# QNA Architecture v4.0.0

## System Overview

```mermaid
graph TD
    SYNTH[GARCH Synthetic Data] --> STRAT[8 Strategies]
    STRAT --> BT[Backtest Engine<br/>Walk-Forward, CPCV, Monte Carlo, PSR/DSR]
    BT --> RISK[Risk Layer<br/>KillSwitch, Kelly, VaR, Regime]
    RISK --> DAEMON[Paper Trading Daemon]
    DAEMON --> AUDIT[Alpha Audit]
    DAEMON --> DASH[Dashboard]
    DAEMON --> PNL[PnL CSV]
    DAEMON --> STATE[AutoDisable State]
    DATA[Data Layer] --> FAILOVER[FailoverProvider]
    DATA --> CACHE[SQLite Cache]
    DATA --> PROVIDERS[12 Providers: CCXT, yFinance, Alpha Vantage, Polygon, ...]
    EXEC[Execution Layer] --> BROKER[Paper/Multi/Exchange Brokers]
    EXEC --> FILL[Fill Tracker]
    EXEC --> GUARD[Position Guards]
    SEC[Security] --> PII[PII Redaction]
    SEC --> AUDITLOG[AuditLogger]
    MEM[Memory] --> JEUM[JeumpaLLM Gateway]
    MEM --> SEUL[Seulanga RAG Bridge]
```

## Modules (378 total)

| Module | Files | LOC | Purpose |
|--------|-------|-----|---------|
| `engine/` | ~120 | ~42K | Backtest, execution, risk, strategy, compliance |
| `data/` | ~35 | ~10K | Multi-provider data pipeline with failover |
| `agents/` | ~25 | ~8K | AI agent orchestration |
| `exchange/` | ~15 | ~5K | Exchange broker wrappers |
| `security/` | ~10 | ~3K | PII redaction, audit logging |
| `llm/` | ~8 | ~3K | JeumpaLLM multi-provider gateway |
| `memory/` | ~8 | ~2K | Seulanga RAG bridge |
| `types/` | ~5 | ~1K | Shared type definitions |
| `connectors/` | ~5 | ~1K | External service connectors |
| `skills/` | ~3 | ~1K | Agent skill definitions |

## Test Status — 1119 Tests

- **3 pre-existing failures** (mocked data provider setup)
- **129 pre-existing errors** (missing optional deps like scipy/numpy in env)
- **72 skipped** (integration/API-key tests)
- **Zero regressions** from our changes

## Automation Scripts

| Script | Purpose |
|--------|---------|
| `auto-init.sh` | Environment setup |
| `auto-audit.sh` | Import + lint + syntax audit (14/14 pass) |
| `auto-graphify.sh` | 5 dependency graphs (architecture, import map, package tree, strategy flow) |
| `auto-list-files.sh` | Complete file inventory |
| `auto-docs.sh` | API docs from source (3922 classes/functions) |
| `auto-register.sh` | Auto-discover and register new modules |
| `auto-report.sh` | Consolidated project report |
| `auto-review.sh` | Code review automation |

## Swarm Evolution

```mermaid
gantt
    title QNA Development — 9 Phases
    dateFormat  YYYY-MM-DD
    section Swarm 1-4
    Core + Risk + Strategies + Data    :done, 2026-06-10, 14d
    section Swarm 5-6
    Daemon + Exchange + 598 Tests      :done, 2026-06-22, 3d
    section Swarm 7-8
    Coverage Push 805→1039 Tests       :done, 2026-06-25, 1d
    section Swarm 9
    Orphan Rescue + Autonomy Suite      :done, 2026-06-27, 1d
```

## Architecture Decisions

- **Package-level `__init__.py` wildcard exports** — all submodules auto-exported for convenience
- **Graceful degradation** — JeumpaLLM and Seulanga RAG degrade without crashing when deps/servers missing
- **Test namespace isolation** — test subdirectories use no `__init__.py` to prevent module conflicts
- **Auto-registration pattern** — new `.py` files auto-detected and wired into `__init__.py` exports
- **Immutability in risk** — risk limits (0.5%/trade, 1%/day, 3%/week) are hardcoded constants, no override
