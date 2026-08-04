#!/usr/bin/env python3
"""
QNA AUTONOMOUS TRADING CYCLE (LEGACY / ORPHAN)
===============================================
DEPRECATED ENTRY POINT — NOT WIRED INTO THE RUNNING SYSTEM.
The live autonomous loop is started by `start_default_scheduler()`
(quant_nanggroe/engine/scheduler.py), which drives `autonomous_self_loop.py`
+ `engine/agentic/autonomous.py`. This module is retained ONLY because
`tests/test_g1_g3_hardening.py` exercises its journal/PositionManager logic.
Do NOT start new trading via this file. See docs/Rencana.md (G3).

Main loop that runs continuously:
1. Fetch market data
2. Generate signals from ALL registered strategies
3. Filter through risk guard (fail-closed)
4. Execute via purified engine (REAL-ONLY MT5, no paper)
5. Manage open positions (trailing, partial TP, stop loss)
6. Record performance, update Kelly fractions
7. Sleep until next cycle

Run: python autonomous_cycle.py


Prevents duplicate order execution when the cycle is accidentally started
twice (e.g. via different venvs / nohup / env). Lock auto-releases on
process death — no stale-lock issue.
"""

import os
import sys
import time
import logging
import signal as sig
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

# Load .env (repo root) so QNA_MT5_LOGIN / QNA_LIVE_TRADING / QNAI_* are
# available even when this module is run directly (not via app.py/launch.bat).
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(_env_path, override=False)
except Exception:  # dotenv optional
    pass

log = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# PYTHONPATH — CRITICAL
# ──────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "quant_nanggroe"))
sys.path.insert(0, str(REPO_ROOT))  # for `import quant_nanggroe.*` (package root)

# ──────────────────────────────────────────────────────────────
# SINGLETON GUARD — one instance per machine (cross-process safety)
# ──────────────────────────────────────────────────────────────
_LOCK_FD: Optional[int] = None


def _acquire_singleton_lock() -> None:
    """Acquire an exclusive OS file lock; exit if another instance holds it.

    On Windows uses msvcrt.locking; on POSIX uses fcntl.flock. The lock is
    released automatically by the OS when the process dies (kill, crash,
    normal exit), so a stale lock file never blocks a restart.
    """
    global _LOCK_FD
    lock_path = REPO_ROOT / ".autonomous_cycle.lock"
    try:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o644)
        # msvcrt.locking cannot lock beyond EOF — ensure ≥1 byte exists
        if os.fstat(fd).st_size == 0:
            os.write(fd, b"0")
        if os.name == "nt":
            import msvcrt
            os.lseek(fd, 0, os.SEEK_SET)
            try:
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            except OSError:
                os.close(fd)
                sys.exit(
                    f"ERROR: Another autonomous_cycle instance is already running "
                    f"(lock: {lock_path}). Kill it first, then retry."
                )
        else:
            import fcntl
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                os.close(fd)
                sys.exit(
                    f"ERROR: Another autonomous_cycle instance is already running "
                    f"(lock: {lock_path}). Kill it first, then retry."
                )
        _LOCK_FD = fd  # keep fd alive for process lifetime
    except SystemExit:
        raise
    except Exception as e:  # fail-open only on lock infra errors (not duplicate)
        log.warning("Singleton lock unavailable (%s) — continuing without lock", e)


# ⚠️ EARLY SINGLETON LOCK — must run BEFORE heavy imports (engine, MT5) to
# close the startup race window. Two processes started together would both
# spend 30-90s importing before main() runs; locking here guarantees the
# second process exits before it ever reaches the trading loop.
if __name__ == "__main__":
    _acquire_singleton_lock()


# ──────────────────────────────────────────────────────────────
# IMPORTS
# ──────────────────────────────────────────────────────────────
from engine_production_bridge_purified import (
    PurifiedEngine, Signal, RiskGuard, MT5Adapter
)
from trade_journal import TradeJournal, resolve_conflicts

# Failure-alert bot (synchronous — safe to call from the main loop / handlers)
from agents.telegram_bot import TelegramSignalBot
_alert_bot = TelegramSignalBot()

# MT5 auto-path: ensure native plugin is loadable BEFORE importing MetaTrader5
try:
    from utils.mt5_launcher import ensure_mt5_env, detect_mt5
    _mt5_ok = ensure_mt5_env()
    if _mt5_ok:
        log.info("MT5 auto-path: terminal found at %s", detect_mt5().get("terminal_path"))
    else:
        log.warning("MT5 auto-path: terminal NOT found — paper mode fallback")
except Exception as _mt5_setup_err:
    log.warning("MT5 auto-path setup skipped: %s", _mt5_setup_err)

# Try to import QNA strategy registry
try:
    from quant_nanggroe.engine.strategies.registry import StrategyRegistry
    QNA_STRATEGIES_AVAILABLE = True
except ImportError:
    QNA_STRATEGIES_AVAILABLE = False

# ──────────────────────────────────────────────────────────────
# LOGGING
# ──────────────────────────────────────────────────────────────
LOG_DIR = REPO_ROOT / "quant_nanggroe" / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "autonomous_cycle.log"),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger("QNA-Autonomous")

# ──────────────────────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────────────────────
class Config:
    # Trading symbols (MT5 format — Valetax broker requires .vx suffix)
    SYMBOLS = ["EURUSD.vx", "GBPUSD.vx", "USDJPY.vx", "BTCUSD.vx", "XAUUSD.vx"]
    
    # Cycle timing
    CYCLE_INTERVAL_SEC = 60          # 1 minute between cycles
    DATA_FETCH_INTERVAL = 300        # 5 min for market data refresh
    
    # Risk parameters (from constants)
    MAX_DAILY_LOSS_PCT = 0.03        # 3% daily loss limit
    MAX_DRAWDOWN_PCT = 0.15          # 15% max drawdown
    MAX_POSITIONS_PER_SYMBOL = 1
    MAX_TOTAL_POSITIONS = 5
    DEFAULT_KELLY = 0.25
    MIN_CONFIDENCE = 0.5             # Min signal confidence to trade (2026-08-04: 0.6→0.5 per user GO — most strategies hardcode 0.5-0.55)
    
    # Position management
    TRAILING_STOP_PCT = 0.005        # 0.5% trailing
    PARTIAL_TP_PCT = 0.5             # Close 50% at first TP
    PARTIAL_TP_R_MULT = 1.0          # First TP at 1R
    FULL_TP_R_MULT = 2.5             # Full TP at 2.5R
    
    # MT5
    MT5_MAGIC = 20260729


CONFIG = Config()

# ──────────────────────────────────────────────────────────────
# MARKET DATA PROVIDER (uses MT5 or falls back to synthetic)
# ──────────────────────────────────────────────────────────────
class MarketData:
    def __init__(self, mt5_adapter: Optional[MT5Adapter] = None):
        self.mt5 = mt5_adapter
        self._cache: Dict[str, Dict] = {}
        self._last_fetch = 0
    
    def get_tick(self, symbol: str) -> Optional[Dict]:
        """Get current bid/ask for symbol from LIVE MT5 only (no synthetic fallback)."""
        if self.mt5 and self.mt5._initialized:
            try:
                import MetaTrader5 as mt5_mod
                tick = mt5_mod.symbol_info_tick(symbol)
                if tick:
                    return {"bid": tick.bid, "ask": tick.ask, "time": tick.time}
            except Exception as e:
                log.error(f"MT5 tick failed for {symbol}: {e}", exc_info=True)
        # HARD GATE: no synthetic/paper price — real data only
        log.error(f"MarketData: no LIVE tick for {symbol} (MT5 not connected) — REAL-ONLY mode")
        return None
    
    def get_candles(self, symbol: str, timeframe: str = "M1", count: int = 100) -> List[Dict]:
        """Get recent candles for strategy calculation"""
        if self.mt5 and self.mt5._initialized:
            try:
                import MetaTrader5 as mt5_mod
                tf_map = {"M1": mt5_mod.TIMEFRAME_M1, "M5": mt5_mod.TIMEFRAME_M5, 
                          "M15": mt5_mod.TIMEFRAME_M15, "H1": mt5_mod.TIMEFRAME_H1}
                rates = mt5_mod.copy_rates_from_pos(symbol, tf_map.get(timeframe, mt5_mod.TIMEFRAME_M1), 0, count)
                if rates is not None and len(rates) > 0:
                    # Canonical key = "timestamp" (engine/data/quality.py checks it
                    # for staleness/gap detection); keep "time" for legacy callers.
                    return [{
                        "timestamp": r[0], "time": r[0],
                        "open": r[1], "high": r[2], "low": r[3],
                        "close": r[4], "volume": r[5],
                    } for r in rates]
            except Exception as e:
                log.error(f"MT5 candles failed for {symbol}: {e}", exc_info=True)
        
        # HARD GATE: no synthetic candles — real data only
        log.error(f"MarketData: no LIVE candles for {symbol} (MT5 not connected) — REAL-ONLY mode")
        return []


# ──────────────────────────────────────────────────────────────
# STRATEGY SIGNAL GENERATOR
# ──────────────────────────────────────────────────────────────
class StrategySignalGenerator:
    """Generates signals from all registered QNA strategies"""
    
    def __init__(self, market_data: MarketData):
        self.market_data = market_data
        self.strategies = {}
        self._load_strategies()
    
    def _load_strategies(self):
        """Load all available strategies from QNA registry"""
        if not QNA_STRATEGIES_AVAILABLE:
            log.warning("QNA strategy registry not available — using built-in strategies")
            self._load_builtin_strategies()
            return
        
        try:
            # Load from StrategyRegistry (canonical source)
            from quant_nanggroe.engine.strategies import create_strategy
            for name in StrategyRegistry.list_strategies():
                try:
                    strat = create_strategy(name)
                    if strat is not None:
                        self.strategies[name] = strat
                        log.info(f"Loaded strategy: {name}")
                except Exception as e:
                    log.debug(f"Failed to load {name}: {e}")
            
            log.info(f"Total strategies loaded: {len(self.strategies)}")
        except Exception as e:
            log.warning(f"Strategy registry load failed: {e} — using built-in")
            self._load_builtin_strategies()
    
    def _load_builtin_strategies(self):
        """Fallback built-in strategies"""
        self.strategies = {
            "SMC": SMCSignalStrategy(),
            "Momentum": MomentumSignalStrategy(),
            "MeanReversion": MeanReversionSignalStrategy(),
            "TrendFollow": TrendFollowSignalStrategy(),
        }
        log.info(f"Built-in strategies loaded: {list(self.strategies.keys())}")
    
    def generate_signals(self, symbol: str, current_price: float) -> List[Signal]:
        """Generate signals from all strategies for a symbol"""
        signals = []
        candles = self.market_data.get_candles(symbol, "M15", 200)
        
        if len(candles) < 50:
            return signals
        
        # ATR for volatility-aware SL/TP (replaces hardcoded ±0.5%/±1%)
        from quant_nanggroe.risk_levels import compute_atr, strategy_sl_tp
        atr = compute_atr(candles, period=14)

        # GAP M1-WIRE: attach QuantScience features to each candle (non-destructive,
        # fail-safe). Strategies can read candle["features"]; unaware strategies unaffected.
        from quant_nanggroe.engine.factors.pipeline import enrich_candles
        try:
            candles = enrich_candles(candles)
        except Exception as fe:
            log.warning("M1-WIRE: feature enrichment skipped (fail-safe): %s", fe)

        # M1-WIRE FIX (2026-08-04, fangbot): build OHLCV DataFrame once for
        # registry strategies (they expect pandas, not list[dict]).
        _candles_df = None
        try:
            import pandas as _pd
            _candles_df = _pd.DataFrame(candles)
        except Exception:
            _candles_df = None

        for name, strategy in self.strategies.items():
            try:
                # G4 FIX: registry strategies implement generate_signal() (returns
                # StrategySignal with .direction/.confidence/.stop_loss/.take_profit),
                # built-in strategies implement analyze() (returns "buy"/"sell"/None).
                # Previously only analyze() was called → registry strategies raised
                # AttributeError (swallowed) → 81 strategies NEVER produced signals.
                #
                # M1-WIRE FIX (2026-08-04, fangbot): registry strategies (RSI,
                # trend_follow, dhaher_system, …) expect a pandas OHLCV DataFrame,
                # but the live path passed a list[dict] → every strategy answered
                # "Insufficient data" / "Unsupported data format" → ZERO signals
                # ever. Convert once; builtin strategies keep list[dict].
                is_builtin = isinstance(strategy, BaseSignalStrategy)
                strategy_input = candles
                if not is_builtin:
                    try:
                        if _candles_df is None:
                            raise RuntimeError("no df")
                        strategy_input = _candles_df
                    except Exception:
                        strategy_input = candles
                signal = None
                conf = 0.5
                sl_hint = None
                tp_hint = None
                try:
                    # R10 FIX (2026-08-04, user GO): feed real multi-timeframe candles
                    # to MultiTimeframeStrategy so HTF/MTF/LTF windows span H1/M15/M5.
                    if getattr(type(strategy), "__name__", "") == "MultiTimeframeStrategy":
                        try:
                            _h1 = self.market_data.get_candles(symbol, "H1", 200)
                            _m5 = self.market_data.get_candles(symbol, "M5", 200)
                        except Exception:
                            _h1 = _m5 = None
                        _mtf_kwargs = {}
                        if _h1:
                            _mtf_kwargs["timeframes"] = {
                                "H1": _h1, "M15": strategy_input, "M5": _m5 or strategy_input,
                            }
                        raw = strategy.generate_signal(strategy_input, **_mtf_kwargs)
                    else:
                        raw = strategy.generate_signal(strategy_input)
                    if raw is not None:
                        if hasattr(raw, "direction"):
                            # StrategySignal / canonical object
                            dir_str = getattr(raw, "direction", None)
                            side = str(dir_str.value if hasattr(dir_str, "value") else dir_str).lower()
                            if side in ("buy", "sell"):
                                signal = side
                                conf = float(getattr(raw, "confidence", 0.5) or 0.5)
                                sl_hint = getattr(raw, "stop_loss", None)
                                tp_hint = getattr(raw, "take_profit", None)
                        elif isinstance(raw, str):
                            side = raw.lower()
                            if side in ("buy", "sell"):
                                signal = side
                                conf = float(getattr(strategy, "last_confidence", 0.5) or 0.5)
                except (AttributeError, NotImplementedError, TypeError):
                    signal = None
                if signal is None:
                    try:
                        raw = strategy.analyze(candles, current_price)
                        if raw is not None:
                            side = str(raw).lower()
                            if side in ("buy", "sell"):
                                signal = side
                                conf = float(getattr(strategy, "last_confidence", 0.5) or 0.5)
                    except (AttributeError, NotImplementedError, TypeError):
                        signal = None

                if signal:
                    # Broker min stop distance (trade_stops_level)
                    min_stop_points = 0.0
                    point_size = 0.00001 if "JPY" not in symbol else 0.001
                    try:
                        import MetaTrader5 as mt5
                        info = mt5.symbol_info(symbol)
                        if info:
                            min_stop_points = getattr(info, "trade_stops_level", 0) or 0
                            # G5 FIX: real point from broker (was hardcoded 0.00001 →
                            # XAUUSD.vx (0.01) / BTCUSD.vx (1.0) clamps were 100–10000x wrong)
                            point_size = float(getattr(info, "point", point_size) or point_size)
                    except Exception:
                        pass
                    levels = strategy_sl_tp(symbol, signal, current_price, atr, candles,
                                            min_stop_points, point_size)
                    # Strategy-provided SL/TP win over ATR-derived (G4)
                    if sl_hint and sl_hint > 0:
                        levels["sl"] = sl_hint
                    if tp_hint and tp_hint > 0:
                        levels["tp"] = tp_hint
                    sig = Signal(
                        symbol=symbol,
                        side=signal,
                        confidence=conf,
                        strategy=name,
                        price=current_price,
                        stop_loss=levels["sl"],
                        take_profit=levels["tp"],
                    )
                    signals.append(sig)
            except Exception as e:
                log.debug(f"Strategy {name} failed for {symbol}: {e}")
        
        return signals


# ──────────────────────────────────────────────────────────────
# BUILT-IN STRATEGY IMPLEMENTATIONS
# ──────────────────────────────────────────────────────────────
class BaseSignalStrategy:
    def __init__(self):
        self.last_confidence = 0.5
    
    def analyze(self, candles: List[Dict], current_price: float) -> Optional[str]:
        raise NotImplementedError


class SMCSignalStrategy(BaseSignalStrategy):
    """Smart Money Concepts - Order Blocks, FVG, Liquidity Sweeps"""
    def analyze(self, candles: List[Dict], current_price: float) -> Optional[str]:
        if len(candles) < 50:
            return None
        
        # Simple SMC: look for BOS (Break of Structure) + FVG
        closes = [c["close"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        
        # Recent swing high/low
        recent_high = max(highs[-20:])
        recent_low = min(lows[-20:])
        prev_high = max(highs[-40:-20])
        prev_low = min(lows[-40:-20])
        
        # BOS Up
        if closes[-1] > recent_high and recent_high > prev_high:
            self.last_confidence = 0.75
            return "buy"
        # BOS Down
        if closes[-1] < recent_low and recent_low < prev_low:
            self.last_confidence = 0.75
            return "sell"
        
        return None


class MomentumSignalStrategy(BaseSignalStrategy):
    """Momentum - RSI + MACD trend following"""
    def analyze(self, candles: List[Dict], current_price: float) -> Optional[str]:
        if len(candles) < 30:
            return None
        
        closes = [c["close"] for c in candles]
        
        # Simple RSI
        gains = []
        losses = []
        for i in range(1, 15):
            diff = closes[-i] - closes[-i-1]
            if diff > 0:
                gains.append(diff)
            else:
                losses.append(abs(diff))
        
        avg_gain = sum(gains) / len(gains) if gains else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        rs = avg_gain / avg_loss if avg_loss > 0 else 100
        rsi = 100 - (100 / (1 + rs))
        
        # Trend: price vs MA20
        ma20 = sum(closes[-20:]) / 20
        trend_up = current_price > ma20
        
        if rsi < 30 and trend_up:
            self.last_confidence = 0.7
            return "buy"
        if rsi > 70 and not trend_up:
            self.last_confidence = 0.7
            return "sell"
        
        return None


class MeanReversionSignalStrategy(BaseSignalStrategy):
    """Mean Reversion - Bollinger Bands + RSI"""
    def analyze(self, candles: List[Dict], current_price: float) -> Optional[str]:
        if len(candles) < 30:
            return None
        
        closes = [c["close"] for c in candles[-20:]]
        ma = sum(closes) / len(closes)
        std = (sum((c - ma)**2 for c in closes) / len(closes))**0.5
        
        upper = ma + 2 * std
        lower = ma - 2 * std
        
        if current_price <= lower:
            self.last_confidence = 0.65
            return "buy"
        if current_price >= upper:
            self.last_confidence = 0.65
            return "sell"
        
        return None


class TrendFollowSignalStrategy(BaseSignalStrategy):
    """Trend Following - EMA crossover"""
    def analyze(self, candles: List[Dict], current_price: float) -> Optional[str]:
        if len(candles) < 50:
            return None
        
        closes = [c["close"] for c in candles]
        
        # EMA 9 and EMA 21
        ema9 = self._ema(closes, 9)
        ema21 = self._ema(closes, 21)
        
        prev_ema9 = self._ema(closes[:-1], 9)
        prev_ema21 = self._ema(closes[:-1], 21)
        
        # Golden cross
        if ema9 > ema21 and prev_ema9 <= prev_ema21:
            self.last_confidence = 0.7
            return "buy"
        # Death cross
        if ema9 < ema21 and prev_ema9 >= prev_ema21:
            self.last_confidence = 0.7
            return "sell"
        
        return None
    
    def _ema(self, data: List[float], period: int) -> float:
        if len(data) < period:
            return sum(data) / len(data)
        k = 2 / (period + 1)
        ema = data[-period]
        for price in data[-period+1:]:
            ema = price * k + ema * (1 - k)
        return ema


# ──────────────────────────────────────────────────────────────
# POSITION MANAGER
# ──────────────────────────────────────────────────────────────
class PositionManager:
    """Manages open positions: trailing stops, partial TP, full TP.
    Records closed trades to TradeJournal for self-eval."""

    def __init__(self, engine: PurifiedEngine, market_data: MarketData, journal=None):
        self.engine = engine
        self.market_data = market_data
        self.journal = journal
        self.positions: Dict[int, Dict] = {}  # ticket -> position info
        self._seen_tickets: set = set()  # track which tickets we've seen open
    
    def reconcile_legacy_positions(self):
        """Boot-step: handle OPEN positions with NO journal record (orphans).

        SAFETY (deep-audit 2026-08-04): force-closing orphans is DESTRUCTIVE on a
        live REAL-ONLY account — it would close the user's MANUAL positions or positions
        opened by another session/bot. Therefore it is OPT-IN: only runs when env
        QNA_RECONCILE_LEGACY=1 is explicitly set. Default (unset) = LOG-ONLY, keep orphans.
        QNA-managed positions (have a journal record) are always kept & managed.
        Returns count closed.
        """
        try:
            import MetaTrader5 as mt5
            positions = mt5.positions_get() or []
        except Exception:
            return 0
        if not positions:
            return 0
        # Default: safe. Only force-close when operator explicitly opts in.
        force_close_enabled = os.environ.get("QNA_RECONCILE_LEGACY", "0") == "1"
        closed = 0
        for pos in positions:
            if self.journal and self.journal.get_open_trade(pos.ticket):
                continue  # QNA-managed position -> keep
            # Orphan position
            if not force_close_enabled:
                log.warning(
                    "LEGACY RECONCILE (SKIPPED, safe-mode): orphan position "
                    "ticket=%d %s %s vol=%s — NOT closed (set QNA_RECONCILE_LEGACY=1 to force-close)",
                    pos.ticket, pos.symbol, "buy" if pos.type == 0 else "sell", pos.volume,
                )
                continue
            side = "buy" if pos.type == 0 else "sell"
            tick = self.market_data.get_tick(pos.symbol)
            price = tick["bid"] if side == "buy" else tick["ask"]
            log.warning(f"LEGACY RECONCILE: closing orphan position "
                        f"ticket={pos.ticket} {pos.symbol} {side} vol={pos.volume}")
            if self._close_position(pos.ticket, pos.symbol, side, pos.volume, price):
                closed += 1
        if closed:
            log.info(f"LEGACY RECONCILE done: {closed} orphan position(s) force-closed")
        return closed

    def update_positions(self):
        """Check all open positions and manage them. Detect closes -> journal."""
        try:
            import MetaTrader5 as mt5
            positions = mt5.positions_get() or []
        except Exception:
            positions = []

        current_tickets = {p.ticket for p in positions}

        # Detect closed positions: seen before but no longer open
        for ticket in list(self._seen_tickets):
            if ticket not in current_tickets:
                self._on_position_closed(ticket)
                self._seen_tickets.discard(ticket)

        for pos in positions:
            self._seen_tickets.add(pos.ticket)
            self._manage_position(pos)
    
    def _on_position_closed(self, ticket: int):
        """Position closed (by TP/SL/manual). Record to journal + self-eval.
        G3-residual FIX: open_rec must be read BEFORE deal-history lookup
        (was used-before-defined NameError on old lines 564/567)."""
        if not self.journal:
            return
        open_rec = self.journal.get_open_trade(ticket)
        if not open_rec:
            return  # not our trade (e.g. manual close of orphan)
        entry_price = open_rec["entry"]
        pnl = 0.0
        exit_price = entry_price
        try:
            import MetaTrader5 as mt5
            from datetime import datetime, timedelta
            deals = mt5.history_deals_get(
                datetime.now() - timedelta(days=30), datetime.now()) or []
            ticket_deals = [d for d in deals if d.position_id == ticket]
            pnl = sum(d.profit for d in ticket_deals)
            close_deals = [d for d in ticket_deals
                           if d.entry == mt5.DEAL_ENTRY_OUT] if hasattr(mt5, "DEAL_ENTRY_OUT") else ticket_deals
            if close_deals:
                vol = sum(abs(d.volume) for d in close_deals) or 1.0
                exit_price = sum(d.price * abs(d.volume) for d in close_deals) / vol
        except Exception as e:
            log.error("MT5 deal-history lookup failed for ticket %d: %s", ticket, e)
        # JOURNAL + RiskGuard PnL feed (G3-core): closes no longer silent.
        self.journal.record_close(ticket, exit_price, pnl)
        self.engine.risk.update_pnl(pnl, pnl > 0)
        if self.performance:
            self.performance.record_trade(
                strategy=open_rec["strategy"], symbol=open_rec["symbol"],
                side=open_rec["side"], entry=entry_price,
                exit=exit_price, volume=0.0, pnl=pnl)
        verdict = self.journal.self_eval()
        for strat, v in verdict.items():
            if v.get("status") == "active" and "kelly" in v:
                self.engine.risk.kelly_cache[strat] = v["kelly"]
                log.info(f"SELF-EVAL {strat}: wr={v['win_rate']} "
                         f"expectancy={v['expectancy']} pnl={v['total_pnl']} "
                         f"kelly={v['kelly']}")
        log.info(f"CLOSED journaled: ticket={ticket} strat={open_rec['strategy']} "
                 f"pnl={pnl:.2f} outcome={'win' if pnl>0 else 'loss'} "
                 f"risk.balance={self.engine.risk.balance:.2f}")

    def _manage_position(self, pos):
        """Apply trailing stop, partial TP, full TP logic"""
        ticket = pos.ticket
        symbol = pos.symbol
        side = "buy" if pos.type == 0 else "sell"
        entry = pos.price_open
        current_sl = pos.sl
        current_tp = pos.tp
        volume = pos.volume
        profit = pos.profit
        
        tick = self.market_data.get_tick(symbol)
        if not tick:
            return
        
        current_price = tick["bid"] if side == "buy" else tick["ask"]
        
        # Calculate R multiple (use ATR-based risk if no SL set)
        try:
            candles = self.market_data.get_candles(symbol, "M15", 30)
            from quant_nanggroe.risk_levels import compute_atr
            atr = compute_atr(candles, period=14) or entry * 0.01
        except Exception:
            atr = entry * 0.01
        risk_per_unit = abs(entry - current_sl) if current_sl > 0 else atr
        if side == "buy":
            r_multiple = (current_price - entry) / risk_per_unit if risk_per_unit > 0 else 0
        else:
            r_multiple = (entry - current_price) / risk_per_unit if risk_per_unit > 0 else 0
        
        # PARTIAL TP at 1R
        if r_multiple >= CONFIG.PARTIAL_TP_R_MULT and ticket not in self.positions.get("partial_done", set()):
            close_vol = volume * CONFIG.PARTIAL_TP_PCT
            self._partial_close(ticket, symbol, side, close_vol, current_price)
            if "partial_done" not in self.positions:
                self.positions["partial_done"] = set()
            self.positions["partial_done"].add(ticket)
            log.info(f"PARTIAL TP: {symbol} {ticket} closed {close_vol} lots at {r_multiple:.2f}R")
        
        # FULL TP at 2.5R
        if r_multiple >= CONFIG.FULL_TP_R_MULT:
            closed = self._close_position(ticket, symbol, side, volume, current_price)
            if closed:
                log.info(f"FULL TP: {symbol} {ticket} closed at {r_multiple:.2f}R")
            else:
                log.info(f"FULL TP: {symbol} {ticket} at {r_multiple:.2f}R — close pending (retcode not DONE; will retry next cycle)")
            return
        
        # BREAKEVEN + TRAILING STOP (G11: structure-based, activates after 1R)
        # Priority: breakeven first (protect capital), then structure trail.
        if r_multiple > 1.0:
            try:
                candles = self.market_data.get_candles(symbol, "M15", 50)
                from quant_nanggroe.risk_levels import compute_atr, trailing_sl_atr, breakeven_sl, trailing_sl_structure
                atr = compute_atr(candles, period=14)
                # 1) Breakeven: after 1R, SL moves to entry so trade can't go red
                new_sl = breakeven_sl(side, entry, current_price, current_sl, activation_r=1.0)
                # 2) Structure trail: only when breakeven already active
                if new_sl == current_sl and current_sl > 0:
                    highs = [c.get("high", 0) for c in candles]
                    lows = [c.get("low", 0) for c in candles]
                    new_sl = trailing_sl_structure(side, entry, current_price, current_sl,
                                                   highs, lows, lookback=20, activation_r=1.0)
                # 3) Fallback: ATR trail if structure returns nothing
                if new_sl == current_sl:
                    new_sl = trailing_sl_atr(side, entry, current_price, current_sl, atr, activation_r=1.0)
            except Exception:
                new_sl = self._calculate_trailing_sl(side, entry, current_price, current_sl)
            if new_sl != current_sl:
                self._modify_sl(ticket, symbol, new_sl)
                log.info(f"TRAIL SL: {symbol} {ticket} SL {current_sl:.5f} -> {new_sl:.5f}")
    
    def _calculate_trailing_sl(self, side: str, entry: float, current: float, current_sl: float) -> float:
        trail_dist = entry * CONFIG.TRAILING_STOP_PCT
        if side == "buy":
            new_sl = current - trail_dist
            return max(new_sl, current_sl) if current_sl > 0 else new_sl
        else:
            new_sl = current + trail_dist
            return min(new_sl, current_sl) if current_sl > 0 else new_sl
    
    def _partial_close(self, ticket: int, symbol: str, side: str, volume: float, price: float):
        try:
            import MetaTrader5 as mt5
            close_type = mt5.ORDER_TYPE_SELL if side == "buy" else mt5.ORDER_TYPE_BUY
            req = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": close_type,
                "position": ticket,
                "price": price,
                "deviation": 10,
                "magic": CONFIG.MT5_MAGIC,
                "comment": "partial_tp",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_FOK,
            }
            mt5.order_send(req)
        except Exception as e:
            log.error(f"Partial close failed: {e}")
    
    def _close_position(self, ticket: int, symbol: str, side: str, volume: float, price: float) -> bool:
        """Close a position. Returns True only when retcode == TRADE_RETCODE_DONE."""
        try:
            import MetaTrader5 as mt5
            close_type = mt5.ORDER_TYPE_SELL if side == "buy" else mt5.ORDER_TYPE_BUY
            req = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": close_type,
                "position": ticket,
                "price": price,
                "deviation": 10,
                "magic": CONFIG.MT5_MAGIC,
                "comment": "full_tp",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_FOK,
            }
            result = mt5.order_send(req)
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                log.info(f"CLOSED position {ticket} {symbol} {side} {volume} lots @ {price}")
                # Record to journal + trigger self-eval
                self._on_position_closed(ticket)
                return True
            else:
                log.error(f"Close failed for {ticket}: retcode={getattr(result, 'retcode', '?')} "
                          f"comment={getattr(result, 'comment', '?')}")
                return False
        except Exception as e:
            log.error(f"Full close failed: {e}")
            return False
    
    def _modify_sl(self, ticket: int, symbol: str, new_sl: float):
        try:
            import MetaTrader5 as mt5
            req = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": symbol,
                "position": ticket,
                "sl": round(new_sl, 5),
                "magic": CONFIG.MT5_MAGIC,
            }
            mt5.order_send(req)
        except Exception as e:
            log.error(f"SL modify failed: {e}")


# ──────────────────────────────────────────────────────────────
# PERFORMANCE TRACKER
# ──────────────────────────────────────────────────────────────
class PerformanceTracker:
    """Tracks strategy performance, updates Kelly fractions"""
    
    def __init__(self, risk_guard: RiskGuard):
        self.risk_guard = risk_guard
        self.strategy_stats: Dict[str, Dict] = {}
    
    def record_trade(self, strategy: str, symbol: str, side: str, 
                     entry: float, exit: float, volume: float, pnl: float):
        if strategy not in self.strategy_stats:
            self.strategy_stats[strategy] = {
                "trades": 0, "wins": 0, "losses": 0,
                "total_pnl": 0.0, "win_pnl": 0.0, "loss_pnl": 0.0
            }
        
        stats = self.strategy_stats[strategy]
        stats["trades"] += 1
        stats["total_pnl"] += pnl
        
        if pnl > 0:
            stats["wins"] += 1
            stats["win_pnl"] += pnl
        else:
            stats["losses"] += 1
            stats["loss_pnl"] += abs(pnl)
        
        # Update Kelly fraction
        if stats["trades"] >= 10:
            win_rate = stats["wins"] / stats["trades"]
            avg_win = stats["win_pnl"] / stats["wins"] if stats["wins"] > 0 else 0
            avg_loss = stats["loss_pnl"] / stats["losses"] if stats["losses"] > 0 else 1
            if avg_loss > 0:
                kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
                kelly = max(0.05, min(0.25, kelly))  # Cap 5%-25%
                # G9 FIX: was _kelly_cache (typo) — RiskGuard attribute is kelly_cache
                self.risk_guard.kelly_cache[strategy] = kelly
                log.info(f"Kelly updated for {strategy}: {kelly:.3f} (wr={win_rate:.2f})")
    
    def get_report(self) -> Dict:
        return {k: v for k, v in self.strategy_stats.items() if v["trades"] > 0}


# ──────────────────────────────────────────────────────────────
# MAIN AUTONOMOUS CYCLE
# ──────────────────────────────────────────────────────────────
class AutonomousCycle:
    def __init__(self):
        self.running = False
        self.engine = None
        self.market_data = None
        self.signal_generator = None
        self.position_manager = None
        self.performance = None
        self.journal = None
        self.cycle_count = 0
        self.last_data_fetch = 0
        self._last_day = None    # G3-reset: track day boundary for reset_daily()
        self._last_week = None    # G3-reset: track week boundary for reset_weekly()
        
        # Signal handling
        sig.signal(sig.SIGINT, self._shutdown)
        sig.signal(sig.SIGTERM, self._shutdown)
    
    def _shutdown(self, signum, frame):
        log.info("Shutdown signal received")
        self.running = False
    
    def initialize(self):
        """Initialize all components"""
        log.info("=" * 60)
        log.info("QNA AUTONOMOUS CYCLE INITIALIZING")
        log.info("=" * 60)

        # G1-deep hardening: check journal schema FIRST, before any network/broker calls.
        # If journal is dead (lock contention, 0-byte DB), fail-closed immediately.
        self.journal = TradeJournal()
        if not self.journal._init_ok or not self.journal.db_healthy():
            log.critical("G1-HARDENING: TradeJournal schema NOT initialized (0 tables / lock contention). Aborting initialize() — fail-closed.")
            raise RuntimeError("TradeJournal schema init failed — refuse to run with dead journal (fail-closed)")

        # 1. Create purified engine
        self.engine = PurifiedEngine(initial_balance=10000.0)
        self.engine.start()
        # GAP F4-WIRE: feed MTM equity into RiskGuard so drawdown is measured from
        # live equity, not balance. Fail-safe: if MT5 down / no equity, falls back
        # to balance (RiskGuard._effective_equity default). No-op when MT5 absent.
        if self.engine.mt5 and getattr(self.engine.mt5, "_initialized", False):
            try:
                self.engine.risk.set_equity_provider(
                    lambda: float(self.engine.mt5.account_info().equity)
                )
                log.info("F4-WIRE: RiskGuard equity_provider set (MTM drawdown active)")
            except Exception as e:
                log.warning("F4-WIRE: equity_provider set skipped (MT5 equity unavailable): %s", e)
        log.info(f"Engine started: MT5={'LIVE' if self.engine.mt5._initialized else 'DOWN'}")

        # 2. Market data
        self.market_data = MarketData(self.engine.mt5)

        # 3. Signal generator
        self.signal_generator = StrategySignalGenerator(self.market_data)

        # 4. Position manager
        self.position_manager = PositionManager(self.engine, self.market_data, self.journal)

        # 5. Performance tracker
        self.performance = PerformanceTracker(self.engine.risk)

        # 6. KillSwitch (constitutional fail-closed) — wire state into RiskGuard
        from quant_nanggroe.engine.risk.kill_switch import KillSwitch, configure_kill_switch_file
        configure_kill_switch_file()
        self.kill_switch = KillSwitch()
        self.engine.risk.set_kill_switch(self.kill_switch.is_active)
        log.info(f"KillSwitch active={self.kill_switch.is_active}")

        log.info("All components initialized")
        log.info(f"Symbols: {CONFIG.SYMBOLS}")
        log.info(f"Cycle interval: {CONFIG.CYCLE_INTERVAL_SEC}s")
        log.info(f"Min confidence: {CONFIG.MIN_CONFIDENCE}")
        log.info("=" * 60)
    
    def run_cycle(self):
        """Execute one full trading cycle"""
        # Ensure components are initialized (idempotent: initialize() is safe to re-call)
        if self.engine is None:
            self.initialize()
        
        self.cycle_count += 1
        log.info(f"=== CYCLE #{self.cycle_count} ===")

        # 0. Refresh KillSwitch state (fail-closed: if active, halt new trades)
        try:
            self.engine.risk.set_kill_switch(self.kill_switch.is_active)
            if self.kill_switch.is_active:
                log.critical("KillSwitch ACTIVE — skipping signal gen + execution this cycle")
                return
        except Exception as e:
            log.error(f"KillSwitch check failed: {e}")

        # G3-reset: daily/weekly PnL boundary — RiskGuard.reset_daily() / reset_weekly()
        # were DEFINED but NEVER CALLED → daily_start_balance stuck at boot value →
        # daily 3% loss veto measured from boot-time equity, not actual day start.
        # Reset when (day, week) boundary crosses.
        now = datetime.now()
        cur_day = now.date()
        cur_week = now.date().isocalendar()[:2]
        if self._last_day != cur_day:
            try:
                self.engine.risk.reset_daily()
                log.info(f"G3-reset: daily PnL reset {self._last_day} -> {cur_day}")
            except Exception as e:
                log.warning(f"reset_daily() failed: {e}")
            self._last_day = cur_day
        if self._last_week != cur_week:
            try:
                self.engine.risk.reset_weekly()
                log.info(f"G3-reset: weekly PnL reset {self._last_week} -> {cur_week}")
            except Exception as e:
                log.warning(f"reset_weekly() failed: {e}")
            self._last_week = cur_week
        try:
            for symbol in CONFIG.SYMBOLS:
                self.market_data.get_tick(symbol)
        except Exception as e:
            log.error(f"Market data stage failed: {e}", exc_info=True)
            _alert_bot.alert_on_fail("market_data", f"{type(e).__name__}: {e}")

        # 2. Manage existing positions
        try:
            # Fail-closed: force-close orphan/legacy positions first (DEBATE_ROUND1)
            self.position_manager.reconcile_legacy_positions()
            self.position_manager.update_positions()
        except Exception as e:
            log.error(f"Position manager stage failed: {e}", exc_info=True)
            _alert_bot.alert_on_fail("position_manager", f"{type(e).__name__}: {e}")

        # R18 FIX (2026-08-04, user GO): data-quality precheck — warn on stale/garbage
        # feeds before generating signals (fail-safe: never blocks the loop).
        try:
            from quant_nanggroe.engine.data.quality import assess as _dq_assess
            import pandas as _pd
            for _sym in CONFIG.SYMBOLS:
                _raw = self.market_data.get_candles(_sym, "M15", 50)
                if _raw:
                    _df = _pd.DataFrame(_raw) if not isinstance(_raw, _pd.DataFrame) else _raw
                    _rep = _dq_assess(_df, _sym)
                    if not _rep.ok:
                        log.warning(f"DATA QUALITY {_sym}: {_rep.warnings}")
        except Exception as e:
            log.warning(f"data_quality precheck skipped: {e}")

        # 3. Generate signals for each symbol
        all_signals = []
        try:
            for symbol in CONFIG.SYMBOLS:
                tick = self.market_data.get_tick(symbol)
                if not tick:
                    continue

                current_price = (tick["bid"] + tick["ask"]) / 2
                signals = self.signal_generator.generate_signals(symbol, current_price)

                # Filter by confidence
                signals = [s for s in signals if s.confidence >= CONFIG.MIN_CONFIDENCE]

                if signals:
                    log.info(f"{symbol}: {len(signals)} signals (price={current_price:.5f})")
                    for s in signals:
                        log.info(f"  {s.strategy}: {s.side.upper()} conf={s.confidence:.2f}")
                    all_signals.extend(signals)
                else:
                    # G10 FIX: log HOLD with reason (was silent — impossible to tell
                    # "no signal" from "market data missing" in the live log)
                    log.info(f"{symbol}: HOLD (no signal above min_conf={CONFIG.MIN_CONFIDENCE})")
        except Exception as e:
            log.error(f"Signal generation stage failed: {e}", exc_info=True)
            _alert_bot.alert_on_fail("signal_generation", f"{type(e).__name__}: {e}")

        if not all_signals:
            log.info("HOLD ALL: no actionable signals this cycle — no trades attempted")

        # 4. Execute signals through purified engine (risk guard enforced inside)
        try:
            if all_signals:
                # CONFLICT RESOLUTION: no random buy+sell for same symbol
                all_signals = resolve_conflicts(all_signals)
                results = self.engine.cycle(all_signals)
                log.info(f"Executed {len(results)} orders")

                # JOURNAL: record every filled order with strategy attribution
                for r in results:
                    ticket = r.get("ticket")
                    if ticket and r.get("status") != "error":
                        # Find the signal that produced this ticket (by symbol+side)
                        sig = next((s for s in all_signals
                                    if s.symbol == r.get("symbol") and s.side == r.get("side")), None)
                        strat = sig.strategy if sig else "unknown"
                        conf = sig.confidence if sig else 0.0
                        self.journal.record_open(
                            ticket=ticket, strategy=strat, symbol=r.get("symbol"),
                            side=r.get("side"), entry=r.get("price", 0.0),
                            sl=r.get("sl"), tp=r.get("tp"),
                            confidence=conf, comment=f"{strat}:{r.get('symbol')}")
                        log.info(f"JOURNALED open: ticket={ticket} strat={strat} {r.get('side')} {r.get('symbol')}")
        except Exception as e:
            log.error(f"Engine execution stage failed: {e}", exc_info=True)
            _alert_bot.alert_on_fail("engine_execution", f"{type(e).__name__}: {e}")

        # 5. Risk status check
        status = {}
        try:
            status = self.engine.status()
            if not status["risk_ok"]:
                log.warning(f"RISK VETO: {status['risk_reason']} — pausing new entries")
        except Exception as e:
            log.error(f"Engine status check failed: {e}", exc_info=True)
            _alert_bot.alert_on_fail("engine_status", f"{type(e).__name__}: {e}")

        log.info(f"Balance: ${status.get('balance', 0):.2f} | Trades: {status.get('trades', 0)} | Wins: {status.get('wins', 0)} | Risk: {'OK' if status.get('risk_ok') else status.get('risk_reason', 'n/a')}")

        # R11 FIX (2026-08-04, user GO): periodic self-eval + self-evolve scheduler.
        # Additive + fail-safe: must NEVER break the main cycle. Frequency via env.
        try:
            _eval_every = int(os.environ.get("QNA_SELF_EVAL_EVERY", "10"))
            if self.cycle_count % _eval_every == 0 and self.journal:
                self.journal.self_eval()
                log.info(f"SELF-EVAL ran (periodic, cycle={self.cycle_count})")
        except Exception as e:
            log.warning(f"self_eval scheduler failed: {e}")
        try:
            _evolve_every = int(os.environ.get("QNA_EVOLVE_EVERY", "50"))
            if self.cycle_count % _evolve_every == 0:
                from quant_nanggroe.engine.strategies.strategy_evolver import StrategyEvolver
                _evo = StrategyEvolver()
                for _name in StrategyRegistry.list_strategies():
                    try:
                        _evo.evolve(_name)
                    except Exception as _ee:
                        log.warning(f"self_evolve {_name} failed: {_ee}")
                log.info(f"SELF-EVOLVE ran (periodic, cycle={self.cycle_count})")
        except Exception as e:
            log.warning(f"self_evolve scheduler failed: {e}")

        return status
    
    def run(self):
        """Main loop"""
        self.initialize()
        self.running = True
        
        log.info("AUTONOMOUS CYCLE STARTED")
        log.info("Press Ctrl+C to stop")
        
        while self.running:
            try:
                start_time = time.time()
                
                self.run_cycle()
                
                # Sleep until next cycle
                elapsed = time.time() - start_time
                sleep_time = max(1, CONFIG.CYCLE_INTERVAL_SEC - elapsed)
                time.sleep(sleep_time)
                
            except Exception as e:
                log.error(f"Cycle error: {e}", exc_info=True)
                try:
                    _alert_bot.alert_on_fail("autonomous_cycle", f"{type(e).__name__}: {e}")
                except Exception as alert_err:
                    log.error(f"Failed to send failure alert: {alert_err}")
                time.sleep(5)
        
        # Cleanup
        if self.engine.mt5 and self.engine.mt5._initialized:
            self.engine.mt5.mt5.shutdown()
        log.info("AUTONOMOUS CYCLE STOPPED")


# ──────────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────────
def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║  QNA AUTONOMOUS TRADING CYCLE                                ║
║  Purified Engine + Strategy Signals + Risk Guard + Positions ║
╚══════════════════════════════════════════════════════════════╝
    """)

    # Singleton lock acquired early (module level) before heavy imports.
    cycle = AutonomousCycle()
    cycle.run()


if __name__ == "__main__":
    main()