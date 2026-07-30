"""Tests: MacroPulseProvider — Yahoo Finance macro market data.

Mocks external HTTP calls via urlopen patching.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from quant_nanggroe.providers.tradebobby.macro_pulse_provider import (
    _CACHE,
    _TICKERS,
    MacroPulseProvider,
)


def _build_yahoo_payload(price: float, prev_close: float) -> bytes:
    return json.dumps({
        "chart": {
            "result": [{
                "meta": {
                    "regularMarketPrice": price,
                    "chartPreviousClose": prev_close,
                    "regularMarketDayHigh": round(price * 1.01, 2),
                    "regularMarketDayLow": round(price * 0.99, 2),
                    "regularMarketTime": 1234567890,
                }
            }]
        }
    }).encode()


def _yahoo_side_effect(ticker: str):
    """Return Yahoo-mock data keyed by ticker symbol."""
    table = {
        # VIX cluster — backwardation (VIX > VIX3M)
        "^VIX": (22.5, 21.0),
        "^VIX9D": (18.0, 23.0),
        "^VIX3M": (19.0, 18.5),
        "^VIX6M": (18.5, 18.0),
        "^VVIX": (115.0, 110.0),
        "^MOVE": (95.0, 93.0),
        # Yield curve — INVERTED (10y < 3m)
        "^TNX": (3.85, 3.80),
        "^FVX": (3.60, 3.55),
        "^IRX": (4.50, 4.45),
        "^TYX": (4.10, 4.05),
        # DXY — strong dollar
        "DX-Y.NYB": (104.5, 104.0),
        # Credit
        "IEF": (92.0, 91.5),
        "LQD": (108.0, 107.5),
        "JNK": (96.0, 96.5),
        "HYG": (95.0, 95.5),
        # Commodities
        "GC=F": (2350.0, 2340.0),
        "SI=F": (28.5, 28.0),
        "CL=F": (78.0, 77.5),
        "BZ=F": (82.0, 81.5),
        "HG=F": (4.20, 4.15),
        # Sectors — risk_on > risk_off
        "XLK": (210.0, 208.0),
        "XLF": (42.0, 41.5),
        "XLE": (88.0, 87.5),
        "XLV": (145.0, 144.5),
        "XLI": (125.0, 124.0),
        "XLY": (180.0, 178.0),
        "XLP": (78.0, 78.5),
        "XLU": (72.0, 72.5),
        "XLB": (85.0, 84.5),
        "XLRE": (38.0, 37.8),
        "XLC": (80.0, 79.5),
        # Mag-7
        "AAPL": (225.0, 223.0),
        "MSFT": (420.0, 418.0),
        "GOOGL": (175.0, 174.0),
        "AMZN": (200.0, 198.0),
        "NVDA": (880.0, 870.0),
        "META": (520.0, 515.0),
        "TSLA": (248.0, 245.0),
        # Indices
        "^GSPC": (5600.0, 5580.0),
        "^NDX": (19500.0, 19450.0),
        "^DJI": (41000.0, 40900.0),
        "^FTSE": (8200.0, 8180.0),
        "^GDAXI": (18500.0, 18450.0),
        "^FCHI": (7500.0, 7480.0),
        "^N225": (39000.0, 38900.0),
        "^HSI": (17500.0, 17450.0),
    }
    price, prev = table.get(ticker, (100.0, 99.0))
    change_pct = round((price - prev) / prev * 100, 4)
    return {
        "price": price,
        "prev_close": prev,
        "change": round(price - prev, 4),
        "change_pct": change_pct,
        "high": round(price * 1.01, 2),
        "low": round(price * 0.99, 2),
        "time": 1234567890,
    }


class TestMacroPulseProviderInit(unittest.TestCase):
    """Provider construction & cache wiring."""

    def setUp(self):
        _CACHE.clear()
        self.provider = MacroPulseProvider()

    def test_provider_initialises(self):
        self.assertIsInstance(self.provider, MacroPulseProvider)
        self.assertIsNotNone(self.provider._cache)

    def test_module_cache_is_shared(self):
        from quant_nanggroe.providers.tradebobby.macro_pulse_provider import _CACHE as module_cache
        self.assertIs(self.provider._cache, module_cache)


class TestFetchAll(unittest.TestCase):
    """fetch_all() returns all tickers and derived metrics."""

    def setUp(self):
        _CACHE.clear()
        self.provider = MacroPulseProvider()

    @patch("quant_nanggroe.providers.tradebobby.macro_pulse_provider._fetch_yahoo")
    def test_fetch_all_returns_dict_with_at_least_40_tickers(self, mock_fetch):
        mock_fetch.side_effect = _yahoo_side_effect
        result = self.provider.fetch_all()
        self.assertIn("data", result)
        self.assertIn("timestamp", result)
        self.assertIn("derived", result)
        self.assertGreaterEqual(len(result["data"]), 40)

    @patch("quant_nanggroe.providers.tradebobby.macro_pulse_provider._fetch_yahoo")
    def test_fetch_all_includes_vol_and_rates(self, mock_fetch):
        mock_fetch.side_effect = _yahoo_side_effect
        result = self.provider.fetch_all()
        data = result["data"]
        self.assertIn("vix", data)
        self.assertIn("us10y", data)
        self.assertIn("dxy", data)
        self.assertIn("gold_f", data)
        self.assertIn("spx", data)

    @patch("quant_nanggroe.providers.tradebobby.macro_pulse_provider._fetch_yahoo")
    def test_fetch_all_derived_has_composite_score(self, mock_fetch):
        mock_fetch.side_effect = _yahoo_side_effect
        result = self.provider.fetch_all()
        derived = result["derived"]
        self.assertIn("composite_risk_score", derived)
        score = derived["composite_risk_score"]
        self.assertIsInstance(score, (int, float))
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

    @patch("quant_nanggroe.providers.tradebobby.macro_pulse_provider._fetch_yahoo")
    def test_fetch_all_derived_has_vol_regime(self, mock_fetch):
        mock_fetch.side_effect = _yahoo_side_effect
        result = self.provider.fetch_all()
        derived = result["derived"]
        self.assertIn("vol_regime", derived)
        self.assertIn(derived["vol_regime"], {"COMPLACENT", "NORMAL", "ELEVATED", "HIGH", "EXTREME"})

    @patch("quant_nanggroe.providers.tradebobby.macro_pulse_provider._fetch_yahoo")
    def test_fetch_all_handles_partial_failures(self, mock_fetch):
        """When _fetch_yahoo returns None for some tickers, others still load."""
        call_count = 0

        def partial_side(ticker):
            nonlocal call_count
            call_count += 1
            if call_count % 5 == 0:
                return None
            return _yahoo_side_effect(ticker)

        mock_fetch.side_effect = partial_side
        result = self.provider.fetch_all()
        self.assertIn("data", result)
        # At least some tickers should have loaded
        self.assertGreater(len(result["data"]), 0)


class TestGetVixTerm(unittest.TestCase):
    """VIX term structure methods."""

    def setUp(self):
        _CACHE.clear()
        self.provider = MacroPulseProvider()

    @patch("quant_nanggroe.providers.tradebobby.macro_pulse_provider._fetch_yahoo")
    def test_get_vix_term_returns_backwardation_flag(self, mock_fetch):
        mock_fetch.side_effect = _yahoo_side_effect
        result = self.provider.get_vix_term()
        self.assertIn("vix", result)
        self.assertIn("vix3m", result)
        self.assertIn("term_structure", result)
        self.assertIn("term_state", result)
        self.assertEqual(result["term_state"], "BACKWARDATION")

    @patch("quant_nanggroe.providers.tradebobby.macro_pulse_provider._fetch_yahoo")
    def test_get_vix_term_includes_vvix(self, mock_fetch):
        mock_fetch.side_effect = _yahoo_side_effect
        result = self.provider.get_vix_term()
        self.assertIn("vvix", result)
        self.assertIn("vvix_vix_ratio", result)

    @patch("quant_nanggroe.providers.tradebobby.macro_pulse_provider._fetch_yahoo")
    def test_get_vix_term_contango_when_vix_below_vix3m(self, mock_fetch):
        def contango_side(ticker):
            base = _yahoo_side_effect(ticker)
            if ticker == "^VIX":
                return {"price": 15.0, "prev_close": 14.5, "change": 0.5,
                        "change_pct": 3.45, "high": 15.2, "low": 14.8, "time": 1234567890}
            if ticker == "^VIX3M":
                return {"price": 18.0, "prev_close": 17.5, "change": 0.5,
                        "change_pct": 2.86, "high": 18.2, "low": 17.8, "time": 1234567890}
            return base

        mock_fetch.side_effect = contango_side
        result = self.provider.get_vix_term()
        self.assertEqual(result["term_state"], "CONTANGO")


class TestGetYieldCurve(unittest.TestCase):
    """Yield curve analysis."""

    def setUp(self):
        _CACHE.clear()
        self.provider = MacroPulseProvider()

    @patch("quant_nanggroe.providers.tradebobby.macro_pulse_provider._fetch_yahoo")
    def test_get_yield_curve_returns_inversion_flag(self, mock_fetch):
        mock_fetch.side_effect = _yahoo_side_effect
        result = self.provider.get_yield_curve()
        self.assertIn("us10y", result)
        self.assertIn("us3m", result)
        self.assertIn("spread_10y_3m", result)
        self.assertIn("inversion_flag", result)
        self.assertIn("curve_state", result)
        self.assertTrue(result["inversion_flag"])
        self.assertEqual(result["curve_state"], "INVERTED")

    @patch("quant_nanggroe.providers.tradebobby.macro_pulse_provider._fetch_yahoo")
    def test_get_yield_curve_normal(self, mock_fetch):
        def normal_side(ticker):
            base = _yahoo_side_effect(ticker)
            if ticker == "^TNX":
                return {"price": 4.80, "prev_close": 4.75, "change": 0.05,
                        "change_pct": 1.05, "high": 4.82, "low": 4.78, "time": 1234567890}
            if ticker == "^IRX":
                return {"price": 3.50, "prev_close": 3.45, "change": 0.05,
                        "change_pct": 1.45, "high": 3.52, "low": 3.48, "time": 1234567890}
            return base

        mock_fetch.side_effect = normal_side
        result = self.provider.get_yield_curve()
        self.assertFalse(result["inversion_flag"])
        self.assertEqual(result["curve_state"], "NORMAL")

    @patch("quant_nanggroe.providers.tradebobby.macro_pulse_provider._fetch_yahoo")
    def test_get_yield_curve_includes_30y_10y_spread(self, mock_fetch):
        mock_fetch.side_effect = _yahoo_side_effect
        result = self.provider.get_yield_curve()
        self.assertIn("spread_30y_10y", result)


class TestGetMacroRegime(unittest.TestCase):
    """Macro regime classification (composite risk score)."""

    def setUp(self):
        _CACHE.clear()
        self.provider = MacroPulseProvider()

    @patch("quant_nanggroe.providers.tradebobby.macro_pulse_provider._fetch_yahoo")
    def test_get_macro_regime_returns_0_to_100_score(self, mock_fetch):
        mock_fetch.side_effect = _yahoo_side_effect
        result = self.provider.get_macro_regime()
        self.assertIn("composite_risk_score", result)
        score = result["composite_risk_score"]
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

    @patch("quant_nanggroe.providers.tradebobby.macro_pulse_provider._fetch_yahoo")
    def test_get_macro_regime_has_classification(self, mock_fetch):
        mock_fetch.side_effect = _yahoo_side_effect
        result = self.provider.get_macro_regime()
        self.assertIn("composite_classification", result)
        self.assertIn(result["composite_classification"],
                      {"RISK_ON", "CAUTIOUS", "RISK_OFF", "CRISIS"})

    @patch("quant_nanggroe.providers.tradebobby.macro_pulse_provider._fetch_yahoo")
    def test_get_macro_regime_has_vol_and_yield(self, mock_fetch):
        mock_fetch.side_effect = _yahoo_side_effect
        result = self.provider.get_macro_regime()
        self.assertIn("vol_regime", result)
        self.assertIn("yield_curve_state", result)
        self.assertIn("vix_term_state", result)


class TestCacheBehavior(unittest.TestCase):
    """TTL cache wired correctly — second call returns cached result."""

    def setUp(self):
        _CACHE.clear()
        self.provider = MacroPulseProvider()

    @patch("quant_nanggroe.providers.tradebobby.macro_pulse_provider._fetch_yahoo")
    def test_fetch_all_returns_cached_result_on_second_call(self, mock_fetch):
        mock_fetch.side_effect = _yahoo_side_effect
        first = self.provider.fetch_all()
        second = self.provider.fetch_all()
        self.assertIs(first, second)
        # _fetch_yahoo should only have been called once per ticker
        self.assertEqual(mock_fetch.call_count, len(_TICKERS))

    @patch("quant_nanggroe.providers.tradebobby.macro_pulse_provider._fetch_yahoo")
    def test_get_vix_term_uses_cache(self, mock_fetch):
        mock_fetch.side_effect = _yahoo_side_effect
        first = self.provider.get_vix_term()
        mock_fetch.reset_mock()
        second = self.provider.get_vix_term()
        self.assertEqual(first, second)
        mock_fetch.assert_not_called()

    @patch("quant_nanggroe.providers.tradebobby.macro_pulse_provider._fetch_yahoo")
    def test_different_methods_have_independent_cache_keys(self, mock_fetch):
        mock_fetch.side_effect = _yahoo_side_effect
        vix = self.provider.get_vix_term()
        yc = self.provider.get_yield_curve()
        self.assertNotEqual(vix, yc)


if __name__ == "__main__":
    unittest.main(verbosity=2)
