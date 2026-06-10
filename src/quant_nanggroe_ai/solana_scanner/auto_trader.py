import logging
import asyncio
import httpx
from typing import Dict, Any, List
from datetime import datetime
import json
import os
from utils.db import save_position, remove_position, get_active_positions, increment_rugs_avoided

logger = logging.getLogger(__name__)

CONFIG_FILE = 'auto_trader_config.json'

class AutoTraderService:
    """
    Service for automated memecoin trading.
    """

    def __init__(self, socketio=None, data_fetcher_service=None, ai_analysis_service=None, trading_service=None, wallet_service=None):
        self.socketio = socketio
        self.data_fetcher_service = data_fetcher_service
        self.ai_analysis_service = ai_analysis_service
        self.trading_service = trading_service
        self.wallet_service = wallet_service
        self.trading_enabled = False
        self.scan_interval_seconds = 60
        self.trade_loop_task = None
        self.background_loop = None
        self.owned_tokens: Dict[str, Dict] = {}
        self.config = self._load_config()
        self._http_client = None

    @property
    def http_client(self):
        if self._http_client is None:
            self._http_client = httpx.AsyncClient()
        return self._http_client

    def set_loop(self, loop):
        self.background_loop = loop

    def post_init(self):
        """Called after all dependencies are injected."""
        # Load active positions from database
        db_positions = get_active_positions()
        self.owned_tokens = {p['token_address']: p for p in db_positions}
        logger.info(f"Loaded {len(self.owned_tokens)} active positions from DB.")

    def _load_config(self) -> Dict:
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading config: {e}")
        
        return {
            "min_liquidity": 5000,
            "max_liquidity": 50000,
            "max_age_hours": 12,
            "min_volume_24h": 10000,
            "min_ai_probability_score": 75,
            "buy_amount_sol": 0.05,
            "slippage": 1.5,
            "take_profit_tiers": [
                {"target_x": 1.5, "sell_percentage": 0.5},
                {"target_x": 2.0, "sell_percentage": 1.0}
            ],
            "stop_loss_percentage": 0.15,
            "trailing_stop_loss_percentage": 0.10,
            "max_risk_score": 40,
            "rugcheck_max_score": 5000,
            "use_vwap_filter": True,
            "jito_tip_sol": 0.001,
            "snipe_only_mode": False,
            "whitelisted_deployers": []
        }

    def _save_config(self):
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving config: {e}")

    def update_config(self, new_config: Dict):
        self.config.update(new_config)
        self._save_config()

    def get_config(self) -> Dict:
        return self.config

    def start_trading(self):
        if not self.trading_enabled:
            self.trading_enabled = True

            if self.background_loop and self.background_loop.is_running():
                self.trade_loop_task = asyncio.run_coroutine_threadsafe(self._trade_loop(), self.background_loop)
            else:
                self.trade_loop_task = asyncio.create_task(self._trade_loop())

            if self.socketio:
                self.socketio.emit('trading_status', {'enabled': True, 'message': 'Automated trading started.'})

    def stop_trading(self):
        if self.trading_enabled:
            self.trading_enabled = False
            if self.trade_loop_task:
                try:
                    self.trade_loop_task.cancel()
                    logger.info("AutoTrader: Cancelled trade loop task.")
                except Exception as e:
                    logger.error(f"AutoTrader: Error cancelling trade loop task: {e}")
                self.trade_loop_task = None
            if self.socketio:
                self.socketio.emit('trading_status', {'enabled': False, 'message': 'Automated trading stopped.'})

    async def _trade_loop(self):
        try:
            while self.trading_enabled:
                try:
                    await self._scan_and_buy()
                    await self._monitor_and_sell()
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error(f"AutoTrader: Error in trade loop: {e}")
                await asyncio.sleep(self.scan_interval_seconds)
        except asyncio.CancelledError:
            logger.info("AutoTrader: Trade loop task cancelled.")
        finally:
            self.trading_enabled = False

    async def _scan_and_buy(self):
        logger.info("AutoTrader: Scanning for new tokens...")
        try:
            all_tokens = await self.data_fetcher_service.get_all_tokens()
            
            # Robust defaults for filtering if missing from config
            min_liq = self.config.get("min_liquidity", 5000)
            max_liq = self.config.get("max_liquidity", float('inf'))
            max_age = self.config.get("max_age_hours", 24)

            for token in all_tokens:
                liquidity = token.get('liquidity', 0)
                age = token.get('age_hours', 0)

                if (liquidity < min_liq or liquidity > max_liq or age > max_age):
                    logger.debug(f"AutoTrader: Skipping {token.get('symbol')} - Liq: {liquidity}, Age: {age}")
                    continue

                if token['address'] in self.owned_tokens:
                    continue

                await self._analyze_and_buy(token)

        except Exception as e:
            logger.error(f"AutoTrader: Error during scan and buy: {e}")

    async def _monitor_and_sell(self):
        tokens_to_remove = []
        for token_address, details in self.owned_tokens.items():
            try:
                # Real balance check
                current_balance = await self.wallet_service.get_token_balance(token_address)
                if current_balance <= 0:
                    tokens_to_remove.append(token_address)
                    continue

                # Sync balance if it changed
                if abs(current_balance - details.get('amount_tokens', 0)) > 0.000001:
                    details['amount_tokens'] = current_balance
                    await asyncio.to_thread(save_position, details)

                current_token_data = await self.data_fetcher_service.get_token_by_address(token_address)
                if not current_token_data: continue

                current_price = current_token_data['price']
                buy_price = details['buy_price']

                # Update highest price for trailing stop-loss
                if current_price > details.get('highest_price', 0):
                    details['highest_price'] = current_price
                    await asyncio.to_thread(save_position, details)
                    logger.info(f"AutoTrader: New highest price for {details['token_symbol']}: {current_price}")

                should_sell = False
                sell_amount = 0
                reason = ""

                # 1. Check Multiple Take-Profit Tiers
                tp_tiers = self.config.get("take_profit_tiers", [])
                hit_tiers = details.get('metadata', {}).get('hit_tp_tiers', [])

                for tier in tp_tiers:
                    target_x = tier['target_x']
                    if target_x not in hit_tiers and current_price >= buy_price * target_x:
                        should_sell = True
                        reason = f"take_profit_{target_x}x"

                        # Calculate how much of the INITIAL position to sell
                        # For simplicity, we sell the percentage of CURRENT balance if it's the last tier,
                        # otherwise we sell the specified percentage of the INITIAL balance.
                        initial_amount = details.get('initial_amount_tokens', details['amount_tokens'])
                        sell_percentage = tier['sell_percentage']

                        if sell_percentage >= 1.0:
                            sell_amount = current_balance
                        else:
                            sell_amount = initial_amount * sell_percentage
                            # Ensure we don't try to sell more than we have
                            sell_amount = min(sell_amount, current_balance)

                        hit_tiers.append(target_x)
                        if 'metadata' not in details: details['metadata'] = {}
                        details['metadata']['hit_tp_tiers'] = hit_tiers
                        break # Only process one tier at a time per loop

                # 2. Check Trailing Stop-Loss
                if not should_sell:
                    tsl_threshold = details.get('highest_price', current_price) * (1 - self.config.get("trailing_stop_loss_percentage", 0.10))
                    if current_price <= tsl_threshold:
                        should_sell = True
                        sell_amount = current_balance
                        reason = "trailing_stop_loss"

                # 3. Check Fixed Stop-Loss
                if not should_sell:
                    sl_threshold = buy_price * (1 - self.config["stop_loss_percentage"])
                    if current_price <= sl_threshold:
                        should_sell = True
                        sell_amount = current_balance
                        reason = "stop_loss"

                if should_sell and sell_amount > 0:
                    jito_tip_lamports = int(self.config.get("jito_tip_sol", 0.001) * 10**9)
                    sell_result = await self.trading_service.execute_sell_order(
                        token_address=token_address,
                        amount_tokens=sell_amount,
                        slippage=self.config["slippage"],
                        jito_tip=jito_tip_lamports
                    )
                    if sell_result.get("success"):
                        # If we sold everything, mark for removal
                        if sell_amount >= current_balance * 0.99: # Account for precision
                            tokens_to_remove.append(token_address)
                        else:
                            # Update remaining position
                            details['amount_tokens'] = current_balance - sell_amount
                            await asyncio.to_thread(save_position, details)

                        if self.socketio:
                            self.socketio.emit('auto_trade_event', {
                                'type': 'sell',
                                'token': details['token_symbol'],
                                'reason': reason,
                                'status': 'success',
                                'amount': sell_amount
                            })

            except Exception as e:
                logger.error(f"AutoTrader: Error monitoring {token_address}: {e}")
        
        for token_address in tokens_to_remove:
            self.owned_tokens.pop(token_address, None)
            await asyncio.to_thread(remove_position, token_address)

    async def handle_new_token(self, token_data: Dict):
        """Callback for newly detected tokens from mempool."""
        if not self.trading_enabled:
            return

        token_address = token_data.get('address')
        if not token_address or token_address in self.owned_tokens:
            return

        # Simple initial filter for autonomous trade
        min_liq = self.config.get("min_liquidity", 5000)
        max_liq = self.config.get("max_liquidity", float('inf'))
        liquidity = token_data.get('liquidity', 0)

        if liquidity > 0 and (liquidity < min_liq or liquidity > max_liq):
             logger.info(f"AutoTrader: Skipping new token {token_address} due to liquidity: {liquidity}")
             return

        # Snipe-Only Filter
        if self.config.get("snipe_only_mode"):
            deployer = token_data.get('deployer')
            whitelisted = self.config.get("whitelisted_deployers", [])
            if not deployer or deployer not in whitelisted:
                logger.info(f"AutoTrader: Skipping {token_address} - Snipe-only mode active and deployer {deployer} not whitelisted.")
                return

        logger.info(f"AutoTrader: New token detected via mempool, analyzing {token_address}...")
        await self._analyze_and_buy(token_data)

    async def _analyze_and_buy(self, token: Dict):
        token_address = token['address']

        # Final pre-buy validation
        if token_address in self.owned_tokens:
            return

        # RugCheck.xyz Full API Integration
        try:
            logger.info(f"AutoTrader: Performing RugCheck for {token_address}...")
            response = await self.http_client.get(f"https://api.rugcheck.xyz/v1/tokens/{token_address}/report")
            if response.status_code == 200:
                rug_report = response.json()
                score = rug_report.get('score', 0)
                max_allowed_score = self.config.get("rugcheck_max_score", 5000)

                if score > max_allowed_score:
                    logger.warning(f"AutoTrader: Skipping {token.get('symbol', token_address)} - RugCheck score ({score}) exceeds max allowed ({max_allowed_score}).")
                    return
                logger.info(f"AutoTrader: RugCheck passed for {token_address} with score: {score}")
            else:
                logger.warning(f"AutoTrader: RugCheck API returned status {response.status_code}. Proceeding with caution.")
        except Exception as e:
            logger.error(f"AutoTrader: RugCheck failed for {token_address}: {e}")

        # Additional Contract Risk Analysis
        if not await self._check_contract_risk(token_address):
            logger.warning(f"AutoTrader: Skipping {token_address} due to contract risk analysis failure.")
            return

        analysis = await self.ai_analysis_service.analyze_token(token_address)

        if analysis and analysis['recommendation'] == "Buy" and \
           analysis['probability_score'] >= self.config["min_ai_probability_score"] and \
           analysis['risk_assessment'] != "High":

            logger.info(f"AutoTrader: AI recommends BUY for {token.get('symbol', token_address)} (Score: {analysis['probability_score']}, Risk: {analysis['risk_assessment']}).")

            # Additional Filtering
            current_token = await self.data_fetcher_service.get_token_by_address(token_address)
            if current_token:
                # Liquidity Filter
                liquidity = current_token.get('liquidity', 0)
                if liquidity < self.config["min_liquidity"] or liquidity > self.config.get("max_liquidity", 1000000):
                    logger.warning(f"AutoTrader: Skipping {token.get('symbol', token_address)} due to liquidity mismatch: {liquidity}")
                    return

                # VWAP Filter: Ensure we are not buying too far above 24h VWAP (momentum filter)
                if self.config.get("use_vwap_filter"):
                    vwap = current_token.get('vwap_24h')
                    current_price = current_token.get('price', 0)
                    if vwap and current_price > vwap * 1.5: # Don't buy if price > 1.5x of 24h VWAP
                        logger.warning(f"AutoTrader: Skipping {token.get('symbol', token_address)} - Price ({current_price}) is too far above VWAP ({vwap}).")
                        return

            logger.info(f"AutoTrader: Proceeding to buy {token.get('symbol', token_address)}.")
            jito_tip_lamports = int(self.config.get("jito_tip_sol", 0.001) * 10**9)
            
            buy_result = await self.trading_service.execute_buy_order(
                token_address=token_address,
                amount_sol=self.config["buy_amount_sol"],
                slippage=self.config["slippage"],
                jito_tip=jito_tip_lamports
            )

            if buy_result.get("success"):
                # Wait for transaction finality and receive tokens
                is_confirmed = buy_result.get("status") == "confirmed"
                logger.info(f"AutoTrader: Buy transaction sent for {token_address}. Confirmed: {is_confirmed}")

                # Retry loop for balance detection to handle RPC lag
                token_balance = 0
                for attempt in range(5):
                    token_balance = await self.wallet_service.get_token_balance(token_address)
                    if token_balance > 0:
                        break
                    logger.info(f"AutoTrader: Balance check attempt {attempt + 1} for {token_address} returned 0. Retrying...")
                    await asyncio.sleep(2)

                if token_balance > 0:
                    logger.info(f"AutoTrader: Confirmed balance of {token_balance} for {token_address}. Recording position.")
                    position_data = {
                        "token_address": token_address,
                        "token_symbol": token.get('symbol') or 'UNKNOWN',
                        "buy_price": token.get('price', 0),
                        "highest_price": token.get('price', 0),
                        "buy_amount_sol": self.config["buy_amount_sol"],
                        "amount_tokens": token_balance,
                        "initial_amount_tokens": token_balance,
                        "purchase_time": datetime.now().isoformat(),
                        "metadata": {"hit_tp_tiers": []}
                    }
                    self.owned_tokens[token_address] = position_data
                    await asyncio.to_thread(save_position, position_data)

                    if self.socketio:
                        self.socketio.emit('auto_trade_event', {'type': 'buy', 'token': position_data['token_symbol'], 'status': 'success'})
                else:
                    logger.warning(f"AutoTrader: Buy executed for {token_address} but 0 balance detected after retries.")

    async def _check_contract_risk(self, token_address: str) -> bool:
        """
        Performs basic contract risk analysis by scanning token metadata and on-chain indicators.
        Returns True if the contract is deemed safe, False otherwise.
        """
        try:
            logger.info(f"AutoTrader: Checking contract risk for {token_address}...")

            # Fetch token security from Birdeye via DataFetcher
            security_info = await self.data_fetcher_service._fetch_token_security(token_address)
            if security_info:
                # Check for high holder concentration
                top10_percent = security_info.get('top10HolderPercent', 0)
                if top10_percent > 80: # 80% is very high
                    logger.warning(f"AutoTrader: High holder concentration ({top10_percent}%) for {token_address}")
                    return False

                # Check if creator has full control
                if security_info.get('creatorHasFullControl'):
                    logger.warning(f"AutoTrader: Creator has full control for {token_address}")
                    return False

            # Check for suspicious patterns in token metadata/details
            token_details = await self.data_fetcher_service.get_token_by_address(token_address)
            if token_details:
                if token_details.get('dev_wallet_active'):
                    logger.warning(f"AutoTrader: Dev wallet still active/controlling for {token_address}")

            logger.info(f"AutoTrader: Contract risk analysis passed for {token_address}")
            return True
        except Exception as e:
            logger.error(f"AutoTrader: Error during contract risk analysis for {token_address}: {e}")
            return True # Proceed if analysis fails, relying on RugCheck and AI

    async def handle_rugpull_alert(self, data: Dict):
        token_address = data.get('token_address') or data.get('details', {}).get('mint')
        if not token_address or token_address not in self.owned_tokens:
            return

        logger.warning(f"AutoTrader: Rugpull alert for {token_address}. Emergency sell!")

        details = self.owned_tokens[token_address]
        sell_amount = await self.wallet_service.get_token_balance(token_address)

        if sell_amount > 0:
            sell_result = await self.trading_service.execute_sell_order(
                token_address=token_address,
                amount_tokens=sell_amount,
                slippage=100
            )
            if sell_result.get("success"):
                await asyncio.to_thread(increment_rugs_avoided)

        self.owned_tokens.pop(token_address, None)
        await asyncio.to_thread(remove_position, token_address)

auto_trader_service = AutoTraderService()
