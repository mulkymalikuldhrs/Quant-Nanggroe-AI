import logging
import asyncio
import json
from datetime import datetime
import base58
from typing import Dict, Optional, List
from solana.rpc.websocket_api import connect
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Commitment, Confirmed
from solana.rpc.core import RPCException
from solders.rpc.config import RpcTransactionLogsFilterMentions
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.transaction import Transaction as SoldersTransaction
from solders.instruction import CompiledInstruction
from solders.message import Message
from solders.system_program import ID as SYSTEM_PROGRAM_ID

from config import SOLANA_RPC_URL, SOLANA_WS_URL

TOKEN_PROGRAM_ID = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5mW")

logger = logging.getLogger(__name__)

PUMP_FUN_PROGRAM_ID = "6EF8rrecthR5DkZJv9RKzyAXYVqBCTs2Fmb7sK559pwt"
RAYDIUM_LIQUIDITY_POOL_V4_ID = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"

class MempoolMonitorService:
    """
    Service to monitor the Solana mempool for new token launches and potential rugpulls.
    Connects to a Solana RPC WebSocket to listen for new transactions.
    """

    def __init__(self, socketio=None, data_fetcher_service=None):
        self.socketio = socketio
        self.data_fetcher_service = data_fetcher_service
        self._solana_client = None
        self.monitoring_task = None
        self.is_running = False
        self.rugpull_callbacks = []
        self.new_token_callbacks = []
        self._token_buffer = []
        self._buffer_lock = asyncio.Lock()

    def on_rugpull(self, callback):
        self.rugpull_callbacks.append(callback)

    def on_new_token(self, callback):
        self.new_token_callbacks.append(callback)

    @property
    def solana_client(self):
        if self._solana_client is None:
            self._solana_client = AsyncClient(SOLANA_RPC_URL)
        return self._solana_client

    async def _monitor_transactions(self):
        """
        Monitors new transactions on the Solana network for new token launches and potential rugpulls.
        Uses a reconnection loop with exponential backoff.
        """
        retry_delay = 1
        max_retry_delay = 30 # Slightly more aggressive for production

        while self.is_running:
            try:
                async with connect(SOLANA_WS_URL) as ws:
                    logger.info(f"Connected to Solana WebSocket: {SOLANA_WS_URL}")
                    retry_delay = 1

                    # Filter for Pump.fun logs
                    await ws.logs_subscribe(
                        filter_=RpcTransactionLogsFilterMentions(Pubkey.from_string(PUMP_FUN_PROGRAM_ID)),
                        commitment=Commitment('processed')
                    )
                    logger.info("Subscribed to Pump.fun logs.")

                    # Filter for Raydium logs
                    await ws.logs_subscribe(
                        filter_=RpcTransactionLogsFilterMentions(Pubkey.from_string(RAYDIUM_LIQUIDITY_POOL_V4_ID)),
                        commitment=Commitment('processed')
                    )
                    logger.info("Subscribed to Raydium logs.")

                    # Also filter for general SPL Token events if needed, but the above are high priority
                    await ws.logs_subscribe(
                        filter_=RpcTransactionLogsFilterMentions(TOKEN_PROGRAM_ID),
                        commitment=Commitment('processed')
                    )
                    logger.info("Subscribed to SPL Token logs.")

                    async for msg in ws:
                        if not self.is_running:
                            break

                        # Handle message formats
                        for event in (msg if isinstance(msg, list) else [msg]):
                            try:
                                if hasattr(event, 'result') and event.result:
                                    value = event.result.value
                                    signature = str(value.signature)
                                    logs = value.logs
                                    await self._process_mempool_event(signature, logs)
                                elif isinstance(event, dict) and 'params' in event:
                                    result = event['params']['result']['value']
                                    signature = result['signature']
                                    logs = result['logs']
                                    await self._process_mempool_event(signature, logs)
                            except (AttributeError, KeyError, TypeError) as e:
                                continue

            except RPCException as e:
                if self.is_running:
                    logger.error(f"RPC WebSocket error: {e}. Retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, max_retry_delay)
                else:
                    break
            except Exception as e:
                if self.is_running:
                    logger.error(f"Unexpected WebSocket connection error: {e}. Retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, max_retry_delay)
                else:
                    break

    async def _get_sol_transfer_amount(self, transaction_data) -> float:
        """
        Calculates the total SOL transfer amount from a transaction.
        """
        total_sol_transfer = 0

        # Determine if we're dealing with a VersionedTransactionResponse or raw transaction data
        meta = None
        if hasattr(transaction_data, 'meta'):
            meta = transaction_data.meta
        elif isinstance(transaction_data, dict) and 'meta' in transaction_data:
            meta = transaction_data['meta']

        if meta:
            pre_balances = getattr(meta, 'pre_balances', [])
            post_balances = getattr(meta, 'post_balances', [])

            if not pre_balances and isinstance(meta, dict):
                pre_balances = meta.get('preBalances', [])
                post_balances = meta.get('postBalances', [])

            if pre_balances and post_balances and len(pre_balances) == len(post_balances):
                for i in range(len(pre_balances)):
                    total_sol_transfer += abs(post_balances[i] - pre_balances[i])

        return total_sol_transfer / 1e9 # Convert lamports to SOL

    async def _process_mempool_event(self, signature: str, logs: list):
        # Optimized filtering based on log content
        is_new_token = False

        # Filter by SOL transfer amount if possible (optional but recommended for noise reduction)
        try:
            sig = Signature.from_string(signature)
            tx_resp = await self.solana_client.get_transaction(
                sig,
                encoding="jsonParsed",
                max_supported_transaction_version=0
            )
            if tx_resp and tx_resp.value:
                sol_amount = await self._get_sol_transfer_amount(tx_resp.value.transaction)
                if sol_amount < 0.1:
                    logger.debug(f"Ignoring transaction {signature} with small SOL transfer: {sol_amount} SOL")
                    return
        except Exception as e:
            logger.warning(f"Could not fetch transaction for pre-filtering: {e}")

        # Pump.fun specific: 'Program log: Instruction: Create'
        if any("Instruction: Create" in log for log in logs) and any(PUMP_FUN_PROGRAM_ID in log for log in logs):
            is_new_token = True

        # Raydium specific: 'Program log: Instruction: Initialize2'
        elif any("Instruction: Initialize2" in log for log in logs) and any(RAYDIUM_LIQUIDITY_POOL_V4_ID in log for log in logs):
            is_new_token = True

        # Standard SPL Token: 'Program log: Instruction: InitializeMint'
        elif any("initializeMint" in log.lower() for log in logs):
            is_new_token = True

        if is_new_token:
            logger.info(f"Potential new token/pool transaction detected: {signature}")
            # Run in background to not block the listener
            asyncio.create_task(self._process_new_token_transaction(signature))

        # Check for rugpull indicators
        await self._process_rugpull_indicators(signature, logs)

    async def _process_new_token_transaction(self, signature: str):
        """
        Fetches and processes transaction details to identify new token mints.
        """
        try:
            sig = Signature.from_string(signature)
            response = await self.solana_client.get_transaction(
                sig,
                encoding="jsonParsed",
                commitment=Confirmed,
                max_supported_transaction_version=0
            )
            
            if not response or not response.value:
                return

            transaction_data = response.value.transaction
            if not transaction_data or not transaction_data.meta:
                return

            # Extract deployer (first signer)
            deployer = None
            account_keys = transaction_data.transaction.message.account_keys
            if account_keys and len(account_keys) > 0:
                first_acc = account_keys[0]
                deployer = first_acc.get('pubkey') if isinstance(first_acc, dict) else str(first_acc)

            # Look for new mints in instructions
            for instruction in transaction_data.transaction.message.instructions:
                program_id = str(instruction.program_id)

                if program_id == str(TOKEN_PROGRAM_ID):
                    # Handle parsed instructions (jsonParsed)
                    if hasattr(instruction, 'parsed') and isinstance(instruction.parsed, dict):
                        if instruction.parsed.get('type') in ['initializeMint', 'initializeMint2']:
                            mint = instruction.parsed['info']['mint']
                            await self._emit_new_token(mint, deployer)
                            return

                    # Handle unparsed CompiledInstruction
                    elif hasattr(instruction, 'data') and hasattr(instruction, 'accounts'):
                        data = instruction.data
                        if isinstance(data, str):
                            data = base58.b58decode(data)

                        # SPL Token initializeMint is 0, initializeMint2 is 20
                        if data and data[0] in [0, 20]:
                            if len(instruction.accounts) > 0:
                                mint_index = instruction.accounts[0]
                                mint_pubkey = transaction_data.transaction.message.account_keys[mint_index]
                                await self._emit_new_token(str(mint_pubkey), deployer)
                                return

                elif program_id == PUMP_FUN_PROGRAM_ID:
                    # For Pump.fun 'Create' instruction, the mint is the first account
                    if hasattr(instruction, 'accounts') and len(instruction.accounts) >= 1:
                        mint_index = instruction.accounts[0]
                        account_keys_list = transaction_data.transaction.message.account_keys
                        mint_pubkey = account_keys_list[mint_index]
                        mint_str = str(mint_pubkey.pubkey) if hasattr(mint_pubkey, 'pubkey') else str(mint_pubkey)
                        await self._emit_new_token(mint_str, deployer)
                        return

                elif program_id == RAYDIUM_LIQUIDITY_POOL_V4_ID:
                    # Raydium 'Initialize2' usually has mints at index 8 and 9 in accounts
                    if hasattr(instruction, 'accounts') and len(instruction.accounts) >= 10:
                        account_keys_list = transaction_data.transaction.message.account_keys
                        for idx in [8, 9]:
                            mint_index = instruction.accounts[idx]
                            mint_pubkey = account_keys_list[mint_index]
                            mint_str = str(mint_pubkey.pubkey) if hasattr(mint_pubkey, 'pubkey') else str(mint_pubkey)
                            # Exclude WSOL
                            if mint_str != "So11111111111111111111111111111111111111112":
                                await self._emit_new_token(mint_str, deployer)
                                return

        except Exception as tx_e:
            logger.error(f"Error processing new token transaction {signature}: {tx_e}")

    async def _emit_new_token(self, mint_address: str, deployer: Optional[str] = None):
        logger.info(f"Confirmed new token mint: {mint_address} (Deployer: {deployer})")
        token_details = None
        if self.data_fetcher_service:
            token_details = await self.data_fetcher_service.get_token_by_address(mint_address)

        if not token_details:
            token_details = {
                'address': mint_address,
                'symbol': 'NEW',
                'name': 'New Token',
                'price': 0,
                'liquidity': 0,
                'age_hours': 0,
                'timestamp': datetime.now().isoformat()
            }

        if deployer:
            token_details['deployer'] = deployer

        async with self._buffer_lock:
            self._token_buffer.append(token_details)
            if len(self._token_buffer) > 100:
                self._token_buffer.pop(0)

        if self.socketio:
            self.socketio.emit('new_token', token_details)

        for callback in self.new_token_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(token_details))
                else:
                    callback(token_details)
            except Exception as e:
                logger.error(f"Error in new token callback: {e}")

    async def _process_rugpull_indicators(self, signature: str, logs: list):
        """
        Analyzes transaction logs for potential rugpull indicators.
        """
        for log in logs:
            reason = None
            if "withdraw liquidity" in log.lower():
                reason = "Liquidity Withdrawal"
            elif "burn" in log.lower() and "mint" not in log.lower():
                reason = "Token Burn"
            elif "close account" in log.lower():
                reason = "Account Closed"

            if reason:
                logger.warning(f"Potential rugpull indicator: {reason} in {signature}")
                alert_data = {
                    'signature': signature,
                    'reason': reason,
                    'log_message': log
                }
                if self.socketio:
                    self.socketio.emit('rugpull_alert', alert_data)

                for callback in self.rugpull_callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            asyncio.create_task(callback(alert_data))
                        else:
                            callback(alert_data)
                    except Exception as e:
                        logger.error(f"Error in rugpull callback: {e}")
                return

    async def start_monitoring(self):
        """
        Starts the background task for mempool monitoring.
        """
        if self.monitoring_task and not self.monitoring_task.done():
            logger.info("Mempool monitoring already running.")
            return

        # Trigger client initialization via property
        _ = self.solana_client

        self.is_running = True
        logger.info("Starting mempool monitoring task.")
        self.monitoring_task = asyncio.create_task(self._monitor_transactions())

    async def stop_monitoring(self):
        """
        Stops the background task for mempool monitoring.
        """
        self.is_running = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            finally:
                self.monitoring_task = None
        logger.info("Mempool monitoring stopped.")

    async def monitor_new_tokens(self) -> Optional[Dict]:
        """
        Synchronous-style polling method for compatibility with REST routes.
        Returns the last detected token if any.
        """
        async with self._buffer_lock:
            if self._token_buffer:
                return self._token_buffer[-1]
        return None

# Create a singleton instance
mempool_monitor_service = MempoolMonitorService()
