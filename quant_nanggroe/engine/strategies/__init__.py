"""Strategies Package — auto-load all strategies from canonical path.

All strategies live in this directory. The legacy path
(``quant_nanggroe.engine.strategy.strategies``) is maintained via a
backward-compat shim for code that hasn't been updated yet.
"""
from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger('strategies')

_strategies_dir = Path(__file__).parent

_explicit_order = [
    'dhaher_system',
    'kronos_wrapper',
    'tradebobby_smc_scanner',
    'smc_strategy_OLD',
]

_modules = list(_explicit_order)
_loaded = set(_explicit_order)

for f in sorted(_strategies_dir.glob('*.py')):
    mod_name = f.stem
    if mod_name.startswith('_') or mod_name in _loaded:
        continue
    _modules.append(mod_name)
    _loaded.add(mod_name)

for mod_name in _modules:
    try:
        __import__(f'quant_nanggroe.engine.strategies.{mod_name}', globals(), locals(), [], 0)
    except ImportError as e:
        log.debug("Skipped %s: %s", mod_name, e)

# ── Public convenience API ────────────────────────────────────
from quant_nanggroe.engine.strategies.registry import (
    StrategyRegistry,
    create_strategy,
    get_strategy_metadata,
    list_strategies,
)

__all__ = ["create_strategy", "list_strategies", "get_strategy_metadata", "StrategyRegistry"]
