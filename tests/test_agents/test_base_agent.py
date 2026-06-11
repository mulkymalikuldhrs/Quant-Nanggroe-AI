"""
Tests for BaseAgent and Agent Factory.

Validates the base agent abstract class, LLM creation, agent registry,
and agent factory functionality.
"""

import pytest
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

from langchain_core.language_models import BaseChatModel

from quant_nanggroe.agents.base import BaseAgent, create_llm
from quant_nanggroe.agents.registry import AgentFactory, AgentRegistry
from quant_nanggroe.agents.state import AgentOutput, AgentRole, AgentState


# Concrete test agent for testing the abstract base
class TestableAgent(BaseAgent):
    """A concrete agent implementation for testing."""

    def run(self, state: AgentState) -> Dict[str, Any]:
        """Simple test implementation."""
        output = self.create_output(
            content=f"Test agent {self.name} executed",
            confidence=0.8,
        )
        return {
            "agent_outputs": {
                **state.get("agent_outputs", {}),
                self.name: output.model_dump(),
            },
            "sender": self.name,
        }


class TestCreateLLM:
    """Test the create_llm function."""

    @patch("quant_nanggroe.agents.base.ChatOpenAI")
    def test_openai_provider(self, mock_openai):
        """Should create ChatOpenAI for openai provider."""
        mock_openai.return_value = MagicMock()
        llm = create_llm("openai", "gpt-4o")
        mock_openai.assert_called_once()

    @patch("quant_nanggroe.agents.base.ChatOpenAI")
    def test_ollama_provider(self, mock_openai):
        """Should create ChatOpenAI for ollama provider."""
        mock_openai.return_value = MagicMock()
        llm = create_llm("ollama", "llama3", base_url="http://localhost:11434/v1")
        mock_openai.assert_called_once()

    @patch("quant_nanggroe.agents.base.ChatOpenAI")
    def test_openrouter_provider(self, mock_openai):
        """Should create ChatOpenAI for openrouter provider."""
        mock_openai.return_value = MagicMock()
        llm = create_llm("openrouter", "gpt-4o", base_url="https://openrouter.ai/api/v1")
        mock_openai.assert_called_once()

    @patch("quant_nanggroe.agents.base.ChatAnthropic")
    def test_anthropic_provider(self, mock_anthropic):
        """Should create ChatAnthropic for anthropic provider."""
        mock_anthropic.return_value = MagicMock()
        llm = create_llm("anthropic", "claude-3-opus-20240229")
        mock_anthropic.assert_called_once()

    @patch("quant_nanggroe.agents.base.ChatGoogleGenerativeAI")
    def test_google_provider(self, mock_google):
        """Should create ChatGoogleGenerativeAI for google provider."""
        mock_google.return_value = MagicMock()
        llm = create_llm("google", "gemini-pro")
        mock_google.assert_called_once()

    def test_unsupported_provider(self):
        """Should raise ValueError for unsupported provider."""
        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            create_llm("invalid_provider", "model")


class TestBaseAgent:
    """Test the BaseAgent abstract class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_llm = MagicMock(spec=BaseChatModel)
        self.agent = TestableAgent(
            name="test_agent",
            role=AgentRole.RESEARCHER,
            description="A test agent",
            llm=self.mock_llm,
        )

    def test_name_property(self):
        """Agent name should be accessible."""
        assert self.agent.name == "test_agent"

    def test_role_property(self):
        """Agent role should be accessible."""
        assert self.agent.role == AgentRole.RESEARCHER

    def test_description_property(self):
        """Agent description should be accessible."""
        assert self.agent.description == "A test agent"

    def test_llm_property(self):
        """Agent LLM should be accessible."""
        assert self.agent.llm == self.mock_llm

    def test_default_system_prompt(self):
        """Should generate default system prompt."""
        prompt = self.agent.default_system_prompt()
        assert "test_agent" in prompt
        assert "researcher" in prompt

    def test_custom_system_prompt(self):
        """Should use custom system prompt."""
        agent = TestableAgent(
            name="custom",
            role=AgentRole.TRADER,
            description="Custom agent",
            llm=self.mock_llm,
            system_prompt="Custom prompt",
        )
        assert "Custom prompt" in agent._system_prompt

    def test_create_output(self):
        """Should create AgentOutput."""
        output = self.agent.create_output(
            content="Test output",
            confidence=0.9,
        )
        assert isinstance(output, AgentOutput)
        assert output.agent_name == "test_agent"
        assert output.agent_role == AgentRole.RESEARCHER
        assert output.content == "Test output"
        assert output.confidence == 0.9
        assert output.success is True

    def test_create_output_with_error(self):
        """Should create AgentOutput with error."""
        output = self.agent.create_output(
            content="Failed",
            success=False,
            error="Test error",
        )
        assert output.success is False
        assert output.error == "Test error"

    def test_run_method(self):
        """Should execute the run method."""
        state: AgentState = {
            "symbols": ["AAPL"],
            "trade_date": "2025-03-01",
            "agent_outputs": {},
        }
        # Fill required fields with defaults
        from quant_nanggroe.agents.state import create_initial_state
        full_state = create_initial_state(["AAPL"], "2025-03-01")

        result = self.agent.run(full_state)
        assert "agent_outputs" in result
        assert "test_agent" in result["agent_outputs"]

    def test_call_method(self):
        """Should be callable as a LangGraph node."""
        from quant_nanggroe.agents.state import create_initial_state
        full_state = create_initial_state(["AAPL"], "2025-03-01")

        result = self.agent(full_state)
        assert "agent_outputs" in result
        assert "sender" in result

    def test_repr(self):
        """Should have a string representation."""
        repr_str = repr(self.agent)
        assert "TestableAgent" in repr_str
        assert "test_agent" in repr_str

    def test_format_state_for_prompt(self):
        """Should format state for inclusion in prompts."""
        from quant_nanggroe.agents.state import create_initial_state
        state = create_initial_state(["AAPL", "MSFT"], "2025-03-01")

        formatted = self.agent.format_state_for_prompt(state)
        assert "AAPL" in formatted
        assert "MSFT" in formatted
        assert "2025-03-01" in formatted


class TestAgentRegistry:
    """Test the AgentRegistry."""

    def setup_method(self):
        """Clear the registry before each test."""
        AgentRegistry.clear()

    def test_register_agent(self):
        """Should register an agent class."""
        @AgentRegistry.register("test_registered", AgentRole.RESEARCHER)
        class TestRegistered(BaseAgent):
            def run(self, state):
                return {}

        assert "test_registered" in AgentRegistry.list_agents()

    def test_get_agent(self):
        """Should get a registered agent by name."""
        @AgentRegistry.register("test_get", AgentRole.TRADER)
        class TestGet(BaseAgent):
            def run(self, state):
                return {}

        factory = AgentRegistry.get("test_get")
        assert factory is not None
        assert factory == TestGet

    def test_get_nonexistent_agent(self):
        """Should return None for unregistered agent."""
        result = AgentRegistry.get("nonexistent")
        assert result is None

    def test_get_by_role(self):
        """Should get agent by role."""
        @AgentRegistry.register("test_by_role", AgentRole.STRATEGIST)
        class TestByRole(BaseAgent):
            def run(self, state):
                return {}

        factory = AgentRegistry.get_by_role(AgentRole.STRATEGIST)
        assert factory is not None

    def test_list_agents(self):
        """Should list all registered agents."""
        @AgentRegistry.register("list_test_1", AgentRole.MACRO)
        class Test1(BaseAgent):
            def run(self, state):
                return {}

        agents = AgentRegistry.list_agents()
        assert "list_test_1" in agents

    def test_clear(self):
        """Should clear the registry."""
        @AgentRegistry.register("clear_test", AgentRole.CRYPTO)
        class TestClear(BaseAgent):
            def run(self, state):
                return {}

        AgentRegistry.clear()
        assert len(AgentRegistry.list_agents()) == 0


class TestAgentFactory:
    """Test the AgentFactory."""

    def setup_method(self):
        """Set up test fixtures."""
        AgentRegistry.clear()

        # Register a test agent
        @AgentRegistry.register("factory_test", AgentRole.RESEARCHER)
        class FactoryTestAgent(BaseAgent):
            def run(self, state):
                return {}

    def test_factory_creation(self):
        """Should create an AgentFactory."""
        factory = AgentFactory(
            llm_provider="openai",
            deep_think_model="gpt-4o",
            quick_think_model="gpt-4o-mini",
        )
        assert factory.llm_provider == "openai"

    @patch("quant_nanggroe.agents.registry.create_llm")
    def test_create_agent(self, mock_create_llm):
        """Should create an agent by name."""
        mock_llm = MagicMock()
        mock_create_llm.return_value = mock_llm

        factory = AgentFactory(llm_provider="openai")
        agent = factory.create_agent("factory_test")
        assert agent is not None
        assert agent.name == "factory_test"

    def test_create_nonexistent_agent(self):
        """Should raise ValueError for unregistered agent."""
        factory = AgentFactory(llm_provider="openai")
        with pytest.raises(ValueError, match="not registered"):
            factory.create_agent("nonexistent")
