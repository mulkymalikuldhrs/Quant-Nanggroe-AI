import logging
import os
from typing import Dict, Any, Optional, List
from solana.rpc.async_api import AsyncClient
from solana.rpc.types import TokenAccountOpts
from solders.pubkey import Pubkey
from solders.keypair import Keypair as SoldersKeypair
import base58
import asyncio
from datetime import datetime
import httpx

from config import SOLANA_PRIVATE_KEY, SOLANA_RPC_URL

logger = logging.getLogger(__name__)

class WalletService:
    """
    Service to handle actual Solana wallet management using a private key.
    """

    def __init__(self, socketio=None, data_fetcher_service=None):
        self.socketio = socketio
        self.data_fetcher_service = data_fetcher_service
        self._solana_client = None
        self._http_client = None
        self.wallet_keypair: Optional[SoldersKeypair] = None
        self.wallet_address: Optional[Pubkey] = None
        self.token_decimals_cache = {}
        self.token_metadata_cache = {}
        self._initialize_wallet()

    @property
    def solana_client(self):
        if self._solana_client is None:
            self._solana_client = AsyncClient(SOLANA_RPC_URL)
        return self._solana_client

    @property
    def http_client(self):
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=10.0)
        return self._http_client

    def _initialize_wallet(self):
        if not SOLANA_PRIVATE_KEY:
            logger.error("SOLANA_PRIVATE_KEY environment variable not set. Wallet service will not function.")
            return

        try:
            private_key_bytes = base58.b58decode(SOLANA_PRIVATE_KEY)
            self.wallet_keypair = SoldersKeypair.from_bytes(private_key_bytes)
            self.wallet_address = self.wallet_keypair.pubkey()
            logger.info(f"Wallet initialized with address: {self.wallet_address}")
        except Exception as e:
            logger.error(f"Error initializing wallet from private key: {e}")
            self.wallet_keypair = None
            self.wallet_address = None

    async def _get_token_decimals(self, mint_address: str) -> int:
        """Fetch and cache token decimals."""
        if mint_address in self.token_decimals_cache:
            return self.token_decimals_cache[mint_address]

        try:
            mint_pubkey = Pubkey.from_string(mint_address)
            response = await self.solana_client.get_account_info(mint_pubkey)
            if response and response.value:
                data = response.value.data
                if len(data) >= 45:
                    decimals = data[44]
                    self.token_decimals_cache[mint_address] = decimals
                    return decimals
        except Exception as e:
            logger.error(f"Error fetching decimals for {mint_address}: {e}")

        return 9 # Fallback

    async def get_wallet_info(self) -> Optional[Dict]:
        """
        Retrieves information about the initialized wallet.
        """
        if not self.wallet_address:
            logger.warning("Wallet not initialized. Cannot fetch wallet info.")
            return None

        try:
            balance_response = await self.solana_client.get_balance(self.wallet_address)
            sol_balance = balance_response.value / 10**9

            token_accounts_response = await self.solana_client.get_token_accounts_by_owner(
                self.wallet_address,
                TokenAccountOpts(program_id=Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5mW")),
            )
            tokens = []
            for account_info in token_accounts_response.value:
                pubkey = account_info.pubkey
                try:
                    data = account_info.account.data
                    mint = str(Pubkey.from_bytes(data[0:32]))
                    amount_raw = int.from_bytes(data[64:72], "little")

                    if amount_raw == 0:
                        continue

                    decimals = await self._get_token_decimals(mint)
                    amount = amount_raw / (10 ** decimals)
 
                    token_info = {
                        "account_address": str(pubkey),
                        "mint_address": mint,
                        "balance_raw": amount_raw,
                        "balance": amount,
                        "decimals": decimals,
                        "symbol": "TOKEN",
                        "name": "Unknown Token",
                        "usd_value": 0.0
                    }

                    # Enrich with metadata if available
                    if self.data_fetcher_service:
                        cached_meta = self.token_metadata_cache.get(mint)
                        if cached_meta:
                            token_info.update(cached_meta)
                        else:
                            # Try to fetch from data_fetcher (could be slow, but we'll try)
                            meta = await self.data_fetcher_service.get_token_by_address(mint)
                            if meta:
                                meta_data = {"symbol": meta.get('symbol', 'TOKEN'), "name": meta.get('name', 'Unknown')}
                                token_info.update(meta_data)
                                self.token_metadata_cache[mint] = meta_data

                    tokens.append(token_info)
                except Exception as e:
                    logger.warning(f"Could not parse token account {pubkey}: {e}")

            # Fetch real SOL and token prices from Jupiter
            sol_price = 0.0
            mints = ["So11111111111111111111111111111111111111112"] + [t['mint_address'] for t in tokens]

            try:
                # Jupiter Price API v2 supports bulk lookups
                price_response = await self.http_client.get(f"https://api.jup.ag/price/v2?ids={','.join(mints)}")
                if price_response.status_code == 200:
                    price_data = price_response.json().get('data', {})

                    sol_price_info = price_data.get('So11111111111111111111111111111111111111112')
                    if sol_price_info:
                        sol_price = float(sol_price_info['price'])

                    for token in tokens:
                        token_price_info = price_data.get(token['mint_address'])
                        if token_price_info:
                            token['price_usd'] = float(token_price_info['price'])
                            token['usd_value'] = token['balance'] * token['price_usd']
            except Exception as pe:
                logger.error(f"Error fetching prices: {pe}")

            usd_value = sol_balance * sol_price
            total_value_usd = usd_value + sum(t.get("usd_value", 0.0) for t in tokens)

            wallet_info = {
                "address": str(self.wallet_address),
                "sol_balance": sol_balance,
                "sol_price": sol_price,
                "usd_value": usd_value,
                "tokens": tokens,
                "total_value_usd": total_value_usd,
                "last_updated": datetime.now().isoformat()
            }
            return wallet_info
        except Exception as e:
            logger.error(f"Error fetching wallet info for {self.wallet_address}: {e}")
            return None

    async def get_wallet_balance(self) -> Dict:
        """
        Gets the balance of the initialized wallet.
        """
        wallet_info = await self.get_wallet_info()
        if wallet_info:
            return {
                'address': wallet_info['address'],
                'sol_balance': wallet_info['sol_balance'],
                'usd_value': wallet_info['usd_value'],
                'tokens': wallet_info['tokens'],
                'total_value_usd': wallet_info['total_value_usd'],
                'last_updated': wallet_info['last_updated']
            }
        return {'address': str(self.wallet_address) if self.wallet_address else None, 'sol_balance': 0, 'usd_value': 0, 'tokens': [], 'total_value_usd': 0, 'last_updated': datetime.now().isoformat()}

    async def get_token_balance(self, mint_address: str) -> float:
        """
        Retrieves the human-readable balance for a specific token mint address.
        """
        if not self.wallet_address:
            return 0.0

        try:
            opts = TokenAccountOpts(mint=Pubkey.from_string(mint_address))
            response = await self.solana_client.get_token_accounts_by_owner(self.wallet_address, opts)

            if not response.value:
                return 0.0

            total_balance_raw = 0
            for account_info in response.value:
                 data = account_info.account.data
                 amount_raw = int.from_bytes(data[64:72], "little")
                 total_balance_raw += amount_raw

            if total_balance_raw == 0:
                return 0.0

            decimals = await self._get_token_decimals(mint_address)
            return total_balance_raw / (10 ** decimals)
        except Exception as e:
            logger.error(f"Error fetching token balance for {mint_address}: {e}")
            return 0.0

# Create a singleton instance
wallet_service = WalletService()
