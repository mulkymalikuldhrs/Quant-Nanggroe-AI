"""Algorithmic Execution Engine — TWAP & VWAP Order Slicing.

Provides institutional execution algorithms to slice large orders over time or volume
profiles, minimizing market impact and slippage.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SliceOrder:
    slice_id: str
    symbol: str
    side: str
    quantity: float
    target_time: float
    executed: bool = False
    executed_price: Optional[float] = None
    executed_qty: float = 0.0


class TWAPExecutionEngine:
    """Time-Weighted Average Price (TWAP) Order Slicer.

    Slices a parent order into equal child slices distributed evenly over a specified duration window.
    """

    def __init__(self, duration_minutes: float = 30.0, num_slices: int = 6):
        self.duration_minutes = duration_minutes
        self.num_slices = max(1, num_slices)

    def slice_order(self, symbol: str, side: str, total_quantity: float) -> List[SliceOrder]:
        """Create TWAP slice schedule for a parent order."""
        if total_quantity <= 0:
            return []

        slice_qty = round(total_quantity / self.num_slices, 8)
        interval_seconds = (self.duration_minutes * 60.0) / self.num_slices
        start_time = time.time()

        slices = []
        for i in range(self.num_slices):
            target_time = start_time + (i * interval_seconds)
            # Adjust last slice for rounding precision
            if i == self.num_slices - 1:
                qty = round(total_quantity - (slice_qty * (self.num_slices - 1)), 8)
            else:
                qty = slice_qty

            slices.append(
                SliceOrder(
                    slice_id=f"twap_{symbol}_{i+1}_{int(target_time)}",
                    symbol=symbol,
                    side=side,
                    quantity=qty,
                    target_time=target_time,
                )
            )
        logger.info("Created %d TWAP slices for %s %s %f", len(slices), side, symbol, total_quantity)
        return slices


class VWAPExecutionEngine:
    """Volume-Weighted Average Price (VWAP) Order Slicer.

    Slices a parent order according to an expected intraday volume profile curve.
    """

    def __init__(self, volume_profile: Optional[List[float]] = None):
        # Default U-shaped volume curve (higher at open/close, lower at midday)
        self.volume_profile = volume_profile or [0.25, 0.15, 0.10, 0.10, 0.15, 0.25]

    def slice_order(self, symbol: str, side: str, total_quantity: float, duration_minutes: float = 30.0) -> List[SliceOrder]:
        """Create VWAP volume-proportional slice schedule."""
        if total_quantity <= 0:
            return []

        total_weight = sum(self.volume_profile)
        num_slices = len(self.volume_profile)
        interval_seconds = (duration_minutes * 60.0) / num_slices
        start_time = time.time()

        slices = []
        allocated = 0.0
        for i, weight in enumerate(self.volume_profile):
            target_time = start_time + (i * interval_seconds)
            if i == num_slices - 1:
                qty = round(total_quantity - allocated, 8)
            else:
                qty = round(total_quantity * (weight / total_weight), 8)
                allocated += qty

            slices.append(
                SliceOrder(
                    slice_id=f"vwap_{symbol}_{i+1}_{int(target_time)}",
                    symbol=symbol,
                    side=side,
                    quantity=qty,
                    target_time=target_time,
                )
            )
        logger.info("Created %d VWAP slices for %s %s %f", len(slices), side, symbol, total_quantity)
        return slices
