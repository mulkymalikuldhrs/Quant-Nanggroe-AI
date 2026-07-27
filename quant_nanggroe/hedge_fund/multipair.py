"""
Multi-Pair Hedge Fund Executor
Scan ALL valid pairs → run Wyckoff + MeanReversion → rank → execute best signal
Logs all activity to data/trades.csv

Packaged version of E:/trading/hedge_fund_multipair.py for QNA integration.
Imports support tools from the local ``tools`` subpackage.
"""
import csv
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

_TOOLS_DIR = Path(__file__).resolve().parent / "tools"
sys.path.insert(0, str(_TOOLS_DIR))

import MetaTrader5 as mt5
from mtf_framework import STYLES, load_mtf, mtf_signal, strategy_wrapper
from risk_module import adaptive_risk

_HF_DIR = Path(__file__).resolve().parent
_DATA_DIR = _HF_DIR.parent / "data"
os.makedirs(_DATA_DIR, exist_ok=True)
LOG_FILE = _DATA_DIR / 'trades.csv'

log = logging.getLogger('mp_hf')

BEST_STRATEGIES = [
    ("WyckoffStrategy", {"lookback": 50, "volume_mult": 1.3}, "Wyckoff", 1.0),
    ("MeanReversionStrategy", {"k_period": 14, "d_period": 5, "oversold": 25, "overbought": 75}, "MeanRev", 0.85),
]


def compute_atr(symbol, period=14, tf=mt5.TIMEFRAME_M15):
    rates = mt5.copy_rates_from_pos(symbol, tf, 0, period + 2)
    if rates is None or len(rates) < period + 1:
        return 0.0010
    trs = []
    for i in range(-period, 0):
        h, l, pc = rates[i][2], rates[i][3], rates[i - 1][4]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return round(sum(trs) / len(trs), 6)


def calc_lot(balance, confidence):
    lot_min = max(0.01, round(balance / 10000, 2))
    lot_max = max(0.02, round(balance / 5000, 2))
    lot = round(lot_min + (lot_max - lot_min) * confidence, 2)
    return min(lot, lot_max)


def log_trade(action, symbol, lot, price, sl, tp, atr, result, pnl=""):
    fieldnames = ["time", "action", "symbol", "volume", "price", "sl", "tp", "atr", "result", "pnl"]
    exists = LOG_FILE.exists() and LOG_FILE.stat().st_size > 0
    with open(LOG_FILE, 'a', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if not exists:
            w.writeheader()
        w.writerow({
            "time": datetime.now().isoformat(), "action": action, "symbol": symbol,
            "volume": lot, "price": price, "sl": sl, "tp": tp, "atr": atr,
            "result": result, "pnl": pnl,
        })


def run_signal_on_pair(symbol, strategy_name, strategy_params, bars=300):
    mtf_data = load_mtf(symbol, bars)
    if not mtf_data:
        return None
    func = strategy_wrapper(strategy_name, **strategy_params)
    best = {"bias": "neutral", "confidence": 0, "style": ""}
    for style_name in STYLES:
        try:
            sig = mtf_signal(mtf_data, style_name, func)
        except Exception:
            continue
        if sig['confidence'] > best['confidence'] and sig['bias'] != 'neutral':
            best = {**sig, "style": style_name}
    return best if best['bias'] != 'neutral' else None


def evaluate_all_pairs(valid_pairs):
    candidates = []
    for pair in valid_pairs:
        symbol = pair['symbol']
        for strat_name, strat_params, strat_label, strat_weight in BEST_STRATEGIES:
            sig = run_signal_on_pair(symbol, strat_name, strat_params)
            if sig is None:
                continue
            combined = round(sig['confidence'] * strat_weight, 3)
            candidates.append({
                "symbol": symbol, "bias": sig['bias'], "confidence": combined,
                "style": sig['style'], "strategy": strat_label,
                "htf_bias": sig.get('htf_bias', 'neutral'),
                "bid": pair['bid'], "ask": pair['ask'], "spread": pair['spread'],
            })
            log.info(f"  📊 {symbol:8s} {strat_label:12s} {sig['bias']:5s} conf={combined:.2f} style={sig['style']}")
    candidates.sort(key=lambda c: c['confidence'], reverse=True)
    return candidates


def execute_best(candidate, balance):
    symbol = candidate['symbol']
    bias = candidate['bias']
    conf = candidate['confidence']
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        log.warning(f"  ❌ No tick for {symbol}")
        log_trade(f"fail_{bias}", symbol, 0, 0, 0, 0, 0, "no_tick")
        return False
    lot = calc_lot(balance, conf)
    atr_val = compute_atr(symbol)
    sl_dist = round(max(atr_val * 2, 0.0010), 5)
    if bias == "buy":
        price = tick.ask
        sl = round(price - sl_dist, 5)
        tp = round(price + sl_dist * 2, 5)
        order_type = mt5.ORDER_TYPE_BUY
    else:
        price = tick.bid
        sl = round(price + sl_dist, 5)
        tp = round(price - sl_dist * 2, 5)
        order_type = mt5.ORDER_TYPE_SELL
    req = {
        "action": mt5.TRADE_ACTION_DEAL, "symbol": symbol, "volume": lot,
        "type": order_type, "price": price, "sl": sl, "tp": tp,
        "deviation": 10, "magic": 20260719,
        "comment": f"MP {candidate['strategy']} {candidate['style']} {bias}",
        "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_IOC,
    }
    res = mt5.order_send(req)
    if res and res.retcode == 10009:
        log.info(f"  ✅ {bias.upper()} {lot} {symbol} @ {price:.5f} SL={sl} TP={tp}")
        log_trade(f"open_{bias}", symbol, lot, price, sl, tp, atr_val, f"executed (order={res.order})", pnl="")
        return True
    else:
        ret = res.retcode if res else "NONE"
        msg = res.comment if res else ""
        log.warning(f"  ❌ Order fail: code={ret} {msg}")
        log_trade(f"fail_{bias}", symbol, lot, price, sl, tp, atr_val, f"code={ret}")
        return False


def run_multipair_cycle():
    log.info("══════════════════════════════════════════")
    log.info("  Multi-Pair Hedge Fund Executor")
    log.info("══════════════════════════════════════════")
    if not mt5.initialize():
        log.error("MT5 unavailable")
        return
    acc = mt5.account_info()
    balance = acc.balance if acc else 1000
    log.info(f"💰 ${balance:.2f}  |  Account #{acc.login if acc else '?'}")
    try:
        from multi_pair_scanner import scan_all_pairs
        valid_pairs, skipped_pairs = scan_all_pairs()
    except Exception as e:
        log.error(f"Pair scan failed: {e}")
        valid_pairs, skipped_pairs = [], []
    if not valid_pairs:
        log.warning("No valid pairs after spread filter")
        mt5.shutdown()
        return
    log.info(f"  Valid: {len(valid_pairs)} pair(s)  Skipped: {len(skipped_pairs)}")
    positions = mt5.positions_get()
    if positions:
        for p in positions:
            log.info(f"📌 OPEN: {p.symbol} {p.type_name} Vol={p.volume} PnL=${p.profit:.2f}")
        log.info("  Positions exist — skipping new entries")
        mt5.shutdown()
        return
    log.info(f"\n── Evaluating {len(BEST_STRATEGIES)} strategies × {len(valid_pairs)} pairs ──")
    candidates = evaluate_all_pairs(valid_pairs)
    if not candidates:
        log.info("⏸ No signal on any pair")
        mt5.shutdown()
        return
    best = candidates[0]
    log.info(f"\n🏆 TOP SIGNAL: {best['symbol']:8s} {best['bias'].upper():5s}  conf={best['confidence']:.2f}  strategy={best['strategy']}  style={best['style']}")
    log.info(f"   Spread={best['spread']}p  HTF={best['htf_bias']}")
    risk = adaptive_risk(balance, 0.0015, 63, best.get('htf_bias', 'neutral'))
    log.info(f"   Risk: {risk['risk_per_trade_pct']}% per trade | Max lot {risk['max_lot']}")
    success = execute_best(best, balance)
    if success:
        log.info(f"🎯 Trade placed: {best['symbol']} {best['bias'].upper()} @ conf={best['confidence']:.2f}")
    else:
        log.warning(f"⚠️  Trade failed for top candidate")
    log.info(f"\n── Full ranking ({len(candidates)} candidate(s)) ──")
    for i, c in enumerate(candidates, 1):
        log.info(f"  #{i} {c['symbol']:8s} {c['bias']:5s}  conf={c['confidence']:.2f}  {c['strategy']:12s}  {c['style']}")
    mt5.shutdown()
    log.info("═══ Done ═══")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
    run_multipair_cycle()
