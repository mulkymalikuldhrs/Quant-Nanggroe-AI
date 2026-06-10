"""
AI Hedge Fund v2.1 - Comprehensive Backtesting System
Tests all strategies, agents, and timeframes following the trading plan
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
from pathlib import Path
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Timeframe(Enum):
    H1 = "H1"
    M15 = "M15"
    M5 = "M5"


class StrategyType(Enum):
    TREND_FOLLOWING = "TREND_FOLLOWING"
    MEAN_REVERSION = "MEAN_REVERSION"
    MOMENTUM = "MOMENTUM"
    BREAKOUT = "BREAKOUT"
    SWING = "SWING"
    SCALP = "SCALP"


@dataclass
class BacktestResult:
    """Result of a single backtest"""

    strategy_name: str
    symbol: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    total_pnl: float
    max_drawdown: float
    sharpe_ratio: float
    average_win: float
    average_loss: float
    risk_reward_ratio: float
    expectancy: float
    equity_curve: List[float]
    trade_log: List[Dict]

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class BacktestConfig:
    """Configuration for backtesting"""

    symbol: str = "EURUSD"
    timeframes: List[str] = field(default_factory=lambda: ["H1", "M15", "M5"])
    start_date: datetime = None
    end_date: datetime = None
    initial_capital: float = 10000.0
    risk_per_trade: float = 0.02
    spread: float = 0.0001
    commission: float = 0.0001
    slippage: float = 0.00005


class MarketDataGenerator:
    """Generates realistic market data for backtesting"""

    @staticmethod
    def generate_ohlcv(symbol: str, timeframe: str, periods: int = 1000, start_price: float = None, volatility: float = 0.001, drift: float = 0.00001) -> pd.DataFrame:
        """Generate OHLCV data with realistic price movements"""

        # Set base price based on symbol
        if start_price is None:
            base_prices = {
                "EURUSD": 1.0850,
                "GBPUSD": 1.2650,
                "USDJPY": 149.50,
                "USDCHF": 0.8850,
                "AUDUSD": 0.6520,
                "GOLD": 2025.0,
            }
            start_price = base_prices.get(symbol, 1.0850)

        # Calculate minutes per candle
        tf_minutes = {"H1": 60, "M15": 15, "M5": 5}
        minutes = tf_minutes.get(timeframe, 60)

        # Generate timestamps
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=minutes * periods)
        timestamps = [start_time + timedelta(minutes=minutes * i) for i in range(periods)]

        # Generate price movements (Geometric Brownian Motion)
        np.random.seed(42 + hash(symbol) % 1000)  # Reproducible but varied
        returns = np.random.normal(drift, volatility, periods)

        # Add some trend patterns
        trend_factor = np.linspace(0, 0.1, periods)  # Slight uptrend
        returns += trend_factor * 0.001

        # Generate prices
        prices = [start_price]
        for r in returns[:-1]:
            prices.append(prices[-1] * (1 + r))

        # Generate OHLC
        data = []
        for i, close in enumerate(prices):
            high = close * (1 + abs(np.random.normal(0, volatility)))
            low = close * (1 - abs(np.random.normal(0, volatility)))
            open_price = prices[i - 1] if i > 0 else close

            volume = np.random.randint(1000, 10000)

            data.append({"time": timestamps[i], "open": open_price, "high": max(high, open_price, close), "low": min(low, open_price, close), "close": close, "volume": volume})

        df = pd.DataFrame(data)
        df.set_index("time", inplace=True)

        # Add technical indicators
        df["rsi"] = MarketDataGenerator._calculate_rsi(df["close"], 14)
        df["macd"] = MarketDataGenerator._calculate_macd(df["close"])
        df["macd_signal"] = MarketDataGenerator._calculate_macd_signal(df["close"])
        df["atr"] = MarketDataGenerator._calculate_atr(df, 14)
        df["ema_20"] = df["close"].ewm(span=20).mean()
        df["ema_50"] = df["close"].ewm(span=50).mean()
        df["ema_200"] = df["close"].ewm(span=200).mean()

        return df

    @staticmethod
    def _calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def _calculate_macd(prices: pd.Series, fast: int = 12, slow: int = 26) -> pd.Series:
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        return ema_fast - ema_slow

    @staticmethod
    def _calculate_macd_signal(prices: pd.Series) -> pd.Series:
        macd = MarketDataGenerator._calculate_macd(prices)
        return macd.ewm(span=9).mean()

    @staticmethod
    def _calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        high_low = df["high"] - df["low"]
        high_close = abs(df["high"] - df["close"].shift())
        low_close = abs(df["low"] - df["close"].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()


class TradingPlanBacktester:
    """Backtests using the User Trading Plan logic (H1/M15/M5)"""

    def __init__(self, config: BacktestConfig):
        self.config = config
        self.results: List[BacktestResult] = []

    def run_backtest(self, symbol: str, timeframe: str) -> BacktestResult:
        """Run backtest for a specific symbol and timeframe"""

        logger.info(f"Backtesting {symbol} on {timeframe}")

        # Generate market data
        periods = {"H1": 500, "M15": 1000, "M5": 3000}
        df = MarketDataGenerator.generate_ohlcv(symbol, timeframe, periods=periods.get(timeframe, 2000))

        # Run trading plan logic
        trades = self._apply_trading_plan(df, symbol, timeframe)

        # Calculate metrics
        result = self._calculate_metrics(trades, symbol, timeframe, df)

        self.results.append(result)
        return result

    def _apply_trading_plan(self, df: pd.DataFrame, symbol: str, timeframe: str) -> List[Dict]:
        """Apply the trading plan logic to generate trades"""

        trades = []
        position = None
        capital = self.config.initial_capital

        h1_df = df if timeframe == "H1" else None

        for i in range(200, len(df)):  # Skip first 200 for indicators
            current = df.iloc[i]
            previous = df.iloc[i - 1]

            # Trading Plan Logic (simplified version)
            signal = self._get_signal(df, i, h1_df)

            if signal == "BUY" and position is None:
                sl = current["close"] - current["atr"] * 1.5 if "atr" in current else current["close"] * 0.998
                tp = current["close"] + current["atr"] * 3.0 if "atr" in current else current["close"] * 1.006

                position = {"type": "LONG", "entry": current["close"], "sl": sl, "tp": tp, "size": self._calculate_position_size(capital, sl, current["close"])}

            elif signal == "SELL" and position is None:
                sl = current["close"] + current["atr"] * 1.5 if "atr" in current else current["close"] * 1.002
                tp = current["close"] - current["atr"] * 3.0 if "atr" in current else current["close"] * 0.994

                position = {"type": "SHORT", "entry": current["close"], "sl": sl, "tp": tp, "size": self._calculate_position_size(capital, sl, current["close"])}

            # Check SL/TP
            if position:
                exit_time = df.index[i]
                if position["type"] == "LONG":
                    if current["close"] <= position["sl"]:
                        trades.append(self._close_trade(position, position["sl"], exit_time, "SL"))
                        position = None
                    elif current["close"] >= position["tp"]:
                        trades.append(self._close_trade(position, position["tp"], exit_time, "TP"))
                        position = None
                else:
                    if current["close"] >= position["sl"]:
                        trades.append(self._close_trade(position, position["sl"], exit_time, "SL"))
                        position = None
                    elif current["close"] <= position["tp"]:
                        trades.append(self._close_trade(position, position["tp"], exit_time, "TP"))
                        position = None

        # Close any open position
        if position:
            trades.append(self._close_trade(position, df.iloc[-1]["close"], df.index[-1], "EOD"))

        return trades

    def _get_signal(self, df: pd.DataFrame, i: int, h1_df: pd.DataFrame = None) -> str:
        """Generate signal based on trading plan rules"""

        current = df.iloc[i]
        ema_20 = current["ema_20"]
        ema_50 = current["ema_50"]
        ema_200 = current["ema_200"]
        rsi = current["rsi"]
        macd = current["macd"]
        macd_signal = current["macd_signal"]

        # Bullish conditions
        bullish = (current["close"] > ema_200) and (ema_20 > ema_50) and (rsi > 50) and (macd > macd_signal)

        # Bearish conditions
        bearish = (current["close"] < ema_200) and (ema_20 < ema_50) and (rsi < 50) and (macd < macd_signal)

        if bullish:
            return "BUY"
        elif bearish:
            return "SELL"
        return "NEUTRAL"

    def _calculate_position_size(self, capital: float, sl: float, entry: float) -> float:
        """Calculate position size based on risk"""
        risk_amount = capital * self.config.risk_per_trade
        sl_distance = abs(entry - sl)
        if sl_distance == 0:
            sl_distance = entry * 0.001
        return risk_amount / sl_distance

    def _close_trade(self, position: Dict, exit_price: float, exit_time: datetime, reason: str) -> Dict:
        """Close a trade and record result"""

        if position["type"] == "LONG":
            pnl_pct = (exit_price - position["entry"]) / position["entry"]
        else:
            pnl_pct = (position["entry"] - exit_price) / position["entry"]

        return {"type": position["type"], "entry": position["entry"], "exit": exit_price, "size": position["size"], "pnl_pct": pnl_pct, "exit_time": exit_time, "reason": reason}

    def _calculate_metrics(self, trades: List[Dict], symbol: str, timeframe: str, df: pd.DataFrame) -> BacktestResult:
        """Calculate backtest metrics"""

        if not trades:
            return BacktestResult(strategy_name="TradingPlan", symbol=symbol, timeframe=timeframe, start_date=df.index[0], end_date=df.index[-1], total_trades=0, winning_trades=0, losing_trades=0, win_rate=0, profit_factor=0, total_pnl=0, max_drawdown=0, sharpe_ratio=0, average_win=0, average_loss=0, risk_reward_ratio=0, expectancy=0, equity_curve=[self.config.initial_capital], trade_log=[])

        # Calculate PnL for each trade
        pnls = [t["pnl_pct"] for t in trades]
        winning_pnls = [p for p in pnls if p > 0]
        losing_pnls = [p for p in pnls if p <= 0]

        # Equity curve
        equity = [self.config.initial_capital]
        for trade in trades:
            equity.append(equity[-1] * (1 + trade["pnl_pct"] * trade["size"]))

        # Max drawdown
        peak = equity[0]
        max_dd = 0
        for e in equity:
            if e > peak:
                peak = e
            dd = (peak - e) / peak
            if dd > max_dd:
                max_dd = dd

        # Calculate metrics
        win_rate = len(winning_pnls) / len(pnls) if pnls else 0
        avg_win = np.mean(winning_pnls) if winning_pnls else 0
        avg_loss = abs(np.mean(losing_pnls)) if losing_pnls else 0
        profit_factor = sum(winning_pnls) / abs(sum(losing_pnls)) if losing_pnls and sum(losing_pnls) != 0 else 0

        total_pnl = (equity[-1] - equity[0]) / equity[0] * 100

        # Sharpe ratio (annualized)
        returns = pd.Series(equity).pct_change().dropna()
        sharpe = returns.mean() / returns.std() * np.sqrt(252 * 24) if returns.std() > 0 else 0

        # Expectancy
        expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)

        # Risk/Reward ratio
        rr = avg_win / avg_loss if avg_loss > 0 else 0

        return BacktestResult(
            strategy_name="TradingPlan",
            symbol=symbol,
            timeframe=timeframe,
            start_date=df.index[0],
            end_date=df.index[-1],
            total_trades=len(trades),
            winning_trades=len(winning_pnls),
            losing_trades=len(losing_pnls),
            win_rate=win_rate * 100,
            profit_factor=profit_factor,
            total_pnl=total_pnl,
            max_drawdown=max_dd * 100,
            sharpe_ratio=sharpe,
            average_win=avg_win * 100,
            average_loss=avg_loss * 100,
            risk_reward_ratio=rr,
            expectancy=expectancy * 100,
            equity_curve=equity,
            trade_log=trades,
        )


class StrategyBacktester:
    """Backtests individual strategies"""

    def __init__(self, config: BacktestConfig):
        self.config = config
        self.results: Dict[str, BacktestResult] = {}

    def run_strategy_backtest(self, strategy_name: str, symbol: str, timeframe: str) -> BacktestResult:
        """Backtest a specific strategy"""

        logger.info(f"Backtesting {strategy_name} on {symbol}/{timeframe}")

        periods = {"H1": 500, "M15": 1000, "M5": 3000}
        df = MarketDataGenerator.generate_ohlcv(symbol, timeframe, periods=periods.get(timeframe, 2000))

        trades = self._apply_strategy(df, strategy_name)
        result = self._calculate_metrics(trades, strategy_name, symbol, timeframe, df)

        self.results[f"{strategy_name}_{symbol}_{timeframe}"] = result
        return result

    def _apply_strategy(self, df: pd.DataFrame, strategy_name: str) -> List[Dict]:
        """Apply strategy-specific logic"""

        trades = []
        position = None

        for i in range(50, len(df)):
            current = df.iloc[i]
            signal = self._get_strategy_signal(df, i, strategy_name)

            if signal == "BUY" and position is None:
                position = self._open_position(df.iloc[i], "LONG")
            elif signal == "SELL" and position is None:
                position = self._open_position(df.iloc[i], "SHORT")

            if position:
                closed, position = self._check_exit(df.iloc[i], position)
                if closed:
                    trades.append(closed)

        if position:
            trades.append(self._close_at_market(position, df.iloc[-1]))

        return trades

    def _get_strategy_signal(self, df: pd.DataFrame, i: int, strategy_name: str) -> str:
        """Get signal based on strategy"""

        current = df.iloc[i]
        prev = df.iloc[i - 1] if i > 0 else current

        signals = {
            "TREND_FOLLOWING": self._trend_following_signal(current, prev),
            "MEAN_REVERSION": self._mean_reversion_signal(current, df, i),
            "MOMENTUM": self._momentum_signal(current, prev),
            "BREAKOUT": self._breakout_signal(df, i),
            "SWING": self._swing_signal(current, prev),
            "SCALP": self._scalp_signal(current, prev),
        }

        return signals.get(strategy_name, "NEUTRAL")

    def _trend_following_signal(self, current, prev) -> str:
        ema_20 = current["ema_20"]
        ema_50 = current["ema_50"]

        if current["close"] > ema_20 > ema_50:
            return "BUY"
        elif current["close"] < ema_20 < ema_50:
            return "SELL"
        return "NEUTRAL"

    def _mean_reversion_signal(self, current, df, i) -> str:
        rsi = current["rsi"]

        if rsi < 30:
            return "BUY"
        elif rsi > 70:
            return "SELL"
        return "NEUTRAL"

    def _momentum_signal(self, current, prev) -> str:
        macd = current["macd"]
        signal = current["macd_signal"]

        if macd > signal and prev["macd"] <= prev["macd_signal"]:
            return "BUY"
        elif macd < signal and prev["macd"] >= prev["macd_signal"]:
            return "SELL"
        return "NEUTRAL"

    def _breakout_signal(self, df, i) -> str:
        if i < 20:
            return "NEUTRAL"

        current = df.iloc[i]
        prev_high = df.iloc[i - 20 : i]["high"].max()
        prev_low = df.iloc[i - 20 : i]["low"].min()

        if current["close"] > prev_high:
            return "BUY"
        elif current["close"] < prev_low:
            return "SELL"
        return "NEUTRAL"

    def _swing_signal(self, current, prev) -> str:
        if current["close"] > prev["close"] * 1.002:
            return "BUY"
        elif current["close"] < prev["close"] * 0.998:
            return "SELL"
        return "NEUTRAL"

    def _scalp_signal(self, current, prev) -> str:
        if current["close"] > prev["close"] and current["rsi"] > 50:
            return "BUY"
        elif current["close"] < prev["close"] and current["rsi"] < 50:
            return "SELL"
        return "NEUTRAL"

    def _open_position(self, candle, side: str) -> Dict:
        atr = candle.get("atr", candle["close"] * 0.001)

        if side == "LONG":
            sl = candle["close"] - atr * 1.5
            tp = candle["close"] + atr * 3.0
        else:
            sl = candle["close"] + atr * 1.5
            tp = candle["close"] - atr * 3.0

        return {"type": side, "entry": candle["close"], "sl": sl, "tp": tp, "size": self.config.risk_per_trade, "entry_time": candle.name}

    def _check_exit(self, candle, position: Dict) -> Tuple[Dict, None]:
        """Check if position should be closed"""

        if position["type"] == "LONG":
            if candle["close"] <= position["sl"]:
                return self._close_trade(position, position["sl"], candle.name, "SL"), None
            elif candle["close"] >= position["tp"]:
                return self._close_trade(position, position["tp"], candle.name, "TP"), None
        else:
            if candle["close"] >= position["sl"]:
                return self._close_trade(position, position["sl"], candle.name, "SL"), None
            elif candle["close"] <= position["tp"]:
                return self._close_trade(position, position["tp"], candle.name, "TP"), None

        return None, position

    def _close_trade(self, position, exit_price, exit_time, reason) -> Dict:
        pnl = (exit_price - position["entry"]) / position["entry"] if position["type"] == "LONG" else (position["entry"] - exit_price) / position["entry"]

        return {"type": position["type"], "entry": position["entry"], "exit": exit_price, "size": position["size"], "pnl_pct": pnl, "exit_time": exit_time, "reason": reason}

    def _close_at_market(self, position, candle) -> Dict:
        return self._close_trade(position, candle["close"], candle.name, "EOD")

    def _calculate_metrics(self, trades: List[Dict], strategy_name: str, symbol: str, timeframe: str, df: pd.DataFrame) -> BacktestResult:
        """Calculate metrics for strategy backtest"""

        if not trades:
            return BacktestResult(strategy_name=strategy_name, symbol=symbol, timeframe=timeframe, start_date=df.index[0], end_date=df.index[-1], total_trades=0, winning_trades=0, losing_trades=0, win_rate=0, profit_factor=0, total_pnl=0, max_drawdown=0, sharpe_ratio=0, average_win=0, average_loss=0, risk_reward_ratio=0, expectancy=0, equity_curve=[self.config.initial_capital], trade_log=[])

        equity = [self.config.initial_capital]
        for trade in trades:
            equity.append(equity[-1] * (1 + trade["pnl_pct"] * trade["size"]))

        pnls = [t["pnl_pct"] for t in trades]
        winning = [p for p in pnls if p > 0]
        losing = [p for p in pnls if p <= 0]

        win_rate = len(winning) / len(pnls) * 100 if pnls else 0
        avg_win = np.mean(winning) * 100 if winning else 0
        avg_loss = abs(np.mean(losing)) * 100 if losing else 0

        peak = equity[0]
        max_dd = 0
        for e in equity:
            if e > peak:
                peak = e
            dd = (peak - e) / peak
            if dd > max_dd:
                max_dd = dd

        total_pnl = (equity[-1] - equity[0]) / equity[0] * 100
        pf = sum(winning) / abs(sum(losing)) if losing and sum(losing) != 0 else 0

        returns = pd.Series(equity).pct_change().dropna()
        sharpe = returns.mean() / returns.std() * np.sqrt(252 * 24) if returns.std() > 0 else 0

        rr = avg_win / avg_loss if avg_loss > 0 else 0
        expectancy = (win_rate / 100 * avg_win) - ((1 - win_rate / 100) * avg_loss)

        return BacktestResult(
            strategy_name=strategy_name,
            symbol=symbol,
            timeframe=timeframe,
            start_date=df.index[0],
            end_date=df.index[-1],
            total_trades=len(trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            win_rate=win_rate,
            profit_factor=pf,
            total_pnl=total_pnl,
            max_drawdown=max_dd * 100,
            sharpe_ratio=sharpe,
            average_win=avg_win,
            average_loss=avg_loss,
            risk_reward_ratio=rr,
            expectancy=expectancy,
            equity_curve=equity,
            trade_log=trades,
        )


class BacktestManager:
    """Manages all backtesting operations"""

    def __init__(self, db_path: str = "backtest_results.db"):
        self.db_path = db_path
        self.config = BacktestConfig()
        self.all_results: List[BacktestResult] = []
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database for results"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS backtest_results (
                id INTEGER PRIMARY KEY,
                strategy_name TEXT,
                symbol TEXT,
                timeframe TEXT,
                start_date TEXT,
                end_date TEXT,
                total_trades INTEGER,
                winning_trades INTEGER,
                losing_trades INTEGER,
                win_rate REAL,
                profit_factor REAL,
                total_pnl REAL,
                max_drawdown REAL,
                sharpe_ratio REAL,
                average_win REAL,
                average_loss REAL,
                risk_reward_ratio REAL,
                expectancy REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS equity_curves (
                id INTEGER PRIMARY KEY,
                result_id INTEGER,
                equity REAL,
                FOREIGN KEY(result_id) REFERENCES backtest_results(id))
        """
        )

        conn.commit()
        conn.close()

    def run_full_backtest(self, symbols: List[str] = None, timeframes: List[str] = None, strategies: List[str] = None) -> Dict:
        """Run comprehensive backtest across all configurations"""

        if symbols is None:
            symbols = ["EURUSD", "GBPUSD", "USDJPY"]
        if timeframes is None:
            timeframes = ["H1", "M15", "M5"]
        if strategies is None:
            strategies = ["TREND_FOLLOWING", "MEAN_REVERSION", "MOMENTUM", "BREAKOUT", "SWING", "SCALP"]

        results = {"trading_plan": {}, "strategies": {}, "summary": {}}

        total_tests = len(symbols) * len(timeframes) * (1 + len(strategies))
        current = 0

        logger.info(f"Starting {total_tests} backtests...")

        # Test Trading Plan for each symbol/timeframe
        for symbol in symbols:
            results["trading_plan"][symbol] = {}
            for tf in timeframes:
                current += 1
                logger.info(f"[{current}/{total_tests}] Testing TradingPlan {symbol}/{tf}")

                tester = TradingPlanBacktester(self.config)
                result = tester.run_backtest(symbol, tf)
                self.all_results.append(result)
                results["trading_plan"][symbol][tf] = result
                self._save_result(result)

        # Test each strategy
        for strategy in strategies:
            results["strategies"][strategy] = {}
            for symbol in symbols:
                for tf in timeframes:
                    current += 1
                    logger.info(f"[{current}/{total_tests}] Testing {strategy} {symbol}/{tf}")

                    tester = StrategyBacktester(self.config)
                    result = tester.run_strategy_backtest(strategy, symbol, tf)
                    self.all_results.append(result)
                    results["strategies"][strategy][f"{symbol}_{tf}"] = result
                    self._save_result(result)

        # Generate summary
        results["summary"] = self._generate_summary()

        return results

    def _save_result(self, result: BacktestResult):
        """Save result to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO backtest_results (
                strategy_name, symbol, timeframe, start_date, end_date,
                total_trades, winning_trades, losing_trades, win_rate,
                profit_factor, total_pnl, max_drawdown, sharpe_ratio,
                average_win, average_loss, risk_reward_ratio, expectancy
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (result.strategy_name, result.symbol, result.timeframe, str(result.start_date), str(result.end_date), result.total_trades, result.winning_trades, result.losing_trades, result.win_rate, result.profit_factor, result.total_pnl, result.max_drawdown, result.sharpe_ratio, result.average_win, result.average_loss, result.risk_reward_ratio, result.expectancy),
        )

        result_id = cursor.lastrowid

        # Save equity curve
        for i, equity in enumerate(result.equity_curve):
            cursor.execute(
                """
                INSERT INTO equity_curves (result_id, equity) VALUES (?, ?)
            """,
                (result_id, equity),
            )

        conn.commit()
        conn.close()

    def _generate_summary(self) -> Dict:
        """Generate summary statistics"""

        if not self.all_results:
            return {}

        by_strategy = {}
        by_timeframe = {}
        by_symbol = {}

        for result in self.all_results:
            # By strategy
            if result.strategy_name not in by_strategy:
                by_strategy[result.strategy_name] = []
            by_strategy[result.strategy_name].append(result)

            # By timeframe
            if result.timeframe not in by_timeframe:
                by_timeframe[result.timeframe] = []
            by_timeframe[result.timeframe].append(result)

            # By symbol
            if result.symbol not in by_symbol:
                by_symbol[result.symbol] = []
            by_symbol[result.symbol].append(result)

        def calc_avg(results_list):
            if not results_list:
                return {}
            return {
                "win_rate": np.mean([r.win_rate for r in results_list]),
                "profit_factor": np.mean([r.profit_factor for r in results_list]),
                "total_pnl": np.mean([r.total_pnl for r in results_list]),
                "max_drawdown": np.mean([r.max_drawdown for r in results_list]),
                "sharpe_ratio": np.mean([r.sharpe_ratio for r in results_list]),
                "risk_reward": np.mean([r.risk_reward_ratio for r in results_list]),
                "total_trades": sum([r.total_trades for r in results_list]),
            }

        summary = {"by_strategy": {k: calc_avg(v) for k, v in by_strategy.items()}, "by_timeframe": {k: calc_avg(v) for k, v in by_timeframe.items()}, "by_symbol": {k: calc_avg(v) for k, v in by_symbol.items()}, "overall": calc_avg(self.all_results), "test_count": len(self.all_results)}

        return summary

    def get_results(self, filters: Dict = None) -> List[BacktestResult]:
        """Query results from database"""
        if filters is None:
            return self.all_results

        results = []
        for r in self.all_results:
            match = True
            for key, value in filters.items():
                if getattr(r, key, None) != value:
                    match = False
                    break
            if match:
                results.append(r)

        return results

    def export_results(self, filepath: str = "backtest_results.json"):
        """Export all results to JSON"""
        data = {"results": [r.to_dict() for r in self.all_results], "summary": self._generate_summary(), "exported_at": datetime.now().isoformat()}

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Results exported to {filepath}")
        return filepath


def run_demo_backtest():
    """Run demonstration backtest"""

    print("\n" + "=" * 70)
    print("🚀 COMPREHENSIVE BACKTESTING SYSTEM v2.1")
    print("=" * 70 + "\n")

    manager = BacktestManager()

    # Quick demo with limited scope
    symbols = ["EURUSD"]
    timeframes = ["H1"]
    strategies = ["TREND_FOLLOWING", "MEAN_REVERSION"]

    print(f"📊 Configuration:")
    print(f"   Symbols: {symbols}")
    print(f"   Timeframes: {timeframes}")
    print(f"   Strategies: {strategies}")
    print(f"   Trading Plan: H1→M15→M5\n")

    print("🔄 Running backtests...\n")

    results = manager.run_full_backtest(symbols, timeframes, strategies)

    # Display results
    print("\n" + "=" * 70)
    print("📈 BACKTEST RESULTS")
    print("=" * 70 + "\n")

    # Trading Plan Results
    print("━" * 70)
    print("📋 TRADING PLAN (Multi-Timeframe)")
    print("━" * 70)

    for symbol, tfs in results["trading_plan"].items():
        for tf, result in tfs.items():
            print(f"\n{symbol} [{tf}]:")
            print(f"   Trades: {result.total_trades} | Win Rate: {result.win_rate:.1f}%")
            print(f"   PnL: {result.total_pnl:+.2f}% | Max DD: {result.max_drawdown:.2f}%")
            print(f"   Sharpe: {result.sharpe_ratio:.2f} | RR: 1:{result.risk_reward_ratio:.2f}")
            print(f"   PF: {result.profit_factor:.2f} | Expectancy: {result.expectancy:.3f}%")

    # Strategy Results
    print("\n" + "━" * 70)
    print("📊 STRATEGY COMPARISON")
    print("━" * 70)

    summary = results["summary"]["by_strategy"]
    for strategy, stats in summary.items():
        print(f"\n{strategy}:")
        print(f"   Win Rate: {stats['win_rate']:.1f}% | PnL: {stats['total_pnl']:+.2f}%")
        print(f"   Sharpe: {stats['sharpe_ratio']:.2f} | RR: 1:{stats['risk_reward']:.2f}")
        print(f"   Max DD: {stats['max_drawdown']:.2f}% | Total Trades: {int(stats['total_trades'])}")

    # Overall Summary
    print("\n" + "=" * 70)
    print("📊 OVERALL SUMMARY")
    print("=" * 70)

    overall = results["summary"]["overall"]
    print(f"\n   Tests Run: {results['summary']['test_count']}")
    print(f"   Avg Win Rate: {overall['win_rate']:.1f}%")
    print(f"   Avg PnL: {overall['total_pnl']:+.2f}%")
    print(f"   Avg Sharpe: {overall['sharpe_ratio']:.2f}")
    print(f"   Avg Max DD: {overall['max_drawdown']:.2f}%")
    print(f"   Total Trades: {int(overall['total_trades'])}")

    # Export
    print("\n" + "=" * 70)
    print("💾 EXPORTING RESULTS")
    print("=" * 70)

    filepath = manager.export_results("backtest_results.json")
    print(f"\n✅ Results saved to: {filepath}")

    print("\n" + "=" * 70)
    print("✅ BACKTEST COMPLETE")
    print("=" * 70 + "\n")

    return manager, results


if __name__ == "__main__":
    manager, results = run_demo_backtest()
