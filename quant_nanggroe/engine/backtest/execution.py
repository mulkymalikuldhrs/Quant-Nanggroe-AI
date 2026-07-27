"""Simulated Execution with Slippage, Commission, and Market Impact.

Provides realistic execution simulation for backtests, supporting
multiple market types with appropriate fee structures.

Extracted from Vibe-Trading's execution model and Misi-Screener's broker simulation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np


@dataclass
class ExecutionConfig:
    """Configuration for execution simulation.

    Attributes:
        commission_rate: Commission rate as decimal (e.g. 0.001 = 0.1%).
        slippage_bps: Slippage in basis points (e.g. 5 = 0.05%).
        market: Market type string for market-specific rules.
        min_commission: Minimum commission per trade.
        market_impact_coeff: Market impact coefficient (0 = no impact).
    """

    commission_rate: float = 0.001
    slippage_bps: float = 5.0
    market: str = "equity"
    min_commission: float = 1.0
    market_impact_coeff: float = 0.0


class ExecutionSimulator:
    """Simulates realistic trade execution.

    Models slippage, commission, and market impact for backtests.
    Different markets have different default execution rules:

    - Equity: T+1 settlement, SEC fees, exchange fees
    - Crypto: 24/7, higher slippage, taker/maker fees
    - Forex: Spread-based, rollover fees
    - Futures: Contract multiplier, exchange fees
    """

    # Market-specific default configurations
    MARKET_DEFAULTS: Dict[str, Dict] = {
        "equity": {"commission_rate": 0.001, "slippage_bps": 5.0, "min_commission": 1.0},
        "crypto": {"commission_rate": 0.002, "slippage_bps": 10.0, "min_commission": 0.5},
        "forex": {"commission_rate": 0.0002, "slippage_bps": 2.0, "min_commission": 0.1},
        "futures": {"commission_rate": 0.0005, "slippage_bps": 3.0, "min_commission": 0.5},
    }

    def __init__(self, config: Optional[ExecutionConfig] = None) -> None:
        if config is None:
            config = ExecutionConfig()
        self.config = config

        # Apply market defaults only when the user did NOT change the field
        # from the base ExecutionConfig default (i.e. they didn't express a
        # preference).  If they set it explicitly, respect that order.
        defaults = self.MARKET_DEFAULTS.get(config.market, {})
        if config.commission_rate == ExecutionConfig().commission_rate and config.market != "equity":
            self._commission_rate = defaults.get("commission_rate", config.commission_rate)
        else:
            self._commission_rate = config.commission_rate

        if config.slippage_bps == ExecutionConfig().slippage_bps and config.market != "equity":
            self._slippage_bps = defaults.get("slippage_bps", config.slippage_bps)
        else:
            self._slippage_bps = config.slippage_bps

    def apply_slippage(self, price: float, direction: int) -> float:
        """Apply slippage to execution price.

        Slippage is always adverse:
        - Buying: price increases
        - Selling: price decreases

        Args:
            price: Raw market price.
            direction: 1 for buying, -1 for selling.

        Returns:
            Slipped execution price.
        """
        slippage_factor = self._slippage_bps / 10000.0
        if direction > 0:  # Buying → price goes up
            return price * (1.0 + slippage_factor)
        elif direction < 0:  # Selling → price goes down
            return price * (1.0 - slippage_factor)
        return price

    def calc_commission(
        self,
        size: float,
        price: float,
        is_closing: bool = False,
    ) -> float:
        """Calculate commission for a trade.

        Commission is calculated as:
        max(min_commission, commission_rate * trade_value)

        Args:
            size: Trade size in units.
            price: Execution price.
            is_closing: Whether this is a closing trade.

        Returns:
            Commission amount in currency.
        """
        trade_value = abs(size * price)
        commission = max(self.config.min_commission, self._commission_rate * trade_value)
        if is_closing:
            commission = commission * 0.5  # closing trades get 50% commission discount
        return commission

    def calc_market_impact(
        self,
        size: float,
        price: float,
        avg_volume: float = 1e6,
    ) -> float:
        """Calculate market impact cost.

        Market impact is modeled as a square-root function of participation rate:
        impact = coeff * sqrt(size / avg_volume) * price

        Args:
            size: Trade size.
            price: Current price.
            avg_volume: Average daily volume.

        Returns:
            Market impact cost in price terms.
        """
        if self.config.market_impact_coeff <= 0 or avg_volume <= 0:
            return 0.0

        participation_rate = abs(size) / avg_volume
        impact = self.config.market_impact_coeff * np.sqrt(participation_rate) * price
        return impact

    def simulate_fill(
        self,
        price: float,
        direction: int,
        size: float,
        avg_volume: float = 1e6,
    ) -> Dict[str, float]:
        """Simulate a complete order fill with all costs.

        Args:
            price: Raw market price.
            direction: 1 for buy, -1 for sell.
            size: Order size.
            avg_volume: Average daily volume for impact calculation.

        Returns:
            Dict with fill_price, commission, market_impact, total_cost.
        """
        slipped_price = self.apply_slippage(price, direction)
        commission = self.calc_commission(size, slipped_price)
        market_impact = self.calc_market_impact(size, price, avg_volume)

        # Total cost includes both slippage and market impact
        total_slippage = abs(slipped_price - price) * size
        total_cost = commission + total_slippage + market_impact * size

        return {
            "fill_price": slipped_price + (market_impact if direction > 0 else -market_impact),
            "commission": commission,
            "market_impact": market_impact * size,
            "slippage_cost": total_slippage,
            "total_cost": total_cost,
        }
