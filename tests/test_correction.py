"""Smoke tests for engine/correction.py — SelfCorrect, RetryStrategy, FallbackResolver."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import tempfile
from pathlib import Path

import pytest

from quant_nanggroe.engine.correction import (
    FallbackResolver,
    Lesson,
    RetryExhausted,
    RetryMode,
    RetryPolicy,
    RetryStrategy,
    SelfCorrect,
)

# ── SelfCorrect ──────────────────────────────────────────────────────────────


class TestSelfCorrect:
    def test_record_lesson(self):
        with tempfile.TemporaryDirectory() as tmp:
            sc = SelfCorrect(Path(tmp) / "lessons.json")
            lesson = sc.record_lesson("test", "error", "test summary", "test detail")
            assert lesson.id
            assert lesson.category == "test"
            assert lesson.severity == "error"
            assert lesson.summary == "test summary"
            assert lesson.detail == "test detail"
            assert not lesson.resolved

    def test_record_and_search_by_keyword(self):
        with tempfile.TemporaryDirectory() as tmp:
            sc = SelfCorrect(Path(tmp) / "lessons.json")
            sc.record_lesson("data_fetch", "error", "API timeout", "connection refused")
            sc.record_lesson("execution", "info", "order filled", "100 BTC @ 67k")
            results = sc.search_lessons(keyword="timeout")
            assert len(results) == 1
            assert results[0].summary == "API timeout"

    def test_search_by_category(self):
        with tempfile.TemporaryDirectory() as tmp:
            sc = SelfCorrect(Path(tmp) / "lessons.json")
            sc.record_lesson("risk", "warning", "drawdown breach", "")
            sc.record_lesson("execution", "info", "order filled", "")
            results = sc.search_lessons(category="risk")
            assert len(results) == 1
            assert results[0].category == "risk"

    def test_search_by_severity(self):
        with tempfile.TemporaryDirectory() as tmp:
            sc = SelfCorrect(Path(tmp) / "lessons.json")
            sc.record_lesson("a", "error", "err1", "")
            sc.record_lesson("b", "warning", "warn1", "")
            results = sc.search_lessons(severity="warning")
            assert len(results) == 1
            assert results[0].severity == "warning"

    def test_search_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            sc = SelfCorrect(Path(tmp) / "lessons.json")
            for i in range(20):
                sc.record_lesson("test", "info", f"lesson {i}", "")
            results = sc.search_lessons(limit=5)
            assert len(results) == 5

    def test_resolve_lesson(self):
        with tempfile.TemporaryDirectory() as tmp:
            sc = SelfCorrect(Path(tmp) / "lessons.json")
            lesson = sc.record_lesson("test", "error", "broken", "")
            assert not lesson.resolved
            ok = sc.resolve_lesson(lesson.id, "fixed it")
            assert ok
            assert sc._lessons[0].resolved
            assert sc._lessons[0].resolution == "fixed it"

    def test_resolve_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmp:
            sc = SelfCorrect(Path(tmp) / "lessons.json")
            assert not sc.resolve_lesson("nonexistent", "nope")

    def test_unresolved_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            sc = SelfCorrect(Path(tmp) / "lessons.json")
            sc.record_lesson("a", "error", "err", "")
            l2 = sc.record_lesson("a", "error", "err2", "")
            sc.resolve_lesson(l2.id, "done")
            assert sc.unresolved_count() == 1
            assert sc.unresolved_count("a") == 1
            assert sc.unresolved_count("b") == 0

    def test_last_lessons(self):
        with tempfile.TemporaryDirectory() as tmp:
            sc = SelfCorrect(Path(tmp) / "lessons.json")
            for i in range(10):
                sc.record_lesson("test", "info", f"l{i}", "")
            last = sc.last_lessons(3)
            assert len(last) == 3

    def test_empty_lessons(self):
        with tempfile.TemporaryDirectory() as tmp:
            sc = SelfCorrect(Path(tmp) / "lessons.json")
            assert sc.search_lessons() == []
            assert sc.unresolved_count() == 0
            assert sc.last_lessons() == []

    def test_pre_existing_lessons_persist(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "lessons.json"
            sc1 = SelfCorrect(p)
            sc1.record_lesson("persist", "error", "survive", "")
            sc2 = SelfCorrect(p)
            assert len(sc2._lessons) == 1
            assert sc2._lessons[0].summary == "survive"

    def test_lesson_dataclass_defaults(self):
        lesson = Lesson(id="abc", category="cat", severity="err", summary="s", detail="")
        assert lesson.detail == ""
        assert lesson.context == {}
        assert lesson.occurred_at
        assert not lesson.resolved
        assert lesson.resolution == ""

    def test_repeat_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            sc = SelfCorrect(Path(tmp) / "lessons.json")
            sc.record_lesson("network", "error", "timeout", "")
            assert sc.repeat_count("network", window_hours=24) == 1
            assert sc.repeat_count("other", window_hours=24) == 0

    def test_get_unresolved(self):
        with tempfile.TemporaryDirectory() as tmp:
            sc = SelfCorrect(Path(tmp) / "lessons.json")
            l1 = sc.record_lesson("a", "error", "err1", "")
            l2 = sc.record_lesson("a", "error", "err2", "")
            sc.resolve_lesson(l1.id, "done")
            unresolved = sc.get_unresolved()
            assert len(unresolved) == 1
            assert unresolved[0].id == l2.id


# ── RetryStrategy ────────────────────────────────────────────────────────────


class TestRetryStrategy:
    def test_success_on_first_attempt(self):
        rs = RetryStrategy()
        result = rs.with_retry(lambda x: x + 1, 41)
        assert result == 42

    def test_success_after_retries(self):
        call_count = [0]

        def flaky(x):
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError(f"attempt {call_count[0]} failed")
            return x

        rs = RetryStrategy(RetryPolicy(max_retries=5, mode=RetryMode.FIXED, base_delay=0.01))
        result = rs.with_retry(flaky, "ok")
        assert result == "ok"
        assert call_count[0] == 3

    def test_exhausted_raises(self):
        call_count = [0]

        def always_fails():
            call_count[0] += 1
            raise ValueError("always fail")

        rs = RetryStrategy(RetryPolicy(max_retries=3, mode=RetryMode.FIXED, base_delay=0.01))
        with pytest.raises(RetryExhausted):
            rs.with_retry(always_fails)
        assert call_count[0] == 3

    def test_fixed_delay_mode(self):
        rs = RetryStrategy(RetryPolicy(mode=RetryMode.FIXED, base_delay=1.0))
        assert rs._compute_delay(1) == 1.0
        assert rs._compute_delay(5) == 1.0

    def test_linear_delay_mode(self):
        rs = RetryStrategy(RetryPolicy(mode=RetryMode.LINEAR, base_delay=1.0))
        assert rs._compute_delay(1) == 1.0
        assert rs._compute_delay(3) == 3.0

    def test_exponential_delay_mode(self):
        rs = RetryStrategy(RetryPolicy(mode=RetryMode.EXPONENTIAL, base_delay=1.0))
        assert rs._compute_delay(1) == 1.0
        assert rs._compute_delay(2) == 2.0
        assert rs._compute_delay(3) == 4.0

    def test_jittered_delay_mode(self):
        rs = RetryStrategy(RetryPolicy(mode=RetryMode.JITTERED, base_delay=1.0, jitter=0.5))
        delays = [rs._compute_delay(1) for _ in range(100)]
        assert all(1.0 <= d <= 1.5 for d in delays)

    def test_max_delay_cap(self):
        rs = RetryStrategy(RetryPolicy(mode=RetryMode.EXPONENTIAL, base_delay=10.0, max_delay=15.0))
        assert rs._compute_delay(10) == 15.0

    def test_default_policy(self):
        rs = RetryStrategy()
        assert rs.policy.max_retries == 3
        assert rs.policy.mode == RetryMode.EXPONENTIAL

    def test_policy_property(self):
        policy = RetryPolicy(max_retries=5)
        rs = RetryStrategy(policy)
        assert rs.policy.max_retries == 5

    def test_custom_policy(self):
        policy = RetryPolicy(mode=RetryMode.LINEAR, max_retries=2, base_delay=0.5)
        rs = RetryStrategy(policy)
        assert rs.policy.mode == RetryMode.LINEAR
        assert rs.policy.max_retries == 2
        assert rs.policy.base_delay == 0.5


# ── FallbackResolver ─────────────────────────────────────────────────────────


class TestFallbackResolver:
    def test_primary_succeeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            sc = SelfCorrect(Path(tmp) / "lessons.json")
            fr = FallbackResolver(sc)

            def primary():
                return 42

            result = fr.try_fallbacks(primary, [])
            assert result == 42

    def test_fallback_chain_succeeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            sc = SelfCorrect(Path(tmp) / "lessons.json")
            fr = FallbackResolver(sc)

            def primary():
                raise ValueError("primary fail")

            def fallback1():
                raise ValueError("fb1 fail")

            def fallback2():
                return "recovered"

            result = fr.try_fallbacks(primary, [fallback1, fallback2])
            assert result == "recovered"

    def test_all_fallbacks_exhausted_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            sc = SelfCorrect(Path(tmp) / "lessons.json")
            fr = FallbackResolver(sc)

            def primary():
                raise ValueError("no")

            def fallback():
                raise ValueError("also no")

            with pytest.raises(RetryExhausted):
                fr.try_fallbacks(primary, [fallback])

    def test_records_lesson_on_fallback_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            sc = SelfCorrect(Path(tmp) / "lessons.json")
            fr = FallbackResolver(sc)

            def primary():
                raise ValueError("boom")

            def fb():
                return "saved"

            fr.try_fallbacks(primary, [fb])
            lessons = sc.search_lessons(keyword="Fallback resolved")
            assert len(lessons) == 1
            assert "fallback_0" in lessons[0].summary

    def test_records_lesson_on_all_exhausted(self):
        with tempfile.TemporaryDirectory() as tmp:
            sc = SelfCorrect(Path(tmp) / "lessons.json")
            fr = FallbackResolver(sc)

            def primary():
                raise ValueError("boom")

            with pytest.raises(RetryExhausted):
                fr.try_fallbacks(primary, [])

            lessons = sc.search_lessons(keyword="All fallbacks exhausted")
            assert len(lessons) == 1

    def test_fallback_with_args(self):
        with tempfile.TemporaryDirectory() as tmp:
            sc = SelfCorrect(Path(tmp) / "lessons.json")
            fr = FallbackResolver(sc)

            def primary(x, y=0):
                raise ValueError("no")

            def fb(x, y=0):
                return x + y

            result = fr.try_fallbacks(primary, [fb], "pipeline", 40, y=2)
            assert result == 42

    def test_none_result_not_treated_as_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            sc = SelfCorrect(Path(tmp) / "lessons.json")
            fr = FallbackResolver(sc)

            def primary():
                return None

            def fb():
                return 99

            result = fr.try_fallbacks(primary, [fb])
            assert result == 99, "None from primary should continue to fallback"

    def test_custom_category(self):
        with tempfile.TemporaryDirectory() as tmp:
            sc = SelfCorrect(Path(tmp) / "lessons.json")
            fr = FallbackResolver(sc)

            def primary():
                raise ValueError("fail")

            def fb():
                return "ok"

            fr.try_fallbacks(primary, [fb], category="network")
            lessons = sc.search_lessons(category="network")
            assert len(lessons) == 1