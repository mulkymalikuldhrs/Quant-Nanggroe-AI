"""Tests for Token Safety Checker (RugChecker).

All tests use mocked RPC responses — no real network calls.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from quant_nanggroe.exchange.solana.rugcheck import (
    RugChecker,
    TokenSafetyReport,
    SafetyVerdict,
    WEIGHT_MINT_AUTHORITY,
    WEIGHT_FREEZE_AUTHORITY,
    WEIGHT_LP_BURN,
    WEIGHT_HOLDER_CONCENTRATION,
)


# ======================================================================
# Fixtures
# ======================================================================

MOCK_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"


@pytest.fixture
def rug_checker():
    """Create a RugChecker instance for testing."""
    return RugChecker(rpc_url="https://api.mainnet-beta.solana.com", timeout=10)


# ======================================================================
# SafetyVerdict
# ======================================================================

class TestSafetyVerdict:
    """Tests for SafetyVerdict enum."""

    def test_verdict_values(self):
        assert SafetyVerdict.GO == "go"
        assert SafetyVerdict.CAUTION == "caution"
        assert SafetyVerdict.NO_GO == "no_go"

    def test_verdict_is_str(self):
        assert isinstance(SafetyVerdict.GO, str)


# ======================================================================
# TokenSafetyReport
# ======================================================================

class TestTokenSafetyReport:
    """Tests for the TokenSafetyReport model."""

    def test_create_safe_report(self):
        report = TokenSafetyReport(
            mint=MOCK_MINT,
            symbol="USDC",
            name="USD Coin",
            mint_authority_revoked=True,
            freeze_authority_revoked=True,
            lp_burn_pct=100.0,
            top_holder_pct=5.0,
            safety_score=95.0,
            verdict=SafetyVerdict.GO,
        )
        assert report.mint == MOCK_MINT
        assert report.symbol == "USDC"
        assert report.safety_score == 95.0
        assert report.verdict == SafetyVerdict.GO
        assert report.warnings == []

    def test_create_unsafe_report(self):
        report = TokenSafetyReport(
            mint="RugToken...",
            mint_authority_revoked=False,
            freeze_authority_revoked=False,
            lp_burn_pct=10.0,
            top_holder_pct=80.0,
            safety_score=15.0,
            verdict=SafetyVerdict.NO_GO,
            warnings=[
                "Mint authority is NOT revoked",
                "Freeze authority is NOT revoked",
                "Low LP burn: only 10.0% burned",
                "High holder concentration: top holder has 80.0%",
            ],
        )
        assert report.safety_score == 15.0
        assert report.verdict == SafetyVerdict.NO_GO
        assert len(report.warnings) == 4

    def test_default_values(self):
        report = TokenSafetyReport(mint=MOCK_MINT)
        assert report.mint_authority_revoked is True
        assert report.freeze_authority_revoked is True
        assert report.lp_burn_pct == 100.0
        assert report.checked_at is not None


# ======================================================================
# Score Computation
# ======================================================================

class TestScoreComputation:
    """Tests for the safety score computation logic."""

    def test_perfect_score(self):
        """All checks pass → score should be 100."""
        score = RugChecker._compute_score(
            mint_revoked=True,
            freeze_revoked=True,
            lp_burn_pct=100.0,
            top_holder_pct=0.0,
        )
        assert score == 100.0

    def test_all_failed(self):
        """All checks fail → score should be low."""
        score = RugChecker._compute_score(
            mint_revoked=False,
            freeze_revoked=False,
            lp_burn_pct=0.0,
            top_holder_pct=100.0,
        )
        assert score == 0.0

    def test_partial_score(self):
        """Some checks pass → partial score."""
        score = RugChecker._compute_score(
            mint_revoked=True,
            freeze_revoked=False,
            lp_burn_pct=50.0,
            top_holder_pct=20.0,
        )
        # 30 (mint) + 0 (freeze) + 12.5 (50% of 25) + 16 (80% of 20) = 58.5
        expected = WEIGHT_MINT_AUTHORITY + 0 + (50.0 / 100.0) * WEIGHT_LP_BURN + (1.0 - 0.2) * WEIGHT_HOLDER_CONCENTRATION
        assert abs(score - round(expected, 1)) < 0.1

    def test_mint_revoked_only(self):
        """Only mint authority revoked."""
        score = RugChecker._compute_score(
            mint_revoked=True,
            freeze_revoked=False,
            lp_burn_pct=0.0,
            top_holder_pct=100.0,
        )
        assert score == WEIGHT_MINT_AUTHORITY

    def test_score_bounded(self):
        """Score should be between 0 and 100."""
        for mint_r in [True, False]:
            for freeze_r in [True, False]:
                for lp in [0, 25, 50, 75, 100]:
                    for top in [0, 25, 50, 75, 100]:
                        score = RugChecker._compute_score(
                            mint_revoked=mint_r,
                            freeze_revoked=freeze_r,
                            lp_burn_pct=float(lp),
                            top_holder_pct=float(top),
                        )
                        assert 0.0 <= score <= 100.0, f"Score out of bounds: {score}"


# ======================================================================
# Verdict Computation
# ======================================================================

class TestVerdictComputation:
    """Tests for the Go/No-Go verdict computation."""

    def test_go_verdict(self):
        """High score and few warnings → GO."""
        verdict = RugChecker._compute_verdict(90.0, [])
        assert verdict == SafetyVerdict.GO

    def test_go_with_minor_warning(self):
        """High score with one warning → GO."""
        verdict = RugChecker._compute_verdict(85.0, ["Minor warning"])
        assert verdict == SafetyVerdict.GO

    def test_caution_verdict(self):
        """Medium score → CAUTION."""
        verdict = RugChecker._compute_verdict(65.0, ["Some concern"])
        assert verdict == SafetyVerdict.CAUTION

    def test_caution_with_two_warnings(self):
        """Medium score with two warnings → CAUTION."""
        verdict = RugChecker._compute_verdict(55.0, ["Warning 1", "Warning 2"])
        assert verdict == SafetyVerdict.CAUTION

    def test_no_go_verdict(self):
        """Low score → NO_GO."""
        verdict = RugChecker._compute_verdict(30.0, [])
        assert verdict == SafetyVerdict.NO_GO

    def test_no_go_two_critical_warnings(self):
        """Two critical warnings (unrevoked authority) → NO_GO."""
        verdict = RugChecker._compute_verdict(
            80.0,
            ["Mint authority is NOT revoked", "Freeze authority is NOT revoked"],
        )
        assert verdict == SafetyVerdict.NO_GO

    def test_one_critical_warning_not_no_go(self):
        """One critical warning alone should not auto-NO_GO."""
        verdict = RugChecker._compute_verdict(
            80.0,
            ["Mint authority is NOT revoked"],
        )
        # With score 80 and 1 warning, should be CAUTION or GO
        assert verdict in (SafetyVerdict.GO, SafetyVerdict.CAUTION)


# ======================================================================
# Individual Checks (mocked)
# ======================================================================

class TestRugCheckerIndividualChecks:
    """Tests for individual rug check methods."""

    @pytest.mark.asyncio
    async def test_check_mint_authority_revoked(self, rug_checker):
        """Test mint authority check with revoked authority."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {
                "value": {
                    "data": {
                        "parsed": {
                            "info": {
                                "mintAuthority": None,
                            }
                        }
                    }
                }
            }
        }

        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)
        mock_http.is_closed = True

        with patch.object(rug_checker, "_get_http", new_callable=AsyncMock, return_value=mock_http):
            result = await rug_checker._check_mint_authority(MOCK_MINT)
            assert result is True

    @pytest.mark.asyncio
    async def test_check_mint_authority_not_revoked(self, rug_checker):
        """Test mint authority check with active authority."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {
                "value": {
                    "data": {
                        "parsed": {
                            "info": {
                                "mintAuthority": "AuthorityAddress...",
                            }
                        }
                    }
                }
            }
        }

        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)
        mock_http.is_closed = True

        with patch.object(rug_checker, "_get_http", new_callable=AsyncMock, return_value=mock_http):
            result = await rug_checker._check_mint_authority(MOCK_MINT)
            assert result is False

    @pytest.mark.asyncio
    async def test_check_mint_authority_error_returns_false(self, rug_checker):
        """Test mint authority check returns False on error."""
        mock_http = AsyncMock()
        mock_http.post = AsyncMock(side_effect=Exception("Network error"))
        mock_http.is_closed = True

        with patch.object(rug_checker, "_get_http", new_callable=AsyncMock, return_value=mock_http):
            result = await rug_checker._check_mint_authority(MOCK_MINT)
            assert result is False

    @pytest.mark.asyncio
    async def test_check_freeze_authority_revoked(self, rug_checker):
        """Test freeze authority check with revoked authority."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {
                "value": {
                    "data": {
                        "parsed": {
                            "info": {
                                "freezeAuthority": None,
                            }
                        }
                    }
                }
            }
        }

        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)
        mock_http.is_closed = True

        with patch.object(rug_checker, "_get_http", new_callable=AsyncMock, return_value=mock_http):
            result = await rug_checker._check_freeze_authority(MOCK_MINT)
            assert result is True


# ======================================================================
# Full Check (mocked)
# ======================================================================

class TestRugCheckerFullCheck:
    """Tests for the full token safety check."""

    @pytest.mark.asyncio
    async def test_check_token_safe(self, rug_checker):
        """Test full check for a safe token."""
        with patch.object(rug_checker, "_check_mint_authority", new_callable=AsyncMock, return_value=True), \
             patch.object(rug_checker, "_check_freeze_authority", new_callable=AsyncMock, return_value=True), \
             patch.object(rug_checker, "_check_lp_burn", new_callable=AsyncMock, return_value=100.0), \
             patch.object(rug_checker, "_check_holder_concentration", new_callable=AsyncMock, return_value=(5.0, 20.0, 500)), \
             patch.object(rug_checker, "_get_token_metadata", new_callable=AsyncMock, return_value=("USDC", "USD Coin")):

            report = await rug_checker.check_token(MOCK_MINT)

        assert report.mint == MOCK_MINT
        assert report.symbol == "USDC"
        assert report.name == "USD Coin"
        assert report.mint_authority_revoked is True
        assert report.freeze_authority_revoked is True
        assert report.lp_burn_pct == 100.0
        assert report.safety_score > 80
        assert report.verdict == SafetyVerdict.GO
        assert len(report.warnings) == 0

    @pytest.mark.asyncio
    async def test_check_token_risky(self, rug_checker):
        """Test full check for a risky token."""
        with patch.object(rug_checker, "_check_mint_authority", new_callable=AsyncMock, return_value=False), \
             patch.object(rug_checker, "_check_freeze_authority", new_callable=AsyncMock, return_value=False), \
             patch.object(rug_checker, "_check_lp_burn", new_callable=AsyncMock, return_value=10.0), \
             patch.object(rug_checker, "_check_holder_concentration", new_callable=AsyncMock, return_value=(80.0, 95.0, 10)), \
             patch.object(rug_checker, "_get_token_metadata", new_callable=AsyncMock, return_value=(None, None)):

            report = await rug_checker.check_token("RugToken123")

        assert report.mint_authority_revoked is False
        assert report.freeze_authority_revoked is False
        assert report.lp_burn_pct == 10.0
        assert report.top_holder_pct == 80.0
        assert report.safety_score < 30
        assert report.verdict == SafetyVerdict.NO_GO
        assert len(report.warnings) >= 3

    @pytest.mark.asyncio
    async def test_check_token_moderate(self, rug_checker):
        """Test full check for a moderately safe token."""
        with patch.object(rug_checker, "_check_mint_authority", new_callable=AsyncMock, return_value=True), \
             patch.object(rug_checker, "_check_freeze_authority", new_callable=AsyncMock, return_value=False), \
             patch.object(rug_checker, "_check_lp_burn", new_callable=AsyncMock, return_value=60.0), \
             patch.object(rug_checker, "_check_holder_concentration", new_callable=AsyncMock, return_value=(25.0, 55.0, 100)), \
             patch.object(rug_checker, "_get_token_metadata", new_callable=AsyncMock, return_value=("TOKEN", "Test Token")):

            report = await rug_checker.check_token("ModerateToken")

        assert report.mint_authority_revoked is True
        assert report.freeze_authority_revoked is False
        assert report.safety_score < 80
        assert report.verdict in (SafetyVerdict.CAUTION, SafetyVerdict.NO_GO)


# ======================================================================
# Close
# ======================================================================

class TestRugCheckerClose:
    """Tests for RugChecker cleanup."""

    @pytest.mark.asyncio
    async def test_close(self, rug_checker):
        """Test closing the HTTP client."""
        rug_checker._http_client = AsyncMock()
        rug_checker._http_client.is_closed = False
        rug_checker._http_client.aclose = AsyncMock()

        await rug_checker.close()
        assert rug_checker._http_client is None

    def test_repr(self, rug_checker):
        """Test RugChecker repr."""
        result = repr(rug_checker)
        assert "RugChecker" in result
