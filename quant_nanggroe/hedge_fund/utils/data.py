"""Historical market data fetching with mock fallback."""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from quant_nanggroe.hedge_fund.utils.config import (
    MT5_AVAILABLE, PAPER_TRADE, _DATA_DIR, log, mt5,
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

    if PAPER_TRADE:
        log.info(f"  Using mock data for {symbol} (paper mode)")
        np.random.seed(hash(symbol) % (2**31))
        now = datetime.now()
        times = [now - timedelta(minutes=i*tf) for i in range(count-1, -1, -1)]

        close = 1.0800
        closes = []
        for i in range(count):
            close += np.random.normal(0, 0.0005)
            close = max(close, 1.0500)
            close = min(close, 1.1200)
            closes.append(close)

        df = pd.DataFrame({
            'open': [c - np.random.uniform(0, 0.001) for c in closes],
            'high': [c + np.random.uniform(0.001, 0.003) for c in closes],
            'low': [c - np.random.uniform(0.001, 0.003) for c in closes],
            'close': closes,
            'tick_volume': [np.random.randint(100, 5000) for _ in range(count)],
            'spread': [np.random.randint(5, 20) for _ in range(count)],
            'real_volume': [np.random.randint(1000, 50000) for _ in range(count)],
        }, index=pd.DatetimeIndex(times))

        return df

    return None
