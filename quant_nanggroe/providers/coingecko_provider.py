"""
CoinGecko Klines Provider (backward-compat cached version)
===========================================================
"""

import time
import json
import logging
from typing import Dict, List, Optional
from pathlib import Path

log = logging.getLogger("QNA.CoinGecko")

_klines_cache: Dict[str, tuple] = {}
CACHE_TTL = 30


def get_klines_cached(symbol: str, limit: int = 100) -> List[Dict]:
    import ssl, urllib.request
    from datetime import datetime

    now = time.time()
    cache_key = f"{symbol}_{limit}"
    if cache_key in _klines_cache:
        data, ts = _klines_cache[cache_key]
        if now - ts < CACHE_TTL:
            return data

    cg_id_map = {
        "BTCUSDT": "bitcoin", "ETHUSDT": "ethereum", "SOLUSDT": "solana",
        "BNBUSDT": "binancecoin", "AVAXUSDT": "avalanche-2",
        "LINKUSDT": "chainlink", "MATICUSDT": "matic-network",
        "DOTUSDT": "polkadot", "ADAUSDT": "cardano", "XRPUSDT": "ripple",
    }
    cg_id = cg_id_map.get(symbol)
    if not cg_id:
        return []

    url = (f"https://api.coingecko.com/api/v3/coins/{cg_id}"
           f"/market_chart?vs_currency=usd&days=1")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "QNA/1.0"})
        with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
            data = json.loads(r.read().decode())

        prices = data.get("prices", [])
        if not prices:
            return []

        candles = []
        for p in prices:
            ts = int(p[0] / 1000)
            price = p[1]
            candles.append({
                "timestamp": ts, "open": price, "high": price,
                "low": price, "close": price, "volume": 0,
            })

        step = max(1, len(candles) // limit)
        result = candles[::step]
        _klines_cache[cache_key] = (result, now)
        return result
    except Exception as e:
        log.debug(f"CoinGecko klines {symbol}: {e}")
        return []
