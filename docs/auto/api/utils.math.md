# utils.math

## Function: 

Safe division that returns default on zero denominator.

Args:
    numerator: Numerator value
    denominator: Denominator value
    default: Default value when denominator is zero

Returns:
    Division result or default if denominator is zero

*Line: 16*

---

## Function: 

Round price to the nearest tick size.

Args:
    price: Price to round
    tick_size: Minimum price increment

Returns:
    Rounded price

*Line: 33*

---

## Function: 

Calculate percentage change between two values.

Args:
    current: Current value
    previous: Previous value

Returns:
    Percentage change as decimal (e.g., 0.05 for 5%)

*Line: 49*

---

## Function: 

Calculate rolling maximum drawdown for a price series.

Args:
    prices: Price series

Returns:
    Series of drawdown percentages

*Line: 63*

---

## Function: 

Compute annualized Sharpe ratio.

Args:
    returns: Series of periodic returns
    risk_free_rate: Annual risk-free rate
    periods_per_year: Number of return periods per year

Returns:
    Annualized Sharpe ratio

*Line: 78*

---

## Function: 

Compute annualized Sortino ratio (downside deviation only).

Args:
    returns: Series of periodic returns
    risk_free_rate: Annual risk-free rate
    periods_per_year: Number of return periods per year

Returns:
    Annualized Sortino ratio

*Line: 102*

---

## Function: 

Wilders Smoothing (exponential with alpha = 1/period).

Used for proper ADX calculation instead of simple SMA proxy.

Args:
    series: Input series
    period: Smoothing period

Returns:
    Smoothed series

*Line: 129*

---

