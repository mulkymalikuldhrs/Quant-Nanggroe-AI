import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
import httpx
import base64

from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solders.keypair import Keypair as SoldersKeypair
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction
from solders.signature import Signature
from solders.message import Message

from config import SOLANA_RPC_URL, JUPITER_API_BASE_URL
from services.wallet_service import wallet_service
from utils.db import record_trade, save_limit_order, get_pending_limit_orders, update_limit_order_status

logger = logging.getLogger(__name__)

class TradingService:
    """
    Service to handle actual trading operations on the Solana blockchain using Jupiter Aggregator.
    """

    def __init__(self, socketio=None, data_fetcher_service=None):
        self.socketio = socketio
        self.data_fetcher_service = data_fetcher_service
        self._solana_client = None
        self._http_client = None

    @property
    def solana_client(self):
        if self._solana_client is None:
            self._solana_client = AsyncClient(SOLANA_RPC_URL)
        return self._solana_client

    @property
    def http_client(self):
        if self._http_client is None:
            self._http_client = httpx.AsyncClient()
        return self._http_client

    async def _get_jito_tip_estimate(self) -> int:
        """
        Fetches the current JITO tip floor estimate from the Block Engine API.
        Returns the 50th percentile (median) tip in lamports.
        """
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTipFloor",
                "params": []
            }
            # Use the global JITO Block Engine endpoint
            response = await self.http_client.post("https://mainnet.block-engine.jito.wtf/api/v1/bundles", json=payload)
            if response.status_code == 200:
                data = response.json()
                if "result" in data and data["result"]:
                    # Expecting a list of results, take the first one
                    result = data["result"][0]
                    tip_estimate = result.get("ema_landed_50th_percentile", 0)
                    # Convert from float to int lamports if necessary, usually it's already in lamports
                    return int(tip_estimate)
            elif response.status_code == 429:
                logger.warning("JITO Tip Floor API rate limited, using default.")
        except Exception as e:
            logger.error(f"Error fetching JITO tip estimate: {e}")

        # Fallback to 0 if estimate fails
        return 0

    async def _get_token_decimals(self, token_mint_address: str) -> Optional[int]:
        """
        Fetches the decimals for a given token mint address from the Solana blockchain.
        """
        try:
            mint_pubkey = Pubkey.from_string(token_mint_address)
            response = await self.solana_client.get_account_info(mint_pubkey)
            if response.value is None:
                logger.warning(f"Mint account not found for {token_mint_address}")
                return None
            
            # Decode the mint account data (decimals at offset 44)
            data = response.value.data
            if len(data) >= 45:
                return data[44]
            return None
        except Exception as e:
            logger.error(f"Error fetching decimals for {token_mint_address}: {e}")
            return None

    async def _get_swap_instructions(self, input_mint: str, output_mint: str, amount: int, slippage_bps: int, jito_tip: int = 0) -> Optional[Dict]:
        """
        Fetches swap instructions from Jupiter Aggregator.
        amount is in lamports (for SOL) or smallest unit (for tokens).
        slippage_bps is slippage in basis points (e.g., 50 for 0.5%).
        jito_tip is in lamports.
        """
        if not wallet_service.wallet_address:
            logger.error("Wallet address not available for Jupiter swap.")
            return None

        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": amount,
            "slippageBps": slippage_bps,
            "swapMode": "ExactIn",
            "userPublicKey": str(wallet_service.wallet_address),
            "wrapUnwrapSOL": True
        }

        try:
            logger.info(f"Fetching Jupiter swap quote with params: {params}")
            response = await self.http_client.get(f"{JUPITER_API_BASE_URL}/quote", params=params)
            response.raise_for_status()
            quote_data = response.json()

            if not quote_data:
                logger.error(f"No swap quote found from Jupiter: {quote_data}")
                return None

            # Fetch the serialized transaction
            logger.info("Fetching Jupiter swap transaction...")

            # Dynamic JITO tip estimation
            dynamic_tip = await self._get_jito_tip_estimate()

            # Use the max of provided tip and dynamic floor
            effective_tip = max(jito_tip, dynamic_tip)

            # Dynamic prioritization or JITO tip
            priority_fee = "auto"
            if effective_tip > 0:
                priority_fee = effective_tip
                logger.info(f"Using JITO Tip: {effective_tip} lamports (Dynamic Estimate: {dynamic_tip})")

            swap_payload = {
                "quoteResponse": quote_data,
                "userPublicKey": str(wallet_service.wallet_address),
                "wrapAndUnwrapSol": True,
                "prioritizationFeeLamports": priority_fee
            }
            response = await self.http_client.post(f"{JUPITER_API_BASE_URL}/swap", json=swap_payload)
            response.raise_for_status()
            swap_data = response.json()

            if "swapTransaction" not in swap_data:
                logger.error(f"No swap transaction found from Jupiter: {swap_data}")
                return None

            # Include outAmount from quote for tracking
            swap_data["outAmount"] = quote_data.get("outAmount")
            return swap_data

        except httpx.RequestError as e:
            logger.error(f"Error fetching Jupiter swap instructions: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in _get_swap_instructions: {e}")
            return None

    async def execute_buy_order(self, token_address: str, amount_sol: float, slippage: float = 1.0, jito_tip: int = 0) -> Dict:
        """
        Executes a buy order for a given token using SOL via Jupiter Aggregator.
        """
        if not wallet_service.wallet_keypair or not wallet_service.wallet_address:
            return {"success": False, "message": "Wallet not initialized. Cannot execute buy order."}

        logger.info(f"Executing BUY order for {token_address}: {amount_sol} SOL with {slippage}% slippage.")

        try:
            # Fetch current price for recording
            current_price = 0.0
            if self.data_fetcher_service:
                token_data = await self.data_fetcher_service.get_token_by_address(token_address)
                if token_data:
                    current_price = token_data.get('price', 0.0)

            amount_lamports = int(amount_sol * 10**9)
            slippage_bps = int(slippage * 100)

            swap_data = await self._get_swap_instructions(
                input_mint="So11111111111111111111111111111111111111112",
                output_mint=token_address,
                amount=amount_lamports,
                slippage_bps=slippage_bps,
                jito_tip=jito_tip
            )

            if not swap_data:
                return {"success": False, "message": "Failed to get swap instructions from Jupiter."}

            serialized_transaction = base64.b64decode(swap_data["swapTransaction"])
            transaction = VersionedTransaction.from_bytes(serialized_transaction)
            signed_transaction = transaction.sign([wallet_service.wallet_keypair])

            response = await self.solana_client.send_raw_transaction(bytes(signed_transaction))
            tx_signature = response.value
            logger.info(f"Transaction sent: {tx_signature}")

            # Confirm transaction
            confirmed = await self._confirm_transaction(tx_signature)
            if not confirmed:
                logger.warning(f"Transaction not confirmed after timeout: {tx_signature}")

            transaction_id = str(tx_signature)
            trade_data = {
                "type": "buy",
                "token_address": token_address,
                "amount_sol": amount_sol,
                "price_usd": current_price,
                "slippage": slippage,
                "transaction_id": transaction_id,
                "status": "confirmed" if confirmed else "pending",
                "timestamp": datetime.now().isoformat()
            }
            # Enrich with token symbol from data fetcher if available
            if self.data_fetcher_service:
                try:
                    token_info = await self.data_fetcher_service.get_token_by_address(token_address)
                    if token_info:
                        trade_data["token_symbol"] = token_info.get('symbol', 'UNKNOWN')
                except Exception:
                    pass
            if self.socketio:
                self.socketio.emit('trade_executed', trade_data)

            # Record trade in DB
            await asyncio.to_thread(record_trade, trade_data)

            return {"success": True, "message": f"Successfully bought {amount_sol} SOL worth of {token_address}", "transaction_id": transaction_id, "token_address": token_address, "amount_sol": amount_sol, "slippage": slippage, "status": "confirmed" if confirmed else "pending", "price_usd": current_price}

        except Exception as e:
            logger.error(f"Error executing buy order: {str(e)}")
            return {"success": False, "message": f"Failed to execute buy order: {str(e)}", "token_address": token_address, "amount_sol": amount_sol, "slippage": slippage, "status": "failed"}

    async def execute_sell_order(self, token_address: str, amount_tokens: float, slippage: float = 1.0, jito_tip: int = 0) -> Dict:
        """
        Executes a sell order for a given token to SOL via Jupiter Aggregator.
        """
        if not wallet_service.wallet_keypair or not wallet_service.wallet_address:
            return {"success": False, "message": "Wallet not initialized. Cannot execute sell order."}

        logger.info(f"Executing SELL order for {token_address}: {amount_tokens} tokens with {slippage}% slippage.")

        try:
            # Fetch current price for recording
            current_price = 0.0
            if self.data_fetcher_service:
                token_data = await self.data_fetcher_service.get_token_by_address(token_address)
                if token_data:
                    current_price = token_data.get('price', 0.0)

            token_decimals = await self._get_token_decimals(token_address)
            if token_decimals is None:
                return {"success": False, "message": f"Could not determine decimals for token {token_address}."}

            amount_smallest_unit = int(amount_tokens * (10**token_decimals))
            slippage_bps = int(slippage * 100)

            swap_data = await self._get_swap_instructions(
                input_mint=token_address,
                output_mint="So11111111111111111111111111111111111111112",
                amount=amount_smallest_unit,
                slippage_bps=slippage_bps,
                jito_tip=jito_tip
            )

            if not swap_data:
                return {"success": False, "message": "Failed to get swap instructions from Jupiter."}

            serialized_transaction = base64.b64decode(swap_data["swapTransaction"])
            transaction = VersionedTransaction.from_bytes(serialized_transaction)
            signed_transaction = transaction.sign([wallet_service.wallet_keypair])

            response = await self.solana_client.send_raw_transaction(bytes(signed_transaction))
            tx_signature = response.value
            logger.info(f"Transaction sent: {tx_signature}")

            confirmed = await self._confirm_transaction(tx_signature)
            if not confirmed:
                logger.warning(f"Transaction not confirmed after timeout: {tx_signature}")

            # Extract proceeds in SOL from swap data
            out_amount_lamports = int(swap_data.get("outAmount", 0))
            amount_sol = out_amount_lamports / 10**9

            transaction_id = str(tx_signature)
            trade_data = {
                "type": "sell",
                "token_address": token_address,
                "amount_tokens": amount_tokens,
                "amount_sol": amount_sol,
                "price_usd": current_price,
                "slippage": slippage,
                "transaction_id": transaction_id,
                "status": "confirmed" if confirmed else "pending",
                "timestamp": datetime.now().isoformat()
            }
            # Enrich with token symbol from data fetcher if available
            if self.data_fetcher_service:
                try:
                    token_info = await self.data_fetcher_service.get_token_by_address(token_address)
                    if token_info:
                        trade_data["token_symbol"] = token_info.get('symbol', 'UNKNOWN')
                except Exception:
                    pass
            if self.socketio:
                self.socketio.emit('trade_executed', trade_data)

            # Record trade in DB
            await asyncio.to_thread(record_trade, trade_data)

            return {"success": True, "message": f"Successfully sold {amount_tokens} tokens", "transaction_id": transaction_id, "token_address": token_address, "amount_tokens": amount_tokens, "slippage": slippage, "status": "confirmed" if confirmed else "pending", "price_usd": current_price}

        except Exception as e:
            logger.error(f"Error executing sell order: {str(e)}")
            return {"success": False, "message": f"Failed to execute sell order: {str(e)}", "token_address": token_address, "amount_tokens": amount_tokens, "slippage": slippage, "status": "failed"}

    async def _confirm_transaction(self, signature: Signature, timeout: int = 60) -> bool:
        """
        Polls for transaction confirmation with exponential backoff.
        """
        start_time = datetime.now().timestamp()
        retry_interval = 2.0
        while (datetime.now().timestamp() - start_time) < timeout:
            try:
                response = await self.solana_client.get_signature_statuses([signature])
                if response.value and response.value[0]:
                    status = response.value[0]
                    if status.err:
                        logger.error(f"Transaction failed: {status.err}")
                        return False
                    if status.confirmation_status in ['confirmed', 'finalized']:
                        return True
            except Exception as e:
                logger.debug(f"Error polling signature status: {e}")

            await asyncio.sleep(retry_interval)
            retry_interval = min(retry_interval * 1.2, 10.0) # Adaptive polling
        return False

    async def place_limit_order(self, token_address: str, target_price: float, amount_sol: float, side: str = 'buy', token_symbol: str = None) -> Dict:
        """
        Places a limit order that will be executed when the price target is reached.
        """
        order_data = {
            "token_address": token_address,
            "token_symbol": token_symbol,
            "target_price": target_price,
            "amount_sol": amount_sol,
            "side": side,
            "status": "pending"
        }
        await asyncio.to_thread(save_limit_order, order_data)
        logger.info(f"Limit order placed: {side} {token_address} at {target_price}")
        return {"success": True, "message": f"Limit {side} order placed for {token_symbol or token_address} at {target_price}"}

    async def check_and_execute_limit_orders(self):
        """
        Checks all pending limit orders and executes them if price targets are met.
        """
        pending_orders = await asyncio.to_thread(get_pending_limit_orders)
        for order in pending_orders:
            try:
                token_data = await self.data_fetcher_service.get_token_by_address(order['token_address'])
                if not token_data:
                    continue

                current_price = token_data['price']
                target_price = order['target_price']
                side = order['side']

                should_execute = False
                if side == 'buy' and current_price <= target_price:
                    should_execute = True
                elif side == 'sell' and current_price >= target_price:
                    should_execute = True

                if should_execute:
                    logger.info(f"Executing limit {side} order for {order['token_address']} at {current_price}")
                    if side == 'buy':
                        result = await self.execute_buy_order(order['token_address'], order['amount_sol'])
                    else:
                        # For sell, we need to know amount of tokens.
                        # Simple implementation: sell all tokens of this type.
                        balance = await wallet_service.get_token_balance(order['token_address'])
                        if balance > 0:
                            result = await self.execute_sell_order(order['token_address'], balance)
                        else:
                            result = {"success": False, "message": "No tokens to sell"}

                    if result.get("success"):
                        await asyncio.to_thread(update_limit_order_status, order['id'], 'executed')
                        if self.socketio:
                            self.socketio.emit('limit_order_executed', {**order, "execution_price": current_price})
                    else:
                        logger.error(f"Failed to execute limit order {order['id']}: {result.get('message')}")

            except Exception as e:
                logger.error(f"Error checking limit order {order['id']}: {e}")

# Create a singleton instance
trading_service = TradingService()
