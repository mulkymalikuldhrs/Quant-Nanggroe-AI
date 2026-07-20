"""
Strategy Registry — semua strategi terdaftar & bisa di-backtest
Plug & play: tambah strategi baru = buat class + daftarkan
"""
import numpy as np
import pandas as pd
from pathlib import Path
import logging, importlib, inspect, json

log = logging.getLogger('registry')

STRATEGIES = {}  # name -> class

def register(cls):
    """Decorator: daftarkan strategi ke registry"""
    name = cls.__name__
    STRATEGIES[name] = cls
    return cls

def list_strategies():
    """Semua strategi yang terdaftar"""
    return list(STRATEGIES.keys())

def get_strategy(name, **params):
    """Buat instance strategi by name"""
    cls = STRATEGIES.get(name)
    if not cls:
        raise ValueError(f"Strategy '{name}' not found. Available: {list_strategies()}")
    return cls(**params)

# ════════════════════════════════════════
# STRATEGY BASE CLASS
# ════════════════════════════════════════

class BaseStrategy:
    """Semua strategi harus inherit dari ini"""
    name = "base"
    description = ""
    
    def generate_signals(self, df):
        """Return: df dengan kolom 'entry' (1=buy, -1=sell, 0=hold)"""
        raise NotImplementedError

    def __init__(self, **params):
        self.params = params
        for k, v in params.items():
            setattr(self, k, v)

# ════════════════════════════════════════
# STRATEGI 1: MSNR — Malaysian S&R
# ════════════════════════════════════════

@register
class MSNRStrategy(BaseStrategy):
    """Malaysian Support & Resistance — storyline-based"""
    name = "msnr"
    description = "MSNR: Hybrid SMC + Price Action, storyline-driven"
    
    def __init__(self, lookback=20, breakout_mult=1.5, **kw):
        super().__init__(lookback=lookback, breakout_mult=breakout_mult, **kw)
    
    def generate_signals(self, df):
        df = df.copy()
        h, l, c = df['high'], df['low'], df['close']
        
        # S/R levels: recent HH/LL
        df['hh'] = h.rolling(self.lookback).max()
        df['ll'] = l.rolling(self.lookback).min()
        df['range'] = df['hh'] - df['ll']
        
        # Breakout signal with volume confirmation
        df['entry'] = 0
        # Buy: close breaks above HH
        buy = (c > df['hh'].shift(1)) & (df['range'] > 0)
        # Sell: close breaks below LL  
        sell = (c < df['ll'].shift(1)) & (df['range'] > 0)
        df.loc[buy, 'entry'] = 1
        df.loc[sell, 'entry'] = -1
        return df

# ════════════════════════════════════════
# STRATEGI 2: SMC — Smart Money Concepts (UPGRADED with smart-money-concepts library)
# ════════════════════════════════════════

try:
    from smartmoneyconcepts.smc import smc as smc_lib
    SMC_LIB_AVAILABLE = True
except ImportError:
    SMC_LIB_AVAILABLE = False

@register
class SMCStrategy(BaseStrategy):
    """Smart Money Concepts — upgraded with smart-money-concepts library (OB, FVG, BOS, CHoCH, Liquidity)"""
    name = "smc"
    description = "SMC: library-based BOS/CHoCH/OB/FVG/Liquidity detection"
    
    def __init__(self, swing_length=10, join_fvg=True, close_break=True, close_mitigation=False,
                 ob_weight=1.0, bos_weight=1.0, choch_weight=1.0, fvg_weight=1.0,
                 min_ob_strength=30.0, **kw):
        super().__init__(
            swing_length=swing_length, join_fvg=join_fvg, close_break=close_break,
            close_mitigation=close_mitigation, ob_weight=ob_weight, bos_weight=bos_weight,
            choch_weight=choch_weight, fvg_weight=fvg_weight, min_ob_strength=min_ob_strength,
            **kw
        )
    
    def generate_signals(self, df):
        df = df.copy()
        
        # Ensure required columns exist with proper names
        ohlc = df.rename(columns={
            c: c.lower() for c in df.columns
        })
        
        # Map volume column (MT5 uses 'tick_volume' or 'real_volume')
        if 'volume' not in ohlc.columns:
            for vol_col in ['tick_volume', 'real_volume', 'Volume', 'TICKVOL']:
                if vol_col in ohlc.columns:
                    ohlc['volume'] = ohlc[vol_col].values
                    break
            if 'volume' not in ohlc.columns:
                ohlc['volume'] = 0  # fallback
        
        if not SMC_LIB_AVAILABLE:
            # Fallback: simple BOS using rolling HH/LL (original logic)
            h, l, c_ = ohlc['high'], ohlc['low'], ohlc['close']
            ohlc['hh'] = h.rolling(self.swing_length).max()
            ohlc['ll'] = l.rolling(self.swing_length).min()
            body = abs(c_ - ohlc['open'])
            avg_body = body.rolling(20).mean()
            big_candle = body > avg_body * 1.5
            ohlc['entry'] = 0
            ohlc.loc[(c_ > ohlc['hh'].shift(1)) & big_candle, 'entry'] = 1
            ohlc.loc[(c_ < ohlc['ll'].shift(1)) & big_candle, 'entry'] = -1
            return ohlc
        
        # ── Step 1: Swing Highs & Lows ──
        shl = smc_lib.swing_highs_lows(ohlc, swing_length=self.swing_length)
        df['swing_hl'] = shl['HighLow'].values
        df['swing_level'] = shl['Level'].values
        
        # ── Step 2: BOS / CHoCH ──
        bos_result = smc_lib.bos_choch(ohlc, shl, close_break=self.close_break)
        df['bos'] = bos_result['BOS'].values
        df['choch'] = bos_result['CHOCH'].values
        df['bos_level'] = bos_result['Level'].values
        
        # ── Step 3: Order Blocks ──
        ob_result = smc_lib.ob(ohlc, shl, close_mitigation=self.close_mitigation)
        df['ob'] = ob_result['OB'].values
        df['ob_top'] = ob_result['Top'].values
        df['ob_bottom'] = ob_result['Bottom'].values
        df['ob_volume'] = ob_result['OBVolume'].values
        df['ob_pct'] = ob_result['Percentage'].values
        
        # ── Step 4: Fair Value Gaps ──
        fvg_result = smc_lib.fvg(ohlc, join_consecutive=self.join_fvg)
        df['fvg'] = fvg_result['FVG'].values
        df['fvg_top'] = fvg_result['Top'].values
        df['fvg_bottom'] = fvg_result['Bottom'].values
        
        # ── Step 5: Entry Signal Generation ──
        df['entry'] = 0
        
        # Bullish signals: BOS+1 OR CHoCH+1, plus OB+1 or FVG+1 for confirmation
        bullish_bos = df['bos'] == 1
        bullish_choch = df['choch'] == 1
        bullish_ob = (df['ob'] == 1) & (df['ob_pct'].fillna(0) >= self.min_ob_strength)
        bullish_fvg = df['fvg'] == 1
        
        # Bearish signals: BOS-1 OR CHoCH-1, plus OB-1 or FVG-1
        bearish_bos = df['bos'] == -1
        bearish_choch = df['choch'] == -1
        bearish_ob = (df['ob'] == -1) & (df['ob_pct'].fillna(0) >= self.min_ob_strength)
        bearish_fvg = df['fvg'] == -1
        
        # Entry rules:
        # Buy: BOS/CHoCH + confirmed by OB or FVG
        buy = (bullish_bos | bullish_choch) & (bullish_ob | bullish_fvg)
        # Sell: BOS/CHoCH + confirmed by OB or FVG
        sell = (bearish_bos | bearish_choch) & (bearish_ob | bearish_fvg)
        
        df.loc[buy, 'entry'] = 1
        df.loc[sell, 'entry'] = -1
        
        return df

# ════════════════════════════════════════
# STRATEGI 3: Mean Reversion (Stochastic)
# ════════════════════════════════════════

@register
class MeanReversionStrategy(BaseStrategy):
    """Mean Reversion via Stochastic Oscillator"""
    name = "mean_rev"
    description = "Mean Reversion: Stochastic %K/%D crossover"
    
    def __init__(self, k_period=14, d_period=3, oversold=20, overbought=80, **kw):
        super().__init__(k_period=k_period, d_period=d_period, oversold=oversold, overbought=overbought, **kw)
    
    def generate_signals(self, df):
        df = df.copy()
        h, l, c = df['high'], df['low'], df['close']
        
        # Stochastic %K
        low_k = l.rolling(self.k_period).min()
        high_k = h.rolling(self.k_period).max()
        df['stoch_k'] = 100 * (c - low_k) / (high_k - low_k)
        df['stoch_d'] = df['stoch_k'].rolling(self.d_period).mean()
        
        df['entry'] = 0
        # Buy when oversold + K crosses above D
        buy = (df['stoch_k'] < self.oversold) & (df['stoch_k'] > df['stoch_d'])
        # Sell when overbought + K crosses below D
        sell = (df['stoch_k'] > self.overbought) & (df['stoch_k'] < df['stoch_d'])
        df.loc[buy, 'entry'] = 1
        df.loc[sell, 'entry'] = -1
        return df

# ════════════════════════════════════════
# STRATEGI 4: Fibo Retracement
# ════════════════════════════════════════

@register
class FiboStrategy(BaseStrategy):
    """Fibonacci Retracement + Extension"""
    name = "fibo"
    description = "Fibonacci: entry di level retracement 0.382/0.5/0.618"
    
    def __init__(self, lookback=30, **kw):
        super().__init__(lookback=lookback, **kw)
    
    def generate_signals(self, df):
        df = df.copy()
        h, l, c = df['high'], df['low'], df['close']
        
        # Swing high/low terakhir
        df['swing_h'] = h.rolling(self.lookback).max()
        df['swing_l'] = l.rolling(self.lookback).min()
        df['range'] = df['swing_h'] - df['swing_l']
        
        # Fibo levels
        df['fib_382'] = df['swing_h'] - df['range'] * 0.382
        df['fib_500'] = df['swing_h'] - df['range'] * 0.500
        df['fib_618'] = df['swing_h'] - df['range'] * 0.618
        
        df['entry'] = 0
        # Buy near fib levels in uptrend
        uptrend = c > df['swing_l'].shift(self.lookback)
        buy = uptrend & (c <= df['fib_618']) & (c >= df['fib_382'])
        # Sell near fib levels in downtrend
        downtrend = c < df['swing_h'].shift(self.lookback)
        sell = downtrend & (c >= df['swing_h'] - df['range'] * 0.382) & (c <= df['swing_h'] - df['range'] * 0.618)
        df.loc[buy, 'entry'] = 1
        df.loc[sell, 'entry'] = -1
        return df

# ════════════════════════════════════════
# STRATEGI 5: EMA + ADX filter
# ════════════════════════════════════════

@register
class EMAADXStrategy(BaseStrategy):
    """EMA crossover dengan ADX trend filter"""
    name = "ema_adx"
    description = "EMA + ADX: hanya trading saat trend kuat"
    
    def __init__(self, fast=12, slow=26, adx_period=14, adx_threshold=25, **kw):
        super().__init__(fast=fast, slow=slow, adx_period=adx_period, adx_threshold=adx_threshold, **kw)
    
    def generate_signals(self, df):
        df = df.copy()
        h, l, c = df['high'], df['low'], df['close']
        
        # EMA
        df['ema_f'] = c.ewm(span=self.fast).mean()
        df['ema_s'] = c.ewm(span=self.slow).mean()
        
        # ADX
        tr = pd.concat([h - l, abs(h - c.shift(1)), abs(l - c.shift(1))], axis=1).max(axis=1)
        atr = tr.rolling(self.adx_period).mean()
        plus_dm = (h - h.shift(1)).where(lambda x: x > 0, 0)
        minus_dm = (l.shift(1) - l).where(lambda x: x > 0, 0)
        plus_di = 100 * (plus_dm.rolling(self.adx_period).sum() / atr.clip(lower=0.001))
        minus_di = 100 * (minus_dm.rolling(self.adx_period).sum() / atr.clip(lower=0.001))
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di).clip(lower=0.001)
        df['adx'] = dx.rolling(self.adx_period).mean()
        
        df['entry'] = 0
        trend = df['adx'] > self.adx_threshold
        buy = trend & (df['ema_f'] > df['ema_s'])
        sell = trend & (df['ema_f'] < df['ema_s'])
        df.loc[buy, 'entry'] = 1
        df.loc[sell, 'entry'] = -1
        return df

# ════════════════════════════════════════
# STRATEGI 7: Quarterly Theory (ICT)
# ════════════════════════════════════════

@register
class QuarterlyTheoryStrategy(BaseStrategy):
    """ICT Quarterly Theory — market structure berdasarkan session"""
    name = "quarterly"
    description = "Quarterly Theory: Asian/London/NY session bias"
    
    def __init__(self, **kw):
        super().__init__(**kw)
    
    def generate_signals(self, df):
        df = df.copy()
        h, l, c = df['high'], df['low'], df['close']
        
        # Session ranges
        df['session_range'] = h.rolling(24) - l.rolling(24)
        df['avg_range'] = df['session_range'].rolling(5).mean()
        
        # Liquidity grab detection
        df['hh_20'] = h.rolling(20).max()
        df['ll_20'] = l.rolling(20).min()
        
        # Entry: after liquidity grab (break HH/LL then reverse)
        df['entry'] = 0
        # Buy: break below recent low then close back above
        for i in range(5, len(df)):
            if c.iloc[i] > df['ll_20'].iloc[i] and c.iloc[i-1] <= df['ll_20'].iloc[i-1]:
                df.loc[df.index[i], 'entry'] = 1
            if c.iloc[i] < df['hh_20'].iloc[i] and c.iloc[i-1] >= df['hh_20'].iloc[i-1]:
                df.loc[df.index[i], 'entry'] = -1
        return df

# ════════════════════════════════════════
# STRATEGI 8: AMDX/XAMD (Market Profile)
# ════════════════════════════════════════

@register
class AMDXStrategy(BaseStrategy):
    """AMDX/XAMD — Market Profile Open/Close relationship"""
    name = "amdx"
    description = "AMDX/XAMD: market profile open-drive-close"
    
    def __init__(self, lookback=8, **kw):
        super().__init__(lookback=lookback, **kw)
    
    def generate_signals(self, df):
        df = df.copy()
        o, h, l, c = df['open'], df['high'], df['low'], df['close']
        
        # AMDX: Open > Close from prev session = bearish bias
        df['gap'] = o - c.shift(1)
        df['body'] = abs(c - o)
        df['range'] = h - l
        
        # XAMD: market profile
        df['open_type'] = 0
        df.loc[o > c.shift(1), 'open_type'] = 1   # gap up
        df.loc[o < c.shift(1), 'open_type'] = -1  # gap down
        
        # Entry: gap fill + continuation
        df['entry'] = 0
        # Buy: gap down + close above open
        buy = (df['open_type'] == -1) & (c > o) & (c > c.shift(1))
        # Sell: gap up + close below open
        sell = (df['open_type'] == 1) & (c < o) & (c < c.shift(1))
        df.loc[buy, 'entry'] = 1
        df.loc[sell, 'entry'] = -1
        return df

# ════════════════════════════════════════
# STRATEGI 9: Algebra (Statistical Arbitrage)
# ════════════════════════════════════════

@register
class AlgebraStrategy(BaseStrategy):
    """Statistical arbitrage via linear algebra — mean reversion with z-score"""
    name = "algebra"
    description = "Algebra: Z-score mean reversion + linear regression"
    
    def __init__(self, window=20, entry_z=2.0, exit_z=0.5, **kw):
        super().__init__(window=window, entry_z=entry_z, exit_z=exit_z, **kw)
    
    def generate_signals(self, df):
        df = df.copy()
        c = df['close']
        
        # Moving average & standard deviation
        ma = c.rolling(self.window).mean()
        std = c.rolling(self.window).std()
        
        # Z-score
        df['z_score'] = (c - ma) / (std + 0.0001)
        
        # Linear regression slope (1st derivative of z-score)
        df['z_slope'] = df['z_score'].diff(3)
        
        df['entry'] = 0
        # Buy: z-score < -entry_z AND z-slope turning up (reversal)
        buy = (df['z_score'] < -self.entry_z) & (df['z_slope'] > 0)
        # Sell: z-score > entry_z AND z-slope turning down
        sell = (df['z_score'] > self.entry_z) & (df['z_slope'] < 0)
        df.loc[buy, 'entry'] = 1
        df.loc[sell, 'entry'] = -1
        return df

@register
class WyckoffStrategy(BaseStrategy):
    """Wyckoff: Accumulation/Distribution volume analysis"""
    name = "wyckoff"
    description = "Wyckoff: volume spread analysis"
    
    def __init__(self, lookback=20, volume_mult=1.5, **kw):
        super().__init__(lookback=lookback, volume_mult=volume_mult, **kw)
    
    def generate_signals(self, df):
        df = df.copy()
        c, v = df['close'], df.get('tick_volume', df.get('volume', pd.Series(0, index=df.index)))
        
        df['v_avg'] = v.rolling(self.lookback).mean()
        df['v_spike'] = v > df['v_avg'] * self.volume_mult
        spread = df['high'] - df['low']
        df['spread_wide'] = spread > spread.rolling(self.lookback).mean() * 1.3
        
        # Accumulation: wide spread down + volume spike = selling climax
        # Distribution: wide spread up + volume spike = buying climax
        df['entry'] = 0
        buy = df['spread_wide'] & df['v_spike'] & (c < c.shift(1))  # selling climax
        sell = df['spread_wide'] & df['v_spike'] & (c > c.shift(1))  # buying climax
        df.loc[buy, 'entry'] = 1
        df.loc[sell, 'entry'] = -1
        return df

# ════════════════════════════════════════
# STRATEGI 10: SMC OLD — archived for comparison
# ════════════════════════════════════════

@register
class SMCStrategyOld(BaseStrategy):
    """OLD Smart Money Concepts — manual rolling HH/LL BOS + big candle OB (pre-library baseline)"""
    name = "smc_old"
    description = "SMC (OLD): manual BOS with rolling HH/LL, big-candle OB"
    
    def __init__(self, bos_period=10, **kw):
        super().__init__(bos_period=bos_period, **kw)
    
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

if __name__ == "__main__":
    print("=== Strategy Registry ===\n")
    for name in list_strategies():
        s = get_strategy(name)
        print(f"  {name}: {s.description}")
    print(f"\nTotal: {len(list_strategies())} strategies registered")

# Late import for externally registered strategies (avoid circular import)
from strategies import dhaher_system, kronos_wrapper, tradebobby_smc_scanner
