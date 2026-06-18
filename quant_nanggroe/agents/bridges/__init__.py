"""Bridges between the deterministic engine layer and the LLM agent layer.

These bridges connect the LangGraph agent pipeline to the deterministic
risk engine, ensuring that the 9-checkpoint RiskCheckGate is always
invoked as the FINAL mandatory gate before any trade is executed.

Architecture:
    Agent Pipeline (LLM)  -->  Bridge  -->  Deterministic Engine

    risk_assessment (LLM) --> RiskGateBridge --> RiskCheckGate (9 checkpoints)
    signal_generation (LLM) --> KellyBridge --> KellyCriterion (position sizing)

CRITICAL RULES:
- The deterministic RiskCheckGate is a HARD GATE — it CANNOT be bypassed.
- If both the LLM risk agent and deterministic gate disagree, the
  deterministic gate WINS.
- The LLM risk agent provides qualitative analysis; the deterministic
  gate provides the FINAL quantitative veto/approval.
"""

from quant_nanggroe.agents.bridges.risk_gate_bridge import RiskGateBridge
from quant_nanggroe.agents.bridges.kelly_bridge import KellyBridge

__all__ = ["RiskGateBridge", "KellyBridge"]
