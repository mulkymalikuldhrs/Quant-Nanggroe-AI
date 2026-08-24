"""Tests: autonomous pipeline risk gate — FAIL-CLOSED contract.

Rule: every risk guard must VETO (block), never warn-and-pass.
Covers the 2026-08-25 audit fix where an exception inside _check_risk
(or a None execution manager) silently allowed trades through.
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from quant_nanggroe.engine.agentic.autonomous import AutonomousPipeline


def _make_pipeline_with_em(em) -> AutonomousPipeline:
    """Build a pipeline instance without running __init__ (no MT5 needed),
    then inject the given execution manager."""
    p = object.__new__(AutonomousPipeline)
    p._em = em
    return p


def _check_risk(p, symbol="EURUSD", signal="buy", confidence=0.9, price=1.1000):
    """_check_risk is sync — invoke directly."""
    return p._check_risk(symbol, signal, confidence, current_price=price)


class TestCheckRiskFailClosed(unittest.TestCase):
    """_check_risk must BLOCK (False) whenever the gate cannot be evaluated."""

    def test_none_em_blocks_trade(self):
        p = _make_pipeline_with_em(None)
        ok, reason, _m = _check_risk(p)
        self.assertFalse(ok)
        self.assertIn("FAIL-CLOSED", reason)

    def test_missing_risk_manager_blocks_trade(self):
        em = SimpleNamespace(_kill_switch=MagicMock(), _risk_manager=None)
        p = _make_pipeline_with_em(em)
        ok, reason, _m = _check_risk(p)
        self.assertFalse(ok)
        self.assertIn("FAIL-CLOSED", reason)

    def test_missing_kill_switch_blocks_trade(self):
        em = SimpleNamespace(_kill_switch=None, _risk_manager=MagicMock())
        p = _make_pipeline_with_em(em)
        ok, reason, _m = _check_risk(p)
        self.assertFalse(ok)
        self.assertIn("FAIL-CLOSED", reason)

    def test_risk_check_exception_blocks_trade(self):
        rm = MagicMock()
        rm.check_trade.side_effect = RuntimeError("boom")
        ks = MagicMock()
        ks.status.return_value = {"is_active": False}
        em = SimpleNamespace(_kill_switch=ks, _risk_manager=rm)
        p = _make_pipeline_with_em(em)
        ok, reason, _m = _check_risk(p)
        self.assertFalse(ok)
        self.assertIn("FAIL-CLOSED", reason)

    def test_active_kill_switch_blocks_trade(self):
        ks = MagicMock()
        ks.status.return_value = {"is_active": True}
        em = SimpleNamespace(_kill_switch=ks, _risk_manager=MagicMock())
        p = _make_pipeline_with_em(em)
        ok, reason, _m = _check_risk(p)
        self.assertFalse(ok)
        self.assertEqual(reason, "Kill switch active")

    def test_vetoed_verdict_blocks_trade(self):
        rm = MagicMock()
        rm.state.current_equity = 10_000.0
        rm.check_trade.return_value = {"verdict": "VETOED", "reason": "WEEKLY_LOSS"}
        ks = MagicMock()
        ks.status.return_value = {"is_active": False}
        em = SimpleNamespace(_kill_switch=ks, _risk_manager=rm)
        p = _make_pipeline_with_em(em)
        ok, reason, m = _check_risk(p)
        self.assertFalse(ok)
        self.assertIn("vetoed", reason.lower())
        self.assertEqual(m.get("risk_verdict"), "VETOED")

    def test_approved_verdict_passes(self):
        rm = MagicMock()
        rm.state.current_equity = 10_000.0
        rm.check_trade.return_value = {"verdict": "APPROVED"}
        ks = MagicMock()
        ks.status.return_value = {"is_active": False}
        em = SimpleNamespace(_kill_switch=ks, _risk_manager=rm)
        p = _make_pipeline_with_em(em)
        ok, reason, m = _check_risk(p)
        self.assertTrue(ok)
        self.assertEqual(m.get("risk_verdict"), "APPROVED")

    def test_hold_signal_blocked_even_when_approved(self):
        rm = MagicMock()
        rm.state.current_equity = 10_000.0
        rm.check_trade.return_value = {"verdict": "APPROVED"}
        ks = MagicMock()
        ks.status.return_value = {"is_active": False}
        em = SimpleNamespace(_kill_switch=ks, _risk_manager=rm)
        p = _make_pipeline_with_em(em)
        ok, reason, _m = _check_risk(p, signal="hold")
        self.assertFalse(ok)

    def test_low_confidence_blocked_even_when_approved(self):
        rm = MagicMock()
        rm.state.current_equity = 10_000.0
        rm.check_trade.return_value = {"verdict": "APPROVED"}
        ks = MagicMock()
        ks.status.return_value = {"is_active": False}
        em = SimpleNamespace(_kill_switch=ks, _risk_manager=rm)
        p = _make_pipeline_with_em(em)
        ok, reason, _m = _check_risk(p, confidence=0.05)
        self.assertFalse(ok)


class TestMakeDecisionSLTP(unittest.TestCase):
    """_make_decision must accept df/atr/timeframe and never reference
    phantom variables (the old 'atr_val' in dir() bug)."""

    def test_signature_accepts_df_atr_timeframe(self):
        import inspect
        sig = inspect.signature(AutonomousPipeline._make_decision)
        self.assertIn("df", sig.parameters)
        self.assertIn("atr_value", sig.parameters)
        self.assertIn("timeframe", sig.parameters)


if __name__ == "__main__":
    unittest.main()
