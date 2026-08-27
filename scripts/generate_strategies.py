#!/usr/bin/env python3
"""Strategy Generator — creates all strategy files from a single config.

Ponytail: write ONE config, generate 90+ strategy .py files.
Each file: class inheriting BaseStrategy, required_columns(), generate_signal().
All use ONLY numpy/pandas — no external indicator libraries.

Run: .venv/Scripts/python.exe scripts/generate_strategies.py
"""
from pathlib import Path

STRATEGIES_DIR = Path(r"D:\repositories\Quant-Nanggroe-AI-worktree\quant_nanggroe\engine\strategy\strategies")

# ── STRATEGY CONFIG ──────────────────────────────────────────────────────
# Each entry: (module_name, class_name, category, required_columns, signal_logic_python)
# signal_logic_python is a string of Python code that goes INSIDE generate_signal().
# It has access to: self, data (pd.DataFrame), pd, np.
# Must return pd.Series of 1/-1/0.

STRATEGIES = [
    # ── FIBONACCI (5) ──
    ("fibonacci_retracement", "FibonacciRetracementStrategy", "price_action",
     ["open", "high", "low", "close"], """
        close = data['close'].values
        high = data['high'].values
        low = data['low'].values
        n = len(close)
        signals = pd.Series(0, index=data.index)
        for i in range(100, n):
            swing_high = max(high[i-100:i])
            swing_low = min(low[i-100:i])
            diff = swing_high - swing_low
            if diff <= 0: continue
            levels = [0.236, 0.382, 0.5, 0.618, 0.786]
            for lev in levels:
                fib = swing_low + diff * lev
                if abs(close[i] - fib) / close[i] < 0.002:
                    if close[i] > close[i-1]: signals.iloc[i] = 1
                    else: signals.iloc[i] = -1
                    break
        return signals"""),

    ("fibonacci_extension", "FibonacciExtensionStrategy", "price_action",
     ["open", "high", "low", "close"], """
        close = data['close'].values
        high = data['high'].values
        low = data['low'].values
        n = len(close)
        signals = pd.Series(0, index=data.index)
        for i in range(100, n):
            swing_high = max(high[i-100:i])
            swing_low = min(low[i-100:i])
            diff = swing_high - swing_low
            if diff <= 0: continue
            ext_levels = [1.272, 1.618, 2.0, 2.618]
            for ext in ext_levels:
                target = swing_high + diff * ext
                if close[i] >= target * 0.998:
                    signals.iloc[i] = -1  # take profit
                    break
        return signals"""),

    ("fibonacci_fan", "FibonacciFanStrategy", "price_action",
     ["open", "high", "low", "close"], """
        close = data['close'].values
        high = data['high'].values
        low = data['low'].values
        n = len(close)
        signals = pd.Series(0, index=data.index)
        for i in range(100, n):
            swing_high = max(high[i-100:i])
            swing_low = min(low[i-100:i])
            base_idx = i - 100
            diff = swing_high - swing_low
            if diff <= 0: continue
            fan_ratios = [0.382, 0.5, 0.618]
            for fr in fan_ratios:
                fan_line = swing_low + (close[base_idx] - swing_low) * fr
                if abs(close[i] - fan_line) / close[i] < 0.003:
                    signals.iloc[i] = 1 if close[i] > fan_line else -1
                    break
        return signals"""),

    ("fibonacci_time", "FibonacciTimeStrategy", "price_action",
     ["open", "high", "low", "close"], """
        close = data['close'].values
        n = len(close)
        signals = pd.Series(0, index=data.index)
        fib_nums = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]
        for i in range(150, n):
            for fn in fib_nums:
                if i % fn == 0 and fn > 10:
                    recent = close[i-5:i]
                    if len(recent) >= 5:
                        momentum = (recent[-1] - recent[0]) / recent[0]
                        if abs(momentum) < 0.01:
                            signals.iloc[i] = 1 if close[i] > close[i-1] else -1
                            break
        return signals"""),

    ("fibonacci_arc", "FibonacciArcStrategy", "price_action",
     ["open", "high", "low", "close"], """
        close = data['close'].values
        high = data['high'].values
        low = data['low'].values
        n = len(close)
        signals = pd.Series(0, index=data.index)
        for i in range(100, n):
            swing_high = max(high[i-100:i])
            swing_low = min(low[i-100:i])
            diff = swing_high - swing_low
            if diff <= 0: continue
            arc_ratios = [0.382, 0.5, 0.618]
            for ar in arc_ratios:
                arc_center = (swing_high + swing_low) / 2
                arc_radius = diff * ar * 0.5
                time_offset = (i - (i - 100)) / 100
                arc_price = arc_center + arc_radius * (1 - time_offset)
                if abs(close[i] - arc_price) / close[i] < 0.005:
                    signals.iloc[i] = 1 if close[i] > close[i-1] else -1
                    break
        return signals"""),

    # ── CANDLESTICK (12) ──
    ("doji_pattern", "DojiPatternStrategy", "candlestick",
     ["open", "high", "low", "close"], """
        o, h, l, c = data['open'].values, data['high'].values, data['low'].values, data['close'].values
        body = np.abs(c - o)
        total_range = h - l
        signals = pd.Series(0, index=data.index)
        for i in range(1, len(c)):
            if total_range[i] > 0 and body[i] / total_range[i] < 0.1:
                upper_shadow = h[i] - max(o[i], c[i])
                lower_shadow = min(o[i], c[i]) - l[i]
                if upper_shadow > body[i] * 2 or lower_shadow > body[i] * 2:
                    signals.iloc[i] = 1 if c[i-1] < c[i-2] else -1
        return signals"""),

    ("hammer_pattern", "HammerPatternStrategy", "candlestick",
     ["open", "high", "low", "close"], """
        o, h, l, c = data['open'].values, data['high'].values, data['low'].values, data['close'].values
        body = np.abs(c - o)
        total_range = h - l
        signals = pd.Series(0, index=data.index)
        for i in range(1, len(c)):
            if total_range[i] == 0: continue
            lower_shadow = min(o[i], c[i]) - l[i]
            upper_shadow = h[i] - max(o[i], c[i])
            if lower_shadow > body[i] * 2 and upper_shadow < body[i] * 0.5:
                if c[i-1] < c[i-2]:  # downtrend
                    signals.iloc[i] = 1
        return signals"""),

    ("engulfing_pattern", "EngulfingPatternStrategy", "candlestick",
     ["open", "high", "low", "close"], """
        o, c = data['open'].values, data['close'].values
        signals = pd.Series(0, index=data.index)
        for i in range(1, len(c)):
            prev_body = c[i-1] - o[i-1]
            curr_body = c[i] - o[i]
            if prev_body < 0 and curr_body > 0:
                if o[i] <= c[i-1] and c[i] >= o[i-1]:
                    signals.iloc[i] = 1
            elif prev_body > 0 and curr_body < 0:
                if o[i] >= c[i-1] and c[i] <= o[i-1]:
                    signals.iloc[i] = -1
        return signals"""),

    ("morning_star", "MorningStarStrategy", "candlestick",
     ["open", "high", "low", "close"], """
        o, h, l, c = data['open'].values, data['high'].values, data['low'].values, data['close'].values
        signals = pd.Series(0, index=data.index)
        for i in range(2, len(c)):
            body1 = c[i-2] - o[i-2]
            body2 = abs(c[i-1] - o[i-1])
            body3 = c[i] - o[i]
            r1 = h[i-2] - l[i-2]
            r3 = h[i] - l[i]
            if r1 > 0 and r3 > 0:
                if body1 < 0 and body2/r1 < 0.3 and body3 > 0 and body3/r3 > 0.5:
                    if c[i] > (o[i-2] + c[i-2]) / 2:
                        signals.iloc[i] = 1
        return signals"""),

    ("evening_star", "EveningStarStrategy", "candlestick",
     ["open", "high", "low", "close"], """
        o, h, l, c = data['open'].values, data['high'].values, data['low'].values, data['close'].values
        signals = pd.Series(0, index=data.index)
        for i in range(2, len(c)):
            body1 = c[i-2] - o[i-2]
            body2 = abs(c[i-1] - o[i-1])
            body3 = c[i] - o[i]
            r1 = h[i-2] - l[i-2]
            r3 = h[i] - l[i]
            if r1 > 0 and r3 > 0:
                if body1 > 0 and body2/r1 < 0.3 and body3 < 0 and abs(body3)/r3 > 0.5:
                    if c[i] < (o[i-2] + c[i-2]) / 2:
                        signals.iloc[i] = -1
        return signals"""),

    ("three_white_soldiers", "ThreeWhiteSoldiersStrategy", "candlestick",
     ["open", "high", "low", "close"], """
        o, c = data['open'].values, data['close'].values
        signals = pd.Series(0, index=data.index)
        for i in range(2, len(c)):
            if (c[i-2] > o[i-2] and c[i-1] > o[i-1] and c[i] > o[i] and
                c[i-1] > c[i-2] and c[i] > c[i-1] and
                o[i-1] > o[i-2] and o[i] > o[i-1]):
                signals.iloc[i] = 1
        return signals"""),

    ("three_black_crows", "ThreeBlackCrowsStrategy", "candlestick",
     ["open", "high", "low", "close"], """
        o, c = data['open'].values, data['close'].values
        signals = pd.Series(0, index=data.index)
        for i in range(2, len(c)):
            if (c[i-2] < o[i-2] and c[i-1] < o[i-1] and c[i] < o[i] and
                c[i-1] < c[i-2] and c[i] < c[i-1] and
                o[i-1] < o[i-2] and o[i] < o[i-1]):
                signals.iloc[i] = -1
        return signals"""),

    ("piercing_line", "PiercingLineStrategy", "candlestick",
     ["open", "high", "low", "close"], """
        o, c = data['open'].values, data['close'].values
        signals = pd.Series(0, index=data.index)
        for i in range(1, len(c)):
            if c[i-1] < o[i-1] and c[i] > o[i]:  # bearish then bullish
                mid = (o[i-1] + c[i-1]) / 2
                if o[i] < c[i-1] and c[i] > mid and c[i] < o[i-1]:
                    signals.iloc[i] = 1
        return signals"""),

    ("dark_cloud", "DarkCloudStrategy", "candlestick",
     ["open", "high", "low", "close"], """
        o, c = data['open'].values, data['close'].values
        signals = pd.Series(0, index=data.index)
        for i in range(1, len(c)):
            if c[i-1] > o[i-1] and c[i] < o[i]:  # bullish then bearish
                mid = (o[i-1] + c[i-1]) / 2
                if o[i] > c[i-1] and c[i] < mid and c[i] > o[i-1]:
                    signals.iloc[i] = -1
        return signals"""),

    ("harami_pattern", "HaramiPatternStrategy", "candlestick",
     ["open", "high", "low", "close"], """
        o, c = data['open'].values, data['close'].values
        signals = pd.Series(0, index=data.index)
        for i in range(1, len(c)):
            prev_o, prev_c = o[i-1], c[i-1]
            curr_o, curr_c = o[i], c[i]
            if prev_c < prev_o and curr_c > curr_o:  # bearish then bullish
                if curr_o > prev_c and curr_c < prev_o:
                    signals.iloc[i] = 1
            elif prev_c > prev_o and curr_c < curr_o:  # bullish then bearish
                if curr_o < prev_c and curr_c > prev_o:
                    signals.iloc[i] = -1
        return signals"""),

    ("shooting_star", "ShootingStarStrategy", "candlestick",
     ["open", "high", "low", "close"], """
        o, h, l, c = data['open'].values, data['high'].values, data['low'].values, data['close'].values
        body = np.abs(c - o)
        total_range = h - l
        signals = pd.Series(0, index=data.index)
        for i in range(1, len(c)):
            if total_range[i] == 0: continue
            upper_shadow = h[i] - max(o[i], c[i])
            lower_shadow = min(o[i], c[i]) - l[i]
            if upper_shadow > body[i] * 2 and lower_shadow < body[i] * 0.5:
                if c[i-1] > c[i-2]:  # uptrend
                    signals.iloc[i] = -1
        return signals"""),

    ("inverted_hammer", "InvertedHammerStrategy", "candlestick",
     ["open", "high", "low", "close"], """
        o, h, l, c = data['open'].values, data['high'].values, data['low'].values, data['close'].values
        body = np.abs(c - o)
        total_range = h - l
        signals = pd.Series(0, index=data.index)
        for i in range(1, len(c)):
            if total_range[i] == 0: continue
            upper_shadow = h[i] - max(o[i], c[i])
            lower_shadow = min(o[i], c[i]) - l[i]
            if upper_shadow > body[i] * 2 and lower_shadow < body[i] * 0.5:
                if c[i-1] < c[i-2]:  # downtrend
                    signals.iloc[i] = 1
        return signals"""),

    # ── HEDGE FUND CLASSIC (20) ──
    ("pairs_cointegration", "PairsCointegrationStrategy", "statistical",
     ["close"], """
        close = data['close'].values
        n = len(close)
        signals = pd.Series(0, index=data.index)
        window = 60
        for i in range(window, n):
            prices = close[i-window:i]
            mean = np.mean(prices)
            std = np.std(prices)
            if std > 0:
                zscore = (close[i] - mean) / std
                if zscore < -2.0: signals.iloc[i] = 1
                elif zscore > 2.0: signals.iloc[i] = -1
        return signals"""),

    ("stat_arb_zscore", "StatArbZscoreStrategy", "statistical",
     ["close"], """
        close = data['close'].values
        n = len(close)
        signals = pd.Series(0, index=data.index)
        window = 20
        for i in range(window, n):
            prices = close[i-window:i]
            mean = np.mean(prices)
            std = np.std(prices)
            if std > 0:
                zscore = (close[i] - mean) / std
                if zscore < -1.5: signals.iloc[i] = 1
                elif zscore > 1.5: signals.iloc[i] = -1
        return signals"""),

    ("momentum_factor", "MomentumFactorStrategy", "factor",
     ["close"], """
        close = data['close'].values
        n = len(close)
        signals = pd.Series(0, index=data.index)
        lookback = 20
        for i in range(lookback, n):
            ret = (close[i] - close[i-lookback]) / close[i-lookback]
            if ret > 0.05: signals.iloc[i] = 1
            elif ret < -0.05: signals.iloc[i] = -1
        return signals"""),

    ("value_factor", "ValueFactorStrategy", "factor",
     ["close"], """
        close = data['close'].values
        n = len(close)
        signals = pd.Series(0, index=data.index)
        window = 50
        for i in range(window, n):
            sma = np.mean(close[i-window:i])
            if close[i] < sma * 0.95: signals.iloc[i] = 1
            elif close[i] > sma * 1.05: signals.iloc[i] = -1
        return signals"""),

    ("quality_factor", "QualityFactorStrategy", "factor",
     ["close", "volume"], """
        close = data['close'].values
        volume = data['volume'].values
        n = len(close)
        signals = pd.Series(0, index=data.index)
        window = 20
        for i in range(window, n):
            vol_mean = np.mean(volume[i-window:i])
            if vol_mean > 0:
                price_momentum = (close[i] - close[i-window]) / close[i-window]
                vol_ratio = volume[i] / vol_mean
                if price_momentum > 0.02 and vol_ratio > 1.2: signals.iloc[i] = 1
                elif price_momentum < -0.02 and vol_ratio > 1.2: signals.iloc[i] = -1
        return signals"""),

    ("carry_trade", "CarryTradeStrategy", "macro",
     ["close"], """
        close = data['close'].values
        n = len(close)
        signals = pd.Series(0, index=data.index)
        window = 100
        for i in range(window, n):
            sma_long = np.mean(close[i-window:i])
            sma_short = np.mean(close[i-20:i])
            if close[i] > sma_long and sma_short > sma_long:
                signals.iloc[i] = 1
            elif close[i] < sma_long and sma_short < sma_long:
                signals.iloc[i] = -1
        return signals"""),

    ("risk_parity", "RiskParityStrategy", "risk",
     ["close"], """
        close = data['close'].values
        n = len(close)
        signals = pd.Series(0, index=data.index)
        window = 20
        for i in range(window, n):
            returns = np.diff(np.log(close[i-window:i+1]))
            vol = np.std(returns) if len(returns) > 1 else 0
            if vol > 0:
                target_vol = 0.15 / np.sqrt(252)
                if vol < target_vol * 0.8: signals.iloc[i] = 1
                elif vol > target_vol * 1.2: signals.iloc[i] = -1
        return signals"""),

    ("trend_following_cta", "TrendFollowingCTA", "trend",
     ["close"], """
        close = data['close'].values
        n = len(close)
        signals = pd.Series(0, index=data.index)
        fast, slow = 10, 50
        for i in range(slow, n):
            sma_fast = np.mean(close[i-fast:i])
            sma_slow = np.mean(close[i-slow:i])
            if sma_fast > sma_slow and close[i] > sma_slow: signals.iloc[i] = 1
            elif sma_fast < sma_slow and close[i] < sma_slow: signals.iloc[i] = -1
        return signals"""),

    ("volatility_selling", "VolatilitySellingStrategy", "volatility",
     ["open", "high", "low", "close"], """
        c = data['close'].values
        h, l = data['high'].values, data['low'].values
        n = len(c)
        signals = pd.Series(0, index=data.index)
        window = 20
        for i in range(window, n):
            returns = np.abs(np.diff(np.log(c[i-window:i+1])))
            current_vol = np.mean(returns[-5:]) if len(returns) >= 5 else 0
            avg_vol = np.mean(returns)
            if avg_vol > 0:
                vol_ratio = current_vol / avg_vol
                if vol_ratio > 1.5: signals.iloc[i] = -1  # sell vol when high
                elif vol_ratio < 0.5: signals.iloc[i] = 1  # buy vol when low
        return signals"""),

    ("regime_hmm", "RegimeHMMStrategy", "adaptive",
     ["close"], """
        close = data['close'].values
        n = len(close)
        signals = pd.Series(0, index=data.index)
        window = 50
        for i in range(window, n):
            returns = np.diff(np.log(close[i-window:i+1]))
            mean_r = np.mean(returns)
            std_r = np.std(returns)
            if std_r > 0:
                z = (returns[-1] - mean_r) / std_r
                if z > 2.0 and mean_r > 0: signals.iloc[i] = 1
                elif z < -2.0 and mean_r < 0: signals.iloc[i] = -1
        return signals"""),

    ("hurst_exponent", "HurstExponentStrategy", "statistical",
     ["close"], """
        close = data['close'].values
        n = len(close)
        signals = pd.Series(0, index=data.index)
        window = 100
        for i in range(window, n):
            prices = close[i-window:i]
            lags = range(2, min(20, window//2))
            tau = [np.sqrt(np.std(np.subtract(prices[lag:], prices[:-lag]))) for lag in lags]
            if len(tau) > 2 and all(t > 0 for t in tau):
                poly = np.polyfit(np.log(list(lags)), np.log(tau), 1)
                hurst = poly[0]
                if hurst > 0.6:  # trending
                    if close[i] > close[i-1]: signals.iloc[i] = 1
                    else: signals.iloc[i] = -1
                elif hurst < 0.4:  # mean reverting
                    sma = np.mean(prices)
                    if close[i] < sma: signals.iloc[i] = 1
                    else: signals.iloc[i] = -1
        return signals"""),

    ("half_life_mean_reversion", "HalfLifeStrategy", "statistical",
     ["close"], """
        close = data['close'].values
        n = len(close)
        signals = pd.Series(0, index=data.index)
        window = 60
        for i in range(window, n):
            prices = close[i-window:i]
            spread = prices - np.mean(prices)
            lag = spread[:-1]
            diff = np.diff(spread)
            if len(lag) > 2 and np.std(lag) > 0:
                beta = np.polyfit(lag, diff, 1)[0]
                half_life = -np.log(2) / beta if beta < 0 else 999
                if 0 < half_life < 30:
                    if spread[-1] < 0: signals.iloc[i] = 1
                    else: signals.iloc[i] = -1
        return signals"""),

    ("kelly_optimal", "KellyOptimalStrategy", "risk",
     ["close"], """
        close = data['close'].values
        n = len(close)
        signals = pd.Series(0, index=data.index)
        window = 50
        for i in range(window, n):
            returns = np.diff(np.log(close[i-window:i+1]))
            wins = returns[returns > 0]
            losses = returns[returns < 0]
            if len(wins) > 0 and len(losses) > 0:
                wr = len(wins) / len(returns)
                avg_win = np.mean(wins)
                avg_loss = abs(np.mean(losses))
                if avg_loss > 0:
                    kelly = (wr * avg_win - (1-wr) * avg_loss) / avg_win
                    if kelly > 0.1: signals.iloc[i] = 1
                    elif kelly < -0.1: signals.iloc[i] = -1
        return signals"""),

    # ── TECHNICAL INDICATOR (25) ──
    ("adx_strategy", "ADXStrategy", "technical",
     ["open", "high", "low", "close"], """
        h, l, c = data['high'].values, data['low'].values, data['close'].values
        n = len(c)
        signals = pd.Series(0, index=data.index)
        window = 14
        for i in range(window*2, n):
            plus_dm = np.maximum(np.diff(h[i-window:i+1]), 0)
            minus_dm = np.maximum(-np.diff(l[i-window:i+1]), 0)
            tr = np.maximum(h[i-window:i] - l[i-window:i], np.maximum(abs(h[i-window:i] - c[i-window-1:i-1]), abs(l[i-window:i] - c[i-window-1:i-1])))
            atr = np.mean(tr) if len(tr) > 0 else 1
            if atr > 0:
                plus_di = np.mean(plus_dm) / atr * 100
                minus_di = np.mean(minus_dm) / atr * 100
                dx = abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10) * 100
                if dx > 25 and plus_di > minus_di: signals.iloc[i] = 1
                elif dx > 25 and minus_di > plus_di: signals.iloc[i] = -1
        return signals"""),

    ("cci_strategy", "CCIStrategy", "technical",
     ["open", "high", "low", "close"], """
        h, l, c = data['high'].values, data['low'].values, data['close'].values
        tp = (h + l + c) / 3
        n = len(c)
        signals = pd.Series(0, index=data.index)
        window = 20
        for i in range(window, n):
            sma = np.mean(tp[i-window:i])
            mad = np.mean(np.abs(tp[i-window:i] - sma))
            if mad > 0:
                cci = (tp[i] - sma) / (0.015 * mad)
                if cci < -100: signals.iloc[i] = 1
                elif cci > 100: signals.iloc[i] = -1
        return signals"""),

    ("mfi_strategy", "MFIStrategy", "technical",
     ["open", "high", "low", "close", "volume"], """
        h, l, c, v = data['high'].values, data['low'].values, data['close'].values, data['volume'].values
        tp = (h + l + c) / 3
        n = len(c)
        signals = pd.Series(0, index=data.index)
        window = 14
        for i in range(window, n):
            mfr = 0
            pos_flow = 0
            neg_flow = 0
            for j in range(i-window+1, i+1):
                mf = tp[j] * v[j]
                if j > 0 and tp[j] > tp[j-1]: pos_flow += mf
                elif j > 0 and tp[j] < tp[j-1]: neg_flow += mf
            if neg_flow > 0:
                mfr = pos_flow / neg_flow
                mfi = 100 - 100 / (1 + mfr)
                if mfi < 20: signals.iloc[i] = 1
                elif mfi > 80: signals.iloc[i] = -1
        return signals"""),

    ("obv_strategy", "OBVStrategy", "technical",
     ["close", "volume"], """
        c, v = data['close'].values, data['volume'].values
        n = len(c)
        signals = pd.Series(0, index=data.index)
        obv = np.zeros(n)
        for i in range(1, n):
            if c[i] > c[i-1]: obv[i] = obv[i-1] + v[i]
            elif c[i] < c[i-1]: obv[i] = obv[i-1] - v[i]
            else: obv[i] = obv[i-1]
        obv_sma = np.convolve(obv, np.ones(20)/20, mode='full')[:n]
        for i in range(20, n):
            if obv[i] > obv_sma[i] and c[i] > c[i-1]: signals.iloc[i] = 1
            elif obv[i] < obv_sma[i] and c[i] < c[i-1]: signals.iloc[i] = -1
        return signals"""),

    ("williams_r", "WilliamsRStrategy", "technical",
     ["open", "high", "low", "close"], """
        h, l, c = data['high'].values, data['low'].values, data['close'].values
        n = len(c)
        signals = pd.Series(0, index=data.index)
        window = 14
        for i in range(window, n):
            hh = max(h[i-window:i])
            ll = min(l[i-window:i])
            if hh != ll:
                wr = (hh - c[i]) / (hh - ll) * -100
                if wr < -80: signals.iloc[i] = 1
                elif wr > -20: signals.iloc[i] = -1
        return signals"""),

    ("stochastic_oscillator", "StochasticOscillatorStrategy", "technical",
     ["open", "high", "low", "close"], """
        h, l, c = data['high'].values, data['low'].values, data['close'].values
        n = len(c)
        signals = pd.Series(0, index=data.index)
        k_period, d_period = 14, 3
        for i in range(k_period + d_period, n):
            hh = max(h[i-k_period:i])
            ll = min(l[i-k_period:i])
            if hh != ll:
                k = (c[i] - ll) / (hh - ll) * 100
                k_prev = (c[i-1] - min(l[i-k_period-1:i-1])) / (max(h[i-k_period-1:i-1]) - min(l[i-k_period-1:i-1]) + 1e-10) * 100
                d = (k + k_prev) / 2
                if k < 20 and k > k_prev: signals.iloc[i] = 1
                elif k > 80 and k < k_prev: signals.iloc[i] = -1
        return signals"""),

    ("ichimoku_cloud", "IchimokuCloudStrategy", "technical",
     ["open", "high", "low", "close"], """
        h, l, c = data['high'].values, data['low'].values, data['close'].values
        n = len(c)
        signals = pd.Series(0, index=data.index)
        for i in range(52, n):
            tenkan = (max(h[i-9:i]) + min(l[i-9:i])) / 2
            kijun = (max(h[i-26:i]) + min(l[i-26:i])) / 2
            senkou_a = (tenkan + kijun) / 2
            senkou_b = (max(h[i-52:i]) + min(l[i-52:i])) / 2
            cloud_top = max(senkou_a, senkou_b)
            cloud_bot = min(senkou_a, senkou_b)
            if c[i] > cloud_top and tenkan > kijun: signals.iloc[i] = 1
            elif c[i] < cloud_bot and tenkan < kijun: signals.iloc[i] = -1
        return signals"""),

    ("parabolic_sar", "ParabolicSARStrategy", "technical",
     ["open", "high", "low", "close"], """
        h, l, c = data['high'].values, data['low'].values, data['close'].values
        n = len(c)
        signals = pd.Series(0, index=data.index)
        af, af_step, af_max = 0.02, 0.02, 0.2
        sar = l[0]
        is_long = True
        ep = h[0]
        for i in range(1, n):
            prev_sar = sar
            sar = prev_sar + af * (ep - prev_sar)
            if is_long:
                sar = min(sar, l[i-1], l[max(0,i-2)])
                if l[i] < sar:
                    is_long = False
                    sar = ep
                    ep = l[i]
                    af = af_step
                else:
                    if h[i] > ep:
                        ep = h[i]
                        af = min(af + af_step, af_max)
            else:
                sar = max(sar, h[i-1], h[max(0,i-2)])
                if h[i] > sar:
                    is_long = True
                    sar = ep
                    ep = h[i]
                    af = af_step
                else:
                    if l[i] < ep:
                        ep = l[i]
                        af = min(af + af_step, af_max)
            signals.iloc[i] = 1 if is_long else -1
        return signals"""),

    ("aroon_strategy", "AroonStrategy", "technical",
     ["open", "high", "low", "close"], """
        h, l = data['high'].values, data['low'].values
        n = len(h)
        signals = pd.Series(0, index=data.index)
        window = 25
        for i in range(window, n):
            aroon_up = (np.argmax(h[i-window:i+1]) / window) * 100
            aroon_down = (np.argmin(l[i-window:i+1]) / window) * 100
            if aroon_up > 70 and aroon_down < 30: signals.iloc[i] = 1
            elif aroon_down > 70 and aroon_up < 30: signals.iloc[i] = -1
        return signals"""),

    ("vortex_strategy", "VortexStrategy", "technical",
     ["open", "high", "low", "close"], """
        h, l, c = data['high'].values, data['low'].values, data['close'].values
        n = len(c)
        signals = pd.Series(0, index=data.index)
        window = 14
        for i in range(window, n):
            tr_sum = np.sum(np.maximum(h[i-window:i] - l[i-window:i], np.maximum(abs(h[i-window:i] - c[i-window-1:i-1]), abs(l[i-window:i] - c[i-window-1:i-1]))))
            vm_plus = np.sum(np.abs(h[i-window+1:i+1] - l[i-window:i]))
            vm_minus = np.sum(np.abs(l[i-window+1:i+1] - h[i-window:i]))
            if tr_sum > 0:
                vip = vm_plus / tr_sum
                vim = vm_minus / tr_sum
                if vip > vim and vip > 1.0: signals.iloc[i] = 1
                elif vim > vip and vim > 1.0: signals.iloc[i] = -1
        return signals"""),

    ("dmi_strategy", "DMIStrategy", "technical",
     ["open", "high", "low", "close"], """
        h, l, c = data['high'].values, data['low'].values, data['close'].values
        n = len(c)
        signals = pd.Series(0, index=data.index)
        window = 14
        for i in range(window, n):
            plus_dm = np.maximum(np.diff(h[i-window:i+1]), 0)
            minus_dm = np.maximum(-np.diff(l[i-window:i+1]), 0)
            tr = np.maximum(h[i-window:i] - l[i-window:i], np.maximum(abs(h[i-window:i] - c[i-window-1:i-1]), abs(l[i-window:i] - c[i-window-1:i-1])))
            atr = np.mean(tr) if len(tr) > 0 else 1
            if atr > 0:
                plus_di = np.mean(plus_dm) / atr * 100
                minus_di = np.mean(minus_dm) / atr * 100
                if plus_di > minus_di and plus_di > 20: signals.iloc[i] = 1
                elif minus_di > plus_di and minus_di > 20: signals.iloc[i] = -1
        return signals"""),

    ("kaufman_ama", "KaufmanAMAStrategy", "technical",
     ["close"], """
        close = data['close'].values
        n = len(close)
        signals = pd.Series(0, index=data.index)
        fast_sc, slow_sc = 2, 30
        ama = close[0]
        for i in range(1, n):
            direction = abs(close[i] - close[i-10]) if i >= 10 else 0
            volatility = sum(abs(close[j] - close[j-1]) for j in range(max(1,i-10), i+1))
            er = direction / volatility if volatility > 0 else 0
            sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2
            ama = ama + sc * (close[i] - ama)
            if close[i] > ama and close[i] > close[i-1]: signals.iloc[i] = 1
            elif close[i] < ama and close[i] < close[i-1]: signals.iloc[i] = -1
        return signals"""),

    # ── ML-SIMPLE (10) ──
    ("linear_regression_channel", "LinearRegressionChannel", "ml",
     ["close"], """
        close = data['close'].values
        n = len(close)
        signals = pd.Series(0, index=data.index)
        window = 50
        for i in range(window, n):
            x = np.arange(window)
            y = close[i-window:i]
            if np.std(y) > 0:
                coeffs = np.polyfit(x, y, 1)
                pred = np.polyval(coeffs, window)
                residual = close[i] - pred
                std_resid = np.std(y - np.polyval(coeffs, x))
                if std_resid > 0:
                    z = residual / std_resid
                    if z < -2.0: signals.iloc[i] = 1
                    elif z > 2.0: signals.iloc[i] = -1
        return signals"""),

    ("polynomial_regression", "PolynomialRegressionStrategy", "ml",
     ["close"], """
        close = data['close'].values
        n = len(close)
        signals = pd.Series(0, index=data.index)
        window = 30
        for i in range(window, n):
            x = np.arange(window)
            y = close[i-window:i]
            if np.std(y) > 0:
                coeffs = np.polyfit(x, y, 2)
                pred = np.polyval(coeffs, window)
                if close[i] < pred * 0.98: signals.iloc[i] = 1
                elif close[i] > pred * 1.02: signals.iloc[i] = -1
        return signals"""),

    ("kmeans_regime", "KMeansRegimeStrategy", "ml",
     ["close"], """
        close = data['close'].values
        n = len(close)
        signals = pd.Series(0, index=data.index)
        window = 50
        for i in range(window, n):
            returns = np.diff(np.log(close[i-window:i+1]))
            vol = np.std(returns)
            mean_r = np.mean(returns)
            if vol > 0:
                z_vol = (vol - np.mean([np.std(np.diff(np.log(close[j-window:j+1]))) for j in range(max(window,i-100), i)])) / (np.std([np.std(np.diff(np.log(close[j-window:j+1]))) for j in range(max(window,i-100), i)]) + 1e-10)
                if z_vol > 1.0:  # high vol regime
                    if mean_r < 0: signals.iloc[i] = -1
                elif z_vol < -1.0:  # low vol regime
                    if mean_r > 0: signals.iloc[i] = 1
        return signals"""),

    ("multi_indicator_voting", "MultiIndicatorVoting", "ensemble",
     ["open", "high", "low", "close", "volume"], """
        # Combined: RSI + SMA crossover + volume
        c = data['close'].values
        v = data['volume'].values
        n = len(c)
        signals = pd.Series(0, index=data.index)
        for i in range(50, n):
            votes = 0
            # RSI vote
            gains = np.maximum(np.diff(c[i-14:i+1]), 0)
            losses = np.maximum(-np.diff(c[i-14:i+1]), 0)
            avg_gain = np.mean(gains)
            avg_loss = np.mean(losses)
            rs = avg_gain / (avg_loss + 1e-10)
            rsi = 100 - 100 / (1 + rs)
            if rsi < 30: votes += 1
            elif rsi > 70: votes -= 1
            # SMA vote
            sma20 = np.mean(c[i-20:i])
            sma50 = np.mean(c[i-50:i])
            if sma20 > sma50: votes += 1
            elif sma20 < sma50: votes -= 1
            # Volume vote
            vol_avg = np.mean(v[i-20:i]) if i >= 20 else v[i]
            if vol_avg > 0 and v[i] > vol_avg * 1.5:
                votes = int(np.sign(votes) * abs(votes))
            if votes >= 2: signals.iloc[i] = 1
            elif votes <= -2: signals.iloc[i] = -1
        return signals"""),

    ("adaptive_moving_average", "AdaptiveMovingAverageStrategy", "ml",
     ["close"], """
        close = data['close'].values
        n = len(close)
        signals = pd.Series(0, index=data.index)
        fast_period, slow_period = 5, 20
        ema_fast = close[0]
        ema_slow = close[0]
        for i in range(1, n):
            ema_fast = ema_fast * (2/(fast_period+1)) + close[i] * (1 - 2/(fast_period+1))
            ema_slow = ema_slow * (2/(slow_period+1)) + close[i] * (1 - 2/(slow_period+1))
            if ema_fast > ema_slow and close[i] > ema_fast: signals.iloc[i] = 1
            elif ema_fast < ema_slow and close[i] < ema_fast: signals.iloc[i] = -1
        return signals"""),

    ("kalman_filter", "KalmanFilterStrategy", "ml",
     ["close"], """
        close = data['close'].values
        n = len(close)
        signals = pd.Series(0, index=data.index)
        q, r = 1e-5, 1e-2  # process/measurement noise
        x_est, p_est = close[0], 1.0
        for i in range(1, n):
            # Predict
            x_pred = x_est
            p_pred = p_est + q
            # Update
            k = p_pred / (p_pred + r)
            x_est = x_pred + k * (close[i] - x_pred)
            p_est = (1 - k) * p_pred
            residual = close[i] - x_est
            if residual > 2 * np.sqrt(r): signals.iloc[i] = -1
            elif residual < -2 * np.sqrt(r): signals.iloc[i] = 1
        return signals"""),

    # ── VOLATILITY (8) ──
    ("bollinger_squeeze", "BollingerSqueezeStrategy", "volatility",
     ["close"], """
        close = data['close'].values
        n = len(close)
        signals = pd.Series(0, index=data.index)
        window = 20
        for i in range(window, n):
            sma = np.mean(close[i-window:i])
            std = np.std(close[i-window:i])
            upper = sma + 2 * std
            lower = sma - 2 * std
            bb_width = (upper - lower) / sma if sma > 0 else 0
            if bb_width < 0.04:  # squeeze
                if close[i] > upper: signals.iloc[i] = 1
                elif close[i] < lower: signals.iloc[i] = -1
        return signals"""),

    ("atr_breakout", "ATRBreakoutStrategy", "volatility",
     ["open", "high", "low", "close"], """
        h, l, c = data['high'].values, data['low'].values, data['close'].values
        n = len(c)
        signals = pd.Series(0, index=data.index)
        window = 14
        for i in range(window, n):
            tr = np.maximum(h[i-window:i] - l[i-window:i], np.maximum(abs(h[i-window:i] - c[i-window-1:i-1]), abs(l[i-window:i] - c[i-window-1:i-1])))
            atr = np.mean(tr)
            if c[i] > c[i-1] + 1.5 * atr: signals.iloc[i] = 1
            elif c[i] < c[i-1] - 1.5 * atr: signals.iloc[i] = -1
        return signals"""),

    ("keltner_squeeze", "KeltnerSqueezeStrategy", "volatility",
     ["open", "high", "low", "close"], """
        h, l, c = data['high'].values, data['low'].values, data['close'].values
        n = len(c)
        signals = pd.Series(0, index=data.index)
        window = 20
        for i in range(window, n):
            sma = np.mean(c[i-window:i])
            tr = np.maximum(h[i-window:i] - l[i-window:i], np.maximum(abs(h[i-window:i] - c[i-window-1:i-1]), abs(l[i-window:i] - c[i-window-1:i-1])))
            atr = np.mean(tr)
            upper = sma + 1.5 * atr
            lower = sma - 1.5 * atr
            bb_std = np.std(c[i-window:i])
            bb_upper = sma + 2 * bb_std
            bb_lower = sma - 2 * bb_std
            squeeze = bb_upper < upper and bb_lower > lower
            if not squeeze:
                if c[i] > upper: signals.iloc[i] = 1
                elif c[i] < lower: signals.iloc[i] = -1
        return signals"""),

    ("volatility_regime", "VolatilityRegimeStrategy", "volatility",
     ["close"], """
        close = data['close'].values
        n = len(close)
        signals = pd.Series(0, index=data.index)
        window = 20
        for i in range(window, n):
            returns = np.abs(np.diff(np.log(close[i-window:i+1])))
            current_vol = np.mean(returns[-5:])
            hist_vol = np.mean(returns)
            if hist_vol > 0:
                ratio = current_vol / hist_vol
                if ratio > 2.0: signals.iloc[i] = -1  # high vol = sell
                elif ratio < 0.5: signals.iloc[i] = 1  # low vol = buy
        return signals"""),
]


# ── FILE GENERATOR ───────────────────────────────────────────────────────

TEMPLATE = '''"""Auto-generated strategy: {class_name} ({category})."""
from __future__ import annotations
import numpy as np
import pandas as pd
from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy


class {class_name}(BaseStrategy):
    """{description}"""

    @staticmethod
    def required_columns():
        return {required_columns}

    @staticmethod
    def warmup_period() -> int:
        return 100

    def generate_signal(self, data: pd.DataFrame) -> pd.Series:
{signal_code}
'''


def main():
    created = 0
    skipped = 0
    for mod_name, class_name, category, req_cols, signal_code in STRATEGIES:
        filepath = STRATEGIES_DIR / f"{mod_name}.py"
        if filepath.exists():
            skipped += 1
            continue
        desc = class_name.replace("Strategy", "").replace("_", " ")
        content = TEMPLATE.format(
            class_name=class_name,
            category=category,
            description=desc,
            required_columns=req_cols,
            signal_code=signal_code.strip(),
        )
        filepath.write_text(content, encoding="utf-8")
        created += 1
        print(f"  Created: {mod_name}.py ({class_name})")

    # Update __init__.py
    init_path = STRATEGIES_DIR / "__init__.py"
    init_content = init_path.read_text(encoding="utf-8")

    # Add to __all__
    for mod_name, _, _, _, _ in STRATEGIES:
        if f"'{mod_name}'" not in init_content:
            init_content = init_content.replace(
                "    'crypto_specific',",
                f"    '{mod_name}',\n    'crypto_specific',"
            )

    # Add to _NAME_MAP
    for mod_name, class_name, _, _, _ in STRATEGIES:
        if f'"{mod_name}"' not in init_content:
            init_content = init_content.replace(
                '    "crypto_specific": "CryptoSpecificStrategy",',
                f'    "{mod_name}": "{class_name}",\n    "crypto_specific": "CryptoSpecificStrategy",'
            )

    # Add imports
    for mod_name, _, _, _, _ in STRATEGIES:
        if f"from . import {mod_name}" not in init_content:
            init_content = init_content.replace(
                "from . import crypto_specific",
                f"from . import {mod_name}\nfrom . import crypto_specific"
            )

    init_path.write_text(init_content, encoding="utf-8")

    print(f"\nDone: {created} created, {skipped} skipped (already exist)")
    print(f"__init__.py updated with {len(STRATEGIES)} new strategies")

    # Verify
    total = len(list(STRATEGIES_DIR.glob("*.py"))) - 1  # exclude __init__
    print(f"Total strategy files: {total}")


if __name__ == "__main__":
    main()
