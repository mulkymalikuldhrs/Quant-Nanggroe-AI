"""
ENTRY ANALYSIS - Intelligent Entry Strategy Selection
Analyzes all signals to determine optimal entry strategy and parameters
"""

import sys
import os
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import statistics

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.integrations.quant_strategies_analysis import quant_strategies_analysis
from src.integrations.retail_strategies import retail_strategies
from src.integrations.enhanced_sentiment_agent import enhanced_sentiment_agent


@dataclass
class EntryRecommendation:
    """Entry recommendation with full analysis"""

    primary_strategy: str
    entry_type: str  # 'quantitative', 'retail', 'sentiment', 'combined'
    confidence_score: float
    risk_level: str  # 'low', 'medium', 'high'
    time_horizon: str  # 'short', 'medium', 'long'
    entry_price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    position_size: Optional[float]
    risk_reward_ratio: Optional[float]
    reasoning: str
    alternative_strategies: List[str]
    market_conditions: Dict[str, Any]
    execution_priority: str  # 'high', 'medium', 'low'


class EntryAnalysis:
    """Intelligent entry analysis and strategy selection"""

    def __init__(self):
        self.confidence_thresholds = {"high": 0.8, "medium": 0.6, "low": 0.4}
        self.risk_multipliers = {"low": 1.0, "medium": 0.7, "high": 0.4}

    def analyze_entry_opportunities(self, ticker: str, market_data: Optional[Dict] = None, portfolio_state: Optional[Dict] = None) -> EntryRecommendation:
        """
        Comprehensive entry analysis for a ticker
        Returns the best entry strategy with full parameters
        """
        # Get all signal sources
        quant_signals = quant_strategies_analysis.analyze_all_strategies(ticker)
        retail_signals = self._get_retail_signals(ticker)
        sentiment_analysis = enhanced_sentiment_agent.get_market_sentiment(ticker)

        # Analyze market conditions
        market_conditions = self._analyze_market_conditions(market_data or {})

        # Evaluate all strategies
        strategy_scores = self._score_all_strategies(quant_signals, retail_signals, sentiment_analysis, market_conditions)

        # Select best entry strategy
        best_strategy = self._select_best_strategy(strategy_scores)

        # Generate detailed recommendation
        recommendation = self._generate_recommendation(best_strategy, quant_signals, retail_signals, sentiment_analysis, market_conditions, portfolio_state or {})

        return recommendation

    def _get_retail_signals(self, ticker: str) -> List[Any]:
        """Get retail strategy signals"""
        retail_signals = []

        # Note: In production, this should fetch real market data.
        import pandas as pd
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(f"Using placeholder data for {ticker} - connect to a real data provider for production use")
        data = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

        current_price = 0.0  # Placeholder
        portfolio_value = 0  # Placeholder

        # Test key retail strategies
        strategies_to_test = ["scalping_momentum", "swing_trading", "breakout_trading"]

        for strategy_name in strategies_to_test:
            signal = retail_strategies.execute_strategy(strategy_name, data, current_price, portfolio_value)
            if signal:
                retail_signals.append(signal)

        return retail_signals

    def _analyze_market_conditions(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze current market conditions"""
        conditions = {"trend": "neutral", "volatility": "medium", "momentum": "neutral", "liquidity": "good", "risk_level": "medium", "market_phase": "sideways"}

        # Analyze based on available data
        if "volatility" in market_data:
            vol = market_data["volatility"]
            if vol > 0.3:
                conditions["volatility"] = "high"
                conditions["risk_level"] = "high"
            elif vol < 0.15:
                conditions["volatility"] = "low"
                conditions["risk_level"] = "low"

        if "trend_strength" in market_data:
            trend = market_data["trend_strength"]
            if trend > 0.7:
                conditions["trend"] = "strong"
                conditions["market_phase"] = "trending"
            elif trend < 0.3:
                conditions["market_phase"] = "ranging"

        return conditions

    def _score_all_strategies(self, quant_signals: Dict, retail_signals: List, sentiment: Dict, market_conditions: Dict) -> Dict[str, Dict]:
        """Score all available strategies"""
        strategy_scores = {}

        # Score quantitative strategies
        for strategy_name, signal in quant_signals.items():
            if signal.action in ["BUY", "SELL"]:
                base_score = signal.confidence

                # Adjust based on market conditions
                market_multiplier = self._get_market_multiplier(signal, market_conditions)

                # Adjust based on risk level
                risk_multiplier = self.risk_multipliers.get(signal.risk_level, 1.0)

                final_score = base_score * market_multiplier * risk_multiplier

                strategy_scores[strategy_name] = {"score": final_score, "signal": signal, "type": "quantitative", "timeframe": signal.timeframe, "risk_level": getattr(signal, "risk_level", "medium") if hasattr(signal, "risk_level") else "medium"}

        # Score retail strategies
        for signal in retail_signals:
            if signal.action in ["BUY", "SELL"]:
                base_score = signal.strength

                # Retail strategies are generally higher risk
                risk_multiplier = 0.8  # Slightly lower due to higher risk

                # Adjust for market conditions
                market_multiplier = self._get_market_multiplier(signal, market_conditions)

                final_score = base_score * market_multiplier * risk_multiplier

                strategy_scores[signal.strategy_name] = {"score": final_score, "signal": signal, "type": "retail", "timeframe": signal.timeframe, "risk_level": getattr(signal, "risk_level", "high") if hasattr(signal, "risk_level") else "high"}

        # Score sentiment-based strategy
        if sentiment and sentiment.get("overall_sentiment") in ["positive", "negative"]:
            sentiment_score = sentiment.get("confidence", 0.5)
            sentiment_multiplier = 0.7  # Sentiment is supportive but not primary

            strategy_scores["sentiment_based"] = {"score": sentiment_score * sentiment_multiplier, "signal": sentiment, "type": "sentiment", "timeframe": "1d", "risk_level": "medium"}

        return strategy_scores

    def _get_market_multiplier(self, signal: Any, market_conditions: Dict) -> float:
        """Get market condition multiplier for strategy"""
        multiplier = 1.0

        # Adjust based on timeframe alignment
        signal_timeframe = getattr(signal, "timeframe", "1d")
        market_phase = market_conditions.get("market_phase", "sideways")

        # Scalping works better in ranging markets
        if "scalping" in getattr(signal, "strategy_name", "").lower():
            if market_phase == "ranging":
                multiplier *= 1.2
            elif market_phase == "trending":
                multiplier *= 0.8

        # Swing trading works better in trending markets
        if "swing" in getattr(signal, "strategy_name", "").lower():
            if market_phase == "trending":
                multiplier *= 1.2
            elif market_phase == "ranging":
                multiplier *= 0.9

        # Adjust for volatility
        volatility = market_conditions.get("volatility", "medium")
        if hasattr(signal, "strategy_name"):
            strategy_name = signal.strategy_name.lower()
            if "breakout" in strategy_name and volatility == "high":
                multiplier *= 1.3  # Breakouts work better in high volatility
            elif "range" in strategy_name and volatility == "low":
                multiplier *= 1.2  # Range trading better in low volatility

        return multiplier

    def _select_best_strategy(self, strategy_scores: Dict[str, Dict]) -> Dict[str, Any]:
        """Select the best strategy from scored options"""
        if not strategy_scores:
            return {"name": "hold", "type": "neutral", "score": 0.0, "signal": None}

        # Find strategy with highest score
        best_strategy_name = max(strategy_scores.keys(), key=lambda k: strategy_scores[k]["score"])
        best_strategy = strategy_scores[best_strategy_name]

        return {"name": best_strategy_name, "type": best_strategy["type"], "score": best_strategy["score"], "signal": best_strategy["signal"], "timeframe": best_strategy["timeframe"], "risk_level": best_strategy["risk_level"]}

    def _generate_recommendation(self, best_strategy: Dict, quant_signals: Dict, retail_signals: List, sentiment: Dict, market_conditions: Dict, portfolio_state: Dict) -> EntryRecommendation:
        """Generate detailed entry recommendation"""

        signal = best_strategy["signal"]
        strategy_name = best_strategy["name"]

        # Determine entry parameters
        entry_price, stop_loss, take_profit, position_size, rr_ratio = self._calculate_entry_parameters(signal, best_strategy, portfolio_state)

        # Determine time horizon
        timeframe = getattr(signal, "timeframe", "1d")
        if "scalping" in strategy_name.lower():
            time_horizon = "short"
        elif "swing" in strategy_name.lower() or "position" in strategy_name.lower():
            time_horizon = "medium"
        else:
            time_horizon = "medium"

        # Determine execution priority
        if best_strategy["score"] > self.confidence_thresholds["high"]:
            execution_priority = "high"
        elif best_strategy["score"] > self.confidence_thresholds["medium"]:
            execution_priority = "medium"
        else:
            execution_priority = "low"

        # Generate reasoning
        reasoning = self._generate_reasoning(best_strategy, quant_signals, retail_signals, sentiment, market_conditions)

        # Get alternative strategies
        alternative_strategies = self._get_alternative_strategies(best_strategy, quant_signals, retail_signals)

        return EntryRecommendation(
            primary_strategy=strategy_name,
            entry_type=best_strategy["type"],
            confidence_score=best_strategy["score"],
            risk_level=best_strategy["risk_level"],
            time_horizon=time_horizon,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=position_size,
            risk_reward_ratio=rr_ratio,
            reasoning=reasoning,
            alternative_strategies=alternative_strategies,
            market_conditions=market_conditions,
            execution_priority=execution_priority,
        )

    def _calculate_entry_parameters(self, signal: Any, strategy_info: Dict, portfolio_state: Dict) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float], Optional[float]]:
        """Calculate entry parameters based on signal and strategy"""

        # Get current price (mock for now)
        current_price = getattr(signal, "entry_price", None)
        if current_price is None:
            current_price = 100.0  # Mock price

        # Calculate stop loss and take profit based on strategy type
        strategy_name = strategy_info["name"].lower()

        if "scalping" in strategy_name:
            # Tight stops for scalping
            stop_loss = current_price * 0.998 if getattr(signal, "action", "") == "BUY" else current_price * 1.002
            take_profit = current_price * 1.005 if signal.action == "BUY" else current_price * 0.995
            rr_ratio = 2.5

        elif "swing" in strategy_name:
            # Wider stops for swing trading
            stop_loss = current_price * 0.97 if signal.action == "BUY" else current_price * 1.03
            take_profit = current_price * 1.05 if signal.action == "BUY" else current_price * 0.95
            rr_ratio = 3.0

        elif "breakout" in strategy_name:
            # Breakout stops based on recent levels
            stop_loss = getattr(signal, "stop_loss", current_price * 0.98 if signal.action == "BUY" else current_price * 1.02)
            take_profit = getattr(signal, "take_profit", current_price * 1.03 if signal.action == "BUY" else current_price * 0.97)
            rr_ratio = 2.0

        else:
            # Default parameters
            stop_loss = current_price * 0.95 if signal.action == "BUY" else current_price * 1.05
            take_profit = current_price * 1.10 if signal.action == "BUY" else current_price * 0.90
            rr_ratio = 2.0

        # Calculate position size based on risk management
        portfolio_value = portfolio_state.get("cash", 10000)
        risk_per_trade = portfolio_value * 0.02  # 2% risk per trade

        if stop_loss and current_price:
            risk_amount = abs(current_price - stop_loss)
            if risk_amount > 0:
                position_size = risk_per_trade / risk_amount
                # Limit position size to reasonable bounds
                position_size = min(position_size, portfolio_value * 0.1 / current_price)
            else:
                position_size = 100  # Default
        else:
            position_size = 100  # Default

        return current_price, stop_loss, take_profit, position_size, rr_ratio

    def _generate_reasoning(self, best_strategy: Dict, quant_signals: Dict, retail_signals: List, sentiment: Dict, market_conditions: Dict) -> str:
        """Generate detailed reasoning for the recommendation"""

        signal = best_strategy["signal"]
        strategy_name = best_strategy["name"]
        strategy_type = best_strategy["type"]

        reasoning_parts = []

        # Primary strategy reasoning
        if strategy_type == "quantitative":
            reasoning_parts.append(f"Selected {strategy_name} quantitative strategy with {best_strategy['score']:.1%} confidence")
        elif strategy_type == "retail":
            reasoning_parts.append(f"Selected {strategy_name} retail strategy with {best_strategy['score']:.1%} confidence")
        elif strategy_type == "sentiment":
            reasoning_parts.append(f"Selected sentiment-based strategy with {best_strategy['score']:.1%} confidence")

        # Market conditions
        market_phase = market_conditions.get("market_phase", "unknown")
        volatility = market_conditions.get("volatility", "unknown")
        reasoning_parts.append(f"Market conditions: {market_phase} phase with {volatility} volatility")

        # Supporting signals
        supporting_signals = []

        # Check for supporting quant signals
        buy_quant = sum(1 for s in quant_signals.values() if getattr(s, "action", "") == "BUY")
        sell_quant = sum(1 for s in quant_signals.values() if getattr(s, "action", "") == "SELL")

        if buy_quant > 0 or sell_quant > 0:
            supporting_signals.append(f"{buy_quant + sell_quant} quantitative strategies aligned")

        # Check for supporting retail signals
        buy_retail = sum(1 for s in retail_signals if getattr(s, "action", "") == "BUY")
        sell_retail = sum(1 for s in retail_signals if getattr(s, "action", "") == "SELL")

        if buy_retail > 0 or sell_retail > 0:
            supporting_signals.append(f"{buy_retail + sell_retail} retail strategies supportive")

        # Sentiment support
        if sentiment and sentiment.get("overall_sentiment") == getattr(signal, "action", "").lower():
            supporting_signals.append("sentiment analysis aligned")

        if supporting_signals:
            reasoning_parts.append(f"Supporting signals: {', '.join(supporting_signals)}")

        return ". ".join(reasoning_parts)

    def _get_alternative_strategies(self, best_strategy: Dict, quant_signals: Dict, retail_signals: List) -> List[str]:
        """Get alternative strategies for consideration"""
        alternatives = []

        # Add high-confidence alternatives from quantitative strategies
        for name, signal in quant_signals.items():
            if name != best_strategy["name"] and getattr(signal, "confidence", 0) > self.confidence_thresholds["medium"]:
                alternatives.append(f"{name} (quantitative)")

        # Add strong retail strategies
        for signal in retail_signals:
            if signal.strategy_name != best_strategy["name"] and getattr(signal, "strength", 0) > self.confidence_thresholds["medium"]:
                alternatives.append(f"{signal.strategy_name} (retail)")

        return alternatives[:3]  # Return top 3 alternatives

    def get_entry_summary(self, ticker: str) -> str:
        """Get a concise entry summary"""
        try:
            recommendation = self.analyze_entry_opportunities(ticker)

            summary = f"""
🎯 ENTRY ANALYSIS - {ticker}

Primary Strategy: {recommendation.primary_strategy} ({recommendation.entry_type})
Confidence: {recommendation.confidence_score:.1%}
Risk Level: {recommendation.risk_level}
Time Horizon: {recommendation.time_horizon}

Entry Parameters:
• Entry Price: ${recommendation.entry_price:.2f}
• Stop Loss: ${recommendation.stop_loss:.2f}
• Take Profit: ${recommendation.take_profit:.2f}
• Position Size: {recommendation.position_size:.0f} shares
• Risk/Reward: {recommendation.risk_reward_ratio:.1f}

Reasoning: {recommendation.reasoning}

Alternative Strategies: {', '.join(recommendation.alternative_strategies[:2])}
Execution Priority: {recommendation.execution_priority.upper()}
"""

            return summary

        except Exception as e:
            return f"❌ Error generating entry summary: {e}"


# Global instance
entry_analysis = EntryAnalysis()
