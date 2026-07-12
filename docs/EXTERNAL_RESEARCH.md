# External Research — Quant-Nanggroe-AI-worktree Benchmarking

> **Audit Date:** 2026-07-11
> **Sources:** arXiv, GitHub, SSRN, academic papers, production frameworks

---

## 1. TradingAgents (UCLA Tauric Research) — v0.2.4 (2026-04-25)

**URL:** https://tradingagents-ai.github.io/ | https://github.com/TauricResearch/TradingAgents

**Architecture:**
- 5-layer LangGraph multi-agent trading firm simulation
- ~12 specialized LLM agents: fundamental analyst, sentiment analyst, technical analyst, trader (multiple risk profiles), risk manager
- Orange Book specification for agent workflow routing
- LangGraph state graph orchestrates message passing between agents
- Backtesting over TOPIX 100 (2023-09 to 2025-11)

**Relevance to Quant-Nanggroe:**
- Same stack: LangGraph, LangChain, LLM agents → validates architecture choice
- Quant-Nanggroe has 8+ agent types (researcher, strategist, crypto analyst, market maker, risk manager, compliance) vs TradingAgents' ~12 → **comparable scale**
- TradingAgents' paper (arXiv 2602.23330) shows empirical backtest results → Quant-Nanggroe lacks this quantitative validation
- Orange Book = formal agent routing spec → Quant-Nanggroe's TradingGraph does similar routing via LangGraph

**Gap:** Quant-Nanggroe has NO published empirical backtesting results for its multi-agent pipeline.

---

## 2. ai-hedge-fund (virattt) — 2026 Fork

**URL:** https://github.com/virattt/ai-hedge-fund

**Architecture:**
- Multi-agent LLM trading simulation with backtesting
- Rebuilt as persistent, always-on AI hedge fund
- Investor agents reimagined as pluggable, backtestable "alpha models"
- Docker-based deployment

**Relevance:**
- Quant-Nanggroe's `BACKTESTS.md` references `ai-hedge-fund` metrics
- ai-hedge-fund uses the **same agent pattern**: analyst → trader → risk workflow
- ai-hedge-fund recently (2026-07-03) rebuilt to support persistent live trading → Quant-Nanggroe's agentic_trading.py pipeline matches this design goal but is NOT wired for live execution

**Gap:** Quant-Nanggroe has more sophisticated financial infrastructure (multi-market backtest engines, HMM regime detection, Kelly sizing, walk-forward analysis) vs ai-hedge-fund which focuses purely on LLM agent orchestration.

---

## 3. RL-BHRP: Reinforcement Learning Bayesian Hierarchical Risk Parity

**arXiv 2508.11856 (2025-08-19)**

**Key contribution:**
- Combines RL with Bayesian hierarchical risk parity for institutional portfolio construction
- Three unified desiderata: statistically stable inputs, interpretable risk budgeting, adaptive allocation
- Two-level: sector-level and stock-level risk allocation

**Gap in Quant-Nanggroe:**
- Has `risk_parity.py` with `RiskParityOptimizer` (deterministic, not Bayesian)
- Has `MeanVarianceOptimizer`, `EqualVolatilityOptimizer`
- **Missing:** Bayesian HRP approach for adaptive allocation
- **Missing:** RL-based portfolio optimization (torch is in external deps but no RL agent exists)

---

## 4. HMM Regime Detection — Academic Evidence

**Paper: "Markov and Hidden Markov Models for Regime Detection in Cryptocurrency Markets" (2024-2026)**
- Found 71.5% win rate across 530 assets using GaussianHMM
- Bull/bear/mean-reverting state classification enables strategy switching
- All use `hmmlearn` (same library Quant-Nanggroe imports but missing from deps)

**Paper: "Trading using HMM during COVID-19 turbulences" (ResearchGate)**
- Monthly DAX returns + VSTOXX + industrial production + inflation
- HMM calibration for regime-switching trading strategies

**Paper: "Gaussian Hidden Markov Model" (TradingView script)**
- Production-ready HMM implementation used by retail traders
- Confirms hmmlearn is the standard approach

**Gap:** Quant-Nanggroe's HMM detector (`hmm_detector.py:1-308`) is well-structured with pydantic models, trained Regime enum, but:
1. `hmmlearn` NOT in dependency manifest
2. Zero tests for HMM detection (`test_regime_hmm_detector.py` exists but was never run)
3. No ensemble: best practice uses HMM + regime ensemble (Quant-Nanggroe has `test_regime_ensemble.py` but HMM not integrated)

---

## 5. Walk-Forward Analysis — Industry Standard Validation

**Source:** https://quanttradingtools.com/walk-forward-analysis/

**Key insight:** "A single backtest is curve-fit by default. Walk-forward tests what Monte Carlo can't."

Quant-Nanggroe has:
- `WalkForwardAnalyzer` ✅
- `WalkForwardResult` ✅  
- `WalkForwardStability` ✅
- Tests pass ✅

This is **hedge-fund grade**. The `walk_forward.py` implementation matches industry standard practice. Only gap: no visualization of results.

---

## 6. Production Deployment Patterns

**Market research (2025-2026):**
- Docker + Kubernetes is standard for production quant systems
- LangSmith for agent monitoring and tracing
- MCP (Model Context Protocol) for connecting external data sources
- Prometheus + Grafana for metrics visualization

**Quant-Nanggroe status:**
- Docker Compose: ✅ exists (`deploy/docker/docker-compose.yml`)
- Kubernetes: ❌ missing
- LangSmith: ❌ missing (LangSmith tracing not integrated)
- MCP: ❌ missing (no MCP server implementation)
- Prometheus: 🟡 in deps but not instrumented everywhere
- Grafana: ❌ missing

---

## Summary: Gap Analysis vs Hedge-Fund Standard

| Capability | Have | Missing |
|---|---|---|
| Multi-agent LangGraph orchestration | ✅ TradingGraph | — |
| Multi-market backtest engines (5 types) | ✅ 67/67 tests pass | — |
| Walk-forward validation | ✅ | — |
| Monte Carlo simulation | ✅ | — |
| HMM regime detection | 🟡 Code exists | `hmmlearn` dep, no tests run |
| Kelly / risk parity position sizing | 🟡 | `pandas_ta` dep |
| Published empirical backtest results | ❌ | Need quantitative validation |
| Live trading pipeline | ❌ | AgenticTrading not production-wired |
| Kubernetes deployment | ❌ | Only Docker Compose |
| LangSmith tracing | ❌ | No observability of agent reasoning |
| MCP protocol integration | ❌ | No external tool connectivity |
| RL portfolio optimization | ❌ | RL-BHRP paper not implemented |
| HMM ensemble regime detection | ❌ | Single HMM only |
