import unittest, os, sys
# Ensure repository root is on the import path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(repo_root)
from quant_nanggroe.engine_bridge import EnginePriceProvider

class TestEnginePriceProvider(unittest.TestCase):
    def setUp(self):
        # Use short cache TTL for test speed
        self.provider = EnginePriceProvider(cache_ttl=30)

    def test_get_all_prices_returns_dict_and_contains_known_symbol(self):
        # Force fresh fetch to avoid relying on cache
        prices = self.provider.get_all_prices(force=True)
        self.assertIsInstance(prices, dict, "Prices should be a dict")
        # Expect at least one of the main symbols to be present
        known_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        self.assertTrue(any(sym in prices for sym in known_symbols),
                        f"At least one known symbol {known_symbols} should be in prices")

if __name__ == "__main__":
    unittest.main()
