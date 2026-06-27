# engine.risk.position_sizing

## Class: 

Result from position sizing calculation.

*Line: 26*

---

## Class: 

Position Sizing with Constitutional Limits.

All methods enforce MAX_RISK_PER_TRADE as a hard cap.
No method can exceed this limit regardless of input parameters.

**Methods:** fixed_fractional, volatility_based, kelly_based, optimal_f

*Line: 37*

---

## Function: 

Fixed fractional position sizing.

Size = (equity * risk_pct) / |entry - stop|

Args:
    equity: Current portfolio equity.
    risk_pct: Desired risk percentage (capped at MAX_RISK_PER_TRADE).
    entry_price: Entry price.
    stop_price: Stop loss price.

Returns:
    PositionSizeResult with calculated size.

*Line: 45*

---

## Function: 

Volatility-based position sizing using ATR.

Stop distance = atr_multiplier * ATR
Size = (equity * risk_pct) / stop_distance

Args:
    equity: Current portfolio equity.
    atr: Average True Range value.
    atr_multiplier: ATR multiplier for stop distance.
    entry_price: Entry price.
    risk_pct: Risk percentage (capped at MAX_RISK_PER_TRADE).

Returns:
    PositionSizeResult.

*Line: 83*

---

## Function: 

Kelly-based position sizing.

Args:
    equity: Current portfolio equity.
    win_rate: Historical win rate.
    avg_win: Average winning trade amount.
    avg_loss: Average losing trade amount.
    fraction: Kelly fraction (0.5 = half Kelly).

Returns:
    PositionSizeResult.

*Line: 124*

---

## Function: 

Ralph Vince's Optimal-f position sizing.

Finds the fraction that maximizes geometric growth from
historical trade results.

Args:
    equity: Current portfolio equity.
    trades_pnl: List of historical trade P&L values.

Returns:
    PositionSizeResult.

*Line: 167*

---

