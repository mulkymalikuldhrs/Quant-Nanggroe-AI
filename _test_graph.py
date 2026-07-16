#!/usr/bin/env python3
"""Test the trading graph construction (no invocation)."""
import sys
sys.path.insert(0, ".")

print("=== GRAPH TEST ===", flush=True)
from quant_nanggroe.agents.graph import get_trading_graph, TradingGraph
print(f"get_trading_graph imported OK", flush=True)

# Just construct — don't invoke (avoids LLM call)
g = get_trading_graph()
print(f"Graph built OK: {type(g).__name__}", flush=True)

