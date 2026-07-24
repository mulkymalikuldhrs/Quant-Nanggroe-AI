"""Shadow trading — execute opposing strategies in paper mode for A/B comparison.

ShadowTrader records paper trades alongside real execution to compare
strategy performance without financial risk.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ShadowTrade:
    symbol: str
    entry_price: float
    exit_price: Optional[float] = None
    side: str = ""
    quantity: float = 0.0
    entry_time: datetime = field(default_factory=datetime.now)
    exit_time: Optional[datetime] = None
    pnl: float = 0.0
    strategy: str = ""


class ShadowTrader:
    def __init__(self):
        self._trades: List[ShadowTrade] = []
        self._real_pnl: Dict[str, float] = {}

    def record_shadow(self, signal, price: float, quantity: float = 1.0) -> None:
        trade = ShadowTrade(
            symbol=signal.symbol if hasattr(signal, "symbol") else "unknown",
            side=signal.direction if hasattr(signal, "direction") else "buy",
            entry_price=price,
            quantity=quantity,
            strategy=signal.strategy if hasattr(signal, "strategy") else "",
        )
        self._trades.append(trade)
        logger.info("Shadow trade recorded: %s %s @ %.2f", trade.side, trade.symbol, trade.entry_price)

    def close_shadow(self, symbol: str, exit_price: float) -> Optional[ShadowTrade]:
        for trade in reversed(self._trades):
            if trade.symbol == symbol and trade.exit_price is None:
                trade.exit_price = exit_price
                trade.exit_time = datetime.now()
                trade.pnl = (exit_price - trade.entry_price) * trade.quantity
                if trade.side == "sell":
                    trade.pnl = -trade.pnl
                logger.info("Shadow trade closed: %s PnL=%.2f", symbol, trade.pnl)
                return trade
        return None

    def compare_performance(self) -> Dict[str, float]:
        shadow_pnl = sum(t.pnl for t in self._trades if t.exit_price is not None)
        real_pnl = sum(self._real_pnl.values())
        return {
            "shadow_pnl": shadow_pnl,
            "real_pnl": real_pnl,
            "difference": shadow_pnl - real_pnl,
            "shadow_trades": len(self._trades),
            "closed_shadow_trades": sum(1 for t in self._trades if t.exit_price is not None),
        }

    @property
    def trades(self) -> List[ShadowTrade]:
        return list(self._trades)
