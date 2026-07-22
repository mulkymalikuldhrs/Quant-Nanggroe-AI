import sys, os, traceback
sys.path.insert(0, r"E:\trading")

# Minimal env to import the broker without full app
os.environ.setdefault("QNAI_JWT_SECRET", "test-secret-for-repro-only")

from quant_nanggroe.exchange.manager import ExchangeManager
from quant_nanggroe.exchange.factory import ExchangeFactory

async def main():
    em = ExchangeManager()
    factory = ExchangeFactory()
    broker = factory.create("mt5", api_key="123", api_secret="x", passphrase="Demo")
    em.register("mt5_0", broker, role="primary")
    # mark healthy+connected so _get_data_exchange returns it (mimics live state)
    reg = em._registrations["mt5_0"]
    reg.healthy = True
    reg.connected = True
    try:
        pos = await em.get_positions("mt5_0")
        print("RESULT:", pos)
    except Exception as e:
        print("EXC TYPE:", type(e).__name__)
        print("EXC:", e)
        traceback.print_exc()

import asyncio
asyncio.run(main())
