"""
failsafe.py — 8-Layer Failsafe System for Trading Platform
Adapted from ghoststudio-ai failsafe.py for trading operations.

Layers:
1. Kill Switch      — emergency halt for all trading
2. Review Mode      — queue trades for manual approval
3. Dry Run          — simulate without executing
4. Error Threshold  — stop after N consecutive errors
5. Quality Gate     — reject signals below quality score
6. Duplicate Detect — reject duplicate trade signals
7. Rate Limit       — limit trades per time window
8. Budget Limiter   — stop when daily loss/exposure exceeded
"""

import time
import hashlib
import threading
from datetime import datetime
from typing import Any, Optional


class FailsafeError(Exception):
    """Base failsafe exception."""
    pass


class KillSwitchActive(FailsafeError):
    """Kill switch is active — all trading halted."""
    pass


class ReviewRequiredError(FailsafeError):
    """Trade requires manual review."""
    pass


class QualityGateError(FailsafeError):
    """Signal failed quality check."""
    pass


class DuplicateSignalError(FailsafeError):
    """Duplicate trade signal detected."""
    pass


class RateLimitError(FailsafeError):
    """Rate limit exceeded."""
    pass


class BudgetLimitError(FailsafeError):
    """Budget/loss limit reached."""
    pass


class ErrorThresholdReached(FailsafeError):
    """Error threshold exceeded."""
    pass


class FailsafeSystem:
    """
    8-layer failsafe system for trading operations.

    Provides multi-layered safety checks before any trading action is executed.
    Each layer can independently block or flag a trade for review.
    """

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.fs_config = self.config.get("failsafe", {})
        self._error_count = 0
        self._consecutive_losses = 0
        self._error_lock = threading.Lock()
        self._rate_buckets: dict[tuple[str, int], int] = {}
        self._rate_lock = threading.Lock()
        self._signal_hashes: dict[str, float] = {}
        self._daily_stats = {
            "trades": 0,
            "api_calls": 0,
            "pnl_usd": 0.0,
            "max_drawdown_usd": 0.0,
            "commission_usd": 0.0,
        }
        self._daily_reset = datetime.now().date()
        self._kill_switch_active = self.fs_config.get("kill_switch", False)

    # ── Layer 1: Kill Switch ─────────────────────────────────

    def check_kill_switch(self) -> None:
        """If kill switch is active, block all trading actions."""
        if self._kill_switch_active:
            raise KillSwitchActive(
                "[Failsafe Layer 1] KILL SWITCH ACTIVE: All trading is halted. "
                "Use reset_kill_switch() to resume."
            )

    def activate_kill_switch(self, reason: str = "Manual activation") -> None:
        """Activate the kill switch — emergency halt."""
        self._kill_switch_active = True

    def reset_kill_switch(self) -> None:
        """Reset the kill switch to allow trading again."""
        self._kill_switch_active = False
        self.reset_error_count()

    @property
    def is_kill_switch_active(self) -> bool:
        return self._kill_switch_active

    # ── Layer 2: Review Mode ─────────────────────────────────

    def check_review_mode(self) -> bool:
        """Check if trade needs manual review. Returns True if auto-approved."""
        if self.fs_config.get("review_mode", False):
            return False  # needs review
        return True  # auto-approved

    # ── Layer 3: Dry Run ─────────────────────────────────────

    def is_dry_run(self) -> bool:
        """Check if dry run mode is active (simulate without execution)."""
        return self.fs_config.get("dry_run", False)

    # ── Layer 4: Error Threshold ─────────────────────────────

    def record_error(self, is_loss: bool = False) -> None:
        """Record an error and check threshold."""
        with self._error_lock:
            self._error_count += 1
            if is_loss:
                self._consecutive_losses += 1

            threshold = self.fs_config.get("error_threshold", 5)
            if self._error_count >= threshold:
                raise ErrorThresholdReached(
                    f"[Failsafe Layer 4] ERROR THRESHOLD: {self._error_count} consecutive errors "
                    f"(max {threshold}). Trading paused."
                )

            loss_threshold = self.fs_config.get("max_consecutive_losses", 7)
            if self._consecutive_losses >= loss_threshold:
                self._kill_switch_active = True
                raise KillSwitchActive(
                    f"[Failsafe Layer 4] CONSECUTIVE LOSSES: {self._consecutive_losses} losses "
                    f"(max {loss_threshold}). Kill switch activated."
                )

    def record_success(self, pnl: float = 0.0) -> None:
        """Reset error count on success."""
        with self._error_lock:
            self._error_count = 0
            if pnl > 0:
                self._consecutive_losses = 0
            elif pnl < 0:
                self._consecutive_losses += 1

    def reset_error_count(self) -> None:
        with self._error_lock:
            self._error_count = 0
            self._consecutive_losses = 0

    # ── Layer 5: Quality Gate ────────────────────────────────

    def check_quality_gate(self, score: float, min_score: Optional[float] = None) -> bool:
        """Check if signal quality meets threshold."""
        if not self.fs_config.get("quality_gate_enabled", True):
            return True
        threshold = min_score if min_score is not None else self.fs_config.get("quality_min_score", 0.6)
        if score < threshold:
            raise QualityGateError(
                f"[Failsafe Layer 5] QUALITY GATE: Signal score {score:.2f} < threshold {threshold:.2f}. "
                f"Trade rejected."
            )
        return True

    # ── Layer 6: Duplicate Detection ─────────────────────────

    def check_duplicate(self, signal_hash: str, ttl_seconds: float = 300.0) -> bool:
        """Check for duplicate trade signals within a time window."""
        if not self.fs_config.get("duplicate_detection", True):
            return True
        now = time.time()
        # Clean old entries
        self._signal_hashes = {
            k: v for k, v in self._signal_hashes.items() if now - v < ttl_seconds
        }
        if signal_hash in self._signal_hashes:
            raise DuplicateSignalError(
                f"[Failsafe Layer 6] DUPLICATE: Signal hash {signal_hash[:16]}... "
                f"already processed within {ttl_seconds}s."
            )
        return True

    @staticmethod
    def compute_signal_hash(
        symbol: str, side: str, price: float, strategy: str = ""
    ) -> str:
        """Compute a hash for duplicate signal detection."""
        raw = f"{symbol}||{side}||{price:.6f}||{strategy}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    # ── Layer 7: Rate Limit ──────────────────────────────────

    def check_rate_limit(self, action_type: str = "trade") -> None:
        """Rate limit trades per minute."""
        max_per_minute = self.fs_config.get(
            f"rate_limit_{action_type}_per_minute",
            self.fs_config.get("rate_limit_per_minute", 10),
        )
        now = time.time()
        minute = int(now // 60)

        with self._rate_lock:
            key = (action_type, minute)
            count = self._rate_buckets.get(key, 0)
            if count >= max_per_minute:
                raise RateLimitError(
                    f"[Failsafe Layer 7] RATE LIMIT: {count} {action_type} actions in current minute "
                    f"(max {max_per_minute})."
                )
            self._rate_buckets[key] = count + 1
            # Clean old buckets
            for k in list(self._rate_buckets.keys()):
                if k[1] < minute - 2:
                    del self._rate_buckets[k]

    # ── Layer 8: Budget/Loss Limiter ─────────────────────────

    def _ensure_daily_reset(self) -> None:
        today = datetime.now().date()
        if today != self._daily_reset:
            self._daily_stats = {
                "trades": 0,
                "api_calls": 0,
                "pnl_usd": 0.0,
                "max_drawdown_usd": 0.0,
                "commission_usd": 0.0,
            }
            self._daily_reset = today

    def track_trade(self, pnl_usd: float = 0.0, commission: float = 0.0) -> None:
        """Track trade towards daily limits."""
        self._ensure_daily_reset()
        if not self.fs_config.get("budget_limiter", True):
            return

        self._daily_stats["trades"] += 1
        self._daily_stats["pnl_usd"] += pnl_usd
        self._daily_stats["commission_usd"] += commission
        if pnl_usd < 0:
            self._daily_stats["max_drawdown_usd"] = min(
                self._daily_stats["max_drawdown_usd"], pnl_usd
            )

        limits = self.config.get("budget_limits", {})
        max_daily_trades = limits.get("max_daily_trades", 50)
        max_daily_loss = limits.get("max_daily_loss_usd", 1000.0)

        if self._daily_stats["trades"] > max_daily_trades:
            raise BudgetLimitError(
                f"[Failsafe Layer 8] DAILY TRADE LIMIT: {self._daily_stats['trades']} trades "
                f"(max {max_daily_trades}). Trading halted for today."
            )

        if self._daily_stats["pnl_usd"] < -max_daily_loss:
            self._kill_switch_active = True
            raise KillSwitchActive(
                f"[Failsafe Layer 8] DAILY LOSS LIMIT: ${abs(self._daily_stats['pnl_usd']):.2f} loss "
                f"(max ${max_daily_loss:.2f}). Kill switch activated."
            )

    def track_api_call(self, cost_usd: float = 0.0) -> None:
        """Track API call towards daily limits."""
        self._ensure_daily_reset()
        limits = self.config.get("budget_limits", {})
        daily_calls_limit = limits.get("daily_api_calls", 1000)
        self._daily_stats["api_calls"] += 1
        if self._daily_stats["api_calls"] > daily_calls_limit:
            raise BudgetLimitError(
                f"[Failsafe Layer 8] API LIMIT: {self._daily_stats['api_calls']} calls today "
                f"(max {daily_calls_limit})."
            )

    def get_daily_stats(self) -> dict[str, Any]:
        self._ensure_daily_reset()
        return dict(self._daily_stats)

    # ── Combined Pre-Flight Check ────────────────────────────

    def preflight(
        self,
        action_type: str = "trade",
        signal_hash: Optional[str] = None,
        quality_score: Optional[float] = None,
        estimated_pnl: float = 0.0,
    ) -> tuple[bool, bool, Optional[str]]:
        """
        Run all applicable failsafe checks before a trade.
        Returns: (passed, needs_review, error_message)
        """
        # Layer 1: Kill Switch
        try:
            self.check_kill_switch()
        except KillSwitchActive as e:
            return False, False, str(e)

        # Layer 2: Review Mode
        can_auto = self.check_review_mode()

        # Layer 7: Rate Limit
        try:
            self.check_rate_limit(action_type)
        except FailsafeError as e:
            return False, False, str(e)

        # Layer 5: Quality Gate
        if quality_score is not None:
            try:
                self.check_quality_gate(quality_score)
            except FailsafeError as e:
                return False, False, str(e)

        # Layer 6: Duplicate Detection
        if signal_hash:
            try:
                self.check_duplicate(signal_hash)
                # Record the signal hash on pass
                self._signal_hashes[signal_hash] = time.time()
            except FailsafeError as e:
                return False, False, str(e)

        # Layer 8: Budget
        try:
            self.track_trade(pnl_usd=estimated_pnl)
        except FailsafeError as e:
            return False, False, str(e)

        return True, (not can_auto), None


# Singleton
_failsafe_instance: Optional[FailsafeSystem] = None


def get_failsafe(config: Optional[dict] = None) -> FailsafeSystem:
    """Get or create the global failsafe system instance."""
    global _failsafe_instance
    if _failsafe_instance is None:
        _failsafe_instance = FailsafeSystem(config)
    return _failsafe_instance
