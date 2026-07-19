"""Position Protection Engine — Intrabar-aware SL/TP/Trailing/Time-limit.

Extracted from QuantDinger Strategy V2. Provides a deterministic protection
evaluator used by both backtest and live execution modes.

Features:
- Intrabar mode selection: conservative, balanced, aggressive
- Stop loss, take profit, trailing stop, time limit
- Gap detection (price gapped past trigger)
- Bar-level and price-level evaluation
- Serializable state for crash recovery

Usage:
    engine = ProtectionEngine(intrabar_mode='balanced')
    state = ProtectionState.open(symbol='BTCUSD', side='long',
                                 entry_price=50000, spec=ProtectionSpec(...))
    decision = engine.evaluate_bar(state, timestamp=ts,
                                   open_price=51000, high_price=52000, low_price=49000)
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

import pandas as pd


@dataclass(frozen=True)
class ProtectionSpec:
    """Position protection specification.

    All percentages are expressed as decimal fractions (0.02 = 2%).
    At least one protection must be enabled for the spec to be active.
    """

    stop_loss_pct: float = 0.0
    take_profit_pct: float = 0.0
    trailing_stop_pct: float = 0.0
    trailing_activation_pct: float = 0.0
    time_limit_seconds: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "stop_loss_pct", _ratio(self.stop_loss_pct, maximum=1.0))
        object.__setattr__(self, "take_profit_pct", _ratio(self.take_profit_pct, maximum=5.0))
        object.__setattr__(self, "trailing_stop_pct", _ratio(self.trailing_stop_pct, maximum=1.0))
        object.__setattr__(
            self,
            "trailing_activation_pct",
            _ratio(self.trailing_activation_pct, maximum=5.0),
        )
        object.__setattr__(self, "time_limit_seconds", max(0, int(self.time_limit_seconds or 0)))

    @property
    def enabled(self) -> bool:
        return any((
            self.stop_loss_pct > 0,
            self.take_profit_pct > 0,
            self.trailing_stop_pct > 0,
            self.time_limit_seconds > 0,
        ))

    def metadata(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_value(cls, value: object = None, **overrides: Any) -> ProtectionSpec | None:
        """Create ProtectionSpec from dict, ProtectionSpec, or keyword overrides.

        Returns None if the resulting spec has no protections enabled.
        """
        source: dict[str, Any] = {}
        if isinstance(value, ProtectionSpec):
            source.update(value.metadata())
        elif isinstance(value, Mapping):
            source.update(value)
        source.update({key: item for key, item in overrides.items() if item is not None})
        trailing = source.get("trailing")
        if isinstance(trailing, Mapping):
            source.setdefault("trailing_stop_pct", trailing.get("pct"))
            source.setdefault("trailing_activation_pct", trailing.get("activation_pct"))
        spec = cls(
            stop_loss_pct=source.get("stop_loss_pct"),
            take_profit_pct=source.get("take_profit_pct"),
            trailing_stop_pct=source.get("trailing_stop_pct"),
            trailing_activation_pct=source.get("trailing_activation_pct"),
            time_limit_seconds=source.get("time_limit_seconds"),
        )
        return spec if spec.enabled else None


@dataclass
class ProtectionState:
    """Mutable state tracking for an active position's protection.

    Tracks highest/lowest prices seen for trailing stop calculation,
    and position duration for time-limit enforcement.
    """

    symbol: str
    side: str
    entry_price: float
    spec: ProtectionSpec
    opened_at: pd.Timestamp
    highest_price: float
    lowest_price: float

    @classmethod
    def open(
        cls,
        *,
        symbol: str,
        side: str,
        entry_price: float,
        spec: ProtectionSpec,
        opened_at: object,
    ) -> ProtectionState:
        price = float(entry_price or 0.0)
        return cls(
            symbol=str(symbol),
            side=str(side).lower(),
            entry_price=price,
            spec=spec,
            opened_at=pd.Timestamp(opened_at),
            highest_price=price,
            lowest_price=price,
        )

    def metadata(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "side": self.side,
            "entry_price": self.entry_price,
            "spec": self.spec.metadata(),
            "opened_at": self.opened_at.isoformat(),
            "highest_price": self.highest_price,
            "lowest_price": self.lowest_price,
        }

    @classmethod
    def from_metadata(cls, value: Mapping[str, Any]) -> ProtectionState | None:
        """Deserialize from metadata dict (for crash recovery)."""
        spec = ProtectionSpec.from_value(value.get("spec"))
        entry_price = _number(value.get("entry_price"))
        if spec is None or entry_price <= 0:
            return None
        state = cls.open(
            symbol=str(value.get("symbol") or ""),
            side=str(value.get("side") or "long"),
            entry_price=entry_price,
            spec=spec,
            opened_at=value.get("opened_at") or pd.Timestamp.utcnow(),
        )
        state.highest_price = max(entry_price, _number(value.get("highest_price"), entry_price))
        lowest = _number(value.get("lowest_price"), entry_price)
        state.lowest_price = min(entry_price, lowest if lowest > 0 else entry_price)
        return state


@dataclass(frozen=True)
class ProtectionDecision:
    """Immutable record of a protection-trigger event."""

    symbol: str
    side: str
    reason: str  # 'stop_loss' | 'trailing_stop' | 'take_profit' | 'time_limit'
    price: float
    trigger_price: float
    timestamp: pd.Timestamp


class ProtectionEngine:
    """Deterministic protection evaluator used by both execution modes.

    Evaluates open position protections on each bar or price tick.

    Intrabar modes:
    - conservative (default): stop_loss > trailing > time_limit > take_profit
    - balanced: nearest trigger to reference price wins
    - aggressive: take_profit > trailing > time_limit > stop_loss

    Extracted from QuantDinger Strategy V2 (services/strategy_v2/protection.py).
    """

    VALID_INTRABAR_MODES = {"conservative", "balanced", "aggressive"}

    def __init__(self, *, intrabar_mode: str = "conservative") -> None:
        mode = str(intrabar_mode or "conservative").strip().lower()
        self.intrabar_mode = mode if mode in self.VALID_INTRABAR_MODES else "conservative"

    def evaluate_bar(
        self,
        state: ProtectionState,
        *,
        timestamp: object,
        open_price: float,
        high_price: float,
        low_price: float,
    ) -> ProtectionDecision | None:
        """Evaluate protections using bar OHLC data.

        Detects gap-through (open past trigger) and intra-bar touches.

        Args:
            state: Current position protection state (mutated in place).
            timestamp: Current bar timestamp.
            open_price: Bar open price.
            high_price: Bar high price.
            low_price: Bar low price.

        Returns:
            ProtectionDecision if a protection was triggered, None otherwise.
        """
        ts = pd.Timestamp(timestamp)
        open_ = _number(open_price)
        high = max(open_, _number(high_price, open_))
        low = min(open_, _number(low_price, open_))
        candidates = self._bar_candidates(state, ts=ts, open_=open_, high=high, low=low)
        decision = self._choose(candidates, open_)
        if decision is None:
            state.highest_price = max(state.highest_price, high)
            state.lowest_price = min(state.lowest_price, low)
        return decision

    def evaluate_price(
        self,
        state: ProtectionState,
        *,
        timestamp: object,
        price: float,
    ) -> ProtectionDecision | None:
        """Evaluate protections at a single price point (live tick).

        Args:
            state: Current position protection state (mutated in place).
            timestamp: Current tick timestamp.
            price: Current price.

        Returns:
            ProtectionDecision if a protection was triggered, None otherwise.
        """
        ts = pd.Timestamp(timestamp)
        current = _number(price)
        if current <= 0:
            return None
        previous_high = state.highest_price
        previous_low = state.lowest_price
        state.highest_price = max(state.highest_price, current)
        state.lowest_price = min(state.lowest_price, current)
        candidates = self._price_candidates(state, ts=ts, price=current)
        if candidates:
            return self._choose(candidates, current)
        if state.highest_price == previous_high and state.lowest_price == previous_low:
            return None
        return None

    def _bar_candidates(
        self,
        state: ProtectionState,
        *,
        ts: pd.Timestamp,
        open_: float,
        high: float,
        low: float,
    ) -> list[ProtectionDecision]:
        spec = state.spec
        entry = state.entry_price
        is_long = state.side == "long"
        candidates: list[ProtectionDecision] = []

        # Stop loss
        if spec.stop_loss_pct > 0:
            trigger = entry * (1 - spec.stop_loss_pct if is_long else 1 + spec.stop_loss_pct)
            touched = low <= trigger if is_long else high >= trigger
            gapped = open_ <= trigger if is_long else open_ >= trigger
            if touched:
                candidates.append(self._decision(state, "stop_loss", open_ if gapped else trigger, trigger, ts))

        # Trailing stop
        trailing = self._trailing_trigger(state)
        if trailing is not None:
            touched = low <= trailing if is_long else high >= trailing
            gapped = open_ <= trailing if is_long else open_ >= trailing
            if touched:
                candidates.append(self._decision(state, "trailing_stop", open_ if gapped else trailing, trailing, ts))

        # Take profit
        if spec.take_profit_pct > 0:
            trigger = entry * (1 + spec.take_profit_pct if is_long else 1 - spec.take_profit_pct)
            touched = high >= trigger if is_long else low <= trigger
            gapped = open_ >= trigger if is_long else open_ <= trigger
            if touched:
                candidates.append(self._decision(state, "take_profit", open_ if gapped else trigger, trigger, ts))

        # Time limit
        if self._time_limit_reached(state, ts):
            candidates.append(self._decision(state, "time_limit", open_, open_, ts))

        return candidates

    def _price_candidates(
        self,
        state: ProtectionState,
        *,
        ts: pd.Timestamp,
        price: float,
    ) -> list[ProtectionDecision]:
        spec = state.spec
        entry = state.entry_price
        is_long = state.side == "long"
        candidates: list[ProtectionDecision] = []

        if spec.stop_loss_pct > 0:
            trigger = entry * (1 - spec.stop_loss_pct if is_long else 1 + spec.stop_loss_pct)
            if (is_long and price <= trigger) or (not is_long and price >= trigger):
                candidates.append(self._decision(state, "stop_loss", price, trigger, ts))

        trailing = self._trailing_trigger(state)
        if trailing is not None and ((is_long and price <= trailing) or (not is_long and price >= trailing)):
            candidates.append(self._decision(state, "trailing_stop", price, trailing, ts))

        if spec.take_profit_pct > 0:
            trigger = entry * (1 + spec.take_profit_pct if is_long else 1 - spec.take_profit_pct)
            if (is_long and price >= trigger) or (not is_long and price <= trigger):
                candidates.append(self._decision(state, "take_profit", price, trigger, ts))

        if self._time_limit_reached(state, ts):
            candidates.append(self._decision(state, "time_limit", price, price, ts))

        return candidates

    def _trailing_trigger(self, state: ProtectionState) -> float | None:
        spec = state.spec
        if spec.trailing_stop_pct <= 0:
            return None
        if state.side == "long":
            if state.highest_price < state.entry_price * (1 + spec.trailing_activation_pct):
                return None
            return state.highest_price * (1 - spec.trailing_stop_pct)
        if state.lowest_price > state.entry_price * (1 - spec.trailing_activation_pct):
            return None
        return state.lowest_price * (1 + spec.trailing_stop_pct)

    @staticmethod
    def _time_limit_reached(state: ProtectionState, timestamp: pd.Timestamp) -> bool:
        limit = state.spec.time_limit_seconds
        return limit > 0 and (timestamp - state.opened_at).total_seconds() >= limit

    def _choose(
        self,
        candidates: list[ProtectionDecision],
        reference_price: float,
    ) -> ProtectionDecision | None:
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]

        if self.intrabar_mode == "aggressive":
            priority = {"take_profit": 0, "trailing_stop": 1, "time_limit": 2, "stop_loss": 3}
            return min(candidates, key=lambda item: priority.get(item.reason, 9))
        if self.intrabar_mode == "balanced":
            return min(candidates, key=lambda item: abs(item.trigger_price - reference_price))

        # conservative (default)
        priority = {"stop_loss": 0, "trailing_stop": 1, "time_limit": 2, "take_profit": 3}
        return min(candidates, key=lambda item: priority.get(item.reason, 9))

    @staticmethod
    def _decision(
        state: ProtectionState,
        reason: str,
        price: float,
        trigger_price: float,
        timestamp: pd.Timestamp,
    ) -> ProtectionDecision:
        return ProtectionDecision(
            symbol=state.symbol,
            side=state.side,
            reason=reason,
            price=float(price),
            trigger_price=float(trigger_price),
            timestamp=timestamp,
        )


def _ratio(value: object, *, maximum: float) -> float:
    number = _number(value)
    return min(float(maximum), max(0.0, number))


def _number(value: object, default: float = 0.0) -> float:
    try:
        number = float(value if value is not None else default)
    except (TypeError, ValueError):
        return float(default)
    return number if number == number else float(default)


__all__ = [
    "ProtectionSpec",
    "ProtectionState",
    "ProtectionDecision",
    "ProtectionEngine",
]
