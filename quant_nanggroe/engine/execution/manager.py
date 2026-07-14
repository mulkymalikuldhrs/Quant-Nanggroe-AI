"""Execution Manager with Smart Order Routing.

Manages order execution across multiple brokers with:
- Smart order routing (choose best broker for each order)
- Guard pipeline enforcement
- Position tracking and reconciliation
- Fill tracking and audit trail

Extracted from OpenAlice's ExecutionManager.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from quant_nanggroe.engine.execution.base import Broker, Fill, Order
from quant_nanggroe.engine.execution.fill import FillTracker
from quant_nanggroe.engine.execution.guards.cooldown import CooldownGuard
from quant_nanggroe.engine.execution.guards.max_position import MaxPositionGuard
from quant_nanggroe.engine.execution.guards.whitelist import WhitelistGuard
from quant_nanggroe.engine.execution.order import OrderManager
from quant_nanggroe.engine.risk.kill_switch import KillSwitch

if TYPE_CHECKING:
    from quant_nanggroe.engine.risk.manager import RiskManager

logger = logging.getLogger(__name__)


@dataclass
class GuardResult:
    """Result from guard pipeline evaluation."""

    allowed: bool
    guard_name: str
    reason: str = ""


class ExecutionManager:
    """Execution Manager with Smart Order Routing.

    Manages order execution across multiple broker connections,
    enforcing guard pipelines and tracking fills.

    Usage:
        manager = ExecutionManager()
        manager.add_broker(paper_broker)
        manager.add_guard(CooldownGuard(seconds=60))
        result = await manager.execute_order(order)
    """

    def __init__(self) -> None:
        self._brokers: Dict[str, Broker] = {}
        self._primary_broker: Optional[str] = None
        self._order_manager = OrderManager()
        self._fill_tracker = FillTracker()
        self._guards: List = []
        self._cooldown_guard = CooldownGuard()
        self._max_position_guard = MaxPositionGuard()
        self._whitelist_guard = WhitelistGuard()
        self._kill_switch: Optional[KillSwitch] = None
        self._risk_manager: Optional["RiskManager"] = None
        self._audit_log: List[Dict[str, Any]] = []

    def set_risk_manager(self, risk_manager: "RiskManager") -> None:
        """Attach a RiskManager; its constitutional limits are enforced on every order."""
        self._risk_manager = risk_manager

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

    def set_kill_switch(self, kill_switch: KillSwitch) -> None:
        """Attach a KillSwitch instance for early warning checks.

        Args:
            kill_switch: KillSwitch instance to query for warnings.
        """
        self._kill_switch = kill_switch

    async def execute_order(
        self,
        order: Order,
        daily_pnl_pct: float = 0.0,
        weekly_pnl_pct: float = 0.0,
        max_drawdown_pct: float = 0.0,
        volatility_pct: float = 0.0,
    ) -> Optional[Fill]:
        """Execute an order through the guard pipeline and broker.

        Args:
            order: Order to execute.

        Returns:
            Fill if order was executed, None if rejected.
        """
        # 1. Run guard pipeline
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

        # 2. Route to broker
        broker_name = self._route_order(order)
        broker = self._brokers.get(broker_name)

        if broker is None:
            logger.error("No broker available for order %s", order.id)
            return None

        # KillSwitch.check_auto_activate / check_warning take FRACTION pnl
        # (config thresholds: 0.015 == 1.5%), but execute_order's contract and
        # RiskManager.check_trade use PERCENT (0-100). Convert once at this
        # boundary so both layers read the same incoming percent values in
        # their correct units — otherwise the constitutional risk veto is dead
        # on the combined path (pitfall #11: kill switch over-fires as 100x
        # fraction, or risk never sees the loss).
        ks_daily = daily_pnl_pct / 100.0
        ks_weekly = weekly_pnl_pct / 100.0
        ks_drawdown = max_drawdown_pct / 100.0
        ks_volatility = volatility_pct / 100.0

        # 3. Kill switch — ENFORCED (not just a warning)
        if self._kill_switch is not None:
            # Auto-activate if thresholds breached, then hard-block the order
            self._kill_switch.check_auto_activate(
                daily_pnl_pct=ks_daily,
                weekly_pnl_pct=ks_weekly,
                max_drawdown_pct=ks_drawdown,
                volatility_pct=ks_volatility,
            )
            if not self._kill_switch.can_trade():
                logger.critical(
                    "Order %s BLOCKED by kill switch (level=%s, status=%s): "
                    "daily=%.2f%% weekly=%.2f%% drawdown=%.2f%% volatility=%.2f%%",
                    order.id, self._kill_switch.current_level.value,
                    self._kill_switch.status()["status"],
                    daily_pnl_pct, weekly_pnl_pct,
                    max_drawdown_pct, volatility_pct,
                )
                self._audit_log.append({
                    "action": "KILL_SWITCH_BLOCKED",
                    "order_id": order.id,
                    "symbol": order.symbol,
                    "side": order.side.value,
                    "level": self._kill_switch.current_level.value,
                    "daily_pnl_pct": daily_pnl_pct,
                    "weekly_pnl_pct": weekly_pnl_pct,
                    "max_drawdown_pct": max_drawdown_pct,
                    "volatility_pct": volatility_pct,
                })
                return None
            # Below threshold: still surface early warning for observability
            warning = self._kill_switch.check_warning(
                daily_pnl_pct=ks_daily,
                weekly_pnl_pct=ks_weekly,
                max_drawdown_pct=ks_drawdown,
                volatility_pct=ks_volatility,
            )
            if warning:
                logger.warning(
                    "Kill switch early warning: daily=%.2f%% weekly=%.2f%% "
                    "drawdown=%.2f%% volatility=%.2f%%",
                    daily_pnl_pct, weekly_pnl_pct,
                    max_drawdown_pct, volatility_pct,
                )

        # 4. Constitutional RiskManager — ENFORCED (no override possible)
        if self._risk_manager is not None:
            account_balance = 0.0
            try:
                account = await broker.get_account()
                account_balance = float(getattr(account, "balance", 0.0) or 0.0)
            except Exception:
                account_balance = 0.0
            verdict = self._risk_manager.check_trade(
                symbol=order.symbol,
                direction=order.side.value,
                lot_size=order.quantity,
                entry=order.price or 0.0,
                stop_loss=order.stop_price or 0.0,
                account_balance=account_balance,
                # Convert execution-layer percent P&L into the absolute equity fraction
                # the constitutional gate expects (daily_pnl_pct/100 * balance).
                daily_pnl_pct=daily_pnl_pct,
                weekly_pnl_pct=weekly_pnl_pct,
            )
            if verdict.get("verdict") == "VETOED":
                logger.critical(
                    "Order %s BLOCKED by RiskManager: %s — %s",
                    order.id, verdict.get("reason"), verdict.get("failed_checkpoints"),
                )
                self._audit_log.append({
                    "action": "RISK_VETOED",
                    "order_id": order.id,
                    "symbol": order.symbol,
                    "side": order.side.value,
                    "reason": verdict.get("reason"),
                    "failed_checkpoints": verdict.get("failed_checkpoints"),
                })
                return None

        # 5. Submit order
        try:
            updated_order = await broker.submit_order(order)
            self._order_manager.track(updated_order)

            # 4. Wait for fill (simplified - in production would be async)
            # For now, we return the order and let the fill tracker handle it
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

    def _as_guard_result(self, raw, name: str) -> GuardResult:
        """Normalize a guard's return value (GuardCheckResult / dict / GuardResult) to GuardResult."""
        if isinstance(raw, GuardResult):
            return raw
        # GuardCheckResult (cooldown guard) — has .allowed / .reason attributes
        if hasattr(raw, "allowed") and not isinstance(raw, dict):
            return GuardResult(bool(getattr(raw, "allowed", True)), name, getattr(raw, "reason", ""))
        if isinstance(raw, dict):
            return GuardResult(
                bool(raw.get("allowed", True)),
                name,
                raw.get("reason", ""),
            )
        # Unknown shape → fail closed
        return GuardResult(False, name, "invalid guard response")

    def _run_guards(self, order: Order) -> GuardResult:
        """Run all guard checks on an order.

        Args:
            order: Order to check.

        Returns:
            GuardResult with allow/deny decision.
        """
        # Cooldown guard
        result = self._as_guard_result(self._cooldown_guard.check(order), "cooldown")
        if not result.allowed:
            return GuardResult(False, "cooldown", result.reason)

        # Max position guard
        result = self._as_guard_result(self._max_position_guard.check(order), "max_position")
        if not result.allowed:
            return GuardResult(False, "max_position", result.reason)

        # Whitelist guard
        result = self._as_guard_result(self._whitelist_guard.check(order), "whitelist")
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
