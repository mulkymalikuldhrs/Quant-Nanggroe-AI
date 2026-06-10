"""
Streamlit Web Dashboard for AI Hedge Fund v2.2
===============================================

Features:
- Real-time portfolio overview
- Position management
- Trade history with analytics
- Signal feed and performance charts
- Configuration panel
- Trading controls (Manual/Semi-Auto/Full-Auto)
- MetaTrader connection status

Usage:
    streamlit run src/dashboard/streamlit_app.py
    or
    python3 -m streamlit run src/dashboard/streamlit_app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.memory.enhanced_memory_system import get_memory_system, AssetType, TradeStatus
from src.trading_plan.trading_plan import get_trading_plan_manager, TradingMode
from src.execution.metatrader_bridge import get_metatrader_bridge


st.set_page_config(
    page_title="AI Hedge Fund v2.2",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 15px;
        margin: 5px;
    }
    .stMetric {
        background-color: #f0f2f6;
        border-radius: 5px;
        padding: 10px;
    }
    .positive {
        color: #00C853;
    }
    .negative {
        color: #FF1744;
    }
    .sidebar-section {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
    }
</style>
""",
    unsafe_allow_html=True,
)


class DashboardState:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not DashboardState._initialized:
            self.memory = get_memory_system()
            self.trading_plan = get_trading_plan_manager()
            self.mt_bridge = None
            self.auto_refresh = False
            self.refresh_interval = 5
            DashboardState._initialized = True

    def get_portfolio_summary(self) -> Dict[str, float]:
        """Get portfolio summary metrics"""
        try:
            status = self.memory.get_system_status()
            portfolio = status.get("portfolio", {})
            return {
                "balance": portfolio.get("balance", 10000.0),
                "equity": portfolio.get("equity", 10000.0),
                "floating_pnl": portfolio.get("floating_pnl", 0.0),
                "floating_pnl_pct": portfolio.get("floating_pnl_pct", 0.0),
                "margin_used": portfolio.get("margin_used", 0.0),
                "free_margin": portfolio.get("free_margin", 10000.0),
                "open_positions": portfolio.get("open_positions", 0),
                "pending_orders": portfolio.get("pending_orders", 0),
            }
        except Exception as e:
            st.error(f"Error getting portfolio: {e}")
            return {
                "balance": 10000.0,
                "equity": 10000.0,
                "floating_pnl": 0.0,
                "floating_pnl_pct": 0.0,
                "margin_used": 0.0,
                "free_margin": 10000.0,
                "open_positions": 0,
                "pending_orders": 0,
            }

    def get_positions(self) -> List[Dict]:
        """Get current positions"""
        try:
            status = self.memory.get_system_status()
            return status.get("open_positions", [])
        except Exception:
            return []

    def get_recent_trades(self, limit: int = 20) -> List[Dict]:
        """Get recent trades"""
        try:
            history = self.memory.get_trade_history(days=30)
            return history[-limit:] if len(history) > limit else history
        except Exception:
            return []

    def get_performance_metrics(self) -> Dict[str, float]:
        """Get performance metrics"""
        try:
            metrics = self.memory.get_performance_metrics()
            return {
                "sharpe_ratio": metrics.get("sharpe_ratio", 0.0),
                "sortino_ratio": metrics.get("sortino_ratio", 0.0),
                "max_drawdown": metrics.get("max_drawdown", 0.0),
                "profit_factor": metrics.get("profit_factor", 0.0),
                "win_rate": metrics.get("win_rate", 0.0),
                "total_trades": metrics.get("total_trades", 0),
                "winning_trades": metrics.get("winning_trades", 0),
                "losing_trades": metrics.get("losing_trades", 0),
                "total_pnl": metrics.get("total_pnl", 0.0),
                "avg_win": metrics.get("avg_win", 0.0),
                "avg_loss": metrics.get("avg_loss", 0.0),
            }
        except Exception:
            return {
                "sharpe_ratio": 0.0,
                "sortino_ratio": 0.0,
                "max_drawdown": 0.0,
                "profit_factor": 0.0,
                "win_rate": 0.0,
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "total_pnl": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
            }

    def get_daily_pnl_history(self, days: int = 30) -> List[Dict]:
        """Get daily P&L history"""
        try:
            trades = self.memory.get_trade_history(days=days)
            daily_pnl = {}
            for trade in trades:
                if trade.get("status") == "closed":
                    date = trade.get("exit_time", "")[:10]
                    if date:
                        daily_pnl[date] = daily_pnl.get(date, 0.0) + trade.get("pnl", 0.0)
            return [{"date": k, "pnl": v} for k, v in sorted(daily_pnl.items())]
        except Exception:
            return []


def get_dashboard_state() -> DashboardState:
    """Get dashboard state singleton"""
    if not hasattr(st.session_state, "dashboard_state"):
        st.session_state.dashboard_state = DashboardState()
    return st.session_state.dashboard_state


def render_header():
    """Render dashboard header"""
    st.markdown('<div class="main-header">🤖 AI HEDGE FUND v2.2</div>', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        st.markdown(f"**Mode:** {st.session_state.get('trading_mode', 'manual').upper()}")
    with col2:
        st.markdown(f"**Time:** {datetime.now().strftime('%H:%M:%S')}")
    with col3:
        mt_status = "🟢 Connected" if st.session_state.get("mt_connected", False) else "🔴 Disconnected"
        st.markdown(f"**MT:** {mt_status}")
    with col4:
        auto_status = "🔄 Auto-refresh" if st.session_state.get("auto_refresh", False) else "⏸️ Manual"
        st.markdown(f"**Status:** {auto_status}")


def render_portfolio_metrics(state: DashboardState):
    """Render portfolio summary metrics"""
    portfolio = state.get_portfolio_summary()

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            "Balance",
            f"${portfolio['balance']:,.2f}",
            delta=f"${portfolio['equity'] - portfolio['balance']:,.2f}" if portfolio["equity"] != portfolio["balance"] else None,
        )

    with col2:
        pnl_delta = portfolio["floating_pnl"]
        pnl_class = "positive" if pnl_delta >= 0 else "negative"
        st.metric(
            "Equity",
            f"${portfolio['equity']:,.2f}",
            delta=f"{pnl_delta:,.2f} ({portfolio['floating_pnl_pct']:.2f}%)",
            delta_color="normal" if pnl_delta >= 0 else "inverse",
        )

    with col3:
        st.metric(
            "Floating P&L",
            f"${pnl_delta:,.2f}",
            delta_color="normal" if pnl_delta >= 0 else "inverse",
        )

    with col4:
        st.metric("Open Positions", portfolio["open_positions"])

    with col5:
        st.metric("Free Margin", f"${portfolio['free_margin']:,.2f}")


def render_positions(state: DashboardState):
    """Render current positions"""
    st.subheader("📊 Current Positions")

    positions = state.get_positions()

    if not positions:
        st.info("No open positions")
        return

    positions_df = pd.DataFrame(positions)

    if not positions_df.empty:
        display_cols = [
            "symbol",
            "direction",
            "entry_price",
            "current_price",
            "position_size",
            "pnl",
            "pnl_pct",
        ]
        available_cols = [c for c in display_cols if c in positions_df.columns]

        if available_cols:
            st.dataframe(
                positions_df[available_cols].style.format(
                    {
                        "entry_price": "${:,.5f}",
                        "current_price": "${:,.5f}",
                        "position_size": "{:,.2f}",
                        "pnl": "${:,.2f}",
                        "pnl_pct": "{:.2f}%",
                    }
                ),
                use_container_width=True,
            )

        for pos in positions:
            with st.expander(f"📍 {pos.get('symbol', 'Unknown')} - {pos.get('direction', '').upper()}"):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.write(f"**Entry:** ${pos.get('entry_price', 0):,.5f}")
                with col2:
                    st.write(f"**Current:** ${pos.get('current_price', 0):,.5f}")
                with col3:
                    st.write(f"**Size:** {pos.get('position_size', 0):,.2f}")
                with col4:
                    pnl = pos.get("pnl", 0)
                    st.write(f"**P&L:** ${pnl:,.2f}")
                if pos.get("stop_loss"):
                    st.write(f"**Stop Loss:** ${pos.get('stop_loss'):,.5f}")
                if pos.get("take_profit"):
                    tp_str = ", ".join([f"${tp:,.5f}" for tp in pos.get("take_profit", [])])
                    st.write(f"**Take Profit:** {tp_str}")


def render_trade_history(state: DashboardState):
    """Render trade history"""
    st.subheader("📜 Trade History")

    trades = state.get_recent_trades(limit=50)

    if not trades:
        st.info("No trades yet")
        return

    trades_df = pd.DataFrame(trades)

    if not trades_df.empty:
        display_cols = [
            "symbol",
            "direction",
            "entry_time",
            "exit_time",
            "entry_price",
            "exit_price",
            "pnl",
            "pnl_pct",
        ]
        available_cols = [c for c in display_cols if c in trades_df.columns]

        if available_cols:
            st.dataframe(
                trades_df[available_cols].style.format(
                    {
                        "entry_price": "${:,.5f}",
                        "exit_price": "${:,.5f}",
                        "pnl": "${:,.2f}",
                        "pnl_pct": "{:.2f}%",
                    }
                ),
                use_container_width=True,
                height=300,
            )


def render_performance_metrics(state: DashboardState):
    """Render performance metrics charts"""
    st.subheader("📈 Performance Metrics")

    metrics = state.get_performance_metrics()
    daily_pnl = state.get_daily_pnl_history(days=30)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Sharpe Ratio", f"{metrics['sharpe_ratio']:.3f}")
    with col2:
        st.metric("Sortino Ratio", f"{metrics['sortino_ratio']:.3f}")
    with col3:
        st.metric("Max Drawdown", f"{metrics['max_drawdown']:.2f}%")
    with col4:
        st.metric("Profit Factor", f"{metrics['profit_factor']:.2f}")

    col5, col6, col7, col8 = st.columns(4)

    with col5:
        st.metric("Win Rate", f"{metrics['win_rate']:.1f}%")
    with col6:
        st.metric("Total Trades", metrics["total_trades"])
    with col7:
        st.metric("Total P&L", f"${metrics['total_pnl']:,.2f}")
    with col8:
        rr = metrics["avg_win"] / abs(metrics["avg_loss"]) if metrics["avg_loss"] != 0 else 0
        st.metric("Avg Win/Loss", f"{rr:.2f}")

    if daily_pnl:
        pnl_df = pd.DataFrame(daily_pnl)

        fig = make_subplots(
            rows=2,
            cols=2,
            subplot_titles=(
                "Daily P&L",
                "P&L Distribution",
                "Cumulative P&L",
                "Win/Loss by Symbol",
            ),
            specs=[
                [{"type": "bar"}, {"type": "histogram"}],
                [{"type": "line"}, {"type": "pie"}],
            ],
        )

        fig.add_trace(
            go.Bar(
                x=pnl_df["date"],
                y=pnl_df["pnl"],
                marker_color=pnl_df["pnl"].apply(lambda x: "#00C853" if x >= 0 else "#FF1744"),
            ),
            row=1,
            col=1,
        )

        fig.add_trace(
            go.Histogram(x=pnl_df["pnl"], nbinsx=20, marker_color="#1E88E5"),
            row=1,
            col=2,
        )

        pnl_df["cumulative"] = pnl_df["pnl"].cumsum()
        fig.add_trace(
            go.Scatter(
                x=pnl_df["date"],
                y=pnl_df["cumulative"],
                mode="lines+markers",
                line=dict(color="#1E88E5", width=2),
            ),
            row=2,
            col=1,
        )

        trades = state.get_recent_trades(limit=100)
        if trades:
            win_trades = sum(1 for t in trades if t.get("pnl", 0) > 0)
            loss_trades = sum(1 for t in trades if t.get("pnl", 0) <= 0)
            fig.add_trace(
                go.Pie(
                    labels=["Wins", "Losses"],
                    values=[win_trades, loss_trades],
                    hole=0.4,
                ),
                row=2,
                col=2,
            )

        fig.update_layout(height=600, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)


def render_trading_controls(state: DashboardState):
    """Render trading controls"""
    st.subheader("🎮 Trading Controls")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### Trading Mode")
        mode = st.selectbox(
            "Select Mode",
            ["manual", "semi-auto", "full-auto"],
            index=["manual", "semi-auto", "full-auto"].index(st.session_state.get("trading_mode", "manual")),
        )
        st.session_state["trading_mode"] = mode

    with col2:
        st.markdown("### MetaTrader Connection")
        if st.button("🔄 Refresh Connection"):
            try:
                state.mt_bridge = get_metatrader_bridge(simulate=True)
                st.session_state["mt_connected"] = True
                st.success("Connected to MetaTrader (Simulator)")
            except Exception as e:
                st.error(f"Connection failed: {e}")

    with col3:
        st.markdown("### Auto Refresh")
        auto_refresh = st.checkbox("Enable Auto Refresh", value=st.session_state.get("auto_refresh", False))
        st.session_state["auto_refresh"] = auto_refresh
        if auto_refresh:
            interval = st.slider(
                "Refresh Interval (seconds)",
                5,
                60,
                st.session_state.get("refresh_interval", 5),
            )
            st.session_state["refresh_interval"] = interval


def render_symbol_analyzer():
    """Render symbol analyzer"""
    st.subheader("🔍 Symbol Analyzer")

    col1, col2 = st.columns([2, 1])

    with col1:
        symbol = st.text_input("Enter Symbol", value="EURUSD", help="e.g., AAPL, BTC/USD, EURUSD")

    with col2:
        timeframe = st.selectbox("Timeframe", ["H1", "M15", "M5", "D1", "W1"], index=0)

    if st.button("📊 Analyze"):
        st.info(f"Analyzing {symbol} on {timeframe}... (Analysis feature coming soon)")


def render_configuration(state: DashboardState):
    """Render configuration panel"""
    st.subheader("⚙️ Configuration")

    with st.expander("Trading Plan Settings"):
        plan = state.trading_plan.plan

        col1, col2 = st.columns(2)

        with col1:
            st.write("**Risk Parameters**")
            st.write(f"Max Risk per Trade: {plan.max_risk_per_trade * 100}%")
            st.write(f"Max Daily Loss: {plan.max_daily_loss * 100}%")
            st.write(f"Max Drawdown Limit: {plan.max_drawdown_limit * 100}%")
            st.write(f"Min Risk-Reward Ratio: 1:{plan.min_risk_reward_ratio}")

        with col2:
            st.write("**Position Sizing**")
            st.write(f"Kelly Fraction: {plan.kelly_fraction * 100}%")
            st.write(f"Max Position Size: {plan.max_position_size * 100}%")
            st.write(f"Consecutive Loss Limit: {plan.consecutive_loss_limit}")

    with st.expander("Account Settings"):
        st.text_input("Account ID", value="DEMO-123456", type="password")
        st.text_input("Broker URL", value="https://trade.mql5.com")
        st.selectbox("Account Type", ["Demo", "Real"])
        st.checkbox("Auto-connect on startup")

    with st.expander("Notification Settings"):
        st.checkbox("Telegram Notifications")
        st.checkbox("Email Notifications")
        st.checkbox("Sound Alerts")


def render_sidebar(state: DashboardState):
    """Render sidebar"""
    with st.sidebar:
        st.markdown("### 🤖 AI Hedge Fund v2.2")

        st.markdown("---")

        st.markdown("**Quick Actions**")
        if st.button("📊 New Analysis"):
            st.session_state["page"] = "analyze"
        if st.button("📝 New Trade"):
            st.session_state["page"] = "trade"
        if st.button("📈 View Portfolio"):
            st.session_state["page"] = "portfolio"
        if st.button("📜 Trade History"):
            st.session_state["page"] = "history"

        st.markdown("---")

        st.markdown("**System Status**")
        portfolio = state.get_portfolio_summary()
        status_color = "🟢" if portfolio["floating_pnl"] >= 0 else "🔴"
        st.markdown(f"{status_color} Trading Status: Active")

        st.markdown(f"📊 Balance: ${portfolio['balance']:,.2f}")
        st.markdown(f"📈 Equity: ${portfolio['equity']:,.2f}")
        st.markdown(f"📍 Positions: {portfolio['open_positions']}")

        st.markdown("---")

        st.markdown("**Latest Signals**")
        try:
            signals = state.memory.get_signal_history(limit=5)
            for signal in signals:
                symbol = signal.get("symbol", "Unknown")
                signal_type = signal.get("signal", "HOLD")
                confidence = signal.get("confidence", 0) * 100
                emoji = "🟢" if signal_type in ["BUY", "STRONG_BUY"] else "🔴" if signal_type in ["SELL", "STRONG_SELL"] else "🟡"
                st.markdown(f"{emoji} {symbol}: {signal_type} ({confidence:.0f}%)")
        except Exception:
            st.markdown("No signals available")

        st.markdown("---")

        st.markdown("**Help**")
        st.markdown("- **Manual**: You confirm all trades")
        st.markdown("- **Semi-Auto**: Auto sizing, you confirm")
        st.markdown("- **Full-Auto**: Autonomous trading")


def main():
    """Main dashboard function"""
    state = get_dashboard_state()

    render_header()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Portfolio", "📈 Analysis", "📜 History", "⚙️ Settings", "📝 Trade"])

    with tab1:
        render_portfolio_metrics(state)
        st.markdown("---")
        render_positions(state)

    with tab2:
        render_symbol_analyzer()
        st.markdown("---")
        render_performance_metrics(state)

    with tab3:
        render_trade_history(state)

    with tab4:
        render_trading_controls(state)
        render_configuration(state)

    with tab5:
        st.subheader("Manual Trade Entry")

        col1, col2, col3 = st.columns(3)

        with col1:
            symbol = st.text_input("Symbol", value="EURUSD")
            direction = st.selectbox("Direction", ["BUY", "SELL"])

        with col2:
            lot_size = st.number_input("Lot Size", min_value=0.01, max_value=100.0, value=0.1)
            st.write(f"Position Size: {lot_size} lots")

        with col3:
            st.write("**Quick Options**")
            if st.button("Set Stop Loss to 1:2 RR"):
                st.info("Calculating SL based on 1:2 risk-reward ratio...")
            if st.button("Set Take Profit Levels"):
                st.info("Setting TP at 1R and 2R...")

        if st.button("Execute Trade"):
            st.success(f"Trade would be executed: {direction} {lot_size} lots of {symbol}")


if __name__ == "__main__":
    main()
