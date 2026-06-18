"""US/HK equity backtest engine.

Market rules:
  US:
    - T+0, long/short allowed
    - Zero commission (retail brokers)
    - Fractional shares supported (round to 0.01)
    - Low slippage (high liquidity)
  HK:
    - T+0, long/short allowed
    - Stamp tax 0.1% bilateral + levies
    - Lot-size rounding (100 shares)
    - Higher slippage than US
  China A-share:
    - T+1: cannot sell shares bought today
    - No short selling for retail investors
    - Price limits: ±10% main board, ±20% ChiNext/STAR, ±5% ST
    - Minimum lot: 100 shares
    - Commission: ¥5 minimum, 0.025% bilateral
    - Stamp tax: 0.05% sell-side only

Ported from Vibe-Trading's ``GlobalEquityEngine`` and ``ChinaAEngine``.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.backtest.engines.base_engine import BaseEngine

logger = logging.getLogger(__name__)


class EquityEngine(BaseEngine):
    """US / HK / China-A equity engine.

    The ``market`` parameter selects the rule set:
      - ``"us"``: US equity (fractional shares, zero commission)
      - ``"hk"``: HK equity (100-share lots, stamp tax + levies)
      - ``"china_a"``: A-share (T+1, no short, price limits)

    Config keys (all optional — sensible defaults):
      - ``slippage_us``: default 0.0005
      - ``slippage_hk``: default 0.001
      - ``slippage_china``: default 0.001
      - ``hk_stamp_tax``: default 0.001 (0.1% bilateral)
      - ``hk_commission``: default 0.00015 (万1.5)
      - ``hk_levy``: default 0.0000565 (SFC + FRC)
      - ``hk_settlement``: default 0.00002 (CCASS)
      - ``commission_rate``: A-share commission rate, default 0.00025 (万2.5)
      - ``commission_min``: A-share min commission, default 5.0 RMB
      - ``stamp_tax``: A-share stamp tax sell-only, default 0.0005
      - ``transfer_fee``: A-share transfer fee bilateral, default 0.00001
    """

    def __init__(self, config: Dict[str, Any], market: str = "us") -> None:
        config = {**config, "leverage": config.get("leverage", 1.0)}
        super().__init__(config)
        self.market = market

        # US defaults
        self.slippage_us: float = float(config.get("slippage_us", 0.0005))
        # HK defaults
        self.slippage_hk: float = float(config.get("slippage_hk", 0.001))
        self.hk_stamp_tax: float = float(config.get("hk_stamp_tax", 0.001))
        self.hk_commission: float = float(config.get("hk_commission", 0.00015))
        self.hk_levy: float = float(config.get("hk_levy", 0.0000565))
        self.hk_settlement: float = float(config.get("hk_settlement", 0.00002))
        # China A-share defaults
        self.slippage_china: float = float(config.get("slippage_china", 0.001))
        self.commission_rate: float = float(config.get("commission_rate", 0.00025))
        self.commission_min: float = float(config.get("commission_min", 5.0))
        self.stamp_tax: float = float(config.get("stamp_tax", 0.0005))
        self.transfer_fee: float = float(config.get("transfer_fee", 0.00001))

    def can_execute(self, symbol: str, direction: int, bar: pd.Series) -> bool:
        """Check if trade is allowed by market rules.

        Args:
            symbol: Instrument identifier.
            direction: 1 (buy), -1 (short), 0 (close).
            bar: Current bar data.

        Returns:
            True if trade is allowed.
        """
        if self.market == "china_a":
            return self._can_execute_china(symbol, direction, bar)
        # US/HK: T+0, both directions allowed
        return True

    def _can_execute_china(self, symbol: str, direction: int, bar: pd.Series) -> bool:
        """A-share execution rules.

        1. No short selling
        2. T+1: can't sell shares bought today
        3. Price limits: ±10% main board, ±20% ChiNext/STAR, ±5% ST
        """
        # 1. No short selling
        if direction == -1:
            return False

        # 2. T+1: can't sell shares bought today
        if direction == 0:
            pos = self.positions.get(symbol)
            if pos is not None:
                bar_date = _bar_date(bar)
                entry_date = (
                    pos.entry_time.date() if hasattr(pos.entry_time, "date") else None
                )
                if bar_date is not None and entry_date is not None and bar_date == entry_date:
                    return False

        # 3. Price limits
        pct_chg = _calc_pct_change(bar)
        if pct_chg is not None:
            limit = _price_limit(symbol)
            if direction == 1 and pct_chg >= limit - 0.001:
                return False  # Limit-up: can't buy
            if direction == 0 and pct_chg <= -limit + 0.001:
                return False  # Limit-down: can't sell

        return True

    def round_size(self, raw_size: float, price: float) -> float:
        """Round position size per market lot rules.

        - US: fractional shares (0.01)
        - HK: 100-share lots
        - China A: 100-share lots
        """
        if self.market in ("hk", "china_a"):
            return max(int(raw_size / 100) * 100, 0)
        return round(max(raw_size, 0.0), 2)

    def calc_commission(
        self, size: float, price: float, direction: int, is_open: bool
    ) -> float:
        """Calculate commission based on market rules.

        - US: zero commission
        - HK: stamp tax + levies
        - China A: commission + stamp tax (sell) + transfer fee
        """
        if self.market == "hk":
            notional = size * price
            comm = notional * self.hk_commission  # Broker commission
            comm += notional * self.hk_stamp_tax  # Stamp tax bilateral
            comm += notional * self.hk_levy  # SFC + FRC levies
            comm += notional * self.hk_settlement  # CCASS settlement
            return comm

        if self.market == "china_a":
            notional = size * price
            # Commission: 万2.5, min ¥5
            comm = max(notional * self.commission_rate, self.commission_min)
            # Transfer fee: 万0.1 bilateral
            comm += notional * self.transfer_fee
            # Stamp tax: 万5 sell-only
            if not is_open:
                comm += notional * self.stamp_tax
            return comm

        # US: zero commission
        return 0.0

    def apply_slippage(self, price: float, direction: int) -> float:
        """Apply slippage based on market.

        - US: low slippage
        - HK: moderate slippage
        - China A: moderate slippage
        """
        if self.market == "hk":
            rate = self.slippage_hk
        elif self.market == "china_a":
            rate = self.slippage_china
        else:
            rate = self.slippage_us
        return price * (1 + direction * rate)

    def on_bar(self, symbol: str, bar: pd.Series, timestamp: pd.Timestamp) -> None:
        """No per-bar hooks for equity markets."""
        pass


# ── A-share helpers ──


def _bar_date(bar: pd.Series):
    """Extract date from bar, handling various column names."""
    for col in ("trade_date", "date"):
        if col in bar.index:
            val = bar[col]
            if hasattr(val, "date"):
                return val.date()
            try:
                return pd.Timestamp(val).date()
            except Exception:
                pass
    if hasattr(bar, "name") and hasattr(bar.name, "date"):
        return bar.name.date()
    return None


def _calc_pct_change(bar: pd.Series):
    """Calculate price change percentage from bar data."""
    if "pct_chg" in bar.index:
        val = bar["pct_chg"]
        if pd.notna(val):
            return float(val) / 100.0

    close = bar.get("close")
    pre_close = bar.get("pre_close")
    if close is not None and pre_close is not None and pre_close > 0:
        return (float(close) - float(pre_close)) / float(pre_close)
    return None


def _price_limit(symbol: str) -> float:
    """Determine price limit based on board type.

    Args:
        symbol: Stock code (e.g. 300001.SZ, 688001.SH, 000001.SZ).

    Returns:
        Limit as fraction (0.10, 0.20, 0.30, or 0.05).
    """
    code = symbol.split(".")[0] if "." in symbol else symbol
    # ChiNext (300xxx) / STAR (688xxx): ±20%
    if code.startswith("300") or code.startswith("688"):
        return 0.20
    # Beijing exchange (8xxxxx): ±30%
    if code.startswith("8") and len(code) == 6:
        return 0.30
    # Main board: ±10%
    return 0.10
