"""Stealth browser patterns from CloakBrowser."""

from __future__ import annotations
import logging
import random
import time
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class StealthConfig:
    """Configuration for stealth browser mode."""
    def __init__(self):
        self.webgl_vendor = "Google Inc."
        self.webgl_renderer = "ANGLE"
        self.navigator_platform = "Win32"
        self.navigator_languages = ["en-US", "en"]
        self.screen_width = 1920
        self.screen_height = 1080
        self.target_recaptcha_score = 0.9
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        ]

    def get_random_user_agent(self) -> str:
        return random.choice(self.user_agents)


class StealthPatterns:
    """Stealth patterns for undetectable browser automation."""

    def __init__(self, config: Optional[StealthConfig] = None):
        from typing import Optional
        self.config = config or StealthConfig()

    def apply_stealth_scripts(self) -> List[str]:
        """Return stealth JavaScript patches."""
        return [
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})",
            "Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})",
            f"Object.defineProperty(screen, 'width', {{get: () => {self.config.screen_width}}})",
            f"Object.defineProperty(screen, 'height', {{get: () => {self.config.screen_height}}})",
        ]

    def check_stealth_score(self) -> float:
        """Simulate stealth score check."""
        return self.config.target_recaptcha_score

    def generate_fingerprint(self) -> Dict[str, Any]:
        """Generate a browser fingerprint."""
        return {
            "user_agent": self.config.get_random_user_agent(),
            "screen": f"{self.config.screen_width}x{self.config.screen_height}",
            "platform": self.config.navigator_platform,
            "languages": self.config.navigator_languages,
            "webgl": f"{self.config.webgl_vendor} - {self.config.webgl_renderer}",
        }
