"""
FRED (Federal Reserve Economic Data) Provider.

Downloads macroeconomic time series from FRED API.
Requires FRED_API_KEY environment variable or configured key.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

# Known FRED series identifiers
FRED_SERIES_MAP: Dict[str, str] = {
    "GDP": "GDP",
    "UNRATE": "UNRATE",
    "CPIAUCSL": "CPIAUCSL",
    "FEDFUNDS": "FEDFUNDS",
    "DGS10": "DGS10",
    "DGS2": "DGS2",
    "SP500": "SP500",
    "T10Y2Y": "T10Y2Y",
    "USREC": "USREC",
    "M2SL": "M2SL",
}

FRED_API_BASE = "https://api.stlouisfed.org/fred"
FRED_API_KEY: str = os.environ.get("FRED_API_KEY", "REDACTED")


class FREDError(Exception):
    """Base exception for FRED provider errors."""

    pass


def _parse_symbol(symbol: str) -> Tuple[str, Dict[str, str]]:
    """Parse a symbol string into series_id and additional parameters.

    Supports format: FRED:SERIES_ID or SERIES_ID or SERIES_ID?param=val&...
    Strips 'FRED:' prefix if present.
    """
    raw = symbol
    if raw.upper().startswith("FRED:"):
        raw = raw[5:]
    if "?" in raw:
        series_id, query = raw.split("?", 1)
        params = dict(q.split("=") for q in query.split("&"))
        return series_id.upper(), params
    return raw.upper(), {}


FRED_CACHE: Dict[str, Any] = {}


class FREDProvider:
    """Provider for FRED economic data."""

    BASE_URL = FRED_API_BASE

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or FRED_API_KEY
        if not self.api_key or self.api_key == "REDACTED":
            logger.warning(
                "FRED_API_KEY not configured; set FRED_API_KEY env var"
            )

    async def get_series(
        self,
        series_id: str,
        observation_start: Optional[str] = None,
        observation_end: Optional[str] = None,
        frequency: Optional[str] = None,
        units: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch observations for a FRED series."""
        url = self._build_url(
            "series/observations",
            series_id=series_id,
            observation_start=observation_start,
            observation_end=observation_end,
            frequency=frequency,
            units=units,
        )

        data = await self._request(url)  # ponytail: extracted for testability
        if "observations" not in data:
            raise FREDError(
                f"FRED API returned no observations for {series_id}: {data.get('error_message', 'unknown error')}"
            )

        return data["observations"]

    async def _request(self, url: str) -> Dict[str, Any]:  # ponytail: hook for tests to mock
        """Execute the HTTP request and return parsed JSON."""
        try:
            req = Request(url)
            with urlopen(req) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            raise FREDError(f"HTTP request failed: {e}") from e

    def _build_url(
        self, endpoint: str, **params: Optional[str]
    ) -> str:
        query = {
            "api_key": self.api_key or FRED_API_KEY,
            "file_type": "json",
        }
        for k, v in params.items():
            if v is not None:
                query[k] = v
        return f"{self.BASE_URL}/{endpoint}?{urlencode(query)}"
