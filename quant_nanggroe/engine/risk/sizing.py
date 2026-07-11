"""Position Sizing — from n8n Trading Pipeline Risk Management node.

Reference: n8ntrading.json → Risk Management JavaScript logic
"""


def calculate_position_size(
    entry_price: float,
    stop_loss: float,
    account_balance: float,
    risk_per_trade: float = 0.02,
    pip_value: float = 1.0,
    instrument_type: str = "forex",
) -> dict:
    """Calculate position size based on account risk.

    Args:
        entry_price: Entry price
        stop_loss: Stop loss price
        account_balance: Account balance in quote currency
        risk_per_trade: Risk per trade as decimal (0.02 = 2%)
        pip_value: Value per pip/lot in quote currency
        instrument_type: 'forex', 'crypto', 'equity'

    Returns:
        dict with lot_size, risk_amount, risk_pct, ticks_risk
    """
    risk_amount = account_balance * risk_per_trade
    ticks_risk = abs(entry_price - stop_loss)

    if ticks_risk == 0:
        return {
            "lot_size": 0.0,
            "risk_amount": risk_amount,
            "risk_pct": risk_per_trade,
            "ticks_risk": 0.0,
            "error": "Stop loss equals entry price",
        }

    if instrument_type == "forex":
        lot_size = risk_amount / (ticks_risk * pip_value)
    elif instrument_type == "crypto":
        lot_size = risk_amount / ticks_risk
    else:
        lot_size = risk_amount / ticks_risk

    return {
        "lot_size": round(lot_size, 4),
        "risk_amount": round(risk_amount, 2),
        "risk_pct": round(risk_per_trade * 100, 2),
        "ticks_risk": round(ticks_risk, 5),
    }


def calculate_kelly_size(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    account_balance: float,
    kelly_fraction: float = 0.25,
) -> dict:
    """Kelly Criterion position sizing with fractional scaling.

    Args:
        win_rate: Win rate as decimal (0.6 = 60%)
        avg_win: Average win amount
        avg_loss: Average loss amount
        account_balance: Account balance
        kelly_fraction: Fraction of Kelly to use (default 0.25 = 25%)

    Returns:
        dict with kelly_pct, fractional_kelly, suggested_position
    """
    if avg_loss == 0:
        return {"error": "Average loss cannot be zero"}

    b = avg_win / avg_loss
    p = win_rate
    q = 1 - p

    kelly_pct = (b * p - q) / b
    kelly_pct = max(0.0, min(kelly_pct, 1.0))

    fractional_kelly = kelly_pct * kelly_fraction
    suggested_position = account_balance * fractional_kelly

    return {
        "kelly_pct": round(kelly_pct * 100, 2),
        "fractional_kelly": round(fractional_kelly * 100, 2),
        "suggested_position": round(suggested_position, 2),
        "kelly_fraction": kelly_fraction,
    }
