"""
Macro & Economic Data Provider
===============================
FRED (Federal Reserve) API for macroeconomic indicators.
Free, unlimited, 800K+ series.
"""

import json
import logging
import os
import time
from typing import Dict, List, Optional

log = logging.getLogger("QNA.Macro")


class MacroProvider:
    FRED_KEY = os.environ.get("FRED_KEY", "")

    def __init__(self, api_key: str = None):
        self.api_key = api_key or self.FRED_KEY
        self.base = "https://api.stlouisfed.org/fred"
        self.last_call = 0

    def _rate_limit(self):
        elapsed = time.time() - self.last_call
        if elapsed < 0.5:
            time.sleep(0.5 - elapsed)
        self.last_call = time.time()

    def _get(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        import urllib.parse
        import urllib.request
        self._rate_limit()
        params = params or {}
        params.update({"api_key": self.api_key, "file_type": "json"})
        url = f"{self.base}/{endpoint}?{urllib.parse.urlencode(params)}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "QNA/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            log.debug(f"FRED {endpoint}: {e}")
            return None

    def get_series(self, series_id: str, limit: int = 1000) -> Optional[List[Dict]]:
        data = self._get("series/observations", {
            "series_id": series_id,
            "sort_order": "desc",
            "limit": limit,
        })
        if data and "observations" in data:
            obs = []
            for o in data["observations"]:
                val = o.get("value")
                if val and val != ".":
                    obs.append({
                        "date": o["date"],
                        "value": float(val),
                    })
            return obs
        return None

    def get_current_value(self, series_id: str) -> Optional[float]:
        obs = self.get_series(series_id, limit=1)
        if obs:
            return obs[0]["value"]
        return None

    def get_macro_snapshot(self) -> Dict:
        indicators = {
            "GDP": "GDP", "CPI": "CPIAUCSL", "UNEMPLOYMENT": "UNRATE",
            "FED_FUNDS": "FEDFUNDS", "SP500": "SP500",
        }
        result = {}
        for name, sid in indicators.items():
            val = self.get_current_value(sid)
            if val is not None:
                result[name] = val
        return result

    def is_available(self) -> bool:
        return bool(self.api_key)

    def __repr__(self):
        return f"MacroProvider(fred_key_set={bool(self.api_key)})"
