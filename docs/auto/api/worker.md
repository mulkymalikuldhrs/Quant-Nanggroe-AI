# worker

## Class: 

Runtime configuration for the trading worker.

*Line: 50*

---

## Class: 

Background trading worker — the heartbeat of the autonomous system.

Manages multiple concurrent async loops:
- Graph runner: Invokes the trading graph per symbol
- Position monitor: Updates PnL for open positions
- Portfolio snapshotter: Records periodic portfolio state
- Kill switch monitor: Checks if trading should halt

All loops are cooperative and can be gracefully stopped.

**Methods:** __init__

*Line: 75*

---

## Function: 

*Line: 88*

---

