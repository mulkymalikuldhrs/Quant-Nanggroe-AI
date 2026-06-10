"""
Execution Layer — Broker Abstractions & Factory
================================================
Unified broker interface for paper trading, Alpaca (equities),
Jupiter (Solana DEX), and Polymarket (prediction markets).

Usage:
    from quant_nanggroe_ai.execution import BrokerFactory, PaperTradingBroker

    broker = BrokerFactory.create("paper", initial_capital=100_000)
    order = await broker.buy("AAPL", 100, 150.0)
"""

from __future__ import annotations

import logging
from typing import Any

from quant_nanggroe_ai.execution.alpaca_broker import AlpacaBroker
from quant_nanggroe_ai.execution.jupiter import JupiterBroker
from quant_nanggroe_ai.execution.paper import PaperTradingBroker
from quant_nanggroe_ai.execution.polymarket import PolymarketBroker

logger = logging.getLogger(__name__)

__all__ = [
    "AlpacaBroker",
    "BrokerFactory",
    "JupiterBroker",
    "PaperTradingBroker",
    "PolymarketBroker",
]

# Type alias for any broker instance
BrokerType = PaperTradingBroker | AlpacaBroker | JupiterBroker | PolymarketBroker


class BrokerFactory:
    """
    Factory for creating broker instances from configuration.

    Supported broker types:
    - "paper": In-memory paper trading broker
    - "alpaca": Alpaca API broker for equities/crypto
    - "jupiter": Jupiter V6 DEX broker for Solana swaps
    - "polymarket": Polymarket broker for prediction markets

    Example:
        broker = BrokerFactory.create("paper", initial_capital=50_000)
        broker = BrokerFactory.create("alpaca", api_key="...", secret_key="...")
    """

    _REGISTRY: dict[str, type[Any]] = {
        "paper": PaperTradingBroker,
        "alpaca": AlpacaBroker,
        "jupiter": JupiterBroker,
        "polymarket": PolymarketBroker,
    }

    @classmethod
    def create(cls, broker_type: str, **kwargs: Any) -> BrokerType:
        """
        Create a broker instance by type name.

        Args:
            broker_type: One of 'paper', 'alpaca', 'jupiter', 'polymarket'
            **kwargs: Broker-specific configuration parameters

        Returns:
            Initialized broker instance

        Raises:
            ValueError: If broker_type is not recognized
        """
        broker_type = broker_type.lower().strip()
        if broker_type not in cls._REGISTRY:
            supported = ", ".join(sorted(cls._REGISTRY.keys()))
            raise ValueError(
                f"Unknown broker type '{broker_type}'. Supported: {supported}"
            )

        broker_cls = cls._REGISTRY[broker_type]
        logger.info("Creating broker: type=%s, class=%s", broker_type, broker_cls.__name__)

        try:
            instance = broker_cls(**kwargs)  # type: ignore[call-arg]
            logger.info("Broker created successfully: %s", broker_type)
            return instance  # type: ignore[return-value]
        except TypeError as exc:
            logger.error("Failed to create broker %s: %s", broker_type, exc)
            raise ValueError(
                f"Invalid configuration for {broker_type} broker: {exc}"
            ) from exc

    @classmethod
    def register(cls, name: str, broker_class: type[Any]) -> None:
        """
        Register a custom broker type.

        Args:
            name: Broker type identifier
            broker_class: Broker class to register
        """
        if not callable(getattr(broker_class, "buy", None)):
            raise ValueError("Broker class must implement a 'buy' method")
        cls._REGISTRY[name.lower()] = broker_class
        logger.info("Registered custom broker: %s -> %s", name, broker_class.__name__)

    @classmethod
    def supported_types(cls) -> list[str]:
        """Return list of supported broker type names."""
        return sorted(cls._REGISTRY.keys())
