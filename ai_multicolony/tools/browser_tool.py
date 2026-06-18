"""Browser automation tool with CloakBrowser stealth integration.

Provides web browsing capabilities with human-like interaction patterns,
anti-detection measures, content extraction (text, HTML, markdown),
screenshot capture, and element interaction.
"""

from __future__ import annotations

import asyncio
import base64
import re
from typing import Any, Optional

from ai_multicolony.browser.human import (
    HumanBehavior,
    human_click,
    human_delay,
    human_scroll,
    human_type,
)
from ai_multicolony.browser.stealth import StealthConfig, apply_stealth, get_stealth_script
from ai_multicolony.config.logging_config import get_logger
from ai_multicolony.core.tool_base import BaseTool
from ai_multicolony.exceptions import ToolExecutionError, ToolTimeoutError
from ai_multicolony.types.tools import ToolCall, ToolDefinition, ToolParameter, ToolResult, ToolType

logger = get_logger(__name__)


def _html_to_markdown(html: str) -> str:
    """Convert a simplified HTML string to Markdown.

    This is a lightweight converter for page content extraction — it
    handles headings, paragraphs, links, images, lists, bold/italic,
    and code blocks.  For full fidelity, use a dedicated library.

    Args:
        html: Raw HTML string.

    Returns:
        Approximate Markdown string.
    """
    # Remove scripts and styles
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)

    # Headings
    for i in range(1, 7):
        html = re.sub(
            rf"<h{i}[^>]*>(.*?)</h{i}>",
            lambda m, lvl=i: "\n" + "#" * lvl + " " + m.group(1).strip() + "\n",
            html, flags=re.DOTALL | re.IGNORECASE,
        )

    # Links
    html = re.sub(
        r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>(.*?)</a>',
        r"[\2](\1)",
        html, flags=re.DOTALL | re.IGNORECASE,
    )

    # Images
    html = re.sub(
        r'<img[^>]*src=["\']([^"\']*)["\'][^>]*alt=["\']([^"\']*)["\'][^>]*/?>',
        r"![\2](\1)",
        html, flags=re.IGNORECASE,
    )
    html = re.sub(
        r'<img[^>]*src=["\']([^"\']*)["\'][^>]*/?>',
        r"![image](\1)",
        html, flags=re.IGNORECASE,
    )

    # Bold / italic
    html = re.sub(r"<(strong|b)>(.*?)</\1>", r"**\2**", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<(em|i)>(.*?)</\1>", r"*\2*", html, flags=re.DOTALL | re.IGNORECASE)

    # Code
    html = re.sub(r"<code>(.*?)</code>", r"`\1`", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<pre[^>]*>(.*?)</pre>", r"```\n\1\n```", html, flags=re.DOTALL | re.IGNORECASE)

    # List items
    html = re.sub(r"<li[^>]*>(.*?)</li>", r"- \1\n", html, flags=re.DOTALL | re.IGNORECASE)

    # Paragraphs / divs → newlines
    html = re.sub(r"<(p|div|br|hr)[^>]*/?>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"</(p|div)>", "\n", html, flags=re.IGNORECASE)

    # Strip remaining tags
    html = re.sub(r"<[^>]+>", "", html)

    # Clean up whitespace
    html = re.sub(r"\n{3,}", "\n\n", html)
    return html.strip()


class BrowserTool(BaseTool):
    """Browser automation tool with stealth capabilities.

    Features:
    - Navigate to URLs
    - Click elements and type text with human-like patterns
    - Select dropdown options
    - Extract page content as text, HTML, or Markdown
    - Screenshot capture (full page or viewport)
    - Cookie and localStorage management
    - Human-like mouse/keyboard patterns (from CloakBrowser)
    - Anti-detection measures (from CloakBrowser stealth module)
    - Page wait strategies
    """

    def __init__(self, config: Optional[dict[str, Any]] = None) -> None:
        super().__init__(config)
        self._headless = self._config.get("headless", True)
        self._stealth_mode = self._config.get("stealth_mode", True)
        self._human_mode = self._config.get("human_mode", True)
        self._page_timeout = self._config.get("page_timeout", 30000)
        self._default_viewport = self._config.get(
            "viewport", {"width": 1280, "height": 720}
        )
        self._stealth_config = StealthConfig(
            hide_webdriver=self._config.get("hide_webdriver", True),
            mock_languages=self._config.get("mock_languages", ["en-US", "en"]),
            mock_plugins=self._config.get("mock_plugins", True),
            mock_permissions=self._config.get("mock_permissions", True),
            disable_automation_flags=self._config.get("disable_automation_flags", True),
            custom_user_agent=self._config.get("custom_user_agent", None),
            disable_images=self._config.get("disable_images", False),
            disable_css=self._config.get("disable_css", False),
        )
        self._human_behavior = HumanBehavior(
            min_delay=self._config.get("human_min_delay", 0.1),
            max_delay=self._config.get("human_max_delay", 0.5),
            typing_delay_min=self._config.get("typing_delay_min", 0.05),
            typing_delay_max=self._config.get("typing_delay_max", 0.15),
        )
        self._browser = None
        self._page = None
        self._playwright = None

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="browser",
            description="Web browser automation with stealth and human-like interaction",
            tool_type=ToolType.BROWSER,
            parameters=[
                ToolParameter(
                    name="action",
                    type="string",
                    description=(
                        "Browser action: navigate, click, type, select, scroll, "
                        "extract, screenshot, wait, go_back, go_forward, "
                        "get_cookies, set_cookies, evaluate"
                    ),
                    required=True,
                    enum=[
                        "navigate", "click", "type", "select", "scroll",
                        "extract", "screenshot", "wait", "go_back",
                        "go_forward", "get_cookies", "set_cookies", "evaluate",
                    ],
                ),
                ToolParameter(
                    name="url",
                    type="string",
                    description="URL to navigate to (for navigate action)",
                    required=False,
                ),
                ToolParameter(
                    name="selector",
                    type="string",
                    description="CSS/XPath selector (for click/type/select actions)",
                    required=False,
                ),
                ToolParameter(
                    name="text",
                    type="string",
                    description="Text to type (for type action)",
                    required=False,
                ),
                ToolParameter(
                    name="value",
                    type="string",
                    description="Value to select (for select action)",
                    required=False,
                ),
                ToolParameter(
                    name="direction",
                    type="string",
                    description="Scroll direction: up, down",
                    required=False,
                    default="down",
                    enum=["up", "down"],
                ),
                ToolParameter(
                    name="amount",
                    type="integer",
                    description="Scroll amount in pixels",
                    required=False,
                    default=500,
                ),
                ToolParameter(
                    name="wait_time",
                    type="integer",
                    description="Wait time in milliseconds (for wait action)",
                    required=False,
                    default=1000,
                ),
                ToolParameter(
                    name="extract_type",
                    type="string",
                    description="What to extract: text, html, markdown, links, images",
                    required=False,
                    default="text",
                    enum=["text", "html", "markdown", "links", "images"],
                ),
                ToolParameter(
                    name="full_page",
                    type="boolean",
                    description="Full page screenshot (for screenshot action)",
                    required=False,
                    default=False,
                ),
                ToolParameter(
                    name="script",
                    type="string",
                    description="JavaScript to evaluate (for evaluate action)",
                    required=False,
                ),
                ToolParameter(
                    name="cookies",
                    type="array",
                    description="Cookies to set (for set_cookies action)",
                    required=False,
                ),
            ],
            tags=["browser", "web", "automation", "stealth"],
            requires_permission="browser.use",
            timeout=60,
        )

    # ------------------------------------------------------------------
    # Browser lifecycle
    # ------------------------------------------------------------------

    async def _ensure_browser(self) -> None:
        """Ensure the browser is initialized with stealth settings."""
        if self._browser is not None:
            return

        try:
            from playwright.async_api import async_playwright

            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self._headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--disable-infobars",
                ],
            )
            context = await self._browser.new_context(
                viewport=self._default_viewport,
                locale="en-US",
                timezone_id="America/New_York",
            )
            self._page = await context.new_page()

            if self._stealth_mode:
                await apply_stealth(self._page, self._stealth_config)

            logger.debug("browser_initialized", stealth=self._stealth_mode, human=self._human_mode)

        except ImportError:
            raise ToolExecutionError(
                "Playwright not installed. Install with: pip install playwright && playwright install chromium",
                tool_name="browser",
            )

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    async def execute(self, tool_call: ToolCall) -> ToolResult:
        """Execute a browser action."""
        action = tool_call.arguments.get("action", "")

        if not action:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="browser",
                success=False, error="No action specified",
            )

        try:
            await self._ensure_browser()

            dispatch: dict[str, Any] = {
                "navigate": self._navigate,
                "click": self._click,
                "type": self._type,
                "select": self._select,
                "scroll": self._scroll,
                "extract": self._extract,
                "screenshot": self._screenshot,
                "wait": self._wait,
                "go_back": self._go_back,
                "go_forward": self._go_forward,
                "get_cookies": self._get_cookies,
                "set_cookies": self._set_cookies,
                "evaluate": self._evaluate,
            }

            handler = dispatch.get(action)
            if handler is None:
                return ToolResult(
                    tool_call_id=tool_call.id, tool_name="browser",
                    success=False, error=f"Unknown browser action: {action}",
                )
            return await handler(tool_call)

        except ToolExecutionError:
            raise
        except Exception as e:
            raise ToolExecutionError(f"Browser action failed: {e}", tool_name="browser")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    async def _navigate(self, tool_call: ToolCall) -> ToolResult:
        """Navigate to a URL."""
        url = tool_call.arguments.get("url", "")
        if not url:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="browser",
                success=False, error="No URL specified",
            )

        await self._page.goto(url, wait_until="domcontentloaded", timeout=self._page_timeout)

        if self._human_mode:
            await human_delay(0.3, 1.0)

        title = await self._page.title()
        current_url = self._page.url

        return ToolResult(
            tool_call_id=tool_call.id, tool_name="browser",
            success=True,
            output=f"Navigated to: {current_url}\nTitle: {title}",
            metadata={"url": current_url, "title": title},
        )

    async def _click(self, tool_call: ToolCall) -> ToolResult:
        """Click an element with optional human-like mouse movement."""
        selector = tool_call.arguments.get("selector", "")
        if not selector:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="browser",
                success=False, error="No selector specified",
            )

        if self._human_mode:
            try:
                await human_click(self._page, selector, self._human_behavior)
            except ValueError as e:
                return ToolResult(
                    tool_call_id=tool_call.id, tool_name="browser",
                    success=False, error=str(e),
                )
        else:
            await self._page.click(selector, timeout=self._page_timeout)

        if self._human_mode:
            await human_delay(0.1, 0.5)

        return ToolResult(
            tool_call_id=tool_call.id, tool_name="browser",
            success=True, output=f"Clicked element: {selector}",
        )

    async def _type(self, tool_call: ToolCall) -> ToolResult:
        """Type text into an element with optional human-like delays."""
        selector = tool_call.arguments.get("selector", "")
        text = tool_call.arguments.get("text", "")
        if not selector:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="browser",
                success=False, error="No selector specified",
            )

        if self._human_mode:
            try:
                await human_type(self._page, selector, text, self._human_behavior)
            except Exception as e:
                return ToolResult(
                    tool_call_id=tool_call.id, tool_name="browser",
                    success=False, error=f"Human type failed: {e}",
                )
        else:
            await self._page.fill(selector, text)

        return ToolResult(
            tool_call_id=tool_call.id, tool_name="browser",
            success=True, output=f"Typed text into: {selector}",
        )

    async def _select(self, tool_call: ToolCall) -> ToolResult:
        """Select an option in a dropdown element."""
        selector = tool_call.arguments.get("selector", "")
        value = tool_call.arguments.get("value", "")
        if not selector or not value:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="browser",
                success=False, error="selector and value are required for select action",
            )

        try:
            await self._page.select_option(selector, value, timeout=self._page_timeout)
        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="browser",
                success=False, error=f"Select failed: {e}",
            )

        return ToolResult(
            tool_call_id=tool_call.id, tool_name="browser",
            success=True, output=f"Selected '{value}' in: {selector}",
        )

    async def _scroll(self, tool_call: ToolCall) -> ToolResult:
        """Scroll the page with optional human-like behavior."""
        direction = tool_call.arguments.get("direction", "down")
        amount = tool_call.arguments.get("amount", 500)

        if self._human_mode:
            await human_scroll(self._page, direction, amount, self._human_behavior)
        else:
            delta = amount if direction == "down" else -amount
            await self._page.mouse.wheel(0, delta)

        return ToolResult(
            tool_call_id=tool_call.id, tool_name="browser",
            success=True, output=f"Scrolled {direction} by {amount}px",
        )

    async def _extract(self, tool_call: ToolCall) -> ToolResult:
        """Extract content from the page."""
        extract_type = tool_call.arguments.get("extract_type", "text")

        try:
            if extract_type == "text":
                content = await self._page.inner_text("body")
            elif extract_type == "html":
                content = await self._page.content()
            elif extract_type == "markdown":
                html = await self._page.content()
                content = _html_to_markdown(html)
            elif extract_type == "links":
                links = await self._page.eval_on_selector_all(
                    "a[href]",
                    "els => els.map(e => ({text: e.innerText.trim(), href: e.href}))",
                )
                content = "\n".join(
                    f"- [{l.get('text', 'N/A')}]({l.get('href', '')})" for l in links[:200]
                )
            elif extract_type == "images":
                images = await self._page.eval_on_selector_all(
                    "img[src]",
                    "els => els.map(e => ({alt: e.alt || '', src: e.src}))",
                )
                content = "\n".join(
                    f"- ![{im.get('alt', 'image')}]({im.get('src', '')})" for im in images[:200]
                )
            else:
                content = await self._page.inner_text("body")

            return ToolResult(
                tool_call_id=tool_call.id, tool_name="browser",
                success=True, output=content[:50000],
                metadata={"extract_type": extract_type},
            )
        except Exception as e:
            raise ToolExecutionError(f"Extraction failed: {e}", tool_name="browser")

    async def _screenshot(self, tool_call: ToolCall) -> ToolResult:
        """Take a screenshot of the current page."""
        full_page = tool_call.arguments.get("full_page", False)

        try:
            screenshot_bytes = await self._page.screenshot(full_page=full_page)
            b64 = base64.b64encode(screenshot_bytes).decode("utf-8")

            return ToolResult(
                tool_call_id=tool_call.id, tool_name="browser",
                success=True,
                output=f"Screenshot taken ({len(screenshot_bytes)} bytes, full_page={full_page})",
                metadata={
                    "screenshot_b64": b64,
                    "size_bytes": len(screenshot_bytes),
                    "full_page": full_page,
                },
            )
        except Exception as e:
            raise ToolExecutionError(f"Screenshot failed: {e}", tool_name="browser")

    async def _wait(self, tool_call: ToolCall) -> ToolResult:
        """Wait for a specified time or for a selector."""
        wait_time = tool_call.arguments.get("wait_time", 1000)
        selector = tool_call.arguments.get("selector")

        if selector:
            try:
                await self._page.wait_for_selector(selector, timeout=wait_time)
                return ToolResult(
                    tool_call_id=tool_call.id, tool_name="browser",
                    success=True, output=f"Element appeared: {selector}",
                )
            except Exception as e:
                return ToolResult(
                    tool_call_id=tool_call.id, tool_name="browser",
                    success=False, error=f"Wait for selector failed: {e}",
                )
        else:
            seconds = wait_time / 1000.0
            await asyncio.sleep(seconds)
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="browser",
                success=True, output=f"Waited {seconds}s",
            )

    async def _go_back(self, tool_call: ToolCall) -> ToolResult:
        """Go back in browser history."""
        await self._page.go_back()
        if self._human_mode:
            await human_delay(0.3, 0.8)
        title = await self._page.title()
        return ToolResult(
            tool_call_id=tool_call.id, tool_name="browser",
            success=True, output=f"Went back. Title: {title}",
        )

    async def _go_forward(self, tool_call: ToolCall) -> ToolResult:
        """Go forward in browser history."""
        await self._page.go_forward()
        if self._human_mode:
            await human_delay(0.3, 0.8)
        title = await self._page.title()
        return ToolResult(
            tool_call_id=tool_call.id, tool_name="browser",
            success=True, output=f"Went forward. Title: {title}",
        )

    async def _get_cookies(self, tool_call: ToolCall) -> ToolResult:
        """Get cookies for the current page."""
        context = self._page.context
        cookies = await context.cookies()
        return ToolResult(
            tool_call_id=tool_call.id, tool_name="browser",
            success=True,
            output=f"Found {len(cookies)} cookies",
            metadata={"cookies": cookies},
        )

    async def _set_cookies(self, tool_call: ToolCall) -> ToolResult:
        """Set cookies for the current page."""
        cookies = tool_call.arguments.get("cookies", [])
        if not cookies:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="browser",
                success=False, error="No cookies provided",
            )

        context = self._page.context
        await context.add_cookies(cookies)
        return ToolResult(
            tool_call_id=tool_call.id, tool_name="browser",
            success=True, output=f"Set {len(cookies)} cookie(s)",
        )

    async def _evaluate(self, tool_call: ToolCall) -> ToolResult:
        """Evaluate JavaScript on the page."""
        script = tool_call.arguments.get("script", "")
        if not script:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="browser",
                success=False, error="No script provided",
            )

        try:
            result = await self._page.evaluate(script)
            output = str(result) if result is not None else "null"
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="browser",
                success=True, output=output[:10000],
            )
        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="browser",
                success=False, error=f"JavaScript evaluation failed: {e}",
            )

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Close the browser and clean up resources."""
        if self._browser:
            try:
                await self._browser.close()
            except Exception as e:
                logger.warning("browser_close_error", error=str(e))
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception as e:
                logger.warning("playwright_stop_error", error=str(e))
        self._browser = None
        self._page = None
        self._playwright = None
