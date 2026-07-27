import asyncio, logging
logging.basicConfig(level=logging.DEBUG)
from quant_nanggroe.engine_production_bridge import ProductionStrategyRunner
from quant_nanggroe.data.providers.binance import BinanceProvider
from quant_nanggroe.data.providers.base import TimeFrame

async def main():
    runner = ProductionStrategyRunner()
    print("RUNNER_STRATEGIES:", len(runner.strategies))
    prov = BinanceProvider()
    try:
        tk = await prov.get_ticker("BTCUSDT")
        print("TICKER:", tk.price if tk else None)
    except Exception as e:
        print("TICKER_ERR:", repr(e))
    try:
        oh = await prov.get_ohlcv("BTCUSDT", TimeFrame.H1, limit=100)
        print("OHLCV_LEN:", len(oh))
    except Exception as e:
        print("OHLCV_ERR:", repr(e))

asyncio.run(main())
