"""Tests for type models."""
import pytest
from ai_multicolony.types import AgentSpec, AgentState, AgentType, AutonomyLevel, AgentCapabilities
from ai_multicolony.types.models import TaskPriority

class TestTypes:
    def test_agent_spec(self):
        caps = AgentCapabilities(tools=["test"])
        s = AgentSpec(agent_id="t1", agent_type=AgentType.MANUS, autonomy_level=AutonomyLevel.L1_SAFE_OPS, colony_id="c", capabilities=caps)
        assert s.agent_id == "t1"
    def test_agent_spec_string_type(self):
        caps = AgentCapabilities(tools=["manus"])
        s = AgentSpec(agent_id="t2", agent_type="manus", autonomy_level=AutonomyLevel.L0_READONLY, colony_id="c", capabilities=caps)
        assert s.agent_type == AgentType.MANUS
    def test_agent_state(self):
        assert AgentState.REGISTERED.value == "registered"
        assert AgentState.TERMINATED.value == "terminated"
    def test_autonomy(self):
        assert AutonomyLevel.L0_READONLY.value == 0
        assert AutonomyLevel.L4_DESTRUCTIVE.value == 4
    def test_task_priority(self):
        assert TaskPriority.CRITICAL.value == 4
        assert TaskPriority.LOW.value == 1
    def test_agent_capabilities(self):
        caps = AgentCapabilities(tools=["browser", "shell"], skills=["research"])
        assert "browser" in caps.tools
        assert "research" in caps.skills
