"""
Strategies Package — auto-load semua strategi.

Loads strategies from two sources:
1. New canonical path (this directory) — 28 migrated strategies
2. Old path (engine/strategy/strategies/) — 110 legacy strategies via shim

All strategies are accessible via ``quant_nanggroe.engine.strategies.XXX``
regardless of which path they live in.
"""
import logging
import sys
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

# ── Legacy bridge: make old-path strategies accessible from new path ──
try:
    import importlib
    _this_mod = sys.modules[__name__]
    _legacy_dir = Path(__file__).parent.parent / "strategy" / "strategies"
    _bridged = 0
    for f in sorted(_legacy_dir.glob('*.py')):
        mod_name = f.stem
        if mod_name.startswith('_') or mod_name in _loaded:
            continue
        try:
            _mod = importlib.import_module(f'quant_nanggroe.engine.strategy.strategies.{mod_name}')
            setattr(_this_mod, mod_name, _mod)
            _loaded.add(mod_name)
            _bridged += 1
        except ImportError:
            pass
    log.info("Legacy bridge: %d bridged + %d canonical = %d total", _bridged, len(_modules), len(_loaded))
except Exception:
    log.debug("Legacy bridge unavailable")
