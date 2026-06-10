"""Tests for Pydantic Validator module."""

from __future__ import annotations

import pytest

from quant_nanggroe_ai.agents.pydantic_validator import (
    TradingSignalValidator,
    RiskAssessmentValidator,
    DecisionValidator,
    validate_trading_signal,
    validate_risk_assessment,
    validate_decision,
)


# ── TradingSignalValidator ────────────────────────────────────────────────

class TestTradingSignalValidator:
    def test_valid_long_signal(self):
        signal = TradingSignalValidator(
            symbol="BTC/USDT",
            direction="LONG",
            confidence=0.85,
            entry_price=65000.0,
            stop_loss=63000.0,
            take_profit_targets=[67000.0, 69000.0, 71000.0],
        )
        assert signal.direction.value == "LONG"
        assert signal.entry_price == 65000.0

    def test_valid_short_signal(self):
        signal = TradingSignalValidator(
            symbol="ETH/USDT",
            direction="SHORT",
            confidence=0.75,
            entry_price=3500.0,
            stop_loss=3700.0,
            take_profit_targets=[3300.0, 3100.0, 2900.0],
        )
        assert signal.direction.value == "SHORT"


# ── RiskAssessmentValidator ───────────────────────────────────────────────

class TestRiskAssessmentValidator:
    def test_valid_blocked_risk(self):
        risk = RiskAssessmentValidator(
            symbol="BTC/USDT",
            direction="LONG",
            risk_pct=0.5,
            veto_reasons=["High volatility"],
        )
        assert risk.clearance.value == "BLOCKED"


# ── DecisionValidator ─────────────────────────────────────────────────────

class TestDecisionValidator:
    def test_valid_no_trade(self):
        decision = DecisionValidator(
            action="NO_TRADE",
            reason="Low confidence",
            matched_rules=["regime_mismatch"],
        )
        assert decision.action.value == "NO_TRADE"


# ── Convenience Functions ─────────────────────────────────────────────────

class TestConvenienceFunctions:
    def test_validate_trading_signal(self):
        model, errors = validate_trading_signal({
            "symbol": "BTC/USDT",
            "direction": "LONG",
            "confidence": 0.85,
            "entry_price": 65000.0,
            "stop_loss": 63000.0,
            "take_profit_targets": [67000.0],
        })
        assert model is not None
        assert len(errors) == 0

    def test_validate_risk_assessment(self):
        model, errors = validate_risk_assessment({
            "symbol": "BTC/USDT",
            "direction": "LONG",
            "risk_pct": 0.5,
            "veto_reasons": ["test"],
        })
        assert model is not None

    def test_validate_decision(self):
        model, errors = validate_decision({
            "action": "NO_TRADE",
            "reason": "Test",
            "matched_rules": ["test_rule"],
        })
        assert model is not None
