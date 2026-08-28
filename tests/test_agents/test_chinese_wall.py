"""Tests for Chinese Wall agent isolation layer (P1-11)."""

from __future__ import annotations

import pytest

from quant_nanggroe.agents.chinese_wall import ChineseWall, ChineseWallError

# ============================================================================
# Compartment Lookup
# ============================================================================


class TestCompartmentLookup:
    def test_researcher_is_research(self):
        wall = ChineseWall()
        assert wall.get_compartment_for("ResearcherAgent") == "RESEARCH"

    def test_macro_is_research(self):
        wall = ChineseWall()
        assert wall.get_compartment_for("MacroAgent") == "RESEARCH"

    def test_strategist_is_signal(self):
        wall = ChineseWall()
        assert wall.get_compartment_for("StrategistAgent") == "SIGNAL"

    def test_crypto_is_signal(self):
        wall = ChineseWall()
        assert wall.get_compartment_for("CryptoAgent") == "SIGNAL"

    def test_forex_is_signal(self):
        wall = ChineseWall()
        assert wall.get_compartment_for("ForexAgent") == "SIGNAL"

    def test_risk_is_risk(self):
        wall = ChineseWall()
        assert wall.get_compartment_for("RiskAgent") == "RISK"

    def test_portfolio_is_risk(self):
        wall = ChineseWall()
        assert wall.get_compartment_for("PortfolioAgent") == "RISK"

    def test_execution_is_execution(self):
        wall = ChineseWall()
        assert wall.get_compartment_for("ExecutionAgent") == "EXECUTION"

    def test_trader_is_execution(self):
        wall = ChineseWall()
        assert wall.get_compartment_for("TraderAgent") == "EXECUTION"

    def test_unknown_agent_raises(self):
        wall = ChineseWall()
        with pytest.raises(ValueError, match="not assigned to any compartment"):
            wall.get_compartment_for("UnknownAgent")


# ============================================================================
# Read Permissions
# ============================================================================


class TestReadPermissions:
    def test_read_within_same_compartment(self):
        wall = ChineseWall()
        assert wall.check_read("ResearcherAgent", "RESEARCH") is True
        assert wall.check_read("StrategistAgent", "SIGNAL") is True
        assert wall.check_read("RiskAgent", "RISK") is True
        assert wall.check_read("ExecutionAgent", "EXECUTION") is True

    def test_read_between_different_compartments_no_bridge(self):
        wall = ChineseWall()
        # RESEARCH -> SIGNAL: no bridge
        assert wall.check_read("ResearcherAgent", "SIGNAL") is False
        # SIGNAL -> RESEARCH: no bridge
        assert wall.check_read("StrategistAgent", "RESEARCH") is False
        # RESEARCH -> EXECUTION: no bridge
        assert wall.check_read("ResearcherAgent", "EXECUTION") is False
        # EXECUTION -> RESEARCH: no bridge
        assert wall.check_read("ExecutionAgent", "RESEARCH") is False

    def test_read_via_bridge_signal_to_risk(self):
        wall = ChineseWall()
        # SIGNAL -> RISK: RISK can read SIGNAL (bridge exists)
        assert wall.check_read("StrategistAgent", "RISK") is False
        # Reverse: RISK reading from SIGNAL — this is the bridge direction
        assert wall.check_read("RiskAgent", "SIGNAL") is True
        assert wall.check_read("PortfolioAgent", "SIGNAL") is True

    def test_read_via_bridge_risk_to_execution(self):
        wall = ChineseWall()
        # RISK -> EXECUTION: EXECUTION can read RISK (bridge exists)
        assert wall.check_read("ExecutionAgent", "RISK") is True
        assert wall.check_read("TraderAgent", "RISK") is True
        # Reverse: not bridged
        assert wall.check_read("RiskAgent", "EXECUTION") is False

    def test_read_with_unregistered_agent(self):
        wall = ChineseWall()
        assert wall.check_read("GhostAgent", "RESEARCH") is False


# ============================================================================
# Write Permissions
# ============================================================================


class TestWritePermissions:
    def test_write_within_same_compartment(self):
        wall = ChineseWall()
        assert wall.check_write("ResearcherAgent", "RESEARCH") is True
        assert wall.check_write("StrategistAgent", "SIGNAL") is True
        assert wall.check_write("RiskAgent", "RISK") is True
        assert wall.check_write("ExecutionAgent", "EXECUTION") is True

    def test_write_to_different_compartment_blocked(self):
        wall = ChineseWall()
        assert wall.check_write("ResearcherAgent", "SIGNAL") is False
        assert wall.check_write("StrategistAgent", "RISK") is False
        assert wall.check_write("RiskAgent", "EXECUTION") is False
        assert wall.check_write("ExecutionAgent", "RESEARCH") is False

    def test_write_via_bridge_still_blocked(self):
        wall = ChineseWall()
        # Bridges allow reads, not writes
        assert wall.check_write("RiskAgent", "SIGNAL") is False
        assert wall.check_write("ExecutionAgent", "RISK") is False


# ============================================================================
# Communication (can_communicate)
# ============================================================================


class TestCanCommunicate:
    def test_same_compartment_communication(self):
        wall = ChineseWall()
        assert wall.can_communicate("ResearcherAgent", "MacroAgent") is True
        assert wall.can_communicate("StrategistAgent", "CryptoAgent") is True
        assert wall.can_communicate("RiskAgent", "PortfolioAgent") is True
        assert wall.can_communicate("ExecutionAgent", "TraderAgent") is True

    def test_bridged_communication(self):
        wall = ChineseWall()
        # SIGNAL -> RISK bridge
        assert wall.can_communicate("StrategistAgent", "RiskAgent") is True
        assert wall.can_communicate("CryptoAgent", "PortfolioAgent") is True
        # RISK -> EXECUTION bridge
        assert wall.can_communicate("RiskAgent", "ExecutionAgent") is True
        assert wall.can_communicate("PortfolioAgent", "TraderAgent") is True

    def test_forbidden_communication(self):
        wall = ChineseWall()
        # RESEARCH -> SIGNAL: blocked
        assert wall.can_communicate("ResearcherAgent", "StrategistAgent") is False
        # RESEARCH -> RISK: blocked
        assert wall.can_communicate("MacroAgent", "RiskAgent") is False
        # RESEARCH -> EXECUTION: blocked
        assert wall.can_communicate("ResearcherAgent", "ExecutionAgent") is False
        # EXECUTION -> RESEARCH: blocked
        assert wall.can_communicate("TraderAgent", "MacroAgent") is False
        # SIGNAL -> EXECUTION: blocked (no direct bridge)
        assert wall.can_communicate("StrategistAgent", "ExecutionAgent") is False
        # EXECUTION -> SIGNAL: blocked
        assert wall.can_communicate("TraderAgent", "StrategistAgent") is False

    def test_unknown_agents_cannot_communicate(self):
        wall = ChineseWall()
        assert wall.can_communicate("GhostAgent", "ResearcherAgent") is False
        assert wall.can_communicate("ResearcherAgent", "GhostAgent") is False


# ============================================================================
# Audit Logging
# ============================================================================


class TestAuditLogging:
    def test_audit_access_logs_internally(self):
        wall = ChineseWall()
        wall.audit_access("ResearcherAgent", "SIGNAL", "read")
        assert len(wall._access_log) == 1
        entry = wall._access_log[0]
        assert entry["source"] == "ResearcherAgent"
        assert entry["target"] == "SIGNAL"
        assert entry["access_type"] == "read"

    def test_audit_access_with_external_logger(self):
        from quant_nanggroe.engine.audit import AuditLogger

        wall = ChineseWall()
        audit_logger = AuditLogger(max_entries=100)

        wall.audit_access("RiskAgent", "ExecutionAgent", "communicate", audit_logger=audit_logger)
        assert len(wall._access_log) == 1

        entries = audit_logger.get_entries(layer="SYSTEM")
        assert len(entries) == 1
        assert "ChineseWall" in entries[0]["message"]

    def test_audit_access_resolves_compartment(self):
        wall = ChineseWall()
        wall.audit_access("ExecutionAgent", "RISK", "read")
        entry = wall._access_log[0]
        assert entry["source_compartment"] == "EXECUTION"


# ============================================================================
# Isolation Report
# ============================================================================


class TestIsolationReport:
    def test_report_contains_compartments(self):
        wall = ChineseWall()
        report = wall.isolation_report()

        assert "compartments" in report
        assert "RESEARCH" in report["compartments"]
        assert "SIGNAL" in report["compartments"]
        assert "RISK" in report["compartments"]
        assert "EXECUTION" in report["compartments"]

    def test_report_contains_bridges(self):
        wall = ChineseWall()
        report = wall.isolation_report()

        assert "bridges" in report
        bridge_pairs = {(b["from"], b["to"]) for b in report["bridges"]}
        assert ("SIGNAL", "RISK") in bridge_pairs
        assert ("RISK", "EXECUTION") in bridge_pairs

    def test_report_shows_wall_active(self):
        wall = ChineseWall()
        report = wall.isolation_report()

        for comp in report["compartments"].values():
            assert comp["wall_active"] is True

    def test_report_tracks_access_log_count(self):
        wall = ChineseWall()
        assert wall.isolation_report()["access_log_count"] == 0

        wall.audit_access("ResearcherAgent", "SIGNAL", "read")
        assert wall.isolation_report()["access_log_count"] == 1

    def test_report_includes_isolation_zones(self):
        wall = ChineseWall()
        report = wall.isolation_report()
        assert "isolation_zones" in report


# ============================================================================
# ChineseWallError
# ============================================================================


class TestChineseWallError:
    def test_error_is_exception(self):
        err = ChineseWallError("test")
        assert isinstance(err, Exception)

    def test_error_has_source_target_and_access_type(self):
        err = ChineseWallError(
            "wall violation",
            source="market_analysis",
            target="signal_generation",
            access_type="read",
        )
        assert err.source == "market_analysis"
        assert err.target == "signal_generation"
        assert err.access_type == "read"
        assert str(err) == "wall violation"

    def test_error_defaults(self):
        err = ChineseWallError("blocked")
        assert err.source == ""
        assert err.target == ""
        assert err.access_type == ""


# ============================================================================
# Graph Integration (TradingGraph with ChineseWall)
# ============================================================================


class TestGraphIntegration:
    """Test TradingGraph._check_wall using a minimal mock-based graph."""

    def _make_graph(self):
        """Construct a TradingGraph instance with all heavy deps mocked away."""
        from unittest.mock import MagicMock

        import quant_nanggroe.agents.graph as g_mod

        g_mod.StateGraph = MagicMock()
        g_mod.create_llm = MagicMock(return_value=MagicMock())
        g_mod.START = "START"
        g_mod.END = "END"

        from quant_nanggroe.agents.graph import TradingGraph
        graph = TradingGraph(audit_logger=None)
        return graph

    def test_check_wall_same_compartment_allowed(self):
        graph = self._make_graph()
        graph._check_wall("risk_assessment", "deterministic_risk_gate")

    def test_check_wall_bridged_allowed(self):
        graph = self._make_graph()
        graph._check_wall("signal_generation", "risk_assessment")

    def test_check_wall_blocked_raises(self):
        graph = self._make_graph()
        with pytest.raises(ChineseWallError) as excinfo:
            graph._check_wall("market_analysis", "signal_generation")
        assert "RESEARCH" in str(excinfo.value)
        assert "SIGNAL" in str(excinfo.value)

    def test_unknown_node_skips_check(self):
        graph = self._make_graph()
        graph._check_wall("unknown", "also_unknown")


# ============================================================================
# Edge Cases & Boundaries
# ============================================================================


class TestEdgeCases:
    def test_empty_compartment_list_does_not_exist(self):
        ChineseWall.COMPARTMENTS["TEST"] = []
        wall = ChineseWall()
        with pytest.raises(ValueError):
            wall.get_compartment_for("AnyAgent")
        del ChineseWall.COMPARTMENTS["TEST"]

    def test_bridge_to_self_is_not_needed(self):
        wall = ChineseWall()
        # Same compartment always works regardless of bridges
        assert wall.can_communicate("ResearcherAgent", "MacroAgent") is True

    def test_all_registered_agents_have_compartment(self):
        registered = [
            "ResearcherAgent", "MacroAgent",
            "StrategistAgent", "CryptoAgent", "ForexAgent",
            "RiskAgent", "PortfolioAgent",
            "ExecutionAgent", "TraderAgent",
        ]
        wall = ChineseWall()
        for agent in registered:
            comp = wall.get_compartment_for(agent)
            assert comp in ChineseWall.COMPARTMENTS
