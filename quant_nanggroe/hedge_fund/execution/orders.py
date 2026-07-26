"""Trade execution and position management."""

import csv
from datetime import datetime

from quant_nanggroe.engine.kelly import FractionalKelly, KellyParameters, KellyMethod
from quant_nanggroe.hedge_fund.utils.config import (
    LOG_FILE, PAPER_LOG, PAPER_TRADE, log, mt5,
)
from quant_nanggroe.hedge_fund.utils.indicators import calc_atr


_MT5_CREDS_CHECKED = False


def trail_sl(pos, tf=mt5.TIMEFRAME_M1, step_pips=10):
    if pos.sl is None:
        return None
    rates = mt5.copy_rates_from_pos(pos.symbol, tf, 0, 15)
    if rates is None or len(rates) < 10:
        return None
    highs = [r[2] for r in rates[-10:]]
    lows = [r[3] for r in rates[-10:]]
    pip = 0.0001
    try:
        sinfo = mt5.symbol_info(pos.symbol)
        if sinfo and sinfo.trade_tick_size:
            pip = float(sinfo.trade_tick_size)
    except Exception:
        pass
    step = step_pips * pip
    if pos.type == 0:
        extreme = max(highs[-5:])
        candidate = extreme - step
        if candidate > pos.sl and candidate < pos.price_open:
            return round(candidate, 5)
    else:
        extreme = min(lows[-5:])
        candidate = extreme + step
        if candidate < pos.sl and candidate > pos.price_open:
            return round(candidate, 5)
    return None


def kelly_lot_size(balance, symbol, confidence):
    try:
        kelly = FractionalKelly(fraction=0.25)
        params = KellyParameters(
            win_rate=0.55,
            avg_win=0.012,
            avg_loss=0.008,
            fraction=0.25,
            leverage_max=0.02,
        )
        if not PAPER_TRADE and mt5 is not None:
            try:
                from datetime import datetime as _dt
                deals = mt5.history_deals_get(_dt(1970, 1, 1), _dt.now())
                if deals and len(deals) > 5:
                    wins = [d.profit for d in deals if d.profit > 0]
                    losses = [abs(d.profit) for d in deals if d.profit < 0]
                    if wins and losses:
                        params.win_rate = len(wins) / len(deals)
                        params.avg_win = sum(wins) / len(wins) / balance if balance > 0 else params.avg_win
                        params.avg_loss = sum(losses) / len(losses) / balance if balance > 0 else params.avg_loss
            except Exception:
                pass

        result = kelly.compute(params)
        kelly_fraction = max(0.01, min(result.f_star, params.leverage_max))
    except Exception as e:
        log.warning(f"Kelly computation failed: {e}, using 0.01 fallback")
        kelly_fraction = 0.01

    contract_size = 100000.0
    pip_size = 0.0001
    if not PAPER_TRADE:
        try:
            sinfo = mt5.symbol_info(symbol)
            if sinfo:
                contract_size = float(sinfo.trade_contract_size or 100000.0)
                pip_size = float(sinfo.trade_tick_size or 0.0001)
        except Exception:
            pass

    atr_val = calc_atr(symbol) or 0.0010
    sl_dist = max(atr_val * 2, 0.0010)
    sl_pips = sl_dist / pip_size if pip_size > 0 else sl_dist / 0.0001
    dollar_per_pip_per_lot = contract_size * pip_size

    risk_amount = balance * kelly_fraction
    raw_lot = (risk_amount / (sl_pips * dollar_per_pip_per_lot)) if (sl_pips * dollar_per_pip_per_lot) > 0 else 0.01
    conf = max(0.1, min(1.0, confidence))
    lot = round(raw_lot * conf, 2)
    lot = max(0.01, lot)
    notional_cap_lot = max(0.01, round((balance * kelly_fraction * 2) / (1.0 / contract_size) if contract_size > 0 else 0.02, 2))
    lot = min(lot, notional_cap_lot)
    lot = max(0.01, lot)
    return lot


def execute(sig, symbol="EURUSD"):
    sym = symbol
    t = None
    if not PAPER_TRADE:
        t = mt5.symbol_info_tick(sym)

    a = mt5.account_info() if not PAPER_TRADE else None
    if not PAPER_TRADE and a is None:
        log.error("MT5 account_info() returned None in live mode - cannot trade")
        return None
    bal = a.balance if a else (1000.0 if PAPER_TRADE else 0.0)
    lot = kelly_lot_size(
        balance=bal,
        symbol=sym,
        confidence=sig.get("confidence", 0.5),
    )
    atr = calc_atr(sym) or 0.0010
    sd = max(atr * 2, 0.0010)
    log.info(f"   Balance=${bal:.0f} -> Lot={lot} (Kelly-optimized, conf={sig.get('confidence', 0.5):.2f})")

    atr = calc_atr(sym) or 0.0010
    sd = max(atr*2, 0.0010)

    if PAPER_TRADE:
        raise RuntimeError(
            f"Paper trade blocked for {sym} — no real price available. "
            "Cannot generate simulated price. Failing closed."
        )

    if sig["bias"] == "buy":
        p, sl, tp, ot = t.ask, round(t.ask-sd,5), round(t.ask+sd*2,5), mt5.ORDER_TYPE_BUY
    else:
        p, sl, tp, ot = t.bid, round(t.bid+sd,5), round(t.bid-sd*2,5), mt5.ORDER_TYPE_SELL

    req = {"action":mt5.TRADE_ACTION_DEAL,"symbol":sym,"volume":lot,"type":ot,
           "price":p,"sl":sl,"tp":tp,"deviation":10,"magic":20260718,
           "comment":f"HFv3 {sig['bias']}","type_time":mt5.ORDER_TIME_GTC,"type_filling":mt5.ORDER_FILLING_IOC}
    res = mt5.order_send(req)
    if res and res.retcode == 10009:
        log.info(f"{sig['bias'].upper()} {lot} {sym} @ {p:.5f} SL={sl} TP={tp}")
        with open(LOG_FILE, 'a', newline='') as f:
            w = csv.writer(f)
            if not LOG_FILE.exists() or LOG_FILE.stat().st_size == 0:
                w.writerow(["time","action","symbol","lot","price","sl","tp","atr","providers","result"])
            srcs = ",".join(v["source"] for v in sig.get("votes",[]))
            w.writerow([datetime.now().isoformat(), f"open_{sig['bias']}", sym, lot, p, sl, tp, round(atr,6), srcs, "executed"])
        return res.order
    log.warning(f"Order fail: {res.retcode if res else 'NONE'} {res.comment if res else ''}")
    return None
