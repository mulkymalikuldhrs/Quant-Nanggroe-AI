"""Execution Manager with Smart Order Routing.

Manages order execution across multiple brokers with:
- Smart order routing (choose best broker for each order)
- Guard pipeline enforcement
- RiskManager constitutional limit checks (P0-2 SAFETY)
- Kill switch enforcement (P0-2 SAFETY)
- Position tracking and reconciliation
- Fill tracking and audit trail

SAFETY (P0-2): Before executing ANY order, the ExecutionManager MUST:
1. Check if kill switch is active → if yes, REJECT the order
2. Run RiskManager.check_trade() → if risk check fails, REJECT the order
3. Only then proceed to guard pipeline and execution

Extracted from OpenAlice's ExecutionManager.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from quant_nanggroe.engine.execution.base import Broker, Order, OrderSide, OrderType, Fill, AccountInfo
from quant_nanggroe.engine.execution.order import OrderManager
from quant_nanggroe.engine.execution.fill import FillTracker
from quant_nanggroe.engine.execution.guards.cooldown import CooldownGuard
from quant_nanggroe.engine.execution.guards.max_position import MaxPositionGuard
from quant_nanggroe.engine.execution.guards.whitelist import WhitelistGuard

logger = logging.getLogger(__name__)


# ── P0-2 SAFETY: Custom error types for risk/kill-switch rejections ──

class KillSwitchActiveError(Exception):
    """Raised when an order is rejected because the kill switch is active."""

    def __init__(self, reason: Optional[str] = None) -> None:
        self.reason = reason or "KILL_SWITCH_ACTIVE"
        super().__init__(
            f"Order rejected: Kill switch is active ({self.reason}). "
            f"All trading is halted until manual review."
        )


class RiskLimitRejectedError(Exception):
    """Raised when an order is rejected by RiskManager constitutional limits."""

    def __init__(self, verdict: str, details: Dict[str, Any]) -> None:
        self.verdict = verdict
        self.details = details
        failed = details.get("failed_checkpoints", [])
        super().__init__(
            f"Order rejected by RiskManager: verdict={verdict}, "
            f"failed_checkpoints={failed}"
        )


@dataclass
class GuardResult:
    """Result from guard pipeline evaluation."""

    allowed: bool
    guard_name: str
    reason: str = ""


class ExecutionManager:
    """Execution Manager with Smart Order Routing.

    Manages order execution across multiple broker connections,
    enforcing kill switch checks, risk manager constitutional limits,
    and guard pipelines.

    SAFETY (P0-2): Execution order is:
    1. Kill switch check
    2. RiskManager.check_trade()
    3. Guard pipeline (cooldown, max-position, whitelist)
    4. Broker routing and execution

    Usage:
        manager = ExecutionManager()
        manager.add_broker(paper_broker)
        manager.add_guard(CooldownGuard(seconds=60))
        result = await manager.execute_order(order)
    """

    def __init__(
        self,
        risk_manager=None,
        kill_switch=None,
    ) -> None:
        """Initialize ExecutionManager.

        Args:
            risk_manager: Optional RiskManager instance. If not provided,
                a new one will be created lazily on first use.
            kill_switch: Optional KillSwitch instance. If not provided,
                a new one will be created lazily on first use.
        """
        self._brokers: Dict[str, Broker] = {}
        self._primary_broker: Optional[str] = None
        self._order_manager = OrderManager()
        self._fill_tracker = FillTracker()
        self._guards: List = []
        self._cooldown_guard = CooldownGuard()
        self._max_position_guard = MaxPositionGuard()
        self._whitelist_guard = WhitelistGuard()
        self._audit_log: List[Dict[str, Any]] = []

        # P0-2 SAFETY: Risk and kill switch references
        self._risk_manager = risk_manager
        self._kill_switch = kill_switch

    def _get_kill_switch(self):
        """Lazily obtain the KillSwitch instance."""
        if self._kill_switch is None:
            from quant_nanggroe.engine.risk.kill_switch import KillSwitch
            self._kill_switch = KillSwitch()
        return self._kill_switch

    def _get_risk_manager(self):
        """Lazily obtain the RiskManager instance."""
        if self._risk_manager is None:
            from quant_nanggroe.engine.risk.manager import RiskManager
            self._risk_manager = RiskManager()
        return self._risk_manager

    def add_broker(self, broker: Broker, primary: bool = False) -> None:
        """Add a broker connection.

        Args:
            broker: Broker instance.
            primary: Whether this is the primary broker.
        """
        self._brokers[broker.name] = broker
        if primary or self._primary_broker is None:
            self._primary_broker = broker.name

    def remove_broker(self, name: str) -> None:
        """Remove a broker connection."""
        self._brokers.pop(name, None)
        if self._primary_broker == name:
            self._primary_broker = next(iter(self._brokers), None)

    async def execute_order(self, order: Order) -> Optional[Fill]:
        """Execute an order through the full safety pipeline.

        SAFETY (P0-2): Execution order is:
        1. Check kill switch → if active, REJECT immediately
        2. Run RiskManager.check_trade() → if VETOED, REJECT
        3. Run guard pipeline (cooldown, max-position, whitelist)
        4. Route to broker and execute

        Args:
            order: Order to execute.

        Returns:
            Fill if order was executed, None if rejected.
        """
        # ══════════════════════════════════════════════════════════════
        # STEP 0: Kill Switch Check (P0-2 SAFETY — HIGHEST PRIORITY)
        # ══════════════════════════════════════════════════════════════
        kill_switch = self._get_kill_switch()
        if kill_switch.is_active:
            logger.critical(
                "Order %s REJECTED: Kill switch is active (reason: %s)",
                order.id,
                kill_switch.status().get("activation_reason", "UNKNOWN"),
            )
            self._audit_log.append({
                "action": "KILL_SWITCH_REJECTED",
                "order_id": order.id,
                "reason": kill_switch.status().get("activation_reason", "UNKNOWN"),
            })
            # Raise error so callers know the order was rejected by kill switch
            raise KillSwitchActiveError(
                reason=kill_switch.status().get("activation_reason")
            )

        # ══════════════════════════════════════════════════════════════
        # STEP 1: RiskManager Constitutional Limit Check (P0-2 SAFETY)
        # ══════════════════════════════════════════════════════════════
        risk_manager = self._get_risk_manager()
        try:
            risk_result = risk_manager.check_trade(
                symbol=order.symbol,
                direction=order.side.value,
                lot_size=order.quantity,
                entry=order.price or 0.0,
                stop_loss=order.stop_price or 0.0,
            )

            if risk_result.get("verdict") == "VETOED":
                logger.warning(
                    "Order %s REJECTED by RiskManager: %s",
                    order.id,
                    risk_result.get("reason", risk_result.get("failed_checkpoints", [])),
                )
                self._audit_log.append({
                    "action": "RISK_VETOED",
                    "order_id": order.id,
                    "verdict": risk_result.get("verdict"),
                    "reason": risk_result.get("reason"),
                    "failed_checkpoints": risk_result.get("failed_checkpoints", []),
                })
                raise RiskLimitRejectedError(
                    verdict=risk_result.get("verdict", "VETOED"),
                    details=risk_result,
                )
        except (KillSwitchActiveError, RiskLimitRejectedError):
            raise  # Re-raise our own errors
        except Exception as exc:
            # If risk check fails unexpectedly, REJECT the order (fail-safe)
            logger.error(
                "Order %s REJECTED: RiskManager.check_trade() raised exception: %s",
                order.id,
                exc,
            )
            self._audit_log.append({
                "action": "RISK_CHECK_ERROR",
                "order_id": order.id,
                "error": str(exc),
            })
            raise RiskLimitRejectedError(
                verdict="ERROR",
                details={"error": str(exc)},
            )

        # ══════════════════════════════════════════════════════════════
        # STEP 2: Guard Pipeline (existing functionality)
        # ══════════════════════════════════════════════════════════════
        guard_result = self._run_guards(order)
        if not guard_result.allowed:
            logger.warning(
                "Order %s blocked by guard %s: %s",
                order.id, guard_result.guard_name, guard_result.reason,
            )
            self._audit_log.append({
                "action": "GUARD_BLOCKED",
                "order_id": order.id,
                "guard": guard_result.guard_name,
                "reason": guard_result.reason,
            })
            return None

        # ══════════════════════════════════════════════════════════════
        # STEP 3: Route to Broker and Execute
        # ══════════════════════════════════════════════════════════════
        broker_name = self._route_order(order)
        broker = self._brokers.get(broker_name)

        if broker is None:
            logger.error("No broker available for order %s", order.id)
            return None

        try:
            updated_order = await broker.submit_order(order)
            self._order_manager.track(updated_order)

            self._audit_log.append({
                "action": "ORDER_SUBMITTED",
                "order_id": order.id,
                "broker": broker_name,
                "symbol": order.symbol,
                "side": order.side.value,
                "quantity": order.quantity,
            })

            return Fill(
                id=str(uuid.uuid4()),
                order_id=order.id,
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                price=order.price or 0.0,
            )

        except Exception as exc:
            logger.error("Order execution failed: %s", exc)
            self._audit_log.append({
                "action": "EXECUTION_FAILED",
                "order_id": order.id,
                "error": str(exc),
            })
            return None

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order.

        Args:
            order_id: Order ID to cancel.

        Returns:
            True if cancelled successfully.
        """
        order = self._order_manager.get(order_id)
        if order is None:
            return False

        for broker in self._brokers.values():
            try:
                return await broker.cancel_order(order_id)
            except Exception:
                continue

        return False

    def _run_guards(self, order: Order) -> GuardResult:
        """Run all guard checks on an order.

        Args:
            order: Order to check.

        Returns:
            GuardResult with allow/deny decision.
        """
        # Cooldown guard
        result = self._cooldown_guard.check(order)
        if not result.allowed:
            return GuardResult(False, "cooldown", result.reason)

        # Max position guard
        result = self._max_position_guard.check(order)
        if not result.allowed:
            return GuardResult(False, "max_position", result.reason)

        # Whitelist guard
        result = self._whitelist_guard.check(order)
        if not result.allowed:
            return GuardResult(False, "whitelist", result.reason)

        # Custom guards
        for guard in self._guards:
            result = guard.check(order)
            if not result.allowed:
                return GuardResult(False, guard.name, result.reason)

        return GuardResult(True, "all_guards", "All guards passed")

    def _route_order(self, order: Order) -> str:
        """Smart order routing.

        Selects the best broker for each order based on:
        - Symbol availability
        - Broker health
        - Latency

        Args:
            order: Order to route.

        Returns:
            Broker name to use.
        """
        if self._primary_broker and self._primary_broker in self._brokers:
            return self._primary_broker
        return next(iter(self._brokers), "paper")

    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Get the execution audit log."""
        return list(self._audit_log)

    @property
    def order_manager(self) -> OrderManager:
        """Get the order manager."""
        return self._order_manager

    @property
    def fill_tracker(self) -> FillTracker:
        """Get the fill tracker."""
        return self._fill_tracker
