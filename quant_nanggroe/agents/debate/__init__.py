"""Debate engine: council, reflection, and multi-agent debate."""

# Package init

__all__ = [
    'council_logger',
    'engine',
    'graph',
    'reflection',
    'research_debate',
    'risk_debate',
]

from . import council_logger
from . import engine
from .engine import Signal, AgentOpinion, RiskMetrics, RiskManager, DebateResult, DebateEngine
from . import graph
from . import reflection
from . import research_debate
from . import risk_debate
