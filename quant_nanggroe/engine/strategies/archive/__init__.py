# ponytail: expose archive strategies to AutoRegistry
# Auto-import all archive modules so @StrategyRegistry.register decorators fire.
import importlib, pkgutil, logging
log = logging.getLogger('archive_init')
_pkg_path = __path__[0]
for mod in sorted(pkgutil.iter_modules([_pkg_path])):
    name = mod.name
    if name.startswith('_'):
        continue
    try:
        importlib.import_module(f'quant_nanggroe.engine.strategies.archive.{name}')
    except Exception as e:
        log.debug('Archive import %s failed: %s', name, e)
