"""COT Position Guard tests — conflict detection logic."""
from __future__ import annotations

from unittest.mock import patch

from quant_nanggroe.engine.risk.cot_position_guard import (
    check_position_conflict,
)

_COT_BULL = {"bias": "bullish", "net_noncommercial": 50000, "strength": 0.3}
_COT_BEAR = {"bias": "bearish", "net_noncommercial": -30000, "strength": 0.25}


class TestConflictDetection:
    @patch("quant_nanggroe.engine.risk.cot_position_guard.get_cot_positioning")
    def test_conflicting_losing_should_close(self, mock_cot):
        mock_cot.return_value = _COT_BULL
        should_close, reason = check_position_conflict("EURUSD.vx", "sell", -50.0)
        assert should_close is True
        assert "CONFLICT" in reason
        assert "LOSING" in reason

    @patch("quant_nanggroe.engine.risk.cot_position_guard.get_cot_positioning")
    def test_conflicting_winning_should_NOT_close(self, mock_cot):
        mock_cot.return_value = _COT_BULL
        should_close, reason = check_position_conflict("EURUSD.vx", "sell", +30.0)
        assert should_close is False
        assert "WINNING" in reason

    @patch("quant_nanggroe.engine.risk.cot_position_guard.get_cot_positioning")
    def test_aligned_should_not_close(self, mock_cot):
        mock_cot.return_value = _COT_BULL
        should_close, reason = check_position_conflict("EURUSD.vx", "buy", -20.0)
        assert should_close is False
        assert reason and "ALIGNED" in reason

    @patch("quant_nanggroe.engine.risk.cot_position_guard.get_cot_positioning")
    def test_no_cot_data_no_action(self, mock_cot):
        mock_cot.return_value = None
        should_close, reason = check_position_conflict("XAUUSD.vx", "buy", -10.0)
        assert should_close is False
        assert reason is None

    @patch("quant_nanggroe.engine.risk.cot_position_guard.get_cot_positioning")
    def test_neutral_bias_no_action(self, mock_cot):
        mock_cot.return_value = {"bias": "neutral", "strength": 0.0}
        should_close, _ = check_position_conflict("GBPUSD.vx", "sell", -5.0)
        assert should_close is False


class TestSymbolMapping:
    def test_eurusd_maps_to_euro_fx(self):
        from quant_nanggroe.engine.risk.cot_position_guard import (
            _symbol_to_cot_market,
        )
        assert _symbol_to_cot_market("EURUSD.vx") == "Euro FX"

    def test_xauusd_maps_to_gold(self):
        from quant_nanggroe.engine.risk.cot_position_guard import (
            _symbol_to_cot_market,
        )
        assert _symbol_to_cot_market("XAUUSD.vx") == "GOLD"
