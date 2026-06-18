"""Tests for TwelveData market data provider.

All tests mock HTTP responses to avoid real API calls.
No TwelveData API key required to run these tests.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from quant_nanggroe.data.providers.twelvedata import (
    TwelveDataProvider,
    TwelveDataError,
    _TIMEFRAME_MAP,
)
from quant_nanggroe.types.market import TimeFrame


# ─── Sample TwelveData API responses ────────────────────────────────

SAMPLE_TIME_SERIES = {
    "meta": {
        "symbol": "AAPL",
        "interval": "1day",
        "exchange_timezone": "America/New_York",
    },
    "values": [
        {"datetime": "2024-01-05", "open": "185.0", "high": "186.5", "low": "184.2", "close": "185.5", "volume": "50000000"},
        {"datetime": "2024-01-04", "open": "183.0", "high": "184.5", "low": "182.5", "close": "184.0", "volume": "45000000"},
        {"datetime": "2024-01-03", "open": "181.0", "high": "183.0", "low": "180.5", "close": "182.5", "volume": "48000000"},
        {"datetime": "2024-01-02", "open": "180.0", "high": "182.0", "low": "179.5", "close": "181.0", "volume": "55000000"},
    ],
    "status": "ok",
}

SAMPLE_QUOTE = {
    "symbol": "AAPL",
    "close": "185.5",
    "open": "184.0",
    "high": "186.5",
    "low": "183.0",
    "volume": "50000000",
    "bid": "185.4",
    "ask": "185.6",
    "percent_change": "1.25",
    "status": "ok",
}

SAMPLE_FOREX_RATE = {
    "meta": {"symbol": "EUR/USD", "interval": "1min"},
    "values": [
        {"datetime": "2024-01-05 10:00:00", "open": "1.0950", "high": "1.0955", "low": "1.0948", "close": "1.0952", "volume": "0"},
    ],
    "status": "ok",
}

SAMPLE_ERROR_RESPONSE = {
    "status": "error",
    "message": "Invalid API key.",
}

SAMPLE_EMPTY_VALUES = {
    "meta": {"symbol": "NONEXISTENT", "interval": "1day"},
    "values": [],
    "status": "ok",
}


# ─── Unit tests ──────────────────────────────────────────────────────────


class TestTimeframeMap:
    """Tests for the timeframe mapping."""

    def test_all_timeframes_mapped(self):
        for tf in TimeFrame:
            assert tf in _TIMEFRAME_MAP

    def test_timeframe_values(self):
        assert _TIMEFRAME_MAP[TimeFrame.D1] == "1day"
        assert _TIMEFRAME_MAP[TimeFrame.H1] == "1h"
        assert _TIMEFRAME_MAP[TimeFrame.M1] == "1min"
        assert _TIMEFRAME_MAP[TimeFrame.W1] == "1week"
        assert _TIMEFRAME_MAP[TimeFrame.MO1] == "1month"


class TestTwelveDataProviderInit:
    """Tests for TwelveDataProvider initialization."""

    def test_init_with_api_key(self):
        provider = TwelveDataProvider(api_key="test-key")
        assert provider.name == "twelvedata"
        assert provider.priority == 15
        assert provider._api_key == "test-key"

    def test_init_custom_priority(self):
        provider = TwelveDataProvider(api_key="test-key", priority=25)
        assert provider.priority == 25

    def test_init_default_priority(self):
        provider = TwelveDataProvider(api_key="test-key")
        assert provider.priority == 15

    def test_repr(self):
        provider = TwelveDataProvider(api_key="test-key")
        assert "twelvedata" in repr(provider)


class TestTwelveDataGetApiKey:
    """Tests for API key resolution."""

    def test_get_api_key_from_param(self):
        provider = TwelveDataProvider(api_key="my-key")
        assert provider._get_api_key() == "my-key"

    def test_get_api_key_from_env(self):
        with patch.dict("os.environ", {"QNAI_TWELVEDATA_API_KEY": "env-key"}):
            provider = TwelveDataProvider()
            assert provider._get_api_key() == "env-key"

    def test_get_api_key_missing_raises(self):
        with patch.dict("os.environ", {}, clear=True):
            import os
            os.environ.pop("QNAI_TWELVEDATA_API_KEY", None)
            provider = TwelveDataProvider()
            with pytest.raises(TwelveDataError, match="TwelveData API key not configured"):
                provider._get_api_key()


class TestTwelveDataGetOHLCV:
    """Tests for get_ohlcv method with mocked API."""

    @pytest.mark.asyncio
    async def test_get_ohlcv_success(self):
        provider = TwelveDataProvider(api_key="test-key")

        with patch.object(provider, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = SAMPLE_TIME_SERIES

            result = await provider.get_ohlcv("AAPL", TimeFrame.D1)

        assert len(result) == 4
        # Should be sorted ascending by timestamp after reverse
        assert result[0].close == 181.0  # 2024-01-02
        assert result[-1].close == 185.5  # 2024-01-05

    @pytest.mark.asyncio
    async def test_get_ohlcv_symbol_preserved(self):
        provider = TwelveDataProvider(api_key="test-key")

        with patch.object(provider, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = SAMPLE_TIME_SERIES

            result = await provider.get_ohlcv("AAPL", TimeFrame.D1)

        for candle in result:
            assert candle.symbol == "AAPL"

    @pytest.mark.asyncio
    async def test_get_ohlcv_ohlcv_values(self):
        provider = TwelveDataProvider(api_key="test-key")

        with patch.object(provider, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = SAMPLE_TIME_SERIES

            result = await provider.get_ohlcv("AAPL", TimeFrame.D1)

        # Check last candle values
        last = result[-1]
        assert last.open == 185.0
        assert last.high == 186.5
        assert last.low == 184.2
        assert last.close == 185.5
        assert last.volume == 50000000.0

    @pytest.mark.asyncio
    async def test_get_ohlcv_empty_response(self):
        provider = TwelveDataProvider(api_key="test-key")

        with patch.object(provider, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = SAMPLE_EMPTY_VALUES

            result = await provider.get_ohlcv("NONEXISTENT", TimeFrame.D1)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_ohlcv_api_error(self):
        provider = TwelveDataProvider(api_key="test-key")

        with patch.object(provider, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = TwelveDataError("API error")

            result = await provider.get_ohlcv("AAPL", TimeFrame.D1)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_ohlcv_timeframe_mapping(self):
        provider = TwelveDataProvider(api_key="test-key")

        with patch.object(provider, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = SAMPLE_TIME_SERIES

            await provider.get_ohlcv("AAPL", TimeFrame.H1)

        call_params = mock_req.call_args[0][1]
        assert call_params["interval"] == "1h"

    @pytest.mark.asyncio
    async def test_get_ohlcv_with_date_range(self):
        provider = TwelveDataProvider(api_key="test-key")

        with patch.object(provider, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = SAMPLE_TIME_SERIES

            await provider.get_ohlcv(
                "AAPL",
                start=datetime(2024, 1, 1),
                end=datetime(2024, 1, 31),
            )

        call_params = mock_req.call_args[0][1]
        assert "start_date" in call_params
        assert "end_date" in call_params

    @pytest.mark.asyncio
    async def test_get_ohlcv_respects_limit(self):
        provider = TwelveDataProvider(api_key="test-key")

        with patch.object(provider, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = SAMPLE_TIME_SERIES

            result = await provider.get_ohlcv("AAPL", TimeFrame.D1, limit=2)

        assert len(result) <= 2

    @pytest.mark.asyncio
    async def test_get_ohlcv_zero_price_skipped(self):
        provider = TwelveDataProvider(api_key="test-key")

        data = {
            "values": [
                {"datetime": "2024-01-05", "open": "0", "high": "0", "low": "0", "close": "0", "volume": "1000"},
            ],
        }

        with patch.object(provider, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = data

            result = await provider.get_ohlcv("AAPL", TimeFrame.D1)

        assert result == []  # Zero prices should be skipped


class TestTwelveDataGetTicker:
    """Tests for get_ticker method with mocked API."""

    @pytest.mark.asyncio
    async def test_get_ticker_success(self):
        provider = TwelveDataProvider(api_key="test-key")

        with patch.object(provider, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = SAMPLE_QUOTE

            ticker = await provider.get_ticker("AAPL")

        assert ticker is not None
        assert ticker.symbol == "AAPL"
        assert ticker.last_price == 185.5
        assert ticker.bid == 185.4
        assert ticker.ask == 185.6
        assert ticker.high_24h == 186.5
        assert ticker.low_24h == 183.0

    @pytest.mark.asyncio
    async def test_get_ticker_no_close(self):
        provider = TwelveDataProvider(api_key="test-key")

        with patch.object(provider, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"symbol": "AAPL", "status": "ok"}

            ticker = await provider.get_ticker("AAPL")

        assert ticker is None

    @pytest.mark.asyncio
    async def test_get_ticker_zero_close(self):
        provider = TwelveDataProvider(api_key="test-key")

        with patch.object(provider, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"close": "0", "status": "ok"}

            ticker = await provider.get_ticker("AAPL")

        assert ticker is None

    @pytest.mark.asyncio
    async def test_get_ticker_api_error(self):
        provider = TwelveDataProvider(api_key="test-key")

        with patch.object(provider, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = TwelveDataError("API error")

            ticker = await provider.get_ticker("AAPL")

        assert ticker is None

    @pytest.mark.asyncio
    async def test_get_ticker_change_pct(self):
        provider = TwelveDataProvider(api_key="test-key")

        with patch.object(provider, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = SAMPLE_QUOTE

            ticker = await provider.get_ticker("AAPL")

        assert ticker is not None
        assert ticker.change_pct_24h == 1.25


class TestTwelveDataGetForexRate:
    """Tests for get_forex_rate method with mocked API."""

    @pytest.mark.asyncio
    async def test_get_forex_rate_success(self):
        provider = TwelveDataProvider(api_key="test-key")

        with patch.object(provider, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = SAMPLE_FOREX_RATE

            rate = await provider.get_forex_rate("EUR/USD")

        assert rate is not None
        assert rate["pair"] == "EUR/USD"
        assert rate["rate"] == 1.0952

    @pytest.mark.asyncio
    async def test_get_forex_rate_empty_values(self):
        provider = TwelveDataProvider(api_key="test-key")

        with patch.object(provider, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"values": [], "status": "ok"}

            rate = await provider.get_forex_rate("EUR/USD")

        assert rate is None

    @pytest.mark.asyncio
    async def test_get_forex_rate_api_error(self):
        provider = TwelveDataProvider(api_key="test-key")

        with patch.object(provider, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = TwelveDataError("API error")

            rate = await provider.get_forex_rate("EUR/USD")

        assert rate is None


class TestTwelveDataGetOrderbook:
    """Tests for get_orderbook method."""

    @pytest.mark.asyncio
    async def test_get_orderbook_returns_none(self):
        provider = TwelveDataProvider(api_key="test-key")
        result = await provider.get_orderbook("AAPL")
        assert result is None


class TestTwelveDataHealthCheck:
    """Tests for health_check method."""

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        provider = TwelveDataProvider(api_key="test-key")

        with patch.object(provider, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = SAMPLE_TIME_SERIES

            result = await provider.health_check()

        assert result is True
        assert provider.is_available is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        provider = TwelveDataProvider(api_key="test-key")

        with patch.object(provider, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = TwelveDataError("Connection failed")

            result = await provider.health_check()

        assert result is False
        assert provider.is_available is False


class TestTwelveDataErrorHandling:
    """Tests for API error response handling."""

    @pytest.mark.asyncio
    async def test_error_status_in_response(self):
        provider = TwelveDataProvider(api_key="test-key")

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_ERROR_RESPONSE
        mock_response.raise_for_status.return_value = None
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False

        provider._client = mock_client

        with pytest.raises(TwelveDataError, match="Invalid API key"):
            await provider._request("time_series", {"symbol": "AAPL"})

    @pytest.mark.asyncio
    async def test_http_status_error(self):
        provider = TwelveDataProvider(api_key="test-key")

        import httpx
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Rate limited", request=MagicMock(), response=mock_response
        )
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False

        provider._client = mock_client

        with pytest.raises(TwelveDataError):
            await provider._request("time_series", {"symbol": "AAPL"})


class TestTwelveDataHealthScore:
    """Tests for health score tracking."""

    def test_initial_health_score(self):
        provider = TwelveDataProvider(api_key="test-key")
        assert provider.health_score == 1.0

    def test_health_score_after_errors(self):
        provider = TwelveDataProvider(api_key="test-key")
        provider.mark_error("test error")
        assert provider.health_score < 1.0

    def test_health_score_mixed(self):
        provider = TwelveDataProvider(api_key="test-key")
        provider.mark_success()
        provider.mark_success()
        provider.mark_error("error")
        assert 0.0 < provider.health_score < 1.0

    def test_unavailable_after_many_errors(self):
        provider = TwelveDataProvider(api_key="test-key")
        for _ in range(10):
            provider.mark_error("error")
        assert not provider.is_available
