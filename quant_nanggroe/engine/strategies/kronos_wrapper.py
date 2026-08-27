"""
Kronos Wrapper — Financial Foundation Model Signal Provider
Provider #10 untuk Hedge Fund Pipeline

Integrasi Kronos (AAAI 2026) sebagai signal provider:
- Zero-shot price forecasting via hierarchical tokenization
- Signals based on predicted price direction (OHLCV)
- Falls back to classical momentum when model unavailable

Architecture:
    OHLCV → BSQuantizer → Hierarchical Tokens → Transformer → Price Forecast → Signal
"""
import logging
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from quant_nanggroe.engine.strategies._df_signal_adapter import DFStrategyAdapter
from quant_nanggroe.engine.strategies.base import Strategy
from quant_nanggroe.engine.strategies.registry import StrategyRegistry

log = logging.getLogger('kronos')

# ─── Attempt Kronos import ─────────────────────────────────────────────────────
# ponytail: the real Kronos model package lives at quant_nanggroe/external/kronos and is OPTIONAL.
# The previous bare `from model import ...` raised NameError (safetensors
# undefined inside the half-installed package) which the `except ImportError`
# did NOT catch — so every signal call logged a crash and fell back. Widen the
# guard to Exception and skip the path insertion unless the dir actually exists.
KRONOS_AVAILABLE = False
_KRONOS_DIR = str(Path(__file__).resolve().parent.parent.parent / 'external' / 'kronos')
if os.path.isdir(_KRONOS_DIR):
    try:
        sys.path.insert(0, _KRONOS_DIR)
        from model import Kronos, KronosPredictor, KronosTokenizer
        KRONOS_AVAILABLE = True
        log.info("Kronos model package loaded")
    except Exception as e:
        KRONOS_AVAILABLE = False
        log.warning(f"Kronos not available ({e}) — using fallback mode")
else:
    log.info("Kronos dir %s absent — using fallback momentum mode", _KRONOS_DIR)

# ─── Fallback: momentum-based signal when Kronos model not loaded ──────────────
class _FallbackKronosPredictor:
    """Lightweight fallback that simulates Kronos-like signal using momentum + volatility."""
    def __init__(self):
        self.price_cols = ['open', 'high', 'low', 'close']
    
    def predict(self, df, x_timestamp, y_timestamp, pred_len=10, **kw):
        """Generate synthetic prediction based on recent trend + volatility."""
        c = df['close'].values
        if len(c) < 50:
            return pd.DataFrame(0, index=y_timestamp, columns=self.price_cols + ['volume', 'amount'])
        
        # Recent momentum (last 20 bars)
        mom_short = c[-1] / c[-5] - 1 if len(c) >= 5 else 0
        mom_med = c[-1] / c[-20] - 1 if len(c) >= 20 else 0
        mom_long = c[-1] / c[-50] - 1 if len(c) >= 50 else 0
        
        # Volatility estimate
        returns = np.diff(c) / c[:-1]
        vol = np.std(returns[-20:]) if len(returns) >= 20 else 0.001
        
        # Bias: weighted momentum
        bias = mom_short * 0.5 + mom_med * 0.3 + mom_long * 0.2
        
        # Generate forecast with momentum drift
        last_close = c[-1]
        forecast = pd.DataFrame(index=range(pred_len), columns=self.price_cols + ['volume', 'amount'])
        forecast['close'] = last_close * (1 + bias * np.linspace(0.001, 0.01, pred_len))
        forecast['open'] = forecast['close'] * (1 + np.random.randn(pred_len) * vol * 0.3)
        forecast['high'] = forecast[['open', 'close']].max(axis=1) * (1 + np.abs(np.random.randn(pred_len)) * vol)
        forecast['low'] = forecast[['open', 'close']].min(axis=1) * (1 - np.abs(np.random.randn(pred_len)) * vol)
        forecast['volume'] = 0
        forecast['amount'] = 0
        forecast.index = y_timestamp
        return forecast


@StrategyRegistry.register
class KronosSignalProvider(DFStrategyAdapter, Strategy):
    """
    Kronos Signal Provider — Provider #10 dalam Hedge Fund.
    
    Menggunakan Kronos financial foundation model untuk:
    1. Forecast OHLCV harga N bar ke depan
    2. Hitung expected return dari forecast
    3. Generate buy/sell/neutral berdasarkan magnitude expected return
    
    Parameters:
        model_name: Nama model HuggingFace (default: NeoQuasar/Kronos-small)
        tokenizer_name: Nama tokenizer HuggingFace (default: NeoQuasar/Kronos-Tokenizer-base)
        lookback: Jumlah bar historical untuk context (max 512)
        pred_len: Jumlah bar forecast ke depan
        signal_threshold: Minimum expected return % untuk trigger signal
        ensemble_count: Jumlah sample untuk averaging
        fallback_momentum: Gunakan momentum fallback jika model tak tersedia
    """
    name = "kronos"
    description = "Kronos Financial Foundation Model — Provider #10 (AAAI 2026)"
    
    def __init__(self, parameters=None, 
                 model_name="NeoQuasar/Kronos-small",
                 tokenizer_name="NeoQuasar/Kronos-Tokenizer-base",
                 lookback=200, 
                 pred_len=10,
                 signal_threshold=0.0015,  # 0.15% minimum move
                 ensemble_count=3,
                 fallback_momentum=True,
                 **kw):
        super().__init__(parameters=None,
            model_name=model_name,
            tokenizer_name=tokenizer_name,
            lookback=lookback,
            pred_len=pred_len,
            signal_threshold=signal_threshold,
            ensemble_count=ensemble_count,
            fallback_momentum=fallback_momentum,
            **kw
        )
        self._predictor = None
        self._initialized = False
    
    def _init_model(self):
        """Initialize Kronos predictor lazily."""
        if self._initialized:
            return
        
        self._initialized = True
        
        if KRONOS_AVAILABLE:
            try:
                import torch
                device = "cuda:0" if torch.cuda.is_available() else "cpu"
                log.info(f"Loading Kronos model on {device}...")
                
                tokenizer = KronosTokenizer.from_pretrained(self.tokenizer_name)
                model = Kronos.from_pretrained(self.model_name)
                
                self._predictor = KronosPredictor(
                    model, tokenizer, 
                    max_context=min(self.lookback, 512),
                    device=device
                )
                log.info(f"✅ Kronos model loaded: {self.model_name}")
            except Exception as e:
                log.warning(f"Kronos load failed ({e}) — using fallback")
                if self.fallback_momentum:
                    self._predictor = _FallbackKronosPredictor()
                else:
                    self._predictor = None
        elif self.fallback_momentum:
            log.info("Using Kronos fallback predictor (momentum-based)")
            self._predictor = _FallbackKronosPredictor()
    
    def generate_signals(self, df):
        """
        Generate trading signals berdasarkan Kronos price forecast.
        
        Strategy:
        1. Ambil N bar terakhir sebagai context (lookback)
        2. Forecast harga N bar ke depan (pred_len)
        3. Hitung expected return = (forecast_close - last_close) / last_close
        4. Signal threshold: expected return > threshold → buy, < -threshold → sell
        
        Returns:
            df dengan kolom 'entry' (1=buy, -1=sell, 0=neutral)
        """
        self._init_model()
        df = df.copy()
        df['entry'] = 0
        
        if self._predictor is None:
            log.warning("No predictor available — all neutral")
            return df
        
        n = len(df)
        if n < self.lookback + self.pred_len:
            log.warning(f"Not enough bars: {n} < {self.lookback + self.pred_len}")
            return df
        
        # Prepare input: last lookback bars
        lookback = min(self.lookback, n - self.pred_len)
        x_df = df.iloc[-lookback-self.pred_len:-self.pred_len]
        y_len = self.pred_len
        
        # Ensure we have all required columns
        req_cols = ['open', 'high', 'low', 'close']
        if not all(c in x_df.columns for c in req_cols):
            log.warning(f"Missing columns: {req_cols}")
            return df
        
        # Fill optional columns
        x_filled = x_df.copy()
        if 'volume' not in x_filled.columns:
            x_filled['volume'] = 0
        if 'amount' not in x_filled.columns:
            x_filled['amount'] = 0
        
        # Timestamps
        x_timestamp = pd.Series(x_filled.index)
        y_idx = df.index[-self.pred_len:]
        y_timestamp = pd.Series(y_idx)
        
        try:
            # Predict
            pred_df = self._predictor.predict(
                x_filled[['open', 'high', 'low', 'close', 'volume', 'amount']],
                x_timestamp=x_timestamp,
                y_timestamp=y_timestamp,
                pred_len=y_len,
                T=0.8,
                top_p=0.9,
                sample_count=self.ensemble_count,
                verbose=False
            )
            
            # Calculate expected return from forecast
            last_close = x_filled['close'].iloc[-1]
            forecast_close = pred_df['close'].values
            
            # Signal per forecast bar, then aggregate
            for i in range(min(y_len, len(forecast_close))):
                expected_ret = (forecast_close[i] - last_close) / last_close
                
                if expected_ret > self.signal_threshold:
                    df.loc[df.index[-y_len + i], 'entry'] = 1
                elif expected_ret < -self.signal_threshold:
                    df.loc[df.index[-y_len + i], 'entry'] = -1
            
        except Exception as e:
            log.error(f"Prediction error: {e}")
        
        return df


@StrategyRegistry.register
class KronosEnsembleStrategy(DFStrategyAdapter, Strategy):
    """
    Kronos Ensemble — Multi-timeframe Kronos signals + momentum confirmation.
    Menggabungkan Kronos forecast dengan teknikal konfirmasi untuk sinyal lebih akurat.
    """
    name = "kronos_ensemble"
    description = "Kronos Ensemble: Kronos forecast + trend + volatility filter"
    
    def __init__(self, parameters=None, 
                 lookback=200, pred_len=10, 
                 signal_threshold=0.002,
                 trend_filter=True,
                 vol_filter=True,
                 **kw):
        super().__init__(parameters=None,
            lookback=lookback, pred_len=pred_len,
            signal_threshold=signal_threshold,
            trend_filter=trend_filter,
            vol_filter=vol_filter,
            **kw
        )
        self._kronos = KronosSignalProvider(
            lookback=lookback, pred_len=pred_len,
            signal_threshold=signal_threshold
        )
    
    def generate_signals(self, df):
        """Generate Kronos signals + EMA trend confirmation + volatility filter."""
        df = df.copy()
        df['entry'] = 0
        
        # Get Kronos base signals
        kronos_df = self._kronos.generate_signals(df.copy())
        
        # Trend filter: EMA20/50
        ema20 = df['close'].ewm(span=20).mean()
        ema50 = df['close'].ewm(span=50).mean()
        trend_up = ema20 > ema50
        trend_down = ema20 < ema50
        
        # Volatility filter: skip if ATR > 2x recent ATR mean (chaotic)
        atr = pd.concat([
            df['high'] - df['low'],
            (df['high'] - df['close'].shift(1)).abs(),
            (df['low'] - df['close'].shift(1)).abs()
        ], axis=1).max(axis=1)
        atr_mean = atr.rolling(20).mean()
        chaos = atr > atr_mean * 2.0
        
        # Combine: Kronos signal + trend agreement + no chaos
        for i in range(len(df)):
            ks = kronos_df['entry'].iloc[i]
            if ks == 0:
                continue
            if chaos.iloc[i]:
                continue
            if self.trend_filter:
                if ks == 1 and not trend_up.iloc[i]:
                    continue
                if ks == -1 and not trend_down.iloc[i]:
                    continue
            df.loc[df.index[i], 'entry'] = ks
        
        return df


# ─── Test / Backtest ───────────────────────────────────────────────────────────
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
    
    print("=== Kronos Wrapper Test ===\n")
    
    # Generate dummy OHLCV data
    np.random.seed(42)
    n = 1000
    dates = pd.date_range('2025-01-01', periods=n, freq='15min')
    
    price = 100.0
    prices = []
    for _ in range(n):
        price += np.random.randn() * 0.1
        prices.append(price)
    
    df = pd.DataFrame({
        'open': prices,
        'high': np.array(prices) + np.abs(np.random.randn(n) * 0.15),
        'low': np.array(prices) - np.abs(np.random.randn(n) * 0.15),
        'close': np.array(prices) + np.random.randn(n) * 0.05,
        'volume': np.abs(np.random.randn(n) * 100 + 1000),
    }, index=dates)
    df['high'] = df[['open', 'close', 'high']].max(axis=1)
    df['low'] = df[['open', 'close', 'low']].min(axis=1)
    
    # Test KronosSignalProvider
    strat = KronosSignalProvider(lookback=200, pred_len=5)
    result = strat.generate_signals(df)
    signals = result['entry'].value_counts()
    print(f"KronosSignalProvider signals: {signals.to_dict()}")
    print(f"  Total bars: {len(result)}, signals: {(result['entry'] != 0).sum()}")
    
    # Test KronosEnsembleStrategy
    strat2 = KronosEnsembleStrategy(lookback=200, pred_len=5)
    result2 = strat2.generate_signals(df)
    signals2 = result2['entry'].value_counts()
    print(f"\nKronosEnsembleStrategy signals: {signals2.to_dict()}")
    print(f"  Total bars: {len(result2)}, signals: {(result2['entry'] != 0).sum()}")
    
    print("\n✅ Kronos Wrapper ready")
