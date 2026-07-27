"""Tests: _ohlcv_data never fabricates OHLCV bars from a bare close/price.

Incomplete data must return None (fail-closed); complete OHLCV passes
through unchanged.
"""

from __future__ import annotations

from quant_nanggroe.pipeline.signal import UnifiedSignalEngine


def test_none_input_returns_none():
    assert UnifiedSignalEngine._ohlcv_data(None) is None


def test_non_dict_returns_none():
    assert UnifiedSignalEngine._ohlcv_data([1, 2, 3]) is None


def test_price_only_returns_none():
    assert UnifiedSignalEngine._ohlcv_data({"price": 100.0}) is None


def test_close_only_returns_none():
    assert UnifiedSignalEngine._ohlcv_data({"close": 100.0}) is None


def test_partial_ohlc_returns_none():
    assert UnifiedSignalEngine._ohlcv_data({"open": 1.0, "high": 2.0, "close": 1.5}) is None


def test_null_field_returns_none():
    assert UnifiedSignalEngine._ohlcv_data({"open": 1.0, "high": 2.0, "low": None, "close": 1.5}) is None


def test_complete_ohlcv_passes_through_unchanged():
    candle = {"open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 10.0}
    out = UnifiedSignalEngine._ohlcv_data(candle)
    assert out is candle
    assert out == {"open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 10.0}
