"""
Agent Nodes Package — LangGraph Trading Graph Nodes
====================================================
Each node is an async function that accepts ``AgentState`` and returns
a ``dict[str, Any]`` that updates the shared state.

Flow:  Researcher → Macro → Analyst → Strategist → RiskManager → Trader → Portfolio

All nodes are importable from this package for graph construction.
"""

from quant_nanggroe_ai.agents.nodes.researcher import researcher_node
from quant_nanggroe_ai.agents.nodes.macro import macro_node
from quant_nanggroe_ai.agents.nodes.analyst import analyst_node
from quant_nanggroe_ai.agents.nodes.strategist import strategist_node
from quant_nanggroe_ai.agents.nodes.risk_manager import risk_manager_node
from quant_nanggroe_ai.agents.nodes.trader import trader_node
from quant_nanggroe_ai.agents.nodes.portfolio import portfolio_node

__all__ = [
    "researcher_node",
    "macro_node",
    "analyst_node",
    "strategist_node",
    "risk_manager_node",
    "trader_node",
    "portfolio_node",
]
