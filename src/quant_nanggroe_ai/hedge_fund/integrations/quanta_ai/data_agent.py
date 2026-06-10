"""
⚡ QUANTA AI - Data Agent
=========================
Specialized agent for market data collection, processing,
validation, and feature engineering.

Features:
- Multi-source data collection (Yahoo, Binance, etc.)
- Real-time and historical data
- Data validation and quality checks
- Feature engineering (50+ technical indicators)
- Data caching and optimization

Author: Quanta AI Team
Version: 2.0.0
"""

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    yf = None

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    aiohttp = None

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from .base import BaseAgent, AgentMessage, MessageType, AgentState, AgentType
import asyncio
import logging
from collections import deque


class DataAgent(BaseAgent):
    """Agent responsible for collecting and processing market data."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(
            agent_id="quanta_data_001",
            name="Data Agent",
            agent_type=AgentType.DATA
        )
        self.capabilities = [
            "fetch_price_data",
            "fetch_crypto_data",
            "fetch_forex_data",
            "fetch_fundamental_data",
            "validate_data",
            "feature_engineering",
            "data_caching",
            "real-time_streaming"
        ]
        self.config = config or {}
        self.data_cache: Dict[str, deque] = {}
        self.cache_max_size = 100  # Max items per symbol
        self._session = None
        self._rate_limit = {"remaining": 100, "reset_time": 0}
        self.last_fetch = {}
        
    def _initialize_impl(self) -> bool:
        """Initialize data agent."""
        self.logger.info("Data Agent initializing...")
        
        # Setup caching
        self.data_cache = {
            'price': deque(maxlen=1000),
            'crypto': deque(maxlen=1000),
            'forex': deque(maxlen=1000)
        }
        
        # Subscribe to messages
        self.subscribe(MessageType.DATA_REQUEST)
        self.subscribe(MessageType.DATA_UPDATE)
        
        self.logger.info("Data Agent initialized")
        return True
    
    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute data collection task."""
        task_type = task.get('type', 'fetch')
        
        if task_type == 'fetch':
            return self._execute_fetch(task)
        elif task_type == 'validate':
            return self._execute_validate(task)
        elif task_type == 'feature':
            return self._execute_feature_engineering(task)
        elif task_type == 'stream':
            return self._execute_stream(task)
        elif task_type == 'get_cached':
            return self._execute_get_cached(task)
        elif task_type == 'clear_cache':
            return self._execute_clear_cache(task)
        else:
            return {
                'status': 'error',
                'message': f'Unknown task type: {task_type}',
                'task_type': task_type
            }
    
    def _execute_fetch(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute data fetch task."""
        symbols = task.get('symbols', [])
        data_type = task.get('data_type', 'price')
        period = task.get('period', '1y')
        interval = task.get('interval', '1d')
        source = task.get('source', 'yahoo')
        start_date = task.get('start')
        end_date = task.get('end')
        
        results = {}
        errors = {}
        
        for symbol in symbols:
            try:
                if data_type == 'price':
                    data = self._fetch_price_data(symbol, period, interval, source, start_date, end_date)
                elif data_type == 'crypto':
                    data = self._fetch_crypto_data(symbol, period, interval, start_date, end_date)
                elif data_type == 'forex':
                    data = self._fetch_forex_data(symbol, period, interval, start_date, end_date)
                elif data_type == 'fundamental':
                    data = self._fetch_fundamental_data(symbol)
                else:
                    data = None
                
                if data is not None and not data.empty:
                    results[symbol] = data
                    cache_key = f"{source}_{symbol}_{data_type}"
                    self._cache_data(cache_key, data)
                else:
                    errors[symbol] = f"No data for {symbol}"
                    
            except Exception as e:
                self.logger.error(f"Error fetching {symbol}: {e}")
                errors[symbol] = str(e)
        
        return {
            'status': 'success' if results else 'warning' if errors else 'error',
            'data': {k: self._dataframe_to_dict(v) for k, v in results.items()},
            'errors': errors,
            'count': len(results),
            'symbols_requested': len(symbols),
            'timestamp': datetime.now().isoformat()
        }
    
    def _fetch_price_data(self, symbol: str, period: str, interval: str,
                         source: str, start_date, end_date) -> Optional[pd.DataFrame]:
        """Fetch price data from source."""
        if not YFINANCE_AVAILABLE:
            self.logger.warning("yfinance not installed. Install with: pip install yfinance")
            return None
            
        try:
            ticker = yf.Ticker(symbol)
            
            if start_date and end_date:
                df = ticker.history(start=start_date, end=end_date, interval=interval)
            else:
                df = ticker.history(period=period, interval=interval)
            
            if df.empty and start_date is None:
                # Try with default date range
                end_dt = datetime.now()
                start_dt = end_dt - timedelta(days=365)
                df = ticker.history(start=start_dt, end=end_dt, interval=interval)
            
            # Add symbol column
            if not df.empty:
                df = df.copy()
                df['Symbol'] = symbol
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error fetching price data for {symbol}: {e}")
            return None
    
    def _fetch_crypto_data(self, symbol: str, period: str,
                          interval: str, start_date, end_date) -> Optional[pd.DataFrame]:
        """Fetch cryptocurrency data."""
        try:
            # Convert symbol format for yfinance
            if not symbol.endswith('-USD') and not symbol.endswith('-USDT'):
                if symbol in ['BTC', 'ETH', 'SOL', 'ADA', 'XRP']:
                    symbol = f"{symbol}-USD"
                else:
                    symbol = f"{symbol}-USD"
            
            return self._fetch_price_data(symbol, period, interval, 'yahoo', start_date, end_date)
            
        except Exception as e:
            self.logger.error(f"Error fetching crypto data for {symbol}: {e}")
            return None
    
    def _fetch_forex_data(self, symbol: str, period: str,
                         interval: str, start_date, end_date) -> Optional[pd.DataFrame]:
        """Fetch forex data."""
        try:
            return self._fetch_price_data(symbol, period, interval, 'yahoo', start_date, end_date)
            
        except Exception as e:
            self.logger.error(f"Error fetching forex data for {symbol}: {e}")
            return None
    
    def _fetch_fundamental_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch fundamental data."""
        if not YFINANCE_AVAILABLE:
            self.logger.warning("yfinance not installed. Install with: pip install yfinance")
            return None
            
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            fundamental_keys = [
                'marketCap', 'peRatio', 'eps', 'dividendYield',
                'beta', 'fiftyTwoWeekHigh', 'fiftyTwoWeekLow',
                'profitMargins', 'revenueGrowth', 'ebitdaMargins',
                'returnOnEquity', 'debtToEquity', 'currentRatio'
            ]
            
            fundamentals = {}
            for key in fundamental_keys:
                if key in info:
                    fundamentals[key] = info[key]
            
            return fundamentals
            
        except Exception as e:
            self.logger.error(f"Error fetching fundamental data for {symbol}: {e}")
            return None
    
    def _execute_validate(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute data validation task."""
        data = task.get('data', {})
        rules = task.get('rules', {
            'no_nulls': True,
            'positive_prices': True,
            'reasonable_range': True,
            'no_duplicates': True,
            'price_continuity': True
        })
        
        results = {}
        
        for symbol, df_data in data.items():
            if isinstance(df_data, dict):
                df = pd.DataFrame(df_data)
            elif isinstance(df_data, pd.DataFrame):
                df = df_data
            else:
                results[symbol] = {'valid': False, 'error': 'Invalid data type'}
                continue
            
            validation = self._validate_dataframe(df, rules)
            results[symbol] = validation
        
        all_valid = all(r.get('valid', False) for r in results.values())
        
        return {
            'status': 'success' if all_valid else 'warning',
            'validation': results,
            'timestamp': datetime.now().isoformat()
        }
    
    def _validate_dataframe(self, df: pd.DataFrame,
                           rules: Dict[str, bool]) -> Dict[str, Any]:
        """Validate a dataframe."""
        issues = []
        warnings = []
        score = 1.0
        
        # Check for nulls
        if rules.get('no_nulls', True):
            null_count = df.isnull().sum().sum()
            if null_count > 0:
                issues.append(f"Found {null_count} null values")
                score -= 0.1
        
        # Check for positive prices
        if rules.get('positive_prices', True) and 'Close' in df.columns:
            negative_prices = (df['Close'] <= 0).sum()
            if negative_prices > 0:
                issues.append(f"Found {negative_prices} non-positive close prices")
                score -= 0.1
        
        # Check for reasonable range
        if rules.get('reasonable_range', True) and 'Close' in df.columns:
            max_price = df['Close'].max()
            min_price = df['Close'].min()
            if max_price > 1e10 or min_price < 1e-10:
                issues.append(f"Suspicious price range: {min_price} to {max_price}")
                score -= 0.1
        
        # Check for duplicates
        if rules.get('no_duplicates', True):
            duplicates = df.index.duplicated().sum()
            if duplicates > 0:
                warnings.append(f"Found {duplicates} duplicate index entries")
                score -= 0.05
        
        # Check for price continuity
        if rules.get('price_continuity', True) and 'Close' in df.columns:
            close = df['Close']
            returns = close.pct_change()
            extreme_returns = (returns.abs() > 0.5).sum()
            if extreme_returns > len(close) * 0.01:
                warnings.append(f"Found {extreme_returns} extreme price jumps")
                score -= 0.05
        
        return {
            'valid': len(issues) == 0,
            'score': max(0, score),
            'issues': issues,
            'warnings': warnings,
            'shape': list(df.shape),
            'date_range': {
                'start': str(df.index.min()) if len(df) > 0 else None,
                'end': str(df.index.max()) if len(df) > 0 else None
            },
            'data_quality': self._calculate_data_quality(df)
        }
    
    def _calculate_data_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate data quality metrics."""
        total_cells = df.shape[0] * df.shape[1]
        non_null = df.notna().sum().sum()
        completeness = non_null / total_cells if total_cells > 0 else 0
        
        return {
            'completeness': f"{completeness:.2%}",
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'columns': list(df.columns)
        }
    
    def _execute_feature_engineering(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute feature engineering task."""
        data = task.get('data', {})
        feature_list = task.get('features', 'all')
        
        results = {}
        
        for symbol, df_data in data.items():
            if isinstance(df_data, dict):
                df = pd.DataFrame(df_data)
            elif isinstance(df_data, pd.DataFrame):
                df = df_data.copy()
            else:
                results[symbol] = {'error': 'Invalid data type'}
                continue
            
            feature_df = self._create_features(df, feature_list)
            results[symbol] = self._dataframe_to_dict(feature_df)
        
        return {
            'status': 'success',
            'features': results,
            'feature_count': len(results.get(list(results.keys())[0], {}).get('columns', [])) if results else 0,
            'timestamp': datetime.now().isoformat()
        }
    
    def _create_features(self, df: pd.DataFrame,
                        feature_list: str) -> pd.DataFrame:
        """Create comprehensive technical features."""
        result = df.copy()
        
        if feature_list == 'all':
            feature_list = [
                'returns', 'log_returns',
                'sma', 'ema', 'wma', 'dema', 'tema',
                'rsi', 'stochastic', 'williams',
                'macd', 'macd_signal', 'macd_hist',
                'bollinger', 'atr', 'kc',
                'adx', 'aroon', 'cci',
                'obv', 'vwap', 'ad',
                'momentum', 'roc', 'tsi',
                'volatility', 'correlation',
                'patterns'
            ]
        
        # Price-based features
        close = result['Close'] if 'Close' in result else result.get('close', result.iloc[:, 0])
        high = result.get('High', result.get('high', close))
        low = result.get('Low', result.get('low', close))
        volume = result.get('Volume', result.get('volume', pd.Series(1, index=close.index)))
        
        # Returns
        if 'returns' in feature_list:
            result['Returns'] = close.pct_change()
            result['Log_Returns'] = np.log(close / close.shift(1))
        
        if 'log_returns' in feature_list and 'Log_Returns' not in result.columns:
            result['Log_Returns'] = np.log(close / close.shift(1))
        
        # Moving Averages
        for period in [5, 10, 20, 50, 100, 200]:
            if 'sma' in feature_list:
                result[f'SMA_{period}'] = close.rolling(period).mean()
            if 'ema' in feature_list:
                result[f'EMA_{period}'] = close.ewm(span=period, adjust=False).mean()
            if 'wma' in feature_list:
                weights = np.arange(1, period + 1)
                result[f'WMA_{period}'] = close.rolling(period).apply(
                    lambda x: np.dot(x, weights) / weights.sum(), raw=True
                )
        
        # Momentum Indicators
        if 'rsi' in feature_list:
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            result['RSI_14'] = 100 - (100 / (1 + rs))
        
        if 'stochastic' in feature_list:
            low_14 = low.rolling(14).min()
            high_14 = high.rolling(14).max()
            result['Stoch_K'] = 100 * (close - low_14) / (high_14 - low_14)
            result['Stoch_D'] = result['Stoch_K'].rolling(3).mean()
        
        if 'williams' in feature_list:
            high_14 = high.rolling(14).max()
            low_14 = low.rolling(14).min()
            result['Williams_%R'] = -100 * (high_14 - close) / (high_14 - low_14)
        
        # MACD
        if 'macd' in feature_list:
            ema_12 = close.ewm(span=12, adjust=False).mean()
            ema_26 = close.ewm(span=26, adjust=False).mean()
            result['MACD'] = ema_12 - ema_26
            result['MACD_Signal'] = result['MACD'].ewm(span=9, adjust=False).mean()
            result['MACD_Hist'] = result['MACD'] - result['MACD_Signal']
        
        # Bollinger Bands
        if 'bollinger' in feature_list:
            sma_20 = close.rolling(20).mean()
            std_20 = close.rolling(20).std()
            result['BB_Upper'] = sma_20 + (std_20 * 2)
            result['BB_Lower'] = sma_20 - (std_20 * 2)
            result['BB_Width'] = (result['BB_Upper'] - result['BB_Lower']) / sma_20
            result['BB_Position'] = (close - result['BB_Lower']) / (result['BB_Upper'] - result['BB_Lower'])
        
        # ATR
        if 'atr' in feature_list:
            high_low = high - low
            high_close = np.abs(high - close.shift())
            low_close = np.abs(low - close.shift())
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            result['ATR_14'] = tr.rolling(14).mean()
            result['ATR_Percent'] = result['ATR_14'] / close * 100
        
        # ADX
        if 'adx' in feature_list:
            plus_dm = high.diff()
            minus_dm = -low.diff()
            plus_dm[plus_dm < 0] = 0
            minus_dm[minus_dm < 0] = 0
            
            tr = pd.concat([high - low, np.abs(high - close.shift()), np.abs(low - close.shift())], axis=1).max(axis=1)
            
            plus_di = 100 * (plus_dm.rolling(14).mean() / tr.rolling(14).mean())
            minus_di = 100 * (minus_dm.rolling(14).mean() / tr.rolling(14).mean())
            
            dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
            result['ADX_14'] = dx.rolling(14).mean()
            result['DI_Plus'] = plus_di
            result['DI_Minus'] = minus_di
        
        # Volume Indicators
        if 'obv' in feature_list:
            obv = (np.sign(close.diff()) * volume).cumsum()
            result['OBV'] = obv
            result['OBV_SMA_10'] = obv.rolling(10).mean()
        
        if 'vwap' in feature_list:
            cumulative_volume = volume.cumsum()
            cumulative_price_volume = (close * volume).cumsum()
            result['VWAP'] = cumulative_price_volume / cumulative_volume
        
        # Volatility
        if 'volatility' in feature_list:
            result['Volatility_5'] = close.pct_change().rolling(5).std()
            result['Volatility_20'] = close.pct_change().rolling(20).std()
            result['Volatility_Ratio'] = result['Volatility_5'] / result['Volatility_20']
        
        # Momentum
        if 'momentum' in feature_list:
            result['Momentum_5'] = close - close.shift(5)
            result['Momentum_10'] = close - close.shift(10)
        
        if 'roc' in feature_list:
            result['ROC_5'] = (close - close.shift(5)) / close.shift(5) * 100
            result['ROC_10'] = (close - close.shift(10)) / close.shift(10) * 100
        
        # Pattern Recognition (simplified)
        if 'patterns' in feature_list:
            result['Higher_High'] = (high > high.shift(1)) & (high > high.shift(2))
            result['Higher_Low'] = (low > low.shift(1)) & (low > low.shift(2))
            result['Lower_High'] = (high < high.shift(1)) & (high < high.shift(2))
            result['Lower_Low'] = (low < low.shift(1)) & (low < low.shift(2))
        
        # Trend Strength
        if 'trend_strength' in feature_list:
            sma_20 = close.rolling(20).mean()
            result['Above_SMA20'] = (close > sma_20).astype(int)
            result['SMA_Slope'] = sma_20.diff(5) / 5
        
        # Drop NaN values
        result = result.dropna()
        
        return result
    
    def _execute_stream(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Start real-time data streaming."""
        symbols = task.get('symbols', [])
        interval = task.get('interval', '1m')
        
        # For now, return streaming configuration
        return {
            'status': 'ready',
            'symbols': symbols,
            'interval': interval,
            'message': 'Real-time streaming configured',
            'note': 'Full streaming requires separate streaming service'
        }
    
    def _execute_get_cached(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Get cached data."""
        pattern = task.get('pattern', None)
        limit = task.get('limit', 10)
        
        cached = {}
        
        for key, data in self.data_cache.items():
            if pattern is None or pattern in key:
                items = list(data)[-limit:]
                cached[key] = [self._dataframe_to_dict(d) if hasattr(d, 'to_dict') else str(d) for d in items]
        
        return {
            'status': 'success',
            'cached_items': len(cached),
            'data': cached
        }
    
    def _execute_clear_cache(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Clear data cache."""
        pattern = task.get('pattern', None)
        
        if pattern:
            keys_to_remove = [k for k in self.data_cache.keys() if pattern in k]
            for key in keys_to_remove:
                self.data_cache[key].clear()
        else:
            for key in self.data_cache:
                self.data_cache[key].clear()
        
        return {
            'status': 'success',
            'cleared': pattern or 'all'
        }
    
    def _cache_data(self, key: str, data: Any) -> None:
        """Cache data with key."""
        if key not in self.data_cache:
            self.data_cache[key] = deque(maxlen=self.cache_max_size)
        self.data_cache[key].append(data)
    
    def _dataframe_to_dict(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Convert dataframe to dictionary."""
        return {
            'columns': list(df.columns),
            'index': [str(idx) for idx in df.index],
            'data': df.values.tolist(),
            'shape': list(df.shape)
        }
    
    def _process_message(self, message: AgentMessage) -> bool:
        """Process incoming message."""
        if message.msg_type == MessageType.DATA_REQUEST:
            task = message.payload
            result = self.execute(task)
            
            response = AgentMessage(
                msg_type=MessageType.DATA_RESPONSE,
                sender_id=self.agent_id,
                receiver_id=message.sender_id,
                payload=result,
                priority=message.priority,
                correlation_id=message.correlation_id
            )
            return self.send_message(response)
        
        elif message.msg_type == MessageType.HEARTBEAT:
            self.heartbeat()
            self.state = AgentState.RUNNING
        
        elif message.msg_type == MessageType.SHUTDOWN:
            self.shutdown()
        
        return True
    
    def get_data_sources_status(self) -> Dict[str, Any]:
        """Get status of data sources."""
        return {
            'yahoo': {
                'status': 'active',
                'cached_symbols': len([k for k in self.data_cache.keys() if 'yahoo' in k])
            },
            'cache_size': sum(len(v) for v in self.data_cache.values())
        }
