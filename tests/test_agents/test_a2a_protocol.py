"""Tests for A2A Protocol module."""

from __future__ import annotations

import asyncio
import pytest

from quant_nanggroe_ai.agents.a2a_protocol import (
    A2ABus,
    A2AMessage,
    A2AMessageType,
    A2AAgent,
    TradingA2AAgent,
    A2APriority,
)


# ── A2AMessage ────────────────────────────────────────────────────────────

class TestA2AMessage:
    def test_create_message(self):
        msg = A2AMessage(
            sender="agent_a",
            recipient="agent_b",
            message_type=A2AMessageType.SIGNAL,
            payload={"action": "BUY", "symbol": "AAPL"},
        )
        assert msg.sender == "agent_a"
        assert msg.recipient == "agent_b"
        assert msg.message_type == A2AMessageType.SIGNAL
        assert msg.payload["action"] == "BUY"

    def test_broadcast_message(self):
        msg = A2AMessage(
            sender="agent_a",
            recipient="broadcast",
            message_type=A2AMessageType.REGIME_CHANGE,
            payload={"regime": "TRENDING_UP"},
        )
        assert msg.recipient == "broadcast"

    def test_message_priority(self):
        msg = A2AMessage(
            sender="risk",
            recipient="trader",
            message_type=A2AMessageType.RISK_ALERT,
            payload={"alert": "DAILY_LIMIT"},
            priority=A2APriority.HIGH,
        )
        assert msg.priority == A2APriority.HIGH

    def test_reply_message(self):
        original = A2AMessage(
            sender="researcher",
            recipient="trader",
            message_type=A2AMessageType.SIGNAL,
            payload={"signal": "BUY"},
        )
        reply = original.reply(sender_id="trader", payload={"action": "EXECUTED"})
        assert reply.sender == "trader"
        assert reply.recipient == "researcher"


# ── A2ABus ────────────────────────────────────────────────────────────────

class TestA2ABus:
    def test_create_bus(self):
        bus = A2ABus()
        assert bus is not None

    def test_register_agent(self):
        bus = A2ABus()
        received = []

        async def callback(msg):
            received.append(msg)

        bus.register_agent("agent_a", callback)
        assert bus.is_registered("agent_a")

    @pytest.mark.asyncio
    async def test_send_message(self):
        bus = A2ABus()
        received = []

        async def callback_a(msg):
            pass

        async def callback_b(msg):
            received.append(msg)

        bus.register_agent("agent_a", callback_a)
        bus.register_agent("agent_b", callback_b)

        msg = A2AMessage(
            sender="agent_a",
            recipient="agent_b",
            message_type=A2AMessageType.SIGNAL,
            payload={"signal": "BUY"},
        )
        await bus.send_message(msg)
        # Give event loop time to process
        await asyncio.sleep(0.05)
        assert len(received) == 1
        assert received[0].payload["signal"] == "BUY"

    @pytest.mark.asyncio
    async def test_broadcast_message(self):
        bus = A2ABus()
        received_a = []
        received_b = []

        async def callback_a(msg):
            received_a.append(msg)

        async def callback_b(msg):
            received_b.append(msg)

        bus.register_agent("agent_a", callback_a)
        bus.register_agent("agent_b", callback_b)

        msg = A2AMessage(
            sender="system",
            recipient="broadcast",
            message_type=A2AMessageType.REGIME_CHANGE,
            payload={"regime": "PANIC"},
        )
        await bus.broadcast(msg)
        await asyncio.sleep(0.05)
        assert len(received_a) == 1
        assert len(received_b) == 1


# ── TradingA2AAgent ───────────────────────────────────────────────────────

class TestTradingA2AAgent:
    def test_create_trading_agent(self):
        bus = A2ABus()
        agent = TradingA2AAgent(agent_id="risk_agent", bus=bus)
        assert agent.agent_id == "risk_agent"

    @pytest.mark.asyncio
    async def test_send_risk_alert(self):
        bus = A2ABus()
        received = []

        async def callback(msg):
            received.append(msg)

        bus.register_agent("trader", callback)

        risk_agent = TradingA2AAgent(agent_id="risk_agent", bus=bus)
        await risk_agent.send_risk_alert(
            recipient="trader",
            alert_type="DAILY_LIMIT",
            details={"drawdown_pct": 3.5},
        )
        await asyncio.sleep(0.05)
        assert len(received) == 1
        assert received[0].message_type == A2AMessageType.RISK_ALERT

    @pytest.mark.asyncio
    async def test_send_signal(self):
        bus = A2ABus()
        received = []

        async def callback(msg):
            received.append(msg)

        bus.register_agent("execution", callback)
        bus.register_agent("researcher", lambda msg: None)

        researcher = TradingA2AAgent(agent_id="researcher", bus=bus)
        await researcher.send_signal(
            symbol="BTC/USDT",
            direction="BUY",
            confidence=0.85,
            recipient="execution",
        )
        await asyncio.sleep(0.05)
        assert len(received) == 1
        assert received[0].message_type == A2AMessageType.SIGNAL
