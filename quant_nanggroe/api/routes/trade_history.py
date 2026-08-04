"""Trade history API routes — closed trades with filtering.

Reads from MT5 history (``mt5.history_deals_get()``) with file-based
journal fallback.  Supports symbol, date range, strategy, and limit filters.
"""

from __future__ import annotations

import logging
import os
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/export")
async def export_trades(
    format: str = Query("excel", description="excel | pdf"),
    limit: int = Query(500, ge=1, le=5000),
) -> FileResponse:
    """Export the trade journal (with metacognition) to Excel or PDF.

    The export serialises exactly what was recorded per trade: APA/KENAPA/
    BAGAIMANA/MENGAPA/KE MANA awareness, exit cause, and self-evolve lesson.
    No recomputation, no fabrication.
    """
    from quant_nanggroe.engine.analytics.trade_export import export as _export

    fmt = (format or "excel").lower()
    if fmt not in ("excel", "pdf"):
        raise HTTPException(400, "format must be 'excel' or 'pdf'")
    try:
        path = _export(format=fmt, limit=limit)
    except Exception as e:
        logger.error("trade export failed: %s", e)
        raise HTTPException(500, f"export failed: {e}")
    media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if fmt == "excel" else "application/pdf"
    return FileResponse(path, media_type=media, filename=os.path.basename(path))


# ── Schemas ──────────────────────────────────────────────────────────


class DealSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class TradeDetail(BaseModel):
    id: str
    ticket: int | None = None
    symbol: str
    side: DealSide
    volume: float
    entry_price: float
    exit_price: float
    entry_time: datetime
    exit_time: datetime
    pnl: float
    pnl_pct: float | None = None
    commission: float = 0.0
    swap: float = 0.0
    strategy: str | None = None
    broker: str | None = None
    comment: str | None = None
    # Metacognition (autonomous mandate): APA/KENAPA/BAGAIMANA/MENGAPA/KE MANA
    # + exit cause + self-evolve lesson. Present in the journal; surfaced to
    # the dashboard so every trade shows its awareness.
    awareness: dict = Field(default_factory=dict)


class TradeHistoryResponse(BaseModel):
    trades: list[TradeDetail] = Field(default_factory=list)
    total_count: int = 0
    limit: int = 50
    filters: dict[str, Any] = Field(default_factory=dict)


# ── MT5 / file-based reader ─────────────────────────────────────────


def _try_mt5_history(
    symbol: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 50,
) -> list[TradeDetail] | None:
    """Read closed trades from MetaTrader 5 history.

    Returns ``None`` if MT5 is not initialised or unavailable.
    """
    try:
        import MetaTrader5 as mt5
    except ImportError:
        return None

    if not mt5.initialize():
        logger.warning("mt5_not_initialized_for_history")
        return None

    dt_from = datetime.combine(date_from or date.today() - timedelta(days=30), datetime.min.time(), tzinfo=timezone.utc)
    dt_to = datetime.combine(date_to or date.today(), datetime.max.time(), tzinfo=timezone.utc)

    try:
        deals = mt5.history_deals_get(dt_from, dt_to) or []
    except Exception as exc:
        logger.warning("mt5_history_deals_error", extra={"error": str(exc)})
        return None

    result: list[TradeDetail] = []
    for d in deals:
        d_sym = getattr(d, "symbol", "")
        if symbol and d_sym.upper() != symbol.upper().replace("/", ""):
            continue
        d_side = DealSide.BUY if getattr(d, "type", 0) == 0 else DealSide.SELL
        entry_price = getattr(d, "price", 0.0)
        profit = getattr(d, "profit", 0.0)
        volume = getattr(d, "volume", 0.0)
        commission = getattr(d, "commission", 0.0) or 0.0
        swap = getattr(d, "swap", 0.0) or 0.0
        d_time = datetime.fromtimestamp(getattr(d, "time", 0), tz=timezone.utc) if getattr(d, "time", 0) else datetime.now(timezone.utc)
        ticket = getattr(d, "ticket", 0)

        result.append(TradeDetail(
            id=str(ticket) if ticket else str(uuid4())[:8],
            ticket=ticket or None,
            symbol=d_sym,
            side=d_side,
            volume=volume,
            entry_price=entry_price,
            exit_price=entry_price,
            entry_time=d_time,
            exit_time=d_time,
            pnl=profit,
            pnl_pct=None,
            commission=commission,
            swap=swap,
            strategy=None,
            broker="mt5",
            comment=getattr(d, "comment", None) or None,
        ))

    result.sort(key=lambda t: t.exit_time, reverse=True)
    return result[:limit]


def _try_journal(
    symbol: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    strategy: str | None = None,
    limit: int = 50,
) -> list[TradeDetail]:
    """Read closed trades from file-based journal (``paper_state/trades.json``)."""
    import json
    import os

    journal_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "paper_state", "trades.json")
    )
    if not os.path.isfile(journal_path):
        return []

    try:
        with open(journal_path, encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        return []

    if isinstance(raw, dict):
        raw = raw.get("trades", raw.get("history", []))

    result: list[TradeDetail] = []
    for entry in raw:
        sym = entry.get("symbol", entry.get("ticker", ""))
        if symbol and sym.upper() != symbol.upper():
            continue
        strat = entry.get("strategy", entry.get("agent", ""))
        if strategy and strat.lower() != strategy.lower():
            continue
        entry_time = entry.get("entry_time", entry.get("time", ""))
        exit_time = entry.get("exit_time", entry.get("close_time", entry_time))
        if date_from or date_to:
            try:
                et = datetime.fromisoformat(exit_time) if isinstance(exit_time, str) else datetime.fromtimestamp(exit_time, tz=timezone.utc)
                if date_from and et.date() < date_from:
                    continue
                if date_to and et.date() > date_to:
                    continue
            except Exception:
                pass

        entry_price = float(entry.get("entry_price", entry.get("price", 0)))
        exit_price = float(entry.get("exit_price", entry.get("close_price", entry_price)))
        pnl = float(entry.get("pnl", entry.get("profit", 0)))
        volume = float(entry.get("volume", entry.get("amount", entry.get("quantity", 0))))
        side_str = str(entry.get("side", "buy")).lower()
        d_side = DealSide.BUY if side_str in ("buy", "long") else DealSide.SELL

        pnl_pct = None
        if entry_price and volume:
            pnl_pct = round((pnl / (entry_price * volume)) * 100, 2)

        result.append(TradeDetail(
            id=entry.get("id", str(uuid4())[:8]),
            ticket=entry.get("ticket"),
            symbol=sym,
            side=d_side,
            volume=volume,
            entry_price=entry_price,
            exit_price=exit_price,
            entry_time=_parse_dt(entry.get("entry_time", entry.get("time", ""))),
            exit_time=_parse_dt(exit_time),
            pnl=pnl,
            pnl_pct=pnl_pct,
            commission=float(entry.get("commission", 0)),
            swap=float(entry.get("swap", 0)),
            strategy=strat or None,
            broker="journal",
            comment=entry.get("comment"),
            awareness=entry.get("awareness", {}) or {},
        ))

    result.sort(key=lambda t: t.exit_time, reverse=True)
    return result[:limit]


def _parse_dt(val: Any) -> datetime:
    if isinstance(val, datetime):
        return val
    if isinstance(val, (int, float)):
        return datetime.fromtimestamp(val, tz=timezone.utc)
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val)
        except Exception:
            pass
    return datetime.now(timezone.utc)


# ── Endpoints ────────────────────────────────────────────────────────


@router.get("/history", response_model=TradeHistoryResponse)
async def get_trade_history(
    symbol: str | None = Query(None, description="Filter by symbol (e.g. BTC/USD)"),
    date_from: date | None = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: date | None = Query(None, description="End date (YYYY-MM-DD)"),
    strategy: str | None = Query(None, description="Filter by strategy name"),
    limit: int = Query(50, ge=1, le=500, description="Max trades to return"),
) -> TradeHistoryResponse:
    """Return closed trades with optional filters.

    Reads from MT5 history first; falls back to file-based journal.
    """
    trades = _try_mt5_history(symbol=symbol, date_from=date_from, date_to=date_to, limit=limit)
    if trades is None:
        trades = _try_journal(symbol=symbol, date_from=date_from, date_to=date_to, strategy=strategy, limit=limit)

    return TradeHistoryResponse(
        trades=trades,
        total_count=len(trades),
        limit=limit,
        filters={
            "symbol": symbol,
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
            "strategy": strategy,
        },
    )


@router.get("/history/{trade_id}", response_model=TradeDetail)
async def get_trade_detail(trade_id: str) -> TradeDetail:
    """Return a single trade by ID.

    Searches MT5 history and journal fallback.
    """
    trades = _try_mt5_history(limit=500) or []
    for t in trades:
        if t.id == trade_id:
            return t

    journal = _try_journal(limit=500)
    for t in journal:
        if t.id == trade_id:
            return t

    # Try searching without limit (ticket-based)
    try:
        import MetaTrader5 as mt5
        if mt5.initialize():
            ticket = int(trade_id) if trade_id.isdigit() else 0
            if ticket:
                deal = mt5.history_deals_get(ticket=ticket)
                if deal:
                    deal = deal[0]
                    d_time = datetime.fromtimestamp(getattr(deal, "time", 0), tz=timezone.utc) if getattr(deal, "time", 0) else datetime.now(timezone.utc)
                    return TradeDetail(
                        id=str(ticket),
                        ticket=ticket,
                        symbol=getattr(deal, "symbol", ""),
                        side=DealSide.BUY if getattr(deal, "type", 0) == 0 else DealSide.SELL,
                        volume=getattr(deal, "volume", 0.0),
                        entry_price=getattr(deal, "price", 0.0),
                        exit_price=getattr(deal, "price", 0.0),
                        entry_time=d_time,
                        exit_time=d_time,
                        pnl=getattr(deal, "profit", 0.0),
                        commission=getattr(deal, "commission", 0.0) or 0.0,
                        swap=getattr(deal, "swap", 0.0) or 0.0,
                        broker="mt5",
                    )
    except Exception:
        pass

    raise HTTPException(status_code=404, detail=f"Trade {trade_id} not found")
