"""Trading Mode Configuration — System-wide trading mode enforcement.

Implements a singleton that governs whether the system can execute real trades.
All exchange creation and order execution must consult this config.

Modes:
    PAPER:      No real execution — paper broker always used. (DEFAULT)
    SIMULATION: Sandbox/testnet mode on exchanges — no real capital.
    LIVE:       Real money trading. Requires CONFIRM_LIVE_TRADING=true env var.

SAFETY: Default is PAPER. Switching to LIVE requires explicit confirmation.
This module is the SINGLE SOURCE OF TRUTH for trading mode across the system.
"""

from __future__ import annotations

import logging
import os
import sys
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class TradingMode(str, Enum):
    """Trading mode enumeration."""

    PAPER = "paper"
    SIMULATION = "simulation"
    LIVE = "live"


class LiveTradingNotConfirmedError(Exception):
    """Raised when LIVE mode is requested without CONFIRM_LIVE_TRADING=true."""

    def __init__(self) -> None:
        super().__init__(
            "LIVE trading mode requires CONFIRM_LIVE_TRADING=true environment variable. "
            "This is a SAFETY requirement — real capital is at risk."
        )


class TradingModeConfig:
    """System-wide trading mode configuration singleton.

    Reads TRADING_MODE and CONFIRM_LIVE_TRADING from environment variables.
    Defaults to PAPER mode for maximum safety.

    Usage:
        config = TradingModeConfig()
        if config.is_live:
            # This path requires CONFIRM_LIVE_TRADING=true
            ...
        else:
            # Safe — paper or simulation mode
            ...
    """

    _instance: Optional[TradingModeConfig] = None

    def __new__(cls) -> TradingModeConfig:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        # Read from environment
        raw_mode = os.environ.get("TRADING_MODE", "paper").lower().strip()
        confirm_live = os.environ.get("CONFIRM_LIVE_TRADING", "").lower().strip()

        # Validate and set mode
        try:
            self._mode = TradingMode(raw_mode)
        except ValueError:
            logger.warning(
                "Invalid TRADING_MODE='%s'. Valid options: %s. Defaulting to PAPER.",
                raw_mode,
                [m.value for m in TradingMode],
            )
            self._mode = TradingMode.PAPER

        # SAFETY: Require explicit confirmation for LIVE mode
        if self._mode == TradingMode.LIVE:
            if confirm_live != "true":
                logger.critical(
                    "SAFETY BLOCK: LIVE trading mode requested but CONFIRM_LIVE_TRADING "
                    "is not set to 'true'. Falling back to PAPER mode."
                )
                self._mode = TradingMode.PAPER
            else:
                logger.critical(
                    "⚠️  LIVE TRADING MODE ENABLED — REAL CAPITAL IS AT RISK  ⚠️"
                )

        # Print startup banner
        self._print_banner()

    def _print_banner(self) -> None:
        """Print a clear startup banner showing the trading mode."""
        mode_str = self._mode.value.upper()
        border = "=" * 60

        if self._mode == TradingMode.LIVE:
            banner = f"""
{border}
  ⚠️  TRADING MODE: {mode_str} — REAL CAPITAL AT RISK  ⚠️
  All orders will execute on LIVE exchanges.
  Ensure risk limits are properly configured.
{border}"""
        elif self._mode == TradingMode.SIMULATION:
            banner = f"""
{border}
  TRADING MODE: {mode_str} — SANDBOX/TESTNET
  Orders execute on exchange testnets. No real capital.
{border}"""
        else:
            banner = f"""
{border}
  TRADING MODE: {mode_str} — NO REAL EXECUTION
  All orders route to paper broker. Safe mode.
{border}"""

        logger.info(banner.strip())
        # Also print to stderr so it's visible even if logging is suppressed
        print(banner, file=sys.stderr)

    @property
    def mode(self) -> TradingMode:
        """Current trading mode."""
        return self._mode

    @property
    def is_live(self) -> bool:
        """Whether LIVE trading mode is active."""
        return self._mode == TradingMode.LIVE

    @property
    def is_paper(self) -> bool:
        """Whether PAPER trading mode is active."""
        return self._mode == TradingMode.PAPER

    @property
    def is_simulation(self) -> bool:
        """Whether SIMULATION trading mode is active."""
        return self._mode == TradingMode.SIMULATION

    @property
    def requires_paper_broker(self) -> bool:
        """Whether the mode forces paper broker usage."""
        return self._mode == TradingMode.PAPER

    @property
    def allows_real_execution(self) -> bool:
        """Whether real exchange execution is permitted."""
        return self._mode in (TradingMode.SIMULATION, TradingMode.LIVE)

    def validate_exchange_creation(self, exchange_name: str) -> str:
        """Validate and potentially redirect exchange creation based on mode.

        Args:
            exchange_name: Requested exchange name.

        Returns:
            The effective exchange name to use.

        Raises:
            LiveTradingNotConfirmedError: If LIVE mode without confirmation.
        """
        if self._mode == TradingMode.PAPER:
            logger.info(
                "TradingModeConfig: Redirecting '%s' to paper broker (PAPER mode)",
                exchange_name,
            )
            return "paper"
        return exchange_name

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton (for testing only)."""
        cls._instance = None

    def __repr__(self) -> str:
        return f"TradingModeConfig(mode={self._mode.value!r})"
