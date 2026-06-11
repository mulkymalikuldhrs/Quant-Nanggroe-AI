"""BrowserTool – browser automation with navigation, interaction, and extraction.

Autonomy levels vary by action:
  - L0: navigate, screenshot, extract, wait_for, get_cookies
  - L1: click, type, scroll, set_cookies
  - L2: execute_js, delete_cookies
"""

from __future__ import annotations

import base64
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from .base import MCPTool

logger = logging.getLogger(__name__)


class BrowserTab:
    """Represents a single browser tab with its state."""

    def __init__(self, tab_id: str, url: str = "about:blank") -> None:
        self.tab_id = tab_id
        self.url = url
        self.title = ""
        self.status_code: int = 200
        self.content: str = ""
        self.cookies: Dict[str, Dict[str, Any]] = {}
        self.history: List[str] = [url]
        self.screenshot_data: Optional[str] = None
        self.element_store: Dict[str, Dict[str, Any]] = {}  # selector -> element info

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tab_id": self.tab_id,
            "url": self.url,
            "title": self.title,
            "status_code": self.status_code,
            "cookie_count": len(self.cookies),
            "history_length": len(self.history),
        }


class BrowserTool(MCPTool):
    """Browser automation: navigate, interact, extract, and capture.

    This is a simulated browser for the MCP layer.  Real Playwright /
    Puppeteer integration would replace the simulation internals while
    keeping the same interface.
    """

    # ── MCPTool interface ────────────────────────────────────────

    def name(self) -> str:
        return "browser.control"

    def category(self) -> str:
        return "browser"

    def autonomy_level(self) -> int:
        return 0  # minimum; varies per action

    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["action"],
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "navigate", "click", "type", "extract",
                        "screenshot", "scroll", "wait_for",
                        "execute_js", "get_cookies", "set_cookies",
                        "delete_cookies", "new_tab", "close_tab",
                        "list_tabs", "switch_tab", "go_back", "go_forward",
                    ],
                    "description": "Browser action to perform",
                },
                "url": {"type": "string", "description": "URL for navigate"},
                "selector": {"type": "string", "description": "CSS selector for element"},
                "text": {"type": "string", "description": "Text to type"},
                "direction": {
                    "type": "string",
                    "enum": ["up", "down"],
                    "default": "down",
                },
                "pixels": {"type": "integer", "default": 300},
                "script": {"type": "string", "description": "JavaScript to execute"},
                "timeout_ms": {"type": "integer", "default": 5000},
                "cookies": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Cookies to set",
                },
                "tab_id": {"type": "string", "description": "Tab identifier"},
                "extract_type": {
                    "type": "string",
                    "enum": ["text", "html", "links", "images"],
                    "default": "text",
                },
            },
        }

    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "action": {"type": "string"},
                "data": {"type": "object"},
            },
        }

    def error_codes(self) -> List[Dict[str, Any]]:
        return [
            {"code": 3001, "message": "Navigation failed"},
            {"code": 3002, "message": "Element not found"},
            {"code": 3003, "message": "Timeout waiting for element"},
            {"code": 3004, "message": "JavaScript execution error"},
            {"code": 3005, "message": "Tab not found"},
            {"code": 3006, "message": "Cookie operation failed"},
        ]

    # ── Constructor ──────────────────────────────────────────────

    def __init__(self) -> None:
        super().__init__()
        self._tabs: Dict[str, BrowserTab] = {}
        self._active_tab: Optional[str] = None
        # Start with one default tab
        default = BrowserTab(tab_id="tab-default")
        self._tabs[default.tab_id] = default
        self._active_tab = default.tab_id

    # ── Autonomy mapping ─────────────────────────────────────────

    @staticmethod
    def action_autonomy(action: str) -> int:
        """Return the required autonomy level for a given action."""
        mapping = {
            "navigate": 0, "screenshot": 0, "extract": 0,
            "wait_for": 0, "get_cookies": 0, "list_tabs": 0,
            "go_back": 0, "go_forward": 0, "new_tab": 0,
            "click": 1, "type": 1, "scroll": 1, "set_cookies": 1,
            "switch_tab": 1, "close_tab": 1,
            "execute_js": 2, "delete_cookies": 2,
        }
        return mapping.get(action, 2)

    # ── Execute ──────────────────────────────────────────────────

    async def execute(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        action: str = params["action"]
        autonomy = context.get("autonomy_level", 0)
        required = self.action_autonomy(action)

        if autonomy < required:
            self.record_call(False)
            return {
                "success": False,
                "action": action,
                "data": {
                    "error": f"Action '{action}' requires L{required}, current level is L{autonomy}",
                    "required_level": required,
                    "current_level": autonomy,
                },
            }

        dispatch = {
            "navigate": self._navigate,
            "click": self._click,
            "type": self._type,
            "extract": self._extract,
            "screenshot": self._screenshot,
            "scroll": self._scroll,
            "wait_for": self._wait_for,
            "execute_js": self._execute_js,
            "get_cookies": self._get_cookies,
            "set_cookies": self._set_cookies,
            "delete_cookies": self._delete_cookies,
            "new_tab": self._new_tab,
            "close_tab": self._close_tab,
            "list_tabs": self._list_tabs,
            "switch_tab": self._switch_tab,
            "go_back": self._go_back,
            "go_forward": self._go_forward,
        }

        handler = dispatch.get(action)
        if handler is None:
            self.record_call(False)
            return {
                "success": False,
                "action": action,
                "data": {"error": f"Unknown action: {action}"},
            }

        start = time.monotonic()
        try:
            result = await handler(params)
            duration = (time.monotonic() - start) * 1000
            self.record_call(result.get("success", True), duration)
            result["action"] = action
            return result
        except Exception as exc:
            duration = (time.monotonic() - start) * 1000
            self.record_call(False, duration)
            return {"success": False, "action": action, "data": {"error": str(exc)}}

    # ── Action implementations ───────────────────────────────────

    def _active(self) -> BrowserTab:
        if self._active_tab and self._active_tab in self._tabs:
            return self._tabs[self._active_tab]
        # Fallback: pick any tab
        if self._tabs:
            first = next(iter(self._tabs))
            self._active_tab = first
            return self._tabs[first]
        default = BrowserTab(tab_id="tab-default")
        self._tabs[default.tab_id] = default
        self._active_tab = default.tab_id
        return default

    async def _navigate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        url = params.get("url", "about:blank")
        tab = self._active()
        tab.url = url
        tab.status_code = 200
        tab.title = f"Page: {url}"
        tab.content = f"<html><body><h1>{url}</h1><p>Simulated page content</p></body></html>"
        tab.history.append(url)
        return {"success": True, "data": {"url": url, "status_code": 200, "title": tab.title}}

    async def _click(self, params: Dict[str, Any]) -> Dict[str, Any]:
        selector = params.get("selector", "")
        tab = self._active()
        # Simulate clicking: store that the element was clicked
        tab.element_store[selector] = {"clicked": True, "timestamp": time.time()}
        return {"success": True, "data": {"selector": selector, "clicked": True}}

    async def _type(self, params: Dict[str, Any]) -> Dict[str, Any]:
        selector = params.get("selector", "")
        text = params.get("text", "")
        tab = self._active()
        tab.element_store[selector] = {"typed": text, "timestamp": time.time()}
        return {"success": True, "data": {"selector": selector, "typed": text, "length": len(text)}}

    async def _extract(self, params: Dict[str, Any]) -> Dict[str, Any]:
        extract_type = params.get("extract_type", "text")
        selector = params.get("selector", "body")
        tab = self._active()

        if extract_type == "text":
            content = f"Extracted text content from {tab.url} [{selector}]"
        elif extract_type == "html":
            content = f"<div>{tab.content}</div>"
        elif extract_type == "links":
            content = [
                {"text": "Link 1", "href": f"{tab.url}/page1"},
                {"text": "Link 2", "href": f"{tab.url}/page2"},
            ]
        elif extract_type == "images":
            content = [
                {"src": f"{tab.url}/img1.png", "alt": "Image 1"},
                {"src": f"{tab.url}/img2.png", "alt": "Image 2"},
            ]
        else:
            content = f"Extracted {extract_type} from {tab.url}"

        return {"success": True, "data": {"content": content, "type": extract_type, "url": tab.url}}

    async def _screenshot(self, params: Dict[str, Any]) -> Dict[str, Any]:
        tab = self._active()
        # Simulate screenshot as a small base64 PNG
        fake_png = base64.b64encode(b"SIMULATED_PNG_DATA").decode()
        tab.screenshot_data = fake_png
        return {
            "success": True,
            "data": {
                "format": "png",
                "size_bytes": len(fake_png),
                "base64": fake_png,
                "url": tab.url,
            },
        }

    async def _scroll(self, params: Dict[str, Any]) -> Dict[str, Any]:
        direction = params.get("direction", "down")
        pixels = params.get("pixels", 300)
        return {"success": True, "data": {"direction": direction, "pixels": pixels}}

    async def _wait_for(self, params: Dict[str, Any]) -> Dict[str, Any]:
        selector = params.get("selector", "body")
        timeout_ms = params.get("timeout_ms", 5000)
        # Simulate waiting – always succeeds immediately
        return {
            "success": True,
            "data": {
                "selector": selector,
                "found": True,
                "wait_time_ms": 0,
                "timeout_ms": timeout_ms,
            },
        }

    async def _execute_js(self, params: Dict[str, Any]) -> Dict[str, Any]:
        script = params.get("script", "")
        tab = self._active()
        # Simulate JS execution
        result = f"JS executed on {tab.url}: {script[:100]}..."
        return {"success": True, "data": {"result": result, "url": tab.url}}

    async def _get_cookies(self, params: Dict[str, Any]) -> Dict[str, Any]:
        tab = self._active()
        cookies = [
            {"name": k, **v} for k, v in tab.cookies.items()
        ]
        return {"success": True, "data": {"cookies": cookies, "count": len(cookies), "url": tab.url}}

    async def _set_cookies(self, params: Dict[str, Any]) -> Dict[str, Any]:
        tab = self._active()
        cookies_list = params.get("cookies", [])
        for cookie in cookies_list:
            name = cookie.get("name", "unknown")
            tab.cookies[name] = {
                "value": cookie.get("value", ""),
                "domain": cookie.get("domain", tab.url),
                "path": cookie.get("path", "/"),
                "secure": cookie.get("secure", False),
                "httpOnly": cookie.get("httpOnly", False),
            }
        return {
            "success": True,
            "data": {"set_count": len(cookies_list), "total_cookies": len(tab.cookies)},
        }

    async def _delete_cookies(self, params: Dict[str, Any]) -> Dict[str, Any]:
        tab = self._active()
        names = params.get("cookie_names", [])
        deleted = 0
        for name in names:
            if name in tab.cookies:
                del tab.cookies[name]
                deleted += 1
        if not names:
            count = len(tab.cookies)
            tab.cookies.clear()
            return {"success": True, "data": {"deleted_all": count}}
        return {"success": True, "data": {"deleted": deleted, "names": names}}

    async def _new_tab(self, params: Dict[str, Any]) -> Dict[str, Any]:
        url = params.get("url", "about:blank")
        tab_id = f"tab-{uuid.uuid4().hex[:8]}"
        tab = BrowserTab(tab_id=tab_id, url=url)
        tab.title = f"New Tab: {url}"
        self._tabs[tab_id] = tab
        self._active_tab = tab_id
        return {"success": True, "data": {"tab_id": tab_id, "url": url}}

    async def _close_tab(self, params: Dict[str, Any]) -> Dict[str, Any]:
        tab_id = params.get("tab_id", self._active_tab)
        if tab_id not in self._tabs:
            return {"success": False, "data": {"error": f"Tab not found: {tab_id}"}}
        del self._tabs[tab_id]
        if self._active_tab == tab_id:
            self._active_tab = next(iter(self._tabs), None)
        return {"success": True, "data": {"closed": tab_id}}

    async def _list_tabs(self, params: Dict[str, Any]) -> Dict[str, Any]:
        tabs = [t.to_dict() for t in self._tabs.values()]
        return {"success": True, "data": {"tabs": tabs, "active": self._active_tab, "count": len(tabs)}}

    async def _switch_tab(self, params: Dict[str, Any]) -> Dict[str, Any]:
        tab_id = params.get("tab_id", "")
        if tab_id not in self._tabs:
            return {"success": False, "data": {"error": f"Tab not found: {tab_id}"}}
        self._active_tab = tab_id
        tab = self._tabs[tab_id]
        return {"success": True, "data": {"active_tab": tab_id, "url": tab.url}}

    async def _go_back(self, params: Dict[str, Any]) -> Dict[str, Any]:
        tab = self._active()
        if len(tab.history) > 1:
            tab.history.pop()
            tab.url = tab.history[-1]
            return {"success": True, "data": {"url": tab.url}}
        return {"success": False, "data": {"error": "No history to go back to"}}

    async def _go_forward(self, params: Dict[str, Any]) -> Dict[str, Any]:
        # Simulated – forward navigation
        tab = self._active()
        return {"success": True, "data": {"url": tab.url, "message": "No forward history"}}
