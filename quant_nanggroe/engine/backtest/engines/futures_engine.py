"""Futures backtest engine with contract-multiplier support.

Adds contract-multiplier awareness on top of BaseEngine. The multiplier
affects:
  - P&L: direction * size * multiplier * (exit - entry)
  - Margin: size * price * multiplier / leverage
  - Position sizing: target_notional / (price * multiplier)

Also provides common futures market rules:
  - Contract multiplier varies by product
  - Exchange fees per contract
  - Margin requirements
  - Price limits and trading halts

Ported from Vibe-Trading's ``FuturesBaseEngine`` and global futures engine.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

import pandas as pd

from quant_nanggroe.engine.backtest.engines.base_engine import BaseEngine

logger = logging.getLogger(__name__)

# ── Known contract multipliers ──

_CN_FUTURES_MULTIPLIERS: Dict[str, float] = {
    # CFFEX financial futures
    "IF": 300, "IC": 200, "IH": 300, "IM": 200,
    "T": 10000, "TF": 10000, "TS": 20000, "TL": 10000,
    # SHFE
    "AU": 1000, "AG": 15, "CU": 5, "AL": 5, "ZN": 5,
    "PB": 5, "NI": 1, "SN": 1, "SS": 5,
    "RB": 10, "HC": 10, "I": 100, "J": 100, "JM": 60,
    "SC": 1000, "FU": 10, "LU": 10, "BU": 10, "NR": 10,
    # DCE
    "C": 10, "CS": 10, "M": 10, "Y": 10, "A": 10,
    "P": 10, "JD": 10, "LH": 16,
    # ZCE
    "CF": 5, "SR": 10, "TA": 5, "MA": 10, "AP": 10,
    "RM": 10, "OI": 10, "SA": 20, "FG": 20, "UR": 20,
    # DCE / ZCE chemicals
    "PP": 5, "L": 5, "V": 5, "EG": 10, "EB": 5, "PF": 5,
    # INE / GFEX
    "SI": 5, "LC": 1,
}

_GLOBAL_FUTURES_MULTIPLIERS: Dict[str, float] = {
    # CME Group
    "ES": 50, "NQ": 20, "YM": 5, "RTY": 50,
    "CL": 1000, "HO": 42000, "RB": 42000, "NG": 10000,
    "GC": 100, "SI": 5000, "HG": 25000, "PL": 50,
    "ZC": 100, "ZW": 5000, "ZS": 5000, "ZM": 500, "ZL": 600,
    "TY": 1000, "FV": 1000, "TU": 2000, "UB": 1000,
    # ICE
    "CT": 50, "SB": 1120, "KC": 375, "CC": 10,
    # Eurex
    "FDAX": 25, "FGBL": 1000, "FESX": 10,
}


def _extract_product(code: str) -> str:
    """Extract product code from futures symbol.

    Handles formats like:
      - ``IF2406.CFFEX`` → ``IF``
      - ``ESZ4`` → ``ES``
      - ``rb2410.SHFE`` → ``rb``
      - ``CL2412`` → ``CL``

    Args:
        code: Futures symbol string.

    Returns:
        Product code string (uppercase).
    """
    # Remove exchange suffix first
    base = code.split(".")[0] if "." in code else code

    # Try to match product prefix (letters) followed by digits
    import re
    m = re.match(r"([A-Za-z]+)\d+", base)
    if m:
        return m.group(1).upper()
    return base.upper()


class FuturesEngine(BaseEngine):
    """Futures engine with contract-multiplier support.

    Config keys:
      - ``leverage``: default 10.0
      - ``commission_per_contract``: per-contract commission, default 0.0
      - ``commission_rate``: rate-based commission, default 0.00005
      - ``slippage``: default 0.0003
      - ``margin_rate``: margin as fraction of notional, default 0.1
      - ``multipliers``: optional dict of symbol -> multiplier overrides

    The engine auto-detects contract multipliers from the product code.
    Override with ``config["multipliers"]`` for custom products.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        config = {**config, "leverage": config.get("leverage", 10.0)}
        super().__init__(config)
        self.commission_per_contract: float = float(
            config.get("commission_per_contract", 0.0)
        )
        self.commission_rate: float = float(config.get("commission_rate", 0.00005))
        self.slippage_rate: float = float(config.get("slippage", 0.0003))
        self.margin_rate: float = float(config.get("margin_rate", 0.1))
        # User overrides for multipliers
        self._custom_multipliers: Dict[str, float] = config.get("multipliers", {})
        # Cache for product -> multiplier lookups to avoid repeated regex/warnings
        self._multiplier_cache: Dict[str, float] = {}

    def get_contract_multiplier(self, symbol: str) -> float:
        """Contract multiplier for the instrument.

        Looks up from custom overrides first, then from known tables.

        Args:
            symbol: Futures symbol (e.g. 'IF2406.CFFEX', 'ESZ4').

        Returns:
            Points-to-currency multiplier (e.g. IF=300, ES=50).
            Default 1.0 if unknown.
        """
        # User override
        if symbol in self._custom_multipliers:
            return self._custom_multipliers[symbol]

        # Check cache
        if symbol in self._multiplier_cache:
            return self._multiplier_cache[symbol]

        product = _extract_product(symbol)

        # Check Chinese futures table
        if product in _CN_FUTURES_MULTIPLIERS:
            result = _CN_FUTURES_MULTIPLIERS[product]
            self._multiplier_cache[symbol] = result
            return result

        # Check global futures table
        if product in _GLOBAL_FUTURES_MULTIPLIERS:
            result = _GLOBAL_FUTURES_MULTIPLIERS[product]
            self._multiplier_cache[symbol] = result
            return result

        logger.debug(
            "Unknown futures product %s (symbol %s), using multiplier=1.0",
            product, symbol,
        )
        self._multiplier_cache[symbol] = 1.0
        return 1.0

    # ── Override P&L / margin / sizing to include multiplier ──

    def _calc_pnl(
        self,
        symbol: str,
        direction: int,
        size: float,
        entry_price: float,
        exit_price: float,
    ) -> float:
        """P&L with contract multiplier: direction * size * cm * (exit - entry)."""
        cm = self.get_contract_multiplier(symbol)
        return direction * size * cm * (exit_price - entry_price)

    def _calc_margin(
        self,
        symbol: str,
        size: float,
        price: float,
        leverage: float,
    ) -> float:
        """Margin with contract multiplier: size * price * cm / leverage."""
        cm = self.get_contract_multiplier(symbol)
        return size * price * cm / leverage

    def _calc_raw_size(
        self,
        symbol: str,
        target_notional: float,
        price: float,
    ) -> float:
        """Position sizing with contract multiplier: target_notional / (price * cm)."""
        cm = self.get_contract_multiplier(symbol)
        return target_notional / (price * cm)

    # ── Market rule interface ──

    def can_execute(self, symbol: str, direction: int, bar: pd.Series) -> bool:
        """Futures: long/short/close allowed. Price limit checks are optional."""
        return True

    def round_size(self, raw_size: float, price: float) -> float:
        """Futures: round to integer number of contracts."""
        return max(int(raw_size), 0)

    def calc_commission(
        self, size: float, price: float, direction: int, is_open: bool
    ) -> float:
        """Futures commission: per-contract fee + rate-based fee.

        Args:
            size: Number of contracts.
            price: Execution price.
            direction: Trade direction.
            is_open: Opening or closing trade.

        Returns:
            Commission amount.
        """
        cm = self.get_contract_multiplier(self._active_symbol)
        notional = size * price * cm

        # Per-contract commission
        comm = abs(size) * self.commission_per_contract

        # Rate-based commission
        comm += notional * self.commission_rate

        return comm

    def apply_slippage(self, price: float, direction: int) -> float:
        """Futures slippage: unfavourable direction."""
        return price * (1 + direction * self.slippage_rate)

    def on_bar(self, symbol: str, bar: pd.Series, timestamp: pd.Timestamp) -> None:
        """No special per-bar hooks for futures (settlement is handled at close)."""
        pass
