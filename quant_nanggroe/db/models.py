"""Database models — imports legacy ORM + adds QNA-specific models."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Text, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

logger = logging.getLogger(__name__)

# Re-export everything from legacy models
import sys
from pathlib import Path
from quant_nanggroe.database.models import (
    Agent, Task, Memory, Workflow, WorkflowExecution, WorkflowStep,
    Deployment, SystemMetric, KnowledgeEntry, UserSession, APILog,
    Base, engine, SessionLocal, get_db_session as _legacy_get_db,
    create_tables as _legacy_create_tables,
)

create_tables = _legacy_create_tables
# ── QNA-specific models ──────────────────────────────────────────

class Trade(Base):
    __tablename__ = "qna_trades"
    id = Column(Integer, primary_key=True)
    trade_id = Column(String(100), unique=True, nullable=False)
    symbol = Column(String(50), nullable=False)
    direction = Column(String(10), nullable=False)
    quantity = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    pnl = Column(Float, default=0.0)
    fees = Column(Float, default=0.0)
    status = Column(String(20), default="open")
    strategy = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    opened_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    closed_at = Column(DateTime, nullable=True)

class BacktestResult(Base):
    __tablename__ = "qna_backtest_results"
    id = Column(Integer, primary_key=True)
    backtest_id = Column(String(100), unique=True, nullable=False)
    symbol = Column(String(50), nullable=False)
    strategy = Column(String(100), nullable=False)
    status = Column(String(20), default="QUEUED")
    total_return = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    win_rate = Column(Float, default=0.0)
    total_trades = Column(Integer, default=0)
    profit_factor = Column(Float, default=0.0)
    equity_curve = Column(JSON, default=list)
    params = Column(JSON, default=dict)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class PortfolioSnapshot(Base):
    __tablename__ = "qna_portfolio_snapshots"
    id = Column(Integer, primary_key=True)
    total_value = Column(Float, default=0.0)
    cash_balance = Column(Float, default=0.0)
    unrealized_pnl = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    position_count = Column(Integer, default=0)
    var_95 = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    snapshot_data = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class StrategyConfig(Base):
    __tablename__ = "qna_strategy_configs"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), unique=True, nullable=False)
    strategy_type = Column(String(100), nullable=False)
    params = Column(JSON, default=dict)
    tags = Column(JSON, default=list)
    enabled = Column(Integer, default=1)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

def init_db():
    """Create all tables (legacy + QNA)."""
    _legacy_create_tables()
    Base.metadata.create_all(bind=engine)
    logger.info("All tables created successfully")

def get_db_session():
    """Get a database session."""
    session = SessionLocal()
    try:
        return session
    finally:
        session.close()
