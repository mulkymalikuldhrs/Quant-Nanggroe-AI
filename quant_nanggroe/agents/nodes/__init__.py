"""
Graph Node Modules for Quant Nanggroe AI Trading Framework v2.

Specialized node implementations for the enhanced multi-path trading graph.
Each module encapsulates a discrete piece of graph logic:
  - Asset routing and class detection
  - ATR-based position sizing with TP1/TP2/TP3 geometry
  - Portfolio concentration / correlation / Kelly validation
  - Smart order routing with venue scoring
  - Human-in-the-loop approval checkpoint
"""

from quant_nanggroe.agents.nodes.asset_router import (
    AssetRouter,
    detect_asset_class,
    route_by_asset_class,
)
from quant_nanggroe.agents.nodes.position_sizer import (
    PositionSizer,
    compute_atr_position_sizing,
)
from quant_nanggroe.agents.nodes.portfolio_validator import (
    PortfolioValidator,
    validate_portfolio,
)
from quant_nanggroe.agents.nodes.smart_executor import (
    SmartExecutor,
    route_order_smart,
)
from quant_nanggroe.agents.nodes.human_checkpoint import (
    HumanCheckpoint,
    check_human_approval,
)

__all__ = [
    # Asset routing
    "AssetRouter",
    "detect_asset_class",
    "route_by_asset_class",
    # Position sizing
    "PositionSizer",
    "compute_atr_position_sizing",
    # Portfolio validation
    "PortfolioValidator",
    "validate_portfolio",
    # Smart execution
    "SmartExecutor",
    "route_order_smart",
    # Human checkpoint
    "HumanCheckpoint",
    "check_human_approval",
]
