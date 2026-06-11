"""Colony subpackage for the Multi-Colony Ecosystem.

This subpackage provides colony configuration, lifecycle management,
and task routing capabilities.
"""

from quant_nanggroe_ai.multicolony.colony.config import (
    AgentConfig,
    ColonyConfig,
    ColonyType,
    DEFAULT_LLM_FAILOVER_CHAIN,
    SecurityLevel,
)
from quant_nanggroe_ai.multicolony.colony.lifecycle import (
    ColonyLifecycle,
    ColonyState,
    ColonyStatus,
    InvalidStateTransition,
    VALID_TRANSITIONS,
)
from quant_nanggroe_ai.multicolony.colony.router import (
    CATEGORY_COLONY_MAP,
    ColonyInfo,
    ColonyRouter,
    NoAvailableColonyError,
    RoutingDecision,
    TaskPriority,
    TaskRequest,
)

__all__ = [
    "AgentConfig",
    "CATEGORY_COLONY_MAP",
    "ColonyConfig",
    "ColonyInfo",
    "ColonyLifecycle",
    "ColonyRouter",
    "ColonyState",
    "ColonyStatus",
    "ColonyType",
    "DEFAULT_LLM_FAILOVER_CHAIN",
    "InvalidStateTransition",
    "NoAvailableColonyError",
    "RoutingDecision",
    "SecurityLevel",
    "TaskPriority",
    "TaskRequest",
    "VALID_TRANSITIONS",
]
