"""
OLD SMC Strategy — archived before library upgrade
Original implementation from strategy_registry.py lines 86-118
"""
import pandas as pd
import numpy as np
from quant_nanggroe.engine.strategies.base import Strategy
from quant_nanggroe.engine.strategies.registry import StrategyRegistry

@StrategyRegistry.register
class SMCStrategy_OLD(Strategy):
    """OLD Smart Money Concepts — manual rolling HH/LL BOS + big candle OB"""
    name = "smc_old"
    description = "SMC (OLD): manual BOS with rolling HH/LL, big-candle OB"
    
    def __init__(self, bos_period=10):
        from quant_nanggroe.engine.strategies.base import StrategyParameters
        super().__init__(parameters=StrategyParameters(params={"bos_period": bos_period}))
    
    def generate_signals(self, df):
        df = df.copy()
        h, l, c = df['high'], df['low'], df['close']
        
        # Market Structure: HH/HL = uptrend, LH/LL = downtrend
        df['hh'] = h.rolling(self.bos_period).max()
        df['ll'] = l.rolling(self.bos_period).min()
        
        # BOS (Break of Structure): price breaks recent HH/LL
        prev_hh = df['hh'].shift(1)
        prev_ll = df['ll'].shift(1)
        
        # Order Block: last big candle before move
        body = abs(c - df['open'])
        avg_body = body.rolling(20).mean()
        big_candle = body > avg_body * 1.5
        
        df['entry'] = 0
        # BOS Buy: price breaks HH with big candle
        bos_buy = (c > prev_hh) & big_candle
        # BOS Sell: price breaks LL with big candle
        bos_sell = (c < prev_ll) & big_candle
        df.loc[bos_buy, 'entry'] = 1
        df.loc[bos_sell, 'entry'] = -1
        return df
