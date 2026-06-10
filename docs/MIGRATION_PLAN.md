# Migration Plan — Quant-Nanggroe-AI Monorepo Consolidation

## Overview

This document details the step-by-step migration of 23 source repositories into a single
production-grade monorepo. The migration preserves commit history via `git subtree` while
resolving dependency conflicts, removing duplicate code, and extracting reusable modules.

## Pre-Migration Checklist

- [x] Create target branch `cl1-agent-4` from `main`
- [x] Merge foundation from `cl1-agent-1` (Python backend, 175 tests, Docker, CI/CD)
- [x] Verify all existing tests pass
- [ ] Complete dependency audit across all repos
- [ ] Generate dependency graph before any code changes

## Repository Classification

### Active — Full Integration (code merged into src/)

| Repository | Target Directory | Language | Status |
|-----------|-----------------|----------|--------|
| Quant-Nanggroe-AI | `src/quant_nanggroe_ai/core/` | TypeScript/Python | ✅ Base |
| Misi-Screener | `src/quant_nanggroe_ai/agents/tools/` | TypeScript | 🔄 Extract screener logic |
| HermesQuantOS | `src/quant_nanggroe_ai/engine/backtest/` | Python | 🔄 Merge backtest engine |
| Trading-Plan-AI-Interactive | `apps/dashboard/` | Python/Dart | 🔄 Extract dashboard UI |
| SolSniperX | `src/quant_nanggroe_ai/agents/nodes/crypto.py` | JS/Rust | 🔄 Port sniper to Python |
| AI-Trader | `src/quant_nanggroe_ai/agents/nodes/trader.py` | Python | 🔄 Consolidate into trader |
| OpenAlice | `src/quant_nanggroe_ai/agents/nodes/researcher.py` | Python | 🔄 Merge social listening |
| TradingAgents | `src/quant_nanggroe_ai/agents/` | Python | 🔄 Convert to LangGraph nodes |
| ai-agents-for-trading | `src/quant_nanggroe_ai/agents/nodes/strategist.py` | Python | 🔄 Convert to state nodes |
| ai-hedge-fund | `src/quant_nanggroe_ai/agents/nodes/portfolio.py` | Python | 🔄 Extract optimization |
| AutoHedge | `src/quant_nanggroe_ai/agents/nodes/risk_manager.py` | Python | 🔄 Convert to risk node |
| Vibe-Trading | `src/quant_nanggroe_ai/engine/factors/` | Python | 🔄 Convert to sentiment factor |
| QuantDinger | `src/quant_nanggroe_ai/engine/backtest/` | Python | 🔄 Port to TimescaleDB |
| QuantMuse | `research/` | Python | 📋 Reorganize as research |
| quant-trading | `src/quant_nanggroe_ai/engine/factors/` | Python | 📋 Standardize templates |
| Kronos | `src/quant_nanggroe_ai/engine/execution/` | Go/C++ | 📋 Future: PyO3 bindings |
| dexter | `src/quant_nanggroe_ai/agents/nodes/macro.py` | Python | 🔄 Merge macro scrapers |
| ai-financial-agent | `src/quant_nanggroe_ai/agents/nodes/researcher.py` | Python | 🔄 Merge search vectors |
| polymarket-cli | `src/quant_nanggroe_ai/execution/polymarket.py` | Rust | 🔄 Port PMXT adapter |

### Research — Reference Only (archived, not merged into src/)

| Repository | Target Directory | Language | Status |
|-----------|-----------------|----------|--------|
| awesome-quant | `research/awesome-quant/` | Markdown | 📋 Reference |
| awesome-vibe-coding | `research/awesome-vibe-coding/` | Markdown | 📋 Reference |
| FinceptTerminal | `apps/terminal/` | TypeScript | 🔄 Extract terminal UI |
| bloomberg-terminal | `apps/terminal/` | C++/Qt | 🗑️ Retire (DEC-001) |

### Infra — Runtime Support

| Repository | Target Directory | Language | Status |
|-----------|-----------------|----------|--------|
| openhuman | `src/quant_nanggroe_ai/memory/` | Python | 🔄 Merge model adapters |
| project-nomad-offline | `infra/` | Bash/Docker | 📋 Offline deployment |

## Merge Execution Script

```bash
#!/usr/bin/env bash
set -euo pipefail

TOKEN="${GITHUB_TOKEN}"
BASE="https://${TOKEN}@github.com/mulkymalikuldhrs"

declare -A REPOS=(
  ["Misi-Screener"]="contrib/misi-screener"
  ["HermesQuantOS"]="contrib/hermes-quant-os"
  ["Trading-Plan-AI-Interactive"]="contrib/trading-plan-ai"
  ["SolSniperX"]="contrib/sol-sniper-x"
  ["AI-Trader"]="contrib/ai-trader"
  ["OpenAlice"]="contrib/open-alice"
  ["TradingAgents"]="contrib/trading-agents"
  ["ai-agents-for-trading"]="contrib/ai-agents-for-trading"
  ["ai-hedge-fund"]="contrib/ai-hedge-fund"
  ["AutoHedge"]="contrib/auto-hedge"
  ["Vibe-Trading"]="contrib/vibe-trading"
  ["QuantDinger"]="contrib/quant-dinger"
  ["QuantMuse"]="contrib/quant-muse"
  ["quant-trading"]="contrib/quant-trading"
  ["dexter"]="contrib/dexter"
  ["ai-financial-agent"]="contrib/ai-financial-agent"
  ["polymarket-cli"]="contrib/polymarket-cli"
  ["FinceptTerminal"]="contrib/fincept-terminal"
  ["awesome-quant"]="research/awesome-quant"
  ["awesome-vibe-coding"]="research/awesome-vibe-coding"
  ["openhuman"]="contrib/openhuman"
  ["project-nomad-offline"]="contrib/project-nomad-offline"
)

for REPO in "${!REPOS[@]}"; do
  DIR="${REPOS[$REPO]}"
  echo "=== Integrating: $REPO → $DIR ==="

  git remote add "temp_$REPO" "$BASE/$REPO.git" 2>/dev/null || true
  git fetch "temp_$REPO" --no-tags

  mkdir -p "$(dirname "$DIR")"
  git subtree add --prefix="$DIR" "temp_$REPO" main -m "Merge $REPO into $DIR" || \
    echo "WARNING: $REPO merge failed, skipping"

  git remote remove "temp_$REPO" 2>/dev/null || true
done

echo "=== Monorepo merge complete ==="
```

## Dependency Conflict Resolution

| Conflict | Repositories | Resolution |
|----------|-------------|------------|
| Pydantic v1 vs v2 | TradingAgents, OpenAlice, agentcloud | Standardize to Pydantic v2; rewrite v1 BaseModel patterns |
| LangChain version | AI-Trader, TradingAgents | Remove LangChain dependency; migrate to LangGraph |
| Python 3.9-3.12 | AI-Trader, quant-trading | Standardize to Python 3.12+ |
| TA-Lib C dependency | Vibe-Trading | Replace with ta-python or numpy-native indicators |
| CCXT version | QuantDinger, SolSniperX | Pin CCXT to latest stable; abstract exchange adapter |
| SQLAlchemy 1.x vs 2.x | OpenAlice, agentcloud | Migrate to SQLAlchemy 2.0 |
| Node.js version | FinceptTerminal, Misi-Screener | Pin Node.js 20 LTS |
| InfluxDB auth | QuantDinger | Replace with TimescaleDB adapter |

## De-duplication Plan

| Duplicate | Repos | Keep | Action |
|-----------|-------|------|--------|
| Market data fetching | AI-Trader, QuantDinger, Vibe-Trading | Unified MarketDataTool | Remove per-repo implementations |
| Sentiment analysis | AI-Trader, OpenAlice | Unified SentimentTool | Merge signal sources |
| Risk checks | AutoHedge, ai-hedge-fund | ConstitutionalRiskGuard | Consolidate to 9-checkpoint system |
| Execution routing | SolSniperX, AI-Trader | Unified ExecutionNode | Keep SOR logic from SolSniperX |
| Config loading | All repos | Centralized config.py | Remove per-repo config files |
| Logging setup | All repos | Centralized logging.py | Standardize structured logging |

## Rollback Plan

If catastrophic failure occurs during migration:

```bash
#!/usr/bin/env bash
# rollback_migration.sh
set -euo pipefail

echo "CRITICAL BUILD FAILURE. INITIALIZING ROLLBACK..."

# Reset to pre-merge state
git reset --hard HEAD
git clean -fd

# Remove temporary remotes
for REMOTE in $(git remote | grep "^temp_"); do
  git remote remove "$REMOTE"
done

# Force checkout last known good commit
git checkout -B cl1-agent-4 origin/cl1-agent-4

echo "ROLLBACK COMPLETE. System returned to stable recovery point."
```

## Post-Migration Validation

After all merges are complete, the following checks must pass:

1. `python -m py_compile` on all `.py` files — no syntax errors
2. `pytest tests/ -v` — all existing tests pass
3. `mypy src/` — type checking passes
4. `docker compose build` — Docker images build successfully
5. `make lint` — no linting errors
6. Import graph analysis — no circular dependencies
7. Dependency audit — no known vulnerabilities (pip-audit / safety)

## Timeline

| Phase | Duration | Milestone |
|-------|----------|-----------|
| Phase I | Week 1-2 | Repo subtrees merged, structure validated |
| Phase II | Week 3-4 | Code deduplication, dependency resolution |
| Phase III | Week 5-6 | All tests green, CI/CD pipeline operational |
| Phase IV | Week 7-8 | Production readiness review, deployment |
