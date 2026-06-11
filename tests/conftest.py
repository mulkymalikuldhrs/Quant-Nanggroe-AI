"""Shared test fixtures for AI-MultiColony test suite."""
import asyncio
import pytest
from ai_multicolony.agents.state import AgentConfig, AgentStateModel
from ai_multicolony.agents.base import BaseAgent, EventBus


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def agent_config():
    return AgentConfig(
        agent_type="test_agent",
        tier=2,
        colony_id="test-colony",
        capabilities=["test"],
        autonomy_level=1,
        heartbeat_interval_ms=30000,
    )


@pytest.fixture
def event_bus():
    return EventBus()
