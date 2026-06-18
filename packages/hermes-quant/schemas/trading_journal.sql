-- ============================================================================
-- HERMES QUANT OS - Trading Journal Database Schema
-- ============================================================================
-- 7 Tables for complete audit trail
-- ============================================================================

-- 1. Trades - Core trade records
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id TEXT UNIQUE NOT NULL,
    symbol TEXT NOT NULL,
    direction TEXT NOT NULL CHECK(direction IN ('BUY','SELL','LONG','SHORT')),
    entry_price REAL NOT NULL,
    exit_price REAL,
    stop_loss REAL NOT NULL,
    take_profit REAL,
    lot_size REAL NOT NULL,
    pnl REAL,
    pnl_pips REAL,
    pnl_pct REAL,
    rr_achieved REAL,
    result TEXT CHECK(result IN ('WIN','LOSS','BREAKEVEN','OPEN','CANCELLED')),
    entry_time TIMESTAMP NOT NULL,
    exit_time TIMESTAMP,
    duration_minutes INTEGER,
    risk_officer_verdict TEXT,
    confluence_score TEXT,
    strategy_scenario TEXT,
    reason TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Risk Checks - Every risk officer evaluation
CREATE TABLE IF NOT EXISTS risk_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    direction TEXT NOT NULL,
    lot_size REAL,
    entry_price REAL,
    stop_loss REAL,
    take_profit REAL,
    risk_pct REAL,
    rr_ratio REAL,
    verdict TEXT NOT NULL CHECK(verdict IN ('APPROVED','VETOED')),
    checkpoints_passed INTEGER,
    checkpoints_failed INTEGER,
    failed_checks TEXT,  -- JSON array of failed checkpoint names
    daily_pnl_at_check REAL,
    weekly_pnl_at_check REAL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Kill Switch Events
CREATE TABLE IF NOT EXISTS kill_switch_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL CHECK(event_type IN ('ACTIVATED','RESET')),
    trigger_reason TEXT NOT NULL,
    daily_pnl REAL,
    weekly_pnl REAL,
    manual_or_auto TEXT CHECK(manual_or_auto IN ('MANUAL','AUTO_DAILY','AUTO_WEEKLY')),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Market Analysis Snapshots
CREATE TABLE IF NOT EXISTS market_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    interval TEXT NOT NULL,
    current_price REAL,
    trend TEXT,
    smc_structure TEXT,  -- JSON
    indicators TEXT,     -- JSON
    technical_thesis TEXT, -- JSON
    confluence_score TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Strategy Scenarios
CREATE TABLE IF NOT EXISTS strategy_scenarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    bullish_entry REAL,
    bullish_sl REAL,
    bullish_tp REAL,
    bullish_rr TEXT,
    bearish_entry REAL,
    bearish_sl REAL,
    bearish_tp REAL,
    bearish_rr TEXT,
    neutral_range TEXT,
    preferred_scenario TEXT,
    confluence_bullish TEXT,
    confluence_bearish TEXT,
    confluence_neutral TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. System Events - Watchdog, crashes, restarts
CREATE TABLE IF NOT EXISTS system_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    details TEXT,  -- JSON
    severity TEXT CHECK(severity IN ('INFO','WARN','ERROR','CRITICAL')),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. Session Memory - Agent conversation and decision log
CREATE TABLE IF NOT EXISTS session_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT,
    provider TEXT,
    decision_framework TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
CREATE INDEX IF NOT EXISTS idx_trades_result ON trades(result);
CREATE INDEX IF NOT EXISTS idx_trades_entry_time ON trades(entry_time);
CREATE INDEX IF NOT EXISTS idx_risk_checks_verdict ON risk_checks(verdict);
CREATE INDEX IF NOT EXISTS idx_risk_checks_timestamp ON risk_checks(timestamp);
CREATE INDEX IF NOT EXISTS idx_kill_switch_timestamp ON kill_switch_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_market_analysis_symbol ON market_analysis(symbol);
CREATE INDEX IF NOT EXISTS idx_system_events_type ON system_events(event_type);
CREATE INDEX IF NOT EXISTS idx_session_memory_session ON session_memory(session_id);
