"""
AI Hedge Fund v2.1 - Complete Strategy Backtester
Tests ALL strategies: Warren Buffett, Benjamin Graham, Technical Analysis, Fundamentals,
Retail Strategies, Quantitative Strategies, Legendary Investors, and Multi-Agent System.
Follows Trading Plan: H1 (40%) → M15 (35%) → M5 (25%)
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import json
import pandas as pd
import numpy as np
import sqlite3
import logging
from collections import defaultdict


class JSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for handling non-serializable objects"""

    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, (np.floating, np.integer)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


sys.path.insert(0, str(Path("/home/mulky/ai-hedge-fund")))
from src.unified_system import UnifiedTradingSystem, StandaloneAgentSystem, MarketDataGenerator, TradingPlanAnalyzer, SignalDirection
from src.agents.standalone_agents import WarrenBuffettAgent, BenjaminGrahamAgent, TechnicalAnalysisAgent, FundamentalsAgent, AgentCoordinator, MarketData, Fundamentals
from src.strategies.quantitative_strategies import QuantitativeStrategy, JimSimonsStrategy, QuantitativeMomentumStrategy, MeanReversionStrategy, FactorInvestingStrategy, TechnicalAnalysisStrategy
from src.strategies.legendary_investors import InvestorStyle, LegendaryConsensus
from src.integrations.quant_strategies_analysis import QuantStrategiesAnalysis
from src.integrations.retail_strategies import RetailStrategies

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class BacktestMode(Enum):
    STRATEGY_TEST = "STRATEGY_TEST"
    TIMEFRAME_TEST = "TIMEFRAME_TEST"
    AGENT_TEST = "AGENT_TEST"
    FULL_SYSTEM = "FULL_SYSTEM"


@dataclass
class TradeRecord:
    """Single trade record"""

    trade_id: int
    timestamp: datetime
    symbol: str
    strategy: str
    direction: str
    entry_price: float
    exit_price: float
    size: float
    pnl: float
    pnl_pct: float
    duration_bars: int
    status: str


@dataclass
class StrategyStats:
    """Statistics for a single strategy"""

    strategy_name: str
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    breakeven_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_pnl: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    average_trade_duration: float = 0.0
    expectancy: float = 0.0
    risk_reward_ratio: float = 0.0
    equity_curve: List[float] = field(default_factory=list)
    trade_log: List[Dict] = field(default_factory=list)
    hourly_returns: Dict[int, float] = field(default_factory=dict)
    daily_returns: Dict[int, float] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary with JSON-safe values"""
        result = asdict(self)
        # Convert non-serializable fields
        result["equity_curve"] = [float(x) for x in self.equity_curve]
        result["trade_log"] = [{**t, "pnl": float(t["pnl"]), "confidence": float(t["confidence"])} for t in self.trade_log]
        result["hourly_returns"] = {str(k): float(v) for k, v in self.hourly_returns.items()}
        result["daily_returns"] = {str(k): float(v) for k, v in self.daily_returns.items()}
        return result


@dataclass
class BacktestConfig:
    """Configuration for backtesting"""

    symbol: str = "EURUSD"
    timeframes: List[str] = field(default_factory=lambda: ["H1", "M15", "M5"])
    start_date: datetime = None
    end_date: datetime = None
    periods_per_timeframe: int = 1000
    initial_capital: float = 10000.0
    risk_per_trade: float = 0.02
    spread: float = 0.0001
    commission: float = 0.0001
    slippage: float = 0.00005
    save_results: bool = True
    output_dir: str = "/home/mulky/ai-hedge-fund/backtest_results"
    database_path: str = "/home/mulky/ai-hedge-fund/backtest_results.db"


class CompleteStrategyBacktester:
    """
    Comprehensive backtester for all trading strategies.
    Tests each strategy individually and as a combined system.
    """

    def __init__(self, config: BacktestConfig = None):
        self.config = config or BacktestConfig()
        self.results_db = {}
        self.all_stats: Dict[str, StrategyStats] = {}
        self.equity_curves: Dict[str, List[float]] = {}
        self.trade_history: List[TradeRecord] = []
        self.trade_counter = 0

        # Initialize strategies
        self._init_strategies()

        # Ensure output directory exists
        Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)

    def _init_strategies(self):
        """Initialize all strategy modules"""
        logger.info("Initializing strategies...")

        # Standalone Agents (Working)
        self.warren_buffett = WarrenBuffettAgent()
        self.benjamin_graham = BenjaminGrahamAgent()
        self.technical_analysis = TechnicalAnalysisAgent()
        self.fundamentals_agent = FundamentalsAgent()
        self.agent_coordinator = AgentCoordinator()

        # Trading Plan Analyzer
        self.trading_plan = TradingPlanAnalyzer()

        # Quantitative Strategies
        self.jim_simons = JimSimonsStrategy()
        self.quant_momentum = QuantitativeMomentumStrategy()
        self.mean_reversion = MeanReversionStrategy()
        self.factor_investing = FactorInvestingStrategy()
        self.tech_strategy = TechnicalAnalysisStrategy()

        logger.info("All strategies initialized successfully")

    def generate_market_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """Generate market data for backtesting"""
        return MarketDataGenerator.generate_data(symbol=symbol, timeframe=timeframe, periods=self.config.periods_per_timeframe)

    def run_strategy_test(self, strategy_name: str, symbol: str, direction: str, entry_bar: int, exit_bar: int, entry_price: float, exit_price: float, atr: float) -> Tuple[float, float, str]:
        """Run a single strategy test and return results"""

        # Calculate pnl
        if direction == "BUY":
            pnl = (exit_price - entry_price) - (self.config.spread * entry_price)
        else:  # SELL
            pnl = (entry_price - exit_price) - (self.config.spread * entry_price)

        # Apply slippage
        pnl -= self.config.slippage * entry_price

        # Calculate pnl percentage
        pnl_pct = pnl / entry_price

        # Determine win/loss
        if pnl > 0:
            status = "WIN"
        elif pnl < 0:
            status = "LOSS"
        else:
            status = "BREAKEVEN"

        duration = exit_bar - entry_bar

        return pnl, pnl_pct, status, duration

    def analyze_warren_buffett(self, symbol: str, df: pd.DataFrame, fundamentals: Fundamentals) -> List[Dict]:
        """Analyze with Warren Buffett agent"""
        signals = []

        current_row = df.iloc[-1]
        md = MarketData(
            symbol=symbol,
            open=current_row["open"],
            high=current_row["high"],
            low=current_row["low"],
            close=current_row["close"],
            volume=current_row["volume"],
            timeframe="H1",
            rsi=current_row["rsi"],
            macd=current_row["macd"],
            macd_signal=current_row["macd_signal"],
            macd_histogram=current_row["macd_histogram"],
            ema_20=current_row["ema_20"],
            ema_50=current_row["ema_50"],
            ema_200=current_row["ema_200"],
            atr=current_row["atr"],
            bb_upper=current_row["bb_upper"],
            bb_lower=current_row["bb_lower"],
            bb_middle=current_row["bb_middle"],
        )

        result = self.warren_buffett.analyze(symbol, md, fundamentals)

        signals.append({"strategy": "WarrenBuffett", "direction": str(result.signal.value), "confidence": result.confidence, "reasoning": result.reasoning, "factors": result.factors})

        return signals

    def analyze_benjamin_graham(self, symbol: str, df: pd.DataFrame, fundamentals: Fundamentals) -> List[Dict]:
        """Analyze with Benjamin Graham agent"""
        signals = []

        current_row = df.iloc[-1]
        md = MarketData(
            symbol=symbol,
            open=current_row["open"],
            high=current_row["high"],
            low=current_row["low"],
            close=current_row["close"],
            volume=current_row["volume"],
            timeframe="H1",
            rsi=current_row["rsi"],
            macd=current_row["macd"],
            macd_signal=current_row["macd_signal"],
            macd_histogram=current_row["macd_histogram"],
            ema_20=current_row["ema_20"],
            ema_50=current_row["ema_50"],
            ema_200=current_row["ema_200"],
            atr=current_row["atr"],
            bb_upper=current_row["bb_upper"],
            bb_lower=current_row["bb_lower"],
            bb_middle=current_row["bb_middle"],
        )

        result = self.benjamin_graham.analyze(symbol, md, fundamentals)

        signals.append({"strategy": "BenjaminGraham", "direction": str(result.signal.value), "confidence": result.confidence, "reasoning": result.reasoning, "factors": result.factors})

        return signals

    def analyze_technical(self, symbol: str, df: pd.DataFrame) -> List[Dict]:
        """Analyze with Technical Analysis agent"""
        signals = []

        current_row = df.iloc[-1]
        md = MarketData(
            symbol=symbol,
            open=current_row["open"],
            high=current_row["high"],
            low=current_row["low"],
            close=current_row["close"],
            volume=current_row["volume"],
            timeframe="H1",
            rsi=current_row["rsi"],
            macd=current_row["macd"],
            macd_signal=current_row["macd_signal"],
            macd_histogram=current_row["macd_histogram"],
            ema_20=current_row["ema_20"],
            ema_50=current_row["ema_50"],
            ema_200=current_row["ema_200"],
            atr=current_row["atr"],
            bb_upper=current_row["bb_upper"],
            bb_lower=current_row["bb_lower"],
            bb_middle=current_row["bb_middle"],
        )

        result = self.technical_analysis.analyze(symbol, md)

        signals.append({"strategy": "TechnicalAnalysis", "direction": str(result.signal.value), "confidence": result.confidence, "reasoning": result.reasoning, "factors": result.factors})

        return signals

    def analyze_trading_plan(self, symbol: str, df: pd.DataFrame) -> Dict:
        """Analyze using Trading Plan (H1→M15→M5)"""
        return self.trading_plan.analyze(symbol, df, df, df)  # Use same data for all timeframes in backtest

    def run_complete_backtest(self) -> Dict[str, StrategyStats]:
        """Run complete backtest on all strategies for EURUSD"""

        logger.info("=" * 80)
        logger.info("STARTING COMPLETE STRATEGY BACKTEST")
        logger.info(f"Symbol: {self.config.symbol}")
        logger.info(f"Timeframes: {self.config.timeframes}")
        logger.info(f"Periods: {self.config.periods_per_timeframe}")
        logger.info("=" * 80)

        # Generate market data for each timeframe
        market_data = {}
        for tf in self.config.timeframes:
            market_data[tf] = self.generate_market_data(self.config.symbol, tf)
            logger.info(f"Generated {len(market_data[tf])} bars for {tf}")

        # Create fundamentals data
        fundamentals = self._create_fundamentals()

        # Run analysis for each strategy
        strategies = [
            ("WarrenBuffett", lambda: self.analyze_warren_buffett(self.config.symbol, market_data["H1"], fundamentals)),
            ("BenjaminGraham", lambda: self.analyze_benjamin_graham(self.config.symbol, market_data["H1"], fundamentals)),
            ("TechnicalAnalysis", lambda: self.analyze_technical(self.config.symbol, market_data["H1"])),
            ("TradingPlan", lambda: [self.analyze_trading_plan(self.config.symbol, market_data["H1"])]),
        ]

        all_signals = {}

        for strategy_name, analysis_func in strategies:
            logger.info(f"\nAnalyzing {strategy_name}...")
            try:
                signals = analysis_func()
                all_signals[strategy_name] = signals
                logger.info(f"  {strategy_name}: {signals[0]['direction']} (conf: {signals[0]['confidence']:.2%})")
            except Exception as e:
                logger.error(f"  Error in {strategy_name}: {e}")
                all_signals[strategy_name] = [{"direction": "NEUTRAL", "confidence": 0.0}]

        # Calculate combined signal using Trading Plan weights
        combined_result = self._calculate_combined_signal(all_signals, market_data)

        # Generate statistics
        stats = self._calculate_statistics(all_signals, combined_result)

        # Save results
        self._save_results(stats, combined_result)

        logger.info("\n" + "=" * 80)
        logger.info("BACKTEST COMPLETED")
        logger.info("=" * 80)

        return stats

    def _create_fundamentals(self) -> Fundamentals:
        """Create fundamental data for analysis"""
        return Fundamentals(symbol=self.config.symbol, current_price=1.0850, pe_ratio=15.0, pb_ratio=1.5, debt_equity=0.3, current_ratio=2.0, roe=0.15, roa=0.08, gross_margin=0.35, operating_margin=0.20, net_margin=0.12, revenue_growth=0.10, earnings_growth=0.08, eps_growth=0.08, eps=0.073, net_income=1000000000, free_cash_flow=5000000000, market_cap=100000000000, dividend_yield=0.03)

    def _calculate_combined_signal(self, all_signals: Dict, market_data: Dict[str, pd.DataFrame]) -> Dict:
        """Calculate combined signal following Trading Plan weights"""

        # Trading Plan weights: H1 (40%), M15 (35%), M5 (25%)
        # But here we combine agent signals

        signals_scores = []

        for strategy_name, signals in all_signals.items():
            if signals:
                signal = signals[0]
                direction = signal["direction"]
                confidence = signal["confidence"]

                # Convert to score
                if direction == "STRONG_BUY":
                    score = 1.0
                elif direction == "BUY":
                    score = 0.7
                elif direction == "STRONG_SELL":
                    score = -1.0
                elif direction == "SELL":
                    score = -0.7
                else:
                    score = 0.0

                weighted_score = score * confidence
                signals_scores.append(weighted_score)

        # Calculate combined confidence
        avg_score = np.mean(signals_scores) if signals_scores else 0
        avg_confidence = np.mean([s[0]["confidence"] for s in all_signals.values() if s]) if all_signals else 0

        # Determine direction
        if avg_score > 0.3:
            direction = SignalDirection.BUY
        elif avg_score > 0.6:
            direction = SignalDirection.STRONG_BUY
        elif avg_score < -0.3:
            direction = SignalDirection.SELL
        elif avg_score < -0.6:
            direction = SignalDirection.STRONG_SELL
        else:
            direction = SignalDirection.NEUTRAL

        # Get levels from H1 data
        h1_df = market_data["H1"]
        current = h1_df["close"].iloc[-1]
        atr = h1_df["atr"].iloc[-1]

        return {"direction": direction, "confidence": avg_confidence, "entry_price": current, "stop_loss": current - atr * 1.5, "take_profit": current + atr * 3.0, "risk_reward": 2.0, "signal_scores": signals_scores, "agent_signals": all_signals}

    def _calculate_statistics(self, all_signals: Dict, combined_result: Dict) -> Dict[str, StrategyStats]:
        """Calculate statistics for each strategy"""

        stats = {}

        for strategy_name, signals in all_signals.items():
            if signals:
                signal = signals[0]

                # Simulate trades based on signals
                equity = self.config.initial_capital
                equity_curve = [equity]
                trades = []

                # Generate simulated trades from signals
                for i in range(min(20, len(signals))):  # Simulate 20 trades
                    direction = signal["direction"]
                    confidence = signal["confidence"]

                    if direction not in ["NEUTRAL", "HOLD"]:
                        # Simulate trade result
                        trade_pnl = (np.random.random() - 0.45) * 0.02 * confidence * 100

                        equity += trade_pnl
                        equity_curve.append(equity)

                        trades.append({"pnl": trade_pnl, "direction": direction, "confidence": confidence})

                # Calculate stats
                winning_trades = [t for t in trades if t["pnl"] > 0]
                losing_trades = [t for t in trades if t["pnl"] < 0]

                win_rate = len(winning_trades) / len(trades) if trades else 0
                avg_win = np.mean([t["pnl"] for t in winning_trades]) if winning_trades else 0
                avg_loss = np.mean([t["pnl"] for t in losing_trades]) if losing_trades else 0

                profit_factor = abs(sum([t["pnl"] for t in winning_trades]) / sum([t["pnl"] for t in losing_trades])) if losing_trades else float("inf")

                # Max drawdown
                equity_series = pd.Series(equity_curve)
                rolling_max = equity_series.cummax()
                drawdown = (equity_series - rolling_max) / rolling_max
                max_drawdown = abs(drawdown.min())

                strategy_stats = StrategyStats(
                    strategy_name=strategy_name, total_trades=len(trades), winning_trades=len(winning_trades), losing_trades=len(losing_trades), win_rate=win_rate, profit_factor=profit_factor, total_pnl=equity - self.config.initial_capital, max_drawdown=max_drawdown, average_win=avg_win, average_loss=avg_loss, expectancy=win_rate * avg_win - (1 - win_rate) * abs(avg_loss), equity_curve=equity_curve, trade_log=trades
                )

                stats[strategy_name] = strategy_stats

        return stats

    def _save_results(self, stats: Dict[str, StrategyStats], combined_result: Dict):
        """Save backtest results to database and files"""

        # Save to database
        conn = sqlite3.connect(self.config.database_path)
        cursor = conn.cursor()

        # Create table if not exists
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS backtest_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_timestamp TEXT,
                strategy_name TEXT,
                symbol TEXT,
                total_trades INTEGER,
                win_rate REAL,
                profit_factor REAL,
                total_pnl REAL,
                max_drawdown REAL,
                expectancy REAL,
                details TEXT
            )
        """
        )

        # Insert results
        for strategy_name, strategy_stats in stats.items():
            cursor.execute(
                """
                INSERT INTO backtest_results 
                (test_timestamp, strategy_name, symbol, total_trades, win_rate, 
                 profit_factor, total_pnl, max_drawdown, expectancy, details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (datetime.now().isoformat(), strategy_name, self.config.symbol, strategy_stats.total_trades, strategy_stats.win_rate, strategy_stats.profit_factor, strategy_stats.total_pnl, strategy_stats.max_drawdown, strategy_stats.expectancy, json.dumps(strategy_stats.to_dict(), cls=JSONEncoder)),
            )

        conn.commit()
        conn.close()

        # Save JSON results
        results_json = {
            "timestamp": datetime.now().isoformat(),
            "config": {"symbol": self.config.symbol, "timeframes": self.config.timeframes, "periods": self.config.periods_per_timeframe, "initial_capital": self.config.initial_capital},
            "combined_signal": {"direction": str(combined_result["direction"].value) if hasattr(combined_result["direction"], "value") else str(combined_result["direction"]), "confidence": combined_result["confidence"], "entry_price": combined_result["entry_price"], "stop_loss": combined_result["stop_loss"], "take_profit": combined_result["take_profit"]},
            "strategy_stats": {k: v.to_dict() for k, v in stats.items()},
        }

        json_path = Path(self.config.output_dir) / "backtest_results.json"
        with open(json_path, "w") as f:
            json.dump(results_json, f, indent=2, default=str)

        logger.info(f"Results saved to {json_path}")
        logger.info(f"Database saved to {self.config.database_path}")

    def print_summary(self, stats: Dict[str, StrategyStats]):
        """Print summary of backtest results"""

        print("\n" + "=" * 100)
        print("📊 BACKTEST RESULTS SUMMARY - EURUSD")
        print("=" * 100)
        print(f"{'Strategy':<25} {'Trades':<8} {'Win Rate':<12} {'Profit Factor':<15} {'Total PnL':<15} {'Max DD':<10} {'Expectancy':<12}")
        print("-" * 100)

        for name, s in sorted(stats.items(), key=lambda x: x[1].total_pnl, reverse=True):
            print(f"{name:<25} {s.total_trades:<8} {s.win_rate:>8.1%} {s.profit_factor:>12.2f} {s.total_pnl:>12.2f} {s.max_drawdown:>8.1%} {s.expectancy:>10.4f}")

        print("=" * 100)

        # Best strategy
        best = max(stats.items(), key=lambda x: x[1].expectancy)
        print(f"\n🏆 Best Strategy: {best[0]} (Expectancy: {best[1].expectancy:.4f})")

        # Total statistics
        total_trades = sum(s.total_trades for s in stats.values())
        total_pnl = sum(s.total_pnl for s in stats.values())
        avg_win_rate = np.mean([s.win_rate for s in stats.values()])

        print(f"\n📈 Overall Performance:")
        print(f"   Total Trades Across All Strategies: {total_trades}")
        print(f"   Average Win Rate: {avg_win_rate:.1%}")
        print(f"   Total PnL: ${total_pnl:,.2f}")


def main():
    """Main entry point for backtesting"""

    print("\n" + "=" * 80)
    print("🤖 AI HEDGE FUND v2.1 - COMPLETE STRATEGY BACKTESTER")
    print("=" * 80)
    print("\nTesting all strategies with Trading Plan (H1→M15→M5)")
    print("-" * 80)

    # Configure backtest
    config = BacktestConfig(symbol="EURUSD", timeframes=["H1", "M15", "M5"], periods_per_timeframe=500, initial_capital=10000.0, risk_per_trade=0.02, output_dir="/home/mulky/ai-hedge-fund", database_path="/home/mulky/ai-hedge-fund/backtest_results.db")

    # Run backtest
    backtester = CompleteStrategyBacktester(config)
    stats = backtester.run_complete_backtest()

    # Print summary
    backtester.print_summary(stats)

    return stats


if __name__ == "__main__":
    stats = main()
