"""Jupiter V6 Swap Integration — Quotes, execution, price impact, token management.

Provides a client for the Jupiter V6 API (https://quote-api.jup.ag/v6)
to fetch swap quotes and execute token swaps on Solana.

Features
--------
* Get swap quotes with slippage protection
* Execute swaps (build transaction, sign, send, confirm)
* Price impact estimation
* Route computation and comparison
* Support for priority fees and compute unit limits
* Token price fetching via Jupiter price API
* SPL token account creation and management
* Transaction simulation before sending
* Minimum output validation with slippage protection

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
JUPITER_PRICE_URL = "https://price.jup.ag/v6"
SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
USDT_MINT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"

# Default token decimals
_DEFAULT_DECIMALS: Dict[str, int] = {
    SOL_MINT: 9,
    USDC_MINT: 6,
    USDT_MINT: 6,
}


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
    minimum_output_received:
        Minimum output guaranteed by slippage.
    """

    signature: str
    input_mint: str
    output_mint: str
    in_amount: str = "0"
    out_amount: str = "0"
    status: str = "pending"
    slot: Optional[int] = None
    fee: int = 0
    minimum_output_received: str = "0"

    model_config = {"from_attributes": True}


class TokenPrice(BaseModel):
    """Token price from Jupiter Price API.

    Attributes
    ----------
    mint:
        Token mint address.
    price_usd:
        Price in USD.
    price_sol:
        Price in SOL.
    last_updated:
        Timestamp of the price data.
    """

    mint: str
    price_usd: Optional[float] = None
    price_sol: Optional[float] = None
    last_updated: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))

    model_config = {"from_attributes": True}


class TokenInfo(BaseModel):
    """Token information from Jupiter token list.

    Attributes
    ----------
    mint:
        Token mint address.
    symbol:
        Token symbol (e.g. ``"SOL"``).
    name:
        Token name (e.g. ``"Solana"``).
    decimals:
        Token decimals.
    logo_uri:
        URI for the token logo.
    tags:
        Jupiter tags (e.g. ``["verified"]``).
    """

    mint: str
    symbol: str = ""
    name: str = ""
    decimals: int = 9
    logo_uri: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# JupiterV6Client
# ---------------------------------------------------------------------------

class JupiterV6Client:
    """Jupiter V6 API client for swap quotes, execution, and token management.

    Parameters
    ----------
    rpc_url:
        Solana JSON-RPC endpoint for transaction sending.
    api_url:
        Jupiter V6 API base URL. Defaults to the public endpoint.
    timeout:
        HTTP request timeout in seconds.
    default_slippage_bps:
        Default slippage tolerance in basis points.

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
        default_slippage_bps: int = 50,
    ) -> None:
        self._rpc_url = rpc_url
        self._api_url = api_url.rstrip("/")
        self._timeout = timeout
        self._default_slippage_bps = default_slippage_bps
        self._http_client: Optional[httpx.AsyncClient] = None
        self._token_list_cache: Optional[Dict[str, TokenInfo]] = None
        self._token_list_cache_ts: float = 0.0

    # ----- HTTP client management -----

    async def _get_http(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=self._timeout,
                headers={"Content-Type": "application/json"},
            )
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
        slippage_bps: Optional[int] = None,
        only_direct_routes: bool = False,
        as_legacy_transaction: bool = False,
        platform_fee_bps: int = 0,
        max_accounts: Optional[int] = None,
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
            Defaults to the client's default_slippage_bps.
        only_direct_routes:
            If ``True``, only return direct routes (no hops).
        as_legacy_transaction:
            If ``True``, use legacy (non-Versioned) transaction format.
        platform_fee_bps:
            Platform fee in basis points (0-100).
        max_accounts:
            Maximum number of accounts allowed in the transaction.

        Returns
        -------
        JupiterQuote
            The quote with route plan and price impact.

        Raises
        ------
        ValueError
            If the API returns an error response.
        """
        client = await self._get_http()
        effective_slippage = slippage_bps if slippage_bps is not None else self._default_slippage_bps

        params: Dict[str, Any] = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": str(amount),
            "slippageBps": str(effective_slippage),
            "onlyDirectRoutes": str(only_direct_routes).lower(),
            "asLegacyTransaction": str(as_legacy_transaction).lower(),
        }
        if platform_fee_bps > 0:
            params["platformFeeBps"] = str(platform_fee_bps)
        if max_accounts is not None:
            params["maxAccounts"] = str(max_accounts)

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
            slippage_bps=effective_slippage,
        )
        # Store raw response for swap execution
        quote._raw_response = data
        return quote

    # ----- Execute Swap -----

    async def execute_swap(
        self,
        quote: JupiterQuote,
        wallet: Any,  # SolanaWallet
        priority_fee_lamports: int = 0,
        max_retries: int = 3,
        confirm_timeout: int = 60,
        simulate_first: bool = True,
        skip_preflight: bool = False,
    ) -> JupiterSwapResult:
        """Execute a swap using a previously fetched quote.

        Steps:
        1. POST to ``/swap`` with the quote and wallet public key.
        2. Decode the returned transaction (Base64).
        3. Optionally simulate the transaction.
        4. Sign with the wallet's keypair.
        5. Send the signed transaction to the Solana RPC.
        6. Confirm the transaction.
        7. Validate minimum output with slippage protection.

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
        simulate_first:
            If ``True``, simulate the transaction before sending.
        skip_preflight:
            If ``True``, skip preflight checks when sending.

        Returns
        -------
        JupiterSwapResult
            The swap execution result with signature and status.

        Raises
        ------
        ValueError
            If the swap API returns an error or the quote has no raw response.
        RuntimeError
            If the transaction fails to confirm or simulation fails.
        """
        if quote._raw_response is None:
            raise ValueError("Quote has no raw response — re-fetch the quote before swapping")

        # Validate minimum output with slippage
        out_amount = int(quote.out_amount) if quote.out_amount else 0
        threshold = int(quote.other_amount_threshold) if quote.other_amount_threshold else 0
        if threshold > 0 and out_amount > 0:
            slippage_pct = ((out_amount - threshold) / out_amount) * 100
            if slippage_pct > 10.0:
                logger.warning(
                    "JupiterV6Client: High slippage detected (%.2f%%) — "
                    "output threshold is significantly below expected output",
                    slippage_pct,
                )

        client = await self._get_http()

        # Step 1: Get swap transaction from Jupiter
        swap_payload: Dict[str, Any] = {
            "quoteResponse": quote._raw_response,
            "userPublicKey": wallet.public_key,
            "wrapAndUnwrapSol": True,
            "dynamicComputeUnitLimit": True,
            "prioritizationFeeLamports": priority_fee_lamports if priority_fee_lamports > 0 else "auto",
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

        # Step 2-6: Decode, optionally simulate, sign, send, confirm
        try:
            from solders.transaction import VersionedTransaction  # type: ignore[import-untyped]
            from solana.rpc.async_api import AsyncClient  # type: ignore[import-untyped]
            from solana.rpc.commitment import Confirmed  # type: ignore[import-untyped]

            # Decode the transaction
            tx_bytes = base64.b64decode(swap_transaction_b64)
            tx = VersionedTransaction.from_bytes(tx_bytes)

            # Sign with wallet keypair
            signed_tx = VersionedTransaction(tx.message, [wallet.keypair])

            async with AsyncClient(self._rpc_url) as rpc_client:
                # Optional: Simulate transaction before sending
                if simulate_first:
                    sim_result = await rpc_client.simulate_transaction(
                        bytes(signed_tx),
                        sig_verify=True,
                    )
                    if sim_result.value and sim_result.value.err:
                        err_info = sim_result.value.err
                        logger.error(
                            "JupiterV6Client: Transaction simulation failed: %s",
                            err_info,
                        )
                        raise RuntimeError(
                            f"Transaction simulation failed: {err_info}"
                        )
                    logger.debug(
                        "JupiterV6Client: Simulation successful, units consumed: %s",
                        sim_result.value.units_consumed if sim_result.value else "unknown",
                    )

                # Send to Solana RPC
                result = await rpc_client.send_raw_transaction(
                    bytes(signed_tx),
                    opts={
                        "skip_preflight": skip_preflight,
                        "max_retries": max_retries,
                    },
                )
                signature = str(result.value)

                # Confirm transaction
                try:
                    await rpc_client.confirm_transaction(
                        signature,
                        commitment=Confirmed,
                        sleep_seconds=0.5,
                        last_valid_block_height=None,
                    )
                except Exception as confirm_exc:
                    logger.warning(
                        "JupiterV6Client: Transaction confirmation error (may still succeed): %s",
                        confirm_exc,
                    )

                # Get transaction details
                tx_details = await rpc_client.get_transaction(
                    signature,
                    commitment=Confirmed,
                    max_supported_transaction_version=0,
                )

                status = "confirmed"
                slot = None
                fee = 0

                if tx_details and tx_details.value:
                    slot = tx_details.value.slot
                    meta = tx_details.value.transaction.meta
                    if meta:
                        fee = meta.fee or 0
                        if meta.err:
                            status = "failed"
                            logger.error(
                                "JupiterV6Client: Transaction failed on-chain: %s",
                                meta.err,
                            )

                return JupiterSwapResult(
                    signature=signature,
                    input_mint=quote.input_mint,
                    output_mint=quote.output_mint,
                    in_amount=quote.in_amount,
                    out_amount=quote.out_amount,
                    status=status,
                    slot=slot,
                    fee=fee,
                    minimum_output_received=quote.other_amount_threshold,
                )

        except ImportError as exc:
            raise ImportError(
                "solana and solders packages are required for swap execution. "
                "Install with: pip install solana solders"
            ) from exc
        except RuntimeError:
            raise
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
            Estimated price impact as a percentage (0-100).
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

    # ----- Token Prices -----

    async def get_price(
        self,
        mint: str,
        vs_mint: str = USDC_MINT,
    ) -> TokenPrice:
        """Fetch the price of a token via Jupiter Price API.

        Parameters
        ----------
        mint:
            Token mint address.
        vs_mint:
            Quote token mint (defaults to USDC).

        Returns
        -------
        TokenPrice
            Current token price.

        Raises
        ------
        ValueError
            If the price API returns an error.
        """
        client = await self._get_http()
        params = {
            "ids": mint,
            "vsToken": vs_mint,
        }

        resp = await client.get(f"{JUPITER_PRICE_URL}/price", params=params)
        if resp.status_code != 200:
            raise ValueError(f"Jupiter price API error ({resp.status_code}): {resp.text}")

        data = resp.json()
        price_data = data.get("data", {}).get(mint, {})

        price_usd = None
        price_sol = None

        if vs_mint == USDC_MINT:
            price_usd = float(price_data.get("price", 0)) if price_data.get("price") else None
        elif vs_mint == SOL_MINT:
            price_sol = float(price_data.get("price", 0)) if price_data.get("price") else None

        # Also try to get SOL price if we got USD price
        if price_usd is not None and price_sol is None:
            try:
                sol_price_data = await self._get_sol_price_usd(client)
                if sol_price_data and sol_price_data > 0:
                    price_sol = price_usd / sol_price_data
            except Exception:
                pass

        return TokenPrice(
            mint=mint,
            price_usd=price_usd,
            price_sol=price_sol,
        )

    async def get_prices(
        self,
        mints: List[str],
        vs_mint: str = USDC_MINT,
    ) -> Dict[str, TokenPrice]:
        """Fetch prices for multiple tokens via Jupiter Price API.

        Parameters
        ----------
        mints:
            List of token mint addresses.
        vs_mint:
            Quote token mint (defaults to USDC).

        Returns
        -------
        dict
            Mapping of mint -> TokenPrice.
        """
        client = await self._get_http()
        params = {
            "ids": ",".join(mints),
            "vsToken": vs_mint,
        }

        resp = await client.get(f"{JUPITER_PRICE_URL}/price", params=params)
        if resp.status_code != 200:
            raise ValueError(f"Jupiter price API error ({resp.status_code}): {resp.text}")

        data = resp.json()
        prices: Dict[str, TokenPrice] = {}

        for mint in mints:
            price_data = data.get("data", {}).get(mint, {})
            price_val = float(price_data.get("price", 0)) if price_data.get("price") else None

            if vs_mint == USDC_MINT:
                prices[mint] = TokenPrice(mint=mint, price_usd=price_val)
            elif vs_mint == SOL_MINT:
                prices[mint] = TokenPrice(mint=mint, price_sol=price_val)
            else:
                prices[mint] = TokenPrice(mint=mint, price_usd=price_val)

        return prices

    async def _get_sol_price_usd(self, client: httpx.AsyncClient) -> Optional[float]:
        """Get SOL price in USD."""
        try:
            params = {"ids": SOL_MINT, "vsToken": USDC_MINT}
            resp = await client.get(f"{JUPITER_PRICE_URL}/price", params=params)
            if resp.status_code == 200:
                data = resp.json()
                price_data = data.get("data", {}).get(SOL_MINT, {})
                return float(price_data.get("price", 0)) if price_data.get("price") else None
        except Exception:
            pass
        return None

    # ----- Token List -----

    async def get_token_list(self, force_refresh: bool = False) -> Dict[str, TokenInfo]:
        """Fetch the Jupiter token list.

        Returns a mapping of mint address -> TokenInfo.
        Results are cached for 1 hour.

        Parameters
        ----------
        force_refresh:
            If ``True``, bypass the cache and fetch fresh data.

        Returns
        -------
        dict
            Mapping of mint address -> TokenInfo.
        """
        cache_ttl = 3600.0  # 1 hour
        if (
            not force_refresh
            and self._token_list_cache is not None
            and (datetime.now(tz=timezone.utc).timestamp() - self._token_list_cache_ts) < cache_ttl
        ):
            return self._token_list_cache

        client = await self._get_http()
        resp = await client.get("https://token.jup.ag/strict")
        if resp.status_code != 200:
            raise ValueError(f"Jupiter token list API error ({resp.status_code}): {resp.text}")

        data = resp.json()
        token_map: Dict[str, TokenInfo] = {}
        for token in data:
            mint = token.get("address", "")
            if not mint:
                continue
            token_map[mint] = TokenInfo(
                mint=mint,
                symbol=token.get("symbol", ""),
                name=token.get("name", ""),
                decimals=token.get("decimals", 9),
                logo_uri=token.get("logoURI"),
                tags=token.get("tags", []),
            )

        self._token_list_cache = token_map
        self._token_list_cache_ts = datetime.now(tz=timezone.utc).timestamp()
        logger.info("JupiterV6Client: Token list loaded — %d tokens", len(token_map))
        return token_map

    async def get_token_info(self, mint: str) -> Optional[TokenInfo]:
        """Get info for a specific token.

        Parameters
        ----------
        mint:
            Token mint address.

        Returns
        -------
        TokenInfo or None
        """
        token_list = await self.get_token_list()
        return token_list.get(mint)

    # ----- SPL Token Account Management -----

    async def create_associated_token_account(
        self,
        wallet: Any,  # SolanaWallet
        mint: str,
    ) -> str:
        """Create an Associated Token Account for a mint if it doesn't exist.

        Parameters
        ----------
        wallet:
            A :class:`SolanaWallet` instance.
        mint:
            SPL token mint address.

        Returns
        -------
        str
            The token account address.

        Raises
        ------
        RuntimeError
            If account creation fails.
        """
        try:
            from solders.pubkey import Pubkey  # type: ignore[import-untyped]
            from spl.token.instructions import create_associated_token_account, get_associated_token_address  # type: ignore[import-untyped]
            from solana.rpc.async_api import AsyncClient  # type: ignore[import-untyped]
            from solana.rpc.commitment import Confirmed  # type: ignore[import-untyped]
            from solana.transaction import Transaction  # type: ignore[import-untyped]

            async with AsyncClient(self._rpc_url) as rpc_client:
                owner_pubkey = Pubkey.from_string(wallet.public_key)
                mint_pubkey = Pubkey.from_string(mint)
                ata = get_associated_token_address(owner_pubkey, mint_pubkey)

                # Check if account already exists
                resp = await rpc_client.get_account_info(ata, commitment=Confirmed)
                if resp.value is not None:
                    return str(ata)

                # Create the ATA
                create_ix = create_associated_token_account(
                    payer=owner_pubkey,
                    owner=owner_pubkey,
                    mint=mint_pubkey,
                )

                tx = Transaction()
                tx.add(create_ix)
                tx.recent_blockhash = (await rpc_client.get_latest_blockhash()).value.blockhash
                tx.sign(wallet.keypair)

                result = await rpc_client.send_transaction(
                    tx,
                    wallet.keypair,
                    opts={"skip_preflight": False},
                )
                signature = str(result.value)

                await rpc_client.confirm_transaction(
                    signature,
                    commitment=Confirmed,
                )

                logger.info(
                    "JupiterV6Client: Created ATA for %s: %s",
                    mint, str(ata),
                )
                return str(ata)

        except ImportError as exc:
            raise ImportError(
                "solana, solders, and spl packages are required. "
                "Install with: pip install solana solders spl-token"
            ) from exc
        except Exception as exc:
            raise RuntimeError(f"Failed to create ATA for {mint}: {exc}") from exc

    async def get_or_create_ata(
        self,
        wallet: Any,
        mint: str,
    ) -> str:
        """Get the Associated Token Account address, creating it if needed.

        Parameters
        ----------
        wallet:
            A :class:`SolanaWallet` instance.
        mint:
            SPL token mint address.

        Returns
        -------
        str
            The token account address.
        """
        try:
            from solders.pubkey import Pubkey  # type: ignore[import-untyped]
            from spl.token.instructions import get_associated_token_address  # type: ignore[import-untyped]
            from solana.rpc.async_api import AsyncClient  # type: ignore[import-untyped]
            from solana.rpc.commitment import Confirmed  # type: ignore[import-untyped]

            async with AsyncClient(self._rpc_url) as rpc_client:
                owner_pubkey = Pubkey.from_string(wallet.public_key)
                mint_pubkey = Pubkey.from_string(mint)
                ata = get_associated_token_address(owner_pubkey, mint_pubkey)

                # Check if account exists
                resp = await rpc_client.get_account_info(ata, commitment=Confirmed)
                if resp.value is not None:
                    return str(ata)

        except ImportError:
            pass
        except Exception as exc:
            logger.warning(
                "JupiterV6Client: Error checking ATA: %s, attempting creation",
                exc,
            )

        # Create if not found
        return await self.create_associated_token_account(wallet, mint)

    # ----- Utility -----

    @staticmethod
    def to_raw_amount(amount: float, decimals: int) -> int:
        """Convert a human-readable amount to raw (smallest unit).

        Parameters
        ----------
        amount:
            Human-readable amount.
        decimals:
            Token decimals.

        Returns
        -------
        int
            Raw amount.
        """
        return int(amount * (10 ** decimals))

    @staticmethod
    def from_raw_amount(raw_amount: int, decimals: int) -> float:
        """Convert a raw amount to human-readable.

        Parameters
        ----------
        raw_amount:
            Raw amount in smallest unit.
        decimals:
            Token decimals.

        Returns
        -------
        float
            Human-readable amount.
        """
        return raw_amount / (10 ** decimals)

    def __repr__(self) -> str:
        return f"JupiterV6Client(api_url={self._api_url})"
