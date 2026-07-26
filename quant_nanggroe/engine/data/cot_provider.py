import logging

logger = logging.getLogger(__name__)


class COTDataNotAvailableError(RuntimeError):
    """Raised when COT data is requested but no CFTC data source is configured."""


class COTProvider:
    def __init__(self, data_source: str | None = None):
        if data_source is None:
            raise COTDataNotAvailableError(
                "COTProvider: no data source configured. "
                "Set COT_DATA_SOURCE env var to one of: cftc, barchart, investing, quandl. "
                "CFTC URL: https://www.cftc.gov/dea/futures/deacmxsf.htm"
            )
        self._data_source = data_source
        self._data: dict = {}

    def fetch(self) -> dict:
        raise NotImplementedError(
            f"COT fetch not implemented for source={self._data_source}. "
            "Install cot_reports (pip install cot_reports) or implement CFTC parser."
        )

    def get_positioning(self, symbol: str) -> dict:
        if not self._data:
            raise COTDataNotAvailableError(f"COT data not loaded for {symbol}. Call fetch() first or configure data source.")
        return {**self._data, "symbol": symbol}

    def get_extreme_readings(self) -> list:
        return []


class COTAnalyzer:
    def __init__(self, provider: COTProvider | None = None):
        if provider is None:
            raise COTDataNotAvailableError(
                "COTAnalyzer: no provider configured. "
                "Pass a COTProvider with a real data source."
            )
        self._provider = provider

    def analyze(self, symbol: str) -> dict:
        pos = self._provider.get_positioning(symbol)
        return {"symbol": symbol, "signal": "hold", "strength": 0.0, "detail": pos}

    def generate_signal(self, symbol: str, price_series=None) -> dict:
        return {"symbol": symbol, "signal": "neutral", "confidence": 0.0, "reasoning": "COT data not available"}


COTDataProvider = COTProvider
