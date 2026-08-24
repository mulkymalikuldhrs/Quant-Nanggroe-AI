"""COT Position Guard — closes positions that conflict with smart money positioning.

FAZE 0+ (user mandate): "close old positions if they contradict the latest
COT release data". Runs every cycle, prioritised on Mondays when fresh COT
data from Friday becomes actionable.

Logic:
    1. Get all open MT5 positions
    2. For each symbol, fetch latest COT net positioning
    3. If position direction CONTRADICTS dominant positioning AND position
       is losing → close immediately (double confirmation)
    4. If CONFLICTING but WINNING → log warning, reduce next entry size
    5. If ALIGNED → no action

This is a RISK OVERLAY, not a signal generator.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("QNA.COTGuard")

# Symbol prefix → CFTC market name mapping
# Only FX majors + gold are covered (matches our trading universe)
_COT_SYMBOL_MAP = {
    "EUR": "Euro FX",
    "GBP": "British Pound Sterling",
    "JPY": "Japanese Yen",
    "AUD": "Australian Dollar",
    "NZD": "New Zealand Dollar",
    "CAD": "Canadian Dollar",
    "XAU": "GOLD",
    "GOLD": "GOLD",
}


def _symbol_to_cot_market(symbol: str) -> Optional[str]:
    """Map a trading symbol like EURUSD.vx or XAUUSD.vx to CFTC market name."""
    s = symbol.upper().replace(".VX", "").replace("-", "")
    for prefix, market in _COT_SYMBOL_MAP.items():
        if s.startswith(prefix):
            return market
    return None


def get_cot_positioning(symbol: str) -> Optional[Dict[str, Any]]:
    """Fetch latest COT positioning for a symbol.

    Returns:
        {
            "net_noncommercial": float,   # >0 = speculators net long
            "net_commercial": float,
            "open_interest": float,
            "report_date": str,
            "bias": "bullish"|"bearish"|"neutral",  # noncommercial bias
            "strength": float,             # |net| / open_interest, 0-1
        }
        None if symbol has no COT mapping or fetch fails.
    """
    try:
        from quant_nanggroe.core.scoring.positioning_scorer import (
            _fetch_cot_from_cftc,
        )
        raw = _fetch_cot_from_cftc(symbol)
        if not raw:
            return None

        nc_net = float(raw.get("noncomm_net", 0) or 0)
        oi = float(raw.get("open_interest", 0) or 0)
        strength = abs(nc_net) / max(oi, 1) if oi > 0 else 0

        if nc_net > 0:
            bias = "bullish"
        elif nc_net < 0:
            bias = "bearish"
        else:
            bias = "neutral"

        return {
            "net_noncommercial": nc_net,
            "net_commercial": float(raw.get("comm_net", 0) or 0),
            "open_interest": oi,
            "report_date": str(raw.get("report_date", "")),
            "bias": bias,
            "strength": round(strength, 4),
        }
    except Exception as e:
        logger.debug("COT fetch failed for %s: %s", symbol, e)
        return None


def check_position_conflict(
    symbol: str,
    side: str,
    pnl: float,
) -> Tuple[bool, Optional[str]]:
    """Check if an OPEN position conflicts with COT positioning.

    Args:
        symbol: Trading symbol (e.g. "EURUSD.vx").
        side: "buy" or "sell" (position direction).
        pnl: Current unrealized PnL.

    Returns:
        (should_close, reason)
        should_close=True only when: COT conflicts AND position is losing.
    """
    cot = get_cot_positioning(symbol)
    if cot is None or cot["bias"] == "neutral":
        return False, None

    side_lower = side.lower().strip()
    position_bullish = side_lower in ("buy", "long")
    cot_bullish = cot["bias"] == "bullish"

    # Check alignment
    aligned = (position_bullish and cot_bullish) or \
              (not position_bullish and not cot_bullish)

    if aligned:
        return False, f"COT_ALIGNED:{cot['bias']}"

    # Conflict detected
    conflict_reason = (
        f"COT_CONFLICT: position={side} but COT bias={cot['bias']} "
        f"(net_nc={cot['net_noncommercial']:.0f}, strength={cot['strength']})"
    )

    if pnl < 0:
        # Conflict AND losing — strong signal to close
        logger.warning(
            "%s %s: COT conflict + losing (PnL=%.2f). %s",
            symbol, side, pnl, conflict_reason,
        )
        return True, conflict_reason + "_LOSING"

    # Conflict but winning — warn only, let trailing stop handle exit
    logger.info(
        "%s %s: COT conflict but winning (PnL=%.2f). Monitoring.",
        symbol, side, pnl,
    )
    return False, conflict_reason + "_WINNING"


def scan_and_close_conflicts(
    em: Any,  # ExecutionManager instance
) -> List[Dict[str, Any]]:
    """Scan all open MT5 positions for COT conflicts and close losers.

    Args:
        em: ExecutionManager with broker access.

    Returns:
        List of closed position summaries.
    """
    if em is None:
        return []

    broker = getattr(em, "_mt5_handle", None) or getattr(em, "_broker_handle", None)
    if broker is None:
        logger.debug("COT guard: no MT5 broker handle available")
        return []

    mt5_mod = getattr(broker, "_mt5", None)
    if mt5_mod is None:
        return []

    try:
        positions = mt5_mod.positions_get() or []
    except Exception as e:
        logger.debug("positions_get failed: %s", e)
        return []

    if not positions:
        return []

    closed: List[Dict[str, Any]] = []
    for pos in positions:
        symbol = pos.symbol
        side = "buy" if pos.type == 0 else "sell"  # POSITION_TYPE_BUY=0
        pnl = float(getattr(pos, "profit", 0.0))

        should_close, reason = check_position_conflict(symbol, side, pnl)

        if should_close:
            logger.warning(
                "COT GUARD: closing %s %s (%.2f lots) — %s",
                side.upper(), symbol, pos.volume, reason,
            )
            try:
                # Submit opposite order to close
                close_side = "sell" if side == "buy" else "buy"
                tick = mt5_mod.symbol_info_tick(symbol)
                if tick is None:
                    continue
                price = tick.bid if close_side == "sell" else tick.ask

                req = {
                    "action": mt5_mod.TRADE_ACTION_DEAL,
                    "position": pos.ticket,
                    "symbol": symbol,
                    "volume": float(pos.volume),
                    "type": (mt5_mod.ORDER_TYPE_SELL if close_side == "sell"
                             else mt5_mod.ORDER_TYPE_BUY),
                    "price": price,
                    "deviation": 20,
                    "magic": 999999,  # distinct magic so we know it's a COT close
                    "comment": "cot_guard_close",
                    "type_filling": mt5_mod.ORDER_FILLING_FOK,
                    "type_time": mt5_mod.ORDER_TIME_GTC,
                }
                result = mt5_mod.order_send(req)
                if result and result.retcode == mt5_mod.TRADE_RETCODE_DONE:
                    closed.append({
                        "ticket": pos.ticket, "symbol": symbol,
                        "side": side, "pnl": pnl, "reason": reason,
                    })
                    logger.info("COT GUARD CLOSED: ticket=%d PnL=%.2f",
                                pos.ticket, pnl)
                else:
                    retcode = getattr(result, "retcode", "?") if result else "?"
                    logger.error("COT close failed: retcode=%s", retcode)
            except Exception as exc:
                logger.error("COT close exception for %s: %s", symbol, exc)

    return closed
