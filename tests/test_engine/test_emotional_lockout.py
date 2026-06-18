"""Comprehensive tests for the Emotional Lockout System.

Tests cover:
- Consecutive loss trigger
- Daily loss threshold trigger
- Override attempt tracking and blocking
- Manual lockout and unlock
- Progressive lockout durations
- Lockout expiry (auto and manual)
- Position-closing orders during lockout
- Audit trail verification
- Notification callbacks
- Edge cases
"""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta

from quant_nanggroe.engine.risk.emotional_lockout import (
    EmotionalLockoutService,
    EmotionalLockoutConfig,
    LockoutState,
    LockoutReason,
    LockoutEvent,
    UNLOCK_CONFIRMATION,
)


# ======================================================================
# Fixtures
# ======================================================================

@pytest.fixture
def service() -> EmotionalLockoutService:
    """Create a lockout service with default config."""
    return EmotionalLockoutService(initial_equity=100_000.0)


@pytest.fixture
def sensitive_service() -> EmotionalLockoutService:
    """Create a lockout service with low thresholds for testing."""
    config = EmotionalLockoutConfig(
        consecutive_losses_threshold=2,
        consecutive_losses_lockout_hours=0.01,  # ~36 seconds
        daily_loss_pct_threshold=0.02,
        override_attempts_limit=2,
        override_blockout_hours=0.01,
        enable_progressive=False,
    )
    return EmotionalLockoutService(config=config, initial_equity=100_000.0)


@pytest.fixture
def progressive_service() -> EmotionalLockoutService:
    """Create a lockout service with progressive lockout enabled."""
    config = EmotionalLockoutConfig(
        consecutive_losses_threshold=2,
        consecutive_losses_lockout_hours=1.0,
        enable_progressive=True,
        progressive_multiplier=2.0,
        max_progressive_hours=72.0,
    )
    return EmotionalLockoutService(config=config, initial_equity=100_000.0)


# ======================================================================
# 1. Basic state checks
# ======================================================================

class TestBasicState:

    def test_initial_state_not_locked_out(self, service: EmotionalLockoutService):
        assert not service.is_locked_out

    def test_initial_state_expired(self, service: EmotionalLockoutService):
        assert service.lockout_state == LockoutState.EXPIRED

    def test_initial_no_reason(self, service: EmotionalLockoutService):
        assert service.lockout_reason is None

    def test_initial_no_expiry(self, service: EmotionalLockoutService):
        assert service.lockout_expires_at is None

    def test_initial_consecutive_losses_zero(self, service: EmotionalLockoutService):
        assert service.consecutive_losses == 0

    def test_initial_daily_pnl_zero(self, service: EmotionalLockoutService):
        assert service.daily_pnl == 0.0

    def test_initial_override_attempts_zero(self, service: EmotionalLockoutService):
        assert service.override_attempts_today == 0

    def test_initial_violations_zero(self, service: EmotionalLockoutService):
        assert service.total_violations == 0


# ======================================================================
# 2. Order allowed checks
# ======================================================================

class TestOrderAllowed:

    def test_orders_allowed_initially(self, service: EmotionalLockoutService):
        result = service.check_order_allowed(symbol="BTC/USDT")
        assert result["allowed"] is True

    def test_closing_orders_always_allowed(self, service: EmotionalLockoutService):
        """Even during lockout, closing orders should be allowed."""
        service.manual_lockout(duration_hours=1.0)
        result = service.check_order_allowed(symbol="BTC/USDT", is_closing=True)
        assert result["allowed"] is True

    def test_new_orders_blocked_during_lockout(self, service: EmotionalLockoutService):
        service.manual_lockout(duration_hours=1.0)
        result = service.check_order_allowed(symbol="BTC/USDT", is_closing=False)
        assert result["allowed"] is False

    def test_check_result_includes_lockout_state(self, service: EmotionalLockoutService):
        service.manual_lockout(duration_hours=1.0)
        result = service.check_order_allowed(symbol="BTC/USDT")
        assert result["lockout_state"] == LockoutState.ACTIVE

    def test_check_result_includes_expiry(self, service: EmotionalLockoutService):
        service.manual_lockout(duration_hours=1.0)
        result = service.check_order_allowed(symbol="BTC/USDT")
        assert result["expires_at"] is not None


# ======================================================================
# 3. Consecutive loss trigger
# ======================================================================

class TestConsecutiveLossTrigger:

    def test_no_lockout_before_threshold(self, service: EmotionalLockoutService):
        """Default threshold is 3 — 2 losses should not trigger."""
        service.record_trade_result("BTC/USDT", pnl=-100.0)
        service.record_trade_result("BTC/USDT", pnl=-200.0)
        assert not service.is_locked_out

    def test_lockout_on_threshold(self, service: EmotionalLockoutService):
        """3 consecutive losses should trigger lockout."""
        service.record_trade_result("BTC/USDT", pnl=-100.0)
        service.record_trade_result("BTC/USDT", pnl=-200.0)
        assert not service.is_locked_out

        service.record_trade_result("BTC/USDT", pnl=-300.0)
        assert service.is_locked_out
        assert service.lockout_reason == LockoutReason.CONSECUTIVE_LOSSES

    def test_winning_trade_resets_streak(self, service: EmotionalLockoutService):
        """A winning trade should reset the consecutive loss counter."""
        service.record_trade_result("BTC/USDT", pnl=-100.0)
        service.record_trade_result("BTC/USDT", pnl=-200.0)
        assert service.consecutive_losses == 2

        # Win
        service.record_trade_result("BTC/USDT", pnl=500.0)
        assert service.consecutive_losses == 0

        # Now 2 more losses should not trigger
        service.record_trade_result("BTC/USDT", pnl=-50.0)
        service.record_trade_result("BTC/USDT", pnl=-50.0)
        assert not service.is_locked_out

    def test_record_trade_returns_state(self, service: EmotionalLockoutService):
        result = service.record_trade_result("BTC/USDT", pnl=-100.0)
        assert result["pnl"] == -100.0
        assert result["consecutive_losses"] == 1
        assert result["lockout_triggered"] is False

    def test_record_trade_returns_triggered(self, sensitive_service: EmotionalLockoutService):
        result = sensitive_service.record_trade_result("BTC/USDT", pnl=-100.0)
        assert not result["lockout_triggered"]

        result = sensitive_service.record_trade_result("BTC/USDT", pnl=-200.0)
        assert result["lockout_triggered"] is True
        assert result["trigger_reason"] == "consecutive_losses"


# ======================================================================
# 4. Daily loss threshold trigger
# ======================================================================

class TestDailyLossTrigger:

    def test_no_lockout_below_threshold(self, service: EmotionalLockoutService):
        """5% of 100k = 5000. Loss of 4000 should not trigger."""
        service.record_trade_result("BTC/USDT", pnl=-4000.0)
        assert not service.is_locked_out

    def test_lockout_at_threshold(self, sensitive_service: EmotionalLockoutService):
        """2% of 100k = 2000. Loss of 2500 should trigger."""
        result = sensitive_service.record_trade_result("BTC/USDT", pnl=-2500.0)
        assert sensitive_service.is_locked_out
        assert sensitive_service.lockout_reason == LockoutReason.DAILY_LOSS_LIMIT

    def test_cumulative_daily_pnl(self, service: EmotionalLockoutService):
        """Multiple trades summing to > 5% should trigger.
        
        We intersperse wins to avoid triggering consecutive_losses first.
        """
        # 5% of 100k = 5000
        service.record_trade_result("BTC/USDT", pnl=-1100.0)
        service.record_trade_result("ETH/USDT", pnl=10.0)  # Tiny win resets consecutive
        service.record_trade_result("BTC/USDT", pnl=-1100.0)
        service.record_trade_result("ETH/USDT", pnl=10.0)  # Tiny win resets consecutive
        service.record_trade_result("BTC/USDT", pnl=-1100.0)
        service.record_trade_result("ETH/USDT", pnl=10.0)  # Tiny win resets consecutive
        service.record_trade_result("BTC/USDT", pnl=-1100.0)
        service.record_trade_result("ETH/USDT", pnl=10.0)  # Tiny win resets consecutive
        service.record_trade_result("BTC/USDT", pnl=-1100.0)
        # Total: -5500 + 40 = -5460 > -5000
        assert service.is_locked_out
        assert service.lockout_reason == LockoutReason.DAILY_LOSS_LIMIT

    def test_daily_pnl_tracking(self, service: EmotionalLockoutService):
        service.record_trade_result("BTC/USDT", pnl=1000.0)
        assert service.daily_pnl == 1000.0
        service.record_trade_result("BTC/USDT", pnl=-500.0)
        assert service.daily_pnl == 500.0


# ======================================================================
# 5. Override attempts
# ======================================================================

class TestOverrideAttempts:

    def test_override_blocked_during_lockout(self, service: EmotionalLockoutService):
        service.manual_lockout(duration_hours=1.0)
        result = service.attempt_override()
        assert result["override_granted"] is False

    def test_override_granted_when_not_locked(self, service: EmotionalLockoutService):
        result = service.attempt_override()
        assert result["override_granted"] is True

    def test_override_attempts_tracked(self, service: EmotionalLockoutService):
        service.manual_lockout(duration_hours=1.0)
        service.attempt_override()
        assert service.override_attempts_today == 1

    def test_override_abuse_triggers_extended_lockout(
        self, sensitive_service: EmotionalLockoutService,
    ):
        sensitive_service.manual_lockout(duration_hours=0.01)
        # Attempt override limit + 1 times
        sensitive_service.attempt_override()
        result = sensitive_service.attempt_override()
        # After 2 attempts (limit=2), should trigger override abuse
        assert result["lockout_state"] == LockoutState.OVERRIDE_BLOCKED

    def test_override_abuse_reason(self, sensitive_service: EmotionalLockoutService):
        sensitive_service.manual_lockout(duration_hours=0.01)
        sensitive_service.attempt_override()
        result = sensitive_service.attempt_override()
        assert "override" in result["reason"].lower()


# ======================================================================
# 6. Manual lockout and unlock
# ======================================================================

class TestManualLockoutUnlock:

    def test_manual_lockout(self, service: EmotionalLockoutService):
        result = service.manual_lockout(duration_hours=2.0, reason="Taking a break")
        assert service.is_locked_out
        assert service.lockout_reason == LockoutReason.MANUAL

    def test_manual_lockout_result(self, service: EmotionalLockoutService):
        result = service.manual_lockout(duration_hours=2.0, reason="Break")
        assert result["status"] == "LOCKOUT_ACTIVATED"
        assert result["reason"] == "manual"
        assert result["duration_hours"] == 2.0

    def test_manual_unlock_without_confirmation(self, service: EmotionalLockoutService):
        service.manual_lockout(duration_hours=1.0)
        result = service.manual_unlock(confirmation="wrong")
        assert result["status"] == "UNLOCK_DENIED"
        assert service.is_locked_out

    def test_manual_unlock_with_confirmation(self, service: EmotionalLockoutService):
        service.manual_lockout(duration_hours=1.0)
        result = service.manual_unlock(confirmation=UNLOCK_CONFIRMATION)
        assert result["status"] == "UNLOCKED"
        assert not service.is_locked_out

    def test_manual_unlock_when_not_locked(self, service: EmotionalLockoutService):
        result = service.manual_unlock(confirmation=UNLOCK_CONFIRMATION)
        assert result["status"] == "NOT_LOCKED"

    def test_unlock_confirmation_constant(self):
        assert UNLOCK_CONFIRMATION == "CONFIRM_UNLOCK"


# ======================================================================
# 7. Lockout expiry
# ======================================================================

class TestLockoutExpiry:

    def test_lockout_has_expiry(self, service: EmotionalLockoutService):
        service.manual_lockout(duration_hours=1.0)
        assert service.lockout_expires_at is not None
        assert service.lockout_expires_at > datetime.now()

    def test_auto_expire(self, sensitive_service: EmotionalLockoutService):
        """Lockout should auto-expire after duration (using very short duration)."""
        sensitive_service.manual_lockout(duration_hours=0.0001)  # ~0.36 seconds
        assert sensitive_service.is_locked_out

        # Wait for expiry
        import time
        time.sleep(0.5)

        # Check should trigger expiry
        result = sensitive_service.check_order_allowed(symbol="BTC/USDT")
        assert not sensitive_service.is_locked_out
        assert sensitive_service.lockout_state == LockoutState.EXPIRED

    def test_expired_lockout_allows_trading(self, sensitive_service: EmotionalLockoutService):
        sensitive_service.manual_lockout(duration_hours=0.0001)
        import time
        time.sleep(0.5)
        result = sensitive_service.check_order_allowed(symbol="BTC/USDT")
        assert result["allowed"] is True


# ======================================================================
# 8. Progressive lockout
# ======================================================================

class TestProgressiveLockout:

    def test_first_violation_base_duration(self, progressive_service: EmotionalLockoutService):
        """First violation should use base duration."""
        progressive_service.record_trade_result("BTC/USDT", pnl=-100.0)
        progressive_service.record_trade_result("BTC/USDT", pnl=-200.0)
        # Triggered lockout
        assert progressive_service.is_locked_out
        assert progressive_service.total_violations == 1
        # Duration should be base (1 hour)
        remaining = (progressive_service.lockout_expires_at - datetime.now()).total_seconds() / 3600
        assert 0.5 < remaining <= 1.1

    def test_second_violation_doubled(self, progressive_service: EmotionalLockoutService):
        """Second violation should double the duration."""
        # First lockout
        progressive_service.record_trade_result("BTC/USDT", pnl=-100.0)
        progressive_service.record_trade_result("BTC/USDT", pnl=-200.0)

        # Manually unlock
        progressive_service.manual_unlock(confirmation=UNLOCK_CONFIRMATION)
        assert not progressive_service.is_locked_out
        assert progressive_service.total_violations == 1

        # Reset consecutive losses (simulate a win)
        progressive_service.record_trade_result("BTC/USDT", pnl=100.0)
        progressive_service.record_trade_result("BTC/USDT", pnl=-100.0)
        progressive_service.record_trade_result("BTC/USDT", pnl=-200.0)

        # Second lockout — duration should be base * 2^1 = 2 hours
        assert progressive_service.is_locked_out
        assert progressive_service.total_violations == 2
        remaining = (progressive_service.lockout_expires_at - datetime.now()).total_seconds() / 3600
        assert 1.5 < remaining <= 2.1

    def test_progressive_disabled(self, sensitive_service: EmotionalLockoutService):
        """With progressive disabled, duration should always be base."""
        sensitive_service.record_trade_result("BTC/USDT", pnl=-100.0)
        sensitive_service.record_trade_result("BTC/USDT", pnl=-200.0)
        assert sensitive_service.is_locked_out

        sensitive_service.manual_unlock(confirmation=UNLOCK_CONFIRMATION)

        # Trigger another lockout
        sensitive_service.record_trade_result("BTC/USDT", pnl=100.0)
        sensitive_service.record_trade_result("BTC/USDT", pnl=-100.0)
        sensitive_service.record_trade_result("BTC/USDT", pnl=-200.0)
        assert sensitive_service.is_locked_out

        # Duration should still be base (no progressive)
        remaining = (sensitive_service.lockout_expires_at - datetime.now()).total_seconds() / 3600
        assert remaining < 0.02  # ~0.01 hours (base)


# ======================================================================
# 9. Audit trail
# ======================================================================

class TestAuditTrail:

    def test_audit_trail_starts_empty(self, service: EmotionalLockoutService):
        assert len(service.audit_trail) == 0

    def test_manual_lockout_creates_event(self, service: EmotionalLockoutService):
        service.manual_lockout(duration_hours=1.0)
        assert len(service.audit_trail) == 1
        event = service.audit_trail[0]
        assert event.event_type == "activated"
        assert event.reason == LockoutReason.MANUAL

    def test_consecutive_loss_creates_event(self, service: EmotionalLockoutService):
        service.record_trade_result("BTC/USDT", pnl=-100.0)
        service.record_trade_result("BTC/USDT", pnl=-200.0)
        service.record_trade_result("BTC/USDT", pnl=-300.0)
        # Should have lockout event
        events = [e for e in service.audit_trail if e.event_type == "activated"]
        assert len(events) == 1
        assert events[0].reason == LockoutReason.CONSECUTIVE_LOSSES

    def test_unlock_creates_event(self, service: EmotionalLockoutService):
        service.manual_lockout(duration_hours=1.0)
        service.manual_unlock(confirmation=UNLOCK_CONFIRMATION)
        events = [e for e in service.audit_trail if e.event_type == "manual_unlocked"]
        assert len(events) == 1

    def test_failed_unlock_creates_event(self, service: EmotionalLockoutService):
        service.manual_lockout(duration_hours=1.0)
        service.manual_unlock(confirmation="wrong")
        events = [e for e in service.audit_trail if e.event_type == "unlock_attempted"]
        assert len(events) == 1

    def test_override_attempt_creates_event(self, service: EmotionalLockoutService):
        service.manual_lockout(duration_hours=1.0)
        service.attempt_override()
        events = [e for e in service.audit_trail if e.event_type == "override_attempted"]
        assert len(events) == 1

    def test_expiry_creates_event(self, sensitive_service: EmotionalLockoutService):
        sensitive_service.manual_lockout(duration_hours=0.0001)
        import time
        time.sleep(0.5)
        sensitive_service.check_order_allowed(symbol="BTC/USDT")
        events = [e for e in sensitive_service.audit_trail if e.event_type == "expired"]
        assert len(events) == 1

    def test_event_has_timestamp(self, service: EmotionalLockoutService):
        service.manual_lockout(duration_hours=1.0)
        event = service.audit_trail[0]
        assert event.timestamp is not None

    def test_event_has_details(self, service: EmotionalLockoutService):
        service.manual_lockout(duration_hours=1.0)
        event = service.audit_trail[0]
        assert event.duration_hours == 1.0
        assert event.expires_at is not None


# ======================================================================
# 10. Notification callbacks
# ======================================================================

class TestNotificationCallbacks:

    def test_callback_on_lockout(self, service: EmotionalLockoutService):
        received = []
        service.add_notification_callback(lambda et, data: received.append((et, data)))

        service.manual_lockout(duration_hours=1.0)
        assert len(received) == 1
        assert received[0][0] == "lockout_activated"

    def test_callback_on_unlock(self, service: EmotionalLockoutService):
        received = []
        service.add_notification_callback(lambda et, data: received.append((et, data)))

        service.manual_lockout(duration_hours=1.0)
        service.manual_unlock(confirmation=UNLOCK_CONFIRMATION)
        assert len(received) == 2
        assert received[1][0] == "unlocked"

    def test_callback_on_expiry(self, sensitive_service: EmotionalLockoutService):
        received = []
        sensitive_service.add_notification_callback(lambda et, data: received.append((et, data)))

        sensitive_service.manual_lockout(duration_hours=0.0001)
        import time
        time.sleep(0.5)
        sensitive_service.check_order_allowed(symbol="BTC/USDT")

        assert len(received) == 2  # activated + expired
        assert received[1][0] == "lockout_expired"

    def test_callback_error_does_not_crash(self, service: EmotionalLockoutService):
        """A failing callback should not prevent lockout activation."""
        def bad_callback(et, data):
            raise RuntimeError("callback error")

        service.add_notification_callback(bad_callback)
        # Should not raise
        service.manual_lockout(duration_hours=1.0)
        assert service.is_locked_out


# ======================================================================
# 11. Get status
# ======================================================================

class TestGetStatus:

    def test_status_when_not_locked(self, service: EmotionalLockoutService):
        status = service.get_status()
        assert status["is_locked_out"] is False
        assert status["lockout_state"] == "expired"
        assert status["lockout_reason"] is None
        assert status["consecutive_losses"] == 0
        assert status["daily_pnl"] == 0.0

    def test_status_when_locked(self, service: EmotionalLockoutService):
        service.manual_lockout(duration_hours=1.0)
        status = service.get_status()
        assert status["is_locked_out"] is True
        assert status["lockout_state"] == "active"
        assert status["lockout_reason"] == "manual"
        assert status["remaining_lockout_hours"] > 0

    def test_status_includes_thresholds(self, service: EmotionalLockoutService):
        status = service.get_status()
        assert "daily_loss_threshold" in status
        assert "override_attempts_limit" in status


# ======================================================================
# 12. Config
# ======================================================================

class TestConfig:

    def test_default_config(self):
        config = EmotionalLockoutConfig()
        assert config.consecutive_losses_threshold == 3
        assert config.consecutive_losses_lockout_hours == 1.0
        assert config.daily_loss_pct_threshold == 0.05
        assert config.override_attempts_limit == 3
        assert config.override_blockout_hours == 24.0
        assert config.enable_progressive is True
        assert config.progressive_multiplier == 2.0

    def test_custom_config(self):
        config = EmotionalLockoutConfig(
            consecutive_losses_threshold=5,
            daily_loss_pct_threshold=0.10,
        )
        assert config.consecutive_losses_threshold == 5
        assert config.daily_loss_pct_threshold == 0.10

    def test_config_validation_threshold_positive(self):
        with pytest.raises(Exception):
            EmotionalLockoutConfig(consecutive_losses_threshold=0)

    def test_config_validation_pct_range(self):
        with pytest.raises(Exception):
            EmotionalLockoutConfig(daily_loss_pct_threshold=2.0)


# ======================================================================
# 13. LockoutReason and LockoutState enums
# ======================================================================

class TestEnums:

    def test_lockout_state_values(self):
        assert LockoutState.ACTIVE.value == "active"
        assert LockoutState.EXPIRED.value == "expired"
        assert LockoutState.OVERRIDE_BLOCKED.value == "override_blocked"

    def test_lockout_reason_values(self):
        assert LockoutReason.CONSECUTIVE_LOSSES.value == "consecutive_losses"
        assert LockoutReason.DAILY_LOSS_LIMIT.value == "daily_loss_limit"
        assert LockoutReason.OVERRIDE_ABUSE.value == "override_abuse"
        assert LockoutReason.MANUAL.value == "manual"
        assert LockoutReason.PROGRESSIVE.value == "progressive"


# ======================================================================
# 14. Edge cases
# ======================================================================

class TestEdgeCases:

    def test_zero_pnl_does_not_count_as_loss(self, service: EmotionalLockoutService):
        service.record_trade_result("BTC/USDT", pnl=0.0)
        assert service.consecutive_losses == 0

    def test_positive_pnl_resets_consecutive_losses(self, service: EmotionalLockoutService):
        service.record_trade_result("BTC/USDT", pnl=-100.0)
        service.record_trade_result("BTC/USDT", pnl=-200.0)
        assert service.consecutive_losses == 2

        service.record_trade_result("BTC/USDT", pnl=0.01)  # Tiny win
        assert service.consecutive_losses == 0

    def test_multiple_manual_lockouts(self, service: EmotionalLockoutService):
        service.manual_lockout(duration_hours=1.0)
        service.manual_unlock(confirmation=UNLOCK_CONFIRMATION)
        service.manual_lockout(duration_hours=2.0)
        assert service.is_locked_out

    def test_lockout_event_model(self):
        event = LockoutEvent(
            event_type="activated",
            reason=LockoutReason.MANUAL,
            duration_hours=1.0,
            message="Test event",
        )
        assert event.event_type == "activated"
        assert event.reason == LockoutReason.MANUAL
        data = event.model_dump()
        assert data["event_type"] == "activated"

    def test_small_equity_daily_loss(self):
        """With small equity, even small losses should trigger threshold."""
        config = EmotionalLockoutConfig(daily_loss_pct_threshold=0.05)
        service = EmotionalLockoutService(config=config, initial_equity=1000.0)
        # 5% of 1000 = 50
        result = service.record_trade_result("BTC/USDT", pnl=-60.0)
        assert service.is_locked_out

    def test_check_order_result_structure(self, service: EmotionalLockoutService):
        result = service.check_order_allowed(symbol="BTC/USDT")
        assert "allowed" in result
        assert "reason" in result
        assert "lockout_state" in result
        assert "expires_at" in result
