"""Historical market data fetching from MT5. Fail-closed on no connection."""

import pandas as pd

from quant_nanggroe.hedge_fund.utils.config import (
    MT5_AVAILABLE,
    PAPER_TRADE,
    mt5,
)


def get_historical_mt5(symbol="EURUSD", count=100, tf=15):
    if MT5_AVAILABLE and not PAPER_TRADE:
        try:
            rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
            if rates is not None and len(rates) > 10:
                df = pd.DataFrame(rates)
                df['time'] = pd.to_datetime(df['time'], unit='s')
                df.set_index('time', inplace=True)
                return df
        except Exception:
            pass

    raise RuntimeError(
        f"No real MT5 data for {symbol} — cannot generate historical data "
        "without live connection. Failing closed (no mock/simulated data)."
    )
