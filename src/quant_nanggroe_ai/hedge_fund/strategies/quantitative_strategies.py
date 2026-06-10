"""
Advanced Quantitative Strategies
Including Jim Simons, Momentum, Mean Reversion, Factor Investing, etc.
"""

import json
import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from statistics import mean, stdev

import pandas as pd
import numpy as np


class StrategyType(Enum):
    """Strategy types"""
    JIM_SIMMONS = "jim_simmons"  # Quantitative/Mathematical
    QUANT_MOMENTUM = "quant_momentum"
    MEAN_REVERSION = "mean_reversion"
    FACTOR_INVESTING = "factor_investing"
    EARNINGS_MOMENTUM = "earnings_momentum"
    TECHNICAL_ANALYSIS = "technical_analysis"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    MACHINE_LEARNING = "machine_learning"
    ARBITRAGE = "arbitrage"
    STATISTICAL_ARBITRAGE = "statistical_arbitrage"


@dataclass
class StrategySignal:
    """Output from a strategy"""
    strategy: str
    signal: str  # BUY, SELL, HOLD
    confidence: float  # 0-100
    score: float  # Raw score
    factors: Dict[str, Any]  # Contributing factors
    reasoning: str
    metadata: Dict[str, Any] = None


@dataclass
class AggregatedSignal:
    """Aggregated signal from all strategies"""
    final_signal: str
    final_confidence: float
    total_strategies: int
    buy_count: int
    sell_count: int
    hold_count: int
    avg_confidence: float
    weighted_score: float
    strategy_details: List[Dict]
    consensus_level: str  # HIGH, MEDIUM, LOW


class QuantitativeStrategy:
    """
    Base class for quantitative strategies
    Inspired by Jim Simons' Renaissance Technologies approach
    """
    
    def __init__(self, name: str, weight: float = 1.0):
        self.name = name
        self.weight = weight
    
    def calculate(self, prices: List, fundamentals: Dict = None, market_data: Dict = None) -> StrategySignal:
        raise NotImplementedError
    
    def _get_prices_array(self, prices: List) -> pd.Series:
        """Convert price list to pandas Series"""
        if not prices:
            return pd.Series([])
        
        # Check if prices are objects with 'close' attribute
        if hasattr(prices[0], 'close'):
            closes = [p.close for p in prices if hasattr(p, 'close')]
            return pd.Series(closes)
        else:
            # Assume simple list of numbers
            return pd.Series(prices)


class JimSimonsStrategy(QuantitativeStrategy):
    """
    Jim Simons-style quantitative strategy
    Uses mathematical models, pattern recognition, and statistical analysis
    """
    
    def __init__(self):
        super().__init__("Jim Simons (Quant)", weight=1.5)
    
    def calculate(self, prices: List, fundamentals: Dict = None, market_data: Dict = None) -> StrategySignal:
        """
        Jim Simons' approach:
        - Statistical pattern recognition
        - Mean reversion with confirmation
        - High-frequency signals
        - Risk management with position sizing
        """
        if len(prices) < 5:
            return StrategySignal(
                strategy=self.name,
                signal="HOLD",
                confidence=50,
                score=0,
                factors={"reason": "Insufficient data"},
                reasoning="Not enough price data for statistical analysis"
            )
        
        closes = self._get_prices_array(prices)
        
        # Calculate returns
        returns = closes.pct_change().dropna()
        
        # Statistical measures
        mean_return = returns.mean()
        std_return = returns.std()
        
        # Sharpe-like ratio (annualized)
        if std_return > 0:
            sharpe = (mean_return / std_return) * np.sqrt(252) if std_return != 0 else 0
        else:
            sharpe = 0
        
        # Recent momentum (last 5 days)
        if len(closes) >= 5:
            momentum = (closes.iloc[-1] / closes.iloc[-5] - 1) * 100
        else:
            momentum = 0
        
        # Mean reversion score
        z_score = (closes.iloc[-1] - closes.mean()) / closes.std() if closes.std() > 0 else 0
        
        # Pattern recognition (simplified)
        recent_volatility = returns.tail(5).std()
        
        # Combine signals
        score = 0
        factors = {}
        
        # Mean reversion component
        if z_score < -2:
            score += 0.3
            factors["mean_reversion"] = "Oversold - potential bounce"
        elif z_score > 2:
            score -= 0.3
            factors["mean_reversion"] = "Overbought - potential pullback"
        else:
            score += 0.1
            factors["mean_reversion"] = "Neutral"
        
        # Momentum component
        if momentum > 5:
            score += 0.2
            factors["momentum"] = f"Strong positive ({momentum:.1f}%)"
        elif momentum < -5:
            score -= 0.2
            factors["momentum"] = f"Strong negative ({momentum:.1f}%)"
        else:
            score += 0.05
            factors["momentum"] = f"Neutral ({momentum:.1f}%)"
        
        # Volatility factor
        if recent_volatility > std_return * 1.5:
            score -= 0.1
            factors["volatility"] = "Elevated volatility"
        else:
            score += 0.1
            factors["volatility"] = "Normal volatility"
        
        # Sharpe ratio contribution
        if sharpe > 1:
            score += 0.2
            factors["sharpe"] = f"Good risk-adjusted returns ({sharpe:.2f})"
        elif sharpe < -1:
            score -= 0.2
            factors["sharpe"] = f"Poor risk-adjusted returns ({sharpe:.2f})"
        
        # Generate signal
        if score > 0.25:
            signal = "BUY"
            confidence = min(85, 50 + score * 50)
        elif score < -0.25:
            signal = "SELL"
            confidence = min(85, 50 + abs(score) * 50)
        else:
            signal = "HOLD"
            confidence = max(40, 70 - abs(score) * 40)
        
        reasoning = f"Quant model: score={score:.3f}, z-score={z_score:.2f}, momentum={momentum:.1f}%, sharpe={sharpe:.2f}"
        
        return StrategySignal(
            strategy=self.name,
            signal=signal,
            confidence=confidence,
            score=score,
            factors=factors,
            reasoning=reasoning,
            metadata={
                "z_score": z_score,
                "momentum": momentum,
                "sharpe": sharpe,
                "volatility_ratio": recent_volatility / std_return if std_return > 0 else 1
            }
        )


class QuantitativeMomentumStrategy(QuantitativeStrategy):
    """
    Quantitative Momentum Strategy
    Based on price momentum, relative strength, and trend analysis
    """
    
    def __init__(self):
        super().__init__("Quant Momentum", weight=1.2)
    
    def calculate(self, prices: List, fundamentals: Dict = None, market_data: Dict = None) -> StrategySignal:
        if len(prices) < 20:
            return StrategySignal(
                strategy=self.name,
                signal="HOLD",
                confidence=50,
                score=0,
                factors={"reason": "Insufficient data for momentum"},
                reasoning="Need at least 20 days of data"
            )
        
        closes = self._get_prices_array(prices)
        
        # Multiple timeframes
        momentum_5d = (closes.iloc[-1] / closes.iloc[-5] - 1) * 100 if len(closes) >= 5 else 0
        momentum_10d = (closes.iloc[-1] / closes.iloc[-10] - 1) * 100 if len(closes) >= 10 else 0
        momentum_20d = (closes.iloc[-1] / closes.iloc[-20] - 1) * 100 if len(closes) >= 20 else 0
        
        # Trend analysis (SMA crossover)
        sma_10 = closes.rolling(10).mean().iloc[-1]
        sma_20 = closes.rolling(20).mean().iloc[-1]
        sma_50 = closes.rolling(50).mean().iloc[-1] if len(closes) >= 50 else sma_20
        
        # Relative strength (vs market)
        # Simplified - using recent trend
        trend_strength = momentum_20d / 20 if momentum_20d != 0 else 0
        
        # Volatility-adjusted momentum
        returns = closes.pct_change().dropna()
        volatility = returns.std() * np.sqrt(252)
        risk_adj_momentum = (momentum_20d / 100) / volatility if volatility > 0 else 0
        
        score = 0
        factors = {}
        
        # Multi-timeframe confirmation
        if momentum_5d > 0 and momentum_10d > 0 and momentum_20d > 0:
            score += 0.3
            factors["trend"] = "All timeframes bullish"
        elif momentum_5d < 0 and momentum_10d < 0 and momentum_20d < 0:
            score -= 0.3
            factors["trend"] = "All timeframes bearish"
        else:
            score += 0.1
            factors["trend"] = "Mixed signals"
        
        # SMA trend
        if closes.iloc[-1] > sma_50 > sma_20 > sma_10:
            score += 0.2
            factors["sma"] = "Strong uptrend (price > SMA50 > SMA20 > SMA10)"
        elif closes.iloc[-1] < sma_50 < sma_20 < sma_10:
            score -= 0.2
            factors["sma"] = "Strong downtrend"
        elif closes.iloc[-1] > sma_20:
            score += 0.1
            factors["sma"] = "Above 20-day SMA"
        else:
            score -= 0.1
            factors["sma"] = "Below 20-day SMA"
        
        # Risk-adjusted momentum
        if risk_adj_momentum > 0.5:
            score += 0.2
            factors["risk_adj"] = f"Strong risk-adjusted momentum ({risk_adj_momentum:.2f})"
        elif risk_adj_momentum < -0.5:
            score -= 0.2
            factors["risk_adj"] = f"Weak risk-adjusted momentum ({risk_adj_momentum:.2f})"
        
        # Signal generation
        if score > 0.35:
            signal = "BUY"
            confidence = min(85, 60 + score * 50)
        elif score < -0.35:
            signal = "SELL"
            confidence = min(85, 60 + abs(score) * 50)
        else:
            signal = "HOLD"
            confidence = max(45, 65 - abs(score) * 30)
        
        reasoning = f"Momentum: 5d={momentum_5d:.1f}%, 10d={momentum_10d:.1f}%, 20d={momentum_20d:.1f}%, score={score:.3f}"
        
        return StrategySignal(
            strategy=self.name,
            signal=signal,
            confidence=confidence,
            score=score,
            factors=factors,
            reasoning=reasoning,
            metadata={
                "momentum_5d": momentum_5d,
                "momentum_10d": momentum_10d,
                "momentum_20d": momentum_20d,
                "risk_adj_momentum": risk_adj_momentum
            }
        )


class MeanReversionStrategy(QuantitativeStrategy):
    """
    Mean Reversion Strategy
    Buys oversold, sells overbought - assuming price returns to mean
    """
    
    def __init__(self):
        super().__init__("Mean Reversion", weight=1.0)
    
    def calculate(self, prices: List, fundamentals: Dict = None, market_data: Dict = None) -> StrategySignal:
        if len(prices) < 30:
            return StrategySignal(
                strategy=self.name,
                signal="HOLD",
                confidence=50,
                score=0,
                factors={"reason": "Insufficient data for mean reversion"},
                reasoning="Need at least 30 days of data"
            )
        
        closes = self._get_prices_array(prices)
        
        # Calculate statistics
        mean_price = closes.mean()
        std_price = closes.std()
        
        # Z-score
        z_score = (closes.iloc[-1] - mean_price) / std_price if std_price > 0 else 0
        
        # Bollinger Bands position
        sma_20 = closes.rolling(20).mean().iloc[-1]
        std_20 = closes.rolling(20).std().iloc[-1]
        bb_position = (closes.iloc[-1] - sma_20) / (2 * std_20) if std_20 > 0 else 0
        
        # RSI (14-day)
        delta = closes.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rs = rs.replace([np.inf, -np.inf], np.nan)
        rsi = 100 - (100 / (1 + rs))
        rsi = rsi.fillna(50)
        
        rsi_value = rsi.iloc[-1]

        # Mean reversion score
        score = 0
        factors = {}
        
        # Z-score analysis
        if z_score < -2:
            score += 0.35
            factors["z_score"] = f"Deeply oversold (z={z_score:.2f})"
        elif z_score < -1:
            score += 0.2
            factors["z_score"] = f"Oversold (z={z_score:.2f})"
        elif z_score > 2:
            score -= 0.35
            factors["z_score"] = f"Deeply overbought (z={z_score:.2f})"
        elif z_score > 1:
            score -= 0.2
            factors["z_score"] = f"Overbought (z={z_score:.2f})"
        else:
            score += 0.1
            factors["z_score"] = f"Near mean (z={z_score:.2f})"
        
        # Bollinger Bands
        if bb_position < -0.8:
            score += 0.2
            factors["bollinger"] = f"Below lower band ({bb_position:.2f})"
        elif bb_position > 0.8:
            score -= 0.2
            factors["bollinger"] = f"Above upper band ({bb_position:.2f})"
        else:
            score += 0.05
            factors["bollinger"] = f"Within bands ({bb_position:.2f})"
        
        # RSI
        if rsi_value < 30:
            score += 0.2
            factors["rsi"] = f"Oversold (RSI={rsi_value:.1f})"
        elif rsi_value > 70:
            score -= 0.2
            factors["rsi"] = f"Overbought (RSI={rsi_value:.1f})"
        elif rsi_value < 45:
            score += 0.1
            factors["rsi"] = f"Weak (RSI={rsi_value:.1f})"
        elif rsi_value > 55:
            score -= 0.1
            factors["rsi"] = f"Strong (RSI={rsi_value:.1f})"
        else:
            factors["rsi"] = f"Neutral (RSI={rsi_value:.1f})"
        
        # Recent price action
        recent_return = (closes.iloc[-1] / closes.iloc[-5] - 1) * 100 if len(closes) >= 5 else 0
        if recent_return < -5:
            score += 0.1
            factors["recent"] = f"Sharp drop ({recent_return:.1f}%)"
        elif recent_return > 5:
            score -= 0.1
            factors["recent"] = f"Sharp rise ({recent_return:.1f}%)"
        
        # Signal
        if score > 0.4:
            signal = "BUY"
            confidence = min(85, 55 + score * 40)
        elif score < -0.4:
            signal = "SELL"
            confidence = min(85, 55 + abs(score) * 40)
        else:
            signal = "HOLD"
            confidence = max(45, 60 - abs(score) * 25)
        
        reasoning = f"Mean Reversion: z={z_score:.2f}, BB={bb_position:.2f}, RSI={rsi_value:.1f}, score={score:.3f}"
        
        return StrategySignal(
            strategy=self.name,
            signal=signal,
            confidence=confidence,
            score=score,
            factors=factors,
            reasoning=reasoning,
            metadata={
                "z_score": z_score,
                "bb_position": bb_position,
                "rsi": rsi_value,
                "mean_price": mean_price
            }
        )


class FactorInvestingStrategy(QuantitativeStrategy):
    """
    Factor Investing Strategy
    Analyzes multiple risk factors (value, momentum, quality, size, volatility)
    """
    
    def __init__(self):
        super().__init__("Factor Investing", weight=1.3)
    
    def calculate(self, prices: List, fundamentals: Dict = None, market_data: Dict = None) -> StrategySignal:
        if len(prices) < 60:
            return StrategySignal(
                strategy=self.name,
                signal="HOLD",
                confidence=50,
                score=0,
                factors={"reason": "Insufficient data for factor analysis"},
                reasoning="Need at least 60 days of data"
            )
        
        closes = self._get_prices_array(prices)
        
        # Value factor (simplified using price trend)
        value_score = self._calculate_value_factor(closes, fundamentals or {})
        
        # Momentum factor
        momentum_score = self._calculate_momentum_factor(closes)
        
        # Quality factor (using volatility as proxy)
        quality_score = self._calculate_quality_factor(closes)
        
        # Volatility factor
        vol_score = self._calculate_volatility_factor(returns := closes.pct_change().dropna())
        
        # Size factor (N/A for single asset, default neutral)
        size_score = 0
        
        # Combine factors
        total_score = (
            value_score * 0.25 +
            momentum_score * 0.25 +
            quality_score * 0.25 +
            vol_score * 0.15 +
            size_score * 0.10
        )
        
        factors = {
            "value": value_score,
            "momentum": momentum_score,
            "quality": quality_score,
            "volatility": vol_score,
            "composite": total_score
        }
        
        # Signal
        if total_score > 0.2:
            signal = "BUY"
            confidence = min(85, 60 + total_score * 60)
        elif total_score < -0.2:
            signal = "SELL"
            confidence = min(85, 60 + abs(total_score) * 60)
        else:
            signal = "HOLD"
            confidence = max(45, 55 - abs(total_score) * 20)
        
        reasoning = f"Factor Model: value={value_score:.2f}, momentum={momentum_score:.2f}, quality={quality_score:.2f}, total={total_score:.3f}"
        
        return StrategySignal(
            strategy=self.name,
            signal=signal,
            confidence=confidence,
            score=total_score,
            factors=factors,
            reasoning=reasoning,
            metadata={
                "value_factor": value_score,
                "momentum_factor": momentum_score,
                "quality_factor": quality_score,
                "volatility_factor": vol_score
            }
        )
    
    def _calculate_value_factor(self, closes: pd.Series, fundamentals: Dict) -> float:
        """Value factor: price relative to historical averages"""
        current_price = closes.iloc[-1]
        sma_200 = closes.rolling(200).mean().iloc[-1] if len(closes) >= 200 else closes.mean()
        
        price_to_sma = current_price / sma_200 if sma_200 > 0 else 1
        
        if price_to_sma < 0.85:
            return 0.3  # Undervalued
        elif price_to_sma < 0.95:
            return 0.1
        elif price_to_sma < 1.05:
            return 0
        elif price_to_sma < 1.15:
            return -0.1
        else:
            return -0.3  # Overvalued
    
    def _calculate_momentum_factor(self, closes: pd.Series) -> float:
        """Momentum factor: 12-month returns minus 1-month"""
        if len(closes) < 252:
            return 0
        
        ret_12m = (closes.iloc[-1] / closes.iloc[-252] - 1) if len(closes) >= 252 else 0
        ret_1m = (closes.iloc[-1] / closes.iloc[-21] - 1) if len(closes) >= 21 else 0
        
        # Momentum: recent 12-month minus 1-month (avoid reversal)
        momentum = ret_12m - ret_1m
        
        if momentum > 0.3:
            return 0.3
        elif momentum > 0.1:
            return 0.15
        elif momentum > 0:
            return 0.05
        elif momentum > -0.1:
            return -0.05
        else:
            return -0.2
    
    def _calculate_quality_factor(self, closes: pd.Series) -> float:
        """Quality factor: return consistency (inverse of volatility)"""
        returns = closes.pct_change().dropna()
        
        if len(returns) < 60:
            return 0
        
        # Lower volatility = higher quality
        volatility = returns.tail(60).std() * np.sqrt(252)
        
        if volatility < 0.15:
            return 0.3
        elif volatility < 0.25:
            return 0.15
        elif volatility < 0.40:
            return 0
        else:
            return -0.15
    
    def _calculate_volatility_factor(self, returns: pd.Series) -> float:
        """Volatility factor: low volatility preferred"""
        if len(returns) < 60:
            return 0
        
        volatility = returns.tail(60).std() * np.sqrt(252)
        
        if volatility < 0.10:
            return 0.2
        elif volatility < 0.20:
            return 0.1
        elif volatility < 0.35:
            return 0
        else:
            return -0.1


class EarningsMomentumStrategy(QuantitativeStrategy):
    """
    Earnings Momentum Strategy
    Based on earnings surprises and trends
    """
    
    def __init__(self):
        super().__init__("Earnings Momentum", weight=1.1)
    
    def calculate(self, prices: List, fundamentals: Dict = None, market_data: Dict = None) -> StrategySignal:
        # This strategy relies more on fundamentals
        # Use price-based proxy for earnings momentum
        
        if len(prices) < 20:
            return StrategySignal(
                strategy=self.name,
                signal="HOLD",
                confidence=50,
                score=0,
                factors={"reason": "Insufficient data"},
                reasoning="Need at least 20 days of data"
            )
        
        closes = self._get_prices_array(prices)
        
        # Earnings momentum proxy: accelerated price changes
        ret_5d = (closes.iloc[-1] / closes.iloc[-5] - 1) if len(closes) >= 5 else 0
        ret_20d = (closes.iloc[-1] / closes.iloc[-20] - 1) if len(closes) >= 20 else 0
        ret_60d = (closes.iloc[-1] / closes.iloc[-60] - 1) if len(closes) >= 60 else 0
        
        # Acceleration: recent change in trend
        acceleration = ret_5d - ret_20d
        
        score = 0
        factors = {}
        
        # Earnings acceleration
        if acceleration > 0.05:
            score += 0.25
            factors["acceleration"] = f"Strong ({acceleration*100:.1f}%)"
        elif acceleration > 0.02:
            score += 0.15
            factors["acceleration"] = f"Moderate ({acceleration*100:.1f}%)"
        elif acceleration < -0.05:
            score -= 0.25
            factors["acceleration"] = f"Weakening ({acceleration*100:.1f}%)"
        elif acceleration < -0.02:
            score -= 0.15
            factors["acceleration"] = f"Slowing ({acceleration*100:.1f}%)"
        else:
            factors["acceleration"] = f"Stable ({acceleration*100:.1f}%)"
        
        # Long-term trend
        if ret_60d > 0.2:
            score += 0.2
            factors["lt_trend"] = f"Strong up ({ret_60d*100:.1f}%)"
        elif ret_60d > 0.1:
            score += 0.1
            factors["lt_trend"] = f"Modest up ({ret_60d*100:.1f}%)"
        elif ret_60d < -0.2:
            score -= 0.2
            factors["lt_trend"] = f"Strong down ({ret_60d*100:.1f}%)"
        elif ret_60d < -0.1:
            score -= 0.1
            factors["lt_trend"] = f"Modest down ({ret_60d*100:.1f}%)"
        
        # Signal
        if score > 0.25:
            signal = "BUY"
            confidence = min(80, 55 + score * 60)
        elif score < -0.25:
            signal = "SELL"
            confidence = min(80, 55 + abs(score) * 60)
        else:
            signal = "HOLD"
            confidence = max(45, 60 - abs(score) * 30)
        
        reasoning = f"Earnings Momentum: accel={acceleration*100:.1f}%, 60d={ret_60d*100:.1f}%, score={score:.3f}"
        
        return StrategySignal(
            strategy=self.name,
            signal=signal,
            confidence=confidence,
            score=score,
            factors=factors,
            reasoning=reasoning,
            metadata={
                "acceleration": acceleration,
                "return_60d": ret_60d,
                "return_20d": ret_20d
            }
        )


class TechnicalAnalysisStrategy(QuantitativeStrategy):
    """
    Technical Analysis Strategy
    Uses traditional technical indicators
    """
    
    def __init__(self):
        super().__init__("Technical Analysis", weight=0.9)
        super().__init__("Technical Analysis", weight=0.9)
    
    def calculate(self, prices: List, fundamentals: Dict = None, market_data: Dict = None) -> StrategySignal:
        if len(prices) < 50:
            return StrategySignal(
                strategy=self.name,
                signal="HOLD",
                confidence=50,
                score=0,
                factors={"reason": "Insufficient data for technical analysis"},
                reasoning="Need at least 50 days of data"
            )
        
        closes = self._get_prices_array(prices)
        
        # Calculate indicators
        sma_20 = closes.rolling(20).mean()
        sma_50 = closes.rolling(50).mean()
        sma_200 = closes.rolling(200).mean()
        
        # EMA
        ema_12 = closes.ewm(span=12).mean()
        ema_26 = closes.ewm(span=26).mean()
        
        # MACD
        macd = ema_12 - ema_26
        signal_line = macd.ewm(span=9).mean()
        macd_histogram = macd - signal_line
        
        # RSI (as Series)
        delta = closes.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rs = rs.replace([np.inf, -np.inf], np.nan)
        rsi = 100 - (100 / (1 + rs))
        rsi = rsi.fillna(50)
        
        # Stochastic
        low_14 = closes.rolling(14).min()
        high_14 = closes.rolling(14).max()
        stoch_k = 100 * (closes - low_14) / (high_14 - low_14)
        stoch_d = stoch_k.rolling(3).mean()
        
        # Bollinger Bands
        bb_sma = closes.rolling(20).mean()
        bb_std = closes.rolling(20).std()
        bb_upper = bb_sma + 2 * bb_std
        bb_lower = bb_sma - 2 * bb_std
        
        score = 0
        factors = {}
        
        # Trend (SMA)
        if closes.iloc[-1] > sma_200.iloc[-1] > sma_50.iloc[-1]:
            score += 0.2
            factors["trend"] = "Strong uptrend (price > SMA200 > SMA50)"
        elif closes.iloc[-1] > sma_50.iloc[-1] > sma_200.iloc[-1]:
            score += 0.1
            factors["trend"] = "Moderate uptrend (price > SMA50)"
        elif closes.iloc[-1] < sma_200.iloc[-1] < sma_50.iloc[-1]:
            score -= 0.2
            factors["trend"] = "Strong downtrend"
        elif closes.iloc[-1] < sma_50.iloc[-1] < sma_200.iloc[-1]:
            score -= 0.1
            factors["trend"] = "Moderate downtrend"
        else:
            factors["trend"] = "Sideways"
        
        # MACD
        if macd_histogram.iloc[-1] > 0 and macd_histogram.iloc[-2] < 0:
            score += 0.15
            factors["macd"] = "Bullish crossover"
        elif macd_histogram.iloc[-1] < 0 and macd_histogram.iloc[-2] > 0:
            score -= 0.15
            factors["macd"] = "Bearish crossover"
        elif macd.iloc[-1] > signal_line.iloc[-1]:
            score += 0.05
            factors["macd"] = "Above signal"
        else:
            score -= 0.05
            factors["macd"] = "Below signal"
        
        # RSI
        if rsi.iloc[-1] < 30:
            score += 0.15
            factors["rsi"] = f"Oversold ({rsi.iloc[-1]:.1f})"
        elif rsi.iloc[-1] > 70:
            score -= 0.15
            factors["rsi"] = f"Overbought ({rsi.iloc[-1]:.1f})"
        elif 45 <= rsi.iloc[-1] <= 55:
            score += 0.05
            factors["rsi"] = f"Neutral ({rsi.iloc[-1]:.1f})"
        
        # Stochastic
        if stoch_k.iloc[-1] < 20:
            score += 0.1
            factors["stoch"] = f"Oversold ({stoch_k.iloc[-1]:.1f})"
        elif stoch_k.iloc[-1] > 80:
            score -= 0.1
            factors["stoch"] = f"Overbought ({stoch_k.iloc[-1]:.1f})"
        elif stoch_k.iloc[-1] > stoch_d.iloc[-1]:
            score += 0.05
            factors["stoch"] = "Bullish"
        else:
            score -= 0.05
            factors["stoch"] = "Bearish"
        
        # Signal
        if score > 0.35:
            signal = "BUY"
            confidence = min(80, 55 + score * 50)
        elif score < -0.35:
            signal = "SELL"
            confidence = min(80, 55 + abs(score) * 50)
        else:
            signal = "HOLD"
            confidence = max(45, 60 - abs(score) * 25)
        
        reasoning = f"Technical: score={score:.3f}, RSI={rsi.iloc[-1]:.1f}, MACD={macd_histogram.iloc[-1]:.2f}"
        
        return StrategySignal(
            strategy=self.name,
            signal=signal,
            confidence=confidence,
            score=score,
            factors=factors,
            reasoning=reasoning,
            metadata={
                "rsi": rsi.iloc[-1],
                "macd_hist": macd_histogram.iloc[-1],
                "stoch_k": stoch_k.iloc[-1],
                "price_vs_sma50": (closes.iloc[-1] / sma_50.iloc[-1] - 1) * 100
            }
        )


# ============ STRATEGY ORCHESTRATOR ============

class StrategyOrchestrator:
    """
    Orchestrates multiple strategies
    Runs all strategies in parallel
    Aggregates results
    Returns most accurate/weighted signal
    """
    
    def __init__(self):
        self.strategies = {
            StrategyType.JIM_SIMMONS: JimSimonsStrategy(),
            StrategyType.QUANT_MOMENTUM: QuantitativeMomentumStrategy(),
            StrategyType.MEAN_REVERSION: MeanReversionStrategy(),
            StrategyType.FACTOR_INVESTING: FactorInvestingStrategy(),
            StrategyType.EARNINGS_MOMENTUM: EarningsMomentumStrategy(),
            StrategyType.TECHNICAL_ANALYSIS: TechnicalAnalysisStrategy(),
        }
    
    def run_all_strategies(
        self,
        prices: List,
        fundamentals: Dict = None,
        market_data: Dict = None
    ) -> AggregatedSignal:
        """
        Run all strategies and aggregate results
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        signals = []
        
        # Run strategies in parallel
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {
                strategy_type: executor.submit(
                    strategy.calculate, prices, fundamentals, market_data
                )
                for strategy_type, strategy in self.strategies.items()
            }
            
            for strategy_type, future in futures.items():
                try:
                    signal = future.result()
                    signals.append({
                        "strategy": signal.strategy,
                        "type": strategy_type.value,
                        "signal": signal.signal,
                        "confidence": signal.confidence,
                        "score": signal.score,
                        "factors": signal.factors,
                        "reasoning": signal.reasoning,
                        "weight": self.strategies[strategy_type].weight,
                        "metadata": signal.metadata
                    })
                except Exception as e:
                    signals.append({
                        "strategy": strategy_type.value,
                        "signal": "ERROR",
                        "confidence": 0,
                        "score": 0,
                        "factors": {"error": str(e)},
                        "reasoning": f"Strategy failed: {e}",
                        "weight": self.strategies[strategy_type].weight
                    })
        
        # Aggregate signals
        return self._aggregate_signals(signals)
    
    def _aggregate_signals(self, signals: List[Dict]) -> AggregatedSignal:
        """Aggregate signals from all strategies"""
        buy_count = sum(1 for s in signals if s["signal"] == "BUY")
        sell_count = sum(1 for s in signals if s["signal"] == "SELL")
        hold_count = sum(1 for s in signals if s["signal"] == "HOLD")
        
        # Weighted scoring
        total_weight = sum(s["weight"] for s in signals)
        weighted_score = sum(s["score"] * s["weight"] for s in signals) / total_weight if total_weight > 0 else 0
        
        # Weighted confidence
        total_weighted_conf = sum(s["confidence"] * s["weight"] for s in signals)
        avg_confidence = total_weighted_conf / total_weight if total_weight > 0 else 0
        
        # Determine final signal
        if buy_count > sell_count and buy_count >= hold_count:
            final_signal = "BUY"
        elif sell_count > buy_count and sell_count >= hold_count:
            final_signal = "SELL"
        else:
            # Use weighted score for HOLD cases
            if weighted_score > 0.1:
                final_signal = "BUY"
            elif weighted_score < -0.1:
                final_signal = "SELL"
            else:
                final_signal = "HOLD"
        
        # Calculate consensus level
        max_count = max(buy_count, sell_count, hold_count)
        consensus_pct = max_count / len(signals)
        
        if consensus_pct >= 0.7:
            consensus_level = "HIGH"
        elif consensus_pct >= 0.5:
            consensus_level = "MEDIUM"
        else:
            consensus_level = "LOW"
        
        # Final confidence based on consensus and weighted score
        final_confidence = avg_confidence * (0.5 + consensus_pct * 0.5)
        final_confidence = min(95, max(20, final_confidence))
        
        return AggregatedSignal(
            final_signal=final_signal,
            final_confidence=final_confidence,
            total_strategies=len(signals),
            buy_count=buy_count,
            sell_count=sell_count,
            hold_count=hold_count,
            avg_confidence=avg_confidence,
            weighted_score=weighted_score,
            strategy_details=signals,
            consensus_level=consensus_level
        )


# ============ CONVENIENCE FUNCTIONS ============

def analyze_with_all_strategies(
    prices: List,
    fundamentals: Dict = None,
    market_data: Dict = None
) -> AggregatedSignal:
    """
    Convenience function to run all strategies
    """
    orchestrator = StrategyOrchestrator()
    return orchestrator.run_all_strategies(prices, fundamentals, market_data)


if __name__ == "__main__":
    print("=== Testing Quantitative Strategies ===\n")
    
    # Create dummy price data
    class DummyPrice:
        def __init__(self, close):
            self.close = close
    
    import random
    prices = [DummyPrice(100 + random.gauss(0, 2)) for _ in range(100)]
    
    # Run all strategies
    orchestrator = StrategyOrchestrator()
    result = orchestrator.run_all_strategies(prices)
    
    print(f"Final Signal: {result.final_signal}")
    print(f"Confidence: {result.final_confidence:.1f}%")
    print(f"Consensus: {result.consensus_level}")
    print(f"Buy: {result.buy_count}, Sell: {result.sell_count}, Hold: {result.hold_count}")
    print(f"\nStrategy Breakdown:")
    for detail in result.strategy_details:
        print(f"  {detail['strategy']}: {detail['signal']} ({detail['confidence']:.0f}%) - {detail['reasoning'][:50]}...")
    
    print("\n=== Test Complete ===")
