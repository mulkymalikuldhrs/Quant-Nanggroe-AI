"""
Strategies Package — auto-load semua strategi
Semua file .py di sini akan di-import sehingga @register decorator firing
"""
import os, sys, logging
from pathlib import Path

log = logging.getLogger('strategies')

# Import all strategy modules from this directory
_strategies_dir = Path(__file__).parent

# Core strategies loaded in specific order
_strategy_modules = [
    'dhaher_system',          # Dhaher System v1.1
    'kronos_wrapper',         # Kronos Signal Provider
    'tradebobby_smc_scanner', # TradeBobby SMC Scanner
    'smc_strategy_OLD',       # SMC Old (reference)
]

# Also scan for any .py files not in the explicit list
_loaded = set(_strategy_modules)
for f in sorted(_strategies_dir.glob('*.py')):
    mod_name = f.stem
    if mod_name.startswith('_') or mod_name in _loaded:
        continue
    if mod_name not in _strategy_modules:
        _strategy_modules.append(mod_name)

for mod_name in _strategy_modules:
    try:
        __import__(f'strategies.{mod_name}', globals(), locals(), [], 0)
        log.debug(f"Loaded strategy: {mod_name}")
    except ImportError as e:
        log.debug(f"Skipped {mod_name}: {e}")
