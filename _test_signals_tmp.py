import asyncio, logging
logging.basicConfig(level=logging.INFO)
from quant_nanggroe.engine.autonomous_self_loop import AutonomousSelfLoopOrchestrator

async def main():
    o = AutonomousSelfLoopOrchestrator()
    sigs = await o._get_pending_signals()
    print("SIGNALS_COUNT:", len(sigs))
    for s in sigs[:5]:
        print("  ", s)

asyncio.run(main())
