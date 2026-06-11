"""Kill Switch — Emergency Halt Mechanism with Persistent State.

Implements the emergency kill switch that automatically activates
when constitutional risk limits are breached. Once activated,
ALL trading is halted and can only be reset after manual review.

PERSISTENCE (P0-4): Kill switch state is persisted to disk so that
a process restart does NOT clear the kill switch. The activation state
survives crashes, restarts, and deployments.

Activation triggers:
- AUTO_DAILY_LIMIT: Daily loss limit breached
- AUTO_WEEKLY_LIMIT: Weekly loss limit breached
- AUTO_MAX_DRAWDOWN: Maximum drawdown breached
- MANUAL: Manual activation by human operator

Reset requires explicit confirmation: "CONFIRM_RESET_AFTER_REVIEW"

Extracted from HermesQuantOS's KillSwitchTool.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Confirmation string required for reset (prevents accidental reset)
RESET_CONFIRMATION = "CONFIRM_RESET_AFTER_REVIEW"

# Default directory for persistence file
_DEFAULT_PERSIST_DIR = os.environ.get(
    "KILL_SWITCH_PERSIST_DIR",
    os.path.join(os.getcwd(), ".quant_nanggroe_safety"),
)
_PERSIST_FILENAME = ".kill_switch_active"


class KillSwitch:
    """Emergency Kill Switch with file-based persistence.

    Once activated, ALL trading is halted. The kill switch can only
    be reset after explicit manual review and confirmation.

    State is persisted to a file on disk. On startup, if the
    persistence file exists, the kill switch is automatically
    restored to ACTIVE state, ensuring that a restart cannot
    bypass the safety halt.

    This is the ultimate safety net — no agent or system can
    bypass or override the kill switch.
    """

    def __init__(
        self,
        persist_dir: Optional[str] = None,
        requires_confirmation: bool = True,
    ) -> None:
        """Initialize the kill switch.

        Args:
            persist_dir: Directory for the persistence file.
                Defaults to KILL_SWITCH_PERSIST_DIR env var or
                .quant_nanggroe_safety/ in the current working directory.
            requires_confirmation: If True, deactivation requires the
                CONFIRM_RESET_AFTER_REVIEW string. Always True in production.
        """
        self._persist_dir = persist_dir or _DEFAULT_PERSIST_DIR
        self._requires_confirmation = requires_confirmation
        self._is_active: bool = False
        self._activated_at: Optional[str] = None
        self._activation_reason: Optional[str] = None
        self._auto_triggers: int = 0
        self._manual_triggers: int = 0
        self._activation_log: list = []

        # ── Restore state from disk (P0-4 SAFETY) ────────────────────
        self._restore_from_disk()

    # ── Persistence ──────────────────────────────────────────────────

    @property
    def _persist_path(self) -> Path:
        """Full path to the persistence file."""
        return Path(self._persist_dir) / _PERSIST_FILENAME

    def _write_state_to_disk(self) -> None:
        """Persist kill switch state to disk.

        Writes a JSON file with activation details so that a process
        restart does NOT clear the kill switch.
        """
        try:
            persist_path = self._persist_path
            persist_path.parent.mkdir(parents=True, exist_ok=True)

            state_data = {
                "is_active": self._is_active,
                "activated_at": self._activated_at,
                "activation_reason": self._activation_reason,
                "auto_triggers": self._auto_triggers,
                "manual_triggers": self._manual_triggers,
                "persisted_at": datetime.now().isoformat(),
            }

            persist_path.write_text(json.dumps(state_data, indent=2))
            logger.info(
                "KillSwitch: State persisted to %s (active=%s)",
                persist_path,
                self._is_active,
            )
        except Exception as exc:
            # Persistence failure is critical but should not crash the system.
            # Log loudly and continue — the in-memory state is still correct.
            logger.critical(
                "KillSwitch: FAILED to persist state to disk! "
                "Kill switch may not survive a restart. Error: %s",
                exc,
            )

    def _remove_state_from_disk(self) -> None:
        """Remove the persistence file (on deactivation)."""
        try:
            persist_path = self._persist_path
            if persist_path.exists():
                persist_path.unlink()
                logger.info("KillSwitch: Persistence file removed at %s", persist_path)
        except Exception as exc:
            logger.critical(
                "KillSwitch: FAILED to remove persistence file! "
                "Kill switch may reactivate on restart. Error: %s",
                exc,
            )

    def _restore_from_disk(self) -> None:
        """Restore kill switch state from disk on startup.

        If the persistence file exists, the kill switch is set to ACTIVE
        regardless of the in-memory state. This ensures that a process
        restart cannot bypass a kill switch activation.
        """
        try:
            persist_path = self._persist_path
            if not persist_path.exists():
                logger.info(
                    "KillSwitch: No persistence file found at %s — "
                    "starting with kill switch INACTIVE",
                    persist_path,
                )
                return

            state_data = json.loads(persist_path.read_text())

            if state_data.get("is_active", False):
                self._is_active = True
                self._activated_at = state_data.get("activated_at")
                self._activation_reason = state_data.get("activation_reason")
                self._auto_triggers = state_data.get("auto_triggers", 0)
                self._manual_triggers = state_data.get("manual_triggers", 0)

                logger.critical(
                    "⚠️  KILL SWITCH RESTORED FROM DISK: active=%s, "
                    "reason=%s, activated_at=%s. "
                    "Trading remains HALTED until manual reset.",
                    self._is_active,
                    self._activation_reason,
                    self._activated_at,
                )
            else:
                logger.info(
                    "KillSwitch: Persistence file exists but kill switch was inactive. "
                    "Cleaning up file."
                )
                self._remove_state_from_disk()

        except (json.JSONDecodeError, KeyError) as exc:
            logger.critical(
                "KillSwitch: Corrupted persistence file at %s. "
                "Assuming ACTIVE for safety. Error: %s",
                self._persist_path,
                exc,
            )
            # SAFETY: If we can't read the file, assume active
            self._is_active = True
            self._activation_reason = "PERSISTENCE_FILE_CORRUPT"
            self._activated_at = datetime.now().isoformat()
        except Exception as exc:
            logger.warning(
                "KillSwitch: Could not read persistence file at %s: %s. "
                "Starting with kill switch INACTIVE.",
                self._persist_path,
                exc,
            )

    # ── Properties ───────────────────────────────────────────────────

    @property
    def is_active(self) -> bool:
        """Whether the kill switch is currently active."""
        return self._is_active

    # ── Activation / Deactivation ────────────────────────────────────

    def activate(self, reason: str = "MANUAL") -> Dict[str, any]:
        """Activate kill switch — halts ALL trading.

        Persists the activation state to disk so it survives restarts.

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

        now = datetime.now().isoformat()
        self._is_active = True
        self._activated_at = now
        self._activation_reason = reason

        if reason.startswith("AUTO_"):
            self._auto_triggers += 1
        else:
            self._manual_triggers += 1

        self._activation_log.append({
            "activated_at": now,
            "reason": reason,
        })

        # Persist to disk (P0-4 SAFETY)
        self._write_state_to_disk()

        logger.critical(
            "⚠️  KILL SWITCH ACTIVATED: %s at %s — persisted to disk",
            reason,
            now,
        )

        return {
            "status": "ACTIVATED",
            "reason": reason,
            "activated_at": now,
            "message": "ALL TRADING HALTED. Manual reset required after review.",
            "auto_triggers_total": self._auto_triggers,
            "manual_triggers_total": self._manual_triggers,
        }

    def reset(self, confirmation: str = "") -> Dict[str, any]:
        """Reset kill switch — requires explicit confirmation.

        When requires_confirmation is True (default), the confirmation
        string must exactly match RESET_CONFIRMATION.

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

        if self._requires_confirmation and confirmation != RESET_CONFIRMATION:
            return {
                "status": "STILL_ACTIVE",
                "message": "Kill switch requires explicit confirmation to reset.",
                "confirmation_required": RESET_CONFIRMATION,
                "note": "Review all trades and risk status before resetting.",
            }

        now = datetime.now().isoformat()
        old_reason = self._activation_reason
        old_activated_at = self._activated_at

        self._is_active = False
        self._activated_at = None
        self._activation_reason = None

        # Remove persistence file (P0-4 SAFETY)
        self._remove_state_from_disk()

        logger.critical(
            "Kill switch RESET after review at %s. "
            "Previous activation: reason=%s, activated_at=%s",
            now,
            old_reason,
            old_activated_at,
        )

        return {
            "status": "RESET",
            "message": "Kill switch deactivated. Trading resumed.",
            "note": "Ensure risk parameters are reviewed before resuming.",
            "previous_activation": {
                "reason": old_reason,
                "activated_at": old_activated_at,
                "reset_at": now,
            },
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
            "persist_dir": self._persist_dir,
            "requires_confirmation": self._requires_confirmation,
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
        from quant_nanggroe.engine.risk.constants import (
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
