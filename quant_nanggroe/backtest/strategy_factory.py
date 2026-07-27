"""
QNA Strategy Factory
====================
Generates 1000+ strategy variants from 15+ templates with parameter grids.
Every variant can be backtested and ranked by Sharpe ratio.

Usage:
  from strategy_factory import StrategyFactory
  factory = StrategyFactory()
  variants = factory.generate()  # Returns 1000+ StrategyVariant objects
"""

import math
from typing import Callable, Dict, List


class StrategyVariant:
    """A single strategy instance with specific parameters."""

    def __init__(self, template_name: str, params: Dict, signal_fn: Callable):
        self.template_name = template_name
        self.params = params
        self.signal_fn = signal_fn
        param_str = ",".join(f"{k}={v}" for k, v in sorted(params.items()))
        self.name = f"{template_name}[{param_str}]"
        self.id = hash(self.name) & 0xFFFFFFFF

    def generate_signals(self, candles: List[Dict]) -> List[int]:
        """Generate signal for each bar: 1=buy, -1=sell, 0=hold."""
        return self.signal_fn(candles, self.params)

    def __repr__(self):
        return f"<Strategy {self.name}>"


# =====================================================================
# INDICATOR LIBRARY — pure Python, no deps
# =====================================================================

def _sma(values, period):
    if len(values) < period:
        return [None] * len(values)
    result = [None] * (period - 1)
    running = sum(values[:period])
    result.append(running / period)
    for i in range(period, len(values)):
        running += values[i] - values[i - period]
        result.append(running / period)
    return result


def _ema(values, period):
    if len(values) < period:
        return [None] * len(values)
    multiplier = 2.0 / (period + 1)
    result = [None] * (period - 1)
    result.append(sum(values[:period]) / period)
    for i in range(period, len(values)):
        result.append((values[i] - result[-1]) * multiplier + result[-1])
    return result


def _rsi(values, period):
    if len(values) < period + 1:
        return [None] * len(values)
    result = [None] * period
    gains, losses = 0, 0
    for i in range(1, period + 1):
        diff = values[i] - values[i - 1]
        gains += max(diff, 0)
        losses += max(-diff, 0)
    avg_g = gains / period
    avg_l = losses / period
    rs = avg_g / avg_l if avg_l > 0 else 100
    result.append(100 - 100 / (1 + rs))
    for i in range(period + 1, len(values)):
        diff = values[i] - values[i - 1]
        avg_g = (avg_g * (period - 1) + max(diff, 0)) / period
        avg_l = (avg_l * (period - 1) + max(-diff, 0)) / period
        rs = avg_g / avg_l if avg_l > 0 else 100
        result.append(100 - 100 / (1 + rs))
    return result


def _std_dev(values, mean, period):
    if len(values) < period:
        return 0
    variance = sum((v - mean) ** 2 for v in values[-period:]) / period
    return math.sqrt(variance)


def _true_range(high, low, prev_close):
    return max(high - low, abs(high - prev_close) if prev_close else high - low,
               abs(low - prev_close) if prev_close else 0)


def _atr(candles, period):
    if len(candles) < period:
        return [None] * len(candles)
    trs = []
    for i in range(len(candles)):
        prev_close = candles[i - 1]["close"] if i > 0 else None
        tr = _true_range(candles[i]["high"], candles[i]["low"], prev_close)
        trs.append(tr)
    return _sma(trs, period) if len(trs) >= period else [None] * len(trs)


def _macd(values, fast, slow, signal):
    ema_fast = _ema(values, fast)
    ema_slow = _ema(values, slow)
    macd_line = [e_f - e_s if e_f is not None and e_s is not None else None
                 for e_f, e_s in zip(ema_fast, ema_slow)]
    signal_line = _ema([m for m in macd_line if m is not None], signal)
    idx = 0
    result = []
    for m in macd_line:
        if m is not None:
            s = signal_line[idx] if idx < len(signal_line) else None
            result.append((m, s, m - s if s is not None else None))
            idx += 1
        else:
            result.append((None, None, None))
    while len(result) < len(values):
        result.insert(0, (None, None, None))
    return result


# =====================================================================
# SIGNAL FUNCTIONS — each returns list[int] of signals
# =====================================================================

def _signal_sma_crossover(candles, params):
    closes = [c["close"] for c in candles]
    fast_sma = _sma(closes, params["fast"])
    slow_sma = _sma(closes, params["slow"])
    signals = [0] * len(candles)
    for i in range(1, len(candles)):
        f_prev = fast_sma[i - 1]
        s_prev = slow_sma[i - 1]
        f_curr = fast_sma[i]
        s_curr = slow_sma[i]
        if f_prev is not None and s_prev is not None:
            if f_prev <= s_prev and f_curr > s_curr:
                signals[i] = 1
            elif f_prev >= s_prev and f_curr < s_curr:
                signals[i] = -1
    return signals


def _signal_rsi(candles, params):
    closes = [c["close"] for c in candles]
    rsi_values = _rsi(closes, params["period"])
    signals = [0] * len(candles)
    for i in range(1, len(candles)):
        r_prev = rsi_values[i - 1]
        r_curr = rsi_values[i]
        if r_prev is not None and r_curr is not None:
            if r_prev <= params["oversold"] and r_curr > params["oversold"]:
                signals[i] = 1
            elif r_prev >= params["overbought"] and r_curr < params["overbought"]:
                signals[i] = -1
    return signals


def _signal_macd(candles, params):
    closes = [c["close"] for c in candles]
    macd_values = _macd(closes, params["fast"], params["slow"], params["signal"])
    signals = [0] * len(candles)
    for i in range(1, len(candles)):
        m_prev, _, h_prev = macd_values[i - 1]
        m_curr, _, h_curr = macd_values[i]
        if h_prev is not None and h_curr is not None:
            if h_prev <= 0 and h_curr > 0:
                signals[i] = 1
            elif h_prev >= 0 and h_curr < 0:
                signals[i] = -1
    return signals


def _signal_bollinger(candles, params):
    closes = [c["close"] for c in candles]
    period = params["period"]
    std_mult = params["std_dev"]
    signals = [0] * len(candles)
    for i in range(period - 1, len(candles)):
        window = closes[i - period + 1:i + 1]
        mean = sum(window) / period
        std = _std_dev(window, mean, period)
        upper = mean + std_mult * std
        lower = mean - std_mult * std
        if closes[i] < lower and closes[i - 1] >= lower:
            signals[i] = 1
        elif closes[i] > upper and closes[i - 1] <= upper:
            signals[i] = -1
    return signals


def _signal_momentum(candles, params):
    closes = [c["close"] for c in candles]
    lookback = params["lookback"]
    threshold = params["threshold"] / 100.0
    signals = [0] * len(candles)
    for i in range(lookback, len(candles)):
        ret = (closes[i] - closes[i - lookback]) / closes[i - lookback]
        if ret > threshold:
            signals[i] = 1
        elif ret < -threshold:
            signals[i] = -1
    return signals


def _signal_mean_reversion(candles, params):
    closes = [c["close"] for c in candles]
    period = params["period"]
    entry_z = params["entry_z"]
    signals = [0] * len(candles)
    for i in range(period, len(candles)):
        window = closes[i - period:i]
        mean = sum(window) / period
        std = _std_dev(window, mean, period)
        if std == 0:
            continue
        z = (closes[i] - mean) / std
        if z < -entry_z:
            signals[i] = 1
        elif z > entry_z:
            signals[i] = -1
    return signals


def _signal_breakout(candles, params):
    closes = [c["close"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    lookback = params["lookback"]
    threshold = params["threshold"] / 100.0
    signals = [0] * len(candles)
    for i in range(lookback, len(candles)):
        high = max(highs[i - lookback:i])
        low = min(lows[i - lookback:i])
        range_val = high - low
        if range_val == 0:
            continue
        if closes[i] > high * (1 + threshold):
            signals[i] = 1
        elif closes[i] < low * (1 - threshold):
            signals[i] = -1
    return signals


def _signal_adx(candles, params):
    """Trend strength — simplified directional movement."""
    closes = [c["close"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    period = params["period"]
    threshold = params["threshold"]
    signals = [0] * len(candles)

    plus_dm, minus_dm, tr = [0], [0], [0]
    for i in range(1, len(candles)):
        up_move = highs[i] - highs[i - 1]
        down_move = lows[i - 1] - lows[i]
        plus_dm.append(max(up_move, 0) if up_move > down_move else 0)
        minus_dm.append(max(down_move, 0) if down_move > up_move else 0)
        tr.append(_true_range(highs[i], lows[i], closes[i - 1]))

    for i in range(period * 2, len(candles)):
        avg_plus = sum(plus_dm[i - period:i]) / period
        avg_minus = sum(minus_dm[i - period:i]) / period
        avg_tr = sum(tr[i - period:i]) / period
        if avg_tr == 0:
            continue
        di_plus = 100 * avg_plus / avg_tr
        di_minus = 100 * avg_minus / avg_tr
        adx = 100 * abs(di_plus - di_minus) / (di_plus + di_minus) if (di_plus + di_minus) > 0 else 0
        if adx > threshold and di_plus > di_minus and plus_dm[i] > 0:
            signals[i] = 1
        elif adx > threshold and di_minus > di_plus and minus_dm[i] > 0:
            signals[i] = -1
    return signals


def _signal_grid(candles, params):
    """Grid trading between recent support/resistance."""
    closes = [c["close"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    lookback = params["lookback"]
    levels = params["levels"]
    signals = [0] * len(candles)
    in_position = False
    entry_prices = []
    for i in range(lookback, len(candles)):
        high = max(highs[i - lookback:i])
        low = min(lows[i - lookback:i])
        grid_step = (high - low) / (levels + 1)
        price = closes[i]
        buy_zones = [low + grid_step * l for l in range(1, levels + 1)]
        sell_zones = [high - grid_step * l for l in range(1, levels + 1)]
        if not in_position:
            for bz in buy_zones:
                if abs(price - bz) / bz < 0.005:
                    signals[i] = 1
                    in_position = True
                    entry_prices.append(price)
                    break
        else:
            for sz in sell_zones:
                if abs(price - sz) / sz < 0.005:
                    signals[i] = -1
                    in_position = False
                    break
    return signals


def _signal_support_resistance(candles, params):
    closes = [c["close"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    lookback = params["lookback"]
    threshold = params["threshold"] / 100.0
    signals = [0] * len(candles)
    for i in range(lookback, len(candles)):
        recent_high = max(highs[i - lookback:i])
        recent_low = min(lows[i - lookback:i])
        range_pct = (recent_high - recent_low) / recent_low
        if range_pct < threshold / 2:
            continue
        if closes[i] > recent_high:
            signals[i] = 1
        elif closes[i] < recent_low:
            signals[i] = -1
    return signals


def _signal_volatility(candles, params):
    closes = [c["close"] for c in candles]
    period = params["period"]
    mult = params["mult"]
    signals = [0] * len(candles)
    returns = [0]
    for i in range(1, len(candles)):
        returns.append((closes[i] - closes[i - 1]) / closes[i - 1])
    for i in range(period, len(candles)):
        window = returns[i - period:i]
        mean_ret = sum(window) / period
        std = _std_dev(window, mean_ret, period) if period > 0 else 0
        if returns[i] < -std * mult:
            signals[i] = 1
        elif returns[i] > std * mult:
            signals[i] = -1
    return signals


def _signal_dual_rsi(candles, params):
    closes = [c["close"] for c in candles]
    rsi_fast = _rsi(closes, params["fast"])
    rsi_slow = _rsi(closes, params["slow"])
    threshold = params["threshold"]
    signals = [0] * len(candles)
    for i in range(1, len(candles)):
        f_p = rsi_fast[i - 1]
        f_c = rsi_fast[i]
        s_p = rsi_slow[i - 1]
        s_c = rsi_slow[i]
        if any(x is None for x in [f_p, f_c, s_p, s_c]):
            continue
        if f_p <= s_p and f_c > s_c and f_c < 100 - threshold:
            signals[i] = 1
        elif f_p >= s_p and f_c < s_c and f_c > threshold:
            signals[i] = -1
    return signals


def _signal_triple_ma(candles, params):
    closes = [c["close"] for c in candles]
    fast_sma = _sma(closes, params["fast"])
    mid_sma = _sma(closes, params["mid"])
    slow_sma = _sma(closes, params["slow"])
    signals = [0] * len(candles)
    for i in range(1, len(candles)):
        f_p, m_p, s_p = fast_sma[i - 1], mid_sma[i - 1], slow_sma[i - 1]
        f_c, m_c, s_c = fast_sma[i], mid_sma[i], slow_sma[i]
        if any(x is None for x in [f_p, m_p, s_p, f_c, m_c, s_c]):
            continue
        if f_p <= m_p <= s_p and f_c > m_c > s_c:
            signals[i] = 1
        elif f_p >= m_p >= s_p and f_c < m_c < s_c:
            signals[i] = -1
    return signals


def _signal_price_action(candles, params):
    """Engulfing pattern + continuation."""
    lookback = params["lookback"]
    reversal_pct = params["reversal_pct"] / 100.0
    signals = [0] * len(candles)
    for i in range(1, len(candles)):
        prev_body = abs(candles[i - 1]["close"] - candles[i - 1]["open"])
        curr_body = abs(candles[i]["close"] - candles[i]["open"])
        if prev_body == 0 or curr_body == 0:
            continue
        prev_bull = candles[i - 1]["close"] > candles[i - 1]["open"]
        prev_high = candles[i - 1]["high"]
        prev_low = candles[i - 1]["low"]
        if prev_bull and candles[i]["close"] < candles[i]["open"]:
            if curr_body > prev_body * 1.2 and candles[i]["close"] < prev_low:
                signals[i] = -1
        elif not prev_bull and candles[i]["close"] > candles[i]["open"]:
            if curr_body > prev_body * 1.2 and candles[i]["close"] > prev_high:
                signals[i] = 1
    return signals


def _signal_stochastic(candles, params):
    closes = [c["close"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    period = params["period"]
    k_period = params["k_period"]
    oversold = params["oversold"]
    overbought = params["overbought"]
    signals = [0] * len(candles)

    raw_k = [None] * len(candles)
    for i in range(period, len(candles)):
        high = max(highs[i - period + 1:i + 1])
        low = min(lows[i - period + 1:i + 1])
        if high != low:
            raw_k[i] = 100 * (closes[i] - low) / (high - low)
    k = _sma([r for r in raw_k if r is not None], k_period) if any(r is not None for r in raw_k) else []

    k_idx = 0
    for i in range(len(candles)):
        if raw_k[i] is not None:
            if k_idx < len(k) and k[k_idx] is not None:
                if k[k_idx] < oversold:
                    signals[i] = 1
                elif k[k_idx] > overbought:
                    signals[i] = -1
            k_idx += 1
    return signals


def _signal_atr_breakout(candles, params):
    closes = [c["close"] for c in candles]
    atr_values = _atr(candles, params["period"])
    mult = params["mult"]
    lookback = params["lookback"]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    signals = [0] * len(candles)
    for i in range(lookback, len(candles)):
        if atr_values[i] is None:
            continue
        high = max(highs[i - lookback:i])
        low = min(lows[i - lookback:i])
        atr = atr_values[i]
        if closes[i] > high + atr * mult:
            signals[i] = 1
        elif closes[i] < low - atr * mult:
            signals[i] = -1
    return signals


def _signal_vwap_reversion(candles, params):
    """Mean reversion from VWAP-like calculation."""
    closes = [c["close"] for c in candles]
    volumes = [c.get("volume", 1) for c in candles]
    period = params["period"]
    std_mult = params["std_mult"]
    signals = [0] * len(candles)
    for i in range(period, len(candles)):
        cum_pv = sum(closes[j] * volumes[j] for j in range(i - period, i))
        cum_v = sum(volumes[j] for j in range(i - period, i))
        if cum_v == 0:
            continue
        vwap = cum_pv / cum_v
        window = closes[i - period:i]
        mean = sum(window) / period
        std = _std_dev(window, mean, period)
        if std == 0:
            continue
        if closes[i] < vwap - std * std_mult:
            signals[i] = 1
        elif closes[i] > vwap + std * std_mult:
            signals[i] = -1
    return signals


# =====================================================================
# TEMPLATE REGISTRY
# =====================================================================

TEMPLATES = [
    {
        "name": "SMA_Crossover",
        "signal_fn": _signal_sma_crossover,
        "params": {
            "fast": {"min": 5, "max": 50, "step": 5},
            "slow": {"min": 10, "max": 200, "step": 10},
        },
        "constraint": lambda p: p["slow"] > p["fast"] * 2,
    },
    {
        "name": "RSI",
        "signal_fn": _signal_rsi,
        "params": {
            "period": {"min": 5, "max": 30, "step": 5},
            "oversold": {"min": 20, "max": 30, "step": 5},
            "overbought": {"min": 70, "max": 80, "step": 5},
        },
        "constraint": lambda p: p["overbought"] > 100 - p["oversold"] + 20,
    },
    {
        "name": "MACD",
        "signal_fn": _signal_macd,
        "params": {
            "fast": {"min": 5, "max": 20, "step": 3},
            "slow": {"min": 10, "max": 40, "step": 5},
            "signal": {"min": 5, "max": 20, "step": 3},
        },
        "constraint": lambda p: 2 < p["fast"] < p["slow"] and p["slow"] / p["fast"] > 1.5,
    },
    {
        "name": "Bollinger",
        "signal_fn": _signal_bollinger,
        "params": {
            "period": {"min": 10, "max": 50, "step": 5},
            "std_dev": {"min": 1.5, "max": 3.0, "step": 0.5},
        },
    },
    {
        "name": "Momentum",
        "signal_fn": _signal_momentum,
        "params": {
            "lookback": {"min": 5, "max": 50, "step": 5},
            "threshold": {"min": 1.0, "max": 5.0, "step": 1.0},
        },
    },
    {
        "name": "MeanReversion",
        "signal_fn": _signal_mean_reversion,
        "params": {
            "period": {"min": 10, "max": 50, "step": 5},
            "entry_z": {"min": 1.0, "max": 3.0, "step": 0.5},
        },
    },
    {
        "name": "Breakout",
        "signal_fn": _signal_breakout,
        "params": {
            "lookback": {"min": 10, "max": 50, "step": 5},
            "threshold": {"min": 0.5, "max": 3.0, "step": 0.5},
        },
    },
    {
        "name": "ADX_Trend",
        "signal_fn": _signal_adx,
        "params": {
            "period": {"min": 10, "max": 30, "step": 5},
            "threshold": {"min": 20, "max": 35, "step": 5},
        },
    },
    {
        "name": "Grid",
        "signal_fn": _signal_grid,
        "params": {
            "lookback": {"min": 20, "max": 60, "step": 10},
            "levels": {"min": 3, "max": 8, "step": 1},
        },
    },
    {
        "name": "SupportResistance",
        "signal_fn": _signal_support_resistance,
        "params": {
            "lookback": {"min": 10, "max": 50, "step": 5},
            "threshold": {"min": 1.0, "max": 5.0, "step": 1.0},
        },
    },
    {
        "name": "Volatility",
        "signal_fn": _signal_volatility,
        "params": {
            "period": {"min": 10, "max": 30, "step": 5},
            "mult": {"min": 1.0, "max": 3.0, "step": 0.5},
        },
    },
    {
        "name": "Dual_RSI",
        "signal_fn": _signal_dual_rsi,
        "params": {
            "fast": {"min": 3, "max": 10, "step": 1},
            "slow": {"min": 14, "max": 30, "step": 4},
            "threshold": {"min": 60, "max": 80, "step": 5},
        },
        "constraint": lambda p: p["slow"] > p["fast"] * 2,
    },
    {
        "name": "Triple_MA",
        "signal_fn": _signal_triple_ma,
        "params": {
            "fast": {"min": 5, "max": 20, "step": 5},
            "mid": {"min": 10, "max": 50, "step": 10},
            "slow": {"min": 20, "max": 100, "step": 10},
        },
        "constraint": lambda p: p["fast"] < p["mid"] < p["slow"],
    },
    {
        "name": "PriceAction",
        "signal_fn": _signal_price_action,
        "params": {
            "lookback": {"min": 5, "max": 20, "step": 5},
            "reversal_pct": {"min": 1.0, "max": 3.0, "step": 0.5},
        },
    },
    {
        "name": "Stochastic",
        "signal_fn": _signal_stochastic,
        "params": {
            "period": {"min": 10, "max": 30, "step": 5},
            "k_period": {"min": 3, "max": 10, "step": 2},
            "oversold": {"min": 15, "max": 25, "step": 5},
            "overbought": {"min": 75, "max": 85, "step": 5},
        },
        "constraint": lambda p: p["overbought"] > 100 - p["oversold"],
    },
    {
        "name": "ATR_Breakout",
        "signal_fn": _signal_atr_breakout,
        "params": {
            "period": {"min": 10, "max": 30, "step": 5},
            "mult": {"min": 1.0, "max": 3.0, "step": 0.5},
            "lookback": {"min": 10, "max": 30, "step": 5},
        },
    },
    {
        "name": "VWAP_Reversion",
        "signal_fn": _signal_vwap_reversion,
        "params": {
            "period": {"min": 10, "max": 50, "step": 5},
            "std_mult": {"min": 1.0, "max": 3.0, "step": 0.5},
        },
    },
]


class StrategyFactory:
    """Generates all strategy variants from templates."""

    def __init__(self, templates=None):
        self.templates = templates or TEMPLATES

    def generate(self, max_variants: int = 0) -> List[StrategyVariant]:
        """Generate all strategy variants across all templates."""
        variants = []
        for template in self.templates:
            count = self._generate_from_template(template, variants)
        if max_variants > 0 and len(variants) > max_variants:
            variants = variants[:max_variants]
        return variants

    def _generate_from_template(self, template, variants):
        """Generate all parameter combinations for one template."""
        param_names = list(template["params"].keys())
        ranges = []
        for name in param_names:
            spec = template["params"][name]
            start = spec["min"]
            stop = spec["max"]
            step = spec["step"]
            if step >= 1:
                values = list(range(int(start), int(stop) + 1, int(step)))
            else:
                count = int((stop - start) / step) + 1
                values = [start + i * step for i in range(count)]
            ranges.append(values)

        from itertools import product
        count = 0
        for combo in product(*ranges):
            params = dict(zip(param_names, combo))
            constraint = template.get("constraint")
            if constraint and not constraint(params):
                continue
            variant = StrategyVariant(
                template_name=template["name"],
                params=params,
                signal_fn=template["signal_fn"],
            )
            variants.append(variant)
            count += 1
        return count

    def stats(self) -> Dict:
        """Return count per template."""
        from collections import Counter
        c = Counter()
        for template in self.templates:
            samples = []
            self._generate_from_template(template, samples)
            c[template["name"]] = len(samples)
        return dict(c)
