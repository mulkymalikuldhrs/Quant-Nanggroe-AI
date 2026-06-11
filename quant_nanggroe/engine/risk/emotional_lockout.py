"""Emotional Lockout System — Prevent revenge trading and emotional decisions.

Implements an automated lockout system that blocks trading when the
trader's emotional state is likely compromised. This prevents the
common pattern of revenge trading after losses, which amplifies drawdowns.

Auto-Lockout Triggers
---------------------
- 3 consecutive losing trades → lockout for 1 hour
- 3 override attempts in a day → lockout for 24 hours
- Daily loss exceeds 5% → lockout until next day
- Manual lockout by user → custom duration

Lockout Enforcement
-------------------
- Block all new order submissions
- Allow only position-closing orders
- Log all lockout events
- Notify user of lockout reason and expiry

Lockout Expiry
--------------
- Auto-expire after duration
- Manual unlock (requires confirmation)
- Progressive lockout (repeat violations = longer lockouts)

Usage
-----
.. code-block:: python

    service = EmotionalLockoutService()

    # Record a trade outcome
    service.record_trade_result(symbol="BTC/USDT", pnl=-100.0)

    # Check if trading is allowed
    allowed = service.check_order_allowed(symbol="BTC/USDT", is_closing=False)

    # Manual lockout
    service.manual_lockout(duration_hours=2, reason="Taking a break")

    # Manual unlock
    service.manual_unlock(confirmation="CONFIRM_UNLOCK")
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, date
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lockout state
# ---------------------------------------------------------------------------

class LockoutState(str, Enum):
    """State of the emotional lockout.

    ACTIVE: Lockout is in effect — no new orders allowed.
    EXPIRED: Lockout has expired — trading resumed.
    OVERRIDE_BLOCKED: Override attempted but blocked due to too many attempts.
    """

    ACTIVE = "active"
    EXPIRED = "expired"
    OVERRIDE_BLOCKED = "override_blocked"


class LockoutReason(str, Enum):
    """Reason for the lockout."""

    CONSECUTIVE_LOSSES = "consecutive_losses"
    DAILY_LOSS_LIMIT = "daily_loss_limit"
    OVERRIDE_ABUSE = "override_abuse"
    MANUAL = "manual"
    PROGRESSIVE = "progressive"


# ---------------------------------------------------------------------------
# Lockout event audit trail
# ---------------------------------------------------------------------------

class LockoutEvent(BaseModel):
    """Audit trail entry for a lockout event.

    Attributes:
        timestamp: When the event occurred.
        event_type: Type of event (activated, expired, override_blocked, etc.).
        reason: Lockout reason.
        duration_hours: Lockout duration in hours.
        expires_at: When the lockout expires.
        consecutive_losses: Number of consecutive losses at time of event.
        daily_loss_pct: Daily loss percentage at time of event.
        override_attempts_today: Number of override attempts today.
        message: Human-readable description.
    """

    timestamp: datetime = Field(default_factory=datetime.now)
    event_type: str  # activated, expired, override_blocked, unlock_attempted, manual_unlocked
    reason: LockoutReason
    duration_hours: float = 0.0
    expires_at: Optional[datetime] = None
    consecutive_losses: int = 0
    daily_loss_pct: float = 0.0
    override_attempts_today: int = 0
    message: str = ""

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class EmotionalLockoutConfig(BaseModel):
    """Configuration for the emotional lockout system.

    Attributes:
        consecutive_losses_threshold: Number of consecutive losses to trigger lockout.
        consecutive_losses_lockout_hours: Duration of lockout after consecutive losses.
        daily_loss_pct_threshold: Daily loss percentage to trigger lockout.
        override_attempts_limit: Number of override attempts before blocking overrides.
        override_blockout_hours: Duration of lockout after override abuse.
        enable_progressive: Whether to enable progressive lockout durations.
        progressive_multiplier: Multiplier for progressive lockout durations.
        max_progressive_hours: Maximum lockout duration in hours.
    """

    consecutive_losses_threshold: int = Field(default=3, ge=1, description="Consecutive losses to trigger lockout")
    consecutive_losses_lockout_hours: float = Field(default=1.0, gt=0, description="Lockout hours after consecutive losses")
    daily_loss_pct_threshold: float = Field(default=0.05, gt=0, le=1.0, description="Daily loss % to trigger lockout")
    override_attempts_limit: int = Field(default=3, ge=1, description="Override attempts before blocking")
    override_blockout_hours: float = Field(default=24.0, gt=0, description="Lockout hours after override abuse")
    enable_progressive: bool = Field(default=True, description="Enable progressive lockout durations")
    progressive_multiplier: float = Field(default=2.0, gt=1.0, description="Multiplier for progressive lockouts")
    max_progressive_hours: float = Field(default=72.0, gt=0, description="Maximum lockout duration")

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Emotional Lockout Service
# ---------------------------------------------------------------------------

UNLOCK_CONFIRMATION = "CONFIRM_UNLOCK"


class EmotionalLockoutService:
    """Emotional lockout service that prevents revenge trading.

    Monitors trading activity and automatically locks out trading when
    emotional decision-making is likely. Supports progressive lockouts
    for repeat violations.

    Features
    --------
    * Auto-lockout on consecutive losses
    * Auto-lockout on daily loss threshold
    * Override attempt tracking and blocking
    * Manual lockout with custom duration
    * Progressive lockout durations
    * Full audit trail of all lockout events
    * Position-closing orders allowed during lockout
    """

    def __init__(
        self,
        config: Optional[EmotionalLockoutConfig] = None,
        initial_equity: float = 1_000_000.0,
    ) -> None:
        """Initialize the emotional lockout service.

        Args:
            config: Lockout configuration. Uses defaults if not provided.
            initial_equity: Starting equity for loss percentage calculations.
        """
        self._config = config or EmotionalLockoutConfig()
        self._initial_equity = initial_equity

        # State tracking
        self._consecutive_losses: int = 0
        self._daily_pnl: float = 0.0
        self._current_date: date = datetime.now().date()
        self._override_attempts_today: int = 0
        self._total_violations: int = 0

        # Active lockout state
        self._lockout_active: bool = False
        self._lockout_state: LockoutState = LockoutState.EXPIRED
        self._lockout_reason: Optional[LockoutReason] = None
        self._lockout_expires_at: Optional[datetime] = None
        self._lockout_activated_at: Optional[datetime] = None

        # Audit trail
        self._audit_trail: List[LockoutEvent] = []

        # Notifications (callback-based)
        self._notification_callbacks: List = []

    # ------------------------------------------------------------------ #
    # Core: Check if order is allowed
    # ------------------------------------------------------------------ #

    def check_order_allowed(
        self,
        symbol: str,
        is_closing: bool = False,
    ) -> Dict[str, Any]:
        """Check whether an order is allowed under current lockout state.

        Args:
            symbol: Trading symbol.
            is_closing: Whether this is a position-closing order.

        Returns:
            Dict with:
            - ``allowed`` (bool): Whether the order is permitted.
            - ``reason`` (str): Reason if not allowed.
            - ``lockout_state`` (LockoutState): Current lockout state.
            - ``expires_at`` (Optional[datetime]): When lockout expires.
        """
        # Auto-expire lockout if duration has passed
        self._check_expiry()

        # Closing orders are always allowed
        if is_closing:
            return {
                "allowed": True,
                "reason": "Closing orders are allowed during lockout",
                "lockout_state": self._lockout_state,
                "expires_at": self._lockout_expires_at,
            }

        # Check if lockout is active
        if self._lockout_active:
            remaining = ""
            if self._lockout_expires_at:
                delta = self._lockout_expires_at - datetime.now()
                if delta.total_seconds() > 0:
                    remaining = f" ({delta.total_seconds() / 3600:.1f}h remaining)"

            reason = (
                f"Trading locked out: {self._lockout_reason.value if self._lockout_reason else 'unknown'}"
                f"{remaining}"
            )
            return {
                "allowed": False,
                "reason": reason,
                "lockout_state": self._lockout_state,
                "expires_at": self._lockout_expires_at,
            }

        return {
            "allowed": True,
            "reason": "No lockout active",
            "lockout_state": self._lockout_state,
            "expires_at": None,
        }

    # ------------------------------------------------------------------ #
    # Core: Record trade results
    # ------------------------------------------------------------------ #

    def record_trade_result(
        self,
        symbol: str,
        pnl: float,
    ) -> Dict[str, Any]:
        """Record the result of a completed trade.

        Updates consecutive loss tracking and daily P&L, then checks
        whether an auto-lockout should be triggered.

        Args:
            symbol: Trading symbol.
            pnl: Profit/loss from the trade.

        Returns:
            Dict with updated state and whether a lockout was triggered.
        """
        self._reset_daily_if_needed()

        # Update daily P&L
        self._daily_pnl += pnl

        # Update consecutive losses
        if pnl < 0:
            self._consecutive_losses += 1
        else:
            self._consecutive_losses = 0

        # Check auto-lockout triggers
        triggered = False
        trigger_reason = None

        # Trigger 1: Consecutive losses
        if self._consecutive_losses >= self._config.consecutive_losses_threshold:
            triggered, trigger_reason = self._trigger_consecutive_losses_lockout()

        # Trigger 2: Daily loss threshold
        if not triggered:
            daily_loss_pct = abs(min(0, self._daily_pnl)) / self._initial_equity
            if self._daily_pnl < 0 and daily_loss_pct >= self._config.daily_loss_pct_threshold:
                triggered, trigger_reason = self._trigger_daily_loss_lockout(daily_loss_pct)

        return {
            "symbol": symbol,
            "pnl": pnl,
            "consecutive_losses": self._consecutive_losses,
            "daily_pnl": self._daily_pnl,
            "lockout_triggered": triggered,
            "trigger_reason": trigger_reason,
        }

    # ------------------------------------------------------------------ #
    # Override attempts
    # ------------------------------------------------------------------ #

    def attempt_override(self) -> Dict[str, Any]:
        """Attempt to override the current lockout.

        Override attempts are tracked. Too many attempts will trigger
        an extended lockout (override abuse protection).

        Returns:
            Dict with override result and current state.
        """
        self._reset_daily_if_needed()

        if not self._lockout_active:
            return {
                "override_granted": True,
                "reason": "No lockout active",
            }

        self._override_attempts_today += 1

        # Check override abuse
        if self._override_attempts_today >= self._config.override_attempts_limit:
            return self._trigger_override_abuse_lockout()

        # Log the override attempt
        event = LockoutEvent(
            event_type="override_attempted",
            reason=self._lockout_reason or LockoutReason.MANUAL,
            override_attempts_today=self._override_attempts_today,
            message=f"Override attempt #{self._override_attempts_today} — blocked",
        )
        self._audit_trail.append(event)
        logger.warning(
            "EmotionalLockout: Override attempt #%d blocked (limit: %d)",
            self._override_attempts_today,
            self._config.override_attempts_limit,
        )

        return {
            "override_granted": False,
            "reason": (
                f"Override not allowed during active lockout. "
                f"Attempt {self._override_attempts_today}/{self._config.override_attempts_limit}"
            ),
            "lockout_state": self._lockout_state,
            "expires_at": self._lockout_expires_at,
            "override_attempts_remaining": (
                self._config.override_attempts_limit - self._override_attempts_today
            ),
        }

    # ------------------------------------------------------------------ #
    # Manual lockout / unlock
    # ------------------------------------------------------------------ #

    def manual_lockout(
        self,
        duration_hours: float = 1.0,
        reason: str = "Manual lockout",
    ) -> Dict[str, Any]:
        """Manually activate a lockout.

        Args:
            duration_hours: Lockout duration in hours.
            reason: Reason for the manual lockout.

        Returns:
            Dict with lockout activation status.
        """
        return self._activate_lockout(
            reason=LockoutReason.MANUAL,
            duration_hours=duration_hours,
            message=reason,
        )

    def manual_unlock(self, confirmation: str = "") -> Dict[str, Any]:
        """Manually unlock the trading system.

        Requires explicit confirmation to prevent accidental unlocks.

        Args:
            confirmation: Must be exactly ``"CONFIRM_UNLOCK"``.

        Returns:
            Dict with unlock result.
        """
        if not self._lockout_active:
            return {
                "status": "NOT_LOCKED",
                "message": "No lockout is currently active.",
            }

        if confirmation != UNLOCK_CONFIRMATION:
            event = LockoutEvent(
                event_type="unlock_attempted",
                reason=self._lockout_reason or LockoutReason.MANUAL,
                message="Unlock failed — incorrect confirmation",
            )
            self._audit_trail.append(event)
            return {
                "status": "UNLOCK_DENIED",
                "message": "Unlock requires explicit confirmation.",
                "confirmation_required": UNLOCK_CONFIRMATION,
            }

        # Perform unlock
        old_reason = self._lockout_reason
        self._lockout_active = False
        self._lockout_state = LockoutState.EXPIRED
        self._lockout_reason = None
        self._lockout_expires_at = None
        self._lockout_activated_at = None

        event = LockoutEvent(
            event_type="manual_unlocked",
            reason=old_reason or LockoutReason.MANUAL,
            message="Manually unlocked after confirmation",
        )
        self._audit_trail.append(event)
        logger.info("EmotionalLockout: Manually unlocked")

        self._notify("unlocked", {"reason": old_reason})

        return {
            "status": "UNLOCKED",
            "message": "Lockout removed. Trading resumed.",
            "previous_reason": old_reason.value if old_reason else None,
        }

    # ------------------------------------------------------------------ #
    # State queries
    # ------------------------------------------------------------------ #

    @property
    def is_locked_out(self) -> bool:
        """Whether trading is currently locked out."""
        self._check_expiry()
        return self._lockout_active

    @property
    def lockout_state(self) -> LockoutState:
        """Current lockout state."""
        self._check_expiry()
        return self._lockout_state

    @property
    def lockout_reason(self) -> Optional[LockoutReason]:
        """Current lockout reason, if any."""
        return self._lockout_reason

    @property
    def lockout_expires_at(self) -> Optional[datetime]:
        """When the current lockout expires, if any."""
        return self._lockout_expires_at

    @property
    def consecutive_losses(self) -> int:
        """Current number of consecutive losing trades."""
        return self._consecutive_losses

    @property
    def daily_pnl(self) -> float:
        """Current daily P&L."""
        return self._daily_pnl

    @property
    def override_attempts_today(self) -> int:
        """Number of override attempts today."""
        return self._override_attempts_today

    @property
    def total_violations(self) -> int:
        """Total number of lockout violations (for progressive calculation)."""
        return self._total_violations

    @property
    def audit_trail(self) -> List[LockoutEvent]:
        """Full audit trail of all lockout events."""
        return list(self._audit_trail)

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status of the emotional lockout system.

        Returns:
            Dict with all current state information.
        """
        self._check_expiry()
        self._reset_daily_if_needed()

        daily_loss_pct = abs(min(0, self._daily_pnl)) / self._initial_equity if self._initial_equity > 0 else 0

        return {
            "is_locked_out": self._lockout_active,
            "lockout_state": self._lockout_state.value,
            "lockout_reason": self._lockout_reason.value if self._lockout_reason else None,
            "lockout_expires_at": self._lockout_expires_at.isoformat() if self._lockout_expires_at else None,
            "lockout_activated_at": self._lockout_activated_at.isoformat() if self._lockout_activated_at else None,
            "consecutive_losses": self._consecutive_losses,
            "daily_pnl": self._daily_pnl,
            "daily_loss_pct": f"{daily_loss_pct:.4f}",
            "daily_loss_threshold": f"{self._config.daily_loss_pct_threshold:.4f}",
            "override_attempts_today": self._override_attempts_today,
            "override_attempts_limit": self._config.override_attempts_limit,
            "total_violations": self._total_violations,
            "remaining_lockout_hours": (
                (self._lockout_expires_at - datetime.now()).total_seconds() / 3600
                if self._lockout_active and self._lockout_expires_at
                else 0.0
            ),
        }

    # ------------------------------------------------------------------ #
    # Notification callbacks
    # ------------------------------------------------------------------ #

    def add_notification_callback(self, callback) -> None:
        """Add a callback to be notified of lockout events.

        Args:
            callback: Callable accepting (event_type: str, data: dict).
        """
        self._notification_callbacks.append(callback)

    def _notify(self, event_type: str, data: Dict[str, Any]) -> None:
        """Notify all registered callbacks of a lockout event."""
        for callback in self._notification_callbacks:
            try:
                callback(event_type, data)
            except Exception as exc:
                logger.warning("EmotionalLockout: Notification callback error: %s", exc)

    # ------------------------------------------------------------------ #
    # Internal: Lockout triggers
    # ------------------------------------------------------------------ #

    def _trigger_consecutive_losses_lockout(self) -> tuple:
        """Trigger lockout due to consecutive losses."""
        duration = self._calculate_progressive_duration(
            self._config.consecutive_losses_lockout_hours,
        )
        reason = LockoutReason.CONSECUTIVE_LOSSES
        message = (
            f"{self._consecutive_losses} consecutive losing trades — "
            f"lockout for {duration:.1f} hours"
        )
        self._activate_lockout(reason=reason, duration_hours=duration, message=message)
        return True, reason.value

    def _trigger_daily_loss_lockout(self, daily_loss_pct: float) -> tuple:
        """Trigger lockout due to daily loss threshold."""
        duration = self._calculate_progressive_duration(
            self._config.consecutive_losses_lockout_hours,
        )
        reason = LockoutReason.DAILY_LOSS_LIMIT
        message = (
            f"Daily loss {daily_loss_pct:.2%} exceeds threshold "
            f"{self._config.daily_loss_pct_threshold:.2%} — "
            f"lockout for {duration:.1f} hours"
        )
        self._activate_lockout(reason=reason, duration_hours=duration, message=message)
        return True, reason.value

    def _trigger_override_abuse_lockout(self) -> Dict[str, Any]:
        """Trigger extended lockout due to override abuse."""
        duration = self._calculate_progressive_duration(
            self._config.override_blockout_hours,
        )
        reason = LockoutReason.OVERRIDE_ABUSE
        message = (
            f"{self._override_attempts_today} override attempts — "
            f"lockout extended to {duration:.1f} hours"
        )
        result = self._activate_lockout(reason=reason, duration_hours=duration, message=message)
        self._lockout_state = LockoutState.OVERRIDE_BLOCKED
        return {
            "override_granted": False,
            "reason": message,
            "lockout_state": self._lockout_state,
            "expires_at": self._lockout_expires_at,
        }

    # ------------------------------------------------------------------ #
    # Internal: Lockout lifecycle
    # ------------------------------------------------------------------ #

    def _activate_lockout(
        self,
        reason: LockoutReason,
        duration_hours: float,
        message: str = "",
    ) -> Dict[str, Any]:
        """Activate a lockout.

        Args:
            reason: Lockout reason.
            duration_hours: Lockout duration.
            message: Human-readable message.

        Returns:
            Dict with activation status.
        """
        now = datetime.now()
        expires_at = now + timedelta(hours=duration_hours)

        self._lockout_active = True
        self._lockout_state = LockoutState.ACTIVE
        self._lockout_reason = reason
        self._lockout_expires_at = expires_at
        self._lockout_activated_at = now
        self._total_violations += 1

        event = LockoutEvent(
            event_type="activated",
            reason=reason,
            duration_hours=duration_hours,
            expires_at=expires_at,
            consecutive_losses=self._consecutive_losses,
            daily_loss_pct=abs(min(0, self._daily_pnl)) / self._initial_equity if self._initial_equity > 0 else 0,
            override_attempts_today=self._override_attempts_today,
            message=message,
        )
        self._audit_trail.append(event)

        logger.warning(
            "EmotionalLockout: ACTIVATED — %s (duration=%.1fh, expires=%s)",
            reason.value, duration_hours, expires_at.isoformat(),
        )

        self._notify("lockout_activated", {
            "reason": reason.value,
            "duration_hours": duration_hours,
            "expires_at": expires_at.isoformat(),
            "message": message,
        })

        return {
            "status": "LOCKOUT_ACTIVATED",
            "reason": reason.value,
            "duration_hours": duration_hours,
            "expires_at": expires_at.isoformat(),
            "message": message,
        }

    def _check_expiry(self) -> None:
        """Check and auto-expire the lockout if duration has passed."""
        if not self._lockout_active:
            return

        if self._lockout_expires_at and datetime.now() >= self._lockout_expires_at:
            old_reason = self._lockout_reason
            self._lockout_active = False
            self._lockout_state = LockoutState.EXPIRED
            self._lockout_reason = None
            self._lockout_expires_at = None
            self._lockout_activated_at = None

            event = LockoutEvent(
                event_type="expired",
                reason=old_reason or LockoutReason.MANUAL,
                message="Lockout auto-expired",
            )
            self._audit_trail.append(event)
            logger.info("EmotionalLockout: Auto-expired (reason was: %s)", old_reason)

            self._notify("lockout_expired", {"reason": old_reason.value if old_reason else None})

    # ------------------------------------------------------------------ #
    # Internal: Progressive lockout
    # ------------------------------------------------------------------ #

    def _calculate_progressive_duration(self, base_hours: float) -> float:
        """Calculate progressive lockout duration based on violation count.

        Each subsequent violation increases the duration by the multiplier.

        Args:
            base_hours: Base lockout duration.

        Returns:
            Calculated duration in hours.
        """
        if not self._config.enable_progressive:
            return base_hours

        # Progressive: base * multiplier^(violations - 1)
        # First violation: base_hours
        # Second violation: base_hours * multiplier
        # Third violation: base_hours * multiplier^2
        violations = max(0, self._total_violations)
        duration = base_hours * (self._config.progressive_multiplier ** violations)
        return min(duration, self._config.max_progressive_hours)

    # ------------------------------------------------------------------ #
    # Internal: Daily reset
    # ------------------------------------------------------------------ #

    def _reset_daily_if_needed(self) -> None:
        """Reset daily counters if a new day has started."""
        today = datetime.now().date()
        if self._current_date != today:
            self._daily_pnl = 0.0
            self._override_attempts_today = 0
            self._current_date = today
