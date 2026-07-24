"""
COT (Commitment of Traders) data provider.

Minimal functional stub: returns neutral positioning so strategies that
depend on COT don't crash the pipeline when CFTC data isn't wired yet.
Real CFTC fetch can be dropped in later without changing the interface.

// ponytail: CFTC publishes weekly COT data at:
//   https://www.cftc.gov/dea/futures/deacmxsf.htm  (legacy TXT)
//   https://www.cftc.gov/MarketReports/CommitmentsofTraders/  (portal)
// Alternative: Quandl/Barchart/Investing.com APIs.
// Parse the TXT with pandas.read_fwf() — format is fixed-width per
// legacy legacy_cftc_cot.pdf spec.  Use cot_reports (PyPI) as a
// ready-made wrapper: pip install cot_reports
"""


class COTProvider:
    """Provides COT positioning data for futures/forex strategies."""

    def fetch(self) -> dict:
        # ponytail: neutral stub — real CFTC pull replaces this; interface stable
        self._data = {
            "net_position": 0.0,
            "percentile": 0.5,
            "sentiment": "neutral",
            "source": "stub",
        }
        return self._data

    def get_positioning(self, symbol: str) -> dict:
        return {**getattr(self, "_data", {}), "symbol": symbol}

    def get_extreme_readings(self) -> list:
        return []


class COTAnalyzer:
    """Analyze COT positioning into trading signals."""

    def __init__(self, provider: COTProvider | None = None):
        self._provider = provider or COTProvider()

    def analyze(self, symbol: str) -> dict:
        pos = self._provider.get_positioning(symbol)
        return {
            "symbol": symbol,
            "signal": "hold",
            "strength": 0.0,
            "detail": pos,
        }

    def generate_signal(self, symbol: str, price_series=None) -> dict:
        # ponytail: returns neutral so COTStrategy yields no signal (safe no-trade)
        return {
            "symbol": symbol,
            "signal": "neutral",
            "confidence": 0.0,
            "reasoning": "COT stub: neutral, no CFTC data wired",
        }


# Backwards-compatible alias used by fundamental/cot.py
COTDataProvider = COTProvider
