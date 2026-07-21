"""
Jeumpa - AI Intelligence Orchestration Layer

Production-ready AI orchestrator that decides between:
1. Answering directly (fast, cost-effective)
2. Orchestrating models, agents, tools, workflows (complex tasks)

Key principles:
- Single API endpoint for users
- Lazy runtime: active only when called, not 24/7
- Memory efficient: minimal idle footprint  
- Free model integration prioritized
- Hermes fallback integration
- Intelligent task routing (answer vs orchestrate)
"""

from jeumpa.core.decision_engine import DecisionEngine
from jeumpa.core.runtime import JeumpaRuntime
from jeumpa.adapters.registry import AdapterRegistry
from jeumpa.integrations import HermesIntegration

__all__ = [
    "DecisionEngine",
    "JeumpaRuntime", 
    "AdapterRegistry",
    "HermesIntegration",
]