"""Tests for Jupiter V6 Swap Integration.

All tests use mocked HTTP responses — no real API calls.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from quant_nanggroe.exchange.solana.jupiter import (
    SOL_MINT,
    USDC_MINT,
    JupiterQuote,
    JupiterRoute,
    JupiterSwapResult,
    JupiterV6Client,
)

# ======================================================================
# Fixtures
# ======================================================================

SAMPLE_QUOTE_RESPONSE = {
    "inputMint": SOL_MINT,
    "outputMint": USDC_MINT,
    "inAmount": "1000000000",
    "outAmount": "150000000",
    "otherAmountThreshold": "149250000",
    "priceImpactPct": 0.05,
    "routePlan": [
        {
            "swapInfo": {
                "inputMint": SOL_MINT,
                "outputMint": USDC_MINT,
                "inAmount": "1000000000",
                "outAmount": "150000000",
            },
            "priceImpactPct": 0.05,
            "label": "Raydium",
        }
    ],
}

SAMPLE_SWAP_RESPONSE = {
    "swapTransaction": "AQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
}


@pytest.fixture
def jupiter_client():
    """Create a Jupiter V6 client for testing."""
    return JupiterV6Client(
        rpc_url="https://api.mainnet-beta.solana.com",
        api_url="https://quote-api.jup.ag/v6",
        timeout=10,
    )


# ======================================================================
# JupiterRoute
# ======================================================================

class TestJupiterRoute:
    """Tests for the JupiterRoute model."""

    def test_create_route(self):
        route = JupiterRoute(
            in_mint=SOL_MINT,
            out_mint=USDC_MINT,
            in_amount="1000000000",
            out_amount="150000000",
            price_impact_pct=0.05,
            label="Raydium",
        )
        assert route.in_mint == SOL_MINT
        assert route.out_mint == USDC_MINT
        assert route.price_impact_pct == 0.05
        assert route.label == "Raydium"

    def test_default_values(self):
        route = JupiterRoute()
        assert route.in_amount == "0"
        assert route.out_amount == "0"
        assert route.price_impact_pct == 0.0


# ======================================================================
# JupiterQuote
# ======================================================================

class TestJupiterQuote:
    """Tests for the JupiterQuote model."""

    def test_create_quote(self):
        quote = JupiterQuote(
            input_mint=SOL_MINT,
            output_mint=USDC_MINT,
            in_amount="1000000000",
            out_amount="150000000",
            other_amount_threshold="149250000",
            price_impact_pct=0.05,
            slippage_bps=50,
        )
        assert quote.input_mint == SOL_MINT
        assert quote.output_mint == USDC_MINT
        assert quote.in_amount == "1000000000"
        assert quote.out_amount == "150000000"
        assert quote.price_impact_pct == 0.05
        assert quote.slippage_bps == 50

    def test_default_values(self):
        quote = JupiterQuote(
            input_mint=SOL_MINT,
            output_mint=USDC_MINT,
        )
        assert quote.in_amount == "0"
        assert quote.out_amount == "0"
        assert quote.route_plan == []
        assert quote.created_at is not None

    def test_raw_response_stored(self):
        quote = JupiterQuote(
            input_mint=SOL_MINT,
            output_mint=USDC_MINT,
        )
        quote._raw_response = {"test": True}
        assert quote._raw_response == {"test": True}


# ======================================================================
# JupiterSwapResult
# ======================================================================

class TestJupiterSwapResult:
    """Tests for the JupiterSwapResult model."""

    def test_create_swap_result(self):
        result = JupiterSwapResult(
            signature="5UfDuX7WXYZ123...",
            input_mint=SOL_MINT,
            output_mint=USDC_MINT,
            in_amount="1000000000",
            out_amount="150000000",
            status="confirmed",
            slot=123456789,
            fee=5000,
        )
        assert result.signature == "5UfDuX7WXYZ123..."
        assert result.status == "confirmed"
        assert result.slot == 123456789
        assert result.fee == 5000

    def test_default_status(self):
        result = JupiterSwapResult(
            signature="sig",
            input_mint=SOL_MINT,
            output_mint=USDC_MINT,
        )
        assert result.status == "pending"


# ======================================================================
# JupiterV6Client — Quote (mocked)
# ======================================================================

class TestJupiterV6ClientQuote:
    """Tests for the get_quote method with mocked HTTP."""

    @pytest.mark.asyncio
    async def test_get_quote_success(self, jupiter_client):
        """Test successful quote retrieval."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_QUOTE_RESPONSE

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        mock_http.is_closed = True

        with patch.object(jupiter_client, "_get_http", new_callable=AsyncMock, return_value=mock_http):
            quote = await jupiter_client.get_quote(
                input_mint=SOL_MINT,
                output_mint=USDC_MINT,
                amount=1_000_000_000,
                slippage_bps=50,
            )

        assert quote.input_mint == SOL_MINT
        assert quote.output_mint == USDC_MINT
        assert quote.in_amount == "1000000000"
        assert quote.out_amount == "150000000"
        assert quote.price_impact_pct == 0.05
        assert len(quote.route_plan) == 1
        assert quote.route_plan[0].label == "Raydium"
        assert quote._raw_response is not None

    @pytest.mark.asyncio
    async def test_get_quote_api_error(self, jupiter_client):
        """Test quote retrieval with API error."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Invalid mint address"

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        mock_http.is_closed = True

        with patch.object(jupiter_client, "_get_http", new_callable=AsyncMock, return_value=mock_http):
            with pytest.raises(ValueError, match="Jupiter quote API error"):
                await jupiter_client.get_quote(
                    input_mint="invalid",
                    output_mint=USDC_MINT,
                    amount=1000,
                )

    @pytest.mark.asyncio
    async def test_get_quote_with_direct_routes(self, jupiter_client):
        """Test quote with only_direct_routes=True."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_QUOTE_RESPONSE

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        mock_http.is_closed = True

        with patch.object(jupiter_client, "_get_http", new_callable=AsyncMock, return_value=mock_http):
            quote = await jupiter_client.get_quote(
                input_mint=SOL_MINT,
                output_mint=USDC_MINT,
                amount=1_000_000_000,
                slippage_bps=50,
                only_direct_routes=True,
            )
        assert quote.input_mint == SOL_MINT


# ======================================================================
# JupiterV6Client — Execute Swap (mocked)
# ======================================================================

class TestJupiterV6ClientSwap:
    """Tests for swap execution with mocked HTTP and RPC."""

    @pytest.mark.asyncio
    async def test_execute_swap_no_raw_response_raises(self, jupiter_client):
        """Execute swap should raise if quote has no raw response."""
        quote = JupiterQuote(
            input_mint=SOL_MINT,
            output_mint=USDC_MINT,
        )
        with pytest.raises(ValueError, match="no raw response"):
            await jupiter_client.execute_swap(quote=quote, wallet=MagicMock())

    def test_repr(self, jupiter_client):
        """Test client repr."""
        result = repr(jupiter_client)
        assert "JupiterV6Client" in result


# ======================================================================
# Price Impact Estimation
# ======================================================================

class TestPriceImpactEstimation:
    """Tests for the price impact estimation method."""

    def test_zero_impact(self):
        """No price impact when effective price equals reference."""
        impact = JupiterV6Client.estimate_price_impact(
            in_amount=1_000_000_000,
            out_amount=150_000_000,
            reference_price=150.0,
            input_decimals=9,
            output_decimals=6,
        )
        assert impact == 0.0

    def test_positive_impact(self):
        """Positive price impact when effective price is lower."""
        # Reference: 150 USDC per SOL
        # Effective: 1 SOL = 120 USDC (less than reference)
        impact = JupiterV6Client.estimate_price_impact(
            in_amount=1_000_000_000,
            out_amount=120_000_000,
            reference_price=150.0,
            input_decimals=9,
            output_decimals=6,
        )
        assert impact > 0
        assert impact < 100

    def test_zero_input(self):
        """Zero input should return zero impact."""
        impact = JupiterV6Client.estimate_price_impact(
            in_amount=0,
            out_amount=100,
            reference_price=150.0,
        )
        assert impact == 0.0

    def test_zero_reference_price(self):
        """Zero reference price should return zero impact."""
        impact = JupiterV6Client.estimate_price_impact(
            in_amount=1_000_000_000,
            out_amount=150_000_000,
            reference_price=0.0,
        )
        assert impact == 0.0

    def test_large_impact(self):
        """Large price impact (50%+) should be capped."""
        impact = JupiterV6Client.estimate_price_impact(
            in_amount=1_000_000_000,
            out_amount=50_000_000,
            reference_price=150.0,
            input_decimals=9,
            output_decimals=6,
        )
        assert impact > 50.0


# ======================================================================
# Route Comparison
# ======================================================================

class TestJupiterV6ClientRoutes:
    """Tests for route comparison functionality."""

    @pytest.mark.asyncio
    async def test_compare_routes(self, jupiter_client):
        """Test route comparison (currently returns single quote)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_QUOTE_RESPONSE

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        mock_http.is_closed = True

        with patch.object(jupiter_client, "_get_http", new_callable=AsyncMock, return_value=mock_http):
            routes = await jupiter_client.compare_routes(
                input_mint=SOL_MINT,
                output_mint=USDC_MINT,
                amount=1_000_000_000,
            )
        assert len(routes) == 1
        assert isinstance(routes[0], JupiterQuote)


# ======================================================================
# Close
# ======================================================================

class TestJupiterV6ClientClose:
    """Tests for client cleanup."""

    @pytest.mark.asyncio
    async def test_close(self, jupiter_client):
        """Test closing the HTTP client."""
        jupiter_client._http_client = AsyncMock()
        jupiter_client._http_client.is_closed = False
        jupiter_client._http_client.aclose = AsyncMock()

        await jupiter_client.close()
        assert jupiter_client._http_client is None

    @pytest.mark.asyncio
    async def test_close_no_client(self, jupiter_client):
        """Test closing when no client exists."""
        jupiter_client._http_client = None
        await jupiter_client.close()  # Should not raise
