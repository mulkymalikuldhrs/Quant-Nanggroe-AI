"""
Unified Execution Router
========================
Single MT5 > Paper > Engine > dict fallback chain.
Replaces the 3 separate fallback chains across the codebase.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

log = logging.getLogger("QNA-Pipeline-Exec")


class UnifiedExecutionRouter:
    """Single execution chain: MT5 (live) → Paper → Engine → dict fallback.

    Mirrors the ProductionExecutionManager fallback logic from
    engine_production_bridge.py but as a standalone router so pipeline/
    does not depend on the full production bridge wiring.
    """

    def __init__(self, allow_live: bool = False):
        self.allow_live = allow_live
        self._mt5: Any = None
        self._paper: Any = None
        self._engine: Any = None
        self._production: Any = None

    def _lazy_mt5(self):
        if self._mt5 is not None:
            return
        if not self.allow_live:
            return
        try:
            from quant_nanggroe.connectors.mt5_broker import MT5Broker
            import os
            self._mt5 = MT5Broker(
                login=int(os.environ.get("MT5_LOGIN", "0")),
                password=os.environ.get("MT5_PASSWORD", ""),
                server=os.environ.get("MT5_SERVER", ""),
            )
            self._mt5.connect()
            log.info("MT5Broker connected")
        except Exception as e:
            log.debug("MT5Broker unavailable: %s", e)
            self._mt5 = None

    def _lazy_paper(self):
        if self._paper is not None:
            return
        try:
            from quant_nanggroe.engine_production_bridge import SyncPaperBroker
            self._paper = SyncPaperBroker()
            log.info("SyncPaperBroker loaded")
        except Exception:
            try:
                from quant_nanggroe.engine.execution.brokers.paper import PaperBroker
                self._paper = PaperBroker()
                log.info("PaperBroker loaded")
            except Exception as e:
                log.debug("Paper broker unavailable: %s", e)
                self._paper = None

    def _lazy_engine(self):
        if self._engine is not None:
            return
        try:
            from quant_nanggroe.engine.execution.builder import build_execution_manager
            self._engine = build_execution_manager(allow_live=self.allow_live)
            log.info("Engine execution manager loaded")
        except Exception as e:
            log.debug("Engine execution manager unavailable: %s", e)
            self._engine = None

    def _lazy_production(self):
        if self._production is not None:
            return
        try:
            from quant_nanggroe.engine_production_bridge import ProductionExecutionManager
            self._production = ProductionExecutionManager()
            log.info("ProductionExecutionManager loaded")
        except Exception as e:
            log.debug("ProductionExecutionManager unavailable: %s", e)

    def execute(
        self,
        symbol: str,
        side: str,
        price: float,
        confidence: float = 0.5,
        qty: Optional[float] = None,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
    ) -> Optional[dict]:
        if side not in ("buy", "sell"):
            return None

        if qty is None or qty <= 0:
            qty = max(0.001, 100.0 / price) if price > 0 else 0.001

        # 1. ProductionExecutionManager (has full MT5 > Paper > Engine chain)
        self._lazy_production()
        if self._production is not None:
            try:
                sig = _SignalStub(symbol, side, confidence, price, sl, tp)
                result = self._production.execute_signal(sig, price, 10000.0)
                if result is not None:
                    return result
            except Exception as e:
                log.debug("ProductionExecutionManager failed: %s", e)

        # 2. Direct MT5 (production bridge failed or not loaded)
        self._lazy_mt5()
        if self._mt5 is not None:
            try:
                from quant_nanggroe.connectors.broker_base import Order
                from quant_nanggroe.engine.execution.base import OrderSide, OrderType
                order = Order(
                    symbol=symbol,
                    side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
                    order_type=OrderType.MARKET,
                    quantity=qty,
                    stop_loss=sl,
                    take_profit=tp,
                )
                ticket = self._mt5.place_order(order)
                if ticket is not None:
                    return {
                        "symbol": symbol,
                        "side": side,
                        "qty": qty,
                        "price": price,
                        "ticket": ticket,
                        "strategy": "pipeline",
                        "mode": "mt5-live",
                    }
            except Exception as e:
                log.debug("Direct MT5 execution failed: %s", e)

        # 3. Paper broker
        self._lazy_paper()
        if self._paper is not None:
            try:
                result = self._paper.place_order(symbol, side, qty, price)
                if result is not None:
                    if isinstance(result, dict):
                        result.setdefault("strategy", "pipeline")
                        result.setdefault("mode", "paper")
                    return result
            except Exception as e:
                log.debug("Paper broker failed: %s", e)

        # 4. Engine execution manager
        self._lazy_engine()
        if self._engine is not None:
            try:
                from quant_nanggroe.engine.execution.base import Order, OrderSide, OrderType
                order = Order(
                    symbol=symbol,
                    side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
                    order_type=OrderType.MARKET,
                    quantity=qty,
                    stop_loss=sl,
                    take_profit=tp,
                )
                fill = self._engine.execute_order(order)
                return {
                    "symbol": symbol,
                    "side": side,
                    "qty": qty,
                    "price": price,
                    "fill_id": getattr(fill, "id", None),
                    "strategy": "pipeline",
                    "mode": "engine",
                }
            except Exception as e:
                log.debug("Engine execution failed: %s", e)

        # 5. No backend available — reject instead of pretending fill succeeded (P0 FIX)
        return {
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "price": price,
            "status": "rejected",
            "mode": "no_backend",
            "error": "All execution backends unavailable",
            "strategy": "pipeline",
        }

    def get_balance(self) -> float:
        if self._paper is not None:
            try:
                return float(self._paper.get_balance())
            except Exception:
                pass
        if self._mt5 is not None:
            try:
                return float(self._mt5.get_balance())  # P0 FIX: MT5Broker has get_balance(), not get_account()
            except Exception:
                pass
        return 0.0


class _SignalStub:
    """Minimal signal duck-type for ProductionExecutionManager.execute_signal()."""

    def __init__(self, symbol: str, side: str, confidence: float, price: float, sl: Optional[float], tp: Optional[float]):
        self.symbol = symbol
        self.side = side
        self.confidence = confidence
        self.price = price
        self.stop_loss = sl
        self.take_profit = tp
        self.strategy = "pipeline"
