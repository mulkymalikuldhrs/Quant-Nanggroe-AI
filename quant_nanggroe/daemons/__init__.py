# TradeBobby Daemons — Python port of TradeBobbyTerminal background daemons
# Adapted from Node.js daemons to Python for Quant-Nanggroe-AI integration

"""
TradeBobby-style data daemons ported from Node.js to Python.
These daemons fetch and refresh data from public APIs.

Daemons:
  - macro_pulse: Yahoo Finance macro data (DXY, VIX, yields, sectors)
  - crypto_pulse: CoinGecko + Binance funding rates
  - cot_fetcher: CFTC Commitment of Traders
  - news_scanner: Google News RSS with sentiment
  - setup_tracker: Trade signal performance tracking
  - agent_synthesis: Multi-source synthesis brief
"""

from .macro_pulse import MacroPulseDaemon
from .crypto_pulse import CryptoPulseDaemon
from .cot_fetcher import COTFetcherDaemon
from .news_scanner import NewsScannerDaemon

__all__ = [
    "MacroPulseDaemon",
    "CryptoPulseDaemon",
    "COTFetcherDaemon",
    "NewsScannerDaemon",
]
