"""Tests for specialized agents."""
import pytest
from ai_multicolony.agents.manus import ManusAgent
from ai_multicolony.agents.planner import PlannerAgent
from ai_multicolony.agents.executor import ExecutorAgent
from ai_multicolony.agents.coder import CoderAgent
from ai_multicolony.agents.browser import BrowserAgent
from ai_multicolony.agents.voice import VoiceAgent
from ai_multicolony.agents.security import SecurityAgent
from ai_multicolony.agents.researcher import ResearcherAgent
from ai_multicolony.agents.colony import ColonyAgent
from ai_multicolony.types import AgentSpec, AgentType, AutonomyLevel, AgentCapabilities

def _spec(t):
    caps = AgentCapabilities(tools=[t.value])
    return AgentSpec(agent_id=f"{t.value}-1", agent_type=t, autonomy_level=AutonomyLevel.L1_SAFE_OPS, colony_id="c", capabilities=caps)

class TestSpecializedAgents:
    @pytest.mark.asyncio
    async def test_manus(self):
        a = ManusAgent(spec=_spec(AgentType.MANUS))
        assert a.agent_id == "manus-1"
    @pytest.mark.asyncio
    async def test_manus_caps(self):
        a = ManusAgent(spec=_spec(AgentType.MANUS))
        assert len(a.capabilities()) > 0
    @pytest.mark.asyncio
    async def test_manus_init(self):
        a = ManusAgent(spec=_spec(AgentType.MANUS))
        await a.initialize()
        assert a.state.value == "ready"
    @pytest.mark.asyncio
    async def test_planner(self):
        a = PlannerAgent(spec=_spec(AgentType.PLANNER))
        assert a.agent_id == "planner-1"
    @pytest.mark.asyncio
    async def test_executor(self):
        a = ExecutorAgent(spec=_spec(AgentType.EXECUTOR))
        assert a.agent_id == "executor-1"
    @pytest.mark.asyncio
    async def test_coder(self):
        a = CoderAgent(spec=_spec(AgentType.CODER))
        assert a.agent_id == "coder-1"
    @pytest.mark.asyncio
    async def test_browser(self):
        a = BrowserAgent(spec=_spec(AgentType.BROWSER))
        assert a.agent_id == "browser-1"
    @pytest.mark.asyncio
    async def test_voice(self):
        a = VoiceAgent(spec=_spec(AgentType.VOICE))
        assert a.agent_id == "voice-1"
    @pytest.mark.asyncio
    async def test_security(self):
        a = SecurityAgent(spec=_spec(AgentType.SECURITY))
        assert a.agent_id == "security-1"
    @pytest.mark.asyncio
    async def test_researcher(self):
        a = ResearcherAgent(spec=_spec(AgentType.RESEARCHER))
        assert a.agent_id == "researcher-1"
    @pytest.mark.asyncio
    async def test_colony(self):
        a = ColonyAgent(spec=_spec(AgentType.COLONY))
        assert a.agent_id == "colony-1"
