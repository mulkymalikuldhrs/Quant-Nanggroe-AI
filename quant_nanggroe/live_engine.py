#!/usr/bin/env python3
"""
QUANT NANGGROE — Autonomous Multi-Asset Hedge Fund Engine
==========================================================
Upgraded: multi-asset (BTC, ETH, SOL, BNB), 5 strategies, Kelly sizing,
trailing stops, take-profit, performance analytics, dashboard, auto-restart.

Usage:
  python3 live_engine.py [start|stop|restart|status|dashboard]
"""

import os, sys, json, time, random, math, logging, sqlite3
import urllib.request, urllib.error, ssl
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Tuple

QNA_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = QNA_DIR / "data"
LOG_DIR = QNA_DIR / "logs"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] QNA %(message)s",
    handlers=[
        logging.FileHandler(str(LOG_DIR / "live-engine.log")),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("QNA-Live")

ASSETS = [
    {"symbol": "BTCUSDT",    "coin_gecko_id": "bitcoin",      "allocation": 0.40},
    {"symbol": "ETHUSDT",    "coin_gecko_id": "ethereum",     "allocation": 0.25},
    {"symbol": "SOLUSDT",    "coin_gecko_id": "solana",       "allocation": 0.20},
    {"symbol": "BNBUSDT",    "coin_gecko_id": "binancecoin",  "allocation": 0.15},
]
ASSET_SYMBOLS = [a["symbol"] for a in ASSETS]
CG_IDS = ",".join(a["coin_gecko_id"] for a in ASSETS)

TP_TARGETS = {
    "SMC": 0.05,
    "Momentum": 0.08,
    "MeanReversion": 0.04,
    "Grid": 0.03,
    "TrendStrength": 0.06,
}
TRAILING_STOP_PCT = 0.03
REBALANCE_THRESHOLD = 0.05
MAX_DRAWDOWN = 0.15
MAX_POSITION_PCT = 0.25
MAX_POSITIONS_TOTAL = 3
HEARTBEAT_INTERVAL = 10
CLEANUP_INTERVAL = 10
REPORT_INTERVAL = 5

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
    db.execute("INSERT OR IGNORE INTO portfolio VALUES ('balance', 10000.0)")
    db.execute("INSERT OR IGNORE INTO portfolio VALUES ('peak', 10000.0)")
    db.execute("INSERT OR IGNORE INTO portfolio VALUES ('total_trades', 0)")
    db.execute("INSERT OR IGNORE INTO portfolio VALUES ('winning_trades', 0)")
    for s in ["SMC", "Momentum", "MeanReversion", "Grid", "TrendStrength"]:
        db.execute("INSERT OR IGNORE INTO strategy_stats VALUES (?,0,0,0,0,0,0,0.25)", (s,))
    db.commit()
    return db

# ─── Exchange Connector ────────────────────────────────────────────

class BinanceConnector:
    def __init__(self):
        pass

    def _request(self, url: str, timeout: int = 10, headers: Dict = None):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "QNA/1.0")
        if headers:
            for k, v in headers.items():
                req.add_header(k, v)
        return urllib.request.urlopen(req, timeout=timeout, context=ctx)

    def get_all_prices(self) -> Dict[str, float]:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={CG_IDS}&vs_currencies=usd"
        try:
            with self._request(url) as resp:
                data = json.loads(resp.read())
                result = {}
                for a in ASSETS:
                    cg = data.get(a["coin_gecko_id"], {})
                    if "usd" in cg:
                        result[a["symbol"]] = float(cg["usd"])
                return result
        except Exception as e:
            log.warning(f"CoinGecko price fetch error: {e}")
            return {}

    def get_klines(self, symbol: str, coin_gecko_id: str, interval: str = "1m", limit: int = 100) -> List[Dict]:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        try:
            with self._request(url) as resp:
                data = json.loads(resp.read())
                if isinstance(data, list) and len(data) > 0:
                    return [{
                        "timestamp": int(k[0]) // 1000,
                        "open": float(k[1]), "high": float(k[2]),
                        "low": float(k[3]), "close": float(k[4]),
                        "volume": float(k[5]),
                    } for k in data]
        except Exception:
            pass
        return self._synthetic_candles(coin_gecko_id, limit)

    def _synthetic_candles(self, coin_gecko_id: str, limit: int) -> List[Dict]:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_gecko_id}&vs_currencies=usd"
        try:
            with self._request(url) as resp:
                data = json.loads(resp.read())
                price = float(data[coin_gecko_id]["usd"])
        except Exception:
            return []
        now = int(time.time())
        candles = []
        for i in range(min(limit, 60)):
            ts = now - (limit - i) * 60
            base = price * (1 + random.uniform(-0.002, 0.002))
            candles.append({
                "timestamp": ts, "open": base, "high": base * 1.001,
                "low": base * 0.999, "close": base, "volume": random.uniform(5, 50)
            })
        return candles

# ─── Strategies ────────────────────────────────────────────────────

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


# ─── Risk Manager ──────────────────────────────────────────────────

class RiskManager:
    def __init__(self, db):
        self.db = db

    def get_balance(self) -> float:
        cur = self.db.execute("SELECT value FROM portfolio WHERE key='balance'")
        return cur.fetchone()[0]

    def get_peak(self) -> float:
        cur = self.db.execute("SELECT value FROM portfolio WHERE key='peak'")
        return cur.fetchone()[0]

    def get_drawdown(self) -> float:
        peak = self.get_peak()
        balance = self.get_balance()
        return (peak - balance) / peak if peak > 0 else 0

    def get_open_position_count(self) -> int:
        cur = self.db.execute("SELECT COUNT(*) FROM positions WHERE status='open'")
        return cur.fetchone()[0]

    def can_trade(self) -> Tuple[bool, str]:
        dd = self.get_drawdown()
        if dd > MAX_DRAWDOWN:
            return False, f"Drawdown {dd:.1%} exceeds {MAX_DRAWDOWN:.1%}"
        open_count = self.get_open_position_count()
        if open_count >= MAX_POSITIONS_TOTAL:
            return False, f"Max positions ({MAX_POSITIONS_TOTAL}) reached"
        return True, "ok"

    def position_size(self, price: float, kelly: float = 1.0) -> float:
        balance = self.get_balance()
        return (balance * MAX_POSITION_PCT * kelly) / price

    def update_peak(self):
        balance = self.get_balance()
        peak = self.get_peak()
        if balance > peak:
            self.db.execute("UPDATE portfolio SET value=? WHERE key='peak'", (balance,))
            self.db.commit()


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
        self.connector = BinanceConnector()
        self.risk = RiskManager(self.db)
        self.perf = PerformanceTracker(self.db)
        self.running = False
        self.pid_file = DATA_DIR / "qna.pid"
        self.cycle_count = 0
        self.total_errors = 0
        self.last_cleanup = 0
        self.last_heartbeat = 0
        self.last_report = 0
        self.prices: Dict[str, float] = {}
        self.asset_candles: Dict[str, List[Dict]] = {}
        self.strategies: Dict[str, Strategy] = {
            "SMC": SMCStrategy(),
            "Momentum": MomentumStrategy(),
            "MeanReversion": MeanReversionStrategy(),
            "Grid": GridTradingStrategy(),
            "Trend": TrendStrengthStrategy(),
        }
        self._load_state()
        self._init_auto_aware()

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

    def _open_position(self, symbol: str, price: float, qty: float, strategy: str):
        now = datetime.now().isoformat()
        tp_target = TP_TARGETS.get(strategy, 0.05)
        self.db.execute(
            "INSERT INTO positions (symbol, side, entry_price, quantity, entry_time, "
            "highest_since_entry, strategy, take_profit) VALUES (?,?,?,?,?,?,?,?)",
            (symbol, "long", price, qty, now, price, strategy, price * (1 + tp_target))
        )
        self.db.commit()
        log.info(f"BUY {symbol} {qty:.4f} @ {price:.2f} ({strategy})")

    def _close_position(self, pos: dict, price: float, reason: str = "signal"):
        remaining = pos["quantity"] - pos["exited_qty"]
        if remaining <= 0:
            return
        pnl = (price - pos["entry_price"]) * remaining
        balance = self.risk.get_balance()
        new_balance = balance + pnl
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
        candles = self.asset_candles.get(symbol, [])
        if len(candles) < 20:
            return

        regime = self.strategies["Trend"].analyze(candles)
        active_strategies = []
        if regime == "trending":
            active_strategies = [self.strategies["SMC"], self.strategies["Momentum"]]
        elif regime == "ranging":
            active_strategies = [self.strategies["SMC"], self.strategies["MeanReversion"],
                                 self.strategies["Grid"]]
        else:
            active_strategies = list(self.strategies.values())

        pos = self._get_open_position(symbol)
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
            ok, msg = self.risk.can_trade()
            if not ok:
                continue
            if signal == "buy" and not pos:
                kelly = self._get_kelly(strategy.name)
                qty = self.risk.position_size(current_price, kelly)
                self._open_position(symbol, current_price, qty, strategy.name)
                pos = self._get_open_position(symbol)
            elif signal == "sell" and pos:
                self._close_position(pos, current_price, strategy.name)
                pos = None

    def execute_cycle(self):
        self.prices = self.connector.get_all_prices()
        if not self.prices:
            log.warning("No prices available from CoinGecko")
            return

        for a in ASSETS:
            sym = a["symbol"]
            cg_id = a["coin_gecko_id"]
            candles = self.connector.get_klines(sym, cg_id, "1m", 60)
            if candles:
                for c in candles:
                    self.db.execute(
                        "INSERT OR REPLACE INTO candles VALUES (?,?,?,?,?,?,?)",
                        (sym, c["timestamp"], c["open"], c["high"],
                         c["low"], c["close"], c["volume"])
                    )
                self.db.commit()
                self.asset_candles[sym] = candles

        for sym in ASSET_SYMBOLS:
            price = self.prices.get(sym)
            if not price:
                continue
            self._execute_signals(sym, price)

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

    def _heartbeat(self, balance: float, portfolio_value: float):
        dd = self.risk.get_drawdown()
        open_pos = self.risk.get_open_position_count()
        log.info(
            f"HEARTBEAT | Cycle {self.cycle_count} | Balance ${balance:.2f} | "
            f"Portfolio ${portfolio_value:.2f} | Drawdown {dd:.2%} | "
            f"Open positions {open_pos} | Errors {self.total_errors}"
        )

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
        if self.pid_file.exists():
            try:
                pid = int(self.pid_file.read_text().strip())
                os.kill(pid, 0)
                log.warning(f"Engine already running (PID: {pid})")
                return
            except (OSError, ValueError):
                pass

        self.pid_file.write_text(str(os.getpid()))
        self.running = True
        log.info("QUANT NANGGROE — MULTI-ASSET HEDGE FUND ENGINE STARTED")
        log.info(f"   Balance: ${self.risk.get_balance():.2f}")
        log.info(f"   Assets: {[a['symbol'] for a in ASSETS]}")
        log.info(f"   Allocations: { {a['symbol']: f'{a['allocation']*100:.0f}%' for a in ASSETS} }")
        log.info(f"   Strategies: {list(self.strategies.keys())}")
        log.info(f"   Resuming from cycle {self.cycle_count}")

        try:
            while self.running:
                self.cycle_count += 1
                log.info(f"--- Cycle {self.cycle_count} ---")
                try:
                    self.execute_cycle()
                except Exception as e:
                    self.total_errors += 1
                    log.error(f"Cycle error: {e}")
                time.sleep(60)
        except KeyboardInterrupt:
            self.stop()
        except Exception as e:
            log.error(f"Engine fatal error: {e}")
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

    def status(self):
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

        print("QUANT NANGGROE — Status")
        print(f"  Running: {running}")
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

    def dashboard(self):
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
            "status": "running" if self.is_running() else "stopped",
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
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Quant Nanggroe Multi-Asset Hedge Fund Engine")
    parser.add_argument("action", choices=["start", "stop", "restart", "status", "dashboard"])
    args = parser.parse_args()

    engine = LiveEngine()

    if args.action == "start":
        engine.start()
    elif args.action == "stop":
        engine.stop()
    elif args.action == "restart":
        engine.stop()
        time.sleep(2)
        engine.start()
    elif args.action == "status":
        engine.status()
    elif args.action == "dashboard":
        print(json.dumps(engine.dashboard(), indent=2))


if __name__ == "__main__":
    main()
