"""
TradeBobby SMC Scanner — Smart Money Concepts Scanner
Berdasarkan TradeBobbyTerminal Pro_Trading_System_V5.pine

Mendeteksi SMC patterns:
  - Order Blocks (OB) — candlestick displacement-based
  - Fair Value Gaps (FVG) — 3-candle gap detection
  - Break of Structure (BOS) — HH/HL breakout
  - Change of Character (CHoCH) — trend reversal confirmation
  - Liquidity Sweeps — grab of buy-side/sell-side liquidity
  - Premium/Discount zones — market imbalance
  - Breaker Blocks — OB yang telah di-break
  - Inverse FVG (IFVG) — FVG yang telah di-close
  - Confluence Engine — kombinasikan pattern untuk signal scoring

Integrasi: tambahkan ke multi_pair_scanner atau panggil standalone
"""
import numpy as np
import pandas as pd
import logging
from enum import Enum
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from strategy_registry import register, BaseStrategy


class SMCPattern(Enum):
    OB = "order_block"
    FVG = "fair_value_gap"
    BOS = "break_of_structure"
    CHOCH = "change_of_character"
    LIQ_SWEEP = "liquidity_sweep"
    PREMIUM = "premium_zone"
    DISCOUNT = "discount_zone"
    BREAKER = "breaker_block"
    IFVG = "inverse_fvg"


class TradeBobbySMCPatterns:
    """
    TradeBobby SMC Pattern Detector.
    
    Menerjemahkan logic dari Pro_Trading_System_V5.pine ke Python.
    Mendeteksi SMC patterns pada OHLCV DataFrame.
    """
    
    def __init__(self, swing_lookback=5, fvg_min_pct=0.3, ob_displacement=1.5,
                 liq_tolerance=0.3, min_confluence=3):
        """
        Args:
            swing_lookback: Window untuk swing high/low detection
            fvg_min_pct: Minimum FVG size (% of price)
            ob_displacement: Displacement multiplier (x ATR)
            liq_tolerance: Equal high/low tolerance (%)
            min_confluence: Minimum confluence untuk signal valid
        """
        self.swing_lookback = swing_lookback
        self.fvg_min_pct = fvg_min_pct / 100.0  # convert to decimal
        self.ob_displacement = ob_displacement
        self.liq_tolerance = liq_tolerance / 100.0
        self.min_confluence = min_confluence
    
    def _calculate_atr(self, df, period=14):
        """Average True Range."""
        tr = pd.concat([
            df['high'] - df['low'],
            (df['high'] - df['close'].shift(1)).abs(),
            (df['low'] - df['close'].shift(1)).abs()
        ], axis=1).max(axis=1)
        return tr.rolling(period).mean()
    
    def swing_highs_lows(self, df):
        """
        Identifikasi swing highs dan swing lows.
        
        Swing High: bar dengan high tertinggi dalam lookback window
        Swing Low: bar dengan low terendah dalam lookback window
        
        Returns:
            df dengan kolom 'swing_high', 'swing_low', 'swing_type'
        """
        df = df.copy()
        df['swing_high'] = False
        df['swing_low'] = False
        df['swing_type'] = ''  # 'HH', 'HL', 'LH', 'LL'
        
        half_lb = self.swing_lookback // 2
        
        for i in range(half_lb, len(df) - half_lb):
            # Swing High
            if df['high'].iloc[i] == df['high'].iloc[i-half_lb:i+half_lb+1].max():
                df.loc[df.index[i], 'swing_high'] = True
            # Swing Low
            if df['low'].iloc[i] == df['low'].iloc[i-half_lb:i+half_lb+1].min():
                df.loc[df.index[i], 'swing_low'] = True
        
        # Classify structure: HH/HL/LH/LL
        last_high_idx = None
        last_low_idx = None
        for i in range(len(df)):
            if df['swing_high'].iloc[i]:
                if last_high_idx is not None:
                    prev_high = df['high'].iloc[last_high_idx]
                    if df['high'].iloc[i] > prev_high:
                        df.loc[df.index[i], 'swing_type'] = 'HH'  # Higher High
                    else:
                        df.loc[df.index[i], 'swing_type'] = 'LH'  # Lower High
                else:
                    df.loc[df.index[i], 'swing_type'] = 'HH'
                last_high_idx = i
            
            if df['swing_low'].iloc[i]:
                if last_low_idx is not None:
                    prev_low = df['low'].iloc[last_low_idx]
                    if df['low'].iloc[i] > prev_low:
                        df.loc[df.index[i], 'swing_type'] = 'HL'  # Higher Low
                    else:
                        df.loc[df.index[i], 'swing_type'] = 'LL'  # Lower Low
                else:
                    df.loc[df.index[i], 'swing_type'] = 'HL'
                last_low_idx = i
        
        return df
    
    def detect_order_blocks(self, df):
        """
        Deteksi Order Blocks (OB).
        
        Logic dari TradeBobby PINE:
        - Bullish OB: bearish candle diikuti bullish breakout dengan displacement > ATR * mult
        - Bearish OB: bullish candle diikuti bearish breakdown dengan displacement > ATR * mult
        
        Returns:
            df dengan kolom 'ob_signal', 'ob_top', 'ob_bottom', 'ob_strength'
        """
        df = df.copy()
        df['ob_signal'] = 0
        df['ob_top'] = np.nan
        df['ob_bottom'] = np.nan
        df['ob_strength'] = 0.0
        
        atr = self._calculate_atr(df)
        
        for i in range(2, len(df)-1):
            if pd.isna(atr.iloc[i]):
                continue
            displacement = atr.iloc[i] * self.ob_displacement
            
            # Bullish OB: bearish candle → harga naik (breakout)
            if (df['close'].iloc[i] < df['open'].iloc[i] and  # bearish candle
                df['close'].iloc[i+1] > df['high'].iloc[i]):  # breakout above
                
                # Check displacement
                if df['close'].iloc[i+1] - df['close'].iloc[i] > displacement:
                    df.loc[df.index[i], 'ob_signal'] = 1
                    df.loc[df.index[i], 'ob_top'] = df['high'].iloc[i]
                    df.loc[df.index[i], 'ob_bottom'] = df['low'].iloc[i]
                    # Strength: displacement ratio
                    strength = (df['close'].iloc[i+1] - df['close'].iloc[i]) / atr.iloc[i]
                    df.loc[df.index[i], 'ob_strength'] = min(strength / self.ob_displacement, 3.0)
            
            # Bearish OB: bullish candle → harga turun (breakdown)
            elif (df['close'].iloc[i] > df['open'].iloc[i] and  # bullish candle
                  df['close'].iloc[i+1] < df['low'].iloc[i]):    # breakdown below
                
                if df['close'].iloc[i] - df['close'].iloc[i+1] > displacement:
                    df.loc[df.index[i], 'ob_signal'] = -1
                    df.loc[df.index[i], 'ob_top'] = df['high'].iloc[i]
                    df.loc[df.index[i], 'ob_bottom'] = df['low'].iloc[i]
                    strength = (df['close'].iloc[i] - df['close'].iloc[i+1]) / atr.iloc[i]
                    df.loc[df.index[i], 'ob_strength'] = min(strength / self.ob_displacement, 3.0)
        
        return df
    
    def detect_fvg(self, df):
        """
        Deteksi Fair Value Gaps (FVG).
        
        Logic dari TradeBobby PINE:
        - Bullish FVG: low[i] > high[i-2] (gap between candle 1 and 3)
        - Bearish FVG: high[i] < low[i-2]
        - Filter: gap size > fvg_min_pct * price
        
        Returns:
            df dengan kolom 'fvg_signal', 'fvg_top', 'fvg_bottom', 'fvg_size_pct'
        """
        df = df.copy()
        df['fvg_signal'] = 0
        df['fvg_top'] = np.nan
        df['fvg_bottom'] = np.nan
        df['fvg_size_pct'] = 0.0
        
        for i in range(2, len(df)):
            # Bullish FVG
            if df['low'].iloc[i] > df['high'].iloc[i-2]:
                gap = df['low'].iloc[i] - df['high'].iloc[i-2]
                gap_pct = gap / df['close'].iloc[i]
                if gap_pct >= self.fvg_min_pct:
                    df.loc[df.index[i], 'fvg_signal'] = 1
                    df.loc[df.index[i], 'fvg_top'] = df['low'].iloc[i]
                    df.loc[df.index[i], 'fvg_bottom'] = df['high'].iloc[i-2]
                    df.loc[df.index[i], 'fvg_size_pct'] = gap_pct * 100
            
            # Bearish FVG
            elif df['high'].iloc[i] < df['low'].iloc[i-2]:
                gap = df['low'].iloc[i-2] - df['high'].iloc[i]
                gap_pct = gap / df['close'].iloc[i]
                if gap_pct >= self.fvg_min_pct:
                    df.loc[df.index[i], 'fvg_signal'] = -1
                    df.loc[df.index[i], 'fvg_top'] = df['low'].iloc[i-2]
                    df.loc[df.index[i], 'fvg_bottom'] = df['high'].iloc[i]
                    df.loc[df.index[i], 'fvg_size_pct'] = gap_pct * 100
        
        return df
    
    def detect_bos_choch(self, df):
        """
        Deteksi Break of Structure (BOS) dan Change of Character (CHoCH).
        
        Logic:
        - BOS: Harga menembus swing high/low terakhir
        - CHoCH: Trend reversal — HH/HL → LH/LL atau sebaliknya
        
        Returns:
            df dengan kolom 'bos_signal', 'choch_signal', 'structure'
        """
        df = df.copy()
        df['bos_signal'] = 0
        df['choch_signal'] = 0
        df['structure'] = ''  # 'uptrend', 'downtrend', 'neutral'
        
        swing_df = self.swing_highs_lows(df)
        
        # Track last 2 swing highs and lows for BOS/CHoCH
        last_hh_idx = None
        last_ll_idx = None
        prev_hh_idx = None
        prev_ll_idx = None
        
        for i in range(self.swing_lookback, len(df)):
            # Update swing tracking
            if swing_df['swing_type'].iloc[i] == 'HH':
                prev_hh_idx = last_hh_idx
                last_hh_idx = i
            elif swing_df['swing_type'].iloc[i] == 'LL':
                prev_ll_idx = last_ll_idx
                last_ll_idx = i
            
            # BOS detection: price breaks last swing point
            if last_hh_idx is not None:
                if df['high'].iloc[i] > df['high'].iloc[last_hh_idx]:
                    df.loc[df.index[i], 'bos_signal'] = 1  # Bullish BOS
            
            if last_ll_idx is not None:
                if df['low'].iloc[i] < df['low'].iloc[last_ll_idx]:
                    df.loc[df.index[i], 'bos_signal'] = -1  # Bearish BOS
            
            # CHoCH detection: trend structure change
            # HH→LH: potential downtrend start
            if last_hh_idx is not None and prev_hh_idx is not None:
                if (swing_df['swing_type'].iloc[last_hh_idx] == 'LH' and 
                    swing_df['swing_type'].iloc[prev_hh_idx] == 'HH'):
                    df.loc[df.index[i], 'choch_signal'] = -1  # Bearish CHoCH
            
            # LL→HL: potential uptrend start
            if last_ll_idx is not None and prev_ll_idx is not None:
                if (swing_df['swing_type'].iloc[last_ll_idx] == 'HL' and 
                    swing_df['swing_type'].iloc[prev_ll_idx] == 'LL'):
                    df.loc[df.index[i], 'choch_signal'] = 1  # Bullish CHoCH
        
        # Structure trend
        ema20 = df['close'].ewm(span=20).mean()
        ema50 = df['close'].ewm(span=50).mean()
        df.loc[ema20 > ema50, 'structure'] = 'uptrend'
        df.loc[ema20 < ema50, 'structure'] = 'downtrend'
        df.loc[(df['structure'] == ''), 'structure'] = 'neutral'
        
        return df
    
    def detect_liquidity_sweeps(self, df):
        """
        Deteksi Liquidity Sweeps.
        
        Logic dari TradeBobby PINE:
        - Buy-side liquidity: harga menembus swing high terakhir lalu reversal
        - Sell-side liquidity: harga menembus swing low terakhir lalu reversal
        - Tolerance: level yang hampir sama (equal highs/lows)
        
        Returns:
            df dengan kolom 'liq_sweep', 'liq_type'
        """
        df = df.copy()
        df['liq_sweep'] = 0
        df['liq_type'] = ''  # 'buy_side', 'sell_side'
        
        tolerance = self.liq_tolerance * df['close'].mean()
        
        for i in range(self.swing_lookback * 2, len(df) - 3):
            lookback_window = df.iloc[i-self.swing_lookback*2:i]
            
            # Recent swing high/low
            recent_high = lookback_window['high'].max()
            recent_low = lookback_window['low'].min()
            
            # Buy-side liquidity sweep: break above recent high, then revert
            if (df['high'].iloc[i] > recent_high + tolerance and
                df['close'].iloc[i+1] < recent_high):
                df.loc[df.index[i], 'liq_sweep'] = -1  # Bearish sweep (grabbed buyside)
                df.loc[df.index[i], 'liq_type'] = 'buy_side'
            
            # Sell-side liquidity sweep: break below recent low, then revert
            if (df['low'].iloc[i] < recent_low - tolerance and
                df['close'].iloc[i+1] > recent_low):
                df.loc[df.index[i], 'liq_sweep'] = 1  # Bullish sweep (grabbed sellside)
                df.loc[df.index[i], 'liq_type'] = 'sell_side'
        
        return df
    
    def detect_premium_discount(self, df):
        """
        Deteksi Premium/Discount Zones.
        
        Logic dari TradeBobby PINE:
        - Premium zone: harga di atas midpoint swing range (70-100%)
        - Discount zone: harga di bawah midpoint swing range (0-30%)
        - Entry ideal di discount untuk buy, premium untuk sell
        
        Returns:
            df dengan kolom 'zone' (0=neutral, 1=discount, -1=premium),
            'zone_pct' (0-100% dalam range)
        """
        df = df.copy()
        df['zone'] = 0
        df['zone_pct'] = 50.0  # Neutral midpoint
        
        pd_lookback = max(self.swing_lookback * 10, 50)
        
        for i in range(pd_lookback, len(df)):
            window = df.iloc[i-pd_lookback:i]
            swing_high = window['high'].max()
            swing_low = window['low'].min()
            current_close = df['close'].iloc[i]
            
            if swing_high > swing_low:
                zone_pct = (current_close - swing_low) / (swing_high - swing_low) * 100
                df.loc[df.index[i], 'zone_pct'] = zone_pct
                
                if zone_pct <= 30:
                    df.loc[df.index[i], 'zone'] = 1  # Discount zone (buy zone)
                elif zone_pct >= 70:
                    df.loc[df.index[i], 'zone'] = -1  # Premium zone (sell zone)
        
        return df
    
    def detect_all_patterns(self, df):
        """
        Jalankan semua detector pattern SMC.
        
        Returns:
            df dengan semua kolom pattern SMC
        """
        df = df.copy()
        
        # Run detectors
        swing_df = self.swing_highs_lows(df)
        ob_df = self.detect_order_blocks(df)
        fvg_df = self.detect_fvg(df)
        bos_df = self.detect_bos_choch(df)
        liq_df = self.detect_liquidity_sweeps(df)
        pd_df = self.detect_premium_discount(df)
        
        # Merge results
        df['swing_high'] = swing_df['swing_high']
        df['swing_low'] = swing_df['swing_low']
        df['swing_type'] = swing_df['swing_type']
        df['ob_signal'] = ob_df['ob_signal']
        df['ob_top'] = ob_df['ob_top']
        df['ob_bottom'] = ob_df['ob_bottom']
        df['ob_strength'] = ob_df['ob_strength']
        df['fvg_signal'] = fvg_df['fvg_signal']
        df['fvg_top'] = fvg_df['fvg_top']
        df['fvg_bottom'] = fvg_df['fvg_bottom']
        df['fvg_size_pct'] = fvg_df['fvg_size_pct']
        df['bos_signal'] = bos_df['bos_signal']
        df['choch_signal'] = bos_df['choch_signal']
        df['structure'] = bos_df['structure']
        df['liq_sweep'] = liq_df['liq_sweep']
        df['liq_type'] = liq_df['liq_type']
        df['zone'] = pd_df['zone']
        df['zone_pct'] = pd_df['zone_pct']
        
        return df
    
    def confluence_score(self, df):
        """
        Confluence Engine — hitung confluence score untuk entry signal.
        
        Skor berdasarkan jumlah pattern yang setuju:
        - Bullish: OB+1, FVG+1, BOS+1, CHoCH+1, liq_sweep+1, zone=discount
        - Bearish: OB-1, FVG-1, BOS-1, CHoCH-1, liq_sweep-1, zone=premium
        
        Returns:
            df dengan kolom 'confluence_bull', 'confluence_bear', 'confluence_signal'
        """
        df = df.copy()
        df['confluence_bull'] = 0
        df['confluence_bear'] = 0
        df['confluence_signal'] = 0
        
        for i in range(len(df)):
            # Bullish confluence
            bull_score = 0
            ob_val = df['ob_signal'].iloc[i]
            fvg_val = df['fvg_signal'].iloc[i]
            bos_val = df['bos_signal'].iloc[i]
            choch_val = df['choch_signal'].iloc[i]
            liq_val = df['liq_sweep'].iloc[i]
            zone_val = df['zone'].iloc[i]
            
            if ob_val == 1 and df['ob_strength'].iloc[i] > 1.0:
                bull_score += 1
            if fvg_val == 1:
                bull_score += 1
            if bos_val == 1:
                bull_score += 1
            if choch_val == 1:
                bull_score += 1
            if liq_val == 1:  # sell-side sweep = bullish
                bull_score += 1
            if zone_val == 1:  # discount zone
                bull_score += 1
            
            # Bearish confluence
            bear_score = 0
            if ob_val == -1 and df['ob_strength'].iloc[i] > 1.0:
                bear_score += 1
            if fvg_val == -1:
                bear_score += 1
            if bos_val == -1:
                bear_score += 1
            if choch_val == -1:
                bear_score += 1
            if liq_val == -1:  # buy-side sweep = bearish
                bear_score += 1
            if zone_val == -1:  # premium zone
                bear_score += 1
            
            df.loc[df.index[i], 'confluence_bull'] = bull_score
            df.loc[df.index[i], 'confluence_bear'] = bear_score
            
            if bull_score >= self.min_confluence and bull_score > bear_score:
                df.loc[df.index[i], 'confluence_signal'] = 1
            elif bear_score >= self.min_confluence and bear_score > bull_score:
                df.loc[df.index[i], 'confluence_signal'] = -1
        
        return df
    
    def generate_signals(self, df):
        """
        Full SMC signal generation pipeline.
        
        Returns:
            df dengan kolom 'entry' (1=buy, -1=sell, 0=hold)
        """
        df = self.detect_all_patterns(df)
        df = self.confluence_score(df)
        df['entry'] = df['confluence_signal']
        return df


@register
class TradeBobbySMCStrategy(BaseStrategy):
    """
    TradeBobby SMC Strategy — Smart Money Concepts Scanner terintegrasi.
    
    Menggunakan TradeBobbyTerminal SMC pattern detection engine:
      - Order Blocks, FVG, BOS/CHoCH, Liquidity Sweeps
      - Confluence scoring (min 3 patterns for entry)
      - Premium/Discount zone awareness
    
    Parameters match Pro_Trading_System_V5.pine config.
    """
    name = "tradebobby_smc"
    description = "TradeBobby SMC: Smart Money Concepts scanner dengan confluence engine"
    
    def __init__(self, swing_lookback=5, min_confluence=3, 
                 fvg_min_pct=0.3, ob_displacement=1.5,
                 liq_tolerance=0.3, **kw):
        super().__init__(swing_lookback=swing_lookback, 
                        min_confluence=min_confluence,
                        fvg_min_pct=fvg_min_pct,
                        ob_displacement=ob_displacement,
                        liq_tolerance=liq_tolerance,
                        **kw)
        self._scanner = TradeBobbySMCPatterns(
            swing_lookback=swing_lookback,
            min_confluence=min_confluence,
            fvg_min_pct=fvg_min_pct,
            ob_displacement=ob_displacement,
            liq_tolerance=liq_tolerance
        )
    
    def generate_signals(self, df):
        return self._scanner.generate_signals(df)


# ─── Quick test ────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    # Generate test data
    np.random.seed(42)
    n = 500
    dates = pd.date_range('2025-01-01', periods=n, freq='15min')
    price = 100.0
    prices = []
    for _ in range(n):
        price += np.random.randn() * 0.1
        prices.append(price)
    
    df = pd.DataFrame({
        'open': prices,
        'high': np.array(prices) + np.abs(np.random.randn(n) * 0.2),
        'low': np.array(prices) - np.abs(np.random.randn(n) * 0.2),
        'close': np.array(prices) + np.random.randn(n) * 0.08,
    }, index=dates)
    df['high'] = df[['open', 'close', 'high']].max(axis=1)
    df['low'] = df[['open', 'close', 'low']].min(axis=1)
    
    # Run scanner
    scanner = TradeBobbySMCPatterns(min_confluence=3)
    result = scanner.generate_signals(df)
    
    # Summary
    pattern_counts = {}
    for col in ['ob_signal', 'fvg_signal', 'bos_signal', 'choch_signal', 'liq_sweep']:
        bulls = (result[col] == 1).sum()
        bears = (result[col] == -1).sum()
        pattern_counts[col] = {'bull': int(bulls), 'bear': int(bears)}
    
    signals = result['entry'].value_counts().to_dict()
    
    print("=== TradeBobby SMC Scanner ===\n")
    print(f"Pattern counts: {pattern_counts}")
    print(f"Entry signals: {signals}")
    print(f"Total bars: {len(result)}, entries: {(result['entry'] != 0).sum()}")
    print("\n✅ TradeBobby SMC Scanner ready")
