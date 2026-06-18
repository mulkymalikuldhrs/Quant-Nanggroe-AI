#!/usr/bin/env python3
"""
Kill Switch Agent (L4 - Execution Layer)
Emergency halt - auto-trigger when risk limits breached
Manual reset only after review
"""

import json
import logging
from datetime import datetime

logger = logging.getLogger("HermesQuantOS.KillSwitch")


class KillSwitchTool:
    """L4 Agent: Kill Switch - Emergency halt system"""

    def __init__(self):
        self.is_active = False
        self.activated_at = None
        self.activation_reason = None
        self.auto_triggers = 0
        self.manual_triggers = 0

    def activate(self, reason: str = "MANUAL") -> str:
        """Activate kill switch - halts all trading"""
        self.is_active = True
        self.activated_at = datetime.now().isoformat()
        self.activation_reason = reason

        if reason == "AUTO_DAILY_LIMIT" or reason == "AUTO_WEEKLY_LIMIT":
            self.auto_triggers += 1
        else:
            self.manual_triggers += 1

        logger.critical(f"KILL SWITCH ACTIVATED: {reason}")

        return json.dumps({
            "status": "ACTIVATED",
            "reason": reason,
            "activated_at": self.activated_at,
            "message": "ALL TRADING HALTED. Manual reset required after review.",
            "auto_triggers_total": self.auto_triggers,
            "manual_triggers_total": self.manual_triggers
        }, indent=2)

    def reset(self, confirmation: str = "") -> str:
        """Reset kill switch - requires explicit confirmation"""
        if confirmation != "CONFIRM_RESET_AFTER_REVIEW":
            return json.dumps({
                "status": "STILL_ACTIVE",
                "message": "Kill switch requires explicit confirmation to reset.",
                "confirmation_required": "CONFIRM_RESET_AFTER_REVIEW",
                "note": "Review all trades and risk status before resetting."
            }, indent=2)

        self.is_active = False
        self.activated_at = None
        self.activation_reason = None

        logger.info("Kill switch RESET after review")

        return json.dumps({
            "status": "RESET",
            "message": "Kill switch deactivated. Trading resumed.",
            "note": "Ensure risk parameters are reviewed before resuming."
        }, indent=2)

    def check_auto_trigger(self, daily_pnl_pct: float, weekly_pnl_pct: float) -> str:
        """Auto-check if kill switch should trigger based on risk limits"""
        from tools.risk_officer_tool import MAX_DAILY_LOSS, MAX_WEEKLY_LOSS

        if abs(min(0, daily_pnl_pct)) >= MAX_DAILY_LOSS:
            return self.activate("AUTO_DAILY_LIMIT")

        if abs(min(0, weekly_pnl_pct)) >= MAX_WEEKLY_LOSS:
            return self.activate("AUTO_WEEKLY_LIMIT")

        return json.dumps({
            "status": "OK" if not self.is_active else "ACTIVE",
            "daily_pnl": f"{daily_pnl_pct:.2%}",
            "weekly_pnl": f"{weekly_pnl_pct:.2%}"
        })

    def status(self) -> str:
        return json.dumps({
            "is_active": self.is_active,
            "activated_at": self.activated_at,
            "activation_reason": self.activation_reason,
            "auto_triggers": self.auto_triggers,
            "manual_triggers": self.manual_triggers,
            "message": "TRADING HALTED" if self.is_active else "System operational"
        }, indent=2)
