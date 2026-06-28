"""Tests for FRED data provider.

All tests mock HTTP responses to avoid real API calls.
No FRED API key required to run these tests.
"""

from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from quant_nanggroe.data.providers.fred import (
    FREDProvider,
    FREDError,
    FRED_SERIES_MAP,
    _parse_symbol,
)
from quant_nanggroe.types.market import TimeFrame


# ─── Sample FRED API responses ────────────────────────────────────────

SAMPLE_OBSERVATIONS_RESPONSE = {
    "realtime_start": "2024-01-01",
    "realtime_end": "2024-12-31",
    "observation_start": "2023-01-01",
    "observation_end": "2024-12-31",
    "count": 4,
    "observations": [
        {"realtime_start": "2024-01-01", "realtime_end": "2024-12-31", "date": "2023-01-01", "value": "25000.0"},
        {"realtime_start": "2024-01-01", "realtime_end": "2024-12-31", "date": "2023-04-01", "value": "25500.0"},
        {"realtime_start": "2024-01-01", "realtime_end": "2024-12-31", "date": "2023-07-01", "value": "26000.0"},
        {"realtime_start": "2024-01-01", "realtime_end": "2024-12-31", "date": "2023-10-01", "value": "26500.0"},
    ],
}

SAMPLE_OBSERVATIONS_MISSING = {
    "realtime_start": "2024-01-01",
    "realtime_end": "2024-12-31",
    "count": 3,
    "observations": [
        {"realtime_start": "2024-01-01", "realtime_end": "2024-12-31", "date": "2023-01-01", "value": "."},
        {"realtime_start": "2024-01-01", "realtime_end": "2024-12-31", "date": "2023-04-01", "value": "100.0"},
        {"realtime_start": "2024-01-01", "realtime_end": "2024-12-31", "date": "2023-07-01", "value": ""},
    ],
}

SAMPLE_LATEST_OBSERVATION = {
    "realtime_start": "2024-01-01",
    "realtime_end": "2024-12-31",
    "count": 1,
    "observations": [
        {"realtime_start": "2024-01-01", "realtime_end": "2024-12-31", "date": "2024-01-01", "value": "3.7"},
    ],
}

SAMPLE_SERIES_INFO = {
    "realtime_start": "2024-01-01",
    "realtime_end": "2024-12-31",
    "seriess": [
        {
            "id": "GDP",
            "title": "Gross Domestic Product",
            "frequency": "Quarterly",
            "units": "Billions of Dollars",
            "seasonal_adjustment": "Seasonally Adjusted Annual Rate",
        }
    ],
}


def _make_mock_response(data: dict, status_code: int = 200) -> MagicMock:
    """Create a mock httpx response."""
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = data
    response.raise_for_status.return_value = None if status_code == 200 else Exception("HTTP Error")
    return response


# ─── Unit tests ──────────────────────────────────────────────────────────


class TestParseSymbol:
    """Tests for the _parse_symbol helper function."""

    def test_parse_with_prefix(self):
        assert _parse_symbol("FRED:GDP") == "GDP"

    def test_parse_without_prefix(self):
        assert _parse_symbol("GDP") == "GDP"

    def test_parse_complex_series(self):
        assert _parse_symbol("FRED:CPIAUCSL") == "CPIAUCSL"

    def test_parse_unrate(self):
        assert _parse_symbol("FRED:UNRATE") == "UNRATE"


class TestFREDSeriesMap:
    """Tests for the FRED series map constants."""

    def test_map_has_key_series(self):
        assert "FRED:GDP" in FRED_SERIES_MAP
        assert "FRED:CPIAUCSL" in FRED_SERIES_MAP
        assert "FRED:UNRATE" in FRED_SERIES_MAP
        assert "FRED:FEDFUNDS" in FRED_SERIES_MAP

    def test_map_descriptions_are_strings(self):
        for key, desc in FRED_SERIES_MAP.items():
            assert isinstance(desc, str)
            assert len(desc) > 0


class TestFREDProviderInit:
    """Tests for FREDProvider initialization."""

    def test_init_with_api_key(self):
        provider = FREDProvider(api_key="<placeholder>")
        assert provider.name == "fred"
        assert provider.priority == 30
        assert provider._api_key == "test-key"

    def test_init_custom_priority(self):
        provider = FREDProvider(api_key="<placeholder>", priority=50)
        assert provider.priority == 50

    def test_init_default_priority(self):
        provider = FREDProvider(api_key="<placeholder>")
        assert provider.priority == 30

    def test_repr(self):
        provider = FREDProvider(api_key="<placeholder>")
        assert "fred" in repr(provider)


class TestFREDGetApiKey:
    """Tests for API key resolution."""

    def test_get_api_key_from_param(self):
        provider = FREDProvider(api_key="<placeholder>")
        assert provider._get_api_key() == "<placeholder>"

    def test_get_api_key_from_env(self):
        with patch.dict("os.environ", {"QNAI_FRED_API_KEY": "env-key"}):
            provider = FREDProvider()
            assert provider._get_api_key() == "env-key"

    def test_get_api_key_missing_raises(self):
        with patch.dict("os.environ", {}, clear=True):
            # Remove any existing env var
            import os
            os.environ.pop("QNAI_FRED_API_KEY", None)
            provider = FREDProvider()
            with pytest.raises(FREDError, match="FRED API key not configured"):
                provider._get_api_key()


class TestFREDGetOHLCV:
    """Tests for get_ohlcv method with mocked API."""

    @pytest.mark.asyncio
    async def test_get_ohlcv_success(self):
        provider = FREDProvider(api_key="<placeholder>")

        mock_response = _make_mock_response(SAMPLE_OBSERVATIONS_RESPONSE)

        with patch.object(provider, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = SAMPLE_OBSERVATIONS_RESPONSE

            result = await provider.get_ohlcv("FRED:GDP", TimeFrame.D1)

        assert len(result) == 4
        assert result[0].symbol == "FRED:GDP"
        assert result[0].open == 25000.0
        assert result[0].close == 25000.0
        assert result[0].volume == 0.0
        assert provider._request_count > 0

    @pytest.mark.asyncio
    async def test_get_ohlcv_uses_raw_series_id(self):
        provider = FREDProvider(api_key="<placeholder>")

        with patch.object(provider, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = SAMPLE_OBSERVATIONS_RESPONSE

            result = await provider.get_ohlcv("GDP", TimeFrame.D1)

        # Should parse "GDP" directly without "FRED:" prefix
        call_args = mock_req.call_args
        assert call_args[0][0] == "series/observations"
        assert call_args[0][1]["series_id"] == "GDP"

    @pytest.mark.asyncio
    async def test_get_ohlcv_skips_missing_values(self):
        provider = FREDProvider(api_key="<placeholder>")

        with patch.object(provider, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = SAMPLE_OBSERVATIONS_MISSING

            result = await provider.get_ohlcv("FRED:UNRATE", TimeFrame.D1)

        # Only one valid observation (100.0)
        assert len(result) == 1
        assert result[0].close == 100.0

    @pytest.mark.asyncio
    async def test_get_ohlcv_empty_response(self):
        provider = FREDProvider(api_key="<placeholder>")

        with patch.object(provider, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"observations": []}

            result = await provider.get_ohlcv("FRED:NONEXISTENT", TimeFrame.D1)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_ohlcv_api_error(self):
        provider = FREDProvider(api_key="<placeholder>")

        with patch.object(provider, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = FREDError("API error")

            result = await provider.get_ohlcv("FRED:GDP", TimeFrame.D1)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_ohlcv_with_date_range(self):
        provider = FREDProvider(api_key="<placeholder>")

        with patch.object(provider, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = SAMPLE_OBSERVATIONS_RESPONSE

            await provider.get_ohlcv(
                "FRED:GDP",
                start=datetime(2023, 1, 1),
                end=datetime(2023, 12, 31),
            )

        call_params = mock_req.call_args[0][1]
        assert "observation_start" in call_params
        assert "observation_end" in call_params

    @pytest.mark.asyncio
    async def test_get_ohlcv_respects_limit(self):
        provider = FREDProvider(api_key="<placeholder>")

        with patch.object(provider, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = SAMPLE_OBSERVATIONS_RESPONSE

            result = await provider.get_ohlcv("FRED:GDP", TimeFrame.D1, limit=2)

        assert len(result) <= 2


class TestFREDGetTicker:
    """Tests for get_ticker method with mocked API."""

    @pytest.mark.asyncio
    async def test_get_ticker_success(self):
        provider = FREDProvider(api_key="<placeholder>")

        with patch.object(provider, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = SAMPLE_LATEST_OBSERVATION

            ticker = await provider.get_ticker("FRED:UNRATE")

        assert ticker is not None
        assert ticker.symbol == "FRED:UNRATE"
        assert ticker.last_price == 3.7

    @pytest.mark.asyncio
    async def test_get_ticker_missing_value(self):
        provider = FREDProvider(api_key="<placeholder>")

        response = {
            "observations": [
                {"date": "2024-01-01", "value": "."},
            ],
        }

        with patch.object(provider, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = response

            ticker = await provider.get_ticker("FRED:UNRATE")

        assert ticker is None

    @pytest.mark.asyncio
    async def test_get_ticker_empty_observations(self):
        provider = FREDProvider(api_key="<placeholder>")

        with patch.object(provider, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"observations": []}

            ticker = await provider.get_ticker("FRED:UNRATE")

        assert ticker is None

    @pytest.mark.asyncio
    async def test_get_ticker_api_error(self):
        provider = FREDProvider(api_key="<placeholder>")

        with patch.object(provider, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = FREDError("API error")

            ticker = await provider.get_ticker("FRED:UNRATE")

        assert ticker is None


class TestFREDGetOrderbook:
    """Tests for get_orderbook method."""

    @pytest.mark.asyncio
    async def test_get_orderbook_returns_none(self):
        provider = FREDProvider(api_key="<placeholder>")
        result = await provider.get_orderbook("FRED:GDP")
        assert result is None


class TestFREDGetSeriesInfo:
    """Tests for get_series_info method."""

    @pytest.mark.asyncio
    async def test_get_series_info_success(self):
        provider = FREDProvider(api_key="<placeholder>")

        with patch.object(provider, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = SAMPLE_SERIES_INFO

            info = await provider.get_series_info("FRED:GDP")

        assert info["title"] == "Gross Domestic Product"
        assert info["frequency"] == "Quarterly"

    @pytest.mark.asyncio
    async def test_get_series_info_error(self):
        provider = FREDProvider(api_key="<placeholder>")

        with patch.object(provider, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = FREDError("API error")

            info = await provider.get_series_info("FRED:NONEXISTENT")

        assert info == {}


class TestFREDHealthCheck:
    """Tests for health_check method."""

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        provider = FREDProvider(api_key="<placeholder>")

        with patch.object(provider, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = SAMPLE_OBSERVATIONS_RESPONSE

            result = await provider.health_check()

        assert result is True
        assert provider.is_available is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        provider = FREDProvider(api_key="<placeholder>")

        with patch.object(provider, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = FREDError("Connection failed")

            result = await provider.health_check()

        assert result is False
        assert provider.is_available is False


class TestFREDHealthScore:
    """Tests for health score tracking."""

    def test_initial_health_score(self):
        provider = FREDProvider(api_key="<placeholder>")
        assert provider.health_score == 1.0

    def test_health_score_after_errors(self):
        provider = FREDProvider(api_key="<placeholder>")
        provider.mark_error("test error")
        assert provider.health_score < 1.0

    def test_health_score_degrades(self):
        provider = FREDProvider(api_key="<placeholder>")
        provider.mark_success()
        provider.mark_success()
        provider.mark_error("error")
        assert 0.0 < provider.health_score < 1.0

    def test_unavailable_after_many_errors(self):
        provider = FREDProvider(api_key="<placeholder>")
        for _ in range(10):
            provider.mark_error("error")
        assert not provider.is_available


class TestFREDErrorHandling:
    """Tests for error handling edge cases."""

    @pytest.mark.asyncio
    async def test_invalid_value_in_observation(self):
        provider = FREDProvider(api_key="<placeholder>")

        response = {
            "observations": [
                {"date": "2023-01-01", "value": "not_a_number"},
            ],
        }

        with patch.object(provider, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = response

            result = await provider.get_ohlcv("FRED:GDP", TimeFrame.D1)

        # Invalid values are skipped
        assert result == []

    @pytest.mark.asyncio
    async def test_invalid_date_in_observation(self):
        provider = FREDProvider(api_key="<placeholder>")

        response = {
            "observations": [
                {"date": "not-a-date", "value": "100.0"},
            ],
        }

        with patch.object(provider, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = response

            result = await provider.get_ohlcv("FRED:GDP", TimeFrame.D1)

        # Invalid dates are skipped
        assert result == []

    @pytest.mark.asyncio
    async def test_negative_value_in_observation(self):
        """FRED can have negative values (e.g., GDP change)."""
        provider = FREDProvider(api_key="<placeholder>")

        response = {
            "observations": [
                {"date": "2023-01-01", "value": "-2.5"},
            ],
        }

        with patch.object(provider, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = response

            result = await provider.get_ohlcv("FRED:GDP", TimeFrame.D1)

        # Negative values would fail OHLCV's gt=0 validation, so they get skipped
        # This is expected behavior for price-type OHLCV data
        assert len(result) == 0  # OHLCV requires positive prices
