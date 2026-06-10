"""
RETAIL STRATEGIES - Comprehensive Retail Trading Strategies
Includes scalping, swing trading, position trading, and more
"""

import sys
import os
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.indicators.technical_indicators import TechnicalIndicators

@dataclass
class RetailSignal:
    """Retail trading signal"""
    strategy_name: str
    action: str  # BUY, SELL, HOLD
    strength: float  # 0-1
    entry_price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    risk_reward_ratio: Optional[float]
    timeframe: str
    indicators_used: List[str]
    reasoning: str

class RetailStrategies:
    """Comprehensive retail trading strategies"""

    def __init__(self):
        self.ti = TechnicalIndicators()
        self.strategies = {
            'scalping_momentum': self._scalping_momentum,
            'swing_trading': self._swing_trading,
            'position_trading': self._position_trading,
            'breakout_trading': self._breakout_trading,
            'reversal_trading': self._reversal_trading,
            'trend_following': self._trend_following,
            'range_trading': self._range_trading,
            'arbitrage_pair': self._statistical_arbitrage,
            'options_straddle': self._options_straddle,
            'gap_trading': self._gap_trading
        }

    def get_available_strategies(self) -> Dict[str, str]:
        """Get list of available retail strategies"""
        return {
            'scalping_momentum': 'High-frequency momentum scalping (1-5 min)',
            'swing_trading': 'Medium-term swing trading (hours-days)',
            'position_trading': 'Long-term position trading (weeks-months)',
            'breakout_trading': 'Breakout trading with volume confirmation',
            'reversal_trading': 'Reversal trading at support/resistance',
            'trend_following': 'Trend following with moving averages',
            'range_trading': 'Range trading in sideways markets',
            'arbitrage_pair': 'Statistical arbitrage pairs trading',
            'options_straddle': 'Options straddle for volatility events',
            'gap_trading': 'Gap trading for earnings/news events'
        }

    def execute_strategy(self, strategy_name: str, data: pd.DataFrame,
                        current_price: float, portfolio_value: float) -> Optional[RetailSignal]:
        """Execute specific retail strategy"""
        if strategy_name not in self.strategies:
            return None

        try:
            return self.strategies[strategy_name](data, current_price, portfolio_value)
        except Exception as e:
            print(f"Error executing {strategy_name}: {e}")
            return None

    def _scalping_momentum(self, data: pd.DataFrame, current_price: float,
                          portfolio_value: float) -> Optional[RetailSignal]:
        """Scalping momentum strategy - very short-term"""
        if len(data) < 20:
            return None

        # Calculate indicators
        rsi = self.ti.rsi(data['close'])
        macd, signal, hist = self.ti.macd(data['close'])

        # Get latest values
        current_rsi = rsi.iloc[-1] if not rsi.empty else 50
        current_hist = hist.iloc[-1] if not hist.empty else 0

        # Scalping logic
        if current_rsi < 30 and current_hist > 0 and data['volume'].iloc[-1] > data['volume'].mean():
            # Oversold + momentum + volume spike = BUY
            stop_loss = current_price * 0.998  # 0.2% stop
            take_profit = current_price * 1.005  # 0.5% target
            return RetailSignal(
                strategy_name='scalping_momentum',
                action='BUY',
                strength=0.8,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_reward_ratio=2.5,
                timeframe='1m',
                indicators_used=['RSI', 'MACD', 'Volume'],
                reasoning='Oversold RSI + bullish MACD + volume spike'
            )
        elif current_rsi > 70 and current_hist < 0:
            # Overbought + bearish momentum = SELL
            stop_loss = current_price * 1.002  # 0.2% stop
            take_profit = current_price * 0.995  # 0.5% target
            return RetailSignal(
                strategy_name='scalping_momentum',
                action='SELL',
                strength=0.8,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_reward_ratio=2.5,
                timeframe='1m',
                indicators_used=['RSI', 'MACD'],
                reasoning='Overbought RSI + bearish MACD'
            )

        return RetailSignal(
            strategy_name='scalping_momentum',
            action='HOLD',
            strength=0.3,
            entry_price=None,
            stop_loss=None,
            take_profit=None,
            risk_reward_ratio=None,
            timeframe='1m',
            indicators_used=['RSI', 'MACD', 'Volume'],
            reasoning='No clear scalping signal'
        )

    def _swing_trading(self, data: pd.DataFrame, current_price: float,
                      portfolio_value: float) -> Optional[RetailSignal]:
        """Swing trading strategy - medium-term"""
        if len(data) < 50:
            return None

        # Calculate indicators
        sma_20 = data['close'].rolling(window=20).mean()
        sma_50 = data['close'].rolling(window=50).mean()
        stoch_k, stoch_d = self.ti.stochastic(data['high'], data['low'], data['close'])
        upper, middle, lower = self.ti.bollinger_bands(data['close'])

        # Get latest values
        current_sma_20 = sma_20.iloc[-1]
        current_sma_50 = sma_50.iloc[-1]
        current_stoch_k = stoch_k.iloc[-1] if not stoch_k.empty else 50
        current_bb_upper = upper.iloc[-1] if not upper.empty else current_price * 1.1
        current_bb_lower = lower.iloc[-1] if not lower.empty else current_price * 0.9

        # Swing trading logic
        if (current_price > current_sma_20 and current_price > current_sma_50 and
            current_stoch_k < 20 and current_price <= current_bb_lower * 1.01):
            # Above trend + oversold + near lower BB = BUY
            stop_loss = current_bb_lower * 0.98
            take_profit = current_price * 1.05  # 5% target
            return RetailSignal(
                strategy_name='swing_trading',
                action='BUY',
                strength=0.7,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_reward_ratio=3.0,
                timeframe='4h',
                indicators_used=['SMA', 'Stochastic', 'Bollinger Bands'],
                reasoning='Above trend + oversold stochastic + near lower BB'
            )
        elif (current_price < current_sma_20 and current_stoch_k > 80 and
              current_price >= current_bb_upper * 0.99):
            # Below trend + overbought + near upper BB = SELL
            stop_loss = current_bb_upper * 1.02
            take_profit = current_price * 0.95  # 5% target
            return RetailSignal(
                strategy_name='swing_trading',
                action='SELL',
                strength=0.7,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_reward_ratio=3.0,
                timeframe='4h',
                indicators_used=['SMA', 'Stochastic', 'Bollinger Bands'],
                reasoning='Below trend + overbought stochastic + near upper BB'
            )

        return RetailSignal(
            strategy_name='swing_trading',
            action='HOLD',
            strength=0.2,
            entry_price=None,
            stop_loss=None,
            take_profit=None,
            risk_reward_ratio=None,
            timeframe='4h',
            indicators_used=['SMA', 'Stochastic', 'Bollinger Bands'],
            reasoning='No clear swing signal'
        )

    def _position_trading(self, data: pd.DataFrame, current_price: float,
                         portfolio_value: float) -> Optional[RetailSignal]:
        """Position trading strategy - long-term"""
        if len(data) < 200:  # Need at least 200 days
            return None

        # Calculate indicators
        sma_100 = data['close'].rolling(window=100).mean()
        sma_200 = data['close'].rolling(window=200).mean()
        volume_sma = data['volume'].rolling(window=50).mean()

        # Get latest values
        current_sma_100 = sma_100.iloc[-1]
        current_sma_200 = sma_200.iloc[-1]
        current_volume = data['volume'].iloc[-1]
        avg_volume = volume_sma.iloc[-1]

        # Position trading logic (very conservative)
        if (current_price > current_sma_100 and current_price > current_sma_200 and
            current_volume > avg_volume * 1.2):
            # Long-term uptrend + volume confirmation = BUY
            stop_loss = current_price * 0.85  # 15% stop (very wide)
            take_profit = current_price * 1.50  # 50% target (long-term)
            return RetailSignal(
                strategy_name='position_trading',
                action='BUY',
                strength=0.6,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_reward_ratio=2.0,
                timeframe='1w',
                indicators_used=['SMA(100)', 'SMA(200)', 'Volume'],
                reasoning='Long-term uptrend + volume confirmation'
            )
        elif current_price < current_sma_200:
            # Below long-term trend = SELL
            stop_loss = current_price * 1.10  # 10% stop
            take_profit = current_price * 0.80  # 20% target
            return RetailSignal(
                strategy_name='position_trading',
                action='SELL',
                strength=0.5,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_reward_ratio=1.5,
                timeframe='1w',
                indicators_used=['SMA(200)'],
                reasoning='Below long-term trend line'
            )

        return RetailSignal(
            strategy_name='position_trading',
            action='HOLD',
            strength=0.1,
            entry_price=None,
            stop_loss=None,
            take_profit=None,
            risk_reward_ratio=None,
            timeframe='1w',
            indicators_used=['SMA(100)', 'SMA(200)', 'Volume'],
            reasoning='No clear long-term signal'
        )

    def _breakout_trading(self, data: pd.DataFrame, current_price: float,
                         portfolio_value: float) -> Optional[RetailSignal]:
        """Breakout trading strategy"""
        if len(data) < 50:
            return None

        # Calculate indicators
        upper, middle, lower = self.ti.bollinger_bands(data['close'])
        volume_sma = data['volume'].rolling(window=20).mean()

        # Find recent high/low
        recent_high = data['high'].rolling(window=20).max()
        recent_low = data['low'].rolling(window=20).min()

        # Get latest values
        current_upper = upper.iloc[-1] if not upper.empty else current_price * 1.05
        current_lower = lower.iloc[-1] if not lower.empty else current_price * 0.95
        recent_high_val = recent_high.iloc[-1]
        recent_low_val = recent_low.iloc[-1]
        current_volume = data['volume'].iloc[-1]
        avg_volume = volume_sma.iloc[-1] if not volume_sma.empty else current_volume

        # Breakout logic
        if (current_price > recent_high_val * 0.995 and current_volume > avg_volume * 1.5):
            # Break above recent high + high volume = BUY
            stop_loss = recent_high_val * 0.98
            take_profit = current_price * 1.03  # 3% target
            return RetailSignal(
                strategy_name='breakout_trading',
                action='BUY',
                strength=0.75,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_reward_ratio=2.0,
                timeframe='1h',
                indicators_used=['Breakout', 'Volume', 'Recent High'],
                reasoning='Break above recent high + high volume'
            )
        elif (current_price < recent_low_val * 1.005 and current_volume > avg_volume * 1.5):
            # Break below recent low + high volume = SELL
            stop_loss = recent_low_val * 1.02
            take_profit = current_price * 0.97  # 3% target
            return RetailSignal(
                strategy_name='breakout_trading',
                action='SELL',
                strength=0.75,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_reward_ratio=2.0,
                timeframe='1h',
                indicators_used=['Breakout', 'Volume', 'Recent Low'],
                reasoning='Break below recent low + high volume'
            )

        return RetailSignal(
            strategy_name='breakout_trading',
            action='HOLD',
            strength=0.2,
            entry_price=None,
            stop_loss=None,
            take_profit=None,
            risk_reward_ratio=None,
            timeframe='1h',
            indicators_used=['Breakout', 'Volume'],
            reasoning='No breakout signal'
        )

    def _reversal_trading(self, data: pd.DataFrame, current_price: float,
                         portfolio_value: float) -> Optional[RetailSignal]:
        """Reversal trading strategy"""
        if len(data) < 30:
            return None

        # Calculate indicators
        rsi = self.ti.rsi(data['close'])
        stoch_k, stoch_d = self.ti.stochastic(data['high'], data['low'], data['close'])

        # Support/Resistance levels (simplified)
        recent_lows = data['low'].rolling(window=20).min()
        recent_highs = data['high'].rolling(window=20).max()

        # Get latest values
        current_rsi = rsi.iloc[-1] if not rsi.empty else 50
        current_stoch_k = stoch_k.iloc[-1] if not stoch_k.empty else 50
        support_level = recent_lows.iloc[-1]
        resistance_level = recent_highs.iloc[-1]

        # Reversal logic
        if (current_rsi < 25 and current_stoch_k < 20 and
            current_price <= support_level * 1.02):
            # Extreme oversold + at support = BUY
            stop_loss = support_level * 0.97
            take_profit = resistance_level * 0.98
            return RetailSignal(
                strategy_name='reversal_trading',
                action='BUY',
                strength=0.65,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_reward_ratio=2.5,
                timeframe='1d',
                indicators_used=['RSI', 'Stochastic', 'Support/Resistance'],
                reasoning='Extreme oversold + support level'
            )
        elif (current_rsi > 75 and current_stoch_k > 80 and
              current_price >= resistance_level * 0.98):
            # Extreme overbought + at resistance = SELL
            stop_loss = resistance_level * 1.03
            take_profit = support_level * 1.02
            return RetailSignal(
                strategy_name='reversal_trading',
                action='SELL',
                strength=0.65,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_reward_ratio=2.5,
                timeframe='1d',
                indicators_used=['RSI', 'Stochastic', 'Support/Resistance'],
                reasoning='Extreme overbought + resistance level'
            )

        return RetailSignal(
            strategy_name='reversal_trading',
            action='HOLD',
            strength=0.1,
            entry_price=None,
            stop_loss=None,
            take_profit=None,
            risk_reward_ratio=None,
            timeframe='1d',
            indicators_used=['RSI', 'Stochastic', 'Support/Resistance'],
            reasoning='No reversal signal'
        )

    def _trend_following(self, data: pd.DataFrame, current_price: float,
                        portfolio_value: float) -> Optional[RetailSignal]:
        """Trend following strategy"""
        if len(data) < 50:
            return None

        # Calculate indicators
        sma_50 = data['close'].rolling(window=50).mean()
        sma_200 = data['close'].rolling(window=200).mean()
        adx = self.ti.adx(data['high'], data['low'], data['close'])[0]  # ADX only

        # Get latest values
        current_sma_50 = sma_50.iloc[-1]
        current_sma_200 = sma_200.iloc[-1]
        current_adx = adx.iloc[-1] if not adx.empty else 20

        # Trend following logic
        if (current_price > current_sma_50 and current_price > current_sma_200 and current_adx > 25):
            # Strong uptrend = BUY
            stop_loss = current_sma_200 * 0.98
            take_profit = current_price * 1.10  # 10% target
            return RetailSignal(
                strategy_name='trend_following',
                action='BUY',
                strength=0.8,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_reward_ratio=4.0,
                timeframe='1d',
                indicators_used=['SMA(50)', 'SMA(200)', 'ADX'],
                reasoning='Strong uptrend + high ADX'
            )
        elif (current_price < current_sma_50 and current_price < current_sma_200 and current_adx > 25):
            # Strong downtrend = SELL
            stop_loss = current_sma_200 * 1.02
            take_profit = current_price * 0.90  # 10% target
            return RetailSignal(
                strategy_name='trend_following',
                action='SELL',
                strength=0.8,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_reward_ratio=4.0,
                timeframe='1d',
                indicators_used=['SMA(50)', 'SMA(200)', 'ADX'],
                reasoning='Strong downtrend + high ADX'
            )

        return RetailSignal(
            strategy_name='trend_following',
            action='HOLD',
            strength=0.3,
            entry_price=None,
            stop_loss=None,
            take_profit=None,
            risk_reward_ratio=None,
            timeframe='1d',
            indicators_used=['SMA(50)', 'SMA(200)', 'ADX'],
            reasoning='No strong trend'
        )

    def _range_trading(self, data: pd.DataFrame, current_price: float,
                      portfolio_value: float) -> Optional[RetailSignal]:
        """Range trading strategy for sideways markets"""
        if len(data) < 30:
            return None

        # Calculate indicators
        upper, middle, lower = self.ti.bollinger_bands(data['close'])
        adx = self.ti.adx(data['high'], data['low'], data['close'])[0]

        # Get latest values
        current_upper = upper.iloc[-1] if not upper.empty else current_price * 1.05
        current_lower = lower.iloc[-1] if not lower.empty else current_price * 0.95
        current_middle = middle.iloc[-1] if not middle.empty else current_price
        current_adx = adx.iloc[-1] if not adx.empty else 30

        # Range trading logic (when ADX is low = ranging market)
        if current_adx < 20:  # Low trend strength = ranging
            if current_price <= current_lower * 1.02:
                # Near lower BB in ranging market = BUY
                stop_loss = current_lower * 0.98
                take_profit = current_middle
                return RetailSignal(
                    strategy_name='range_trading',
                    action='BUY',
                    strength=0.6,
                    entry_price=current_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    risk_reward_ratio=1.5,
                    timeframe='1h',
                    indicators_used=['Bollinger Bands', 'ADX'],
                    reasoning='Near lower BB in ranging market'
                )
            elif current_price >= current_upper * 0.98:
                # Near upper BB in ranging market = SELL
                stop_loss = current_upper * 1.02
                take_profit = current_middle
                return RetailSignal(
                    strategy_name='range_trading',
                    action='SELL',
                    strength=0.6,
                    entry_price=current_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    risk_reward_ratio=1.5,
                    timeframe='1h',
                    indicators_used=['Bollinger Bands', 'ADX'],
                    reasoning='Near upper BB in ranging market'
                )

        return RetailSignal(
            strategy_name='range_trading',
            action='HOLD',
            strength=0.2,
            entry_price=None,
            stop_loss=None,
            take_profit=None,
            risk_reward_ratio=None,
            timeframe='1h',
            indicators_used=['Bollinger Bands', 'ADX'],
            reasoning='Strong trend or unclear range'
        )

    def _statistical_arbitrage(self, data: pd.DataFrame, current_price: float,
                              portfolio_value: float) -> Optional[RetailSignal]:
        """Statistical arbitrage pairs trading"""
        # This would require pair data - simplified version
        return RetailSignal(
            strategy_name='arbitrage_pair',
            action='HOLD',
            strength=0.1,
            entry_price=None,
            stop_loss=None,
            take_profit=None,
            risk_reward_ratio=None,
            timeframe='1h',
            indicators_used=['Z-score', 'Cointegration'],
            reasoning='Statistical arbitrage requires pair data'
        )

    def _options_straddle(self, data: pd.DataFrame, current_price: float,
                         portfolio_value: float) -> Optional[RetailSignal]:
        """Options straddle strategy"""
        # Simplified options strategy
        volatility = data['close'].pct_change().std() * 100
        if volatility > 5:  # High volatility
            return RetailSignal(
                strategy_name='options_straddle',
                action='STRADDLE',
                strength=0.7,
                entry_price=current_price,
                stop_loss=None,
                take_profit=None,
                risk_reward_ratio=None,
                timeframe='1d',
                indicators_used=['Volatility'],
                reasoning='High volatility - options straddle opportunity'
            )
        return RetailSignal(
            strategy_name='options_straddle',
            action='HOLD',
            strength=0.1,
            entry_price=None,
            stop_loss=None,
            take_profit=None,
            risk_reward_ratio=None,
            timeframe='1d',
            indicators_used=['Volatility'],
            reasoning='Low volatility - no straddle signal'
        )

    def _gap_trading(self, data: pd.DataFrame, current_price: float,
                    portfolio_value: float) -> Optional[RetailSignal]:
        """Gap trading strategy"""
        if len(data) < 2:
            return None

        prev_close = data['close'].iloc[-2]
        prev_open = data['open'].iloc[-2]
        current_open = data['open'].iloc[-1]

        # Check for gap
        gap_up = current_open > prev_close * 1.02  # 2% gap up
        gap_down = current_open < prev_close * 0.98  # 2% gap down

        if gap_up and data['volume'].iloc[-1] > data['volume'].mean() * 1.5:
            # Gap up + volume = BUY (gap fill expected)
            stop_loss = current_open * 0.98
            take_profit = prev_close
            return RetailSignal(
                strategy_name='gap_trading',
                action='BUY',
                strength=0.7,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_reward_ratio=2.0,
                timeframe='1d',
                indicators_used=['Gap Analysis', 'Volume'],
                reasoning='Gap up + high volume - gap fill opportunity'
            )
        elif gap_down and data['volume'].iloc[-1] > data['volume'].mean() * 1.5:
            # Gap down + volume = SELL (gap fill expected)
            stop_loss = current_open * 1.02
            take_profit = prev_close
            return RetailSignal(
                strategy_name='gap_trading',
                action='SELL',
                strength=0.7,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_reward_ratio=2.0,
                timeframe='1d',
                indicators_used=['Gap Analysis', 'Volume'],
                reasoning='Gap down + high volume - gap fill opportunity'
            )

        return RetailSignal(
            strategy_name='gap_trading',
            action='HOLD',
            strength=0.1,
            entry_price=None,
            stop_loss=None,
            take_profit=None,
            risk_reward_ratio=None,
            timeframe='1d',
            indicators_used=['Gap Analysis', 'Volume'],
            reasoning='No significant gap'
        )

# Global instance
retail_strategies = RetailStrategies()