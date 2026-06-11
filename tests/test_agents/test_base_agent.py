"""Tests for BaseAgent lifecycle, health, circuit breaker."""
import pytest
import asyncio
from ai_multicolony.agents.base import BaseAgent, EventBus, CircuitBreaker, RetryPolicy
from ai_multicolony.types import AgentSpec, AgentState, AgentType, AutonomyLevel, CircuitBreakerState, AgentCapabilities
from ai_multicolony.agents.state import HealthReport

def _spec(agent_type=AgentType.MANUS):
    caps = AgentCapabilities(tools=["test"])
    return AgentSpec(
        agent_id="test-agent",
        agent_type=agent_type,
        autonomy_level=AutonomyLevel.L1_SAFE_OPS,
        colony_id="test-colony",
        capabilities=caps,
    )

class TestEventBus:
    def test_create(self):
        bus = EventBus()
        assert bus is not None

    @pytest.mark.asyncio
    async def test_subscribe_and_publish(self):
        from ai_multicolony.types import EventType
        bus = EventBus()
        received = []
        def handler(event):
            received.append(event)
        bus.subscribe(EventType.HEARTBEAT, handler)
        await bus.publish_typed(EventType.HEARTBEAT, "src", {"k": "v"})
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_clear(self):
        from ai_multicolony.types import EventType
        bus = EventBus()
        await bus.publish_typed(EventType.HEARTBEAT, "src", {})
        bus.clear()
        assert len(bus.get_events()) == 0


class TestCircuitBreaker:
    def test_initial_closed(self):
        cb = CircuitBreaker(failure_threshold=5, timeout=60)
        assert cb.state == CircuitBreakerState.CLOSED

    def test_opens_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=3, timeout=60)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN

    def test_can_execute_closed(self):
        cb = CircuitBreaker(failure_threshold=5, timeout=60)
        assert cb.can_execute() is True

    def test_reset(self):
        cb = CircuitBreaker(failure_threshold=2, timeout=60)
        cb.record_failure()
        cb.record_failure()
        cb.reset()
        assert cb.state == CircuitBreakerState.CLOSED


class TestRetryPolicy:
    def test_defaults(self):
        rp = RetryPolicy()
        assert rp.max_retries == 3

    def test_custom(self):
        rp = RetryPolicy(max_retries=5, base_delay=2.0)
        assert rp.max_retries == 5


class TestHealthReport:
    def test_healthy(self):
        r = HealthReport(breakdown={
            "liveness": 1.0, "task_success_rate": 0.9,
            "context_health": 0.5, "circuit_breaker_health": 1.0, "heartbeat_regularity": 1.0
        })
        r.recalculate()
        assert r.is_healthy

    def test_unhealthy(self):
        r = HealthReport(breakdown={
            "liveness": 0.3, "task_success_rate": 0.3,
            "context_health": 0.1, "circuit_breaker_health": 0.3, "heartbeat_regularity": 0.3
        })
        r.recalculate()
        assert not r.is_healthy


class TestBaseAgent:
    @pytest.mark.asyncio
    async def test_create(self):
        agent = BaseAgent(spec=_spec())
        assert agent.agent_id == "test-agent"
        assert agent.state == AgentState.REGISTERED

    @pytest.mark.asyncio
    async def test_initialize(self):
        agent = BaseAgent(spec=_spec())
        await agent.initialize()
        assert agent.state == AgentState.READY

    @pytest.mark.asyncio
    async def test_terminate(self):
        agent = BaseAgent(spec=_spec())
        await agent.initialize()
        await agent.terminate()
        assert agent.state == AgentState.TERMINATED

    @pytest.mark.asyncio
    async def test_capabilities(self):
        from ai_multicolony.agents.manus import ManusAgent
        agent = ManusAgent(spec=_spec())
        caps = agent.capabilities()
        assert isinstance(caps, (list, tuple)) and len(caps) > 0

    @pytest.mark.asyncio
    async def test_health_score(self):
        agent = BaseAgent(spec=_spec())
        assert agent.health_score == 1.0

    @pytest.mark.asyncio
    async def test_heartbeat(self):
        agent = BaseAgent(spec=_spec())
        agent.heartbeat()
        assert agent._last_heartbeat is not None

    @pytest.mark.asyncio
    async def test_context_add(self):
        agent = BaseAgent(spec=_spec())
        agent.add_context("test", {"data": "hello"})
        assert len(agent._context) >= 1

    @pytest.mark.asyncio
    async def test_escalate_autonomy(self):
        agent = BaseAgent(spec=_spec())
        result = await agent.escalate_autonomy(AutonomyLevel.L2_MODERATE, "test")
        assert result is True

    @pytest.mark.asyncio
    async def test_deescalate_autonomy(self):
        caps = AgentCapabilities(tools=["test"])
        agent = BaseAgent(spec=AgentSpec(
            agent_id="t", agent_type=AgentType.MANUS,
            autonomy_level=AutonomyLevel.L2_MODERATE,
            colony_id="c", capabilities=caps,
        ))
        await agent.deescalate_autonomy(AutonomyLevel.L0_READONLY)
        assert agent.autonomy_level == AutonomyLevel.L0_READONLY

    @pytest.mark.asyncio
    async def test_send_message(self):
        agent = BaseAgent(spec=_spec())
        msg_id = await agent.send_message("recipient", "query", {"test": True})
        assert isinstance(msg_id, str)

    @pytest.mark.asyncio
    async def test_register_tool(self):
        agent = BaseAgent(spec=_spec())
        agent.register_tool("test_tool", lambda: None)
        assert "test_tool" in agent.tools
