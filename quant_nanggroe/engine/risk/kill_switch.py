"""Kill Switch — Emergency Halt Mechanism.

Implements the emergency kill switch that automatically activates
when constitutional risk limits are breached. Once activated,
ALL trading is halted and can only be reset after manual review.

Activation triggers:
- AUTO_DAILY_LIMIT: Daily loss limit breached
- AUTO_WEEKLY_LIMIT: Weekly loss limit breached
- AUTO_MAX_DRAWDOWN: Maximum drawdown breached
- MANUAL: Manual activation by human operator

Reset requires explicit confirmation: "CONFIRM_RESET_AFTER_REVIEW"

Extracted from HermesQuantOS's KillSwitchTool.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Confirmation string required for reset (prevents accidental reset)
RESET_CONFIRMATION = "CONFIRM_RESET_AFTER_REVIEW"


class KillSwitch:
    """Emergency Kill Switch.

    Once activated, ALL trading is halted. The kill switch can only
    be reset after explicit manual review and confirmation.

    This is the ultimate safety net — no agent or system can
    bypass or override the kill switch.

    Enhanced from HermesQuantOS with:
    - Escalation levels (SOFT/HARD/FULL)
    - Per-symbol kill capability
    - Cooldown period after reset
    - Audit trail with detailed logging
    """

    # Escalation levels
    LEVEL_SOFT = "SOFT"       # Halt new positions, allow exits
    LEVEL_HARD = "HARD"       # Halt all trading except emergency exits
    LEVEL_FULL = "FULL"       # Full halt — nothing allowed

    def __init__(self, cooldown_minutes: int = 30) -> None:
        self._is_active: bool = False
        self._activated_at: Optional[str] = None
        self._activation_reason: Optional[str] = None
        self._escalation_level: str = self.LEVEL_FULL
        self._auto_triggers: int = 0
        self._manual_triggers: int = 0
        self._activation_log: list = []
        self._symbol_kills: Dict[str, Dict] = {}
        self._cooldown_minutes: int = cooldown_minutes
        self._last_reset_at: Optional[str] = None
        self._cooldown_until: Optional[str] = None

    @property
    def is_active(self) -> bool:
        """Whether the kill switch is currently active."""
        return self._is_active

    def activate(
        self,
        reason: str = "MANUAL",
        level: str = None,
    ) -> Dict[str, any]:
        """Activate kill switch — halts ALL trading.

        Args:
            reason: Activation reason.
            level: Escalation level (SOFT/HARD/FULL). Defaults to FULL.

        Returns:
            Dict with activation status.
        """
        if self._is_active:
            return {
                "status": "ALREADY_ACTIVE",
                "reason": self._activation_reason,
                "activated_at": self._activated_at,
                "level": self._escalation_level,
            }

        level = level or self.LEVEL_FULL
        self._is_active = True
        self._activated_at = datetime.now().isoformat()
        self._activation_reason = reason
        self._escalation_level = level

        if reason.startswith("AUTO_"):
            self._auto_triggers += 1
        else:
            self._manual_triggers += 1

        log_entry = {
            "activated_at": self._activated_at,
            "reason": reason,
            "level": level,
        }
        self._activation_log.append(log_entry)

        logger.critical("KILL SWITCH ACTIVATED: %s (level=%s)", reason, level)

        return {
            "status": "ACTIVATED",
            "reason": reason,
            "level": level,
            "activated_at": self._activated_at,
            "message": f"Trading halted at {level} level. Manual reset required after review.",
            "auto_triggers_total": self._auto_triggers,
            "manual_triggers_total": self._manual_triggers,
        }

    def reset(self, confirmation: str = "") -> Dict[str, any]:
        """Reset kill switch — requires explicit confirmation.

        After reset, a cooldown period is enforced before trading resumes.

        Args:
            confirmation: Must be exactly "CONFIRM_RESET_AFTER_REVIEW".

        Returns:
            Dict with reset status.
        """
        if not self._is_active:
            return {
                "status": "NOT_ACTIVE",
                "message": "Kill switch is not currently active.",
            }

        if confirmation != RESET_CONFIRMATION:
            return {
                "status": "STILL_ACTIVE",
                "message": "Kill switch requires explicit confirmation to reset.",
                "confirmation_required": RESET_CONFIRMATION,
                "note": "Review all trades and risk status before resetting.",
            }

        from datetime import timedelta
        now = datetime.now()
        cooldown_end = now + timedelta(minutes=self._cooldown_minutes)

        self._is_active = False
        self._activated_at = None
        self._activation_reason = None
        self._escalation_level = self.LEVEL_FULL
        self._last_reset_at = now.isoformat()
        self._cooldown_until = cooldown_end.isoformat()
        self._symbol_kills.clear()

        logger.info(
            "Kill switch RESET after review. Cooldown until %s",
            cooldown_end.isoformat(),
        )

        return {
            "status": "RESET",
            "message": "Kill switch deactivated. Trading resumes after cooldown.",
            "cooldown_until": cooldown_end.isoformat(),
            "cooldown_minutes": self._cooldown_minutes,
            "note": "Ensure risk parameters are reviewed before resuming.",
        }

    def status(self) -> Dict[str, any]:
        """Get kill switch status."""
        now = datetime.now()
        in_cooldown = (
            self._cooldown_until is not None
            and now.isoformat() < self._cooldown_until
        )
        return {
            "is_active": self._is_active,
            "escalation_level": self._escalation_level,
            "activated_at": self._activated_at,
            "activation_reason": self._activation_reason,
            "auto_triggers": self._auto_triggers,
            "manual_triggers": self._manual_triggers,
            "total_activations": self._auto_triggers + self._manual_triggers,
            "symbol_kills": list(self._symbol_kills.keys()),
            "last_reset_at": self._last_reset_at,
            "in_cooldown": in_cooldown,
            "cooldown_until": self._cooldown_until,
            "activation_log_count": len(self._activation_log),
            "message": "TRADING HALTED" if self._is_active else ("IN COOLDOWN" if in_cooldown else "System operational"),
        }

    def check_auto_trigger(
        self,
        daily_loss_pct: float,
        weekly_loss_pct: float,
        drawdown_pct: float = 0.0,
    ) -> Optional[Dict[str, any]]:
        """Auto-check if kill switch should trigger based on risk limits.

        Escalation logic:
        - Daily loss at limit → HARD level
        - Weekly loss at limit → HARD level
        - Max drawdown at limit → FULL level

        Args:
            daily_loss_pct: Current daily loss as fraction.
            weekly_loss_pct: Current weekly loss as fraction.
            drawdown_pct: Current drawdown as fraction.

        Returns:
            Activation dict if triggered, None otherwise.
        """
        from quant_nanggroe.engine.risk.constants import (
            MAX_DAILY_LOSS,
            MAX_WEEKLY_LOSS,
            MAX_DRAWDOWN_PCT,
        )
        MAX_DRAWDOWN = MAX_DRAWDOWN_PCT

        if daily_loss_pct >= MAX_DAILY_LOSS:
            return self.activate("AUTO_DAILY_LIMIT", level=self.LEVEL_HARD)

        if weekly_loss_pct >= MAX_WEEKLY_LOSS:
            return self.activate("AUTO_WEEKLY_LIMIT", level=self.LEVEL_HARD)

        if drawdown_pct >= MAX_DRAWDOWN:
            return self.activate("AUTO_MAX_DRAWDOWN", level=self.LEVEL_FULL)

        return None

    def activate_for_symbol(self, symbol: str, reason: str = "MANUAL") -> Dict[str, any]:
        """Activate kill switch for a specific symbol only.

        Args:
            symbol: Trading symbol to halt.
            reason: Reason for symbol-level kill.

        Returns:
            Dict with activation status.
        """
        if symbol in self._symbol_kills:
            return {
                "status": "ALREADY_KILLED",
                "symbol": symbol,
                "reason": self._symbol_kills[symbol]["reason"],
            }

        entry = {
            "activated_at": datetime.now().isoformat(),
            "reason": reason,
        }
        self._symbol_kills[symbol] = entry

        logger.warning("Symbol kill switch activated: %s (%s)", symbol, reason)

        return {
            "status": "SYMBOL_KILLED",
            "symbol": symbol,
            "reason": reason,
            "activated_at": entry["activated_at"],
        }

    def is_symbol_killed(self, symbol: str) -> bool:
        """Check if a specific symbol is killed."""
        if self._is_active:
            return True
        return symbol in self._symbol_kills

    def get_activation_log(self, limit: int = 20) -> list:
        """Get recent activation log entries.

        Args:
            limit: Maximum entries to return.

        Returns:
            List of activation log entries.
        """
        return self._activation_log[-limit:]
