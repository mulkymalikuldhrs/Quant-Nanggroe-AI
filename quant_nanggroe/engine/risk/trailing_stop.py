"""Trailing stop loss — monitors positions and auto-closes when price reverses."""
from __future__ import annotations
import logging
from typing import Dict, Optional
from dataclasses import dataclass, field

log = logging.getLogger("QNA.TrailingStop")

@dataclass
class TrailingStopConfig:
    activation_pct: float = 0.02
    trail_pct: float = 0.01
    min_stop_pct: float = 0.02
    use_atr_multiple: bool = False
    atr_multiple: float = 2.0

@dataclass
class TrailingStopState:
    entry_price: float
    peak_price: float
    current_stop: float
    is_active: bool = False
    symbol: str = ""

class TrailingStopManager:
    def __init__(self, config: Optional[TrailingStopConfig] = None):
        self.config = config or TrailingStopConfig()
        self._positions: Dict[str, TrailingStopState] = {}

    def add_position(self, symbol: str, entry_price: float):
        initial_stop = entry_price * (1 - self.config.min_stop_pct)
        self._positions[symbol] = TrailingStopState(
            entry_price=entry_price,
            peak_price=entry_price,
            current_stop=entry_price * (1 - self.config.min_stop_pct),
            symbol=symbol,
        )

    def remove_position(self, symbol: str):
        self._positions.pop(symbol, None)

    def update(self, symbol: str, current_price: float) -> Optional[str]:
        state = self._positions.get(symbol)
        if not state:
            return None

        if current_price > state.peak_price:
            state.peak_price = current_price
            profit_pct = (current_price - state.entry_price) / state.entry_price
            if profit_pct >= self.config.activation_pct:
                state.is_active = True
                state.current_stop = current_price * (1 - self.config.trail_pct)

        if state.is_active and current_price <= state.current_stop:
            log.info(f"Trailing stop triggered for {symbol}: entry={state.entry_price:.2f}, peak={state.peak_price:.2f}, exit={current_price:.2f}")
            self.remove_position(symbol)
            return symbol

        return None

    def get_stop_price(self, symbol: str) -> Optional[float]:
        state = self._positions.get(symbol)
        return state.current_stop if state else None
