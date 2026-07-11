"""Market Making Strategy using the Avellaneda-Stoikov model.

Computes optimal bid and ask quotes that account for inventory
risk, order arrival dynamics, and market volatility.

References:
    Avellaneda, M. & Stoikov, S. (2008). High-Frequency Trading
    in a Limit Order Book. *Quantitative Finance*, 8(3), 217-224.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional

import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class MarketMakingStrategy(BaseStrategy):
    """Avellaneda-Stoikov market maker with inventory management.

    The reservation price shifts away from mid-price based on
    current inventory, risk aversion, and volatility.  Optimal
    bid/ask quotes are placed symmetrically around the reservation
    price with a spread governed by volatility and order arrival.

    Parameters
    ----------
    gamma : float
        Risk aversion coefficient (default 0.1).
    kappa : float
        Order arrival rate (default 1.5).
    sigma : float
        Volatility estimate (default 0.02).
    inventory_target : float
        Desired inventory level (default 0.0).
    max_inventory : float
        Maximum absolute position (default 100).
    order_size : float
        Base quote size per level (default 1.0).
    num_levels : int
        Quote depth on each side (default 1).
    spread_multiplier : float
        Scale factor applied to the base spread (default 1.0).
    transaction_cost_bps : float
        Round-trip transaction cost in basis points (default 10.0).
    min_trade_interval_bars : int
        Minimum bars between trade signals (default 1).
    symbol : str
        Trading symbol (default "ASSET").
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(name="MarketMaking", params=params)
        self.gamma: float = self.params.get("gamma", 0.1)
        self.kappa: float = self.params.get("kappa", 1.5)
        self.sigma: float = self.params.get("sigma", 0.02)
        self.inventory_target: float = self.params.get("inventory_target", 0.0)
        self.max_inventory: float = self.params.get("max_inventory", 100.0)
        self.order_size: float = self.params.get("order_size", 1.0)
        self.num_levels: int = self.params.get("num_levels", 1)
        self.spread_multiplier: float = self.params.get("spread_multiplier", 1.0)
        self.transaction_cost_bps: float = self.params.get("transaction_cost_bps", 10.0)
        self.min_trade_interval_bars: int = self.params.get("min_trade_interval_bars", 1)
        self.symbol: str = self.params.get("symbol", "ASSET")

        self._inventory: float = 0.0
        self._bars_since_trade: int = 0

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return 20

    # ------------------------------------------------------------------
    # Public helpers (called by the engine to sync state)
    # ------------------------------------------------------------------

    def update_inventory(self, filled_qty: float) -> None:
        """Update internal inventory after a fill."""
        self._inventory += filled_qty
        self._bars_since_trade = 0

    # ------------------------------------------------------------------
    # A-S core maths
    # ------------------------------------------------------------------

    def _reservation_price(self, mid: float, sigma: float, T: float = 1.0) -> float:
        """r = S - gamma * sigma^2 * q * T"""
        return mid - self.gamma * sigma ** 2 * self._inventory * T

    def _fee_adjustment(self) -> float:
        """(1/gamma) * ln(1 + gamma/kappa)"""
        return (1.0 / self.gamma) * math.log(1.0 + self.gamma / self.kappa)

    def _base_spread(self, sigma: float, T: float = 1.0) -> float:
        """gamma * sigma^2 * T, scaled by the user multiplier."""
        return self.gamma * sigma ** 2 * T * self.spread_multiplier

    # ponytail: inventory skew uses a simple linear taper, not a full A-S optimisation
    def _inv_skew(self) -> float:
        return (self._inventory - self.inventory_target) / max(self.max_inventory, 1.0)

    # ------------------------------------------------------------------
    # Quote construction
    # ------------------------------------------------------------------

    def _quote_levels(
        self, mid: float, sigma: float, T: float = 1.0
    ) -> List[Dict[str, float]]:
        """Build ``num_levels`` of bid/ask quotes.

        Returns a list of dicts, each containing:
            bid_price, ask_price, bid_size, ask_size
        """
        reservation = self._reservation_price(mid, sigma, T)
        spread = self._base_spread(sigma, T)
        fee = self._fee_adjustment()
        skew = self._inv_skew()

        levels: List[Dict[str, float]] = []
        for level in range(self.num_levels):
            # ponytail: level spacing is a fixed fraction of the base spread
            offset = level * spread * 0.5
            size = self.order_size * max(0.0, 1.0 - abs(skew) * 0.5)

            bid = reservation - spread / 2.0 - fee - offset
            ask = reservation + spread / 2.0 + fee + offset
            bid_sz = size * max(0.0, 1.0 - skew)
            ask_sz = size * max(0.0, 1.0 + skew)

            levels.append({
                "bid_price": round(bid, 6),
                "ask_price": round(ask, 6),
                "bid_size": round(bid_sz, 4),
                "ask_size": round(ask_sz, 4),
            })

        return levels

    def _estimate_sigma(self, data: pd.DataFrame) -> float:
        """Rolling 20-bar close-to-close volatility, falling back to param."""
        returns = data["close"].pct_change().dropna()
        if len(returns) < 5:
            return self.sigma  # ponytail: not enough data, use param default
        window = min(len(returns), 20)
        return max(float(returns.iloc[-window:].std()), 1e-8)

    # ------------------------------------------------------------------
    # Signal generation
    # ------------------------------------------------------------------

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None

        # Rate-limit: skip signal if we haven't waited long enough
        if self._bars_since_trade < self.min_trade_interval_bars - 1:
            self._bars_since_trade += 1
            return None

        mid = float(data["close"].iloc[-1])
        sigma = self._estimate_sigma(data)
        levels = self._quote_levels(mid, sigma)
        top = levels[0]

        self._bars_since_trade += 1

        return Signal(
            symbol=self.symbol,
            signal_type=SignalType.HOLD,
            confidence=0.5,
            price=round(mid, 6),
            source_agent=self.name,
            source_strategy=self.name,
            reasoning=(
                f"bid={top['bid_price']:.4f}@{top['bid_size']:.2f}, "
                f"ask={top['ask_price']:.4f}@{top['ask_size']:.2f}, "
                f"inv={self._inventory:.1f}/{self.max_inventory:.0f}"
            ),
            metadata={
                "bid_price": top["bid_price"],
                "ask_price": top["ask_price"],
                "bid_size": top["bid_size"],
                "ask_size": top["ask_size"],
                "reservation_price": round(
                    self._reservation_price(mid, sigma), 6
                ),
                "inventory": self._inventory,
                "sigma": round(sigma, 6),
                "spread": round(top["ask_price"] - top["bid_price"], 6),
                "num_levels": self.num_levels,
                "levels": levels,
            },
            factors=["market_making", "avellaneda_stoikov"],
        )
