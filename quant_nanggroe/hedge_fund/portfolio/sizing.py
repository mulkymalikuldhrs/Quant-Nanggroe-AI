"""Kelly-based position sizing with signal confidence scaling."""

from quant_nanggroe.engine.kelly import FractionalKelly, KellyParameters
from quant_nanggroe.hedge_fund.utils.config import PAPER_TRADE, log, mt5
from quant_nanggroe.hedge_fund.utils.indicators import calc_atr

MAX_RISK_PER_TRADE = 0.005  # 0.5% — matches engine/risk/constants.py constitutional limit


def calculate_position_size(signal, balance, atr=None, config=None):
    """Compute position size from signal, balance, and volatility.

    Uses FractionalKelly scaled by signal confidence, then converts
    the risk fraction to a lot size based on ATR and instrument specs.

    Args:
        signal: Signal dict with 'confidence' (0-1) and 'symbol'.
        balance: Account balance in quote currency.
        atr: Optional pre-computed ATR value. Computed if None.
        config: Optional override dict with keys: kelly_fraction,
            max_risk_per_trade, win_rate, avg_win, avg_loss.

    Returns:
        Dict with keys: volume, kelly_fraction, position_fraction, confidence.
    """
    conf = max(0.1, min(1.0, signal.get("confidence", 0.5) if isinstance(signal, dict) else 0.5))
    symbol = signal.get("symbol", "EURUSD") if isinstance(signal, dict) else "EURUSD"

    cfg = config or {}
    kelly_frac = cfg.get("kelly_fraction", 0.25)  # ponytail: 0.25 = quarter-Kelly, gate-passing default per quant-engineering-os skill
    max_risk = cfg.get("max_risk_per_trade", MAX_RISK_PER_TRADE)

    kelly = FractionalKelly(fraction=kelly_frac)
    params = KellyParameters(
        win_rate=cfg.get("win_rate", 0.55),
        avg_win=cfg.get("avg_win", 0.012),
        avg_loss=cfg.get("avg_loss", 0.008),
        fraction=kelly_frac,
        leverage_max=max_risk,
    )

    if not PAPER_TRADE and mt5 is not None:
        try:
            from datetime import datetime
            deals = mt5.history_deals_get(datetime(1970, 1, 1), datetime.now())
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
    kelly_fraction = max(0.01, min(result.f_star, max_risk))

    position_fraction = kelly_fraction * conf
    position_fraction = min(position_fraction, max_risk)

    if atr is None:
        atr = calc_atr(symbol) or 0.0010

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

    sl_dist = max(atr * 2, 0.0010)
    sl_pips = sl_dist / pip_size if pip_size > 0 else sl_dist / 0.0001
    dollar_per_pip_per_lot = contract_size * pip_size

    risk_amount = balance * position_fraction
    raw_lot = (risk_amount / (sl_pips * dollar_per_pip_per_lot)) if (sl_pips * dollar_per_pip_per_lot) > 0 else 0.01
    lot = max(0.01, round(raw_lot, 2))
    notional_cap_lot = max(0.01, round(balance * position_fraction * 2 / 1000, 2))
    lot = min(lot, notional_cap_lot)
    lot = max(0.01, lot)

    return {
        "volume": lot,
        "kelly_fraction": round(kelly_fraction, 4),
        "position_fraction": round(position_fraction, 4),
        "confidence": conf,
    }
