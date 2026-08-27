"""Kelly Bridge — Connects Agent Pipeline to Kelly Criterion Position Sizing.

This bridge connects the LLM-based agent pipeline to the deterministic
Kelly Criterion engine for optimal position sizing.

The Kelly Bridge:
1. Takes a trade signal (ticker, direction, confidence) from the agent pipeline
2. Calculates optimal position size using the Kelly Criterion
3. Respects constitutional limits (max 0.5% per trade, etc.)
4. Returns the position size to the execution agent

Constitutional limits enforced (HARDCODED — NO OVERRIDE):
- Max 0.5% risk per trade
- Position size capped at Kelly-adjusted fraction
- No position can exceed constitutional limits regardless of confidence

Usage:
    bridge = KellyBridge(account_balance=1_000_000)
    result = bridge.calculate(
        symbol="AAPL",
        direction="BUY",
        confidence=0.8,
        entry=150.0,
        stop_loss=148.0,
        take_profit=156.0,
    )
    # result.position_size, result.position_size_pct, etc.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from quant_nanggroe.engine.risk.constants import (
    MAX_POSITION_SIZE_PCT,
    MAX_RISK_PER_TRADE,
)
from quant_nanggroe.engine.risk.kelly import KellyCriterion, KellyMethod, KellyParameters

logger = logging.getLogger(__name__)


@dataclass
class KellyBridgeResult:
    """Result from the Kelly Bridge position sizing calculation.

    Attributes:
        symbol: Trading symbol.
        direction: Trade direction.
        position_size: Calculated position size in currency units.
        position_size_pct: Position size as percentage of portfolio.
        lot_size: Position size in lots (for forex) or shares (for stocks).
        kelly_fraction: Kelly criterion optimal fraction (before constraints).
        adjusted_fraction: Kelly fraction after applying constitutional limits.
        confidence_adjusted: Whether confidence was used to adjust the fraction.
        capped: Whether the position was capped at constitutional limits.
        cap_reason: Why the position was capped, if applicable.
        risk_amount: Dollar amount at risk.
        risk_pct: Risk as percentage of account.
        stop_loss_distance: Distance from entry to stop loss.
        method: Kelly method used.
        timestamp: When the calculation was performed.
    """

    symbol: str
    direction: str
    position_size: float = 0.0
    position_size_pct: float = 0.0
    lot_size: float = 0.0
    kelly_fraction: float = 0.0
    adjusted_fraction: float = 0.0
    confidence_adjusted: bool = False
    capped: bool = False
    cap_reason: str = ""
    risk_amount: float = 0.0
    risk_pct: float = 0.0
    stop_loss_distance: float = 0.0
    method: str = "QUARTER_KELLY"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for agent state."""
        return {
            "symbol": self.symbol,
            "direction": self.direction,
            "position_size": self.position_size,
            "position_size_pct": self.position_size_pct,
            "lot_size": self.lot_size,
            "kelly_fraction": self.kelly_fraction,
            "adjusted_fraction": self.adjusted_fraction,
            "confidence_adjusted": self.confidence_adjusted,
            "capped": self.capped,
            "cap_reason": self.cap_reason,
            "risk_amount": self.risk_amount,
            "risk_pct": self.risk_pct,
            "stop_loss_distance": self.stop_loss_distance,
            "method": self.method,
            "timestamp": self.timestamp,
            "source": "kelly_bridge",
        }


class KellyBridge:
    """Bridge between the LLM agent pipeline and Kelly Criterion position sizing.

    This bridge calculates optimal position sizes using the Kelly Criterion,
    then applies constitutional limits to ensure no trade exceeds hardcoded
    risk limits.

    The Kelly calculation is CONFIRMED by the deterministic engine — it is
    NOT just a suggestion from the LLM.
    """

    # Default historical statistics (used when no historical data available)
    DEFAULT_WIN_RATE: float = 0.55
    DEFAULT_AVG_WIN_LOSS_RATIO: float = 2.0  # Consistent with min R:R of 1:2

    def __init__(
        self,
        account_balance: float = 1_000_000.0,
        default_method: str = "QUARTER_KELLY",
        win_rate_override: Optional[float] = None,
        avg_win_override: Optional[float] = None,
        avg_loss_override: Optional[float] = None,
    ) -> None:
        """Initialize the Kelly Bridge.

        Args:
            account_balance: Current account balance.
            default_method: Default Kelly method (FULL_KELLY, HALF_KELLY, QUARTER_KELLY).
            win_rate_override: Override for default win rate (if historical data available).
            avg_win_override: Override for average win amount.
            avg_loss_override: Override for average loss amount.
        """
        self._account_balance = account_balance
        self._default_method = default_method
        self._win_rate_override = win_rate_override
        self._avg_win_override = avg_win_override
        self._avg_loss_override = avg_loss_override
        self._kelly = KellyCriterion()

        logger.info(
            "KellyBridge initialized: balance=%.2f, method=%s, "
            "constitutional max_risk=%.2f%%, max_position=%.0f%%",
            account_balance,
            default_method,
            MAX_RISK_PER_TRADE * 100,
            MAX_POSITION_SIZE_PCT * 100,
        )

    @property
    def account_balance(self) -> float:
        """Current account balance."""
        return self._account_balance

    @account_balance.setter
    def account_balance(self, value: float) -> None:
        """Update account balance."""
        self._account_balance = value

    def calculate(
        self,
        symbol: str,
        direction: str,
        confidence: float = 0.5,
        entry: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        win_rate: Optional[float] = None,
        avg_win: Optional[float] = None,
        avg_loss: Optional[float] = None,
        method: Optional[str] = None,
    ) -> KellyBridgeResult:
        """Calculate optimal position size using Kelly Criterion.

        Respects constitutional limits:
        - Max 0.5% risk per trade (HARDCODED)
        - Position size capped at MAX_POSITION_SIZE_PCT

        Args:
            symbol: Trading symbol (e.g., "AAPL", "EURUSD").
            direction: Trade direction ("BUY" or "SELL").
            confidence: Signal confidence (0-1) from the agent pipeline.
            entry: Entry price.
            stop_loss: Stop loss price.
            take_profit: Take profit price.
            win_rate: Override win rate (if historical data available).
            avg_win: Override average win amount.
            avg_loss: Override average loss amount.
            method: Kelly method override.

        Returns:
            KellyBridgeResult with position sizing details.
        """
        logger.info(
            "Kelly Bridge: Calculating position size for %s %s (confidence=%.2f)",
            direction, symbol, confidence,
        )

        # Use provided values or defaults
        effective_win_rate = win_rate or self._win_rate_override or self.DEFAULT_WIN_RATE
        effective_method = method or self._default_method

        # Calculate average win/loss from entry/SL/TP if available
        if entry and stop_loss:
            sl_distance = abs(entry - stop_loss)
            effective_avg_loss = avg_loss or self._avg_loss_override or sl_distance
            if take_profit:
                tp_distance = abs(take_profit - entry)
                effective_avg_win = avg_win or self._avg_win_override or tp_distance
            else:
                effective_avg_win = (
                    avg_win or self._avg_win_override
                    or sl_distance * self.DEFAULT_AVG_WIN_LOSS_RATIO
                )
        else:
            effective_avg_loss = avg_loss or self._avg_loss_override or 1.0
            effective_avg_win = avg_win or self._avg_win_override or 2.0

        # Adjust win rate based on confidence
        confidence_adjusted = False
        if confidence > 0 and confidence < 1.0:
            # Blend the default win rate with confidence
            # Higher confidence → higher effective win rate (capped)
            adjusted_win_rate = effective_win_rate * (0.5 + 0.5 * confidence)
            adjusted_win_rate = min(adjusted_win_rate, 0.95)  # Cap at 95%
            if abs(adjusted_win_rate - effective_win_rate) > 0.01:
                confidence_adjusted = True
                effective_win_rate = adjusted_win_rate

        # Run Kelly Criterion calculation
        kelly_method = KellyMethod(effective_method.upper())
        params = KellyParameters(
            win_rate=effective_win_rate,
            avg_win=effective_avg_win,
            avg_loss=effective_avg_loss,
            confidence=confidence,
        )

        kelly_result = self._kelly.calculate_kelly(params, kelly_method)

        # Apply constitutional limits
        adjusted_fraction = kelly_result.adjusted_fraction
        capped = False
        cap_reason = ""

        # Cap 1: Max risk per trade (0.5%)
        if adjusted_fraction > MAX_RISK_PER_TRADE:
            logger.info(
                "Kelly Bridge: Capping fraction %.4f → %.4f (MAX_RISK_PER_TRADE)",
                adjusted_fraction, MAX_RISK_PER_TRADE,
            )
            adjusted_fraction = MAX_RISK_PER_TRADE
            capped = True
            cap_reason = f"Constitutional limit: max risk per trade = {MAX_RISK_PER_TRADE:.2%}"

        # Cap 2: Max position size percentage
        if adjusted_fraction > MAX_POSITION_SIZE_PCT:
            logger.info(
                "Kelly Bridge: Capping fraction %.4f → %.4f (MAX_POSITION_SIZE_PCT)",
                adjusted_fraction, MAX_POSITION_SIZE_PCT,
            )
            adjusted_fraction = MAX_POSITION_SIZE_PCT
            capped = True
            cap_reason = f"Constitutional limit: max position size = {MAX_POSITION_SIZE_PCT:.0%}"

        # Calculate position size
        position_size = self._account_balance * adjusted_fraction
        position_size_pct = adjusted_fraction * 100

        # Calculate lot size based on entry/SL
        lot_size = 0.0
        stop_loss_distance = 0.0
        risk_amount = self._account_balance * min(adjusted_fraction, MAX_RISK_PER_TRADE)
        risk_pct = min(adjusted_fraction, MAX_RISK_PER_TRADE) * 100

        if entry and stop_loss and abs(entry - stop_loss) > 0:
            stop_loss_distance = abs(entry - stop_loss)
            # For forex: 1 lot = 100,000 units
            # Risk per lot = SL distance * 100,000
            risk_per_lot = stop_loss_distance * 100_000
            if risk_per_lot > 0:
                lot_size = risk_amount / risk_per_lot
                lot_size = max(0.01, round(lot_size * 100) / 100)

        result = KellyBridgeResult(
            symbol=symbol,
            direction=direction,
            position_size=round(position_size, 2),
            position_size_pct=round(position_size_pct, 4),
            lot_size=lot_size,
            kelly_fraction=kelly_result.optimal_fraction,
            adjusted_fraction=adjusted_fraction,
            confidence_adjusted=confidence_adjusted,
            capped=capped,
            cap_reason=cap_reason,
            risk_amount=round(risk_amount, 2),
            risk_pct=round(risk_pct, 4),
            stop_loss_distance=round(stop_loss_distance, 4),
            method=effective_method,
        )

        logger.info(
            "Kelly Bridge: %s %s → position=%.2f (%.2f%%), lot=%.4f, "
            "kelly_frac=%.4f, adjusted_frac=%.4f%s",
            direction, symbol,
            result.position_size, result.position_size_pct,
            result.lot_size,
            result.kelly_fraction, result.adjusted_fraction,
            " [CAPPED: " + cap_reason + "]" if capped else "",
        )

        return result

    def calculate_from_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate Kelly position sizing for all signals/decisions in agent state.

        Args:
            state: Current AgentState dictionary.

        Returns:
            State updates with Kelly position sizing results.
        """
        logger.info("=== Kelly Bridge: Calculating from agent state ===")

        # Update account balance from state if available
        portfolio_state = state.get("portfolio_state", {})
        if "total_value" in portfolio_state:
            self._account_balance = portfolio_state["total_value"]

        signals = state.get("signals", [])
        decisions = state.get("decisions", [])

        # Process signals to add position sizing
        kelly_results: List[Dict[str, Any]] = []
        modified_signals = []

        for signal in signals:
            if not isinstance(signal, dict):
                modified_signals.append(signal)
                continue

            action = signal.get("action", "HOLD")
            if action in ("HOLD", "CLOSE", "EMERGENCY_EXIT"):
                modified_signals.append(signal)
                continue

            confidence = signal.get("confidence", 0.5)
            kelly_result = self.calculate(
                symbol=signal.get("symbol", "UNKNOWN"),
                direction=action,
                confidence=confidence,
                entry=signal.get("entry_price"),
                stop_loss=signal.get("stop_loss"),
                take_profit=signal.get("take_profit"),
            )

            kelly_results.append(kelly_result.to_dict())
            modified_signal = {
                **signal,
                "position_size_pct": kelly_result.position_size_pct,
                "quantity": kelly_result.lot_size,
                "kelly_sizing": kelly_result.to_dict(),
            }
            modified_signals.append(modified_signal)

        # Process decisions to add/validate position sizing
        modified_decisions = []
        for decision in decisions:
            if not isinstance(decision, dict):
                modified_decisions.append(decision)
                continue

            action = decision.get("action", "HOLD")
            if action in ("HOLD", "CLOSE", "EMERGENCY_EXIT"):
                modified_decisions.append(decision)
                continue

            confidence = decision.get("confidence", 0.5)
            kelly_result = self.calculate(
                symbol=decision.get("symbol", "UNKNOWN"),
                direction=action,
                confidence=confidence,
                entry=decision.get("entry_price"),
                stop_loss=decision.get("stop_loss"),
                take_profit=decision.get("take_profit"),
            )

            # Override the decision's position size with Kelly's
            modified_decision = {
                **decision,
                "quantity": kelly_result.lot_size,
                "position_size_pct": kelly_result.position_size_pct,
                "kelly_sizing": kelly_result.to_dict(),
            }
            modified_decisions.append(modified_decision)

        logger.info(
            "Kelly Bridge: Processed %d signals, %d decisions",
            len(signals), len(decisions),
        )

        return {
            "kelly_results": kelly_results,
            "signals": modified_signals,
            "decisions": modified_decisions,
            "sender": "kelly_bridge",
        }
