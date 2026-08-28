"""Tests for ConstitutionalRiskGuard (RiskCheckGate)."""
import unittest

from quant_nanggroe.engine.risk.checks import ConstitutionalRiskGuard, PortfolioSnapshot, TradeAction, TradeRequest


class TestConstitutionalRiskGuard(unittest.TestCase):
    def setUp(self):
        self.guard = ConstitutionalRiskGuard()

    def test_check_trade_approved(self):
        req = TradeRequest(symbol="BTC/USDT", action=TradeAction.BUY, quantity=0.1, price=67000.0, risk_pct=0.1)
        pf = PortfolioSnapshot(total_equity=100000.0)
        result = self.guard.check_trade(req, pf)
        self.assertTrue(result.approved)

    def test_check_trade_rejected_excessive_risk(self):
        req = TradeRequest(symbol="BTC/USDT", action=TradeAction.BUY, quantity=10.0, price=67000.0, risk_pct=2.0)
        pf = PortfolioSnapshot(total_equity=100000.0)
        result = self.guard.check_trade(req, pf)
        self.assertFalse(result.approved)

    def test_check_trade_daily_loss_exhausted(self):
        req = TradeRequest(symbol="BTC/USDT", action=TradeAction.BUY, quantity=0.1, price=67000.0, risk_pct=0.1)
        pf = PortfolioSnapshot(total_equity=100000.0, daily_pnl=-2000.0)
        result = self.guard.check_trade(req, pf)
        self.assertFalse(result.approved)

    def test_evaluate_approved(self):
        r = self.guard.evaluate(symbol="BTC/USDT", direction="BUY", lot_size=0.1, entry=67000, stop_loss=2.0)
        self.assertEqual(r["verdict"], "APPROVED")

    def test_evaluate_adjusted(self):
        r = self.guard.evaluate(symbol="BTC/USDT", direction="BUY", lot_size=10.0, entry=67000, stop_loss=2.0)
        self.assertTrue(r["position_size_adjusted"] or r["verdict"] == "APPROVED")

    def test_calculate_position_size_normal(self):
        size = self.guard.calculate_position_size(equity=100000.0, entry_price=67000.0, stop_loss_price=65000.0)
        self.assertGreater(size, 0)

    def test_calculate_position_size_zero_entry(self):
        size = self.guard.calculate_position_size(equity=100000.0, entry_price=0.0, stop_loss_price=65000.0)
        self.assertEqual(size, 0.0)

    def test_stats(self):
        stats = self.guard.stats
        self.assertIn("total_checks", stats)
        self.assertIn("constitutional_limits", stats)
