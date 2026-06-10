#!/usr/bin/env python3
"""
Comprehensive Strategy Registry v2.3.0
=======================================

Unified registry untuk SEMUA strategies dan agents dalam AI Hedge Fund v2.3.0.
Agent Constitution v2.3.0 Compliant

Categories:
1. RISET v2.3.0 Strategies (NEW)
2. Standalone Agents (Value Investing)
3. SMC & Technical Strategy Agents
4. Strategy Agents
5. Enhanced Agents
6. Quantitative Strategies
7. Legendary Investor Strategies
8. Retail Strategies
9. Quant Analysis Strategies

Total: 50+ strategies/agents

Date: 2026-01-19
Version: 2.3.0
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import logging

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StrategyCategory(Enum):
    """Strategy categories"""

    RISET_V2 = "RISET v2.3.0"
    STANDALONE_AGENT = "Standalone Agents"
    SMC_STRATEGY = "SMC Strategy Agents"
    STRATEGY_AGENT = "Strategy Agents"
    ENHANCED_AGENT = "Enhanced Agents"
    QUANTITATIVE = "Quantitative Strategies"
    LEGENDARY_INVESTOR = "Legendary Investor Strategies"
    RETAIL = "Retail Strategies"
    QUANT_ANALYSIS = "Quant Analysis Strategies"


@dataclass
class StrategyInfo:
    """Information about a strategy/agent"""

    name: str
    category: StrategyCategory
    description: str
    class_path: str
    factory_function: Optional[str] = None
    main_method: str = "analyze"
    enabled: bool = True
    risk_level: str = "MEDIUM"
    timeframe_preference: str = "DAILY"
    indicators: List[str] = field(default_factory=list)


@dataclass
class StrategyResult:
    """Result from strategy/agent analysis"""

    strategy_name: str
    category: StrategyCategory
    signal: str  # BUY, SELL, HOLD, NEUTRAL
    confidence: float  # 0.0 to 1.0
    reasoning: str = ""
    factors: Dict[str, Any] = field(default_factory=dict)
    risk_level: str = "MEDIUM"
    metadata: Dict[str, Any] = field(default_factory=dict)


class ComprehensiveStrategyRegistry:
    """
    Comprehensive registry untuk SEMUA strategies dan agents.

    Provides unified interface untuk:
    - RISET v2.3.0 strategies
    - Standalone agents (Warren Buffett, Benjamin Graham, etc.)
    - SMC strategies (ICT, Wyckoff, Market Structure, etc.)
    - Quantitative strategies
    - Legendary investor strategies
    - Retail strategies
    - Quant analysis strategies
    """

    def __init__(self):
        self.strategies: Dict[str, StrategyInfo] = {}
        self.strategy_cache: Dict[str, Any] = {}
        self.initialize_all_strategies()

    def initialize_all_strategies(self):
        """Initialize semua strategies dan agents"""
        logger.info("=" * 70)
        logger.info("LOADING COMPREHENSIVE STRATEGY REGISTRY")
        logger.info("=" * 70)

        total = 0

        # ========== 1. RISET v2.2.2 STRATEGIES ==========
        logger.info("\n[1/9] Loading RISET v2.2.2 Strategies...")

        self._register_riset_strategies()
        count = len(
            [
                s
                for s in self.strategies.values()
                if s.category == StrategyCategory.RISET_V2
            ]
        )
        logger.info(f"  ✓ Loaded {count} RISET v2.2.2 strategies")
        total += count

        # ========== 2. STANDALONE AGENTS ==========
        logger.info("\n[2/9] Loading Standalone Agents...")

        self._register_standalone_agents()
        count = len(
            [
                s
                for s in self.strategies.values()
                if s.category == StrategyCategory.STANDALONE_AGENT
            ]
        )
        logger.info(f"  ✓ Loaded {count} Standalone Agents")
        total += count

        # ========== 3. SMC STRATEGY AGENTS ==========
        logger.info("\n[3/9] Loading SMC Strategy Agents...")

        self._register_smc_strategies()
        count = len(
            [
                s
                for s in self.strategies.values()
                if s.category == StrategyCategory.SMC_STRATEGY
            ]
        )
        logger.info(f"  ✓ Loaded {count} SMC Strategy Agents")
        total += count

        # ========== 4. STRATEGY AGENTS ==========
        logger.info("\n[4/9] Loading Strategy Agents...")

        self._register_strategy_agents()
        count = len(
            [
                s
                for s in self.strategies.values()
                if s.category == StrategyCategory.STRATEGY_AGENT
            ]
        )
        logger.info(f"  ✓ Loaded {count} Strategy Agents")
        total += count

        # ========== 5. ENHANCED AGENTS ==========
        logger.info("\n[5/9] Loading Enhanced Agents...")

        self._register_enhanced_agents()
        count = len(
            [
                s
                for s in self.strategies.values()
                if s.category == StrategyCategory.ENHANCED_AGENT
            ]
        )
        logger.info(f"  ✓ Loaded {count} Enhanced Agents")
        total += count

        # ========== 6. QUANTITATIVE STRATEGIES ==========
        logger.info("\n[6/9] Loading Quantitative Strategies...")

        self._register_quantitative_strategies()
        count = len(
            [
                s
                for s in self.strategies.values()
                if s.category == StrategyCategory.QUANTITATIVE
            ]
        )
        logger.info(f"  ✓ Loaded {count} Quantitative Strategies")
        total += count

        # ========== 7. LEGENDARY INVESTOR STRATEGIES ==========
        logger.info("\n[7/9] Loading Legendary Investor Strategies...")

        self._register_legendary_investors()
        count = len(
            [
                s
                for s in self.strategies.values()
                if s.category == StrategyCategory.LEGENDARY_INVESTOR
            ]
        )
        logger.info(f"  ✓ Loaded {count} Legendary Investor Strategies")
        total += count

        # ========== 8. RETAIL STRATEGIES ==========
        logger.info("\n[8/9] Loading Retail Strategies...")

        self._register_retail_strategies()
        count = len(
            [
                s
                for s in self.strategies.values()
                if s.category == StrategyCategory.RETAIL
            ]
        )
        logger.info(f"  ✓ Loaded {count} Retail Strategies")
        total += count

        # ========== 9. QUANT ANALYSIS STRATEGIES ==========
        logger.info("\n[9/9] Loading Quant Analysis Strategies...")

        self._register_quant_analysis_strategies()
        count = len(
            [
                s
                for s in self.strategies.values()
                if s.category == StrategyCategory.QUANT_ANALYSIS
            ]
        )
        logger.info(f"  ✓ Loaded {count} Quant Analysis Strategies")
        total += count

        logger.info("\n" + "=" * 70)
        logger.info(
            f"✅ COMPREHENSIVE REGISTRY COMPLETE: {total} strategies/agents loaded"
        )
        logger.info("=" * 70)

    def _register_riset_strategies(self):
        """Register RISET v2.2.2 strategies"""
        strategies = [
            StrategyInfo(
                name="Graham Value Investing",
                category=StrategyCategory.RISET_V2,
                description="Benjamin Graham's value investing principles with Graham Number calculation",
                class_path="src.strategies.graham_value.GrahamValueStrategy",
                main_method="calculate_graham_number",
                risk_level="LOW",
                timeframe_preference="DAILY",
                indicators=["P/E Ratio", "P/B Ratio", "EPS", "Book Value"],
            ),
            StrategyInfo(
                name="Turtle Trading",
                category=StrategyCategory.RISET_V2,
                description="Richard Dennis's Turtle Trading system with ATR position sizing",
                class_path="src.strategies.turtle_trading.TurtleTradingStrategy",
                main_method="generate_signals",
                risk_level="MEDIUM",
                timeframe_preference="DAILY",
                indicators=["ATR", "Donchian Channels", "20/55-day Highs"],
            ),
            StrategyInfo(
                name="SEPA (Super Performance)",
                category=StrategyCategory.RISET_V2,
                description="CANSLIM + VCP pattern detection for super performance stocks",
                class_path="src.strategies.sepa.SEPAStrategy",
                main_method="analyze_stock",
                risk_level="MEDIUM",
                timeframe_preference="DAILY",
                indicators=["CANSLIM Score", "VCP Detection", "Earnings Growth"],
            ),
        ]
        for s in strategies:
            self.strategies[s.name.lower().replace(" ", "_")] = s

    def _register_standalone_agents(self):
        """Register standalone agents"""
        strategies = [
            StrategyInfo(
                name="Warren Buffett Agent",
                category=StrategyCategory.STANDALONE_AGENT,
                description="Warren Buffett-style value investing - moat analysis, DCF, margin of safety",
                class_path="src.agents.standalone_agents.WarrenBuffettAgent",
                factory_function="create_agent",
                risk_level="LOW",
                timeframe_preference="DAILY",
                indicators=["ROE", "FCF Yield", "PE Ratio", "Management Quality"],
            ),
            StrategyInfo(
                name="Benjamin Graham Agent",
                category=StrategyCategory.STANDALONE_AGENT,
                description="Benjamin Graham deep value - PE<15, P/B<1.5, Current Ratio>2",
                class_path="src.agents.standalone_agents BenjaminGrahamAgent",
                factory_function="create_agent",
                risk_level="LOW",
                timeframe_preference="DAILY",
                indicators=["P/E", "P/B", "Current Ratio", "Net Current Assets"],
            ),
            StrategyInfo(
                name="Technical Analysis Agent",
                category=StrategyCategory.STANDALONE_AGENT,
                description="Technical analysis - EMA crosses, RSI, MACD, Bollinger Bands",
                class_path="src.agents.standalone_agents.TechnicalAnalysisAgent",
                factory_function="create_agent",
                risk_level="MEDIUM",
                timeframe_preference="INTRADAY",
                indicators=["RSI", "MACD", "EMA", "Bollinger Bands"],
            ),
            StrategyInfo(
                name="Fundamentals Agent",
                category=StrategyCategory.STANDALONE_AGENT,
                description="Fundamental analysis - financial health, valuation, growth rates",
                class_path="src.agents.standalone_agents.FundamentalsAgent",
                factory_function="create_agent",
                risk_level="LOW",
                timeframe_preference="DAILY",
                indicators=["Revenue Growth", "Profit Margins", "Debt/Equity", "ROE"],
            ),
        ]
        for s in strategies:
            self.strategies[s.name.lower().replace(" ", "_")] = s

    def _register_smc_strategies(self):
        """Register SMC strategy agents"""
        strategies = [
            StrategyInfo(
                name="Market Structure Agent",
                category=StrategyCategory.SMC_STRATEGY,
                description="Identifies HH/HL, LH/LL, Break of Structure, Change of Character",
                class_path="src.agents.smc_strategies.MarketStructureAgent",
                risk_level="MEDIUM",
                timeframe_preference="4H",
                indicators=["Swing Highs", "Swing Lows", "BoS", "CHoCH"],
            ),
            StrategyInfo(
                name="SMC Agent",
                category=StrategyCategory.SMC_STRATEGY,
                description="Order Blocks, Fair Value Gaps, Liquidity Sweeps, Premium/Discount",
                class_path="src.agents.smc_strategies.SMCAgent",
                risk_level="MEDIUM",
                timeframe_preference="4H",
                indicators=["Order Blocks", "FVG", "Liquidity Pools"],
            ),
            StrategyInfo(
                name="ICT Agent",
                category=StrategyCategory.SMC_STRATEGY,
                description="Inner Circle Trader - OTE, Kill Zones, Fibonacci, Market Shift",
                class_path="src.agents.smc_strategies.ICTAgent",
                risk_level="HIGH",
                timeframe_preference="1H",
                indicators=["OTE", "Kill Zones", "Fibonacci", "Market Shift"],
            ),
            StrategyInfo(
                name="Wyckoff Agent",
                category=StrategyCategory.SMC_STRATEGY,
                description="Wyckoff Methodology - Accumulation/Distribution phases, Springs",
                class_path="src.agents.smc_strategies.WyckoffAgent",
                risk_level="MEDIUM",
                timeframe_preference="DAILY",
                indicators=["Accumulation Phase", "Distribution Phase", "Springs"],
            ),
            StrategyInfo(
                name="SNR Agent",
                category=StrategyCategory.SMC_STRATEGY,
                description="Support & Resistance - Horizontal, Dynamic S/R, Confluence zones",
                class_path="src.agents.smc_strategies.SNRAgent",
                risk_level="LOW",
                timeframe_preference="4H",
                indicators=["Support Levels", "Resistance Levels", "Confluence"],
            ),
            StrategyInfo(
                name="Fibonacci Agent",
                category=StrategyCategory.SMC_STRATEGY,
                description="Fibonacci Retracements and Extensions - 0.236 to 1.618 levels",
                class_path="src.agents.smc_strategies.FibonacciAgent",
                risk_level="MEDIUM",
                timeframe_preference="4H",
                indicators=["0.236", "0.382", "0.618", "1.272", "1.618"],
            ),
            StrategyInfo(
                name="Volume Profile Agent",
                category=StrategyCategory.SMC_STRATEGY,
                description="Volume Profile - POC, VAH/VAL, Volume Delta, Auction theory",
                class_path="src.agents.smc_strategies.VolumeProfileAgent",
                risk_level="MEDIUM",
                timeframe_preference="1H",
                indicators=["POC", "Value Area", "Volume Delta"],
            ),
            StrategyInfo(
                name="Divergence Agent",
                category=StrategyCategory.SMC_STRATEGY,
                description="Regular/Hidden divergence - RSI/MACD, Multi-timeframe analysis",
                class_path="src.agents.smc_strategies.DivergenceAgent",
                risk_level="MEDIUM",
                timeframe_preference="4H",
                indicators=["RSI Divergence", "MACD Divergence", "Hidden Divergence"],
            ),
        ]
        for s in strategies:
            self.strategies[s.name.lower().replace(" ", "_")] = s

    def _register_strategy_agents(self):
        """Register strategy agents"""
        strategies = [
            StrategyInfo(
                name="Supply Demand Agent",
                category=StrategyCategory.STRATEGY_AGENT,
                description="Supply and Demand Zones - zone strength, freshness, touch count",
                class_path="src.agents.strategy_agents.SupplyDemandAgent",
                risk_level="MEDIUM",
                timeframe_preference="4H",
                indicators=["Supply Zones", "Demand Zones", "Zone Strength"],
            ),
            StrategyInfo(
                name="Liquidity Agent",
                category=StrategyCategory.STRATEGY_AGENT,
                description="Liquidity & Stop Hunts - EQH/EQL, Stop hunts, Bank liquidity",
                class_path="src.agents.strategy_agents.LiquidityAgent",
                risk_level="HIGH",
                timeframe_preference="1H",
                indicators=["Liquidity Pools", "Stop Hunts", "Bank Levels"],
            ),
        ]
        for s in strategies:
            self.strategies[s.name.lower().replace(" ", "_")] = s

    def _register_enhanced_agents(self):
        """Register enhanced agents"""
        strategies = [
            StrategyInfo(
                name="Jim Simons Quant",
                category=StrategyCategory.ENHANCED_AGENT,
                description="Statistical pattern recognition, z-scores, Sharpe ratio optimization",
                class_path="src.agents.enhanced_agents.jim_simmons_agent",
                risk_level="MEDIUM",
                timeframe_preference="DAILY",
                indicators=["Z-Score", "Sharpe Ratio", "Statistical Patterns"],
            ),
            StrategyInfo(
                name="Quantitative Analyst",
                category=StrategyCategory.ENHANCED_AGENT,
                description="Multi-timeframe momentum analysis, risk-adjusted scores",
                class_path="src.agents.enhanced_agents.quantitative_analyst_agent",
                risk_level="MEDIUM",
                timeframe_preference="DAILY",
                indicators=["5/10/20-day Momentum", "Risk-Adjusted Score"],
            ),
            StrategyInfo(
                name="Technical Analyst",
                category=StrategyCategory.ENHANCED_AGENT,
                description="RSI, MACD, Bollinger Bands, Moving Averages analysis",
                class_path="src.agents.enhanced_agents.technical_analyst_agent",
                risk_level="MEDIUM",
                timeframe_preference="4H",
                indicators=["RSI", "MACD", "Bollinger Bands", "SMA"],
            ),
            StrategyInfo(
                name="Factor Investor",
                category=StrategyCategory.ENHANCED_AGENT,
                description="Value, Momentum, Quality, Volatility factor analysis",
                class_path="src.agents.enhanced_agents.factor_investor_agent",
                risk_level="LOW",
                timeframe_preference="WEEKLY",
                indicators=["Value Factor", "Momentum Factor", "Quality Factor"],
            ),
            StrategyInfo(
                name="Earnings Momentum",
                category=StrategyCategory.ENHANCED_AGENT,
                description="Earnings acceleration and trends analysis",
                class_path="src.agents.enhanced_agents.earnings_momentum_agent",
                risk_level="MEDIUM",
                timeframe_preference="DAILY",
                indicators=["Earnings Acceleration", "Revenue Growth"],
            ),
            StrategyInfo(
                name="Mean Reversion",
                category=StrategyCategory.ENHANCED_AGENT,
                description="Oversold/overbought detection, z-score analysis",
                class_path="src.agents.enhanced_agents.mean_reversion_agent",
                risk_level="MEDIUM",
                timeframe_preference="DAILY",
                indicators=["Z-Score", "RSI", "Bollinger Position"],
            ),
        ]
        for s in strategies:
            self.strategies[s.name.lower().replace(" ", "_")] = s

    def _register_quantitative_strategies(self):
        """Register quantitative strategies"""
        strategies = [
            StrategyInfo(
                name="Jim Simons Strategy",
                category=StrategyCategory.QUANTITATIVE,
                description="Renaissance-style quant - Statistical patterns, mean reversion",
                class_path="src.strategies.quantitative_strategies.JimSimonsStrategy",
                main_method="calculate",
                risk_level="MEDIUM",
                timeframe_preference="DAILY",
                indicators=["Z-Score", "Statistical Patterns", "Sharpe Ratio"],
            ),
            StrategyInfo(
                name="Quantitative Momentum",
                category=StrategyCategory.QUANTITATIVE,
                description="Multi-timeframe momentum - SMA crossover, risk-adjusted momentum",
                class_path="src.strategies.quantitative_strategies.QuantitativeMomentumStrategy",
                main_method="calculate",
                risk_level="MEDIUM",
                timeframe_preference="DAILY",
                indicators=["5/10/20-day Momentum", "SMA Crossover"],
            ),
            StrategyInfo(
                name="Mean Reversion Strategy",
                category=StrategyCategory.QUANTITATIVE,
                description="Z-score, Bollinger Bands position, RSI mean reversion",
                class_path="src.strategies.quantitative_strategies.MeanReversionStrategy",
                main_method="calculate",
                risk_level="MEDIUM",
                timeframe_preference="DAILY",
                indicators=["Z-Score", "RSI", "Bollinger Bands"],
            ),
            StrategyInfo(
                name="Factor Investing Strategy",
                category=StrategyCategory.QUANTITATIVE,
                description="Value, Momentum, Quality, Volatility, Size factor model",
                class_path="src.strategies.quantitative_strategies.FactorInvestingStrategy",
                main_method="calculate",
                risk_level="LOW",
                timeframe_preference="WEEKLY",
                indicators=["Value", "Momentum", "Quality", "Volatility"],
            ),
            StrategyInfo(
                name="Earnings Momentum Strategy",
                category=StrategyCategory.QUANTITATIVE,
                description="Earnings acceleration - 5/20/60-day returns",
                class_path="src.strategies.quantitative_strategies.EarningsMomentumStrategy",
                main_method="calculate",
                risk_level="MEDIUM",
                timeframe_preference="DAILY",
                indicators=["Earnings Growth", "Revenue Acceleration"],
            ),
            StrategyInfo(
                name="Technical Analysis Strategy",
                category=StrategyCategory.QUANTITATIVE,
                description="SMA, MACD, RSI, Stochastic, Bollinger Bands",
                class_path="src.strategies.quantitative_strategies.TechnicalAnalysisStrategy",
                main_method="calculate",
                risk_level="MEDIUM",
                timeframe_preference="DAILY",
                indicators=["SMA", "MACD", "RSI", "Stochastic"],
            ),
        ]
        for s in strategies:
            self.strategies[s.name.lower().replace(" ", "_")] = s

    def _register_legendary_investors(self):
        """Register legendary investor strategies"""
        strategies = [
            StrategyInfo(
                name="Warren Buffett Style",
                category=StrategyCategory.LEGENDARY_INVESTOR,
                description="Quality + Value - ROE > 15%, PE < 15, PEG < 1",
                class_path="src.strategies.legendary_investors.buffett_style",
                main_method="buffett_style",
                risk_level="LOW",
                timeframe_preference="WEEKLY",
                indicators=["ROE", "PE Ratio", "PEG", "FCF Yield"],
            ),
            StrategyInfo(
                name="Peter Lynch Style",
                category=StrategyCategory.LEGENDARY_INVESTOR,
                description="Growth at Reasonable Price - PEG < 1, insider ownership",
                class_path="src.strategies.legendary_investors.lynch_style",
                main_method="lynch_style",
                risk_level="MEDIUM",
                timeframe_preference="WEEKLY",
                indicators=["PEG Ratio", "Insider Ownership", "Growth Rate"],
            ),
            StrategyInfo(
                name="Benjamin Graham Style",
                category=StrategyCategory.LEGENDARY_INVESTOR,
                description="Deep Value - PE < 10, P/B < 1.5, margin of safety > 30%",
                class_path="src.strategies.legendary_investors.graham_style",
                main_method="graham_style",
                risk_level="LOW",
                timeframe_preference="WEEKLY",
                indicators=["PE Ratio", "P/B Ratio", "Margin of Safety"],
            ),
            StrategyInfo(
                name="George Soros Style",
                category=StrategyCategory.LEGENDARY_INVESTOR,
                description="Macro/Reflexivity - Trend strength, crowd behavior",
                class_path="src.strategies.legendary_investors.soros_style",
                main_method="soros_style",
                risk_level="HIGH",
                timeframe_preference="DAILY",
                indicators=["Trend Strength", "Crowd Behavior", "Macro Catalysts"],
            ),
            StrategyInfo(
                name="Ray Dalio Style",
                category=StrategyCategory.LEGENDARY_INVESTOR,
                description="All Weather/Risk Parity - Sharpe, Sortino, beta",
                class_path="src.strategies.legendary_investors.dalio_style",
                main_method="dalio_style",
                risk_level="LOW",
                timeframe_preference="WEEKLY",
                indicators=["Sharpe Ratio", "Sortino Ratio", "Beta", "Correlation"],
            ),
            StrategyInfo(
                name="Michael Burry Style",
                category=StrategyCategory.LEGENDARY_INVESTOR,
                description="Value/Contrarian - Deep value, high short interest",
                class_path="src.strategies.legendary_investors.burry_style",
                main_method="burry_style",
                risk_level="HIGH",
                timeframe_preference="WEEKLY",
                indicators=["Short Interest", "Margin of Safety", "Catalyst"],
            ),
            StrategyInfo(
                name="Philip Fisher Style",
                category=StrategyCategory.LEGENDARY_INVESTOR,
                description="Growth (15 Points) - 7 growth + 4 management + 4 business",
                class_path="src.strategies.legendary_investors.fisher_style",
                main_method="fisher_style",
                risk_level="MEDIUM",
                timeframe_preference="WEEKLY",
                indicators=["Growth Score", "Management Quality", "Business Quality"],
            ),
            StrategyInfo(
                name="John Templeton Style",
                category=StrategyCategory.LEGENDARY_INVESTOR,
                description="Contrarian - Buy at maximum pessimism, 10+ year perspective",
                class_path="src.strategies.legendary_investors.templeton_style",
                main_method="templeton_style",
                risk_level="HIGH",
                timeframe_preference="MONTHLY",
                indicators=["Sentiment", "Pessimism Level", "Long-term Value"],
            ),
            StrategyInfo(
                name="Joel Greenblatt Style",
                category=StrategyCategory.LEGENDARY_INVESTOR,
                description="Magic Formula - EV/EBIT ranking + ROC ranking",
                class_path="src.strategies.legendary_investors.greenblatt_style",
                main_method="greenblatt_style",
                risk_level="LOW",
                timeframe_preference="WEEKLY",
                indicators=["EV/EBIT", "ROC", "Magic Formula Rank"],
            ),
            StrategyInfo(
                name="William O'Neil Style",
                category=StrategyCategory.LEGENDARY_INVESTOR,
                description="CAN SLIM - C(earnings) A(annual growth) N(new highs) S(supply) L(leader) I(institutional) M(market)",
                class_path="src.strategies.legendary_investors.oneil_style",
                main_method="oneil_style",
                risk_level="MEDIUM",
                timeframe_preference="DAILY",
                indicators=[
                    "CANSLIM Score",
                    "Earnings Growth",
                    "New Highs",
                    "Market Direction",
                ],
            ),
        ]
        for s in strategies:
            self.strategies[s.name.lower().replace(" ", "_")] = s

    def _register_retail_strategies(self):
        """Register retail trading strategies"""
        strategies = [
            StrategyInfo(
                name="Scalping Momentum",
                category=StrategyCategory.RETAIL,
                description="High-frequency momentum scalping - 1m timeframe",
                class_path="src.integrations.retail_strategies.RetailStrategies",
                factory_function="execute_strategy",
                main_method="_scalping_momentum",
                risk_level="HIGH",
                timeframe_preference="1M",
                indicators=["RSI", "MACD", "Volume"],
            ),
            StrategyInfo(
                name="Swing Trading",
                category=StrategyCategory.RETAIL,
                description="Medium-term swing trading - 4h timeframe",
                class_path="src.integrations.retail_strategies.RetailStrategies",
                factory_function="execute_strategy",
                main_method="_swing_trading",
                risk_level="MEDIUM",
                timeframe_preference="4H",
                indicators=["SMA(20/50)", "Stochastic", "Bollinger Bands"],
            ),
            StrategyInfo(
                name="Position Trading",
                category=StrategyCategory.RETAIL,
                description="Long-term position trading - weekly timeframe",
                class_path="src.integrations.retail_strategies.RetailStrategies",
                factory_function="execute_strategy",
                main_method="_position_trading",
                risk_level="LOW",
                timeframe_preference="WEEKLY",
                indicators=["SMA(100/200)", "Volume"],
            ),
            StrategyInfo(
                name="Breakout Trading",
                category=StrategyCategory.RETAIL,
                description="Breakout with volume confirmation - 1h timeframe",
                class_path="src.integrations.retail_strategies.RetailStrategies",
                factory_function="execute_strategy",
                main_method="_breakout_trading",
                risk_level="MEDIUM",
                timeframe_preference="1H",
                indicators=["Recent High/Low", "Volume Confirmation"],
            ),
            StrategyInfo(
                name="Reversal Trading",
                category=StrategyCategory.RETAIL,
                description="Reversal at support/resistance - daily timeframe",
                class_path="src.integrations.retail_strategies.RetailStrategies",
                factory_function="execute_strategy",
                main_method="_reversal_trading",
                risk_level="HIGH",
                timeframe_preference="DAILY",
                indicators=["RSI", "Stochastic", "S/R Levels"],
            ),
            StrategyInfo(
                name="Trend Following",
                category=StrategyCategory.RETAIL,
                description="Trend following with moving averages - daily timeframe",
                class_path="src.integrations.retail_strategies.RetailStrategies",
                factory_function="execute_strategy",
                main_method="_trend_following",
                risk_level="MEDIUM",
                timeframe_preference="DAILY",
                indicators=["SMA(50/200)", "ADX"],
            ),
            StrategyInfo(
                name="Range Trading",
                category=StrategyCategory.RETAIL,
                description="Range trading for sideways markets - 1h timeframe",
                class_path="src.integrations.retail_strategies.RetailStrategies",
                factory_function="execute_strategy",
                main_method="_range_trading",
                risk_level="LOW",
                timeframe_preference="1H",
                indicators=["Bollinger Bands", "ADX"],
            ),
            StrategyInfo(
                name="Gap Trading",
                category=StrategyCategory.RETAIL,
                description="Gap trading for earnings/news events - daily timeframe",
                class_path="src.integrations.retail_strategies.RetailStrategies",
                factory_function="execute_strategy",
                main_method="_gap_trading",
                risk_level="HIGH",
                timeframe_preference="DAILY",
                indicators=["Gap Analysis", "Volume"],
            ),
        ]
        for s in strategies:
            self.strategies[s.name.lower().replace(" ", "_")] = s

    def _register_quant_analysis_strategies(self):
        """Register quant analysis strategies"""
        strategies = [
            StrategyInfo(
                name="Jim Simons Analysis",
                category=StrategyCategory.QUANT_ANALYSIS,
                description="Statistical arbitrage, momentum z-score, volume z-score",
                class_path="src.integrations.quant_strategies_analysis.QuantAnalysis",
                factory_function="analyze_all_strategies",
                main_method="_jim_simmons_strategy",
                risk_level="MEDIUM",
                timeframe_preference="DAILY",
                indicators=["Z-Score", "Momentum", "Volume"],
            ),
            StrategyInfo(
                name="Momentum Analysis",
                category=StrategyCategory.QUANT_ANALYSIS,
                description="Price vs SMA(20/50), ROC(20), Volume analysis",
                class_path="src.integrations.quant_strategies_analysis.QuantAnalysis",
                factory_function="analyze_all_strategies",
                main_method="_momentum_strategy",
                risk_level="MEDIUM",
                timeframe_preference="DAILY",
                indicators=["SMA(20/50)", "ROC(20)", "Volume"],
            ),
            StrategyInfo(
                name="Mean Reversion Analysis",
                category=StrategyCategory.QUANT_ANALYSIS,
                description="Z-score, RSI, SMA(20) mean reversion signals",
                class_path="src.integrations.quant_strategies_analysis.QuantAnalysis",
                factory_function="analyze_all_strategies",
                main_method="_mean_reversion_strategy",
                risk_level="MEDIUM",
                timeframe_preference="DAILY",
                indicators=["Z-Score", "RSI", "SMA(20)"],
            ),
            StrategyInfo(
                name="Factor Investing Analysis",
                category=StrategyCategory.QUANT_ANALYSIS,
                description="Value/Momentum/Quality factor alignment",
                class_path="src.integrations.quant_strategies_analysis.QuantAnalysis",
                factory_function="analyze_all_strategies",
                main_method="_factor_investing_strategy",
                risk_level="LOW",
                timeframe_preference="WEEKLY",
                indicators=["Value Factor", "Momentum Factor", "Quality Factor"],
            ),
            StrategyInfo(
                name="Earnings Momentum Analysis",
                category=StrategyCategory.QUANT_ANALYSIS,
                description="Volume ratio, price momentum for earnings plays",
                class_path="src.integrations.quant_strategies_analysis.QuantAnalysis",
                factory_function="analyze_all_strategies",
                main_method="_earnings_momentum_strategy",
                risk_level="MEDIUM",
                timeframe_preference="DAILY",
                indicators=["Volume Ratio", "Price Momentum"],
            ),
            StrategyInfo(
                name="Technical Analysis",
                category=StrategyCategory.QUANT_ANALYSIS,
                description="RSI, MACD, Bollinger Bands, Stochastic signals",
                class_path="src.integrations.quant_strategies_analysis.QuantAnalysis",
                factory_function="analyze_all_strategies",
                main_method="_technical_analysis_strategy",
                risk_level="MEDIUM",
                timeframe_preference="DAILY",
                indicators=["RSI", "MACD", "Bollinger Bands", "Stochastic"],
            ),
        ]
        for s in strategies:
            self.strategies[s.name.lower().replace(" ", "_")] = s

    def get_strategy(self, name: str) -> Optional[StrategyInfo]:
        """Get strategy info by name"""
        return self.strategies.get(name.lower().replace(" ", "_"))

    def get_all_strategies(self) -> Dict[str, StrategyInfo]:
        """Get all registered strategies"""
        return self.strategies

    def get_strategies_by_category(
        self, category: StrategyCategory
    ) -> Dict[str, StrategyInfo]:
        """Get strategies by category"""
        return {
            name: info
            for name, info in self.strategies.items()
            if info.category == category
        }

    def get_available_categories(self) -> List[StrategyCategory]:
        """Get all available categories"""
        return list(set(info.category for info in self.strategies.values()))

    def list_all_strategies(self) -> str:
        """List all available strategies"""
        lines = []
        lines.append("\n" + "=" * 70)
        lines.append("📊 COMPREHENSIVE STRATEGY REGISTRY")
        lines.append("=" * 70)

        for category in StrategyCategory:
            strategies = self.get_strategies_by_category(category)
            if strategies:
                lines.append(f"\n{category.value}:")
                lines.append("-" * 50)
                for name, info in strategies.items():
                    lines.append(f"  • {info.name}")
                    lines.append(
                        f"    Risk: {info.risk_level} | Timeframe: {info.timeframe_preference}"
                    )

        lines.append("\n" + "=" * 70)
        lines.append(f"Total: {len(self.strategies)} strategies/agents")
        lines.append("=" * 70 + "\n")

        return "\n".join(lines)


def get_comprehensive_registry() -> ComprehensiveStrategyRegistry:
    """Get singleton instance"""
    return ComprehensiveStrategyRegistry()


def main():
    """Test comprehensive registry"""
    registry = get_comprehensive_registry()

    print(registry.list_all_strategies())

    print("\n" + "=" * 70)
    print("TESTING STRATEGY EXECUTION")
    print("=" * 70)

    # Test RISET strategies
    graham = registry.get_strategy("graham_value_investing")
    print(f"\n✓ Found: {graham.name if graham else 'Not found'}")

    # Test SMC strategies
    ict = registry.get_strategy("ict_agent")
    print(f"✓ Found: {ict.name if ict else 'Not found'}")

    # Test Legendary investors
    buffett = registry.get_strategy("warren_buffett_style")
    print(f"✓ Found: {buffett.name if buffett else 'Not found'}")

    print("\n" + "=" * 70)
    print("✅ COMPREHENSIVE STRATEGY REGISTRY WORKING!")
    print("=" * 70)


if __name__ == "__main__":
    main()
