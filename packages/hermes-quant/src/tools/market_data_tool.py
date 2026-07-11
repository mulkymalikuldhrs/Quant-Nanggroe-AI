#!/usr/bin/env python3
"""
Market Data Agent (L1 - Data Layer)
Fetches OHLCV, economic calendar, market overview
"""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, List

logger = logging.getLogger("HermesQuantOS.MarketData")


class MarketDataTool:
    """L1 Agent: Market Data - Real-time and historical market data"""

    PROVIDERS = {
        "yfinance": True,  # Always available (free)
        "mt5": False,      # Requires MT5 terminal
        "oanda": False,    # Requires OANDA API key
        "binance": False,  # Requires Binance API key
    }

    # Symbol mapping for different providers
    SYMBOL_MAP = {
        "XAUUSD": {"yfinance": "GC=F", "mt5": "XAUUSD", "binance": "XAUUSDT"},
        "EURUSD": {"yfinance": "EURUSD=X", "mt5": "EURUSD", "binance": "EURUSDT"},
        "GBPUSD": {"yfinance": "GBPUSD=X", "mt5": "GBPUSD", "binance": "GBPUSDT"},
        "USDJPY": {"yfinance": "USDJPY=X", "mt5": "USDJPY", "binance": "USDJPY"},
        "BTCUSDT": {"yfinance": "BTC-USD", "mt5": None, "binance": "BTCUSDT"},
        "SHIB": {"yfinance": "SHIB-USD", "mt5": None, "binance": "SHIBUSDT"},
        "TRX": {"yfinance": "TRX-USD", "mt5": None, "binance": "TRXUSDT"},
    }

    INTERVAL_MAP = {
        "1m": {"yfinance": "1m", "mt5": "M1"},
        "5m": {"yfinance": "5m", "mt5": "M5"},
        "15m": {"yfinance": "15m", "mt5": "M15"},
        "1h": {"yfinance": "1h", "mt5": "H1"},
        "4h": {"yfinance": "4h", "mt5": "H4"},
        "1d": {"yfinance": "1d", "mt5": "D1"},
        "1w": {"yfinance": "1wk", "mt5": "W1"},
    }

    def __init__(self):
        self.cache = {}
        self.cache_duration = 60  # seconds
        self.last_fetch = {}

    def get_ohlcv(self, symbol: str = "XAUUSD", interval: str = "1h",
                  bars: int = 50) -> str:
        """
        Fetch OHLCV data for a symbol.

        Args:
            symbol: Trading symbol (XAUUSD, EURUSD, BTCUSDT, etc.)
            interval: Timeframe (1m, 5m, 15m, 1h, 4h, 1d, 1w)
            bars: Number of candles to fetch

        Returns:
            JSON string with OHLCV data
        """
        try:
            import yfinance as yf
            yf_symbol = self.SYMBOL_MAP.get(symbol, {}).get("yfinance", symbol)
            yf_interval = self.INTERVAL_MAP.get(interval, {}).get("yfinance", "1h")

            # yfinance has limits on intraday data range
            period = "60d"
            if interval in ["1m"]:
                period = "7d"
            elif interval in ["5m", "15m"]:
                period = "60d"
            elif interval in ["1h", "4h"]:
                period = "730d"

            ticker = yf.Ticker(yf_symbol)
            df = ticker.history(period=period, interval=yf_interval)

            if df.empty:
                return json.dumps({
                    "symbol": symbol,
                    "error": "No data returned",
                    "suggestion": f"Check if {symbol} is a valid symbol"
                })

            # Take last N bars
            df = df.tail(bars)

            result = {
                "symbol": symbol,
                "interval": interval,
                "bars": len(df),
                "last_update": str(df.index[-1]),
                "data": [{
                    "time": str(idx),
                    "open": round(float(row["Open"]), 5),
                    "high": round(float(row["High"]), 5),
                    "low": round(float(row["Low"]), 5),
                    "close": round(float(row["Close"]), 5),
                    "volume": int(row["Volume"]) if row["Volume"] > 0 else 0
                } for idx, row in df.iterrows()],
                "summary": {
                    "latest_close": round(float(df["Close"].iloc[-1]), 5),
                    "period_high": round(float(df["High"].max()), 5),
                    "period_low": round(float(df["Low"].min()), 5),
                    "avg_volume": round(float(df["Volume"].mean()), 0) if df["Volume"].mean() > 0 else "N/A"
                }
            }

            return json.dumps(result, indent=2)

        except ImportError:
            return json.dumps({
                "error": "yfinance not installed",
                "install": "pip install yfinance",
                "symbol": symbol
            })
        except Exception as e:
            return json.dumps({"error": str(e), "symbol": symbol})

    def get_market_overview(self) -> str:
        """Get overview of major markets"""
        try:
            import yfinance as yf

            symbols = {
                "XAUUSD": "GC=F",
                "EURUSD": "EURUSD=X",
                "SPX500": "^GSPC",
                "US30": "^DJI",
                "NAS100": "^IXIC",
                "BTCUSDT": "BTC-USD",
                "VIX": "^VIX",
                "US10Y": "^TNX",
                "DXY": "DX-Y.NYB"
            }

            overview = {}
            for name, yf_sym in symbols.items():
                try:
                    ticker = yf.Ticker(yf_sym)
                    hist = ticker.history(period="2d")
                    if not hist.empty:
                        close = float(hist["Close"].iloc[-1])
                        prev_close = float(hist["Close"].iloc[0]) if len(hist) > 1 else close
                        change = ((close - prev_close) / prev_close) * 100
                        overview[name] = {
                            "price": round(close, 2),
                            "change_pct": round(change, 2),
                            "direction": "UP" if change > 0 else "DOWN" if change < 0 else "FLAT"
                        }
                except Exception:
                    overview[name] = {"price": "N/A", "change_pct": "N/A", "direction": "N/A"}

            return json.dumps({
                "timestamp": datetime.now().isoformat(),
                "markets": overview
            }, indent=2)

        except Exception as e:
            return json.dumps({"error": str(e)})

    def get_economic_calendar(self) -> str:
        """Get upcoming economic events - requires external API integration"""
        return json.dumps({
            "status": "not_configured",
            "message": "Economic calendar requires additional API integration",
            "suggested_apis": ["ForexFactory", "Investing.com", "FRED"],
            "implementation": "Configure an economic calendar API in config/hermes-quant.yaml to enable live data"
        })
