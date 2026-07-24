"""Generate a basic trading signal — example usage of strategy API."""
import logging

logging.basicConfig(level=logging.INFO)

try:
    from quant_nanggroe.engine.strategy.strategies import create_strategy, list_strategies

    strategies = list_strategies()
    print(f"Available strategies ({len(strategies)}): {strategies[:5]}...")

    strategy = create_strategy("momentum")
    signal = strategy.generate(symbol="BTCUSD")
    print(f"Signal for BTCUSD: direction={signal.direction}, confidence={signal.confidence:.2f}")

except ImportError as e:
    print(f"Could not import QNA modules: {e}")
    print("Make sure QNA is installed: pip install -e .")
except Exception as e:
    print(f"Signal generation failed (expected if no data source): {e}")
