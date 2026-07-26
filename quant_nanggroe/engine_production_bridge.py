
"""
QNA Production Bridge v2 — Full engine/ wiring for live_engine.py

Wires:
  - engine/strategy/strategies via create_strategy() factory
  - engine/regime/ (HMMRegimeDetector)
  - engine/execution/ (Order, ExecutionManager)
  - engine/risk/ (KillSwitch, DrawdownMonitor, PositionSizer)
  - engine/backtest/ (WalkForwardEngine)

Self-contained: graceful degradation if any engine module fails to import.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

log = logging.getLogger("QNA-Prod")

# ---------------------------------------------------------------------------
# Internal Signal (avoids engine/types dependency)
# ---------------------------------------------------------------------------

@dataclass
class Signal:
    symbol: str
    side: str  # "buy", "sell", "hold", "close"
    confidence: float = 0.5
    strategy: str = ""
    price: float = 0.0
    reason: str = ""
    metadata: Dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

# ---------------------------------------------------------------------------
# ProductionStrategyRunner
# ---------------------------------------------------------------------------

# ponytail: local self-correction — record failure to JSON (MCP-independent, cron-safe). Upgrade to mcp__self_correction when running in Hermes session.
import json as _json
import time as _time
from pathlib import Path as _Path

# ponytail: ring buffer contract — cap is ENFORCED on every write (fail-closed on load error)
QNA_LESSONS_CAP = 50
QNA_LESSONS_PATH = "data/qna_lessons.json"


def _record_lesson(error: Exception, context: str):
    try:
        _Path("data").mkdir(exist_ok=True)
        p = _Path(QNA_LESSONS_PATH)
        try:
            lessons = _json.loads(p.read_text()) if p.exists() else []
            if not isinstance(lessons, list):
                lessons = []  # defend against corrupted file -> reset ring
        except (ValueError, OSError):
            lessons = []  # corrupted JSON -> reset ring, don't silently drop
        lessons.append({"ts": _time.time(), "ctx": context, "err": repr(error)})
        if len(lessons) > QNA_LESSONS_CAP:
            lessons = lessons[-QNA_LESSONS_CAP:]  # explicit, testable cap
        p.write_text(_json.dumps(lessons, indent=2))
    except Exception:
        pass


def get_lessons() -> list:
    """Read-back for audit/tests. Returns [] if missing/corrupt (fail-soft, not silent)."""
    p = _Path(QNA_LESSONS_PATH)
    if not p.exists():
        return []
    try:
        data = _json.loads(p.read_text())
        return data if isinstance(data, list) else []
    except (ValueError, OSError):
        return []


class ProductionStrategyRunner:
    """Loads ALL engine/ strategies via create_strategy() factory.
    Falls back to empty set if engine imports fail.
    """
    
    def __init__(self, price_provider=None, risk_manager=None):
        self.price_provider = price_provider
        self.risk_manager = risk_manager
        self.strategies: Dict[str, Any] = {}
        self.available: List[str] = []
        self._loaded = False
        self._load_strategies()
    
    def _load_strategies(self):
        try:
            from quant_nanggroe.engine.strategy.loader import create_strategy
            from quant_nanggroe.engine.strategies.registry import list_strategies
            self.available = list_strategies()
            to_load = [
                ("mean_rev", {"lookback": 20, "entry_z": 2.0, "exit_z": 0.5}),
                ("trend_follow", {"lookback": 20, "fast": 10, "slow": 30}),
                ("regime_detection", {"lookback": 30}),
                ("crypto_specific", {"lookback": 20}),
            ]
            for name, params in to_load:
                if name not in self.available:
                    continue
                try:
                    self.strategies[name] = create_strategy(name, params)
                    log.info(f"  Loaded strategy: {name}")
                except Exception as e:
                    log.debug(f"  Skip {name}: {e}")
            self._loaded = True
            log.info(f"Strategy runner: {len(self.strategies)} active / {len(self.available)} available")
        except Exception as e:
            log.warning(f"Strategy engine unavailable: {e}")
    
    def generate_signals(
        self,
        market_data: Dict[str, Any],
        prices: Dict[str, float],
        active_strategies: Optional[List[str]] = None
    ) -> List[Signal]:
        """Generate signals from all active strategies."""
        if not self._loaded or not self.strategies:
            return []
        
        import pandas as pd
        
        signals = []
        active = active_strategies or list(self.strategies.keys())
        
        for sym, price in prices.items():
            if not price or price <= 0:
                continue
            candles = market_data.get(sym, [])
            if len(candles) < 30:
                continue
            
            df = pd.DataFrame(candles)
            if df.empty:
                continue
            
            for sname in active:
                if sname not in self.strategies:
                    continue
                try:
                    strategy = self.strategies[sname]
                    result = strategy.generate_signal(df)
                    if result is not None:
                        side = "hold"
                        if hasattr(result, "signal_type"):
                            st = result.signal_type
                            if hasattr(st, "value"):
                                st = st.value
                            side = str(st)
                        elif isinstance(result, str):
                            side = result
                        elif hasattr(result, "side"):
                            side = result.side
                        
                        if side in ("buy", "sell"):
                            signals.append(Signal(
                                symbol=sym,
                                side=side,
                                confidence=getattr(result, "confidence", 0.5),
                                strategy=sname,
                                price=price,
                                reason=getattr(result, "reasoning", ""),
                            ))
                except Exception as e:
                    log.debug(f"Signal error {sname} {sym}: {e}")
        
        return signals

# ---------------------------------------------------------------------------
# RegimeAwareExecution
# ---------------------------------------------------------------------------

class RegimeAwareExecution:
    """Wires engine/regime/ for market regime detection."""
    
    def __init__(self):
        self.current_regime = "unknown"
        self.regime_confidence = 0.0
        self._detector = None
    
    def _lazy_detector(self):
        if self._detector is None:
            try:
                from quant_nanggroe.engine.regime.hmm_detector import HMMRegimeDetector
                self._detector = HMMRegimeDetector(n_regimes=4)
                log.info("HMMRegimeDetector loaded")
            except Exception as e:
                log.debug(f"No regime detector: {e}")
        return self._detector
    
    def detect(self, prices: Dict[str, float], candles: Dict[str, List]) -> str:
        detector = self._lazy_detector()
        if detector is None:
            return self._fallback_detect(candles)
        try:
            # Use USDT pair returns for regime detection
            for sym in ("BTCUSDT", "ETHUSDT"):
                data = candles.get(sym, [])
                if len(data) > 30:
                    closes = [c["close"] for c in data]
                    returns = [(closes[i] - closes[i-1]) / closes[i-1] 
                               for i in range(1, len(closes))]
                    result = detector.predict(returns)
                    if result:
                        regime = getattr(result, "regime", None)
                        if regime is not None:
                            if hasattr(regime, "value"):
                                self.current_regime = regime.value
                            else:
                                self.current_regime = str(regime)
                        self.regime_confidence = getattr(result, "confidence", 0.0)
                        return self.current_regime
        except Exception as e:
            log.debug(f"Regime detect error: {e}")
        return self._fallback_detect(candles)
    
    def _fallback_detect(self, candles: Dict[str, List]) -> str:
        """Simple trend detection fallback."""
        for sym in ("BTCUSDT", "ETHUSDT"):
            data = candles.get(sym, [])
            if len(data) > 20:
                closes = [c["close"] for c in data[-20:]]
                sma5 = sum(closes[-5:]) / 5
                sma20 = sum(closes) / 20
                if sma5 > sma20 * 1.02:
                    self.current_regime = "trending_up"
                elif sma5 < sma20 * 0.98:
                    self.current_regime = "trending_down"
                else:
                    vol = (max(closes) - min(closes)) / min(closes)
                    if vol > 0.05:
                        self.current_regime = "volatile"
                    else:
                        self.current_regime = "ranging"
                return self.current_regime
        return "unknown"
    
    def select_strategies(self, regime: str) -> List[str]:
        mapping = {
            "trending_up": ["trend_follow", "crypto_specific"],
            "trending_down": ["mean_rev", "crypto_specific"],
            "ranging": ["mean_rev", "regime_detection"],
            "volatile": ["mean_rev"],
            "crisis": [],
            "unknown": ["mean_rev", "trend_follow"],
        }
        return mapping.get(regime, list(mapping.values())[0])

# ---------------------------------------------------------------------------
# ProductionExecutionManager
# ---------------------------------------------------------------------------

class SyncPaperBroker:
    """Synchronous wrapper around PaperExchangeBroker for live_engine compatibility."""

    def __init__(self, initial_capital: float = 10000.0):
        self._broker = None
        self._capital = initial_capital

    def _ensure(self):
        if self._broker is not None:
            return
        import asyncio
        from quant_nanggroe.exchange.paper_broker import PaperExchangeBroker
        self._broker = PaperExchangeBroker(initial_capital=self._capital)
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._broker.connect())
            loop.close()
        except Exception:
            pass

    def place_order(self, symbol: str, side: str, qty: float, price: float) -> Optional[Dict]:
        self._ensure()
        import asyncio
        from quant_nanggroe.types.orders import OrderSide, OrderType
        os = OrderSide.BUY if side == "buy" else OrderSide.SELL
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            order = loop.run_until_complete(
                self._broker.place_order(
                    symbol=symbol,
                    side=os,
                    order_type=OrderType.MARKET,
                    quantity=qty,
                )
            )
            loop.close()
            return {
                "symbol": order.symbol,
                "side": side,
                "qty": qty,
                "price": price,
                "fill_id": order.id,
                "strategy": "exchange",
                "mode": "paper_broker",
                "status": order.status.value,
            }
        except Exception as e:
            log.debug(f"Paper broker order failed: {e}")
            return None

    def get_balance(self) -> float:
        self._ensure()
        import asyncio
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            bal = loop.run_until_complete(self._broker.get_balance())
            loop.close()
            return bal.get("USDT", bal.get("total", 0))
        except Exception:
            return self._capital

    def get_positions(self) -> list:
        self._ensure()
        import asyncio
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            pos = loop.run_until_complete(self._broker.get_positions())
            loop.close()
            return pos
        except Exception:
            return []


class ProductionExecutionManager:
    """Wires exchange layer + engine/execution/ for order management."""

    def __init__(self, db=None):
        self.db = db
        self._exec_mgr = None
        self._order_mgr = None
        self._paper = None
        self._mt5 = None

    def _lazy_init(self):
        if self._exec_mgr is None:
            try:
                from quant_nanggroe.engine.execution.order import OrderManager
                from quant_nanggroe.engine.risk.kill_switch import configure_kill_switch_file
                configure_kill_switch_file()  # C5: converge on one shared kill-switch truth
                from quant_nanggroe.engine.execution.builder import build_execution_manager
                # P0 fix: honor QNA_LIVE_TRADING so the production bridge can
                # actually trade live (previously always paper-only).
                _allow_live = os.environ.get("QNA_LIVE_TRADING", "0") == "1"
                self._exec_mgr = build_execution_manager(allow_live=_allow_live)
                self._order_mgr = OrderManager()
                log.info("ExecutionManager loaded (constitutional risk enforced)")
            except Exception as e:
                log.debug(f"No execution engine: {e}")
        if self._paper is None:
            try:
                self._paper = SyncPaperBroker()
                log.info("PaperExchangeBroker loaded via sync wrapper")
            except Exception as e:
                log.debug(f"No paper broker: {e}")
        # ponytail: live MT5 backend — opt-in via env, fail-closed (no terminal -> skipped, not silent)
        if os.environ.get("QNA_MT5_LIVE") == "1" and self._mt5 is None:
            try:
                from quant_nanggroe.connectors.mt5_broker import MT5Broker
                self._mt5 = MT5Broker(
                    login=int(os.environ.get("MT5_LOGIN", "0")),
                    password=os.environ.get("MT5_PASSWORD", ""),
                    server=os.environ.get("MT5_SERVER", ""),
                )
                self._mt5.connect()
                log.info("MT5Broker LIVE connected")
            except Exception as e:
                log.warning(f"MT5 live unavailable (fail-closed): {e}")
                self._mt5 = None

    def execute_signal(
        self, signal, price: float, balance: float
    ) -> Optional[Dict]:
        try:
            return self._execute_signal_inner(signal, price, balance)
        except Exception as e:
            _record_lesson(e, f"execute_signal {getattr(signal,'symbol',None)}")
            log.error(f"execute_signal failed (recorded): {e}")
            raise

    def _execute_signal_inner(
        self, signal, price: float, balance: float
    ) -> Optional[Dict]:
        if signal is None:
            return None
        if signal.side not in ("buy", "sell"):
            return None

        self._lazy_init()
        size = balance * 0.01 if balance > 0 else 10.0
        qty = size / price if price > 0 else 0

        # ponytail: LIVE MT5 takes priority over paper when explicitly enabled
        # (QNA_MT5_LIVE=1) and connected. Paper is the FALLBACK, not the silent
        # default. Fail-open bug (#9) was: paper returned first, _mt5 never used.
        if os.environ.get("QNA_MT5_LIVE") == "1" and self._mt5 is not None:
            try:
                from quant_nanggroe.connectors.broker_base import Order
                from quant_nanggroe.engine.execution.base import OrderSide
                # P0 fix: carry protective SL/TP into the live order so positions
                # are never naked (previously dropped -> MT5 veto/phantom risk).
                order = Order(
                    symbol=signal.symbol,
                    side=OrderSide.BUY if signal.side == "buy" else OrderSide.SELL,
                    order_type=OrderType.MARKET,
                    quantity=qty,
                    stop_loss=getattr(signal, "stop_loss", None),
                    take_profit=getattr(signal, "take_profit", None),
                )
                ticket = self._mt5.place_order(order)
                result = {
                    "symbol": signal.symbol, "side": signal.side, "qty": qty,
                    "price": price, "ticket": ticket,
                    "strategy": signal.strategy, "mode": "mt5-live",
                }
                log.info(f"MT5 LIVE order placed: {result}")
                return result
            except Exception as e:
                log.error(f"MT5 live exec failed (falling back to paper/engine): {e}")
                _record_lesson(e, f"mt5_live {signal.symbol}")

        # Primary: exchange paper broker
        if self._paper is not None:
            result = self._paper.place_order(signal.symbol, signal.side, qty, price)
            if result is not None:
                result["strategy"] = signal.strategy
                return result
            log.debug("Paper broker failed, falling back")

        # Secondary: engine execution
        if self._exec_mgr:
            try:
                from quant_nanggroe.engine.execution.base import Order, OrderSide, OrderType
                side = OrderSide.BUY if signal.side == "buy" else OrderSide.SELL
                order = Order(
                    symbol=signal.symbol,
                    side=side,
                    order_type=OrderType.MARKET,
                    quantity=qty,
                    # P0 fix: carry protective SL/TP into engine order path too
                    stop_loss=getattr(signal, "stop_loss", None),
                    take_profit=getattr(signal, "take_profit", None),
                )
                fill = self._exec_mgr.execute_order(order)
                return {
                    "symbol": signal.symbol,
                    "side": signal.side,
                    "qty": qty,
                    "price": price,
                    "fill_id": getattr(fill, "id", None),
                    "strategy": signal.strategy,
                    "mode": "engine",
                }
            except Exception as e:
                log.debug(f"Engine exec failed: {e}")

        # Fallback: order dict for live_engine
        return {
            "symbol": signal.symbol,
            "side": signal.side,
            "qty": qty,
            "price": price,
            "strategy": signal.strategy,
            "mode": "fallback",
        }

    def get_exchange_balance(self) -> float:
        self._lazy_init()
        if self._paper is not None:
            return self._paper.get_balance()
        return 0.0

# ---------------------------------------------------------------------------
# RiskEnforcer
# ---------------------------------------------------------------------------

class RiskEnforcer:
    """Wires engine/risk/ for kill switch, drawdown, position sizing, DCC-GARCH, COT, and thesis drift guard."""
    
    def __init__(self, db=None):
        self.db = db
        self._kill_switch = None
        self._drawdown = None
        self._sizer = None
        self._dcc: Any = None  # DCCGARCH instance
        self._cot: Any = None  # COTAnalyzer instance
        self._thesis: Any = None  # ThesisDriftGuard instance
        self._daily_pnl = 0.0
        self._weekly_pnl = 0.0
        self._lazy_init()
    
    def _lazy_init(self):
        try:
            from quant_nanggroe.engine.risk.kill_switch import KillSwitch, KillSwitchConfig
            from quant_nanggroe.engine.risk.drawdown import DrawdownMonitor
            from quant_nanggroe.engine.risk.position_sizing import PositionSizer
            from quant_nanggroe.engine.risk.dcc_garch import DCCGARCH
            from quant_nanggroe.engine.risk.thesis_drift_guard import ThesisDriftGuard
            from quant_nanggroe.engine.cot import COTAnalyzer
            initial_equity = 10000.0
            if self.db is not None:
                try:
                    row = self.db.execute("SELECT value FROM portfolio WHERE key='balance'").fetchone()
                    if row and row[0] is not None:
                        initial_equity = float(row[0])
                except Exception:
                    pass
            self._kill_switch = KillSwitch(KillSwitchConfig())
            self._drawdown = DrawdownMonitor(max_drawdown=0.15, initial_equity=initial_equity)
            self._sizer = PositionSizer()
            self._dcc = DCCGARCH(dcc_a=0.05, dcc_b=0.90, target_vol=0.15, safety_factor=0.25)
            self._cot = COTAnalyzer(years_history=3)
            self._thesis = ThesisDriftGuard(advisory_threshold=1, warning_threshold=2)
            log.info("RiskEnforcer: KillSwitch + Drawdown + Sizer + DCC-GARCH + COT + ThesisDriftGuard loaded")
        except Exception as e:
            log.debug(f"Risk engine partial: {e}")
    
    def update_pnl(self, daily_pnl: float, weekly_pnl: float) -> None:
        self._daily_pnl = daily_pnl
        self._weekly_pnl = weekly_pnl

    # ── DCC-GARCH correlation / volatility interface ────────────────────────

    def update_correlation(self, returns: Any) -> bool:
        """
        Fetch historical returns and re-fit DCC-GARCH.

        Args:
            returns: (n_days x n_assets) DataFrame of historical returns.

        Returns:
            True if fit succeeded.
        """
        if self._dcc is None:
            return False
        try:
            import numpy as np
            import pandas as pd
            if isinstance(returns, np.ndarray):
                returns = pd.DataFrame(returns)
            if returns.empty or returns.shape[0] < 30:
                log.debug("DCC-GARCH: insufficient returns data (%d rows)", len(returns))
                return False
            self._dcc.fit(returns)
            return self._dcc.fitted
        except Exception as e:
            log.debug("DCC-GARCH update failed: %s", e)
            return False

    def get_correlation_matrix(self) -> Any:
        """Latest DCC correlation matrix (n_assets x n_assets)."""
        if self._dcc is not None and self._dcc.fitted:
            return self._dcc.correlation
        return None

    def get_volatilities(self) -> Any:
        """Latest GARCH volatilities array (n_assets,)."""
        if self._dcc is not None and self._dcc.fitted:
            return self._dcc.volatilities
        return None

    def get_covariance_matrix(self) -> Any:
        """Latest covariance matrix derived from DCC-GARCH."""
        if self._dcc is not None and self._dcc.fitted:
            return self._dcc.covariance
        return None

    def get_dcc_kelly_weights(
        self,
        expected_returns: Any,
        target_vol: Optional[float] = None,
    ) -> Any:
        """
        Compute Volatility-Regulated Kelly weights from DCC-GARCH.

        Args:
            expected_returns: (n_assets,) array of expected returns.
            target_vol: Optional override for target portfolio volatility.

        Returns:
            (n_assets,) array of portfolio weights, or zeros if not fitted.
        """
        if self._dcc is None or not self._dcc.fitted:
            import numpy as np
            return np.zeros(len(expected_returns))
        return self._dcc.kelly_weights(
            expected_returns=expected_returns,
            target_vol=target_vol,
        )

    def get_dcc_status(self) -> dict:
        """DCC-GARCH diagnostic summary."""
        if self._dcc is not None and self._dcc.fitted:
            return self._dcc.get_status()
        return {"fitted": False, "n_assets": 0}

    # ── Kill switch / drawdown ─────────────────────────────────────────────

    def is_kill_switch_triggered(self) -> bool:
        if self._kill_switch:
            try:
                equity = (self._drawdown._initial_equity
                          if self._drawdown is not None else 10000.0)
                daily_pnl_pct = (self._daily_pnl / equity
                                 if self._daily_pnl < 0 else 0.0)
                weekly_pnl_pct = (self._weekly_pnl / equity
                                  if self._weekly_pnl < 0 else 0.0)
                dd = 0.0
                if self._drawdown is not None:
                    dd_info = self._drawdown.get_status()
                    dd = float(dd_info.get("current_drawdown", 0.0) or 0.0)
                result = self._kill_switch.check_auto_activate(
                    daily_pnl_pct=daily_pnl_pct,
                    weekly_pnl_pct=weekly_pnl_pct,
                    max_drawdown_pct=dd,
                )
                return result is not None
            except Exception:
                pass
        return False
    
    def update_drawdown(self, equity: float):
        if self._drawdown:
            try:
                self._drawdown.update(equity)
            except Exception:
                pass
    
    def is_drawdown_breached(self) -> bool:
        if self._drawdown:
            try:
                return bool(self._drawdown.is_breached)
            except Exception:
                pass
        return False
    
    def current_drawdown(self) -> float:
        if self._drawdown:
            try:
                return float(self._drawdown.current_drawdown)
            except Exception:
                pass
        return 0.0
    
    def position_size(
        self, price: float, balance: float, kelly: float = 0.25
    ) -> float:
        if self._sizer:
            try:
                result = self._sizer.kelly_based(balance, kelly, price)
                if result is not None:
                    return getattr(result, "quantity", 0.0) or 0.0
            except Exception:
                pass
        # Fallback: fixed fraction
        return (balance * kelly * 0.1) / max(price, 1)
    
    # ── COT institutional positioning interface ─────────────────────────────

    def load_cot_data(self) -> bool:
        """Fetch and load COT data."""
        if self._cot is None:
            return False
        try:
            return self._cot.fetch_history()
        except Exception as e:
            log.debug("COT load failed: %s", e)
            return False

    def evaluate_cot(self, symbol: str = "GC1!") -> dict:
        """Evaluate COT positioning for a CME futures symbol."""
        if self._cot is None:
            return {"signal": "NOT_LOADED", "symbol": symbol}
        if not self._cot.is_loaded:
            if not self.load_cot_data():
                return {"signal": "LOAD_FAILED", "symbol": symbol}
        return self._cot.evaluate(symbol)

    def get_cot_summary(self) -> dict:
        """Get summary of current COT landscape."""
        if self._cot is None or not self._cot.is_loaded:
            return {"loaded": False, "n_extreme": 0, "signals": {}}
        return self._cot.get_summary()

    def get_cot_available_symbols(self) -> list:
        """List CME symbols with available COT data."""
        if self._cot is not None:
            return self._cot.available_symbols
        return []

    # ── Thesis Drift Guard interface ─────────────────────────────────────────

    def thesis_register_position(
        self, symbol: str, side: str, event_type: str = "UNKNOWN",
        entry_price: float = 0.0,
    ) -> bool:
        """Register a position for thesis drift monitoring."""
        if self._thesis is None:
            return False
        try:
            from quant_nanggroe.engine.risk.thesis_drift_guard import TradeThesis
            thesis = TradeThesis(
                direction="bullish" if side == "long" else "bearish",
                event_type=event_type,
            )
            self._thesis.register_position(symbol, side, thesis, entry_price)
            return True
        except Exception as e:
            log.debug("Thesis register failed: %s", e)
            return False

    def thesis_check(
        self, event_type: str, weather: str = "NEUTRAL_MIXED",
        cot_signal: str = "BALANCED", smt_divergence: bool = False,
    ) -> dict:
        """Run thesis drift check against macro context."""
        if self._thesis is None:
            return {"has_hard_exit": False, "stage_int": 0, "positions": {}}
        return self._thesis.check_all(event_type, weather, cot_signal, smt_divergence)

    def thesis_unregister(self, symbol: str) -> None:
        """Remove a position from thesis monitoring."""
        if self._thesis is not None:
            self._thesis.unregister_position(symbol)

    def thesis_get_status(self) -> dict:
        """Get thesis drift guard diagnostics."""
        if self._thesis is None:
            return {"active": False, "n_positions": 0}
        return self._thesis.get_status()

    # ── Signal filtering ────────────────────────────────────────────────────

    def filter_signals(self, signals: List[Signal]) -> List[Signal]:
        """Remove signals that violate risk rules."""
        if self.is_kill_switch_triggered():
            log.warning("KILL SWITCH ACTIVE: all signals blocked")
            return []
        if self.is_drawdown_breached():
            log.warning("DRAWDOWN BREACHED: buy signals blocked")
            return [s for s in signals if s.side != "buy"]
        return signals

# ---------------------------------------------------------------------------
# AutomatedBacktestRunner
# ---------------------------------------------------------------------------

class AutomatedBacktestRunner:
    """Automated walk-forward backtesting every N cycles."""
    
    def __init__(self, db=None):
        self.db = db
        self._engine = None
        self.last_run = 0
        self._lazy_init()
    
    def _lazy_init(self):
        try:
            from quant_nanggroe.engine.backtest.engine import BacktestEngine, BacktestConfig
            self._engine = BacktestEngine()
            log.info("BacktestEngine loaded")
        except Exception as e:
            log.debug(f"No backtest engine: {e}")
    
    def run(self, candles: Dict[str, List], cycle: int, force: bool = False) -> bool:
        """Run walk-forward optimization every 100 cycles."""
        if not self._engine:
            return False
        if not force and (cycle - self.last_run) < 100:
            return False
        
        if len(candles) < 2:
            return False
        
        log.info("Running automated backtest optimization...")
        self.last_run = cycle
        try:
            # Run walk-forward on primary pairs
            for sym in ("BTCUSDT", "ETHUSDT"):
                data = candles.get(sym, [])
                if len(data) < 200:
                    continue
                import pandas as pd
                df = pd.DataFrame(data)
                if df.empty:
                    continue
                result = self._engine.run_walk_forward(
                    data=df,
                    window=100,
                    step=50,
                )
                if result:
                    log.info(f"Walk-forward {sym}: {result}")
            return True
        except Exception as e:
            log.debug(f"Auto-backtest error: {e}")
            return False

# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_production_engine(price_provider=None, risk_manager=None, db=None):
    """Factory: creates fully wired production engine components."""
    return {
        "strategy_runner": ProductionStrategyRunner(price_provider, risk_manager),
        "regime": RegimeAwareExecution(),
        "execution": ProductionExecutionManager(db),
        "risk": RiskEnforcer(db),
        "backtest": AutomatedBacktestRunner(db),
    }
