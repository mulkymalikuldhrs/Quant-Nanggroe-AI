"""Human-like browser interaction patterns.

Provides realistic Mouse, Keyboard, and Scroll behavior with
async variants and actionability checks from CloakBrowser patterns.
"""

from __future__ import annotations

import asyncio
import math
import random
from dataclasses import dataclass
from typing import Any, Optional, Tuple

from ai_multicolony.config.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class HumanBehavior:
    """Configuration for human-like browser behavior.

    From CloakBrowser patterns for realistic interaction simulation.
    """

    min_delay: float = 0.1
    max_delay: float = 0.5
    typing_delay_min: float = 0.05
    typing_delay_max: float = 0.15
    scroll_amount_min: int = 100
    scroll_amount_max: int = 400
    mouse_steps_min: int = 10
    mouse_steps_max: int = 30
    click_offset_max: int = 5  # Max pixel offset from center


async def human_delay(min_seconds: float = 0.1, max_seconds: float = 0.5) -> None:
    """Introduce a random human-like delay.

    Args:
        min_seconds: Minimum delay.
        max_seconds: Maximum delay.
    """
    delay = random.uniform(min_seconds, max_seconds)
    await asyncio.sleep(delay)


class Mouse:
    """Human-like mouse interactions.

    Provides realistic mouse movement with bezier curves,
    natural clicking, and actionability checks.
    """

    def __init__(self, page: Any, behavior: Optional[HumanBehavior] = None) -> None:
        self._page = page
        self._behavior = behavior or HumanBehavior()
        self._position: Tuple[float, float] = (0, 0)

    async def move_to(self, x: float, y: float, steps: Optional[int] = None) -> None:
        """Move the mouse to coordinates with human-like movement.

        Args:
            x: Target X coordinate.
            y: Target Y coordinate.
            steps: Number of intermediate steps. Random if None.
        """
        if steps is None:
            steps = random.randint(self._behavior.mouse_steps_min, self._behavior.mouse_steps_max)

        start_x, start_y = self._position

        for i in range(steps):
            progress = (i + 1) / steps

            # Bezier curve approximation with slight randomness
            t = progress
            mid_x = (start_x + x) / 2 + random.uniform(-20, 20)
            mid_y = (start_y + y) / 2 + random.uniform(-20, 20)

            # Quadratic bezier
            curr_x = (1 - t) ** 2 * start_x + 2 * (1 - t) * t * mid_x + t ** 2 * x
            curr_y = (1 - t) ** 2 * start_y + 2 * (1 - t) * t * mid_y + t ** 2 * y

            # Add jitter
            curr_x += random.uniform(-1, 1)
            curr_y += random.uniform(-1, 1)

            await self._page.mouse.move(curr_x, curr_y)
            await asyncio.sleep(random.uniform(0.005, 0.02))

        self._position = (x, y)

    async def click(self, x: float, y: float, button: str = "left", click_count: int = 1) -> None:
        """Click at coordinates with human-like movement.

        Args:
            x: Target X coordinate.
            y: Target Y coordinate.
            button: Mouse button (left, right, middle).
            click_count: Number of clicks (1 for single, 2 for double).
        """
        await self.move_to(x, y)
        await human_delay(0.05, 0.15)
        await self._page.mouse.click(x, y, button=button, click_count=click_count)

    async def click_element(self, selector: str) -> None:
        """Click an element with human-like mouse movement.

        Args:
            selector: CSS selector for the element.
        """
        element = await self._page.query_selector(selector)
        if not element:
            raise ValueError(f"Element not found: {selector}")

        # Check actionability
        await self._check_actionable(element)

        box = await element.bounding_box()
        if not box:
            raise ValueError(f"Element has no bounding box: {selector}")

        target_x = box["x"] + box["width"] / 2 + random.uniform(-self._behavior.click_offset_max, self._behavior.click_offset_max)
        target_y = box["y"] + box["height"] / 2 + random.uniform(-self._behavior.click_offset_max, self._behavior.click_offset_max)

        await self.click(target_x, target_y)

    async def right_click(self, x: float, y: float) -> None:
        """Right-click at coordinates."""
        await self.move_to(x, y)
        await human_delay(0.05, 0.1)
        await self._page.mouse.click(x, y, button="right")

    async def hover(self, selector: str) -> None:
        """Hover over an element.

        Args:
            selector: CSS selector for the element.
        """
        element = await self._page.query_selector(selector)
        if not element:
            raise ValueError(f"Element not found: {selector}")

        box = await element.bounding_box()
        if not box:
            raise ValueError(f"Element has no bounding box: {selector}")

        x = box["x"] + box["width"] / 2
        y = box["y"] + box["height"] / 2

        await self.move_to(x, y)
        await human_delay(0.1, 0.3)

    async def drag_and_drop(self, source_selector: str, target_selector: str) -> None:
        """Drag an element to a target.

        Args:
            source_selector: CSS selector for the source element.
            target_selector: CSS selector for the target element.
        """
        source = await self._page.query_selector(source_selector)
        target = await self._page.query_selector(target_selector)
        if not source or not target:
            raise ValueError("Source or target element not found")

        source_box = await source.bounding_box()
        target_box = await target.bounding_box()
        if not source_box or not target_box:
            raise ValueError("Elements have no bounding boxes")

        sx = source_box["x"] + source_box["width"] / 2
        sy = source_box["y"] + source_box["height"] / 2
        tx = target_box["x"] + target_box["width"] / 2
        ty = target_box["y"] + target_box["height"] / 2

        await self.move_to(sx, sy)
        await self._page.mouse.down()
        await human_delay(0.1, 0.2)
        await self.move_to(tx, ty)
        await human_delay(0.05, 0.1)
        await self._page.mouse.up()

    async def _check_actionable(self, element: Any) -> None:
        """Check if an element is actionable (visible, enabled).

        Args:
            element: The Playwright element handle.

        Raises:
            ValueError: If the element is not actionable.
        """
        is_visible = await element.is_visible()
        if not is_visible:
            raise ValueError("Element is not visible")

        is_enabled = await element.is_enabled()
        if not is_enabled:
            raise ValueError("Element is not enabled")

    @property
    def position(self) -> Tuple[float, float]:
        """Get current mouse position."""
        return self._position


class Keyboard:
    """Human-like keyboard interactions.

    Provides realistic typing with variable delays,
    keyboard shortcuts, and modifier key support.
    """

    def __init__(self, page: Any, behavior: Optional[HumanBehavior] = None) -> None:
        self._page = page
        self._behavior = behavior or HumanBehavior()

    async def type_text(self, selector: str, text: str, clear: bool = True) -> None:
        """Type text with human-like delays between keystrokes.

        Args:
            selector: CSS selector for the input element.
            text: Text to type.
            clear: Whether to clear the field first.
        """
        element = await self._page.query_selector(selector)
        if not element:
            raise ValueError(f"Element not found: {selector}")

        await element.click()
        await human_delay(self._behavior.min_delay, self._behavior.max_delay)

        if clear:
            # Select all and delete
            await self._page.keyboard.press("Control+a")
            await self._page.keyboard.press("Backspace")
            await human_delay(0.05, 0.1)

        for char in text:
            delay_ms = random.randint(
                int(self._behavior.typing_delay_min * 1000),
                int(self._behavior.typing_delay_max * 1000),
            )
            await self._page.keyboard.type(char, delay=delay_ms)

            # Occasional longer pause (thinking)
            if random.random() < 0.05:
                await human_delay(0.2, 0.5)

    async def press_key(self, key: str) -> None:
        """Press a single key.

        Args:
            key: Key name (e.g., 'Enter', 'Tab', 'Escape').
        """
        await self._page.keyboard.press(key)
        await human_delay(0.05, 0.15)

    async def press_shortcut(self, *keys: str) -> None:
        """Press a keyboard shortcut (combination of keys).

        Args:
            keys: Key names (e.g., 'Control', 'c' for Ctrl+C).
        """
        combination = "+".join(keys)
        await self._page.keyboard.press(combination)
        await human_delay(0.05, 0.15)

    async def type_slowly(self, selector: str, text: str) -> None:
        """Type text very slowly for sensitive fields.

        Args:
            selector: CSS selector for the input element.
            text: Text to type.
        """
        element = await self._page.query_selector(selector)
        if not element:
            raise ValueError(f"Element not found: {selector}")

        await element.click()
        await human_delay(0.2, 0.4)

        for char in text:
            delay_ms = random.randint(80, 200)
            await self._page.keyboard.type(char, delay=delay_ms)
            if random.random() < 0.1:
                await human_delay(0.3, 0.8)


class Scroll:
    """Human-like scroll interactions.

    Provides realistic scrolling with incremental movements,
    variable speeds, and natural pauses.
    """

    def __init__(self, page: Any, behavior: Optional[HumanBehavior] = None) -> None:
        self._page = page
        self._behavior = behavior or HumanBehavior()

    async def down(self, amount: Optional[int] = None) -> None:
        """Scroll down with human-like behavior.

        Args:
            amount: Scroll amount in pixels. Random if None.
        """
        if amount is None:
            amount = random.randint(self._behavior.scroll_amount_min, self._behavior.scroll_amount_max)

        await self._scroll(amount, "down")

    async def up(self, amount: Optional[int] = None) -> None:
        """Scroll up with human-like behavior.

        Args:
            amount: Scroll amount in pixels. Random if None.
        """
        if amount is None:
            amount = random.randint(self._behavior.scroll_amount_min, self._behavior.scroll_amount_max)

        await self._scroll(amount, "up")

    async def to_bottom(self) -> None:
        """Scroll to the bottom of the page."""
        for _ in range(random.randint(3, 8)):
            await self.down(random.randint(200, 500))
            await human_delay(0.3, 0.8)

    async def to_top(self) -> None:
        """Scroll to the top of the page."""
        for _ in range(random.randint(3, 8)):
            await self.up(random.randint(200, 500))
            await human_delay(0.3, 0.8)

    async def to_element(self, selector: str) -> None:
        """Scroll to make an element visible.

        Args:
            selector: CSS selector for the element.
        """
        element = await self._page.query_selector(selector)
        if element:
            await element.scroll_into_view_if_needed()
            await human_delay(0.1, 0.3)

    async def _scroll(self, amount: int, direction: str) -> None:
        """Perform a scroll with incremental movements.

        Args:
            amount: Total scroll amount in pixels.
            direction: Scroll direction ("up" or "down").
        """
        increments = random.randint(2, 5)
        increment_amount = amount // increments

        for _ in range(increments):
            delta = increment_amount if direction == "down" else -increment_amount
            # Add slight variation
            delta += random.randint(-10, 10)
            await self._page.mouse.wheel(0, delta)
            await human_delay(0.05, 0.2)


# Backward-compatible module-level functions

async def human_type(page: Any, selector: str, text: str, behavior: Optional[HumanBehavior] = None) -> None:
    """Type text with human-like delays between keystrokes.

    Args:
        page: The Playwright page.
        selector: CSS selector for the input element.
        text: Text to type.
        behavior: Human behavior configuration.
    """
    kb = Keyboard(page, behavior)
    await kb.type_text(selector, text)


async def human_scroll(page: Any, direction: str = "down", amount: Optional[int] = None, behavior: Optional[HumanBehavior] = None) -> None:
    """Scroll with human-like behavior.

    Args:
        page: The Playwright page.
        direction: Scroll direction ("up" or "down").
        amount: Scroll amount in pixels. Random if None.
        behavior: Human behavior configuration.
    """
    scroller = Scroll(page, behavior)
    if direction == "down":
        await scroller.down(amount)
    else:
        await scroller.up(amount)


async def human_click(page: Any, selector: str, behavior: Optional[HumanBehavior] = None) -> None:
    """Click an element with human-like mouse movement.

    Args:
        page: The Playwright page.
        selector: CSS selector for the element.
        behavior: Human behavior configuration.
    """
    mouse = Mouse(page, behavior)
    await mouse.click_element(selector)


async def human_mouse_move(page: Any, target_x: float, target_y: float, behavior: Optional[HumanBehavior] = None) -> None:
    """Move the mouse with human-like bezier curve movement.

    Args:
        page: The Playwright page.
        target_x: Target X coordinate.
        target_y: Target Y coordinate.
        behavior: Human behavior configuration.
    """
    mouse = Mouse(page, behavior)
    await mouse.move_to(target_x, target_y)
