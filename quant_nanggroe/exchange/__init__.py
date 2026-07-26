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
    'order_types',
    'paper_broker',
    'polymarket_broker',
    'quantdinger_factory',
]

from . import alpaca_broker
from . import base
from . import broker_pack
from . import factory
from . import guards
from . import ibkr_broker
from . import manager
from . import mt5_broker
from . import order_types
from . import paper_broker
from . import polymarket_broker
from . import quantdinger_factory

# ccxt_broker is lazy-imported to avoid ccxt dependency errors at init time.
# Access via `exchange.get_ccxt_broker()` or `from exchange.ccxt_broker import CCXTBroker`.
def get_ccxt_broker():
    import importlib
    try:
        return importlib.import_module('.ccxt_broker', __package__)
    except Exception:
        return None
