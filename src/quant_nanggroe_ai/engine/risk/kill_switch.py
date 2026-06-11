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
    """

    def __init__(self) -> None:
        self._is_active: bool = False
        self._activated_at: Optional[str] = None
        self._activation_reason: Optional[str] = None
        self._auto_triggers: int = 0
        self._manual_triggers: int = 0
        self._activation_log: list = []

    @property
    def is_active(self) -> bool:
        """Whether the kill switch is currently active."""
        return self._is_active

    def activate(self, reason: str = "MANUAL") -> Dict[str, any]:
        """Activate kill switch — halts ALL trading.

        Args:
            reason: Activation reason.

        Returns:
            Dict with activation status.
        """
        if self._is_active:
            return {
                "status": "ALREADY_ACTIVE",
                "reason": self._activation_reason,
                "activated_at": self._activated_at,
            }

        self._is_active = True
        self._activated_at = datetime.now().isoformat()
        self._activation_reason = reason

        if reason.startswith("AUTO_"):
            self._auto_triggers += 1
        else:
            self._manual_triggers += 1

        self._activation_log.append({
            "activated_at": self._activated_at,
            "reason": reason,
        })

        logger.critical("⚠️ KILL SWITCH ACTIVATED: %s", reason)

        return {
            "status": "ACTIVATED",
            "reason": reason,
            "activated_at": self._activated_at,
            "message": "ALL TRADING HALTED. Manual reset required after review.",
            "auto_triggers_total": self._auto_triggers,
            "manual_triggers_total": self._manual_triggers,
        }

    def reset(self, confirmation: str = "") -> Dict[str, any]:
        """Reset kill switch — requires explicit confirmation.

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

        self._is_active = False
        self._activated_at = None
        self._activation_reason = None

        logger.info("Kill switch RESET after review")

        return {
            "status": "RESET",
            "message": "Kill switch deactivated. Trading resumed.",
            "note": "Ensure risk parameters are reviewed before resuming.",
        }

    def status(self) -> Dict[str, any]:
        """Get kill switch status."""
        return {
            "is_active": self._is_active,
            "activated_at": self._activated_at,
            "activation_reason": self._activation_reason,
            "auto_triggers": self._auto_triggers,
            "manual_triggers": self._manual_triggers,
            "total_activations": self._auto_triggers + self._manual_triggers,
            "message": "TRADING HALTED" if self._is_active else "System operational",
        }

    def check_auto_trigger(
        self,
        daily_loss_pct: float,
        weekly_loss_pct: float,
        drawdown_pct: float = 0.0,
    ) -> Optional[Dict[str, any]]:
        """Auto-check if kill switch should trigger based on risk limits.

        Args:
            daily_loss_pct: Current daily loss as fraction.
            weekly_loss_pct: Current weekly loss as fraction.
            drawdown_pct: Current drawdown as fraction.

        Returns:
            Activation dict if triggered, None otherwise.
        """
        from quant_nanggroe_ai.engine.risk.constants import (
            MAX_DAILY_LOSS,
            MAX_WEEKLY_LOSS,
            MAX_DRAWDOWN_PCT,
        )
        MAX_DRAWDOWN = MAX_DRAWDOWN_PCT

        if daily_loss_pct >= MAX_DAILY_LOSS:
            return self.activate("AUTO_DAILY_LIMIT")

        if weekly_loss_pct >= MAX_WEEKLY_LOSS:
            return self.activate("AUTO_WEEKLY_LIMIT")

        if drawdown_pct >= MAX_DRAWDOWN:
            return self.activate("AUTO_MAX_DRAWDOWN")

        return None
