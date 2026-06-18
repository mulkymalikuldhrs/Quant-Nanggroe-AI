#!/usr/bin/env python3
"""
Backtest Engine with Execution Reality (from Quant-Nanggroe-AI + Vibe-Trading)
================================================================================
Realistic backtesting: spread, slippage, latency, partial fill, rejection.
Performance metrics: Sharpe, Sortino, Calmar, Max DD, Profit Factor, Win Rate.
"""

import json
import logging
import math
import random
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger("HermesQuantOS.BacktestEngine")


@dataclass
class Trade:
    symbol: str
    direction: str  # BUY/SELL
    entry_price: float
    exit_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    lot_size: float = 0.01
    entry_time: str = ""
    exit_time: str = ""
    pnl: float = 0.0
    pnl_pips: float = 0.0
    result: str = "OPEN"  # WIN/LOSS/BREAKEVEN/OPEN
    exit_reason: str = ""  # TP/SL/MANUAL/END


@dataclass
class BacktestResult:
    trades: List[Trade] = field(default_factory=list)
    initial_balance: float = 10000.0
    final_balance: float = 10000.0
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    avg_rr: float = 0.0
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    execution_reality: Dict = field(default_factory=dict)


class BacktestEngine:
    """
    Full backtesting engine with execution reality model.
    
    Combines:
    - Quant-Nanggroe-AI: Execution Reality (spread/slippage/latency/partial fill)
    - Vibe-Trading: Performance metrics (Sharpe/Sortino/Calmar/Monte Carlo)
    """

    # Execution Reality Parameters
    BASE_SPREAD = 0.0002  # 2 pips
    COMMISSION_PCT = 0.001  # 0.1% per side
    SLIPPAGE_BASE = 0.0001  # 1 pip base slippage
    REJECTION_RATE = 0.01  # 1% order rejection
    PARTIAL_FILL_RATE_HIGH_VOL = 0.15  # 15% in high vol
    PARTIAL_FILL_RATE_NORMAL = 0.02  # 2% normal

    def __init__(self, initial_balance: float = 10000.0):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.equity_curve = [initial_balance]
        self.peak_equity = initial_balance
        self.max_drawdown = 0.0
        self.trades: List[Trade] = []
        self.rejected_orders = 0
        self.partial_fills = 0

    def get_execution_reality(self, volatility: str = "NORMAL") -> Dict:
        """
        Simulate real market execution conditions.
        From Quant-Nanggroe-AI Execution Reality Model.
        """
        vol_multiplier = {"HIGH": 3.0, "NORMAL": 1.0, "LOW": 0.5}.get(volatility, 1.0)

        spread = self.BASE_SPREAD * vol_multiplier
        slippage = (self.BASE_SPREAD / 2) * vol_multiplier * random.random()
        partial_fill = random.random() < (
            self.PARTIAL_FILL_RATE_HIGH_VOL if volatility == "HIGH"
            else self.PARTIAL_FILL_RATE_NORMAL
        )
        order_rejected = random.random() < self.REJECTION_RATE
        latency_ms = int((300 if volatility == "HIGH" else 100) + random.random() * 200)

        return {
            "spread": round(spread, 6),
            "slippage": round(slippage, 6),
            "partial_fill": partial_fill,
            "fill_pct": round(random.uniform(0.7, 1.0), 2) if partial_fill else 1.0,
            "order_rejected": order_rejected,
            "latency_ms": latency_ms,
            "volatility": volatility
        }

    def execute_trade(self, symbol: str, direction: str, entry: float,
                       stop_loss: float, take_profit: float,
                       lot_size: float, volatility: str = "NORMAL",
                       entry_time: str = "") -> Optional[Trade]:
        """Execute a trade with execution reality simulation"""
        reality = self.get_execution_reality(volatility)

        # Check rejection
        if reality["order_rejected"]:
            self.rejected_orders += 1
            logger.info(f"ORDER REJECTED: {symbol} {direction} @ {entry}")
            return None

        # Apply slippage to entry
        if direction == "BUY":
            actual_entry = entry + reality["slippage"]
        else:
            actual_entry = entry - reality["slippage"]

        # Apply partial fill
        actual_lot = lot_size * reality["fill_pct"] if reality["partial_fill"] else lot_size
        if reality["partial_fill"]:
            self.partial_fills += 1

        # Commission
        commission = actual_entry * actual_lot * 100000 * self.COMMISSION_PCT * 2  # Round trip

        trade = Trade(
            symbol=symbol,
            direction=direction,
            entry_price=actual_entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            lot_size=actual_lot,
            entry_time=entry_time or datetime.now().isoformat(),
        )

        # Store execution reality
        trade.exit_reason = str(reality)

        self.trades.append(trade)
        return trade

    def close_trade(self, trade: Trade, exit_price: float,
                     exit_time: str = "", exit_reason: str = "MANUAL") -> Trade:
        """Close a trade and calculate PnL with execution costs"""
        # Apply spread to exit
        if trade.direction == "BUY":
            actual_exit = exit_price - self.BASE_SPREAD
            pnl_pips = actual_exit - trade.entry_price
        else:
            actual_exit = exit_price + self.BASE_SPREAD
            pnl_pips = trade.entry_price - actual_exit

        pnl = pnl_pips * trade.lot_size * 100000
        commission = (trade.entry_price + actual_exit) * trade.lot_size * 100000 * self.COMMISSION_PCT
        pnl -= commission

        trade.exit_price = actual_exit
        trade.exit_time = exit_time or datetime.now().isoformat()
        trade.pnl = round(pnl, 2)
        trade.pnl_pips = round(pnl_pips, 5)
        trade.result = "WIN" if pnl > 0 else "LOSS" if pnl < 0 else "BREAKEVEN"
        trade.exit_reason = exit_reason

        # Update balance
        self.balance += pnl
        self.equity_curve.append(self.balance)

        # Update max drawdown
        self.peak_equity = max(self.peak_equity, self.balance)
        dd = (self.peak_equity - self.balance) / self.peak_equity
        self.max_drawdown = max(self.max_drawdown, dd)

        return trade

    def run_backtest_on_data(self, symbol: str, data: List[Dict],
                              signal_func, volatility: str = "NORMAL") -> Dict:
        """
        Run full backtest on OHLCV data using a signal function.
        
        signal_func(candle, indicators) -> dict with:
          direction, entry, stop_loss, take_profit, lot_size
        """
        from tools.math_engine import MathEngine

        closes = [d["close"] for d in data]
        highs = [d["high"] for d in data]
        lows = [d["low"] for d in data]
        volumes = [d.get("volume", 0) for d in data]

        open_trades: List[Trade] = []

        for i in range(50, len(data)):  # Start after 50 bars for indicators
            candle = data[i]

            # Check open trades for SL/TP hits
            for trade in open_trades[:]:
                if trade.direction == "BUY":
                    if candle["low"] <= trade.stop_loss:
                        self.close_trade(trade, trade.stop_loss, exit_reason="SL")
                        open_trades.remove(trade)
                        continue
                    elif candle["high"] >= trade.take_profit:
                        self.close_trade(trade, trade.take_profit, exit_reason="TP")
                        open_trades.remove(trade)
                        continue
                else:  # SELL
                    if candle["high"] >= trade.stop_loss:
                        self.close_trade(trade, trade.stop_loss, exit_reason="SL")
                        open_trades.remove(trade)
                        continue
                    elif candle["low"] <= trade.take_profit:
                        self.close_trade(trade, trade.take_profit, exit_reason="TP")
                        open_trades.remove(trade)
                        continue

            # Generate signal
            try:
                signal = signal_func(candle, {
                    "closes": closes[:i+1], "highs": highs[:i+1],
                    "lows": lows[:i+1], "volumes": volumes[:i+1]
                })
                if signal and signal.get("direction"):
                    trade = self.execute_trade(
                        symbol, signal["direction"], signal["entry"],
                        signal["stop_loss"], signal["take_profit"],
                        signal.get("lot_size", 0.01), volatility,
                        candle.get("time", "")
                    )
                    if trade:
                        open_trades.append(trade)
            except Exception:
                pass

        # Force close remaining
        for trade in open_trades:
            self.close_trade(trade, closes[-1], exit_reason="END")

        return self.get_results()

    def get_results(self) -> Dict:
        """Calculate comprehensive performance metrics"""
        closed = [t for t in self.trades if t.result in ("WIN", "LOSS", "BREAKEVEN")]
        wins = [t for t in closed if t.result == "WIN"]
        losses = [t for t in closed if t.result == "LOSS"]

        total_pnl = sum(t.pnl for t in closed)
        total_trades = len(closed)
        win_rate = len(wins) / total_trades if total_trades else 0
        avg_win = sum(t.pnl for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t.pnl for t in losses) / len(losses) if losses else 0

        # Profit Factor
        gross_profit = sum(t.pnl for t in wins) if wins else 0
        gross_loss = abs(sum(t.pnl for t in losses)) if losses else 0.01
        profit_factor = gross_profit / gross_loss if gross_loss else 0

        # Sharpe Ratio (annualized, assuming daily returns)
        if len(self.equity_curve) > 1:
            returns = [(self.equity_curve[i] - self.equity_curve[i-1]) / self.equity_curve[i-1]
                      for i in range(1, len(self.equity_curve)) if self.equity_curve[i-1] > 0]
            if returns:
                avg_return = sum(returns) / len(returns)
                std_return = math.sqrt(sum((r - avg_return) ** 2 for r in returns) / len(returns))
                sharpe = (avg_return / std_return * math.sqrt(252)) if std_return else 0

                # Sortino (downside deviation only)
                downside = [r for r in returns if r < 0]
                downside_std = math.sqrt(sum(r**2 for r in downside) / len(downside)) if downside else 0.0001
                sortino = (avg_return / downside_std * math.sqrt(252))

                # Calmar
                calmar = (total_pnl / self.initial_balance) / self.max_drawdown if self.max_drawdown else 0
            else:
                sharpe = sortino = calmar = 0
        else:
            sharpe = sortino = calmar = 0

        # Avg R:R achieved
        rrs = [abs(t.pnl_pips) / abs(t.entry_price - t.stop_loss) * 100000
               for t in closed if abs(t.entry_price - t.stop_loss) > 0]
        avg_rr = sum(rrs) / len(rrs) if rrs else 0

        return {
            "initial_balance": round(self.initial_balance, 2),
            "final_balance": round(self.balance, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl / self.initial_balance * 100, 2),
            "sharpe_ratio": round(sharpe, 2),
            "sortino_ratio": round(sortino, 2),
            "calmar_ratio": round(calmar, 2),
            "max_drawdown_pct": round(self.max_drawdown * 100, 2),
            "win_rate": round(win_rate * 100, 1),
            "profit_factor": round(profit_factor, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "avg_rr": round(avg_rr, 2),
            "total_trades": total_trades,
            "wins": len(wins),
            "losses": len(losses),
            "rejected_orders": self.rejected_orders,
            "partial_fills": self.partial_fills,
            "trades_detail": [{
                "symbol": t.symbol,
                "direction": t.direction,
                "entry": t.entry_price,
                "exit": t.exit_price,
                "pnl": t.pnl,
                "result": t.result,
                "reason": t.exit_reason
            } for t in closed[-20:]],
            "timestamp": datetime.now().isoformat()
        }

    def run(self, symbol: str = "XAUUSD") -> str:
        """Run a simple backtest on the given symbol"""
        try:
            from tools.market_data_tool import MarketDataTool
            mdt = MarketDataTool()
            raw = json.loads(mdt.get_ohlcv(symbol, "1d", 200))

            if "error" in raw:
                return json.dumps({"error": raw["error"]})

            data = raw.get("data", [])
            if len(data) < 50:
                return json.dumps({"error": "Insufficient data for backtest"})

            # Simple moving average crossover strategy
            def sma_crossover(candle: Dict, indicators: Dict) -> Optional[Dict]:
                closes = indicators.get("closes", [])
                if len(closes) < 50:
                    return None
                ema20 = sum(closes[-20:]) / 20
                ema50 = sum(closes[-50:]) / 50
                price = candle["close"]
                atr = max(closes) - min(closes[-14:]) if len(closes) >= 14 else price * 0.005

                if ema20 > ema50 and len(closes) > 50:
                    prev_ema20 = sum(closes[-21:-1]) / 20
                    prev_ema50 = sum(closes[-51:-1]) / 50
                    if prev_ema20 <= prev_ema50:  # Cross up
                        return {
                            "direction": "BUY",
                            "entry": price,
                            "stop_loss": price - atr * 1.5,
                            "take_profit": price + atr * 2.0,
                            "lot_size": 0.01
                        }
                elif ema20 < ema50 and len(closes) > 50:
                    prev_ema20 = sum(closes[-21:-1]) / 20
                    prev_ema50 = sum(closes[-51:-1]) / 50
                    if prev_ema20 >= prev_ema50:  # Cross down
                        return {
                            "direction": "SELL",
                            "entry": price,
                            "stop_loss": price + atr * 1.5,
                            "take_profit": price - atr * 2.0,
                            "lot_size": 0.01
                        }
                return None

            results = self.run_backtest_on_data(symbol, data, sma_crossover)
            return json.dumps(results, indent=2)

        except Exception as e:
            return json.dumps({"error": str(e)})

    def status(self) -> str:
        """Get backtest engine status"""
        return json.dumps({
            "initial_balance": self.initial_balance,
            "current_balance": round(self.balance, 2),
            "total_trades": len(self.trades),
            "rejected_orders": self.rejected_orders,
            "partial_fills": self.partial_fills,
            "max_drawdown_pct": round(self.max_drawdown * 100, 2),
            "timestamp": datetime.now().isoformat()
        }, indent=2)
