"""
⚡ QUANTA AI - Cognitive Analyst Agent
======================================
Advanced market analysis with technical analysis,
pattern recognition, and regime detection.

Features:
- Technical indicator analysis
- Chart pattern recognition
- Market regime detection
- Multi-timeframe analysis
- Anomaly detection

Author: Quanta AI Team
Version: 2.0.0
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from scipy import stats
from scipy.signal import argrelextrema, find_peaks
from .base import BaseAgent, AgentMessage, MessageType, AgentState, AgentType
import logging


class AnalystAgent(BaseAgent):
    """Agent responsible for comprehensive market analysis."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(
            agent_id="quanta_cognitive_001",
            name="Cognitive Analyst",
            agent_type=AgentType.COGNITIVE
        )
        self.capabilities = [
            "technical_analysis",
            "pattern_recognition",
            "regime_detection",
            "momentum_analysis",
            "mean_reversion_signals",
            "anomaly_detection",
            "multi_timeframe",
            "correlation_analysis"
        ]
        self.config = config or {}
        self.analysis_cache: Dict[str, Dict[str, Any]] = {}
        
    def _initialize_impl(self) -> bool:
        """Initialize analyst agent."""
        self.logger.info("Cognitive Analyst initializing...")
        self.subscribe(MessageType.ANALYSIS_REQUEST)
        self.subscribe(MessageType.DATA_RESPONSE)
        self.logger.info("Cognitive Analyst initialized")
        return True
    
    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute analysis task."""
        task_type = task.get('type', 'analyze')
        
        if task_type == 'technical':
            return self._technical_analysis(task)
        elif task_type == 'fundamental':
            return self._fundamental_analysis(task)
        elif task_type == 'pattern':
            return self._pattern_recognition(task)
        elif task_type == 'regime':
            return self._regime_detection(task)
        elif task_type == 'anomaly':
            return self._anomaly_detection(task)
        elif task_type == 'comprehensive':
            return self._comprehensive_analysis(task)
        elif task_type == 'multi_timeframe':
            return self._multi_timeframe_analysis(task)
        elif task_type == 'correlation':
            return self._correlation_analysis(task)
        else:
            return {
                'status': 'error',
                'message': f'Unknown task type: {task_type}',
                'task_type': task_type
            }
    
    def _technical_analysis(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Perform technical analysis."""
        data = task.get('data', {})
        symbols = task.get('symbols', [])
        
        results = {}
        
        for symbol in symbols:
            if symbol in data:
                df = data[symbol]
                if isinstance(df, dict):
                    df = pd.DataFrame(df)
                
                analysis = self._analyze_symbol_technicals(df, symbol)
                results[symbol] = analysis
        
        return {
            'status': 'success',
            'analysis': results,
            'timestamp': datetime.now().isoformat()
        }
    
    def _analyze_symbol_technicals(self, df: pd.DataFrame,
                                   symbol: str) -> Dict[str, Any]:
        """Analyze a single symbol technically."""
        if len(df) < 2:
            return {'error': 'Insufficient data'}
        
        latest = df.iloc[-1] if len(df) > 0 else {}
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        current_price = float(latest.get('Close', latest.get('close', 0)))
        prev_price = float(prev.get('Close', prev.get('close', 0)))
        
        analysis = {
            'symbol': symbol,
            'current_price': current_price,
            'change': current_price - prev_price,
            'change_pct': ((current_price / prev_price) - 1) * 100 if prev_price > 0 else 0,
            'indicators': {},
            'signals': {},
            'scores': {},
            'recommendation': 'HOLD'
        }
        
        # RSI Analysis
        rsi = latest.get('RSI_14', 50)
        if rsi < 30:
            rsi_signal = 'oversold'
            rsi_score = 1
        elif rsi > 70:
            rsi_signal = 'overbought'
            rsi_score = -1
        else:
            rsi_signal = 'neutral'
            rsi_score = (rsi - 50) / 20  # -1 to 1 scale
        
        analysis['indicators']['rsi'] = {
            'value': float(rsi),
            'signal': rsi_signal,
            'score': float(rsi_score)
        }
        analysis['signals']['rsi'] = rsi_signal
        analysis['scores']['rsi'] = rsi_score
        
        # Trend Analysis
        trend_analysis = self._analyze_trend(df, latest)
        analysis['indicators']['trend'] = trend_analysis
        analysis['signals']['trend'] = trend_analysis.get('signal', 'sideways')
        analysis['scores']['trend'] = trend_analysis.get('score', 0)
        
        # MACD Analysis
        macd = latest.get('MACD', 0)
        macd_signal = latest.get('MACD_Signal', 0)
        macd_hist = latest.get('MACD_Hist', 0)
        prev_hist = prev.get('MACD_Hist', 0)
        
        if macd_hist > 0 and macd_hist > prev_hist:
            macd_signal_name = 'bullish_momentum'
            macd_score = 1
        elif macd_hist < 0 and macd_hist < prev_hist:
            macd_signal_name = 'bearish_momentum'
            macd_score = -1
        elif macd > macd_signal:
            macd_signal_name = 'bullish'
            macd_score = 0.5
        else:
            macd_signal_name = 'bearish'
            macd_score = -0.5
        
        analysis['indicators']['macd'] = {
            'macd': float(macd),
            'signal': float(macd_signal),
            'histogram': float(macd_hist),
            'signal_name': macd_signal_name,
            'score': float(macd_score)
        }
        analysis['signals']['macd'] = macd_signal_name
        analysis['scores']['macd'] = macd_score
        
        # Bollinger Bands Analysis
        bb_analysis = self._analyze_bollinger(latest, current_price)
        analysis['indicators']['bollinger'] = bb_analysis
        analysis['signals']['bollinger'] = bb_analysis.get('signal', 'neutral')
        analysis['scores']['bollinger'] = bb_analysis.get('score', 0)
        
        # Stochastic Analysis
        stoch_k = latest.get('Stoch_K', 50)
        stoch_d = latest.get('Stoch_D', 50)
        stoch_analysis = self._analyze_stochastic(stoch_k, stoch_d)
        analysis['indicators']['stochastic'] = stoch_analysis
        analysis['signals']['stochastic'] = stoch_analysis.get('signal', 'neutral')
        analysis['scores']['stochastic'] = stoch_analysis.get('score', 0)
        
        # Volume Analysis
        vol_analysis = self._analyze_volume(latest)
        analysis['indicators']['volume'] = vol_analysis
        analysis['signals']['volume'] = vol_analysis.get('signal', 'normal')
        
        # Volatility Analysis
        vol_analysis = self._analyze_volatility(latest)
        analysis['indicators']['volatility'] = vol_analysis
        
        # Support/Resistance
        sr_levels = self._find_support_resistance(df)
        analysis['indicators']['support_resistance'] = sr_levels
        
        # Calculate overall score
        scores = analysis.get('scores', {})
        if scores:
            overall_score = np.mean(list(scores.values()))
            analysis['overall_score'] = float(overall_score)
            
            # Generate recommendation
            if overall_score > 0.3:
                analysis['recommendation'] = 'STRONG_BUY'
            elif overall_score > 0.1:
                analysis['recommendation'] = 'BUY'
            elif overall_score < -0.3:
                analysis['recommendation'] = 'STRONG_SELL'
            elif overall_score < -0.1:
                analysis['recommendation'] = 'SELL'
            else:
                analysis['recommendation'] = 'HOLD'
        
        return analysis
    
    def _analyze_trend(self, df: pd.DataFrame, latest: pd.Series) -> Dict[str, Any]:
        """Analyze trend direction and strength."""
        close = df['Close'] if 'Close' in df else df.iloc[:, 0]
        
        sma_5 = latest.get('SMA_5', close.rolling(5).mean().iloc[-1])
        sma_20 = latest.get('SMA_20', close.rolling(20).mean().iloc[-1])
        sma_50 = latest.get('SMA_50', close.rolling(50).mean().iloc[-1])
        sma_200 = latest.get('SMA_200', close.rolling(200).mean().iloc[-1]) if len(close) > 200 else sma_50
        
        current_price = latest.get('Close', close.iloc[-1])
        
        # Count trend signals
        trend_scores = []
        
        if sma_5 > sma_20:
            trend_scores.append(1)
        elif sma_5 < sma_20:
            trend_scores.append(-1)
        
        if sma_20 > sma_50:
            trend_scores.append(1)
        elif sma_20 < sma_50:
            trend_scores.append(-1)
        
        if sma_50 > sma_200:
            trend_scores.append(1)
        elif sma_50 < sma_200:
            trend_scores.append(-1)
        
        if current_price > sma_50:
            trend_scores.append(1)
        elif current_price < sma_50:
            trend_scores.append(-1)
        
        # Calculate slope
        x = np.arange(min(20, len(close)))
        y = close.tail(20).values
        if len(y) > 1:
            slope, _, r_value, _, _ = stats.linregress(x, y)
            if slope > 0 and r_value > 0.8:
                trend_scores.append(1)
            elif slope < 0 and r_value > 0.8:
                trend_scores.append(-1)
        
        trend_score = np.mean(trend_scores) if trend_scores else 0
        
        if trend_score > 0.3:
            signal = 'strong_bullish'
        elif trend_score > 0.1:
            signal = 'bullish'
        elif trend_score < -0.3:
            signal = 'strong_bearish'
        elif trend_score < -0.1:
            signal = 'bearish'
        else:
            signal = 'sideways'
        
        return {
            'sma_5': float(sma_5),
            'sma_20': float(sma_20),
            'sma_50': float(sma_50),
            'sma_200': float(sma_200),
            'price_vs_sma50': float((current_price / sma_50 - 1) * 100),
            'signal': signal,
            'score': float(trend_score),
            'strength': abs(trend_score)
        }
    
    def _analyze_bollinger(self, latest: pd.Series, current_price: float) -> Dict[str, Any]:
        """Analyze Bollinger Bands position."""
        bb_upper = latest.get('BB_Upper', 0)
        bb_lower = latest.get('BB_Lower', 0)
        bb_position = latest.get('BB_Position', 0.5)
        
        if bb_upper > 0 and bb_lower > 0:
            if bb_position > 0.9:
                signal = 'overbought'
                score = -1
            elif bb_position < 0.1:
                signal = 'oversold'
                score = 1
            elif bb_position > 0.7:
                signal = 'bullish'
                score = 0.5
            elif bb_position < 0.3:
                signal = 'bearish'
                score = -0.5
            else:
                signal = 'neutral'
                score = 0
        else:
            signal = 'unknown'
            score = 0
            bb_position = 0.5
        
        return {
            'upper': float(bb_upper),
            'lower': float(bb_lower),
            'middle': float(latest.get('SMA_20', (bb_upper + bb_lower) / 2)),
            'position': float(bb_position),
            'width': float(latest.get('BB_Width', 0)),
            'signal': signal,
            'score': score
        }
    
    def _analyze_stochastic(self, k: float, d: float) -> Dict[str, Any]:
        """Analyze Stochastic oscillator."""
        if k < 20 and d < 20:
            signal = 'oversold'
            score = 1
        elif k > 80 and d > 80:
            signal = 'overbought'
            score = -1
        elif k > d and k < 80:
            signal = 'bullish_crossover'
            score = 0.5
        elif k < d and k > 20:
            signal = 'bearish_crossover'
            score = -0.5
        else:
            signal = 'neutral'
            score = 0
        
        return {
            'k': float(k),
            'd': float(d),
            'signal': signal,
            'score': score
        }
    
    def _analyze_volume(self, latest: pd.Series) -> Dict[str, Any]:
        """Analyze volume patterns."""
        vol_ratio = latest.get('Volume_Ratio', 1)
        vol_sma = latest.get('Volume_SMA_20', 1)
        
        if vol_ratio > 2:
            signal = 'high_volume'
            score = 0.5 if vol_ratio > 0 else -0.5
        elif vol_ratio < 0.5:
            signal = 'low_volume'
            score = 0
        else:
            signal = 'normal'
            score = 0
        
        # Check for volume confirmation
        change_pct = latest.get('Change_Pct', 0)
        if change_pct > 0 and vol_ratio > 1.5:
            score += 0.3  # Bullish confirmation
        elif change_pct < 0 and vol_ratio > 1.5:
            score -= 0.3  # Bearish confirmation
        
        return {
            'ratio': float(vol_ratio),
            'sma_20': float(vol_sma),
            'signal': signal,
            'score': float(max(-1, min(1, score)))
        }
    
    def _analyze_volatility(self, latest: pd.Series) -> Dict[str, Any]:
        """Analyze volatility levels."""
        vol_5 = latest.get('Volatility_5', 0)
        vol_20 = latest.get('Volatility_20', 0)
        atr_pct = latest.get('ATR_Percent', 0)
        
        vol_percentile = vol_20 * 100 if vol_20 else 0
        
        if vol_percentile > 2:
            vol_signal = 'high'
        elif vol_percentile < 0.5:
            vol_signal = 'low'
        else:
            vol_signal = 'normal'
        
        return {
            'volatility_5d': float(vol_5 * 100),
            'volatility_20d': float(vol_20 * 100),
            'atr_percent': float(atr_pct),
            'signal': vol_signal,
            'regime': 'volatile' if vol_percentile > 1.5 else 'calm'
        }
    
    def _find_support_resistance(self, df: pd.DataFrame, window: int = 20) -> Dict[str, Any]:
        """Find support and resistance levels."""
        high = df['High'].tail(window)
        low = df['Low'].tail(window)
        close = df['Close'].tail(window)
        
        # Find local maxima and minima
        local_max_idx = argrelextrema(close.values, np.greater, order=5)[0]
        local_min_idx = argrelextrema(close.values, np.less, order=5)[0]
        
        resistance_levels = [float(high.iloc[i]) for i in local_max_idx if len(high) > i]
        support_levels = [float(low.iloc[i]) for i in local_min_idx if len(low) > i]
        
        # Add recent high/low
        resistance_levels.append(float(high.max()))
        support_levels.append(float(low.min()))
        
        # Cluster nearby levels
        resistance_levels = self._cluster_levels(resistance_levels)
        support_levels = self._cluster_levels(support_levels)
        
        return {
            'resistance': sorted(resistance_levels, reverse=True)[:3],
            'support': sorted(support_levels)[:3],
            'pivot_point': float((high.max() + low.min() + close.iloc[-1]) / 3)
        }
    
    def _cluster_levels(self, levels: List[float], threshold: float = 0.02) -> List[float]:
        """Cluster nearby price levels."""
        if not levels:
            return []
        
        sorted_levels = sorted(set(levels))
        clustered = [sorted_levels[0]]
        
        for level in sorted_levels[1:]:
            if level / clustered[-1] - 1 < threshold:
                # Average with previous level
                clustered[-1] = (clustered[-1] + level) / 2
            else:
                clustered.append(level)
        
        return clustered
    
    def _pattern_recognition(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Recognize chart patterns."""
        data = task.get('data', {})
        symbols = task.get('symbols', [])
        
        results = {}
        
        for symbol in symbols:
            if symbol in data:
                df = data[symbol]
                if isinstance(df, dict):
                    df = pd.DataFrame(df)
                
                patterns = self._detect_patterns(df)
                results[symbol] = {
                    'patterns': patterns,
                    'pattern_count': len(patterns),
                    'confidence': np.mean([p['confidence'] for p in patterns]) if patterns else 0
                }
        
        return {
            'status': 'success',
            'patterns': results,
            'timestamp': datetime.now().isoformat()
        }
    
    def _detect_patterns(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect chart patterns in price data."""
        patterns = []
        
        if len(df) < 30:
            return patterns
        
        close = df['Close'].values
        high = df['High'].values
        low = df['Low'].values
        
        # Detect local extrema
        local_max = argrelextrema(close, np.greater, order=5)[0]
        local_min = argrelextrema(close, np.less, order=5)[0]
        
        # Double Top
        if len(local_max) >= 2:
            max_prices = close[local_max]
            if len(max_prices) >= 2:
                last_two_max = max_prices[-2:]
                if abs(last_two_max[-1] - last_two_max[-2]) / last_two_max[-2] < 0.03:
                    patterns.append({
                        'pattern': 'double_top',
                        'confidence': 0.75,
                        'direction': 'bearish',
                        'description': 'Two peaks at similar price level'
                    })
        
        # Double Bottom
        if len(local_min) >= 2:
            min_prices = close[local_min]
            if len(min_prices) >= 2:
                last_two_min = min_prices[-2:]
                if abs(last_two_min[-1] - last_two_min[-2]) / last_two_min[-2] < 0.03:
                    patterns.append({
                        'pattern': 'double_bottom',
                        'confidence': 0.75,
                        'direction': 'bullish',
                        'description': 'Two troughs at similar price level'
                    })
        
        # Head and Shoulders (simplified)
        if len(local_max) >= 3:
            max_prices = close[local_max]
            if len(max_prices) >= 3:
                if (max_prices[-3] > max_prices[-2] and max_prices[-1] < max_prices[-2]) or \
                   (max_prices[-3] < max_prices[-2] and max_prices[-1] > max_prices[-2]):
                    patterns.append({
                        'pattern': 'head_shoulders',
                        'confidence': 0.65,
                        'direction': 'bearish',
                        'description': 'Head and shoulders pattern detected'
                    })
        
        # Trend Line
        x = np.arange(len(close))
        slope, _, r_value, _, _ = stats.linregress(x, close)
        
        if abs(r_value) > 0.85:
            direction = 'bullish' if slope > 0 else 'bearish'
            patterns.append({
                'pattern': 'trend_line',
                'confidence': abs(r_value),
                'direction': direction,
                'description': f'Strong {direction} trend line'
            })
        
        # Triangle Pattern
        highs = df['High'].rolling(5).max()
        lows = df['Low'].rolling(5).min()
        high_range = highs.diff()
        low_range = lows.diff()
        
        if len(high_range) > 10:
            high_trend = np.polyfit(range(10), high_range.tail(10).values, 1)[0]
            low_trend = np.polyfit(range(10), low_range.tail(10).values, 1)[0]
            
            if abs(high_trend) < 0.001 and abs(low_trend) < 0.001:
                patterns.append({
                    'pattern': 'symmetrical_triangle',
                    'confidence': 0.70,
                    'direction': 'neutral',
                    'description': 'Converging highs and lows'
                })
        
        return patterns
    
    def _regime_detection(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Detect market regime."""
        data = task.get('data', {})
        symbols = task.get('symbols', [])
        
        results = {}
        
        for symbol in symbols:
            if symbol in data:
                df = data[symbol]
                if isinstance(df, dict):
                    df = pd.DataFrame(df)
                
                regime = self._detect_regime(df)
                results[symbol] = regime
        
        return {
            'status': 'success',
            'regimes': results,
            'timestamp': datetime.now().isoformat()
        }
    
    def _detect_regime(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect market regime for a symbol."""
        if len(df) < 50:
            return {'regime': 'unknown', 'confidence': 0, 'reason': 'Insufficient data'}
        
        close = df['Close']
        returns = close.pct_change().dropna()
        
        # Calculate metrics
        mean_return = returns.mean() * 252  # Annualized
        volatility = returns.std() * np.sqrt(252)  # Annualized
        momentum_20 = (close.iloc[-1] / close.iloc[-20] - 1) if len(close) >= 20 else 0
        
        # Trend detection
        sma_20 = close.rolling(20).mean().iloc[-1]
        sma_50 = close.rolling(50).mean().iloc[-1]
        sma_200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else sma_50
        
        if close.iloc[-1] > sma_200 > sma_50 > sma_20:
            trend = 'strong_bull'
        elif close.iloc[-1] > sma_50 > sma_20:
            trend = 'bull'
        elif close.iloc[-1] < sma_200 < sma_50 < sma_20:
            trend = 'strong_bear'
        elif close.iloc[-1] < sma_50 < sma_20:
            trend = 'bear'
        else:
            trend = 'sideways'
        
        # Volatility regime
        vol_percentile = stats.rankdata([volatility])[0] / 1  # Simplified
        if volatility > 0.3:
            vol_regime = 'high'
        elif volatility < 0.15:
            vol_regime = 'low'
        else:
            vol_regime = 'normal'
        
        # Combine into regime
        regime_map = {
            ('strong_bull', 'low'): 'bull_calm',
            ('strong_bull', 'normal'): 'bull_normal',
            ('strong_bull', 'high'): 'bull_volatile',
            ('bull', 'low'): 'bull_calm',
            ('bull', 'normal'): 'bull_normal',
            ('bull', 'high'): 'bull_volatile',
            ('strong_bear', 'low'): 'bear_calm',
            ('strong_bear', 'normal'): 'bear_normal',
            ('strong_bear', 'high'): 'bear_volatile',
            ('bear', 'low'): 'bear_calm',
            ('bear', 'normal'): 'bear_normal',
            ('bear', 'high'): 'bear_volatile',
            ('sideways', 'low'): 'range_calm',
            ('sideways', 'normal'): 'range_normal',
            ('sideways', 'high'): 'range_chop',
        }
        
        regime = regime_map.get((trend, vol_regime), 'unknown')
        
        return {
            'regime': regime,
            'trend': trend,
            'volatility': vol_regime,
            'annualized_return': float(mean_return),
            'annualized_volatility': float(volatility),
            'momentum_20d': float(momentum_20),
            'sharpe_approx': float(mean_return / volatility) if volatility > 0 else 0,
            'confidence': 0.85
        }
    
    def _anomaly_detection(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Detect anomalies in price data."""
        data = task.get('data', {})
        symbols = task.get('symbols', [])
        
        results = {}
        
        for symbol in symbols:
            if symbol in data:
                df = data[symbol]
                if isinstance(df, dict):
                    df = pd.DataFrame(df)
                
                anomalies = self._find_anomalies(df)
                results[symbol] = {
                    'anomalies': anomalies,
                    'anomaly_count': len(anomalies),
                    'anomaly_rate': len(anomalies) / len(df) if len(df) > 0 else 0
                }
        
        return {
            'status': 'success',
            'anomalies': results,
            'timestamp': datetime.now().isoformat()
        }
    
    def _find_anomalies(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Find anomalies in price data."""
        anomalies = []
        
        if len(df) < 10:
            return anomalies
        
        close = df['Close']
        returns = close.pct_change().dropna()
        
        # Z-score based anomaly detection
        z_scores = stats.zscore(returns)
        anomaly_indices = np.where(np.abs(z_scores) > 3)[0]
        
        for idx in anomaly_indices:
            if idx < len(df):
                date = df.index[idx]
                price = close.iloc[idx]
                return_pct = returns.iloc[idx] * 100
                
                anomalies.append({
                    'date': str(date),
                    'price': float(price),
                    'return_pct': float(return_pct),
                    'z_score': float(z_scores[idx]),
                    'type': 'extreme_move'
                })
        
        # Volume anomaly
        if 'Volume' in df.columns:
            volume = df['Volume']
            vol_z = stats.zscore(volume)
            vol_anomalies = np.where(np.abs(vol_z) > 3)[0]
            
            for idx in vol_anomalies:
                if idx < len(df):
                    date = df.index[idx]
                    anomalies.append({
                        'date': str(date),
                        'volume': float(volume.iloc[idx]),
                        'volume_z': float(vol_z[idx]),
                        'type': 'volume_spike'
                    })
        
        return anomalies
    
    def _comprehensive_analysis(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comprehensive analysis."""
        # Run multiple analyses
        technical_result = self._technical_analysis(task)
        
        # Get regime info
        regime_task = task.copy()
        regime_result = self._regime_detection(regime_task)
        
        # Get pattern info
        pattern_task = task.copy()
        pattern_result = self._pattern_recognition(pattern_task)
        
        return {
            'status': 'success',
            'technical': technical_result.get('analysis', {}),
            'regimes': regime_result.get('regimes', {}),
            'patterns': pattern_result.get('patterns', {}),
            'timestamp': datetime.now().isoformat()
        }
    
    def _multi_timeframe_analysis(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Perform multi-timeframe analysis."""
        # Simplified: analyze with different lookback periods
        data = task.get('data', {})
        symbols = task.get('symbols', [])
        
        results = {}
        
        for symbol in symbols:
            if symbol in data:
                df = data[symbol]
                if isinstance(df, dict):
                    df = pd.DataFrame(df)
                
                analysis = {
                    'symbol': symbol,
                    'timeframes': {}
                }
                
                # Short-term
                short_df = df.tail(20)
                short_score = self._calculate_trend_strength(short_df)
                
                # Medium-term
                medium_df = df.tail(50)
                medium_score = self._calculate_trend_strength(medium_df)
                
                # Long-term
                long_df = df.tail(200)
                long_score = self._calculate_trend_strength(long_df)
                
                analysis['timeframes'] = {
                    'short_term': {
                        'period': '1M',
                        'score': short_score,
                        'trend': 'bullish' if short_score > 0.1 else 'bearish' if short_score < -0.1 else 'sideways'
                    },
                    'medium_term': {
                        'period': '3M',
                        'score': medium_score,
                        'trend': 'bullish' if medium_score > 0.1 else 'bearish' if medium_score < -0.1 else 'sideways'
                    },
                    'long_term': {
                        'period': '1Y',
                        'score': long_score,
                        'trend': 'bullish' if long_score > 0.1 else 'bearish' if long_score < -0.1 else 'sideways'
                    }
                }
                
                # Overall assessment
                if short_score == medium_score == long_score:
                    analysis['alignment'] = 'aligned'
                    analysis['confidence'] = 0.9
                elif (short_score > 0 and medium_score > 0 and long_score > 0) or \
                     (short_score < 0 and medium_score < 0 and long_score < 0):
                    analysis['alignment'] = 'partially_aligned'
                    analysis['confidence'] = 0.7
                else:
                    analysis['alignment'] = 'diverging'
                    analysis['confidence'] = 0.5
                
                results[symbol] = analysis
        
        return {
            'status': 'success',
            'multi_timeframe': results,
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_trend_strength(self, df: pd.DataFrame) -> float:
        """Calculate trend strength from price data."""
        if len(df) < 5:
            return 0
        
        close = df['Close']
        
        # Calculate various trend indicators
        sma_short = close.rolling(5).mean().iloc[-1]
        sma_long = close.rolling(20).mean().iloc[-1] if len(close) >= 20 else close.mean()
        
        score = 0
        
        # SMA position
        if sma_short > sma_long:
            score += 0.3
        else:
            score -= 0.3
        
        # Price position
        if close.iloc[-1] > sma_long:
            score += 0.2
        else:
            score -= 0.2
        
        # Recent momentum
        momentum = (close.iloc[-1] / close.iloc[-5] - 1) if len(close) >= 5 else 0
        if momentum > 0.05:
            score += 0.3
        elif momentum > 0.02:
            score += 0.1
        elif momentum < -0.05:
            score -= 0.3
        elif momentum < -0.02:
            score -= 0.1
        
        # Trend consistency
        returns = close.pct_change()
        positive_ratio = (returns > 0).mean()
        score += (positive_ratio - 0.5) * 0.4
        
        return max(-1, min(1, score))
    
    def _correlation_analysis(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze correlations between symbols."""
        data = task.get('data', {})
        symbols = list(data.keys())
        
        if len(symbols) < 2:
            return {
                'status': 'error',
                'message': 'Need at least 2 symbols for correlation analysis'
            }
        
        correlations = {}
        
        for i, symbol1 in enumerate(symbols):
            for symbol2 in symbols[i+1:]:
                df1 = data[symbol1]
                df2 = data[symbol2]
                
                if isinstance(df1, dict):
                    df1 = pd.DataFrame(df1)
                if isinstance(df2, dict):
                    df2 = pd.DataFrame(df2)
                
                close1 = df1['Close'] if 'Close' in df1 else df1.iloc[:, 0]
                close2 = df2['Close'] if 'Close' in df2 else df2.iloc[:, 0]
                
                # Align series
                min_len = min(len(close1), len(close2))
                corr = close1.tail(min_len).corr(close2.tail(min_len))
                
                correlations[f"{symbol1}_{symbol2}"] = {
                    'correlation': float(corr),
                    'strength': 'strong' if abs(corr) > 0.7 else 'moderate' if abs(corr) > 0.4 else 'weak',
                    'direction': 'positive' if corr > 0 else 'negative'
                }
        
        return {
            'status': 'success',
            'correlations': correlations,
            'timestamp': datetime.now().isoformat()
        }
    
    def _fundamental_analysis(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Perform fundamental analysis."""
        # Placeholder - would require financial data APIs
        return {
            'status': 'success',
            'message': 'Fundamental analysis requires extended data sources',
            'note': 'PE ratio, earnings, revenue analysis pending'
        }
    
    def _process_message(self, message: AgentMessage) -> bool:
        """Process incoming message."""
        if message.msg_type == MessageType.ANALYSIS_REQUEST:
            task = message.payload
            result = self.execute(task)
            
            response = AgentMessage(
                msg_type=MessageType.ANALYSIS_RESPONSE,
                sender_id=self.agent_id,
                receiver_id=message.sender_id,
                payload=result,
                priority=message.priority,
                correlation_id=message.correlation_id
            )
            return self.send_message(response)
        
        elif message.msg_type == MessageType.DATA_RESPONSE:
            # Could trigger analysis on new data
            pass
        
        elif message.msg_type == MessageType.HEARTBEAT:
            self.heartbeat()
            self.state = AgentState.RUNNING
        
        return True
