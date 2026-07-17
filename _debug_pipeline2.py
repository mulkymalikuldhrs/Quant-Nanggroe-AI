#!/usr/bin/env python3
"""Debug: strip all try/except to see real error."""
import asyncio, logging, os
logging.basicConfig(level=logging.INFO, format='%(name)s | %(levelname)s | %(message)s')
os.environ.pop('OPENAI_API_KEY', None)

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
    
    # Manually call _deterministic_pipeline directly
    from quant_nanggroe.exchange.paper_broker import PaperExchangeBroker
    
    broker = PaperExchangeBroker()
    broker.set_price('BTC-USD', 50000.0)
    
    rs = worker._risk_manager.state
    print(f"rs: peak={rs.peak_equity}, daily={rs.daily_pnl}", flush=True)
    
    # Test gate evaluate directly in asyncio context, without any try/except
    print("Testing gate evaluate...", flush=True)
    gate_result = worker._risk_manager.check_gate.evaluate(
        symbol='BTC-USD',
        account_balance=rs.peak_equity if rs.peak_equity > 0 else 1_000_000.0,
        daily_pnl=float(rs.daily_pnl),
        weekly_pnl=float(rs.weekly_pnl),
        trade_count_today=int(rs.trade_count_today),
    )
    print(f"Gate: {gate_result['verdict']}", flush=True)
    
    # Run the full deterministic pipeline
    print("Testing full pipeline...", flush=True)
    result = await worker._deterministic_pipeline('BTC-USD', {})
    print(f"Pipeline result: {result['decision_action']}", flush=True)
    
asyncio.run(test())
