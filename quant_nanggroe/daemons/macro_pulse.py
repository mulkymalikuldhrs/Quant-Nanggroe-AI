# Macro Pulse Daemon — Fetches macro market data from Yahoo Finance
# Ported from TradeBobbyTerminal/dashboard/macro-pulse.js

import json
import time
import logging
from pathlib import Path
from datetime import datetime

try:
    import yfinance as yf
except ImportError:
    yf = None

logger = logging.getLogger(__name__)

# Yahoo Finance tickers for macro dashboard
MACRO_TICKERS = {
    "DXY": "DX-Y.NYB",
    "VIX": "^VIX",
    "US10Y": "^TNX",
    "US13W": "^IRX",
    "SPX": "^GSPC",
    "NAS": "^IXIC",
    "DJI": "^DJI",
    "GOLD": "GC=F",
    "SILVER": "SI=F",
    "WTI": "CL=F",
    "BRENT": "BZ=F",
    "COPPER": "HG=F",
}

# Sector ETFs
SECTOR_ETFS = {
    "XLK": "Technology",
    "XLF": "Financials",
    "XLV": "Healthcare",
    "XLE": "Energy",
    "XLY": "Consumer Disc",
    "XLP": "Consumer Staples",
    "XLI": "Industrials",
    "XLU": "Utilities",
    "XLRE": "Real Estate",
    "XLB": "Materials",
    "XLC": "Communication",
}

# Mag-7 / Tech Giants
MAG7_TICKERS = {
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "GOOGL": "Alphabet",
    "AMZN": "Amazon",
    "NVDA": "NVIDIA",
    "META": "Meta",
    "TSLA": "Tesla",
}


class MacroPulseDaemon:
    """Fetches macro market data every 5 minutes."""

    def __init__(self, data_dir: str = "data/macro"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.running = False

    def fetch_macro_data(self) -> dict:
        """Fetch all macro tickers from Yahoo Finance."""
        if yf is None:
            raise RuntimeError("yfinance not installed. Run: pip install yfinance")

        results = {}
        all_tickers = {**MACRO_TICKERS, **{k: k for k in SECTOR_ETFS}, **MAG7_TICKERS}

        try:
            tickers = yf.Tickers(" ".join(all_tickers.values()))
            for symbol, yf_symbol in all_tickers.items():
                try:
                    info = tickers.tickers[yf_symbol].fast_info
                    results[symbol] = {
                        "price": float(info.last_price) if hasattr(info, "last_price") else 0,
                        "change_pct": float(info.last_price / info.previous_close - 1) * 100 if hasattr(info, "last_price") and hasattr(info, "previous_close") and info.previous_close else 0,
                        "name": MACRO_TICKERS.get(symbol) or SECTOR_ETFS.get(symbol) or MAG7_TICKERS.get(symbol, symbol),
                    }
                except Exception as e:
                    logger.debug(f"Failed to fetch {symbol}: {e}")
                    results[symbol] = {"price": 0, "change_pct": 0, "name": symbol}
        except Exception as e:
            logger.error(f"Failed to fetch macro data: {e}")
            raise

        return results

    def calculate_regime(self, data: dict) -> dict:
        """Calculate market regime from macro data."""
        vix = data.get("VIX", {}).get("price", 15)
        dxy = data.get("DXY", {}).get("price", 104)
        gold = data.get("GOLD", {}).get("price", 2400)
        spx_change = data.get("SPX", {}).get("change_pct", 0)

        risk_score = 50
        if vix > 25:
            risk_score += 20
        elif vix < 15:
            risk_score -= 15
        if spx_change < -1:
            risk_score += 15
        elif spx_change > 1:
            risk_score -= 10
        risk_score = max(0, min(100, risk_score))

        if risk_score < 35:
            regime = "RISK-ON"
        elif risk_score > 65:
            regime = "RISK-OFF"
        else:
            regime = "MIXED"

        return {
            "regime": regime,
            "risk_index": risk_score,
            "vix": vix,
            "dxy": dxy,
            "gold": gold,
            "timestamp": datetime.now().isoformat(),
        }

    def run_once(self) -> dict:
        """Run one data fetch cycle."""
        logger.info("Fetching macro pulse data...")
        data = self.fetch_macro_data()
        regime = self.calculate_regime(data)

        output = {
            "macro": data,
            "regime": regime,
            "updated_at": datetime.now().isoformat(),
        }

        # Save to file
        out_file = self.data_dir / "macro_pulse.json"
        out_file.write_text(json.dumps(output, indent=2))
        logger.info(f"Macro pulse data saved to {out_file}")

        return output

    def run_loop(self, interval_minutes: int = 5):
        """Run daemon in a loop."""
        self.running = True
        logger.info(f"Macro Pulse daemon started (interval: {interval_minutes}m)")

        while self.running:
            try:
                self.run_once()
            except Exception as e:
                logger.error(f"Macro pulse error: {e}")
            time.sleep(interval_minutes * 60)

    def stop(self):
        """Stop the daemon loop."""
        self.running = False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    daemon = MacroPulseDaemon()
    result = daemon.run_once()
    print(json.dumps(result, indent=2))
