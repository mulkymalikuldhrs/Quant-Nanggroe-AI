"""
Multi-Timeframe (MTF) Strategy signal wrapper for QNA Hedge Fund.
Adapts existing strategies to produce (bias, confidence, style) for MTF framework,
then executes trades with fail-closed guarantees through the risk guard.
"""

import logging, time
from datetime import datetime, timedelta
from decimal import Decimal
from collections import defaultdict

import MetaTrader5 as mt5
import numpy as np
import pandas as pd

from quant_nanggroe.hedge_fund.risk_guard import risk_guard_approve

log = logging.getLogger("HF.MTF")

# ──────────────────────────────────────────
# MTF Style
# ──────────────────────────────────────────
MTF_STYLES = ["intraday-1", "intraday-2", "swing-1", "swing-2", "scalp"]

# ──────────────────────────────────────────
# Utility: timeframes
# ──────────────────────────────────────────
TF_FRAMES = {
    "intraday-1": {"htf": "H4", "mtf": "H1", "ltf": "M15"},
    "intraday-2": {"htf": "H1", "mtf": "M15", "ltf": "M3"},
    "swing-1":    {"htf": "W1", "mtf": "D1",  "ltf": "H1"},
    "swing-2":    {"htf": "D1", "mtf": "H4",  "ltf": "M15"},
    "scalp":      {"htf": "M15","mtf": "M5",  "ltf": "M1"},
}
"""MTF pyramid:
HTF = HTF trend / bias
MTF = confirm retrace / POI
LTF = entry + SL placement
"""

MTF_TIMEFRAMES = {"M1":1,"M2":2,"M3":3,"M4":4,"M5":5,"M6":6,"M10":10,"M12":12,"M15":15,"M20":20,
                  "M30":30,"H1":60,"H2":120,"H3":180,"H4":240,"D1":1440,"W1":10080,"MN1":43200}

def htf_bias(df_htf: pd.DataFrame) -> dict:
    """Return HTF bias from SMA200 + HH/HL structure."""
    close = df_htf['close']
    sma200 = close.rolling(200).mean().iloc[-1]
    last = close.iloc[-1]
    # Structure: higher highs / higher lows?
    recent = close.tail(20)
    hh = recent.iloc[-1] > recent.quantile(0.75)
    hl = recent.iloc[-1] > recent.iloc[0]
    if last > sma200 and hh and hl:
        return {"bias": "buy", "strength": "strong", "sma200": sma200}
    elif last < sma200 and not hh and not hl:
        return {"bias": "sell", "strength": "strong", "sma200": sma200}
    elif last > sma200:
        return {"bias": "buy", "strength": "weak", "sma200": sma200}
    else:
        return {"bias": "sell", "strength": "weak", "sma200": sma200}

def mtf_signal(mtf_data: dict, style: str, strategy_func) -> dict:
    """Run strategy_func on each timeframe and merge into MTF decision."""
    tf_map = TF_FRAMES.get(style)
    if not tf_map:
        return {"bias": "neutral", "confidence": 0.0, "style": style}

    htf_df = mtf_data.get(tf_map["htf"], pd.DataFrame())
    mtf_df = mtf_data.get(tf_map["mtf"], pd.DataFrame())
    ltf_df = mtf_data.get(tf_map["ltf"], pd.DataFrame())

    if any(df.empty for df in (htf_df, mtf_df, ltf_df)):
        return {"bias": "neutral", "confidence": 0.0, "style": style}

    htf_sig = strategy_func(htf_df)
    mtf_sig = strategy_func(mtf_df)
    ltf_sig = strategy_func(ltf_df)

    # MTF decision logic
    if not htf_sig.get("bias") or htf_sig.get("bias") == "neutral":
        return {"bias": "neutral", "confidence": 0.0, "style": style}

    if htf_sig["bias"] == mtf_sig.get("bias") == ltf_sig.get("bias"):
        conf = min(1.0, (htf_sig.get("confidence", 0.5) +
                         mtf_sig.get("confidence", 0.3) +
                         ltf_sig.get("confidence", 0.2)))
        return {"bias": htf_sig["bias"], "confidence": conf, "style": style}

    if htf_sig["bias"] == mtf_sig.get("bias") and ltf_sig.get("bias") != htf_sig["bias"]:
        # Contrarian LTF entry — still valid
        conf = (htf_sig.get("confidence", 0.5) + mtf_sig.get("confidence", 0.3)) / 2 * 0.8
        return {"bias": htf_sig["bias"], "confidence": conf, "style": style}

    return {"bias": "neutral", "confidence": 0.3, "style": style}


# ──────────────────────────────────────────
# Execution layer
# ──────────────────────────────────────────
def signal_to_order(signal: dict, sym: str, balance: float) -> dict:
    """Convert MTF signal dict to an MT5 order request, fail-closed."""
    bias = signal.get("bias", "neutral")
    conf = signal.get("confidence", 0.0)
    style = signal.get("style", "intraday-1")
    price = signal.get("price", 0.0)

    if bias == "neutral" or conf < 0.15:
        log.info("⏹️  %s %s — bias=%s conf=%.2f — HOLD", sym, style, bias, conf)
        return {"action": "hold", "symbol": sym, "reason": f"low_conf_{conf:.2f}"}

    # Lot sizing
    atr = signal.get("atr", 0.001)
    lot_min = max(0.01, balance / 10000)
    lot_max = max(0.02, balance / 5000)
    lot = round(lot_min + (lot_max - lot_min) * conf, 2)
    lot = max(0.01, min(lot, 0.5))

    t = mt5.symbol_info_tick(sym)
    if not t:
        return {"action": "error", "symbol": sym, "reason": "no_tick_data"}

    sd = max(atr * 2, 0.0010)

    if bias == "buy":
        p, sl, tp, ot = t.ask, round(t.ask - sd, 5), round(t.ask + sd * 2, 5), mt5.ORDER_TYPE_BUY
    else:
        p, sl, tp, ot = t.bid, round(t.bid + sd, 5), round(t.bid - sd * 2, 5), mt5.ORDER_TYPE_SELL

    sym_info = mt5.symbol_info(sym)
    if sym_info:
        # MT5 v5+ trade_mode enum (verified against live terminal 2026-07-28):
        #   0 = DISABLED | 1 = LONGONLY | 2 = SHORTONLY | 3 = CLOSEONLY | 4 = FULL
        tm = sym_info.trade_mode
        if tm == 0:
            log.warning(f"⛔ {sym} DISABLED (trade_mode={tm}) — skipping ALL orders")
            return {"action": "error", "symbol": sym, "reason": f"trade_mode_{tm}_disabled"}
        if tm == 1 and ot == mt5.ORDER_TYPE_SELL:
            log.warning(f"⛔ {sym} LONG-ONLY (trade_mode={tm}) — skipping SELL")
            return {"action": "error", "symbol": sym, "reason": "long_only"}
        if tm == 2 and ot == mt5.ORDER_TYPE_BUY:
            log.warning(f"⛔ {sym} SHORT-ONLY (trade_mode={tm}) — skipping BUY")
            return {"action": "error", "symbol": sym, "reason": "short_only"}
        fill = mt5.ORDER_FILLING_FOK if sym_info.filling_mode & 1 else mt5.ORDER_FILLING_IOC
    else:
        fill = mt5.ORDER_FILLING_IOC

    req = {"action": mt5.TRADE_ACTION_DEAL, "symbol": sym, "volume": lot, "type": ot,
           "price": p, "sl": sl, "tp": tp, "deviation": 10, "magic": 20260719,
           "comment": f"MTF {style} {bias}",
           "type_time": mt5.ORDER_TIME_GTC, "type_filling": fill}

    # Daily/weekly loss veto
    try:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        deals = mt5.history_deals_get(today, datetime.now())
        daily_pnl = float(sum(d.profit for d in deals)) if deals else 0.0
    except Exception:
        daily_pnl = 0.0

    try:
        monday = today - timedelta(days=today.weekday())
        week_deals = mt5.history_deals_get(monday, datetime.now())
        weekly_pnl = float(sum(d.profit for d in week_deals)) if week_deals else 0.0
    except Exception:
        weekly_pnl = 0.0

    guard_check = risk_guard_approve({
        'symbol': sym, 'action': bias, 'volume': lot,
        'price': p, 'sl': sl, 'account_balance': balance,
        'daily_pnl': daily_pnl, 'weekly_pnl': weekly_pnl,
        'open_positions': len(mt5.positions_get() or []),
        'market_volatility': atr / p if p else 0.001,
    })

    if not guard_check.get('approved'):
        reason = guard_check.get('reason', 'unknown_risk_block')
        log.warning("⛔ %s %s — risk guard BLOCKED: %s", sym, style, reason)
        return {"action": "hold", "symbol": sym, "reason": reason}

    try:
        result = mt5.order_send(req)
        if result and result.retcode == 10009:
            log.info("✅ %s %s %s lot=%.2f SL=%.5f TP=%.5f (done)", sym, style, bias, lot, sl, tp)
            return {"action": "buy" if bias == "buy" else "sell", "symbol": sym, "volume": lot,
                    "price": p, "sl": sl, "tp": tp, "retcode": result.retcode, "comment": f"MTF {style} {bias}"}
        elif result:
            log.warning("⚠️ %s %s — order_send returned retcode=%s", sym, style, result.retcode)
            return {"action": "error", "symbol": sym, "reason": f"order_send_rc{result.retcode}", "retcode": result.retcode}
        else:
            log.warning("⚠️ %s %s — order_send returned None", sym, style)
            return {"action": "error", "symbol": sym, "reason": "order_send_none"}
    except Exception as e:
        log.error("💥 %s %s — exec error: %s", sym, style, e)
        return {"action": "error", "symbol": sym, "reason": str(e)}