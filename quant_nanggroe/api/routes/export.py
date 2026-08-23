"""Export Center API — trades/summary in custom date ranges to multiple formats.

GATE-4 (user mandate): "export trades with custom time range ... to *excel,
*pdf, *md, etc."

Endpoints (mounted under /api/export):
    GET /trades   ?from=YYYY-MM-DD &to=YYYY-MM-DD &strategy= &symbol= &format=csv|xlsx|md|json|pdf
    GET /summary  ?from &to                      -> per-strategy stats JSON

Honest capability matrix:
    csv/json/md/xlsx always available (stdlib/openpyxl/pandas)
    pdf requires `reportlab` -> 501 with install hint when missing
"""
from __future__ import annotations

import csv
import io
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

router = APIRouter(prefix="/export", tags=["export"])

_JOURNAL_DB_CANDIDATES = [
    Path(__file__).resolve().parents[3] / "quant_nanggroe" / "data" / "qna_trade_journal.db",
    Path(__file__).resolve().parents[3] / "data" / "qna_trade_journal.db",
]

TRADE_COLUMNS = [
    "ticket", "strategy", "symbol", "side", "entry", "sl", "tp",
    "confidence", "open_time", "close_time", "exit_price", "pnl",
    "outcome", "comment", "hypothesis", "setup_ctx", "close_reason",
    "hit_type", "market_ctx", "tf_category",
]


def _db_path() -> Path:
    for p in _JOURNAL_DB_CANDIDATES:
        if p.exists():
            return p
    raise HTTPException(404, "trade journal database not found")


def _query_trades(date_from: Optional[str], date_to: Optional[str],
                  strategy: Optional[str], symbol: Optional[str]) -> List[dict]:
    con = sqlite3.connect(str(_db_path()))
    con.row_factory = sqlite3.Row
    try:
        sql = "SELECT * FROM trades WHERE 1=1"
        params: list = []
        if date_from:
            sql += " AND date(close_time) >= date(?)"
            params.append(date_from)
        if date_to:
            sql += " AND date(close_time) <= date(?)"
            params.append(date_to)
        if strategy:
            sql += " AND strategy = ?"
            params.append(strategy)
        if symbol:
            sql += " AND symbol LIKE ?"
            params.append(f"%{symbol}%")
        sql += " ORDER BY close_time DESC"
        return [dict(r) for r in con.execute(sql, params)]
    finally:
        con.close()


def _to_csv(rows: List[dict]) -> bytes:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=TRADE_COLUMNS, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue().encode("utf-8-sig")


def _to_md(rows: List[dict]) -> bytes:
    cols = ["ticket", "strategy", "symbol", "side", "entry", "exit_price",
            "pnl", "outcome", "close_reason", "close_time"]
    lines = ["# QNA Trade History", "",
             "| " + " | ".join(cols) + " |",
             "|" + "---|" * len(cols)]
    for r in rows:
        lines.append("| " + " | ".join(str(r.get(c, "")) for c in cols) + " |")
    return "\n".join(lines).encode("utf-8")


def _to_xlsx(rows: List[dict]) -> bytes:
    try:
        from openpyxl import Workbook
    except ImportError as e:
        raise HTTPException(501, "xlsx needs openpyxl: pip install openpyxl") from e
    wb = Workbook()
    ws = wb.active
    ws.title = "trades"
    ws.append(TRADE_COLUMNS)
    for r in rows:
        ws.append([r.get(c) for c in TRADE_COLUMNS])
    # summary sheet
    ws2 = wb.create_sheet("summary")
    ws2.append(["strategy", "n_trades", "total_pnl", "win_rate"])
    agg: dict[str, dict] = {}
    for r in rows:
        a = agg.setdefault(r["strategy"], {"n": 0, "pnl": 0.0, "wins": 0})
        a["n"] += 1
        try:
            a["pnl"] += float(r.get("pnl") or 0)
        except (TypeError, ValueError):
            pass
        if str(r.get("outcome", "")).lower() in ("win", "tp"):
            a["wins"] += 1
    for s, a in sorted(agg.items()):
        ws2.append([s, a["n"], round(a["pnl"], 2),
                    round(a["wins"] / a["n"], 4) if a["n"] else 0])
    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue()


def _to_pdf(rows: List[dict]) -> bytes:
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
    except ImportError as e:
        raise HTTPException(
            501, "pdf needs reportlab: pip install reportlab") from e
    cols = ["ticket", "strategy", "symbol", "side", "entry", "exit_price", "pnl"]
    data = [cols] + [[str(r.get(c, ""))[:24] for c in cols] for r in rows[:400]]
    table = Table(data)
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.3, (0.6, 0.6, 0.6)),
        ("BACKGROUND", (0, 0), (-1, 0), (0.85, 0.85, 0.85)),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
    ]))
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, title="QNA Trade History")
    doc.build([table])
    return buf.getvalue()


@router.get("/trades")
async def export_trades(
    format: str = "csv",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    strategy: Optional[str] = None,
    symbol: Optional[str] = None,
) -> Response:
    rows = _query_trades(date_from, date_to, strategy, symbol)
    fmt = format.lower()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if fmt == "json":
        return Response(content=json.dumps(rows, default=str).encode(),
                        media_type="application/json")
    if fmt == "csv":
        return Response(_to_csv(rows), media_type="text/csv",
                        headers={"Content-Disposition":
                                 f'attachment; filename="qna_trades_{stamp}.csv"'})
    if fmt == "md":
        return Response(_to_md(rows), media_type="text/markdown",
                        headers={"Content-Disposition":
                                 f'attachment; filename="qna_trades_{stamp}.md"'})
    if fmt == "xlsx":
        return Response(_to_xlsx(rows),
                        media_type=("application/vnd.openxmlformats-officedocument"
                                    ".spreadsheetml.sheet"),
                        headers={"Content-Disposition":
                                 f'attachment; filename="qna_trades_{stamp}.xlsx"'})
    if fmt == "pdf":
        content = _to_pdf(rows)  # raises 501 when reportlab missing
        return Response(content=content, media_type="application/pdf",
                        headers={"Content-Disposition":
                                 f'attachment; filename="qna_trades_{stamp}.pdf"'})
    raise HTTPException(400, f"unknown format '{format}' "
                             "(csv|xlsx|md|json|pdf)")


class SummaryRow(BaseModel):
    strategy: str
    n_trades: int
    total_pnl: float
    win_rate: float
    avg_pnl: float
    best_trade: float
    worst_trade: float


@router.get("/summary")
async def export_summary(date_from: Optional[str] = None,
                         date_to: Optional[str] = None) -> dict:
    rows = _query_trades(date_from, date_to, None, None)
    agg: dict[str, dict] = {}
    for r in rows:
        s = r["strategy"]
        a = agg.setdefault(s, {"n": 0, "pnl": 0.0, "wins": 0,
                               "pnls": []})
        a["n"] += 1
        try:
            p = float(r.get("pnl") or 0)
        except (TypeError, ValueError):
            p = 0.0
        a["pnl"] += p
        a["pnls"].append(p)
        if str(r.get("outcome", "")).lower() in ("win", "tp"):
            a["wins"] += 1
    out = []
    for s, a in sorted(agg.items(), key=lambda kv: kv[1]["pnl"], reverse=True):
        pnls = a["pnls"]
        out.append(SummaryRow(
            strategy=s, n_trades=a["n"], total_pnl=round(a["pnl"], 2),
            win_rate=round(a["wins"] / a["n"], 4) if a["n"] else 0,
            avg_pnl=round(a["pnl"] / a["n"], 4) if a["n"] else 0,
            best_trade=round(max(pnls), 2) if pnls else 0,
            worst_trade=round(min(pnls), 2) if pnls else 0,
        ).model_dump())
    return {"rows": out, "total_trades": len(rows), "strategies": len(out)}


@router.get("/awareness")
async def export_awareness(date_from: Optional[str] = None,
                           date_to: Optional[str] = None,
                           strategy: Optional[str] = None,
                           limit: int = 500) -> dict:
    """GATE-3: deterministic what/why/how/lesson per closed trade."""
    from quant_nanggroe.engine.analytics.trade_awareness import explain_journal
    items = explain_journal(date_from=date_from, date_to=date_to,
                            strategy=strategy, limit=limit)
    return {"items": items, "count": len(items)}


@router.get("/allocation")
async def strategy_allocation_view(symbol: Optional[str] = None) -> dict:
    """CANONICAL 15.6: per-symbol CPCV specialists view.

    No ``symbol`` -> full allocation map (asset class -> admitted strategies).
    With ``symbol`` -> admitted list for that symbol (None evidence => null).
    """
    from quant_nanggroe.engine import strategy_allocation as sa
    if symbol:
        admitted = sa.admitted_for_symbol(symbol)
        return {"symbol": symbol, "admitted": admitted,
                "threshold": sa.MIN_COMBO_PROFIT_SHARE}
    return {
        "allocation_map": sa.allocation_map(),
        "threshold": sa.MIN_COMBO_PROFIT_SHARE,
        "asset_map": {k: v for k, v in sorted(sa.SYMBOL_ASSET_MAP.items())},
    }


@router.get("/scorecard")
async def strategy_scorecard() -> dict:
    """Real per-strategy scorecard from synced journal (FAZE 2).

    Returns expectancy / PF / Sharpe / WR / max_dd / t-statistic per
    strategy with KEEP/TUNE/KILL verdict. This is the bridge between
    raw MT5 deals and the self-evolve loop.
    """
    from quant_nanggroe.engine.analytics.strategy_scorecard import (
        compute_all_strategies,
    )
    return compute_all_strategies()
