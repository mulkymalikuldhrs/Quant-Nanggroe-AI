#!/usr/bin/env python3
"""Standalone backtest of ALL 14 QNAI-specific strategies on BTC-USD and EURUSD.

Reimplements each strategy's core signal logic inline (no QNAI engine import).
Uses only numpy/pandas/yfinance.
Outputs comparison table to backtest_results.md
"""

import numpy as np
import pandas as pd
import warnings, textwrap, sys, os
from datetime import datetime, timedelta

warnings.filterwarnings("ignore")

# ============================================================
# 1. DATA LOADING
# ============================================================

def load_data(symbol, period="2y"):
    """Load OHLCV data via yfinance."""
    import yfinance as yf
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period)
    if df.empty:
        raise ValueError(f"No data for {symbol}")
    # Flatten MultiIndex columns if needed
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    df.index = pd.DatetimeIndex(df.index)
    return df

# ============================================================
# 2. HELPER FUNCTIONS (from base_strategy)
# ============================================================

def compute_sma(series, period):
    return series.rolling(window=period, min_periods=period).mean()

def compute_ema(series, period):
    return series.ewm(span=period, adjust=False, min_periods=period).mean()

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1.0/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0/period, min_periods=period, adjust=False).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    return 100.0 - (100.0 / (1.0 + rs))

def compute_atr(high, low, close, period=14):
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period, min_periods=period).mean()

def compute_bollinger(series, period=20, num_std=2.0):
    middle = series.rolling(window=period, min_periods=period).mean()
    std = series.rolling(window=period, min_periods=period).std()
    return middle + num_std*std, middle, middle - num_std*std

def compute_macd(series, fast=12, slow=26, signal=9):
    fast_ema = series.ewm(span=fast, adjust=False).mean()
    slow_ema = series.ewm(span=slow, adjust=False).mean()
    macd = fast_ema - slow_ema
    sig = macd.ewm(span=signal, adjust=False).mean()
    return macd, sig, macd - sig

def compute_zscore(series, period):
    rm = series.rolling(window=period, min_periods=period).mean()
    rs = series.rolling(window=period, min_periods=period).std()
    return (series - rm) / (rs + 1e-10)

# ============================================================
# 3. STRATEGY SIGNAL FUNCTIONS
# Each returns a pd.Series of -1 (short), 0 (flat), 1 (long) aligned to input index
# ============================================================

# --- 3a. Mean Reversion ---
def mean_reversion_signals(df, lookback=20, entry_threshold=2.0):
    close = df['close']
    zs = compute_zscore(close, lookback)
    sig = pd.Series(0.0, index=df.index)
    sig[zs > entry_threshold] = -1.0   # short overbought
    sig[zs < -entry_threshold] = 1.0    # long oversold
    return sig

# --- 3b. Momentum (time-series) ---
def momentum_signals(df, lookback=126, entry_threshold=0.05):
    close = df['close']
    ret = close.pct_change(lookback)
    sig = pd.Series(0.0, index=df.index)
    sig[ret > entry_threshold] = 1.0
    sig[ret < -entry_threshold] = -1.0
    return sig

# --- 3c. Volatility Arbitrage ---
def vol_arb_signals(df, vol_lookback=20, vol_long_lookback=60, entry_threshold=2.0):
    close = df['close']
    log_ret = np.log(close / close.shift(1))
    # EWMA vol
    lam = 0.94
    vol = np.sqrt(log_ret.pow(2).ewm(alpha=1-lam, adjust=False).mean())
    hist_vol = vol.rolling(vol_long_lookback, min_periods=vol_long_lookback).mean()
    ratio = vol / (hist_vol + 1e-10)
    rmean = ratio.rolling(vol_long_lookback, min_periods=vol_long_lookback).mean()
    rstd = ratio.rolling(vol_long_lookback, min_periods=vol_long_lookback).std()
    z = (ratio - rmean) / (rstd + 1e-10)
    sig = pd.Series(0.0, index=df.index)
    sig[z > entry_threshold] = -1.0   # short vol (vol too high)
    sig[z < -entry_threshold] = 1.0    # long vol (vol too low)
    return sig

# --- 3d. Market Making (simplified for daily) ---
def market_making_signals(df):
    # On daily data, market making doesn't make sense.
    # Simplified: buy dips below lower bollinger, sell rips above upper
    close = df['close']
    upper, mid, lower = compute_bollinger(close, 20, 2.0)
    sig = pd.Series(0.0, index=df.index)
    sig[close < lower] = 1.0
    sig[close > upper] = -1.0
    return sig

# --- 3e. Regime-Based (fallback detection) ---
def regime_based_signals(df):
    close = df['close']
    returns = close.pct_change().dropna()
    sig = pd.Series(0.0, index=df.index)

    for i in range(60, len(df)):
        window = returns.iloc[i-60:i]
        if len(window) < 20:
            continue
        r = float(window.iloc[-20:].mean()) * 252
        v = float(window.iloc[-20:].std()) * np.sqrt(252)
        lt_v = float(window.std()) * np.sqrt(252)
        hv = v > lt_v * 1.5

        if hv:
            regime = 3  # high vol
        elif r > 0.05:
            regime = 0  # bull
        elif r < -0.05:
            regime = 1  # bear
        else:
            regime = 2  # range

        p = float(close.iloc[i])
        sma20 = float(compute_sma(close.iloc[:i+1], 20).iloc[-1]) if i >= 20 else p

        if regime == 0:
            ratio = p / sma20 if sma20 > 0 else 1.0
            sig.iloc[i] = min((ratio - 1.0) * 10, 1.0) if ratio > 1.0 else 0.0
        elif regime == 1:
            ratio = p / sma20 if sma20 > 0 else 1.0
            sig.iloc[i] = -min((1.0 - ratio) * 10, 1.0) if ratio < 1.0 else 0.0
        elif regime == 2:
            rsi_val = float(compute_rsi(close.iloc[:i+1], 14).iloc[-1])
            if rsi_val < 30:
                sig.iloc[i] = 0.5
            elif rsi_val > 70:
                sig.iloc[i] = -0.5
    return sig

# --- 3f. SMC (Smart Money Concepts) ---
def smc_signals(df, min_confluence=2):
    close = df['close'].values
    high = df['high'].values
    low = df['low'].values
    n = len(df)
    sig = pd.Series(0.0, index=df.index)

    # Order blocks
    ob = np.zeros(n)
    for i in range(2, n):
        if close[i-1] > close[i-2] and close[i] < close[i-1]:
            ob[i] = -1  # bearish OB
        elif close[i-1] < close[i-2] and close[i] > close[i-1]:
            ob[i] = 1   # bullish OB

    # Liquidity sweeps
    liq = np.zeros(n)
    for i in range(5, n):
        if high[i] > np.max(high[i-5:i]):
            liq[i] = -1
        if low[i] < np.min(low[i-5:i]):
            liq[i] = 1

    # FVG
    fvg = np.zeros(n)
    for i in range(2, n):
        if low[i-2] > high[i]:
            fvg[i-1] = 1
        elif high[i-2] < low[i]:
            fvg[i-1] = -1

    # Market structure
    ms = np.zeros(n)
    for i in range(2, n):
        if high[i] > high[i-1] or low[i] > low[i-1]:
            ms[i] = 1
        elif high[i] < high[i-1] or low[i] < low[i-1]:
            ms[i] = -1

    atr_vals = compute_atr(df['high'], df['low'], df['close']).values

    for i in range(20, n):
        buy_score = sum([ob[i]==1, liq[i]==1, fvg[i]==1, ms[i]==1])
        sell_score = sum([ob[i]==-1, liq[i]==-1, fvg[i]==-1, ms[i]==-1])
        if buy_score >= min_confluence:
            sig.iloc[i] = 1.0
        elif sell_score >= min_confluence:
            sig.iloc[i] = -1.0

    return sig

# --- 3g. ICT (Inner Circle Trader) ---
def ict_signals(df, disp_atr_mult=1.5, ote_min=0.618, ote_max=0.702):
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values
    atr = compute_atr(df['high'], df['low'], df['close'], 14).values
    n = len(df)
    sig = pd.Series(0.0, index=df.index)

    for i in range(30, n):
        # Detect displacement in last 10 bars
        displacement = None
        disp_start = None
        for j in range(i, max(i-10, 2), -1):
            if j < 2 or np.isnan(atr[j]):
                continue
            candle_range = high[j] - low[j]
            body = abs(close[j] - close[j-1])
            if candle_range > atr[j] * disp_atr_mult and body > candle_range * 0.5:
                if close[j] > close[j-1]:
                    displacement = "bullish"
                else:
                    displacement = "bearish"
                disp_start = j
                break

        if not displacement:
            continue

        # FVG at displacement
        fvg_dir = None
        if disp_start >= 2:
            if low[disp_start-2] > high[disp_start]:
                fvg_dir = "bullish"
            elif high[disp_start-2] < low[disp_start]:
                fvg_dir = "bearish"

        # Order block at displacement
        ob_dir = None
        if disp_start >= 3:
            if close[disp_start] > close[disp_start-1] and close[disp_start-1] < close[disp_start-2]:
                ob_dir = "bullish"
            elif close[disp_start] < close[disp_start-1] and close[disp_start-1] > close[disp_start-2]:
                ob_dir = "bearish"

        # OTE levels
        move_high = max(high[max(0,disp_start-1):min(n, disp_start+2)])
        move_low = min(low[max(0,disp_start-1):min(n, disp_start+2)])
        dist = move_high - move_low
        ote_buy_high = move_low + dist * ote_max
        ote_buy_low = move_low + dist * ote_min
        ote_sell_high = move_high - dist * ote_min
        ote_sell_low = move_high - dist * ote_max

        price = float(close[i])

        if displacement == "bullish":
            in_ote = ote_buy_low <= price <= ote_buy_high
            conf = sum([fvg_dir=="bullish", ob_dir=="bullish", in_ote])
            if conf >= 2:
                sig.iloc[i] = 1.0
        elif displacement == "bearish":
            in_ote = ote_sell_low <= price <= ote_sell_high
            conf = sum([fvg_dir=="bearish", ob_dir=="bearish", in_ote])
            if conf >= 2:
                sig.iloc[i] = -1.0

    return sig

# --- 3h. Wyckoff ---
def wyckoff_signals(df, lookback=50, vol_mult=2.0):
    close = df['close'].values
    high = df['high'].values
    low = df['low'].values
    vol = df['volume'].values
    atr = compute_atr(df['high'], df['low'], df['close']).values
    n = len(df)
    sig = pd.Series(0.0, index=df.index)

    for i in range(60, n):
        window_close = close[max(0,i-lookback):i+1]
        window_high = high[max(0,i-lookback):i+1]
        window_low = low[max(0,i-lookback):i+1]
        window_vol = vol[max(0,i-lookback):i+1]
        window_atr = atr[max(0,i-lookback):i+1]
        w_n = len(window_close)

        # -- accumulation --
        trend = window_close[-1] - window_close[0]
        if trend < 0:
            avg_vol = np.mean(window_vol)
            vol_surges = np.where(window_vol > avg_vol * vol_mult)[0]
            if len(vol_surges) >= 2:
                # SC: biggest vol surge in last 30 bars
                recent = vol_surges[vol_surges >= w_n - min(30, w_n)]
                if len(recent) > 0:
                    sc_idx = recent[np.argmax(window_vol[recent])]
                    sc_low = window_low[sc_idx]
                    # AR check
                    if sc_idx + 5 < w_n:
                        ar_rising = window_close[sc_idx+1] > window_close[sc_idx]
                        ar_vol = np.mean(window_vol[sc_idx+1:sc_idx+6])
                        if ar_rising and ar_vol < avg_vol * 1.5:
                            # ST check
                            st_idx = min(sc_idx + 10, w_n - 1)
                            near_sc = abs(window_low[st_idx] - sc_low) / sc_low < 0.02
                            lower_vol = window_vol[st_idx] < window_vol[sc_idx] * 0.7
                            if near_sc and lower_vol:
                                # Spring check
                                spring = False
                                for k in range(st_idx+1, w_n):
                                    if window_low[k] < sc_low - window_atr[k] * 0.5:
                                        spring = True
                                        break
                                sig.iloc[i] = 1.0 * (0.7 if spring else 0.5)
                                continue

        # -- distribution --
        if trend > 0:
            avg_vol = np.mean(window_vol)
            vol_surges = np.where(window_vol > avg_vol * vol_mult)[0]
            if len(vol_surges) >= 2:
                recent = vol_surges[vol_surges >= w_n - min(30, w_n)]
                if len(recent) > 0:
                    lc_idx = recent[np.argmax(window_vol[recent])]
                    lc_high = window_high[lc_idx]
                    if lc_idx + 5 < w_n:
                        ad_down = window_close[lc_idx+1] < window_close[lc_idx]
                        if ad_down:
                            st_idx = min(lc_idx + 8, w_n - 1)
                            near_lc = abs(window_high[st_idx] - lc_high) / lc_high < 0.02
                            lower_vol = window_vol[st_idx] < window_vol[lc_idx] * 0.7
                            if near_lc and lower_vol:
                                # UT check
                                ut = False
                                for k in range(st_idx+1, w_n):
                                    if window_high[k] > lc_high + window_atr[k] * 0.5:
                                        ut = True
                                        break
                                sig.iloc[i] = -1.0 * (0.7 if ut else 0.5)

    return sig

# --- 3i. Supply/Demand ---
def supply_demand_signals(df, zone_lookback=5, zone_pct=0.003, min_strength=2):
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values
    vol = df['volume'].values if 'volume' in df.columns else np.ones(len(df))
    n = len(df)
    sig = pd.Series(0.0, index=df.index)

    for i in range(20, n):
        buy_signal = False
        sell_signal = False

        # Demand zones (bounce)
        for j in range(zone_lookback, i):
            base_high = np.max(high[j-zone_lookback:j])
            base_low = np.min(low[j-zone_lookback:j])
            base_range = base_high - base_low
            base_body = abs(close[j] - close[j-zone_lookback])
            if base_range > 0 and base_body < base_range * 0.3:
                continue
            rally = close[j+1] - close[j] if j+1 < n else 0
            if rally / close[j] > 0.01 and base_range > 0:
                zone_top = base_high
                if abs(close[i] - zone_top) / close[i] <= zone_pct:
                    # Count touches
                    touches = 0
                    for k in range(j+1, i+1):
                        if low[k] <= zone_top:
                            touches += 1
                    if touches >= min_strength:
                        buy_signal = True
                        break

        # Supply zones
        for j in range(zone_lookback, i):
            base_high = np.max(high[j-zone_lookback:j])
            base_low = np.min(low[j-zone_lookback:j])
            base_range = base_high - base_low
            base_body = abs(close[j] - close[j-zone_lookback])
            if base_range > 0 and base_body < base_range * 0.3:
                continue
            drop = close[j] - close[j+1] if j+1 < n else 0
            if drop / close[j] > 0.01 and base_range > 0:
                zone_bot = base_low
                if abs(close[i] - zone_bot) / close[i] <= zone_pct:
                    touches = 0
                    for k in range(j+1, i+1):
                        if high[k] >= zone_bot:
                            touches += 1
                    if touches >= min_strength:
                        sell_signal = True
                        break

        if buy_signal:
            sig.iloc[i] = 1.0
        elif sell_signal:
            sig.iloc[i] = -1.0

    return sig

# --- 3j. Support/Resistance ---
def support_resistance_signals(df, pivot_window=5, zone_pct=0.005, min_touches=2, breakout_pct=0.003):
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values
    n = len(df)
    sig = pd.Series(0.0, index=df.index)

    for i in range(20, n):
        chunk_high = high[:i+1]
        chunk_low = low[:i+1]
        chunk_close = close[:i+1]

        # Swing points
        swing_highs = []
        swing_lows = []
        for j in range(pivot_window, i - pivot_window + 1):
            if chunk_high[j] == np.max(chunk_high[j-pivot_window:j+pivot_window+1]):
                swing_highs.append(chunk_high[j])
            if chunk_low[j] == np.min(chunk_low[j-pivot_window:j+pivot_window+1]):
                swing_lows.append(chunk_low[j])

        # Cluster resistance
        resistance_zones = []
        if swing_highs:
            sh = sorted(swing_highs)
            cluster = [sh[0]]
            for lvl in sh[1:]:
                if abs(lvl - np.mean(cluster)) / np.mean(cluster) <= zone_pct:
                    cluster.append(lvl)
                else:
                    avg_p = np.mean(cluster)
                    touches = sum(1 for p in chunk_close if abs(p-avg_p)/avg_p <= zone_pct*0.5)
                    if touches >= min_touches:
                        resistance_zones.append({'price': avg_p, 'touches': touches})
                    cluster = [lvl]
            if cluster:
                avg_p = np.mean(cluster)
                touches = sum(1 for p in chunk_close if abs(p-avg_p)/avg_p <= zone_pct*0.5)
                if touches >= min_touches:
                    resistance_zones.append({'price': avg_p, 'touches': touches})

        # Cluster support
        support_zones = []
        if swing_lows:
            sl = sorted(swing_lows)
            cluster = [sl[0]]
            for lvl in sl[1:]:
                if abs(lvl - np.mean(cluster)) / np.mean(cluster) <= zone_pct:
                    cluster.append(lvl)
                else:
                    avg_p = np.mean(cluster)
                    touches = sum(1 for p in chunk_close if abs(p-avg_p)/avg_p <= zone_pct*0.5)
                    if touches >= min_touches:
                        support_zones.append({'price': avg_p, 'touches': touches})
                    cluster = [lvl]
            if cluster:
                avg_p = np.mean(cluster)
                touches = sum(1 for p in chunk_close if abs(p-avg_p)/avg_p <= zone_pct*0.5)
                if touches >= min_touches:
                    support_zones.append({'price': avg_p, 'touches': touches})

        price = float(close[i])

        # Breakout above resistance
        for rz in resistance_zones:
            dist = (rz['price'] - price) / price
            if -breakout_pct <= dist <= breakout_pct:
                sig.iloc[i] = 1.0
                break
        if sig.iloc[i] != 0:
            continue

        # Bounce off support
        for sz in support_zones:
            dist = (price - sz['price']) / price
            if -breakout_pct <= dist <= breakout_pct and dist >= 0:
                sig.iloc[i] = 1.0
                break
        if sig.iloc[i] != 0:
            continue

        # Breakdown below support
        for sz in support_zones:
            dist = (price - sz['price']) / sz['price']
            if -breakout_pct <= dist <= breakout_pct and dist < 0:
                sig.iloc[i] = -1.0
                break

    return sig

# --- 3k. Pairs Trading (needs 2 symbols) ---
def pairs_trading_signals(df_a, df_b, lookback=60, entry_z=2.0, hedge_lookback=252):
    """df_a is primary, df_b is the pair. Returns signal series aligned to df_a."""
    close_a = df_a['close']
    close_b = df_b['close']
    # Align
    common = close_a.index.intersection(close_b.index)
    close_a = close_a.loc[common]
    close_b = close_b.loc[common]
    n = len(close_a)
    sig = pd.Series(0.0, index=close_a.index)

    for i in range(hedge_lookback + lookback, n):
        # Hedge ratio via OLS on trailing hedge_lookback
        a_train = close_a.iloc[i-hedge_lookback:i].values
        b_train = close_b.iloc[i-hedge_lookback:i].values
        x_ = np.column_stack([np.ones(len(a_train)), a_train])
        try:
            beta = np.linalg.lstsq(x_, b_train, rcond=None)[0]
        except np.linalg.LinAlgError:
            continue
        hedge = beta[1]

        # Spread z-score on trailing lookback
        spread = close_b.iloc[i-lookback:i] - hedge * close_a.iloc[i-lookback:i]
        sm = spread.mean()
        ss = spread.std(ddof=1)
        if ss < 1e-10:
            continue
        z = (spread - sm) / ss
        cur_z = float(z.iloc[-1])
        prev_z = float(z.iloc[-2]) if len(z) > 1 else 0.0

        if cur_z < -entry_z and prev_z >= -entry_z:
            sig.iloc[i] = 1.0   # long spread
        elif cur_z > entry_z and prev_z <= entry_z:
            sig.iloc[i] = -1.0  # short spread
        elif abs(cur_z) < 0.5:
            sig.iloc[i] = 0.0

    return sig

# --- 3l. Statistical Arbitrage (needs multi-asset universe) ---
def stat_arb_signals(df_dict, primary, lookback=60, n_factors=3, entry_threshold=2.0, return_lookback=20):
    """df_dict: {symbol: DataFrame}. Returns signal series for primary symbol."""
    # Align all to common dates
    close_frames = []
    symbols = []
    for sym, d in df_dict.items():
        close_frames.append(d['close'].rename(sym))
        symbols.append(sym)
    close_all = pd.concat(close_frames, axis=1).dropna()
    n = len(close_all)
    sig = pd.Series(0.0, index=close_all.index)

    for i in range(max(lookback, return_lookback) + 50, n):
        window = close_all.iloc[i-lookback:i]
        returns = window.pct_change(return_lookback).dropna()
        if len(returns) < lookback // 2:
            continue

        vals = returns.values
        n_comp = min(n_factors, vals.shape[1]-1)
        if n_comp < 1:
            continue

        centered = vals - vals.mean(axis=0)
        _U, _S, Vt = np.linalg.svd(centered, full_matrices=False)
        loadings = Vt[:n_comp].T
        factors = centered @ loadings
        predicted = factors @ loadings.T
        residuals = centered - predicted

        rz = (residuals[-1] - residuals.mean(axis=0)) / (residuals.std(axis=0, ddof=1) + 1e-10)
        if primary not in symbols:
            continue
        idx = symbols.index(primary)
        current_z = float(rz[idx])
        if np.isnan(current_z):
            continue

        if current_z > entry_threshold:
            sig.iloc[i] = -1.0  # short (overpriced)
        elif current_z < -entry_threshold:
            sig.iloc[i] = 1.0   # long (underpriced)
        elif abs(current_z) < 0.5:
            sig.iloc[i] = 0.0

    return sig

# --- 3m. COT (simplified — price-based proxy) ---
def cot_signals(df):
    """COT proxy: extreme price levels as contrarian signals (no real COT data)."""
    close = df['close']
    rsi = compute_rsi(close, 14)
    sig = pd.Series(0.0, index=df.index)
    sig[rsi < 20] = 1.0    # oversold → buy
    sig[rsi > 80] = -1.0   # overbought → sell
    return sig

# --- 3n. Fundamental (simplified — trend + vol proxy) ---
def fundamental_signals(df):
    """Fundamental proxy: vol-adjusted momentum (no real economic calendar)."""
    close = df['close']
    returns = close.pct_change()
    sig = pd.Series(0.0, index=df.index)

    for i in range(20, len(df)):
        r = returns.iloc[i-19:i+1]
        avg_ret = r.mean()
        vol = r.std()
        if vol < 1e-10:
            continue
        sharpe = avg_ret / vol * np.sqrt(252)
        if sharpe > 0.5:
            sig.iloc[i] = 1.0
        elif sharpe < -0.5:
            sig.iloc[i] = -1.0

    return sig


# ============================================================
# 4. BACKTEST ENGINE
# ============================================================

def backtest(signal_series, close, initial_capital=100000, commission_pct=0.001):
    """Simple backtest: trade on signal changes, long/short/flat."""
    position = 0.0
    entry_price = 0.0
    trade_returns = []
    equity_curve = [initial_capital]

    for i in range(1, len(signal_series)):
        sig = signal_series.iloc[i]
        price = float(close.iloc[i])
        prev_price = float(close.iloc[i-1])

        # Determine target position
        if sig > 0.5:
            target = 1.0
        elif sig < -0.5:
            target = -1.0
        else:
            target = 0.0

        # If position changes
        if target != position:
            # Close old position
            if position != 0:
                ret = position * (price / entry_price - 1) - commission_pct
                trade_returns.append(ret)

            # Open new position
            if target != 0:
                entry_price = price

            position = target

        # Daily PnL
        if position != 0:
            daily_ret = position * (price / prev_price - 1)
            equity = equity_curve[-1] * (1 + daily_ret)
        else:
            equity = equity_curve[-1]

        equity_curve.append(equity)

    # Close final position
    if position != 0:
        ret = position * (float(close.iloc[-1]) / entry_price - 1) - commission_pct
        trade_returns.append(ret)

    equity_curve = np.array(equity_curve)
    total_return = (equity_curve[-1] / initial_capital - 1) * 100

    # Win rate
    if len(trade_returns) > 0:
        wins = sum(1 for r in trade_returns if r > 0)
        win_rate = wins / len(trade_returns) * 100
    else:
        win_rate = 0.0

    # Sharpe ratio
    daily_returns = np.diff(equity_curve) / equity_curve[:-1]
    if len(daily_returns) > 1:
        sharpe = np.mean(daily_returns) / (np.std(daily_returns) + 1e-10) * np.sqrt(252)
    else:
        sharpe = 0.0

    # Max drawdown
    peak = np.maximum.accumulate(equity_curve)
    dd = (equity_curve - peak) / peak
    max_dd = np.min(dd) * 100

    # Profit factor
    if len(trade_returns) > 0:
        gross_profit = sum(r for r in trade_returns if r > 0)
        gross_loss = abs(sum(r for r in trade_returns if r < 0))
        profit_factor = gross_profit / (gross_loss + 1e-10)
    else:
        profit_factor = 0.0

    # R:R ratio (avg win / avg loss)
    if len(trade_returns) > 0:
        avg_win = np.mean([r for r in trade_returns if r > 0]) if any(r > 0 for r in trade_returns) else 0
        avg_loss = abs(np.mean([r for r in trade_returns if r < 0])) if any(r < 0 for r in trade_returns) else 0
        rr_ratio = avg_win / (avg_loss + 1e-10)
    else:
        rr_ratio = 0.0

    return {
        'total_return_pct': round(total_return, 2),
        'win_rate_pct': round(win_rate, 1),
        'sharpe': round(sharpe, 3),
        'max_drawdown_pct': round(max_dd, 2),
        'profit_factor': round(profit_factor, 2),
        'rr_ratio': round(rr_ratio, 2),
        'num_trades': len(trade_returns),
    }


# ============================================================
# 5. MAIN
# ============================================================

def run_all():
    symbols = ['BTC-USD', 'EURUSD=X']
    results = {}

    for symbol in symbols:
        print(f"\n=== Loading {symbol} ===")
        df = load_data(symbol)
        # Use Yahoo Finance 2y of daily data
        close = df['close']

        print(f"  Bars: {len(df)}, Period: {df.index[0].date()} -> {df.index[-1].date()}")

        # Additional data for multi-asset strategies
        if symbol == 'BTC-USD':
            print("  Loading ETH-USD for pairs/statarb...")
            df_pair = load_data('ETH-USD')
            df_sol = load_data('SOL-USD')
            # For statarb, use BTC, ETH, SOL as universe
            statarb_dict = {'BTC-USD': df, 'ETH-USD': df_pair, 'SOL-USD': df_sol}
            pairs_sig = pairs_trading_signals(df, df_pair)
            statarb_sig = stat_arb_signals(statarb_dict, 'BTC-USD')
        else:
            print("  Loading GBPUSD=X for pairs/statarb...")
            df_pair = load_data('GBPUSD=X')
            df_jpy = load_data('USDJPY=X')
            statarb_dict = {'EURUSD=X': df, 'GBPUSD=X': df_pair, 'USDJPY=X': df_jpy}
            pairs_sig = pairs_trading_signals(df, df_pair)
            statarb_sig = stat_arb_signals(statarb_dict, 'EURUSD=X')

        # Compute all strategy signals
        strategies = {
            'Mean Reversion': mean_reversion_signals(df),
            'Momentum': momentum_signals(df),
            'Vol Arb': vol_arb_signals(df),
            'Market Making': market_making_signals(df),
            'Regime-Based': regime_based_signals(df),
            'SMC': smc_signals(df),
            'ICT': ict_signals(df),
            'Wyckoff': wyckoff_signals(df),
            'Supply/Demand': supply_demand_signals(df),
            'S/R': support_resistance_signals(df),
        }

        # Strategies needing extra data
        strategies['Pairs Trading'] = pairs_sig
        strategies['Stat Arb'] = statarb_sig

        # COT & Fundamental (simplified price-based proxies)
        strategies['COT'] = cot_signals(df)
        strategies['Fundamental'] = fundamental_signals(df)

        # Backtest each
        sym_results = {}
        for name, sig in strategies.items():
            # Align signal to df index (pairs/statarb may have different index)
            sig = sig.reindex(df.index).fillna(0.0)
            if sig.abs().sum() == 0:
                print(f"  {name}: no signals generated")
                sym_results[name] = {k: 'N/A' for k in ['total_return_pct','win_rate_pct','sharpe','max_drawdown_pct','profit_factor','rr_ratio','num_trades']}
                sym_results[name]['num_trades'] = 0
                continue

            bt = backtest(sig, close)
            sym_results[name] = bt
            print(f"  {name:20s}  R={bt['total_return_pct']:>7.2f}%  WR={bt['win_rate_pct']:>5.1f}%  SR={bt['sharpe']:>6.3f}  DD={bt['max_drawdown_pct']:>6.2f}%  PF={bt['profit_factor']:>5.2f}  RR={bt['rr_ratio']:>5.2f}  N={bt['num_trades']}")

        results[symbol] = sym_results

    # Generate markdown table
    md = "# QNAI Strategy Backtest Results\n\n"
    md += f"Run date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    md += "Data: 2 years of daily OHLCV via Yahoo Finance\n"
    md += "Commission: 0.1% per trade, Initial capital: $100,000\n\n"

    for symbol in symbols:
        md += f"## {symbol}\n\n"
        md += "| Strategy | Return% | Win Rate% | Sharpe | Max DD% | Profit Factor | R:R | Trades |\n"
        md += "|----------|---------|-----------|--------|---------|--------------|-----|--------|\n"

        for name, bt in results[symbol].items():
            if isinstance(bt['total_return_pct'], str):
                md += f"| {name} | {bt['total_return_pct']} | {bt['win_rate_pct']} | {bt['sharpe']} | {bt['max_drawdown_pct']} | {bt['profit_factor']} | {bt['rr_ratio']} | {bt['num_trades']} |\n"
            else:
                md += f"| {name} | {bt['total_return_pct']:+.2f}% | {bt['win_rate_pct']:.1f}% | {bt['sharpe']:.3f} | {bt['max_drawdown_pct']:.2f}% | {bt['profit_factor']:.2f} | {bt['rr_ratio']:.2f} | {bt['num_trades']} |\n"

        md += "\n"

    with open('backtest_results.md', 'w') as f:
        f.write(md)

    print(f"\nResults written to backtest_results.md")
    return results


if __name__ == '__main__':
    run_all()
