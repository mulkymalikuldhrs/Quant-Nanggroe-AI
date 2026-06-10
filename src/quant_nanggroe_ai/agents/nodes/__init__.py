"""
Agent Nodes Package — LangGraph Trading Graph Nodes
====================================================
Each node is an async function that accepts ``AgentState`` and returns
a ``dict[str, Any]`` that updates the shared state.

Core Flow:  Researcher → Macro → Analyst → Strategist → RiskManager → Trader → Portfolio

Extended Nodes:
  - Crypto: Mempool monitoring, DEX sniper & anti-rug protection
  - Forex: Currency pair analysis, carry trade identification, CB tracking
  - Execution: Smart order routing, multi-venue execution, latency monitoring
  - PredictionMarket: Polymarket/Kalshi integration, cross-market hedging

All nodes are importable from this package for graph construction.
"""

from quant_nanggroe_ai.agents.nodes.researcher import researcher_node
from quant_nanggroe_ai.agents.nodes.macro import macro_node
from quant_nanggroe_ai.agents.nodes.analyst import analyst_node
from quant_nanggroe_ai.agents.nodes.strategist import strategist_node
from quant_nanggroe_ai.agents.nodes.risk_manager import risk_manager_node
from quant_nanggroe_ai.agents.nodes.trader import trader_node
from quant_nanggroe_ai.agents.nodes.portfolio import portfolio_node
from quant_nanggroe_ai.agents.nodes.crypto import crypto_node
from quant_nanggroe_ai.agents.nodes.forex import forex_node
from quant_nanggroe_ai.agents.nodes.execution import execution_node
from quant_nanggroe_ai.agents.nodes.prediction_market import prediction_market_node

__all__ = [
    "researcher_node",
    "macro_node",
    "analyst_node",
    "strategist_node",
    "risk_manager_node",
    "trader_node",
    "portfolio_node",
    "crypto_node",
    "forex_node",
    "execution_node",
    "prediction_market_node",
]
