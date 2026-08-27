"""QNA Assistant API — natural-language trading copilot.

Accepts user messages, routes to appropriate handler based on intent,
returns structured response with data and/or action results.

NO LLM dependency — pure rule-based intent matching for speed and
determinism. Every command maps directly to a real API call.

Endpoints (mounted under /api/assistant):
    POST /chat  { "message": "..." } → { "reply": "...", "data": {...}, "actions": [...] }
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/assistant", tags=["Assistant"])


class ChatMessage(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    data: Optional[Any] = None
    actions: List[Dict[str, Any]] = []
    intent: str = "unknown"


# ── Intent handlers ────────────────────────────────────────────────

def _handle_status() -> Dict[str, Any]:
    """System status: PnL, trades, kill switch."""
    from quant_nanggroe.engine.journal_sync import get_journal_stats
    stats = get_journal_stats()
    pnl = stats.get("net_pnl", 0)
    total = stats.get("total_trades", 0)
    wr = stats.get("win_rate", 0)

    emoji = "🟢" if pnl >= 0 else "🔴"
    reply = (
        f"{emoji} QNA Status\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Total Trades: {total}\n"
        f"Net P&L: ${pnl:+,.2f}\n"
        f"Win Rate: {wr:.1%}\n"
        f"Kill Switch: {'ACTIVE ⛔' if stats.get('kill_switch_active') else 'Inactive ✅'}"
    )
    return {"reply": reply, "data": stats, "intent": "status"}


def _handle_positions() -> Dict[str, Any]:
    """List open positions."""
    try:
        import MetaTrader5 as mt5
        if not mt5.initialize():
            return {"reply": "⚠️ MT5 terminal not connected", "intent": "positions"}
        positions = mt5.positions_get() or []
        if not positions:
            return {"reply": "📭 No open positions", "intent": "positions"}

        lines = ["📊 Open Positions:\n"]
        total_pnl = 0.0
        for p in positions:
            side = "BUY" if p.type == 0 else "SELL"
            lines.append(
                f"  {side} {p.volume} {p.symbol} @ {p.price_open:.2f} "
                f"→ P&L: {p.profit:+.2f}"
            )
            total_pnl += p.profit
        lines.append(f"\n  Total Floating P&L: {total_pnl:+.2f}")
        mt5.shutdown()
        return {"reply": "\n".join(lines), "data": {"count": len(positions)},
                "intent": "positions"}
    except Exception as e:
        return {"reply": f"❌ MT5 error: {e}", "intent": "positions"}


def _handle_scorecard() -> Dict[str, Any]:
    """Strategy scorecard."""
    from quant_nanggroe.engine.analytics.strategy_scorecard import (
        compute_all_strategies,
    )
    result = compute_all_strategies()
    strategies = result.get("strategies", {})
    portfolio = result.get("portfolio", {})

    lines = [f"📈 Strategy Scorecards ({portfolio.get('total_trades', 0)} trades):\n"]
    for name, card in sorted(strategies.items(),
                             key=lambda x: x[1].get("expectancy", 0),
                             reverse=True):
        verdict_emoji = {
            "PROVEN_GOOD": "✅", "MARGINAL_POSITIVE": "🟡",
            "NEGATIVE_EDGE": "🔴", "NEUTRAL": "⚪",
            "INSUFFICIENT_DATA": "⚪",
        }.get(card["verdict"], "⚪")
        lines.append(
            f"  {verdict_emoji} {name}: {card['n_trades']} trades, "
            f"PnL={card['total_pnl']:+.2f}, PF={card['profit_factor']}, "
            f"WR={card['win_rate']:.0%}"
        )
    return {"reply": "\n".join(lines), "data": result, "intent": "scorecard"}


def _handle_allocation() -> Dict[str, Any]:
    """Per-symbol CPCV allocation."""
    from quant_nanggroe.engine.strategy_allocation import allocation_map
    alloc = allocation_map()
    lines = ["🎯 Per-Symbol Specialists:\n"]
    for asset_class, strategies in sorted(alloc.items()):
        lines.append(f"  {asset_class}: {', '.join(strategies)}")
    return {"reply": "\n".join(lines), "data": alloc, "intent": "allocation"}


def _handle_export(symbol: Optional[str] = None) -> Dict[str, Any]:
    """Export info."""
    msg = "📤 Export available at /api/export/trades?format=xlsx"
    if symbol:
        msg += f"\nFiltering by symbol: {symbol}"
    msg += "\nFormats: csv, xlsx, md, json (pdf needs reportlab)"
    return {"reply": msg, "actions": [{"type": "export", "format": "xlsx"}],
            "intent": "export"}


def _handle_close(symbol: str) -> Dict[str, Any]:
    """Close a position by symbol."""
    try:
        import MetaTrader5 as mt5
        if not mt5.initialize():
            return {"reply": "⚠️ MT5 not connected", "intent": "close"}

        positions = [p for p in (mt5.positions_get() or []) if symbol.upper() in p.symbol.upper()]
        if not positions:
            return {"reply": f"📭 No open position matching '{symbol}'",
                    "intent": "close"}

        closed_count = 0
        for pos in positions:
            close_side = "sell" if pos.type == 0 else "buy"
            tick = mt5.symbol_info_tick(pos.symbol)
            if not tick:
                continue
            price = tick.bid if close_side == "sell" else tick.ask
            req = {
                "action": mt5.TRADE_ACTION_DEAL,
                "position": pos.ticket,
                "symbol": pos.symbol,
                "volume": float(pos.volume),
                "type": mt5.ORDER_TYPE_SELL if close_side == "sell" else mt5.ORDER_TYPE_BUY,
                "price": price,
                "deviation": 20,
                "comment": "assistant_close",
                "type_filling": mt5.ORDER_FILLING_FOK,
            }
            r = mt5.order_send(req)
            if r and r.retcode == mt5.TRADE_RETCODE_DONE:
                closed_count += 1

        mt5.shutdown()
        return {"reply": f"✅ Closed {closed_count} position(s) for {symbol}",
                "intent": "close"}
    except Exception as e:
        return {"reply": f"❌ Close failed: {e}", "intent": "close"}


def _handle_help() -> Dict[str, Any]:
    return {
        "reply": (
            "🤖 QNA Assistant Commands:\n\n"
            "  status / pnl       → System status + P&L\n"
            "  positions / open   → Open positions\n"
            "  scorecard          → Strategy performance\n"
            "  allocation         → CPCV specialists per symbol\n"
            "  close EURUSD       → Close EURUSD position\n"
            "  export             → Export trade data\n"
            "  help               → This message"
        ),
        "intent": "help",
    }


# ── Intent Router ──────────────────────────────────────────────────

_INTENT_PATTERNS = [
    (r"(status|pnl|profit|loss|how.*doing)", lambda _: _handle_status()),
    (r"(position|open|floating|holding)", lambda _: _handle_positions()),
    (r"(scorecard|strategy.*perform|which.*strateg)", lambda _: _handle_scorecard()),
    (r"(allocation|specialist|who.*trade|cpcv)", lambda _: _handle_allocation()),
    (r"close\s+(\w+)", None),  # handled specially below
    (r"export|download|xlsx|excel", lambda _: _handle_export()),
    (r"help|command|what.*can|how", lambda _: _handle_help()),
]


@router.post("/chat")
async def chat(body: ChatMessage) -> Dict[str, Any]:
    """Process a user chat message and route to the appropriate handler."""
    msg = body.message.strip().lower()
    if not msg:
        raise HTTPException(400, "Empty message")

    # Check close command first (has argument)
    close_match = re.match(r"close\s+(\w+)", msg)
    if close_match:
        return _handle_close(close_match.group(1))

    # Route through intent patterns
    for pattern, handler in _INTENT_PATTERNS:
        if re.search(pattern, msg):
            if handler is None:
                continue
            return handler()

    # Default: help
    help_result = _handle_help()
    help_result["reply"] = (
        f"I didn't understand \"{body.message}\".\n\n{help_result['reply']}"
    )
    return help_result


