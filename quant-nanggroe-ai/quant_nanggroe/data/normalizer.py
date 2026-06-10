"""Cross-provider data normalization.

Converts provider-specific data formats into the canonical
internal types defined in ``quant_nanggroe.types.market``.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from quant_nanggroe.types.market import (
    OHLCV,
    DataMetadata,
    Interval,
    OrderBook,
    OrderBookLevel,
    Ticker,
)

logger = logging.getLogger("quant_nanggroe.data.normalizer")


def normalize_ohlcv(
    raw_candles: list[dict[str, Any]],
    symbol: str,
    source: str,
    interval: Interval = Interval.DAY_1,
    trust_score: float = 0.85,
) -> list[OHLCV]:
    """Normalize raw OHLCV data from any provider into canonical OHLCV types.

    Accepts a list of dictionaries with keys that may vary by provider
    and produces a list of typed OHLCV objects.

    Args:
        raw_candles: List of dicts with OHLCV data.
        symbol: Symbol to assign to each candle.
        source: Provider name for metadata.
        interval: Candle interval.
        trust_score: Trust score for the data source.

    Returns:
        List of normalized OHLCV objects.
    """
    metadata = DataMetadata(
        source=source,
        trust_score=trust_score,
        latency_estimate_ms=0.0,
        update_frequency=interval.value,
        domain_type="market",
    )

    candles: list[OHLCV] = []
    for raw in raw_candles:
        try:
            # Support multiple key naming conventions
            ts = _extract_timestamp(raw)
            o = float(raw.get("open", raw.get("Open", raw.get("o", 0))))
            h = float(raw.get("high", raw.get("High", raw.get("h", 0))))
            l = float(raw.get("low", raw.get("Low", raw.get("l", 0))))
            c = float(raw.get("close", raw.get("Close", raw.get("c", 0))))
            v = float(raw.get("volume", raw.get("Volume", raw.get("v", 0))))

            if h < l:
                h, l = l, h  # Swap if inverted

            candles.append(
                OHLCV(
                    symbol=symbol,
                    timestamp=ts,
                    open=max(o, 0.0001),
                    high=max(h, 0.0001),
                    low=max(l, 0.0001),
                    close=max(c, 0.0001),
                    volume=max(v, 0.0),
                    interval=interval,
                    metadata=metadata,
                )
            )
        except (KeyError, ValueError, TypeError) as e:
            logger.warning(f"Skipping invalid candle: {raw} — {e}")
            continue

    return candles


def normalize_ticker(
    raw: dict[str, Any],
    symbol: str,
    source: str,
    trust_score: float = 0.85,
) -> Ticker:
    """Normalize raw ticker data into a canonical Ticker type.

    Args:
        raw: Dictionary with ticker data.
        symbol: Symbol to assign.
        source: Provider name.
        trust_score: Trust score for the source.

    Returns:
        Normalized Ticker object.
    """
    metadata = DataMetadata(
        source=source,
        trust_score=trust_score,
        update_frequency="realtime",
        domain_type="market",
    )

    current_price = float(
        raw.get("current_price", raw.get("last", raw.get("price", raw.get("c", 0))))
    )

    return Ticker(
        symbol=symbol,
        name=raw.get("name"),
        current_price=max(current_price, 0.0001),
        price_change_24h=float(raw.get("price_change_24h", raw.get("change", 0)) or 0),
        price_change_pct_24h=float(raw.get("price_change_pct_24h", raw.get("percentage", 0)) or 0),
        high_24h=_safe_float(raw.get("high_24h", raw.get("high"))),
        low_24h=_safe_float(raw.get("low_24h", raw.get("low"))),
        volume_24h=_safe_float(raw.get("volume_24h", raw.get("quoteVolume"))),
        bid=_safe_float(raw.get("bid")),
        ask=_safe_float(raw.get("ask")),
        metadata=metadata,
    )


def normalize_orderbook(
    raw: dict[str, Any],
    symbol: str,
    source: str,
    trust_score: float = 0.85,
) -> OrderBook:
    """Normalize raw order book data into a canonical OrderBook type.

    Args:
        raw: Dictionary with 'bids' and 'asks' lists.
        symbol: Symbol to assign.
        source: Provider name.
        trust_score: Trust score for the source.

    Returns:
        Normalized OrderBook object.
    """
    metadata = DataMetadata(
        source=source,
        trust_score=trust_score,
        update_frequency="realtime",
        domain_type="market",
    )

    bids: list[OrderBookLevel] = []
    for b in raw.get("bids", []):
        if isinstance(b, (list, tuple)):
            bids.append(OrderBookLevel(price=float(b[0]), quantity=float(b[1])))
        elif isinstance(b, dict):
            bids.append(
                OrderBookLevel(
                    price=float(b.get("price", 0)),
                    quantity=float(b.get("quantity", b.get("amount", 0))),
                )
            )

    asks: list[OrderBookLevel] = []
    for a in raw.get("asks", []):
        if isinstance(a, (list, tuple)):
            asks.append(OrderBookLevel(price=float(a[0]), quantity=float(a[1])))
        elif isinstance(a, dict):
            asks.append(
                OrderBookLevel(
                    price=float(a.get("price", 0)),
                    quantity=float(a.get("quantity", a.get("amount", 0))),
                )
            )

    return OrderBook(
        symbol=symbol,
        timestamp=datetime.now(tz=timezone.utc),
        bids=bids,
        asks=asks,
        metadata=metadata,
    )


def _extract_timestamp(raw: dict[str, Any]) -> datetime:
    """Extract a datetime from a raw data dict, handling multiple formats."""
    for key in ("timestamp", "time", "date", "t", "datetime"):
        val = raw.get(key)
        if val is None:
            continue
        if isinstance(val, datetime):
            return val
        if isinstance(val, (int, float)):
            # Could be seconds or milliseconds
            if val > 1e12:
                return datetime.fromtimestamp(val / 1000, tz=timezone.utc)
            return datetime.fromtimestamp(val, tz=timezone.utc)
        if isinstance(val, str):
            try:
                return datetime.fromisoformat(val.replace("Z", "+00:00"))
            except ValueError:
                continue

    return datetime.now(tz=timezone.utc)


def _safe_float(val: Any) -> Optional[float]:
    """Convert a value to float, returning None on failure."""
    if val is None:
        return None
    try:
        result = float(val)
        return result if result != 0 or val == 0 else None
    except (ValueError, TypeError):
        return None
