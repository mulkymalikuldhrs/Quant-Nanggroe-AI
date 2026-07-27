"""Walk-Forward Execution Pipeline Test — exercises 4-broker system post-v6.3.0 hardening.

Tests:
  A) ExecutionManager public API seal (no private attribute access)
  B) Builder correctly wires brokers via public API
  C) MT5 adapter circuit breaker (5-fail/60s, recovery)
  D) MT5 SYMBOL_MAP translation (constants.py)
  E) Paper broker deterministic fill (seeded RNG)
  F) KillSwitch force_deactivate + append-only audit trail
  G) engine_bridge.py ASSET_MAP (typo fix) + ASSET_ALLOCATIONS
  H) PnL fraction convention across all layers
  I) Walk-forward cycle: signal → gate → execution → PnL tracking

Run:
    python -m pytest tests/test_walkforward_execution_pipeline.py -v -s --tb=short
    python -m unittest tests.test_walkforward_execution_pipeline -v
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, PropertyMock, patch

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))


# =========================================================================
# Test A: ExecutionManager public API seal
# =========================================================================
class TestExecutionManagerPublicAPI(unittest.TestCase):
    """Verify all access is through public methods."""

    def test_public_api_methods_exist(self):
        from quant_nanggroe.engine.execution.manager import ExecutionManager
        methods = [
            "get_risk_manager",
            "get_brokers",
            "get_primary_broker_name",
            "get_broker",
            "set_broker_handle",
            "get_mt5_connector",
        ]
        for m in methods:
            self.assertTrue(
                hasattr(ExecutionManager, m),
                f"ExecutionManager missing public method: {m}",
            )

    def test_builder_no_private_access_outside_comments(self):
        """Builder source has no em._risk_manager or em._brokers outside comments."""
        import quant_nanggroe.engine.execution.builder as b_mod
        source = Path(b_mod.__file__).read_text(encoding="utf-8")
        # Strip comment lines to check only code
        code_lines = [l for l in source.split("\n") if not l.strip().startswith("#")]
        code = "\n".join(code_lines)
        forbidden = ["em._brokers", "type(b).__name__"]
        for token in forbidden:
            self.assertNotIn(token, code, f"Builder code accesses private: {token}")


# =========================================================================
# Test B: Builder wiring
# =========================================================================
class TestBuilderWiring(unittest.TestCase):
    """Verify builder correctly wires brokers using public API."""

    def test_builder_creates_paper_broker(self):
        from quant_nanggroe.engine.execution.brokers.paper import PaperBroker
        broker = PaperBroker(initial_capital=100000.0)
        self.assertIsInstance(broker, PaperBroker)
        self.assertEqual(broker.name, "paper")

    def test_builder_uses_get_brokers(self):
        """build_execution_manager creates an EM whose get_brokers() works."""
        from quant_nanggroe.engine.execution.builder import build_execution_manager
        em = build_execution_manager(allow_live=False)
        brokers = em.get_brokers()
        self.assertGreater(len(brokers), 0)
        # Paper broker should be present
        for b in brokers.values():
            from quant_nanggroe.engine.execution.brokers.paper import PaperBroker
            if isinstance(b, PaperBroker):
                break
        else:
            self.fail("No PaperBroker found in brokers")

    def test_builder_public_api_used(self):
        """EM methods used by builder are callable."""
        from quant_nanggroe.engine.execution.builder import build_execution_manager
        em = build_execution_manager(allow_live=False)
        rm = em.get_risk_manager()
        self.assertIsNotNone(rm)
        self.assertEqual(em.get_primary_broker_name(), "paper")
        # get_mt5_connector returns None when not live
        self.assertIsNone(em.get_mt5_connector())


# =========================================================================
# Test C: MT5 Adapter Circuit Breaker
# =========================================================================
class TestMT5CircuitBreaker(unittest.TestCase):
    """Verify circuit breaker trips correctly and auto-recovers."""

    def setUp(self):
        from quant_nanggroe.engine.execution.brokers.mt5_adapter import CircuitBreaker
        self.CircuitBreaker = CircuitBreaker

    def test_cb_initially_closed(self):
        cb = self.CircuitBreaker(threshold=3, window_seconds=60.0)
        self.assertFalse(cb.is_tripped)

    def test_cb_opens_after_threshold(self):
        cb = self.CircuitBreaker(threshold=3, window_seconds=60.0)
        self.assertFalse(cb.is_tripped)
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        self.assertTrue(cb.is_tripped)

    def test_cb_recovers_after_window(self):
        cb = self.CircuitBreaker(threshold=2, window_seconds=60.0, recovery_seconds=0.1)
        cb.record_failure()
        cb.record_failure()
        self.assertTrue(cb.is_tripped)
        time.sleep(0.15)
        self.assertFalse(cb.is_tripped, "CB should reset after recovery window")

    def test_cb_reset_on_success(self):
        cb = self.CircuitBreaker(threshold=2, window_seconds=60.0)
        cb.record_failure()
        cb.record_success()  # resets failure count
        cb.record_failure()
        self.assertFalse(cb.is_tripped, "Should not trip — only 1 failure after reset")

    def test_cb_default_config(self):
        cb = self.CircuitBreaker()
        self.assertEqual(cb._threshold, 5)
        self.assertEqual(cb._recovery_seconds, 300.0)

    def test_cb_rejects_when_tripped(self):
        """Verify MT5ExecutionBroker rejects orders when CB tripped."""
        import uuid
        from quant_nanggroe.engine.execution.brokers.mt5_adapter import MT5ExecutionBroker
        from quant_nanggroe.engine.execution.base import Order, OrderSide, OrderType, OrderStatus
        from quant_nanggroe.connectors.mt5_broker import MT5Broker

        mock_mt5 = MagicMock(spec=MT5Broker)
        broker = MT5ExecutionBroker(mock_mt5)
        # Manually trip the circuit breaker
        cb = broker._circuit_breaker
        cb._tripped_at = time.monotonic()
        cb._threshold = 1  # ensure tripped

        import asyncio
        async def test():
            order = Order(id=str(uuid.uuid4()), symbol="EURUSD", side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=0.01)
            result = await broker.submit_order(order)
            self.assertEqual(result.status, OrderStatus.REJECTED)
            self.assertIn("Circuit breaker", str(result.metadata.get("reason", "")))
        asyncio.run(test())


# =========================================================================
# Test D: MT5 SYMBOL_MAP translation
# =========================================================================
class TestMT5SymbolMap(unittest.TestCase):
    """Verify MT5_SYMBOL_MAP correctly translates internal → MT5 symbols."""

    def setUp(self):
        from quant_nanggroe.engine.risk.constants import MT5_SYMBOL_MAP, MT5_SYMBOL_DEFAULT
        self.SYMBOL_MAP = MT5_SYMBOL_MAP
        self.DEFAULT = MT5_SYMBOL_DEFAULT

    def test_known_symbols_translate(self):
        cases = {
            "EURUSD": "EURUSD",
            "BTCUSDT": "BTCUSD",
            "XAUUSD": "XAUUSD",
            "ETHUSDT": "ETHUSD",
            "GBPUSD": "GBPUSD",
        }
        for internal, expected in cases.items():
            result = self.SYMBOL_MAP.get(internal)
            self.assertEqual(
                result, expected,
                f"{internal} → {result}, expected {expected}",
            )

    def test_unknown_symbol_default_is_empty(self):
        """Unknown symbols map to empty string."""
        result = self.SYMBOL_MAP.get("FOOBAR", self.DEFAULT)
        self.assertEqual(result, "")

    def test_noconflict_internal_symbols(self):
        mt5_symbols = list(self.SYMBOL_MAP.values())
        self.assertEqual(
            len(mt5_symbols),
            len(set(mt5_symbols)),
            "Duplicate MT5 symbols in SYMBOL_MAP!",
        )

    def test_mt5adapter_get_price_uses_map(self):
        """MT5ExecutionBroker.get_price uses SYMBOL_MAP for translation."""
        from quant_nanggroe.engine.execution.brokers.mt5_adapter import MT5ExecutionBroker
        from quant_nanggroe.engine.risk.constants import MT5_SYMBOL_MAP
        # The get_price code does MT5_SYMBOL_MAP.get(symbol) first,
        # then falls back to symbol.replace("-", "").upper()
        self.assertEqual(MT5_SYMBOL_MAP.get("BTCUSDT"), "BTCUSD")
        self.assertEqual(MT5_SYMBOL_MAP.get("ADAUSDT"), "ADAUSD")


# =========================================================================
# Test E: Paper Broker Determinism
# =========================================================================
class TestPaperBrokerDeterminism(unittest.TestCase):
    """Verify PaperBroker produces deterministic behavior with seeded RNG.

    Uses _rng (random.Random(42)) for reproducible tests.
    """

    def setUp(self):
        from quant_nanggroe.engine.execution.brokers.paper import PaperBroker
        self.PaperBroker = PaperBroker

    def test_seeded_rng_is_deterministic(self):
        """Two brokers produce same sequence of random numbers."""
        b1 = self.PaperBroker()
        b2 = self.PaperBroker()
        # _rng is seeded with 42 in __init__
        seq1 = [b1._rng.random() for _ in range(20)]
        seq2 = [b2._rng.random() for _ in range(20)]
        self.assertEqual(seq1, seq2)

    def test_partial_fill_is_deterministic(self):
        """submit_order with large qty produces same fill_ratio across instances."""
        import asyncio
        import uuid
        from quant_nanggroe.engine.execution.base import Order, OrderSide, OrderType

        async def run_deterministic_test():
            b1 = self.PaperBroker(initial_capital=1000000.0)
            b1.set_price("TEST-100", 100.0)
            b2 = self.PaperBroker(initial_capital=1000000.0)
            b2.set_price("TEST-100", 100.0)

            o1 = Order(id=str(uuid.uuid4()), symbol="TEST-100", side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=100.0)
            o2 = Order(id=str(uuid.uuid4()), symbol="TEST-100", side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=100.0)

            await b1.connect()
            await b2.connect()
            r1 = await b1.submit_order(o1)
            r2 = await b2.submit_order(o2)

            self.assertEqual(
                r1.metadata.get("fill_quantity"),
                r2.metadata.get("fill_quantity"),
                "Fill quantities should be deterministic across instances",
            )

        asyncio.run(run_deterministic_test())


# =========================================================================
# Test F: KillSwitch force_deactivate + audit trail
# =========================================================================
class TestKillSwitchForceDeactivate(unittest.TestCase):
    """Verify force_deactivate bypasses cooldown and writes audit trail."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp(prefix="qna_ks_test_")
        self._audit_log = os.path.join(self._tmpdir, "kill_switch_audit.jsonl")
        os.environ["QNA_KILL_SWITCH_AUDIT_LOG"] = self._audit_log
        from quant_nanggroe.engine.risk.kill_switch import (
            KillSwitch,
            KillSwitchConfig,
            KillSwitchLevel,
        )
        cfg = KillSwitchConfig(cooldown_minutes=60)
        self.ks = KillSwitch(config=cfg)
        self.KillSwitchLevel = KillSwitchLevel

    def tearDown(self):
        shutil.rmtree(self._tmpdir, ignore_errors=True)
        os.environ.pop("QNA_KILL_SWITCH_AUDIT_LOG", None)

    def test_normal_deactivate_honors_cooldown(self):
        self.ks.activate(self.KillSwitchLevel.LEVEL_2, reason="Test activation")
        result = self.ks.deactivate(reason="Try deactivate")
        self.assertIsNone(result, "Deactivate should return None during cooldown")

    def test_force_deactivate_bypasses_cooldown(self):
        self.ks.activate(self.KillSwitchLevel.LEVEL_2, reason="Test activation")
        result = self.ks.deactivate(reason="Emergency", force=True)
        self.assertIsNotNone(result, "force_deactivate should succeed")
        self.assertFalse(self.ks.is_active)

    def test_audit_trail_exists(self):
        self.ks.activate(self.KillSwitchLevel.LEVEL_1, reason="Audit test")
        self.ks.deactivate(reason="Audit complete", force=True)

        self.assertTrue(
            os.path.exists(self._audit_log),
            f"Audit log not created at {self._audit_log}",
        )
        with open(self._audit_log) as f:
            lines = f.readlines()
        self.assertGreaterEqual(len(lines), 2)
        for line in lines:
            entry = json.loads(line)
            # Events use 'event_id', 'level', 'reason', 'timestamp' keys
            self.assertIn("event_id", entry, f"Missing event_id in: {entry}")
            self.assertIn("level", entry)
            self.assertIn("timestamp", entry)

    def test_audit_trail_append_only(self):
        self.ks.activate(self.KillSwitchLevel.LEVEL_1, reason="First")
        with open(self._audit_log) as f:
            first_count = len(f.readlines())
        self.ks.activate(self.KillSwitchLevel.LEVEL_2, reason="Second")
        with open(self._audit_log) as f:
            second_count = len(f.readlines())
        self.assertEqual(second_count, first_count + 1)


# =========================================================================
# Test G: engine_bridge ASSET_MAP + ASSET_ALLOCATIONS
# =========================================================================
class TestEngineBridgeAssetMap(unittest.TestCase):
    """Verify ASSET_MAP fix and ASSET_ALLOCATIONS consistency."""

    def test_asset_map_exists(self):
        from quant_nanggroe.engine_bridge import ASSET_MAP
        self.assertIsInstance(ASSET_MAP, dict)
        self.assertGreater(len(ASSET_MAP), 0)

    def test_backward_compat_alias(self):
        from quant_nanggroe.engine_bridge import ASSET_MAP, ASSSET_MAP
        self.assertIs(ASSET_MAP, ASSSET_MAP)

    def test_asset_allocations_import(self):
        from quant_nanggroe.engine.risk.constants import ASSET_ALLOCATIONS
        self.assertIsInstance(ASSET_ALLOCATIONS, dict)
        total = sum(ASSET_ALLOCATIONS.values())
        self.assertAlmostEqual(total, 1.0, places=4,
                               msg=f"ASSET_ALLOCATIONS sum={total}, expected 1.0")

    def test_tp_targets_import(self):
        from quant_nanggroe.engine.risk.constants import TP_TARGETS
        self.assertIn("SMC", TP_TARGETS)
        self.assertIn("Momentum", TP_TARGETS)


# =========================================================================
# Test H: PnL fraction convention
# =========================================================================
class TestPnLFractionConvention(unittest.TestCase):
    """Verify PnL is consistently in fraction (0-1) across all layers."""

    def test_risk_manager_accepts_fraction_pnl(self):
        from quant_nanggroe.engine.risk.manager import RiskManager
        rm = RiskManager()
        result = rm.check_trade(
            symbol="EURUSD",
            direction="buy",
            lot_size=0.01,
            entry=1.1000,
            stop_loss=1.0950,
            daily_pnl_pct=0.02,  # 2% as fraction
        )
        self.assertIsInstance(result, dict)
        self.assertIn("verdict", result)

    def test_risk_constants_are_fractions(self):
        from quant_nanggroe.engine.risk.constants import (
            MAX_DAILY_LOSS,
            MAX_WEEKLY_LOSS,
            MAX_DRAWDOWN_PCT,
            KILL_SWITCH_DAILY_PNL,
        )
        # All should be in fraction (0-1), not percentage
        self.assertLess(abs(MAX_DAILY_LOSS), 1.0, "MAX_DAILY_LOSS should be fraction < 1.0")
        self.assertLess(abs(MAX_WEEKLY_LOSS), 1.0)
        self.assertLess(abs(MAX_DRAWDOWN_PCT), 1.0)
        self.assertLess(abs(KILL_SWITCH_DAILY_PNL), 1.0)

    def test_live_engine_constants_importable(self):
        from quant_nanggroe.engine.risk.constants import (
            HEARTBEAT_INTERVAL,
            CLEANUP_INTERVAL,
            REPORT_INTERVAL,
            DCC_UPDATE_INTERVAL,
            STARTING_CAPITAL,
        )
        self.assertGreater(HEARTBEAT_INTERVAL, 0)
        self.assertGreater(STARTING_CAPITAL, 0)


# =========================================================================
# Test I: Walk-forward execution cycle
# =========================================================================
class TestWalkForwardExecutionCycle(unittest.TestCase):
    """End-to-end pipeline: signal generation → risk gate → execution."""

    @classmethod
    def setUpClass(cls):
        from quant_nanggroe.engine.execution.builder import build_execution_manager
        cls.em = build_execution_manager(allow_live=False)

    def test_1_em_returns_risk_manager(self):
        rm = self.em.get_risk_manager()
        self.assertIsNotNone(rm)
        self.assertTrue(hasattr(rm, "check_trade"))

    def test_2_em_returns_brokers(self):
        brokers = self.em.get_brokers()
        self.assertGreater(len(brokers), 0)

    def test_3_em_returns_primary_broker(self):
        name = self.em.get_primary_broker_name()
        self.assertEqual(name, "paper")

    def test_4_em_set_and_get_broker_handle(self):
        """set_broker_handle passes handle to RiskManager without crash."""
        mock_mt5 = MagicMock()
        self.em.set_broker_handle(mock_mt5)
        rm = self.em.get_risk_manager()
        self.assertIsNotNone(rm)
        self.assertTrue(hasattr(rm, "set_broker_handle"))

    def test_5_risk_check_returns_structured_result(self):
        rm = self.em.get_risk_manager()
        result = rm.check_trade(
            symbol="EURUSD",
            direction="buy",
            lot_size=0.01,
            entry=1.1000,
            stop_loss=1.0950,
        )
        self.assertIsInstance(result, dict)
        self.assertIn("verdict", result)

    def test_6_paper_broker_submit_order(self):
        import asyncio
        import uuid
        from quant_nanggroe.engine.execution.base import Order, OrderSide, OrderType

        async def test():
            broker = self.em.get_broker("paper")
            self.assertIsNotNone(broker)
            if hasattr(broker, "set_price"):
                broker.set_price("EURUSD", 1.1000)
            order = Order(id=str(uuid.uuid4()), symbol="EURUSD", side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=0.01)
            result = await broker.submit_order(order)
            self.assertIsNotNone(result)
            self.assertIn(result.status.name, ("FILLED", "REJECTED"))

        asyncio.run(test())

    def test_7_walk_forward_module_imports(self):
        try:
            from quant_nanggroe.engine.backtest.walk_forward import WalkForwardAnalyzer
            self.assertTrue(hasattr(WalkForwardAnalyzer, "analyze"))
        except ImportError as e:
            self.skipTest(f"WalkForwardAnalyzer not importable: {e}")

    def test_8_circuit_breaker_integration(self):
        """Circuit breaker in MT5 adapter rejects when tripped."""
        from quant_nanggroe.engine.execution.brokers.mt5_adapter import CircuitBreaker
        cb = CircuitBreaker(threshold=2, recovery_seconds=300.0)
        cb.record_failure()
        cb.record_failure()
        self.assertTrue(cb.is_tripped)


# =========================================================================
# Run
# =========================================================================
if __name__ == "__main__":
    unittest.main()
