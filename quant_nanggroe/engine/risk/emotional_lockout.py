"""Emotional Lockout System — prevents revenge trading and excessive losses.

Tracks consecutive losses, daily P&L, and enforces escalating lockout
durations to block emotional trading decisions.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

UNLOCK_CONFIRMATION = "CONFIRM_UNLOCK"


class LockoutState(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    OVERRIDE_BLOCKED = "override_blocked"


class LockoutReason(str, Enum):
    CONSECUTIVE_LOSSES = "consecutive_losses"
    DAILY_LOSS_LIMIT = "daily_loss_limit"
    OVERRIDE_ABUSE = "override_abuse"
    MANUAL = "manual"
    PROGRESSIVE = "progressive"


class EmotionalLockoutConfig(BaseModel):
    consecutive_losses_threshold: int = 3
    consecutive_losses_lockout_hours: float = 1.0
    daily_loss_pct_threshold: float = 0.05
    override_attempts_limit: int = 3
    override_blockout_hours: float = 24.0
    enable_progressive: bool = True
    progressive_multiplier: float = 2.0
    max_progressive_hours: float = 72.0

    @field_validator("consecutive_losses_threshold")
    @classmethod
    def must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("consecutive_losses_threshold must be positive")
        return v

    @field_validator("daily_loss_pct_threshold")
    @classmethod
    def must_be_below_one(cls, v: float) -> float:
        if not 0 < v < 1.0:
            raise ValueError("daily_loss_pct_threshold must be between 0 and 1")
        return v


class LockoutEvent(BaseModel):
    event_type: str
    reason: LockoutReason
    duration_hours: float = 0.0
    message: str = ""
    timestamp: datetime = Field(default_factory=datetime.now)
    expires_at: datetime | None = None


class EmotionalLockoutService:
    """Prevents emotional trading by locking out after consecutive losses
    or daily loss threshold breaches, with progressive duration escalation."""

    def __init__(
        self,
        config: EmotionalLockoutConfig | None = None,
        initial_equity: float = 100_000.0,
    ):
        self._config = config or EmotionalLockoutConfig()
        self._initial_equity = initial_equity
        self._is_locked_out = False
        self._lockout_state: LockoutState = LockoutState.EXPIRED
        self._lockout_reason: LockoutReason | None = None
        self._lockout_expires_at: datetime | None = None
        self._consecutive_losses = 0
        self._daily_pnl = 0.0
        self._override_attempts_today = 0
        self._total_violations = 0
        self._audit_trail: list[LockoutEvent] = []
        self._callbacks: list[Callable[[str, dict[str, Any]], None]] = []

    # ── Properties ──────────────────────────────────────────────────────

    @property
    def is_locked_out(self) -> bool:
        return self._is_locked_out

    @property
    def lockout_state(self) -> LockoutState:
        return self._lockout_state

    @property
    def lockout_reason(self) -> LockoutReason | None:
        return self._lockout_reason

    @property
    def lockout_expires_at(self) -> datetime | None:
        return self._lockout_expires_at

    @property
    def consecutive_losses(self) -> int:
        return self._consecutive_losses

    @property
    def daily_pnl(self) -> float:
        return self._daily_pnl

    @property
    def override_attempts_today(self) -> int:
        return self._override_attempts_today

    @property
    def total_violations(self) -> int:
        return self._total_violations

    @property
    def audit_trail(self) -> list[LockoutEvent]:
        return list(self._audit_trail)

    # ── Public API ──────────────────────────────────────────────────────

    def record_trade_result(self, symbol: str, pnl: float) -> dict[str, Any]:
        """Record a trade result, update consecutive losses and daily P&L.

        Returns a dict with keys: pnl, consecutive_losses, lockout_triggered,
        and (if triggered) trigger_reason.
        """
        self._daily_pnl += pnl

        if pnl >= 0:
            self._consecutive_losses = 0
        else:
            self._consecutive_losses += 1

        result: dict[str, Any] = {
            "pnl": pnl,
            "consecutive_losses": self._consecutive_losses,
            "lockout_triggered": False,
        }

        if self._consecutive_losses >= self._config.consecutive_losses_threshold and not self._is_locked_out:
            self._activate_lockout(LockoutReason.CONSECUTIVE_LOSSES)
            result["lockout_triggered"] = True
            result["trigger_reason"] = "consecutive_losses"
        elif self._daily_pnl / self._initial_equity <= -self._config.daily_loss_pct_threshold and not self._is_locked_out:
            self._activate_lockout(LockoutReason.DAILY_LOSS_LIMIT)
            result["lockout_triggered"] = True
            result["trigger_reason"] = "daily_loss"

        return result

    def check_order_allowed(self, symbol: str, is_closing: bool = False) -> dict[str, Any]:
        """Check if a new or closing order is allowed.

        Auto-expires lockout if duration has passed.
        """
        self._check_expiry()

        allowed = not self._is_locked_out or is_closing
        return {
            "allowed": allowed,
            "reason": (
                ""
                if allowed
                else f"Locked out: {self._lockout_reason.value if self._lockout_reason else 'unknown'}"
            ),
            "lockout_state": self._lockout_state.value,
            "expires_at": self._lockout_expires_at.isoformat() if self._lockout_expires_at else None,
        }

    def manual_lockout(self, duration_hours: float, reason: str = "") -> dict[str, Any]:
        """Manually activate a lockout for a given duration."""
        self._activate_lockout(LockoutReason.MANUAL, duration_hours=duration_hours, message=reason)
        return {
            "status": "LOCKOUT_ACTIVATED",
            "reason": "manual",
            "duration_hours": duration_hours,
        }

    def manual_unlock(self, confirmation: str) -> dict[str, Any]:
        """Manually unlock with CONFIRM_UNLOCK string."""
        if not self._is_locked_out:
            self._record_event("unlock_attempted", LockoutReason.MANUAL, message="Not locked")
            return {"status": "NOT_LOCKED"}

        if confirmation != UNLOCK_CONFIRMATION:
            self._record_event("unlock_attempted", self._lockout_reason or LockoutReason.MANUAL, message="Wrong confirmation")
            return {"status": "UNLOCK_DENIED"}

        reason = self._lockout_reason or LockoutReason.MANUAL
        self._is_locked_out = False
        self._lockout_state = LockoutState.EXPIRED
        self._lockout_reason = None
        self._lockout_expires_at = None
        self._record_event("manual_unlocked", reason)
        self._notify("unlocked", {})
        return {"status": "UNLOCKED"}

    def attempt_override(self) -> dict[str, Any]:
        """Attempt to override an active lockout.

        Tracks attempts; exceeding the limit triggers an extended lockout.
        """
        self._override_attempts_today += 1

        if not self._is_locked_out:
            return {"override_granted": True, "lockout_state": self._lockout_state.value, "reason": "Not locked"}

        self._record_event("override_attempted", self._lockout_reason or LockoutReason.MANUAL)

        if self._override_attempts_today >= self._config.override_attempts_limit:
            self._activate_lockout(
                LockoutReason.OVERRIDE_ABUSE,
                duration_hours=self._config.override_blockout_hours,
            )
            return {
                "override_granted": False,
                "lockout_state": LockoutState.OVERRIDE_BLOCKED.value,
                "reason": "Override abuse — extended lockout activated",
            }

        return {
            "override_granted": False,
            "lockout_state": self._lockout_state.value,
            "reason": f"Locked out: {self._lockout_reason.value if self._lockout_reason else 'unknown'}",
        }

    def get_status(self) -> dict[str, Any]:
        """Return current lockout status for dashboard / monitoring."""
        remaining = 0.0
        if self._is_locked_out and self._lockout_expires_at:
            remaining = max(0.0, (self._lockout_expires_at - datetime.now()).total_seconds() / 3600)

        return {
            "is_locked_out": self._is_locked_out,
            "lockout_state": self._lockout_state.value,
            "lockout_reason": self._lockout_reason.value if self._lockout_reason else None,
            "consecutive_losses": self._consecutive_losses,
            "daily_pnl": self._daily_pnl,
            "remaining_lockout_hours": remaining,
            "override_attempts_today": self._override_attempts_today,
            "daily_loss_threshold": self._config.daily_loss_pct_threshold,
            "override_attempts_limit": self._config.override_attempts_limit,
        }

    def add_notification_callback(self, callback: Callable[[str, dict[str, Any]], None]) -> None:
        """Register a callback for lockout events (activated, unlocked, expired)."""
        self._callbacks.append(callback)

    def _calculate_progressive_duration(self, base_hours: float) -> float:
        """Return escalated duration based on violation count.

        Formula: base * multiplier^(violations - 1)
        violations=0 → base/2, violations=1 → base, violations=2 → base*multiplier.
        Capped at max_progressive_hours.
        """
        multiplier = self._config.progressive_multiplier ** (self._total_violations - 1)
        return min(base_hours * multiplier, self._config.max_progressive_hours)

    # ── Internal helpers ────────────────────────────────────────────────

    def _activate_lockout(self, reason: LockoutReason, duration_hours: float | None = None, message: str = "") -> None:
        """Set lockout state, compute duration, record event, notify."""
        if duration_hours is None:
            if reason in (LockoutReason.CONSECUTIVE_LOSSES, LockoutReason.DAILY_LOSS_LIMIT):
                duration_hours = self._config.consecutive_losses_lockout_hours
            elif reason == LockoutReason.OVERRIDE_ABUSE:
                duration_hours = self._config.override_blockout_hours
            else:
                duration_hours = 1.0

        if self._config.enable_progressive and reason in (
            LockoutReason.CONSECUTIVE_LOSSES,
            LockoutReason.DAILY_LOSS_LIMIT,
            LockoutReason.OVERRIDE_ABUSE,
        ):
            self._total_violations += 1
            duration_hours = self._calculate_progressive_duration(duration_hours)

        self._is_locked_out = True
        self._lockout_state = LockoutState.ACTIVE
        self._lockout_reason = reason
        self._lockout_expires_at = datetime.now() + timedelta(hours=duration_hours)

        self._record_event("activated", reason, duration_hours=duration_hours, message=message)
        self._notify("lockout_activated", {
            "reason": reason.value,
            "duration_hours": duration_hours,
        })

    def _check_expiry(self) -> None:
        """Auto-expire lockout if duration has elapsed."""
        if not self._is_locked_out or not self._lockout_expires_at:
            return
        if datetime.now() >= self._lockout_expires_at:
            reason = self._lockout_reason or LockoutReason.MANUAL
            self._is_locked_out = False
            self._lockout_state = LockoutState.EXPIRED
            self._lockout_reason = None
            self._lockout_expires_at = None
            self._record_event("expired", reason)
            self._notify("lockout_expired", {})

    def _record_event(self, event_type: str, reason: LockoutReason, duration_hours: float = 0.0, message: str = "") -> None:
        """Append an audit trail entry."""
        event = LockoutEvent(
            event_type=event_type,
            reason=reason,
            duration_hours=duration_hours,
            message=message,
            expires_at=self._lockout_expires_at,
        )
        self._audit_trail.append(event)

    def _notify(self, event_type: str, data: dict[str, Any]) -> None:
        """Fire registered callbacks, catching exceptions so one bad callback doesn't break lockout logic."""
        for callback in self._callbacks:
            try:
                callback(event_type, data)
            except Exception:
                logger.exception("Lockout callback failed for event %s", event_type)
