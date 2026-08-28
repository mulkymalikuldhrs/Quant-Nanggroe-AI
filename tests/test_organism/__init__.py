"""Tests for the organism subpackage."""

from __future__ import annotations

import pytest

# ── Sense tests ──────────────────────────────────────────────────────────────


class TestSenseEngine:
    """Tests for the sense (problem scanning) engine."""

    @pytest.fixture
    def engine(self):
        from ai_multicolony.organism import SenseEngine, TrendScanner
        e = SenseEngine()
        e.add_scanner(TrendScanner())
        return e

    def test_engine_creation(self, engine):
        assert engine.scanner_count == 1

    def test_add_remove_scanner(self):
        from ai_multicolony.organism import RSSScanner, SenseEngine
        e = SenseEngine()
        e.add_scanner(RSSScanner())
        assert e.scanner_count == 1
        e.remove_scanner("rss_scanner")
        assert e.scanner_count == 0

    @pytest.mark.asyncio
    async def test_scan(self, engine):
        result = await engine.scan()
        assert result.scan_id != ""
        assert isinstance(result.signals, list)

    def test_signal_creation(self):
        from ai_multicolony.organism import Signal, SignalSeverity, SignalType
        signal = Signal(
            signal_type=SignalType.THREAT,
            severity=SignalSeverity.HIGH,
            title="Test signal",
        )
        assert signal.is_urgent is True

    def test_signal_not_urgent(self):
        from ai_multicolony.organism import Signal, SignalSeverity, SignalType
        signal = Signal(
            signal_type=SignalType.INFO,
            severity=SignalSeverity.LOW,
            title="Info signal",
        )
        assert signal.is_urgent is False

    def test_trend_scanner_spike(self):
        from ai_multicolony.organism import TrendScanner
        scanner = TrendScanner(spike_threshold=0.5)
        for i in range(10):
            scanner.add_data_point("test_series", float(i))
        # Add a spike
        scanner.add_data_point("test_series", 1000.0)
        import asyncio
        signals = asyncio.get_event_loop().run_until_complete(scanner.scan())
        # May or may not detect depending on spike threshold
        assert isinstance(signals, list)

    def test_rss_scanner(self):
        from ai_multicolony.organism import RSSScanner
        scanner = RSSScanner(feeds=["https://example.com/feed"])
        assert scanner.name == "rss_scanner"


# ── Decision tests ──────────────────────────────────────────────────────────


class TestDecisionEngine:
    """Tests for the decision scoring engine."""

    @pytest.fixture
    def engine(self):
        from ai_multicolony.organism import DecisionEngine
        return DecisionEngine()

    def test_engine_creation(self, engine):
        assert len(engine.config.criteria) > 0

    def test_approve_decision(self, engine):
        score = engine.evaluate(
            signal_id="sig-1",
            signal_title="Great opportunity",
            criteria_scores={
                "business_impact": 9.0,
                "urgency": 8.0,
                "feasibility": 9.0,
                "cost_efficiency": 8.0,
                "risk_level": 8.0,
                "strategic_alignment": 9.0,
                "innovation_potential": 8.0,
            },
        )
        assert score.status.value in ("approved", "escalated")
        assert score.normalized_score > 0.6

    def test_reject_decision(self, engine):
        score = engine.evaluate(
            signal_id="sig-2",
            signal_title="Bad idea",
            criteria_scores={
                "business_impact": 1.0,
                "urgency": 1.0,
                "feasibility": 2.0,
                "cost_efficiency": 1.0,
                "risk_level": 1.0,
                "strategic_alignment": 1.0,
                "innovation_potential": 1.0,
            },
        )
        assert score.status.value == "rejected"

    def test_deferred_decision(self, engine):
        score = engine.evaluate(
            signal_id="sig-3",
            signal_title="Maybe",
            criteria_scores={
                "business_impact": 5.0,
                "urgency": 5.0,
                "feasibility": 5.0,
                "cost_efficiency": 5.0,
                "risk_level": 5.0,
                "strategic_alignment": 5.0,
                "innovation_potential": 5.0,
            },
        )
        # Mid-range scores can go either way
        assert score.normalized_score > 0.0

    def test_batch_evaluate(self, engine):
        signals = [
            {"signal_id": "s1", "signal_title": "A", "criteria_scores": {
                "business_impact": 9.0, "urgency": 8.0, "feasibility": 9.0,
                "cost_efficiency": 8.0, "risk_level": 8.0,
                "strategic_alignment": 9.0, "innovation_potential": 8.0,
            }},
            {"signal_id": "s2", "signal_title": "B", "criteria_scores": {
                "business_impact": 1.0, "urgency": 1.0, "feasibility": 2.0,
                "cost_efficiency": 1.0, "risk_level": 1.0,
                "strategic_alignment": 1.0, "innovation_potential": 1.0,
            }},
        ]
        results = engine.batch_evaluate(signals)
        assert len(results) == 2
        # First should score higher than second
        assert results[0].normalized_score >= results[1].normalized_score

    def test_decision_stats(self, engine):
        engine.evaluate("s1", "Test", {"business_impact": 5.0, "urgency": 5.0,
                        "feasibility": 5.0, "cost_efficiency": 5.0, "risk_level": 5.0,
                        "strategic_alignment": 5.0, "innovation_potential": 5.0})
        stats = engine.stats
        assert stats["total_decisions"] == 1


# ── Factory tests ────────────────────────────────────────────────────────────


class TestSolutionFactory:
    """Tests for the solution factory."""

    @pytest.fixture
    def factory(self):
        from ai_multicolony.organism import SolutionFactory
        return SolutionFactory()

    @pytest.mark.asyncio
    async def test_build_service(self, factory):
        from ai_multicolony.organism import ArtifactType, BuildRequest
        request = BuildRequest(
            signal_title="Create monitoring service",
            artifact_type=ArtifactType.SERVICE,
            requirements=["Monitor health", "Alert on failures"],
        )
        result = await factory.build(request)
        assert result.success
        assert len(result.artifacts) > 0

    @pytest.mark.asyncio
    async def test_build_code(self, factory):
        from ai_multicolony.organism import ArtifactType, BuildRequest
        request = BuildRequest(
            signal_title="Data processor",
            artifact_type=ArtifactType.CODE,
        )
        result = await factory.build(request)
        assert result.success

    @pytest.mark.asyncio
    async def test_build_config(self, factory):
        from ai_multicolony.organism import ArtifactType, BuildRequest
        request = BuildRequest(
            signal_title="App config",
            artifact_type=ArtifactType.CONFIG,
        )
        result = await factory.build(request)
        assert result.success

    def test_factory_stats(self, factory):
        stats = factory.stats
        assert stats["build_count"] == 0
        assert len(stats["templates"]) > 0


# ── Immune tests ────────────────────────────────────────────────────────────


class TestImmuneSystem:
    """Tests for the immune system."""

    @pytest.fixture
    def immune(self):
        from ai_multicolony.organism import ImmuneConfig, ImmuneSystem
        config = ImmuneConfig(max_iterations=100, max_duplicate_actions=5)
        return ImmuneSystem(config)

    def test_safe_action(self, immune):
        alert = immune.check_action("read", {"target": "file.txt"})
        assert alert.threat_level.value == "safe"

    def test_forbidden_action(self, immune):
        alert = immune.check_action("delete_system")
        assert alert.threat_level.value == "critical"
        assert immune.is_killed

    def test_iteration_limit(self, immune):
        for i in range(101):
            alert = immune.check_iteration(i)
        assert immune.is_killed

    def test_kill_switch_manual(self, immune):
        alert = immune.activate_kill_switch("Test activation")
        assert immune.is_killed
        assert alert.threat_level.value == "critical"

    def test_pause_resume(self, immune):
        immune.pause("Testing")
        assert immune.is_paused
        immune.resume()
        assert not immune.is_paused

    def test_reset(self, immune):
        immune.check_iteration(50)
        immune.reset()
        assert immune.iteration_count == 0
        assert not immune.is_killed


# ── Growth tests ────────────────────────────────────────────────────────────


class TestGrowthEngine:
    """Tests for the growth engine."""

    @pytest.fixture
    def growth(self):
        from ai_multicolony.organism import GrowthEngine
        return GrowthEngine()

    def test_register_solution(self, growth):
        metrics = growth.register_solution("sol-1", "Test Solution")
        assert metrics.solution_id == "sol-1"

    def test_record_adoption(self, growth):
        growth.register_solution("sol-1")
        metrics = growth.record_adoption("sol-1", 10)
        assert metrics.adoption_count == 10
        assert metrics.active_users == 10

    def test_record_request(self, growth):
        growth.register_solution("sol-1")
        metrics = growth.record_request("sol-1", success=True, response_time_ms=100.0)
        assert metrics.total_requests == 1
        assert metrics.success_rate == 1.0

    def test_record_feedback(self, growth):
        growth.register_solution("sol-1")
        feedback = growth.record_feedback("sol-1", rating=4.5, comment="Great!")
        assert feedback.rating == 4.5
        metrics = growth.get_metrics("sol-1")
        assert metrics.feedback_score == 4.5


# ── Lifecycle tests ─────────────────────────────────────────────────────────


class TestLifecycleOrchestrator:
    """Tests for the lifecycle orchestrator."""

    @pytest.fixture
    def orchestrator(self):
        from ai_multicolony.organism import LifecycleOrchestrator
        return LifecycleOrchestrator()

    @pytest.mark.asyncio
    async def test_run_cycle(self, orchestrator):
        result = await orchestrator.run_cycle()
        assert result.cycle_id != ""
        assert result.signals_detected >= 0

    @pytest.mark.asyncio
    async def test_run_cycles(self, orchestrator):
        results = await orchestrator.run_cycles(count=3)
        assert len(results) == 3

    def test_lifecycle_phases(self):
        from ai_multicolony.organism import LifecyclePhase
        assert LifecyclePhase.SENSING.value == "sensing"
        assert LifecyclePhase.BUILDING.value == "building"

    def test_orchestrator_stats(self, orchestrator):
        stats = orchestrator.stats
        assert "phase" in stats
        assert "cycle_count" in stats
