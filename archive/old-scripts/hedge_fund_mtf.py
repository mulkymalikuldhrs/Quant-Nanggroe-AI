"""
Hedge Fund MTF — multi-timeframe execution
Wyckoff Volume Spread across 5 trading styles
"""
import sys, logging, json, os
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent))

from mtf_framework import STYLES, load_mtf, mtf_signal, strategy_wrapper
from risk_module import adaptive_risk
from risk_guard import approve as risk_guard_approve
import MetaTrader5 as mt5

SRC = Path(r'E:/trading')
log = logging.getLogger('hfmtf')

BEST_STRATEGIES = [
    ("WyckoffStrategy", {"lookback": 50, "volume_mult": 1.3}, "Volume Spread"),
    ("MeanReversionStrategy", {"k_period": 14, "d_period": 5, "oversold": 25, "overbought": 75}, "Stochastic MeanRev"),
    ("DhaherSystem", {"lookback": 14, "atr_mult": 1.5, "rr_min": 2.0, "min_confluence": 2}, "Dhaher System v1.1"),
    # NEW: Kronos Signal Provider #10
    ("KronosSignalProvider", {"lookback": 200, "pred_len": 10, "signal_threshold": 0.0015}, "Kronos Foundation Model (AAAI 2026)"),
    ("KronosEnsembleStrategy", {"lookback": 200, "pred_len": 10, "signal_threshold": 0.002, "trend_filter": True}, "Kronos Ensemble + Trend"),
    # NEW: TradeBobby SMC Scanner
    ("TradeBobbySMCStrategy", {"swing_lookback": 5, "min_confluence": 3, "ob_displacement": 1.5}, "TradeBobby SMC Scanner"),
]

def run_mtf_cycle():
    """Multi-timeframe analysis → multi-pair scan → trade best"""
    log.info("═══ MTF Hedge Fund ═══")
    
    if not mt5.initialize():
        log.error("MT5 unavailable"); return
    
    a = mt5.account_info()
    bal = a.balance if a else 1000
    log.info(f"💰 ${bal:.2f}")
    
    # Multi-pair scan: cari semua pair yang lolos filter spread
    log.info("📡 Scanning all pairs...")
    from multi_pair_scanner import scan_all_pairs
    valid_pairs, _ = scan_all_pairs()
    log.info(f"   {len(valid_pairs)} pairs tradable")
    
    # Market context: fundamental data
    log.info("📊 Market context:")
    from market_context import market_context
    ctx = market_context()
    log.info(f"   DXY: {ctx['dxy']['price']} ({ctx['dxy']['trend']}) | Yield: {ctx.get('yield_10y',{}).get('yield','?')}% {ctx.get('yield_10y',{}).get('trend','')}")
    log.info(f"   Sentiment: {ctx.get('sentiment',{}).get('label','?')} (VIX: {ctx.get('sentiment',{}).get('vix','?')}) | Geo: {ctx.get('geopolitics',{}).get('score',0)}/100")
    log.info(f"   FX: {', '.join(f'{k}{v:+.1f}%' for k,v in list(ctx.get('currency_strength',{}).items())[:5])}")
    log.info(f"   USD: EUR={'📈' if ctx['eurusd_bias']=='buy' else '📉'} GBP={'📈' if ctx.get('currency_strength',{}).get('GBP',0)>0 else '📉'} JPY={'📈' if ctx.get('currency_strength',{}).get('JPY',0)<0 else '📉'} XAU={'📈' if ctx['dxy']['trend']=='bear' else '📉'}")
    cot = ctx.get('cot', {})
    if isinstance(cot, dict):
        for pair in ["EURUSD", "GBPUSD", "XAU", "XAG"]:
            data = cot.get(pair, {})
            if isinstance(data, dict) and 'net' in data:
                oi_str = f" OI={data['oi']:,}" if data.get('oi', 0) else ""
                log.info(f"   COT {pair}: net={data['net']:+d}{oi_str} ({data.get('bias','?')}) src={data.get('source','?')}")
    cal = ctx.get('economic_calendar', {})
    if cal.get('next_event'):
        log.info(f"   Calendar: {cal['next_event']['title']} ({cal['next_event']['country']}) - {cal['next_event']['impact']}")
    # XAU/XAG
    try:
        import yfinance as yf
        for sym, name in [("GC=F", "XAU"), ("SI=F", "XAG")]:
            t = yf.Ticker(sym)
            h = t.history(period="5d")
            if len(h) > 1:
                p = h.iloc[-1]['Close']
                chg = (p - h.iloc[-2]['Close']) / h.iloc[-2]['Close'] * 100
                log.info(f"   {name}: ${p:.0f} ({'+' if chg>0 else ''}{chg:.1f}%) {'📈' if chg>0 else '📉'}")
    except: pass
    
    if not valid_pairs:
        log.warning("No tradable pairs — skipping")
        mt5.shutdown(); return
    
    # Prioritaskan pair dengan spread terendah
    best_pair = min(valid_pairs, key=lambda p: p['spread'])
    symbol = best_pair['symbol']
    log.info(f"   Best pair: {symbol} (spread={best_pair['spread']}p)")
    
    # Load MTF data untuk pair terbaik
    from mtf_framework import load_mtf, STYLES, mtf_signal, strategy_wrapper
    mtf_data = load_mtf(symbol, 500)
    if not mtf_data:
        mt5.shutdown(); return
    
    # Eval ALL best strategies across ALL styles → pick best signal
    best_signal = {"bias": "neutral", "confidence": 0, "style": "", "strategy": ""}
    
    for strat_name, strat_params, strat_label in BEST_STRATEGIES:
        func = strategy_wrapper(strat_name, **strat_params)
        for style_name in STYLES:
            sig = mtf_signal(mtf_data, style_name, func)
            log.info(f"  {strat_label:20s} {style_name:12s}: {sig['bias']:8s} conf={sig['confidence']:.2f} HTF={sig['htf_bias']}")
            if sig['confidence'] > best_signal['confidence'] and sig['bias'] != 'neutral':
                best_signal = {**sig, "style": style_name, "strategy": strat_name, "strategy_label": strat_label}
    
    # Risk
    risk = adaptive_risk(bal, 0.0015, 63, best_signal.get('htf_bias', 'neutral'))
    
    pos = mt5.positions_get()
    if pos:
        for p in pos:
            log.info(f"📌 OPEN: {p.symbol} {'BUY' if p.type==0 else 'SELL'} PnL=${p.profit:.2f}")
    elif best_signal['bias'] in ('buy','sell'):
        strat_label = best_signal.get('strategy_label', best_signal.get('strategy', 'MTF'))
        log.info(f"🎯 SIGNAL: {best_signal['bias'].upper()} | {strat_label} | Style={best_signal['style']} | Conf={best_signal['confidence']:.0%}")
        log.info(f"   Risk: {risk['risk_per_trade_pct']}% per trade | Lot max {risk['max_lot']}")
        execute_mtf(best_signal, bal, symbol)
    else:
        log.info("⏸ No signal across any style")
    
    mt5.shutdown()

def execute_mtf(signal, balance, symbol):
    sym = symbol; t = mt5.symbol_info_tick(sym)
    lot = round(max(0.01, balance/10000) + (balance/5000 - balance/10000)*signal['confidence'], 2)
    atr = 0.0015; sd = max(atr*2, 0.0010)
    
    if signal['bias'] == 'buy':
        p,sl,tp,ot = t.ask, round(t.ask-sd,5), round(t.ask+sd*2,5), mt5.ORDER_TYPE_BUY
    else:
        p,sl,tp,ot = t.bid, round(t.bid+sd,5), round(t.bid-sd*2,5), mt5.ORDER_TYPE_SELL
    
    # Check symbol trade mode — Valetax demo .vx = short only (mode 4)
    sym_info = mt5.symbol_info(sym)
    if sym_info:
        if sym_info.trade_mode == 4 and ot == mt5.ORDER_TYPE_BUY:
            log.warning(f"⛔ {sym} is SHORT ONLY — skipping BUY order")
            return
        if sym_info.trade_mode == 3 and ot == mt5.ORDER_TYPE_SELL:
            log.warning(f"⛔ {sym} is LONG ONLY — skipping SELL order")
            return
        # Use supported filling mode
        fill = mt5.ORDER_FILLING_FOK if sym_info.filling_mode & 1 else mt5.ORDER_FILLING_IOC
    else:
        fill = mt5.ORDER_FILLING_IOC
    
    req = {"action":mt5.TRADE_ACTION_DEAL,"symbol":sym,"volume":lot,"type":ot,
           "price":p,"sl":sl,"tp":tp,"deviation":10,"magic":20260719,
           "comment":f"MTF {signal['style']} {signal['bias']}",
           "type_time":mt5.ORDER_TIME_GTC,"type_filling":fill}
    
    # Risk Guard gate — veto sebelum eksekusi
    # FIX: daily_pnl HARUS nilai REAL dari MT5, bukan literal 0.
    # Literal 0 -> loss_ratio selalu 0 -> daily-loss veto MATI (silent-disable).
    try:
        _today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        _deals = mt5.history_deals_get(_today, datetime.now())
        daily_pnl = float(sum(d.profit for d in _deals)) if _deals else 0.0
    except Exception:
        daily_pnl = 0.0
    # FIX phantom-veto (2026-07-21): jangan pakai floating account_info().profit
    # sebagai daily_pnl. Demo account dgn open posisi floating -$100 (10% dari
    # $1000) memicu daily_loss_limit_hit VETOED padahal ZERO real fills.
    # Hanya realized deals yg dihitung; kalau kosong -> 0.0 (bukan floating).
    if daily_pnl == 0.0:
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
