"""
Quant Nanggroe AI — Agentic Trading Intelligence OS

A production-grade multi-agent trading framework using LangGraph for
orchestration, MCP protocol for tool integration, and constitutional
risk management with 9-checkpoint gates.

Architecture:
    Agents Layer  — 9 specialized agents (Researcher, Trader, Strategist,
                    Risk, Portfolio, Execution, Macro, Crypto, Forex)
    Engine Layer  — Backtest, Execution, Factors, Risk, Models
    Memory Layer  — Letta-style paging, Knowledge Graph, Journal
    Data Layer    — Multi-provider with failover, CCXT exchange abstraction
    MCP Layer     — Model Context Protocol for tool integration
    API/CLI Layer — FastAPI server, Click CLI, WebSocket streaming

Constitutional Risk Limits (HARDCODED — no override):
    Max risk per trade:    0.5%
    Max daily loss:        1.0%
    Max weekly loss:       3.0%
    Min risk:reward:       1:2
    Max position size:     10%
    Max leverage:          3x
    Max drawdown:          15% (kill switch)
    Max trades/day:        5
"""

__version__ = "5.1.0"  # ponytail: keep in sync with pyproject.toml
__author__ = "Quant Nanggroe AI Team"
QNA_VERSION = __version__
