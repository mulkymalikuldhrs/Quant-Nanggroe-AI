"""Exchange abstraction: brokers, order types, and factory."""

# Package init

__all__ = [
    'alpaca_broker',
    'base',
    'broker_pack',
    'ccxt_broker',
    'factory',
    'guards',
    'ibkr_broker',
    'manager',
    'mt5_broker',
    'paper_broker',
]

from . import (
    alpaca_broker,
    base,
    broker_pack,
    factory,
    guards,
    ibkr_broker,
    manager,
    mt5_broker,
    paper_broker,
)


# ccxt_broker is lazy-imported to avoid ccxt dependency errors at init time.
# Access via `exchange.get_ccxt_broker()` or `from exchange.ccxt_broker import CCXTBroker`.
def get_ccxt_broker():
    import importlib
    try:
        return importlib.import_module('.ccxt_broker', __package__)
    except Exception:
        return None
