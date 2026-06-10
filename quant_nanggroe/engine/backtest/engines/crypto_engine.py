"""Crypto perpetual-contract backtest engine.

Market rules:
  - 24/7 trading, no restrictions on direction
  - Maker/Taker fee separation
  - Funding fee settlement every 8 hours (00:00/08:00/16:00 UTC)
  - Forced liquidation when maintenance margin ratio <= 100%
  - Fractional position sizes allowed

Ported from Vibe-Trading's ``CryptoEngine``.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Set

import pandas as pd

from quant_nanggroe.engine.backtest.engines.base_engine import BaseEngine

logger = logging.getLogger(__name__)

# ── OKX-style tiered maintenance margin table (simplified) ──

_TIER_TABLE = [
    (100_000, 0.004),
    (500_000, 0.006),
    (1_000_000, 0.01),
    (5_000_000, 0.02),
    (10_000_000, 0.05),
    (float("inf"), 0.10),
]

FUNDING_HOURS = {0, 8, 16}


def _maintenance_rate(notional_usd: float) -> float:
    """Look up tiered maintenance margin rate.

    Args:
        notional_usd: Position notional in USD.

    Returns:
        Maintenance margin rate.
    """
    for tier_max, rate in _TIER_TABLE:
        if notional_usd <= tier_max:
            return rate
    return _TIER_TABLE[-1][1]


def calc_crypto_funding_fee(
    symbol: str,
    bar: pd.Series,
    timestamp: pd.Timestamp,
    positions: Dict,
    funding_rate: float,
    applied_set: Set,
    daily_done_set: Set,
) -> float:
    """Calculate crypto funding fee for one symbol.

    Funding fees are charged every 8 hours (00:00/08:00/16:00 UTC).
    For daily data, a single daily funding fee is applied as fallback.

    Args:
        symbol: Instrument code.
        bar: Current bar data.
        timestamp: Bar timestamp.
        positions: Shared positions dict.
        funding_rate: Fixed rate per settlement.
        applied_set: ``(symbol, date, hour)`` dedup set — mutated.
        daily_done_set: ``(symbol, date)`` dedup set — mutated.

    Returns:
        Fee amount (positive = longs pay, negative = longs receive).
    """
    if not hasattr(timestamp, "date"):
        return 0.0

    current_date = timestamp.date()
    hour = timestamp.hour if hasattr(timestamp, "hour") else 0

    if hour in FUNDING_HOURS:
        key = (symbol, current_date, hour)
        if key in applied_set:
            return 0.0
        applied_set.add(key)
    else:
        # Daily fallback for daily bars
        day_key = (symbol, current_date)
        if day_key in daily_done_set:
            return 0.0
        daily_done_set.add(day_key)

    pos = positions.get(symbol)
    if pos is None:
        return 0.0

    mark_price = float(bar.get("close", pos.entry_price))
    notional = pos.size * mark_price
    return notional * funding_rate * pos.direction


def check_crypto_liquidation(
    symbol: str,
    bar: pd.Series,
    positions: Dict,
) -> bool:
    """Check if a crypto position should be liquidated.

    Uses tiered maintenance margin model. A position is liquidated
    when ``margin + unrealized <= maintenance_margin``.

    Args:
        symbol: Instrument code.
        bar: Current bar data.
        positions: Shared positions dict.

    Returns:
        True if liquidation should be triggered.
    """
    pos = positions.get(symbol)
    if pos is None or pos.leverage <= 1.0:
        return False

    mark_price = float(bar.get("close", pos.entry_price))
    margin = pos.size * pos.entry_price / pos.leverage
    unrealized = pos.direction * pos.size * (mark_price - pos.entry_price)

    notional = pos.size * mark_price
    maint_rate = _maintenance_rate(notional)
    maint_margin = notional * maint_rate

    return (margin + unrealized) <= maint_margin


class CryptoEngine(BaseEngine):
    """Crypto perpetual contract engine.

    Config keys:
      - ``leverage``: default 1.0
      - ``maker_rate``: default 0.0002
      - ``taker_rate``: default 0.0005
      - ``slippage``: default 0.0005
      - ``margin_mode``: ``"isolated"`` (default) or ``"cross"``
      - ``funding_rate``: fixed rate per settlement, default 0.0001
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        config = {**config, "leverage": config.get("leverage", 1.0)}
        super().__init__(config)
        self.maker_rate: float = float(config.get("maker_rate", 0.0002))
        self.taker_rate: float = float(config.get("taker_rate", 0.0005))
        self.slippage_rate: float = float(config.get("slippage", 0.0005))
        self.margin_mode: str = config.get("margin_mode", "isolated")
        self.funding_rate: float = float(config.get("funding_rate", 0.0001))
        self._funding_applied: Set = set()  # (symbol, date, hour) dedup
        self._funding_daily_done: Set = set()  # (symbol, date) dedup

    def _reset_state(self) -> None:
        """Reset engine state including funding fee tracking."""
        super()._reset_state()
        self._funding_applied = set()
        self._funding_daily_done = set()

    def can_execute(self, symbol: str, direction: int, bar: pd.Series) -> bool:
        """Crypto: 24/7, long/short/close all allowed."""
        return True

    def round_size(self, raw_size: float, price: float) -> float:
        """Crypto supports fractional sizes, round to 6 decimals."""
        return round(max(raw_size, 0.0), 6)

    def calc_commission(
        self, size: float, price: float, direction: int, is_open: bool
    ) -> float:
        """Maker/Taker separated.

        Opens typically hit taker, closes hit maker.
        """
        rate = self.taker_rate if is_open else self.maker_rate
        return size * price * rate

    def apply_slippage(self, price: float, direction: int) -> float:
        """Slippage: unfavourable direction."""
        return price * (1 + direction * self.slippage_rate)

    def on_bar(self, symbol: str, bar: pd.Series, timestamp: pd.Timestamp) -> None:
        """Crypto per-bar hooks: funding fee + liquidation check."""
        # Apply funding fee
        fee = calc_crypto_funding_fee(
            symbol,
            bar,
            timestamp,
            self.positions,
            self.funding_rate,
            self._funding_applied,
            self._funding_daily_done,
        )
        self.capital -= fee

        # Check liquidation
        if check_crypto_liquidation(symbol, bar, self.positions):
            pos = self.positions.get(symbol)
            if pos is not None:
                mark_price = float(bar.get("close", pos.entry_price))
                liq_price = self.apply_slippage(mark_price, -pos.direction)
                self._close_position(symbol, liq_price, timestamp, "liquidation")
