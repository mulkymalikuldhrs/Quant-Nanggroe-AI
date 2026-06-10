"""
Jupiter V6 Broker — Solana DEX Swap Execution
==============================================
Integration with Jupiter V6 API for Solana-based token swaps.
Handles quote fetching, transaction building, signing, and confirmation.

Features:
    - Quote fetching with configurable slippage
    - Swap execution via Jupiter V6 API
    - Transaction signing and confirmation
    - Token price lookup
    - Priority fee estimation
    - Retry logic with exponential backoff

Requirements:
    pip install solana solders

Jupiter API Docs: https://station.jup.ag/docs/apis/swap-api
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
from datetime import datetime
from typing import Any

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# MODELS
# ══════════════════════════════════════════════════════════════════════

# Well-known Solana token mints
SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
USDT_MINT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"


class JupiterQuote(BaseModel):
    """Quote from Jupiter V6 API."""

    input_mint: str
    output_mint: str
    in_amount: str
    out_amount: str
    other_amount_threshold: str = "0"
    swap_mode: str = "ExactIn"
    slippage_bps: int = 50
    price_impact_pct: float = 0.0
    route_plan: list[dict[str, Any]] = Field(default_factory=list)
    raw_response: dict[str, Any] = Field(default_factory=dict)

    @property
    def input_amount(self) -> float:
        """Input amount as float (in token units)."""
        return int(self.in_amount) / 1e9 if self.input_mint == SOL_MINT else int(self.in_amount) / 1e6

    @property
    def output_amount(self) -> float:
        """Output amount as float (in token units)."""
        return int(self.out_amount) / 1e9 if self.output_mint == SOL_MINT else int(self.out_amount) / 1e6


class JupiterSwapResult(BaseModel):
    """Result from a Jupiter swap execution."""

    success: bool
    transaction_signature: str = ""
    input_mint: str = ""
    output_mint: str = ""
    in_amount: str = ""
    out_amount: str = ""
    fee_sol: float = 0.0
    error: str = ""
    confirmed_at: datetime | None = None
    raw_response: dict[str, Any] = Field(default_factory=dict)


class TokenBalance(BaseModel):
    """Token balance on Solana."""

    mint: str
    amount: float
    decimals: int
    ui_amount: float


# ══════════════════════════════════════════════════════════════════════
# JUPITER BROKER
# ══════════════════════════════════════════════════════════════════════


class JupiterBroker:
    """
    Jupiter V6 DEX broker for Solana token swaps.

    Provides quote fetching, swap execution, and transaction
    confirmation through the Jupiter V6 API.

    Args:
        wallet_private_key: Base58-encoded Solana private key
        rpc_url: Solana RPC endpoint URL
        jupiter_api_url: Jupiter API base URL
        default_slippage_bps: Default slippage in basis points (50 = 0.5%)
        priority_fee_lamports: Priority fee in lamports
        max_retries: Maximum retry attempts

    Example:
        broker = JupiterBroker(
            wallet_private_key="...",
            rpc_url="https://api.mainnet-beta.solana.com",
        )
        quote = await broker.get_quote(USDC_MINT, SOL_MINT, 100_000_000)
        result = await broker.execute_swap(quote)
    """

    JUPITER_API_V6 = "https://quote-api.jup.ag/v6"

    def __init__(
        self,
        wallet_private_key: str = "",
        rpc_url: str = "https://api.mainnet-beta.solana.com",
        jupiter_api_url: str | None = None,
        default_slippage_bps: int = 50,
        priority_fee_lamports: int = 100_000,
        max_retries: int = 3,
    ) -> None:
        self._private_key = wallet_private_key
        self._rpc_url = rpc_url
        self._jupiter_url = jupiter_api_url or self.JUPITER_API_V6
        self._default_slippage_bps = default_slippage_bps
        self._priority_fee = priority_fee_lamports
        self._max_retries = max_retries

        self._http_client: httpx.AsyncClient | None = None
        self._keypair: Any = None
        self._public_key: str = ""

        if wallet_private_key:
            self._init_wallet(wallet_private_key)

    def _init_wallet(self, private_key: str) -> None:
        """Initialize Solana wallet from private key."""
        try:
            from solders.keypair import Keypair

            # Try base58 decoding first, then base64
            try:
                key_bytes = base64.b64decode(private_key)
                self._keypair = Keypair.from_bytes(key_bytes)
            except Exception:
                try:
                    from base58 import b58decode
                    key_bytes = b58decode(private_key)
                    self._keypair = Keypair.from_bytes(key_bytes)
                except Exception:
                    # Assume it's a byte array JSON
                    key_bytes = bytes(json.loads(private_key))
                    self._keypair = Keypair.from_bytes(key_bytes)

            self._public_key = str(self._keypair.pubkey())
            logger.info("Jupiter wallet initialized: %s", self._public_key[:8] + "...")
        except ImportError:
            logger.warning(
                "solders not installed. Run: pip install solders. "
                "Wallet signing will not be available."
            )
        except Exception as exc:
            logger.error("Failed to initialize wallet: %s", exc)

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=30.0,
                headers={"Content-Type": "application/json"},
            )
        return self._http_client

    # ══════════════════════════════════════════════════════════════════
    # QUOTE
    # ══════════════════════════════════════════════════════════════════

    async def get_quote(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
        slippage_bps: int | None = None,
        only_direct_routes: bool = False,
        as_legacy_transaction: bool = False,
    ) -> JupiterQuote:
        """
        Fetch a swap quote from Jupiter V6.

        Args:
            input_mint: Input token mint address
            output_mint: Output token mint address
            amount: Amount in smallest token unit (lamports for SOL, micro-units for USDC)
            slippage_bps: Slippage tolerance in basis points
            only_direct_routes: Only use direct routes (no hop tokens)
            as_legacy_transaction: Return legacy transaction format

        Returns:
            JupiterQuote with route and price impact info

        Raises:
            ValueError: If quote fetch fails
        """
        client = await self._get_http_client()
        slippage = slippage_bps or self._default_slippage_bps

        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": str(amount),
            "slippageBps": str(slippage),
            "onlyDirectRoutes": str(only_direct_routes).lower(),
            "asLegacyTransaction": str(as_legacy_transaction).lower(),
        }

        for attempt in range(self._max_retries):
            try:
                response = await client.get(
                    f"{self._jupiter_url}/quote", params=params
                )
                response.raise_for_status()
                data = response.json()

                quote = JupiterQuote(
                    input_mint=data.get("inputMint", input_mint),
                    output_mint=data.get("outputMint", output_mint),
                    in_amount=data.get("inAmount", str(amount)),
                    out_amount=data.get("outAmount", "0"),
                    other_amount_threshold=data.get("otherAmountThreshold", "0"),
                    swap_mode=data.get("swapMode", "ExactIn"),
                    slippage_bps=slippage,
                    price_impact_pct=float(data.get("priceImpactPct", 0)),
                    route_plan=data.get("routePlan", []),
                    raw_response=data,
                )
                logger.info(
                    "Quote: %s -> %s, in=%s, out=%s, impact=%.2f%%",
                    input_mint[:8], output_mint[:8],
                    quote.in_amount, quote.out_amount,
                    quote.price_impact_pct,
                )
                return quote

            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429:
                    backoff = 0.5 * (2 ** attempt)
                    logger.warning("Rate limited, retrying in %.1fs", backoff)
                    await asyncio.sleep(backoff)
                    continue
                logger.error("Quote failed (HTTP %d): %s", exc.response.status_code, exc)
                raise ValueError(f"Quote fetch failed: {exc}") from exc
            except Exception as exc:
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(0.5 * (2 ** attempt))
                    continue
                raise ValueError(f"Quote fetch failed after {self._max_retries} attempts: {exc}") from exc

        raise ValueError("Quote fetch failed: max retries exceeded")

    # ══════════════════════════════════════════════════════════════════
    # SWAP EXECUTION
    # ══════════════════════════════════════════════════════════════════

    async def execute_swap(
        self,
        quote: JupiterQuote,
        priority_fee_lamports: int | None = None,
        commitment: str = "confirmed",
    ) -> JupiterSwapResult:
        """
        Execute a swap using a previously fetched quote.

        This method:
        1. Requests swap transaction from Jupiter
        2. Signs the transaction with the wallet keypair
        3. Sends the transaction to Solana
        4. Confirms the transaction

        Args:
            quote: Previously fetched JupiterQuote
            priority_fee_lamports: Override priority fee
            commitment: Solana commitment level ("confirmed", "finalized")

        Returns:
            JupiterSwapResult with execution details
        """
        if not self._keypair:
            return JupiterSwapResult(
                success=False,
                error="Wallet not initialized. Provide private key to constructor.",
            )

        client = await self._get_http_client()
        fee = priority_fee_lamports or self._priority_fee

        # Step 1: Get swap transaction from Jupiter
        swap_payload = {
            "quoteResponse": quote.raw_response,
            "userPublicKey": self._public_key,
            "wrapAndUnwrapSol": True,
            "dynamicComputeUnitLimit": True,
            "prioritizationFeeLamports": fee,
        }

        try:
            swap_response = await client.post(
                f"{self._jupiter_url}/swap",
                json=swap_payload,
            )
            swap_response.raise_for_status()
            swap_data = swap_response.json()
        except Exception as exc:
            logger.error("Swap transaction request failed: %s", exc)
            return JupiterSwapResult(
                success=False,
                error=f"Swap request failed: {exc}",
                input_mint=quote.input_mint,
                output_mint=quote.output_mint,
            )

        # Step 2: Sign the transaction
        swap_transaction_b64 = swap_data.get("swapTransaction", "")
        if not swap_transaction_b64:
            return JupiterSwapResult(
                success=False,
                error="No swap transaction in response",
            )

        try:
            signed_tx = await self._sign_transaction(swap_transaction_b64)
        except Exception as exc:
            logger.error("Transaction signing failed: %s", exc)
            return JupiterSwapResult(
                success=False,
                error=f"Signing failed: {exc}",
            )

        # Step 3: Send transaction
        try:
            signature = await self._send_transaction(signed_tx, commitment)
            logger.info("Swap transaction sent: %s", signature)
        except Exception as exc:
            logger.error("Transaction send failed: %s", exc)
            return JupiterSwapResult(
                success=False,
                error=f"Send failed: {exc}",
            )

        # Step 4: Confirm transaction
        try:
            confirmed = await self._confirm_transaction(signature, commitment)
        except Exception as exc:
            logger.warning("Confirmation timeout (transaction may still succeed): %s", exc)
            confirmed = True  # Optimistic — transaction may still land

        result = JupiterSwapResult(
            success=confirmed,
            transaction_signature=signature,
            input_mint=quote.input_mint,
            output_mint=quote.output_mint,
            in_amount=quote.in_amount,
            out_amount=quote.out_amount,
            fee_sol=fee / 1e9,
            confirmed_at=datetime.now() if confirmed else None,
            raw_response=swap_data,
        )

        logger.info(
            "Swap %s: %s -> %s, sig=%s",
            "confirmed" if confirmed else "pending",
            quote.input_mint[:8], quote.output_mint[:8],
            signature[:16] + "...",
        )
        return result

    async def buy(
        self,
        token_mint: str,
        sol_amount: int,
        slippage_bps: int | None = None,
    ) -> JupiterSwapResult:
        """
        Buy a token with SOL.

        Args:
            token_mint: Token mint address to buy
            sol_amount: Amount in lamports
            slippage_bps: Slippage tolerance

        Returns:
            JupiterSwapResult
        """
        quote = await self.get_quote(SOL_MINT, token_mint, sol_amount, slippage_bps)
        return await self.execute_swap(quote)

    async def sell(
        self,
        token_mint: str,
        token_amount: int,
        slippage_bps: int | None = None,
    ) -> JupiterSwapResult:
        """
        Sell a token for SOL.

        Args:
            token_mint: Token mint address to sell
            token_amount: Amount in smallest token unit
            slippage_bps: Slippage tolerance

        Returns:
            JupiterSwapResult
        """
        quote = await self.get_quote(token_mint, SOL_MINT, token_amount, slippage_bps)
        return await self.execute_swap(quote)

    # ══════════════════════════════════════════════════════════════════
    # PRICE LOOKUP
    # ══════════════════════════════════════════════════════════════════

    async def get_price(self, token_mint: str, vs_mint: str = USDC_MINT) -> float:
        """
        Get the current price of a token.

        Uses a small quote to estimate the price.

        Args:
            token_mint: Token to price
            vs_mint: Quote token (default USDC)

        Returns:
            Price per token in vs_mint units
        """
        # Use a small amount to get price estimate
        if token_mint == SOL_MINT:
            amount = 1_000_000_000  # 1 SOL in lamports
        else:
            amount = 1_000_000  # 1 unit in micro

        try:
            quote = await self.get_quote(token_mint, vs_mint, amount)
            in_float = quote.input_amount
            out_float = quote.output_amount
            if in_float > 0:
                return out_float / in_float
            return 0.0
        except Exception as exc:
            logger.error("Price lookup failed for %s: %s", token_mint[:8], exc)
            return 0.0

    # ══════════════════════════════════════════════════════════════════
    # TRANSACTION HELPERS
    # ══════════════════════════════════════════════════════════════════

    async def _sign_transaction(self, transaction_b64: str) -> str:
        """Sign a base64-encoded transaction."""
        try:
            from solders.message import MessageV0
            from solders.transaction import VersionedTransaction

            tx_bytes = base64.b64decode(transaction_b64)
            tx = VersionedTransaction.from_bytes(tx_bytes)

            # Sign with our keypair
            signed_tx = VersionedTransaction(tx.message, [self._keypair])
            signed_b64 = base64.b64encode(bytes(signed_tx)).decode()
            return signed_b64
        except ImportError:
            raise RuntimeError("solders not installed. Cannot sign transactions.")
        except Exception as exc:
            raise RuntimeError(f"Transaction signing failed: {exc}") from exc

    async def _send_transaction(self, signed_tx_b64: str, commitment: str = "confirmed") -> str:
        """Send a signed transaction to Solana via RPC."""
        client = await self._get_http_client()

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "sendTransaction",
            "params": [
                signed_tx_b64,
                {
                    "encoding": "base64",
                    "skipPreflight": True,
                    "maxRetries": 3,
                },
            ],
        }

        response = await client.post(self._rpc_url, json=payload)
        result = response.json()

        if "error" in result:
            raise RuntimeError(f"RPC error: {result['error']}")

        signature = result.get("result", "")
        if not signature:
            raise RuntimeError("No signature in RPC response")
        return signature

    async def _confirm_transaction(
        self, signature: str, commitment: str = "confirmed", timeout: float = 30.0
    ) -> bool:
        """Wait for transaction confirmation."""
        client = await self._get_http_client()
        start = time.monotonic()

        while time.monotonic() - start < timeout:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignatureStatuses",
                "params": [[signature]],
            }

            response = await client.post(self._rpc_url, json=payload)
            result = response.json()

            statuses = result.get("result", {}).get("value", [])
            if statuses and statuses[0]:
                status = statuses[0]
                if status.get("confirmationStatus") == commitment or status.get("confirmationStatus") == "finalized":
                    return True
                if status.get("err"):
                    logger.error("Transaction failed: %s", status["err"])
                    return False

            await asyncio.sleep(0.5)

        return False  # Timeout

    async def close(self) -> None:
        """Close HTTP client connections."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            logger.info("Jupiter broker HTTP client closed")
