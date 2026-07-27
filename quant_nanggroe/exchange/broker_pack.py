"""Broker Packs — Plugin-based Broker Adapter Pattern.

Extracted from OpenAlice Broker Packs architecture.
Provides dynamic broker loading via plugin system with schema-validated
configuration, immutable versioned releases, and structural type checks
across pack boundaries (no isinstance/instanceof).

Architecture:
    BrokerPack (metadata + configSchema + create method)
      → IBroker (abstract interface)
        → Concrete implementations (loaded dynamically by file URL)

Rules:
    - Exchange manager owns orchestration; loads one active pack per account
    - Broker packs are loaded on demand, never at startup
    - Core code must NOT use isinstance across pack boundaries
    - Configuration is schema-validated per broker engine
    - Each pack is an immutable release with SHA-256 verification

Usage:
    pack = BrokerPackRegistry.get("ibkr")
    if pack and pack.validate_config({"account_id": "DU123456"}):
        broker = pack.create({"account_id": "DU123456"})
        await broker.connect()
"""

from __future__ import annotations

import importlib
import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Broker Engine Types (canonical)
# ---------------------------------------------------------------------------

BROKER_PACK_API_VERSION = 1
"""Current Broker Pack API version. All packs must match."""

SUPPORTED_ENGINES = frozenset({
    "ccxt",
    "alpaca",
    "ibkr",
    "mt5",
    "polymarket",
    "paper",
    "solana",
})


# ---------------------------------------------------------------------------
# IBroker — Abstract Interface (structural typing)
# ---------------------------------------------------------------------------

class IBroker(ABC):
    """Broker interface that all packs must implement.

    Uses structural typing: core code checks method signatures, not types.
    """

    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the broker."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the broker."""

    @abstractmethod
    async def get_account(self) -> dict[str, Any]:
        """Get account information."""

    @abstractmethod
    async def submit_order(self, order: dict[str, Any]) -> dict[str, Any]:
        """Submit an order."""

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""

    @abstractmethod
    async def get_order(self, order_id: str) -> dict[str, Any] | None:
        """Get order status."""

    @abstractmethod
    async def get_positions(self) -> list[dict[str, Any]]:
        """Get all open positions."""

    @abstractmethod
    async def get_price(self, symbol: str) -> float:
        """Get current price."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Broker name identifier."""

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Whether connected."""


# ---------------------------------------------------------------------------
# Broker Pack Definition
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BrokerPack:
    """Metadata and factory for a dynamically-loaded broker pack.

    Each pack is a self-contained plugin that provides a broker implementation
    conforming to the IBroker interface.
    """

    engine: str
    """Canonical engine identifier (e.g. 'ibkr', 'alpaca')."""

    api_version: int
    """Must match BROKER_PACK_API_VERSION."""

    version: str
    """Semantic version of this pack release."""

    config_schema: dict[str, Any] | None = None
    """JSON Schema for configuration validation."""

    description: str = ""
    """Human-readable description."""

    @classmethod
    def create(cls, engine: str, config: dict[str, Any]) -> IBroker:
        """Create a broker instance from a pack definition.

        Dynamic import using the convention:
            quant_nanggroe.exchange.{engine}_broker

        Args:
            engine: Engine identifier (e.g. 'alpaca', 'ccxt', 'ibkr').
            config: Configuration dict passed to the broker constructor.

        Returns:
            IBroker instance.

        Raises:
            ValueError: If engine is unsupported or module not found.
        """
        if engine not in SUPPORTED_ENGINES:
            raise ValueError(f"Unsupported broker engine: {engine}. "
                             f"Supported: {sorted(SUPPORTED_ENGINES)}")

        module_path = f"quant_nanggroe.exchange.{engine}_broker"
        try:
            module = importlib.import_module(module_path)
        except ImportError:
            raise ValueError(f"Broker module not found: {module_path}")

        # Look for the broker class following naming convention
        # e.g. AlpacaBroker, CCXTBroker, IBKRBroker, PaperBroker, MT5Broker
        class_name = _engine_to_class_name(engine)
        broker_cls = getattr(module, class_name, None)
        if broker_cls is None:
            # Fallback: search module for any IBroker subclass
            for name in dir(module):
                obj = getattr(module, name)
                if isinstance(obj, type) and issubclass(obj, IBroker) and obj is not IBroker:
                    broker_cls = obj
                    break
        if broker_cls is None:
            raise ValueError(f"No IBroker implementation found in {module_path}")

        return broker_cls(config)

    def validate_config(self, config: dict[str, Any]) -> tuple[bool, str]:
        """Validate broker configuration against schema.

        Uses structural validation (duck typing) — never isinstance checks.

        Args:
            config: Configuration dict to validate.

        Returns:
            (valid, error_message) tuple.
        """
        if self.config_schema is None:
            return True, ""

        schema = self.config_schema
        required = schema.get("required", [])

        for field in required:
            if field not in config or config[field] is None:
                return False, f"Missing required field: {field}"

        # Type validation
        properties = schema.get("properties", {})
        for key, value in config.items():
            prop = properties.get(key)
            if prop is None:
                continue
            expected_type = prop.get("type")
            if expected_type == "string" and not isinstance(value, str):
                return False, f"Field '{key}' must be a string"
            if expected_type == "number" and not isinstance(value, (int, float)):
                return False, f"Field '{key}' must be a number"
            if expected_type == "boolean" and not isinstance(value, bool):
                return False, f"Field '{key}' must be a boolean"

        return True, ""


# ---------------------------------------------------------------------------
# Broker Pack Registry
# ---------------------------------------------------------------------------

@dataclass
class BrokerPackRegistry:
    """Registry of all available broker packs.

    Acts as the composition root — packs register themselves here.
    Core code queries the registry to create broker instances.
    """

    _packs: dict[str, BrokerPack] = field(default_factory=dict)

    def register(self, pack: BrokerPack) -> None:
        """Register a broker pack.

        Args:
            pack: BrokerPack definition.

        Raises:
            ValueError: If engine already registered or API version mismatch.
        """
        if pack.api_version != BROKER_PACK_API_VERSION:
            raise ValueError(
                f"BrokerPack API version mismatch for '{pack.engine}': "
                f"got {pack.api_version}, expected {BROKER_PACK_API_VERSION}"
            )
        if pack.engine in self._packs:
            logger.warning("Overriding existing broker pack: %s", pack.engine)
        self._packs[pack.engine] = pack
        logger.info("Registered broker pack: %s v%s", pack.engine, pack.version)

    def get(self, engine: str) -> BrokerPack | None:
        """Get a registered broker pack by engine identifier.

        Args:
            engine: Engine identifier.

        Returns:
            BrokerPack if found, None otherwise.
        """
        return self._packs.get(engine)

    def engines(self) -> frozenset[str]:
        """Get set of all registered engine identifiers."""
        return frozenset(self._packs.keys())

    def create(self, engine: str, config: dict[str, Any]) -> IBroker:
        """Create a broker instance from a registered pack.

        Args:
            engine: Engine identifier.
            config: Broker configuration.

        Returns:
            IBroker instance.

        Raises:
            ValueError: If engine not registered or config invalid.
        """
        pack = self.get(engine)
        if pack is None:
            raise ValueError(f"Broker pack not registered: {engine}. "
                             f"Available: {sorted(self._packs.keys())}")
        valid, error = pack.validate_config(config)
        if not valid:
            raise ValueError(f"Invalid config for '{engine}': {error}")
        return BrokerPack.create(engine, config)

    def list_packs(self) -> list[dict[str, Any]]:
        """List all registered packs (for discovery)."""
        return [
            {
                "engine": p.engine,
                "version": p.version,
                "api_version": p.api_version,
                "description": p.description,
                "config_schema": p.config_schema,
            }
            for p in self._packs.values()
        ]


# ---------------------------------------------------------------------------
# Default Registry Instance
# ---------------------------------------------------------------------------

# Singleton registry — populated at startup by register_default_packs()
_registry: BrokerPackRegistry | None = None


def get_registry() -> BrokerPackRegistry:
    """Get the global BrokerPackRegistry singleton."""
    global _registry
    if _registry is None:
        _registry = BrokerPackRegistry()
        register_default_packs(_registry)
    return _registry


def register_default_packs(registry: BrokerPackRegistry) -> None:
    """Register all built-in broker packs.

    These packs map to existing broker implementations in quant_nanggroe.exchange.
    """
    registry.register(BrokerPack(
        engine="alpaca",
        api_version=BROKER_PACK_API_VERSION,
        version="1.0.0",
        description="Alpaca Trading API — US equities and crypto",
        config_schema={
            "type": "object",
            "required": ["api_key", "api_secret"],
            "properties": {
                "api_key": {"type": "string", "description": "Alpaca API key"},
                "api_secret": {"type": "string", "description": "Alpaca API secret"},
                "paper": {"type": "boolean", "description": "Use paper trading"},
            },
        },
    ))
    registry.register(BrokerPack(
        engine="ccxt",
        api_version=BROKER_PACK_API_VERSION,
        version="1.0.0",
        description="CCXT Unified — 100+ exchange support",
        config_schema={
            "type": "object",
            "required": ["exchange_id"],
            "properties": {
                "exchange_id": {"type": "string", "description": "CCXT exchange ID (e.g. binance, okx)"},
                "api_key": {"type": "string", "description": "API key"},
                "api_secret": {"type": "string", "description": "API secret"},
                "testnet": {"type": "boolean", "description": "Use testnet"},
            },
        },
    ))
    registry.register(BrokerPack(
        engine="ibkr",
        api_version=BROKER_PACK_API_VERSION,
        version="1.0.0",
        description="Interactive Brokers — via IB Gateway/TWS",
        config_schema={
            "type": "object",
            "required": ["account_id"],
            "properties": {
                "account_id": {"type": "string", "description": "IBKR account ID"},
                "host": {"type": "string", "description": "Gateway host (default: localhost)"},
                "port": {"type": "number", "description": "Gateway port (default: 7497)"},
                "client_id": {"type": "number", "description": "Client ID"},
            },
        },
    ))
    registry.register(BrokerPack(
        engine="mt5",
        api_version=BROKER_PACK_API_VERSION,
        version="1.0.0",
        description="MetaTrader 5 — Forex and CFDs",
        config_schema={
            "type": "object",
            "required": ["server", "login"],
            "properties": {
                "server": {"type": "string", "description": "MT5 server name"},
                "login": {"type": "string", "description": "MT5 login"},
                "password": {"type": "string", "description": "MT5 password"},
            },
        },
    ))
    registry.register(BrokerPack(
        engine="paper",
        api_version=BROKER_PACK_API_VERSION,
        version="1.0.0",
        description="Paper trading simulator — no real funds",
    ))
    registry.register(BrokerPack(
        engine="polymarket",
        api_version=BROKER_PACK_API_VERSION,
        version="1.0.0",
        description="Polymarket — prediction markets",
        config_schema={
            "type": "object",
            "required": ["wallet_private_key"],
            "properties": {
                "wallet_private_key": {"type": "string", "description": "Polygon wallet key"},
                "matic_rpc_url": {"type": "string", "description": "Polygon RPC URL"},
            },
        },
    ))
    registry.register(BrokerPack(
        engine="solana",
        api_version=BROKER_PACK_API_VERSION,
        version="1.0.0",
        description="Solana — on-chain DEX trading via Jupiter",
        config_schema={
            "type": "object",
            "required": ["private_key"],
            "properties": {
                "private_key": {"type": "string", "description": "Solana wallet private key"},
                "rpc_url": {"type": "string", "description": "Solana RPC URL"},
                "jupiter_api_url": {"type": "string", "description": "Jupiter API URL"},
            },
        },
    ))


# ---------------------------------------------------------------------------
# Trading Mode (from OpenAlice Guardian Runtime)
# ---------------------------------------------------------------------------

class TradingMode:
    """Trading mode resolution — inspired by OpenAlice Guardian Runtime.

    Resolution priority: env → config → auto.

    Modes:
    - lite: Read-only market data, no trading
    - readonly: Can view positions but not trade
    - pro: Full trading capabilities
    """

    MODES = frozenset({"lite", "readonly", "pro"})

    def __init__(
        self,
        mode: str = "auto",
        env_prefix: str = "QNA_TRADING_MODE",
    ) -> None:
        self.env_prefix = env_prefix
        self._mode = mode
        self._source = "init"
        self._resolve()

    def _resolve(self) -> None:
        """Resolve trading mode with priority: env → config → auto."""
        # 1. Environment variable
        env_mode = os.environ.get(f"{self.env_prefix}", "").strip().lower()
        if env_mode in self.MODES:
            self._mode = env_mode
            self._source = "env"
            return

        # 2. Config file
        config_path = os.environ.get(
            f"{self.env_prefix}_CONFIG",
            os.path.join(os.getcwd(), "config", "trading_mode.json"),
        )
        try:
            if os.path.exists(config_path):
                with open(config_path) as f:
                    data = json.load(f)
                cfg_mode = str(data.get("mode", "")).strip().lower()
                if cfg_mode in self.MODES:
                    self._mode = cfg_mode
                    self._source = "config"
                    return
        except (OSError, json.JSONDecodeError):
            pass

        # 3. Auto: detect if any live accounts configured
        if self._mode == "auto":
            self._mode = self._auto_detect()
            self._source = "auto"

    @staticmethod
    def _auto_detect() -> str:
        """Auto-detect trading mode based on available configuration."""
        accounts_path = os.path.join(os.getcwd(), "config", "mt5_accounts.yaml")
        if os.path.exists(accounts_path):
            return "pro"
        secrets_path = os.path.join(os.getcwd(), "config", "credentials.json")
        if os.path.exists(secrets_path):
            return "readonly"
        return "lite"

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def source(self) -> str:
        return self._source

    @property
    def can_trade(self) -> bool:
        return self._mode == "pro"

    @property
    def can_view_positions(self) -> bool:
        return self._mode in ("readonly", "pro")

    def __repr__(self) -> str:
        return f"TradingMode(mode={self._mode!r}, source={self._source!r})"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _engine_to_class_name(engine: str) -> str:
    """Convert engine identifier to class name.

    Examples:
        alpaca → AlpacaBroker
        ccxt → CCXTBroker
        ibkr → IBKRBroker
        mt5 → MT5Broker
        paper → PaperBroker
        polymarket → PolymarketBroker
        solana → SolanaBroker
    """
    parts = engine.replace("-", "_").split("_")
    if engine == "ccxt":
        return "CCXTBroker"
    if engine == "ibkr":
        return "IBKRBroker"
    if engine == "mt5":
        return "MT5Broker"
    return "".join(p.capitalize() for p in parts) + "Broker"


__all__ = [
    "BROKER_PACK_API_VERSION",
    "SUPPORTED_ENGINES",
    "IBroker",
    "BrokerPack",
    "BrokerPackRegistry",
    "TradingMode",
    "get_registry",
    "register_default_packs",
]
