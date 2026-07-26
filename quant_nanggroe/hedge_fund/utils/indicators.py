"""Technical analysis indicators."""

from quant_nanggroe.hedge_fund.utils.config import MT5_AVAILABLE, mt5


def calc_atr(symbol="EURUSD", period=14, tf=1):
    if not MT5_AVAILABLE:
        return None
    r = mt5.copy_rates_from_pos(symbol, 1, 0, period+2)
    if r is None or len(r) < period+1:
        return None
    trs = []
    for i in range(-period, 0):
        h, lo, pc = r[i][2], r[i][3], r[i-1][4]
        trs.append(max(h-lo, abs(h-pc), abs(lo-pc)))
    return sum(trs)/len(trs)
