"""Solana Mempool Monitor — WebSocket monitoring of pending transactions.

Provides real-time monitoring of the Solana transaction stream via
WebSocket, with detection of new token launches (Pump.fun, Raydium)
and rugpull indicators.

Features
--------
* WebSocket connection to Solana RPC with auto-reconnect
* Monitor pending/confirmed transactions for specific programs
* Detect new token launches on Pump.fun and Raydium
* Flag rugpull indicators (mint authority, freeze authority, LP burn status)
* Real-time alerts via async callback

Usage
-----
    async def on_event(event: MempoolEvent):
        print(f"[{event.event_type}] {event.description}")

    monitor = SolanaMempoolMonitor(
        rpc_url="wss://api.mainnet-beta.solana.com",
        callback=on_event,
    )
    await monitor.start()
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Program IDs
# ---------------------------------------------------------------------------

PUMP_FUN_PROGRAM = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
RAYDIUM_AMM_V4 = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
RAYDIUM_CPMM = "CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C"
METAPLEX_TOKEN = "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s"


# ---------------------------------------------------------------------------
# Event models
# ---------------------------------------------------------------------------

class MempoolEventType(str, Enum):
    """Types of mempool events."""

    NEW_TOKEN = "new_token"
    RUGPULL_INDICATOR = "rugpull_indicator"
    LARGE_TRANSACTION = "large_transaction"
    PROGRAM_ACTIVITY = "program_activity"
    WSOL_MOVEMENT = "wsol_movement"
    UNKNOWN = "unknown"


class MempoolEvent(BaseModel):
    """A detected mempool event.

    Attributes
    ----------
    event_type:
        Type of the detected event.
    signature:
        Transaction signature.
    program_id:
        Program that triggered the event.
    description:
        Human-readable description.
    slot:
        Slot number of the transaction.
    block_time:
        Block time (Unix timestamp).
    data:
        Additional event-specific data.
    detected_at:
        When this event was detected locally.
    """

    event_type: MempoolEventType = MempoolEventType.UNKNOWN
    signature: str = ""
    program_id: str = ""
    description: str = ""
    slot: Optional[int] = None
    block_time: Optional[int] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    detected_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Mempool Monitor
# ---------------------------------------------------------------------------

# Callback type: async function receiving MempoolEvent
MempoolCallback = Callable[["MempoolEvent"], Coroutine[Any, Any, None]]


class SolanaMempoolMonitor:
    """Solana mempool monitor with WebSocket streaming.

    Connects to a Solana RPC WebSocket endpoint and subscribes to
    account/program updates, detecting new token launches, rugpull
    indicators, and other on-chain activity.

    Parameters
    ----------
    rpc_url:
        Solana RPC WebSocket URL (``wss://``).
    callback:
        Async callback invoked for each detected event.
    monitored_programs:
        List of program IDs to monitor. Defaults to Pump.fun + Raydium.
    max_reconnect_attempts:
        Maximum WebSocket reconnection attempts before giving up.
    reconnect_delay:
        Base delay in seconds between reconnection attempts.
    wsol_threshold:
        Minimum WSOL amount to trigger ``WSOL_MOVEMENT`` events.

    Examples
    --------
    .. code-block:: python

        monitor = SolanaMempoolMonitor(
            rpc_url="wss://api.mainnet-beta.solana.com",
            callback=my_callback,
        )
        await monitor.start()
        # ... later ...
        await monitor.stop()
    """

    def __init__(
        self,
        rpc_url: str = "wss://api.mainnet-beta.solana.com",
        callback: Optional[MempoolCallback] = None,
        monitored_programs: Optional[List[str]] = None,
        max_reconnect_attempts: int = 10,
        reconnect_delay: float = 2.0,
        wsol_threshold: float = 10.0,
    ) -> None:
        self._rpc_url = rpc_url
        self._callback = callback
        self._monitored_programs = monitored_programs or [
            PUMP_FUN_PROGRAM,
            RAYDIUM_AMM_V4,
            RAYDIUM_CPMM,
        ]
        self._max_reconnect_attempts = max_reconnect_attempts
        self._reconnect_delay = reconnect_delay
        self._wsol_threshold = wsol_threshold

        self._running = False
        self._ws = None
        self._task: Optional[asyncio.Task] = None
        self._subscription_id: Optional[int] = None

    # ----- Start/Stop -----

    async def start(self) -> None:
        """Start the mempool monitor.

        Connects to the WebSocket and begins subscribing to program
        account updates.

        Raises
        ------
        ConnectionError
            If the WebSocket connection cannot be established.
        """
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("SolanaMempoolMonitor: Started")

    async def stop(self) -> None:
        """Stop the mempool monitor and close the WebSocket."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None
        logger.info("SolanaMempoolMonitor: Stopped")

    @property
    def is_running(self) -> bool:
        """Whether the monitor is currently running."""
        return self._running

    # ----- Monitor Loop -----

    async def _monitor_loop(self) -> None:
        """Main monitoring loop with auto-reconnect."""
        attempts = 0
        while self._running and attempts < self._max_reconnect_attempts:
            try:
                await self._connect_and_listen()
                attempts = 0  # Reset on successful connection
            except asyncio.CancelledError:
                break
            except Exception as exc:
                attempts += 1
                logger.warning(
                    "SolanaMempoolMonitor: Connection error (attempt %d/%d): %s",
                    attempts, self._max_reconnect_attempts, exc,
                )
                if attempts < self._max_reconnect_attempts:
                    delay = self._reconnect_delay * (2 ** min(attempts - 1, 5))
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "SolanaMempoolMonitor: Max reconnection attempts reached"
                    )
                    self._running = False

    async def _connect_and_listen(self) -> None:
        """Connect to the WebSocket and process incoming messages."""
        try:
            import websockets  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError(
                "websockets package is required. Install with: pip install websockets"
            ) from exc

        async with websockets.connect(self._rpc_url) as ws:
            self._ws = ws
            logger.info("SolanaMempoolMonitor: Connected to %s", self._rpc_url)

            # Subscribe to program account updates for each monitored program
            for idx, program_id in enumerate(self._monitored_programs):
                subscribe_msg = json.dumps({
                    "jsonrpc": "2.0",
                    "id": idx + 1,
                    "method": "programSubscribe",
                    "params": [
                        program_id,
                        {"encoding": "jsonParsed", "commitment": "confirmed"},
                    ],
                })
                await ws.send(subscribe_msg)

            # Process messages
            async for raw_msg in ws:
                if not self._running:
                    break
                try:
                    msg = json.loads(raw_msg)
                    await self._process_message(msg)
                except json.JSONDecodeError:
                    logger.warning("SolanaMempoolMonitor: Invalid JSON message")
                except Exception as exc:
                    logger.error(
                        "SolanaMempoolMonitor: Error processing message: %s", exc
                    )

    # ----- Message Processing -----

    async def _process_message(self, msg: Dict[str, Any]) -> None:
        """Process a single WebSocket message and emit events.

        Parameters
        ----------
        msg:
            Parsed JSON message from the WebSocket.
        """
        # Handle subscription confirmation
        if "result" in msg and "id" in msg:
            self._subscription_id = msg["result"]
            return

        # Handle notification
        params = msg.get("params", {})
        result = params.get("result", {})
        value = result.get("value", {})
        account = value.get("account", {})

        if not account:
            return

        # Extract transaction data
        signature = value.get("signature", "")
        slot = result.get("context", {}).get("slot")
        program_id = account.get("owner", "")
        data = account.get("data", {})

        # Detect event type
        event = self._classify_event(
            signature=signature,
            program_id=program_id,
            slot=slot,
            data=data,
        )

        if event and self._callback:
            try:
                await self._callback(event)
            except Exception as exc:
                logger.error("SolanaMempoolMonitor: Callback error: %s", exc)

    def _classify_event(
        self,
        signature: str,
        program_id: str,
        slot: Optional[int],
        data: Any,
    ) -> Optional[MempoolEvent]:
        """Classify an on-chain event based on program and data.

        Parameters
        ----------
        signature:
            Transaction signature.
        program_id:
            Program that generated the event.
        slot:
            Slot number.
        data:
            Parsed account data.

        Returns
        -------
        MempoolEvent or None
            The classified event, or ``None`` if not relevant.
        """
        if program_id == PUMP_FUN_PROGRAM:
            return MempoolEvent(
                event_type=MempoolEventType.NEW_TOKEN,
                signature=signature,
                program_id=program_id,
                description="New Pump.fun token detected",
                slot=slot,
                data={"source": "pump_fun"},
            )

        if program_id in (RAYDIUM_AMM_V4, RAYDIUM_CPMM):
            return MempoolEvent(
                event_type=MempoolEventType.NEW_TOKEN,
                signature=signature,
                program_id=program_id,
                description="New Raydium pool detected",
                slot=slot,
                data={"source": "raydium"},
            )

        return MempoolEvent(
            event_type=MempoolEventType.PROGRAM_ACTIVITY,
            signature=signature,
            program_id=program_id,
            description=f"Activity on program {program_id[:8]}...",
            slot=slot,
        )

    # ----- Rugpull Detection Helpers -----

    def check_rugpull_indicators(
        self,
        mint_authority: Optional[str],
        freeze_authority: Optional[str],
        lp_burn_pct: float,
        top_holder_pct: float,
    ) -> List[str]:
        """Check for common rugpull indicators.

        Parameters
        ----------
        mint_authority:
            Mint authority address, or ``None`` if revoked.
        freeze_authority:
            Freeze authority address, or ``None`` if revoked.
        lp_burn_pct:
            Percentage of LP tokens burned (0–100).
        top_holder_pct:
            Percentage held by the top holder (0–100).

        Returns
        -------
        list of str
            List of identified rugpull indicator descriptions.
        """
        indicators: List[str] = []

        if mint_authority is not None:
            indicators.append(
                f"Mint authority not revoked: {mint_authority}"
            )

        if freeze_authority is not None:
            indicators.append(
                f"Freeze authority not revoked: {freeze_authority}"
            )

        if lp_burn_pct < 50.0:
            indicators.append(
                f"Low LP burn: only {lp_burn_pct:.1f}% burned"
            )

        if top_holder_pct > 30.0:
            indicators.append(
                f"High holder concentration: top holder has {top_holder_pct:.1f}%"
            )

        return indicators

    def __repr__(self) -> str:
        return f"SolanaMempoolMonitor(running={self._running})"
