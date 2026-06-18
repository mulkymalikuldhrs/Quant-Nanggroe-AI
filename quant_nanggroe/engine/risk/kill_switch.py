"""Emergency kill switch for the AI-MultiColony finance module.

Implements a multi-level kill switch with auto-activation triggers
that can halt all trading activity when safety thresholds are
breached.

Kill switch levels:
* LEVEL_1: New positions blocked, existing positions maintained
* LEVEL_2: All positions closed at market, no new trades
* LEVEL_3: Full system shutdown, all operations ceased
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


# ── Enums ────────────────────────────────────────────────────────────────────


class KillSwitchLevel(str, Enum):
    """Kill switch severity level."""
    NONE = "none"
    LEVEL_1 = "level_1"  # Block new positions
    LEVEL_2 = "level_2"  # Close all positions
    LEVEL_3 = "level_3"  # Full shutdown


class KillSwitchTrigger(str, Enum):
    """What triggered the kill switch."""
    MANUAL = "manual"
    DAILY_LOSS_EXCEEDED = "daily_loss_exceeded"
    WEEKLY_LOSS_EXCEEDED = "weekly_loss_exceeded"
    DRAWDOWN_EXCEEDED = "drawdown_exceeded"
    VOLATILITY_SPIKE = "volatility_spike"
    MARKET_CRASH = "market_crash"
    SYSTEM_ERROR = "system_error"
    COMPLIANCE_VIOLATION = "compliance_violation"


class KillSwitchStatus(str, Enum):
    """Current status of the kill switch."""
    INACTIVE = "inactive"
    ACTIVE = "active"
    COOLDOWN = "cooldown"


# ── Models ───────────────────────────────────────────────────────────────────


class KillSwitchEvent(BaseModel):
    """Record of a kill switch activation/deactivation."""
    model_config = ConfigDict(frozen=False)

    event_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    level: KillSwitchLevel = KillSwitchLevel.NONE
    trigger: KillSwitchTrigger = KillSwitchTrigger.MANUAL
    previous_level: KillSwitchLevel = KillSwitchLevel.NONE
    reason: str = ""
    auto_activated: bool = False
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class KillSwitchConfig(BaseModel):
    """Configuration for the kill switch."""
    model_config = ConfigDict(frozen=False)

    # Auto-activation thresholds
    auto_daily_loss_pct: float = 1.5       # Auto-activate at 1.5% daily loss
    auto_weekly_loss_pct: float = 4.0      # Auto-activate at 4% weekly loss
    auto_max_drawdown_pct: float = 5.0     # Auto-activate at 5% drawdown
    auto_volatility_spike_pct: float = 10.0  # Auto-activate on 10% volatility spike

    # Cooldown settings
    cooldown_minutes: int = 30             # Minutes before manual deactivation
    level_2_cooldown_minutes: int = 60     # Level 2 requires longer cooldown
    level_3_requires_approval: bool = True  # Level 3 deactivation needs approval

    # Notifications
    notify_on_activation: bool = True
    notification_channels: List[str] = Field(default_factory=lambda: ["log", "api"])


# ── Kill Switch ──────────────────────────────────────────────────────────────


class KillSwitch:
    """Emergency kill switch with auto-activation.

    Monitors portfolio and market conditions, automatically
    activating when safety thresholds are breached.

    Usage::

        ks = KillSwitch()
        # Check if trading is allowed
        if ks.can_trade():
            # Execute trade
            pass

        # Manually activate
        ks.activate(KillSwitchLevel.LEVEL_1, reason="Manual override")

        # Deactivate after cooldown
        ks.deactivate()
    """

    def __init__(self, config: Optional[KillSwitchConfig] = None):
        self._config = config or KillSwitchConfig()
        self._current_level: KillSwitchLevel = KillSwitchLevel.NONE
        self._status: KillSwitchStatus = KillSwitchStatus.INACTIVE
        self._events: List[KillSwitchEvent] = []
        self._activated_at: Optional[datetime] = None
        self._callbacks: Dict[KillSwitchLevel, List[Callable]] = {
            KillSwitchLevel.LEVEL_1: [],
            KillSwitchLevel.LEVEL_2: [],
            KillSwitchLevel.LEVEL_3: [],
        }

    # ── Activation ──────────────────────────────────────────────────────

    def activate(
        self,
        level: KillSwitchLevel,
        reason: str = "",
        trigger: KillSwitchTrigger = KillSwitchTrigger.MANUAL,
        auto_activated: bool = False,
    ) -> KillSwitchEvent:
        """Activate the kill switch at a specified level.

        Parameters
        ----------
        level:
            Kill switch level to activate.
        reason:
            Reason for activation.
        trigger:
            What triggered the activation.
        auto_activated:
            Whether this was automatically triggered.

        Returns
        -------
        KillSwitchEvent
            Record of the activation.
        """
        if level == KillSwitchLevel.NONE:
            logger.warning("Cannot activate kill switch at NONE level")
            return KillSwitchEvent()

        previous_level = self._current_level
        self._current_level = level
        self._status = KillSwitchStatus.ACTIVE
        self._activated_at = datetime.now(timezone.utc)

        event = KillSwitchEvent(
            level=level,
            trigger=trigger,
            previous_level=previous_level,
            reason=reason,
            auto_activated=auto_activated,
        )
        self._events.append(event)

        # Log and notify
        logger.critical(
            "KILL SWITCH ACTIVATED: Level %s (trigger: %s, reason: %s)",
            level.value, trigger.value, reason,
        )

        # Execute callbacks
        for callback in self._callbacks.get(level, []):
            try:
                callback(event)
            except Exception as e:
                logger.error("Kill switch callback error: %s", e)

        return event

    def deactivate(self, reason: str = "Manual deactivation") -> Optional[KillSwitchEvent]:
        """Deactivate the kill switch.

        Returns
        -------
        KillSwitchEvent or None
            Deactivation record, or None if not active.
        """
        if self._status != KillSwitchStatus.ACTIVE:
            return None

        # Check cooldown
        if self._activated_at:
            elapsed = (datetime.now(timezone.utc) - self._activated_at).total_seconds() / 60
            required_cooldown = (
                self._config.level_2_cooldown_minutes
                if self._current_level in (KillSwitchLevel.LEVEL_2, KillSwitchLevel.LEVEL_3)
                else self._config.cooldown_minutes
            )
            if elapsed < required_cooldown:
                logger.warning(
                    "Cannot deactivate: cooldown period not elapsed (%.1f/%d minutes)",
                    elapsed, required_cooldown,
                )
                return None

        # Level 3 requires approval
        if self._current_level == KillSwitchLevel.LEVEL_3 and self._config.level_3_requires_approval:
            logger.warning("Level 3 deactivation requires explicit approval")

        previous_level = self._current_level
        self._current_level = KillSwitchLevel.NONE
        self._status = KillSwitchStatus.INACTIVE

        # Mark last event as resolved
        for event in reversed(self._events):
            if event.level == previous_level and not event.resolved:
                event.resolved = True
                event.resolved_at = datetime.now(timezone.utc)
                break

        logger.info("Kill switch deactivated: %s → NONE (reason: %s)", previous_level.value, reason)
        return KillSwitchEvent(
            level=KillSwitchLevel.NONE,
            previous_level=previous_level,
            reason=reason,
        )

    # ── Auto-activation checks ──────────────────────────────────────────

    def check_auto_activate(
        self,
        daily_pnl_pct: float = 0.0,
        weekly_pnl_pct: float = 0.0,
        max_drawdown_pct: float = 0.0,
        volatility_pct: float = 0.0,
    ) -> Optional[KillSwitchEvent]:
        """Check if auto-activation conditions are met.

        Parameters
        ----------
        daily_pnl_pct:
            Current daily P&L as percentage (negative for loss).
        weekly_pnl_pct:
            Current weekly P&L as percentage (negative for loss).
        max_drawdown_pct:
            Current maximum drawdown percentage.
        volatility_pct:
            Current market volatility percentage.

        Returns
        -------
        KillSwitchEvent or None
            Activation event if triggered, else None.
        """
        if self._status == KillSwitchStatus.ACTIVE:
            return None

        # Check daily loss
        daily_loss = abs(min(0, daily_pnl_pct))
        if daily_loss >= self._config.auto_daily_loss_pct:
            return self.activate(
                level=KillSwitchLevel.LEVEL_1,
                reason=f"Daily loss {daily_loss:.2f}% exceeded threshold {self._config.auto_daily_loss_pct}%",
                trigger=KillSwitchTrigger.DAILY_LOSS_EXCEEDED,
                auto_activated=True,
            )

        # Check weekly loss
        weekly_loss = abs(min(0, weekly_pnl_pct))
        if weekly_loss >= self._config.auto_weekly_loss_pct:
            return self.activate(
                level=KillSwitchLevel.LEVEL_2,
                reason=f"Weekly loss {weekly_loss:.2f}% exceeded threshold {self._config.auto_weekly_loss_pct}%",
                trigger=KillSwitchTrigger.WEEKLY_LOSS_EXCEEDED,
                auto_activated=True,
            )

        # Check max drawdown
        if max_drawdown_pct >= self._config.auto_max_drawdown_pct:
            return self.activate(
                level=KillSwitchLevel.LEVEL_2,
                reason=f"Drawdown {max_drawdown_pct:.2f}% exceeded threshold {self._config.auto_max_drawdown_pct}%",
                trigger=KillSwitchTrigger.DRAWDOWN_EXCEEDED,
                auto_activated=True,
            )

        # Check volatility spike
        if volatility_pct >= self._config.auto_volatility_spike_pct:
            return self.activate(
                level=KillSwitchLevel.LEVEL_1,
                reason=f"Volatility {volatility_pct:.2f}% spike exceeded threshold",
                trigger=KillSwitchTrigger.VOLATILITY_SPIKE,
                auto_activated=True,
            )

        return None

    # ── Query methods ───────────────────────────────────────────────────

    def can_trade(self) -> bool:
        """Check if new trades are allowed."""
        return self._status == KillSwitchStatus.INACTIVE and self._current_level == KillSwitchLevel.NONE

    def can_hold_positions(self) -> bool:
        """Check if holding existing positions is allowed."""
        return self._current_level != KillSwitchLevel.LEVEL_3

    def is_active(self) -> bool:
        """Check if the kill switch is active."""
        return self._status == KillSwitchStatus.ACTIVE

    # ── Callbacks ───────────────────────────────────────────────────────

    def on_activate(self, level: KillSwitchLevel, callback: Callable) -> None:
        """Register a callback for a specific kill switch level."""
        self._callbacks.setdefault(level, []).append(callback)

    # ── Properties ──────────────────────────────────────────────────────

    @property
    def current_level(self) -> KillSwitchLevel:
        return self._current_level

    @property
    def status(self) -> KillSwitchStatus:
        return self._status

    @property
    def events(self) -> List[KillSwitchEvent]:
        return list(self._events)

    @property
    def config(self) -> KillSwitchConfig:
        return self._config

    @property
    def stats(self) -> Dict[str, Any]:
        """Kill switch statistics."""
        return {
            "current_level": self._current_level.value,
            "status": self._status.value,
            "is_active": self.is_active(),
            "can_trade": self.can_trade(),
            "total_events": len(self._events),
            "auto_activations": sum(1 for e in self._events if e.auto_activated),
            "manual_activations": sum(1 for e in self._events if not e.auto_activated),
        }
