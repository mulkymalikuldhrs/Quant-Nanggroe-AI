"""
🌟 ORCHID QUANTUM AI - Data Agent
==================================
Specialized agent for market data collection and processing.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from .base import BaseAgent, AgentMessage, MessageType, AgentState
import asyncio
import aiohttp
import logging


class DataAgent(BaseAgent):
    """Agent responsible for collecting and processing market data."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(
            agent_id="data_agent_001",
            name="Data Agent"
        )
        self.capabilities = [
            "fetch_price_data",
            "fetch_fundamental_data",
            "fetch_crypto_data",
            "fetch_sentiment_data",
            "validate_data",
            "feature_engineering"
        ]
        self.config = config or {}
        self.data_cache: Dict[str, pd.DataFrame] = {}
        self.data_sources = {
            'yahoo': yf,
        }
        self._session = None
        
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the data agent."""
        self.config.update(config)
        self.logger.info("Data Agent initialized")
        return True
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create async session."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session
    
    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute data collection task."""
        task_type = task.get('type', 'fetch')
        
        if task_type == 'fetch':
            return self._execute_fetch(task)
        elif task_type == 'validate':
            return self._execute_validate(task)
        elif task_type == 'feature':
            return self._execute_feature_engineering(task)
        else:
            return {'status': 'error', 'message': f'Unknown task type: {task_type}'}
    
    def _execute_fetch(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute data fetch task."""
        symbols = task.get('symbols', [])
        data_type = task.get('data_type', 'price')
        period = task.get('period', '1y')
        interval = task.get('interval', '1d')
        source = task.get('source', 'yahoo')
        
        results = {}
        
        for symbol in symbols:
            try:
                if data_type == 'price':
                    data = self._fetch_price_data(symbol, period, interval, source)
                elif data_type == 'crypto':
                    data = self._fetch_crypto_data(symbol, period, interval)
                elif data_type == 'forex':
                    data = self._fetch_forex_data(symbol, period, interval)
                else:
                    data = None
                
                if data is not None and not data.empty:
                    results[symbol] = data
                    self.data_cache[f"{source}_{symbol}"] = data
                    
            except Exception as e:
                self.logger.error(f"Error fetching {symbol}: {e}")
                results[symbol] = {'error': str(e)}
        
        return {
            'status': 'success',
            'data': {k: v.to_dict() if isinstance(v, pd.DataFrame) else v 
                    for k, v in results.items()},
            'count': len(results)
        }
    
    def _fetch_price_data(self, symbol: str, period: str, interval: str, 
                          source: str = 'yahoo') -> Optional[pd.DataFrame]:
        """Fetch price data from source."""
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            
            if df.empty:
                # Try with start/end dates
                end_date = datetime.now()
                start_date = end_date - timedelta(days=365)
                df = ticker.history(start=start_date, end=end_date, interval=interval)
            
            return df
        except Exception as e:
            self.logger.error(f"Error fetching price data for {symbol}: {e}")
            return None
    
    def _fetch_crypto_data(self, symbol: str, period: str, 
                          interval: str) -> Optional[pd.DataFrame]:
        """Fetch cryptocurrency data."""
        try:
            # Convert symbol format for yfinance
            if not symbol.endswith('-USD'):
                symbol = f"{symbol}-USD"
            
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            return df
        except Exception as e:
            self.logger.error(f"Error fetching crypto data for {symbol}: {e}")
            return None
    
    def _fetch_forex_data(self, symbol: str, period: str, 
                         interval: str) -> Optional[pd.DataFrame]:
        """Fetch forex data."""
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            return df
        except Exception as e:
            self.logger.error(f"Error fetching forex data for {symbol}: {e}")
            return None
    
    def _execute_validate(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute data validation task."""
        data = task.get('data', {})
        validation_rules = task.get('rules', {
            'no_nulls': True,
            'positive_prices': True,
            'reasonable_range': True,
            'no_duplicates': True
        })
        
        results = {}
        
        for symbol, df_data in data.items():
            if isinstance(df_data, dict):
                df = pd.DataFrame(df_data)
            else:
                df = df_data
            
            validation = self._validate_dataframe(df, validation_rules)
            results[symbol] = validation
        
        return {
            'status': 'success',
            'validation': results
        }
    
    def _validate_dataframe(self, df: pd.DataFrame, 
                           rules: Dict[str, bool]) -> Dict[str, Any]:
        """Validate a dataframe."""
        issues = []
        
        if rules.get('no_nulls', True):
            null_count = df.isnull().sum().sum()
            if null_count > 0:
                issues.append(f"Found {null_count} null values")
        
        if rules.get('positive_prices', True):
            if 'Close' in df.columns:
                negative_prices = (df['Close'] <= 0).sum()
                if negative_prices > 0:
                    issues.append(f"Found {negative_prices} non-positive close prices")
        
        if rules.get('reasonable_range', True):
            if 'Close' in df.columns:
                max_price = df['Close'].max()
                min_price = df['Close'].min()
                if max_price > 1e10 or min_price < 1e-10:
                    issues.append(f"Suspicious price range: {min_price} to {max_price}")
        
        if rules.get('no_duplicates', True):
            duplicates = df.index.duplicated().sum()
            if duplicates > 0:
                issues.append(f"Found {duplicates} duplicate index entries")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'shape': df.shape,
            'date_range': {
                'start': str(df.index.min()) if len(df) > 0 else None,
                'end': str(df.index.max()) if len(df) > 0 else None
            }
        }
    
    def _execute_feature_engineering(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute feature engineering task."""
        data = task.get('data', {})
        features = task.get('features', ['sma', 'ema', 'rsi', 'macd'])
        
        results = {}
        
        for symbol, df_data in data.items():
            if isinstance(df_data, dict):
                df = pd.DataFrame(df_data)
            else:
                df = df_data
            
            feature_df = self._create_features(df, features)
            results[symbol] = feature_df
        
        return {
            'status': 'success',
            'features': {k: v.to_dict() for k, v in results.items()},
            'feature_names': list(results.get(list(results.keys())[0], pd.DataFrame()).columns) if results else []
        }
    
    def _create_features(self, df: pd.DataFrame, 
                        feature_list: List[str]) -> pd.DataFrame:
        """Create technical features."""
        result = df.copy()
        
        # Price-based features
        result['Returns'] = df['Close'].pct_change()
        result['Log_Returns'] = np.log(df['Close'] / df['Close'].shift(1))
        
        # Volatility
        result['Volatility_5'] = df['Close'].pct_change().rolling(5).std()
        result['Volatility_20'] = df['Close'].pct_change().rolling(20).std()
        
        # Moving averages
        if 'sma' in feature_list:
            result['SMA_5'] = df['Close'].rolling(5).mean()
            result['SMA_20'] = df['Close'].rolling(20).mean()
            result['SMA_50'] = df['Close'].rolling(50).mean()
        
        if 'ema' in feature_list:
            result['EMA_5'] = df['Close'].ewm(span=5, adjust=False).mean()
            result['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
        
        # RSI
        if 'rsi' in feature_list:
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            result['RSI_14'] = 100 - (100 / (1 + rs))
        
        # MACD
        if 'macd' in feature_list:
            ema_12 = df['Close'].ewm(span=12, adjust=False).mean()
            ema_26 = df['Close'].ewm(span=26, adjust=False).mean()
            result['MACD'] = ema_12 - ema_26
            result['MACD_Signal'] = result['MACD'].ewm(span=9, adjust=False).mean()
            result['MACD_Hist'] = result['MACD'] - result['MACD_Signal']
        
        # Bollinger Bands
        if 'bollinger' in feature_list:
            result['BB_Upper'] = df['Close'].rolling(20).mean() + (df['Close'].rolling(20).std() * 2)
            result['BB_Lower'] = df['Close'].rolling(20).mean() - (df['Close'].rolling(20).std() * 2)
            result['BB_Width'] = (result['BB_Upper'] - result['BB_Lower']) / df['Close'].rolling(20).mean()
        
        # ATR
        if 'atr' in feature_list:
            high_low = df['High'] - df['Low']
            high_close = np.abs(df['High'] - df['Close'].shift())
            low_close = np.abs(df['Low'] - df['Close'].shift())
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            result['ATR_14'] = tr.rolling(14).mean()
        
        # Volume features
        if 'volume' in feature_list:
            result['Volume_SMA_20'] = df['Volume'].rolling(20).mean()
            result['Volume_Ratio'] = df['Volume'] / result['Volume_SMA_20']
        
        # Stochastic
        if 'stochastic' in feature_list:
            low_14 = df['Low'].rolling(14).min()
            high_14 = df['High'].rolling(14).max()
            result['Stoch_K'] = 100 * (df['Close'] - low_14) / (high_14 - low_14)
            result['Stoch_D'] = result['Stoch_K'].rolling(3).mean()
        
        # ADX
        if 'adx' in feature_list:
            plus_di = 100 * (df['High'].diff().positive() / df['High'].diff().abs().rolling(14).mean())
            minus_di = 100 * (-df['Low'].diff().positive() / df['Low'].diff().abs().rolling(14).mean())
            result['ADX'] = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).rolling(14).mean()
        
        # Drop NaN values
        result = result.dropna()
        
        return result
    
    def _process_message(self, message: AgentMessage) -> None:
        """Process incoming message."""
        if message.msg_type == MessageType.DATA_REQUEST:
            # Handle data request
            task = message.payload
            result = self.execute(task)
            
            response = AgentMessage(
                msg_type=MessageType.DATA_RESPONSE,
                sender_id=self.agent_id,
                receiver_id=message.sender_id,
                payload=result,
                priority=message.priority
            )
            self._deliver_message(response)
        
        elif message.msg_type == MessageType.HEARTBEAT:
            self.heartbeat()
            self.state = AgentState.RUNNING
        
        elif message.msg_type == MessageType.SHUTDOWN:
            self.stop()
    
    def get_cached_data(self, key: str) -> Optional[pd.DataFrame]:
        """Get cached data."""
        return self.data_cache.get(key)
    
    def clear_cache(self, pattern: str = None) -> int:
        """Clear data cache."""
        if pattern:
            keys_to_remove = [k for k in self.data_cache.keys() if pattern in k]
        else:
            keys_to_remove = list(self.data_cache.keys())
        
        for key in keys_to_remove:
            del self.data_cache[key]
        
        return len(keys_to_remove)
    
    def get_data_sources_status(self) -> Dict[str, Any]:
        """Get status of data sources."""
        return {
            'yahoo': {
                'status': 'active',
                'cached_symbols': len(self.data_cache)
            }
        }
