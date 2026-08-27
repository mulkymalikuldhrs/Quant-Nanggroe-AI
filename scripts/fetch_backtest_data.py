#!/usr/bin/env python3
"""Fetch historical daily OHLCV data via Bybit CDN bypass for backtesting."""

import json
import sys
import time
from pathlib import Path
from typing import Dict, List

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from quant_nanggroe.engine_bridge import DNSBypass, ExchangeBypassProvider

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]
DATA_DIR = REPO / "quant_nanggroe" / "data" / "backtest"
DATA_DIR.mkdir(parents=True, exist_ok=True)

exchange = ExchangeBypassProvider(cache_ttl=60)

def fetch_daily_klines(symbol: str, limit: int = 365) -> List[Dict]:
    """Fetch daily klines from Bybit via CDN bypass."""
    exchange._refresh_dns()
    for ip in exchange._bybit_ips:
        data = DNSBypass._raw_https(
            ip, exchange.BYBIT_CDN_CNAME, exchange.BYBIT_HOST,
            f"/v5/market/kline?category=spot&symbol={symbol}&interval=D&limit={limit}"
        )
        if data and data.get("retCode") == 0:
            raw = data["result"].get("list", [])
            candles = []
            for r in raw:
                candles.append({
                    "timestamp": int(r[0]),
                    "open": float(r[1]), "high": float(r[2]),
                    "low": float(r[3]), "close": float(r[4]),
                    "volume": float(r[5]),
                    "date": time.strftime("%Y-%m-%d", time.gmtime(int(r[0]) / 1000)),
                })
            # Bybit returns newest first, reverse to chronological
            candles.reverse()
            return candles
    # Fallback: try with smaller limit to debug
    print("  Bybit CDN failed, trying smaller limit=200...")
    for ip in exchange._bybit_ips:
        data = DNSBypass._raw_https(
            ip, exchange.BYBIT_CDN_CNAME, exchange.BYBIT_HOST,
            f"/v5/market/kline?category=spot&symbol={symbol}&interval=D&limit=200"
        )
        if data and data.get("retCode") == 0:
            raw = data["result"].get("list", [])
            candles = []
            for r in raw:
                candles.append({
                    "timestamp": int(r[0]),
                    "open": float(r[1]), "high": float(r[2]),
                    "low": float(r[3]), "close": float(r[4]),
                    "volume": float(r[5]),
                    "date": time.strftime("%Y-%m-%d", time.gmtime(int(r[0]) / 1000)),
                })
            candles.reverse()
            return candles
    return []

def main():
    for symbol in SYMBOLS:
        path = DATA_DIR / f"{symbol}_daily.json"
        if path.exists():
            print(f"{symbol}: cached ({path.stat().st_size} bytes)")
            continue
        print(f"{symbol}: fetching daily data from Bybit...")
        candles = fetch_daily_klines(symbol, limit=365)
        if candles:
            path.write_text(json.dumps(candles, indent=2))
            print(f"  {len(candles)} daily candles ({candles[0]['date']} to {candles[-1]['date']})")
            # Print price range
            closes = [c["close"] for c in candles]
            print(f"  Price range: ${min(closes):.2f} - ${max(closes):.2f}")
        else:
            print("  FAILED")
        time.sleep(0.5)

if __name__ == "__main__":
    main()
