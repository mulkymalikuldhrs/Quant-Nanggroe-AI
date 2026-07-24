"""
London Strategic Edge (LSE) market data provider.

Provides: stocks, crypto, forex, ETFs, indices, options, economics, bonds.
Prasyarat: LSE_API_KEY env var (daftar gratis di https://londonstrategicedge.com/data).

Usage:
    from quant_nanggroe.providers.lse_provider import LSEProvider
    lse = LSEProvider()
    for tick in lse.stream(["BTC/USD", "AAPL"]):
        print(tick)
"""

import os
from typing import Optional


class LSEProvider:
    """Wrapper around lse-data client. Berguna untuk streaming + history.

    Args:
        api_key: LSE API key. Default dari LSE_API_KEY env var.
        timeout: REST call timeout (default 60s, naikkan untuk heavy query).
    """

    def __init__(self, api_key: Optional[str] = None, timeout: float = 60):
        from lse import LSE  # lazy import — optional dependency
        key = api_key or os.environ.get("LSE_API_KEY")
        if not key:
            raise ValueError(
                "LSE_API_KEY tidak ditemukan. "
                "Daftar gratis di https://londonstrategicedge.com/data "
                "dan set LSE_API_KEY env var atau pass api_key=."
            )
        self._client = LSE(api_key=key, timeout=timeout)

    def stream(self, symbols: list[str]):
        """Stream live ticks. Context manager — disconnect otomatis."""
        # ponytail: wrapper tipis, langsung delegasi ke LSE.client
        return self._client.stream(symbols)

    def subscribe(self, symbols: list[str]):
        """Subscribe symbols + connect (blocking). Pakai callback via on()."""
        self._client.subscribe(symbols)

    def on(self, event: str, callback):
        """Register callback: 'tick', 'trade', 'quote', dll."""
        self._client.on(event, callback)

    def connect(self):
        """Start blocking connection."""
        self._client.connect()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._client.disconnect()
