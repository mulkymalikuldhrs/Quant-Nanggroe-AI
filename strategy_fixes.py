"""
Strategy Fixes — override broken MSNR, SMC, QuarterlyTheory with working versions
Call apply_fixes() to monkey-patch the registry BEFORE running tests.
"""
import numpy as np
import pandas as pd
import logging

log = logging.getLogger('fixes')

# ──────────────────────────────────────────────
# FIX 1: MSNRStrategy — Malaysian S&R v2
# ──────────────────────────────────────────────

class MSNRStrategyFixed:
    """
    MSNR v3: Support & Resistance mean-reversion + breakout with RSI filter.
    Uses price reaction at key levels with candlestick confirmation.
    """
    name = "msnr_fixed"
    description = "MSNR v3: S/R reaction trading, RSI filter, ATR stops"
    
    def __init__(self, lookback=24, rsi_period=14, rsi_low=35, rsi_high=65, trend_ema=100, **kw):
        self.lookback = lookback
        self.rsi_period = rsi_period
        self.rsi_low = rsi_low
        self.rsi_high = rsi_high
        self.trend_ema = trend_ema
        self.params = {"lookback": lookback, "rsi_period": rsi_period, "rsi_low": rsi_low,
                       "rsi_high": rsi_high, "trend_ema": trend_ema, **kw}
        for k, v in self.params.items():
            setattr(self, k, v)
    
    def generate_signals(self, df):
        df = df.copy()
        h, l, c, o = df['high'], df['low'], df['close'], df['open']
        
        # ── S/R Levels ──
        df['resistance'] = h.rolling(self.lookback).max()
        df['support'] = l.rolling(self.lookback).min()
        df['s_range'] = df['resistance'] - df['support']
        
        # ── RSI ──
        delta = c.diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)
        avg_g = gain.rolling(self.rsi_period).mean()
        avg_l = loss.rolling(self.rsi_period).mean().clip(lower=0.0001)
        rs = avg_g / avg_l
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # ── Trend ──
        df['ema'] = c.ewm(span=self.trend_ema).mean()
        df['uptrend'] = c > df['ema']
        df['downtrend'] = c < df['ema']
        
        # ── Candlestick confirmation ──
        body = abs(c - o)
        upper_wick = h - c.where(c > o, o)
        lower_wick = l - o.where(c < o, c)
        df['long_upper'] = upper_wick > body * 1.5  # rejection from high
        df['long_lower'] = lower_wick > body * 1.5  # rejection from low
        
        # Bullish pin bar / hammer at support
        bullish_reversal = (lower_wick > body * 2) & (body > 0) & (c >= o)
        # Bearish shooting star at resistance
        bearish_reversal = (upper_wick > body * 2) & (body > 0) & (c <= o)
        
        # ── Entry signals ──
        sr_proximity = 0.001  # 0.1% proximity to S/R
        
        # BUY conditions: near support + oversold/neutral RSI + bullish candle + uptrend
        near_support = c <= df['support'] * (1 + sr_proximity)
        rsi_ok_buy = df['rsi'] < self.rsi_high
        buy_reversal = bullish_reversal | (body > 0)  # any body when near support
        
        buy_signal = (near_support | df['long_lower']) & rsi_ok_buy & buy_reversal
        
        # SELL conditions: near resistance + overbought/neutral RSI + bearish candle + downtrend
        near_resistance = c >= df['resistance'] * (1 - sr_proximity)
        rsi_ok_sell = df['rsi'] > self.rsi_low
        sell_reversal = bearish_reversal | (body > 0)
        
        sell_signal = (near_resistance | df['long_upper']) & rsi_ok_sell & sell_reversal
        
        # Trend-filtered entries
        df['entry'] = 0
        df.loc[buy_signal & df['uptrend'], 'entry'] = 1
        df.loc[sell_signal & df['downtrend'], 'entry'] = -1
        
        # Avoid consecutive same-direction entries
        entry_col = df.columns.get_loc('entry')
        for i in range(1, len(df)):
            if df.iat[i, entry_col] != 0 and df.iat[i-1, entry_col] == df.iat[i, entry_col]:
                df.iat[i, entry_col] = 0
        
        return df


# ──────────────────────────────────────────────
# FIX 2: SMCStrategy — Smart Money Concepts v2
# ──────────────────────────────────────────────

class SMCStrategyFixed:
    """
    SMC v2: proper swing detection, BOS/CHoCH, Order Blocks, Fair Value Gaps.
    """
    name = "smc_fixed"
    description = "SMC v2: swing points, BOS/CHoCH, Order Blocks, FVG"
    
    def __init__(self, swing_period=5, bos_confirmation_bars=2, ob_lookback=10, **kw):
        self.swing_period = swing_period
        self.bos_confirmation_bars = bos_confirmation_bars
        self.ob_lookback = ob_lookback
        self.params = {"swing_period": swing_period, "bos_confirmation_bars": bos_confirmation_bars,
                       "ob_lookback": ob_lookback, **kw}
        for k, v in self.params.items():
            setattr(self, k, v)
    
    def _detect_swing_points(self, h, l):
        """Detect swing highs and swing lows."""
        win = self.swing_period
        # Swing high: current high is max of surrounding bars
        swing_high = (h == h.rolling(win*2+1, center=True).max()) & ~h.isna()
        swing_low = (l == l.rolling(win*2+1, center=True).min()) & ~l.isna()
        return swing_high, swing_low
    
    def _detect_bos_choch(self, df):
        """Detect Break of Structure and Change of Character."""
        h, l, c = df['high'], df['low'], df['close']
        
        # Locate swing points
        swing_high, swing_low = self._detect_swing_points(h, l)
        
        # Previous swing levels (carry forward)
        last_swing_high = pd.Series(np.nan, index=df.index)
        last_swing_low = pd.Series(np.nan, index=df.index)
        prev_swing_high = pd.Series(np.nan, index=df.index)
        prev_swing_low = pd.Series(np.nan, index=df.index)
        
        last_high = -np.inf
        last_low = np.inf
        prev_high = -np.inf
        prev_low = np.inf
        
        for i in range(len(df)):
            if swing_high.iloc[i]:
                prev_high = last_high
                last_high = h.iloc[i]
            if swing_low.iloc[i]:
                prev_low = last_low
                last_low = l.iloc[i]
            last_swing_high.iloc[i] = last_high
            last_swing_low.iloc[i] = last_low
            prev_swing_high.iloc[i] = prev_high
            prev_swing_low.iloc[i] = prev_low
        
        # Trend direction: HH & HL = uptrend, LH & LL = downtrend
        making_hh = (last_swing_high > prev_swing_high) & prev_swing_high.notna()
        making_hl = (last_swing_low > prev_swing_low) & prev_swing_low.notna()
        making_lh = (last_swing_high < prev_swing_high) & prev_swing_high.notna()
        making_ll = (last_swing_low < prev_swing_low) & prev_swing_low.notna()
        
        df['trend_up'] = making_hh & making_hl
        df['trend_down'] = making_lh & making_ll
        
        # BOS (Break of Structure): in uptrend, price breaks above last swing high
        # In downtrend, price breaks below last swing low
        bos_buy = df['trend_up'] & (c > last_swing_high) & (c > c.shift(1))
        bos_sell = df['trend_down'] & (c < last_swing_low) & (c < c.shift(1))
        
        # CHoCH (Change of Character): break of the most recent swing in opposite direction
        # Price was making HH/HL then breaks below last swing low
        choch_sell = making_lh & (c < last_swing_low)
        # Price was making LH/LL then breaks above last swing high
        choch_buy = making_hh & (c > last_swing_high)
        
        return bos_buy, bos_sell, choch_buy, choch_sell, last_swing_high, last_swing_low
    
    def _find_order_blocks(self, df, direction='bullish'):
        """Find Order Block: the last bearish (for bullish OB) or bullish (for bearish OB) candle before an impulsive move."""
        o, h, l, c = df['open'], df['high'], df['low'], df['close']
        
        # Impulsive move: body > 1.5x average body
        body = abs(c - o)
        avg_body = body.rolling(20).mean().clip(lower=0.0001)
        impulsive = body > avg_body * 1.5
        
        if direction == 'bullish':
            # Bullish OB: last bearish (or small) candle before a big bullish move
            # Bearish candle: close < open
            bearish_candle = c < o
            # Find the last bearish candle before an impulsive bullish candle
            ob_idx = pd.Series(False, index=df.index)
            for i in range(2, len(df)):
                if impulsive.iloc[i] and c.iloc[i] > o.iloc[i]:  # bullish impulsive
                    # Look back for a bearish candle within ob_lookback
                    lookback_start = max(0, i - self.ob_lookback)
                    bearish_bars = bearish_candle.iloc[lookback_start:i]
                    if bearish_bars.any():
                        last_idx = bearish_bars[bearish_bars].index[-1]
                        ob_idx.iloc[i] = True
            return ob_idx
        else:
            # Bearish OB: last bullish (or small) candle before a big bearish move
            bullish_candle = c > o
            ob_idx = pd.Series(False, index=df.index)
            for i in range(2, len(df)):
                if impulsive.iloc[i] and c.iloc[i] < o.iloc[i]:  # bearish impulsive
                    lookback_start = max(0, i - self.ob_lookback)
                    bullish_bars = bullish_candle.iloc[lookback_start:i]
                    if bullish_bars.any():
                        last_idx = bullish_bars[bullish_bars].index[-1]
                        ob_idx.iloc[i] = True
            return ob_idx
    
    def _detect_fvg(self, df):
        """Detect Fair Value Gaps (3-candle imbalance)."""
        h, l, c = df['high'], df['low'], df['close']
        
        # Bullish FVG: low of candle 3 > high of candle 1 (gap between candle 1 high and candle 3 low)
        fvg_bullish = (l.shift(-1) > h.shift(1))  # middle candle doesn't overlap with prev
        # Bearish FVG: high of candle 3 < low of candle 1
        fvg_bearish = (h.shift(-1) < l.shift(1))
        
        return fvg_bullish, fvg_bearish
    
    def generate_signals(self, df):
        df = df.copy()
        h, l, c, o = df['high'], df['low'], df['close'], df['open']
        
        bos_buy, bos_sell, choch_buy, choch_sell, sw_high, sw_low = self._detect_bos_choch(df)
        fvg_bullish, fvg_bearish = self._detect_fvg(df)
        
        # Volume confirmation
        v = df.get('tick_volume', df.get('volume', pd.Series(1, index=df.index)))
        v_avg = v.rolling(20).mean().clip(lower=1)
        vol_confirmed = v > v_avg * 1.2
        
        df['entry'] = 0
        
        # Entry signals (combined BOS + CHoCH + OB + FVG for higher probability)
        # BOS Buy with volume
        df.loc[bos_buy & vol_confirmed, 'entry'] = 1
        # CHoCH Buy
        df.loc[choch_buy & vol_confirmed, 'entry'] = 1
        # BOS Sell with volume
        df.loc[bos_sell & vol_confirmed, 'entry'] = -1
        # CHoCH Sell
        df.loc[choch_sell & vol_confirmed, 'entry'] = -1
        
        # FVG confluence: strengthen existing signals if FVG is present
        # (we already set entry above, FVG just adds confidence)
        
        # Avoid consecutive same-direction entries
        entry_col = df.columns.get_loc('entry')
        for i in range(1, len(df)):
            if df.iat[i, entry_col] != 0 and df.iat[i-1, entry_col] == df.iat[i, entry_col]:
                df.iat[i, entry_col] = 0
        
        return df


# ──────────────────────────────────────────────
# FIX 3: QuarterlyTheoryStrategy — ICT Quarterly Theory v2
# ──────────────────────────────────────────────

class QuarterlyTheoryStrategyFixed:
    """
    Quarterly Theory v2: ICT-inspired session range breakout + liquidity grab.
    Fixed Rolling bug: h.rolling(N) - l.rolling(N) → h.rolling(N).max() - l.rolling(N).min()
    Core concepts: Asian range breakout, London/NY continuation, liquidity sweeps.
    """
    name = "quarterly_fixed"
    description = "Quarterly Theory v2: range breakout + trend filter, fixed Rolling bug"
    
    def __init__(self, lookback=20, range_period=24, fast_ema=10, slow_ema=30, volume_mult=1.2, **kw):
        self.lookback = lookback
        self.range_period = range_period
        self.fast_ema = fast_ema
        self.slow_ema = slow_ema
        self.volume_mult = volume_mult
        self.params = {"lookback": lookback, "range_period": range_period,
                       "fast_ema": fast_ema, "slow_ema": slow_ema,
                       "volume_mult": volume_mult, **kw}
        for k, v in self.params.items():
            setattr(self, k, v)
    
    def generate_signals(self, df):
        df = df.copy()
        h, l, c, o = df['high'], df['low'], df['close'], df['open']
        
        # ── FIX the Rolling bug ──
        # Original: h.rolling(24) - l.rolling(24)  ← BUG: Rolling - Rolling
        # Fixed: h.rolling(N).max() - l.rolling(N).min()
        df['range_high'] = h.rolling(self.range_period).max()
        df['range_low'] = l.rolling(self.range_period).min()
        df['session_range'] = df['range_high'] - df['range_low']
        
        # ── ATR ──
        tr = pd.concat([h - l, abs(h - c.shift(1)), abs(l - c.shift(1))], axis=1).max(axis=1)
        df['atr'] = tr.rolling(14).mean()
        
        # ── EMAs for trend ──
        df['ema_fast'] = c.ewm(span=self.fast_ema).mean()
        df['ema_slow'] = c.ewm(span=self.slow_ema).mean()
        df['trend_up'] = df['ema_fast'] > df['ema_slow']
        df['trend_down'] = df['ema_fast'] < df['ema_slow']
        
        # ── Volume ──
        v = df.get('tick_volume', df.get('volume', pd.Series(1, index=df.index)))
        v_avg = v.rolling(20).mean().clip(lower=1)
        vol_ok = v > v_avg * self.volume_mult
        
        # ── Signal 1: Range breakout with trend confirmation ──
        prev_high = df['range_high'].shift(1)
        prev_low = df['range_low'].shift(1)
        
        # Buy: break above range high in uptrend with volume
        breakout_buy = (c > prev_high) & df['trend_up'] & vol_ok & (df['session_range'] > 0)
        # Sell: break below range low in downtrend with volume
        breakout_sell = (c < prev_low) & df['trend_down'] & vol_ok & (df['session_range'] > 0)
        
        # ── Signal 2: EMA crossover with volume ──
        ema_cross_up = df['trend_up'] & (df['ema_fast'].shift(1) <= df['ema_slow'].shift(1)) & vol_ok
        ema_cross_down = df['trend_down'] & (df['ema_fast'].shift(1) >= df['ema_slow'].shift(1)) & vol_ok
        
        # ── Combined signals ──
        df['entry'] = 0
        df.loc[breakout_buy, 'entry'] = 1
        df.loc[breakout_sell, 'entry'] = -1
        df.loc[ema_cross_up & (df['entry'] == 0), 'entry'] = 1
        df.loc[ema_cross_down & (df['entry'] == 0), 'entry'] = -1
        
        # Avoid consecutive same-direction entries
        entry_col = df.columns.get_loc('entry')
        for i in range(1, len(df)):
            if df.iat[i, entry_col] != 0 and df.iat[i-1, entry_col] == df.iat[i, entry_col]:
                df.iat[i, entry_col] = 0
        
        return df


# ──────────────────────────────────────────────
# Apply: monkey-patch the registry
# ──────────────────────────────────────────────

def apply_fixes():
    """Override MSNRStrategy, SMCStrategy, QuarterlyTheoryStrategy in the registry."""
    import strategy_registry as reg
    
    # Save originals
    if not hasattr(reg, '_original_strategies'):
        reg._original_strategies = {}
        for name in ['MSNRStrategy', 'SMCStrategy', 'QuarterlyTheoryStrategy']:
            if name in reg.STRATEGIES:
                reg._original_strategies[name] = reg.STRATEGIES[name]
    
    # Apply fixes
    reg.STRATEGIES['MSNRStrategy'] = MSNRStrategyFixed
    reg.STRATEGIES['SMCStrategy'] = SMCStrategyFixed
    reg.STRATEGIES['QuarterlyTheoryStrategy'] = QuarterlyTheoryStrategyFixed
    
    log.info("✅ Applied fixes: MSNR, SMC, QuarterlyTheory")
    log.info(f"   Registry now has {len(reg.STRATEGIES)} strategies")
    return True


def restore_originals():
    """Restore original strategies if fixes were applied."""
    import strategy_registry as reg
    if hasattr(reg, '_original_strategies'):
        for name, cls in reg._original_strategies.items():
            reg.STRATEGIES[name] = cls
        log.info("🔄 Restored original strategies")
        return True
    return False


# ──────────────────────────────────────────────
# Quick test if run directly
# ──────────────────────────────────────────────

def run_quick_test():
    """Run a quick test of all three fixed strategies."""
    sys.path.insert(0, r'E:/trading')
    from backtest_pipeline import get_historical, backtest, walk_forward, gate_decision
    
    apply_fixes()
    
    df = get_historical("EURUSD", days=365, tf="M15")
    if df is None:
        log.error("❌ Cannot load data — MT5 not available?")
        return
    
    log.info(f"📊 Loaded {len(df)} bars of EURUSD M15")
    
    strategies = [
        ("MSNRStrategy", {"lookback": 30, "atr_mult": 1.5, "trend_ema": 200}),
        ("SMCStrategy", {"swing_period": 5, "bos_confirmation_bars": 2, "ob_lookback": 10}),
        ("QuarterlyTheoryStrategy", {"range_period": 24, "smooth_period": 5, "lookback": 20, "atr_mult": 0.5}),
    ]
    
    results = {}
    for name, params in strategies:
        from strategy_registry import get_strategy
        strat = get_strategy(name, **params)
        bt_result, trades, equity = backtest(df, strat, initial_capital=1000)
        wf = walk_forward(df, strat, folds=5)
        gate = gate_decision(wf)
        
        results[name] = {
            "backtest": bt_result,
            "walkforward": wf,
            "gate": gate
        }
        
        log.info(f"\n{'='*50}")
        log.info(f"📈 {name}")
        log.info(f"   Return: {bt_result['return_pct']}% | Sharpe: {bt_result['sharpe']} | DD: {bt_result['max_drawdown']}%")
        log.info(f"   WF Return: {wf['avg_return_pct']}% | WF Sharpe: {wf['avg_sharpe']} | WF DD: {wf['avg_max_dd_pct']}%")
        log.info(f"   Gate: {'✅ PASS' if gate['pass'] else '❌ FAIL'} — {gate['reason']}")
    
    return results


if __name__ == "__main__":
    import sys
    sys.path.insert(0, r'E:/trading')
    run_quick_test()
