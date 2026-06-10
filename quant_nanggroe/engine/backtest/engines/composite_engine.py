"""Composite cross-market backtest engine.

Manages a shared capital pool across multiple market engines.
Sub-engines are used as stateless "rule books" for market-specific
calculations (commission, slippage, lot rounding, etc.).
All state (capital, positions, trades) lives in CompositeEngine.

Ported from Vibe-Trading's ``CompositeEngine``.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set

import pandas as pd

from quant_nanggroe.engine.backtest.engines.base_engine import BaseEngine
from quant_nanggroe.engine.backtest.engines.equity_engine import EquityEngine
from quant_nanggroe.engine.backtest.engines.crypto_engine import (
    CryptoEngine,
    calc_crypto_funding_fee,
    check_crypto_liquidation,
)
from quant_nanggroe.engine.backtest.engines.forex_engine import (
    ForexEngine,
    calc_forex_swap,
)
from quant_nanggroe.engine.backtest.engines.futures_engine import FuturesEngine
from quant_nanggroe.engine.backtest.engines.market_detection import (
    detect_market,
    detect_submarket,
    is_china_futures,
)

logger = logging.getLogger(__name__)


def _build_rule_engines(
    config: Dict[str, Any], codes: List[str]
) -> Dict[str, BaseEngine]:
    """Instantiate one sub-engine per market type detected in codes.

    Sub-engines are stateless rule providers — they don't hold their own
    capital, positions, or trades. All state lives in CompositeEngine.

    Args:
        config: Backtest configuration dict.
        codes: List of instrument codes.

    Returns:
        Mapping of market type -> engine instance.
    """
    markets = {detect_market(c) for c in codes}
    engines: Dict[str, BaseEngine] = {}

    for market in markets:
        if market == "a_share":
            engines["a_share"] = EquityEngine(config, market="china_a")
        elif market == "us_equity":
            engines["us_equity"] = EquityEngine(config, market="us")
        elif market == "hk_equity":
            engines["hk_equity"] = EquityEngine(config, market="hk")
        elif market == "crypto":
            engines["crypto"] = CryptoEngine(config)
        elif market == "forex":
            engines["forex"] = ForexEngine(config)
        elif market == "futures":
            engines["futures"] = FuturesEngine(config)

    return engines


class CompositeEngine(BaseEngine):
    """Cross-market engine with shared capital pool.

    Sub-engines are stateless rule providers. All positions, capital,
    and trades live here (inherited from BaseEngine).

    Args:
        config: Backtest configuration dict.
        codes: List of instrument codes spanning multiple markets.
    """

    def __init__(
        self, config: Dict[str, Any], codes: Optional[List[str]] = None
    ) -> None:
        super().__init__(config)

        codes = codes or []

        # Build symbol -> market mapping
        self._symbol_market: Dict[str, str] = {
            c: detect_market(c) for c in codes
        }

        # Build sub-engines (one per market type)
        self._rule_engines = _build_rule_engines(config, codes)

        # Crypto dedup state (owned by CompositeEngine, not sub-engine)
        self._funding_applied: Set = set()
        self._funding_daily_done: Set = set()

        # Forex dedup state
        self._last_swap_dates: Dict = {}

    def _reset_state(self) -> None:
        """Reset engine state including cross-market tracking."""
        super()._reset_state()
        self._funding_applied = set()
        self._funding_daily_done = set()
        self._last_swap_dates = {}

    def _rule_for(self, symbol: str) -> BaseEngine:
        """Get the sub-engine that provides rules for this symbol.

        Args:
            symbol: Instrument identifier.

        Returns:
            Sub-engine instance.

        Raises:
            ValueError: If no rule engine is available for the symbol's market.
        """
        market = self._symbol_market.get(symbol, "us_equity")
        if market not in self._rule_engines:
            # Auto-register a default equity engine if needed
            if market in ("us_equity", "hk_equity", "a_share"):
                submarket = "us"
                if market == "hk_equity":
                    submarket = "hk"
                elif market == "a_share":
                    submarket = "china_a"
                self._rule_engines[market] = EquityEngine(self.config, market=submarket)
            else:
                raise ValueError(
                    f"No rule engine for market '{market}' (symbol: {symbol})"
                )
        return self._rule_engines[market]

    # ── Stateless method dispatch ──

    def can_execute(self, symbol: str, direction: int, bar: pd.Series) -> bool:
        """Market-rule check with T+1 interceptor for A-shares."""
        market = self._symbol_market.get(symbol, "us_equity")

        # T+1: intercept here because sub-engine has no access to shared positions
        if market == "a_share" and direction == 0:
            pos = self.positions.get(symbol)
            if pos is not None:
                bar_date = None
                if hasattr(bar, "name") and hasattr(bar.name, "date"):
                    bar_date = bar.name.date()
                entry_date = (
                    pos.entry_time.date()
                    if hasattr(pos.entry_time, "date")
                    else None
                )
                if bar_date and entry_date and bar_date == entry_date:
                    return False

        # Delegate remaining checks (price limits, short-sell block, etc.)
        return self._rule_for(symbol).can_execute(symbol, direction, bar)

    def round_size(self, raw_size: float, price: float) -> float:
        """Delegate to active symbol's sub-engine."""
        return self._rule_for(self._active_symbol).round_size(raw_size, price)

    def calc_commission(
        self, size: float, price: float, direction: int, is_open: bool
    ) -> float:
        """Delegate to active symbol's sub-engine."""
        return self._rule_for(self._active_symbol).calc_commission(
            size, price, direction, is_open
        )

    def apply_slippage(self, price: float, direction: int) -> float:
        """Delegate to active symbol's sub-engine."""
        sub = self._rule_for(self._active_symbol)
        # ForexEngine needs _active_symbol set on the sub-engine
        sub._active_symbol = self._active_symbol
        return sub.apply_slippage(price, direction)

    # ── P&L / margin dispatch (route by symbol, not _active_symbol) ──

    def _calc_pnl(
        self,
        symbol: str,
        direction: int,
        size: float,
        entry_price: float,
        exit_price: float,
    ) -> float:
        """Delegate P&L calculation to the symbol's rule engine."""
        return self._rule_for(symbol)._calc_pnl(
            symbol, direction, size, entry_price, exit_price
        )

    def _calc_margin(
        self,
        symbol: str,
        size: float,
        price: float,
        leverage: float,
    ) -> float:
        """Delegate margin calculation to the symbol's rule engine."""
        return self._rule_for(symbol)._calc_margin(symbol, size, price, leverage)

    def _calc_raw_size(
        self,
        symbol: str,
        target_notional: float,
        price: float,
    ) -> float:
        """Delegate size calculation to the symbol's rule engine."""
        return self._rule_for(symbol)._calc_raw_size(symbol, target_notional, price)

    # ── Stateful hooks (implemented directly, NO delegation) ──

    def on_bar(self, symbol: str, bar: pd.Series, timestamp: pd.Timestamp) -> None:
        """Per-bar hooks dispatched by market type.

        Crypto: funding fee + liquidation check.
        Forex: swap/rollover.
        """
        market = self._symbol_market.get(symbol)

        if market == "crypto":
            crypto_sub = self._rule_engines.get("crypto")
            if crypto_sub is not None and isinstance(crypto_sub, CryptoEngine):
                fee = calc_crypto_funding_fee(
                    symbol,
                    bar,
                    timestamp,
                    self.positions,
                    crypto_sub.funding_rate,
                    self._funding_applied,
                    self._funding_daily_done,
                )
                self.capital -= fee

                if check_crypto_liquidation(symbol, bar, self.positions):
                    pos = self.positions.get(symbol)
                    if pos is not None:
                        mark_price = float(bar.get("close", pos.entry_price))
                        liq_price = crypto_sub.apply_slippage(mark_price, -pos.direction)
                        self._close_position(
                            symbol, liq_price, timestamp, "liquidation"
                        )

        elif market == "forex":
            forex_sub = self._rule_engines.get("forex")
            if forex_sub is not None and isinstance(forex_sub, ForexEngine):
                if forex_sub.swap_enabled:
                    swap = calc_forex_swap(
                        symbol,
                        timestamp,
                        self.positions,
                        forex_sub.lot_size,
                        self._last_swap_dates,
                    )
                    self.capital += swap
