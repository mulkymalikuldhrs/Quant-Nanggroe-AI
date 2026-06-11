"""Execution Engine for Quant-Nanggroe-AI.

Provides a unified execution layer supporting multiple brokers
and smart order routing with guard pipelines.

Supported Brokers:
- Alpaca (US stocks)
- CCXT (100+ crypto exchanges)
- Binance (direct API)
- Paper trading with realistic simulation

Guard Pipeline (from OpenAlice):
- Cooldown guard: Prevent rapid-fire trades
- Max position guard: Limit position concentration
- Symbol whitelist guard: Only trade approved symbols
"""

from quant_nanggroe.engine.execution.base import Broker, Order, OrderType, OrderSide, Fill
from quant_nanggroe.engine.execution.manager import ExecutionManager
from quant_nanggroe.engine.execution.order import OrderManager
from quant_nanggroe.engine.execution.fill import FillTracker

__all__ = [
    "Broker",
    "Order",
    "OrderType",
    "OrderSide",
    "Fill",
    "ExecutionManager",
    "OrderManager",
    "FillTracker",
]
