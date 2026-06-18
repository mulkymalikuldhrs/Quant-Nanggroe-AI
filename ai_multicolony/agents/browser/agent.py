"""Browser agent - using CloakBrowser stealth patterns.

Specializes in web browsing, data extraction, form filling,
and stealth navigation with anti-bot-detection measures.
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional

from ai_multicolony.config.logging_config import get_logger
from ai_multicolony.core.base_agent import BaseAgent
from ai_multicolony.types.agent import AgentCapabilities, AgentConfig, AgentRole, AgentState
from ai_multicolony.types.memory import MemoryType
from ai_multicolony.types.messages import Message, MessageRole
from ai_multicolony.agents.browser.prompts import (
    BROWSER_SYSTEM_PROMPT,
    BROWSER_SEARCH_PROMPT,
    BROWSER_EXTRACT_PROMPT,
    BROWSER_FORM_FILL_PROMPT,
    BROWSER_STEALTH_PROMPT,
    BROWSER_DATA_EXTRACTION_PROMPT,
)

logger = get_logger(__name__)


class BrowserAgent(BaseAgent):
    """Browser agent with CloakBrowser stealth integration.

    Specializes in web browsing, data extraction, and form interaction
    using stealth techniques to avoid bot detection.

    State-specific behavior:
    - IDLE: Ready for browsing tasks
    - RUNNING: Actively navigating or interacting with pages
    - THINKING: Analyzing page content or planning next action
    - WAITING: Waiting for page load or element availability
    - PAUSED: Browsing paused, resumable
    - ERROR: Navigation or extraction error, attempts recovery
    """

    # Track browsing history
    _browsing_history: list[dict[str, Any]]
    _pages_visited: int = 0
    _stealth_mode: bool = True
    _rate_limit_wait: float = 0.0

    def __init__(self, config: Optional[AgentConfig] = None, **kwargs: Any) -> None:
        if config is None:
            config = AgentConfig(
                role=AgentRole.BROWSER,
                name="browser-agent",
                description="Web browsing and data extraction with stealth capabilities",
                tools=["browser", "search", "file", "memory"],
                system_prompt=BROWSER_SYSTEM_PROMPT,
                temperature=0.1,
                max_iterations=20,  # More iterations for multi-step browsing
                capabilities=AgentCapabilities(
                    web_browsing=True,
                    web_search=True,
                    file_operations=True,
                    memory_management=True,
                ),
            )
        else:
            if not config.system_prompt:
                config.system_prompt = BROWSER_SYSTEM_PROMPT
            if not config.tools:
                config.tools = ["browser", "search", "file", "memory"]

        super().__init__(config=config, **kwargs)
        self._browsing_history = []
        self._pages_visited = 0
        self._stealth_mode = True
        self._rate_limit_wait = 0.0

    # ------------------------------------------------------------------
    # Required tools
    # ------------------------------------------------------------------

    @classmethod
    def get_required_tools(cls) -> list[str]:
        """Return the list of tool names BrowserAgent requires.

        Returns:
            Tools needed for browsing operations.
        """
        return ["browser", "search", "file", "memory"]

    # ------------------------------------------------------------------
    # System prompt
    # ------------------------------------------------------------------

    def get_system_prompt(self) -> str:
        """Get the system prompt for the Browser agent."""
        return self.config.system_prompt or BROWSER_SYSTEM_PROMPT

    # ------------------------------------------------------------------
    # State-specific behavior
    # ------------------------------------------------------------------

    def _on_enter_running(self) -> None:
        """Hook called when entering RUNNING state."""
        logger.info(
            "browser_agent_running",
            agent_id=self.agent_id,
            pages_visited=self._pages_visited,
            stealth=self._stealth_mode,
        )

    def _on_enter_error(self) -> None:
        """Hook called when entering ERROR state."""
        logger.warning(
            "browser_agent_error",
            agent_id=self.agent_id,
            error_count=self.error_count,
            last_url=self._browsing_history[-1] if self._browsing_history else None,
        )

    def _on_enter_waiting(self) -> None:
        """Hook called when entering WAITING state (page load, etc.)."""
        logger.info("browser_agent_waiting", agent_id=self.agent_id)

    # ------------------------------------------------------------------
    # Core browsing methods
    # ------------------------------------------------------------------

    async def browse(self, url: str, task: str = "Extract relevant information") -> str:
        """Browse a URL and perform a task.

        Args:
            url: The URL to browse.
            task: What to do on the page.

        Returns:
            The browsing result.
        """
        self._pages_visited += 1

        if self._stealth_mode:
            stealth_prompt = BROWSER_STEALTH_PROMPT.format(context=f"Navigate to {url}")
            self.messages.append(Message(
                role=MessageRole.ASSISTANT,
                content=stealth_prompt,
            ))

        prompt = f"Browse to {url} and {task}"
        result = await self.run(prompt)

        # Record browsing history
        self._browsing_history.append({
            "url": url,
            "task": task,
            "result_preview": result[:200],
            "stealth": self._stealth_mode,
        })

        return result

    async def search(self, query: str) -> str:
        """Search the web for information.

        Args:
            query: The search query.

        Returns:
            Search results summary.
        """
        prompt = BROWSER_SEARCH_PROMPT.format(query=query)
        result = await self.run(prompt)

        self._browsing_history.append({
            "action": "search",
            "query": query,
            "result_preview": result[:200],
        })

        return result

    async def extract(self, url: str, target: str) -> str:
        """Extract specific information from a web page.

        Args:
            url: The URL to browse.
            target: What information to extract.

        Returns:
            Extracted information.
        """
        self._pages_visited += 1

        prompt = f"Browse to {url}\n\n" + BROWSER_EXTRACT_PROMPT.format(target=target)
        result = await self.run(prompt)

        self._browsing_history.append({
            "action": "extract",
            "url": url,
            "target": target[:100],
            "result_preview": result[:200],
        })

        return result

    async def fill_form(self, url: str, fields: dict[str, str]) -> str:
        """Fill out a form on a web page.

        Args:
            url: The URL containing the form.
            fields: Dictionary of field_name -> value to fill.

        Returns:
            Form submission result.
        """
        self._pages_visited += 1

        fields_str = "\n".join(f"  {k}: {v}" for k, v in fields.items())
        prompt = (
            f"Browse to {url}\n\n"
            + BROWSER_FORM_FILL_PROMPT.format(fields=fields_str)
        )
        result = await self.run(prompt)

        self._browsing_history.append({
            "action": "form_fill",
            "url": url,
            "fields_count": len(fields),
            "result_preview": result[:200],
        })

        return result

    async def extract_structured(self, url: str, schema: dict[str, str]) -> str:
        """Extract structured data from a web page.

        Args:
            url: The URL to browse.
            schema: Dictionary mapping field names to descriptions.

        Returns:
            Structured data in JSON format.
        """
        self._pages_visited += 1

        schema_str = "\n".join(f"  {k}: {v}" for k, v in schema.items())
        prompt = (
            f"Browse to {url}\n\n"
            + BROWSER_DATA_EXTRACTION_PROMPT.format(schema=schema_str)
        )
        result = await self.run(prompt)

        self._browsing_history.append({
            "action": "structured_extraction",
            "url": url,
            "schema_fields": list(schema.keys()),
            "result_preview": result[:200],
        })

        return result

    # ------------------------------------------------------------------
    # Stealth management
    # ------------------------------------------------------------------

    def enable_stealth(self) -> None:
        """Enable stealth mode for browsing."""
        self._stealth_mode = True
        logger.info("stealth_enabled", agent_id=self.agent_id)

    def disable_stealth(self) -> None:
        """Disable stealth mode for browsing."""
        self._stealth_mode = False
        logger.info("stealth_disabled", agent_id=self.agent_id)

    def set_rate_limit_wait(self, seconds: float) -> None:
        """Set the rate limit wait time between page loads.

        Args:
            seconds: Wait time in seconds.
        """
        self._rate_limit_wait = max(0.0, seconds)

    # ------------------------------------------------------------------
    # Browsing history
    # ------------------------------------------------------------------

    def get_browsing_history(self) -> list[dict[str, Any]]:
        """Get the browsing history for this agent.

        Returns:
            List of browsing history entries.
        """
        return list(self._browsing_history)

    def clear_browsing_history(self) -> None:
        """Clear the browsing history."""
        self._browsing_history.clear()
        self._pages_visited = 0
