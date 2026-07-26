from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ThesisStatus(Enum):
    ACTIVE = "active"
    WEAKENED = "weakened"
    INVALIDATED = "invalidated"


class InvalidatorType(Enum):
    MACRO_DATA = "macro_data_release"
    CENTRAL_BANK = "central_bank_intervention"
    GEOPOLITICAL = "geopolitical_shift"
    TECHNICAL = "technical_invalidation"
    POSITION_SIZING = "position_sizing_breach"


@dataclass
class ThesisState:
    trade_id: str
    symbol: str
    direction: str
    entry_price: float
    thesis_summary: str
    status: ThesisStatus
    invalidator_type: InvalidatorType | None = None
    invalidator_detail: str = ""
    opened_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    invalidated_at: datetime | None = None
    value_at_risk: float = 0.0


@dataclass
class MacroTrigger:
    invalidator: InvalidatorType
    severity: float
    description: str
    affected_assets: list[str]


MACRO_TRIGGERS: dict[str, list[MacroTrigger]] = {
    "GEOPOLITICAL_SUPPLY_SHOCK": [
        MacroTrigger(InvalidatorType.GEOPOLITICAL, 0.9, "Supply disruption event detected", ["GC1!", "SI1!", "ES1!"]),
    ],
    "CENTRAL_BANK_RATE_CUT": [
        MacroTrigger(InvalidatorType.CENTRAL_BANK, 0.8, "Unexpected rate cut — bullish equities, bearish USD", ["DXY", "ES1!", "6E1!"]),
    ],
    "CENTRAL_BANK_RATE_HIKE": [
        MacroTrigger(InvalidatorType.CENTRAL_BANK, 0.8, "Unexpected rate hike — bearish equities, bullish USD", ["DXY", "ES1!", "6E1!"]),
    ],
    "INFLATION_SURPRISE_ABOVE": [
        MacroTrigger(InvalidatorType.MACRO_DATA, 0.7, "CPI/inflation above consensus — bearish bonds, bullish USD", ["ZB1!", "DXY", "GC1!"]),
    ],
    "INFLATION_SURPRISE_BELOW": [
        MacroTrigger(InvalidatorType.MACRO_DATA, 0.7, "CPI/inflation below consensus — bullish bonds, bearish USD", ["ZB1!", "DXY", "GC1!"]),
    ],
    "NFP_MISS": [
        MacroTrigger(InvalidatorType.MACRO_DATA, 0.6, "NFP miss — weakening labor market", ["ES1!", "DXY"]),
    ],
    "NFP_BEAT": [
        MacroTrigger(InvalidatorType.MACRO_DATA, 0.6, "NFP beat — strong labor market", ["ES1!", "DXY"]),
    ],
}


class ThesisDriftGuard:
    """Hard guardrail: monitors macro thesis and triggers hard exit when invalidated."""

    def __init__(self):
        self._active_trades: dict[str, ThesisState] = {}

    def register_trade(self, trade_id: str, symbol: str, direction: str, entry_price: float, thesis_summary: str, var: float = 0.0) -> None:
        self._active_trades[trade_id] = ThesisState(
            trade_id=trade_id,
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            thesis_summary=thesis_summary,
            status=ThesisStatus.ACTIVE,
            value_at_risk=var,
        )
        logger.info("Thesis registered: %s %s @ %.2f — %s", trade_id, symbol, entry_price, thesis_summary)

    def evaluate_macro_event(self, event_type: str, affected_symbols: list[str] | None = None) -> dict[str, dict[str, Any]]:
        triggers = MACRO_TRIGGERS.get(event_type, [])
        if not triggers:
            return {}

        results: dict[str, dict[str, Any]] = {}
        for trade_id, state in list(self._active_trades.items()):
            if state.status != ThesisStatus.ACTIVE:
                continue

            relevant = [t for t in triggers if state.symbol in t.affected_assets or (affected_symbols and state.symbol in affected_symbols)]
            if not relevant:
                continue

            max_severity = max(t.severity for t in relevant)
            invalidator = relevant[0]

            if max_severity >= 0.7:
                state.status = ThesisStatus.INVALIDATED
                state.invalidator_type = invalidator.invalidator
                state.invalidator_detail = f"{invalidator.description} (severity={max_severity:.1f})"
                state.invalidated_at = datetime.now(timezone.utc)
                results[trade_id] = {
                    "action": "HARD_EXIT",
                    "symbol": state.symbol,
                    "direction": state.direction,
                    "entry_price": state.entry_price,
                    "reason": state.invalidator_detail,
                    "invalidator": invalidator.invalidator.value,
                }
                logger.warning("THESIS INVALIDATED: %s — %s", trade_id, state.invalidator_detail)
            elif max_severity >= 0.4:
                state.status = ThesisStatus.WEAKENED
                results[trade_id] = {
                    "action": "REDUCE",
                    "symbol": state.symbol,
                    "direction": state.direction,
                    "entry_price": state.entry_price,
                    "reason": f"Thesis weakened by {invalidator.description} (severity={max_severity:.1f})",
                    "invalidator": invalidator.invalidator.value,
                }
                logger.info("Thesis weakened: %s — %s", trade_id, state.invalidator_detail)

        return results

    def check_macro_surprise_thesis(self, msi_score: float, symbol: str, direction: str) -> dict[str, Any]:
        if direction == "BUY" and msi_score < -1.5:
            return {"alarm": True, "reason": f"Macro surprise ({msi_score:.2f}) contradicts bullish thesis on {symbol}", "action": "REVIEW"}
        elif direction == "SELL" and msi_score > 1.5:
            return {"alarm": True, "reason": f"Macro surprise ({msi_score:.2f}) contradicts bearish thesis on {symbol}", "action": "REVIEW"}
        return {"alarm": False, "reason": "Macro surprise aligned with thesis", "action": "HOLD"}

    def active_count(self) -> int:
        return sum(1 for s in self._active_trades.values() if s.status == ThesisStatus.ACTIVE)

    def get_state(self, trade_id: str) -> ThesisState | None:
        return self._active_trades.get(trade_id)

    def all_active(self) -> list[ThesisState]:
        return [s for s in self._active_trades.values() if s.status == ThesisStatus.ACTIVE]

    def clear_completed(self, trade_id: str) -> None:
        self._active_trades.pop(trade_id, None)
