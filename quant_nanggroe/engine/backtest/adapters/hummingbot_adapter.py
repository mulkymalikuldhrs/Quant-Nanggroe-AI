"""Hummingbot Adapter for Quant Nanggroe AI.

Provides integration with Hummingbot for automated market making
and liquidity provision on decentralized and centralized exchanges.

Supported Strategies:
    - Pure Market Making
    - Cross-Exchange Market Making
    - Avellaneda-Stoikov Market Making
    - Liquidity Mining
    - TWAP/VWAP Execution
    - Grid Strategy

Supported Exchanges (via Hummingbot):
    Binance, Coinbase Pro, KuCoin, Gate.io, Bybit, OKX,
    Uniswap, PancakeSwap, dYdX, and more.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict

from quant_nanggroe.agents.state import (
    AssetClass,
    TradeAction,
)

logger = logging.getLogger(__name__)


class HummingbotStrategy(str, Enum):
    """Supported Hummingbot strategy types."""
    PURE_MARKET_MAKING = "pure_market_making"
    CROSS_EXCHANGE_MM = "cross_exchange_mm"
    AVELLANEDA_STOIKOV = "avellaneda_stoikov"
    LIQUIDITY_MINING = "liquidity_mining"
    TWAP = "twap"
    VWAP = "vwap"
    GRID = "grid"
    ARBITRAGE = "arbitrage"


class HummingbotOrderType(str, Enum):
    """Hummingbot order types."""
    LIMIT = "limit"
    LIMIT_MAKER = "limit_maker"
    MARKET = "market"


class HummingbotConfig(BaseModel):
    """Configuration for Hummingbot adapter.

    Attributes:
        instance_name: Name for this Hummingbot instance.
        strategy: Primary trading strategy.
        exchange: Target exchange connector.
        market: Spot or perpetual market.
        trading_pair: Trading pair (e.g., 'BTC-USDT').
        bid_spread: Bid spread in decimal (e.g., 0.001 = 0.1%).
        ask_spread: Ask spread in decimal.
        order_amount: Order size per side.
        order_levels: Number of order levels per side.
        order_refresh_time: Order refresh interval in seconds.
        inventory_skew_enabled: Enable inventory skewing.
        inventory_target_base_pct: Target base asset inventory percentage.
        hanging_orders_enabled: Allow hanging orders.
        filled_order_delay: Delay after fill in seconds.
        minimum_spread: Minimum spread threshold.
        maximum_spread: Maximum spread threshold.
        price_source: Price source (current_market/external_market/custom_api).
        price_source_exchange: External exchange for price (if applicable).
        cancel_order_wait_time: Wait time before cancelling orders.
    """
    model_config = ConfigDict(extra="allow")

    instance_name: str = Field("qn-ai-hbot", description="Instance name")
    strategy: HummingbotStrategy = Field(
        HummingbotStrategy.PURE_MARKET_MAKING, description="Strategy type"
    )
    exchange: str = Field("binance", description="Exchange connector")
    market: str = Field("spot", description="Market type")
    trading_pair: str = Field("BTC-USDT", description="Trading pair")
    bid_spread: float = Field(0.001, ge=0, le=0.1, description="Bid spread")
    ask_spread: float = Field(0.001, ge=0, le=0.1, description="Ask spread")
    order_amount: float = Field(0.01, gt=0, description="Order size")
    order_levels: int = Field(1, ge=1, le=15, description="Order levels")
    order_refresh_time: float = Field(60.0, gt=0, description="Refresh interval (s)")
    inventory_skew_enabled: bool = Field(True, description="Enable inventory skew")
    inventory_target_base_pct: float = Field(0.5, ge=0, le=1, description="Target base %")
    hanging_orders_enabled: bool = Field(False, description="Hanging orders")
    filled_order_delay: float = Field(60.0, gt=0, description="Fill delay (s)")
    minimum_spread: float = Field(0.0001, ge=0, description="Minimum spread")
    maximum_spread: float = Field(0.05, ge=0, description="Maximum spread")
    price_source: str = Field("current_market", description="Price source")
    price_source_exchange: str = Field("", description="External price exchange")
    cancel_order_wait_time: float = Field(30.0, gt=0, description="Cancel wait (s)")


class AvellanedaStoikovConfig(HummingbotConfig):
    """Extended configuration for Avellaneda-Stoikov market making.

    The A-S model dynamically adjusts spreads based on:
    - Volatility (sigma)
    - Time until trading end (T-t)
    - Risk aversion parameter (gamma)
    - Order flow intensity (kappa)
    - Inventory level (q)
    - Reserve price calculation

    Key Equations:
        Reserve price: r = s - q * gamma * sigma^2 * (T - t)
        Bid spread: delta_b = (gamma * sigma^2 * (T-t))/2 + (1/gamma) * ln(1 + gamma/kappa)
        Ask spread: delta_a = (gamma * sigma^2 * (T-t))/2 + (1/gamma) * ln(1 + gamma/kappa)
    """
    strategy: HummingbotStrategy = Field(
        HummingbotStrategy.AVELLANEDA_STOIKOV, description="A-S strategy"
    )
    gamma: float = Field(0.1, gt=0, le=10, description="Risk aversion parameter")
    sigma: float = Field(0.01, gt=0, le=1, description="Volatility estimate")
    kappa: float = Field(0.5, gt=0, le=100, description="Order flow intensity")
    trading_hours: float = Field(24.0, gt=0, description="Total trading hours (T)")
    order_book_depth: int = Field(10, ge=1, le=50, description="Order book depth")


@dataclass
class MarketMakingState:
    """Current state of market making activity."""
    is_running: bool = False
    strategy: str = ""
    trading_pair: str = ""
    exchange: str = ""
    bid_price: float = 0.0
    ask_price: float = 0.0
    mid_price: float = 0.0
    spread_bps: float = 0.0
    inventory_base: float = 0.0
    inventory_quote: float = 0.0
    total_trades: int = 0
    pnl: float = 0.0
    inventory_skew: float = 0.0
    active_orders: int = 0
    last_fill_time: Optional[datetime] = None
    started_at: Optional[datetime] = None
    uptime_seconds: float = 0.0


class HummingbotAdapter:
    """Adapter for Hummingbot market making integration.

    Provides a high-level interface for:
    - Configuring and launching market making strategies
    - Monitoring market making performance
    - Adjusting parameters dynamically based on market conditions
    - Integrating with our agent pipeline for strategy decisions

    Usage:
        .. code-block:: python

            config = HummingbotConfig(
                exchange="binance",
                trading_pair="BTC-USDT",
                bid_spread=0.001,
                ask_spread=0.001,
                order_amount=0.01,
            )
            adapter = HummingbotAdapter(config)
            adapter.start()
            status = adapter.get_status()

    Note:
        This adapter generates Hummingbot configuration files and
        status monitoring. Actual execution requires a running
        Hummingbot instance or Docker container.
    """

    def __init__(self, config: Optional[HummingbotConfig] = None) -> None:
        """Initialize the Hummingbot adapter.

        Args:
            config: Adapter configuration. Uses defaults if not provided.
        """
        self.config = config or HummingbotConfig()
        self._state = MarketMakingState(
            strategy=self.config.strategy.value,
            trading_pair=self.config.trading_pair,
            exchange=self.config.exchange,
        )
        logger.info(
            "HummingbotAdapter initialized: %s on %s (%s)",
            self.config.trading_pair,
            self.config.exchange,
            self.config.strategy.value,
        )

    def start(self) -> Dict[str, Any]:
        """Start the market making strategy.

        Returns:
            Startup confirmation with configuration.
        """
        self._state.is_running = True
        self._state.started_at = datetime.now()

        config_yaml = self.generate_config_yaml()

        result = {
            "status": "started",
            "instance": self.config.instance_name,
            "strategy": self.config.strategy.value,
            "exchange": self.config.exchange,
            "trading_pair": self.config.trading_pair,
            "config_yaml": config_yaml,
            "docker_command": self._generate_docker_command(),
        }

        logger.info(
            "Market making started: %s %s on %s",
            self.config.strategy.value,
            self.config.trading_pair,
            self.config.exchange,
        )
        return result

    def stop(self) -> Dict[str, Any]:
        """Stop the market making strategy.

        Returns:
            Stop confirmation with final state.
        """
        self._state.is_running = False
        return {
            "status": "stopped",
            "instance": self.config.instance_name,
            "final_state": self._state.__dict__,
        }

    def get_status(self) -> MarketMakingState:
        """Get current market making status.

        Returns:
            Current state of market making activity.
        """
        if self._state.started_at and self._state.is_running:
            self._state.uptime_seconds = (
                datetime.now() - self._state.started_at
            ).total_seconds()
        return self._state

    def update_parameters(self, **kwargs: Any) -> Dict[str, Any]:
        """Dynamically update market making parameters.

        This method allows our agent pipeline to adjust market making
        parameters based on market conditions, risk assessments, etc.

        Args:
            **kwargs: Parameters to update (bid_spread, ask_spread, etc.).

        Returns:
            Updated parameters confirmation.
        """
        updated = {}
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                updated[key] = value

        logger.info("Updated parameters: %s", updated)
        return {
            "status": "parameters_updated",
            "updated": updated,
            "new_config": self.config.model_dump(),
        }

    def calculate_optimal_spreads(
        self,
        volatility: float,
        inventory_ratio: float,
        order_flow_intensity: float = 0.5,
    ) -> Dict[str, float]:
        """Calculate optimal bid/ask spreads using Avellaneda-Stoikov model.

        Args:
            volatility: Current market volatility (sigma).
            inventory_ratio: Current inventory ratio (0-1, base asset fraction).
            order_flow_intensity: Order arrival rate (kappa).

        Returns:
            Optimal spread configuration.
        """
        gamma = getattr(self.config, 'gamma', 0.1)
        time_remaining = getattr(self.config, 'trading_hours', 24.0) / 24.0  # Normalized

        # Avellaneda-Stoikov reserve price adjustment
        inventory_skew = (inventory_ratio - 0.5) * 2  # -1 to +1

        # Bid/ask spreads from A-S model
        base_spread = (gamma * volatility**2 * time_remaining) / 2
        log_term = (1 / gamma) * max(0.001, (1 + gamma / max(0.01, order_flow_intensity)))

        optimal_bid_spread = base_spread + log_term * (1 + inventory_skew)
        optimal_ask_spread = base_spread + log_term * (1 - inventory_skew)

        # Apply min/max constraints
        bid_spread = max(self.config.minimum_spread, min(optimal_bid_spread, self.config.maximum_spread))
        ask_spread = max(self.config.minimum_spread, min(optimal_ask_spread, self.config.maximum_spread))

        return {
            "optimal_bid_spread": round(bid_spread, 6),
            "optimal_ask_spread": round(ask_spread, 6),
            "inventory_skew": round(inventory_skew, 4),
            "reserve_price_adjustment": round(-inventory_skew * gamma * volatility**2 * time_remaining, 6),
            "model": "avellaneda_stoikov",
        }

    def generate_config_yaml(self) -> str:
        """Generate Hummingbot configuration YAML file.

        Returns:
            Complete YAML configuration string.
        """
        lines = [
            f"# Hummingbot Configuration - Generated by Quant Nanggroe AI",
            f"# Instance: {self.config.instance_name}",
            f"# Generated: {datetime.now().isoformat()}",
            "",
            f"conf_strategy: {self.config.strategy.value}",
            f"exchange: {self.config.exchange}",
            f"market: {self.config.market}",
            f"trading_pair: {self.config.trading_pair}",
            "",
            "# Spreads and Orders",
            f"bid_spread: {self.config.bid_spread}",
            f"ask_spread: {self.config.ask_spread}",
            f"order_amount: {self.config.order_amount}",
            f"order_levels: {self.config.order_levels}",
            f"order_refresh_time: {self.config.order_refresh_time}",
            f"filled_order_delay: {self.config.filled_order_delay}",
            "",
            "# Inventory Management",
            f"inventory_skew_enabled: {str(self.config.inventory_skew_enabled).lower()}",
            f"inventory_target_base_pct: {self.config.inventory_target_base_pct}",
            f"hanging_orders_enabled: {str(self.config.hanging_orders_enabled).lower()}",
            "",
            "# Spread Limits",
            f"minimum_spread: {self.config.minimum_spread}",
            f"maximum_spread: {self.config.maximum_spread}",
            "",
            "# Price Source",
            f"price_source: {self.config.price_source}",
        ]

        if self.config.price_source_exchange:
            lines.append(f"price_source_exchange: {self.config.price_source_exchange}")

        # Add A-S specific parameters if applicable
        if self.config.strategy == HummingbotStrategy.AVELLANEDA_STOIKOV:
            as_config = getattr(self, '_as_config', None)
            if as_config:
                lines.extend([
                    "",
                    "# Avellaneda-Stoikov Parameters",
                    f"gamma: {as_config.gamma}",
                    f"sigma: {as_config.sigma}",
                    f"kappa: {as_config.kappa}",
                    f"trading_hours: {as_config.trading_hours}",
                    f"order_book_depth: {as_config.order_book_depth}",
                ])

        return '\n'.join(lines)

    def _generate_docker_command(self) -> str:
        """Generate Docker command for running Hummingbot.

        Returns:
            Docker CLI command string.
        """
        return (
            f"docker run -it --rm "
            f"--name {self.config.instance_name} "
            f"-v $(pwd)/conf:/conf "
            f"-v $(pwd)/logs:/logs "
            f"hummingbot/hummingbot:latest"
        )

    def calculate_performance_metrics(self) -> Dict[str, Any]:
        """Calculate market making performance metrics.

        Returns:
            Performance metrics dictionary.
        """
        if not self._state.started_at:
            return {"error": "Not started"}

        uptime = self._state.uptime_seconds or 0
        trades = self._state.total_trades

        return {
            "uptime_seconds": uptime,
            "total_trades": trades,
            "trades_per_hour": trades / max(uptime / 3600, 1),
            "pnl": self._state.pnl,
            "pnl_per_trade": self._state.pnl / max(trades, 1),
            "inventory_base": self._state.inventory_base,
            "inventory_quote": self._state.inventory_quote,
            "spread_bps": self._state.spread_bps,
            "active_orders": self._state.active_orders,
            "inventory_skew": self._state.inventory_skew,
        }

    @classmethod
    def from_agent_decision(
        cls,
        decision: Dict[str, Any],
        exchange: str = "binance",
    ) -> HummingbotAdapter:
        """Create adapter from agent pipeline decision.

        Allows the trading agent pipeline to automatically configure
        market making based on its analysis.

        Args:
            decision: Agent decision dictionary.
            exchange: Target exchange.

        Returns:
            Configured HummingbotAdapter instance.
        """
        symbol = decision.get("symbol", "BTC-USDT")
        # Convert our symbol format to Hummingbot format
        hb_pair = symbol.replace("/", "-")

        config = HummingbotConfig(
            exchange=exchange,
            trading_pair=hb_pair,
            order_amount=decision.get("quantity", 0.01),
            bid_spread=decision.get("bid_spread", 0.001),
            ask_spread=decision.get("ask_spread", 0.001),
        )

        return cls(config)
