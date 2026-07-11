#!/usr/bin/env python3
"""
Hermes Quant OS - Shared State Manager
========================================
Single Source of Truth for all runtime state.
Solves: PnL desync, state lost on restart, redundant tool instances.

Architecture:
- All tools reference the SAME RiskOfficerTool instance
- SQLite persistence via existing trading_journal.sql schema
- Kill switch state persisted across restarts
"""

import json
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Union, List, TypedDict

logger = logging.getLogger("HermesQuantOS.SharedState")

# Default database path
DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "hermes_quant.db"


class SharedState:
    """
    Global shared state singleton for Hermes Quant OS.

    Guarantees:
    - One RiskOfficerTool instance (PnL never desyncs)
    - One KillSwitchTool instance (state persists across restarts)
    - SQLite persistence for all trades, risk checks, and events
    - Thread-safe access via Python GIL
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path: Optional[str] = None):
        if self._initialized:
            return

        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize shared tool instances
        self._risk_officer = None
        self._kill_switch = None
        self._journal = None

        # Initialize database
        self._init_db()

        # Restore persisted state
        self._restore_state()

        self._initialized = True
        logger.info(f"SharedState initialized: db={self.db_path}")

    def _init_db(self) -> None:
        """Initialize SQLite database with trading_journal.sql schema"""
        schema_path = Path(__file__).parent.parent / "schemas" / "trading_journal.sql"

        conn = sqlite3.connect(str(self.db_path))
        try:
            if schema_path.exists():
                with open(schema_path, 'r') as f:
                    conn.executescript(f.read())
                logger.info("Database schema initialized from trading_journal.sql")
            else:
                # Minimal schema if file missing
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS trades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        trade_id TEXT UNIQUE NOT NULL,
                        symbol TEXT NOT NULL,
                        direction TEXT NOT NULL,
                        entry_price REAL NOT NULL,
                        exit_price REAL,
                        stop_loss REAL NOT NULL,
                        take_profit REAL,
                        lot_size REAL NOT NULL,
                        pnl REAL,
                        pnl_pct REAL,
                        result TEXT,
                        entry_time TIMESTAMP NOT NULL,
                        exit_time TIMESTAMP,
                        reason TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE TABLE IF NOT EXISTS risk_checks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        direction TEXT NOT NULL,
                        verdict TEXT NOT NULL,
                        daily_pnl_at_check REAL,
                        weekly_pnl_at_check REAL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE TABLE IF NOT EXISTS kill_switch_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_type TEXT NOT NULL,
                        trigger_reason TEXT NOT NULL,
                        daily_pnl REAL,
                        weekly_pnl REAL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE TABLE IF NOT EXISTS system_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_type TEXT NOT NULL,
                        details TEXT,
                        severity TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE TABLE IF NOT EXISTS persisted_state (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE TABLE IF NOT EXISTS strategy_lifecycle (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        state TEXT NOT NULL,
                        trades_count INTEGER DEFAULT 0,
                        wins INTEGER DEFAULT 0,
                        losses INTEGER DEFAULT 0,
                        total_pnl REAL DEFAULT 0.0,
                        expectancy REAL DEFAULT 0.0,
                        max_drawdown REAL DEFAULT 0.0,
                        last_evaluated TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                logger.info("Database schema initialized (minimal fallback)")
        finally:
            conn.close()

    def _restore_state(self) -> None:
        """Restore persisted state from SQLite"""
        conn = sqlite3.connect(str(self.db_path))
        try:
            # Restore risk officer PnL
            row = conn.execute(
                "SELECT value FROM persisted_state WHERE key = 'risk_officer_state'"
            ).fetchone()
            if row:
                state = json.loads(row[0])
                ro = self.risk_officer
                ro.daily_pnl = state.get("daily_pnl", 0.0)
                ro.weekly_pnl = state.get("weekly_pnl", 0.0)
                ro.trade_count_today = state.get("trade_count_today", 0)
                ro.trade_count_week = state.get("trade_count_week", 0)
                ro.veto_count = state.get("veto_count", 0)
                ro.approval_count = state.get("approval_count", 0)
                last_reset = state.get("last_reset")
                if last_reset:
                    ro.last_reset = datetime.fromisoformat(last_reset).date()
                logger.info(f"Restored RiskOfficer state: daily_pnl={ro.daily_pnl:.4f}")

            # Restore kill switch state
            row = conn.execute(
                "SELECT value FROM persisted_state WHERE key = 'kill_switch_state'"
            ).fetchone()
            if row:
                state = json.loads(row[0])
                ks = self.kill_switch
                ks.is_active = state.get("is_active", False)
                ks.activated_at = state.get("activated_at")
                ks.activation_reason = state.get("activation_reason")
                ks.auto_triggers = state.get("auto_triggers", 0)
                ks.manual_triggers = state.get("manual_triggers", 0)
                if ks.is_active:
                    logger.warning(f"Kill switch was ACTIVE on last shutdown: {ks.activation_reason}")

            # Restore strategy lifecycle
            rows = conn.execute(
                "SELECT name, state, trades_count, wins, losses, total_pnl, expectancy, max_drawdown FROM strategy_lifecycle"
            ).fetchall()
            if rows:
                from tools.strategy_lifecycle import StrategyLifecycleManager
                slm = self._get_or_create("strategy_lifecycle", StrategyLifecycleManager)
                for row in rows:
                    name, state, tc, wins, losses, pnl, exp, dd = row
                    slm.strategies[name] = {
                        "name": name, "state": state,
                        "trades_count": tc, "wins": wins, "losses": losses,
                        "total_pnl": pnl, "expectancy": exp, "max_drawdown": dd,
                        "win_rate": wins / max(tc, 1),
                        "registered_at": datetime.now().isoformat(),
                        "last_evaluated": None,
                        "state_history": []
                    }
                logger.info(f"Restored {len(rows)} strategy lifecycle entries")

        finally:
            conn.close()

    def persist_risk_officer_state(self) -> None:
        """Persist RiskOfficer state to SQLite"""
        ro = self.risk_officer
        state = {
            "daily_pnl": ro.daily_pnl,
            "weekly_pnl": ro.weekly_pnl,
            "trade_count_today": ro.trade_count_today,
            "trade_count_week": ro.trade_count_week,
            "veto_count": ro.veto_count,
            "approval_count": ro.approval_count,
            "last_reset": ro.last_reset.isoformat() if ro.last_reset else None
        }
        self._persist_key("risk_officer_state", json.dumps(state))

    def persist_kill_switch_state(self) -> None:
        """Persist KillSwitch state to SQLite"""
        ks = self.kill_switch
        state = {
            "is_active": ks.is_active,
            "activated_at": ks.activated_at,
            "activation_reason": ks.activation_reason,
            "auto_triggers": ks.auto_triggers,
            "manual_triggers": ks.manual_triggers
        }
        self._persist_key("kill_switch_state", json.dumps(state))

    def persist_strategy(self, name: str, strategy_data: Dict[str, Union[str, int, float]]) -> None:
        """Persist a single strategy to SQLite"""
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("""
                INSERT OR REPLACE INTO strategy_lifecycle
                (name, state, trades_count, wins, losses, total_pnl, expectancy, max_drawdown, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name, strategy_data.get("state", "ACTIVE"),
                strategy_data.get("trades_count", 0),
                strategy_data.get("wins", 0), strategy_data.get("losses", 0),
                strategy_data.get("total_pnl", 0.0),
                strategy_data.get("expectancy", 0.0),
                strategy_data.get("max_drawdown", 0.0),
                datetime.now().isoformat()
            ))
            conn.commit()
        finally:
            conn.close()

    def log_trade(self, trade_data: Dict[str, Union[str, float, int, None]]) -> None:
        """Log a trade to SQLite"""
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("""
                INSERT INTO trades (trade_id, symbol, direction, entry_price, exit_price,
                    stop_loss, take_profit, lot_size, pnl, pnl_pct, result,
                    entry_time, exit_time, reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade_data.get("trade_id", f"T_{datetime.now().strftime('%Y%m%d%H%M%S')}"),
                trade_data.get("symbol", ""),
                trade_data.get("direction", ""),
                trade_data.get("entry", 0.0),
                trade_data.get("exit_price"),
                trade_data.get("stop_loss", 0.0),
                trade_data.get("take_profit"),
                trade_data.get("lot_size", 0.0),
                trade_data.get("pnl"),
                trade_data.get("pnl_pct"),
                trade_data.get("result", ""),
                trade_data.get("entry_time", datetime.now().isoformat()),
                trade_data.get("exit_time"),
                trade_data.get("reason", "")
            ))
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to log trade: {e}")
        finally:
            conn.close()

    def log_risk_check(self, symbol: str, direction: str, verdict: str,
                       daily_pnl: float, weekly_pnl: float) -> None:
        """Log a risk check to SQLite"""
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("""
                INSERT INTO risk_checks (symbol, direction, verdict, daily_pnl_at_check, weekly_pnl_at_check)
                VALUES (?, ?, ?, ?, ?)
            """, (symbol, direction, verdict, daily_pnl, weekly_pnl))
            conn.commit()
        finally:
            conn.close()

    def log_kill_switch_event(self, event_type: str, trigger_reason: str,
                              daily_pnl: float = 0.0, weekly_pnl: float = 0.0) -> None:
        """Log a kill switch event to SQLite"""
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("""
                INSERT INTO kill_switch_events (event_type, trigger_reason, daily_pnl, weekly_pnl)
                VALUES (?, ?, ?, ?)
            """, (event_type, trigger_reason, daily_pnl, weekly_pnl))
            conn.commit()
        finally:
            conn.close()

    def log_system_event(self, event_type: str, details: str, severity: str = "INFO") -> None:
        """Log a system event to SQLite"""
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("""
                INSERT INTO system_events (event_type, details, severity)
                VALUES (?, ?, ?)
            """, (event_type, details, severity))
            conn.commit()
        finally:
            conn.close()

    def _persist_key(self, key: str, value: str) -> None:
        """Generic key-value persistence"""
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("""
                INSERT OR REPLACE INTO persisted_state (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, value, datetime.now().isoformat()))
            conn.commit()
        finally:
            conn.close()

    # ── Shared Tool Instances ──────────────────────────────────────

    @property
    def risk_officer(self):
        """Get the SHARED RiskOfficerTool instance"""
        if self._risk_officer is None:
            from tools.risk_officer_tool import RiskOfficerTool
            self._risk_officer = RiskOfficerTool()
        return self._risk_officer

    @property
    def kill_switch(self):
        """Get the SHARED KillSwitchTool instance"""
        if self._kill_switch is None:
            from tools.kill_switch_tool import KillSwitchTool
            self._kill_switch = KillSwitchTool()
        return self._kill_switch

    @property
    def journal(self):
        """Get the SHARED JournalTool instance"""
        if self._journal is None:
            from tools.journal_tool import JournalTool
            self._journal = JournalTool()
        return self._journal

    @property
    def technical_analysis(self):
        """Get the SHARED TechnicalAnalysisTool instance"""
        if not hasattr(self, '_technical_analysis') or self._technical_analysis is None:
            from tools.technical_analysis_tool import TechnicalAnalysisTool
            self._technical_analysis = TechnicalAnalysisTool()
        return self._technical_analysis

    @property
    def market_state_engine(self):
        """Get the SHARED MarketStateEngine instance"""
        if not hasattr(self, '_market_state_engine') or self._market_state_engine is None:
            from tools.market_state_engine import MarketStateEngine
            self._market_state_engine = MarketStateEngine()
        return self._market_state_engine

    @property
    def market_data(self):
        """Get the SHARED MarketDataTool instance"""
        if not hasattr(self, '_market_data') or self._market_data is None:
            from tools.market_data_tool import MarketDataTool
            self._market_data = MarketDataTool()
        return self._market_data

    def _get_or_create(self, attr_name: str, cls: type) -> object:
        """Get or create a shared tool instance"""
        if not hasattr(self, f'_{attr_name}') or getattr(self, f'_{attr_name}') is None:
            setattr(self, f'_{attr_name}', cls())
        return getattr(self, f'_{attr_name}')


# Module-level convenience accessor
_shared_state = None


def get_shared_state(db_path: Optional[str] = None) -> SharedState:
    """Get the global SharedState instance"""
    global _shared_state
    if _shared_state is None:
        _shared_state = SharedState(db_path)
    return _shared_state
