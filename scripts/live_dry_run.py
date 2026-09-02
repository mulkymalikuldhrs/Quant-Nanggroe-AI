"""Live dry-run: autodetect + get_account + get_positions without placing order."""
import os
import asyncio

os.environ["QNA_LIVE_TRADING"] = "1"

async def main():
    from quant_nanggroe.engine.execution.builder import build_execution_manager
    print("Building ExecutionManager allow_live=True ...")
    em = build_execution_manager(allow_live=True)
    brokers = em.get_brokers()
    print(f"Brokers: {list(brokers.keys())}")
    if not brokers:
        print("FAIL: no brokers wired")
        return 1
    broker = list(brokers.values())[0]
    print(f"Broker: {type(broker).__name__} name={getattr(broker, 'name', '?')}")
    try:
        acct = await broker.get_account()
        print(f"Account: balance={acct.balance} equity={acct.equity} buying_power={acct.buying_power}")
    except Exception as e:
        print(f"get_account FAIL: {type(e).__name__}: {e}")
        return 1
    try:
        positions = await broker.get_positions()
        print(f"Positions: {len(positions)}")
        for p in positions[:3]:
            print(f"  {p}")
    except Exception as e:
        print(f"get_positions FAIL: {type(e).__name__}: {e}")
        return 1
    print("DRY-RUN PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
