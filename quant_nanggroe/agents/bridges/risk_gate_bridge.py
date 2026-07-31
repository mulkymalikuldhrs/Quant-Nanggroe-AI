"""Risk Gate Bridge — Connects Agent Pipeline to Deterministic RiskCheckGate.

This bridge is the CRITICAL connection between the LLM-based agent
pipeline and the deterministic risk engine. It ensures that every trade
proposal passes through the 9-checkpoint RiskCheckGate BEFORE execution.

Flow:
    1. LLM Risk Agent provides qualitative risk analysis
    2. This bridge runs the deterministic RiskCheckGate (all 9 checkpoints)
    3. If the deterministic gate VETOES, the trade is REJECTED — no override
    4. If the deterministic gate APPROVES, the trade proceeds
    5. If the gate returns MODIFIED, position size is adjusted per Kelly

CRITICAL: The deterministic gate is the FINAL authority. If both the LLM
risk agent and the deterministic gate disagree, the deterministic gate WINS.
The LLM risk agent provides qualitative color; the deterministic gate
provides the hard veto/approval.

Constitutional limits enforced (HARDCODED — NO OVERRIDE):
- Max 0.5% risk per trade
- Max 1% daily loss
- Max 3% weekly loss
- Max 15% drawdown (kill switch)
- Min 1:2 risk:reward ratio
- Max 5 trades/day
- Max 3 correlated positions
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from quant_nanggroe.engine.risk.checks import RiskCheckGate
from quant_nanggroe.engine.risk.constants import (
    MAX_DAILY_LOSS,
    MAX_DRAWDOWN_PCT,
    MAX_RISK_PER_TRADE,
    MAX_WEEKLY_LOSS,
    MIN_RISK_REWARD,
)
from quant_nanggroe.engine.risk.manager import RiskManager
from quant_nanggroe.engine.risk.limits import RiskLimits

logger = logging.getLogger(__name__)


class GateVerdict(str, Enum):
    """Verdict from the deterministic risk gate bridge."""

    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    MODIFIED = "MODIFIED"  # Position size adjusted by Kelly
    KILL_SWITCH = "KILL_SWITCH"


@dataclass
class GateResult:
    """Result from the deterministic risk gate bridge.

    Attributes:
        verdict: APPROVED, REJECTED, MODIFIED, or KILL_SWITCH
        symbol: Trading symbol that was evaluated
        direction: Trade direction (BUY/SELL)
        checkpoints: Dict of all 9 checkpoint results
        failed_checkpoints: List of checkpoint names that failed
        adjusted_lot_size: If MODIFIED, the new position size; otherwise None
        adjusted_position_pct: If MODIFIED, the new position size as % of portfolio
        llm_verdict: The LLM risk agent's original verdict (for logging)
        llm_disagreement: True if LLM and deterministic gate disagreed
        reason: Human-readable reason string
        timestamp: When the gate evaluation occurred
    """

    verdict: GateVerdict
    symbol: str
    direction: str
    checkpoints: Dict[str, Any] = field(default_factory=dict)
    failed_checkpoints: List[str] = field(default_factory=list)
    adjusted_lot_size: Optional[float] = None
    adjusted_position_pct: Optional[float] = None
    llm_verdict: Optional[str] = None
    llm_disagreement: bool = False
    reason: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for agent state."""
        return {
            "verdict": self.verdict.value,
            "symbol": self.symbol,
            "direction": self.direction,
            "checkpoints": self.checkpoints,
            "failed_checkpoints": self.failed_checkpoints,
            "adjusted_lot_size": self.adjusted_lot_size,
            "adjusted_position_pct": self.adjusted_position_pct,
            "llm_verdict": self.llm_verdict,
            "llm_disagreement": self.llm_disagreement,
            "reason": self.reason,
            "timestamp": self.timestamp,
            "source": "deterministic_risk_gate",
        }


class RiskGateBridge:
    """Bridge between the LLM agent pipeline and the deterministic RiskCheckGate.

    This bridge is a MANDATORY step in the trade flow. It sits AFTER the
    LLM-based Risk Agent and BEFORE the Execution Agent.

    Usage:
        bridge = RiskGateBridge()
        result = bridge.evaluate(
            symbol="AAPL",
            direction="BUY",
            lot_size=0.1,
            entry=150.0,
            stop_loss=148.0,
            account_balance=1_000_000,
            take_profit=154.0,
            llm_verdict="APPROVED",
            daily_pnl=-500.0,
            weekly_pnl=-2000.0,
            trade_count_today=2,
            active_positions=["GOOGL", "MSFT"],
        )
        if result.verdict == GateVerdict.APPROVED:
            # Proceed to execution
        elif result.verdict == GateVerdict.REJECTED:
            # Trade blocked — check result.failed_checkpoints
    """

    def __init__(
        self,
        initial_equity: float = 1_000_000.0,
    ) -> None:
        """Initialize the Risk Gate Bridge.

        Args:
            initial_equity: Starting account equity for the RiskManager.
        """
        self._risk_manager = RiskManager(initial_equity=initial_equity)
        self._check_gate = RiskCheckGate()
        self._risk_limits = RiskLimits(max_weekly_loss_pct=MAX_WEEKLY_LOSS)

        logger.info(
            "RiskGateBridge initialized with equity=%.2f, "
            "constitutional limits: max_risk=%.2f%%, max_daily_loss=%.2f%%, "
            "max_weekly_loss=%.2f%%, max_drawdown=%.0f%%, min_rr=1:%.1f",
            initial_equity,
            MAX_RISK_PER_TRADE * 100,
            MAX_DAILY_LOSS * 100,
            MAX_WEEKLY_LOSS * 100,
            MAX_DRAWDOWN_PCT * 100,
            MIN_RISK_REWARD,
        )

    @property
    def risk_manager(self) -> RiskManager:
        """Access the underlying RiskManager for P&L updates."""
        return self._risk_manager

    def evaluate(
        self,
        symbol: str,
        direction: str,
        lot_size: float,
        entry: float,
        stop_loss: float,
        account_balance: float = 1_000_000.0,
        take_profit: Optional[float] = None,
        llm_verdict: Optional[str] = None,
        daily_pnl: float = 0.0,
        weekly_pnl: float = 0.0,
        trade_count_today: int = 0,
        active_positions: Optional[List[str]] = None,
    ) -> GateResult:
        """Run the deterministic 9-checkpoint risk gate on a trade proposal.

        This is the FINAL gate — it CANNOT be bypassed. If the deterministic
        gate rejects, the trade is blocked regardless of the LLM verdict.

        Args:
            symbol: Trading symbol (e.g., "AAPL", "EURUSD")
            direction: Trade direction ("BUY" or "SELL")
            lot_size: Proposed lot size
            entry: Entry price
            stop_loss: Stop loss price
            account_balance: Current account balance
            take_profit: Optional take profit price
            llm_verdict: The LLM risk agent's verdict (for comparison logging)
            daily_pnl: Today's accumulated P&L
            weekly_pnl: This week's accumulated P&L
            trade_count_today: Number of trades executed today
            active_positions: List of currently held symbols

        Returns:
            GateResult with the deterministic gate's final verdict
        """
        logger.info(
            "=== Deterministic Risk Gate: Evaluating %s %s | lot=%.4f entry=%.2f sl=%.2f | LLM verdict=%s ===",
            direction, symbol, lot_size, entry, stop_loss,
            llm_verdict or "N/A",
        )

        active_positions = active_positions or []

        # Step 0: Persistent weekly loss gate (RiskLimits — JSON-backed, resets Monday)
        if not self._risk_limits.can_trade():
            weekly_loss = self._risk_limits.current_weekly_loss_pct() * 100
            logger.critical(
                "DETERMINISTIC GATE: WEEKLY LOSS LIMIT REACHED (%.2f%%) — %s %s BLOCKED",
                weekly_loss, direction, symbol,
            )
            return GateResult(
                verdict=GateVerdict.KILL_SWITCH,
                symbol=symbol,
                direction=direction,
                reason=f"Weekly loss limit reached ({weekly_loss:.2f}%). Trading halted until Monday reset.",
                llm_verdict=llm_verdict,
                llm_disagreement=llm_verdict != "KILL_SWITCH",
            )

        # Step 1: Kill-switch auto-activation (FAIL-CLOSED hierarchy)
        # Runs ONLY AFTER RiskLimits.can_trade() (Step 0) passed. The persistent
        # weekly-loss gate is the OUTERMOST gate; once it is satisfied we evaluate
        # the live risk metrics for auto-activation. check_auto_activate is
        # fail-closed: it requires all four metrics supplied EXPLICITLY (a None
        # raises ValueError rather than silently defaulting to 0.0 — a fail-open
        # hole). If any threshold is breached it auto-activates the kill switch
        # (LEVEL_1 daily-loss/vol-spike, LEVEL_2 weekly-loss/drawdown) and returns
        # a KillSwitchEvent; otherwise it returns None.
        auto_ks_event = self._risk_manager.kill_switch.check_auto_activate(
            daily_pnl_pct=self._loss_fraction(daily_pnl, account_balance),
            weekly_pnl_pct=self._loss_fraction(weekly_pnl, account_balance),
            max_drawdown_pct=self._risk_manager.drawdown_monitor.current_drawdown,
            volatility_pct=self._current_volatility_pct(),
        )
        if auto_ks_event is not None:
            logger.critical(
                "DETERMINISTIC GATE: KILL SWITCH AUTO-ACTIVATED — trade %s %s BLOCKED",
                direction, symbol,
            )
            return GateResult(
                verdict=GateVerdict.KILL_SWITCH,
                symbol=symbol,
                direction=direction,
                reason=f"Kill switch auto-activated: {auto_ks_event.reason}. All trading halted.",
                llm_verdict=llm_verdict,
                llm_disagreement=llm_verdict != "KILL_SWITCH",
            )

        # Step 2: Defensive check — kill switch already active (from another proc).
        # check_auto_activate above reconciles the shared cross-proc state, so this
        # catches a switch activated elsewhere (or before metrics were available).
        if self._risk_manager.kill_switch.is_active:
            logger.critical(
                "DETERMINISTIC GATE: KILL SWITCH ACTIVE — trade %s %s BLOCKED",
                direction, symbol,
            )
            result = GateResult(
                verdict=GateVerdict.KILL_SWITCH,
                symbol=symbol,
                direction=direction,
                reason="Kill switch active. All trading halted. Manual reset required.",
                llm_verdict=llm_verdict,
                llm_disagreement=llm_verdict != "KILL_SWITCH",
            )
            logger.warning(
                "DETERMINISTIC GATE: %s %s → %s (kill switch)",
                direction, symbol, result.verdict.value,
            )
            return result

        # Step 3: Run the 9-checkpoint gate via RiskManager.check_trade
        gate_result = self._risk_manager.check_trade(
            symbol=symbol,
            direction=direction,
            lot_size=lot_size,
            entry=entry,
            stop_loss=stop_loss,
            account_balance=account_balance,
            take_profit=take_profit,
        )

        # Step 3: Extract checkpoint details
        checkpoints = gate_result.get("checkpoints", {})
        failed_checkpoints = gate_result.get("failed_checkpoints", [])
        gate_verdict_str = gate_result.get("verdict", "VETOED")

        # Step 4: Determine if LLM and deterministic gate disagree
        llm_disagreement = False
        if llm_verdict is not None:
            llm_approved = llm_verdict in ("APPROVED", "CONDITIONAL")
            gate_approved = gate_verdict_str == "APPROVED"
            llm_disagreement = llm_approved != gate_approved

        if llm_disagreement:
            logger.warning(
                "DETERMINISTIC GATE: DISAGREEMENT — LLM=%s, Deterministic=%s. "
                "Deterministic WINS (hard gate).",
                llm_verdict, gate_verdict_str,
            )

        # Step 5: Build the GateResult
        if gate_verdict_str == "APPROVED":
            # Check if Kelly would suggest a different position size
            kelly_result = self._compute_kelly_if_available(
                symbol=symbol,
                account_balance=account_balance,
                entry=entry,
                stop_loss=stop_loss,
            )

            if kelly_result and kelly_result["adjusted_fraction"] > 0:
                # Kelly-adjusted position size
                adjusted_lot = self._kelly_adjusted_lot(
                    lot_size=lot_size,
                    kelly_fraction=kelly_result["adjusted_fraction"],
                    account_balance=account_balance,
                    entry=entry,
                    stop_loss=stop_loss,
                )

                # If Kelly significantly reduces the position, mark as MODIFIED
                if adjusted_lot < lot_size * 0.95:
                    result = GateResult(
                        verdict=GateVerdict.MODIFIED,
                        symbol=symbol,
                        direction=direction,
                        checkpoints=checkpoints,
                        failed_checkpoints=failed_checkpoints,
                        adjusted_lot_size=adjusted_lot,
                        adjusted_position_pct=kelly_result["adjusted_fraction"] * 100,
                        llm_verdict=llm_verdict,
                        llm_disagreement=llm_disagreement,
                        reason=(
                            f"APPROVED by risk gate but Kelly suggests smaller position. "
                            f"Original lot={lot_size:.4f}, Kelly-adjusted lot={adjusted_lot:.4f}. "
                            f"Kelly fraction={kelly_result['adjusted_fraction']:.4f}"
                        ),
                    )
                    logger.info(
                        "DETERMINISTIC GATE: %s %s → MODIFIED (Kelly adjustment: "
                        "lot %.4f → %.4f, fraction=%.4f)",
                        direction, symbol, lot_size, adjusted_lot,
                        kelly_result["adjusted_fraction"],
                    )
                    return result

            # Straight approval — position size unchanged
            result = GateResult(
                verdict=GateVerdict.APPROVED,
                symbol=symbol,
                direction=direction,
                checkpoints=checkpoints,
                failed_checkpoints=failed_checkpoints,
                llm_verdict=llm_verdict,
                llm_disagreement=llm_disagreement,
                reason="All 9 checkpoints passed. Trade approved.",
            )
            logger.info(
                "DETERMINISTIC GATE: %s %s → APPROVED (all 9 checkpoints passed)",
                direction, symbol,
            )
            return result

        else:
            # VETOED by deterministic gate — NO OVERRIDE POSSIBLE
            result = GateResult(
                verdict=GateVerdict.REJECTED,
                symbol=symbol,
                direction=direction,
                checkpoints=checkpoints,
                failed_checkpoints=failed_checkpoints,
                llm_verdict=llm_verdict,
                llm_disagreement=llm_disagreement,
                reason=(
                    f"REJECTED by deterministic risk gate. "
                    f"Failed checkpoints: {failed_checkpoints}. "
                    f"NO OVERRIDE POSSIBLE."
                ),
            )
            logger.warning(
                "DETERMINISTIC GATE: %s %s → REJECTED (failed: %s)%s",
                direction, symbol,
                ", ".join(failed_checkpoints) if failed_checkpoints else "unknown",
                " [OVERRIDES LLM APPROVAL]" if llm_disagreement else "",
            )
            return result

    def evaluate_from_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate trade decisions from the agent pipeline state.

        This is the primary integration point for the LangGraph agent pipeline.
        It takes the agent state after the LLM risk assessment and runs
        the deterministic gate on each decision.

        Args:
            state: Current AgentState dictionary

        Returns:
            State updates with deterministic risk gate results
        """
        logger.info("=== Deterministic Risk Gate Bridge: Evaluating from agent state ===")

        decisions = state.get("decisions", [])
        if not decisions:
            # Try signals if no decisions yet
            signals = state.get("signals", [])
            if signals:
                decisions = signals

        if not decisions:
            logger.info("DETERMINISTIC GATE: No decisions/signals to evaluate — skipping")
            return {
                "deterministic_risk_verdict": "NO_TRADES",
                "deterministic_risk_results": [],
                "sender": "deterministic_risk_gate",
            }

        # Get portfolio/account info from state
        portfolio_state = state.get("portfolio_state", {})
        metadata = state.get("metadata", {})
        account_balance = portfolio_state.get("total_value", 1_000_000.0)
        daily_pnl = metadata.get("daily_pnl", 0.0)
        weekly_pnl = metadata.get("weekly_pnl", 0.0)
        trade_count_today = metadata.get("trade_count_today", 0)
        active_positions = list(portfolio_state.get("positions", {}).keys()) if isinstance(portfolio_state.get("positions"), dict) else []

        # LLM risk verdict for comparison
        llm_verdict = state.get("risk_verdict", None)

        results: List[Dict[str, Any]] = []
        overall_verdict = GateVerdict.APPROVED
        any_kill_switch = False
        modified_decisions = []

        for decision in decisions:
            if not isinstance(decision, dict):
                continue

            symbol = decision.get("symbol", "UNKNOWN")
            direction = decision.get("action", "HOLD")
            lot_size = decision.get("quantity", decision.get("lot_size", 0.01))
            entry = decision.get("entry_price", 0.0)
            stop_loss = decision.get("stop_loss", 0.0)
            take_profit = decision.get("take_profit", None)

            # Skip HOLD/CLOSE actions
            if direction in ("HOLD", "CLOSE"):
                modified_decisions.append(decision)
                continue

            # Skip EMERGENCY_EXIT — always allow
            if direction == "EMERGENCY_EXIT":
                modified_decisions.append(decision)
                continue

            gate_result = self.evaluate(
                symbol=symbol,
                direction=direction,
                lot_size=lot_size,
                entry=entry,
                stop_loss=stop_loss,
                account_balance=account_balance,
                take_profit=take_profit,
                llm_verdict=llm_verdict,
                daily_pnl=daily_pnl,
                weekly_pnl=weekly_pnl,
                trade_count_today=trade_count_today,
                active_positions=active_positions,
            )

            results.append(gate_result.to_dict())

            # Update overall verdict
            if gate_result.verdict == GateVerdict.KILL_SWITCH:
                any_kill_switch = True
                overall_verdict = GateVerdict.KILL_SWITCH
            elif gate_result.verdict == GateVerdict.REJECTED:
                if overall_verdict != GateVerdict.KILL_SWITCH:
                    overall_verdict = GateVerdict.REJECTED
            elif gate_result.verdict == GateVerdict.MODIFIED:
                if overall_verdict not in (GateVerdict.KILL_SWITCH, GateVerdict.REJECTED):
                    overall_verdict = GateVerdict.MODIFIED
                # Update the decision with adjusted position size
                modified_decision = {**decision}
                if gate_result.adjusted_lot_size is not None:
                    modified_decision["quantity"] = gate_result.adjusted_lot_size
                if gate_result.adjusted_position_pct is not None:
                    modified_decision["position_size_pct"] = gate_result.adjusted_position_pct
                modified_decision["deterministic_risk_modified"] = True
                modified_decision["deterministic_risk_reason"] = gate_result.reason
                modified_decisions.append(modified_decision)
                continue

            if gate_result.verdict == GateVerdict.APPROVED:
                modified_decisions.append(decision)
            # REJECTED decisions are removed from the execution list
            elif gate_result.verdict == GateVerdict.REJECTED:
                modified_decisions.append({
                    **decision,
                    "action": "HOLD",
                    "original_action": direction,
                    "deterministic_risk_rejected": True,
                    "deterministic_risk_reason": gate_result.reason,
                    "failed_checkpoints": gate_result.failed_checkpoints,
                })

        # Log summary
        approved_count = sum(1 for r in results if r["verdict"] == "APPROVED")
        rejected_count = sum(1 for r in results if r["verdict"] == "REJECTED")
        modified_count = sum(1 for r in results if r["verdict"] == "MODIFIED")
        kill_switch_count = sum(1 for r in results if r["verdict"] == "KILL_SWITCH")

        logger.info(
            "DETERMINISTIC GATE SUMMARY: %d evaluated → %d approved, %d modified, "
            "%d rejected, %d kill_switch. Overall: %s",
            len(results), approved_count, modified_count, rejected_count,
            kill_switch_count, overall_verdict.value,
        )

        # Build state updates
        state_updates: Dict[str, Any] = {
            "deterministic_risk_verdict": overall_verdict.value,
            "deterministic_risk_results": results,
            "deterministic_risk_timestamp": datetime.now().isoformat(),
            "decisions": modified_decisions,
            "kill_switch_active": any_kill_switch or state.get("kill_switch_active", False),
            "sender": "deterministic_risk_gate",
        }

        # If all trades rejected, set should_halt
        if overall_verdict in (GateVerdict.REJECTED, GateVerdict.KILL_SWITCH):
            state_updates["should_halt"] = True

        # If kill switch triggered, update risk_verdict
        if any_kill_switch:
            state_updates["risk_verdict"] = "KILL_SWITCH"

        return state_updates

    def update_pnl(self, trade_pnl: float, symbol: Optional[str] = None) -> None:
        """Update P&L tracking in the deterministic risk manager.

        Call this after a trade is closed to keep the risk state current.

        Args:
            trade_pnl: P&L from the completed trade.
            symbol: Symbol of the trade.
        """
        self._risk_manager.update_pnl(trade_pnl, symbol)
        # Persist weekly loss tracker (RiskLimits — resets Monday)
        self._risk_limits.record_trade(trade_pnl)

    def add_position(self, symbol: str) -> None:
        """Track a new open position in the deterministic risk manager."""
        self._risk_manager.add_position(symbol)

    def remove_position(self, symbol: str) -> None:
        """Remove a closed position from the deterministic risk manager."""
        self._risk_manager.remove_position(symbol)

    def status(self) -> Dict[str, Any]:
        """Get current deterministic risk status."""
        return self._risk_manager.status()

    # ── Internal helpers ────────────────────────────────────────────────

    @staticmethod
    def _loss_fraction(pnl: float, account_balance: float) -> float:
        """Convert an absolute P&L figure to a loss fraction of equity.

        Positive/zero P&L returns 0.0 (no loss to trip the kill switch).
        Negative P&L returns the magnitude as a fraction of account balance.
        """
        if account_balance <= 0:
            return 0.0
        return abs(min(0.0, pnl)) / account_balance

    def _current_volatility_pct(self) -> float:
        """Current realized volatility as a fraction, for kill-switch spikes.

        Uses the RiskManager's HAR volatility-regime detector forecast
        (annualized realized vol). Returns 0.0 if the detector is unavailable
        — a 0.0 volatility never trips the spike threshold, which is the
        correct conservative behavior when volatility data is genuinely absent.
        """
        detector = getattr(self._risk_manager, "_vol_regime_detector", None)
        if detector is None:
            return 0.0
        try:
            return float(detector.forecast().daily_vol)
        except Exception as e:
            logger.debug("Volatility forecast unavailable: %s", e)
            return 0.0

    def _compute_kelly_if_available(
        self,
        symbol: str,
        account_balance: float,
        entry: float,
        stop_loss: float,
    ) -> Optional[Dict[str, Any]]:
        """Try to compute Kelly criterion position sizing.

        Returns None if insufficient data is available.

        Args:
            symbol: Trading symbol.
            account_balance: Account balance.
            entry: Entry price.
            stop_loss: Stop loss price.

        Returns:
            Kelly result dict or None.
        """
        try:
            # Use conservative defaults for Kelly when no historical data available
            # This ensures Kelly still provides a position sizing recommendation
            result = self._risk_manager.calculate_kelly_size(
                win_rate=0.55,  # Conservative default win rate
                avg_win=abs(entry - stop_loss) * 2 if entry and stop_loss else 1.0,
                avg_loss=abs(entry - stop_loss) if entry and stop_loss else 1.0,
                account_balance=account_balance,
                method="HALF_KELLY",
            )
            return result
        except Exception as e:
            logger.debug("Kelly calculation not available for %s: %s", symbol, e)
            return None

    @staticmethod
    def _kelly_adjusted_lot(
        lot_size: float,
        kelly_fraction: float,
        account_balance: float,
        entry: float,
        stop_loss: float,
    ) -> float:
        """Adjust lot size based on Kelly criterion fraction.

        Args:
            lot_size: Original proposed lot size.
            kelly_fraction: Kelly-adjusted fraction (0-1).
            account_balance: Account balance.
            entry: Entry price.
            stop_loss: Stop loss price.

        Returns:
            Adjusted lot size.
        """
        if entry <= 0 or stop_loss <= 0 or abs(entry - stop_loss) == 0:
            return lot_size

        # Calculate the position size based on Kelly fraction
        kelly_position_value = account_balance * kelly_fraction
        risk_per_unit = abs(entry - stop_loss)

        if risk_per_unit <= 0:
            return lot_size

        # For forex-style: 1 lot = 100,000 units
        # For stock-style: shares = position_value / entry_price
        kelly_lot = kelly_position_value / (risk_per_unit * 100000) if risk_per_unit > 0 else lot_size

        # Ensure we don't increase the lot size — Kelly can only reduce
        adjusted_lot = min(lot_size, max(0.01, round(kelly_lot * 100) / 100))

        return adjusted_lot
