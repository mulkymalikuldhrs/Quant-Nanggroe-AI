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

import json
import logging
import os
import threading
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

EARLY_WARNING_THRESHOLD: float = 0.8
RESET_CONFIRMATION: str = "CONFIRM_RESET_AFTER_REVIEW"

# ── Cross-process shared state (C5: single source of truth across procs) ──
# When QNA_KILL_SWITCH_STATE_FILE is set, EVERY KillSwitch() instance — in any
# worker, daemon, or the production bridge — reads/writes the SAME file. This
# collapses the previous split-brain (per-ExecutionManager / per-worker
# in-memory switches that never agreed). Fail-closed: unreadable/corrupt state
# file => assumed ACTIVE (halt). Default (env unset): pure in-memory, so tests
# and single-process use stay isolated.  // ponytail: single file = single writer
_KS_FILE_ENV: str = "QNA_KILL_SWITCH_STATE_FILE"
_KS_LOCK = threading.RLock()


def _ks_store_path() -> Optional[Path]:
    p = os.environ.get(_KS_FILE_ENV)
    return Path(p) if p else None


def _ks_read(path: Path) -> Optional[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None  # no activation recorded -> inactive
    except Exception:  # corrupt / permission denied -> FAIL CLOSED
        logger.critical("Kill switch state file %s unreadable — FAIL CLOSED (assume active)", path)
        return {"_fail_closed": True}


def _ks_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, default=str), encoding="utf-8")
    os.replace(tmp, path)  # atomic on POSIX + Windows


def configure_kill_switch_file(path: Optional[str] = None) -> None:
    """Point all KillSwitch() instances in this process at a shared file.

    Idempotent. Call once at runtime startup (API / daemon / bridge). When the
    env is already set, this is a no-op. Without it, instances stay in-memory.
    """
    if os.environ.get(_KS_FILE_ENV):
        return
    if path is None:
        path = str(Path(__file__).resolve().parents[3] / "data" / "kill_switch_state.json")
    os.environ[_KS_FILE_ENV] = path

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
    DATA_STALE = "data_stale"
    CORRELATION_HERDING = "correlation_herding"


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

    # Auto-activation thresholds (as fractions, e.g. 0.015 = 1.5%)
    auto_daily_loss_pct: float = 0.015
    auto_weekly_loss_pct: float = 0.04
    auto_max_drawdown_pct: float = 0.05
    auto_volatility_spike_pct: float = 0.10

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
        self._level3_approved: bool = False
        self._ks_file = _ks_store_path()
        if self._ks_file:
            self._reconcile()
        self._callbacks: Dict[KillSwitchLevel, List[Callable[[KillSwitchEvent], None]]] = {
            KillSwitchLevel.LEVEL_1: [],
            KillSwitchLevel.LEVEL_2: [],
            KillSwitchLevel.LEVEL_3: [],
        }

    # ── Backward-compatible API ────────────────────────────────────────

    @property
    def is_active(self) -> bool:
        """Property access for is_active (backward compat)."""
        return self._status == KillSwitchStatus.ACTIVE

    def status(self) -> Dict[str, Any]:
        """Dict-returning status (backward compat for tests/RiskManager)."""
        return {
            "is_active": self.is_active,
            "current_level": self._current_level.value,
            "status": self._status.value,
            "activation_reason": self._events[-1].reason if self._events else "",
            "total_activations": len(self._events),
            "auto_triggers": sum(1 for e in self._events if e.auto_activated),
            "manual_triggers": sum(1 for e in self._events if not e.auto_activated),
            "activated_at": (
                self._activated_at.isoformat() if self._activated_at else None
            ),
        }

    def reset(self, confirmation: str = "") -> Dict[str, str]:
        """Reset kill switch (bypasses cooldown for emergency reset)."""
        if not self.is_active:
            return {"status": "NOT_ACTIVE"}
        if confirmation != RESET_CONFIRMATION:
            return {"status": "STILL_ACTIVE"}
        previous_level = self._current_level
        self._current_level = KillSwitchLevel.NONE
        self._status = KillSwitchStatus.INACTIVE
        self._activated_at = None
        for event in reversed(self._events):
            if not event.resolved:
                event.resolved = True
                event.resolved_at = datetime.now(timezone.utc)
                break
        logger.info("Kill switch reset via confirmation: %s → NONE", previous_level.value)
        self._flush()  # C5: persist reset so other procs stop halting
        return {"status": "RESET"}

    # ── Cross-process reconcile / flush (C5) ───────────────────────────

    def _reconcile(self) -> None:
        """Load activation truth from the shared file (called on init + before gate checks)."""
        if not self._ks_file:
            return
        data = _ks_read(self._ks_file)
        if data is None:
            return
        if data.get("_fail_closed"):  # unreadable file => halt, no flush (can't write)
            self._status = KillSwitchStatus.ACTIVE
            self._current_level = KillSwitchLevel.LEVEL_2
            self._activated_at = self._activated_at or datetime.now(timezone.utc)
            return
        if data.get("status") == "active":  # KillSwitchStatus.ACTIVE.value
            lvl = KillSwitchLevel(data.get("current_level", "level_2"))
            # Re-apply without re-recording a duplicate activation event.
            self._current_level = lvl
            self._status = KillSwitchStatus.ACTIVE
            if self._activated_at is None:
                try:
                    self._activated_at = datetime.fromisoformat(data["activated_at"]) if data.get("activated_at") else datetime.now(timezone.utc)
                except Exception:
                    self._activated_at = datetime.now(timezone.utc)
            # ponytail: a DAILY-LIMIT (level_1) breach is scoped to the trading
            # day it occurred. A stale level_1 persisted from a previous day must
            # auto-expire on reconcile, else the hedge fund freezes forever while
            # /health still reports "healthy" (silent trade-blocker). Weekly/
            # drawdown/systemic (level_2/3) breaches must NOT auto-expire — those
            # require explicit human review (RESET_CONFIRMATION).
            if lvl == KillSwitchLevel.LEVEL_1 and self._activated_at is not None:
                activated_day = self._activated_at.date()
                today = datetime.now(timezone.utc).date()
                if activated_day < today:
                    logger.info(
                        "Kill switch: stale level_1 (daily-limit) from %s expired on new day %s — auto-deactivating",
                        activated_day.isoformat(), today.isoformat(),
                    )
                    self._status = KillSwitchStatus.INACTIVE
                    self._current_level = KillSwitchLevel.NONE
                    self._activated_at = None
                    # Persist the expiry so every proc sees one truth.
                    self._flush()

    def _flush(self) -> None:
        """Write current activation truth to the shared file (called after every state change)."""
        if not self._ks_file:
            return
        with _KS_LOCK:
            data = {
                "status": self._status.value,
                "current_level": self._current_level.value,
                "activated_at": self._activated_at.isoformat() if self._activated_at else None,
                "reason": self._events[-1].reason if self._events else "",
            }
            _ks_write(self._ks_file, data)

    def _ensure_reconciled(self) -> None:
        """Gate checks must see the freshest cross-proc truth before deciding."""
        if self._ks_file:
            self._reconcile()

    def check_auto_trigger(
        self,
        daily_loss_pct: float = 0.0,
        weekly_loss_pct: float = 0.0,
        drawdown_pct: float = 0.0,
        volatility_pct: float = 0.0,
    ) -> Optional[Dict[str, Any]]:
        """Dict-returning auto-trigger check (backward compat)."""
        event = self.check_auto_activate(
            daily_pnl_pct=-daily_loss_pct,
            weekly_pnl_pct=-weekly_loss_pct,
            max_drawdown_pct=drawdown_pct,
            volatility_pct=volatility_pct,
        )
        if event is None:
            return None
        return self.status()

    # ── Activation ──────────────────────────────────────────────────────

    def activate(
        self,
        level: KillSwitchLevel | str | None = None,
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
        if isinstance(level, str) and not isinstance(level, KillSwitchLevel):
            reason = level
            level = KillSwitchLevel.LEVEL_1
            trigger = KillSwitchTrigger.MANUAL

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

        # C5: persist to shared file so every proc/worker sees one truth
        self._flush()

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
            if not self._level3_approved:
                logger.warning("Level 3 deactivation requires explicit approval — call approve_level3_deactivation()")
                return None
            self._level3_approved = False  # reset after use

        previous_level = self._current_level
        self._current_level = KillSwitchLevel.NONE
        self._status = KillSwitchStatus.INACTIVE

        # C5: persist deactivation so every proc/worker stops halting
        self._flush()

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

    def approve_level3_deactivation(self) -> None:
        """Approve Level 3 deactivation. Must be called before deactivate() will succeed."""
        self._level3_approved = True
        logger.info("Level 3 deactivation approved")

    # ── Auto-activation checks ──────────────────────────────────────────

    def check_auto_activate(
        self,
        daily_pnl_pct: float = 0.0,
        weekly_pnl_pct: float = 0.0,
        max_drawdown_pct: float = 0.0,
        volatility_pct: float = 0.0,
    ) -> Optional[KillSwitchEvent]:
        self._ensure_reconciled()  # C5: see freshest cross-proc activation before deciding
        if self._status == KillSwitchStatus.ACTIVE:
            return None
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

    def check_warning(
        self,
        daily_pnl_pct: float = 0.0,
        weekly_pnl_pct: float = 0.0,
        max_drawdown_pct: float = 0.0,
        volatility_pct: float = 0.0,
    ) -> bool:
        """Check if any metric is approaching its auto-activation threshold.

        Returns True if any metric exceeds EARLY_WARNING_THRESHOLD (80%)
        of its limit. Does NOT trigger the kill switch — just returns a flag.

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
        bool
            True if any metric is in the warning zone.
        """
        daily_loss = abs(min(0, daily_pnl_pct))
        if daily_loss >= self._config.auto_daily_loss_pct * EARLY_WARNING_THRESHOLD:
            logger.info("Early warning: daily loss %.2f%% approaching limit", daily_loss)
            return True

        weekly_loss = abs(min(0, weekly_pnl_pct))
        if weekly_loss >= self._config.auto_weekly_loss_pct * EARLY_WARNING_THRESHOLD:
            logger.info("Early warning: weekly loss %.2f%% approaching limit", weekly_loss)
            return True

        if max_drawdown_pct >= self._config.auto_max_drawdown_pct * EARLY_WARNING_THRESHOLD:
            logger.info("Early warning: drawdown %.2f%% approaching limit", max_drawdown_pct)
            return True

        if volatility_pct >= self._config.auto_volatility_spike_pct * EARLY_WARNING_THRESHOLD:
            logger.info("Early warning: volatility %.2f%% approaching limit", volatility_pct)
            return True

        return False

    def can_trade(self) -> bool:
        """Check if new trades are allowed.

        Reconciles with the shared file first so this worker halts the instant
        ANY other process (worker A, daemon, bridge) activates the switch.
        """
        self._ensure_reconciled()
        return self._status == KillSwitchStatus.INACTIVE and self._current_level == KillSwitchLevel.NONE

    def can_hold_positions(self) -> bool:
        """Check if holding existing positions is allowed."""
        return self._current_level != KillSwitchLevel.LEVEL_3

    # ── Callbacks ───────────────────────────────────────────────────────

    def on_activate(self, level: KillSwitchLevel, callback: Callable[[KillSwitchEvent], None]) -> None:
        """Register a callback for a specific kill switch level."""
        self._callbacks.setdefault(level, []).append(callback)

    # ── Properties ──────────────────────────────────────────────────────

    @property
    def current_level(self) -> KillSwitchLevel:
        return self._current_level

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
            "is_active": self.is_active,
            "can_trade": self.can_trade(),
            "total_events": len(self._events),
            "auto_activations": sum(1 for e in self._events if e.auto_activated),
            "manual_activations": sum(1 for e in self._events if not e.auto_activated),
        }
