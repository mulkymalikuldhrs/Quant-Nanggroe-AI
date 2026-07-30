"""Tests: CryptoPulseProvider — Fear & Greed, dominance, funding rates.

Mocks _safe_fetch (module-level helper) to avoid the complexity of
mocking urllib.request.urlopen with its context manager protocol.
"""

from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from quant_nanggroe.providers.tradebobby.crypto_pulse_provider import (
    _CACHE,
    CryptoPulseProvider,
)

FNG_RESPONSE = {
    "data": [
        {"value": "25", "value_classification": "Fear", "timestamp": "1743206400"},
        {"value": "30", "value_classification": "Fear", "timestamp": "1743120000"},
        {"value": "35", "value_classification": "Fear", "timestamp": "1743033600"},
        {"value": "40", "value_classification": "Fear", "timestamp": "1742947200"},
        {"value": "28", "value_classification": "Fear", "timestamp": "1742860800"},
        {"value": "32", "value_classification": "Fear", "timestamp": "1742774400"},
        {"value": "38", "value_classification": "Fear", "timestamp": "1742688000"},
        {"value": "42", "value_classification": "Fear", "timestamp": "1742601600"},
    ]
}

COINGECKO_RESPONSE = {
    "data": {
        "active_cryptocurrencies": 12534,
        "market_cap_percentage": {"btc": 55.23, "eth": 12.84},
        "total_market_cap": {"usd": 2560000000000},
        "total_volume": {"usd": 82500000000},
        "market_cap_change_percentage_24h_usd": 3.12,
    }
}

BINANCE_RESPONSE = [
    {"symbol": "BTCUSDT", "markPrice": "65400.00", "indexPrice": "65380.00",
     "lastFundingRate": "0.00012", "nextFundingTime": 1743321600000},
    {"symbol": "ETHUSDT", "markPrice": "3450.00", "indexPrice": "3448.50",
     "lastFundingRate": "0.00008", "nextFundingTime": 1743321600000},
    {"symbol": "SOLUSDT", "markPrice": "142.50", "indexPrice": "142.30",
     "lastFundingRate": "-0.00005", "nextFundingTime": 1743321600000},
    {"symbol": "XRPUSDT", "markPrice": "0.62", "indexPrice": "0.6195",
     "lastFundingRate": "0.00001", "nextFundingTime": 1743321600000},
    {"symbol": "SOMEUSDT", "markPrice": "1.00", "indexPrice": "0.99",
     "lastFundingRate": "0.00500", "nextFundingTime": 1743321600000},
    {"symbol": "LOWUSDT", "markPrice": "1.00", "indexPrice": "0.99",
     "lastFundingRate": "-0.00300", "nextFundingTime": 1743321600000},
]


class TestCryptoPulseProviderInit(unittest.TestCase):
    """Provider construction."""

    def setUp(self):
        _CACHE.clear()
        self.provider = CryptoPulseProvider()

    def test_provider_initialises(self):
        self.assertIsInstance(self.provider, CryptoPulseProvider)

    def test_cache_is_wired(self):
        from quant_nanggroe.providers.tradebobby.crypto_pulse_provider import _CACHE as module_cache
        self.assertIs(self.provider._cache, module_cache)


class TestFearGreed(unittest.TestCase):
    """get_fear_greed() behaviour."""

    def setUp(self):
        _CACHE.clear()
        self.provider = CryptoPulseProvider()

    @patch("quant_nanggroe.providers.tradebobby.crypto_pulse_provider._safe_fetch")
    def test_get_fear_greed_returns_value_and_classification(self, mock_fetch):
        mock_fetch.return_value = FNG_RESPONSE
        result = self.provider.get_fear_greed()
        self.assertIsNotNone(result)
        self.assertIn("current", result)
        self.assertIn("classification", result)
        self.assertEqual(result["current"], 25)
        self.assertEqual(result["classification"], "Fear")

    @patch("quant_nanggroe.providers.tradebobby.crypto_pulse_provider._safe_fetch")
    def test_get_fear_greed_includes_change(self, mock_fetch):
        mock_fetch.return_value = FNG_RESPONSE
        result = self.provider.get_fear_greed()
        self.assertIn("change_1d", result)
        self.assertIn("change_7d", result)
        self.assertEqual(result["change_1d"], -5)

    @patch("quant_nanggroe.providers.tradebobby.crypto_pulse_provider._safe_fetch")
    def test_get_fear_greed_includes_history(self, mock_fetch):
        mock_fetch.return_value = FNG_RESPONSE
        result = self.provider.get_fear_greed()
        self.assertIn("history", result)
        self.assertEqual(len(result["history"]), 8)

    @patch("quant_nanggroe.providers.tradebobby.crypto_pulse_provider._safe_fetch")
    def test_get_fear_greed_returns_none_on_bad_api(self, mock_fetch):
        mock_fetch.return_value = None
        result = self.provider.get_fear_greed()
        self.assertIsNone(result)

    @patch("quant_nanggroe.providers.tradebobby.crypto_pulse_provider._safe_fetch")
    def test_get_fear_greed_returns_none_on_empty_data(self, mock_fetch):
        mock_fetch.return_value = {"data": []}
        result = self.provider.get_fear_greed()
        self.assertIsNone(result)


class TestDominance(unittest.TestCase):
    """get_dominance() behaviour."""

    def setUp(self):
        _CACHE.clear()
        self.provider = CryptoPulseProvider()

    @patch("quant_nanggroe.providers.tradebobby.crypto_pulse_provider._safe_fetch")
    def test_get_dominance_returns_btc_eth_pct(self, mock_fetch):
        mock_fetch.return_value = COINGECKO_RESPONSE
        result = self.provider.get_dominance()
        self.assertIsNotNone(result)
        self.assertIn("btc_dominance", result)
        self.assertIn("eth_dominance", result)
        self.assertEqual(result["btc_dominance"], 55.23)
        self.assertEqual(result["eth_dominance"], 12.84)

    @patch("quant_nanggroe.providers.tradebobby.crypto_pulse_provider._safe_fetch")
    def test_get_dominance_includes_market_stats(self, mock_fetch):
        mock_fetch.return_value = COINGECKO_RESPONSE
        result = self.provider.get_dominance()
        self.assertIn("total_mcap_usd", result)
        self.assertIn("total_volume_usd", result)
        self.assertIn("mcap_change_24h", result)
        self.assertIn("active_cryptos", result)

    @patch("quant_nanggroe.providers.tradebobby.crypto_pulse_provider._safe_fetch")
    def test_get_dominance_returns_none_on_api_failure(self, mock_fetch):
        mock_fetch.return_value = None
        result = self.provider.get_dominance()
        self.assertIsNone(result)


class TestFundingRates(unittest.TestCase):
    """get_funding_rates() behaviour."""

    def setUp(self):
        _CACHE.clear()
        self.provider = CryptoPulseProvider()

    @patch("quant_nanggroe.providers.tradebobby.crypto_pulse_provider._safe_fetch")
    def test_get_funding_rates_returns_tracked(self, mock_fetch):
        mock_fetch.return_value = BINANCE_RESPONSE
        result = self.provider.get_funding_rates()
        self.assertIsNotNone(result)
        self.assertIn("tracked", result)
        tracked = result["tracked"]
        self.assertIn("BTCUSDT", tracked)
        self.assertEqual(tracked["BTCUSDT"]["funding_pct"], 0.012)

    @patch("quant_nanggroe.providers.tradebobby.crypto_pulse_provider._safe_fetch")
    def test_get_funding_rates_includes_top_long_short(self, mock_fetch):
        mock_fetch.return_value = BINANCE_RESPONSE
        result = self.provider.get_funding_rates()
        self.assertIn("top_long", result)
        self.assertIn("top_short", result)
        self.assertGreater(len(result["top_long"]), 0)
        self.assertGreater(len(result["top_short"]), 0)

    @patch("quant_nanggroe.providers.tradebobby.crypto_pulse_provider._safe_fetch")
    def test_get_funding_rates_returns_none_for_non_list(self, mock_fetch):
        mock_fetch.return_value = {"error": "not an array"}
        result = self.provider.get_funding_rates()
        self.assertIsNone(result)


class TestCryptoPulse(unittest.TestCase):
    """get_crypto_pulse() combined output."""

    def setUp(self):
        _CACHE.clear()
        self.provider = CryptoPulseProvider()

    @patch("quant_nanggroe.providers.tradebobby.crypto_pulse_provider._safe_fetch")
    def test_get_crypto_pulse_returns_combined_dict(self, mock_fetch):
        mock_fetch.side_effect = [FNG_RESPONSE, COINGECKO_RESPONSE, BINANCE_RESPONSE]
        result = self.provider.get_crypto_pulse()
        self.assertIn("fear_greed", result)
        self.assertIn("dominance", result)
        self.assertIn("funding", result)
        self.assertIn("regime", result)
        self.assertIn("signal", result)
        self.assertIn("funding_signal", result)
        self.assertIn("timestamp", result)

    @patch("quant_nanggroe.providers.tradebobby.crypto_pulse_provider._safe_fetch")
    def test_get_crypto_pulse_regime_extreme_fear(self, mock_fetch):
        fear_data = {"data": [{"value": "15", "value_classification": "Extreme Fear",
                                "timestamp": "1743206400"}]}
        mock_fetch.side_effect = [fear_data, COINGECKO_RESPONSE, BINANCE_RESPONSE]
        result = self.provider.get_crypto_pulse()
        self.assertEqual(result["regime"], "EXTREME-FEAR")
        self.assertIn("Contrarian LONG", result["signal"])

    @patch("quant_nanggroe.providers.tradebobby.crypto_pulse_provider._safe_fetch")
    def test_get_crypto_pulse_regime_extreme_greed(self, mock_fetch):
        greed_data = {"data": [{"value": "85", "value_classification": "Extreme Greed",
                                 "timestamp": "1743206400"}]}
        mock_fetch.side_effect = [greed_data, COINGECKO_RESPONSE, BINANCE_RESPONSE]
        result = self.provider.get_crypto_pulse()
        self.assertEqual(result["regime"], "EXTREME-GREED")
        self.assertIn("Contrarian SHORT", result["signal"])


class TestCacheBehavior(unittest.TestCase):
    """TTLCache returns cached result on second call."""

    def setUp(self):
        _CACHE.clear()
        self.provider = CryptoPulseProvider()

    @patch("quant_nanggroe.providers.tradebobby.crypto_pulse_provider._safe_fetch")
    def test_get_fear_greed_caches(self, mock_fetch):
        mock_fetch.return_value = FNG_RESPONSE
        first = self.provider.get_fear_greed()
        mock_fetch.reset_mock()
        second = self.provider.get_fear_greed()
        self.assertEqual(first, second)
        mock_fetch.assert_not_called()

    @patch("quant_nanggroe.providers.tradebobby.crypto_pulse_provider._safe_fetch")
    def test_get_dominance_caches(self, mock_fetch):
        mock_fetch.return_value = COINGECKO_RESPONSE
        first = self.provider.get_dominance()
        mock_fetch.reset_mock()
        second = self.provider.get_dominance()
        self.assertEqual(first, second)
        mock_fetch.assert_not_called()

    @patch("quant_nanggroe.providers.tradebobby.crypto_pulse_provider._safe_fetch")
    def test_get_crypto_pulse_caches_sub_calls(self, mock_fetch):
        mock_fetch.return_value = FNG_RESPONSE
        self.provider.get_fear_greed()
        mock_fetch.reset_mock()
        result = self.provider.get_fear_greed()
        self.assertIsNotNone(result)
        mock_fetch.assert_not_called()


class TestGracefulDegradation(unittest.TestCase):
    """Provider never crashes on API failures."""

    def setUp(self):
        _CACHE.clear()
        self.provider = CryptoPulseProvider()

    @patch("quant_nanggroe.providers.tradebobby.crypto_pulse_provider._safe_fetch")
    def test_get_crypto_pulse_graceful_on_all_failures(self, mock_fetch):
        mock_fetch.return_value = None
        result = self.provider.get_crypto_pulse()
        self.assertIsNotNone(result)
        self.assertIn("regime", result)
        self.assertEqual(result["regime"], "NEUTRAL")
        self.assertIsNone(result["fear_greed"])
        self.assertIsNone(result["dominance"])
        self.assertIsNone(result["funding"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
