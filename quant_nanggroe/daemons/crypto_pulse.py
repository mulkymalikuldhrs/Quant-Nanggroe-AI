# Crypto Pulse Daemon — Fetches crypto market data
# Ported from TradeBobbyTerminal/dashboard/crypto-pulse.js

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

# Tracked crypto symbols
CRYPTO_SYMBOLS = ["bitcoin", "ethereum", "solana", "binancecoin", "ripple", "dogecoin", "cardano", "avalanche-2"]
CRYPTO_MAP = {
    "bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL", "binancecoin": "BNB",
    "ripple": "XRP", "dogecoin": "DOGE", "cardano": "ADA", "avalanche-2": "AVAX",
}

# Fear & Greed Index
FNG_URL = "https://api.alternative.me/fng/?limit=1"

# CoinGecko
COINGECKO_URL = "https://api.coingecko.com/api/v3/coins/markets"
COINGECKO_PARAMS = {
    "vs_currency": "usd",
    "ids": ",".join(CRYPTO_SYMBOLS),
    "order": "market_cap_desc",
    "sparkline": "false",
    "price_change_percentage": "24h",
}

# Binance funding rates (perpetual futures)
BINANCE_FAPI = "https://fapi.binance.com"
BINANCE_FUNDING_URL = f"{BINANCE_FAPI}/fapi/v1/premiumIndex"


class CryptoPulseDaemon:
    """Fetches crypto market data every 5 minutes."""

    def __init__(self, data_dir: str = "data/crypto"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.running = False

    async def fetch_coingecko(self) -> list:
        """Fetch crypto prices from CoinGecko."""
        if httpx is None:
            return self._mock_prices()
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(COINGECKO_URL, params=COINGECKO_PARAMS)
                resp.raise_for_status()
                data = resp.json()
                return [
                    {
                        "id": c["id"],
                        "symbol": CRYPTO_MAP.get(c["id"], c["symbol"].upper()),
                        "price": c["current_price"],
                        "change_24h": c.get("price_change_percentage_24h", 0) or 0,
                        "market_cap": c.get("market_cap", 0),
                        "volume_24h": c.get("total_volume", 0),
                    }
                    for c in data
                ]
        except Exception as e:
            logger.error(f"CoinGecko fetch failed: {e}")
            return self._mock_prices()

    async def fetch_funding_rates(self) -> dict:
        """Fetch Binance perpetual funding rates."""
        if httpx is None:
            return {}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(BINANCE_FUNDING_URL)
                resp.raise_for_status()
                data = resp.json()
                rates = {}
                for item in data:
                    symbol = item.get("symbol", "")
                    # Filter to tracked perpetuals
                    for cid, csym in CRYPTO_MAP.items():
                        if symbol.startswith(csym) and symbol.endswith("USDT"):
                            rates[csym] = {
                                "funding_rate": float(item.get("lastFundingRate", 0)),
                                "mark_price": float(item.get("markPrice", 0)),
                                "index_price": float(item.get("indexPrice", 0)),
                            }
                return rates
        except Exception as e:
            logger.error(f"Binance funding fetch failed: {e}")
            return {}

    async def fetch_fear_greed(self) -> dict:
        """Fetch Fear & Greed Index."""
        if httpx is None:
            return {"value": 50, "classification": "Neutral"}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(FNG_URL)
                resp.raise_for_status()
                data = resp.json()["data"][0]
                return {"value": int(data["value"]), "classification": data["value_classification"]}
        except Exception as e:
            logger.error(f"Fear & Greed fetch failed: {e}")
            return {"value": 50, "classification": "Neutral"}

    def _mock_prices(self) -> list:
        """Mock data when API unavailable."""
        import random
        return [
            {"id": cid, "symbol": csym, "price": random.uniform(100, 70000), "change_24h": random.uniform(-5, 5), "market_cap": 0, "volume_24h": 0}
            for cid, csym in CRYPTO_MAP.items()
        ]

    async def run_once(self) -> dict:
        """Run one fetch cycle."""
        logger.info("Fetching crypto pulse data...")
        prices = await self.fetch_coingecko()
        funding = await self.fetch_funding_rates()
        fng = await self.fetch_fear_greed()

        output = {
            "prices": prices,
            "funding_rates": funding,
            "fear_greed": fng,
            "updated_at": datetime.now().isoformat(),
        }

        out_file = self.data_dir / "crypto_pulse.json"
        out_file.write_text(json.dumps(output, indent=2))
        logger.info(f"Crypto pulse data saved to {out_file}")

        return output

    def run_sync(self) -> dict:
        """Synchronous wrapper for run_once."""
        import asyncio
        return asyncio.run(self.run_once())

    def stop(self):
        self.running = False
