"""Solana Wallet Service — Keypair management, SOL/SPL balance checking.

Provides utilities for managing Solana keypairs, checking SOL and SPL token
balances, and managing token accounts. Uses the ``solana`` and ``solders``
Python packages for on-chain interactions.

Features
--------
* Create keypair from Base58-encoded private key or BIP39 mnemonic
* Query SOL balance via ``getBalance`` RPC
* Query SPL token balances via ``getTokenAccountsByOwner`` RPC
* Retrieve all token accounts for the wallet
* Airdrop SOL on devnet for testing

Security
--------
Private keys are **never** logged or exposed. The :attr:`public_key` property
provides the wallet's public address for sharing.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class TokenAccountInfo(BaseModel):
    """Information about a single SPL token account.

    Attributes
    ----------
    address:
        The token account address (Base58).
    mint:
        The SPL token mint address (Base58).
    owner:
        The wallet public key that owns this account.
    amount:
        Raw token amount (as integer, before decimals adjustment).
    decimals:
        Token decimals.
    ui_amount:
        Human-readable token balance (float).
    """

    address: str
    mint: str
    owner: str
    amount: int = 0
    decimals: int = 0
    ui_amount: float = 0.0

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# SolanaWallet
# ---------------------------------------------------------------------------

class SolanaWallet:
    """Solana wallet service for keypair management and balance queries.

    Parameters
    ----------
    private_key_bs58:
        Base58-encoded private key (Ed25519 keypair bytes).
    rpc_url:
        Solana JSON-RPC endpoint URL.
    mnemonic:
        BIP39 mnemonic phrase (alternative to ``private_key_bs58``).
    derivation_path:
        BIP44 derivation path when using mnemonic.
        Defaults to ``m/44'/501'/0'/0'``.

    Raises
    ------
    ValueError
        If neither ``private_key_bs58`` nor ``mnemonic`` is provided.

    Examples
    --------
    .. code-block:: python

        wallet = SolanaWallet(
            private_key_bs58="4zEM...qL3z",
            rpc_url="https://api.mainnet-beta.solana.com",
        )
        balance = await wallet.get_sol_balance()
    """

    def __init__(
        self,
        private_key_bs58: Optional[str] = None,
        rpc_url: str = "https://api.mainnet-beta.solana.com",
        mnemonic: Optional[str] = None,
        derivation_path: str = "m/44'/501'/0'/0'",
    ) -> None:
        self._rpc_url = rpc_url
        self._derivation_path = derivation_path

        # Lazy imports — solana/solders are optional dependencies
        try:
            from solders.keypair import Keypair  # type: ignore[import-untyped]
            from solders.pubkey import Pubkey  # type: ignore[import-untyped]
            self._Keypair = Keypair
            self._Pubkey = Pubkey
        except ImportError as exc:
            raise ImportError(
                "solders package is required for SolanaWallet. "
                "Install with: pip install solders"
            ) from exc

        if private_key_bs58:
            try:
                from solders.keypair import Keypair
                self._keypair = Keypair.from_base58_string(private_key_bs58)
            except Exception as exc:
                raise ValueError(f"Invalid Base58 private key: {exc}") from exc
        elif mnemonic:
            try:
                from solders.keypair import Keypair
                import mnemonic  # type: ignore[import-untyped]
                # Derive keypair from mnemonic using BIP44
                seed = mnemonic.Mnemonic.to_seed(mnemonic)
                self._keypair = Keypair.from_seed_and_derivation_path(
                    seed[:32], derivation_path
                )
            except Exception as exc:
                raise ValueError(f"Invalid mnemonic or derivation: {exc}") from exc
        else:
            raise ValueError("Either private_key_bs58 or mnemonic must be provided")

    # ----- Public properties -----

    @property
    def public_key(self) -> str:
        """The wallet's public key as a Base58 string."""
        return str(self._keypair.pubkey())

    @property
    def keypair(self):
        """The underlying ``solders.Keypair`` instance (use with caution)."""
        return self._keypair

    # ----- SOL Balance -----

    async def get_sol_balance(self) -> float:
        """Query the wallet's SOL balance.

        Returns
        -------
        float
            SOL balance (in SOL, not lamports).

        Raises
        ------
        ConnectionError
            If the RPC endpoint is unreachable.
        """
        try:
            from solana.rpc.async_api import AsyncClient  # type: ignore[import-untyped]

            async with AsyncClient(self._rpc_url) as client:
                pubkey = self._keypair.pubkey()
                resp = await client.get_balance(pubkey)
                if resp.value is not None:
                    return resp.value / 1_000_000_000  # lamports → SOL
                return 0.0
        except ImportError as exc:
            raise ImportError(
                "solana package is required. Install with: pip install solana"
            ) from exc
        except Exception as exc:
            logger.error("Failed to get SOL balance: %s", exc)
            raise ConnectionError(f"RPC error: {exc}") from exc

    # ----- SPL Token Balance -----

    async def get_spl_token_balance(self, mint_address: str) -> float:
        """Query the wallet's balance for a specific SPL token.

        Parameters
        ----------
        mint_address:
            The SPL token mint address (Base58).

        Returns
        -------
        float
            Human-readable token balance, or 0.0 if no account exists.
        """
        token_accounts = await self.get_token_accounts(mint=mint_address)
        if not token_accounts:
            return 0.0
        return token_accounts[0].ui_amount

    # ----- Token Accounts -----

    async def get_token_accounts(
        self,
        mint: Optional[str] = None,
    ) -> List[TokenAccountInfo]:
        """Retrieve SPL token accounts for this wallet.

        Parameters
        ----------
        mint:
            Optional mint address to filter by. If ``None``, returns all
            token accounts.

        Returns
        -------
        list of TokenAccountInfo
            Token account information for each matching account.
        """
        try:
            from solana.rpc.async_api import AsyncClient
            from solana.rpc.commitment import Confirmed  # type: ignore[import-untyped]
            from solders.pubkey import Pubkey

            async with AsyncClient(self._rpc_url) as client:
                opts: Dict = {}
                if mint:
                    opts["mint"] = Pubkey.from_string(mint)

                resp = await client.get_token_accounts_by_owner_json_parsed(
                    self._keypair.pubkey(),
                    opts,
                    commitment=Confirmed,
                )

                accounts: List[TokenAccountInfo] = []
                if resp.value:
                    for acct in resp.value:
                        info = acct.account.data.parsed.get("info", {})
                        token_amount = info.get("tokenAmount", {})
                        accounts.append(
                            TokenAccountInfo(
                                address=str(acct.pubkey),
                                mint=info.get("mint", ""),
                                owner=info.get("owner", ""),
                                amount=int(token_amount.get("amount", 0)),
                                decimals=int(token_amount.get("decimals", 0)),
                                ui_amount=float(token_amount.get("uiAmount", 0.0) or 0.0),
                            )
                        )
                return accounts

        except ImportError as exc:
            raise ImportError(
                "solana package is required. Install with: pip install solana"
            ) from exc
        except Exception as exc:
            logger.error("Failed to get token accounts: %s", exc)
            raise ConnectionError(f"RPC error: {exc}") from exc

    # ----- Airdrop (devnet only) -----

    async def request_airdrop(self, sol: float = 1.0) -> str:
        """Request an airdrop of SOL (devnet/testnet only).

        Parameters
        ----------
        sol:
            Amount of SOL to request.

        Returns
        -------
        str
            Transaction signature.

        Raises
        ------
        RuntimeError
            If the airdrop request fails.
        """
        try:
            from solana.rpc.async_api import AsyncClient

            async with AsyncClient(self._rpc_url) as client:
                lamports = int(sol * 1_000_000_000)
                resp = await client.request_airdrop(
                    self._keypair.pubkey(),
                    lamports,
                )
                if resp.value:
                    return str(resp.value)
                raise RuntimeError("Airdrop returned no signature")
        except ImportError as exc:
            raise ImportError(
                "solana package is required. Install with: pip install solana"
            ) from exc
        except RuntimeError:
            raise
        except Exception as exc:
            logger.error("Airdrop failed: %s", exc)
            raise ConnectionError(f"RPC error: {exc}") from exc

    # ----- Utility -----

    def sign_message(self, message: bytes) -> bytes:
        """Sign a message with the wallet's private key.

        Parameters
        ----------
        message:
            Raw bytes to sign.

        Returns
        -------
        bytes
            The Ed25519 signature.
        """
        return self._keypair.sign_message(message)

    def __repr__(self) -> str:
        return f"SolanaWallet(public_key={self.public_key})"
