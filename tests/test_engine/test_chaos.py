"""Tests for the chaos engineering module."""
import pytest
from unittest.mock import patch

from quant_nanggroe.engine.chaos import (
    ChaosType,
    ChaosConfig,
    ChaosResult,
    ChaosEngine,
)


class TestChaosDisabledNoInjection:
    """When chaos is disabled, no injection should occur."""

    def test_chaos_disabled_no_injection(self):
        config = ChaosConfig(enabled=False)
        engine = ChaosEngine(config)
        for ct in ChaosType:
            result = engine.maybe_inject(ct)
            assert result.injected is False
            assert "disabled" in result.description.lower()


class TestChaosProbability0:
    """Probability of 0 should never inject."""

    def test_chaos_probability_0(self):
        config = ChaosConfig(enabled=True, probability=0.0, seed=42)
        engine = ChaosEngine(config)
        for ct in ChaosType:
            result = engine.maybe_inject(ct)
            assert result.injected is False


class TestChaosProbability1:
    """Probability of 1 should always inject (when enabled and type in scope)."""

    def test_chaos_probability_1(self):
        config = ChaosConfig(
            enabled=True,
            probability=1.0,
            chaos_types=[ChaosType.EXCHANGE_TIMEOUT],
            seed=42,
        )
        engine = ChaosEngine(config)
        result = engine.maybe_inject(ChaosType.EXCHANGE_TIMEOUT)
        assert result.injected is True
        assert engine.injection_count == 1


class TestChaosSeedReproducible:
    """Same seed should produce same injection decisions."""

    def test_chaos_seed_reproducible(self):
        config1 = ChaosConfig(enabled=True, probability=0.5, seed=123)
        config2 = ChaosConfig(enabled=True, probability=0.5, seed=123)
        engine1 = ChaosEngine(config1)
        engine2 = ChaosEngine(config2)

        types = [ChaosType.PARTIAL_FILL, ChaosType.SLIPPAGE_BURST, ChaosType.EXCHANGE_TIMEOUT]
        for ct in types:
            r1 = engine1.maybe_inject(ct)
            r2 = engine2.maybe_inject(ct)
            assert r1.injected == r2.injected
            assert r1.description == r2.description


class TestLatencyInjection:
    """Test latency spike injection."""

    def test_latency_injection(self):
        config = ChaosConfig(
            enabled=True,
            probability=1.0,
            chaos_types=[ChaosType.LATENCY_SPIKE],
            max_latency_ms=10,
            seed=42,
        )
        engine = ChaosEngine(config)
        result = engine.maybe_inject(ChaosType.LATENCY_SPIKE)
        assert result.injected is True
        assert result.duration_ms >= 0
        assert "latency" in result.description.lower()


class TestPartialFill:
    """Test partial fill injection."""

    def test_partial_fill(self):
        config = ChaosConfig(
            enabled=True,
            probability=1.0,
            chaos_types=[ChaosType.PARTIAL_FILL],
            seed=42,
        )
        engine = ChaosEngine(config)
        result = engine.maybe_inject(ChaosType.PARTIAL_FILL)
        assert result.injected is True
        assert "partial fill" in result.description.lower()


class TestGetResults:
    """Test get_results returns list of ChaosResult."""

    def test_get_results(self):
        config = ChaosConfig(
            enabled=True,
            probability=1.0,
            chaos_types=[ChaosType.EXCHANGE_TIMEOUT, ChaosType.KILL_SWITCH_STORM],
            seed=42,
        )
        engine = ChaosEngine(config)
        engine.maybe_inject(ChaosType.EXCHANGE_TIMEOUT)
        engine.maybe_inject(ChaosType.KILL_SWITCH_STORM)
        results = engine.get_results()
        assert len(results) == 2
        assert all(isinstance(r, ChaosResult) for r in results)
        assert all(r.injected for r in results)


class TestReset:
    """Test reset clears state."""

    def test_reset(self):
        config = ChaosConfig(
            enabled=True,
            probability=1.0,
            chaos_types=[ChaosType.EXCHANGE_TIMEOUT],
            seed=42,
        )
        engine = ChaosEngine(config)
        engine.maybe_inject(ChaosType.EXCHANGE_TIMEOUT)
        assert engine.injection_count == 1
        assert len(engine.get_results()) == 1

        engine.reset()
        assert engine.injection_count == 0
        assert len(engine.get_results()) == 0
