"""
🌟 ORCHID QUANTUM AI - Analyst Agent
=====================================
Specialized agent for technical and fundamental analysis.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from scipy import stats
from .base import BaseAgent, AgentMessage, MessageType, AgentState
import logging


class AnalystAgent(BaseAgent):
    """Agent responsible for market analysis."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(
            agent_id="analyst_001",
            name="Analyst Agent"
        )
        self.capabilities = [
            "technical_analysis",
            "fundamental_analysis",
            "pattern_recognition",
            "regime_detection",
            "momentum_analysis",
            "mean_reversion_signals"
        ]
        self.config = config or {}
        self.analysis_cache: Dict[str, Dict[str, Any]] = {}
        
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the analyst agent."""
        self.config.update(config)
        self.logger.info("Analyst Agent initialized")
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
        elif task_type == 'comprehensive':
            return self._comprehensive_analysis(task)
        else:
            return {'status': 'error', 'message': f'Unknown task type: {task_type}'}
    
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
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        analysis = {
            'symbol': symbol,
            'current_price': float(latest.get('Close', latest.get('close', 0))),
            'change': float(latest.get('Close', 0)) - float(prev.get('Close', 0)),
            'change_pct': float((latest.get('Close', 0) / prev.get('Close', 1) - 1) * 100),
            'indicators': {},
            'signals': {},
            'score': 0
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
            rsi_score = 0
        
        analysis['indicators']['rsi'] = {
            'value': float(rsi),
            'signal': rsi_signal
        }
        analysis['signals']['rsi'] = rsi_signal
        
        # Trend Analysis (SMA)
        sma_5 = latest.get('SMA_5', 0)
        sma_20 = latest.get('SMA_20', 0)
        sma_50 = latest.get('SMA_50', 0)
        current_price = latest.get('Close', 0)
        
        trend_scores = []
        if sma_5 > sma_20:
            trend_scores.append(1)
        elif sma_5 < sma_20:
            trend_scores.append(-1)
        
        if sma_20 > sma_50:
            trend_scores.append(1)
        elif sma_20 < sma_50:
            trend_scores.append(-1)
        
        if current_price > sma_50:
            trend_scores.append(1)
        elif current_price < sma_50:
            trend_scores.append(-1)
        
        trend_score = np.mean(trend_scores) if trend_scores else 0
        
        if trend_score > 0.3:
            trend_signal = 'bullish'
        elif trend_score < -0.3:
            trend_signal = 'bearish'
        else:
            trend_signal = 'sideways'
        
        analysis['indicators']['trend'] = {
            'sma_5': float(sma_5),
            'sma_20': float(sma_20),
            'sma_50': float(sma_50),
            'signal': trend_signal,
            'score': float(trend_score)
        }
        analysis['signals']['trend'] = trend_signal
        
        # MACD Analysis
        macd = latest.get('MACD', 0)
        macd_signal = latest.get('MACD_Signal', 0)
        macd_hist = latest.get('MACD_Hist', 0)
        
        if macd_hist > 0 and macd_hist > prev.get('MACD_Hist', 0):
            macd_signal_name = 'bullish_momentum'
            macd_score = 1
        elif macd_hist < 0 and macd_hist < prev.get('MACD_Hist', 0):
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
            'signal_name': macd_signal_name
        }
        analysis['signals']['macd'] = macd_signal_name
        
        # Bollinger Bands Analysis
        bb_upper = latest.get('BB_Upper', 0)
        bb_lower = latest.get('BB_Lower', 0)
        
        if bb_upper > 0 and bb_lower > 0:
            bb_position = (current_price - bb_lower) / (bb_upper - bb_lower)
            
            if bb_position > 0.9:
                bb_signal = 'overbought'
            elif bb_position < 0.1:
                bb_signal = 'oversold'
            else:
                bb_signal = 'neutral'
        else:
            bb_position = 0.5
            bb_signal = 'unknown'
        
        analysis['indicators']['bollinger'] = {
            'upper': float(bb_upper),
            'lower': float(bb_lower),
            'position': float(bb_position),
            'signal': bb_signal
        }
        analysis['signals']['bollinger'] = bb_signal
        
        # Stochastic Analysis
        stoch_k = latest.get('Stoch_K', 50)
        stoch_d = latest.get('Stoch_D', 50)
        
        if stoch_k < 20 and stoch_d < 20:
            stoch_signal = 'oversold'
        elif stoch_k > 80 and stoch_d > 80:
            stoch_signal = 'overbought'
        elif stoch_k > stoch_d and stoch_k < 80:
            stoch_signal = 'bullish_crossover'
        elif stoch_k < stoch_d and stoch_k > 20:
            stoch_signal = 'bearish_crossover'
        else:
            stoch_signal = 'neutral'
        
        analysis['indicators']['stochastic'] = {
            'k': float(stoch_k),
            'd': float(stoch_d),
            'signal': stoch_signal
        }
        analysis['signals']['stochastic'] = stoch_signal
        
        # Volatility Analysis
        volatility = latest.get('Volatility_20', 0)
        volatility_pct = volatility * 100 if volatility else 0
        
        if volatility_pct > 2:
            vol_signal = 'high'
        elif volatility_pct < 0.5:
            vol_signal = 'low'
        else:
            vol_signal = 'normal'
        
        analysis['indicators']['volatility'] = {
            'value': float(volatility_pct),
            'signal': vol_signal
        }
        
        # Volume Analysis
        vol_ratio = latest.get('Volume_Ratio', 1)
        if vol_ratio > 2:
            vol_signal = 'high_volume'
        elif vol_ratio < 0.5:
            vol_signal = 'low_volume'
        else:
            vol_signal = 'normal_volume'
        
        analysis['indicators']['volume'] = {
            'ratio': float(vol_ratio),
            'signal': vol_signal
        }
        
        # Calculate overall score
        scores = {
            'rsi': 1 if rsi_signal == 'oversold' else -1 if rsi_signal == 'overbought' else 0,
            'trend': trend_score,
            'macd': macd_score,
            'bollinger': 1 if bb_position < 0.1 else -1 if bb_position > 0.9 else 0,
            'stochastic': 1 if stoch_signal == 'oversold' else -1 if stoch_signal == 'overbought' else 0
        }
        
        analysis['score'] = float(np.mean(list(scores.values())))
        
        # Generate recommendation
        score = analysis['score']
        if score > 0.3:
            analysis['recommendation'] = 'BUY'
        elif score < -0.3:
            analysis['recommendation'] = 'SELL'
        else:
            analysis['recommendation'] = 'HOLD'
        
        return analysis
    
    def _fundamental_analysis(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Perform fundamental analysis."""
        # Placeholder for fundamental analysis
        return {
            'status': 'success',
            'analysis': {
                'note': 'Fundamental analysis requires extended data sources'
            }
        }
    
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
                    'confidence': np.mean([p['confidence'] for p in patterns]) if patterns else 0
                }
        
        return {
            'status': 'success',
            'patterns': results
        }
    
    def _detect_patterns(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect chart patterns in price data."""
        patterns = []
        
        if len(df) < 20:
            return patterns
        
        # Simple pattern detection
        closes = df['Close'].values
        
        # Head and shoulders detection (simplified)
        highs = df['High'].values
        lows = df['Low'].values
        
        # Check for double top/bottom
        n = len(closes)
        
        # Calculate local maxima and minima
        from scipy.signal import argrelextrema
        
        try:
            local_max = argrelextrema(closes, np.greater, order=5)[0]
            local_min = argrelextrema(closes, np.less, order=5)[0]
            
            if len(local_max) >= 2:
                max_prices = closes[local_max]
                if len(local_max) >= 2:
                    # Check for double top
                    if abs(max_prices[-1] - max_prices[-2]) / max_prices[-2] < 0.02:
                        patterns.append({
                            'pattern': 'double_top',
                            'confidence': 0.75,
                            'direction': 'bearish'
                        })
            
            if len(local_min) >= 2:
                min_prices = closes[local_min]
                if len(local_min) >= 2:
                    # Check for double bottom
                    if abs(min_prices[-1] - min_prices[-2]) / min_prices[-2] < 0.02:
                        patterns.append({
                            'pattern': 'double_bottom',
                            'confidence': 0.75,
                            'direction': 'bullish'
                        })
        
        except Exception as e:
            self.logger.warning(f"Pattern detection error: {e}")
        
        # Trend line detection (simplified)
        x = np.arange(len(closes))
        slope, _, r_value, _, _ = stats.linregress(x, closes)
        
        if abs(r_value) > 0.8:
            if slope > 0:
                patterns.append({
                    'pattern': 'uptrend_line',
                    'confidence': abs(r_value),
                    'direction': 'bullish'
                })
            else:
                patterns.append({
                    'pattern': 'downtrend_line',
                    'confidence': abs(r_value),
                    'direction': 'bearish'
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
            'regimes': results
        }
    
    def _detect_regime(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect market regime for a symbol."""
        if len(df) < 50:
            return {'regime': 'unknown', 'confidence': 0}
        
        returns = df['Close'].pct_change().dropna()
        
        # Calculate metrics
        mean_return = returns.mean()
        volatility = returns.std()
        recent_returns = returns.tail(20)
        
        # Trend detection
        sma_20 = df['Close'].rolling(20).mean().iloc[-1]
        sma_50 = df['Close'].rolling(50).mean().iloc[-1]
        current_price = df['Close'].iloc[-1]
        
        if current_price > sma_50 > sma_20:
            trend = 'bullish'
        elif current_price < sma_50 < sma_20:
            trend = 'bearish'
        else:
            trend = 'sideways'
        
        # Volatility regime
        vol_percentile = stats.rankdata(volatility) / len(volatility)
        if vol_percentile > 0.75:
            vol_regime = 'high'
        elif vol_percentile < 0.25:
            vol_regime = 'low'
        else:
            vol_regime = 'normal'
        
        # Momentum
        momentum = (df['Close'].iloc[-1] / df['Close'].iloc[-20]) - 1 if len(df) >= 20 else 0
        
        # Combine into regime
        if trend == 'bullish' and vol_regime != 'high':
            regime = 'bull_boring'
        elif trend == 'bullish' and vol_regime == 'high':
            regime = 'bull_volatile'
        elif trend == 'bearish' and vol_regime != 'high':
            regime = 'bear_boring'
        elif trend == 'bearish' and vol_regime == 'high':
            regime = 'bear_volatile'
        elif vol_regime == 'high':
            regime = 'chop'
        else:
            regime = 'range_bound'
        
        return {
            'regime': regime,
            'trend': trend,
            'volatility': vol_regime,
            'momentum': float(momentum),
            'confidence': 0.8
        }
    
    def _comprehensive_analysis(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comprehensive analysis combining all methods."""
        technical_result = self._technical_analysis(task)
        
        task_with_regime = task.copy()
        regime_result = self._regime_detection(task)
        
        return {
            'status': 'success',
            'technical': technical_result.get('analysis', {}),
            'regimes': regime_result.get('regimes', {}),
            'timestamp': datetime.now().isoformat()
        }
    
    def _process_message(self, message: AgentMessage) -> None:
        """Process incoming message."""
        if message.msg_type == MessageType.ANALYSIS_REQUEST:
            task = message.payload
            result = self.execute(task)
            
            response = AgentMessage(
                msg_type=MessageType.ANALYSIS_RESPONSE,
                sender_id=self.agent_id,
                receiver_id=message.sender_id,
                payload=result,
                priority=message.priority
            )
            self._deliver_message(response)
        
        elif message.msg_type == MessageType.HEARTBEAT:
            self.heartbeat()
            self.state = AgentState.RUNNING
