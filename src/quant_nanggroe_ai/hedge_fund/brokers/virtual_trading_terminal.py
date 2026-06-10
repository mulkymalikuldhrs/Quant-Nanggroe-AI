"""
Virtual Trading Terminal - Web-based Interface for AI Hedge Fund

Features:
- Real-time market data streaming
- AI-powered signal generation dashboard
- One-click order execution
- Portfolio management
- Performance analytics
- Multi-broker support

No paid MetaTrader API needed - built from scratch!
"""

import asyncio
import json
import logging
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.utils import PlotlyJSONEncoder
from src.brokers.free_broker_api import FreeBrokerGateway, BrokerAPI, BrokerType, OrderRequest, OrderSide, OrderType, TimeInForce, Account, Position, MarketData
from src.strategies.wyckoff.wyckoff_strategy import WyckoffAnalyzer, WyckoffPhase
from src.analysis.timeframe.multi_timeframe import MultiTimeframeAnalyzer, TrendDirection

logger = logging.getLogger(__name__)


class TradingTerminal:
    """
    Virtual Trading Terminal - Web-based trading interface
    """

    def __init__(self, flask_app: Flask, socketio: SocketIO):
        self.app = flask_app
        self.socketio = socketio
        self.broker_gateway = FreeBrokerGateway()
        self.wyckoff_analyzer = WyckoffAnalyzer()
        self.tf_analyzer = MultiTimeframeAnalyzer()

        self.active_trades: Dict[str, Dict] = {}
        self.trade_history: List[Dict] = []
        self.performance_metrics: Dict = self._init_metrics()

        self._setup_routes()
        self._setup_websocket()

    def _init_metrics(self) -> Dict:
        return {"total_pnl": 0.0, "win_rate": 0.0, "profit_factor": 0.0, "total_trades": 0, "winning_trades": 0, "losing_trades": 0, "avg_win": 0.0, "avg_loss": 0.0, "max_drawdown": 0.0, "sharpe_ratio": 0.0, "equity_curve": [], "daily_returns": []}

    def _setup_routes(self):
        @self.app.route("/")
        def index():
            return render_template("terminal.html")

        @self.app.route("/api/status")
        def status():
            return jsonify({"status": "online", "timestamp": datetime.now().isoformat(), "brokers": {b.name: b.connected for b in self.broker_gateway.brokers.values()}, "active_trades": len(self.active_trades), "performance": self.performance_metrics})

        @self.app.route("/api/account")
        async def account():
            accounts = await self.broker_gateway.get_all_accounts()
            return jsonify({"accounts": [self._serialize_account(acc) for acc in accounts]})

        @self.app.route("/api/orders", methods=["GET", "POST"])
        async def orders():
            if request.method == "POST":
                data = request.json
                order = OrderRequest(symbol=data["symbol"], side=OrderSide(data["side"]), order_type=OrderType(data.get("order_type", "market")), quantity=float(data["quantity"]), price=float(data.get("price", 0)) if data.get("price") else None, broker=BrokerType(data.get("broker", "paper")))

                result = await self.broker_gateway.place_order(order)
                return jsonify({"success": True, "order": asdict(result)})

            return jsonify({"orders": [asdict(o) for o in (await self.broker_gateway.get_all_accounts())[0].orders.values()]})

        @self.app.route("/api/trades")
        def trades():
            return jsonify({"active": self.active_trades, "history": self.trade_history})

        @self.app.route("/api/analysis/wyckoff")
        async def wyckoff_analysis():
            symbol = request.args.get("symbol", "BTCUSDT")
            candles = await self._fetch_candles(symbol, "1h", 100)

            analysis = self.wyckoff_analyzer.analyze(candles)
            return jsonify({"symbol": symbol, "phase": analysis.phase.value if analysis.phase else None, "confidence": analysis.confidence if analysis else 0, "events": analysis.events if analysis else [], "projection": {"target": analysis.target if analysis else None, "stop": analysis.stop if analysis else None}})

        @self.app.route("/api/analysis/timeframe")
        async def timeframe_analysis():
            symbol = request.args.get("symbol", "BTCUSDT")

            tf_analysis = await self.tf_analyzer.analyze_alignment(symbol, timeframes=["1h", "4h", "1d"])

            return jsonify({"symbol": symbol, "alignment": {"direction": tf_analysis.direction.value if tf_analysis.direction else None, "confidence": tf_analysis.confidence if tf_analysis.direction else 0, "timeframes": tf_analysis.timeframe_results}})

        @self.app.route("/api/analysis/combined")
        async def combined_analysis():
            symbol = request.args.get("symbol", "BTCUSDT")

            wyckoff = self.wyckoff_analyzer.analyze(await self._fetch_candles(symbol, "1h", 100))
            tf_analysis = await self.tf_analyzer.analyze_alignment(symbol, ["1h", "4h", "1d"])

            signal_score = 0
            reasons = []

            if wyckoff and wyckoff.phase in [WyckoffPhase.ACCUMULATION_C, WyckoffPhase.MARKUP]:
                signal_score += 40
                reasons.append(f"Wyckoff: {wyckoff.phase.value}")

            if tf_analysis.direction == TrendDirection.BULLISH:
                signal_score += 30
                reasons.append("Multi-TF: Bullish alignment")

            if tf_analysis.confidence > 70:
                signal_score += 20
                reasons.append(f"High confidence: {tf_analysis.confidence}%")

            if wyckoff and wyckoff.events:
                signal_score += 10
                reasons.append(f"Wyckoff events: {', '.join(wyckoff.events)}")

            return jsonify(
                {
                    "symbol": symbol,
                    "signal_score": signal_score,
                    "signal": "STRONG_BUY" if signal_score > 70 else "BUY" if signal_score > 50 else "NEUTRAL" if signal_score > 30 else "AVOID",
                    "reasons": reasons,
                    "wyckoff": {"phase": wyckoff.phase.value if wyckoff else None, "confidence": wyckoff.confidence if wyckoff else 0},
                    "timeframe": {"direction": tf_analysis.direction.value if tf_analysis else None, "confidence": tf_analysis.confidence if tf_analysis else 0},
                }
            )

        @self.app.route("/api/charts/equity")
        def equity_chart():
            equity_curve = self.performance_metrics["equity_curve"]

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=[e["timestamp"] for e in equity_curve], y=[e["equity"] for e in equity_curve], mode="lines", name="Equity", line=dict(color="#00FF00", width=2)))

            fig.update_layout(title="Equity Curve", xaxis_title="Date", yaxis_title="Equity ($)", template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")

            return jsonify({"chart": json.dumps(fig, cls=PlotlyJSONEncoder)})

        @self.app.route("/api/charts/performance")
        def performance_charts():
            returns = self.performance_metrics["daily_returns"]

            fig = go.Figure()
            fig.add_trace(go.Bar(x=[r["date"] for r in returns], y=[r["return"] for r in returns], marker_color=["#00FF00" if r["return"] > 0 else "#FF0000" for r in returns]))

            fig.update_layout(title="Daily Returns", xaxis_title="Date", yaxis_title="Return (%)", template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")

            return jsonify({"chart": json.dumps(fig, cls=PlotlyJSONEncoder)})

        @self.app.route("/api/settings", methods=["GET", "POST"])
        def settings():
            if request.method == "POST":
                data = request.json
                self.broker_gateway.default_broker = BrokerType(data.get("default_broker", "paper"))
                return jsonify({"success": True})

            return jsonify({"default_broker": self.broker_gateway.default_broker.value, "available_brokers": [b.value for b in BrokerType]})

    def _setup_websocket(self):
        @self.socketio.on("connect")
        def handle_connect():
            logger.info("Client connected to trading terminal")
            emit("status", {"status": "connected", "timestamp": datetime.now().isoformat()})

        @self.socketio.on("subscribe_market_data")
        async def handle_subscribe(data):
            symbol = data.get("symbol", "BTCUSDT")
            while True:
                try:
                    market_data = await self.broker_gateway.get_best_broker(symbol).get_market_data(symbol)
                    emit("market_data", asdict(market_data))
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f"Market data streaming error: {e}")
                    break

        @self.socketio.on("execute_signal")
        async def handle_execute_signal(data):
            symbol = data.get("symbol", "BTCUSDT")
            signal_type = data.get("signal", "BUY")
            quantity = float(data.get("quantity", 0.01))

            side = OrderSide.BUY if signal_type in ["BUY", "STRONG_BUY"] else OrderSide.SELL
            order = OrderRequest(symbol=symbol, side=side, order_type=OrderType.MARKET, quantity=quantity)

            result = await self.broker_gateway.place_order(order)

            self.active_trades[result.order_id] = {"order_id": result.order_id, "symbol": symbol, "side": side.value, "quantity": quantity, "entry_price": result.price, "entry_time": datetime.now().isoformat(), "status": "open"}

            emit("order_executed", {"success": True, "order": asdict(result), "trade": self.active_trades[result.order_id]})

        @self.socketio.on("close_position")
        async def handle_close_position(data):
            order_id = data.get("order_id")
            if order_id in self.active_trades:
                trade = self.active_trades[order_id]
                current_price = (await self.broker_gateway.get_best_broker(trade["symbol"]).get_market_data(trade["symbol"])).price

                pnl = (current_price - trade["entry_price"]) * float(trade["quantity"])
                if trade["side"] == "sell":
                    pnl = -pnl

                self.trade_history.append({**trade, "exit_price": current_price, "exit_time": datetime.now().isoformat(), "pnl": pnl, "pnl_pct": (pnl / (trade["entry_price"] * float(trade["quantity"]))) * 100})

                del self.active_trades[order_id]
                self._update_metrics()

                emit("position_closed", {"success": True, "trade": self.trade_history[-1]})

    def _serialize_account(self, account: Account) -> Dict:
        return {
            "broker": account.broker.value,
            "balance": {"cash": account.balance.cash, "buying_power": account.balance.buying_power, "portfolio_value": account.balance.portfolio_value},
            "positions": {symbol: {"symbol": pos.symbol, "quantity": pos.quantity, "avg_price": pos.avg_price, "side": pos.side.value, "market_value": pos.market_value, "unrealized_pnl": pos.unrealized_pnl} for symbol, pos in account.positions.items()},
            "orders": {oid: asdict(order) for oid, order in account.orders.items()},
        }

    async def _fetch_candles(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        """Fetch candlestick data from the broker gateway."""
        try:
            broker = self.broker_gateway.get_best_broker(symbol)
            market_data = await broker.get_market_data(symbol)
            # If broker provides historical data, use it; otherwise return empty DataFrame
            if hasattr(broker, 'get_historical_data'):
                return await broker.get_historical_data(symbol, timeframe, limit)
            # Fallback: return minimal DataFrame with latest market data
            logger.warning(f"Historical data not available for {symbol}, returning empty candles")
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
        except Exception as e:
            logger.error(f"Error fetching candles for {symbol}: {e}")
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

    def _update_metrics(self):
        if not self.trade_history:
            return

        pnls = [t["pnl"] for t in self.trade_history]
        self.performance_metrics["total_pnl"] = sum(pnls)
        self.performance_metrics["total_trades"] = len(self.trade_history)
        self.performance_metrics["winning_trades"] = len([p for p in pnls if p > 0])
        self.performance_metrics["losing_trades"] = len([p for p in pnls if p < 0])

        if self.performance_metrics["total_trades"] > 0:
            self.performance_metrics["win_rate"] = (self.performance_metrics["winning_trades"] / self.performance_metrics["total_trades"]) * 100

        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]

        if wins:
            self.performance_metrics["avg_win"] = sum(wins) / len(wins)
        if losses:
            self.performance_metrics["avg_loss"] = sum(losses) / len(losses)

        if self.performance_metrics["avg_loss"] != 0:
            self.performance_metrics["profit_factor"] = (sum(wins) / abs(sum(losses))) if losses else float("inf")

        equity = 1000000
        equity_curve = [{"timestamp": datetime.now().isoformat(), "equity": equity}]

        for trade in self.trade_history:
            equity += trade["pnl"]
            equity_curve.append({"timestamp": trade["exit_time"], "equity": equity})

        self.performance_metrics["equity_curve"] = equity_curve

        returns = [0]
        for i in range(1, len(equity_curve)):
            daily_return = ((equity_curve[i]["equity"] - equity_curve[i - 1]["equity"]) / equity_curve[i - 1]["equity"]) * 100
            returns.append(daily_return)

        self.performance_metrics["daily_returns"] = [{"date": equity_curve[i]["timestamp"], "return": returns[i]} for i in range(len(equity_curve))]

        if len(returns) > 1:
            returns_array = np.array(returns[1:])
            self.performance_metrics["sharpe_ratio"] = (np.mean(returns_array) / np.std(returns_array)) * np.sqrt(252) if np.std(returns_array) > 0 else 0

        equity_series = pd.Series([e["equity"] for e in equity_curve])
        rolling_max = equity_series.expanding().max()
        drawdown = (equity_series - rolling_max) / rolling_max * 100
        self.performance_metrics["max_drawdown"] = abs(min(drawdown))


def create_trading_terminal() -> tuple[Flask, SocketIO, TradingTerminal]:
    """
    Create and configure the Virtual Trading Terminal

    Returns:
        Flask app, SocketIO instance, and TradingTerminal
    """
    app = Flask(__name__, template_folder="../../templates", static_folder="../../static")
    app.config["SECRET_KEY"] = os.environ.get("TRADING_TERMINAL_SECRET_KEY", os.urandom(24).hex())
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

    terminal = TradingTerminal(app, socketio)

    return app, socketio, terminal
