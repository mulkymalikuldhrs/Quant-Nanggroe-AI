"""Self-Correct module for QNA autonomous hedge fund.

Companion to self_aware.py — SelfAware detects anomalies, SelfCorrect
records lessons, searches past resolutions, and retries failed operations
with configurable strategies.

Dependency-light (stdlib + json) like self_aware.py.
"""
from __future__ import annotations

import json
import logging
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

LESSONS_PATH = Path(__file__).parent.parent / "data" / "lessons.json"


class LessonCategory(str, Enum):
    DATA_FETCH = "data_fetch"
    SIGNAL_GEN = "signal_gen"
    EXECUTION = "execution"
    RISK = "risk"
    PIPELINE = "pipeline"
    LLM = "llm"
    CONFIG = "config"
    NETWORK = "network"
    OTHER = "other"


class LessonSeverity(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class RetryMode(str, Enum):
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    JITTERED = "jittered"


@dataclass
class Lesson:
    id: str
    category: str
    severity: str
    summary: str
    detail: str
    context: Dict[str, Any] = field(default_factory=dict)
    occurred_at: str = ""
    resolved: bool = False
    resolution: str = ""

    def __post_init__(self):
        if not self.occurred_at:
            self.occurred_at = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())


@dataclass
class RetryPolicy:
    mode: RetryMode = RetryMode.EXPONENTIAL
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    jitter: float = 0.1


class RetryExhausted(Exception):
    pass


class SelfCorrect:
    def __init__(self, lessons_path: Path = LESSONS_PATH):
        self._lessons_path = lessons_path
        self._lessons: List[Lesson] = []
        self._load()

    def _load(self) -> None:
        if not self._lessons_path.exists():
            self._lessons = []
            return
        try:
            raw = self._lessons_path.read_text(encoding="utf-8")
            data = json.loads(raw)
            self._lessons = [Lesson(**item) for item in data]
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning("Failed to load lessons from %s: %s", self._lessons_path, e)
            self._lessons = []

    def _save(self) -> None:
        self._lessons_path.parent.mkdir(parents=True, exist_ok=True)
        data = [asdict(lesson) for lesson in self._lessons]
        self._lessons_path.write_text(
            json.dumps(data, indent=2, default=str), encoding="utf-8"
        )

    def record_lesson(
        self,
        category: str,
        severity: str,
        summary: str,
        detail: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> Lesson:
        lesson = Lesson(
            id=uuid.uuid4().hex[:12],
            category=category,
            severity=severity,
            summary=summary,
            detail=detail,
            context=context or {},
        )
        self._lessons.append(lesson)
        self._save()
        logger.info("Lesson recorded [%s] %s: %s", category, severity, summary)
        return lesson

    def search_lessons(
        self,
        category: Optional[str] = None,
        severity: Optional[str] = None,
        keyword: Optional[str] = None,
        limit: int = 10,
    ) -> List[Lesson]:
        results = list(self._lessons)
        if category:
            results = [l for l in results if l.category == category]
        if severity:
            results = [l for l in results if l.severity == severity]
        if keyword:
            kw = keyword.lower()
            results = [
                l
                for l in results
                if kw in l.summary.lower() or kw in l.detail.lower()
            ]
        results.sort(key=lambda l: l.occurred_at, reverse=True)
        return results[:limit]

    def resolve_lesson(self, lesson_id: str, resolution: str) -> bool:
        for lesson in self._lessons:
            if lesson.id == lesson_id:
                lesson.resolved = True
                lesson.resolution = resolution
                self._save()
                logger.info("Lesson %s resolved: %s", lesson_id, resolution)
                return True
        logger.warning("Lesson %s not found for resolution", lesson_id)
        return False

    def unresolved_count(self, category: Optional[str] = None) -> int:
        lessons = self._lessons
        if category:
            lessons = [l for l in lessons if l.category == category]
        return sum(1 for l in lessons if not l.resolved)

    def repeat_count(self, category: str, window_hours: float = 24) -> int:
        cutoff = time.time() - window_hours * 3600
        count = 0
        for lesson in self._lessons:
            try:
                ts = time.mktime(time.strptime(lesson.occurred_at[:19], "%Y-%m-%dT%H:%M:%S"))
                if lesson.category == category and ts >= cutoff:
                    count += 1
            except (ValueError, OSError):
                pass
        return count

    def get_unresolved(self) -> List[Lesson]:
        return [l for l in self._lessons if not l.resolved]

    def last_lessons(self, n: int = 5) -> List[Lesson]:
        sorted_lessons = sorted(
            self._lessons, key=lambda l: l.occurred_at, reverse=True
        )
        return sorted_lessons[:n]


class RetryStrategy:
    def __init__(self, policy: Optional[RetryPolicy] = None):
        self._policy = policy or RetryPolicy()

    def with_retry(self, fn, *args, **kwargs):
        last_exc = None
        for attempt in range(1, self._policy.max_retries + 1):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                last_exc = e
                delay = self._compute_delay(attempt)
                logger.warning(
                    "Attempt %d/%d failed for %s: %s. Retrying in %.2fs",
                    attempt,
                    self._policy.max_retries,
                    getattr(fn, "__name__", repr(fn)),
                    e,
                    delay,
                )
                time.sleep(delay)
        raise RetryExhausted(
            f"{getattr(fn, '__name__', repr(fn))} failed after "
            f"{self._policy.max_retries} attempts"
        ) from last_exc

    async def with_retry_async(self, fn, *args, **kwargs):
        last_exc = None
        for attempt in range(1, self._policy.max_retries + 1):
            try:
                return await fn(*args, **kwargs)
            except Exception as e:
                last_exc = e
                delay = self._compute_delay(attempt)
                logger.warning(
                    "Attempt %d/%d failed for %s: %s. Retrying in %.2fs",
                    attempt,
                    self._policy.max_retries,
                    getattr(fn, "__name__", repr(fn)),
                    e,
                    delay,
                )
                await asyncio.sleep(delay)
        raise RetryExhausted(
            f"{getattr(fn, '__name__', repr(fn))} failed after "
            f"{self._policy.max_retries} attempts"
        ) from last_exc

    def _compute_delay(self, attempt: int) -> float:
        mode = self._policy.mode
        base = self._policy.base_delay
        if mode == RetryMode.FIXED:
            delay = base
        elif mode == RetryMode.LINEAR:
            delay = base * attempt
        elif mode == RetryMode.JITTERED:
            import random
            delay = base + random.uniform(0, self._policy.jitter * base)
        else:
            delay = base * (2 ** (attempt - 1))
        return min(delay, self._policy.max_delay)

    @property
    def policy(self) -> RetryPolicy:
        return self._policy


import asyncio


class FallbackResolver:
    def __init__(self, correction: SelfCorrect):
        self._correction = correction

    def try_fallbacks(
        self,
        primary_fn,
        fallbacks: List,
        category: str = "pipeline",
        *args,
        **kwargs,
    ):
        strategies = [("primary", primary_fn)] + [
            (f"fallback_{i}", fb) for i, fb in enumerate(fallbacks)
        ]
        last_exc = None
        for name, fn in strategies:
            try:
                result = fn(*args, **kwargs)
                if result is not None:
                    self._correction.record_lesson(
                        category=category,
                        severity="info",
                        summary=f"Fallback resolved via {name}",
                        detail=f"Primary failed; {name} succeeded.",
                    )
                    return result
            except Exception as e:
                last_exc = e
                logger.warning("Fallback %s failed: %s", name, e)

        self._correction.record_lesson(
            category=category,
            severity="error",
            summary="All fallbacks exhausted",
            detail=f"Primary and {len(fallbacks)} fallbacks all failed. Last error: {last_exc}",
        )
        raise RetryExhausted(
            f"All {1 + len(fallbacks)} strategies failed"
        ) from last_exc
