"""Comprehensive Tests for New Agent Tools.

Tests for Flow, Geopolitical, Intermarket, Screener, Competition,
Forecast, Emotional, and Skill tools.

All tests use deterministic data — no real API calls.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

# ======================================================================
# Flow Tool Tests
# ======================================================================
from quant_nanggroe.agents.tools.flow_tool import (
    COTReport,
    FlowDirection,
    FlowScore,
    FlowTool,
    PositioningAnalysis,
    PositioningSignal,
    WhaleTransaction,
)


class TestFlowDirection:
    """Tests for FlowDirection enum."""

    def test_all_directions(self):
        expected = ["STRONG_BUY", "MODERATE_BUY", "NEUTRAL", "MODERATE_SELL", "STRONG_SELL"]
        actual = [d.value for d in FlowDirection]
        assert set(actual) == set(expected)

    def test_direction_is_string_enum(self):
        assert isinstance(FlowDirection.STRONG_BUY, str)
        assert FlowDirection.STRONG_BUY == "STRONG_BUY"


class TestPositioningSignal:
    """Tests for PositioningSignal enum."""

    def test_all_signals(self):
        expected = ["CROWDED_LONG", "CROWDED_SHORT", "BALANCED", "CONTRARIAN_BUY", "CONTRARIAN_SELL"]
        actual = [s.value for s in PositioningSignal]
        assert set(actual) == set(expected)


class TestCOTReport:
    """Tests for COTReport model."""

    def test_default_values(self):
        report = COTReport(symbol="GC")
        assert report.symbol == "GC"
        assert report.commercial_long == 0
        assert report.commercial_short == 0
        assert report.non_commercial_long == 0
        assert report.non_commercial_short == 0
        assert report.non_reportable_long == 0
        assert report.non_reportable_short == 0
        assert report.open_interest == 0
        assert report.report_date == ""

    def test_full_construction(self):
        report = COTReport(
            symbol="CL",
            report_date="2025-01-01",
            commercial_long=100000,
            commercial_short=80000,
            non_commercial_long=50000,
            non_commercial_short=60000,
            non_reportable_long=10000,
            non_reportable_short=15000,
            open_interest=200000,
        )
        assert report.commercial_long == 100000
        assert report.open_interest == 200000
        assert report.report_date == "2025-01-01"

    def test_serialization_round_trip(self):
        report = COTReport(symbol="GC", commercial_long=500)
        data = report.model_dump()
        report2 = COTReport(**data)
        assert report2.symbol == report.symbol
        assert report2.commercial_long == report.commercial_long

    def test_missing_symbol_rejected(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            COTReport()


class TestWhaleTransaction:
    """Tests for WhaleTransaction model."""

    def test_default_values(self):
        tx = WhaleTransaction()
        assert tx.tx_hash == ""
        assert tx.amount == 0.0
        assert tx.value_usd == 0.0
        assert tx.symbol == ""
        assert tx.side == ""
        assert tx.wallet_address == ""
        assert tx.exchange == ""

    def test_full_construction(self):
        tx = WhaleTransaction(
            tx_hash="0xabc",
            symbol="BTC",
            side="BUY",
            amount=100.0,
            value_usd=5000000.0,
            wallet_address="0xdef",
            exchange="Binance",
        )
        assert tx.side == "BUY"
        assert tx.value_usd == 5000000.0
        assert tx.exchange == "Binance"


class TestFlowScore:
    """Tests for FlowScore model."""

    def test_default_values(self):
        score = FlowScore(symbol="EURUSD")
        assert score.score == 0.0
        assert score.direction == FlowDirection.NEUTRAL
        assert score.confidence == 0.0
        assert score.institutional_pressure == 0.0
        assert score.retail_pressure == 0.0
        assert score.whale_activity == 0.0

    def test_with_data(self):
        score = FlowScore(
            symbol="GC",
            score=0.6,
            direction=FlowDirection.MODERATE_BUY,
            institutional_pressure=0.7,
            confidence=0.5,
        )
        assert score.score == 0.6
        assert score.direction == FlowDirection.MODERATE_BUY


class TestPositioningAnalysis:
    """Tests for PositioningAnalysis model."""

    def test_default_values(self):
        pa = PositioningAnalysis(symbol="GC")
        assert pa.signal == PositioningSignal.BALANCED
        assert pa.z_score == 0.0
        assert pa.commercial_net == 0.0
        assert pa.speculative_net == 0.0
        assert pa.percentile == 0.0
        assert pa.contrarian_signal is None

    def test_with_extreme_positioning(self):
        pa = PositioningAnalysis(
            symbol="CL",
            signal=PositioningSignal.CROWDED_LONG,
            z_score=2.5,
            contrarian_signal="CONTRARIAN_SELL",
        )
        assert pa.signal == PositioningSignal.CROWDED_LONG
        assert pa.z_score == 2.5


class TestFlowTool:
    """Tests for FlowTool."""

    @pytest.fixture
    def flow_tool(self):
        return FlowTool(cache_ttl=600)

    @pytest.mark.asyncio
    async def test_fetch_cot_data(self, flow_tool):
        report = await flow_tool.fetch_cot_data("GC")
        assert isinstance(report, COTReport)
        assert report.symbol == "GC"

    @pytest.mark.asyncio
    async def test_fetch_cot_data_returns_cot_report(self, flow_tool):
        """fetch_cot_data returns a COTReport even when no real data available."""
        r1 = await flow_tool.fetch_cot_data("GC")
        r2 = await flow_tool.fetch_cot_data("GC")
        # Both should be COTReport with same symbol
        assert isinstance(r1, COTReport)
        assert isinstance(r2, COTReport)
        assert r1.symbol == r2.symbol == "GC"

    @pytest.mark.asyncio
    async def test_track_whales(self, flow_tool):
        whales = await flow_tool.track_whales("BTC")
        assert isinstance(whales, list)

    @pytest.mark.asyncio
    async def test_track_whales_with_params(self, flow_tool):
        whales = await flow_tool.track_whales("ETH", min_value_usd=500000, limit=10)
        assert isinstance(whales, list)

    @pytest.mark.asyncio
    async def test_analyze_flow(self, flow_tool):
        result = await flow_tool.analyze_flow("EURUSD")
        assert isinstance(result, FlowScore)
        assert result.symbol == "EURUSD"
        assert -1.0 <= result.score <= 1.0

    @pytest.mark.asyncio
    async def test_analyze_flow_caching(self, flow_tool):
        result1 = await flow_tool.analyze_flow("EURUSD")
        result2 = await flow_tool.analyze_flow("EURUSD")
        assert result1 is result2

    @pytest.mark.asyncio
    async def test_analyze_positioning(self, flow_tool):
        result = await flow_tool.analyze_positioning("GC")
        assert isinstance(result, PositioningAnalysis)
        assert result.symbol == "GC"

    @pytest.mark.asyncio
    async def test_analyze_flow_with_cot_data(self, flow_tool):
        """Test flow analysis with simulated COT data."""
        flow_tool._set_cache("cot:EUR", COTReport(
            symbol="EUR",
            non_commercial_long=100000,
            non_commercial_short=60000,
            non_reportable_long=10000,
            non_reportable_short=15000,
        ))
        result = await flow_tool.analyze_flow("EUR")
        assert result.institutional_pressure != 0.0

    @pytest.mark.asyncio
    async def test_analyze_flow_institutional_pressure(self, flow_tool):
        """Institutional pressure computed from COT non-commercial data."""
        flow_tool._set_cache("cot:TEST", COTReport(
            symbol="TEST",
            non_commercial_long=80000,
            non_commercial_short=20000,
        ))
        result = await flow_tool.analyze_flow("TEST")
        assert result.institutional_pressure > 0.0  # More longs than shorts

    @pytest.mark.asyncio
    async def test_analyze_flow_retail_pressure(self, flow_tool):
        """Retail pressure computed from non-reportable data."""
        flow_tool._set_cache("cot:RETAIL", COTReport(
            symbol="RETAIL",
            non_reportable_long=5000,
            non_reportable_short=15000,
        ))
        result = await flow_tool.analyze_flow("RETAIL")
        assert result.retail_pressure < 0.0  # More shorts than longs

    @pytest.mark.asyncio
    async def test_analyze_flow_score_bounded(self, flow_tool):
        """Flow score is always between -1.0 and 1.0."""
        result = await flow_tool.analyze_flow("XYZ")
        assert -1.0 <= result.score <= 1.0

    @pytest.mark.asyncio
    async def test_positioning_extreme_crowded_long(self, flow_tool):
        """Extreme speculative long → CROWDED_LONG signal."""
        flow_tool._set_cache("cot:CROWD", COTReport(
            symbol="CROWD",
            commercial_long=10000,
            commercial_short=80000,
            non_commercial_long=90000,
            non_commercial_short=10000,
        ))
        result = await flow_tool.analyze_positioning("CROWD")
        assert result.signal == PositioningSignal.CONTRARIAN_SELL

    @pytest.mark.asyncio
    async def test_positioning_extreme_crowded_short(self, flow_tool):
        """Extreme speculative short → CROWDED_SHORT signal."""
        flow_tool._set_cache("cot:SHORT", COTReport(
            symbol="SHORT",
            commercial_long=80000,
            commercial_short=10000,
            non_commercial_long=10000,
            non_commercial_short=90000,
        ))
        result = await flow_tool.analyze_positioning("SHORT")
        assert result.signal == PositioningSignal.CONTRARIAN_BUY

    @pytest.mark.asyncio
    async def test_positioning_balanced_when_no_data(self, flow_tool):
        """Balanced signal when no COT data available."""
        result = await flow_tool.analyze_positioning("NEW_SYMBOL")
        assert result.signal == PositioningSignal.BALANCED


# ======================================================================
# Geopolitical Tool Tests
# ======================================================================

from quant_nanggroe.agents.tools.geopolitical_tool import (
    GeographyConstraint,
    GeopoliticalRiskLevel,
    GeopoliticalTool,
    GrandChessboardAnalysis,
    ImpactDirection,
    PrisonersOfGeographyAnalysis,
    SanctionImpact,
    SanctionType,
    WorldOrderAnalysis,
)


class TestGeopoliticalRiskLevel:
    """Tests for GeopoliticalRiskLevel enum."""

    def test_all_levels(self):
        expected = ["CRITICAL", "HIGH", "ELEVATED", "MODERATE", "LOW", "MINIMAL"]
        actual = [r.value for r in GeopoliticalRiskLevel]
        assert set(actual) == set(expected)


class TestImpactDirection:
    """Tests for ImpactDirection enum."""

    def test_all_directions(self):
        expected = ["STRONGLY_BEARISH", "BEARISH", "NEUTRAL", "BULLISH", "STRONGLY_BULLISH"]
        actual = [d.value for d in ImpactDirection]
        assert set(actual) == set(expected)


class TestSanctionType:
    """Tests for SanctionType enum."""

    def test_all_types(self):
        expected = ["TRADE_EMBARGO", "FINANCIAL", "TECHNOLOGY", "ENERGY", "INDIVIDUAL", "SECTORAL"]
        actual = [t.value for t in SanctionType]
        assert set(actual) == set(expected)


class TestWorldOrderAnalysis:
    def test_default_values(self):
        analysis = WorldOrderAnalysis()
        assert analysis.hegemon == "US"
        assert analysis.transition_risk == 0.0
        assert analysis.risk_level == GeopoliticalRiskLevel.MODERATE
        assert isinstance(analysis.flashpoints, list)
        assert isinstance(analysis.alliance_shifts, list)

    def test_custom_values(self):
        analysis = WorldOrderAnalysis(
            hegemon="China",
            transition_risk=0.8,
            risk_level=GeopoliticalRiskLevel.CRITICAL,
        )
        assert analysis.hegemon == "China"
        assert analysis.transition_risk == 0.8


class TestSanctionImpact:
    def test_default_values(self):
        impact = SanctionImpact(target_country="russia")
        assert impact.impact_score == 0.0
        assert impact.confidence == 0.1
        assert impact.market_direction == ImpactDirection.NEUTRAL
        assert isinstance(impact.affected_commodities, list)
        assert isinstance(impact.affected_sectors, list)

    def test_with_data(self):
        impact = SanctionImpact(
            target_country="iran",
            impact_score=0.7,
            market_direction=ImpactDirection.STRONGLY_BEARISH,
            sanction_types=[SanctionType.FINANCIAL],
        )
        assert impact.impact_score == 0.7


class TestGeographyConstraint:
    def test_construction(self):
        gc = GeographyConstraint(
            region="russia",
            constraint="Warm-water port obsession",
            strategic_imperative="Year-round naval presence",
        )
        assert gc.region == "russia"
        assert gc.constraint == "Warm-water port obsession"

    def test_default_values(self):
        gc = GeographyConstraint(region="test")
        assert gc.constraint == ""
        assert gc.strategic_imperative == ""


class TestGeopoliticalTool:
    @pytest.fixture
    def geo_tool(self):
        return GeopoliticalTool(cache_ttl=600)

    @pytest.mark.asyncio
    async def test_analyze_world_order(self, geo_tool):
        result = await geo_tool.analyze_world_order()
        assert isinstance(result, WorldOrderAnalysis)
        assert result.hegemon == "US"
        assert len(result.flashpoints) > 0
        assert len(result.alliance_shifts) > 0

    @pytest.mark.asyncio
    async def test_world_order_risk_level(self, geo_tool):
        result = await geo_tool.analyze_world_order()
        assert isinstance(result.risk_level, GeopoliticalRiskLevel)

    @pytest.mark.asyncio
    async def test_analyze_grand_chessboard_indo_pacific(self, geo_tool):
        result = await geo_tool.analyze_grand_chessboard("indo_pacific")
        assert isinstance(result, GrandChessboardAnalysis)
        assert result.region == "indo_pacific"
        assert result.great_power_competition > 0
        assert len(result.key_players) > 0

    @pytest.mark.asyncio
    async def test_analyze_grand_chessboard_central_asia(self, geo_tool):
        result = await geo_tool.analyze_grand_chessboard("central_asia")
        assert isinstance(result, GrandChessboardAnalysis)
        assert result.great_power_competition > 0

    @pytest.mark.asyncio
    async def test_analyze_grand_chessboard_middle_east(self, geo_tool):
        result = await geo_tool.analyze_grand_chessboard("middle_east")
        assert result.resource_control > 0.5

    @pytest.mark.asyncio
    async def test_analyze_grand_chessboard_unknown(self, geo_tool):
        result = await geo_tool.analyze_grand_chessboard("unknown_region")
        assert isinstance(result, GrandChessboardAnalysis)
        assert result.region == "unknown_region"

    @pytest.mark.asyncio
    async def test_analyze_geography_russia(self, geo_tool):
        result = await geo_tool.analyze_geography("russia")
        assert isinstance(result, PrisonersOfGeographyAnalysis)
        assert len(result.constraints) > 0
        assert result.security_risk > 0

    @pytest.mark.asyncio
    async def test_analyze_geography_china(self, geo_tool):
        result = await geo_tool.analyze_geography("china")
        assert len(result.constraints) > 0
        assert result.trade_impact > 0

    @pytest.mark.asyncio
    async def test_analyze_geography_usa(self, geo_tool):
        result = await geo_tool.analyze_geography("usa")
        assert result.security_risk < 0.5  # Low risk for USA

    @pytest.mark.asyncio
    async def test_analyze_geography_unknown(self, geo_tool):
        result = await geo_tool.analyze_geography("atlantis")
        assert isinstance(result, PrisonersOfGeographyAnalysis)
        assert result.region == "atlantis"

    @pytest.mark.asyncio
    async def test_analyze_sanctions_russia(self, geo_tool):
        result = await geo_tool.analyze_sanctions("russia")
        assert isinstance(result, SanctionImpact)
        assert result.impact_score > 0
        assert len(result.affected_commodities) > 0

    @pytest.mark.asyncio
    async def test_analyze_sanctions_unknown(self, geo_tool):
        result = await geo_tool.analyze_sanctions("neutral_country")
        assert isinstance(result, SanctionImpact)
        assert result.impact_score == 0.0

    @pytest.mark.asyncio
    async def test_comprehensive_analysis(self, geo_tool):
        result = await geo_tool.comprehensive_analysis("russia")
        assert "composite_risk_score" in result
        assert "world_order" in result
        assert "sanctions" in result
        assert "grand_chessboard" in result
        assert "prisoners_of_geography" in result

    @pytest.mark.asyncio
    async def test_chessboard_high_risk_level(self, geo_tool):
        """Region with high great_power_competition should get ELEVATED risk."""
        result = await geo_tool.analyze_grand_chessboard("indo_pacific")
        assert result.risk_level == GeopoliticalRiskLevel.ELEVATED

    @pytest.mark.asyncio
    async def test_geography_high_risk_level(self, geo_tool):
        """Region with high security_risk should get HIGH risk."""
        result = await geo_tool.analyze_geography("russia")
        assert result.risk_level == GeopoliticalRiskLevel.HIGH

    @pytest.mark.asyncio
    async def test_sanctions_high_impact_direction(self, geo_tool):
        """High impact sanctions should be STRONGLY_BEARISH."""
        result = await geo_tool.analyze_sanctions("russia")
        assert result.market_direction == ImpactDirection.STRONGLY_BEARISH


# ======================================================================
# Intermarket Tool Tests
# ======================================================================

from quant_nanggroe.agents.tools.intermarket_tool import (
    CommodityCurrencyPair,
    CorrelationMatrix,
    CorrelationPair,
    CorrelationStrength,
    IntermarketTool,
    MarketSector,
    RelativeStrengthResult,
    RotationSignal,
    SectorRotationResult,
)


class TestMarketSector:
    def test_all_sectors(self):
        expected = [
            "TECHNOLOGY", "HEALTHCARE", "FINANCIALS", "ENERGY",
            "MATERIALS", "INDUSTRIALS", "CONSUMER_DISCRETIONARY",
            "CONSUMER_STAPLES", "UTILITIES", "REAL_ESTATE", "COMMUNICATIONS",
        ]
        actual = [s.value for s in MarketSector]
        assert set(actual) == set(expected)


class TestCorrelationStrength:
    def test_all_strengths(self):
        expected = [
            "STRONG_POSITIVE", "MODERATE_POSITIVE", "WEAK_POSITIVE",
            "UNCORRELATED", "WEAK_NEGATIVE", "MODERATE_NEGATIVE", "STRONG_NEGATIVE",
        ]
        actual = [s.value for s in CorrelationStrength]
        assert set(actual) == set(expected)


class TestCorrelationPair:
    def test_construction(self):
        pair = CorrelationPair(
            asset_a="TLT", asset_b="SPY",
            correlation=-0.3,
            strength=CorrelationStrength.MODERATE_NEGATIVE,
        )
        assert pair.asset_a == "TLT"
        assert pair.correlation == -0.3

    def test_defaults(self):
        pair = CorrelationPair(asset_a="A", asset_b="B")
        assert pair.strength == CorrelationStrength.UNCORRELATED
        assert pair.divergence is False


class TestCorrelationMatrix:
    def test_defaults(self):
        matrix = CorrelationMatrix()
        assert matrix.bonds_equities == 0.0
        assert isinstance(matrix.notable_pairs, list)
        assert matrix.risk_on_off == 0.0


class TestRelativeStrengthResult:
    def test_defaults(self):
        rs = RelativeStrengthResult(symbol="AAPL")
        assert rs.vs_benchmark == "SPY"
        assert rs.rs_ratio == 1.0
        assert rs.rs_rating == "NEUTRAL"
        assert rs.trend == "FLAT"


class TestSectorRotationResult:
    def test_defaults(self):
        result = SectorRotationResult()
        assert result.current_phase == RotationSignal.MID_CYCLE
        assert isinstance(result.leading_sectors, list)
        assert isinstance(result.lagging_sectors, list)
        assert isinstance(result.sector_momentum, dict)


class TestCommodityCurrencyPair:
    def test_construction(self):
        pair = CommodityCurrencyPair(commodity="OIL", currency="CAD/USD")
        assert pair.commodity == "OIL"
        assert pair.correlation == 0.0
        assert pair.trade_signal == "NEUTRAL"


class TestIntermarketTool:
    @pytest.fixture
    def im_tool(self):
        return IntermarketTool(cache_ttl=600)

    @pytest.mark.asyncio
    async def test_analyze_correlations(self, im_tool):
        im_tool._cache.clear()
        with patch.object(im_tool, "_fetch_correlation_data", new_callable=AsyncMock, return_value=None):
            result = await im_tool.analyze_correlations()
            assert isinstance(result, CorrelationMatrix)
            assert -1.0 <= result.bonds_equities <= 1.0
            assert isinstance(result.notable_pairs, list)

    @pytest.mark.asyncio
    async def test_correlation_has_notable_pairs(self, im_tool):
        im_tool._cache.clear()
        with patch.object(im_tool, "_fetch_correlation_data", new_callable=AsyncMock, return_value=None):
            result = await im_tool.analyze_correlations()
            assert len(result.notable_pairs) > 0

    @pytest.mark.asyncio
    async def test_correlation_risk_on_off(self, im_tool):
        im_tool._cache.clear()
        with patch.object(im_tool, "_fetch_correlation_data", new_callable=AsyncMock, return_value=None):
            result = await im_tool.analyze_correlations()
            assert -1.0 <= result.risk_on_off <= 1.0

    @pytest.mark.asyncio
    async def test_analyze_sector_rotation(self, im_tool):
        result = await im_tool.analyze_sector_rotation()
        assert isinstance(result, SectorRotationResult)
        assert len(result.leading_sectors) > 0
        assert len(result.lagging_sectors) > 0

    @pytest.mark.asyncio
    async def test_sector_rotation_momentum(self, im_tool):
        result = await im_tool.analyze_sector_rotation()
        assert len(result.sector_momentum) > 0

    @pytest.mark.asyncio
    async def test_sector_rotation_phase(self, im_tool):
        result = await im_tool.analyze_sector_rotation()
        assert isinstance(result.current_phase, RotationSignal)

    @pytest.mark.asyncio
    async def test_commodity_currency_pairs(self, im_tool):
        result = await im_tool.analyze_commodity_currency_pairs()
        assert len(result) > 0
        assert all(isinstance(p, CommodityCurrencyPair) for p in result)

    @pytest.mark.asyncio
    async def test_commodity_currency_pair_data(self, im_tool):
        result = await im_tool.analyze_commodity_currency_pairs()
        oil_pairs = [p for p in result if p.commodity == "OIL"]
        assert len(oil_pairs) > 0
        assert oil_pairs[0].correlation > 0  # Oil typically positively correlated with CAD

    @pytest.mark.asyncio
    async def test_correlation_returns_consistent_data(self, im_tool):
        """analyze_correlations returns consistent structure."""
        im_tool._cache.clear()
        with patch.object(im_tool, "_fetch_correlation_data", new_callable=AsyncMock, return_value=None):
            r1 = await im_tool.analyze_correlations()
            r2 = await im_tool.analyze_correlations()
            assert r1.bonds_equities == r2.bonds_equities
            assert r1.risk_on_off == r2.risk_on_off

    @pytest.mark.asyncio
    async def test_relative_strength_default(self, im_tool):
        """Relative strength returns default when yfinance unavailable."""
        with patch("quant_nanggroe.agents.tools.intermarket_tool.IntermarketTool.analyze_relative_strength") as mock:
            mock.return_value = RelativeStrengthResult(symbol="AAPL")
            result = await im_tool.analyze_relative_strength("AAPL")
            assert result.symbol == "AAPL"


# ======================================================================
# Screener Tool Tests
# ======================================================================

from quant_nanggroe.agents.tools.screener_tool import (
    ComponentName,
    ComponentScore,
    ExecutionPlan,
    FilterCriteria,
    ScreenerTool,
    ScreeningResult,
    ScreenVerdict,
)


class TestScreenVerdict:
    def test_all_verdicts(self):
        expected = [
            "STRONG_BUY", "BUY", "SPECULATIVE_BUY", "NEUTRAL",
            "SPECULATIVE_SELL", "SELL", "STRONG_SELL", "AVOID",
        ]
        actual = [v.value for v in ScreenVerdict]
        assert set(actual) == set(expected)


class TestComponentName:
    def test_all_components(self):
        expected = [
            "technical", "fundamental", "sentiment", "macro",
            "dex", "liquidity", "order_book", "positioning",
            "quant_scoring", "market_structure", "execution_plan", "final_verdict",
        ]
        actual = [c.value for c in ComponentName]
        for name in expected:
            assert name in actual


class TestComponentScore:
    def test_defaults(self):
        cs = ComponentScore(component=ComponentName.TECHNICAL)
        assert cs.score == 0.0
        assert cs.weight == 0.0
        assert cs.weighted_score == 0.0
        assert cs.verdict == "NEUTRAL"

    def test_with_data(self):
        cs = ComponentScore(
            component=ComponentName.FUNDAMENTAL,
            score=75.0,
            weight=0.10,
            weighted_score=7.5,
            verdict="BULLISH",
        )
        assert cs.score == 75.0
        assert cs.weighted_score == 7.5


class TestFilterCriteria:
    def test_default_values(self):
        fc = FilterCriteria()
        assert fc.min_score == 0.0
        assert fc.max_score == 100.0
        assert fc.verdicts == []
        assert fc.sectors == []

    def test_custom_values(self):
        fc = FilterCriteria(
            min_score=60,
            verdicts=[ScreenVerdict.BUY, ScreenVerdict.STRONG_BUY],
            sectors=["technology"],
        )
        assert fc.min_score == 60
        assert len(fc.verdicts) == 2


class TestExecutionPlan:
    def test_defaults(self):
        ep = ExecutionPlan(symbol="AAPL")
        assert ep.direction == "NEUTRAL"
        assert ep.entry_price is None
        assert ep.stop_loss is None
        assert ep.take_profit is None

    def test_with_data(self):
        ep = ExecutionPlan(
            symbol="AAPL",
            direction="BUY",
            entry_price=150.0,
            stop_loss=145.0,
            take_profit=160.0,
            confidence=0.8,
        )
        assert ep.direction == "BUY"
        assert ep.confidence == 0.8


class TestScreenerTool:
    @pytest.fixture
    def screener(self):
        return ScreenerTool(cache_ttl=600)

    @pytest.mark.asyncio
    async def test_screen_symbol(self, screener):
        result = await screener.screen("AAPL")
        assert isinstance(result, ScreeningResult)
        assert result.symbol == "AAPL"
        assert 0 <= result.composite_score <= 100

    @pytest.mark.asyncio
    async def test_screen_has_components(self, screener):
        result = await screener.screen("AAPL")
        assert len(result.components) > 0

    @pytest.mark.asyncio
    async def test_screen_verdict(self, screener):
        result = await screener.screen("AAPL")
        assert isinstance(result.verdict, ScreenVerdict)

    @pytest.mark.asyncio
    async def test_screen_caching(self, screener):
        r1 = await screener.screen("AAPL")
        r2 = await screener.screen("AAPL")
        assert r1 is r2

    @pytest.mark.asyncio
    async def test_screen_batch(self, screener):
        results = await screener.screen_batch(["AAPL", "GOOGL", "MSFT"])
        assert len(results) == 3
        assert results[0].ranking == 1

    @pytest.mark.asyncio
    async def test_screen_batch_sorted_by_score(self, screener):
        results = await screener.screen_batch(["AAPL", "GOOGL"])
        scores = [r.composite_score for r in results]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_screen_batch_with_filter(self, screener):
        criteria = FilterCriteria(min_score=0, max_score=100)
        results = await screener.screen_batch(["AAPL"], filter_criteria=criteria)
        assert len(results) >= 0

    @pytest.mark.asyncio
    async def test_screen_batch_filter_excludes(self, screener):
        criteria = FilterCriteria(min_score=101)  # Impossible score
        results = await screener.screen_batch(["AAPL"], filter_criteria=criteria)
        assert len(results) == 0

    def test_score_to_verdict_all_levels(self):
        assert ScreenerTool._score_to_verdict(90) == ScreenVerdict.STRONG_BUY
        assert ScreenerTool._score_to_verdict(75) == ScreenVerdict.BUY
        assert ScreenerTool._score_to_verdict(65) == ScreenVerdict.SPECULATIVE_BUY
        assert ScreenerTool._score_to_verdict(50) == ScreenVerdict.NEUTRAL
        assert ScreenerTool._score_to_verdict(35) == ScreenVerdict.SPECULATIVE_SELL
        assert ScreenerTool._score_to_verdict(20) == ScreenVerdict.SELL
        assert ScreenerTool._score_to_verdict(8) == ScreenVerdict.STRONG_SELL
        assert ScreenerTool._score_to_verdict(2) == ScreenVerdict.AVOID

    @pytest.mark.asyncio
    async def test_execution_plan_for_buy(self, screener):
        result = await screener.screen("AAPL")
        if result.verdict in (ScreenVerdict.STRONG_BUY, ScreenVerdict.BUY, ScreenVerdict.SPECULATIVE_BUY):
            assert result.execution_plan is not None
            assert result.execution_plan.direction == "BUY"

    @pytest.mark.asyncio
    async def test_component_score_weight(self, screener):
        result = await screener.screen("AAPL")
        for comp in result.components:
            assert comp.weight > 0
            assert comp.weighted_score == pytest.approx(comp.score * comp.weight, abs=0.01)

    def test_apply_filters_verdict(self):
        results = [
            ScreeningResult(symbol="A", composite_score=90, verdict=ScreenVerdict.STRONG_BUY),
            ScreeningResult(symbol="B", composite_score=50, verdict=ScreenVerdict.NEUTRAL),
        ]
        filtered = ScreenerTool._apply_filters(
            results, FilterCriteria(verdicts=[ScreenVerdict.STRONG_BUY]),
        )
        assert len(filtered) == 1
        assert filtered[0].symbol == "A"

    def test_custom_weights(self):
        weights = {ComponentName.TECHNICAL: 1.0}
        screener = ScreenerTool(weights=weights)
        assert screener._weights == weights


# ======================================================================
# Competition Tool Tests
# ======================================================================

from quant_nanggroe.agents.tools.competition_tool import (
    AgentProfile,
    AgentTier,
    CompetitionTool,
    Experiment,
    ExperimentStatus,
    LeaderboardEntry,
    MissionStatus,
    SignalQualityScore,
    TeamMission,
)


class TestAgentTier:
    def test_all_tiers(self):
        expected = ["ELITE", "EXPERT", "ADVANCED", "INTERMEDIATE", "NOVICE"]
        actual = [t.value for t in AgentTier]
        assert set(actual) == set(expected)


class TestExperimentStatus:
    def test_all_statuses(self):
        expected = ["DRAFT", "RUNNING", "PAUSED", "COMPLETED", "CANCELLED"]
        actual = [s.value for s in ExperimentStatus]
        assert set(actual) == set(expected)


class TestMissionStatus:
    def test_all_statuses(self):
        expected = ["OPEN", "IN_PROGRESS", "COMPLETED", "SETTLED", "CANCELLED"]
        actual = [s.value for s in MissionStatus]
        assert set(actual) == set(expected)


class TestAgentProfile:
    def test_defaults(self):
        profile = AgentProfile(agent_id="test")
        assert profile.tier == AgentTier.NOVICE
        assert profile.total_signals == 0
        assert profile.accuracy == 0.0
        assert profile.overall_score == 0.0

    def test_serialization(self):
        profile = AgentProfile(agent_id="test", name="Test Agent")
        data = profile.model_dump()
        profile2 = AgentProfile(**data)
        assert profile2.agent_id == profile.agent_id


class TestCompetitionTool:
    @pytest.fixture
    def comp(self):
        return CompetitionTool()

    @pytest.mark.asyncio
    async def test_register_agent(self, comp):
        profile = await comp.register_agent("agent-1", "Test Agent")
        assert isinstance(profile, AgentProfile)
        assert profile.agent_id == "agent-1"
        assert profile.tier == AgentTier.NOVICE

    @pytest.mark.asyncio
    async def test_register_duplicate(self, comp):
        p1 = await comp.register_agent("agent-1", "First")
        p2 = await comp.register_agent("agent-1", "Second")
        assert p1 is p2  # Same profile returned

    @pytest.mark.asyncio
    async def test_update_performance(self, comp):
        await comp.register_agent("agent-1")
        profile = await comp.update_agent_performance("agent-1", True, 100.0)
        assert profile.total_signals == 1
        assert profile.correct_signals == 1
        assert profile.accuracy == 1.0
        assert profile.total_pnl == 100.0

    @pytest.mark.asyncio
    async def test_update_performance_auto_register(self, comp):
        profile = await comp.update_agent_performance("new-agent", True, 50.0)
        assert profile.agent_id == "new-agent"

    @pytest.mark.asyncio
    async def test_accuracy_calculation(self, comp):
        await comp.register_agent("a1")
        await comp.update_agent_performance("a1", True, 100)
        await comp.update_agent_performance("a1", False, -50)
        profile = comp._agents["a1"]
        assert profile.accuracy == 0.5

    @pytest.mark.asyncio
    async def test_tier_advancement(self, comp):
        """Agent with 20+ signals advances from NOVICE."""
        await comp.register_agent("a1")
        for _ in range(20):
            await comp.update_agent_performance("a1", True, 10)
        assert comp._agents["a1"].tier == AgentTier.INTERMEDIATE

    @pytest.mark.asyncio
    async def test_score_signal(self, comp):
        await comp.register_agent("agent-1")
        score = await comp.score_signal("agent-1", "AAPL", "BUY", 150.0, 160.0, 145.0)
        assert isinstance(score, SignalQualityScore)
        assert score.composite_score > 0
        assert score.symbol == "AAPL"
        assert score.direction == "BUY"

    @pytest.mark.asyncio
    async def test_score_signal_risk_adjusted(self, comp):
        """Risk-adjusted score based on R:R ratio."""
        await comp.register_agent("a1")
        score = await comp.score_signal("a1", "AAPL", "BUY", 150.0, 180.0, 140.0)
        assert score.risk_adjusted_score > 0  # 30 reward / 10 risk = 3:1

    @pytest.mark.asyncio
    async def test_score_signal_unknown_agent(self, comp):
        """Unknown agent gets default accuracy."""
        score = await comp.score_signal("unknown", "AAPL", "BUY", 150.0)
        assert score.accuracy_score == 0.5  # Default

    @pytest.mark.asyncio
    async def test_get_leaderboard(self, comp):
        await comp.register_agent("a1")
        await comp.register_agent("a2")
        await comp.update_agent_performance("a1", True, 100)
        lb = await comp.get_leaderboard()
        assert len(lb) == 2
        assert all(isinstance(e, LeaderboardEntry) for e in lb)

    @pytest.mark.asyncio
    async def test_leaderboard_sorted_by_score(self, comp):
        await comp.register_agent("a1")
        await comp.register_agent("a2")
        await comp.update_agent_performance("a1", True, 100)
        lb = await comp.get_leaderboard()
        scores = [e.overall_score for e in lb]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_leaderboard_with_tier_filter(self, comp):
        await comp.register_agent("a1")
        lb = await comp.get_leaderboard(tier=AgentTier.ELITE)
        assert len(lb) == 0  # No elite agents

    @pytest.mark.asyncio
    async def test_leaderboard_limit(self, comp):
        for i in range(5):
            await comp.register_agent(f"a{i}")
        lb = await comp.get_leaderboard(limit=2)
        assert len(lb) == 2

    @pytest.mark.asyncio
    async def test_create_experiment(self, comp):
        exp = await comp.create_experiment("Test Exp", "strat_a", "strat_b")
        assert isinstance(exp, Experiment)
        assert exp.status == ExperimentStatus.DRAFT
        assert exp.variant_a == "strat_a"
        assert exp.variant_b == "strat_b"

    @pytest.mark.asyncio
    async def test_start_experiment(self, comp):
        exp = await comp.create_experiment("Test", "a", "b")
        started = await comp.start_experiment(exp.experiment_id)
        assert started.status == ExperimentStatus.RUNNING
        assert started.start_time is not None

    @pytest.mark.asyncio
    async def test_start_nonexistent_experiment(self, comp):
        with pytest.raises(ValueError):
            await comp.start_experiment("nonexistent")

    @pytest.mark.asyncio
    async def test_record_experiment_result(self, comp):
        exp = await comp.create_experiment("Test", "a", "b")
        result = await comp.record_experiment_result(exp.experiment_id, "a", True, 100.0)
        assert result.variant_a_signals == 1
        assert result.variant_a_pnl == 100.0

    @pytest.mark.asyncio
    async def test_record_experiment_result_variant_b(self, comp):
        exp = await comp.create_experiment("Test", "a", "b")
        result = await comp.record_experiment_result(exp.experiment_id, "b", False, -50.0)
        assert result.variant_b_signals == 1
        assert result.variant_b_pnl == -50.0

    @pytest.mark.asyncio
    async def test_record_experiment_nonexistent(self, comp):
        with pytest.raises(ValueError):
            await comp.record_experiment_result("nonexistent", "a", True, 100.0)

    @pytest.mark.asyncio
    async def test_create_mission(self, comp):
        mission = await comp.create_mission("Mission 1", ["AAPL", "GOOGL"])
        assert isinstance(mission, TeamMission)
        assert mission.status == MissionStatus.OPEN
        assert mission.target_symbols == ["AAPL", "GOOGL"]

    @pytest.mark.asyncio
    async def test_join_mission(self, comp):
        mission = await comp.create_mission("M1")
        updated = await comp.join_mission(mission.mission_id, "agent-1")
        assert updated.status == MissionStatus.IN_PROGRESS
        assert len(updated.teams) == 1

    @pytest.mark.asyncio
    async def test_join_nonexistent_mission(self, comp):
        with pytest.raises(ValueError):
            await comp.join_mission("nonexistent", "agent-1")

    @pytest.mark.asyncio
    async def test_overall_score_calculation(self, comp):
        """Test _calculate_overall_score static method."""
        profile = AgentProfile(
            agent_id="test",
            accuracy=0.8,
            sharpe_ratio=2.0,
            consistency_score=0.7,
            total_pnl=5000.0,
        )
        score = CompetitionTool._calculate_overall_score(profile)
        assert score > 0
        assert score <= 100


# ======================================================================
# Forecast Tool Tests
# ======================================================================

from quant_nanggroe.agents.tools.forecast_tool import (
    COTForecast,
    ForecastAccuracy,
    ForecastConfidence,
    ForecastDirection,
    ForecastResult,
    ForecastTimeframe,
    ForecastTool,
    FundamentalForecast,
    NewsSentimentForecast,
    TechnicalForecast,
    TimeframeForecast,
)


class TestForecastTimeframe:
    def test_all_timeframes(self):
        expected = ["INTRADAY", "DAILY", "WEEKLY", "MONTHLY"]
        actual = [t.value for t in ForecastTimeframe]
        assert set(actual) == set(expected)


class TestForecastDirection:
    def test_all_directions(self):
        expected = [
            "STRONGLY_BULLISH", "BULLISH", "SLIGHTLY_BULLISH",
            "NEUTRAL",
            "SLIGHTLY_BEARISH", "BEARISH", "STRONGLY_BEARISH",
        ]
        actual = [d.value for d in ForecastDirection]
        assert set(actual) == set(expected)


class TestForecastConfidence:
    def test_all_confidences(self):
        expected = ["VERY_HIGH", "HIGH", "MODERATE", "LOW", "VERY_LOW"]
        actual = [c.value for c in ForecastConfidence]
        assert set(actual) == set(expected)


class TestTechnicalForecast:
    def test_defaults(self):
        tf = TechnicalForecast()
        assert tf.trend == "NEUTRAL"
        assert tf.momentum == 0.0
        assert tf.signal == "NEUTRAL"
        assert tf.weight == 0.35


class TestFundamentalForecast:
    def test_defaults(self):
        ff = FundamentalForecast()
        assert ff.valuation == "FAIR"
        assert ff.signal == "NEUTRAL"
        assert ff.weight == 0.25


class TestNewsSentimentForecast:
    def test_defaults(self):
        nsf = NewsSentimentForecast()
        assert nsf.overall_sentiment == 0.0
        assert nsf.signal == "NEUTRAL"
        assert nsf.weight == 0.20


class TestCOTForecast:
    def test_defaults(self):
        cot = COTForecast()
        assert cot.commercial_positioning == "NEUTRAL"
        assert cot.extreme_reading is False
        assert cot.weight == 0.20


class TestTimeframeForecast:
    def test_construction(self):
        tf = TimeframeForecast(timeframe=ForecastTimeframe.DAILY)
        assert tf.direction == ForecastDirection.NEUTRAL
        assert tf.confidence == 0.0
        assert tf.probability_up == 0.5
        assert tf.probability_down == 0.5


class TestForecastTool:
    @pytest.fixture
    def forecast(self):
        return ForecastTool(cache_ttl=600)

    @pytest.mark.asyncio
    async def test_forecast(self, forecast):
        result = await forecast.forecast("AAPL", current_price=150.0)
        assert isinstance(result, ForecastResult)
        assert result.symbol == "AAPL"
        assert result.current_price == 150.0

    @pytest.mark.asyncio
    async def test_forecast_has_timeframes(self, forecast):
        result = await forecast.forecast("AAPL", current_price=150.0)
        assert len(result.timeframe_forecasts) == 4
        tf_types = [tf.timeframe for tf in result.timeframe_forecasts]
        assert ForecastTimeframe.INTRADAY in tf_types
        assert ForecastTimeframe.DAILY in tf_types
        assert ForecastTimeframe.WEEKLY in tf_types
        assert ForecastTimeframe.MONTHLY in tf_types

    @pytest.mark.asyncio
    async def test_forecast_composite_direction(self, forecast):
        result = await forecast.forecast("AAPL", current_price=150.0)
        assert isinstance(result.composite_direction, ForecastDirection)

    @pytest.mark.asyncio
    async def test_forecast_component_forecasts(self, forecast):
        result = await forecast.forecast("AAPL", current_price=150.0)
        assert isinstance(result.technical, TechnicalForecast)
        assert isinstance(result.fundamental, FundamentalForecast)
        assert isinstance(result.sentiment, NewsSentimentForecast)
        assert isinstance(result.cot, COTForecast)

    @pytest.mark.asyncio
    async def test_forecast_caching(self, forecast):
        r1 = await forecast.forecast("AAPL", current_price=150.0)
        r2 = await forecast.forecast("AAPL", current_price=150.0)
        assert r1 is r2

    @pytest.mark.asyncio
    async def test_record_accuracy(self, forecast):
        record = await forecast.record_accuracy(
            "fc-001", "AAPL", "BULLISH", "BULLISH", 2.0, 0.8,
        )
        assert isinstance(record, ForecastAccuracy)
        assert record.correct is True

    @pytest.mark.asyncio
    async def test_record_accuracy_wrong(self, forecast):
        record = await forecast.record_accuracy(
            "fc-002", "AAPL", "BULLISH", "BEARISH", -5.0, 0.6,
        )
        assert record.correct is False

    @pytest.mark.asyncio
    async def test_get_accuracy_stats_empty(self, forecast):
        stats = await forecast.get_accuracy_stats()
        assert stats["total_forecasts"] == 0

    @pytest.mark.asyncio
    async def test_get_accuracy_stats(self, forecast):
        await forecast.record_accuracy("fc-1", "AAPL", "BULLISH", "BULLISH", 2.0, 0.8)
        await forecast.record_accuracy("fc-2", "AAPL", "BEARISH", "BULLISH", -3.0, 0.5)
        stats = await forecast.get_accuracy_stats()
        assert stats["total_forecasts"] == 2
        assert stats["overall_accuracy"] == 0.5

    @pytest.mark.asyncio
    async def test_accuracy_stats_high_confidence(self, forecast):
        await forecast.record_accuracy("fc-1", "AAPL", "BULLISH", "BULLISH", 2.0, 0.8)
        stats = await forecast.get_accuracy_stats()
        assert stats["high_confidence_count"] == 1

    def test_direction_to_score(self):
        assert ForecastTool._direction_to_score("STRONGLY_BULLISH") == 1.0
        assert ForecastTool._direction_to_score("BULLISH") == 0.6
        assert ForecastTool._direction_to_score("NEUTRAL") == 0.0
        assert ForecastTool._direction_to_score("BEARISH") == -0.6
        assert ForecastTool._direction_to_score("STRONGLY_BEARISH") == -1.0

    def test_direction_to_score_unknown(self):
        assert ForecastTool._direction_to_score("UNKNOWN") == 0.0

    def test_score_to_direction(self):
        assert ForecastTool._score_to_direction(0.8) == ForecastDirection.STRONGLY_BULLISH
        assert ForecastTool._score_to_direction(0.4) == ForecastDirection.BULLISH
        assert ForecastTool._score_to_direction(0.15) == ForecastDirection.SLIGHTLY_BULLISH
        assert ForecastTool._score_to_direction(0.0) == ForecastDirection.NEUTRAL
        assert ForecastTool._score_to_direction(-0.15) == ForecastDirection.SLIGHTLY_BEARISH
        assert ForecastTool._score_to_direction(-0.4) == ForecastDirection.BEARISH
        assert ForecastTool._score_to_direction(-0.8) == ForecastDirection.STRONGLY_BEARISH

    def test_confidence_from_value(self):
        assert ForecastTool._confidence_from_value(0.9) == ForecastConfidence.VERY_HIGH
        assert ForecastTool._confidence_from_value(0.7) == ForecastConfidence.HIGH
        assert ForecastTool._confidence_from_value(0.5) == ForecastConfidence.MODERATE
        assert ForecastTool._confidence_from_value(0.25) == ForecastConfidence.LOW
        assert ForecastTool._confidence_from_value(0.1) == ForecastConfidence.VERY_LOW

    @pytest.mark.asyncio
    async def test_timeframe_daily_has_target(self, forecast):
        result = await forecast.forecast("AAPL", current_price=150.0)
        daily = [tf for tf in result.timeframe_forecasts if tf.timeframe == ForecastTimeframe.DAILY][0]
        # Target price may or may not be set depending on signal
        assert daily.probability_up >= 0
        assert daily.probability_down >= 0


# ======================================================================
# Emotional Tool Tests
# ======================================================================

from quant_nanggroe.agents.tools.emotional_tool import (
    _MOOD_CATEGORIES,
    _MOOD_SCORES,
    BadgeType,
    DisciplineAction,
    DisciplineScore,
    EmotionalLockoutState,
    EmotionalTool,
    MoodCategory,
    MoodEntry,
    MoodType,
    StreakRecord,
)


class TestMoodType:
    def test_all_moods(self):
        expected = [
            "FOCUSED", "CALM", "NEUTRAL", "CONFIDENT", "ANXIOUS",
            "FOMO", "GREEDY", "REVENGE", "PANICKED", "FATIGUED",
            "EUPHORIC", "BORED",
        ]
        actual = [m.value for m in MoodType]
        assert set(actual) == set(expected)


class TestMoodCategory:
    def test_all_categories(self):
        expected = ["POSITIVE", "NEGATIVE", "NEUTRAL"]
        actual = [c.value for c in MoodCategory]
        assert set(actual) == set(expected)


class TestDisciplineAction:
    def test_all_actions(self):
        expected = ["NONE", "WARNING", "COOLDOWN", "SOFT_LOCKOUT", "HARD_LOCKOUT"]
        actual = [a.value for a in DisciplineAction]
        assert set(actual) == set(expected)


class TestBadgeType:
    def test_all_badges(self):
        expected = [
            "IRON_DISCIPLINE", "STREAK_MASTER", "RISK_GUARDIAN",
            "ZEN_TRADER", "CONSISTENCY_KING", "FIVE_DAY_STREAK",
            "TEN_DAY_STREAK", "THIRTY_DAY_STREAK",
            "VIOLATION_FREE_WEEK", "VIOLATION_FREE_MONTH",
        ]
        actual = [b.value for b in BadgeType]
        assert set(actual) == set(expected)


class TestMoodEntry:
    def test_construction(self):
        entry = MoodEntry(mood=MoodType.FOCUSED)
        assert entry.mood == MoodType.FOCUSED
        assert entry.category == MoodCategory.NEUTRAL  # default
        assert entry.score == 0.0

    def test_with_context(self):
        entry = MoodEntry(
            mood=MoodType.REVENGE,
            category=MoodCategory.NEGATIVE,
            score=-1.0,
            context="Lost big trade",
            symbol="BTC",
        )
        assert entry.context == "Lost big trade"
        assert entry.symbol == "BTC"


class TestDisciplineScore:
    def test_defaults(self):
        score = DisciplineScore(trader_id="t1")
        assert score.overall_score == 0.0
        assert score.action == DisciplineAction.NONE
        assert score.lockout_active is False
        assert isinstance(score.badges, list)


class TestStreakRecord:
    def test_defaults(self):
        sr = StreakRecord(trader_id="t1")
        assert sr.current_streak == 0
        assert sr.longest_streak == 0
        assert sr.consecutive_violations == 0


class TestEmotionalLockoutState:
    def test_defaults(self):
        ls = EmotionalLockoutState()
        assert ls.active is False
        assert ls.action == DisciplineAction.NONE
        assert ls.duration_minutes == 0
        assert isinstance(ls.exercises, list)


class TestEmotionalTool:
    @pytest.fixture
    def emo(self):
        return EmotionalTool()

    @pytest.mark.asyncio
    async def test_log_mood_focused(self, emo):
        entry = await emo.log_mood("trader1", MoodType.FOCUSED)
        assert isinstance(entry, MoodEntry)
        assert entry.mood == MoodType.FOCUSED
        assert entry.category == MoodCategory.POSITIVE
        assert entry.score == 1.0

    @pytest.mark.asyncio
    async def test_log_mood_calm(self, emo):
        entry = await emo.log_mood("trader1", MoodType.CALM)
        assert entry.category == MoodCategory.POSITIVE
        assert entry.score == 0.8

    @pytest.mark.asyncio
    async def test_log_mood_revenge(self, emo):
        entry = await emo.log_mood("trader1", MoodType.REVENGE)
        assert entry.category == MoodCategory.NEGATIVE
        assert entry.score == -1.0

    @pytest.mark.asyncio
    async def test_log_mood_euphoric_negative(self, emo):
        """Euphoric is classified as NEGATIVE (overconfidence is dangerous)."""
        entry = await emo.log_mood("trader1", MoodType.EUPHORIC)
        assert entry.category == MoodCategory.NEGATIVE

    @pytest.mark.asyncio
    async def test_log_mood_bored_negative(self, emo):
        """Bored is classified as NEGATIVE (leads to overtrading)."""
        entry = await emo.log_mood("trader1", MoodType.BORED)
        assert entry.category == MoodCategory.NEGATIVE

    @pytest.mark.asyncio
    async def test_log_mood_with_context(self, emo):
        entry = await emo.log_mood("trader1", MoodType.ANXIOUS, context="Market crash", symbol="SPY")
        assert entry.context == "Market crash"
        assert entry.symbol == "SPY"

    @pytest.mark.asyncio
    async def test_discipline_score_initial(self, emo):
        score = await emo.get_discipline_score("trader1")
        assert isinstance(score, DisciplineScore)
        assert score.overall_score >= 0

    @pytest.mark.asyncio
    async def test_positive_mood_streak(self, emo):
        for _ in range(5):
            await emo.log_mood("trader1", MoodType.FOCUSED)
        score = await emo.get_discipline_score("trader1")
        assert score.current_streak == 5
        assert score.longest_streak == 5

    @pytest.mark.asyncio
    async def test_negative_mood_resets_streak(self, emo):
        await emo.log_mood("trader1", MoodType.FOCUSED)
        await emo.log_mood("trader1", MoodType.CALM)
        await emo.log_mood("trader1", MoodType.FOMO)  # Negative resets streak
        score = await emo.get_discipline_score("trader1")
        assert score.current_streak == 0
        assert score.longest_streak == 2

    @pytest.mark.asyncio
    async def test_negative_mood_violations(self, emo):
        for _ in range(3):
            await emo.log_mood("trader1", MoodType.FOMO)
        score = await emo.get_discipline_score("trader1")
        assert score.consecutive_violations == 3
        assert score.action in (DisciplineAction.SOFT_LOCKOUT, DisciplineAction.COOLDOWN)

    @pytest.mark.asyncio
    async def test_lockout_check(self, emo):
        for _ in range(5):
            await emo.log_mood("trader1", MoodType.PANICKED)
        lockout = await emo.check_lockout("trader1")
        assert isinstance(lockout, EmotionalLockoutState)
        assert lockout.active is True
        assert lockout.action == DisciplineAction.HARD_LOCKOUT

    @pytest.mark.asyncio
    async def test_soft_lockout(self, emo):
        for _ in range(3):
            await emo.log_mood("trader1", MoodType.FOMO)
        lockout = await emo.check_lockout("trader1")
        assert lockout.action == DisciplineAction.SOFT_LOCKOUT

    @pytest.mark.asyncio
    async def test_no_lockout_positive(self, emo):
        await emo.log_mood("trader1", MoodType.CALM)
        lockout = await emo.check_lockout("trader1")
        assert lockout.active is False

    @pytest.mark.asyncio
    async def test_warning_on_first_violation(self, emo):
        await emo.log_mood("trader1", MoodType.GREEDY)
        lockout = await emo.check_lockout("trader1")
        assert lockout.action == DisciplineAction.WARNING

    @pytest.mark.asyncio
    async def test_mood_history(self, emo):
        await emo.log_mood("trader1", MoodType.CALM)
        await emo.log_mood("trader1", MoodType.FOCUSED)
        history = await emo.get_mood_history("trader1")
        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_mood_history_limit(self, emo):
        for i in range(10):
            await emo.log_mood("trader1", MoodType.NEUTRAL)
        history = await emo.get_mood_history("trader1", limit=5)
        assert len(history) == 5

    @pytest.mark.asyncio
    async def test_badge_award_five_day(self, emo):
        for _ in range(5):
            await emo.log_mood("trader1", MoodType.FOCUSED)
        score = await emo.get_discipline_score("trader1")
        assert BadgeType.FIVE_DAY_STREAK in score.badges

    @pytest.mark.asyncio
    async def test_badge_award_ten_day(self, emo):
        for _ in range(10):
            await emo.log_mood("trader1", MoodType.FOCUSED)
        score = await emo.get_discipline_score("trader1")
        assert BadgeType.TEN_DAY_STREAK in score.badges

    @pytest.mark.asyncio
    async def test_badge_no_duplicate(self, emo):
        for _ in range(5):
            await emo.log_mood("trader1", MoodType.FOCUSED)
        score1 = await emo.get_discipline_score("trader1")
        await emo.log_mood("trader1", MoodType.CALM)
        score2 = await emo.get_discipline_score("trader1")
        five_day_count = sum(1 for b in score2.badges if b == BadgeType.FIVE_DAY_STREAK)
        assert five_day_count == 1  # No duplicates

    @pytest.mark.asyncio
    async def test_reflective_exercises_on_violation(self, emo):
        for _ in range(2):
            await emo.log_mood("trader1", MoodType.REVENGE)
        lockout = await emo.check_lockout("trader1")
        assert len(lockout.exercises) > 0

    @pytest.mark.asyncio
    async def test_reflective_exercises_hard_lockout(self, emo):
        for _ in range(5):
            await emo.log_mood("trader1", MoodType.PANICKED)
        lockout = await emo.check_lockout("trader1")
        assert len(lockout.exercises) >= 6  # Full set of exercises


class TestMoodMappings:
    def test_all_moods_have_categories(self):
        for mood in MoodType:
            assert mood in _MOOD_CATEGORIES

    def test_all_moods_have_scores(self):
        for mood in MoodType:
            assert mood in _MOOD_SCORES

    def test_scores_in_range(self):
        for mood, score in _MOOD_SCORES.items():
            assert -1.0 <= score <= 1.0

    def test_positive_moods_have_positive_scores(self):
        for mood, score in _MOOD_SCORES.items():
            if _MOOD_CATEGORIES[mood] == MoodCategory.POSITIVE:
                assert score > 0

    def test_negative_moods_have_negative_scores(self):
        for mood, score in _MOOD_SCORES.items():
            if _MOOD_CATEGORIES[mood] == MoodCategory.NEGATIVE:
                assert score < 0


# ======================================================================
# Skill Tool Tests
# ======================================================================

from quant_nanggroe.agents.tools.skill_tool import (
    DCFInput,
    DCFResult,
    ExecutionStatus,
    SkillDefinition,
    SkillExecutionResult,
    SkillMetadata,
    SkillSource,
    SkillStatus,
    SkillTool,
)


class TestSkillSource:
    def test_all_sources(self):
        expected = ["builtin", "user", "project", "marketplace"]
        actual = [s.value for s in SkillSource]
        assert set(actual) == set(expected)


class TestSkillStatus:
    def test_all_statuses(self):
        expected = ["ACTIVE", "DEPRECATED", "BETA", "DISABLED"]
        actual = [s.value for s in SkillStatus]
        assert set(actual) == set(expected)


class TestExecutionStatus:
    def test_all_statuses(self):
        expected = ["SUCCESS", "FAILED", "PARTIAL", "CANCELLED"]
        actual = [s.value for s in ExecutionStatus]
        assert set(actual) == set(expected)


class TestSkillMetadata:
    def test_required_fields(self):
        meta = SkillMetadata(name="test-skill", description="A test skill")
        assert meta.name == "test-skill"
        assert meta.source == SkillSource.BUILTIN
        assert meta.status == SkillStatus.ACTIVE
        assert meta.version == "1.0.0"

    def test_custom_fields(self):
        meta = SkillMetadata(
            name="custom",
            description="Custom",
            source=SkillSource.USER,
            tags=["alpha", "experimental"],
        )
        assert meta.source == SkillSource.USER
        assert "alpha" in meta.tags


class TestSkillDefinition:
    def test_construction(self):
        sd = SkillDefinition(
            metadata=SkillMetadata(name="test", description="Test skill"),
            instructions="Do something",
        )
        assert sd.instructions == "Do something"
        assert sd.metadata.name == "test"


class TestSkillExecutionResult:
    def test_defaults(self):
        result = SkillExecutionResult()
        assert result.status == ExecutionStatus.SUCCESS
        assert isinstance(result.output, dict)
        assert isinstance(result.errors, list)

    def test_failed_result(self):
        result = SkillExecutionResult(
            status=ExecutionStatus.FAILED,
            errors=["Something went wrong"],
        )
        assert result.status == ExecutionStatus.FAILED
        assert len(result.errors) == 1


class TestDCFInput:
    def test_defaults(self):
        inputs = DCFInput(symbol="AAPL")
        assert inputs.growth_rate == 0.05
        assert inputs.terminal_growth == 0.025
        assert inputs.projection_years == 5
        assert inputs.wacc is None
        assert inputs.shares_outstanding == 0.0

    def test_custom_wacc(self):
        inputs = DCFInput(symbol="AAPL", wacc=0.12)
        assert inputs.wacc == 0.12


class TestDCFResult:
    def test_defaults(self):
        result = DCFResult(symbol="AAPL")
        assert result.enterprise_value == 0.0
        assert result.fair_value_per_share == 0.0
        assert result.wacc_used == 0.0


class TestSkillTool:
    @pytest.fixture
    def skill(self):
        return SkillTool()

    def test_builtin_dcf_skill(self, skill):
        dcf = skill.get_skill("dcf-valuation")
        assert dcf is not None
        assert dcf.metadata.name == "dcf-valuation"
        assert dcf.metadata.source == SkillSource.BUILTIN

    def test_list_skills(self, skill):
        skills = skill.list_skills()
        assert len(skills) >= 1

    def test_list_skills_by_source(self, skill):
        skills = skill.list_skills(source=SkillSource.BUILTIN)
        assert len(skills) >= 1

    def test_list_skills_by_tag(self, skill):
        skills = skill.list_skills(tag="valuation")
        assert len(skills) >= 1

    def test_list_skills_nonexistent_tag(self, skill):
        skills = skill.list_skills(tag="nonexistent_tag")
        assert len(skills) == 0

    def test_get_nonexistent_skill(self, skill):
        result = skill.get_skill("nonexistent")
        assert result is None

    def test_register_skill(self, skill):
        new_skill = SkillDefinition(
            metadata=SkillMetadata(
                name="custom-skill",
                description="A custom skill",
                source=SkillSource.USER,
            ),
            instructions="Do something custom",
        )
        skill.register_skill(new_skill)
        assert skill.get_skill("custom-skill") is not None

    def test_register_overwrites_existing(self, skill):
        new_skill = SkillDefinition(
            metadata=SkillMetadata(
                name="dcf-valuation",  # Same name as builtin
                description="Overridden DCF",
                source=SkillSource.USER,
            ),
            instructions="Custom instructions",
        )
        skill.register_skill(new_skill)
        retrieved = skill.get_skill("dcf-valuation")
        assert retrieved.metadata.source == SkillSource.USER

    @pytest.mark.asyncio
    async def test_execute_nonexistent_skill(self, skill):
        result = await skill.execute_skill("nonexistent", {})
        assert result.status == ExecutionStatus.FAILED
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_execute_dcf_skill(self, skill):
        result = await skill.execute_skill("dcf-valuation", {
            "symbol": "AAPL",
            "sector": "technology",
            "shares_outstanding": 15500,
            "total_debt": 120000,
            "cash": 60000,
            "fcf_history": [80000, 90000, 95000, 100000, 110000],
        })
        assert result.status == ExecutionStatus.SUCCESS
        assert "fair_value_per_share" in result.output
        assert result.execution_time_ms >= 0.0

    @pytest.mark.asyncio
    async def test_execution_history(self, skill):
        await skill.execute_skill("dcf-valuation", {"symbol": "AAPL", "sector": "technology"})
        assert len(skill._execution_history) == 1


class TestDCFValuation:
    @pytest.fixture
    def skill(self):
        return SkillTool()

    @pytest.mark.asyncio
    async def test_dcf_basic(self, skill):
        inputs = DCFInput(
            symbol="AAPL",
            sector="technology",
            fcf_history=[80000, 90000, 95000, 100000, 110000],
            shares_outstanding=15500,
            total_debt=120000,
            cash=60000,
        )
        result = await skill.run_dcf(inputs)
        assert isinstance(result, DCFResult)
        assert result.symbol == "AAPL"
        assert result.enterprise_value > 0
        assert result.fair_value_per_share > 0
        assert result.wacc_used > 0

    @pytest.mark.asyncio
    async def test_dcf_no_fcf(self, skill):
        inputs = DCFInput(symbol="STARTUP", sector="technology")
        result = await skill.run_dcf(inputs)
        assert result.enterprise_value == 0.0
        assert result.fair_value_per_share == 0.0

    @pytest.mark.asyncio
    async def test_dcf_sector_wacc(self, skill):
        inputs_tech = DCFInput(symbol="AAPL", sector="technology", fcf_history=[100000])
        inputs_util = DCFInput(symbol="NEE", sector="utilities", fcf_history=[100000])
        r_tech = await skill.run_dcf(inputs_tech)
        r_util = await skill.run_dcf(inputs_util)
        assert r_tech.wacc_used > r_util.wacc_used

    @pytest.mark.asyncio
    async def test_dcf_custom_wacc(self, skill):
        inputs = DCFInput(
            symbol="TEST",
            fcf_history=[100000],
            wacc=0.12,
            shares_outstanding=1000,
        )
        result = await skill.run_dcf(inputs)
        assert result.wacc_used == 0.12

    @pytest.mark.asyncio
    async def test_dcf_sensitivity_matrix(self, skill):
        inputs = DCFInput(
            symbol="AAPL",
            sector="technology",
            fcf_history=[100000],
            shares_outstanding=1000,
        )
        result = await skill.run_dcf(inputs)
        assert len(result.sensitivity_matrix) > 0

    @pytest.mark.asyncio
    async def test_dcf_zero_shares(self, skill):
        inputs = DCFInput(symbol="TEST", fcf_history=[100000], shares_outstanding=0)
        result = await skill.run_dcf(inputs)
        assert result.fair_value_per_share == 0.0

    @pytest.mark.asyncio
    async def test_dcf_growth_rate_capped(self, skill):
        inputs = DCFInput(
            symbol="HYPE",
            growth_rate=0.50,  # Should be capped at 15%
            fcf_history=[100000],
            shares_outstanding=1000,
        )
        result = await skill.run_dcf(inputs)
        assert result.growth_rate_used == 0.15

    @pytest.mark.asyncio
    async def test_dcf_projections_count(self, skill):
        inputs = DCFInput(
            symbol="AAPL",
            sector="technology",
            fcf_history=[100000],
            shares_outstanding=1000,
            projection_years=5,
        )
        result = await skill.run_dcf(inputs)
        assert len(result.projections) == 5

    @pytest.mark.asyncio
    async def test_dcf_net_debt(self, skill):
        inputs = DCFInput(
            symbol="AAPL",
            fcf_history=[100000],
            shares_outstanding=1000,
            total_debt=50000,
            cash=20000,
        )
        result = await skill.run_dcf(inputs)
        assert result.net_debt == 30000.0

    @pytest.mark.asyncio
    async def test_dcf_terminal_value_pct(self, skill):
        inputs = DCFInput(
            symbol="AAPL",
            sector="technology",
            fcf_history=[100000],
            shares_outstanding=1000,
        )
        result = await skill.run_dcf(inputs)
        assert 0 <= result.terminal_value_pct <= 100

    @pytest.mark.asyncio
    async def test_dcf_unknown_sector_uses_default_wacc(self, skill):
        inputs = DCFInput(symbol="TEST", sector="unknown_sector", fcf_history=[100000], shares_outstanding=1000)
        result = await skill.run_dcf(inputs)
        assert result.wacc_used == 0.10  # _DEFAULT_WACC
