"""Tests for SEC EDGAR data provider.

All tests mock HTTP responses to avoid real API calls.
No SEC EDGAR API key required (it's free, but rate-limited).
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from quant_nanggroe.data.providers.sec_edgar import (
    SECEdgarProvider,
    SECEdgarError,
)
from quant_nanggroe.types.market import TimeFrame


# ─── Sample SEC EDGAR API responses ──────────────────────────────────

SAMPLE_TICKER_MAP = {
    "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
    "1": {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft Corporation"},
    "2": {"cik_str": 1067983, "ticker": "GOOGL", "title": "Alphabet Inc."},
}

SAMPLE_SUBMISSIONS = {
    "cin": "0000320193",
    "entityType": "operating",
    "sic": "3571",
    "sicDescription": "Electronic Computers",
    "name": "Apple Inc.",
    "ticker": "AAPL",
    "filings": {
        "recent": {
            "accessionNumber": ["0000320193-24-000001", "0000320193-24-000002", "0000320193-24-000003"],
            "filingDate": ["2024-01-15", "2024-02-10", "2024-03-05"],
            "form": ["10-K", "10-Q", "4"],
            "primaryDocument": ["aapl-20230930.htm", "aapl-20231231.htm", "primary_doc.xml"],
            "primaryDocDescription": ["Annual Report", "Quarterly Report", "Insider Transaction"],
        }
    },
}

SAMPLE_COMPANY_FACTS = {
    "cik": 320193,
    "entityName": "Apple Inc.",
    "facts": {
        "us-gaap": {
            "Revenues": {
                "label": "Revenues",
                "description": "Amount of revenue recognized from goods/services.",
                "units": {
                    "USD": [
                        {"filed": "2023-11-03", "form": "10-K", "fy": 2023, "fp": "FY", "val": 383285000000, "end": "2023-09-30"},
                        {"filed": "2023-02-03", "form": "10-K", "fy": 2022, "fp": "FY", "val": 394328000000, "end": "2022-09-30"},
                    ]
                }
            },
            "NetIncomeLoss": {
                "label": "Net Income (Loss)",
                "description": "The portion of profit or loss for the period.",
                "units": {
                    "USD": [
                        {"filed": "2023-11-03", "form": "10-K", "fy": 2023, "fp": "FY", "val": 96995000000, "end": "2023-09-30"},
                        {"filed": "2023-02-03", "form": "10-K", "fy": 2022, "fp": "FY", "val": 99803000000, "end": "2022-09-30"},
                    ]
                }
            },
        }
    },
}


# ─── Unit tests ──────────────────────────────────────────────────────────


class TestSECEdgarProviderInit:
    """Tests for SECEdgarProvider initialization."""

    def test_init_defaults(self):
        provider = SECEdgarProvider()
        assert provider.name == "sec_edgar"
        assert provider.priority == 35

    def test_init_with_email(self):
        provider = SECEdgarProvider(user_email="test@example.com")
        assert provider._user_email == "test@example.com"

    def test_init_custom_priority(self):
        provider = SECEdgarProvider(priority=40)
        assert provider.priority == 40

    def test_init_custom_name(self):
        provider = SECEdgarProvider(user_name="TestCorp")
        assert provider._user_name == "TestCorp"

    def test_repr(self):
        provider = SECEdgarProvider()
        assert "sec_edgar" in repr(provider)


class TestSECEdgarUserAgent:
    """Tests for User-Agent header construction."""

    def test_user_agent_with_email(self):
        provider = SECEdgarProvider(user_email="dev@example.com")
        ua = provider._get_user_agent()
        assert "dev@example.com" in ua
        assert "QuantNanggroeAI" in ua

    def test_user_agent_from_env(self):
        with patch.dict("os.environ", {"QNAI_SEC_USER_EMAIL": "env@test.com"}):
            provider = SECEdgarProvider()
            ua = provider._get_user_agent()
            assert "env@test.com" in ua

    def test_user_agent_default_fallback(self):
        with patch.dict("os.environ", {}, clear=True):
            import os
            os.environ.pop("QNAI_SEC_USER_EMAIL", None)
            provider = SECEdgarProvider()
            ua = provider._get_user_agent()
            assert "dev@quant-nanggroe.local" in ua


class TestSECEdgarResolveCIK:
    """Tests for CIK resolution from ticker symbols."""

    @pytest.mark.asyncio
    async def test_resolve_cik_success(self):
        provider = SECEdgarProvider()

        with patch.object(provider, "_rate_limited_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = SAMPLE_TICKER_MAP

            cik = await provider._resolve_cik("AAPL")

        assert cik == "0000320193"

    @pytest.mark.asyncio
    async def test_resolve_cik_case_insensitive(self):
        provider = SECEdgarProvider()

        with patch.object(provider, "_rate_limited_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = SAMPLE_TICKER_MAP

            cik = await provider._resolve_cik("aapl")

        assert cik == "0000320193"

    @pytest.mark.asyncio
    async def test_resolve_cik_not_found(self):
        provider = SECEdgarProvider()

        with patch.object(provider, "_rate_limited_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = SAMPLE_TICKER_MAP

            cik = await provider._resolve_cik("NONEXISTENT")

        assert cik is None

    @pytest.mark.asyncio
    async def test_resolve_cik_caches_result(self):
        provider = SECEdgarProvider()

        with patch.object(provider, "_rate_limited_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = SAMPLE_TICKER_MAP

            cik1 = await provider._resolve_cik("AAPL")
            cik2 = await provider._resolve_cik("AAPL")

        # Second call should use cache
        assert cik1 == cik2
        assert mock_req.call_count == 1  # Only one API call


class TestSECEdgarGetFundamentals:
    """Tests for get_fundamentals method."""

    @pytest.mark.asyncio
    async def test_get_fundamentals_success(self):
        provider = SECEdgarProvider()

        with patch.object(provider, "_resolve_cik", new_callable=AsyncMock) as mock_cik:
            mock_cik.return_value = "0000320193"
            with patch.object(provider, "_rate_limited_request", new_callable=AsyncMock) as mock_req:
                mock_req.return_value = SAMPLE_COMPANY_FACTS

                facts = await provider.get_fundamentals("AAPL")

        assert "us-gaap" in facts
        assert "Revenues" in facts["us-gaap"]

    @pytest.mark.asyncio
    async def test_get_fundamentals_cik_not_found(self):
        provider = SECEdgarProvider()

        with patch.object(provider, "_resolve_cik", new_callable=AsyncMock) as mock_cik:
            mock_cik.return_value = None

            facts = await provider.get_fundamentals("NONEXISTENT")

        assert facts == {}

    @pytest.mark.asyncio
    async def test_get_fundamentals_api_error(self):
        provider = SECEdgarProvider()

        with patch.object(provider, "_resolve_cik", new_callable=AsyncMock) as mock_cik:
            mock_cik.return_value = "0000320193"
            with patch.object(provider, "_rate_limited_request", new_callable=AsyncMock) as mock_req:
                mock_req.side_effect = SECEdgarError("Rate limited")

                facts = await provider.get_fundamentals("AAPL")

        assert facts == {}


class TestSECEdgarGetFilings:
    """Tests for get_filings method."""

    @pytest.mark.asyncio
    async def test_get_filings_all(self):
        provider = SECEdgarProvider()

        with patch.object(provider, "_resolve_cik", new_callable=AsyncMock) as mock_cik:
            mock_cik.return_value = "0000320193"
            with patch.object(provider, "_rate_limited_request", new_callable=AsyncMock) as mock_req:
                mock_req.return_value = SAMPLE_SUBMISSIONS

                filings = await provider.get_filings("AAPL")

        assert len(filings) == 3
        assert filings[0]["form"] == "10-K"

    @pytest.mark.asyncio
    async def test_get_filings_filtered_by_type(self):
        provider = SECEdgarProvider()

        with patch.object(provider, "_resolve_cik", new_callable=AsyncMock) as mock_cik:
            mock_cik.return_value = "0000320193"
            with patch.object(provider, "_rate_limited_request", new_callable=AsyncMock) as mock_req:
                mock_req.return_value = SAMPLE_SUBMISSIONS

                filings = await provider.get_filings("AAPL", filing_type="10-K")

        assert len(filings) == 1
        assert filings[0]["form"] == "10-K"

    @pytest.mark.asyncio
    async def test_get_filings_with_date_range(self):
        provider = SECEdgarProvider()

        with patch.object(provider, "_resolve_cik", new_callable=AsyncMock) as mock_cik:
            mock_cik.return_value = "0000320193"
            with patch.object(provider, "_rate_limited_request", new_callable=AsyncMock) as mock_req:
                mock_req.return_value = SAMPLE_SUBMISSIONS

                filings = await provider.get_filings(
                    "AAPL",
                    start=datetime(2024, 1, 1),
                    end=datetime(2024, 2, 28),
                )

        # Only filings within the date range
        assert len(filings) == 2  # 2024-01-15 and 2024-02-10

    @pytest.mark.asyncio
    async def test_get_filings_with_limit(self):
        provider = SECEdgarProvider()

        with patch.object(provider, "_resolve_cik", new_callable=AsyncMock) as mock_cik:
            mock_cik.return_value = "0000320193"
            with patch.object(provider, "_rate_limited_request", new_callable=AsyncMock) as mock_req:
                mock_req.return_value = SAMPLE_SUBMISSIONS

                filings = await provider.get_filings("AAPL", limit=1)

        assert len(filings) == 1

    @pytest.mark.asyncio
    async def test_get_filings_cik_not_found(self):
        provider = SECEdgarProvider()

        with patch.object(provider, "_resolve_cik", new_callable=AsyncMock) as mock_cik:
            mock_cik.return_value = None

            filings = await provider.get_filings("NONEXISTENT")

        assert filings == []


class TestSECEdgarGetInsiderTransactions:
    """Tests for get_insider_transactions method."""

    @pytest.mark.asyncio
    async def test_get_insider_transactions(self):
        provider = SECEdgarProvider()

        with patch.object(provider, "get_filings", new_callable=AsyncMock) as mock_filings:
            mock_filings.return_value = [
                {"form": "4", "filing_date": "2024-01-15", "accession_number": "001"},
            ]

            transactions = await provider.get_insider_transactions("AAPL")

        assert len(transactions) > 0

    @pytest.mark.asyncio
    async def test_get_insider_transactions_with_limit(self):
        provider = SECEdgarProvider()

        with patch.object(provider, "get_filings", new_callable=AsyncMock) as mock_filings:
            mock_filings.return_value = [
                {"form": "4", "filing_date": "2024-01-15", "accession_number": "001"},
            ]

            transactions = await provider.get_insider_transactions("AAPL", limit=1)

        assert len(transactions) <= 1


class TestSECEdgarGetFinancialStatements:
    """Tests for get_financial_statements method."""

    @pytest.mark.asyncio
    async def test_get_income_statement(self):
        provider = SECEdgarProvider()

        with patch.object(provider, "get_fundamentals", new_callable=AsyncMock) as mock_fund:
            mock_fund.return_value = SAMPLE_COMPANY_FACTS["facts"]

            stmt = await provider.get_financial_statements("AAPL", "income_statement", "annual")

        assert "Revenues" in stmt or "NetIncomeLoss" in stmt

    @pytest.mark.asyncio
    async def test_get_balance_sheet(self):
        provider = SECEdgarProvider()

        with patch.object(provider, "get_fundamentals", new_callable=AsyncMock) as mock_fund:
            mock_fund.return_value = SAMPLE_COMPANY_FACTS["facts"]

            stmt = await provider.get_financial_statements("AAPL", "balance_sheet", "annual")

        # Balance sheet concepts not in sample data, so might be empty
        assert isinstance(stmt, dict)

    @pytest.mark.asyncio
    async def test_get_financial_statements_empty_facts(self):
        provider = SECEdgarProvider()

        with patch.object(provider, "get_fundamentals", new_callable=AsyncMock) as mock_fund:
            mock_fund.return_value = {}

            stmt = await provider.get_financial_statements("AAPL", "income_statement")

        assert stmt == {}


class TestSECEdgarDataProviderInterface:
    """Tests for DataProvider interface methods."""

    @pytest.mark.asyncio
    async def test_get_ohlcv_returns_empty(self):
        provider = SECEdgarProvider()
        result = await provider.get_ohlcv("AAPL")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_ticker_returns_none(self):
        provider = SECEdgarProvider()
        result = await provider.get_ticker("AAPL")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_orderbook_returns_none(self):
        provider = SECEdgarProvider()
        result = await provider.get_orderbook("AAPL")
        assert result is None


class TestSECEdgarHealthCheck:
    """Tests for health_check method."""

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        provider = SECEdgarProvider()

        with patch.object(provider, "_rate_limited_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = SAMPLE_TICKER_MAP

            result = await provider.health_check()

        assert result is True
        assert provider.is_available is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        provider = SECEdgarProvider()

        with patch.object(provider, "_rate_limited_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = SECEdgarError("Connection failed")

            result = await provider.health_check()

        assert result is False
        assert provider.is_available is False


class TestSECEdgarRateLimiting:
    """Tests for rate limiting behavior."""

    @pytest.mark.asyncio
    async def test_rate_limiting_enforced(self):
        provider = SECEdgarProvider()

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_TICKER_MAP
        mock_response.raise_for_status.return_value = None
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False

        provider._client = mock_client

        # Make two rapid requests
        await provider._rate_limited_request("https://test.com/1")
        await provider._rate_limited_request("https://test.com/2")

        # Both should succeed (rate limiting adds delay but doesn't block)
        assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_api_error_handling(self):
        provider = SECEdgarProvider()

        import httpx
        mock_client = MagicMock()
        mock_request = MagicMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.RequestError("Network error", request=mock_request)
        )
        mock_client.is_closed = False

        provider._client = mock_client

        with pytest.raises(SECEdgarError):
            await provider._rate_limited_request("https://test.com")


class TestSECEdgarHealthScore:
    """Tests for health score tracking."""

    def test_initial_health_score(self):
        provider = SECEdgarProvider()
        assert provider.health_score == 1.0

    def test_health_score_after_errors(self):
        provider = SECEdgarProvider()
        provider.mark_error("test error")
        assert provider.health_score < 1.0

    def test_error_tracking(self):
        provider = SECEdgarProvider()
        provider.mark_error("error 1")
        assert provider.last_error == "error 1"
        assert provider._error_count == 1
