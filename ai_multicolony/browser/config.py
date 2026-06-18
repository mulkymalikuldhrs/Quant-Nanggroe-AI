"""Browser configuration with proxy, viewport, locale, and timezone settings."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BrowserConfig:
    """Configuration for browser automation.

    Consolidates browser settings from CloakBrowser and Playwright
    with proxy, viewport, locale, and timezone support.
    """

    # Browser engine
    headless: bool = True
    browser_type: str = "chromium"  # chromium, firefox, webkit

    # Viewport
    viewport_width: int = 1920
    viewport_height: int = 1080

    # Timeouts
    page_timeout: int = 30000  # ms
    navigation_timeout: int = 60000  # ms

    # Stealth
    stealth_mode: bool = True
    disable_images: bool = False
    disable_css: bool = False
    user_agent: Optional[str] = None

    # Proxy
    proxy_server: Optional[str] = None
    proxy_username: Optional[str] = None
    proxy_password: Optional[str] = None
    proxy_bypass: Optional[str] = None

    # Locale and timezone
    locale: str = "en-US"
    timezone: str = "America/New_York"
    geolocation: Optional[dict[str, float]] = None
    permissions: list[str] = field(default_factory=lambda: ["geolocation"])

    # Network
    extra_headers: dict[str, str] = field(default_factory=dict)
    ignore_https_errors: bool = True
    offline: bool = False

    # Human behavior settings
    human_delays: bool = True
    typing_delay_ms: int = 50
    click_delay_ms: int = 100

    # Screenshot settings
    screenshot_format: str = "png"
    screenshot_quality: int = 80
    full_page_screenshots: bool = False

    # Storage
    storage_state: Optional[str] = None  # Path to storage state file
    record_har: Optional[str] = None  # Path to HAR file for recording

    def to_playwright_kwargs(self) -> dict:
        """Convert to Playwright browser launch keyword arguments.

        Returns:
            Dictionary of Playwright launch arguments.
        """
        kwargs: dict[str, dict] = {
            "context": {},
            "launch": {},
        }

        # Context options
        kwargs["context"]["viewport"] = {
            "width": self.viewport_width,
            "height": self.viewport_height,
        }
        kwargs["context"]["locale"] = self.locale
        kwargs["context"]["timezone_id"] = self.timezone
        kwargs["context"]["ignore_https_errors"] = self.ignore_https_errors

        if self.user_agent:
            kwargs["context"]["user_agent"] = self.user_agent
        if self.geolocation:
            kwargs["context"]["geolocation"] = self.geolocation
        if self.permissions:
            kwargs["context"]["permissions"] = self.permissions
        if self.extra_headers:
            kwargs["context"]["extra_http_headers"] = self.extra_headers
        if self.storage_state:
            kwargs["context"]["storage_state"] = self.storage_state
        if self.offline:
            kwargs["context"]["offline"] = True
        if self.record_har:
            kwargs["context"]["record_har"] = self.record_har

        # Launch options
        kwargs["launch"]["headless"] = self.headless
        kwargs["launch"]["args"] = [
            "--disable-blink-features=AutomationControlled",
        ]

        if self.proxy_server:
            proxy: dict[str, str] = {"server": self.proxy_server}
            if self.proxy_username:
                proxy["username"] = self.proxy_username
            if self.proxy_password:
                proxy["password"] = self.proxy_password
            if self.proxy_bypass:
                proxy["bypass"] = self.proxy_bypass
            kwargs["launch"]["proxy"] = proxy

        return kwargs

    def to_stealth_config(self) -> dict:
        """Convert to StealthConfig-compatible dictionary.

        Returns:
            Dictionary of stealth configuration options.
        """
        return {
            "hide_webdriver": self.stealth_mode,
            "custom_user_agent": self.user_agent,
            "disable_images": self.disable_images,
            "disable_css": self.disable_css,
            "proxy_server": self.proxy_server,
            "proxy_username": self.proxy_username,
            "proxy_password": self.proxy_password,
        }
