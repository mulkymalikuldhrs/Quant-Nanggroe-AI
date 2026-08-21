"""Trailing stop loss — monitors positions and auto-closes when price reverses.

GATE-7 upgrade (2026-08-22):
- Breakeven ratchet: once profit >= ``breakeven_trigger_pct``, the stop jumps
  to entry +/- a small buffer, so ordinary retracements can never turn a
  winner into a loser.
- Real ATR trailing: when ``use_atr_multiple`` is on and the caller supplies
  the current ATR, the trail distance becomes ``atr_multiple * ATR``
  (volatility-adaptive) instead of the fixed ``trail_pct``.
- Monotonic ratchet: stops only ever tighten, never loosen.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Optional

log = logging.getLogger("QNA.TrailingStop")


@dataclass
class TrailingStopConfig:
    activation_pct: float = 0.02        # profit needed before % trailing arms
    trail_pct: float = 0.01             # fixed-percent trail distance
    min_stop_pct: float = 0.02          # initial hard stop below entry
    use_atr_multiple: bool = False      # when True + ATR supplied -> ATR trail
    atr_multiple: float = 2.0           # trail = atr_multiple * ATR
    # GATE-7 additions:
    breakeven_enabled: bool = True
    breakeven_trigger_pct: float = 0.01   # +1% profit -> stop to entry
    breakeven_buffer_pct: float = 0.0005  # lock a hair above entry


@dataclass
class TrailingStopState:
    entry_price: float
    peak_price: float
    current_stop: float
    is_active: bool = False
    breakeven_moved: bool = False
    symbol: str = ""


class TrailingStopManager:
    def __init__(self, config: Optional[TrailingStopConfig] = None):
        self.config = config or TrailingStopConfig()
        self._positions: Dict[str, TrailingStopState] = {}

    def add_position(self, symbol: str, entry_price: float):
        self._positions[symbol] = TrailingStopState(
            entry_price=entry_price,
            peak_price=entry_price,
            current_stop=entry_price * (1 - self.config.min_stop_pct),
            symbol=symbol,
        )

    def remove_position(self, symbol: str):
        self._positions.pop(symbol, None)

    def update(self, symbol: str, current_price: float,
               atr: Optional[float] = None) -> Optional[str]:
        """Advance the trailing logic one tick.

        Args:
            symbol: tracked position key.
            current_price: latest market price.
            atr: current ATR (same units as price). Required for ATR trailing;
                ignored when ``use_atr_multiple`` is False or ATR unavailable.

        Returns:
            symbol when the trailing stop fired (caller should close), else None.
        """
        state = self._positions.get(symbol)
        if not state:
            return None

        if current_price > state.peak_price:
            state.peak_price = current_price

        profit_pct = (current_price - state.entry_price) / state.entry_price

        # 1) Breakeven ratchet — fires before the wider % trail arms.
        cfg = self.config
        if (cfg.breakeven_enabled and not state.breakeven_moved
                and profit_pct >= cfg.breakeven_trigger_pct):
            be_stop = state.entry_price * (1 + cfg.breakeven_buffer_pct)
            if be_stop > state.current_stop:
                state.current_stop = be_stop
                state.breakeven_moved = True
                log.info(
                    "Breakeven moved for %s: stop=%.2f (entry=%.2f, peak=%.2f)",
                    symbol, state.current_stop, state.entry_price, state.peak_price,
                )

        # 2) Arm percent/ATR trailing after activation threshold.
        if profit_pct >= cfg.activation_pct:
            state.is_active = True

        if state.is_active:
            if cfg.use_atr_multiple and atr is not None and atr > 0:
                candidate = current_price - cfg.atr_multiple * float(atr)
            else:
                candidate = current_price * (1 - cfg.trail_pct)
            # Monotonic ratchet: never loosen the stop.
            if candidate > state.current_stop:
                state.current_stop = candidate

        # 3) Fire when price touches the stop.
        if state.is_active or state.breakeven_moved:
            if current_price <= state.current_stop:
                reason = ("breakeven" if state.breakeven_moved and not state.is_active
                          else "trailing")
                log.info(
                    "%s stop triggered for %s: entry=%.2f peak=%.2f stop=%.2f exit=%.2f",
                    reason.capitalize(), symbol, state.entry_price,
                    state.peak_price, state.current_stop, current_price,
                )
                self.remove_position(symbol)
                return symbol

        return None

    def get_stop_price(self, symbol: str) -> Optional[float]:
        state = self._positions.get(symbol)
        return state.current_stop if state else None
