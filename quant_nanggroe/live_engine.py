#!/usr/bin/env python3
# NOTE: Use pipeline/ module for new code — see quant_nanggroe.pipeline.UnifiedPipeline
"""
QUANT NANGGROE — Autonomous Multi-Asset Hedge Fund Engine
==========================================================
Upgraded: multi-asset (BTC, ETH, SOL, BNB), 5 strategies, Kelly sizing,
trailing stops, take-profit, performance analytics, dashboard, auto-restart.

Usage:
  python3 live_engine.py [start|stop|restart|status|dashboard]
"""

import json
import logging
import os
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# GLOBAL FLAG: Route all strategy signal generation through the adaptive pipeline
# (loads ALL 73+ registered strategies via registry, not just 4 hardcoded).
QNA_USE_ADAPTIVE_PIPELINE = os.environ.get("QNA_USE_ADAPTIVE_PIPELINE", "1") == "1"

QNA_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = QNA_DIR / "data"
LOG_DIR = QNA_DIR / "logs"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

from quant_nanggroe.engine.live.adaptive_integration import create_live_pipeline
from quant_nanggroe.engine.risk.constants import (
    ASSET_ALLOCATIONS,
    CLEANUP_INTERVAL,
    DCC_UPDATE_INTERVAL,
    HEARTBEAT_INTERVAL,
    MAX_DRAWDOWN_PCT,
    MAX_POSITION_SIZE_PCT,
    MAX_POSITIONS_TOTAL,
    REBALANCE_THRESHOLD,
    REPORT_INTERVAL,
    TP_TARGETS,
    TRAILING_STOP_PCT,
)
from quant_nanggroe.engine.risk.kill_switch import KillSwitch, configure_kill_switch_file
from quant_nanggroe.engine_bridge import EnginePriceProvider, EngineRiskManager, StalePositionAnalyzer
from quant_nanggroe.engine_production_bridge import create_production_engine
from quant_nanggroe.notifier import format_error_message, format_heartbeat, send_telegram
from quant_nanggroe.data.providers.data_manager import DataManager
from quant_nanggroe.strategies.trend_follow import TrendFollow
from quant_nanggroe.strategies.tsmom import TSMOM

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] QNA %(message)s",
    handlers=[
        logging.FileHandler(str(LOG_DIR / "live-engine.log")),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("QNA-Live")

# Asset allocations sourced from constants.py (single source of truth).
ASSETS = [
    {"symbol": sym, "coin_gecko_id": cg_id, "allocation": alloc}
    for sym, cg_id, alloc in [
        ("BTCUSDT", "bitcoin", ASSET_ALLOCATIONS["BTCUSDT"]),
        ("ETHUSDT", "ethereum", ASSET_ALLOCATIONS["ETHUSDT"]),
        ("SOLUSDT", "solana", ASSET_ALLOCATIONS["SOLUSDT"]),
        ("BNBUSDT", "binancecoin", ASSET_ALLOCATIONS["BNBUSDT"]),
        ("AVAXUSDT", "avalanche-2", ASSET_ALLOCATIONS["AVAXUSDT"]),
        ("LINKUSDT", "chainlink", ASSET_ALLOCATIONS["LINKUSDT"]),
        ("XRPUSDT", "ripple", ASSET_ALLOCATIONS["XRPUSDT"]),
        ("ADAUSDT", "cardano", ASSET_ALLOCATIONS["ADAUSDT"]),
    ]
]
ASSET_CG_MAP = {a["symbol"]: a["coin_gecko_id"] for a in ASSETS}
ASSET_SYMBOLS = [a["symbol"] for a in ASSETS]
CG_IDS = ",".join(a["coin_gecko_id"] for a in ASSETS)

# TP targets sourced from constants.py.
TP_TARGETS = TP_TARGETS
TRAILING_STOP_PCT = TRAILING_STOP_PCT
REBALANCE_THRESHOLD = REBALANCE_THRESHOLD
MAX_DRAWDOWN = MAX_DRAWDOWN_PCT
MAX_POSITION_PCT = MAX_POSITION_SIZE_PCT
MAX_POSITIONS_TOTAL = MAX_POSITIONS_TOTAL
HEARTBEAT_INTERVAL = HEARTBEAT_INTERVAL
CLEANUP_INTERVAL = CLEANUP_INTERVAL
REPORT_INTERVAL = REPORT_INTERVAL
DCC_UPDATE_INTERVAL = DCC_UPDATE_INTERVAL

def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


# ─── Database ──────────────────────────────────────────────────────

def init_db():
    db = sqlite3.connect(str(DATA_DIR / "qna_live.db"))
    db.execute("""
        CREATE TABLE IF NOT EXISTS candles (
            symbol TEXT, timestamp INTEGER, open REAL, high REAL,
            low REAL, close REAL, volume REAL,
            PRIMARY KEY (symbol, timestamp)
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT, side TEXT DEFAULT 'long', entry_price REAL,
            quantity REAL, entry_time TEXT, highest_since_entry REAL,
            strategy TEXT, stop_loss REAL DEFAULT 0, take_profit REAL DEFAULT 0,
            partial_exit_price REAL DEFAULT 0, exited_qty REAL DEFAULT 0,
            status TEXT DEFAULT 'open'
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT, side TEXT, entry_price REAL, exit_price REAL,
            quantity REAL, entry_time TEXT, exit_time TEXT,
            pnl REAL, strategy TEXT
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS portfolio (
            key TEXT PRIMARY KEY, value REAL
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT, strategy TEXT, signal TEXT, price REAL,
            timestamp TEXT
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS strategy_stats (
            strategy TEXT PRIMARY KEY,
            trades INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            total_pnl REAL DEFAULT 0,
            total_win_pnl REAL DEFAULT 0,
            total_loss_pnl REAL DEFAULT 0,
            kelly_fraction REAL DEFAULT 0.25
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS engine_state (
            key TEXT PRIMARY KEY, value TEXT
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_history (
            timestamp INTEGER PRIMARY KEY,
            balance REAL,
            portfolio_value REAL
        )
    """)
    # TODO: Starting capital should come from config, not hardcoded
    db.execute("INSERT OR IGNORE INTO portfolio VALUES ('balance', 10000.0)")
    db.execute("INSERT OR IGNORE INTO portfolio VALUES ('peak', 10000.0)")
    db.execute("INSERT OR IGNORE INTO portfolio VALUES ('total_trades', 0)")
    db.execute("INSERT OR IGNORE INTO portfolio VALUES ('winning_trades', 0)")
    for s in ["SMC", "Momentum", "MeanReversion", "Grid", "TrendStrength",
              "TSMOM", "TrendFollow"]:
        db.execute("INSERT OR IGNORE INTO strategy_stats VALUES (?,0,0,0,0,0,0,0.25)", (s,))
    db.commit()
    return db

# ─── Exchange Connector (bridged to engine/ layer) ────────────────
# BinanceConnector is replaced by EnginePriceProvider from engine_bridge.py.
# The old BinanceConnector used direct CoinGecko calls with no caching or
# rate limiting. EnginePriceProvider adds caching (engine/data/caching),
# rate limiting (engine/data/rate_limiter), and uses engine/risk/ constants.

BinanceConnector = EnginePriceProvider  # backward compat alias for auto_aware

# ─── Strategies ────────────────────────────────────────────────────
# FIX 29 RESOLVED: Inline legacy strategies removed (2026-07-27).
# MomentumStrategy, MeanReversionStrategy, GridTradingStrategy,
# TrendStrengthStrategy) are FALLBACK/LEGACY implementations.
# Canonical implementations live in quant_nanggroe/engine/strategies/.
# These are only used when the adaptive pipeline has no signals for a
# symbol (see _execute_signals fallback branch). Do NOT add new logic
# here — extend engine/strategies/ instead.

class Strategy:
    def __init__(self, name: str, params: Dict = None):
        self.name = name
        self.params = params or {}

    def analyze(self, candles: List[Dict]) -> str:
        return "hold"

    def __repr__(self):
        return f"{self.name}({self.params})"


class SMCStrategy(Strategy):
    def __init__(self, params: Dict = None):
        super().__init__("SMC", params or {"lookback": 20})

    def analyze(self, candles: List[Dict]) -> str:
        lb = self.params["lookback"]
        if len(candles) < lb:
            return "hold"
        closes = [c["close"] for c in candles[-lb:]]
        highs = [c["high"] for c in candles[-lb:]]
        lows = [c["low"] for c in candles[-lb:]]
        recent_high = max(highs[-10:])
        recent_low = min(lows[-10:])
        current = closes[-1]
        prev = closes[-2]
        if current > recent_high and (len(closes) > 2 and prev > closes[-3]):
            return "buy"
        if current < recent_low and (len(closes) > 2 and prev < closes[-3]):
            return "sell"
        return "hold"


class MomentumStrategy(Strategy):
    def __init__(self, params: Dict = None):
        super().__init__("Momentum", params or {"fast": 5, "slow": 15})

    def analyze(self, candles: List[Dict]) -> str:
        slow = self.params["slow"]
        fast = self.params["fast"]
        if len(candles) < slow:
            return "hold"
        closes = [c["close"] for c in candles]
        fast_ma = sum(closes[-fast:]) / fast
        slow_ma = sum(closes[-slow:]) / slow
        if fast_ma > slow_ma > closes[-1]:
            return "buy"
        if fast_ma < slow_ma < closes[-1]:
            return "sell"
        return "hold"


class MeanReversionStrategy(Strategy):
    def __init__(self, params: Dict = None):
        super().__init__("MeanReversion", params or {"period": 20, "std_dev": 2})

    def analyze(self, candles: List[Dict]) -> str:
        period = self.params["period"]
        if len(candles) < period:
            return "hold"
        closes = [c["close"] for c in candles[-period:]]
        mean = sum(closes) / len(closes)
        variance = sum((c - mean) ** 2 for c in closes) / len(closes)
        std = variance ** 0.5
        current = closes[-1]
        if current < mean - std * self.params["std_dev"]:
            return "buy"
        if current > mean + std * self.params["std_dev"]:
            return "sell"
        return "hold"


class GridTradingStrategy(Strategy):
    def __init__(self, params: Dict = None):
        super().__init__("Grid", params or {"lookback": 30, "levels": [0.25, 0.50, 0.75]})

    def analyze(self, candles: List[Dict]) -> str:
        lb = self.params["lookback"]
        if len(candles) < lb:
            return "hold"
        highs = [c["high"] for c in candles[-lb:]]
        lows = [c["low"] for c in candles[-lb:]]
        recent_high = max(highs)
        recent_low = min(lows)
        rang = recent_high - recent_low
        if rang == 0:
            return "hold"

        prev_close = candles[-2]["close"]
        curr_close = candles[-1]["close"]

        for level in self.params["levels"]:
            buy_line = recent_low + level * rang
            sell_line = recent_high - level * rang
            if prev_close <= buy_line < curr_close:
                return "buy"
            if prev_close >= sell_line > curr_close:
                return "sell"
        return "hold"


class TrendStrengthStrategy(Strategy):
    def __init__(self, params: Dict = None):
        super().__init__("TrendStrength", params={"period": 14, "threshold": 25})

    def analyze(self, candles: List[Dict]) -> str:
        period = self.params["period"]
        if len(candles) < period * 2:
            return "hold"
        tr_vals, plus_dm_vals, minus_dm_vals = [], [], []
        for i in range(1, len(candles)):
            h, l, pc = candles[i]["high"], candles[i]["low"], candles[i-1]["close"]
            ph, pl = candles[i-1]["high"], candles[i-1]["low"]
            tr = max(h - l, abs(h - pc), abs(l - pc))
            up = h - ph
            down = pl - l
            plus_dm = up if up > down and up > 0 else 0
            minus_dm = down if down > up and down > 0 else 0
            tr_vals.append(tr)
            plus_dm_vals.append(plus_dm)
            minus_dm_vals.append(minus_dm)

        dx_vals = []
        for i in range(period - 1, len(tr_vals)):
            chunk_tr = sum(tr_vals[i - period + 1:i + 1]) / period
            chunk_p = sum(plus_dm_vals[i - period + 1:i + 1]) / period
            chunk_m = sum(minus_dm_vals[i - period + 1:i + 1]) / period
            if chunk_tr == 0:
                continue
            pdi = 100 * chunk_p / chunk_tr
            ndi = 100 * chunk_m / chunk_tr
            if pdi + ndi == 0:
                continue
            dx_vals.append(100 * abs(pdi - ndi) / (pdi + ndi))

        if len(dx_vals) < period:
            return "hold"
        adx = sum(dx_vals[-period:]) / period
        if adx >= self.params["threshold"]:
            return "trending"
        return "ranging"


# ─── Risk Manager (bridged to engine/ layer) ──────────────────────
# The inline RiskManager is replaced by EngineRiskManager from engine_bridge.py.
# EngineRiskManager uses constitutional limits from engine/risk/constants
# and persists state via engine/persistence/ (FileBackend).

RiskManager = EngineRiskManager  # backward-compatible alias


# ─── Performance Tracker ──────────────────────────────────────────

class PerformanceTracker:
    def __init__(self, db):
        self.db = db

    def record_snapshot(self, balance: float, portfolio_value: float):
        now_ts = int(time.time())
        self.db.execute(
            "INSERT OR REPLACE INTO portfolio_history VALUES (?,?,?)",
            (now_ts, balance, portfolio_value)
        )
        self.db.commit()

    def get_sharpe(self, risk_free: float = 0.02) -> float:
        cur = self.db.execute(
            "SELECT portfolio_value, timestamp FROM portfolio_history ORDER BY timestamp"
        )
        rows = cur.fetchall()
        if len(rows) < 2:
            return 0.0

        daily_returns = {}
        for i in range(1, len(rows)):
            d1 = datetime.fromtimestamp(rows[i-1][1]).strftime("%Y-%m-%d")
            d2 = datetime.fromtimestamp(rows[i][1]).strftime("%Y-%m-%d")
            if d1 != d2:
                ret = (rows[i][0] - rows[i-1][0]) / rows[i-1][0] if rows[i-1][0] > 0 else 0
                daily_returns[d2] = ret

        vals = list(daily_returns.values())
        if len(vals) < 2:
            return 0.0
        mean_ret = sum(vals) / len(vals)
        variance = sum((r - mean_ret) ** 2 for r in vals) / len(vals)
        std = variance ** 0.5
        if std == 0:
            return 0.0
        daily_rf = risk_free / 252
        sharpe = (mean_ret - daily_rf) / std
        return sharpe * (252 ** 0.5)

    def get_volatility(self) -> float:
        cur = self.db.execute(
            "SELECT portfolio_value FROM portfolio_history ORDER BY timestamp"
        )
        values = [r[0] for r in cur.fetchall()]
        if len(values) < 5:
            return 0.0
        returns = [(values[i] - values[i-1]) / values[i-1] for i in range(1, len(values))]
        mean_r = sum(returns) / len(returns)
        variance = sum((r - mean_r) ** 2 for r in returns) / len(returns)
        return (variance ** 0.5) * (252 ** 0.5)

    def get_strategy_stats(self) -> List[Dict]:
        cur = self.db.execute("SELECT * FROM strategy_stats")
        rows = cur.fetchall()
        return [{
            "strategy": r[0], "trades": r[1], "wins": r[2], "losses": r[3],
            "total_pnl": r[4], "avg_win": r[5] / r[2] if r[2] > 0 else 0,
            "avg_loss": r[6] / r[3] if r[3] > 0 else 0,
            "kelly": r[7],
        } for r in rows]

    def generate_report(self, balance: float, portfolio_value: float, asset_pnl: Dict[str, float]):
        dd = RiskManager(self.db).get_drawdown()
        sharpe = self.get_sharpe()
        vol = self.get_volatility()
        cur = self.db.execute("SELECT value FROM portfolio WHERE key='total_trades'")
        total = cur.fetchone()[0]
        cur = self.db.execute("SELECT value FROM portfolio WHERE key='winning_trades'")
        wins = cur.fetchone()[0]
        win_rate = (wins / total * 100) if total > 0 else 0
        stats = self.get_strategy_stats()
        lines = [
            "=== QNA PERFORMANCE REPORT ===",
            f"Balance: ${balance:.2f}",
            f"Portfolio Value: ${portfolio_value:.2f}",
            f"Total PnL: ${portfolio_value - 10000:.2f}",
            f"Return: {((portfolio_value - 10000) / 10000 * 100):.2f}%",
            f"Drawdown: {dd:.2%}",
            f"Sharpe (annualized): {sharpe:.2f}",
            f"Volatility (annualized): {vol:.2%}",
            f"Total Trades: {total}",
            f"Win Rate: {win_rate:.1f}%",
            "",
            "--- Per-Asset PnL ---",
        ]
        for sym, pnl in sorted(asset_pnl.items()):
            lines.append(f"  {sym}: ${pnl:.2f}")
        lines.append("")
        lines.append("--- Strategy Performance ---")
        for s in stats:
            wr = (s["wins"] / s["trades"] * 100) if s["trades"] > 0 else 0
            lines.append(f"  {s['strategy']}: {s['trades']} trades, {wr:.0f}% WR, "
                         f"PnL ${s['total_pnl']:.2f}, Kelly {s['kelly']:.2%}")
        lines.append("=" * 40)
        log.info("\n".join(lines))

    def update_kelly(self, strategy: str):
        cur = self.db.execute(
            "SELECT trades, wins, losses, total_win_pnl, total_loss_pnl "
            "FROM strategy_stats WHERE strategy=?",
            (strategy,)
        )
        row = cur.fetchone()
        if not row or row[0] < 3:
            return
        trades, wins, losses, twp, tlp = row
        win_rate = wins / trades
        avg_win = twp / wins if wins > 0 else 0
        avg_loss = abs(tlp / losses) if losses > 0 else 1
        if avg_loss == 0:
            avg_loss = 1
        kelly = win_rate - (1 - win_rate) / (avg_win / avg_loss) if avg_win > 0 else 0
        kelly = max(0.05, min(0.25, kelly))
        self.db.execute(
            "UPDATE strategy_stats SET kelly_fraction=? WHERE strategy=?",
            (kelly, strategy)
        )
        self.db.commit()

    def record_trade_result(self, strategy: str, pnl: float):
        self.db.execute(
            "UPDATE strategy_stats SET trades=trades+1, total_pnl=total_pnl+? "
            "WHERE strategy=?",
            (pnl, strategy)
        )
        if pnl > 0:
            self.db.execute(
                "UPDATE strategy_stats SET wins=wins+1, total_win_pnl=total_win_pnl+? "
                "WHERE strategy=?",
                (pnl, strategy)
            )
        else:
            self.db.execute(
                "UPDATE strategy_stats SET losses=losses+1, total_loss_pnl=total_loss_pnl+? "
                "WHERE strategy=?",
                (abs(pnl), strategy)
            )
        self.db.commit()
        self.update_kelly(strategy)


# ─── Live Engine ──────────────────────────────────────────────────

class LiveEngine:
    def __init__(self):
        self.db = init_db()
        self.price_provider = EnginePriceProvider()
        self.connector = self.price_provider
        self.risk = EngineRiskManager(self.db)
        self.perf = PerformanceTracker(self.db)
        self.data = DataManager(cg_api_key=os.environ.get("CG_API_KEY", ""))
        self.running = False
        self.trading_enabled = _env_bool("QNA_TRADING_ENABLED", False)
        self.pid_file = DATA_DIR / "qna.pid"
        self.cycle_count = 0
        self.total_errors = 0
        self.last_cleanup = 0
        self.last_heartbeat = 0
        self.last_report = 0
        self.prices: Dict[str, float] = {}
        self.asset_candles: Dict[str, List[Dict]] = {}
        self.htf_candles: Dict[str, List[Dict]] = {}
        self.mtf_candles: Dict[str, List[Dict]] = {}
        self.strategies: Dict[str, Strategy] = {
            "SMC": SMCStrategy(),
            "Momentum": MomentumStrategy(),
            "MeanReversion": MeanReversionStrategy(),
            "Grid": GridTradingStrategy(),
            "Trend": TrendStrengthStrategy(),
        }
        self.np_strategies: Dict[str, object] = {
            "TSMOM": TSMOM(),
            "TrendFollow": TrendFollow(),
        }
        self._load_state()
        self._init_auto_aware()
        # ── KillSwitch (cross-process fail-closed) ──
        configure_kill_switch_file()
        self._kill_switch = KillSwitch()
        log.info(f"KillSwitch initialized (active={self._kill_switch.is_active})")

        self.production = create_production_engine(
            price_provider=self.price_provider,
            risk_manager=self.risk,
            db=self.db,
        )
        log.info(f"Production engine: {list(self.production['strategy_runner'].strategies.keys())} strategies")
        self._exec = self.production["execution"]  # Phase A: wired execution path
        self._sync_broker_positions()  # Phase A: sync ledger with broker on startup
        # ── Adaptive integration (replaces inline strategies) ──
        self._signal_pipeline, self._risk_gate, self._data_feeds = create_live_pipeline(
            initial_equity=10000.0,
            enable_mtf=True,
            enable_cot=True,
            enable_calendar=True,
        )
        summary = self._signal_pipeline.get_summary()
        log.info(
            f"Adaptive pipeline: {summary['strategies_loaded']} strategies, "
            f"MTF={summary['mtf_enabled']}, COT={summary['cot_enabled']}, "
            f"Calendar={summary['calendar_enabled']}"
        )
        self._cot_analysis: Dict = {}
        self._calendar_events: List = []
        self._sentiment_data: Dict[str, Dict] = {}

    def _init_auto_aware(self):
        try:
            from quant_nanggroe.auto_aware import AutoAware
            aa = AutoAware(self.db, self.connector, self.risk)
            if aa.active_strategies:
                log.info(f"AutoAware loaded {len(aa.active_strategies)} backtest strategies")
            self.auto_aware = aa
        except Exception as e:
            self.auto_aware = None
            log.debug(f"AutoAware: {e}")

    def _load_state(self):
        try:
            cur = self.db.execute("SELECT value FROM engine_state WHERE key='cycle_count'")
            row = cur.fetchone()
            if row:
                self.cycle_count = int(row[0])
            cur = self.db.execute("SELECT value FROM engine_state WHERE key='total_errors'")
            row = cur.fetchone()
            if row:
                self.total_errors = int(row[0])
        except Exception:
            pass

    def _save_state(self):
        try:
            self.db.execute(
                "INSERT OR REPLACE INTO engine_state VALUES (?,?)",
                ("cycle_count", str(self.cycle_count))
            )
            self.db.execute(
                "INSERT OR REPLACE INTO engine_state VALUES (?,?)",
                ("total_errors", str(self.total_errors))
            )
            self.db.execute(
                "INSERT OR REPLACE INTO engine_state VALUES (?,?)",
                ("last_heartbeat", datetime.now().isoformat())
            )
            self.db.commit()
        except Exception as e:
            log.warning(f"State save error: {e}")

    def _get_kelly(self, strategy: str) -> float:
        cur = self.db.execute(
            "SELECT kelly_fraction FROM strategy_stats WHERE strategy=?",
            (strategy,)
        )
        row = cur.fetchone()
        return row[0] if row and row[0] > 0 else 0.25

    def _get_open_position(self, symbol: str) -> Optional[Dict]:
        cur = self.db.execute(
            "SELECT id, symbol, side, entry_price, quantity, entry_time, "
            "highest_since_entry, strategy, partial_exit_price, exited_qty "
            "FROM positions WHERE symbol=? AND status='open' ORDER BY id DESC LIMIT 1",
            (symbol,)
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row[0], "symbol": row[1], "side": row[2],
            "entry_price": row[3], "quantity": row[4], "entry_time": row[5],
            "highest_since_entry": row[6] or row[3],
            "strategy": row[7], "partial_exit_price": row[8] or 0,
            "exited_qty": row[9] or 0,
        }

    def _can_open_new_position(self, symbol: str) -> tuple[bool, str]:
        # KillSwitch gate: fail-closed if kill switch is active
        if self._kill_switch.is_active:
            return False, "KillSwitch active — no new positions"
        if not self.trading_enabled:
            return False, "QNA_TRADING_ENABLED is not true"
        if self._get_open_position(symbol):
            return False, f"{symbol} already has an open position"
        ok, reason = self.risk.can_trade()
        if not ok:
            return False, reason
        return True, "ok"

    def _update_dcc_garch(self):
        """Auto-fit DCC-GARCH from candle data for dynamic correlation tracking.

        Computes log returns from available asset candles, builds a DataFrame,
        and calls RiskEnforcer.update_correlation() to re-fit the model.

        Runs every DCC_UPDATE_INTERVAL cycles.
        """
        try:
            import numpy as np
            import pandas as pd

            # Gather close prices for all available assets
            close_data: dict[str, list[float]] = {}
            n_obs = 0
            for sym in ASSET_SYMBOLS:
                candles = self.asset_candles.get(sym, [])
                if len(candles) < 30:
                    continue
                closes = [c["close"] for c in candles]
                if len(closes) > n_obs:
                    n_obs = len(closes)
                close_data[sym] = closes

            if len(close_data) < 2:
                log.debug("DCC auto-fit: need at least 2 assets with 30+ candles")
                return

            # Align to same length (shortest)
            min_len = min(len(v) for v in close_data.values())
            if min_len < 30:
                log.debug("DCC auto-fit: insufficient data (%d obs)", min_len)
                return

            aligned = {sym: prices[-min_len:] for sym, prices in close_data.items()}
            df = pd.DataFrame(aligned)

            # Compute log returns
            log_returns = np.log(df / df.shift(1)).dropna()
            if len(log_returns) < 30:
                log.debug("DCC auto-fit: insufficient returns (%d rows)", len(log_returns))
                return

            # Fit DCC-GARCH via RiskEnforcer
            success = self.production["risk"].update_correlation(log_returns)
            if success:
                status = self.production["risk"].get_dcc_status()
                log.info(
                    "DCC-GARCH auto-fit: %d assets, mean vol=%.2f%%, mean corr=%.4f",
                    status.get("n_assets", 0),
                    status.get("mean_vol_pct", 0),
                    status.get("mean_corr", 0),
                )
                # Expose DCC context via env vars for downstream providers
                os.environ["QNA_DCC_MEAN_CORR"] = str(status.get("mean_corr", 0))
                os.environ["QNA_DCC_MEAN_VOL_PCT"] = str(status.get("mean_vol_pct", 0))
                os.environ["QNA_DCC_N_ASSETS"] = str(status.get("n_assets", 0))
            else:
                log.debug("DCC-GARCH auto-fit failed")
        except Exception as e:
            log.debug("DCC auto-fit error: %s", e)

    def _sync_broker_positions(self):
        """Phase A: reconcile open positions in ledger with broker (MT5 or paper)
        so the engine does not double-open when restarted live."""
        try:
            if not hasattr(self, "_exec") or self._exec is None:
                return
            # Use public API — not self._exec._mt5 (private, always None)
            mt5 = self._exec.get_mt5_connector()
            if mt5 is not None and mt5.connected:
                for p in mt5.get_positions():
                    sym = p.symbol
                    # reverse map MT5 BTCUSD -> QNA BTCUSDT not needed; keep MT5 symbol
                    if self._get_open_position(sym) is None:
                        self.db.execute(
                            "INSERT INTO positions (symbol, side, entry_price, quantity, "
                            "entry_time, highest_since_entry, strategy, take_profit) "
                            "VALUES (?,?,?,?,?,?,?,?)",
                            (sym, "long" if p.quantity > 0 else "short", p.entry_price,
                             abs(p.quantity), datetime.now().isoformat(), p.entry_price,
                             "mt5-sync", p.entry_price * 1.05))
                        self.db.commit()
                        log.info(f"SYNCED broker position {sym} {p.quantity}")
        except Exception as e:
            log.warning(f"Broker position sync skipped: {e}")

    def _open_position(self, symbol: str, price: float, qty: float, strategy: str):
        allowed, reason = self._can_open_new_position(symbol)
        if not allowed:
            log.warning(f"OPEN BLOCKED {symbol} ({strategy}): {reason}")
            return
        now = datetime.now().isoformat()
        tp_target = TP_TARGETS.get(strategy, 0.05)
        tp_price = price * (1 + tp_target)
        # Phase A: push real order through wired execution manager (MT5 or paper)
        # P0 FIX: only record position AFTER confirming fill — no phantom positions on failure
        try:
            result = self._exec.execute_signal(
                type("Sig", (), {"symbol": symbol, "side": "buy", "strategy": strategy,
                                 "stop_loss": price * (1 - TRAILING_STOP_PCT),
                                 "take_profit": tp_price})(),
                price, self.risk.get_balance())
            mode = (result or {}).get("mode", "unknown")
            status = (result or {}).get("status", "")
            # Reject if backend explicitly rejected the order or returned no fill
            if status in ("rejected", "failed") or (result or {}).get("fill_id") is False:
                log.error(f"ORDER REJECTED {symbol} ({strategy}): {result}")
                return
            log.info(f"ORDER SENT {symbol} {qty:.4f} @ {price:.2f} ({strategy}) -> {mode}")
            # Ledger insert only after confirmed fill (audit trail)
            self.db.execute(
                "INSERT INTO positions (symbol, side, entry_price, quantity, entry_time, "
                "highest_since_entry, strategy, take_profit) VALUES (?,?,?,?,?,?,?,?)",
                (symbol, "long", price, qty, now, price, strategy, tp_price)
            )
            self.db.commit()
            log.info(f"BUY {symbol} {qty:.4f} @ {price:.2f} ({strategy})")
        except Exception as e:
            log.error(f"Live order failed {symbol}: {e}")
            return  # P0 FIX: do NOT record position on exception
        # Register position with ThesisDriftGuard for macro thesis monitoring
        try:
            event_type = os.environ.get("QNA_MACRO_EVENT", "UNKNOWN")
            self.production["risk"].thesis_register_position(
                symbol, "long", event_type=event_type, entry_price=price,
            )
        except Exception as e:
            log.debug("Thesis register: %s", e)

    def _close_position(self, pos: dict, price: float, reason: str = "signal"):
        remaining = pos["quantity"] - pos["exited_qty"]
        if remaining <= 0:
            return
        pnl = (price - pos["entry_price"]) * remaining
        balance = self.risk.get_balance()
        new_balance = balance + pnl
        # Phase A: send real close order through wired execution manager (MT5, paper, or engine)
        try:
            close_signal = type("Sig", (), {
                "symbol": pos["symbol"], "side": "sell", "strategy": pos.get("strategy", ""),
                "stop_loss": None, "take_profit": None,
            })()
            result = self._exec.execute_signal(close_signal, price, balance)
            mode = (result or {}).get("mode", "unknown")
            log.info(f"CLOSE ORDER SENT {pos['symbol']} {remaining:.4f} @ {price:.2f} -> {mode}")
        except Exception as e:
            log.error(f"Live close failed {pos['symbol']}: {e}")
            # record lesson — import here to avoid circular or missing import
            try:
                from quant_nanggroe.engine_production_bridge import _record_lesson
                _record_lesson(e, f"close_position {pos['symbol']}")
            except Exception:
                pass
        self.db.execute("UPDATE portfolio SET value=? WHERE key='balance'", (new_balance,))
        self.db.execute("UPDATE portfolio SET value=value+1 WHERE key='total_trades'")
        if pnl > 0:
            self.db.execute("UPDATE portfolio SET value=value+1 WHERE key='winning_trades'")
        total_pnl = pnl
        if pos["exited_qty"] > 0:
            partial_pnl = (pos["partial_exit_price"] - pos["entry_price"]) * pos["exited_qty"]
            total_pnl += partial_pnl
        self.db.execute(
            "INSERT INTO trades (symbol, side, entry_price, exit_price, quantity, "
            "entry_time, exit_time, pnl, strategy) VALUES (?,?,?,?,?,?,?,?,?)",
            (pos["symbol"], "long", pos["entry_price"], price, remaining,
             pos["entry_time"], datetime.now().isoformat(), pnl, pos["strategy"])
        )
        self.db.execute("UPDATE positions SET status='closed' WHERE id=?", (pos["id"],))
        self.db.commit()
        self.perf.record_trade_result(pos["strategy"], total_pnl)
        # Unregister from thesis drift guard
        try:
            self.production["risk"].thesis_unregister(pos["symbol"])
        except Exception as e:
            log.debug("Thesis unregister: %s", e)
        log.info(f"SELL {pos['symbol']} @ {price:.2f} | PnL: ${pnl:.2f} | Reason: {reason} | "
                 f"Balance: ${new_balance:.2f}")

    def _partial_exit(self, pos: dict, price: float):
        if pos["exited_qty"] > 0:
            return
        exit_qty = pos["quantity"] / 2
        pnl = (price - pos["entry_price"]) * exit_qty
        balance = self.risk.get_balance()
        new_balance = balance + pnl
        self.db.execute("UPDATE portfolio SET value=? WHERE key='balance'", (new_balance,))
        self.db.execute("UPDATE portfolio SET value=value+1 WHERE key='total_trades'")
        if pnl > 0:
            self.db.execute("UPDATE portfolio SET value=value+1 WHERE key='winning_trades'")
        self.db.execute(
            "UPDATE positions SET partial_exit_price=?, exited_qty=? WHERE id=?",
            (price, exit_qty, pos["id"])
        )
        self.db.execute(
            "INSERT INTO trades (symbol, side, entry_price, exit_price, quantity, "
            "entry_time, exit_time, pnl, strategy) VALUES (?,?,?,?,?,?,?,?,?)",
            (pos["symbol"], "partial", pos["entry_price"], price, exit_qty,
             pos["entry_time"], datetime.now().isoformat(), pnl, pos["strategy"] + "_TP")
        )
        self.db.commit()
        log.info(f"PARTIAL EXIT {pos['symbol']} {exit_qty:.4f} @ {price:.2f} | PnL: ${pnl:.2f}")

    def _update_positions(self):
        for sym in ASSET_SYMBOLS:
            pos = self._get_open_position(sym)
            if not pos:
                continue
            price = self.prices.get(sym)
            if not price:
                continue

            if price > pos["highest_since_entry"]:
                pos["highest_since_entry"] = price
                self.db.execute(
                    "UPDATE positions SET highest_since_entry=? WHERE id=?",
                    (price, pos["id"])
                )
                self.db.commit()

            trail_price = pos["highest_since_entry"] * (1 - TRAILING_STOP_PCT)
            if price < trail_price:
                self._close_position(pos, price, "trailing_stop")
                continue

            if pos["exited_qty"] == 0:
                tp_target = TP_TARGETS.get(pos["strategy"], 0.05)
                tp_price = pos["entry_price"] * (1 + tp_target)
                if price >= tp_price:
                    self._partial_exit(pos, price)

    def _check_rebalance(self):
        balance = self.risk.get_balance()
        positions_value = 0.0
        asset_values = {}
        for sym in ASSET_SYMBOLS:
            pos = self._get_open_position(sym)
            price = self.prices.get(sym, 0)
            val = (pos["quantity"] - pos["exited_qty"]) * price if pos and price > 0 else 0
            asset_values[sym] = val
            positions_value += val
        total_value = balance + positions_value
        if total_value <= 0:
            return
        for a in ASSETS:
            sym = a["symbol"]
            current_alloc = asset_values.get(sym, 0) / total_value
            target = a["allocation"]
            drift = abs(current_alloc - target)
            if drift > REBALANCE_THRESHOLD:
                if current_alloc > target + REBALANCE_THRESHOLD:
                    pos = self._get_open_position(sym)
                    if pos:
                        self._close_position(pos, self.prices.get(sym, 0), "rebalance")
                log.info(f"REBALANCE {sym}: alloc {current_alloc:.1%} vs target {target:.1%} (drift {drift:.1%})")

    def _execute_signals(self, symbol: str, current_price: float):
        pos = self._get_open_position(symbol)

        # Primary: adaptive pipeline (15 strategies, regime-based, MTF-aligned)
        adaptive_signals = self._signal_pipeline.generate_signals(
            candles_dict={symbol: self.asset_candles.get(symbol, [])},
            prices={symbol: current_price},
            htf_candles={symbol: self.htf_candles.get(symbol, [])} if self.htf_candles else None,
            mtf_candles={symbol: self.mtf_candles.get(symbol, [])} if self.mtf_candles else None,
            cot_data=self._cot_analysis,
            calendar_data=self._calendar_events,
            sentiment_data=self._sentiment_data,
        )

        for ls in adaptive_signals:
            if ls.side == "hold":
                continue
            self.db.execute(
                "INSERT INTO signals (symbol, strategy, signal, price, timestamp) "
                "VALUES (?,?,?,?,?)",
                (symbol, ls.strategy, ls.side, current_price, datetime.now().isoformat())
            )
            self.db.commit()

            # Risk gate pre-trade check
            balance = self.risk.get_balance()
            allowed, reason = self._risk_gate.check_signal(ls, balance)
            if not allowed:
                log.debug(f"Risk veto {ls.strategy} {symbol}: {reason}")
                continue

            if ls.side == "buy" and not pos:
                kelly = self._get_kelly(ls.strategy)
                qty = self._risk_gate.position_size(current_price, balance, kelly)
                if qty > 0:
                    self._open_position(symbol, current_price, qty, ls.strategy)
                    self._risk_gate.add_position(symbol)
                    pos = self._get_open_position(symbol)
            elif ls.side == "sell" and pos:
                self._close_position(pos, current_price, ls.strategy)
                self._risk_gate.remove_position(symbol)
                pos = None

        # Also run inline strategies as fallback for strategies not in adaptive pipeline
        if not adaptive_signals and symbol in self.strategies:
            candles = self.asset_candles.get(symbol, [])
            if len(candles) >= 20:
                # Regime-aware selection from the 4 core inline strategies
                regime = self.strategies["Trend"].analyze(candles)
                active_strategies = []
                if regime == "trending":
                    active_strategies = [self.strategies["SMC"], self.strategies["Momentum"]]
                elif regime == "ranging":
                    active_strategies = [self.strategies["SMC"], self.strategies["MeanReversion"],
                                         self.strategies["Grid"]]
                else:
                    active_strategies = list(self.strategies.values())

                for strategy in active_strategies:
                    if strategy.name == "Trend":
                        continue
                    signal = strategy.analyze(candles)
                    if signal == "hold":
                        continue
                    self.db.execute(
                        "INSERT INTO signals (symbol, strategy, signal, price, timestamp) "
                        "VALUES (?,?,?,?,?)",
                        (symbol, strategy.name, signal, current_price, datetime.now().isoformat())
                    )
                    self.db.commit()
                    if signal == "buy":
                        ok, msg = self._can_open_new_position(symbol)
                        if not ok:
                            log.debug(f"Risk veto {strategy.name} {symbol}: {msg}")
                            continue
                    if signal == "buy" and not pos:
                        kelly = self._get_kelly(strategy.name)
                        qty = self.risk.position_size(current_price, kelly)
                        self._open_position(symbol, current_price, qty, strategy.name)
                        pos = self._get_open_position(symbol)
                    elif signal == "sell" and pos:
                        self._close_position(pos, current_price, strategy.name)
                        pos = None

    def _execute_np_signals(self, symbol: str, current_price: float):
        candles = self.asset_candles.get(symbol, [])
        if len(candles) < 30:
            return
        closes = [c["close"] for c in candles]
        pos = self._get_open_position(symbol)

        for name, strat in self.np_strategies.items():
            try:
                result = strat.analyze(closes)
                sig = result["signal"]
                if sig == "hold":
                    continue
                self.db.execute(
                    "INSERT INTO signals (symbol, strategy, signal, price, timestamp) "
                    "VALUES (?,?,?,?,?)",
                    (symbol, name, sig, current_price, datetime.now().isoformat())
                )
                self.db.commit()
                if sig == "buy":
                    ok, msg = self._can_open_new_position(symbol)
                    if not ok:
                        log.debug(f"Risk veto {name} {symbol}: {msg}")
                        continue
                if sig == "buy" and not pos:
                    kelly = self._get_kelly(name)
                    qty = self.risk.position_size(current_price, kelly)
                    self._open_position(symbol, current_price, qty, name)
                    pos = self._get_open_position(symbol)
                elif sig == "sell" and pos:
                    self._close_position(pos, current_price, name)
                    pos = None
            except Exception as e:
                log.debug(f"{name} {symbol}: {e}")

    def execute_cycle(self):
        # ── KillSwitch gate (cross-process fail-closed) ──
        if self._kill_switch.is_active:
            log.critical("KillSwitch ACTIVE — halting all trading in execute_cycle")
            return

        # Production bridge: risk check
        balance = self.risk.get_balance()
        pos_count = self.risk.get_open_position_count()
        portfolio_val = balance
        for sym in ASSET_SYMBOLS:
            pos = self._get_open_position(sym)
            price = self.prices.get(sym, 0)
            if pos and price > 0:
                portfolio_val += (pos["quantity"] - pos["exited_qty"]) * price
        self.production["risk"].update_drawdown(portfolio_val)
        if self.production["risk"].is_kill_switch_triggered():
            log.critical("KILL SWITCH ACTIVE — halting all trading")
            return

        # ── DCC-GARCH: auto-fit dynamic correlation every N cycles ──
        if self.cycle_count > 0 and self.cycle_count % DCC_UPDATE_INTERVAL == 0:
            self._update_dcc_garch()

        # ── Thesis Drift Guard: check macro context against active positions ──
        if self.cycle_count % 3 == 0:  # check every 3 cycles
            try:
                macro_event = os.environ.get("QNA_MACRO_EVENT", "")
                weather = os.environ.get("QNA_MACRO_WEATHER", "NEUTRAL_MIXED")
                cot_signal = os.environ.get("QNA_COT_SIGNAL", "BALANCED")
                smt = os.environ.get("QNA_SMT_DIVERGENCE", "false").lower() == "true"
                self._thesis_result = self.production["risk"].thesis_check(
                    event_type=macro_event or "UNKNOWN",
                    weather=weather,
                    cot_signal=cot_signal,
                    smt_divergence=smt,
                )
                if self._thesis_result.get("has_hard_exit"):
                    log.critical(
                        "THESIS DRIFT HARD EXIT triggered — closing invalidated positions"
                    )
                    for sym, pos_data in self._thesis_result.get("positions", {}).items():
                        if pos_data.get("stage") == "HARD_EXIT":
                            live_pos = self._get_open_position(sym)
                            if live_pos:
                                price = self.prices.get(sym, 0)
                                if price > 0:
                                    log.warning(
                                        "THESIS HARD EXIT: closing %s at %.2f (%s)",
                                        sym, price, pos_data.get("latest_contradictions", []),
                                    )
                                    self._close_position(
                                        live_pos, price,
                                        f"thesis_hard_exit_{macro_event}",
                                    )
            except Exception as e:
                log.debug("Thesis drift check: %s", e)
        
        self.prices = self.data.get_all_prices()
        if not self.prices:
            self.prices = self.connector.get_all_prices()
        if not self.prices:
            log.warning("No prices available from any provider")
            return

        fetch_klines = (self.cycle_count % 3 == 0)
        fetch_mtf = (self.cycle_count % 6 == 0)   # MTF data every 2nd kline fetch
        fetch_htf = (self.cycle_count % 15 == 0)   # HTF data every 5th kline fetch
        for a in ASSETS:
            sym = a["symbol"]
            if fetch_klines:
                candles = self.data.get_klines(sym, "1m", 60)
                if not candles:
                    candles = self.price_provider.get_klines(sym, "1m", 60)
                if candles:
                    for c in candles:
                        self.db.execute(
                            "INSERT OR REPLACE INTO candles VALUES (?,?,?,?,?,?,?)",
                            (sym, c["timestamp"], c["open"], c["high"],
                             c["low"], c["close"], c["volume"])
                        )
                    self.db.commit()
                    self.asset_candles[sym] = candles
            else:
                cur = self.db.execute(
                    "SELECT timestamp, open, high, low, close, volume "
                    "FROM candles WHERE symbol=? ORDER BY timestamp DESC LIMIT 60",
                    (sym,))
                rows = cur.fetchall()
                if rows:
                    self.asset_candles[sym] = [
                        {"timestamp": r[0], "open": r[1], "high": r[2],
                         "low": r[3], "close": r[4], "volume": r[5]}
                        for r in reversed(rows)]

            # MTF: entry-level timeframe (15m) for signal precision
            if fetch_mtf:
                mtf_candles = self.data.get_klines(sym, "15m", 60)
                if mtf_candles:
                    self.mtf_candles[sym] = mtf_candles

            # HTF: trend-level timeframe (4h) for higher trend direction
            if fetch_htf:
                htf_candles = self.data.get_klines(sym, "4h", 30)
                if htf_candles:
                    self.htf_candles[sym] = htf_candles

        # Fetch COT + calendar data periodically
        if self.cycle_count % 20 == 0:
            try:
                self._cot_analysis = self._data_feeds.get_cot_analysis(
                    symbols=["BTC", "ETH"] + ASSET_SYMBOLS
                )
            except Exception as e:
                log.debug(f"COT fetch: {e}")
        if self.cycle_count % 10 == 0:
            try:
                self._calendar_events = self._data_feeds.get_calendar_events(hours_ahead=48)
            except Exception as e:
                log.debug(f"Calendar fetch: {e}")
        if self.cycle_count % 15 == 0:
            try:
                self._sentiment_data = self._data_feeds.get_sentiment_scores(
                    symbols=["BTC", "ETH"] + [a["symbol"] for a in ASSETS]
                )
            except Exception as e:
                log.debug(f"Sentiment fetch: {e}")

        for sym in ASSET_SYMBOLS:
            price = self.prices.get(sym)
            if not price:
                continue
            self._execute_signals(sym, price)
            self._execute_np_signals(sym, price)
        
        # Production bridge: regime-aware production strategy signals
        if self.cycle_count % 5 == 0:
            regime = self.production["regime"].detect(self.prices, self.asset_candles)
        else:
            regime = self.production["regime"].current_regime
        active_strats = self.production["regime"].select_strategies(regime)
        prod_signals = self.production["strategy_runner"].generate_signals(
            self.asset_candles, self.prices, active_strats)
        safe_signals = self.production["risk"].filter_signals(prod_signals)
        for sig in safe_signals:
            if sig.side == "buy":
                ok, msg = self._can_open_new_position(sig.symbol)
                if not ok:
                    log.debug(f"Production risk veto {sig.strategy} {sig.symbol}: {msg}")
                    continue
            exec_order = self.production["execution"].execute_signal(
                sig, self.prices.get(sig.symbol, 0), balance)
            if exec_order and exec_order["mode"] == "fallback":
                # Fallback: use existing position management
                if exec_order["side"] == "buy" and not self._get_open_position(sig.symbol):
                    kelly = self._get_kelly(sig.strategy)
                    qty = self.risk.position_size(exec_order["price"], kelly)
                    self._open_position(sig.symbol, exec_order["price"], qty, sig.strategy)
                elif exec_order["side"] == "sell":
                    pos = self._get_open_position(sig.symbol)
                    if pos:
                        self._close_position(pos, exec_order["price"], sig.strategy)

        # Production bridge: automated backtest every 100 cycles
        if self.cycle_count > 0:
            self.production["backtest"].run(self.asset_candles, self.cycle_count)
        
        self._update_positions()
        self.risk.update_peak()
        self._check_rebalance()

        balance = self.risk.get_balance()
        portfolio_value = balance
        for sym in ASSET_SYMBOLS:
            pos = self._get_open_position(sym)
            price = self.prices.get(sym, 0)
            if pos and price > 0:
                remaining = pos["quantity"] - pos["exited_qty"]
                portfolio_value += remaining * price
        self.perf.record_snapshot(balance, portfolio_value)

        if self.cycle_count % HEARTBEAT_INTERVAL == 0:
            self._heartbeat(balance, portfolio_value)

        # Phase E: closed-PnL feedback loop (daily @ 60s cycle)
        if self.cycle_count % 1440 == 0 and self.cycle_count > 0:
            self._closed_pnl_feedback()

        if self.auto_aware and self.cycle_count % 5 == 0:
            try:
                self.auto_aware.tick(self.asset_candles)
            except Exception as e:
                log.debug(f"AutoAware tick: {e}")
        if self.cycle_count % CLEANUP_INTERVAL == 0:
            self._auto_cleanup()
        if self.cycle_count % REPORT_INTERVAL == 0 and self.cycle_count > 0:
            asset_pnl = self._calc_asset_pnl()
            self.perf.generate_report(balance, portfolio_value, asset_pnl)

        self._save_state()

    def _calc_asset_pnl(self) -> Dict[str, float]:
        result = {}
        for sym in ASSET_SYMBOLS:
            cur = self.db.execute(
                "SELECT COALESCE(SUM(pnl), 0) FROM trades WHERE symbol=?",
                (sym,)
            )
            result[sym] = round(cur.fetchone()[0], 2)
        return result

    def _closed_pnl_feedback(self):
        """Phase E: rank strategies by closed-PnL expectation, trigger evolver
        for losers, promote winners. Runs daily (every 1440 cycles @ 60s)."""
        try:
            cur = self.db.execute(
                "SELECT strategy, trades, wins, total_pnl FROM strategy_stats")
            rows = cur.fetchall()
            ranked = []
            for s, t, w, pnl in rows:
                if t < 3:
                    continue
                win_rate = w / t
                expectation = pnl / t  # avg PnL per trade
                ranked.append((s, t, win_rate, expectation))
            ranked.sort(key=lambda x: x[3], reverse=True)
            for s, t, wr, exp in ranked:
                if exp < 0:  # negative expectation -> evolve or disable
                    log.warning(f"STRATEGY {s}: negative expectation ${exp:.2f}/trade "
                                 f"({wr:.0%} WR, {t} trades) — candidate for evolver")
                    # Trigger StrategyEvolver if available
                    try:
                        from quant_nanggroe.engine.strategies.strategy_evolver import StrategyEvolver
                        from quant_nanggroe.engine.strategies.registry import StrategyRegistry
                        import random
                        ev = StrategyEvolver()
                        baseline = {"lookback": 20, "atr_mult": 1.2}
                        try:
                            strategy_cls = StrategyRegistry.get(s)
                            if strategy_cls:
                                inst = strategy_cls()
                                params = inst.get_parameters()
                                if params:
                                    baseline = params
                        except Exception:
                            pass
                        mutated = {k: v * (1 + random.uniform(-0.15, 0.15)) for k, v in baseline.items()}
                        att = ev.evaluate(s, baseline, mutated)
                        log.info(f"Evolver {s}: {att.reason}")
                    except Exception as e:
                        log.debug(f"Evolver skip {s}: {e}")
                else:
                    log.info(f"STRATEGY {s}: +${exp:.2f}/trade ({wr:.0%} WR) — KEEP/PROMOTE")
            if ranked:
                best = ranked[0]
                log.info(f"CLOSED-PnL RANK: best={best[0]} (${best[3]:.2f}/trade)")
        except Exception as e:
            log.debug(f"Closed-PnL feedback: {e}")

    def _heartbeat(self, balance: float, portfolio_value: float):
        dd = self.risk.get_drawdown()
        open_pos = self.risk.get_open_position_count()
        regime = self.production["regime"].current_regime
        prod_strats = len(self.production["strategy_runner"].strategies)
        log.info(
            f"HEARTBEAT | Cycle {self.cycle_count} | Regime {regime} | "
            f"Balance ${balance:.2f} | Portfolio ${portfolio_value:.2f} | "
            f"Drawdown {dd:.2%} | Open positions {open_pos} | "
            f"Prod strats {prod_strats} | Errors {self.total_errors}"
        )

        # Append DCC-GARCH correlation insight to heartbeat
        try:
            dcc_status = self.production["risk"].get_dcc_status()
            if dcc_status.get("fitted"):
                log.info(
                    "DCC-GARCH: mean_corr=%.4f mean_vol=%.2f%% (%d assets)",
                    dcc_status.get("mean_corr", 0),
                    dcc_status.get("mean_vol_pct", 0),
                    dcc_status.get("n_assets", 0),
                )
        except Exception:
            pass
        msg = format_heartbeat(self.cycle_count, balance, portfolio_value,
                               dd, open_pos, self.total_errors)
        send_telegram(msg)

    def _auto_cleanup(self):
        cutoff = int((datetime.now() - timedelta(days=7)).timestamp())
        self.db.execute("DELETE FROM candles WHERE timestamp < ?", (cutoff,))
        self.db.execute(
            "DELETE FROM portfolio_history WHERE timestamp < ?",
            (cutoff,)
        )
        self.db.commit()
        log.info("Cleaned up data older than 7 days")

    def start(self):
        self.pid_file.write_text(str(os.getpid()))
        self.running = True
        log.info("QUANT NANGGROE — MULTI-ASSET HEDGE FUND ENGINE STARTED")
        log.info(f"   Balance: ${self.risk.get_balance():.2f}")
        log.info(f"   Assets: {[a['symbol'] for a in ASSETS]}")
        allocations = {a['symbol']: f"{a['allocation']*100:.0f}%" for a in ASSETS}
        log.info(f"   Allocations: {allocations}")
        log.info(f"   Strategies: {list(self.strategies.keys())}")
        log.info(f"   Trading enabled: {self.trading_enabled}")
        log.info(f"   Resuming from cycle {self.cycle_count}")

        try:
            stale = StalePositionAnalyzer(self.db, self.price_provider)
            stale.analyze()
        except Exception as e:
            log.debug(f"Stale position analysis: {e}")

        try:
            while self.running:
                self.cycle_count += 1
                log.info(f"--- Cycle {self.cycle_count} ---")
                try:
                    self.execute_cycle()
                except Exception as e:
                    self.total_errors += 1
                    log.error(f"Cycle error: {e}")
                    if self.total_errors % 3 == 0:
                        send_telegram(format_error_message(str(e), self.cycle_count))
                time.sleep(60)
        except KeyboardInterrupt:
            self.stop()
        except Exception as e:
            log.error(f"Engine fatal error: {e}")
            send_telegram(format_error_message(f"FATAL: {e}", self.cycle_count))
            self.stop()

    def stop(self):
        self.running = False
        self._save_state()
        self.pid_file.unlink(missing_ok=True)
        log.info("QUANT NANGGROE — ENGINE STOPPED")

    def is_running(self) -> bool:
        if self.pid_file.exists():
            try:
                pid = int(self.pid_file.read_text().strip())
                os.kill(pid, 0)
                return True
            except (OSError, ValueError):
                pass
        return self.running

    def health(self) -> int:
        issues = []
        open_pos = self.risk.get_open_position_count()
        dd = self.risk.get_drawdown()
        balance = self.risk.get_balance()
        peak = self.risk.get_peak()
        if open_pos > MAX_POSITIONS_TOTAL:
            issues.append(f"open_positions={open_pos} exceeds limit={MAX_POSITIONS_TOTAL}")
        if dd > self.risk.MAX_DRAWDOWN:
            issues.append(f"drawdown={dd:.2%} exceeds limit={self.risk.MAX_DRAWDOWN:.2%}")
        if balance <= 0:
            issues.append(f"balance={balance:.2f} must be positive")
        if peak < balance:
            issues.append(f"peak={peak:.2f} is below balance={balance:.2f}")

        print("QNA HEALTH")
        print(f"  trading_enabled: {self.trading_enabled}")
        print(f"  balance: ${balance:.2f}")
        print(f"  peak: ${peak:.2f}")
        print(f"  drawdown: {dd:.2%}")
        print(f"  open_positions: {open_pos}/{MAX_POSITIONS_TOTAL}")
        if issues:
            print("  status: NOT_READY")
            for issue in issues:
                print(f"  issue: {issue}")
            return 1
        print("  status: READY")
        return 0

    def status(self):
        if not self.prices:
            self.prices = self.data.get_all_prices()
            if not self.prices:
                self.prices = self.price_provider.get_all_prices()
        running = self.is_running()
        balance = self.risk.get_balance()
        cur = self.db.execute("SELECT value FROM portfolio WHERE key='total_trades'")
        total = cur.fetchone()[0]
        cur = self.db.execute("SELECT value FROM portfolio WHERE key='winning_trades'")
        wins = cur.fetchone()[0]
        open_pos = self.risk.get_open_position_count()
        dd = self.risk.get_drawdown()
        win_rate = (wins / total * 100) if total > 0 else 0
        portfolio_value = balance
        asset_pnl = self._calc_asset_pnl()
        for sym in ASSET_SYMBOLS:
            pos = self._get_open_position(sym)
            price = self.prices.get(sym, 0)
            if pos and price > 0:
                portfolio_value += (pos["quantity"] - pos["exited_qty"]) * price

        print("QUANT NANGGROE — BEAST MODE")
        print(f"  Running: {running}")
        print(f"  Data Providers: {repr(self.data)}")
        print(f"  Numpy Strategies: {list(self.np_strategies.keys())}")
        print(f"  Assets: {len(ASSETS)}")
        print(f"  Balance: ${balance:.2f}")
        print(f"  Portfolio Value: ${portfolio_value:.2f}")
        print(f"  Total PnL: ${portfolio_value - 10000:.2f}")
        print(f"  Total Trades: {total}")
        print(f"  Win Rate: {win_rate:.1f}%")
        print(f"  Drawdown: {dd:.2%}")
        print(f"  Open Positions: {open_pos}")
        print(f"  Cycles: {self.cycle_count}")
        print(f"  Errors: {self.total_errors}")
        print(f"  Per-Asset PnL: {asset_pnl}")
        sharpe = self.perf.get_sharpe()
        vol = self.perf.get_volatility()
        print(f"  Sharpe (ann.): {sharpe:.2f}")
        print(f"  Volatility (ann.): {vol:.2%}")

    def _get_routing_status(self) -> dict:
        try:
            try:
                from quant_nanggroe.warp_provider import status as warp_status
            except ImportError:
                warp_status = lambda: {"connected": False, "registered": False, "account_type": "none"}
            ws = warp_status()
        except Exception:
            ws = {"connected": False, "registered": False, "account_type": "none"}
        return {
            "warp": ws,
            "ssh_relay": True,
            "direct": False,
        }

    def dashboard(self):
        if not self.prices:
            self.prices = self.data.get_all_prices()
            if not self.prices:
                self.prices = self.price_provider.get_all_prices()
        balance = self.risk.get_balance()
        cur = self.db.execute("SELECT value FROM portfolio WHERE key='total_trades'")
        total = cur.fetchone()[0]
        cur = self.db.execute("SELECT value FROM portfolio WHERE key='winning_trades'")
        wins = cur.fetchone()[0]
        dd = self.risk.get_drawdown()
        win_rate = (wins / total * 100) if total > 0 else 0
        portfolio_value = balance
        asset_pnl = self._calc_asset_pnl()
        for sym in ASSET_SYMBOLS:
            pos = self._get_open_position(sym)
            price = self.prices.get(sym, 0)
            if pos and price > 0:
                portfolio_value += (pos["quantity"] - pos["exited_qty"]) * price

        cur = self.db.execute(
            "SELECT symbol, side, entry_price, exit_price, pnl, strategy "
            "FROM trades ORDER BY id DESC LIMIT 10"
        )
        trades = [{"symbol": r[0], "side": r[1], "entry": r[2], "exit": r[3],
                    "pnl": r[4], "strategy": r[5]} for r in cur.fetchall()]

        cur = self.db.execute(
            "SELECT strategy, signal, price, timestamp FROM signals ORDER BY id DESC LIMIT 10"
        )
        signals = [{"strategy": r[0], "signal": r[1], "price": r[2], "time": r[3]}
                   for r in cur.fetchall()]

        allocation_data = []
        for a in ASSETS:
            sym = a["symbol"]
            pos = self._get_open_position(sym)
            price = self.prices.get(sym, 0)
            val = (pos["quantity"] - pos["exited_qty"]) * price if pos and price > 0 else 0
            allocation_data.append({
                "symbol": sym,
                "target": a["allocation"],
                "current": round(val / portfolio_value, 4) if portfolio_value > 0 else 0,
                "value": round(val, 2),
            })

        strategy_perf = self.perf.get_strategy_stats()
        sharpe = self.perf.get_sharpe()
        vol = self.perf.get_volatility()

        open_positions = []
        for sym in ASSET_SYMBOLS:
            pos = self._get_open_position(sym)
            if pos:
                price = self.prices.get(sym, 0)
                unrealized = (price - pos["entry_price"]) * (pos["quantity"] - pos["exited_qty"])
                open_positions.append({
                    "symbol": sym, "entry": pos["entry_price"],
                    "current": price, "qty": pos["quantity"] - pos["exited_qty"],
                    "pnl": round(unrealized, 2), "strategy": pos["strategy"],
                })

        return {
            "version": "2.0-beast",
            "status": "running" if self.is_running() else "stopped",
            "data_providers": repr(self.data),
            "numpy_strategies": list(self.np_strategies.keys()),
            "assets_count": len(ASSETS),
            "balance": balance,
            "portfolio_value": round(portfolio_value, 2),
            "total_pnl": round(portfolio_value - 10000, 2),
            "total_trades": total,
            "win_rate": f"{win_rate:.1f}%",
            "drawdown": f"{dd:.2%}",
            "sharpe_ratio": round(sharpe, 2),
            "volatility": round(vol, 4),
            "cycle_count": self.cycle_count,
            "errors": self.total_errors,
            "current_prices": {sym: round(p, 2) for sym, p in self.prices.items()},
            "asset_pnl": asset_pnl,
            "allocation": allocation_data,
            "strategy_performance": strategy_perf,
            "open_positions": open_positions,
            "recent_trades": trades,
            "recent_signals": signals,
            "routing": self._get_routing_status(),
        }


# Entry point archived — use qna.py instead.
# Previous standalone main() moved to .bak/live_engine_main.py.archive
