# exchange.solana.mempool

## Class: 

Types of mempool events.

*Line: 54*

---

## Class: 

A detected mempool event.

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

*Line: 65*

---

## Class: 

Solana mempool monitor with WebSocket streaming.

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

**Methods:** __init__, is_running, _classify_event, check_rugpull_indicators, __repr__

*Line: 108*

---

## Function: 

*Line: 143*

---

## Function: 

Whether the monitor is currently running.

*Line: 206*

---

## Function: 

Classify an on-chain event based on program and data.

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

*Line: 320*

---

## Function: 

Check for common rugpull indicators.

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

*Line: 375*

---

## Function: 

*Line: 424*

---

