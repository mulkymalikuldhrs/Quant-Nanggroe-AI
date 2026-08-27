"""Execution Manager with Smart Order Routing.

Manages order execution across multiple brokers with:
- Smart order routing (choose best broker for each order)
- Guard pipeline enforcement
- Position tracking and reconciliation
- Fill tracking and audit trail

Extracted from OpenAlice's ExecutionManager.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from quant_nanggroe.engine.execution.base import Broker, Fill, Order, OrderStatus
from quant_nanggroe.engine.execution.fill import FillTracker
from quant_nanggroe.engine.execution.guards.cooldown import CooldownGuard
from quant_nanggroe.engine.execution.guards.max_position import MaxPositionGuard
from quant_nanggroe.engine.execution.guards.whitelist import WhitelistGuard
from quant_nanggroe.engine.execution.order import OrderManager
from quant_nanggroe.engine.risk.kill_switch import KillSwitch
from quant_nanggroe.engine.risk.veto_guard import GovernanceVetoGuard

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
        self._governance_veto = GovernanceVetoGuard()
        # ponytail: default ACTIVE switch — bare ExecutionManager() is enforced, not silently open
        self._kill_switch: Optional[KillSwitch] = KillSwitch()
        self._risk_manager: Optional["RiskManager"] = None
        self._audit_log: List[Dict[str, Any]] = []
        self._audit_log_path: Optional[str] = None
        self._setup_audit_log()

    def _setup_audit_log(self) -> None:
        """Initialize audit log path for persistence."""
        try:
            state_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
                "paper_state",
            )
            os.makedirs(state_dir, exist_ok=True)
            self._audit_log_path = os.path.join(state_dir, "execution_audit.jsonl")
        except Exception:
            self._audit_log_path = None

    def _persist_audit_entry(self, entry: Dict[str, Any]) -> None:
        """Append a single audit entry to the JSONL log file."""
        if not self._audit_log_path:
            return
        try:
            entry_with_ts = {**entry, "timestamp": datetime.now(timezone.utc).isoformat()}
            with open(self._audit_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry_with_ts, default=str) + "\n")
        except Exception:
            pass

    def _record_audit(self, entry: Dict[str, Any]) -> None:
        """Record an audit entry to both in-memory log and persistent JSONL file."""
        self._audit_log.append(entry)
        self._persist_audit_entry(entry)

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

    # ── Public API for external consumers (builder, live_engine) ──

    def get_risk_manager(self) -> Optional["RiskManager"]:
        """Return the attached RiskManager, or None."""
        return self._risk_manager

    def get_brokers(self) -> Dict[str, Broker]:
        """Return a shallow copy of the broker map (name → Broker)."""
        return dict(self._brokers)

    def get_primary_broker_name(self) -> Optional[str]:
        """Return the name of the primary broker."""
        return self._primary_broker

    def get_broker(self, name: str) -> Optional[Broker]:
        """Return a broker by name, or None if not registered."""
        return self._brokers.get(name)

    def set_broker_handle(self, mt5_handle) -> None:
        """Attach a live MT5 handle to the RiskManager for realized PnL sync.

        Replaces the fragile em._risk_manager.set_broker_handle(mt5)
        private-attribute access pattern used by builder.py.
        """
        if self._risk_manager is not None:
            self._risk_manager.set_broker_handle(mt5_handle)
        else:
            logger.warning("set_broker_handle called but no RiskManager attached")

    def get_mt5_connector(self):
        """Return the raw MT5Broker connector if one is registered, else None.

        Used by live_engine.py for broker position sync on startup.
        """
        for b in self._brokers.values():
            if hasattr(b, "_mt5"):
                return b._mt5
        return None

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
        # All downstream consumers (guard, kill switch, RiskManager) take FRACTION
        # pnl (config thresholds: 0.015 == 1.5%). Convert once at this boundary so
        # every layer reads the same fraction convention — this closes the 100x silent
        # under-report that occurred when feeding snapshot fractions (returned by
        # current_risk_snapshot) into check_trade which expected percent.
        ks_daily = daily_pnl_pct / 100.0
        ks_weekly = weekly_pnl_pct / 100.0
        ks_drawdown = max_drawdown_pct / 100.0
        ks_volatility = volatility_pct / 100.0

        # F14: the daemon calls execute_order WITHOUT pnl args (all zeros),
        # which left the governance veto and EM-level kill-switch auto-activate
        # inert. Pull REAL fractions from the wired RiskManager state instead.
        if self._risk_manager is not None and hasattr(self._risk_manager, "state"):
            try:
                rm_state = self._risk_manager.state
                peak = float(getattr(rm_state, "peak_equity", 0.0) or 0.0)
                if daily_pnl_pct == 0.0 and peak > 0:
                    ks_daily = min(0.0, float(getattr(rm_state, "daily_pnl", 0.0) or 0.0)) / peak
                if weekly_pnl_pct == 0.0 and peak > 0:
                    ks_weekly = min(0.0, float(getattr(rm_state, "weekly_pnl", 0.0) or 0.0)) / peak
            except Exception:
                pass

        # 1. Run guard pipeline
        self._governance_veto.update_pnl(ks_daily, ks_weekly)
        self._governance_veto.update_drawdown(ks_drawdown)
        guard_result = self._run_guards(order)
        if not guard_result.allowed:
            logger.warning(
                "Order %s blocked by guard %s: %s",
                order.id, guard_result.guard_name, guard_result.reason,
            )
            self._record_audit({
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

        # 2.5 ONE-POSITION-PER-SYMBOL mandate (non-negotiable rule #5).
        # Query BROKER TRUTH (not local state) so restarts/reconciliations
        # cannot desync. Fail-closed: a failed position query blocks the trade.
        # R2 companion fix (2026-08-25): an OPPOSITE-side order CLOSES the open
        # position — blocking it left trailing-stop exits permanently blocked.
        # Rule now: block only SAME-SIDE additions (pyramiding) or unknown-side
        # positions unless the order is explicitly reduce_only.
        try:
            open_positions = await broker.get_positions()
            incoming_buy = order.side.value.lower() == "buy"
            reduce_only = bool(order.metadata.get("reduce_only", False))

            def _base_name(s: str) -> str:
                # F8: broker positions carry suffixed names (EURUSD.vx) while
                # orders may carry bare names (EURUSD) — compare base-only so
                # suffix variants cannot defeat the one-position mandate.
                return str(s).upper().split(".")[0]

            order_base = _base_name(order.symbol)
            conflicts = []
            for p in (open_positions or []):
                if _base_name(getattr(p, "symbol", "")) != order_base:
                    continue
                pos_side = str(getattr(p, "side", "") or "").lower()
                if not pos_side:
                    qty = float(getattr(p, "quantity", 0.0) or 0.0)
                    pos_side = "buy" if qty > 0 else ("sell" if qty < 0 else "")
                if reduce_only:
                    continue  # explicit exit intent — never blocked by this gate
                if pos_side == "":
                    conflicts.append(p)  # unknown direction → fail-closed
                elif (pos_side == "buy") == incoming_buy:
                    conflicts.append(p)  # same-side pyramid → forbidden
            if conflicts:
                logger.critical(
                    "Order %s BLOCKED: position already OPEN on %s "
                    "(%d conflicting, sides=%s) — one-position-per-symbol mandate",
                    order.id, order.symbol, len(conflicts),
                    [getattr(p, "side", getattr(p, "quantity", "?")) for p in conflicts],
                )
                self._record_audit({
                    "action": "DUPLICATE_POSITION_BLOCKED",
                    "order_id": order.id,
                    "symbol": order.symbol,
                    "open_count": len(conflicts),
                })
                return None
        except Exception as pos_exc:
            logger.critical(
                "Order %s BLOCKED: position query failed (%s) — fail-closed",
                order.id, pos_exc,
            )
            self._record_audit({
                "action": "POSITION_QUERY_FAILED",
                "order_id": order.id,
                "symbol": order.symbol,
                "reason": str(pos_exc),
            })
            return None

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
                self._record_audit({
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
                # daily_pnl_pct is already converted to fraction at line 181;
                # check_trade now expects fraction (range [0, 1]).
                daily_pnl_pct=ks_daily,
                weekly_pnl_pct=ks_weekly,
            )
            if verdict.get("verdict") == "VETOED":
                logger.critical(
                    "Order %s BLOCKED by RiskManager: %s — %s",
                    order.id, verdict.get("reason"), verdict.get("failed_checkpoints"),
                )
                self._record_audit({
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

            # 5.5 Fill-status gate: a REJECTED order must NEVER produce a Fill.
            # The old code built a phantom Fill (price 0.0) for rejected orders —
            # fake Telegram "TRADE EXECUTED", trailing stop anchored at 0,
            # polluted guard/cooldown state. Fail-closed on any non-FILLED status.
            if getattr(updated_order, "status", None) != OrderStatus.FILLED:
                logger.critical(
                    "Order %s NOT FILLED (status=%s, reason=%s) — no fill returned",
                    order.id,
                    getattr(updated_order.status, "value", updated_order.status),
                    updated_order.metadata.get("reason", "n/a"),
                )
                self._record_audit({
                    "action": "ORDER_NOT_FILLED",
                    "order_id": order.id,
                    "status": getattr(updated_order.status, "value", str(updated_order.status)),
                    "error_code": updated_order.metadata.get("error_code"),
                    "reason": updated_order.metadata.get("reason"),
                    "symbol": order.symbol,
                })
                return None

            self._record_audit({
                "action": "ORDER_SUBMITTED",
                "order_id": order.id,
                "broker": broker_name,
                "symbol": order.symbol,
                "side": order.side.value,
                "quantity": order.quantity,
            })

            # Use broker's actual fill price (from metadata), not the order's limit price
            fill_price = updated_order.metadata.get("fill_price") or updated_order.price or 0.0
            fill = Fill(
                id=str(uuid.uuid4()),
                order_id=order.id,
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                price=fill_price,
                commission=updated_order.metadata.get("commission", 0.0),
            )

            # Wire guards: record trade for cooldown, update position tracking
            self._cooldown_guard.record_trade(order.symbol)
            fill_notional = fill.price * fill.quantity
            self._max_position_guard.update_position(order.symbol, fill_notional)

            # Record fill in tracker for execution quality metrics
            self._fill_tracker.record(fill)

            return fill

        except Exception as exc:
            logger.error("Order execution failed: %s [%s]", exc, type(exc).__name__, exc_info=True)
            self._record_audit({
                "action": "EXECUTION_FAILED",
                "order_id": order.id,
                "error": str(exc),
                "error_type": type(exc).__name__,
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

        # Try to cancel via the broker that handled the order
        broker_name = self._route_order(order)
        broker = self._brokers.get(broker_name)
        if broker:
            try:
                return await broker.cancel_order(order_id)
            except Exception:
                pass

        # Fallback: try all other brokers
        for name, b in self._brokers.items():
            if name == broker_name:
                continue
            try:
                return await b.cancel_order(order_id)
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

        # Max position guard — update portfolio value from RiskManager before check
        if self._risk_manager is not None:
            equity = getattr(self._risk_manager.state, "current_equity", 0)
            if equity > 0:
                self._max_position_guard.update_portfolio_value(equity)
        result = self._as_guard_result(self._max_position_guard.check(order), "max_position")
        if not result.allowed:
            return GuardResult(False, "max_position", result.reason)

        # Whitelist guard
        result = self._as_guard_result(self._whitelist_guard.check(order), "whitelist")
        if not result.allowed:
            return GuardResult(False, "whitelist", result.reason)

        # Governance veto — fail-closed constitutional check
        gov_result = self._as_guard_result(
            self._governance_veto.check(order), "governance_veto"
        )
        if not gov_result.allowed:
            return GuardResult(False, "governance_veto", gov_result.reason)

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
        - Broker health (connected status)
        - Fallback chain if primary is unhealthy

        Args:
            order: Order to route.

        Returns:
            Broker name to use.
        """
        # Symbol-specific routing hints
        crypto_symbols = {"BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "ADA-USD"}
        forex_symbols = {"EURUSD", "GBPUSD", "USDJPY", "USDCAD", "AUDUSD"}

        def _broker_healthy(name: str) -> bool:
            b = self._brokers.get(name)
            return b is not None and b.is_connected

        # Try primary broker first if healthy
        if self._primary_broker and self._primary_broker in self._brokers:
            if _broker_healthy(self._primary_broker):
                return self._primary_broker
            logger.warning("Primary broker %s unhealthy, falling back", self._primary_broker)

        # Symbol-aware fallback: try brokers that likely support the symbol
        if order.symbol in crypto_symbols:
            preferred_order = ["binance", "paper"]
        elif order.symbol in forex_symbols:
            preferred_order = ["mt5", "paper"]
        else:
            preferred_order = ["paper"]

        for name in preferred_order:
            if name in self._brokers and _broker_healthy(name):
                return name

        # Last resort: any healthy broker
        for name, broker in self._brokers.items():
            if broker.is_connected:
                return name

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
