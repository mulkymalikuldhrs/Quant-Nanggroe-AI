"""
Smoke integration test — verifies the full paper trading pipeline
can initialize and complete a dry-run cycle without errors.

This is NOT a unit test. It instantiates real objects (no mocks).
"""
from __future__ import annotations

import asyncio
import shutil
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from quant_nanggroe.agents.compliance.agent import ComplianceAgent
from quant_nanggroe.agents.risk.agent import RiskAgent
from quant_nanggroe.engine.monitor_hub import MonitorHub
from quant_nanggroe.engine.risk.constants import MAX_DRAWDOWN_PCT
from quant_nanggroe.engine.risk.correlation import StrategyCorrelationMonitor
from quant_nanggroe.engine.risk.drawdown import DrawdownMonitor
from quant_nanggroe.engine.risk.kill_switch import KillSwitch, KillSwitchLevel, KillSwitchTrigger
from quant_nanggroe.engine.risk.strategy_auto_disable import AutoDisableManager
from quant_nanggroe.engine.strategy.strategies import create_strategy, list_strategies
from quant_nanggroe.exchange.paper_broker import PaperExchangeBroker


@pytest.fixture
def temp_state_dir():
    d = tempfile.mkdtemp()
    yield Path(d)
    shutil.rmtree(d)


@pytest.fixture
def sample_df():
    np.random.seed(42)
    n = 300
    idx = pd.date_range("2024-01-01", periods=n, freq="h")
    price = 100.0 * (1 + np.random.normal(0, 0.005, n)).cumprod()
    return pd.DataFrame({
        "open": price * (1 + np.random.normal(0, 0.001, n)),
        "high": price * (1 + abs(np.random.normal(0, 0.01, n))),
        "low": price * (1 - abs(np.random.normal(0, 0.01, n))),
        "close": price,
        "volume": np.random.uniform(1000, 5000, n),
    }, index=idx)


class TestStrategyGeneration:
    """Verify every registered strategy can generate a signal."""

    def test_all_strategies_import(self):
        names = list_strategies()
        expected = [
            "CryptoSpecific", "MarketMaking", "MeanReversion",
            "Momentum", "PairsTrading", "RegimeBased",
            "StatisticalArbitrage", "TrendFollow", "VolatilityArbitrage",
        ]
        assert sorted(names) == sorted(expected), f"Got {names}"

    def test_every_strategy_generates_signal(self, sample_df):
        df_extended = sample_df.copy()
        df_extended["funding_rate"] = 0.01
        for name in list_strategies():
            strat = create_strategy(name)
            sig = strat.generate_signal(df_extended)
            if sig is not None:
                assert sig.signal_type is not None
                assert 0.0 <= sig.confidence <= 1.0


class TestPaperBrokerIntegration:
    """Verify PaperExchangeBroker operates correctly."""

    @pytest.mark.asyncio
    async def test_place_and_fetch_portfolio(self):
        broker = PaperExchangeBroker(initial_capital=10000.0)
        await broker.connect()
        try:
            order = await broker.place_order(
                symbol="BTC/USDT",
                side="buy",
                order_type="market",
                quantity=0.01,
                price=67000.0,
                strategy_name="test",
            )
            assert order is not None
            portfolio = await broker.get_portfolio()
            assert portfolio.total_value > 0
        finally:
            await broker.disconnect()

    @pytest.mark.asyncio
    async def test_get_positions(self):
        broker = PaperExchangeBroker(initial_capital=10000.0)
        await broker.connect()
        try:
            await broker.place_order(
                symbol="BTC/USDT", side="buy", order_type="market",
                quantity=0.01, price=67000.0, strategy_name="test",
            )
            positions = await broker.get_positions()
            assert len(positions) > 0
        finally:
            await broker.disconnect()


class TestRiskSystemIntegration:
    """Verify risk manager, kill switch, and auto-disable wired correctly."""

    def test_kill_switch_lifecycle(self):
        ks = KillSwitch()
        assert ks.can_trade() is True
        assert ks.is_active is False
        ks.activate(KillSwitchLevel.LEVEL_2, "test", KillSwitchTrigger.MANUAL, True)
        assert ks.can_trade() is False
        assert ks.is_active is True
        status = ks.status()
        assert status["current_level"] == "level_2"

    def test_auto_disable_manager(self, temp_state_dir):
        ks = KillSwitch()
        ad = AutoDisableManager(
            kill_switch=ks,
            sharpe_window=30,
            threshold=0.3,
            state_path=str(temp_state_dir / "auto_disable_state.json"),
            paper_mode=True,
        )
        returns = np.random.normal(0.001, 0.02, 30)
        ad.update("TestStrategy", returns)
        assert not ad.is_disabled("TestStrategy")

    def test_drawdown_monitor(self):
        dd = DrawdownMonitor(max_drawdown=MAX_DRAWDOWN_PCT, initial_equity=10000.0)
        dd.update(9500.0)
        assert not dd.is_breached
        dd.update(8000.0)
        assert dd.is_breached

    def test_correlation_monitor(self, temp_state_dir):
        ks = KillSwitch()
        cm = StrategyCorrelationMonitor(kill_switch=ks, state_dir=str(temp_state_dir), paper_mode=True)
        r1 = np.random.normal(0, 0.01, 100)
        r2 = np.random.normal(0, 0.01, 100)
        cm.update("S1", r1)
        cm.update("S2", r2)
        result = cm.check_and_act()
        assert "avg_correlation" in result
        assert "num_strategies" in result

    def test_risk_agent_verdict(self):
        agent = RiskAgent()
        verdict = agent.check_trade(
            symbol="BTC/USDT", side="buy", qty=0.1, price=67000.0,
            strategy="momentum", portfolio_value=10000.0,
            current_positions={},
        )
        assert verdict.status in ("APPROVED", "REJECTED")

    def test_compliance_agent_verdict(self):
        agent = ComplianceAgent()
        verdict = agent.check_trade(
            symbol="BTC/USDT", side="buy", qty=0.1,
            strategy="momentum", equity=10000.0, price=67000.0,
            positions={},
        )
        assert verdict.status in ("APPROVED", "REJECT")


class TestMonitorHubIntegration:
    """Verify MonitorHub records data correctly."""

    def test_monitor_hub_snapshot(self, temp_state_dir):
        hub = MonitorHub(log_dir=str(temp_state_dir))
        hub.record_cycle()
        hub.record_signal()
        snap = hub.snapshot()
        assert snap.cycle_count > 0
        assert snap.system_health > 0
