"""
Kill Switch — Emergency Halt System
====================================
From HermesQuantOS — Auto-activate on limit breach, manual reset only.

State is persisted across restarts (via file or database).
Once activated, ALL trading is halted until explicit manual review.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from quant_nanggroe_ai.config import MAX_DAILY_LOSS, MAX_WEEKLY_LOSS


class KillSwitchState(BaseModel):
    """Persistent kill switch state."""

    is_active: bool = False
    activated_at: datetime | None = None
    activation_reason: str | None = None
    auto_triggers: int = 0
    manual_triggers: int = 0
    reset_history: list[dict[str, Any]] = Field(default_factory=list)


class KillSwitch:
    """
    L4 Agent: Kill Switch — Emergency halt system.

    Features:
    - Auto-activates when daily or weekly loss limits are breached
    - Manual activation via API
    - Manual reset ONLY after explicit confirmation
    - State persistence to file for crash recovery
    - Full audit trail of activations and resets
    """

    CONFIRMATION_PHRASE = "CONFIRM_RESET_AFTER_REVIEW"
    STATE_FILE = Path(".kill_switch_state.json")

    def __init__(self, state_dir: str | None = None) -> None:
        self._state_dir = Path(state_dir) if state_dir else Path(".")
        self._state = self._load_state()

    def _state_file_path(self) -> Path:
        return self._state_dir / self.STATE_FILE

    def _load_state(self) -> KillSwitchState:
        """Load persisted state from file."""
        path = self._state_file_path()
        if path.exists():
            try:
                data = json.loads(path.read_text())
                return KillSwitchState(**data)
            except (json.JSONDecodeError, ValueError):
                pass
        return KillSwitchState()

    def _save_state(self) -> None:
        """Persist state to file."""
        path = self._state_file_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self._state.model_dump_json(indent=2))

    @property
    def is_active(self) -> bool:
        """Check if kill switch is currently active."""
        return self._state.is_active

    def activate(self, reason: str = "MANUAL") -> dict[str, Any]:
        """
        Activate kill switch — halts all trading.

        Args:
            reason: Activation reason ("MANUAL", "AUTO_DAILY_LIMIT", "AUTO_WEEKLY_LIMIT")

        Returns:
            Dict with activation status
        """
        self._state.is_active = True
        self._state.activated_at = datetime.now()
        self._state.activation_reason = reason

        if reason.startswith("AUTO_"):
            self._state.auto_triggers += 1
        else:
            self._state.manual_triggers += 1

        self._save_state()

        return {
            "status": "ACTIVATED",
            "reason": reason,
            "activated_at": self._state.activated_at.isoformat(),
            "message": "ALL TRADING HALTED. Manual reset required after review.",
            "auto_triggers_total": self._state.auto_triggers,
            "manual_triggers_total": self._state.manual_triggers,
        }

    def reset(self, confirmation: str = "") -> dict[str, Any]:
        """
        Reset kill switch — requires explicit confirmation.

        The confirmation phrase is deliberately long and explicit to prevent
        accidental resets. No automated system should be able to reset this.

        Args:
            confirmation: Must be exactly "CONFIRM_RESET_AFTER_REVIEW"

        Returns:
            Dict with reset status
        """
        if confirmation != self.CONFIRMATION_PHRASE:
            return {
                "status": "STILL_ACTIVE",
                "message": "Kill switch requires explicit confirmation to reset.",
                "confirmation_required": self.CONFIRMATION_PHRASE,
                "note": "Review all trades and risk status before resetting.",
            }

        # Record reset in history
        self._state.reset_history.append(
            {
                "reset_at": datetime.now().isoformat(),
                "was_activated_by": self._state.activation_reason,
                "was_activated_at": self._state.activated_at.isoformat() if self._state.activated_at else None,
            }
        )

        self._state.is_active = False
        self._state.activated_at = None
        self._state.activation_reason = None

        self._save_state()

        return {
            "status": "RESET",
            "message": "Kill switch deactivated. Trading resumed.",
            "note": "Ensure risk parameters are reviewed before resuming.",
        }

    def check_auto_trigger(
        self,
        daily_pnl_pct: float,
        weekly_pnl_pct: float,
    ) -> dict[str, Any]:
        """
        Auto-check if kill switch should trigger based on risk limits.

        Called by the risk guard after every trade PnL update.

        Args:
            daily_pnl_pct: Current daily PnL as percentage of account
            weekly_pnl_pct: Current weekly PnL as percentage of account

        Returns:
            Dict with current status
        """
        if abs(min(0.0, daily_pnl_pct)) >= MAX_DAILY_LOSS:
            return self.activate("AUTO_DAILY_LIMIT")

        if abs(min(0.0, weekly_pnl_pct)) >= MAX_WEEKLY_LOSS:
            return self.activate("AUTO_WEEKLY_LIMIT")

        return {
            "status": "OK" if not self._state.is_active else "ACTIVE",
            "daily_pnl": f"{daily_pnl_pct:.2%}",
            "weekly_pnl": f"{weekly_pnl_pct:.2%}",
        }

    def status(self) -> dict[str, Any]:
        """Get current kill switch status."""
        return {
            "is_active": self._state.is_active,
            "activated_at": self._state.activated_at.isoformat() if self._state.activated_at else None,
            "activation_reason": self._state.activation_reason,
            "auto_triggers": self._state.auto_triggers,
            "manual_triggers": self._state.manual_triggers,
            "total_resets": len(self._state.reset_history),
            "message": "TRADING HALTED" if self._state.is_active else "System operational",
        }
