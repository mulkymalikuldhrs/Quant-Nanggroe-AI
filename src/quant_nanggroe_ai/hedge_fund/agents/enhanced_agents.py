"""
AI Hedge Fund - Enhanced Agents
Including Jim Simons Quant Agent, Technical Analyst, Factor Investor, etc.
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pathlib import Path
import sys

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.tools.advanced_data_provider import data_provider
from src.strategies.quantitative_strategies import StrategyOrchestrator, analyze_with_all_strategies, StrategyType
from src.utils.analysts import ANALYST_ORDER

# Integrated components
try:
    from src.integrations.enhanced_sentiment_agent import enhanced_sentiment_agent
    from src.integrations.enhanced_autonomous_trader import enhanced_autonomous_trader
    from src.integrations.enhanced_risk_analyzer import enhanced_risk_analyzer

    INTEGRATIONS_AVAILABLE = True
except ImportError:
    INTEGRATIONS_AVAILABLE = False
    print("⚠️  Integrated components not available, using basic functionality")


# ============ DATA MODELS ============


@dataclass
class EnhancedSignal:
    signal: str
    confidence: float
    reasoning: str
    factors: Dict[str, Any]
    strategy_type: str
    metadata: Dict[str, Any] = None


# ============ INTEGRATED MULTI-AGENT SYSTEM ============


def run_enhanced_multi_agent_analysis(tickers: List[str], context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Enhanced multi-agent analysis with integrated components
    Combines traditional agents with advanced integrations
    """
    if context is None:
        context = {}

    results = {}

    # Initialize integrations if available
    sentiment_data = {}
    autonomous_decisions = {}
    risk_analysis = {}

    if INTEGRATIONS_AVAILABLE:
        # Initialize integrated components
        enhanced_sentiment_agent.initialize()
        enhanced_autonomous_trader.initialize()
        enhanced_risk_analyzer.initialize()

        # Get sentiment analysis for all tickers
        for ticker in tickers:
            sentiment_data[ticker] = enhanced_sentiment_agent.get_market_sentiment(ticker)

    for ticker in tickers:
        # Get traditional strategy analysis
        strategy_results = analyze_with_all_strategies(ticker, [], context)

        # Enhanced analysis with integrated components
        enhanced_analysis = {"traditional_signals": strategy_results, "sentiment_analysis": sentiment_data.get(ticker, {}), "autonomous_decision": None, "risk_assessment": None}

        # Add autonomous trading decision if available
        if INTEGRATIONS_AVAILABLE and enhanced_autonomous_trader.initialized:
            market_data = context.get("market_data", {}).get(ticker, {})
            portfolio_state = context.get("portfolio", {"cash": 10000, "positions": {}})
            autonomous_decision = enhanced_autonomous_trader.generate_autonomous_decision(ticker, market_data, portfolio_state)
            enhanced_analysis["autonomous_decision"] = autonomous_decision

        # Add risk analysis if available
        if INTEGRATIONS_AVAILABLE and enhanced_risk_analyzer.initialized:
            portfolio = context.get("portfolio", {"cash": 10000, "positions": {}})
            market_data = context.get("market_data", {})
            risk_analysis = enhanced_risk_analyzer.analyze_portfolio_risk(portfolio, market_data)
            enhanced_analysis["risk_assessment"] = risk_analysis

            # Check kill switch
            if enhanced_risk_analyzer.check_kill_switch(risk_analysis):
                enhanced_analysis["kill_switch_activated"] = True

        results[ticker] = enhanced_analysis

    return {"tickers_analyzed": tickers, "results": results, "integrations_active": INTEGRATIONS_AVAILABLE, "timestamp": datetime.now().isoformat()}


# ============ JIM SIMMONS AGENT ============


@dataclass
class JimSimonsOutput:
    signal: str
    confidence: int
    reasoning: str
    statistical_model: str
    z_score: float
    momentum: float
    sharpe_ratio: float
    volatility_regime: str
    pattern_signal: str


def jim_simmons_agent(ticker: str, prices: List, fundamentals: Dict = None, market_data: Dict = None) -> JimSimonsOutput:
    """
    Jim Simons-inspired quantitative analyst
    Uses statistical models and pattern recognition
    """
    from src.strategies.quantitative_strategies import JimSimonsStrategy

    strategy = JimSimonsStrategy()
    signal = strategy.calculate(prices, fundamentals, market_data)

    return JimSimonsOutput(
        signal=signal.signal,
        confidence=int(signal.confidence),
        reasoning=signal.reasoning,
        statistical_model="Medallion-inspired statistical model",
        z_score=signal.metadata.get("z_score", 0) if signal.metadata else 0,
        momentum=signal.metadata.get("momentum", 0) if signal.metadata else 0,
        sharpe_ratio=signal.metadata.get("sharpe", 0) if signal.metadata else 0,
        volatility_regime="Normal" if signal.metadata.get("volatility_ratio", 1) < 1.5 else "Elevated",
        pattern_signal=signal.factors.get("mean_reversion", "Neutral"),
    )


# ============ QUANTITATIVE ANALYST AGENT ============


@dataclass
class QuantAnalystOutput:
    signal: str
    confidence: int
    reasoning: str
    momentum_scores: Dict[str, float]
    trend_strength: float
    risk_adjusted_score: float


def quantitative_analyst_agent(ticker: str, prices: List, fundamentals: Dict = None, market_data: Dict = None) -> QuantAnalystOutput:
    """
    Quantitative Momentum Analyst
    Analyzes price momentum across multiple timeframes
    """
    from src.strategies.quantitative_strategies import QuantitativeMomentumStrategy

    strategy = QuantitativeMomentumStrategy()
    signal = strategy.calculate(prices, fundamentals, market_data)

    return QuantAnalystOutput(
        signal=signal.signal,
        confidence=int(signal.confidence),
        reasoning=signal.reasoning,
        momentum_scores={"5_day": signal.metadata.get("momentum_5d", 0) if signal.metadata else 0, "10_day": signal.metadata.get("momentum_10d", 0) if signal.metadata else 0, "20_day": signal.metadata.get("momentum_20d", 0) if signal.metadata else 0},
        trend_strength=abs(signal.metadata.get("risk_adj_momentum", 0)) if signal.metadata else 0,
        risk_adjusted_score=signal.metadata.get("risk_adj_momentum", 0) if signal.metadata else 0,
    )


# ============ TECHNICAL ANALYST AGENT ============


@dataclass
class TechnicalAnalystOutput:
    signal: str
    confidence: int
    reasoning: str
    indicators: Dict[str, float]
    trend_status: str
    support_level: float
    resistance_level: float


def technical_analyst_agent(ticker: str, prices: List, fundamentals: Dict = None, market_data: Dict = None) -> TechnicalAnalystOutput:
    """
    Technical Analysis Agent
    Uses RSI, MACD, Bollinger Bands, Moving Averages
    """
    from src.strategies.quantitative_strategies import TechnicalAnalysisStrategy

    strategy = TechnicalAnalysisStrategy()
    signal = strategy.calculate(prices, fundamentals, market_data)

    closes = [p.close for p in prices if hasattr(p, "close")] if prices else []

    # Calculate support/resistance
    if closes:
        support = min(closes[-20:]) if len(closes) >= 20 else min(closes)
        resistance = max(closes[-20:]) if len(closes) >= 20 else max(closes)
    else:
        support = resistance = 0

    return TechnicalAnalystOutput(
        signal=signal.signal,
        confidence=int(signal.confidence),
        reasoning=signal.reasoning,
        indicators={"rsi": signal.metadata.get("rsi", 50) if signal.metadata else 50, "macd_hist": signal.metadata.get("macd_hist", 0) if signal.metadata else 0, "stochastic": signal.metadata.get("stoch_k", 50) if signal.metadata else 50, "price_vs_sma50": signal.metadata.get("price_vs_sma50", 0) if signal.metadata else 0},
        trend_status=signal.factors.get("trend", "Unknown"),
        support_level=support,
        resistance_level=resistance,
    )


# ============ FACTOR INVESTOR AGENT ============


@dataclass
class FactorInvestorOutput:
    signal: str
    confidence: int
    reasoning: str
    factor_scores: Dict[str, float]
    composite_score: float
    factor_exposure: Dict[str, str]


def factor_investor_agent(ticker: str, prices: List, fundamentals: Dict = None, market_data: Dict = None) -> FactorInvestorOutput:
    """
    Factor Investing Agent
    Analyzes value, momentum, quality, volatility factors
    """
    from src.strategies.quantitative_strategies import FactorInvestingStrategy

    strategy = FactorInvestingStrategy()
    signal = strategy.calculate(prices, fundamentals, market_data)

    return FactorInvestorOutput(
        signal=signal.signal,
        confidence=int(signal.confidence),
        reasoning=signal.reasoning,
        factor_scores={"value": signal.factors.get("value", 0), "momentum": signal.factors.get("momentum", 0), "quality": signal.factors.get("quality", 0), "volatility": signal.factors.get("volatility", 0)},
        composite_score=signal.factors.get("composite", 0),
        factor_exposure={"value": "Underweight" if signal.factors.get("value", 0) < 0 else "Overweight", "momentum": "Long" if signal.factors.get("momentum", 0) > 0 else "Short", "quality": "High" if signal.factors.get("quality", 0) > 0 else "Low", "volatility": "Low" if signal.factors.get("volatility", 0) > 0 else "High"},
    )


# ============ EARNINGS MOMENTUM AGENT ============


@dataclass
class EarningsMomentumOutput:
    signal: str
    confidence: int
    reasoning: str
    acceleration: float
    earnings_trend: str
    surprise_proxy: float


def earnings_momentum_agent(ticker: str, prices: List, fundamentals: Dict = None, market_data: Dict = None) -> EarningsMomentumOutput:
    """
    Earnings Momentum Agent
    Analyzes earnings acceleration and trends
    """
    from src.strategies.quantitative_strategies import EarningsMomentumStrategy

    strategy = EarningsMomentumStrategy()
    signal = strategy.calculate(prices, fundamentals, market_data)

    accel = signal.metadata.get("acceleration", 0) if signal.metadata else 0
    ret_60d = signal.metadata.get("return_60d", 0) if signal.metadata else 0

    return EarningsMomentumOutput(signal=signal.signal, confidence=int(signal.confidence), reasoning=signal.reasoning, acceleration=accel, earnings_trend="Accelerating" if accel > 0.02 else "Decelerating" if accel < -0.02 else "Stable", surprise_proxy=ret_60d)


# ============ MEAN REVERSION AGENT ============


@dataclass
class MeanReversionOutput:
    signal: str
    confidence: int
    reasoning: str
    z_score: float
    rsi: float
    bb_position: float
    mean_price: float


def mean_reversion_agent(ticker: str, prices: List, fundamentals: Dict = None, market_data: Dict = None) -> MeanReversionOutput:
    """
    Mean Reversion Agent
    Identifies oversold/overbought conditions
    """
    from src.strategies.quantitative_strategies import MeanReversionStrategy

    strategy = MeanReversionStrategy()
    signal = strategy.calculate(prices, fundamentals, market_data)

    return MeanReversionOutput(signal=signal.signal, confidence=int(signal.confidence), reasoning=signal.reasoning, z_score=signal.metadata.get("z_score", 0) if signal.metadata else 0, rsi=signal.metadata.get("rsi", 50) if signal.metadata else 50, bb_position=signal.metadata.get("bb_position", 0) if signal.metadata else 0, mean_price=signal.metadata.get("mean_price", 0) if signal.metadata else 0)


# ============ MULTI-AGENT ORCHESTRATOR ============


@dataclass
class MultiAgentAnalysis:
    final_signal: str
    final_confidence: float
    consensus_level: str
    agents_called: List[str]
    signals: List[Dict]
    aggregated_result: Dict


def run_multi_agent_analysis(ticker: str, prices: List, fundamentals: Dict = None, market_data: Dict = None, agent_types: List[str] = None) -> MultiAgentAnalysis:
    """
    Run multiple agents and aggregate their results
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    # Default agents
    if agent_types is None:
        agent_types = ["jim_simmons", "quantitative_analyst", "technical_analyst", "factor_investor", "earnings_momentum", "mean_reversion"]

    agent_functions = {
        "jim_simmons": lambda: jim_simmons_agent(ticker, prices, fundamentals, market_data),
        "quantitative_analyst": lambda: quantitative_analyst_agent(ticker, prices, fundamentals, market_data),
        "technical_analyst": lambda: technical_analyst_agent(ticker, prices, fundamentals, market_data),
        "factor_investor": lambda: factor_investor_agent(ticker, prices, fundamentals, market_data),
        "earnings_momentum": lambda: earnings_momentum_agent(ticker, prices, fundamentals, market_data),
        "mean_reversion": lambda: mean_reversion_agent(ticker, prices, fundamentals, market_data),
    }

    signals = []

    # Run agents in parallel
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {agent: executor.submit(agent_functions[agent]) for agent in agent_types if agent in agent_functions}

        for agent, future in futures.items():
            try:
                result = future.result()

                # Convert to dict
                signal_dict = {"agent": agent.replace("_", " ").title(), "signal": result.signal, "confidence": result.confidence, "reasoning": result.reasoning, "metadata": result.__dict__}
                signals.append(signal_dict)
            except Exception as e:
                signals.append({"agent": agent.replace("_", " ").title(), "signal": "ERROR", "confidence": 0, "reasoning": f"Agent error: {str(e)}", "metadata": {}})

    # Also run full strategy analysis
    strategy_result = analyze_with_all_strategies(prices, fundamentals, market_data)

    # Aggregate results
    buy_count = sum(1 for s in signals if s["signal"] == "BUY")
    sell_count = sum(1 for s in signals if s["signal"] == "SELL")
    hold_count = sum(1 for s in signals if s["signal"] == "HOLD")

    # Calculate confidence
    total_conf = sum(s["confidence"] for s in signals)
    avg_conf = total_conf / len(signals) if signals else 50

    # Determine final signal
    if buy_count > sell_count and buy_count >= hold_count:
        final_signal = "BUY"
    elif sell_count > buy_count and sell_count >= hold_count:
        final_signal = "SELL"
    else:
        # Use strategy result as tiebreaker
        final_signal = strategy_result.final_signal

    # Consensus level
    max_count = max(buy_count, sell_count, hold_count)
    consensus_pct = max_count / len(signals) if signals else 0
    consensus_level = "HIGH" if consensus_pct >= 0.7 else "MEDIUM" if consensus_pct >= 0.5 else "LOW"

    # Final confidence
    final_confidence = min(95, avg_conf * (0.6 + consensus_pct * 0.4))

    return MultiAgentAnalysis(
        final_signal=final_signal, final_confidence=final_confidence, consensus_level=consensus_level, agents_called=agent_types, signals=signals, aggregated_result={"buy_count": buy_count, "sell_count": sell_count, "hold_count": hold_count, "strategy_final": strategy_result.final_signal, "strategy_confidence": strategy_result.final_confidence, "strategy_consensus": strategy_result.consensus_level}
    )


# ============ AGENT REGISTRY ============

# Register new agents with the system
ENHANCED_AGENTS = {
    "jim_simmons": {"name": "Jim Simons (Quant)", "description": "Statistical pattern recognition and quantitative analysis", "function": jim_simmons_agent, "weight": 1.5},
    "quantitative_analyst": {"name": "Quantitative Momentum", "description": "Multi-timeframe momentum analysis", "function": quantitative_analyst_agent, "weight": 1.2},
    "technical_analyst": {"name": "Technical Analyst", "description": "RSI, MACD, Bollinger Bands, Moving Averages", "function": technical_analyst_agent, "weight": 0.9},
    "factor_investor": {"name": "Factor Investor", "description": "Value, Momentum, Quality, Volatility factors", "function": factor_investor_agent, "weight": 1.3},
    "earnings_momentum": {"name": "Earnings Momentum", "description": "Earnings acceleration and trends", "function": earnings_momentum_agent, "weight": 1.1},
    "mean_reversion": {"name": "Mean Reversion", "description": "Oversold/overbought detection", "function": mean_reversion_agent, "weight": 1.0},
}


if __name__ == "__main__":
    print("=== Testing Enhanced Agents ===\n")

    # Create dummy price data
    class DummyPrice:
        def __init__(self, close, date=None):
            self.close = close
            self.date = date or "2026-01-14"
            self.open = close * 0.99
            self.high = close * 1.02
            self.low = close * 0.98
            self.volume = 1000000

    import random

    prices = [DummyPrice(100 + random.gauss(0, 3) + i * 0.1) for i in range(100)]

    # Test single agent
    print("1. Jim Simons Agent:")
    result = jim_simmons_agent("AAPL", prices)
    print(f"   Signal: {result.signal} ({result.confidence}%)")
    print(f"   Z-Score: {result.z_score:.2f}, Sharpe: {result.sharpe_ratio:.2f}")

    # Test multi-agent
    print("\n2. Multi-Agent Analysis:")
    multi_result = run_multi_agent_analysis("AAPL", prices)
    print(f"   Final Signal: {multi_result.final_signal}")
    print(f"   Confidence: {multi_result.final_confidence:.1f}%")
    print(f"   Consensus: {multi_result.consensus_level}")
    print(f"   Buy: {multi_result.aggregated_result['buy_count']}, Sell: {multi_result.aggregated_result['sell_count']}")

    print("\n=== Test Complete ===")
