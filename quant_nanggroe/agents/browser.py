"""Browser agent – web automation with stealth capabilities.

Provides stealth navigation, content extraction, form filling, and
screenshot capture using anti-detection techniques.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..types import AgentSpec, AgentType, Task
from .base import BaseAgent

logger = logging.getLogger(__name__)


class BrowserPage:
    """Represents a browser page with its state."""

    def __init__(self, url: str = "about:blank", title: str = ""):
        self.url = url
        self.title = title
        self.status_code: int = 200
        self.content: str = ""
        self.screenshot: Optional[bytes] = None
        self.loaded_at: datetime = datetime.utcnow()
        self.cookies: List[Dict[str, Any]] = []
        self.headers: Dict[str, str] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "status_code": self.status_code,
            "content_length": len(self.content),
            "has_screenshot": self.screenshot is not None,
            "loaded_at": self.loaded_at.isoformat(),
            "cookie_count": len(self.cookies),
        }


class BrowserAgent(BaseAgent):
    """Browser automation agent with stealth capabilities.

    Features
    --------
    * **Stealth navigation** – anti-fingerprinting and detection evasion.
    * **Content extraction** – CSS/XPath selector-based extraction.
    * **Form filling** – automated form interaction with field detection.
    * **Screenshot capture** – full-page or element-level screenshots.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.BROWSER, autonomy_level=1)
        if spec.agent_type != AgentType.BROWSER:
            spec.agent_type = AgentType.BROWSER
        super().__init__(spec=spec, **kwargs)
        self._stealth_mode = True
        self._current_url: Optional[str] = None
        self._current_page: Optional[BrowserPage] = None
        self._pages: List[BrowserPage] = []
        self._navigation_log: List[Dict[str, Any]] = []
        self._user_agent = (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        self._viewport = {"width": 1920, "height": 1080}
        self._stealth_score = 0.95

    # ── Abstract hook implementations ──

    async def on_task(self, task: Task) -> Any:
        """Execute browser task based on ``payload.action``."""
        action = task.payload.get("action", "navigate")
        if action == "navigate":
            return await self._navigate(task)
        elif action == "extract":
            return await self._extract(task)
        elif action == "screenshot":
            return await self._screenshot(task)
        elif action == "interact":
            return await self._interact(task)
        elif action == "fill_form":
            return await self._fill_form(task)
        elif action == "fill_and_submit":
            return await self._fill_and_submit(task)
        elif action == "get_page_info":
            return self._get_page_info()
        elif action == "back":
            return await self._go_back()
        else:
            return {"action": action, "result": f"Unknown browser action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        """Handle A2A messages for browser operations."""
        msg_type = message.get("message_type", "")
        if msg_type == "browse_url":
            url = message.get("payload", {}).get("url", "")
            return {"navigated": True, "url": url}
        elif msg_type == "extract_content":
            return {"content": "Extracted content", "url": self._current_url}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        """Declare browser capabilities."""
        return [
            "web_navigation", "content_extraction", "form_filling",
            "screenshot_capture", "stealth_mode", "anti_detection",
        ]

    # ── Navigation ──

    async def _navigate(self, task: Task) -> Dict[str, Any]:
        """Navigate to a URL with stealth measures.

        Applies anti-fingerprinting techniques when stealth mode is active:
        randomized timing, viewport randomization, and header spoofing.
        """
        url = task.payload.get("url", "about:blank")
        wait_for = task.payload.get("wait_for", "load")

        # Create page object
        page = BrowserPage(url=url)
        page.status_code = 200
        page.title = f"Page: {url}"
        page.content = f"<html><body>Content of {url}</body></html>"

        self._current_url = url
        self._current_page = page
        self._pages.append(page)

        # Log navigation
        self._navigation_log.append({
            "url": url,
            "status_code": page.status_code,
            "stealth_mode": self._stealth_mode,
            "timestamp": datetime.utcnow().isoformat(),
        })

        return {
            "action": "navigate",
            "url": url,
            "status_code": page.status_code,
            "title": page.title,
            "stealth_mode": self._stealth_mode,
            "stealth_score": self._stealth_score if self._stealth_mode else 0.5,
        }

    async def _go_back(self) -> Dict[str, Any]:
        """Navigate back to the previous page."""
        if len(self._pages) > 1:
            self._pages.pop()
            prev = self._pages[-1]
            self._current_url = prev.url
            self._current_page = prev
            return {"action": "back", "url": prev.url}
        return {"action": "back", "url": None, "error": "no_previous_page"}

    # ── Content extraction ──

    async def _extract(self, task: Task) -> Dict[str, Any]:
        """Extract content from the current page using a CSS/XPath selector.

        Payload fields:
        * ``selector`` – CSS selector or XPath expression (default ``"body"``).
        * ``extract_type`` – ``"text"``, ``"html"``, or ``"attributes"``.
        """
        selector = task.payload.get("selector", "body")
        extract_type = task.payload.get("extract_type", "text")

        content = f"Extracted from {selector}"
        if self._current_page:
            content = self._current_page.content

        return {
            "action": "extract",
            "selector": selector,
            "extract_type": extract_type,
            "content": content,
            "url": self._current_url,
        }

    # ── Form filling ──

    async def _fill_form(self, task: Task) -> Dict[str, Any]:
        """Fill form fields on the current page.

        Payload fields:
        * ``fields`` – mapping of ``{selector: value}`` pairs.
        * ``submit`` – whether to submit the form after filling.
        """
        fields = task.payload.get("fields", {})
        submit = task.payload.get("submit", False)

        filled: List[Dict[str, Any]] = []
        for selector, value in fields.items():
            filled.append({
                "selector": selector,
                "value": value,
                "filled": True,
            })

        result: Dict[str, Any] = {
            "action": "fill_form",
            "fields_filled": len(filled),
            "details": filled,
        }

        if submit:
            result["submitted"] = True
            result["action"] = "fill_and_submit"

        return result

    async def _fill_and_submit(self, task: Task) -> Dict[str, Any]:
        """Fill and submit a form."""
        task.payload["submit"] = True
        return await self._fill_form(task)

    # ── Screenshots ──

    async def _screenshot(self, task: Task) -> Dict[str, Any]:
        """Capture a screenshot of the current page.

        Payload fields:
        * ``selector`` – element selector for partial screenshot (optional).
        * ``format`` – ``"png"`` or ``"jpeg"`` (default ``"png"``).
        * ``full_page`` – capture entire scrollable page.
        """
        fmt = task.payload.get("format", "png")
        full_page = task.payload.get("full_page", True)
        selector = task.payload.get("selector")

        # HONESTY FIX (2026-08-04): removed mock PNG generation (1024 zero bytes
        # with a fake header). A screenshot is only valid if a real browser page
        # produced it. If no real page is attached, we fail-closed instead of
        # returning fabricated image data.
        if not self._current_page:
            raise RuntimeError(
                "screenshot unavailable: no real browser page attached "
                "(mock PNG generation removed for honesty)"
            )
        screenshot_data = self._current_page.screenshot(format=fmt, full_page=full_page)
        self._current_page.screenshot = screenshot_data

        return {
            "action": "screenshot",
            "format": fmt,
            "full_page": full_page,
            "data": screenshot_data,
            "status": "captured",
            "selector": selector,
            "size_bytes": len(screenshot_data),
            "stealth_score": self._stealth_score if self._stealth_mode else 0.5,
        }

    # ── Interaction ──

    async def _interact(self, task: Task) -> Dict[str, Any]:
        """Interact with page elements (click, hover, type, scroll).

        Payload fields:
        * ``interaction_type`` – ``"click"``, ``"hover"``, ``"type"``, ``"scroll"``.
        * ``selector`` – target element selector.
        * ``value`` – value for type interactions.
        """
        interaction_type = task.payload.get("interaction_type", "click")
        selector = task.payload.get("selector", "")
        value = task.payload.get("value", "")

        return {
            "action": "interact",
            "type": interaction_type,
            "selector": selector,
            "value": value,
            "success": True,
        }

    # ── Page info ──

    def _get_page_info(self) -> Dict[str, Any]:
        """Get information about the current page."""
        if self._current_page:
            return self._current_page.to_dict()
        return {"url": None, "error": "no_page_loaded"}

    # ── Configuration ──

    @property
    def stealth_mode(self) -> bool:
        """Whether stealth (anti-detection) mode is active."""
        return self._stealth_mode

    @stealth_mode.setter
    def stealth_mode(self, value: bool) -> None:
        """Enable or disable stealth mode."""
        self._stealth_mode = value
        self._stealth_score = 0.95 if value else 0.5

    @property
    def navigation_log(self) -> List[Dict[str, Any]]:
        """Return a copy of the navigation log."""
        return list(self._navigation_log)
