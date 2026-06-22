#!/usr/bin/env python3
"""Fetch current Ethereum gas price (Wei) via a public RPC endpoint."""
import json, sys, urllib.request, ssl

# Public RPC – no API key required
RPC_URL = "https://rpc.ankr.com/eth"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

payload = json.dumps({"jsonrpc":"2.0","method":"eth_gasPrice","params":[],"id":1}).encode()
req = urllib.request.Request(RPC_URL, data=payload, headers={"Content-Type":"application/json", "User-Agent": "QNA/2.0"})

try:
    with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
        data = json.loads(resp.read())
        gas_price_hex = data.get("result")
        if gas_price_hex:
            gas_price = int(gas_price_hex, 16)
            print(f"Current gas price: {gas_price} wei ({gas_price/1e9:.2f} Gwei)")
        else:
            print("No result returned from RPC", file=sys.stderr)
except Exception as e:
    print(f"Error fetching gas price: {e}", file=sys.stderr)
    sys.exit(1)
