"""initial_schema — all 7 tables

Revision ID: 001_initial
Revises: None
Create Date: 2025-06-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Users Table ──────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), unique=True, nullable=False, index=True),
        sa.Column("username", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=True),
        sa.Column("is_active", sa.Boolean, default=True, nullable=False),
        sa.Column("is_admin", sa.Boolean, default=False, nullable=False),
        sa.Column("preferences", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── Strategies Table ─────────────────────────────────────────────
    op.create_table(
        "strategies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("strategy_type", sa.String(50), nullable=False, comment="e.g., momentum, mean_revert, breakout, pressure"),
        sa.Column("status", sa.String(20), nullable=False, default="ACTIVE", comment="ACTIVE / HIBERNATING / KILLED"),
        sa.Column("parameters", JSONB, nullable=True),
        sa.Column("total_trades", sa.Integer, default=0, nullable=False),
        sa.Column("win_rate", sa.Float, default=0.0, nullable=False),
        sa.Column("sharpe_ratio", sa.Float, default=0.0, nullable=False),
        sa.Column("max_drawdown", sa.Float, default=0.0, nullable=False),
        sa.Column("expectancy", sa.Float, default=0.0, nullable=False),
        sa.Column("total_pnl", sa.Float, default=0.0, nullable=False),
        sa.Column("death_threshold", sa.Integer, default=20, nullable=False),
        sa.Column("consecutive_losses", sa.Integer, default=0, nullable=False),
        sa.Column("symbols", JSONB, nullable=True, comment="List of symbols this strategy trades"),
        sa.Column("timeframe", sa.String(10), default="1d", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("killed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_strategies_user_status", "strategies", ["user_id", "status"])
    op.create_index("ix_strategies_type_status", "strategies", ["strategy_type", "status"])

    # ── Trades Table ─────────────────────────────────────────────────
    op.create_table(
        "trades",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("strategy_id", UUID(as_uuid=True), sa.ForeignKey("strategies.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("order_id", sa.String(100), nullable=True, index=True),
        sa.Column("symbol", sa.String(30), nullable=False, index=True),
        sa.Column("direction", sa.String(10), nullable=False, comment="BUY / SELL / LONG / SHORT"),
        sa.Column("entry_price", sa.Float, nullable=False),
        sa.Column("exit_price", sa.Float, nullable=True),
        sa.Column("quantity", sa.Float, nullable=False),
        sa.Column("stop_loss", sa.Float, nullable=True),
        sa.Column("take_profit", JSONB, nullable=True, comment="List of TP levels"),
        sa.Column("order_type", sa.String(20), default="MARKET", comment="MARKET / LIMIT / STOP"),
        sa.Column("execution_status", sa.String(20), default="PENDING", comment="PENDING / FILLED / PARTIAL / CANCELLED / REJECTED"),
        sa.Column("slippage", sa.Float, default=0.0, nullable=False),
        sa.Column("fees", sa.Float, default=0.0, nullable=False),
        sa.Column("realized_pnl", sa.Float, nullable=True),
        sa.Column("pnl_pct", sa.Float, nullable=True),
        sa.Column("risk_verdict", sa.String(20), nullable=True),
        sa.Column("risk_checkpoints", JSONB, nullable=True),
        sa.Column("agent_trace", JSONB, nullable=True),
        sa.Column("decision_action", sa.String(30), nullable=True),
        sa.Column("decision_reason", sa.Text, nullable=True),
        sa.Column("market_regime", sa.String(30), nullable=True),
        sa.Column("volatility_level", sa.String(20), nullable=True),
        sa.Column("sentiment_score", sa.Float, nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_trades_user_symbol", "trades", ["user_id", "symbol"])
    op.create_index("ix_trades_status", "trades", ["execution_status"])
    op.create_index("ix_trades_opened_at", "trades", ["opened_at"])
    op.create_index("ix_trades_symbol_direction", "trades", ["symbol", "direction"])

    # ── Positions Table ──────────────────────────────────────────────
    op.create_table(
        "positions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("trade_id", UUID(as_uuid=True), sa.ForeignKey("trades.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("symbol", sa.String(30), nullable=False, index=True),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("quantity", sa.Float, nullable=False),
        sa.Column("avg_entry_price", sa.Float, nullable=False),
        sa.Column("current_price", sa.Float, default=0.0, nullable=False),
        sa.Column("unrealized_pnl", sa.Float, default=0.0, nullable=False),
        sa.Column("unrealized_pnl_pct", sa.Float, default=0.0, nullable=False),
        sa.Column("stop_loss", sa.Float, nullable=True),
        sa.Column("take_profit", sa.Float, nullable=True),
        sa.Column("risk_reward_ratio", sa.Float, nullable=True),
        sa.Column("strategy_id", UUID(as_uuid=True), sa.ForeignKey("strategies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_positions_user_symbol", "positions", ["user_id", "symbol"])
    op.create_unique_constraint("uq_position_user_symbol_dir", "positions", ["user_id", "symbol", "direction"])

    # ── Portfolio Snapshots Table ─────────────────────────────────────
    op.create_table(
        "portfolio_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("total_equity", sa.Float, nullable=False),
        sa.Column("cash_balance", sa.Float, nullable=False),
        sa.Column("unrealized_pnl", sa.Float, default=0.0, nullable=False),
        sa.Column("realized_pnl", sa.Float, default=0.0, nullable=False),
        sa.Column("daily_pnl", sa.Float, default=0.0, nullable=False),
        sa.Column("daily_pnl_pct", sa.Float, default=0.0, nullable=False),
        sa.Column("gross_exposure", sa.Float, default=0.0, nullable=False),
        sa.Column("net_exposure", sa.Float, default=0.0, nullable=False),
        sa.Column("num_positions", sa.Integer, default=0, nullable=False),
        sa.Column("current_drawdown", sa.Float, default=0.0, nullable=False),
        sa.Column("var_95", sa.Float, nullable=True, comment="Value at Risk 95%"),
        sa.Column("cvar_95", sa.Float, nullable=True, comment="Conditional VaR 95%"),
        sa.Column("positions_breakdown", JSONB, nullable=True),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), nullable=False, index=True, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_snapshots_user_time", "portfolio_snapshots", ["user_id", "snapshot_at"])

    # ── Risk Events Table ────────────────────────────────────────────
    op.create_table(
        "risk_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("trade_id", UUID(as_uuid=True), sa.ForeignKey("trades.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(50), nullable=False, index=True, comment="VETO / WARNING / LIMIT_BREACH / KILL_SWITCH"),
        sa.Column("severity", sa.String(20), nullable=False, default="INFO", comment="INFO / WARNING / CRITICAL / EMERGENCY"),
        sa.Column("symbol", sa.String(30), nullable=True),
        sa.Column("direction", sa.String(10), nullable=True),
        sa.Column("verdict", sa.String(20), nullable=False, comment="APPROVED / VETOED"),
        sa.Column("risk_pct", sa.Float, nullable=True),
        sa.Column("checkpoints", JSONB, nullable=True),
        sa.Column("message", sa.Text, nullable=True),
        sa.Column("market_regime", sa.String(30), nullable=True),
        sa.Column("daily_pnl_pct", sa.Float, nullable=True),
        sa.Column("weekly_pnl_pct", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, index=True, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_risk_events_type_severity", "risk_events", ["event_type", "severity"])
    op.create_index("ix_risk_events_created", "risk_events", ["created_at"])

    # ── Agent Logs Table ─────────────────────────────────────────────
    op.create_table(
        "agent_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("trade_id", UUID(as_uuid=True), sa.ForeignKey("trades.id", ondelete="SET NULL"), nullable=True),
        sa.Column("agent_name", sa.String(50), nullable=False, index=True, comment="researcher / analyst / strategist / risk_manager / trader / portfolio_manager"),
        sa.Column("graph_run_id", sa.String(100), nullable=True, index=True, comment="Groups logs from the same graph execution"),
        sa.Column("status", sa.String(20), nullable=False, default="completed", comment="completed / failed / skipped / timeout"),
        sa.Column("latency_ms", sa.Float, nullable=True),
        sa.Column("llm_model", sa.String(100), nullable=True),
        sa.Column("llm_provider", sa.String(50), nullable=True),
        sa.Column("prompt_tokens", sa.Integer, nullable=True),
        sa.Column("completion_tokens", sa.Integer, nullable=True),
        sa.Column("total_tokens", sa.Integer, nullable=True),
        sa.Column("input_data", JSONB, nullable=True),
        sa.Column("output_data", JSONB, nullable=True),
        sa.Column("symbol", sa.String(30), nullable=True, index=True),
        sa.Column("timeframe", sa.String(10), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("error_traceback", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, index=True, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_agent_logs_name_status", "agent_logs", ["agent_name", "status"])
    op.create_index("ix_agent_logs_graph_run", "agent_logs", ["graph_run_id"])
    op.create_index("ix_agent_logs_created", "agent_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("agent_logs")
    op.drop_table("risk_events")
    op.drop_table("portfolio_snapshots")
    op.drop_table("positions")
    op.drop_table("trades")
    op.drop_table("strategies")
    op.drop_table("users")
