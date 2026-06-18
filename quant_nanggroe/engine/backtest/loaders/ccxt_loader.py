"""CCXT loader: unified crypto exchange data (100+ exchanges).

Uses the CCXT library to fetch OHLCV candles from any supported exchange.
Defaults to Binance; configurable via ``CCXT_EXCHANGE`` env var.
No API key required for public market data.

Includes bounded retry with wall-clock budget to handle flaky API calls.

Ported from Vibe-Trading's ``backtest.loaders.ccxt_loader``.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Dict, List, Optional

import pandas as pd

from quant_nanggroe.engine.backtest.loaders.base_loader import (
    BaseLoader,
    check_budget,
    retry_with_budget,
    validate_date_range,
)

logger = logging.getLogger(__name__)

_INTERVAL_MAP = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1H": "1h",
    "4H": "4h",
    "1D": "1d",
}

# Wall-clock budget per symbol fetch
_CCXT_TIMEOUT_MS = int(os.getenv("CCXT_TIMEOUT_MS", "15000"))
_CCXT_FETCH_BUDGET_S = float(os.getenv("CCXT_FETCH_BUDGET_S", "60"))


class CCXTLoader(BaseLoader):
    """CCXT-backed crypto OHLCV loader (100+ exchanges).

    Uses the CCXT library to fetch OHLCV candles from any supported
    exchange. Defaults to Binance; configurable via ``CCXT_EXCHANGE``
    environment variable.

    No API key required for public market data.

    Environment variables:
      - ``CCXT_EXCHANGE``: Exchange to use (default: ``binance``).
      - ``CCXT_TIMEOUT_MS``: HTTP request timeout in ms (default: 15000).
      - ``CCXT_FETCH_BUDGET_S``: Wall-clock budget per symbol in seconds (default: 60).
    """

    name = "ccxt"
    markets = {"crypto"}
    requires_auth = False

    def is_available(self) -> bool:
        """Available if ccxt is installed."""
        try:
            import ccxt  # noqa: F401

            return True
        except ImportError:
            return False

    def _get_exchange(self):
        """Create exchange instance.

        Returns:
            CCXT exchange instance.

        Raises:
            ImportError: If ccxt is not installed.
        """
        import ccxt

        exchange_id = os.getenv("CCXT_EXCHANGE", "binance").lower()
        exchange_cls = getattr(ccxt, exchange_id, None)
        if exchange_cls is None:
            logger.warning(
                "Unknown CCXT exchange %s, falling back to binance", exchange_id
            )
            exchange_cls = ccxt.binance
        return exchange_cls({"enableRateLimit": True, "timeout": _CCXT_TIMEOUT_MS})

    def fetch(
        self,
        codes: List[str],
        start_date: str,
        end_date: str,
        *,
        interval: str = "1D",
        fields: Optional[List[str]] = None,
    ) -> Dict[str, pd.DataFrame]:
        """Fetch crypto OHLCV via CCXT.

        Args:
            codes: Symbols like ``["BTC-USDT", "ETH-USDT"]``.
            start_date: Start date (YYYY-MM-DD).
            end_date: End date (YYYY-MM-DD).
            interval: Bar size (1m/5m/15m/30m/1H/4H/1D).
            fields: Ignored.

        Returns:
            Mapping symbol -> OHLCV DataFrame.
        """
        if not codes:
            return {}

        validate_date_range(start_date, end_date)

        try:
            exchange = self._get_exchange()
        except ImportError:
            logger.error("ccxt is not installed. Install with: pip install ccxt")
            return {}

        timeframe = _INTERVAL_MAP.get(interval, "1d")
        since_ms = int(pd.Timestamp(start_date).timestamp() * 1000)
        end_ms = int(
            (pd.Timestamp(end_date) + pd.Timedelta(days=1)).timestamp() * 1000
        )

        result: Dict[str, pd.DataFrame] = {}
        for code in codes:
            try:
                ccxt_symbol = code.replace("-", "/").upper()
                df = self._fetch_one(
                    exchange, ccxt_symbol, timeframe, since_ms, end_ms
                )
                if df is not None and not df.empty:
                    result[code] = df
            except Exception as exc:
                logger.warning("CCXT failed for %s: %s", code, exc)
        return result

    @staticmethod
    def _fetch_one(
        exchange,
        symbol: str,
        timeframe: str,
        since_ms: int,
        end_ms: int,
    ) -> Optional[pd.DataFrame]:
        """Paginated OHLCV fetch for one symbol.

        Uses bounded retry with wall-clock budget to handle flaky API calls.

        Args:
            exchange: CCXT exchange instance.
            symbol: Trading pair symbol (e.g. ``BTC/USDT``).
            timeframe: Candle timeframe string.
            since_ms: Start timestamp in milliseconds.
            end_ms: End timestamp in milliseconds.

        Returns:
            OHLCV DataFrame or None if no data.
        """
        import ccxt

        all_rows: list = []
        cursor = since_ms
        limit = 1000
        deadline = time.monotonic() + _CCXT_FETCH_BUDGET_S
        label = f"ccxt fetch for {symbol}"

        for _ in range(200):  # Safety limit on pagination
            check_budget(deadline, label, budget_s=_CCXT_FETCH_BUDGET_S)

            ohlcv = retry_with_budget(
                lambda: exchange.fetch_ohlcv(
                    symbol, timeframe, since=cursor, limit=limit
                ),
                transient=ccxt.NetworkError,
                deadline=deadline,
                label=label,
            )
            if not ohlcv:
                break
            all_rows.extend(ohlcv)
            last_ts = ohlcv[-1][0]
            if last_ts >= end_ms or len(ohlcv) < limit:
                break
            cursor = last_ts + 1

        if not all_rows:
            return None

        df = pd.DataFrame(
            all_rows,
            columns=["timestamp", "open", "high", "low", "close", "volume"],
        )
        df["trade_date"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.set_index("trade_date").sort_index()

        start_dt = pd.Timestamp(since_ms, unit="ms")
        end_dt = pd.Timestamp(end_ms, unit="ms")
        df = df[(df.index >= start_dt) & (df.index < end_dt)]

        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df[["open", "high", "low", "close", "volume"]].dropna(
            subset=["open", "high", "low", "close"]
        )
        return df if not df.empty else None
