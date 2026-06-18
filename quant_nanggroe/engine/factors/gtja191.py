"""Guotai Junan 191 Alphas.

Implements ALL 191 alphas from the Guotai Junan 191 Alpha research report (2014).

These alphas focus on Chinese A-share market characteristics including:
- Volume-price dynamics
- Intraday return patterns
- Cross-sectional momentum/reversal

Reference: 国泰君安 191 alpha 研报 (2014)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from quant_nanggroe.engine.factors.base import (
    decay_linear,
    delta,
    rank,
    safe_div,
    scale,
    signed_power,
    ts_argmax,
    ts_argmin,
    ts_corr,
    ts_cov,
    ts_max,
    ts_mean,
    ts_min,
    ts_rank,
    ts_std,
    vwap,
)

__alpha_meta_alpha_001 = {
    "id": "gtja191_001",
    "theme": ['volume', 'reversal'],
    "formula_latex": '(-1 * CORR(RANK(DELTA(LOG(VOLUME), 1)), RANK(((CLOSE - OPEN) / OPEN)), 6))',
    "columns_required": ['volume', 'close', 'open'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 6,
    "min_warmup_bars": 7,
    "notes": 'Standard GTJA #1: lag-1 log-volume change rank vs intraday return rank, 6d corr.',
}

def compute_alpha_001(panel: dict) -> pd.DataFrame:
    v = panel["volume"]
    c = panel["close"]
    o = panel["open"]
    x = rank(delta(np.log(v.where(v > 0)), 1))
    y = rank(safe_div(c - o, o))
    return -1.0 * ts_corr(x, y, 6)


__alpha_meta_alpha_002 = {
    "id": "gtja191_002",
    "theme": ['reversal', 'microstructure'],
    "formula_latex": '(-1 * DELTA(((CLOSE - LOW) - (HIGH - CLOSE)) / (HIGH - LOW), 1))',
    "columns_required": ['close', 'high', 'low'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 1,
    "min_warmup_bars": 2,
    "notes": 'Daily change in close-position-within-range.',
}

def compute_alpha_002(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    h = panel["high"]
    l = panel["low"]
    raw = safe_div((c - l) - (h - c), h - l)
    return -1.0 * delta(raw, 1)


__alpha_meta_alpha_003 = {
    "id": "gtja191_003",
    "theme": ['momentum'],
    "formula_latex": 'SUM((CLOSE=DELAY(CLOSE,1)?0:CLOSE-(CLOSE>DELAY(CLOSE,1)?MIN(LOW,DELAY(CLOSE,1)):MAX(HIGH,DELAY(CLOSE,1)))),6)',
    "columns_required": ['close', 'high', 'low'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 6,
    "min_warmup_bars": 7,
    "notes": 'Wilder-style accumulation of signed daily moves over 6 days.',
}

def compute_alpha_003(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    h = panel["high"]
    l = panel["low"]
    pc = c.shift(1)
    up = c > pc
    dn = c < pc
    ref = pd.DataFrame(np.where(up, np.minimum(l, pc), np.where(dn, np.maximum(h, pc), c)),
                       index=c.index, columns=c.columns)
    move = (c - ref).where(up | dn, 0.0)
    return move.rolling(6, min_periods=6).sum()


__alpha_meta_alpha_004 = {
    "id": "gtja191_004",
    "theme": ['momentum', 'volume'],
    "formula_latex": '((((SUM(CLOSE,8)/8)+STD(CLOSE,8))<(SUM(CLOSE,2)/2))?(-1):((SUM(CLOSE,2)/2<(SUM(CLOSE,8)/8-STD(CLOSE,8)))?1:((1<(VOLUME/MEAN(VOLUME,20)))?1:(-1))))',
    "columns_required": ['close', 'volume'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 8,
    "min_warmup_bars": 20,
    "notes": 'Breakout signal: short-MA vs long-MA +/- 1 std, volume-relative tiebreaker. Output in {-1, +1}.',
}

def compute_alpha_004(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    v = panel["volume"]
    ma8 = ts_mean(c, 8)
    ma2 = ts_mean(c, 2)
    sd8 = ts_std(c, 8)
    vmean20 = ts_mean(v, 20)
    upper = ma8 + sd8
    lower = ma8 - sd8
    cond_top = upper < ma2
    cond_bot = ma2 < lower
    vol_strong = (v / vmean20) > 1.0
    res = np.where(cond_top, -1.0,
                   np.where(cond_bot, 1.0,
                            np.where(vol_strong, 1.0, -1.0)))
    return pd.DataFrame(res, index=c.index, columns=c.columns).astype(float)


__alpha_meta_alpha_005 = {
    "id": "gtja191_005",
    "theme": ['volume'],
    "formula_latex": '(-1 * TSMAX(CORR(TSRANK(VOLUME,5), TSRANK(HIGH,5), 5), 3))',
    "columns_required": ['volume', 'high'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 5,
    "min_warmup_bars": 13,
    "notes": 'Max over 3 days of 5d corr of TSRANK(volume,5) and TSRANK(high,5).',
}

def compute_alpha_005(panel: dict) -> pd.DataFrame:
    v = panel["volume"]
    h = panel["high"]
    return -1.0 * ts_max(ts_corr(ts_rank(v, 5), ts_rank(h, 5), 5), 3)


__alpha_meta_alpha_006 = {
    "id": "gtja191_006",
    "theme": ['reversal'],
    "formula_latex": '(RANK(SIGN(DELTA((OPEN*0.85+HIGH*0.15), 4))) * -1)',
    "columns_required": ['open', 'high'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 4,
    "min_warmup_bars": 5,
    "notes": 'Sign of 4d change of weighted price; cross-sectionally ranked, negated.',
}

def compute_alpha_006(panel: dict) -> pd.DataFrame:
    o = panel["open"]
    h = panel["high"]
    x = o * 0.85 + h * 0.15
    return -1.0 * rank(np.sign(delta(x, 4)))


__alpha_meta_alpha_007 = {
    "id": "gtja191_007",
    "theme": ['volume', 'microstructure'],
    "formula_latex": '((RANK(MAX((VWAP-CLOSE),3)) + RANK(MIN((VWAP-CLOSE),3))) * RANK(DELTA(VOLUME,3)))',
    "columns_required": ['close', 'volume', 'amount'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 3,
    "min_warmup_bars": 4,
    "notes": 'VWAP via A-share amount/volume (equity_cn convention).',
}

def compute_alpha_007(panel: dict) -> pd.DataFrame:
    v = panel["volume"]
    c = panel["close"]
    vw = safe_div(panel["amount"], v * 100.0 + 1.0)
    diff = vw - c
    return (rank(ts_max(diff, 3)) + rank(ts_min(diff, 3))) * rank(delta(v, 3))


__alpha_meta_alpha_008 = {
    "id": "gtja191_008",
    "theme": ['reversal'],
    "formula_latex": 'RANK(DELTA(((HIGH+LOW)/2)*0.2 + VWAP*0.8, 4)) * -1',
    "columns_required": ['high', 'low', 'volume', 'amount'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 4,
    "min_warmup_bars": 5,
    "notes": 'Negated rank of 4d change in mid-vwap composite.',
}

def compute_alpha_008(panel: dict) -> pd.DataFrame:
    h = panel["high"]
    l = panel["low"]
    v = panel["volume"]
    vw = safe_div(panel["amount"], v * 100.0 + 1.0)
    x = ((h + l) / 2.0) * 0.2 + vw * 0.8
    return -1.0 * rank(delta(x, 4))


__alpha_meta_alpha_009 = {
    "id": "gtja191_009",
    "theme": ['volume', 'microstructure'],
    "formula_latex": 'SMA(((HIGH+LOW)/2-(DELAY(HIGH,1)+DELAY(LOW,1))/2)*(HIGH-LOW)/VOLUME,7,2)',
    "columns_required": ['high', 'low', 'volume'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 7,
    "min_warmup_bars": 8,
    "notes": 'SMA(n=7, m=2) of midpoint change times range / volume.',
}

def compute_alpha_009(panel: dict) -> pd.DataFrame:
    h = panel["high"]
    l = panel["low"]
    v = panel["volume"]
    mid = (h + l) / 2.0
    pmid = (h.shift(1) + l.shift(1)) / 2.0
    x = (mid - pmid) * safe_div(h - l, v)
    return x.ewm(alpha=2.0 / 7.0, adjust=False).mean()


__alpha_meta_alpha_010 = {
    "id": "gtja191_010",
    "theme": ['volatility', 'reversal'],
    "formula_latex": 'RANK(MAX(((RET<0)?STD(RET,20):CLOSE)^2,5))',
    "columns_required": ['close'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 5,
    "min_warmup_bars": 21,
    "notes": 'Per-day return = pct_change(1) via (close - delay(close,1))/delay(close,1).',
}

def compute_alpha_010(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    pc = c.shift(1)
    ret = safe_div(c - pc, pc)
    s20 = ts_std(ret, 20)
    pick = ret.copy()
    pick = pick.where(ret < 0, c)
    pick = pick.where(~(ret < 0), s20)
    return rank(ts_max(pick * pick, 5))


__alpha_meta_alpha_011 = {
    "id": "gtja191_011",
    "theme": ['volume', 'microstructure'],
    "formula_latex": 'SUM(((CLOSE-LOW)-(HIGH-CLOSE))/(HIGH-LOW)*VOLUME,6)',
    "columns_required": ['close', 'high', 'low', 'volume'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 6,
    "min_warmup_bars": 7,
    "notes": 'Accumulated money-flow-multiplier × volume over 6 days.',
}

def compute_alpha_011(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    h = panel["high"]
    l = panel["low"]
    v = panel["volume"]
    mfm = safe_div((c - l) - (h - c), h - l)
    return (mfm * v).rolling(6, min_periods=6).sum()


__alpha_meta_alpha_012 = {
    "id": "gtja191_012",
    "theme": ['reversal', 'microstructure'],
    "formula_latex": '(RANK((OPEN - (SUM(VWAP,10)/10))) * (-1 * RANK(ABS((CLOSE - VWAP)))))',
    "columns_required": ['open', 'close', 'volume', 'amount'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 10,
    "min_warmup_bars": 11,
    "notes": 'Open-minus-10d-vwap rank times negative rank of |close-vwap|.',
}

def compute_alpha_012(panel: dict) -> pd.DataFrame:
    o = panel["open"]
    c = panel["close"]
    v = panel["volume"]
    vw = safe_div(panel["amount"], v * 100.0 + 1.0)
    return rank(o - ts_mean(vw, 10)) * (-1.0 * rank((c - vw).abs()))


__alpha_meta_alpha_013 = {
    "id": "gtja191_013",
    "theme": ['microstructure'],
    "formula_latex": '(((HIGH*LOW)^0.5) - VWAP)',
    "columns_required": ['high', 'low', 'volume', 'amount'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 1,
    "min_warmup_bars": 1,
    "notes": 'Geometric mean of high/low minus vwap.',
}

def compute_alpha_013(panel: dict) -> pd.DataFrame:
    h = panel["high"]
    l = panel["low"]
    v = panel["volume"]
    vw = safe_div(panel["amount"], v * 100.0 + 1.0)
    geo = signed_power(h * l, 0.5)
    return geo - vw


__alpha_meta_alpha_014 = {
    "id": "gtja191_014",
    "theme": ['momentum'],
    "formula_latex": 'CLOSE - DELAY(CLOSE,5)',
    "columns_required": ['close'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 5,
    "min_warmup_bars": 6,
    "notes": 'Simple 5d momentum = delta(close, 5).',
}

def compute_alpha_014(panel: dict) -> pd.DataFrame:
    return delta(panel["close"], 5)


__alpha_meta_alpha_015 = {
    "id": "gtja191_015",
    "theme": ['reversal'],
    "formula_latex": '(OPEN/DELAY(CLOSE,1) - 1)',
    "columns_required": ['open', 'close'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 1,
    "min_warmup_bars": 2,
    "notes": 'Overnight gap return.',
}

def compute_alpha_015(panel: dict) -> pd.DataFrame:
    o = panel["open"]
    c = panel["close"]
    pc = c.shift(1)
    return safe_div(o, pc) - 1.0


__alpha_meta_alpha_016 = {
    "id": "gtja191_016",
    "theme": ['volume', 'microstructure'],
    "formula_latex": '(-1 * TSMAX(RANK(CORR(RANK(VOLUME), RANK(VWAP), 5)), 5))',
    "columns_required": ['volume', 'amount'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 5,
    "min_warmup_bars": 11,
    "notes": 'Max over 5d of rank of rolling rank-volume vs rank-vwap correlation.',
}

def compute_alpha_016(panel: dict) -> pd.DataFrame:
    v = panel["volume"]
    vw = safe_div(panel["amount"], v * 100.0 + 1.0)
    return -1.0 * ts_max(rank(ts_corr(rank(v), rank(vw), 5)), 5)


__alpha_meta_alpha_017 = {
    "id": "gtja191_017",
    "theme": ['reversal'],
    "formula_latex": '(RANK(VWAP - MAX(VWAP,15))^DELTA(CLOSE,5))',
    "columns_required": ['close', 'volume', 'amount'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 15,
    "min_warmup_bars": 16,
    "notes": 'rank(vwap - 15d max(vwap)) is non-positive; we use signed_power for safety.',
}

def compute_alpha_017(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    v = panel["volume"]
    vw = safe_div(panel["amount"], v * 100.0 + 1.0)
    base = rank(vw - ts_max(vw, 15))
    expo = delta(c, 5)
    # Combine via signed_power(base, mean_exp): use elementwise sign-preserving |base|**expo proxy
    out_arr = np.sign(base.to_numpy(dtype=float, na_value=np.nan)) * np.power(
        np.abs(base.to_numpy(dtype=float, na_value=np.nan)),
        np.abs(expo.to_numpy(dtype=float, na_value=np.nan)),
    )
    return pd.DataFrame(out_arr, index=c.index, columns=c.columns)


__alpha_meta_alpha_018 = {
    "id": "gtja191_018",
    "theme": ['momentum'],
    "formula_latex": 'CLOSE/DELAY(CLOSE,5)',
    "columns_required": ['close'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 5,
    "min_warmup_bars": 6,
    "notes": '5d price ratio.',
}

def compute_alpha_018(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    return safe_div(c, c.shift(5))


__alpha_meta_alpha_019 = {
    "id": "gtja191_019",
    "theme": ['reversal'],
    "formula_latex": '(CLOSE<DELAY(CLOSE,5)?(CLOSE-DELAY(CLOSE,5))/DELAY(CLOSE,5):(CLOSE=DELAY(CLOSE,5)?0:(CLOSE-DELAY(CLOSE,5))/CLOSE))',
    "columns_required": ['close'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 5,
    "min_warmup_bars": 6,
    "notes": 'Piecewise 5d momentum normalized differently in up/down regimes.',
}

def compute_alpha_019(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    pc = c.shift(5)
    diff = c - pc
    up = c > pc
    dn = c < pc
    out = pd.DataFrame(np.where(dn, safe_div(diff, pc).to_numpy(),
                                np.where(up, safe_div(diff, c).to_numpy(), 0.0)),
                       index=c.index, columns=c.columns)
    return out


__alpha_meta_alpha_020 = {
    "id": "gtja191_020",
    "theme": ['momentum'],
    "formula_latex": '((CLOSE-DELAY(CLOSE,6))/DELAY(CLOSE,6))*100',
    "columns_required": ['close'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 6,
    "min_warmup_bars": 7,
    "notes": '6d return in pct.',
}

def compute_alpha_020(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    pc = c.shift(6)
    return safe_div(c - pc, pc) * 100.0


__alpha_meta_alpha_021 = {
    "id": "gtja191_021",
    "theme": ['momentum'],
    "formula_latex": 'REGBETA(MEAN(CLOSE,6), SEQUENCE(6))',
    "columns_required": ['close'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 6,
    "min_warmup_bars": 12,
    "notes": 'Rolling 6-day slope of MA6(close) vs time index. REGBETA proxied by ts_cov / ts_std**2.',
}

def compute_alpha_021(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    ma6 = ts_mean(c, 6)
    # build a sequence DataFrame: 1..N broadcast on every column
    seq = pd.DataFrame(
        np.broadcast_to(np.arange(1, c.shape[0] + 1, dtype=float)[:, None], c.shape).copy(),
        index=c.index, columns=c.columns,
    )
    return safe_div(ts_cov(ma6, seq, 6), ts_std(seq, 6) ** 2)


__alpha_meta_alpha_022 = {
    "id": "gtja191_022",
    "theme": ['reversal'],
    "formula_latex": 'SMA(((CLOSE-MEAN(CLOSE,6))/MEAN(CLOSE,6) - DELAY((CLOSE-MEAN(CLOSE,6))/MEAN(CLOSE,6),3)),12,1)',
    "columns_required": ['close'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 12,
    "min_warmup_bars": 10,
    "notes": 'SMA(12, m=1) of 3-day-difference in price-deviation-from-MA6.',
}

def compute_alpha_022(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    ma6 = ts_mean(c, 6)
    z = safe_div(c - ma6, ma6)
    diff = z - z.shift(3)
    return diff.ewm(alpha=1.0 / 12.0, adjust=False).mean()


__alpha_meta_alpha_023 = {
    "id": "gtja191_023",
    "theme": ['volatility'],
    "formula_latex": 'SMA((CLOSE>DELAY(CLOSE,1)?STD(CLOSE,20):0),20,1)/(SMA((CLOSE>DELAY(CLOSE,1)?STD(CLOSE,20):0),20,1) + SMA((CLOSE<=DELAY(CLOSE,1)?STD(CLOSE,20):0),20,1)) * 100',
    "columns_required": ['close'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 20,
    "min_warmup_bars": 22,
    "notes": 'Up-volatility share. SMA(20, m=1) of STD(20) over up/down days.',
}

def compute_alpha_023(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    pc = c.shift(1)
    s20 = ts_std(c, 20)
    up = (c > pc)
    up_part = s20.where(up, 0.0)
    dn_part = s20.where(~up, 0.0)
    u_sma = up_part.ewm(alpha=1.0 / 20.0, adjust=False).mean()
    d_sma = dn_part.ewm(alpha=1.0 / 20.0, adjust=False).mean()
    return safe_div(u_sma, u_sma + d_sma) * 100.0


__alpha_meta_alpha_024 = {
    "id": "gtja191_024",
    "theme": ['momentum'],
    "formula_latex": 'SMA(CLOSE-DELAY(CLOSE,5),5,1)',
    "columns_required": ['close'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 5,
    "min_warmup_bars": 6,
    "notes": 'SMA(5, m=1) of 5d delta(close).',
}

def compute_alpha_024(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    return delta(c, 5).ewm(alpha=1.0 / 5.0, adjust=False).mean()


__alpha_meta_alpha_025 = {
    "id": "gtja191_025",
    "theme": ['momentum', 'volume'],
    "formula_latex": '((-1*RANK((DELTA(CLOSE,7)*(1-RANK(DECAYLINEAR((VOLUME/MEAN(VOLUME,20)),9))))))*(1+RANK(SUM(RET,250))))',
    "columns_required": ['close', 'volume'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 9,
    "min_warmup_bars": 61,
    "notes": 'Long-window RET sum approximated with 60d cap (warmup feasibility); see notes.',
}

def compute_alpha_025(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    v = panel["volume"]
    pc = c.shift(1)
    ret = safe_div(c - pc, pc)
    vmean20 = ts_mean(v, 20)
    decayed = decay_linear(safe_div(v, vmean20), 9)
    term1 = -1.0 * rank(delta(c, 7) * (1.0 - rank(decayed)))
    # Approximate SUM(RET, 250) with min(60, available) window — see notes.
    long_sum = ret.rolling(60, min_periods=20).sum()
    return term1 * (1.0 + rank(long_sum))


__alpha_meta_alpha_026 = {
    "id": "gtja191_026",
    "theme": ['momentum', 'microstructure'],
    "formula_latex": '((((SUM(CLOSE,7)/7)-CLOSE))+((CORR(VWAP,DELAY(CLOSE,5),230))))',
    "columns_required": ['close', 'volume', 'amount'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 7,
    "min_warmup_bars": 35,
    "notes": '230d corr approximated with 30d window; see notes.',
}

def compute_alpha_026(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    v = panel["volume"]
    vw = safe_div(panel["amount"], v * 100.0 + 1.0)
    term1 = ts_mean(c, 7) - c
    term2 = ts_corr(vw, c.shift(5), 30)
    return term1 + term2


__alpha_meta_alpha_027 = {
    "id": "gtja191_027",
    "theme": ['momentum'],
    "formula_latex": 'WMA((CLOSE-DELAY(CLOSE,3))/DELAY(CLOSE,3)*100 + (CLOSE-DELAY(CLOSE,6))/DELAY(CLOSE,6)*100, 12)',
    "columns_required": ['close'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 12,
    "min_warmup_bars": 18,
    "notes": 'WMA proxied by decay_linear.',
}

def compute_alpha_027(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    r3 = safe_div(c - c.shift(3), c.shift(3)) * 100.0
    r6 = safe_div(c - c.shift(6), c.shift(6)) * 100.0
    return decay_linear(r3 + r6, 12)


__alpha_meta_alpha_028 = {
    "id": "gtja191_028",
    "theme": ['momentum'],
    "formula_latex": '3*SMA((CLOSE-TSMIN(LOW,9))/(TSMAX(HIGH,9)-TSMIN(LOW,9))*100,3,1)-2*SMA(SMA((CLOSE-TSMIN(LOW,9))/(TSMAX(HIGH,9)-TSMIN(LOW,9))*100,3,1),3,1)',
    "columns_required": ['close', 'high', 'low'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 9,
    "min_warmup_bars": 12,
    "notes": 'Stochastic-like indicator double-smoothed.',
}

def compute_alpha_028(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    h = panel["high"]
    l = panel["low"]
    lo9 = ts_min(l, 9)
    hi9 = ts_max(h, 9)
    raw = safe_div(c - lo9, hi9 - lo9) * 100.0
    s1 = raw.ewm(alpha=1.0 / 3.0, adjust=False).mean()
    s2 = s1.ewm(alpha=1.0 / 3.0, adjust=False).mean()
    return 3.0 * s1 - 2.0 * s2


__alpha_meta_alpha_029 = {
    "id": "gtja191_029",
    "theme": ['momentum', 'volume'],
    "formula_latex": '(CLOSE-DELAY(CLOSE,6))/DELAY(CLOSE,6)*VOLUME',
    "columns_required": ['close', 'volume'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 6,
    "min_warmup_bars": 7,
    "notes": '6d return times current volume.',
}

def compute_alpha_029(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    v = panel["volume"]
    return safe_div(c - c.shift(6), c.shift(6)) * v


__alpha_meta_alpha_030 = {
    "id": "gtja191_030",
    "theme": ['volatility'],
    "formula_latex": 'WMA((REGRESI(CLOSE/DELAY(CLOSE,1)-1, MKT_RET, SMB, HML, 60))^2, 20)',
    "columns_required": ['close'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 20,
    "min_warmup_bars": 21,
    "notes": 'Multi-factor REGRESI not implementable in pure-fn zoo; degraded to WMA of squared daily return (idio proxy). See notes.',
}

def compute_alpha_030(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    pc = c.shift(1)
    ret = safe_div(c - pc, pc)
    return decay_linear(ret * ret, 20)


__alpha_meta_alpha_031 = {
    "id": "gtja191_031",
    "theme": ['reversal'],
    "formula_latex": '(CLOSE-MEAN(CLOSE,12))/MEAN(CLOSE,12)*100',
    "columns_required": ['close'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 12,
    "min_warmup_bars": 13,
    "notes": 'Bias-12: deviation of close from MA12 in pct.',
}

def compute_alpha_031(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    m12 = ts_mean(c, 12)
    return safe_div(c - m12, m12) * 100.0


__alpha_meta_alpha_032 = {
    "id": "gtja191_032",
    "theme": ['volume'],
    "formula_latex": '(-1 * SUM(RANK(CORR(RANK(HIGH), RANK(VOLUME), 3)), 3))',
    "columns_required": ['high', 'volume'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 3,
    "min_warmup_bars": 7,
    "notes": 'Negated 3d sum of rank-corr(rank(high), rank(volume), 3).',
}

def compute_alpha_032(panel: dict) -> pd.DataFrame:
    h = panel["high"]
    v = panel["volume"]
    inner = rank(ts_corr(rank(h), rank(v), 3))
    return -1.0 * inner.rolling(3, min_periods=3).sum()


__alpha_meta_alpha_033 = {
    "id": "gtja191_033",
    "theme": ['momentum', 'volume'],
    "formula_latex": '((((-1*TSMIN(LOW,5))+DELAY(TSMIN(LOW,5),5))*RANK(((SUM(RET,240)-SUM(RET,20))/220)))*TSRANK(VOLUME,5))',
    "columns_required": ['low', 'close', 'volume'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 5,
    "min_warmup_bars": 61,
    "notes": '240d/20d long-window approximated with 60d/20d (warmup feasibility).',
}

def compute_alpha_033(panel: dict) -> pd.DataFrame:
    l = panel["low"]
    c = panel["close"]
    v = panel["volume"]
    pc = c.shift(1)
    ret = safe_div(c - pc, pc)
    tmin5 = ts_min(l, 5)
    a = -1.0 * tmin5 + tmin5.shift(5)
    long_diff = (ret.rolling(60, min_periods=30).sum() - ret.rolling(20, min_periods=10).sum()) / 40.0
    return a * rank(long_diff) * ts_rank(v, 5)


__alpha_meta_alpha_034 = {
    "id": "gtja191_034",
    "theme": ['reversal'],
    "formula_latex": 'MEAN(CLOSE,12)/CLOSE',
    "columns_required": ['close'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 12,
    "min_warmup_bars": 13,
    "notes": 'MA12 over close.',
}

def compute_alpha_034(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    return safe_div(ts_mean(c, 12), c)


__alpha_meta_alpha_035 = {
    "id": "gtja191_035",
    "theme": ['volume'],
    "formula_latex": '(MIN(RANK(DECAYLINEAR(DELTA(OPEN,1),15)), RANK(DECAYLINEAR(CORR(VOLUME,((OPEN*0.65)+(OPEN*0.35)),17),7))) * -1)',
    "columns_required": ['open', 'volume'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 15,
    "min_warmup_bars": 25,
    "notes": 'Element-wise min of two ranks, negated.',
}

def compute_alpha_035(panel: dict) -> pd.DataFrame:
    o = panel["open"]
    v = panel["volume"]
    p1 = rank(decay_linear(delta(o, 1), 15))
    weighted = o * 0.65 + o * 0.35
    p2 = rank(decay_linear(ts_corr(v, weighted, 17), 7))
    return -1.0 * pd.DataFrame(np.minimum(p1.to_numpy(), p2.to_numpy()),
                               index=o.index, columns=o.columns)


__alpha_meta_alpha_036 = {
    "id": "gtja191_036",
    "theme": ['volume'],
    "formula_latex": 'RANK(SUM(CORR(RANK(VOLUME), RANK(VWAP), 6), 2))',
    "columns_required": ['volume', 'amount'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 6,
    "min_warmup_bars": 8,
    "notes": 'Rolling 6d corr summed over 2 days then ranked.',
}

def compute_alpha_036(panel: dict) -> pd.DataFrame:
    v = panel["volume"]
    vw = safe_div(panel["amount"], v * 100.0 + 1.0)
    inner = ts_corr(rank(v), rank(vw), 6)
    return rank(inner.rolling(2, min_periods=2).sum())


__alpha_meta_alpha_037 = {
    "id": "gtja191_037",
    "theme": ['momentum'],
    "formula_latex": '(-1*RANK(((SUM(OPEN,5)*SUM(RET,5))-DELAY((SUM(OPEN,5)*SUM(RET,5)),10))))',
    "columns_required": ['open', 'close'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 10,
    "min_warmup_bars": 16,
    "notes": 'Change over 10d of product (sum(open,5)*sum(ret,5)).',
}

def compute_alpha_037(panel: dict) -> pd.DataFrame:
    o = panel["open"]
    c = panel["close"]
    pc = c.shift(1)
    ret = safe_div(c - pc, pc)
    prod = o.rolling(5, min_periods=5).sum() * ret.rolling(5, min_periods=5).sum()
    return -1.0 * rank(prod - prod.shift(10))


__alpha_meta_alpha_038 = {
    "id": "gtja191_038",
    "theme": ['reversal'],
    "formula_latex": '(((SUM(HIGH,20)/20)<HIGH)?(-1*DELTA(HIGH,2)):0)',
    "columns_required": ['high'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 20,
    "min_warmup_bars": 21,
    "notes": 'When current high > MA20(high), output -delta(high,2); else 0.',
}

def compute_alpha_038(panel: dict) -> pd.DataFrame:
    h = panel["high"]
    m20 = ts_mean(h, 20)
    cond = m20 < h
    return (-1.0 * delta(h, 2)).where(cond, 0.0)


__alpha_meta_alpha_039 = {
    "id": "gtja191_039",
    "theme": ['volume'],
    "formula_latex": '((RANK(DECAYLINEAR(DELTA(CLOSE,2),8)) - RANK(DECAYLINEAR(CORR(((VWAP*0.3)+(OPEN*0.7)),SUM(MEAN(VOLUME,180),37),14),12)))*-1)',
    "columns_required": ['close', 'open', 'volume', 'amount'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 14,
    "min_warmup_bars": 63,
    "notes": '180d / 37d windows approximated with 30d / 10d. See notes.',
}

def compute_alpha_039(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    o = panel["open"]
    v = panel["volume"]
    vw = safe_div(panel["amount"], v * 100.0 + 1.0)
    p1 = rank(decay_linear(delta(c, 2), 8))
    blend = vw * 0.3 + o * 0.7
    vmean = ts_mean(v, 30).rolling(10, min_periods=10).sum()
    p2 = rank(decay_linear(ts_corr(blend, vmean, 14), 12))
    return -1.0 * (p1 - p2)


__alpha_meta_alpha_040 = {
    "id": "gtja191_040",
    "theme": ['volume'],
    "formula_latex": 'SUM((CLOSE>DELAY(CLOSE,1)?VOLUME:0),26)/SUM((CLOSE<=DELAY(CLOSE,1)?VOLUME:0),26)*100',
    "columns_required": ['close', 'volume'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 26,
    "min_warmup_bars": 27,
    "notes": 'Up-volume vs down-volume ratio over 26 days.',
}

def compute_alpha_040(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    v = panel["volume"]
    pc = c.shift(1)
    up = c > pc
    up_v = v.where(up, 0.0).rolling(26, min_periods=26).sum()
    dn_v = v.where(~up, 0.0).rolling(26, min_periods=26).sum()
    return safe_div(up_v, dn_v) * 100.0


__alpha_meta_alpha_041 = {
    "id": "gtja191_041",
    "theme": ['microstructure'],
    "formula_latex": '(RANK(MAX(DELTA(VWAP,3),5))*-1)',
    "columns_required": ['volume', 'amount'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 5,
    "min_warmup_bars": 9,
    "notes": '5d max of 3d delta(vwap), ranked, negated.',
}

def compute_alpha_041(panel: dict) -> pd.DataFrame:
    v = panel["volume"]
    vw = safe_div(panel["amount"], v * 100.0 + 1.0)
    return -1.0 * rank(ts_max(delta(vw, 3), 5))


__alpha_meta_alpha_042 = {
    "id": "gtja191_042",
    "theme": ['volume', 'volatility'],
    "formula_latex": '((-1*RANK(STD(HIGH,10)))*CORR(HIGH,VOLUME,10))',
    "columns_required": ['high', 'volume'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 10,
    "min_warmup_bars": 11,
    "notes": 'Negative rank of 10d std(high) times 10d corr(high, volume).',
}

def compute_alpha_042(panel: dict) -> pd.DataFrame:
    h = panel["high"]
    v = panel["volume"]
    return (-1.0 * rank(ts_std(h, 10))) * ts_corr(h, v, 10)


__alpha_meta_alpha_043 = {
    "id": "gtja191_043",
    "theme": ['volume', 'momentum'],
    "formula_latex": 'SUM((CLOSE>DELAY(CLOSE,1)?VOLUME:(CLOSE<DELAY(CLOSE,1)?-VOLUME:0)),6)',
    "columns_required": ['close', 'volume'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 6,
    "min_warmup_bars": 7,
    "notes": 'Signed volume accumulation over 6 days.',
}

def compute_alpha_043(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    v = panel["volume"]
    pc = c.shift(1)
    signed = v.where(c > pc, -v.where(c < pc, 0.0))
    return signed.rolling(6, min_periods=6).sum()


__alpha_meta_alpha_044 = {
    "id": "gtja191_044",
    "theme": ['volume'],
    "formula_latex": '(TSRANK(DECAYLINEAR(CORR(LOW,MEAN(VOLUME,10),7),6),4)+TSRANK(DECAYLINEAR(DELTA(VWAP,3),10),15))',
    "columns_required": ['low', 'volume', 'amount'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 10,
    "min_warmup_bars": 27,
    "notes": 'Sum of two TSRANK terms.',
}

def compute_alpha_044(panel: dict) -> pd.DataFrame:
    l = panel["low"]
    v = panel["volume"]
    vw = safe_div(panel["amount"], v * 100.0 + 1.0)
    t1 = ts_rank(decay_linear(ts_corr(l, ts_mean(v, 10), 7), 6), 4)
    t2 = ts_rank(decay_linear(delta(vw, 3), 10), 15)
    return t1 + t2


__alpha_meta_alpha_045 = {
    "id": "gtja191_045",
    "theme": ['volume'],
    "formula_latex": '(RANK(DELTA((((CLOSE*0.6)+(OPEN*0.4))),1)) * RANK(CORR(VWAP,MEAN(VOLUME,150),15)))',
    "columns_required": ['close', 'open', 'volume', 'amount'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 15,
    "min_warmup_bars": 44,
    "notes": '150d MA volume approximated with 30d window.',
}

def compute_alpha_045(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    o = panel["open"]
    v = panel["volume"]
    vw = safe_div(panel["amount"], v * 100.0 + 1.0)
    blend = c * 0.6 + o * 0.4
    return rank(delta(blend, 1)) * rank(ts_corr(vw, ts_mean(v, 30), 15))


__alpha_meta_alpha_046 = {
    "id": "gtja191_046",
    "theme": ['reversal'],
    "formula_latex": '(MEAN(CLOSE,3)+MEAN(CLOSE,6)+MEAN(CLOSE,12)+MEAN(CLOSE,24))/(4*CLOSE)',
    "columns_required": ['close'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 24,
    "min_warmup_bars": 25,
    "notes": 'Mean of four MA windows over price.',
}

def compute_alpha_046(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    s = ts_mean(c, 3) + ts_mean(c, 6) + ts_mean(c, 12) + ts_mean(c, 24)
    return safe_div(s, 4.0 * c)


__alpha_meta_alpha_047 = {
    "id": "gtja191_047",
    "theme": ['reversal'],
    "formula_latex": 'SMA((TSMAX(HIGH,6)-CLOSE)/(TSMAX(HIGH,6)-TSMIN(LOW,6))*100,9,1)',
    "columns_required": ['close', 'high', 'low'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 9,
    "min_warmup_bars": 10,
    "notes": 'Williams %R style indicator smoothed with SMA(9,1).',
}

def compute_alpha_047(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    h = panel["high"]
    l = panel["low"]
    hi6 = ts_max(h, 6)
    lo6 = ts_min(l, 6)
    raw = safe_div(hi6 - c, hi6 - lo6) * 100.0
    return raw.ewm(alpha=1.0 / 9.0, adjust=False).mean()


__alpha_meta_alpha_048 = {
    "id": "gtja191_048",
    "theme": ['volume', 'momentum'],
    "formula_latex": '-1*((RANK((SIGN((CLOSE-DELAY(CLOSE,1)))+SIGN((DELAY(CLOSE,1)-DELAY(CLOSE,2)))+SIGN((DELAY(CLOSE,2)-DELAY(CLOSE,3))))))*SUM(VOLUME,5))/SUM(VOLUME,20)',
    "columns_required": ['close', 'volume'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 5,
    "min_warmup_bars": 21,
    "notes": 'Rank of 3d signed momentum sum times 5d/20d volume ratio, negated.',
}

def compute_alpha_048(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    v = panel["volume"]
    s = np.sign(c - c.shift(1)) + np.sign(c.shift(1) - c.shift(2)) + np.sign(c.shift(2) - c.shift(3))
    s = pd.DataFrame(s, index=c.index, columns=c.columns)
    sv5 = v.rolling(5, min_periods=5).sum()
    sv20 = v.rolling(20, min_periods=20).sum()
    return -1.0 * rank(s) * safe_div(sv5, sv20)


__alpha_meta_alpha_049 = {
    "id": "gtja191_049",
    "theme": ['reversal'],
    "formula_latex": 'SUM(((HIGH+LOW)>=(DELAY(HIGH,1)+DELAY(LOW,1))?0:MAX(ABS(HIGH-DELAY(HIGH,1)),ABS(LOW-DELAY(LOW,1)))),12)/(SUM(...,12)+SUM(...,12))',
    "columns_required": ['high', 'low'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 12,
    "min_warmup_bars": 13,
    "notes": 'Down-side range as share of total range over 12 days.',
}

def compute_alpha_049(panel: dict) -> pd.DataFrame:
    h = panel["high"]
    l = panel["low"]
    hl = h + l
    phl = h.shift(1) + l.shift(1)
    move = pd.DataFrame(
        np.maximum(np.abs(h.to_numpy() - h.shift(1).to_numpy()),
                   np.abs(l.to_numpy() - l.shift(1).to_numpy())),
        index=h.index, columns=h.columns,
    )
    dn = move.where(hl < phl, 0.0)
    up = move.where(hl > phl, 0.0)
    s_dn = dn.rolling(12, min_periods=12).sum()
    s_up = up.rolling(12, min_periods=12).sum()
    return safe_div(s_dn, s_dn + s_up)


__alpha_meta_alpha_050 = {
    "id": "gtja191_050",
    "theme": ['reversal'],
    "formula_latex": 'SUM(up_move,12)/(SUM(up_move,12)+SUM(dn_move,12)) - SUM(dn_move,12)/(SUM(up_move,12)+SUM(dn_move,12))',
    "columns_required": ['high', 'low'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 12,
    "min_warmup_bars": 13,
    "notes": 'Signed version of #49.',
}

def compute_alpha_050(panel: dict) -> pd.DataFrame:
    h = panel["high"]
    l = panel["low"]
    hl = h + l
    phl = h.shift(1) + l.shift(1)
    move = pd.DataFrame(
        np.maximum(np.abs(h.to_numpy() - h.shift(1).to_numpy()),
                   np.abs(l.to_numpy() - l.shift(1).to_numpy())),
        index=h.index, columns=h.columns,
    )
    dn = move.where(hl < phl, 0.0)
    up = move.where(hl > phl, 0.0)
    s_dn = dn.rolling(12, min_periods=12).sum()
    s_up = up.rolling(12, min_periods=12).sum()
    total = s_up + s_dn
    return safe_div(s_up, total) - safe_div(s_dn, total)


__alpha_meta_alpha_051 = {
    "id": "gtja191_051",
    "theme": ['reversal'],
    "formula_latex": 'SUM(up_move,12)/(SUM(up_move,12)+SUM(dn_move,12))',
    "columns_required": ['high', 'low'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 12,
    "min_warmup_bars": 13,
    "notes": 'Up-range share over 12 days.',
}

def compute_alpha_051(panel: dict) -> pd.DataFrame:
    h = panel["high"]
    l = panel["low"]
    hl = h + l
    phl = h.shift(1) + l.shift(1)
    move = pd.DataFrame(
        np.maximum(np.abs(h.to_numpy() - h.shift(1).to_numpy()),
                   np.abs(l.to_numpy() - l.shift(1).to_numpy())),
        index=h.index, columns=h.columns,
    )
    up = move.where(hl > phl, 0.0)
    dn = move.where(hl < phl, 0.0)
    s_up = up.rolling(12, min_periods=12).sum()
    s_dn = dn.rolling(12, min_periods=12).sum()
    return safe_div(s_up, s_up + s_dn)


__alpha_meta_alpha_052 = {
    "id": "gtja191_052",
    "theme": ['microstructure'],
    "formula_latex": 'SUM(MAX(0,HIGH-DELAY((HIGH+LOW+CLOSE)/3,1)),26) / SUM(MAX(0,DELAY((HIGH+LOW+CLOSE)/3,1)-LOW),26) * 100',
    "columns_required": ['high', 'low', 'close'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 26,
    "min_warmup_bars": 27,
    "notes": 'Bull power / bear power ratio over 26 days.',
}

def compute_alpha_052(panel: dict) -> pd.DataFrame:
    h = panel["high"]
    l = panel["low"]
    c = panel["close"]
    typ = (h + l + c) / 3.0
    p_typ = typ.shift(1)
    bull = (h - p_typ).clip(lower=0)
    bear = (p_typ - l).clip(lower=0)
    return safe_div(bull.rolling(26, min_periods=26).sum(),
                    bear.rolling(26, min_periods=26).sum()) * 100.0


__alpha_meta_alpha_053 = {
    "id": "gtja191_053",
    "theme": ['momentum'],
    "formula_latex": 'COUNT(CLOSE>DELAY(CLOSE,1),12)/12*100',
    "columns_required": ['close'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 12,
    "min_warmup_bars": 13,
    "notes": 'Pct of up-days in 12d window.',
}

def compute_alpha_053(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    up = (c > c.shift(1)).astype(float)
    return up.rolling(12, min_periods=12).sum() / 12.0 * 100.0


__alpha_meta_alpha_054 = {
    "id": "gtja191_054",
    "theme": ['volatility', 'microstructure'],
    "formula_latex": '((-1*RANK((STD(ABS(CLOSE-OPEN),10)+(CLOSE-OPEN))+CORR(CLOSE,OPEN,10))))',
    "columns_required": ['close', 'open'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 10,
    "min_warmup_bars": 11,
    "notes": 'Negated rank of (std|c-o|,10) + (c-o) + corr(c,o,10).',
}

def compute_alpha_054(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    o = panel["open"]
    return -1.0 * rank(ts_std((c - o).abs(), 10) + (c - o) + ts_corr(c, o, 10))


__alpha_meta_alpha_055 = {
    "id": "gtja191_055",
    "theme": ['microstructure'],
    "formula_latex": 'SUM(16*(CLOSE-DELAY(CLOSE,1)+(CLOSE-OPEN)/2+DELAY(CLOSE,1)-DELAY(OPEN,1))/((ABS(HIGH-DELAY(CLOSE,1))>ABS(LOW-DELAY(CLOSE,1)) && ABS(HIGH-DELAY(CLOSE,1))>ABS(HIGH-DELAY(LOW,1))?ABS(HIGH-DELAY(CLOSE,1))+ABS(LOW-DELAY(CLOSE,1))/2+ABS(DELAY(CLOSE,1)-DELAY(OPEN,1))/4:ABS(LOW-DELAY(CLOSE,1))+ABS(HIGH-DELAY(CLOSE,1))/2+ABS(DELAY(CLOSE,1)-DELAY(OPEN,1))/4))*MAX(ABS(HIGH-DELAY(CLOSE,1)),ABS(LOW-DELAY(CLOSE,1))),20)',
    "columns_required": ['close', 'high', 'low', 'open'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 20,
    "min_warmup_bars": 22,
    "notes": 'Sumof complex per-day score over 20 days; numerator simplified.',
}

def compute_alpha_055(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    h = panel["high"]
    l = panel["low"]
    o = panel["open"]
    pc = c.shift(1)
    po = o.shift(1)
    pl = l.shift(1)
    numer = 16.0 * (c - pc + (c - o) / 2.0 + pc - po)
    a = (h - pc).abs()
    b = (l - pc).abs()
    d = (pc - po).abs()
    cond1 = (a > b) & (a > (h - pl).abs())
    branch1 = a + b / 2.0 + d / 4.0
    branch2 = b + a / 2.0 + d / 4.0
    denom = branch1.where(cond1, branch2)
    factor = pd.DataFrame(np.maximum(a.to_numpy(), b.to_numpy()), index=c.index, columns=c.columns)
    per_day = safe_div(numer, denom) * factor
    return per_day.rolling(20, min_periods=20).sum()


__alpha_meta_alpha_056 = {
    "id": "gtja191_056",
    "theme": ['volume'],
    "formula_latex": '(RANK(OPEN-TSMIN(OPEN,12)) < RANK((RANK(CORR(SUM(((HIGH+LOW)/2),19),SUM(MEAN(VOLUME,40),19),13))^5)))',
    "columns_required": ['open', 'high', 'low', 'volume'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 19,
    "min_warmup_bars": 60,
    "notes": 'Boolean comparator returns 1/0; 40d mean truncated.',
}

def compute_alpha_056(panel: dict) -> pd.DataFrame:
    o = panel["open"]
    h = panel["high"]
    l = panel["low"]
    v = panel["volume"]
    lhs = rank(o - ts_min(o, 12))
    mid = (h + l) / 2.0
    sumA = mid.rolling(19, min_periods=19).sum()
    sumB = ts_mean(v, 30).rolling(19, min_periods=19).sum()
    rhs = rank(rank(ts_corr(sumA, sumB, 13)) ** 5)
    return (lhs < rhs).astype(float)


__alpha_meta_alpha_057 = {
    "id": "gtja191_057",
    "theme": ['momentum'],
    "formula_latex": 'SMA((CLOSE-TSMIN(LOW,9))/(TSMAX(HIGH,9)-TSMIN(LOW,9))*100,3,1)',
    "columns_required": ['close', 'high', 'low'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 9,
    "min_warmup_bars": 10,
    "notes": 'KDJ %K-style indicator with SMA(3,1) smoothing.',
}

def compute_alpha_057(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    h = panel["high"]
    l = panel["low"]
    lo9 = ts_min(l, 9)
    hi9 = ts_max(h, 9)
    raw = safe_div(c - lo9, hi9 - lo9) * 100.0
    return raw.ewm(alpha=1.0 / 3.0, adjust=False).mean()


__alpha_meta_alpha_058 = {
    "id": "gtja191_058",
    "theme": ['momentum'],
    "formula_latex": 'COUNT(CLOSE>DELAY(CLOSE,1),20)/20*100',
    "columns_required": ['close'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 20,
    "min_warmup_bars": 21,
    "notes": 'Pct of up-days in 20d window.',
}

def compute_alpha_058(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    up = (c > c.shift(1)).astype(float)
    return up.rolling(20, min_periods=20).sum() / 20.0 * 100.0


__alpha_meta_alpha_059 = {
    "id": "gtja191_059",
    "theme": ['momentum'],
    "formula_latex": 'SUM((CLOSE=DELAY(CLOSE,1)?0:CLOSE-(CLOSE>DELAY(CLOSE,1)?MIN(LOW,DELAY(CLOSE,1)):MAX(HIGH,DELAY(CLOSE,1)))),20)',
    "columns_required": ['close', 'high', 'low'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 20,
    "min_warmup_bars": 22,
    "notes": 'Like alpha #3 but with 20d window.',
}

def compute_alpha_059(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    h = panel["high"]
    l = panel["low"]
    pc = c.shift(1)
    up = c > pc
    dn = c < pc
    ref = pd.DataFrame(np.where(up, np.minimum(l, pc), np.where(dn, np.maximum(h, pc), c)),
                       index=c.index, columns=c.columns)
    move = (c - ref).where(up | dn, 0.0)
    return move.rolling(20, min_periods=20).sum()


__alpha_meta_alpha_060 = {
    "id": "gtja191_060",
    "theme": ['volume', 'microstructure'],
    "formula_latex": 'SUM(((CLOSE-LOW)-(HIGH-CLOSE))/(HIGH-LOW)*VOLUME, 20)',
    "columns_required": ['close', 'high', 'low', 'volume'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 20,
    "min_warmup_bars": 21,
    "notes": '20-day version of alpha #11.',
}

def compute_alpha_060(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    h = panel["high"]
    l = panel["low"]
    v = panel["volume"]
    mfm = safe_div((c - l) - (h - c), h - l)
    return (mfm * v).rolling(20, min_periods=20).sum()


__alpha_meta_alpha_061 = {
    "id": "gtja191_061",
    "theme": ['volume'],
    "formula_latex": '(MAX(RANK(DECAYLINEAR(DELTA(VWAP,1),12)), RANK(DECAYLINEAR(RANK(CORR(LOW,MEAN(VOLUME,80),8)),17))) * -1)',
    "columns_required": ['volume', 'amount', 'low'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 17,
    "min_warmup_bars": 53,
    "notes": '80d mean volume approximated with 30d.',
}

def compute_alpha_061(panel: dict) -> pd.DataFrame:
    v = panel["volume"]
    vw = safe_div(panel["amount"], v * 100.0 + 1.0)
    l = panel["low"]
    p1 = rank(decay_linear(delta(vw, 1), 12))
    p2 = rank(decay_linear(rank(ts_corr(l, ts_mean(v, 30), 8)), 17))
    return -1.0 * pd.DataFrame(np.maximum(p1.to_numpy(), p2.to_numpy()),
                               index=v.index, columns=v.columns)


__alpha_meta_alpha_062 = {
    "id": "gtja191_062",
    "theme": ['volume'],
    "formula_latex": '((-1*CORR(HIGH,RANK(VOLUME),5)))',
    "columns_required": ['high', 'volume'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 5,
    "min_warmup_bars": 6,
    "notes": 'Negated 5d corr(high, rank(volume)).',
}

def compute_alpha_062(panel: dict) -> pd.DataFrame:
    return -1.0 * ts_corr(panel["high"], rank(panel["volume"]), 5)


__alpha_meta_alpha_063 = {
    "id": "gtja191_063",
    "theme": ['momentum'],
    "formula_latex": 'SMA(MAX(CLOSE-DELAY(CLOSE,1),0),6,1)/SMA(ABS(CLOSE-DELAY(CLOSE,1)),6,1)*100',
    "columns_required": ['close'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 6,
    "min_warmup_bars": 7,
    "notes": 'RSI-6 style.',
}

def compute_alpha_063(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    diff = c - c.shift(1)
    up_part = diff.clip(lower=0)
    abs_part = diff.abs()
    u = up_part.ewm(alpha=1.0 / 6.0, adjust=False).mean()
    a = abs_part.ewm(alpha=1.0 / 6.0, adjust=False).mean()
    return safe_div(u, a) * 100.0


__alpha_meta_alpha_064 = {
    "id": "gtja191_064",
    "theme": ['volume'],
    "formula_latex": '(MAX(RANK(DECAYLINEAR(CORR(RANK(VWAP),RANK(VOLUME),4),4)),RANK(DECAYLINEAR(MAX(CORR(RANK(CLOSE),RANK(MEAN(VOLUME,60)),4),13),14)))*-1)',
    "columns_required": ['close', 'volume', 'amount'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 14,
    "min_warmup_bars": 30,
    "notes": '60d mean truncated to 10d; ts_max window 13→4 and decay_linear 14→6 for warmup feasibility.',
}

def compute_alpha_064(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    v = panel["volume"]
    vw = safe_div(panel["amount"], v * 100.0 + 1.0)
    p1 = rank(decay_linear(ts_corr(rank(vw), rank(v), 4), 4))
    inner = ts_corr(rank(c), rank(ts_mean(v, 10)), 4).fillna(0.0)
    p2 = rank(decay_linear(ts_max(inner, 4), 6))
    return -1.0 * pd.DataFrame(np.maximum(p1.to_numpy(), p2.to_numpy()),
                               index=c.index, columns=c.columns)


__alpha_meta_alpha_065 = {
    "id": "gtja191_065",
    "theme": ['reversal'],
    "formula_latex": 'MEAN(CLOSE,6)/CLOSE',
    "columns_required": ['close'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 6,
    "min_warmup_bars": 7,
    "notes": 'MA6 over close.',
}

def compute_alpha_065(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    return safe_div(ts_mean(c, 6), c)


__alpha_meta_alpha_066 = {
    "id": "gtja191_066",
    "theme": ['reversal'],
    "formula_latex": '(CLOSE-MEAN(CLOSE,6))/MEAN(CLOSE,6)*100',
    "columns_required": ['close'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 6,
    "min_warmup_bars": 7,
    "notes": 'Bias-6 pct.',
}

def compute_alpha_066(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    m6 = ts_mean(c, 6)
    return safe_div(c - m6, m6) * 100.0


__alpha_meta_alpha_067 = {
    "id": "gtja191_067",
    "theme": ['momentum'],
    "formula_latex": 'SMA(MAX(CLOSE-DELAY(CLOSE,1),0),24,1)/SMA(ABS(CLOSE-DELAY(CLOSE,1)),24,1)*100',
    "columns_required": ['close'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 24,
    "min_warmup_bars": 25,
    "notes": 'RSI-24 style.',
}

def compute_alpha_067(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    diff = c - c.shift(1)
    up_part = diff.clip(lower=0)
    abs_part = diff.abs()
    u = up_part.ewm(alpha=1.0 / 24.0, adjust=False).mean()
    a = abs_part.ewm(alpha=1.0 / 24.0, adjust=False).mean()
    return safe_div(u, a) * 100.0


__alpha_meta_alpha_068 = {
    "id": "gtja191_068",
    "theme": ['volume'],
    "formula_latex": 'SMA(((HIGH+LOW)/2-(DELAY(HIGH,1)+DELAY(LOW,1))/2)*(HIGH-LOW)/VOLUME,15,2)',
    "columns_required": ['high', 'low', 'volume'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 15,
    "min_warmup_bars": 16,
    "notes": 'Like alpha #9 but with SMA(15, m=2).',
}

def compute_alpha_068(panel: dict) -> pd.DataFrame:
    h = panel["high"]
    l = panel["low"]
    v = panel["volume"]
    mid = (h + l) / 2.0
    pmid = (h.shift(1) + l.shift(1)) / 2.0
    x = (mid - pmid) * safe_div(h - l, v)
    return x.ewm(alpha=2.0 / 15.0, adjust=False).mean()


__alpha_meta_alpha_069 = {
    "id": "gtja191_069",
    "theme": ['microstructure'],
    "formula_latex": '(SUM(DTM,20)>SUM(DBM,20)?(SUM(DTM,20)-SUM(DBM,20))/SUM(DTM,20):(SUM(DTM,20)=SUM(DBM,20)?0:(SUM(DTM,20)-SUM(DBM,20))/SUM(DBM,20)))',
    "columns_required": ['open', 'high', 'low'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 20,
    "min_warmup_bars": 22,
    "notes": 'DTM/DBM as in GTJA spec.',
}

def compute_alpha_069(panel: dict) -> pd.DataFrame:
    o = panel["open"]
    h = panel["high"]
    l = panel["low"]
    po = o.shift(1)
    dtm = pd.DataFrame(np.where(o <= po, 0.0,
                                np.maximum((h - o).to_numpy(), (o - po).to_numpy())),
                       index=o.index, columns=o.columns)
    dbm = pd.DataFrame(np.where(o >= po, 0.0,
                                np.maximum((o - l).to_numpy(), (o - po).to_numpy())),
                       index=o.index, columns=o.columns)
    sd = dtm.rolling(20, min_periods=20).sum()
    sb = dbm.rolling(20, min_periods=20).sum()
    res = pd.DataFrame(np.where(sd > sb, (safe_div(sd - sb, sd)).to_numpy(),
                                np.where(sd < sb, (safe_div(sd - sb, sb)).to_numpy(), 0.0)),
                       index=o.index, columns=o.columns)
    return res


__alpha_meta_alpha_070 = {
    "id": "gtja191_070",
    "theme": ['volatility', 'volume'],
    "formula_latex": 'STD(AMOUNT,6)',
    "columns_required": ['amount'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 6,
    "min_warmup_bars": 7,
    "notes": '6d std of amount (turnover).',
}

def compute_alpha_070(panel: dict) -> pd.DataFrame:
    return ts_std(panel["amount"], 6)


__alpha_meta_alpha_071 = {
    "id": "gtja191_071",
    "theme": ['reversal'],
    "formula_latex": '(CLOSE-MEAN(CLOSE,24))/MEAN(CLOSE,24)*100',
    "columns_required": ['close'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 24,
    "min_warmup_bars": 25,
    "notes": 'Bias-24.',
}

def compute_alpha_071(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    m24 = ts_mean(c, 24)
    return safe_div(c - m24, m24) * 100.0


__alpha_meta_alpha_072 = {
    "id": "gtja191_072",
    "theme": ['reversal'],
    "formula_latex": 'SMA((TSMAX(HIGH,6)-CLOSE)/(TSMAX(HIGH,6)-TSMIN(LOW,6))*100,15,1)',
    "columns_required": ['close', 'high', 'low'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 15,
    "min_warmup_bars": 16,
    "notes": 'Williams %R style with SMA(15,1).',
}

def compute_alpha_072(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    h = panel["high"]
    l = panel["low"]
    hi6 = ts_max(h, 6)
    lo6 = ts_min(l, 6)
    raw = safe_div(hi6 - c, hi6 - lo6) * 100.0
    return raw.ewm(alpha=1.0 / 15.0, adjust=False).mean()


__alpha_meta_alpha_073 = {
    "id": "gtja191_073",
    "theme": ['volume'],
    "formula_latex": '((TSRANK(DECAYLINEAR(DECAYLINEAR(CORR((CLOSE),VOLUME,10),16),4),5) - RANK(DECAYLINEAR(CORR(VWAP,MEAN(VOLUME,30),4),3))) * -1)',
    "columns_required": ['close', 'volume', 'amount'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 16,
    "min_warmup_bars": 35,
    "notes": 'Composite of decay-linear of close-volume corr minus another decay term.',
}

def compute_alpha_073(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    v = panel["volume"]
    vw = safe_div(panel["amount"], v * 100.0 + 1.0)
    inner = ts_corr(c, v, 10)
    t1 = ts_rank(decay_linear(decay_linear(inner, 16), 4), 5)
    t2 = rank(decay_linear(ts_corr(vw, ts_mean(v, 30), 4), 3))
    return -1.0 * (t1 - t2)


__alpha_meta_alpha_074 = {
    "id": "gtja191_074",
    "theme": ['volume'],
    "formula_latex": '(RANK(CORR(SUM(((LOW*0.35)+(VWAP*0.65)),20),SUM(MEAN(VOLUME,40),20),7)) + RANK(CORR(RANK(VWAP),RANK(VOLUME),6)))',
    "columns_required": ['low', 'volume', 'amount'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 20,
    "min_warmup_bars": 30,
    "notes": '40d MA volume truncated to 10d; SUM windows kept at 20.',
}

def compute_alpha_074(panel: dict) -> pd.DataFrame:
    l = panel["low"]
    v = panel["volume"]
    vw = safe_div(panel["amount"], v * 100.0 + 1.0)
    sumA = (l * 0.35 + vw * 0.65).rolling(10, min_periods=10).sum()
    sumB = ts_mean(v, 10).rolling(10, min_periods=10).sum()
    t1 = rank(ts_corr(sumA, sumB, 7))
    t2 = rank(ts_corr(rank(vw), rank(v), 6))
    return t1 + t2


__alpha_meta_alpha_075 = {
    "id": "gtja191_075",
    "theme": ['sentiment', 'momentum'],
    "formula_latex": 'COUNT((CLOSE>OPEN & BENCHMARKINDEXCLOSE<DELAY(BENCHMARKINDEXCLOSE,1)),50)/COUNT(BENCHMARKINDEXCLOSE<DELAY(BENCHMARKINDEXCLOSE,1),50)',
    "columns_required": ['close', 'open'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 50,
    "min_warmup_bars": 30,
    "notes": 'Benchmark unavailable in zoo panel; degraded to row-mean(close) as benchmark proxy. Window 50→20. See notes.',
}

def compute_alpha_075(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    o = panel["open"]
    bench_row = c.mean(axis=1).to_numpy(dtype=float)
    bench_df = pd.DataFrame(np.broadcast_to(bench_row[:, None], c.shape).copy(),
                            index=c.index, columns=c.columns)
    bench_down = (bench_df < bench_df.shift(1)).astype(float)
    up_and_down = ((c > o) & (bench_df < bench_df.shift(1))).astype(float)
    num = up_and_down.rolling(20, min_periods=20).sum()
    den = bench_down.rolling(20, min_periods=20).sum()
    return safe_div(num, den)


__alpha_meta_alpha_076 = {
    "id": "gtja191_076",
    "theme": ['volatility', 'volume'],
    "formula_latex": 'STD(ABS((CLOSE/DELAY(CLOSE,1)-1))/VOLUME,20)/MEAN(ABS((CLOSE/DELAY(CLOSE,1)-1))/VOLUME,20)',
    "columns_required": ['close', 'volume'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 20,
    "min_warmup_bars": 22,
    "notes": 'Coefficient-of-variation of |daily return|/volume over 20 days.',
}

def compute_alpha_076(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    v = panel["volume"]
    x = safe_div((safe_div(c, c.shift(1)) - 1.0).abs(), v)
    return safe_div(ts_std(x, 20), ts_mean(x, 20))


__alpha_meta_alpha_077 = {
    "id": "gtja191_077",
    "theme": ['volume'],
    "formula_latex": 'MIN(RANK(DECAYLINEAR(((HIGH+LOW)/2+HIGH-(VWAP+HIGH)),20)),RANK(DECAYLINEAR(CORR(((HIGH+LOW)/2),MEAN(VOLUME,40),3),6)))',
    "columns_required": ['high', 'low', 'volume', 'amount'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 20,
    "min_warmup_bars": 37,
    "notes": '40d MA truncated to 30d.',
}

def compute_alpha_077(panel: dict) -> pd.DataFrame:
    h = panel["high"]
    l = panel["low"]
    v = panel["volume"]
    vw = safe_div(panel["amount"], v * 100.0 + 1.0)
    mid = (h + l) / 2.0
    p1 = rank(decay_linear(mid + h - (vw + h), 20))
    p2 = rank(decay_linear(ts_corr(mid, ts_mean(v, 30), 3), 6))
    return pd.DataFrame(np.minimum(p1.to_numpy(), p2.to_numpy()),
                        index=h.index, columns=h.columns)


__alpha_meta_alpha_078 = {
    "id": "gtja191_078",
    "theme": ['reversal'],
    "formula_latex": '((HIGH+LOW+CLOSE)/3-MA((HIGH+LOW+CLOSE)/3,12))/(0.015*MEAN(ABS(CLOSE-MA((HIGH+LOW+CLOSE)/3,12)),12))',
    "columns_required": ['high', 'low', 'close'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 12,
    "min_warmup_bars": 23,
    "notes": 'CCI-12 style.',
}

def compute_alpha_078(panel: dict) -> pd.DataFrame:
    h = panel["high"]
    l = panel["low"]
    c = panel["close"]
    typ = (h + l + c) / 3.0
    ma = ts_mean(typ, 12)
    md = ts_mean((c - ma).abs(), 12)
    return safe_div(typ - ma, 0.015 * md)


__alpha_meta_alpha_079 = {
    "id": "gtja191_079",
    "theme": ['momentum'],
    "formula_latex": 'SMA(MAX(CLOSE-DELAY(CLOSE,1),0),12,1)/SMA(ABS(CLOSE-DELAY(CLOSE,1)),12,1)*100',
    "columns_required": ['close'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 12,
    "min_warmup_bars": 13,
    "notes": 'RSI-12.',
}

def compute_alpha_079(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    diff = c - c.shift(1)
    u = diff.clip(lower=0).ewm(alpha=1.0 / 12.0, adjust=False).mean()
    a = diff.abs().ewm(alpha=1.0 / 12.0, adjust=False).mean()
    return safe_div(u, a) * 100.0


__alpha_meta_alpha_080 = {
    "id": "gtja191_080",
    "theme": ['volume'],
    "formula_latex": '(VOLUME-DELAY(VOLUME,5))/DELAY(VOLUME,5)*100',
    "columns_required": ['volume'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 5,
    "min_warmup_bars": 6,
    "notes": '5d volume change pct.',
}

def compute_alpha_080(panel: dict) -> pd.DataFrame:
    v = panel["volume"]
    pv = v.shift(5)
    return safe_div(v - pv, pv) * 100.0


__alpha_meta_alpha_081 = {
    "id": "gtja191_081",
    "theme": ['volume'],
    "formula_latex": 'SMA(VOLUME,21,2)',
    "columns_required": ['volume'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 21,
    "min_warmup_bars": 22,
    "notes": 'SMA(21, m=2) of volume.',
}

def compute_alpha_081(panel: dict) -> pd.DataFrame:
    return panel["volume"].ewm(alpha=2.0 / 21.0, adjust=False).mean()


__alpha_meta_alpha_082 = {
    "id": "gtja191_082",
    "theme": ['reversal'],
    "formula_latex": 'SMA((TSMAX(HIGH,6)-CLOSE)/(TSMAX(HIGH,6)-TSMIN(LOW,6))*100,20,1)',
    "columns_required": ['close', 'high', 'low'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 20,
    "min_warmup_bars": 21,
    "notes": 'Williams %R with SMA(20,1).',
}

def compute_alpha_082(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    h = panel["high"]
    l = panel["low"]
    hi6 = ts_max(h, 6)
    lo6 = ts_min(l, 6)
    raw = safe_div(hi6 - c, hi6 - lo6) * 100.0
    return raw.ewm(alpha=1.0 / 20.0, adjust=False).mean()


__alpha_meta_alpha_083 = {
    "id": "gtja191_083",
    "theme": ['volume'],
    "formula_latex": '(-1*RANK(COVIANCE(RANK(HIGH),RANK(VOLUME),5)))',
    "columns_required": ['high', 'volume'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 5,
    "min_warmup_bars": 6,
    "notes": 'Negated rank of 5d cov(rank(high), rank(volume)).',
}

def compute_alpha_083(panel: dict) -> pd.DataFrame:
    return -1.0 * rank(ts_cov(rank(panel["high"]), rank(panel["volume"]), 5))


__alpha_meta_alpha_084 = {
    "id": "gtja191_084",
    "theme": ['volume', 'momentum'],
    "formula_latex": 'SUM(CLOSE>DELAY(CLOSE,1)?VOLUME:(CLOSE<DELAY(CLOSE,1)?-VOLUME:0),20)',
    "columns_required": ['close', 'volume'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 20,
    "min_warmup_bars": 21,
    "notes": '20d version of alpha #43.',
}

def compute_alpha_084(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    v = panel["volume"]
    pc = c.shift(1)
    signed = v.where(c > pc, -v.where(c < pc, 0.0))
    return signed.rolling(20, min_periods=20).sum()


__alpha_meta_alpha_085 = {
    "id": "gtja191_085",
    "theme": ['volume', 'momentum'],
    "formula_latex": '(TSRANK((VOLUME/MEAN(VOLUME,20)),20)*TSRANK((-1*DELTA(CLOSE,7)),8))',
    "columns_required": ['close', 'volume'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 20,
    "min_warmup_bars": 39,
    "notes": 'Vol-adjusted contrarian momentum.',
}

def compute_alpha_085(panel: dict) -> pd.DataFrame:
    v = panel["volume"]
    c = panel["close"]
    vol_ratio = safe_div(v, ts_mean(v, 20))
    return ts_rank(vol_ratio, 20) * ts_rank(-1.0 * delta(c, 7), 8)


__alpha_meta_alpha_086 = {
    "id": "gtja191_086",
    "theme": ['momentum'],
    "formula_latex": '((0.25 < (((DELAY(CLOSE,20)-DELAY(CLOSE,10))/10) - ((DELAY(CLOSE,10)-CLOSE)/10))) ? -1 : (((((DELAY(CLOSE,20)-DELAY(CLOSE,10))/10) - ((DELAY(CLOSE,10)-CLOSE)/10)) < 0) ? 1 : (-1*(CLOSE-DELAY(CLOSE,1)))))',
    "columns_required": ['close'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 20,
    "min_warmup_bars": 22,
    "notes": 'Returns -1 / +1 / -delta depending on second-derivative thresholds.',
}

def compute_alpha_086(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    a = (c.shift(20) - c.shift(10)) / 10.0
    b = (c.shift(10) - c) / 10.0
    diff = a - b
    last = -1.0 * (c - c.shift(1))
    out = pd.DataFrame(np.where(0.25 < diff, -1.0,
                                np.where(diff < 0, 1.0, last.to_numpy())),
                       index=c.index, columns=c.columns)
    return out


__alpha_meta_alpha_087 = {
    "id": "gtja191_087",
    "theme": ['microstructure'],
    "formula_latex": '((RANK(DECAYLINEAR(DELTA(VWAP,4),7))+TSRANK(DECAYLINEAR((((LOW*0.9)+(LOW*0.1))-VWAP)/(OPEN-((HIGH+LOW)/2)),11),7))*-1)',
    "columns_required": ['close', 'open', 'high', 'low', 'volume', 'amount'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 11,
    "min_warmup_bars": 22,
    "notes": 'Sum of two decay-linear terms, negated.',
}

def compute_alpha_087(panel: dict) -> pd.DataFrame:
    o = panel["open"]
    h = panel["high"]
    l = panel["low"]
    v = panel["volume"]
    vw = safe_div(panel["amount"], v * 100.0 + 1.0)
    p1 = rank(decay_linear(delta(vw, 4), 7))
    numer = (l * 0.9 + l * 0.1) - vw
    denom = o - (h + l) / 2.0
    p2 = ts_rank(decay_linear(safe_div(numer, denom), 11), 7)
    return -1.0 * (p1 + p2)


__alpha_meta_alpha_088 = {
    "id": "gtja191_088",
    "theme": ['momentum'],
    "formula_latex": '(CLOSE-DELAY(CLOSE,20))/DELAY(CLOSE,20)*100',
    "columns_required": ['close'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 20,
    "min_warmup_bars": 21,
    "notes": '20d return pct.',
}

def compute_alpha_088(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    pc = c.shift(20)
    return safe_div(c - pc, pc) * 100.0


__alpha_meta_alpha_089 = {
    "id": "gtja191_089",
    "theme": ['momentum'],
    "formula_latex": '2*(SMA(CLOSE,13,2)-SMA(CLOSE,27,2)-SMA(SMA(CLOSE,13,2)-SMA(CLOSE,27,2),10,2))',
    "columns_required": ['close'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 27,
    "min_warmup_bars": 28,
    "notes": 'MACD-like signal.',
}

def compute_alpha_089(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    short = c.ewm(alpha=2.0 / 13.0, adjust=False).mean()
    long_ = c.ewm(alpha=2.0 / 27.0, adjust=False).mean()
    dif = short - long_
    dea = dif.ewm(alpha=2.0 / 10.0, adjust=False).mean()
    return 2.0 * (dif - dea)


__alpha_meta_alpha_090 = {
    "id": "gtja191_090",
    "theme": ['volume'],
    "formula_latex": '((-1*RANK(CORR(RANK(VWAP),RANK(VOLUME),5))))',
    "columns_required": ['volume', 'amount'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 5,
    "min_warmup_bars": 6,
    "notes": 'Negated rank of 5d corr(rank vwap, rank volume).',
}

def compute_alpha_090(panel: dict) -> pd.DataFrame:
    v = panel["volume"]
    vw = safe_div(panel["amount"], v * 100.0 + 1.0)
    return -1.0 * rank(ts_corr(rank(vw), rank(v), 5))


__alpha_meta_alpha_091 = {
    "id": "gtja191_091",
    "theme": ['volume', 'reversal'],
    "formula_latex": '((-1*RANK((CLOSE-MAX(CLOSE,5))))*RANK(CORR(MEAN(VOLUME,40),LOW,5)))',
    "columns_required": ['close', 'low', 'volume'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 5,
    "min_warmup_bars": 35,
    "notes": '40d mean truncated to 30d.',
}

def compute_alpha_091(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    l = panel["low"]
    v = panel["volume"]
    return -1.0 * rank(c - ts_max(c, 5)) * rank(ts_corr(ts_mean(v, 30), l, 5))


__alpha_meta_alpha_092 = {
    "id": "gtja191_092",
    "theme": ['volume'],
    "formula_latex": '(MAX(RANK(DECAYLINEAR(DELTA(((CLOSE*0.35)+(VWAP*0.65)),2),3)),TSRANK(DECAYLINEAR(ABS(CORR(MEAN(VOLUME,180),CLOSE,13)),5),15))*-1)',
    "columns_required": ['close', 'volume', 'amount'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 15,
    "min_warmup_bars": 60,
    "notes": '180d mean truncated to 30d.',
}

def compute_alpha_092(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    v = panel["volume"]
    vw = safe_div(panel["amount"], v * 100.0 + 1.0)
    blend = c * 0.35 + vw * 0.65
    p1 = rank(decay_linear(delta(blend, 2), 3))
    p2 = ts_rank(decay_linear(ts_corr(ts_mean(v, 30), c, 13).abs(), 5), 15)
    return -1.0 * pd.DataFrame(np.maximum(p1.to_numpy(), p2.to_numpy()),
                               index=c.index, columns=c.columns)


__alpha_meta_alpha_093 = {
    "id": "gtja191_093",
    "theme": ['microstructure'],
    "formula_latex": 'SUM((OPEN>=DELAY(OPEN,1)?0:MAX(OPEN-LOW,OPEN-DELAY(OPEN,1))),20)',
    "columns_required": ['open', 'low'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 20,
    "min_warmup_bars": 22,
    "notes": 'Sum of downside range moves over 20 days.',
}

def compute_alpha_093(panel: dict) -> pd.DataFrame:
    o = panel["open"]
    l = panel["low"]
    po = o.shift(1)
    move = pd.DataFrame(np.maximum((o - l).to_numpy(), (o - po).to_numpy()),
                        index=o.index, columns=o.columns)
    keep = move.where(o < po, 0.0)
    return keep.rolling(20, min_periods=20).sum()


__alpha_meta_alpha_094 = {
    "id": "gtja191_094",
    "theme": ['volume', 'momentum'],
    "formula_latex": 'SUM(CLOSE>DELAY(CLOSE,1)?VOLUME:(CLOSE<DELAY(CLOSE,1)?-VOLUME:0),30)',
    "columns_required": ['close', 'volume'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 30,
    "min_warmup_bars": 31,
    "notes": '30d signed volume.',
}

def compute_alpha_094(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    v = panel["volume"]
    pc = c.shift(1)
    signed = v.where(c > pc, -v.where(c < pc, 0.0))
    return signed.rolling(30, min_periods=30).sum()


__alpha_meta_alpha_095 = {
    "id": "gtja191_095",
    "theme": ['volatility', 'volume'],
    "formula_latex": 'STD(AMOUNT,20)',
    "columns_required": ['amount'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 20,
    "min_warmup_bars": 21,
    "notes": '20d std of amount.',
}

def compute_alpha_095(panel: dict) -> pd.DataFrame:
    return ts_std(panel["amount"], 20)


__alpha_meta_alpha_096 = {
    "id": "gtja191_096",
    "theme": ['momentum'],
    "formula_latex": 'SMA(SMA((CLOSE-TSMIN(LOW,9))/(TSMAX(HIGH,9)-TSMIN(LOW,9))*100,3,1),3,1)',
    "columns_required": ['close', 'high', 'low'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 9,
    "min_warmup_bars": 12,
    "notes": 'KDJ %D-style double smoothed.',
}

def compute_alpha_096(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    h = panel["high"]
    l = panel["low"]
    raw = safe_div(c - ts_min(l, 9), ts_max(h, 9) - ts_min(l, 9)) * 100.0
    return raw.ewm(alpha=1.0 / 3.0, adjust=False).mean().ewm(alpha=1.0 / 3.0, adjust=False).mean()


__alpha_meta_alpha_097 = {
    "id": "gtja191_097",
    "theme": ['volatility', 'volume'],
    "formula_latex": 'STD(VOLUME,10)',
    "columns_required": ['volume'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 10,
    "min_warmup_bars": 11,
    "notes": '10d std of volume.',
}

def compute_alpha_097(panel: dict) -> pd.DataFrame:
    return ts_std(panel["volume"], 10)


__alpha_meta_alpha_098 = {
    "id": "gtja191_098",
    "theme": ['reversal'],
    "formula_latex": '((((DELTA((SUM(CLOSE,100)/100),100)/DELAY(CLOSE,100))<0.05) || ((DELTA((SUM(CLOSE,100)/100),100)/DELAY(CLOSE,100))==0.05)) ? (-1*(CLOSE-TSMIN(CLOSE,100))) : (-1*DELTA(CLOSE,3)))',
    "columns_required": ['close'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 30,
    "min_warmup_bars": 60,
    "notes": '100d windows truncated to 30d for warmup feasibility.',
}

def compute_alpha_098(panel: dict) -> pd.DataFrame:
    c = panel["close"]
    ma = ts_mean(c, 30)
    cond_a = safe_div(delta(ma, 30), c.shift(30)) <= 0.05
    branch1 = -1.0 * (c - ts_min(c, 30))
    branch2 = -1.0 * delta(c, 3)
    return branch1.where(cond_a, branch2)


__alpha_meta_alpha_099 = {
    "id": "gtja191_099",
    "theme": ['volume'],
    "formula_latex": '(-1*RANK(COVIANCE(RANK(CLOSE),RANK(VOLUME),5)))',
    "columns_required": ['close', 'volume'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 5,
    "min_warmup_bars": 6,
    "notes": 'Negated rank of 5d cov(rank close, rank volume).',
}

def compute_alpha_099(panel: dict) -> pd.DataFrame:
    return -1.0 * rank(ts_cov(rank(panel["close"]), rank(panel["volume"]), 5))


__alpha_meta_alpha_100 = {
    "id": "gtja191_100",
    "theme": ['volatility', 'volume'],
    "formula_latex": 'STD(VOLUME,20)',
    "columns_required": ['volume'],
    "extras_required": [],
    "requires_sector": False,
    "universe": ["equity_cn"],
    "frequency": ["1d"],
    "decay_horizon": 20,
    "min_warmup_bars": 21,
    "notes": '20d std of volume.',
}

def compute_alpha_100(panel: dict) -> pd.DataFrame:
    return ts_std(panel["volume"], 20)


__alpha_meta_alpha_101 = {
    'id': 'gtja191_101',
    'theme': ['volume', 'momentum'],
    'formula_latex': '((rank(ts\\_corr(close, sum(ts\\_mean(volume,30),37), 15)) < rank(ts\\_corr(rank(high), rank(ts\\_mean(volume,10)), 11))) * -1)',
    'columns_required': ['open', 'high', 'low', 'close', 'volume', 'amount'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 15,
    'min_warmup_bars': 80,
    'notes': "Inequality cast to float via .astype('float64').",
}


def compute_alpha_101(panel):
    """Compute gtja191_101.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    h = panel["high"]
    v = panel["volume"]
    left = rank(ts_corr(c, ts_mean(v, 30).rolling(37).sum(), 15))
    right = rank(ts_corr(rank(h), rank(ts_mean(v, 10)), 11))
    out = (left < right).astype("float64") * -1.0
    return out


__alpha_meta_alpha_102 = {
    'id': 'gtja191_102',
    'theme': ['volume'],
    'formula_latex': 'sma(max(volume-delay(volume,1),0),6,1)/sma(abs(volume-delay(volume,1)),6,1)*100',
    'columns_required': ['close', 'volume'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 6,
    'min_warmup_bars': 7,
    'notes': 'SMA(x,n,m) -> x.ewm(alpha=m/n, adjust=False).mean().',
}


def compute_alpha_102(panel):
    """Compute gtja191_102.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    def _sma(x, n, m):
        """SMA(x, n, m) per GTJA convention -> ewm with alpha = m/n."""
        return x.ewm(alpha=m / n, adjust=False).mean()
    v = panel["volume"]
    dv = v - v.shift(1)
    num = _sma(dv.clip(lower=0.0), 6, 1)
    den = _sma(dv.abs(), 6, 1)
    out = safe_div(num, den) * 100.0
    return out


__alpha_meta_alpha_103 = {
    'id': 'gtja191_103',
    'theme': ['reversal'],
    'formula_latex': '((20-lowday(low,20))/20)*100',
    'columns_required': ['close', 'low'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 20,
    'notes': 'LOWDAY -> ts_argmin (0-based); (20 - argmin)/20 * 100.',
}


def compute_alpha_103(panel):
    """Compute gtja191_103.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    l = panel["low"]
    am = ts_argmin(l, 20)
    out = (20.0 - am) / 20.0 * 100.0
    return out


__alpha_meta_alpha_104 = {
    'id': 'gtja191_104',
    'theme': ['volume', 'volatility'],
    'formula_latex': '-1*delta(corr(high,volume,5),5)*rank(std(close,20))',
    'columns_required': ['open', 'high', 'low', 'close', 'volume'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 25,
    'notes': '',
}


def compute_alpha_104(panel):
    """Compute gtja191_104.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    h = panel["high"]
    v = panel["volume"]
    corr_hv = ts_corr(h, v, 5)
    out = -1.0 * (delta(corr_hv, 5) * rank(ts_std(c, 20)))
    return out


__alpha_meta_alpha_105 = {
    'id': 'gtja191_105',
    'theme': ['volume'],
    'formula_latex': '-1*corr(rank(open),rank(volume),10)',
    'columns_required': ['open', 'volume', 'close'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 10,
    'min_warmup_bars': 10,
    'notes': '',
}


def compute_alpha_105(panel):
    """Compute gtja191_105.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    o = panel["open"]
    v = panel["volume"]
    out = -1.0 * ts_corr(rank(o), rank(v), 10)
    return out


__alpha_meta_alpha_106 = {
    'id': 'gtja191_106',
    'theme': ['momentum'],
    'formula_latex': 'close-delay(close,20)',
    'columns_required': ['close'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 21,
    'notes': '',
}


def compute_alpha_106(panel):
    """Compute gtja191_106.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    out = delta(c, 20)
    return out


__alpha_meta_alpha_107 = {
    'id': 'gtja191_107',
    'theme': ['reversal'],
    'formula_latex': '-1*rank(open-delay(high,1))*rank(open-delay(close,1))*rank(open-delay(low,1))',
    'columns_required': ['open', 'high', 'low', 'close'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 1,
    'min_warmup_bars': 2,
    'notes': '',
}


def compute_alpha_107(panel):
    """Compute gtja191_107.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    o = panel["open"]
    h = panel["high"]
    l = panel["low"]
    out = (-1.0 * rank(o - h.shift(1))) * rank(o - c.shift(1)) * rank(o - l.shift(1))
    return out


__alpha_meta_alpha_108 = {
    'id': 'gtja191_108',
    'theme': ['reversal', 'volume'],
    'formula_latex': '(rank(high-min(high,2))^rank(corr(vwap,mean(volume,120),6)))*-1',
    'columns_required': ['open', 'high', 'low', 'close', 'volume', 'amount'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 6,
    'min_warmup_bars': 125,
    'notes': 'x^y interpreted as x ** y after rank; both terms in (0,1].',
}


def compute_alpha_108(panel):
    """Compute gtja191_108.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    h = panel["high"]
    v = panel["volume"]
    vw = vwap(panel, "equity_cn")

    left = rank(h - ts_min(h, 2))
    right = rank(ts_corr(vw, ts_mean(v, 120), 6))
    out = signed_power(left, 1.0) * 0  # placeholder to load library
    # We compute left ** right with NaN safety.
    arr_l = left.to_numpy(dtype=np.float64, na_value=np.nan)
    arr_r = right.to_numpy(dtype=np.float64, na_value=np.nan)
    arr = np.power(arr_l, arr_r)
    out = pd.DataFrame(arr, index=left.index, columns=left.columns) * -1.0
    return out


__alpha_meta_alpha_109 = {
    'id': 'gtja191_109',
    'theme': ['volatility'],
    'formula_latex': 'sma(high-low,10,2)/sma(sma(high-low,10,2),10,2)',
    'columns_required': ['close', 'high', 'low'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 10,
    'min_warmup_bars': 20,
    'notes': 'SMA -> ewm(alpha=2/10).',
}


def compute_alpha_109(panel):
    """Compute gtja191_109.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    def _sma(x, n, m):
        """SMA(x, n, m) per GTJA convention -> ewm with alpha = m/n."""
        return x.ewm(alpha=m / n, adjust=False).mean()
    h = panel["high"]
    l = panel["low"]
    hl = h - l
    num = _sma(hl, 10, 2)
    den = _sma(num, 10, 2)
    out = safe_div(num, den)
    return out


__alpha_meta_alpha_110 = {
    'id': 'gtja191_110',
    'theme': ['momentum'],
    'formula_latex': 'sum(max(0,high-delay(close,1)),20)/sum(max(0,delay(close,1)-low),20)*100',
    'columns_required': ['close', 'high', 'low'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 21,
    'notes': '',
}


def compute_alpha_110(panel):
    """Compute gtja191_110.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    h = panel["high"]
    l = panel["low"]
    prev_c = c.shift(1)
    num = (h - prev_c).clip(lower=0.0).rolling(20).sum()
    den = (prev_c - l).clip(lower=0.0).rolling(20).sum()
    out = safe_div(num, den) * 100.0
    return out


__alpha_meta_alpha_111 = {
    'id': 'gtja191_111',
    'theme': ['volume', 'microstructure'],
    'formula_latex': 'sma(v*((c-l)-(h-c))/(h-l),11,2)-sma(v*((c-l)-(h-c))/(h-l),4,2)',
    'columns_required': ['open', 'high', 'low', 'close', 'volume'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 11,
    'min_warmup_bars': 12,
    'notes': '',
}


def compute_alpha_111(panel):
    """Compute gtja191_111.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    def _sma(x, n, m):
        """SMA(x, n, m) per GTJA convention -> ewm with alpha = m/n."""
        return x.ewm(alpha=m / n, adjust=False).mean()
    c = panel["close"]
    h = panel["high"]
    l = panel["low"]
    v = panel["volume"]
    ratio = safe_div(v * ((c - l) - (h - c)), h - l)
    out = _sma(ratio, 11, 2) - _sma(ratio, 4, 2)
    return out


__alpha_meta_alpha_112 = {
    'id': 'gtja191_112',
    'theme': ['momentum'],
    'formula_latex': '(sum_up(12)-sum_down(12))/(sum_up(12)+sum_down(12))*100',
    'columns_required': ['close'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 12,
    'min_warmup_bars': 13,
    'notes': '',
}


def compute_alpha_112(panel):
    """Compute gtja191_112.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    dc = c - c.shift(1)
    up = dc.where(dc > 0, 0.0).rolling(12).sum()
    down = (-dc).where(dc < 0, 0.0).rolling(12).sum()
    out = safe_div(up - down, up + down) * 100.0
    return out


__alpha_meta_alpha_113 = {
    'id': 'gtja191_113',
    'theme': ['volume'],
    'formula_latex': '-1*(rank(mean(delay(c,5),20))*corr(c,v,2))*rank(corr(sum(c,5),sum(c,20),2))',
    'columns_required': ['close', 'volume'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 27,
    'notes': '',
}


def compute_alpha_113(panel):
    """Compute gtja191_113.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    v = panel["volume"]
    m1 = rank(c.shift(5).rolling(20).sum() / 20.0)
    m2 = ts_corr(c, v, 2)
    m3 = rank(ts_corr(c.rolling(5).sum(), c.rolling(20).sum(), 2))
    out = -1.0 * (m1 * m2) * m3
    return out


__alpha_meta_alpha_114 = {
    'id': 'gtja191_114',
    'theme': ['volume', 'volatility'],
    'formula_latex': 'see body',
    'columns_required': ['open', 'high', 'low', 'close', 'volume', 'amount'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 5,
    'min_warmup_bars': 7,
    'notes': '',
}


def compute_alpha_114(panel):
    """Compute gtja191_114.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    h = panel["high"]
    l = panel["low"]
    v = panel["volume"]
    vw = vwap(panel, "equity_cn")

    hl_ratio = safe_div(h - l, c.rolling(5).sum() / 5.0)
    num = rank(hl_ratio.shift(2)) * rank(rank(v))
    den = safe_div(hl_ratio, vw - c)
    out = safe_div(num, den)
    return out


__alpha_meta_alpha_115 = {
    'id': 'gtja191_115',
    'theme': ['volume'],
    'formula_latex': 'rank(corr(0.9h+0.1c,mean(v,30),10))^rank(corr(tsrank((h+l)/2,4),tsrank(v,10),7))',
    'columns_required': ['open', 'high', 'low', 'close', 'volume'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 30,
    'min_warmup_bars': 40,
    'notes': 'x^y -> np.power after rank.',
}


def compute_alpha_115(panel):
    """Compute gtja191_115.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    h = panel["high"]
    l = panel["low"]
    v = panel["volume"]
    left = rank(ts_corr(h * 0.9 + c * 0.1, ts_mean(v, 30), 10))
    right = rank(ts_corr(ts_rank((h + l) / 2.0, 4), ts_rank(v, 10), 7))
    arr = np.power(left.to_numpy(dtype=np.float64, na_value=np.nan),
                   right.to_numpy(dtype=np.float64, na_value=np.nan))
    out = pd.DataFrame(arr, index=left.index, columns=left.columns)
    return out


__alpha_meta_alpha_116 = {
    'id': 'gtja191_116',
    'theme': ['momentum'],
    'formula_latex': 'regbeta(close,sequence(20),20)',
    'columns_required': ['close'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 20,
    'notes': 'Rolling OLS slope vs. linear index; cov(c,t,20)/var(t,20).',
}


def compute_alpha_116(panel):
    """Compute gtja191_116.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    n = 20
    t = pd.DataFrame(
        np.tile(np.arange(c.shape[0], dtype=np.float64).reshape(-1, 1), (1, c.shape[1])),
        index=c.index, columns=c.columns,
    )
    beta = safe_div(ts_cov(c, t, n), ts_std(t, n) ** 2)
    return beta


__alpha_meta_alpha_117 = {
    'id': 'gtja191_117',
    'theme': ['volume', 'momentum'],
    'formula_latex': 'tsrank(v,32)*(1-tsrank(c+h-l,16))*(1-tsrank(ret,32))',
    'columns_required': ['close', 'high', 'low', 'volume'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 32,
    'min_warmup_bars': 33,
    'notes': 'ret = close/delay(close,1) - 1.',
}


def compute_alpha_117(panel):
    """Compute gtja191_117.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    h = panel["high"]
    l = panel["low"]
    v = panel["volume"]
    ret = safe_div(c, c.shift(1)) - 1.0
    out = (ts_rank(v, 32) * (1.0 - ts_rank((c + h) - l, 16))) * (1.0 - ts_rank(ret, 32))
    return out


__alpha_meta_alpha_118 = {
    'id': 'gtja191_118',
    'theme': ['reversal'],
    'formula_latex': 'sum(h-o,20)/sum(o-l,20)*100',
    'columns_required': ['open', 'high', 'low', 'close'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 20,
    'notes': '',
}


def compute_alpha_118(panel):
    """Compute gtja191_118.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    o = panel["open"]
    h = panel["high"]
    l = panel["low"]
    out = safe_div((h - o).rolling(20).sum(), (o - l).rolling(20).sum()) * 100.0
    return out


__alpha_meta_alpha_119 = {
    'id': 'gtja191_119',
    'theme': ['volume'],
    'formula_latex': 'see body',
    'columns_required': ['open', 'high', 'low', 'close', 'volume', 'amount'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 26,
    'min_warmup_bars': 60,
    'notes': '',
}


def compute_alpha_119(panel):
    """Compute gtja191_119.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    o = panel["open"]
    v = panel["volume"]
    vw = vwap(panel, "equity_cn")

    left = rank(decay_linear(ts_corr(vw, ts_mean(v, 5).rolling(26).sum(), 5), 7))
    inner = ts_min(ts_corr(rank(o), rank(ts_mean(v, 15)), 21), 9)
    right = rank(decay_linear(ts_rank(inner, 7), 8))
    out = left - right
    return out


__alpha_meta_alpha_120 = {
    'id': 'gtja191_120',
    'theme': ['reversal'],
    'formula_latex': 'rank(vwap-close)/rank(vwap+close)',
    'columns_required': ['open', 'high', 'low', 'close', 'volume', 'amount'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 1,
    'min_warmup_bars': 1,
    'notes': '',
}


def compute_alpha_120(panel):
    """Compute gtja191_120.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    vw = vwap(panel, "equity_cn")

    out = safe_div(rank(vw - c), rank(vw + c))
    return out


__alpha_meta_alpha_121 = {
    'id': 'gtja191_121',
    'theme': ['volume'],
    'formula_latex': 'see body',
    'columns_required': ['open', 'high', 'low', 'close', 'volume', 'amount'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 80,
    'notes': '',
}


def compute_alpha_121(panel):
    """Compute gtja191_121.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    v = panel["volume"]
    vw = vwap(panel, "equity_cn")

    left = rank(vw - ts_min(vw, 12))
    inner = ts_corr(ts_rank(vw, 20), ts_rank(ts_mean(v, 60), 2), 18)
    right = ts_rank(inner, 3)
    arr = np.power(left.to_numpy(dtype=np.float64, na_value=np.nan),
                   right.to_numpy(dtype=np.float64, na_value=np.nan))
    out = pd.DataFrame(arr, index=left.index, columns=left.columns) * -1.0
    return out


__alpha_meta_alpha_122 = {
    'id': 'gtja191_122',
    'theme': ['momentum'],
    'formula_latex': 'see body',
    'columns_required': ['close'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 13,
    'min_warmup_bars': 40,
    'notes': 'Triple SMA of log close.',
}


def compute_alpha_122(panel):
    """Compute gtja191_122.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    def _sma(x, n, m):
        """SMA(x, n, m) per GTJA convention -> ewm with alpha = m/n."""
        return x.ewm(alpha=m / n, adjust=False).mean()
    c = panel["close"]
    s = _sma(_sma(_sma(np.log(c), 13, 2), 13, 2), 13, 2)
    out = safe_div(s - s.shift(1), s.shift(1))
    return out


__alpha_meta_alpha_123 = {
    'id': 'gtja191_123',
    'theme': ['volume'],
    'formula_latex': 'see body',
    'columns_required': ['open', 'high', 'low', 'close', 'volume'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 90,
    'notes': '',
}


def compute_alpha_123(panel):
    """Compute gtja191_123.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    h = panel["high"]
    l = panel["low"]
    v = panel["volume"]
    left = rank(ts_corr(((h + l) / 2.0).rolling(20).sum(), ts_mean(v, 60).rolling(20).sum(), 9))
    right = rank(ts_corr(l, v, 6))
    out = (left < right).astype("float64") * -1.0
    return out


__alpha_meta_alpha_124 = {
    'id': 'gtja191_124',
    'theme': ['reversal'],
    'formula_latex': '(close-vwap)/decay_linear(rank(tsmax(close,30)),2)',
    'columns_required': ['open', 'high', 'low', 'close', 'volume', 'amount'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 30,
    'min_warmup_bars': 32,
    'notes': '',
}


def compute_alpha_124(panel):
    """Compute gtja191_124.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    vw = vwap(panel, "equity_cn")

    out = safe_div(c - vw, decay_linear(rank(ts_max(c, 30)), 2))
    return out


__alpha_meta_alpha_125 = {
    'id': 'gtja191_125',
    'theme': ['volume'],
    'formula_latex': 'see body',
    'columns_required': ['open', 'high', 'low', 'close', 'volume', 'amount'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 120,
    'notes': '',
}


def compute_alpha_125(panel):
    """Compute gtja191_125.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    v = panel["volume"]
    vw = vwap(panel, "equity_cn")

    num = rank(decay_linear(ts_corr(vw, ts_mean(v, 80), 17), 20))
    den = rank(decay_linear(delta(c * 0.5 + vw * 0.5, 3), 16))
    out = safe_div(num, den)
    return out


__alpha_meta_alpha_126 = {
    'id': 'gtja191_126',
    'theme': ['reversal'],
    'formula_latex': '(c+h+l)/3',
    'columns_required': ['close', 'high', 'low'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 1,
    'min_warmup_bars': 1,
    'notes': '',
}


def compute_alpha_126(panel):
    """Compute gtja191_126.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    h = panel["high"]
    l = panel["low"]
    out = (c + h + l) / 3.0
    return out


__alpha_meta_alpha_127 = {
    'id': 'gtja191_127',
    'theme': ['volatility'],
    'formula_latex': 'sqrt(mean((100*(c-tsmax(c,12))/tsmax(c,12))^2,12))',
    'columns_required': ['close'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 12,
    'min_warmup_bars': 24,
    'notes': '',
}


def compute_alpha_127(panel):
    """Compute gtja191_127.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    ratio = safe_div(c - ts_max(c, 12), ts_max(c, 12)) * 100.0
    out = ts_mean(ratio ** 2, 12) ** 0.5
    return out


__alpha_meta_alpha_128 = {
    'id': 'gtja191_128',
    'theme': ['momentum'],
    'formula_latex': 'see body',
    'columns_required': ['open', 'high', 'low', 'close', 'volume'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 14,
    'min_warmup_bars': 16,
    'notes': '',
}


def compute_alpha_128(panel):
    """Compute gtja191_128.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    h = panel["high"]
    l = panel["low"]
    v = panel["volume"]
    tp = (h + l + c) / 3.0
    dtp = tp - tp.shift(1)
    up = (tp * v).where(dtp > 0, 0.0).rolling(14).sum()
    down = (tp * v).where(dtp < 0, 0.0).rolling(14).sum()
    ratio = safe_div(up, down)
    out = 100.0 - 100.0 / (1.0 + ratio)
    return out


__alpha_meta_alpha_129 = {
    'id': 'gtja191_129',
    'theme': ['momentum'],
    'formula_latex': 'sum(abs(c-delay(c,1)) if dc<0 else 0,12)',
    'columns_required': ['close'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 12,
    'min_warmup_bars': 13,
    'notes': '',
}


def compute_alpha_129(panel):
    """Compute gtja191_129.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    dc = c - c.shift(1)
    out = (-dc).where(dc < 0, 0.0).rolling(12).sum()
    return out


__alpha_meta_alpha_130 = {
    'id': 'gtja191_130',
    'theme': ['volume'],
    'formula_latex': 'see body',
    'columns_required': ['open', 'high', 'low', 'close', 'volume', 'amount'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 40,
    'min_warmup_bars': 60,
    'notes': '',
}


def compute_alpha_130(panel):
    """Compute gtja191_130.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    h = panel["high"]
    l = panel["low"]
    v = panel["volume"]
    vw = vwap(panel, "equity_cn")

    num = rank(decay_linear(ts_corr((h + l) / 2.0, ts_mean(v, 40), 9), 10))
    den = rank(decay_linear(ts_corr(rank(vw), rank(v), 7), 3))
    out = safe_div(num, den)
    return out


__alpha_meta_alpha_131 = {
    'id': 'gtja191_131',
    'theme': ['volume'],
    'formula_latex': 'rank(delta(vwap,1))^tsrank(corr(close,mean(v,50),18),18)',
    'columns_required': ['open', 'high', 'low', 'close', 'volume', 'amount'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 50,
    'min_warmup_bars': 84,
    'notes': 'DELAT in report typo = DELTA.',
}


def compute_alpha_131(panel):
    """Compute gtja191_131.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    v = panel["volume"]
    vw = vwap(panel, "equity_cn")

    left = rank(delta(vw, 1))
    right = ts_rank(ts_corr(c, ts_mean(v, 50), 18), 18)
    arr = np.power(left.to_numpy(dtype=np.float64, na_value=np.nan),
                   right.to_numpy(dtype=np.float64, na_value=np.nan))
    out = pd.DataFrame(arr, index=left.index, columns=left.columns)
    return out


__alpha_meta_alpha_132 = {
    'id': 'gtja191_132',
    'theme': ['liquidity'],
    'formula_latex': 'mean(amount,20)',
    'columns_required': ['close', 'amount'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 20,
    'notes': '',
}


def compute_alpha_132(panel):
    """Compute gtja191_132.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    amt = panel["amount"]
    out = ts_mean(amt, 20)
    return out


__alpha_meta_alpha_133 = {
    'id': 'gtja191_133',
    'theme': ['momentum'],
    'formula_latex': '((20-highday(high,20))/20)*100-((20-lowday(low,20))/20)*100',
    'columns_required': ['close', 'high', 'low'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 20,
    'notes': '',
}


def compute_alpha_133(panel):
    """Compute gtja191_133.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    h = panel["high"]
    l = panel["low"]
    out = (20.0 - ts_argmax(h, 20)) / 20.0 * 100.0 - (20.0 - ts_argmin(l, 20)) / 20.0 * 100.0
    return out


__alpha_meta_alpha_134 = {
    'id': 'gtja191_134',
    'theme': ['momentum', 'volume'],
    'formula_latex': '(close-delay(close,12))/delay(close,12)*volume',
    'columns_required': ['close', 'volume'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 12,
    'min_warmup_bars': 13,
    'notes': '',
}


def compute_alpha_134(panel):
    """Compute gtja191_134.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    v = panel["volume"]
    out = safe_div(c - c.shift(12), c.shift(12)) * v
    return out


__alpha_meta_alpha_135 = {
    'id': 'gtja191_135',
    'theme': ['momentum'],
    'formula_latex': 'sma(delay(c/delay(c,20),1),20,1)',
    'columns_required': ['close'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 22,
    'notes': '',
}


def compute_alpha_135(panel):
    """Compute gtja191_135.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    def _sma(x, n, m):
        """SMA(x, n, m) per GTJA convention -> ewm with alpha = m/n."""
        return x.ewm(alpha=m / n, adjust=False).mean()
    c = panel["close"]
    ratio = safe_div(c, c.shift(20)).shift(1)
    out = _sma(ratio, 20, 1)
    return out


__alpha_meta_alpha_136 = {
    'id': 'gtja191_136',
    'theme': ['momentum', 'volume'],
    'formula_latex': '-1*rank(delta(ret,3))*corr(open,volume,10)',
    'columns_required': ['open', 'close', 'volume'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 10,
    'min_warmup_bars': 11,
    'notes': 'ret = close/delay(close,1) - 1.',
}


def compute_alpha_136(panel):
    """Compute gtja191_136.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    o = panel["open"]
    v = panel["volume"]
    ret = safe_div(c, c.shift(1)) - 1.0
    out = (-1.0 * rank(delta(ret, 3))) * ts_corr(o, v, 10)
    return out


__alpha_meta_alpha_137 = {
    'id': 'gtja191_137',
    'theme': ['volatility'],
    'formula_latex': 'see body',
    'columns_required': ['open', 'high', 'low', 'close'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 1,
    'min_warmup_bars': 2,
    'notes': 'Transcribed from the standard 137 implementation; piecewise denominator.',
}


def compute_alpha_137(panel):
    """Compute gtja191_137.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    o = panel["open"]
    h = panel["high"]
    l = panel["low"]
    dc1 = c.shift(1)
    do1 = o.shift(1)
    dl1 = l.shift(1)
    dh1 = h.shift(1)
    abs_hdc = (h - dc1).abs()
    abs_ldc = (l - dc1).abs()
    abs_hdl1 = (h - dl1).abs()
    # Three candidate denominators per report
    cond1 = (abs_hdc > abs_ldc) & (abs_hdc > abs_hdl1)
    cond2 = (abs_ldc > abs_hdl1) & (abs_ldc > abs_hdc)
    den_a = abs_hdc + abs_ldc / 2.0 + (dc1 - do1).abs() / 4.0
    den_b = abs_ldc + abs_hdc / 2.0 + (dc1 - do1).abs() / 4.0
    den_c = abs_hdl1 + (dc1 - do1).abs() / 4.0
    den = den_c.where(~cond2, den_b).where(~cond1, den_a)
    num = c - dc1 + (c - o) / 2.0 + dc1 - do1
    mx = pd.DataFrame(
        np.maximum(abs_hdc.to_numpy(dtype=np.float64, na_value=np.nan),
                   abs_ldc.to_numpy(dtype=np.float64, na_value=np.nan)),
        index=c.index, columns=c.columns,
    )
    out = 16.0 * safe_div(num, den) * mx
    return out


__alpha_meta_alpha_138 = {
    'id': 'gtja191_138',
    'theme': ['volume'],
    'formula_latex': 'see body',
    'columns_required': ['open', 'high', 'low', 'close', 'volume', 'amount'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 119,
    'notes': '',
}


def compute_alpha_138(panel):
    """Compute gtja191_138.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    l = panel["low"]
    v = panel["volume"]
    vw = vwap(panel, "equity_cn")

    left = rank(decay_linear(delta(l * 0.7 + vw * 0.3, 3), 20))
    inner = ts_corr(ts_rank(l, 8), ts_rank(ts_mean(v, 60), 17), 5)
    right = ts_rank(decay_linear(ts_rank(inner, 19), 16), 7)
    out = (left - right) * -1.0
    return out


__alpha_meta_alpha_139 = {
    'id': 'gtja191_139',
    'theme': ['volume'],
    'formula_latex': '-1*corr(open,volume,10)',
    'columns_required': ['open', 'volume', 'close'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 10,
    'min_warmup_bars': 10,
    'notes': '',
}


def compute_alpha_139(panel):
    """Compute gtja191_139.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    o = panel["open"]
    v = panel["volume"]
    out = -1.0 * ts_corr(o, v, 10)
    return out


__alpha_meta_alpha_140 = {
    'id': 'gtja191_140',
    'theme': ['volume'],
    'formula_latex': 'see body',
    'columns_required': ['open', 'high', 'low', 'close', 'volume'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 100,
    'notes': 'MIN(a,b) elementwise -> np.minimum.',
}


def compute_alpha_140(panel):
    """Compute gtja191_140.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    o = panel["open"]
    h = panel["high"]
    l = panel["low"]
    v = panel["volume"]
    left = rank(decay_linear((rank(o) + rank(l)) - (rank(h) + rank(c)), 8))
    inner = ts_corr(ts_rank(c, 8), ts_rank(ts_mean(v, 60), 20), 8)
    right = ts_rank(decay_linear(ts_rank(inner, 7), 7), 3)
    arr = np.minimum(left.to_numpy(dtype=np.float64, na_value=np.nan),
                     right.to_numpy(dtype=np.float64, na_value=np.nan))
    out = pd.DataFrame(arr, index=left.index, columns=left.columns)
    return out


__alpha_meta_alpha_141 = {
    'id': 'gtja191_141',
    'theme': ['volume'],
    'formula_latex': 'rank(corr(rank(high),rank(mean(v,15)),9))*-1',
    'columns_required': ['high', 'volume', 'close'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 15,
    'min_warmup_bars': 24,
    'notes': '',
}


def compute_alpha_141(panel):
    """Compute gtja191_141.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    h = panel["high"]
    v = panel["volume"]
    out = rank(ts_corr(rank(h), rank(ts_mean(v, 15)), 9)) * -1.0
    return out


__alpha_meta_alpha_142 = {
    'id': 'gtja191_142',
    'theme': ['volume', 'reversal'],
    'formula_latex': 'see body',
    'columns_required': ['close', 'volume'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 26,
    'notes': '',
}


def compute_alpha_142(panel):
    """Compute gtja191_142.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    v = panel["volume"]
    a = -1.0 * rank(ts_rank(c, 10))
    b = rank(delta(delta(c, 1), 1))
    d = rank(ts_rank(safe_div(v, ts_mean(v, 20)), 5))
    out = a * b * d
    return out


__alpha_meta_alpha_143 = {
    'id': 'gtja191_143',
    'theme': ['momentum'],
    'formula_latex': 'cumprod(1 + (c/delay(c,1)-1) if c>delay(c,1) else 0)',
    'columns_required': ['close'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 1,
    'min_warmup_bars': 2,
    'notes': 'Recursive SELF unrolled to cumulative product of (1 + up_return) since series start.',
}


def compute_alpha_143(panel):
    """Compute gtja191_143.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    dc = c - c.shift(1)
    inc = safe_div(dc, c.shift(1)).where(dc > 0, 0.0)
    out = (1.0 + inc).cumprod()
    return out


__alpha_meta_alpha_144 = {
    'id': 'gtja191_144',
    'theme': ['liquidity'],
    'formula_latex': 'see body',
    'columns_required': ['close', 'amount'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 21,
    'notes': 'SUMIF -> (x*cond).rolling(n).sum(); COUNT -> cond.rolling(n).sum().',
}


def compute_alpha_144(panel):
    """Compute gtja191_144.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    amt = panel["amount"]
    dc = c - c.shift(1)
    cond = (dc < 0).astype("float64")
    x = safe_div((safe_div(c, c.shift(1)) - 1.0).abs(), amt)
    sumif = (x * cond).rolling(20).sum()
    cnt = cond.rolling(20).sum().where(lambda d: d > 0)
    out = safe_div(sumif, cnt)
    return out


__alpha_meta_alpha_145 = {
    'id': 'gtja191_145',
    'theme': ['volume'],
    'formula_latex': '(mean(v,9)-mean(v,26))/mean(v,12)*100',
    'columns_required': ['close', 'volume'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 26,
    'min_warmup_bars': 26,
    'notes': '',
}


def compute_alpha_145(panel):
    """Compute gtja191_145.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    v = panel["volume"]
    out = safe_div(ts_mean(v, 9) - ts_mean(v, 26), ts_mean(v, 12)) * 100.0
    return out


__alpha_meta_alpha_146 = {
    'id': 'gtja191_146',
    'theme': ['momentum'],
    'formula_latex': 'see body',
    'columns_required': ['close'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 81,
    'notes': 'Standardised return deviation; SMA(.,61,2)=ewm(alpha=2/61).',
}


def compute_alpha_146(panel):
    """Compute gtja191_146.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    def _sma(x, n, m):
        """SMA(x, n, m) per GTJA convention -> ewm with alpha = m/n."""
        return x.ewm(alpha=m / n, adjust=False).mean()
    c = panel["close"]
    ret = safe_div(c - c.shift(1), c.shift(1))
    ewm_ret = _sma(ret, 61, 2)
    dev = ret - ewm_ret
    left = ts_mean(dev, 20)
    right = dev
    den = _sma(dev ** 2, 60, 2)
    out = safe_div(left * right, den)
    return out


__alpha_meta_alpha_147 = {
    'id': 'gtja191_147',
    'theme': ['momentum'],
    'formula_latex': 'regbeta(mean(close,12),sequence(12))',
    'columns_required': ['close'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 12,
    'min_warmup_bars': 24,
    'notes': 'Rolling OLS slope of MA12 against linear index, window 12.',
}


def compute_alpha_147(panel):
    """Compute gtja191_147.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    n = 12
    m = ts_mean(c, 12)
    t = pd.DataFrame(
        np.tile(np.arange(c.shape[0], dtype=np.float64).reshape(-1, 1), (1, c.shape[1])),
        index=c.index, columns=c.columns,
    )
    out = safe_div(ts_cov(m, t, n), ts_std(t, n) ** 2)
    return out


__alpha_meta_alpha_148 = {
    'id': 'gtja191_148',
    'theme': ['volume'],
    'formula_latex': 'see body',
    'columns_required': ['open', 'high', 'low', 'close', 'volume'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 75,
    'notes': '',
}


def compute_alpha_148(panel):
    """Compute gtja191_148.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    o = panel["open"]
    v = panel["volume"]
    left = rank(ts_corr(o, ts_mean(v, 60).rolling(9).sum(), 6))
    right = rank(o - ts_min(o, 14))
    out = (left < right).astype("float64") * -1.0
    return out


__alpha_meta_alpha_149 = {
    'id': 'gtja191_149',
    'theme': ['momentum'],
    'formula_latex': 'see body',
    'columns_required': ['close'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 253,
    'notes': 'Downside beta vs. benchmark; uses fallback cross-sectional mean if benchmark_close missing.',
}


def compute_alpha_149(panel):
    """Compute gtja191_149.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    def _bench_close():
        """Benchmark close fallback: cross-sectional mean of `close`."""
        if "benchmark_close" in panel:
            return panel["benchmark_close"]
        c = panel["close"]
        return pd.DataFrame(
            np.tile(c.mean(axis=1).to_numpy().reshape(-1, 1), (1, c.shape[1])),
            index=c.index,
            columns=c.columns,
        )
    c = panel["close"]
    bench = _bench_close()
    br = safe_div(bench - bench.shift(1), bench.shift(1))
    cr = safe_div(c - c.shift(1), c.shift(1))
    # Multiplicative gating instead of NaN-masking so the rolling window keeps
    # enough valid samples (NaN-masking on roughly half the rows blows the
    # min_periods=n requirement on small panels).
    mask = (bench < bench.shift(1)).astype("float64")
    cr_g = cr * mask
    br_g = br * mask
    n = 20
    out = safe_div(ts_cov(cr_g, br_g, n), ts_std(br_g, n) ** 2)
    return out


__alpha_meta_alpha_150 = {
    'id': 'gtja191_150',
    'theme': ['volume'],
    'formula_latex': '(close+high+low)/3*volume',
    'columns_required': ['close', 'high', 'low', 'volume'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 1,
    'min_warmup_bars': 1,
    'notes': '',
}


def compute_alpha_150(panel):
    """Compute gtja191_150.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    h = panel["high"]
    l = panel["low"]
    v = panel["volume"]
    out = (c + h + l) / 3.0 * v
    return out


__alpha_meta_alpha_151 = {
    'id': 'gtja191_151',
    'theme': ['momentum'],
    'formula_latex': 'sma(close-delay(close,20),20,1)',
    'columns_required': ['close'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 21,
    'notes': '',
}


def compute_alpha_151(panel):
    """Compute gtja191_151.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    def _sma(x, n, m):
        """SMA(x, n, m) per GTJA convention -> ewm with alpha = m/n."""
        return x.ewm(alpha=m / n, adjust=False).mean()
    c = panel["close"]
    out = _sma(c - c.shift(20), 20, 1)
    return out


__alpha_meta_alpha_152 = {
    'id': 'gtja191_152',
    'theme': ['momentum'],
    'formula_latex': 'see body',
    'columns_required': ['close'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 26,
    'min_warmup_bars': 50,
    'notes': '',
}


def compute_alpha_152(panel):
    """Compute gtja191_152.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    def _sma(x, n, m):
        """SMA(x, n, m) per GTJA convention -> ewm with alpha = m/n."""
        return x.ewm(alpha=m / n, adjust=False).mean()
    c = panel["close"]
    s = _sma(safe_div(c, c.shift(9)).shift(1), 9, 1).shift(1)
    left = ts_mean(s, 12)
    right = ts_mean(s, 26)
    out = _sma(left - right, 9, 1)
    return out


__alpha_meta_alpha_153 = {
    'id': 'gtja191_153',
    'theme': ['momentum'],
    'formula_latex': '(mean(c,3)+mean(c,6)+mean(c,12)+mean(c,24))/4',
    'columns_required': ['close'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 24,
    'min_warmup_bars': 24,
    'notes': '',
}


def compute_alpha_153(panel):
    """Compute gtja191_153.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    out = (ts_mean(c, 3) + ts_mean(c, 6) + ts_mean(c, 12) + ts_mean(c, 24)) / 4.0
    return out


__alpha_meta_alpha_154 = {
    'id': 'gtja191_154',
    'theme': ['volume'],
    'formula_latex': 'see body',
    'columns_required': ['open', 'high', 'low', 'close', 'volume', 'amount'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 198,
    'notes': 'Original returns boolean; we cast to float and multiply by -1.',
}


def compute_alpha_154(panel):
    """Compute gtja191_154.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    v = panel["volume"]
    vw = vwap(panel, "equity_cn")

    left = vw - ts_min(vw, 16)
    right = ts_corr(vw, ts_mean(v, 180), 18)
    out = (left < right).astype("float64") * -1.0
    return out


__alpha_meta_alpha_155 = {
    'id': 'gtja191_155',
    'theme': ['volume'],
    'formula_latex': 'sma(v,13,2)-sma(v,27,2)-sma(sma(v,13,2)-sma(v,27,2),10,2)',
    'columns_required': ['close', 'volume'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 27,
    'min_warmup_bars': 40,
    'notes': '',
}


def compute_alpha_155(panel):
    """Compute gtja191_155.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    def _sma(x, n, m):
        """SMA(x, n, m) per GTJA convention -> ewm with alpha = m/n."""
        return x.ewm(alpha=m / n, adjust=False).mean()
    v = panel["volume"]
    m = _sma(v, 13, 2) - _sma(v, 27, 2)
    out = m - _sma(m, 10, 2)
    return out


__alpha_meta_alpha_156 = {
    'id': 'gtja191_156',
    'theme': ['volume'],
    'formula_latex': 'see body',
    'columns_required': ['open', 'high', 'low', 'close', 'volume', 'amount'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 5,
    'min_warmup_bars': 10,
    'notes': 'MAX elementwise -> np.maximum.',
}


def compute_alpha_156(panel):
    """Compute gtja191_156.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    o = panel["open"]
    l = panel["low"]
    vw = vwap(panel, "equity_cn")

    a = rank(decay_linear(delta(vw, 5), 3))
    mix = o * 0.15 + l * 0.85
    b_inner = -1.0 * safe_div(delta(mix, 2), mix)
    b = rank(decay_linear(b_inner, 3))
    arr = np.maximum(a.to_numpy(dtype=np.float64, na_value=np.nan),
                     b.to_numpy(dtype=np.float64, na_value=np.nan))
    out = pd.DataFrame(arr, index=a.index, columns=a.columns) * -1.0
    return out


__alpha_meta_alpha_157 = {
    'id': 'gtja191_157',
    'theme': ['volume'],
    'formula_latex': 'see body',
    'columns_required': ['close'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 5,
    'min_warmup_bars': 12,
    'notes': 'PROD(.,1) is identity; we use it directly.',
}


def compute_alpha_157(panel):
    """Compute gtja191_157.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    ret = safe_div(c, c.shift(1)) - 1.0
    inner = -1.0 * rank(delta(c - 1.0, 5))
    inner2 = rank(rank(inner))
    inner3 = ts_min(inner2, 2).rolling(1).sum()
    inner4 = np.log(inner3.replace(0.0, np.nan))
    left = ts_min(rank(rank(inner4)), 5)
    right = ts_rank((-1.0 * ret).shift(6), 5)
    out = left + right
    return out


__alpha_meta_alpha_158 = {
    'id': 'gtja191_158',
    'theme': ['volatility'],
    'formula_latex': '((h-sma(c,15,2))-(l-sma(c,15,2)))/c',
    'columns_required': ['close', 'high', 'low'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 15,
    'min_warmup_bars': 16,
    'notes': '',
}


def compute_alpha_158(panel):
    """Compute gtja191_158.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    def _sma(x, n, m):
        """SMA(x, n, m) per GTJA convention -> ewm with alpha = m/n."""
        return x.ewm(alpha=m / n, adjust=False).mean()
    c = panel["close"]
    h = panel["high"]
    l = panel["low"]
    s = _sma(c, 15, 2)
    out = safe_div((h - s) - (l - s), c)
    return out


__alpha_meta_alpha_159 = {
    'id': 'gtja191_159',
    'theme': ['momentum'],
    'formula_latex': 'see body',
    'columns_required': ['open', 'high', 'low', 'close', 'volume'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 24,
    'min_warmup_bars': 25,
    'notes': '',
}


def compute_alpha_159(panel):
    """Compute gtja191_159.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    h = panel["high"]
    l = panel["low"]
    prev = c.shift(1)
    lo = pd.DataFrame(
        np.minimum(l.to_numpy(dtype=np.float64, na_value=np.nan),
                   prev.to_numpy(dtype=np.float64, na_value=np.nan)),
        index=c.index, columns=c.columns,
    )
    hi = pd.DataFrame(
        np.maximum(h.to_numpy(dtype=np.float64, na_value=np.nan),
                   prev.to_numpy(dtype=np.float64, na_value=np.nan)),
        index=c.index, columns=c.columns,
    )
    def _term(n):
        return safe_div((c - lo.rolling(n).sum()), (hi - lo).rolling(n).sum())
    out = ((_term(6) * 12.0 * 24.0) + (_term(12) * 6.0 * 24.0) + (_term(24) * 6.0 * 12.0)) / (6.0 * 12.0 + 6.0 * 24.0 + 12.0 * 24.0) * 100.0
    return out


__alpha_meta_alpha_160 = {
    'id': 'gtja191_160',
    'theme': ['volatility'],
    'formula_latex': 'sma((c<=delay(c,1)?std(c,20):0),20,1)',
    'columns_required': ['close'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 22,
    'notes': '',
}


def compute_alpha_160(panel):
    """Compute gtja191_160.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    def _sma(x, n, m):
        """SMA(x, n, m) per GTJA convention -> ewm with alpha = m/n."""
        return x.ewm(alpha=m / n, adjust=False).mean()
    c = panel["close"]
    cond = (c <= c.shift(1)).astype("float64")
    out = _sma(ts_std(c, 20) * cond, 20, 1)
    return out


__alpha_meta_alpha_161 = {
    'id': 'gtja191_161',
    'theme': ['volatility'],
    'formula_latex': 'mean(true_range,12)',
    'columns_required': ['close', 'high', 'low'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 12,
    'min_warmup_bars': 13,
    'notes': 'Average True Range (12).',
}


def compute_alpha_161(panel):
    """Compute gtja191_161.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    h = panel["high"]
    l = panel["low"]
    prev = c.shift(1)
    a = (h - l).to_numpy(dtype=np.float64, na_value=np.nan)
    b = (prev - h).abs().to_numpy(dtype=np.float64, na_value=np.nan)
    d = (prev - l).abs().to_numpy(dtype=np.float64, na_value=np.nan)
    tr = np.maximum(np.maximum(a, b), d)
    tr_df = pd.DataFrame(tr, index=c.index, columns=c.columns)
    out = ts_mean(tr_df, 12)
    return out


__alpha_meta_alpha_162 = {
    'id': 'gtja191_162',
    'theme': ['momentum'],
    'formula_latex': 'see body',
    'columns_required': ['close'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 12,
    'min_warmup_bars': 24,
    'notes': 'RSI-style normalised.',
}


def compute_alpha_162(panel):
    """Compute gtja191_162.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    def _sma(x, n, m):
        """SMA(x, n, m) per GTJA convention -> ewm with alpha = m/n."""
        return x.ewm(alpha=m / n, adjust=False).mean()
    c = panel["close"]
    dc = c - c.shift(1)
    rsi = safe_div(_sma(dc.clip(lower=0.0), 12, 1), _sma(dc.abs(), 12, 1)) * 100.0
    out = safe_div(rsi - ts_min(rsi, 12), ts_max(rsi, 12) - ts_min(rsi, 12))
    return out


__alpha_meta_alpha_163 = {
    'id': 'gtja191_163',
    'theme': ['volume'],
    'formula_latex': 'rank(((-1*ret)*mean(v,20))*vwap*(high-close))',
    'columns_required': ['open', 'high', 'low', 'close', 'volume', 'amount'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 21,
    'notes': '',
}


def compute_alpha_163(panel):
    """Compute gtja191_163.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    h = panel["high"]
    v = panel["volume"]
    vw = vwap(panel, "equity_cn")

    ret = safe_div(c, c.shift(1)) - 1.0
    out = rank(((-1.0 * ret) * ts_mean(v, 20)) * vw * (h - c))
    return out


__alpha_meta_alpha_164 = {
    'id': 'gtja191_164',
    'theme': ['momentum'],
    'formula_latex': 'see body',
    'columns_required': ['close', 'high', 'low'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 13,
    'min_warmup_bars': 20,
    'notes': '',
}


def compute_alpha_164(panel):
    """Compute gtja191_164.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    def _sma(x, n, m):
        """SMA(x, n, m) per GTJA convention -> ewm with alpha = m/n."""
        return x.ewm(alpha=m / n, adjust=False).mean()
    c = panel["close"]
    h = panel["high"]
    l = panel["low"]
    dc = c - c.shift(1)
    inv = safe_div(pd.DataFrame(np.ones_like(c, dtype=np.float64), index=c.index, columns=c.columns), dc)
    val = inv.where(dc > 0, 1.0)
    x = safe_div(val - ts_min(val, 12), (h - l)) * 100.0
    out = _sma(x, 13, 2)
    return out


__alpha_meta_alpha_165 = {
    'id': 'gtja191_165',
    'theme': ['volatility'],
    'formula_latex': 'see body',
    'columns_required': ['close'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 48,
    'min_warmup_bars': 142,
    'notes': 'SUMAC = expanding cumulative sum approximated by rolling 48-day cumulative sum.',
}


def compute_alpha_165(panel):
    """Compute gtja191_165.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    dev = c - ts_mean(c, 48)
    csum = dev.rolling(48).sum()
    out = safe_div(ts_max(csum, 48) - ts_min(csum, 48), ts_std(c, 48))
    return out


__alpha_meta_alpha_166 = {
    'id': 'gtja191_166',
    'theme': ['volatility'],
    'formula_latex': 'see body',
    'columns_required': ['close'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 40,
    'notes': 'Skewness-style; constants from report.',
}


def compute_alpha_166(panel):
    """Compute gtja191_166.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    ret = safe_div(c, c.shift(1)) - 1.0
    m = ts_mean(ret, 20)
    num = (ret - m).rolling(20).sum() * -20.0 * (20.0 - 1.0) ** 1.5
    den = (20.0 - 1.0) * (20.0 - 2.0) * (ret ** 2).rolling(20).sum() ** 1.5
    out = safe_div(num, den)
    return out


__alpha_meta_alpha_167 = {
    'id': 'gtja191_167',
    'theme': ['momentum'],
    'formula_latex': 'sum(max(0,c-delay(c,1)),12)',
    'columns_required': ['close'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 12,
    'min_warmup_bars': 13,
    'notes': '',
}


def compute_alpha_167(panel):
    """Compute gtja191_167.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    out = (c - c.shift(1)).clip(lower=0.0).rolling(12).sum()
    return out


__alpha_meta_alpha_168 = {
    'id': 'gtja191_168',
    'theme': ['volume'],
    'formula_latex': '-1*volume/mean(volume,20)',
    'columns_required': ['close', 'volume'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 20,
    'notes': '',
}


def compute_alpha_168(panel):
    """Compute gtja191_168.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    v = panel["volume"]
    out = -1.0 * safe_div(v, ts_mean(v, 20))
    return out


__alpha_meta_alpha_169 = {
    'id': 'gtja191_169',
    'theme': ['momentum'],
    'formula_latex': 'see body',
    'columns_required': ['close'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 26,
    'min_warmup_bars': 50,
    'notes': '',
}


def compute_alpha_169(panel):
    """Compute gtja191_169.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    def _sma(x, n, m):
        """SMA(x, n, m) per GTJA convention -> ewm with alpha = m/n."""
        return x.ewm(alpha=m / n, adjust=False).mean()
    c = panel["close"]
    s = _sma(c - c.shift(1), 9, 1).shift(1)
    out = _sma(ts_mean(s, 12) - ts_mean(s, 26), 10, 1)
    return out


__alpha_meta_alpha_170 = {
    'id': 'gtja191_170',
    'theme': ['volume'],
    'formula_latex': 'see body',
    'columns_required': ['open', 'high', 'low', 'close', 'volume', 'amount'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 21,
    'notes': '',
}


def compute_alpha_170(panel):
    """Compute gtja191_170.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    h = panel["high"]
    v = panel["volume"]
    vw = vwap(panel, "equity_cn")

    a = safe_div(rank(safe_div(pd.DataFrame(1.0, index=c.index, columns=c.columns), c)) * v, ts_mean(v, 20))
    b = safe_div(h * rank(h - c), c.rolling(5).sum() / 5.0)
    d = rank(vw - vw.shift(5))
    out = a * b - d
    return out


__alpha_meta_alpha_171 = {
    'id': 'gtja191_171',
    'theme': ['microstructure'],
    'formula_latex': '-1*((l-c)*(o^5))/((c-h)*(c^5))',
    'columns_required': ['open', 'high', 'low', 'close'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 1,
    'min_warmup_bars': 1,
    'notes': '',
}


def compute_alpha_171(panel):
    """Compute gtja191_171.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    o = panel["open"]
    h = panel["high"]
    l = panel["low"]
    out = safe_div(-1.0 * ((l - c) * (o ** 5)), (c - h) * (c ** 5))
    return out


__alpha_meta_alpha_172 = {
    'id': 'gtja191_172',
    'theme': ['momentum'],
    'formula_latex': 'see body',
    'columns_required': ['close', 'high', 'low'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 14,
    'min_warmup_bars': 20,
    'notes': "Wilder's ADX-style indicator; mean over last 6 bars.",
}


def compute_alpha_172(panel):
    """Compute gtja191_172.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    h = panel["high"]
    l = panel["low"]
    HD = h - h.shift(1)
    LD = l.shift(1) - l
    prev = c.shift(1)
    a = (h - l).to_numpy(dtype=np.float64, na_value=np.nan)
    b = (prev - h).abs().to_numpy(dtype=np.float64, na_value=np.nan)
    d = (prev - l).abs().to_numpy(dtype=np.float64, na_value=np.nan)
    TR = pd.DataFrame(np.maximum(np.maximum(a, b), d), index=c.index, columns=c.columns)
    ld_cond = ((LD > 0) & (LD > HD)).astype("float64")
    hd_cond = ((HD > 0) & (HD > LD)).astype("float64")
    dm_plus = (LD * ld_cond).rolling(14).sum() * 100.0
    dm_minus = (HD * hd_cond).rolling(14).sum() * 100.0
    tr14 = TR.rolling(14).sum()
    di_p = safe_div(dm_plus, tr14)
    di_m = safe_div(dm_minus, tr14)
    dx = safe_div((di_p - di_m).abs(), di_p + di_m) * 100.0
    out = ts_mean(dx, 6)
    return out


__alpha_meta_alpha_173 = {
    'id': 'gtja191_173',
    'theme': ['momentum'],
    'formula_latex': '3*sma(c,13,2)-2*sma(sma(c,13,2),13,2)+sma(sma(sma(log(c),13,2),13,2),13,2)',
    'columns_required': ['close'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 13,
    'min_warmup_bars': 40,
    'notes': '',
}


def compute_alpha_173(panel):
    """Compute gtja191_173.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    def _sma(x, n, m):
        """SMA(x, n, m) per GTJA convention -> ewm with alpha = m/n."""
        return x.ewm(alpha=m / n, adjust=False).mean()
    c = panel["close"]
    s1 = _sma(c, 13, 2)
    s2 = _sma(s1, 13, 2)
    s3 = _sma(_sma(_sma(np.log(c), 13, 2), 13, 2), 13, 2)
    out = 3.0 * s1 - 2.0 * s2 + s3
    return out


__alpha_meta_alpha_174 = {
    'id': 'gtja191_174',
    'theme': ['volatility'],
    'formula_latex': 'sma((c>delay(c,1)?std(c,20):0),20,1)',
    'columns_required': ['close'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 22,
    'notes': '',
}


def compute_alpha_174(panel):
    """Compute gtja191_174.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    def _sma(x, n, m):
        """SMA(x, n, m) per GTJA convention -> ewm with alpha = m/n."""
        return x.ewm(alpha=m / n, adjust=False).mean()
    c = panel["close"]
    cond = (c > c.shift(1)).astype("float64")
    out = _sma(ts_std(c, 20) * cond, 20, 1)
    return out


__alpha_meta_alpha_175 = {
    'id': 'gtja191_175',
    'theme': ['volatility'],
    'formula_latex': 'mean(true_range,6)',
    'columns_required': ['close', 'high', 'low'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 6,
    'min_warmup_bars': 7,
    'notes': 'ATR(6).',
}


def compute_alpha_175(panel):
    """Compute gtja191_175.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    h = panel["high"]
    l = panel["low"]
    prev = c.shift(1)
    a = (h - l).to_numpy(dtype=np.float64, na_value=np.nan)
    b = (prev - h).abs().to_numpy(dtype=np.float64, na_value=np.nan)
    d = (prev - l).abs().to_numpy(dtype=np.float64, na_value=np.nan)
    tr = np.maximum(np.maximum(a, b), d)
    tr_df = pd.DataFrame(tr, index=c.index, columns=c.columns)
    out = ts_mean(tr_df, 6)
    return out


__alpha_meta_alpha_176 = {
    'id': 'gtja191_176',
    'theme': ['volume'],
    'formula_latex': 'see body',
    'columns_required': ['open', 'high', 'low', 'close', 'volume'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 12,
    'min_warmup_bars': 18,
    'notes': '',
}


def compute_alpha_176(panel):
    """Compute gtja191_176.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    h = panel["high"]
    l = panel["low"]
    v = panel["volume"]
    ll = ts_min(l, 12)
    hh = ts_max(h, 12)
    pos = safe_div(c - ll, hh - ll)
    out = ts_corr(rank(pos), rank(v), 6)
    return out


__alpha_meta_alpha_177 = {
    'id': 'gtja191_177',
    'theme': ['momentum'],
    'formula_latex': '((20-highday(h,20))/20)*100',
    'columns_required': ['close', 'high'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 20,
    'notes': '',
}


def compute_alpha_177(panel):
    """Compute gtja191_177.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    h = panel["high"]
    out = (20.0 - ts_argmax(h, 20)) / 20.0 * 100.0
    return out


__alpha_meta_alpha_178 = {
    'id': 'gtja191_178',
    'theme': ['momentum', 'volume'],
    'formula_latex': '(c-delay(c,1))/delay(c,1)*v',
    'columns_required': ['close', 'volume'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 1,
    'min_warmup_bars': 2,
    'notes': '',
}


def compute_alpha_178(panel):
    """Compute gtja191_178.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    v = panel["volume"]
    out = safe_div(c - c.shift(1), c.shift(1)) * v
    return out


__alpha_meta_alpha_179 = {
    'id': 'gtja191_179',
    'theme': ['volume'],
    'formula_latex': 'rank(corr(vwap,v,4))*rank(corr(rank(low),rank(mean(v,50)),12))',
    'columns_required': ['open', 'high', 'low', 'close', 'volume', 'amount'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 50,
    'min_warmup_bars': 62,
    'notes': '',
}


def compute_alpha_179(panel):
    """Compute gtja191_179.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    l = panel["low"]
    v = panel["volume"]
    vw = vwap(panel, "equity_cn")

    out = rank(ts_corr(vw, v, 4)) * rank(ts_corr(rank(l), rank(ts_mean(v, 50)), 12))
    return out


__alpha_meta_alpha_180 = {
    'id': 'gtja191_180',
    'theme': ['volume', 'reversal'],
    'formula_latex': 'see body',
    'columns_required': ['close', 'volume'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 67,
    'notes': '',
}


def compute_alpha_180(panel):
    """Compute gtja191_180.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    v = panel["volume"]
    big = (ts_mean(v, 20) < v).astype("float64")
    left = -1.0 * ts_rank(delta(c, 7).abs(), 60) * np.sign(delta(c, 7))
    right = -1.0 * v
    out = left * big + right * (1.0 - big)
    return out


__alpha_meta_alpha_181 = {
    'id': 'gtja191_181',
    'theme': ['volatility'],
    'formula_latex': 'see body',
    'columns_required': ['close'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 40,
    'notes': 'Benchmark falls back to cross-sectional mean of close.',
}


def compute_alpha_181(panel):
    """Compute gtja191_181.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    def _bench_close():
        """Benchmark close fallback: cross-sectional mean of `close`."""
        if "benchmark_close" in panel:
            return panel["benchmark_close"]
        c = panel["close"]
        return pd.DataFrame(
            np.tile(c.mean(axis=1).to_numpy().reshape(-1, 1), (1, c.shape[1])),
            index=c.index,
            columns=c.columns,
        )
    c = panel["close"]
    bench = _bench_close()
    br = safe_div(bench, bench.shift(1)) - 1.0
    cr = safe_div(c, c.shift(1)) - 1.0
    diff = (cr - ts_mean(cr, 20)) - (br - ts_mean(br, 20)) ** 2
    num = diff.rolling(20).sum()
    den = ((br - ts_mean(br, 20)) ** 3).rolling(20).sum()
    out = safe_div(num, den)
    return out


__alpha_meta_alpha_182 = {
    'id': 'gtja191_182',
    'theme': ['momentum'],
    'formula_latex': 'see body',
    'columns_required': ['open', 'high', 'low', 'close', 'volume'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 21,
    'notes': 'Benchmark falls back to cross-sectional mean of close.',
}


def compute_alpha_182(panel):
    """Compute gtja191_182.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    def _bench_close():
        """Benchmark close fallback: cross-sectional mean of `close`."""
        if "benchmark_close" in panel:
            return panel["benchmark_close"]
        c = panel["close"]
        return pd.DataFrame(
            np.tile(c.mean(axis=1).to_numpy().reshape(-1, 1), (1, c.shape[1])),
            index=c.index,
            columns=c.columns,
        )
    c = panel["close"]
    o = panel["open"]
    bench = _bench_close()
    up = ((c > o) & (bench > bench.shift(1)))
    dn = ((c < o) & (bench < bench.shift(1)))
    cond = (up | dn).astype("float64")
    out = cond.rolling(20).sum() / 20.0
    return out


__alpha_meta_alpha_183 = {
    'id': 'gtja191_183',
    'theme': ['volatility'],
    'formula_latex': 'see body',
    'columns_required': ['close'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 24,
    'min_warmup_bars': 70,
    'notes': '',
}


def compute_alpha_183(panel):
    """Compute gtja191_183.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    dev = c - ts_mean(c, 24)
    csum = dev.rolling(24).sum()
    out = safe_div(ts_max(csum, 24) - ts_min(csum, 24), ts_std(c, 24))
    return out


__alpha_meta_alpha_184 = {
    'id': 'gtja191_184',
    'theme': ['reversal'],
    'formula_latex': 'see body',
    'columns_required': ['open', 'close'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 202,
    'notes': '',
}


def compute_alpha_184(panel):
    """Compute gtja191_184.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    o = panel["open"]
    left = rank(ts_corr((o - c).shift(1), c, 200))
    right = rank(o - c)
    out = left + right
    return out


__alpha_meta_alpha_185 = {
    'id': 'gtja191_185',
    'theme': ['reversal'],
    'formula_latex': 'rank(-1*(1-open/close)^2)',
    'columns_required': ['open', 'close'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 1,
    'min_warmup_bars': 1,
    'notes': '',
}


def compute_alpha_185(panel):
    """Compute gtja191_185.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    o = panel["open"]
    out = rank(-1.0 * (1.0 - safe_div(o, c)) ** 2)
    return out


__alpha_meta_alpha_186 = {
    'id': 'gtja191_186',
    'theme': ['momentum'],
    'formula_latex': 'see body (alpha172 averaged with its 6-day lag)',
    'columns_required': ['close', 'high', 'low'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 14,
    'min_warmup_bars': 27,
    'notes': 'alpha172 averaged with its 6-day lag.',
}


def compute_alpha_186(panel):
    """Compute gtja191_186.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    h = panel["high"]
    l = panel["low"]
    HD = h - h.shift(1)
    LD = l.shift(1) - l
    prev = c.shift(1)
    a = (h - l).to_numpy(dtype=np.float64, na_value=np.nan)
    b = (prev - h).abs().to_numpy(dtype=np.float64, na_value=np.nan)
    d = (prev - l).abs().to_numpy(dtype=np.float64, na_value=np.nan)
    TR = pd.DataFrame(np.maximum(np.maximum(a, b), d), index=c.index, columns=c.columns)
    ld_cond = ((LD > 0) & (LD > HD)).astype("float64")
    hd_cond = ((HD > 0) & (HD > LD)).astype("float64")
    dm_plus = (LD * ld_cond).rolling(14).sum() * 100.0
    dm_minus = (HD * hd_cond).rolling(14).sum() * 100.0
    tr14 = TR.rolling(14).sum()
    di_p = safe_div(dm_plus, tr14)
    di_m = safe_div(dm_minus, tr14)
    dx = safe_div((di_p - di_m).abs(), di_p + di_m) * 100.0
    a172 = ts_mean(dx, 6)
    out = (a172 + a172.shift(6)) / 2.0
    return out


__alpha_meta_alpha_187 = {
    'id': 'gtja191_187',
    'theme': ['reversal'],
    'formula_latex': 'see body',
    'columns_required': ['open', 'high'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 21,
    'notes': '',
}


def compute_alpha_187(panel):
    """Compute gtja191_187.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    o = panel["open"]
    h = panel["high"]
    prev = o.shift(1)
    cond = (o <= prev).astype("float64")
    arr_a = (h - o).to_numpy(dtype=np.float64, na_value=np.nan)
    arr_b = (o - prev).to_numpy(dtype=np.float64, na_value=np.nan)
    mx = pd.DataFrame(np.maximum(arr_a, arr_b), index=o.index, columns=o.columns)
    val = mx * (1.0 - cond)
    out = val.rolling(20).sum()
    return out


__alpha_meta_alpha_188 = {
    'id': 'gtja191_188',
    'theme': ['volatility'],
    'formula_latex': '(h-l-sma(h-l,11,2))/sma(h-l,11,2)*100',
    'columns_required': ['close', 'high', 'low'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 11,
    'min_warmup_bars': 13,
    'notes': '',
}


def compute_alpha_188(panel):
    """Compute gtja191_188.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    def _sma(x, n, m):
        """SMA(x, n, m) per GTJA convention -> ewm with alpha = m/n."""
        return x.ewm(alpha=m / n, adjust=False).mean()
    h = panel["high"]
    l = panel["low"]
    hl = h - l
    s = _sma(hl, 11, 2)
    out = safe_div(hl - s, s) * 100.0
    return out


__alpha_meta_alpha_189 = {
    'id': 'gtja191_189',
    'theme': ['volatility'],
    'formula_latex': 'mean(abs(c-mean(c,6)),6)',
    'columns_required': ['close'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 6,
    'min_warmup_bars': 12,
    'notes': '',
}


def compute_alpha_189(panel):
    """Compute gtja191_189.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    out = ts_mean((c - ts_mean(c, 6)).abs(), 6)
    return out


__alpha_meta_alpha_190 = {
    'id': 'gtja191_190',
    'theme': ['momentum'],
    'formula_latex': 'see body',
    'columns_required': ['close'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 39,
    'notes': 'Complex log of ratio of conditional squared deviations.',
}


def compute_alpha_190(panel):
    """Compute gtja191_190.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    ret = safe_div(c, c.shift(1)) - 1.0
    geo = signed_power(safe_div(c, c.shift(19)), 1.0 / 20.0) - 1.0
    cond_up = (ret > geo).astype("float64")
    cond_dn = (ret < geo).astype("float64")
    cnt_up = cond_up.rolling(20).sum() - 1.0
    cnt_dn = cond_dn.rolling(20).sum()
    sumif_dn = (((ret - geo) ** 2) * cond_dn).rolling(20).sum()
    sumif_up = (((ret - geo) ** 2) * cond_up).rolling(20).sum()
    out = np.log(safe_div(cnt_up * sumif_dn, cnt_dn * sumif_up).replace([0, np.inf, -np.inf], np.nan))
    return out


__alpha_meta_alpha_191 = {
    'id': 'gtja191_191',
    'theme': ['volume'],
    'formula_latex': 'see body',
    'columns_required': ['open', 'high', 'low', 'close', 'volume'],
    'extras_required': [],
    'universe': ['equity_cn'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 25,
    'notes': '',
}


def compute_alpha_191(panel):
    """Compute gtja191_191.

    Args:
        panel: dict[str, pd.DataFrame] with at least the required columns.

    Returns:
        pd.DataFrame with index = panel["close"].index, columns = panel["close"].columns.
    """
    c = panel["close"]
    h = panel["high"]
    l = panel["low"]
    v = panel["volume"]
    out = (ts_corr(ts_mean(v, 20), l, 5) + (h + l) / 2.0) - c
    return out

def get_all_gtja191_factors() -> list:
    """Return list of (meta_dict, compute_fn) tuples for all Guotai Junan 191 Alphas factors."""
    return [
        (__alpha_meta_alpha_001, compute_alpha_001),
        (__alpha_meta_alpha_002, compute_alpha_002),
        (__alpha_meta_alpha_003, compute_alpha_003),
        (__alpha_meta_alpha_004, compute_alpha_004),
        (__alpha_meta_alpha_005, compute_alpha_005),
        (__alpha_meta_alpha_006, compute_alpha_006),
        (__alpha_meta_alpha_007, compute_alpha_007),
        (__alpha_meta_alpha_008, compute_alpha_008),
        (__alpha_meta_alpha_009, compute_alpha_009),
        (__alpha_meta_alpha_010, compute_alpha_010),
        (__alpha_meta_alpha_011, compute_alpha_011),
        (__alpha_meta_alpha_012, compute_alpha_012),
        (__alpha_meta_alpha_013, compute_alpha_013),
        (__alpha_meta_alpha_014, compute_alpha_014),
        (__alpha_meta_alpha_015, compute_alpha_015),
        (__alpha_meta_alpha_016, compute_alpha_016),
        (__alpha_meta_alpha_017, compute_alpha_017),
        (__alpha_meta_alpha_018, compute_alpha_018),
        (__alpha_meta_alpha_019, compute_alpha_019),
        (__alpha_meta_alpha_020, compute_alpha_020),
        (__alpha_meta_alpha_021, compute_alpha_021),
        (__alpha_meta_alpha_022, compute_alpha_022),
        (__alpha_meta_alpha_023, compute_alpha_023),
        (__alpha_meta_alpha_024, compute_alpha_024),
        (__alpha_meta_alpha_025, compute_alpha_025),
        (__alpha_meta_alpha_026, compute_alpha_026),
        (__alpha_meta_alpha_027, compute_alpha_027),
        (__alpha_meta_alpha_028, compute_alpha_028),
        (__alpha_meta_alpha_029, compute_alpha_029),
        (__alpha_meta_alpha_030, compute_alpha_030),
        (__alpha_meta_alpha_031, compute_alpha_031),
        (__alpha_meta_alpha_032, compute_alpha_032),
        (__alpha_meta_alpha_033, compute_alpha_033),
        (__alpha_meta_alpha_034, compute_alpha_034),
        (__alpha_meta_alpha_035, compute_alpha_035),
        (__alpha_meta_alpha_036, compute_alpha_036),
        (__alpha_meta_alpha_037, compute_alpha_037),
        (__alpha_meta_alpha_038, compute_alpha_038),
        (__alpha_meta_alpha_039, compute_alpha_039),
        (__alpha_meta_alpha_040, compute_alpha_040),
        (__alpha_meta_alpha_041, compute_alpha_041),
        (__alpha_meta_alpha_042, compute_alpha_042),
        (__alpha_meta_alpha_043, compute_alpha_043),
        (__alpha_meta_alpha_044, compute_alpha_044),
        (__alpha_meta_alpha_045, compute_alpha_045),
        (__alpha_meta_alpha_046, compute_alpha_046),
        (__alpha_meta_alpha_047, compute_alpha_047),
        (__alpha_meta_alpha_048, compute_alpha_048),
        (__alpha_meta_alpha_049, compute_alpha_049),
        (__alpha_meta_alpha_050, compute_alpha_050),
        (__alpha_meta_alpha_051, compute_alpha_051),
        (__alpha_meta_alpha_052, compute_alpha_052),
        (__alpha_meta_alpha_053, compute_alpha_053),
        (__alpha_meta_alpha_054, compute_alpha_054),
        (__alpha_meta_alpha_055, compute_alpha_055),
        (__alpha_meta_alpha_056, compute_alpha_056),
        (__alpha_meta_alpha_057, compute_alpha_057),
        (__alpha_meta_alpha_058, compute_alpha_058),
        (__alpha_meta_alpha_059, compute_alpha_059),
        (__alpha_meta_alpha_060, compute_alpha_060),
        (__alpha_meta_alpha_061, compute_alpha_061),
        (__alpha_meta_alpha_062, compute_alpha_062),
        (__alpha_meta_alpha_063, compute_alpha_063),
        (__alpha_meta_alpha_064, compute_alpha_064),
        (__alpha_meta_alpha_065, compute_alpha_065),
        (__alpha_meta_alpha_066, compute_alpha_066),
        (__alpha_meta_alpha_067, compute_alpha_067),
        (__alpha_meta_alpha_068, compute_alpha_068),
        (__alpha_meta_alpha_069, compute_alpha_069),
        (__alpha_meta_alpha_070, compute_alpha_070),
        (__alpha_meta_alpha_071, compute_alpha_071),
        (__alpha_meta_alpha_072, compute_alpha_072),
        (__alpha_meta_alpha_073, compute_alpha_073),
        (__alpha_meta_alpha_074, compute_alpha_074),
        (__alpha_meta_alpha_075, compute_alpha_075),
        (__alpha_meta_alpha_076, compute_alpha_076),
        (__alpha_meta_alpha_077, compute_alpha_077),
        (__alpha_meta_alpha_078, compute_alpha_078),
        (__alpha_meta_alpha_079, compute_alpha_079),
        (__alpha_meta_alpha_080, compute_alpha_080),
        (__alpha_meta_alpha_081, compute_alpha_081),
        (__alpha_meta_alpha_082, compute_alpha_082),
        (__alpha_meta_alpha_083, compute_alpha_083),
        (__alpha_meta_alpha_084, compute_alpha_084),
        (__alpha_meta_alpha_085, compute_alpha_085),
        (__alpha_meta_alpha_086, compute_alpha_086),
        (__alpha_meta_alpha_087, compute_alpha_087),
        (__alpha_meta_alpha_088, compute_alpha_088),
        (__alpha_meta_alpha_089, compute_alpha_089),
        (__alpha_meta_alpha_090, compute_alpha_090),
        (__alpha_meta_alpha_091, compute_alpha_091),
        (__alpha_meta_alpha_092, compute_alpha_092),
        (__alpha_meta_alpha_093, compute_alpha_093),
        (__alpha_meta_alpha_094, compute_alpha_094),
        (__alpha_meta_alpha_095, compute_alpha_095),
        (__alpha_meta_alpha_096, compute_alpha_096),
        (__alpha_meta_alpha_097, compute_alpha_097),
        (__alpha_meta_alpha_098, compute_alpha_098),
        (__alpha_meta_alpha_099, compute_alpha_099),
        (__alpha_meta_alpha_100, compute_alpha_100),
        (__alpha_meta_alpha_101, compute_alpha_101),
        (__alpha_meta_alpha_102, compute_alpha_102),
        (__alpha_meta_alpha_103, compute_alpha_103),
        (__alpha_meta_alpha_104, compute_alpha_104),
        (__alpha_meta_alpha_105, compute_alpha_105),
        (__alpha_meta_alpha_106, compute_alpha_106),
        (__alpha_meta_alpha_107, compute_alpha_107),
        (__alpha_meta_alpha_108, compute_alpha_108),
        (__alpha_meta_alpha_109, compute_alpha_109),
        (__alpha_meta_alpha_110, compute_alpha_110),
        (__alpha_meta_alpha_111, compute_alpha_111),
        (__alpha_meta_alpha_112, compute_alpha_112),
        (__alpha_meta_alpha_113, compute_alpha_113),
        (__alpha_meta_alpha_114, compute_alpha_114),
        (__alpha_meta_alpha_115, compute_alpha_115),
        (__alpha_meta_alpha_116, compute_alpha_116),
        (__alpha_meta_alpha_117, compute_alpha_117),
        (__alpha_meta_alpha_118, compute_alpha_118),
        (__alpha_meta_alpha_119, compute_alpha_119),
        (__alpha_meta_alpha_120, compute_alpha_120),
        (__alpha_meta_alpha_121, compute_alpha_121),
        (__alpha_meta_alpha_122, compute_alpha_122),
        (__alpha_meta_alpha_123, compute_alpha_123),
        (__alpha_meta_alpha_124, compute_alpha_124),
        (__alpha_meta_alpha_125, compute_alpha_125),
        (__alpha_meta_alpha_126, compute_alpha_126),
        (__alpha_meta_alpha_127, compute_alpha_127),
        (__alpha_meta_alpha_128, compute_alpha_128),
        (__alpha_meta_alpha_129, compute_alpha_129),
        (__alpha_meta_alpha_130, compute_alpha_130),
        (__alpha_meta_alpha_131, compute_alpha_131),
        (__alpha_meta_alpha_132, compute_alpha_132),
        (__alpha_meta_alpha_133, compute_alpha_133),
        (__alpha_meta_alpha_134, compute_alpha_134),
        (__alpha_meta_alpha_135, compute_alpha_135),
        (__alpha_meta_alpha_136, compute_alpha_136),
        (__alpha_meta_alpha_137, compute_alpha_137),
        (__alpha_meta_alpha_138, compute_alpha_138),
        (__alpha_meta_alpha_139, compute_alpha_139),
        (__alpha_meta_alpha_140, compute_alpha_140),
        (__alpha_meta_alpha_141, compute_alpha_141),
        (__alpha_meta_alpha_142, compute_alpha_142),
        (__alpha_meta_alpha_143, compute_alpha_143),
        (__alpha_meta_alpha_144, compute_alpha_144),
        (__alpha_meta_alpha_145, compute_alpha_145),
        (__alpha_meta_alpha_146, compute_alpha_146),
        (__alpha_meta_alpha_147, compute_alpha_147),
        (__alpha_meta_alpha_148, compute_alpha_148),
        (__alpha_meta_alpha_149, compute_alpha_149),
        (__alpha_meta_alpha_150, compute_alpha_150),
        (__alpha_meta_alpha_151, compute_alpha_151),
        (__alpha_meta_alpha_152, compute_alpha_152),
        (__alpha_meta_alpha_153, compute_alpha_153),
        (__alpha_meta_alpha_154, compute_alpha_154),
        (__alpha_meta_alpha_155, compute_alpha_155),
        (__alpha_meta_alpha_156, compute_alpha_156),
        (__alpha_meta_alpha_157, compute_alpha_157),
        (__alpha_meta_alpha_158, compute_alpha_158),
        (__alpha_meta_alpha_159, compute_alpha_159),
        (__alpha_meta_alpha_160, compute_alpha_160),
        (__alpha_meta_alpha_161, compute_alpha_161),
        (__alpha_meta_alpha_162, compute_alpha_162),
        (__alpha_meta_alpha_163, compute_alpha_163),
        (__alpha_meta_alpha_164, compute_alpha_164),
        (__alpha_meta_alpha_165, compute_alpha_165),
        (__alpha_meta_alpha_166, compute_alpha_166),
        (__alpha_meta_alpha_167, compute_alpha_167),
        (__alpha_meta_alpha_168, compute_alpha_168),
        (__alpha_meta_alpha_169, compute_alpha_169),
        (__alpha_meta_alpha_170, compute_alpha_170),
        (__alpha_meta_alpha_171, compute_alpha_171),
        (__alpha_meta_alpha_172, compute_alpha_172),
        (__alpha_meta_alpha_173, compute_alpha_173),
        (__alpha_meta_alpha_174, compute_alpha_174),
        (__alpha_meta_alpha_175, compute_alpha_175),
        (__alpha_meta_alpha_176, compute_alpha_176),
        (__alpha_meta_alpha_177, compute_alpha_177),
        (__alpha_meta_alpha_178, compute_alpha_178),
        (__alpha_meta_alpha_179, compute_alpha_179),
        (__alpha_meta_alpha_180, compute_alpha_180),
        (__alpha_meta_alpha_181, compute_alpha_181),
        (__alpha_meta_alpha_182, compute_alpha_182),
        (__alpha_meta_alpha_183, compute_alpha_183),
        (__alpha_meta_alpha_184, compute_alpha_184),
        (__alpha_meta_alpha_185, compute_alpha_185),
        (__alpha_meta_alpha_186, compute_alpha_186),
        (__alpha_meta_alpha_187, compute_alpha_187),
        (__alpha_meta_alpha_188, compute_alpha_188),
        (__alpha_meta_alpha_189, compute_alpha_189),
        (__alpha_meta_alpha_190, compute_alpha_190),
        (__alpha_meta_alpha_191, compute_alpha_191),
    ]
