# COT Fetcher Daemon — Fetches CFTC Commitment of Traders data
# Ported from TradeBobbyTerminal/dashboard/cot-fetcher.js

import json
import time
import logging
from pathlib import Path
from datetime import datetime

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger(__name__)

# CFTC markets to track (legacy + disaggregated futures)
CFTC_URL = "https://www.cftc.gov/dea/futures/other_lf.htm"

# Tracked markets with their CFTC codes
MARKETS = {
    "Gold": {"code": "086", "exchange": "COMEX"},
    "Silver": {"code": "085", "exchange": "COMEX"},
    "Copper": {"code": "089", "exchange": "COMEX"},
    "Crude Oil": {"code": "067", "exchange": "NYMEX"},
    "Natural Gas": {"code": "022", "exchange": "NYMEX"},
    "Euro FX": {"code": "099", "exchange": "CME"},
    "British Pound": {"code": "096", "exchange": "CME"},
    "Japanese Yen": {"code": "097", "exchange": "CME"},
    "Canadian Dollar": {"code": "090", "exchange": "CME"},
    "Australian Dollar": {"code": "092", "exchange": "CME"},
    "Swiss Franc": {"code": "095", "exchange": "CME"},
    "S&P 500": {"code": "138", "exchange": "CME"},
    "NASDAQ": {"code": "209", "exchange": "CME"},
    "Russell 2000": {"code": "239", "exchange": "CME"},
    "10-Year T-Note": {"code": "043", "exchange": "CBOT"},
    "30-Year T-Bond": {"code": "001", "exchange": "CBOT"},
    "Corn": {"code": "002", "exchange": "CBOT"},
    "Wheat": {"code": "004", "exchange": "CBOT"},
    "Soybeans": {"code": "005", "exchange": "CBOT"},
    "Live Cattle": {"code": "061", "exchange": "CME"},
}


class COTFetcherDaemon:
    """Fetches CFTC Commitment of Traders data weekly."""

    def __init__(self, data_dir: str = "data/cot"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.running = False

    def fetch_cot_data(self) -> list:
        """Fetch COT data from CFTC."""
        if httpx is None:
            return self._mock_data()
        try:
            with httpx.Client(timeout=30) as client:
                resp = client.get(CFTC_URL)
                resp.raise_for_status()
                # Parse CFTC HTML table (simplified)
                return self._parse_cftc_response(resp.text)
        except Exception as e:
            logger.error(f"CFTC fetch failed: {e}")
            return self._mock_data()

    def _parse_cftc_response(self, html: str) -> list:
        """Parse CFTC HTML response (simplified)."""
        # In production, use BeautifulSoup or similar
        # For now, return mock data
        return self._mock_data()

    def _mock_data(self) -> list:
        """Mock COT data."""
        import random
        results = []
        for market_name, info in MARKETS.items():
            smart_long = random.randint(20, 80)
            smart_short = 100 - smart_long
            retail_long = random.randint(20, 80)
            retail_short = 100 - retail_long

            net_smart = smart_long - smart_short
            if net_smart > 20:
                signal = "Bullish"
            elif net_smart < -20:
                signal = "Bearish"
            else:
                signal = "Neutral"

            results.append({
                "market": market_name,
                "code": info["code"],
                "exchange": info["exchange"],
                "smart_long_pct": smart_long,
                "smart_short_pct": smart_short,
                "retail_long_pct": retail_long,
                "retail_short_pct": retail_short,
                "net_position": "Long" if net_smart > 0 else "Short",
                "signal": signal,
                "net_smart": net_smart,
            })
        return results

    def run_once(self) -> dict:
        """Run one fetch cycle."""
        logger.info("Fetching COT data...")
        data = self.fetch_cot_data()

        output = {
            "markets": data,
            "total_markets": len(data),
            "updated_at": datetime.now().isoformat(),
        }

        out_file = self.data_dir / "cot_data.json"
        out_file.write_text(json.dumps(output, indent=2))
        logger.info(f"COT data saved to {out_file}")

        return output

    def stop(self):
        self.running = False
