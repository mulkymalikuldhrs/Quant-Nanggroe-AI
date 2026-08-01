#!/usr/bin/env python3
"""
QNA AUTONOMOUS TRADING CYCLE
============================
Main loop that runs continuously:
1. Fetch market data
2. Generate signals from ALL registered strategies
3. Filter through risk guard (fail-closed)
4. Execute via purified engine (REAL-ONLY MT5, no paper)
5. Manage open positions (trailing, partial TP, stop loss)
6. Record performance, update Kelly fractions
7. Sleep until next cycle

Run: python autonomous_cycle.py
"""

import os
import sys
import time
import logging
import signal as sig
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

log = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# PYTHONPATH — CRITICAL
# ──────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "quant_nanggroe"))

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
    MIN_CONFIDENCE = 0.6             # Minimum signal confidence to trade
    
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
                    return [{"time": r[0], "open": r[1], "high": r[2], "low": r[3], "close": r[4], "volume": r[5]} for r in rates]
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
        
        for name, strategy in self.strategies.items():
            try:
                signal = strategy.analyze(candles, current_price)
                if signal and signal != "hold":
                    sig = Signal(
                        symbol=symbol,
                        side=signal,
                        confidence=getattr(strategy, 'last_confidence', 0.5),
                        strategy=name,
                        price=current_price,
                        stop_loss=current_price * (0.995 if signal == "buy" else 1.005),
                        take_profit=current_price * (1.01 if signal == "buy" else 0.99),
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
        """Position closed (by TP/SL/manual). Record to journal + self-eval."""
        if not self.journal:
            return
        # Get realized PnL from MT5 deal history for this ticket
        try:
            import MetaTrader5 as mt5
            from datetime import datetime, timedelta
            deals = mt5.history_deals_get(
                datetime.now() - timedelta(days=7), datetime.now()) or []
            pnl = sum(d.profit for d in deals if d.position_id == ticket)
        except Exception:
            pnl = 0.0

        # Read open record to get entry/strategy
        open_rec = self.journal.get_open_trade(ticket)
        if not open_rec:
            return  # not our trade (e.g. manual)
        exit_price = open_rec["entry"] + (pnl / open_rec["entry"] if open_rec["entry"] else 0)
        self.journal.record_close(ticket, exit_price, pnl)

        # SELF-EVAL: recompute per-strategy kelly from journal
        verdict = self.journal.self_eval()
        for strat, v in verdict.items():
            if v.get("status") == "active" and "kelly" in v:
                self.engine.risk.kelly_cache[strat] = v["kelly"]
                log.info(f"SELF-EVAL {strat}: wr={v['win_rate']} "
                         f"expectancy={v['expectancy']} pnl={v['total_pnl']} "
                         f"kelly={v['kelly']}")
        log.info(f"CLOSED journaled: ticket={ticket} strat={open_rec['strategy']} "
                 f"pnl={pnl:.2f} outcome={'win' if pnl>0 else 'loss'}")

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
        
        # Calculate R multiple
        if side == "buy":
            risk_per_unit = entry - current_sl if current_sl > 0 else entry * 0.005
            r_multiple = (current_price - entry) / risk_per_unit if risk_per_unit > 0 else 0
        else:
            risk_per_unit = current_sl - entry if current_sl > 0 else entry * 0.005
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
            self._close_position(ticket, symbol, side, volume, current_price)
            log.info(f"FULL TP: {symbol} {ticket} closed at {r_multiple:.2f}R")
            return
        
        # TRAILING STOP
        if r_multiple > 1.0:  # Only trail after 1R profit
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
    
    def _close_position(self, ticket: int, symbol: str, side: str, volume: float, price: float):
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
            mt5.order_send(req)
        except Exception as e:
            log.error(f"Full close failed: {e}")
    
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
                self.risk_guard._kelly_cache[strategy] = kelly
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
        
        # 1. Create purified engine
        self.engine = PurifiedEngine(initial_balance=10000.0)
        self.engine.start()
        log.info(f"Engine started: MT5={'LIVE' if self.engine.mt5._initialized else 'DOWN'}")
        
        # 2. Market data
        self.market_data = MarketData(self.engine.mt5)
        
        # 3. Signal generator
        self.signal_generator = StrategySignalGenerator(self.market_data)
        
        # 4. Position manager
        self.position_manager = PositionManager(self.engine, self.market_data, self.journal)
        
        # 5. Performance tracker
        self.performance = PerformanceTracker(self.engine.risk)

        # 6. Trade journal (strategy attribution + self-eval, SQLite-backed)
        self.journal = TradeJournal()

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

        # 1. Update market data cache
        try:
            for symbol in CONFIG.SYMBOLS:
                self.market_data.get_tick(symbol)
        except Exception as e:
            log.error(f"Market data stage failed: {e}", exc_info=True)
            _alert_bot.alert_on_fail("market_data", f"{type(e).__name__}: {e}")

        # 2. Manage existing positions
        try:
            self.position_manager.update_positions()
        except Exception as e:
            log.error(f"Position manager stage failed: {e}", exc_info=True)
            _alert_bot.alert_on_fail("position_manager", f"{type(e).__name__}: {e}")

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
        except Exception as e:
            log.error(f"Signal generation stage failed: {e}", exc_info=True)
            _alert_bot.alert_on_fail("signal_generation", f"{type(e).__name__}: {e}")

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
    
    cycle = AutonomousCycle()
    cycle.run()


if __name__ == "__main__":
    main()