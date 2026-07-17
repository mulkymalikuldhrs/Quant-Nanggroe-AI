#!/usr/bin/env python3
"""Debug pipeline_gate_error with full traceback."""
import asyncio, logging, os, traceback

logging.basicConfig(level=logging.INFO, format='%(name)s | %(levelname)s | %(message)s')
os.environ.pop('OPENAI_API_KEY', None)

# Monkey-patch the worker's _deterministic_pipeline to catch gate error
import quant_nanggroe.worker as wmod
orig_pipeline = wmod.TradingWorker._deterministic_pipeline

async def debug_pipeline(self, symbol, snap=None):
    try:
        # Call the real method but with debug prints around gate
        print(f"\n=== DEBUG PIPELINE symbol={symbol} ===", flush=True)
        rm = self._risk_manager
        print(f"rm type: {type(rm).__name__}", flush=True)
        rs = rm.state
        print(f"rs: peak_equity={rs.peak_equity}, daily_pnl={rs.daily_pnl}", flush=True)
        
        # Test gate directly
        try:
            result = rm.check_gate.evaluate(
                symbol=symbol,
                account_balance=rs.peak_equity if rs.peak_equity > 0 else 1_000_000.0,
                daily_pnl=float(rs.daily_pnl),
                weekly_pnl=float(rs.weekly_pnl),
                trade_count_today=int(rs.trade_count_today),
            )
            print(f"Gate: {result['verdict']}", flush=True)
        except Exception as e:
            print(f"GATE ERROR: {e}", flush=True)
            traceback.print_exc()
        
        return await orig_pipeline(self, symbol, snap)
    except Exception as e:
        print(f"PIPELINE ERROR: {e}", flush=True)
        traceback.print_exc()
        raise

wmod.TradingWorker._deterministic_pipeline = debug_pipeline

from quant_nanggroe.worker import TradingWorker, WorkerConfig

async def test():
    config = WorkerConfig(
        graph_interval=5,
        position_monitor_interval=30,
        snapshot_interval=30,
        health_interval=60,
        symbols=['BTC-USD'],
        max_concurrent_graphs=1,
        graph_timeout=15,
        kill_switch_check_interval=5,
    )
    worker = TradingWorker(config=config)
    await worker.start()
    print('=== WORKER STARTED ===', flush=True)
    await asyncio.sleep(8)
    await worker.stop()
    print('=== WORKER STOPPED ===', flush=True)

asyncio.run(test())
