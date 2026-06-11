"""Jupiter V6 Swap Integration — Quotes, execution, price impact.

Provides a client for the Jupiter V6 API (https://quote-api.jup.ag/v6)
to fetch swap quotes and execute token swaps on Solana.

Features
--------
* Get swap quotes with slippage protection
* Execute swaps (build transaction, sign, send, confirm)
* Price impact estimation
* Route computation and comparison
* Support for priority fees and compute unit limits

Security
--------
All swap transactions are signed locally — private keys never leave the
machine. The wallet's keypair is used only for signing.
"""

from __future__ import annotations

import base64
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

JUPITER_V6_BASE_URL = "https://quote-api.jup.ag/v6"
SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class JupiterRoute(BaseModel):
    """A single route in a Jupiter quote.

    Attributes
    ----------
    in_mint:
        Input token mint address.
    out_mint:
        Output token mint address.
    in_amount:
        Input amount (raw, smallest unit).
    out_amount:
        Expected output amount (raw, smallest unit).
    price_impact_pct:
        Estimated price impact as a percentage.
    label:
        DEX or label used for this route step.
    """

    in_mint: str = ""
    out_mint: str = ""
    in_amount: str = "0"
    out_amount: str = "0"
    price_impact_pct: float = 0.0
    label: str = ""

    model_config = {"from_attributes": True}


class JupiterQuote(BaseModel):
    """A swap quote from Jupiter V6.

    Attributes
    ----------
    input_mint:
        Input token mint address.
    output_mint:
        Output token mint address.
    in_amount:
        Input amount (raw).
    out_amount:
        Expected output amount (raw).
    other_amount_threshold:
        Minimum output amount given slippage.
    price_impact_pct:
        Estimated price impact as a percentage.
    route_plan:
        Ordered list of route steps.
    slippage_bps:
        Slippage tolerance in basis points.
    created_at:
        Timestamp when the quote was fetched.
    """

    input_mint: str
    output_mint: str
    in_amount: str = "0"
    out_amount: str = "0"
    other_amount_threshold: str = "0"
    price_impact_pct: float = 0.0
    route_plan: List[JupiterRoute] = Field(default_factory=list)
    slippage_bps: int = 50
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    # Raw response stored for swap execution
    _raw_response: Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}


class JupiterSwapResult(BaseModel):
    """Result of a Jupiter V6 swap execution.

    Attributes
    ----------
    signature:
        Transaction signature on Solana.
    input_mint:
        Input token mint.
    output_mint:
        Output token mint.
    in_amount:
        Input amount.
    out_amount:
        Output amount received.
    status:
        Transaction status (confirmed, failed, etc.).
    slot:
        Slot number of the confirmed transaction.
    fee:
        Transaction fee paid (lamports).
    """

    signature: str
    input_mint: str
    output_mint: str
    in_amount: str = "0"
    out_amount: str = "0"
    status: str = "pending"
    slot: Optional[int] = None
    fee: int = 0

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# JupiterV6Client
# ---------------------------------------------------------------------------

class JupiterV6Client:
    """Jupiter V6 API client for swap quotes and execution.

    Parameters
    ----------
    rpc_url:
        Solana JSON-RPC endpoint for transaction sending.
    api_url:
        Jupiter V6 API base URL. Defaults to the public endpoint.
    timeout:
        HTTP request timeout in seconds.

    Examples
    --------
    .. code-block:: python

        client = JupiterV6Client(rpc_url="https://api.mainnet-beta.solana.com")
        quote = await client.get_quote(
            input_mint=SOL_MINT,
            output_mint=USDC_MINT,
            amount=1_000_000,
            slippage_bps=50,
        )
    """

    def __init__(
        self,
        rpc_url: str = "https://api.mainnet-beta.solana.com",
        api_url: str = JUPITER_V6_BASE_URL,
        timeout: int = 30,
    ) -> None:
        self._rpc_url = rpc_url
        self._api_url = api_url.rstrip("/")
        self._timeout = timeout
        self._http_client: Optional[httpx.AsyncClient] = None

    # ----- HTTP client management -----

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

    # ----- Get Quote -----

    async def get_quote(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
        slippage_bps: int = 50,
        only_direct_routes: bool = False,
        as_legacy_transaction: bool = False,
        platform_fee_bps: int = 0,
    ) -> JupiterQuote:
        """Fetch a swap quote from Jupiter V6.

        Parameters
        ----------
        input_mint:
            Input token mint address.
        output_mint:
            Output token mint address.
        amount:
            Input amount in the smallest token unit (lamports for SOL).
        slippage_bps:
            Slippage tolerance in basis points (e.g. 50 = 0.5%).
        only_direct_routes:
            If ``True``, only return direct routes (no hops).
        as_legacy_transaction:
            If ``True``, use legacy (non-Versioned) transaction format.
        platform_fee_bps:
            Platform fee in basis points (0–100).

        Returns
        -------
        JupiterQuote
            The quote with route plan and price impact.

        Raises
        ------
        httpx.HTTPError
            On network/API errors.
        ValueError
            If the API returns an error response.
        """
        client = await self._get_http()
        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": str(amount),
            "slippageBps": str(slippage_bps),
            "onlyDirectRoutes": str(only_direct_routes).lower(),
            "asLegacyTransaction": str(as_legacy_transaction).lower(),
        }
        if platform_fee_bps > 0:
            params["platformFeeBps"] = str(platform_fee_bps)

        resp = await client.get(f"{self._api_url}/quote", params=params)
        if resp.status_code != 200:
            error_msg = resp.text
            raise ValueError(f"Jupiter quote API error ({resp.status_code}): {error_msg}")

        data = resp.json()

        # Parse route plan
        route_plan: List[JupiterRoute] = []
        for step in data.get("routePlan", []):
            swap_info = step.get("swapInfo", {})
            route_plan.append(
                JupiterRoute(
                    in_mint=swap_info.get("inputMint", ""),
                    out_mint=swap_info.get("outputMint", ""),
                    in_amount=swap_info.get("inAmount", "0"),
                    out_amount=swap_info.get("outAmount", "0"),
                    price_impact_pct=float(step.get("priceImpactPct", 0.0)),
                    label=step.get("label", ""),
                )
            )

        quote = JupiterQuote(
            input_mint=data.get("inputMint", input_mint),
            output_mint=data.get("outputMint", output_mint),
            in_amount=data.get("inAmount", str(amount)),
            out_amount=data.get("outAmount", "0"),
            other_amount_threshold=data.get("otherAmountThreshold", "0"),
            price_impact_pct=float(data.get("priceImpactPct", 0.0)),
            route_plan=route_plan,
            slippage_bps=slippage_bps,
        )
        # Store raw response for swap execution
        quote._raw_response = data
        return quote

    # ----- Execute Swap -----

    async def execute_swap(
        self,
        quote: JupiterQuote,
        wallet,  # SolanaWallet
        priority_fee_lamports: int = 0,
        max_retries: int = 3,
        confirm_timeout: int = 60,
    ) -> JupiterSwapResult:
        """Execute a swap using a previously fetched quote.

        Steps:
        1. POST to ``/swap`` with the quote and wallet public key.
        2. Decode the returned transaction (Base64).
        3. Sign with the wallet's keypair.
        4. Send the signed transaction to the Solana RPC.
        5. Confirm the transaction.

        Parameters
        ----------
        quote:
            A :class:`JupiterQuote` previously fetched via :meth:`get_quote`.
        wallet:
            A :class:`SolanaWallet` instance for signing.
        priority_fee_lamports:
            Optional priority fee in lamports.
        max_retries:
            Maximum number of retries for sending the transaction.
        confirm_timeout:
            Timeout in seconds for transaction confirmation.

        Returns
        -------
        JupiterSwapResult
            The swap execution result with signature and status.

        Raises
        ------
        ValueError
            If the swap API returns an error or the quote has no raw response.
        RuntimeError
            If the transaction fails to confirm.
        """
        if quote._raw_response is None:
            raise ValueError("Quote has no raw response — re-fetch the quote before swapping")

        client = await self._get_http()

        # Step 1: Get swap transaction from Jupiter
        swap_payload = {
            "quoteResponse": quote._raw_response,
            "userPublicKey": wallet.public_key,
            "wrapAndUnwrapSol": True,
            "dynamicComputeUnitLimit": True,
            "prioritizationFeeLamports": priority_fee_lamports or "auto",
        }

        resp = await client.post(
            f"{self._api_url}/swap",
            json=swap_payload,
        )
        if resp.status_code != 200:
            error_msg = resp.text
            raise ValueError(f"Jupiter swap API error ({resp.status_code}): {error_msg}")

        swap_data = resp.json()
        swap_transaction_b64 = swap_data.get("swapTransaction", "")
        if not swap_transaction_b64:
            raise ValueError("No swap transaction returned from Jupiter")

        # Step 2-4: Decode, sign, and send the transaction
        try:
            from solders.transaction import VersionedTransaction  # type: ignore[import-untyped]
            from solana.rpc.async_api import AsyncClient  # type: ignore[import-untyped]
            from solana.rpc.commitment import Confirmed  # type: ignore[import-untyped]

            # Decode the transaction
            tx_bytes = base64.b64decode(swap_transaction_b64)
            tx = VersionedTransaction.from_bytes(tx_bytes)

            # Sign with wallet keypair
            signed_tx = VersionedTransaction(tx.message, [wallet.keypair])

            # Send to Solana RPC
            async with AsyncClient(self._rpc_url) as rpc_client:
                result = await rpc_client.send_raw_transaction(
                    bytes(signed_tx),
                    opts={"skip_preflight": True, "max_retries": max_retries},
                )
                signature = str(result.value)

                # Confirm transaction
                await rpc_client.confirm_transaction(
                    signature,
                    commitment=Confirmed,
                    sleep_seconds=0.5,
                    last_valid_block_height=None,
                )

                # Get transaction details
                tx_details = await rpc_client.get_transaction(
                    signature,
                    commitment=Confirmed,
                )

                status = "confirmed"
                slot = None
                fee = 0
                out_amount = quote.out_amount

                if tx_details.value:
                    slot = tx_details.value.slot
                    meta = tx_details.value.transaction.meta
                    if meta:
                        fee = meta.fee
                        if meta.err:
                            status = "failed"

                return JupiterSwapResult(
                    signature=signature,
                    input_mint=quote.input_mint,
                    output_mint=quote.output_mint,
                    in_amount=quote.in_amount,
                    out_amount=out_amount,
                    status=status,
                    slot=slot,
                    fee=fee,
                )

        except ImportError as exc:
            raise ImportError(
                "solana and solders packages are required for swap execution. "
                "Install with: pip install solana solders"
            ) from exc
        except Exception as exc:
            logger.error("Swap execution failed: %s", exc)
            raise RuntimeError(f"Swap execution failed: {exc}") from exc

    # ----- Price Impact Estimation -----

    @staticmethod
    def estimate_price_impact(
        in_amount: float,
        out_amount: float,
        reference_price: float,
        input_decimals: int = 9,
        output_decimals: int = 6,
    ) -> float:
        """Estimate price impact from a swap.

        Parameters
        ----------
        in_amount:
            Raw input amount.
        out_amount:
            Raw output amount.
        reference_price:
            Reference price (output per input in human-readable units).
        input_decimals:
            Input token decimals.
        output_decimals:
            Output token decimals.

        Returns
        -------
        float
            Estimated price impact as a percentage (0–100).
        """
        in_human = in_amount / (10 ** input_decimals) if in_amount else 0
        out_human = out_amount / (10 ** output_decimals) if out_amount else 0

        if in_human == 0 or reference_price == 0:
            return 0.0

        effective_price = out_human / in_human
        impact = ((reference_price - effective_price) / reference_price) * 100
        return max(0.0, impact)

    # ----- Route Computation -----

    async def compare_routes(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
        slippage_bps: int = 50,
    ) -> List[JupiterQuote]:
        """Fetch multiple route options for comparison.

        Currently returns a single quote (Jupiter's API picks the best route).
        Future versions may support split-route exploration.

        Parameters
        ----------
        input_mint:
            Input token mint address.
        output_mint:
            Output token mint address.
        amount:
            Input amount in smallest token unit.
        slippage_bps:
            Slippage tolerance in basis points.

        Returns
        -------
        list of JupiterQuote
            Available route options (currently one).
        """
        quote = await self.get_quote(
            input_mint=input_mint,
            output_mint=output_mint,
            amount=amount,
            slippage_bps=slippage_bps,
        )
        return [quote]

    def __repr__(self) -> str:
        return f"JupiterV6Client(api_url={self._api_url})"
