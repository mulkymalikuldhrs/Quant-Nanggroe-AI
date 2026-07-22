import sys, os, traceback, asyncio
sys.path.insert(0, r"E:\trading")
os.environ.setdefault("QNAI_JWT_SECRET", "test-secret-for-repro-only")
PYTHONPATH_OLD = os.environ.pop("PYTHONPATH", "")

from quant_nanggroe.exchange.manager import ExchangeManager
from quant_nanggroe.exchange.factory import ExchangeFactory

async def main():
    em = ExchangeManager()
    factory = ExchangeFactory()
    broker = factory.create("mt5", api_key="123", api_secret="x", passphrase="Demo")
    em.register("mt5_0", broker, role="primary")
    reg = em._registrations["mt5_0"]
    # Mimic the LIVE server's registration state: reg.healthy=True, reg.connected=True
    # (the live server reported mt5_0 connected/healthy, but the broker object was
    #  likely never actually connected, OR connect_all mutated it)
    reg.healthy = True
    reg.connected = True
    try:
        pos = await em.get_positions("mt5_0")
        print("RESULT:", pos)
    except Exception as e:
        print("EXC TYPE:", type(e).__name__)
        print("EXC:", e)
        # is it ValueError? if so that's the 500 cause
        if isinstance(e, ValueError):
            print(">>> VALUEERROR CONFIRMED as 500 source")
        traceback.print_exc()

asyncio.run(main())
