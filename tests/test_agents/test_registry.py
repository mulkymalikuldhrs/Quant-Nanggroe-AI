"""Tests for AgentRegistry."""
import pytest
from ai_multicolony.agents.registry import AgentRegistry
from ai_multicolony.agents.manus import ManusAgent
from ai_multicolony.agents.coder import CoderAgent
from ai_multicolony.types import AgentSpec, AgentType, AutonomyLevel, AgentCapabilities

def _spec(t, aid=None):
    caps = AgentCapabilities(tools=[t.value])
    return AgentSpec(agent_id=aid or f"{t.value}-1", agent_type=t, autonomy_level=AutonomyLevel.L1_SAFE_OPS, colony_id="c", capabilities=caps)

class TestRegistry:
    def test_create(self):
        r = AgentRegistry()
        assert r is not None
    def test_register_type(self):
        r = AgentRegistry()
        r.register_type(AgentType.MANUS, ManusAgent)
        agent = r.create_agent(AgentType.MANUS, spec=_spec(AgentType.MANUS))
        assert agent is not None
    def test_list_agents(self):
        r = AgentRegistry()
        r.register_type(AgentType.MANUS, ManusAgent)
        agent = r.create_agent(AgentType.MANUS, spec=_spec(AgentType.MANUS, aid="list-test"))
        agents = r.list_agents()
        assert isinstance(agents, list)
    def test_search_by_capability(self):
        r = AgentRegistry()
        r.register_type(AgentType.MANUS, ManusAgent)
        r.create_agent(AgentType.MANUS, spec=_spec(AgentType.MANUS, aid="search-test"))
        results = r.search_by_capability("manus")
        assert isinstance(results, list)
