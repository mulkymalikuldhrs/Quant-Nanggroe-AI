#!/usr/bin/env python3
"""Check persistence backend state."""
import sys
sys.path.insert(0, ".")
from quant_nanggroe.engine.persistence import get_persistence_backend

b = get_persistence_backend()
print(f"Backend type: {type(b).__name__}")
print(f"weekly_pnl: {b.get('risk:weekly_pnl')}")
print(f"daily_pnl: {b.get('risk:daily_pnl')}")
print(f"trades_today: {b.get('risk:trades_today')}")
print(f"peak_equity: {b.get('risk:peak_equity')}")

# List all files in the persistence dir
import pathlib
for p in pathlib.Path("data/persistence").iterdir():
    print(f"  File: {p}")
