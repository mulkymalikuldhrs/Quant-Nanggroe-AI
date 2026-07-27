# Package init
# NOTE: Client imports are LAZY to avoid ccxt dependency issues at import time.
# Use get_client_class() or AVAILABLE_CLIENTS dict to access classes.
import logging
from typing import Dict, Type

from quant_nanggroe.exchange.clients.base_rest_client import BaseRestClient

log = logging.getLogger(__name__)

_CLIENT_MODULES: Dict[str, str] = {
    "binance": "quant_nanggroe.exchange.clients.binance_client",
    "bitfinex": "quant_nanggroe.exchange.clients.bitfinex_client",
    "bitget": "quant_nanggroe.exchange.clients.bitget_client",
    "bybit": "quant_nanggroe.exchange.clients.bybit_client",
    "coinbase": "quant_nanggroe.exchange.clients.coinbase_client",
    "gate": "quant_nanggroe.exchange.clients.gate_client",
    "kraken": "quant_nanggroe.exchange.clients.kraken_client",
    "kucoin": "quant_nanggroe.exchange.clients.kucoin_client",
    "longbridge": "quant_nanggroe.exchange.clients.longbridge_client",
    "okx": "quant_nanggroe.exchange.clients.okx_client",
}

_CLIENT_CLASS_NAMES: Dict[str, str] = {
    "binance": "BinanceClient",
    "bitfinex": "BitfinexClient",
    "bitget": "BitgetClient",
    "bybit": "BybitClient",
    "coinbase": "CoinbaseClient",
    "gate": "GateClient",
    "kraken": "KrakenClient",
    "kucoin": "KuCoinClient",
    "longbridge": "LongbridgeClient",
    "okx": "OKXClient",
}


def get_client_class(name: str) -> Type[BaseRestClient]:
    """Lazy-import a client class by name. Returns None on import failure."""
    import importlib
    mod_path = _CLIENT_MODULES.get(name)
    cls_name = _CLIENT_CLASS_NAMES.get(name)
    if not mod_path or not cls_name:
        return None
    try:
        mod = importlib.import_module(mod_path)
        cls = getattr(mod, cls_name, None)
        if cls is None:
            log.warning("Client %s: class %s not found in module", name, cls_name)
        return cls
    except Exception as e:
        log.debug("Client %s import failed (will retry on use): %s", name, e)
        return None


class _LazyClientRegistry:
    """Lazy-loading proxy for AVAILABLE_CLIENTS."""

    def __getitem__(self, name: str) -> Type[BaseRestClient]:
        cls = get_client_class(name)
        if cls is None:
            raise KeyError(f"Client '{name}' not available (import failed)")
        return cls

    def get(self, name: str, default=None) -> Type[BaseRestClient]:
        try:
            return self[name]
        except KeyError:
            return default

    def keys(self):
        return _CLIENT_MODULES.keys()

    def items(self):
        for name in self.keys():
            cls = get_client_class(name)
            if cls is not None:
                yield name, cls

    def values(self):
        for name in self.keys():
            cls = get_client_class(name)
            if cls is not None:
                yield cls

    def __len__(self):
        return len(_CLIENT_MODULES)

    def __iter__(self):
        return iter(self.keys())

    def __contains__(self, name):
        return name in _CLIENT_MODULES


AVAILABLE_CLIENTS: _LazyClientRegistry = _LazyClientRegistry()

__all__ = [
    'AVAILABLE_CLIENTS',
    'get_client_class',
    'BaseRestClient',
]
