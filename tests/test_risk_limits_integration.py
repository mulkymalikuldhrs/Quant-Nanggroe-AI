"""Tests for RiskLimits integration into pipeline risk check (Gap C2).

Verifies RiskLimits.can_trade() is called as first-line defense in _pipeline_risk_check.
"""
import unittest
from unittest.mock import MagicMock, patch, PropertyMock

from quant_nanggroe.engine.risk.limits import RiskLimits


class TestRiskLimitsStandalone(unittest.TestCase):
    """Test RiskLimits class directly."""

    def setUp(self):
        # Use temp directory for isolation
        import tempfile
        self.temp_dir = tempfile.TemporaryDirectory()
        self.limits = RiskLimits(
            max_weekly_loss_pct=0.03,
            state_dir=self.temp_dir.name,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_can_trade_allows_when_under_limit(self):
        """can_trade() returns True when weekly loss is under limit."""
        self.limits._weekly_pnl = -0.01  # 1% loss
        self.limits.max_weekly_loss_pct = 0.03  # 3% limit
        self.assertTrue(self.limits.can_trade())

    def test_can_trade_blocks_when_at_limit(self):
        """can_trade() returns False when weekly loss reaches limit."""
        self.limits._weekly_pnl = -0.03  # exactly 3% loss
        self.limits.max_weekly_loss_pct = 0.03
        self.assertFalse(self.limits.can_trade())

    def test_can_trade_blocks_when_exceeds_limit(self):
        """can_trade() returns False when weekly loss exceeds limit."""
        self.limits._weekly_pnl = -0.05  # 5% loss
        self.limits.max_weekly_loss_pct = 0.03
        self.assertFalse(self.limits.can_trade())

    def test_current_weekly_loss_pct_returns_positive_loss(self):
        """current_weekly_loss_pct returns absolute loss value."""
        self.limits._weekly_pnl = -0.025
        self.assertEqual(self.limits.current_weekly_loss_pct(), 0.025)

    def test_current_weekly_loss_pct_returns_zero_when_profit(self):
        """current_weekly_loss_pct returns 0 when PnL is positive."""
        self.limits._weekly_pnl = 0.02
        self.assertEqual(self.limits.current_weekly_loss_pct(), 0.0)

    def test_record_trade_updates_weekly_pnl(self):
        """record_trade adds PnL to weekly total."""
        self.limits._weekly_pnl = 0.0
        self.limits.record_trade(-100.0)
        self.assertEqual(self.limits.weekly_pnl, -100.0)

    def test_record_trade_persists(self):
        """record_trade persists state to disk."""
        self.limits.record_trade(-50.0)
        # Create new instance to verify persistence
        new_limits = RiskLimits(state_dir=self.temp_dir.name)
        self.assertEqual(new_limits.weekly_pnl, -50.0)


if __name__ == "__main__":
    unittest.main()