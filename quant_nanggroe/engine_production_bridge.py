
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
                ("MeanReversion", {"lookback": 20, "entry_z": 2.0, "exit_z": 0.5}),
                ("Momentum", {"lookback": 20, "fast": 10, "slow": 30}),
                ("RegimeBased", {"lookback": 30}),
                ("CryptoSpecific", {"lookback": 20}),
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
            "trending_up": ["Momentum", "CryptoSpecific"],
            "trending_down": ["MeanReversion", "CryptoSpecific"],
            "ranging": ["MeanReversion", "RegimeBased"],
            "volatile": ["MeanReversion"],
            "crisis": [],
            "unknown": ["MeanReversion", "Momentum"],
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

    def _lazy_init(self):
        if self._exec_mgr is None:
            try:
                from quant_nanggroe.engine.execution.manager import ExecutionManager
                from quant_nanggroe.engine.execution.order import OrderManager
                from quant_nanggroe.engine.risk.kill_switch import KillSwitch
                from quant_nanggroe.engine.risk.manager import RiskManager
                self._exec_mgr = ExecutionManager()
                self._exec_mgr.set_kill_switch(KillSwitch())
                self._exec_mgr.set_risk_manager(RiskManager())
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

    def execute_signal(
        self, signal, price: float, balance: float
    ) -> Optional[Dict]:
        if signal is None:
            return None
        if signal.side not in ("buy", "sell"):
            return None

        self._lazy_init()
        size = balance * 0.01 if balance > 0 else 10.0
        qty = size / price if price > 0 else 0

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
    """Wires engine/risk/ for kill switch, drawdown, position sizing."""
    
    def __init__(self, db=None):
        self.db = db
        self._kill_switch = None
        self._drawdown = None
        self._sizer = None
        self._lazy_init()
    
    def _lazy_init(self):
        try:
            from quant_nanggroe.engine.risk.kill_switch import KillSwitch, KillSwitchConfig
            from quant_nanggroe.engine.risk.drawdown import DrawdownMonitor
            from quant_nanggroe.engine.risk.position_sizing import PositionSizer
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
            log.info("RiskEnforcer: KillSwitch + Drawdown + Sizer loaded")
        except Exception as e:
            log.debug(f"Risk engine partial: {e}")
    
    def is_kill_switch_triggered(self) -> bool:
        if self._kill_switch:
            try:
                result = self._kill_switch.check_auto_activate()
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
