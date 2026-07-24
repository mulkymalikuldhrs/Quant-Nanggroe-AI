"""Run one cycle of the autonomous pipeline — example usage."""
import asyncio
import logging

logging.basicConfig(level=logging.INFO)


async def main():
    try:
        from quant_nanggroe.engine.agentic.autonomous import AutonomousPipeline

        pipeline = AutonomousPipeline()
        await pipeline.initialize()

        print("Pipeline initialized, running one cycle...")
        result = await pipeline.run_once()

        print(f"Cycle complete: {result.get('status', 'unknown')}")
        print(f"Signals generated: {len(result.get('signals', []))}")
        print(f"Trades executed: {len(result.get('trades', []))}")

    except ImportError as e:
        print(f"Could not import QNA modules: {e}")
    except Exception as e:
        print(f"Pipeline run failed (expected if no MT5/broker): {e}")


if __name__ == "__main__":
    asyncio.run(main())
