"""ATR-based Stop Loss — from MULKY_OS Indicator.

Implements Wilder's ATR calculation and position sizing for stop losses.
Reference: MULKY_OS_Indicator_v2.pine → get_atr_sl()
"""

from typing import Optional


def wilder_atr(high, low, close, period: int = 14) -> float:
    """Wilder's smoothed ATR from high/low/close arrays."""
    n = len(high)
    if n < period + 1:
        return 0.0

    tr_sum = 0.0
    for i in range(1, period + 1):
        hl = high[i] - low[i]
        hc = abs(high[i] - close[i - 1])
        lc = abs(low[i] - close[i - 1])
        tr_sum += max(hl, hc, lc)

    atr = tr_sum / period
    for i in range(period + 1, n):
        hl = high[i] - low[i]
        hc = abs(high[i] - close[i - 1])
        lc = abs(low[i] - close[i - 1])
        tr = max(hl, hc, lc)
        atr = (atr * (period - 1) + tr) / period

    return atr


def calculate_atr_sl(
    high,
    low,
    close,
    entry_price: float,
    side: str = "long",
    atr_period: int = 14,
    atr_multiplier: float = 1.5,
    min_sl_distance: Optional[float] = None,
) -> dict:
    """Calculate ATR-based stop loss.

    Args:
        high: Array of high prices
        low: Array of low prices
        close: Array of close prices
        entry_price: Entry price
        side: 'long' or 'short'
        atr_period: ATR lookback (default 14)
        atr_multiplier: ATR multiplier for SL distance (default 1.5)
        min_sl_distance: Minimum SL distance in price units

    Returns:
        dict with stop_loss, sl_distance, atr_value
    """
    atr_value = wilder_atr(high, low, close, atr_period)
    sl_distance = atr_value * atr_multiplier

    if min_sl_distance is not None:
        sl_distance = max(sl_distance, min_sl_distance)

    if side == "long":
        stop_loss = entry_price - sl_distance
    else:
        stop_loss = entry_price + sl_distance

    return {
        "stop_loss": round(stop_loss, 5),
        "sl_distance": round(sl_distance, 5),
        "atr_value": round(atr_value, 5),
        "atr_period": atr_period,
        "atr_multiplier": atr_multiplier,
    }
