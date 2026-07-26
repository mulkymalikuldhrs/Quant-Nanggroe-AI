"""
ThesisDriftGuard — 3-Stage Circuit Breaker for Macro Thesis Invalidation.

Monitors active positions against macro context changes and escalates
through three stages when the trade thesis is contradicted:

  Stage 1  MONITORING  — Baseline: no contradictions, tracking normally.
  Stage 2  WARNING     — Multiple contradictions. Flag for review, tighten stops.
  Stage 3  HARD_EXIT   — Thesis clearly invalidated. Auto-close with market order.

Institutional pattern (from Riset_QNA.md §4.D.2):
    "Jika terjadi intervensi makro sekunder yang membatalkan tesis fundamental,
     sistem memicu Hard Exit (Close Market Order) secara otomatis tanpa menunggu
     hit Stop Loss teknikal."

Usage:
    from quant_nanggroe.engine.risk.thesis_drift_guard import ThesisDriftGuard

    guard = ThesisDriftGuard()
    guard.register_position("XAUUSD", "long", thesis={"direction": "bullish", "event": "GEOPOLITICAL_SUPPLY_SHOCK"})
    status = guard.check("GEOPOLITICAL_SUPPLY_SHOCK", "RISK_OFF")  # consistent
    status = guard.check("CENTRAL_BANK_HAWKISH", "RISK_OFF")      # may contradict
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
#  Stage enum & constants
# ══════════════════════════════════════════════════════════════════════


class ThesisStage(Enum):
    """Three stages of thesis drift severity.

    MONITORING = 1  — Baseline: tracking, no contradictions detected
    WARNING    = 2  — Multiple contradictions, tighten risk
    HARD_EXIT  = 3  — Thesis invalidated, close positions immediately
    """

    MONITORING = 1
    WARNING = 2
    HARD_EXIT = 3


STAGE_LABELS = {
    ThesisStage.MONITORING: "MONITORING",
    ThesisStage.WARNING: "WARNING",
    ThesisStage.HARD_EXIT: "HARD EXIT",
}

STAGE_ACTIONS = {
    ThesisStage.MONITORING: "NORMAL — no contradictions, tracking normally",
    ThesisStage.WARNING: (
        "FLAG + TIGHTEN — multiple contradictions, tighten stop losses, "
        "flag position for review"
    ),
    ThesisStage.HARD_EXIT: (
        "HARD EXIT — thesis invalidated, close all related positions "
        "with market orders immediately"
    ),
}


# ══════════════════════════════════════════════════════════════════════
#  Thesis definition & position tracking
# ══════════════════════════════════════════════════════════════════════


@dataclass
class TradeThesis:
    """The fundamental thesis behind a trade position.

    Defines the macro conditions under which a position was opened,
    so the guard can detect when those conditions are invalidated.

    Attributes:
        direction: Expected price direction ('bullish' or 'bearish').
        event_type: The macro event type that justified the trade
                    (e.g. 'GEOPOLITICAL_SUPPLY_SHOCK', 'INFLATION_SURPRISE').
        expected_weather: Expected macro weather at entry ('RISK_ON', 'RISK_OFF', etc.).
        expected_bias_sign: Sign of the causal bias (+1 for bullish, -1 for bearish).
        notes: Optional human-readable notes about the thesis.
    """

    direction: str  # 'bullish' | 'bearish'
    event_type: str = "UNKNOWN"
    expected_weather: str = "NEUTRAL_MIXED"
    expected_bias_sign: int = 0  # +1 or -1
    notes: str = ""


@dataclass
class TrackedPosition:
    """A position being monitored by the ThesisDriftGuard.

    Attributes:
        symbol: Trading symbol (e.g. 'XAUUSD', 'BTCUSDT').
        side: Position side ('long' or 'short').
        thesis: The TradeThesis that justified the entry.
        entry_price: Price at entry.
        entry_time: When the position was opened.
        current_stage: Current thesis drift stage.
        stage_history: List of (stage, timestamp, reason) tuples.
    """

    symbol: str
    side: str  # 'long' | 'short'
    thesis: TradeThesis
    entry_price: float = 0.0
    entry_time: str = ""
    current_stage: ThesisStage = ThesisStage.MONITORING
    stage_history: list[dict[str, Any]] = field(default_factory=list)
    contradiction_count: int = 0


# ══════════════════════════════════════════════════════════════════════
#  Contradiction rules
# ══════════════════════════════════════════════════════════════════════

# Each rule defines when a macro event contradicts a thesis direction.
# Key: (event_type, position_side, macro_weather) -> (contradicts_bool, reason)
#
# A contradiction means the incoming macro context is OPPOSITE to what the
# thesis expected. Multiple contradictions escalate the stage.


def _weather_contradicts_side(weather: str, side: str) -> tuple[bool, str]:
    """Check if macro weather contradicts a position side."""
    if weather == "RISK_OFF" and side == "long":
        return True, "Risk-Off weather contradicts long position (capital fleeing to safety)"
    if weather == "RISK_ON" and side == "short":
        return True, "Risk-On weather contradicts short position (risk appetite rising)"
    return False, ""


def _event_contradicts_thesis(
    event_type: str, side: str, thesis: TradeThesis
) -> tuple[bool, str]:
    """Check if a new macro event contradicts the original trade thesis."""
    # Same event type as thesis = consistent (no contradiction)
    if event_type == thesis.event_type:
        return False, ""

    # Define opposite/contradictory event pairs (bidirectional lookup via set)
    contradictory_pairs: set[tuple[str, str]] = {
        ("CENTRAL_BANK_HAWKISH", "CENTRAL_BANK_DOVISH"),
        ("CENTRAL_BANK_HAWKISH", "RISK_ON_SENTIMENT"),
        ("CENTRAL_BANK_DOVISH", "CENTRAL_BANK_HAWKISH"),
        ("CENTRAL_BANK_DOVISH", "INFLATION_SURPRISE"),
        ("INFLATION_SURPRISE", "RISK_OFF_SENTIMENT"),
        ("RISK_OFF_SENTIMENT", "INFLATION_SURPRISE"),
        ("RISK_ON_SENTIMENT", "RISK_OFF_SENTIMENT"),
        ("RISK_OFF_SENTIMENT", "RISK_ON_SENTIMENT"),
        ("GEOPOLITICAL_SUPPLY_SHOCK", "RISK_ON_SENTIMENT"),
        ("GEOPOLITICAL_SUPPLY_SHOCK", "CENTRAL_BANK_DOVISH"),
    }

    # If the new event is the opposite of the thesis event, it's a contradiction
    if (thesis.event_type, event_type) in contradictory_pairs:
        return True, (
            f"New event '{event_type}' is opposite to thesis event "
            f"'{thesis.event_type}' — fundamental thesis contradicted"
        )

    # Check if event_type direction opposes position side
    bearish_events = {"CENTRAL_BANK_HAWKISH", "INFLATION_SURPRISE", "GEOPOLITICAL_SUPPLY_SHOCK"}
    bullish_events = {"CENTRAL_BANK_DOVISH", "RISK_ON_SENTIMENT"}

    if side == "long" and event_type in bearish_events:
        return True, f"Bearish event '{event_type}' contradicts long position"
    if side == "short" and event_type in bullish_events:
        return True, f"Bullish event '{event_type}' contradicts short position"

    return False, ""


# ══════════════════════════════════════════════════════════════════════
#  ThesisDriftGuard
# ══════════════════════════════════════════════════════════════════════


class ThesisDriftGuard:
    """3-Stage circuit breaker for macro thesis invalidation.

    Monitors all active positions against incoming macro context and
    escalates through MONITORING → WARNING → HARD_EXIT stages when
    the trade thesis is contradicted.

    The guard is designed to be called each trading cycle with the
    latest macro context. It maintains internal state per position.
    """

    def __init__(
        self,
        advisory_threshold: int = 1,
        warning_threshold: int = 2,
        hard_exit_enabled: bool = True,
    ):
        """
        Args:
            advisory_threshold: Number of contradictions before WARNING (default: 1).
            warning_threshold: Number of contradictions before WARNING (default: 2).
            hard_exit_enabled: Whether Stage 3 automatically closes positions (default: True).
        """
        self.advisory_threshold = advisory_threshold
        self.warning_threshold = warning_threshold
        self.hard_exit_enabled = hard_exit_enabled
        self._positions: dict[str, TrackedPosition] = {}
        self._last_check_result: dict[str, Any] = {}

    # ── Position lifecycle ─────────────────────────────────────

    def register_position(
        self,
        symbol: str,
        side: str,
        thesis: Optional[TradeThesis] = None,
        entry_price: float = 0.0,
    ) -> None:
        """Register a new position for thesis monitoring.

        Args:
            symbol: Trading symbol (e.g. 'XAUUSD').
            side: Position side ('long' or 'short').
            thesis: The TradeThesis that justified the entry.
                    If None, a default thesis is inferred from side.
            entry_price: Entry price for reference.
        """
        if thesis is None:
            thesis = TradeThesis(
                direction="bullish" if side == "long" else "bearish",
                event_type="UNKNOWN",
                expected_weather="NEUTRAL_MIXED",
                expected_bias_sign=1 if side == "long" else -1,
                notes="Auto-inferred thesis",
            )
        pos = TrackedPosition(
            symbol=symbol,
            side=side,
            thesis=thesis,
            entry_price=entry_price,
            entry_time=datetime.now(timezone.utc).isoformat(),
            current_stage=ThesisStage.MONITORING,
            contradiction_count=0,
        )
        self._positions[symbol] = pos
        logger.info(
            "THESIS REGISTERED: %s %s (event=%s, weather=%s)",
            symbol, side, thesis.event_type, thesis.expected_weather,
        )

    def unregister_position(self, symbol: str) -> None:
        """Remove a position from monitoring (e.g., after manual close)."""
        if symbol in self._positions:
            logger.info("THESIS UNREGISTERED: %s", symbol)
            del self._positions[symbol]

    def get_position(self, symbol: str) -> Optional[TrackedPosition]:
        """Get the tracked position for a symbol."""
        return self._positions.get(symbol)

    @property
    def active_positions(self) -> dict[str, TrackedPosition]:
        """All currently tracked positions."""
        return dict(self._positions)

    @property
    def n_positions(self) -> int:
        """Number of tracked positions."""
        return len(self._positions)

    # ── Core check: per-cycle macro evaluation ─────────────────

    def check(
        self,
        event_type: str,
        weather: str = "NEUTRAL_MIXED",
        cot_signal: str = "BALANCED",
        smt_divergence: bool = False,
        position_symbol: Optional[str] = None,
    ) -> dict[str, Any]:
        """Run thesis drift check against latest macro context.

        Evaluates all tracked positions (or a single position) against the
        latest macro context. Returns a result dict with per-position status.

        Args:
            event_type: Current macro event type.
            weather: Current macro weather classification.
            cot_signal: Current COT positioning signal.
            smt_divergence: Whether SMT divergence is detected.
            position_symbol: Optional — check only this symbol.

        Returns:
            Dict with:
              - stage: Highest stage across all checked positions
              - label: Human-readable stage label
              - positions: Per-position evaluation results
              - has_hard_exit: Whether any position triggered Stage 3
              - actions: List of recommended actions
        """
        symbols_to_check = (
            [position_symbol] if position_symbol else list(self._positions.keys())
        )

        results: dict[str, Any] = {}
        max_stage = ThesisStage.MONITORING
        all_actions: list[str] = []

        for sym in symbols_to_check:
            pos = self._positions.get(sym)
            if pos is None:
                continue

            # Skip positions already at HARD_EXIT (use STAGE_LABELS for consistent key)
            if pos.current_stage == ThesisStage.HARD_EXIT:
                results[sym] = {
                    "symbol": sym,
                    "side": pos.side,
                    "stage": STAGE_LABELS[ThesisStage.HARD_EXIT],
                    "stage_int": 3,
                    "contradictions": pos.contradiction_count,
                    "action": STAGE_ACTIONS[ThesisStage.HARD_EXIT],
                }
                continue

            # Evaluate contradictions
            contradictions = self._evaluate_contradictions(
                pos=pos,
                event_type=event_type,
                weather=weather,
                cot_signal=cot_signal,
                smt_divergence=smt_divergence,
            )

            if contradictions:
                pos.contradiction_count += 1
                timestamp = datetime.now(timezone.utc).isoformat()
                for reason in contradictions:
                    pos.stage_history.append({
                        "timestamp": timestamp,
                        "event_type": event_type,
                        "weather": weather,
                        "reason": reason,
                    })

            # Determine stage from contradiction count
            new_stage = self._resolve_stage(pos.contradiction_count)
            pos.current_stage = new_stage

            if new_stage.value > max_stage.value:
                max_stage = new_stage

            action = STAGE_ACTIONS[new_stage]
            all_actions.append(f"{sym}: {action}")

            if new_stage == ThesisStage.HARD_EXIT:
                logger.warning(
                    "THESIS HARD EXIT: %s %s at entry=%.2f — %d contradictions",
                    sym, pos.side, pos.entry_price, pos.contradiction_count,
                )

            results[sym] = {
                "symbol": sym,
                "side": pos.side,
                "stage": STAGE_LABELS[new_stage],
                "stage_int": new_stage.value,
                "contradictions": pos.contradiction_count,
                "latest_contradictions": contradictions,
                "stage_history": pos.stage_history[-5:],  # last 5 events
                "action": action,
            }

        self._last_check_result = {
            "stage": max_stage,
            "label": STAGE_LABELS[max_stage],
            "stage_int": max_stage.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "weather": weather,
            "cot_signal": cot_signal,
            "smt_divergence": smt_divergence,
            "positions": results,
            "has_hard_exit": any(
                r.get("stage_int") == 3 for r in results.values()
            ),
            "actions": all_actions,
        }

        return self._last_check_result

    def check_all(
        self,
        event_type: str,
        weather: str = "NEUTRAL_MIXED",
        cot_signal: str = "BALANCED",
        smt_divergence: bool = False,
    ) -> dict[str, Any]:
        """Run thesis drift check against ALL tracked positions.

        Convenience wrapper around check().
        """
        return self.check(event_type, weather, cot_signal, smt_divergence)

    # ── Contradiction evaluation ───────────────────────────────

    def _evaluate_contradictions(
        self,
        pos: TrackedPosition,
        event_type: str,
        weather: str,
        cot_signal: str,
        smt_divergence: bool,
    ) -> list[str]:
        """Check all macro dimensions for thesis contradictions.

        Returns list of contradiction reasons (empty if no contradictions).
        """
        contradictions: list[str] = []

        # 1. Weather contradiction
        weather_contradicts, weather_reason = _weather_contradicts_side(weather, pos.side)
        if weather_contradicts:
            contradictions.append(weather_reason)

        # 2. Event contradiction
        event_contradicts, event_reason = _event_contradicts_thesis(
            event_type, pos.side, pos.thesis
        )
        if event_contradicts:
            contradictions.append(event_reason)

        # 3. COT extreme signal against position
        if cot_signal in ("EXTREME_LONG_OVERBOUGHT", "RETAIL_EXTREME_LONG") and pos.side == "long":
            contradictions.append(
                f"COT {cot_signal} — institutional positioning warns against longs"
            )
        if cot_signal in ("EXTREME_SHORT_OVERSOLD", "RETAIL_EXTREME_SHORT") and pos.side == "short":
            contradictions.append(
                f"COT {cot_signal} — institutional positioning warns against shorts"
            )

        # 4. SMT divergence against position
        if smt_divergence and pos.side == "long":
            contradictions.append(
                "SMT divergence detected in correlated pair — potential fakeout against longs"
            )

        return contradictions

    def _resolve_stage(self, contradiction_count: int) -> ThesisStage:
        """Map contradiction count to thesis stage."""
        if contradiction_count >= self.warning_threshold:
            return ThesisStage.HARD_EXIT
        elif contradiction_count >= self.advisory_threshold:
            return ThesisStage.WARNING
        return ThesisStage.MONITORING

    # ── Status & diagnostics ──────────────────────────────────

    def get_status(self) -> dict[str, Any]:
        """Get diagnostic summary of all tracked positions and stages."""
        positions_status = {}
        for sym, pos in self._positions.items():
            positions_status[sym] = {
                "symbol": sym,
                "side": pos.side,
                "entry_price": pos.entry_price,
                "entry_time": pos.entry_time,
                "thesis_event": pos.thesis.event_type,
                "thesis_direction": pos.thesis.direction,
                "current_stage": STAGE_LABELS[pos.current_stage],
                "contradictions": pos.contradiction_count,
                "n_history_events": len(pos.stage_history),
            }

        return {
            "active": True,
            "n_positions": len(self._positions),
            "positions": positions_status,
            "advisory_threshold": self.advisory_threshold,
            "warning_threshold": self.warning_threshold,
            "hard_exit_enabled": self.hard_exit_enabled,
            "last_check": self._last_check_result.get("timestamp", None),
            "last_max_stage": STAGE_LABELS.get(
                self._last_check_result.get("stage", ThesisStage.MONITORING),
                "UNKNOWN",
            ),
        }

    def reset_position(self, symbol: str) -> None:
        """Reset a position's contradiction counter (e.g., after manual review)."""
        pos = self._positions.get(symbol)
        if pos:
            pos.contradiction_count = 0
            pos.current_stage = ThesisStage.MONITORING
            logger.info("THESIS RESET: %s — contradiction count cleared", symbol)

    def clear(self) -> None:
        """Clear all tracked positions (e.g., on engine shutdown)."""
        self._positions.clear()
        self._last_check_result = {}
        logger.info("THESIS GUARD: all positions cleared")
