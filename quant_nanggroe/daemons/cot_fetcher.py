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
    """Fetches CFTC Commitment of Traders data weekly.

    Delegates to the real engine/cot/ COTFetcher (cot_reports-based)
    instead of scraping CFTC HTML directly.
    """

    def __init__(self, data_dir: str = "data/cot"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.running = False

    def fetch_cot_data(self) -> list:
        """Fetch COT data via the real engine/cot/ COTFetcher."""
        try:
            from quant_nanggroe.engine.cot import COTFetcher as RealCOTFetcher
            fetcher = RealCOTFetcher()
            df = fetcher.fetch()
            if df.empty:
                logger.warning("COTFetcher returned empty data")
                return []
            # Convert DataFrame rows to list of dicts for JSON serialization
            return df.tail(50).to_dict(orient="records")
        except ImportError:
            logger.error("engine.cot not available — install cot_reports")
            raise
        except Exception as e:
            logger.error(f"COT fetch failed: {e}")
            raise

    def _parse_cftc_response(self, html: str) -> list:
        """Deprecated — COT fetching now uses cot_reports via engine/cot/."""
        logger.warning("_parse_cftc_response is deprecated; using engine/cot/ COTFetcher instead")
        return self.fetch_cot_data()

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
