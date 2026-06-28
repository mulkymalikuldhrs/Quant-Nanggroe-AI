"""Solana Broker Adapter — Implements ExchangeInterface for Solana/Jupiter.

Provides a full implementation of
:class:`~quant_nanggroe.exchange.base.ExchangeInterface` for Solana,
using Jupiter V6 for swap execution and the Solana RPC for balance
queries and transaction management.

Features
--------
* Connect/disconnect via Solana RPC
* Place swap orders via Jupiter V6
* Get SOL and SPL token balances
* Portfolio tracking for Solana assets
* Health check via RPC ping

Notes
-----
Solana uses a swap-based model (no traditional order book for most tokens),
so ``place_order`` is mapped to Jupiter swaps. Market orders execute as
immediate swaps; limit orders are not directly supported on-chain.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from quant_nanggroe.exchange.base import (
    ExchangeConfig,
    ExchangeError,
    ExchangeInterface,
    ExchangeState,
    ConnectionError,
    OrderError,
    InsufficientFundsError,
    MarketDataError,
    WebSocketCallback,
)
from quant_nanggroe.exchange.solana.wallet import SolanaWallet
from quant_nanggroe.exchange.solana.jupiter import (
    JupiterV6Client,
    JupiterQuote,
    SOL_MINT,
    USDC_MINT,
)
from quant_nanggroe.types.market import OHLCV, OrderBook, Ticker, TimeFrame
from quant_nanggroe.types.orders import Order, OrderSide, OrderStatus, OrderType
from quant_nanggroe.types.positions import Position, PositionSide, Portfolio

logger = logging.getLogger(__name__)


class SolanaBroker(ExchangeInterface):
    """Solana broker adapter implementing ExchangeInterface.

    Uses Jupiter V6 for swap execution and the Solana RPC for
    account queries and transaction management.

    Parameters
    ----------
    config:
        Exchange configuration. ``exchange_id`` should be ``"solana"``.
        ``api_key`` is the Base58-encoded private key.
        ``api_secret`` is unused (pass ``None``).
    rpc_url:
        Solana JSON-RPC endpoint.
    jupiter_url:
        Jupiter V6 API base URL.

    Examples
    --------
    .. code-block:: python

        config = ExchangeConfig(
            exchange_id="solana",
            api_key="<placeholder>",  # Base58 private key
        )
        broker = SolanaBroker(config)
        await broker.connect()
        balance = await broker.get_balance()
    """

    def __init__(
        self,
        config: ExchangeConfig,
        rpc_url: str = "https://api.mainnet-beta.solana.com",
        jupiter_url: str = "https://quote-api.jup.ag/v6",
    ) -> None:
        self._config = config
        self._rpc_url = rpc_url
        self._state: ExchangeState = ExchangeState.DISCONNECTED
        self._wallet: Optional[SolanaWallet] = None
        self._jupiter: Optional[JupiterV6Client] = None
        self._local_positions: Dict[str, Position] = {}
        self._local_orders: Dict[str, Order] = {}

    # ----- Connection lifecycle -----

    async def connect(self) -> bool:
        """Establish connection to Solana RPC and initialize wallet.

        Returns
        -------
        bool
            ``True`` if connected successfully.

        Raises
        ------
        ConnectionError
            If the wallet or RPC connection fails.
        """
        if self._state == ExchangeState.CONNECTED:
            return True

        self._state = ExchangeState.CONNECTING
        try:
            # Initialize wallet from config
            if not self._config.api_key:
                raise ConnectionError(
                    "api_key (Base58 private key) is required for SolanaBroker",
                    exchange="solana",
                )

            self._wallet = SolanaWallet(
                private_key_bs58=self._config.api_key,
                rpc_url=self._rpc_url,
            )

            # Initialize Jupiter client
            self._jupiter = JupiterV6Client(
                rpc_url=self._rpc_url,
                api_url=jupiter_url if jupiter_url else "https://quote-api.jup.ag/v6",
            )

            # Verify connection by getting balance
            await self._wallet.get_sol_balance()

            self._state = ExchangeState.CONNECTED
            logger.info(
                "SolanaBroker: Connected — wallet %s",
                self._wallet.public_key[:8] + "...",
            )
            return True

        except Exception as exc:
            self._state = ExchangeState.ERROR
            raise ConnectionError(
                f"Failed to connect to Solana: {exc}",
                exchange="solana",
                original=exc,
            ) from exc

    async def disconnect(self) -> None:
        """Close connections and clean up resources."""
        if self._jupiter:
            await self._jupiter.close()
        self._wallet = None
        self._jupiter = None
        self._state = ExchangeState.DISCONNECTED
        logger.info("SolanaBroker: Disconnected")

    @property
    def is_connected(self) -> bool:
        return self._state == ExchangeState.CONNECTED

    @property
    def state(self) -> ExchangeState:
        return self._state

    @property
    def name(self) -> str:
        return "solana"

    # ----- Account -----

    async def get_balance(self) -> Dict[str, float]:
        """Get SOL and SPL token balances.

        Returns
        -------
        dict
            Mapping of token symbol/mint → balance.
        """
        self._require_wallet()
        try:
            balances: Dict[str, float] = {}

            # SOL balance
            sol_balance = await self._wallet.get_sol_balance()
            balances["SOL"] = sol_balance

            # SPL token balances
            token_accounts = await self._wallet.get_token_accounts()
            for acct in token_accounts:
                key = acct.mint if not acct.ui_amount else acct.mint
                balances[key] = acct.ui_amount

            return balances
        except Exception as exc:
            raise ExchangeError(
                f"Failed to get balance: {exc}", exchange="solana", original=exc
            ) from exc

    async def get_positions(self) -> List[Position]:
        """Get current positions based on token balances.

        Returns
        -------
        list of Position
            Positions for non-zero token holdings.
        """
        self._require_wallet()
        return list(self._local_positions.values())

    async def get_portfolio(self) -> Portfolio:
        """Get portfolio snapshot with all token positions.

        Returns
        -------
        Portfolio
            Portfolio with positions and cash (SOL) balance.
        """
        self._require_wallet()
        try:
            balances = await self.get_balance()
            cash = balances.get("SOL", 0.0)

            portfolio = Portfolio(
                name="solana",
                currency="SOL",
                initial_capital=cash,
                cash=cash,
            )
            for pos in self._local_positions.values():
                portfolio.positions[pos.symbol] = pos
            portfolio.recalculate()
            return portfolio
        except Exception as exc:
            raise ExchangeError(
                f"Failed to get portfolio: {exc}", exchange="solana", original=exc
            ) from exc

    # ----- Trading -----

    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        client_order_id: Optional[str] = None,
        strategy_name: Optional[str] = None,
        agent_name: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Order:
        """Place a swap order via Jupiter V6.

        The ``symbol`` is interpreted as ``"INPUT_MINT/OUTPUT_MINT"``.
        For example, ``"SOL/USDC"`` means swap SOL → USDC.

        BUY = swap from quote to base (e.g. USDC → SOL)
        SELL = swap from base to quote (e.g. SOL → USDC)

        Parameters
        ----------
        symbol:
            Trading pair as ``"BASE/QUOTE"``.
        side:
            BUY or SELL.
        order_type:
            Only MARKET is fully supported; LIMIT is not supported on-chain.
        quantity:
            Amount to swap in base units.
        price:
            Not used for MARKET orders on Solana.
        stop_price:
            Not supported.
        client_order_id:
            Optional client-assigned ID.

        Returns
        -------
        Order
            The placed order with signature as ``broker_order_id``.
        """
        self._require_wallet()
        self._require_jupiter()

        if order_type != OrderType.MARKET:
            raise OrderError(
                f"Only MARKET orders are supported on Solana, got {order_type}",
                exchange="solana",
            )

        try:
            # Parse symbol → mints
            input_mint, output_mint = self._parse_symbol(symbol, side)

            # Convert quantity to smallest unit (assuming 9 decimals for SOL)
            amount_raw = int(quantity * 1_000_000_000) if input_mint == SOL_MINT else int(quantity * 1_000_000)

            # Get quote
            quote = await self._jupiter.get_quote(
                input_mint=input_mint,
                output_mint=output_mint,
                amount=amount_raw,
                slippage_bps=50,
            )

            # Execute swap
            result = await self._jupiter.execute_swap(
                quote=quote,
                wallet=self._wallet,
            )

            # Build Order model
            order = Order(
                id=str(uuid.uuid4()),
                client_order_id=client_order_id,
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=price,
                status=(
                    OrderStatus.FILLED
                    if result.status == "confirmed"
                    else OrderStatus.REJECTED
                ),
                filled_quantity=quantity if result.status == "confirmed" else 0.0,
                average_fill_price=None,
                commission=result.fee / 1_000_000_000,  # lamports → SOL
                created_at=datetime.now(tz=timezone.utc),
                updated_at=datetime.now(tz=timezone.utc),
                broker_id="solana",
                broker_order_id=result.signature,
                strategy_name=strategy_name,
                agent_name=agent_name,
                notes=notes,
            )

            self._local_orders[order.id] = order
            return order

        except (OrderError, InsufficientFundsError):
            raise
        except Exception as exc:
            raise OrderError(
                f"Failed to place swap order: {exc}",
                exchange="solana",
                original=exc,
            ) from exc

    async def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> Order:
        """Cancel an order.

        Not supported on Solana — swap transactions are instant.
        """
        raise OrderError(
            "Order cancellation is not supported on Solana — swaps are instant",
            order_id=order_id,
            exchange="solana",
        )

    async def get_order(self, order_id: str, symbol: Optional[str] = None) -> Order:
        """Get order by ID from local cache.

        Parameters
        ----------
        order_id:
            Local order ID.

        Returns
        -------
        Order
            The cached order.
        """
        order = self._local_orders.get(order_id)
        if not order:
            raise OrderError(
                f"Order not found: {order_id}",
                order_id=order_id,
                exchange="solana",
            )
        return order

    # ----- Market Data (not supported on-chain) -----

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: TimeFrame = TimeFrame.D1,
        since: Optional[datetime] = None,
        limit: int = 500,
    ) -> List[OHLCV]:
        """OHLCV data is not directly available on-chain.

        Use an external data provider (e.g. Birdeye, CoinGecko) instead.
        """
        raise MarketDataError(
            "OHLCV data not available on-chain. Use an external data provider.",
            exchange="solana",
        )

    async def get_ticker(self, symbol: str) -> Ticker:
        """Ticker data is not directly available on-chain.

        Use an external data provider instead.
        """
        raise MarketDataError(
            "Ticker data not available on-chain. Use an external data provider.",
            exchange="solana",
        )

    async def get_orderbook(self, symbol: str, limit: int = 20) -> OrderBook:
        """Order book data is not available for Solana swaps.

        Use an external DEX aggregator instead.
        """
        raise MarketDataError(
            "Order book not available for Solana swaps. Use Jupiter for route info.",
            exchange="solana",
        )

    async def get_trades(
        self,
        symbol: str,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Trade history is not directly available on-chain."""
        raise MarketDataError(
            "Trade history not available on-chain. Use Solscan or similar.",
            exchange="solana",
        )

    # ----- WebSocket -----

    async def subscribe_ticker(self, symbol: str, callback: WebSocketCallback) -> None:
        """Not supported — Solana doesn't have traditional tickers."""
        raise MarketDataError(
            "Ticker subscription not supported for Solana",
            exchange="solana",
        )

    async def subscribe_orderbook(self, symbol: str, callback: WebSocketCallback) -> None:
        """Not supported — Solana uses AMMs, not order books."""
        raise MarketDataError(
            "Order book subscription not supported for Solana",
            exchange="solana",
        )

    async def subscribe_trades(self, symbol: str, callback: WebSocketCallback) -> None:
        """Subscribe to on-chain trades via mempool monitor.

        Not implemented in this version.
        """
        raise MarketDataError(
            "Trade subscription not yet implemented for Solana",
            exchange="solana",
        )

    async def unsubscribe(self, symbol: str, channel: str) -> None:
        """Unsubscribe — not applicable for Solana."""
        pass

    # ----- Utility -----

    async def get_markets(self) -> List[str]:
        """List known Solana swap pairs.

        Returns a list of common pairs; the full list depends on
        Jupiter's supported routes.
        """
        return [
            "SOL/USDC",
            "SOL/USDT",
            "BONK/SOL",
            "JUP/SOL",
            "WIF/SOL",
        ]

    async def health_check(self) -> bool:
        """Check Solana RPC health by getting the wallet balance.

        Returns
        -------
        bool
            ``True`` if the RPC is responsive.
        """
        try:
            if self._wallet:
                await self._wallet.get_sol_balance()
                self._state = ExchangeState.CONNECTED
                return True
            return False
        except Exception:
            self._state = ExchangeState.ERROR
            return False

    # ----- Internal Helpers -----

    def _require_wallet(self) -> SolanaWallet:
        """Ensure wallet is initialized."""
        if not self._wallet or not self.is_connected:
            raise ConnectionError(
                "SolanaBroker is not connected", exchange="solana"
            )
        return self._wallet

    def _require_jupiter(self) -> JupiterV6Client:
        """Ensure Jupiter client is initialized."""
        if not self._jupiter or not self.is_connected:
            raise ConnectionError(
                "SolanaBroker is not connected", exchange="solana"
            )
        return self._jupiter

    @staticmethod
    def _parse_symbol(symbol: str, side: OrderSide) -> tuple[str, str]:
        """Parse a trading pair symbol into input/output mints.

        Parameters
        ----------
        symbol:
            Trading pair like ``"SOL/USDC"``.
        side:
            BUY means swap quote→base, SELL means swap base→quote.

        Returns
        -------
        tuple of (input_mint, output_mint)
        """
        # Known mint mapping
        MINT_MAP = {
            "SOL": SOL_MINT,
            "USDC": USDC_MINT,
            "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
        }

        parts = symbol.split("/")
        if len(parts) != 2:
            raise OrderError(
                f"Invalid symbol format: {symbol}. Expected 'BASE/QUOTE'",
                exchange="solana",
            )

        base, quote = parts[0].upper(), parts[1].upper()
        base_mint = MINT_MAP.get(base, base)
        quote_mint = MINT_MAP.get(quote, quote)

        if side == OrderSide.BUY:
            # BUY base with quote: input=quote, output=base
            return quote_mint, base_mint
        else:
            # SELL base for quote: input=base, output=quote
            return base_mint, quote_mint

    def __repr__(self) -> str:
        state = self._state.value
        return f"SolanaBroker(state={state})"
