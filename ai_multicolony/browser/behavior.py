from __future__ import annotations
"""Human-like behavior simulation for browser automation."""
import logging

import random
import time
import math
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


class HumanBehavior:
    """Simulates human-like browser behavior."""

    def __init__(self, typing_speed_wpm: int = 40, click_delay_ms: int = 200):
        self.typing_speed_wpm = typing_speed_wpm
        self.click_delay_ms = click_delay_ms

    def get_typing_delay(self, char: str) -> float:
        """Get delay between keystrokes."""
        base = 60000 / (self.typing_speed_wpm * 5)  # ms per char
        jitter = random.uniform(0.5, 1.5)
        if char in " .,":
            jitter *= 2  # Longer pause on spaces/punctuation
        return base * jitter / 1000

    def get_click_position(self, element_x: int, element_y: int, element_width: int, element_height: int) -> Tuple[int, int]:
        """Get a random position within an element for clicking."""
        padding = 0.2
        x = element_x + element_width * random.uniform(padding, 1 - padding)
        y = element_y + element_height * random.uniform(padding, 1 - padding)
        return int(x), int(y)

    def generate_mouse_path(self, start: Tuple[int, int], end: Tuple[int, int], steps: int = 20) -> List[Tuple[int, int]]:
        """Generate a human-like mouse movement path."""
        path = []
        for i in range(steps + 1):
            t = i / steps
            # Bezier curve with random control points
            cx1 = start[0] + (end[0] - start[0]) * 0.3 + random.uniform(-50, 50)
            cy1 = start[1] + (end[1] - start[1]) * 0.3 + random.uniform(-50, 50)
            cx2 = start[0] + (end[0] - start[0]) * 0.7 + random.uniform(-50, 50)
            cy2 = start[1] + (end[1] - start[1]) * 0.7 + random.uniform(-50, 50)
            x = (1-t)**3 * start[0] + 3*(1-t)**2*t * cx1 + 3*(1-t)*t**2 * cx2 + t**3 * end[0]
            y = (1-t)**3 * start[1] + 3*(1-t)**2*t * cy1 + 3*(1-t)*t**2 * cy2 + t**3 * end[1]
            path.append((int(x), int(y)))
        return path

    def get_scroll_amount(self) -> int:
        """Get a human-like scroll amount."""
        return random.randint(100, 500)

    def get_page_view_time(self) -> float:
        """Get time to simulate reading a page."""
        return random.uniform(2.0, 8.0)
