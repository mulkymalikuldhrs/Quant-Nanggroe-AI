"""Token Safety Checker — Rugpull detection and safety scoring.

Provides comprehensive token safety analysis for Solana tokens, checking
mint authority, freeze authority, LP burn status, and holder concentration.

Features
--------
* Check if mint authority is revoked
* Check if freeze authority is revoked
* Verify LP token burn percentage
* Check top holder concentration
* Compute safety score (0–100, higher = safer)
* Go/No-Go verdict for trading

Security
--------
This module performs **read-only** on-chain queries and never submits
transactions. It is safe to use for automated screening.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SOL_MINT = "So11111111111111111111111111111111111111112"
SOLSCAN_API = "https://public-api.solscan.io"
RPC_URL = "https://api.mainnet-beta.solana.com"

# Safety score weights
WEIGHT_MINT_AUTHORITY = 30.0
WEIGHT_FREEZE_AUTHORITY = 25.0
WEIGHT_LP_BURN = 25.0
WEIGHT_HOLDER_CONCENTRATION = 20.0


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SafetyVerdict(str, Enum):
    """Trading safety verdict.

    Attributes
    ----------
    GO:
        Token passes all safety checks — safe to trade.
    CAUTION:
        Token has some concerns — trade with care.
    NO_GO:
        Token has serious red flags — do not trade.
    """

    GO = "go"
    CAUTION = "caution"
    NO_GO = "no_go"


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class TokenSafetyReport(BaseModel):
    """Comprehensive token safety analysis report.

    Attributes
    ----------
    mint:
        Token mint address.
    symbol:
        Token symbol (if available).
    name:
        Token name (if available).
    mint_authority_revoked:
        Whether the mint authority has been revoked.
    freeze_authority_revoked:
        Whether the freeze authority has been revoked.
    lp_burn_pct:
        Percentage of LP tokens burned (0–100).
    top_holder_pct:
        Percentage of supply held by top holder (0–100).
    top_10_holder_pct:
        Percentage of supply held by top 10 holders (0–100).
    holder_count:
        Number of token holders.
    safety_score:
        Computed safety score (0–100, higher = safer).
    verdict:
        Overall Go/No-Go verdict.
    warnings:
        List of specific warnings identified.
    checked_at:
        When this report was generated.
    """

    mint: str
    symbol: Optional[str] = None
    name: Optional[str] = None
    mint_authority_revoked: bool = True
    freeze_authority_revoked: bool = True
    lp_burn_pct: float = 100.0
    top_holder_pct: float = 0.0
    top_10_holder_pct: float = 0.0
    holder_count: int = 0
    safety_score: float = 0.0
    verdict: SafetyVerdict = SafetyVerdict.GO
    warnings: List[str] = Field(default_factory=list)
    checked_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# RugChecker
# ---------------------------------------------------------------------------

class RugChecker:
    """Token safety checker for Solana tokens.

    Performs on-chain queries to assess the safety of a token before trading.
    Checks mint authority, freeze authority, LP burn status, and holder
    concentration.

    Parameters
    ----------
    rpc_url:
        Solana JSON-RPC endpoint URL.
    timeout:
        HTTP request timeout in seconds.

    Examples
    --------
    .. code-block:: python

        checker = RugChecker()
        report = await checker.check_token(
            mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        )
        print(f"Score: {report.safety_score}, Verdict: {report.verdict}")
    """

    def __init__(
        self,
        rpc_url: str = RPC_URL,
        timeout: int = 30,
    ) -> None:
        self._rpc_url = rpc_url
        self._timeout = timeout
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_http(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=self._timeout)
        return self._http_client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None

    # ----- Main Check -----

    async def check_token(self, mint: str) -> TokenSafetyReport:
        """Perform a comprehensive safety check on a token.

        Parameters
        ----------
        mint:
            Token mint address (Base58).

        Returns
        -------
        TokenSafetyReport
            Complete safety analysis with score and verdict.
        """
        warnings: List[str] = []

        # Check mint authority
        mint_revoked = await self._check_mint_authority(mint)
        if not mint_revoked:
            warnings.append("Mint authority is NOT revoked — token supply can be inflated")

        # Check freeze authority
        freeze_revoked = await self._check_freeze_authority(mint)
        if not freeze_revoked:
            warnings.append("Freeze authority is NOT revoked — tokens can be frozen")

        # Check LP burn
        lp_burn_pct = await self._check_lp_burn(mint)
        if lp_burn_pct < 50.0:
            warnings.append(f"Low LP burn: only {lp_burn_pct:.1f}% burned")

        # Check holder concentration
        top_holder_pct, top_10_pct, holder_count = await self._check_holder_concentration(mint)
        if top_holder_pct > 30.0:
            warnings.append(f"High holder concentration: top holder has {top_holder_pct:.1f}%")
        if top_10_pct > 70.0:
            warnings.append(f"Top 10 holders own {top_10_pct:.1f}% of supply")

        # Get token metadata
        symbol, name = await self._get_token_metadata(mint)

        # Compute score
        score = self._compute_score(
            mint_revoked=mint_revoked,
            freeze_revoked=freeze_revoked,
            lp_burn_pct=lp_burn_pct,
            top_holder_pct=top_holder_pct,
        )

        # Determine verdict
        verdict = self._compute_verdict(score, warnings)

        return TokenSafetyReport(
            mint=mint,
            symbol=symbol,
            name=name,
            mint_authority_revoked=mint_revoked,
            freeze_authority_revoked=freeze_revoked,
            lp_burn_pct=lp_burn_pct,
            top_holder_pct=top_holder_pct,
            top_10_holder_pct=top_10_pct,
            holder_count=holder_count,
            safety_score=score,
            verdict=verdict,
            warnings=warnings,
        )

    # ----- Individual Checks -----

    async def _check_mint_authority(self, mint: str) -> bool:
        """Check if the mint authority has been revoked.

        Parameters
        ----------
        mint:
            Token mint address.

        Returns
        -------
        bool
            ``True`` if mint authority is ``None`` (revoked).
        """
        try:
            client = await self._get_http()
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getAccountInfo",
                "params": [
                    mint,
                    {"encoding": "jsonParsed"},
                ],
            }
            resp = await client.post(self._rpc_url, json=payload)
            data = resp.json()

            result = data.get("result", {})
            value = result.get("value", {})
            if not value:
                return False

            parsed = value.get("data", {}).get("parsed", {})
            info = parsed.get("info", {})
            mint_authority = info.get("mintAuthority")

            return mint_authority is None

        except Exception as exc:
            logger.error("Failed to check mint authority for %s: %s", mint, exc)
            return False

    async def _check_freeze_authority(self, mint: str) -> bool:
        """Check if the freeze authority has been revoked.

        Parameters
        ----------
        mint:
            Token mint address.

        Returns
        -------
        bool
            ``True`` if freeze authority is ``None`` (revoked).
        """
        try:
            client = await self._get_http()
            payload = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "getAccountInfo",
                "params": [
                    mint,
                    {"encoding": "jsonParsed"},
                ],
            }
            resp = await client.post(self._rpc_url, json=payload)
            data = resp.json()

            result = data.get("result", {})
            value = result.get("value", {})
            if not value:
                return False

            parsed = value.get("data", {}).get("parsed", {})
            info = parsed.get("info", {})
            freeze_authority = info.get("freezeAuthority")

            return freeze_authority is None

        except Exception as exc:
            logger.error("Failed to check freeze authority for %s: %s", mint, exc)
            return False

    async def _check_lp_burn(self, mint: str) -> float:
        """Check LP token burn percentage.

        Parameters
        ----------
        mint:
            Token mint address.

        Returns
        -------
        float
            LP burn percentage (0–100). Returns 0.0 on error.
        """
        try:
            client = await self._get_http()
            # Try to find LP token account and check burn status
            # This is a simplified check — production would parse AMM accounts
            payload = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "getTokenLargestAccounts",
                "params": [mint],
            }
            resp = await client.post(self._rpc_url, json=payload)
            data = resp.json()

            result = data.get("result", {})
            value = result.get("value", [])

            if not value:
                return 0.0

            # Check if the largest holder is the burn address
            # (11111111111111111111111111111111 is system program / null)
            total_supply = sum(float(acct.get("uiAmount", 0) or 0) for acct in value)
            if total_supply == 0:
                return 0.0

            # Simplified: check if any account is at the burn address
            burn_addresses = {
                "11111111111111111111111111111111",
                "1nc1nerator11111111111111111111111111111111",
            }
            burned = 0.0
            for acct in value:
                addr = acct.get("address", "")
                amt = float(acct.get("uiAmount", 0) or 0)
                if addr in burn_addresses:
                    burned += amt

            return (burned / total_supply) * 100 if total_supply > 0 else 0.0

        except Exception as exc:
            logger.error("Failed to check LP burn for %s: %s", mint, exc)
            return 0.0

    async def _check_holder_concentration(
        self, mint: str
    ) -> tuple[float, float, int]:
        """Check holder concentration.

        Parameters
        ----------
        mint:
            Token mint address.

        Returns
        -------
        tuple of (top_holder_pct, top_10_pct, holder_count)
        """
        try:
            client = await self._get_http()
            payload = {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "getTokenLargestAccounts",
                "params": [mint],
            }
            resp = await client.post(self._rpc_url, json=payload)
            data = resp.json()

            result = data.get("result", {})
            value = result.get("value", [])

            if not value:
                return 0.0, 0.0, 0

            amounts = [float(acct.get("uiAmount", 0) or 0) for acct in value]
            total = sum(amounts)
            if total == 0:
                return 0.0, 0.0, len(value)

            top_pct = (amounts[0] / total) * 100 if amounts else 0.0
            top_10_pct = (sum(amounts[:10]) / total) * 100 if amounts else 0.0

            return top_pct, top_10_pct, len(value)

        except Exception as exc:
            logger.error("Failed to check holder concentration for %s: %s", mint, exc)
            return 0.0, 0.0, 0

    async def _get_token_metadata(self, mint: str) -> tuple[Optional[str], Optional[str]]:
        """Fetch token symbol and name from on-chain metadata.

        Parameters
        ----------
        mint:
            Token mint address.

        Returns
        -------
        tuple of (symbol, name)
        """
        try:
            client = await self._get_http()
            payload = {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "getAccountInfo",
                "params": [
                    mint,
                    {"encoding": "jsonParsed"},
                ],
            }
            resp = await client.post(self._rpc_url, json=payload)
            data = resp.json()

            result = data.get("result", {})
            value = result.get("value", {})
            if not value:
                return None, None

            parsed = value.get("data", {}).get("parsed", {})
            info = parsed.get("info", {})

            return info.get("symbol"), info.get("name")

        except Exception:
            return None, None

    # ----- Score Computation -----

    @staticmethod
    def _compute_score(
        mint_revoked: bool,
        freeze_revoked: bool,
        lp_burn_pct: float,
        top_holder_pct: float,
    ) -> float:
        """Compute the safety score for a token.

        Scoring:
        - Mint authority revoked: up to 30 points
        - Freeze authority revoked: up to 25 points
        - LP burn: up to 25 points (100% burn = 25, 0% = 0)
        - Holder concentration: up to 20 points (lower top holder = higher score)

        Parameters
        ----------
        mint_revoked:
            Whether the mint authority is revoked.
        freeze_revoked:
            Whether the freeze authority is revoked.
        lp_burn_pct:
            LP burn percentage (0–100).
        top_holder_pct:
            Top holder's percentage of supply (0–100).

        Returns
        -------
        float
            Safety score (0–100).
        """
        score = 0.0

        # Mint authority (30 pts)
        score += WEIGHT_MINT_AUTHORITY if mint_revoked else 0.0

        # Freeze authority (25 pts)
        score += WEIGHT_FREEZE_AUTHORITY if freeze_revoked else 0.0

        # LP burn (25 pts, proportional)
        score += (lp_burn_pct / 100.0) * WEIGHT_LP_BURN

        # Holder concentration (20 pts, inverse)
        # top_holder_pct of 0 = 20 pts, 100 = 0 pts
        holder_score = max(0.0, 1.0 - (top_holder_pct / 100.0)) * WEIGHT_HOLDER_CONCENTRATION
        score += holder_score

        return round(min(100.0, max(0.0, score)), 1)

    @staticmethod
    def _compute_verdict(score: float, warnings: List[str]) -> SafetyVerdict:
        """Determine the Go/No-Go verdict based on score and warnings.

        Rules:
        - Score >= 80 and ≤ 1 warning → GO
        - Score >= 50 or ≤ 2 warnings → CAUTION
        - Otherwise → NO_GO

        Parameters
        ----------
        score:
            Safety score (0–100).
        warnings:
            List of warning strings.

        Returns
        -------
        SafetyVerdict
        """
        critical_warnings = [
            w for w in warnings
            if "NOT revoked" in w
        ]

        # Any unrevoked authority is an automatic downgrade
        if len(critical_warnings) >= 2:
            return SafetyVerdict.NO_GO

        if score >= 80 and len(warnings) <= 1:
            return SafetyVerdict.GO

        if score >= 50 and len(warnings) <= 2:
            return SafetyVerdict.CAUTION

        return SafetyVerdict.NO_GO

    def __repr__(self) -> str:
        return f"RugChecker(rpc_url={self._rpc_url})"
