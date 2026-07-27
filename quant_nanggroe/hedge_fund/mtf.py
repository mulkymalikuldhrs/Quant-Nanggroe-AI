"""
Hedge Fund MTF — multi-timeframe execution
Wyckoff Volume Spread across 5 trading styles

Packaged version of E:/trading/hedge_fund_mtf.py for QNA integration.
Imports support tools from the local ``tools`` subpackage (no E:/trading dependency).
"""
import logging
import sys
from datetime import datetime
from pathlib import Path

# Ensure local tools are importable
_TOOLS_DIR = Path(__file__).resolve().parent / "tools"
sys.path.insert(0, str(_TOOLS_DIR))

import MetaTrader5 as mt5
from mtf_framework import STYLES, load_mtf, mtf_signal, strategy_wrapper
from risk_guard import approve as risk_guard_approve
from risk_module import adaptive_risk

try:
    from market_context import market_context
except Exception:  # pragma: no cover - market context is best-effort
    market_context = None

log = logging.getLogger('hfmtf')

BEST_STRATEGIES = [
    ("WyckoffStrategy", {"lookback": 50, "volume_mult": 1.3}, "Volume Spread"),
    ("MeanReversionStrategy", {"k_period": 14, "d_period": 5, "oversold": 25, "overbought": 75}, "Stochastic MeanRev"),
    ("DhaherSystem", {"lookback": 14, "atr_mult": 1.5, "rr_min": 2.0, "min_confluence": 2}, "Dhaher System v1.1"),
    ("KronosSignalProvider", {"lookback": 200, "pred_len": 10, "signal_threshold": 0.0015}, "Kronos Foundation Model (AAAI 2026)"),
    ("KronosEnsembleStrategy", {"lookback": 200, "pred_len": 10, "signal_threshold": 0.002, "trend_filter": True}, "Kronos Ensemble + Trend"),
    ("TradeBobbySMCStrategy", {"swing_lookback": 5, "min_confluence": 3, "ob_displacement": 1.5}, "TradeBobby SMC Scanner"),
]


def run_mtf_cycle():
    """Multi-timeframe analysis → multi-pair scan → trade best"""
    log.info("═══ MTF Hedge Fund ═══")

    if not mt5.initialize():
        log.error("MT5 unavailable")
        return

    a = mt5.account_info()
    bal = a.balance if a else 1000
    log.info(f"💰 ${bal:.2f}")

    log.info("📡 Scanning all pairs...")
    try:
        from multi_pair_scanner import scan_all_pairs
        valid_pairs, _ = scan_all_pairs()
    except Exception as e:
        log.error(f"Pair scan failed: {e}")
        valid_pairs = []
    log.info(f"   {len(valid_pairs)} pairs tradable")

    if market_context:
        try:
            ctx = market_context()
            log.info(f"   DXY: {ctx['dxy']['price']} ({ctx['dxy']['trend']})")
        except Exception as e:
            log.warning(f"Market context unavailable: {e}")

    if not valid_pairs:
        log.warning("No tradable pairs — skipping")
        mt5.shutdown()
        return

    best_pair = min(valid_pairs, key=lambda p: p['spread'])
    symbol = best_pair['symbol']
    log.info(f"   Best pair: {symbol} (spread={best_pair['spread']}p)")

    mtf_data = load_mtf(symbol, 500)
    if not mtf_data:
        mt5.shutdown()
        return

    best_signal = {"bias": "neutral", "confidence": 0, "style": "", "strategy": ""}

    for strat_name, strat_params, strat_label in BEST_STRATEGIES:
        func = strategy_wrapper(strat_name, **strat_params)
        for style_name in STYLES:
            sig = mtf_signal(mtf_data, style_name, func)
            log.info(f"  {strat_label:20s} {style_name:12s}: {sig['bias']:8s} conf={sig['confidence']:.2f} HTF={sig['htf_bias']}")
            if sig['confidence'] > best_signal['confidence'] and sig['bias'] != 'neutral':
                best_signal = {**sig, "style": style_name, "strategy": strat_name, "strategy_label": strat_label}

    risk = adaptive_risk(bal, 0.0015, 63, best_signal.get('htf_bias', 'neutral'))

    pos = mt5.positions_get()
    if pos:
        for p in pos:
            log.info(f"📌 OPEN: {p.symbol} {'BUY' if p.type == 0 else 'SELL'} PnL=${p.profit:.2f}")
    elif best_signal['bias'] in ('buy', 'sell'):
        strat_label = best_signal.get('strategy_label', best_signal.get('strategy', 'MTF'))
        log.info(f"🎯 SIGNAL: {best_signal['bias'].upper()} | {strat_label} | Style={best_signal['style']} | Conf={best_signal['confidence']:.0%}")
        log.info(f"   Risk: {risk['risk_per_trade_pct']}% per trade | Lot max {risk['max_lot']}")
        execute_mtf(best_signal, bal, symbol)
    else:
        log.info("⏸ No signal across any style")

    mt5.shutdown()


def execute_mtf(signal, balance, symbol):
    sym = symbol
    t = mt5.symbol_info_tick(sym)
    if not t:
        log.warning(f"No tick for {sym}")
        return
    lot = round(max(0.01, balance / 10000) + (balance / 5000 - balance / 10000) * signal['confidence'], 2)
    atr = 0.0015
    sd = max(atr * 2, 0.0010)

    if signal['bias'] == 'buy':
        p, sl, tp, ot = t.ask, round(t.ask - sd, 5), round(t.ask + sd * 2, 5), mt5.ORDER_TYPE_BUY
    else:
        p, sl, tp, ot = t.bid, round(t.bid + sd, 5), round(t.bid - sd * 2, 5), mt5.ORDER_TYPE_SELL

    sym_info = mt5.symbol_info(sym)
    if sym_info:
        if sym_info.trade_mode == 4 and ot == mt5.ORDER_TYPE_BUY:
            log.warning(f"⛔ {sym} is SHORT ONLY — skipping BUY order")
            return
        if sym_info.trade_mode == 3 and ot == mt5.ORDER_TYPE_SELL:
            log.warning(f"⛔ {sym} is LONG ONLY — skipping SELL order")
            return
        fill = mt5.ORDER_FILLING_FOK if sym_info.filling_mode & 1 else mt5.ORDER_FILLING_IOC
    else:
        fill = mt5.ORDER_FILLING_IOC

    req = {"action": mt5.TRADE_ACTION_DEAL, "symbol": sym, "volume": lot, "type": ot,
           "price": p, "sl": sl, "tp": tp, "deviation": 10, "magic": 20260719,
           "comment": f"MTF {signal['style']} {signal['bias']}",
           "type_time": mt5.ORDER_TIME_GTC, "type_filling": fill}

    try:
        _today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        _deals = mt5.history_deals_get(_today, datetime.now())
        daily_pnl = float(sum(d.profit for d in _deals)) if _deals else 0.0
    except Exception:
        daily_pnl = 0.0

    guard_check = risk_guard_approve({
        'symbol': sym, 'action': signal['bias'], 'volume': lot,
        'price': p, 'sl': sl, 'account_balance': balance,
        'daily_pnl': daily_pnl, 'open_positions': len(mt5.positions_get() or []),
        'market_volatility': atr / p if p else 0.001,
    })
    if guard_check['status'] == 'VETOED':
        log.warning(f"🛑 RISK GUARD VETOED: {sym} {signal['bias']} — {'; '.join(guard_check['reasons'])}")
        return

    res = mt5.order_send(req)
    if res and res.retcode == 10009:
        log.info(f"✅ {signal['bias'].upper()} {lot} {sym} @ {p:.5f}")
    else:
        log.warning(f"Order: {res.retcode if res else 'NONE'} {res.comment if res else ''}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
    run_mtf_cycle()
