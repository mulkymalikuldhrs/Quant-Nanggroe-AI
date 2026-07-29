"""Order book API routes — Level 2 market depth data.

Fetches real-time order book snapshots from Binance public API
with CCXT fallback.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()

# Binance depth endpoint (no API key required for public data)
BINANCE_DEPTH_URL = "https://api.binance.com/api/v3/depth"


class OrderBookLevel(BaseModel):
    price: float
    quantity: float
    total: float | None = None


class OrderBookResponse(BaseModel):
    symbol: str
    exchange: str = "binance"
    bids: list[OrderBookLevel] = Field(default_factory=list)
    asks: list[OrderBookLevel] = Field(default_factory=list)
    bid_depth: float = 0.0
    ask_depth: float = 0.0
    spread: float = 0.0
    spread_pct: float = 0.0
    mid_price: float = 0.0
    timestamp: str = ""
    source: str = ""


async def _fetch_binance_depth(symbol: str, limit: int = 20) -> dict[str, Any] | None:
    """Fetch order book from Binance public REST API."""
    import httpx

    norm = symbol.replace("/", "").upper()
    url = f"{BINANCE_DEPTH_URL}?symbol={norm}&limit={limit}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        logger.warning("binance_depth_error", extra={"symbol": symbol, "error": str(exc)})
        return None


async def _fetch_ccxt_depth(symbol: str, limit: int = 20) -> dict[str, Any] | None:
    """Fallback using CCXT if installed and Binance API fails."""
    try:
        import ccxt.async_support as ccxt
    except ImportError:
        return None
    try:
        exchange = ccxt.binance({"enableRateLimit": True})
        ob = await exchange.fetch_order_book(symbol, limit=limit)
        await exchange.close()
        return ob
    except Exception as exc:
        logger.warning("ccxt_depth_error", extra={"symbol": symbol, "error": str(exc)})
        return None


@router.get("/orderbook/{symbol}", response_model=OrderBookResponse)
async def get_orderbook(symbol: str, limit: int = 20) -> OrderBookResponse:
    """Return Level 2 order book data for a given symbol.

    Fetches from Binance public API; falls back to CCXT if available.
    Symbol format: ``BTC/USDT``, ``ETH/USDT`` (converted automatically).
    """
    from datetime import datetime, timezone

    data = await _fetch_binance_depth(symbol, limit=limit)
    source = "binance_rest"

    if data is None:
        data = await _fetch_ccxt_depth(symbol, limit=limit)
        source = "ccxt_binance"

    if data is None:
        raise HTTPException(
            status_code=503,
            detail=f"Order book unavailable for {symbol} — all upstream sources failed",
        )

    bids_raw = data.get("bids", [])
    asks_raw = data.get("asks", [])

    bids: list[OrderBookLevel] = []
    bid_depth = 0.0
    for level in bids_raw[:limit]:
        if isinstance(level, list) and len(level) >= 2:
            p = float(level[0])
            q = float(level[1])
            bids.append(OrderBookLevel(price=p, quantity=q, total=round(p * q, 2)))
            bid_depth += q

    asks: list[OrderBookLevel] = []
    ask_depth = 0.0
    for level in asks_raw[:limit]:
        if isinstance(level, list) and len(level) >= 2:
            p = float(level[0])
            q = float(level[1])
            asks.append(OrderBookLevel(price=p, quantity=q, total=round(p * q, 2)))
            ask_depth += q

    best_bid = bids[0].price if bids else 0.0
    best_ask = asks[0].price if asks else 0.0
    spread = best_ask - best_bid
    mid_price = (best_bid + best_ask) / 2 if best_bid and best_ask else 0.0
    spread_pct = (spread / mid_price * 100) if mid_price else 0.0

    return OrderBookResponse(
        symbol=symbol,
        exchange="binance",
        bids=bids,
        asks=asks,
        bid_depth=round(bid_depth, 4),
        ask_depth=round(ask_depth, 4),
        spread=round(spread, 8),
        spread_pct=round(spread_pct, 4),
        mid_price=round(mid_price, 8),
        timestamp=datetime.now(timezone.utc).isoformat(),
        source=source,
    )
