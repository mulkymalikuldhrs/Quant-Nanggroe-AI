# Auto-generated archive strategy wrappers
# Each wraps an existing strategy and re-registers with 'archive_' prefix

from __future__ import annotations

from quant_nanggroe.engine.strategies.registry import StrategyRegistry

# Exclude these names (adjust as needed)
_exclude = {"archive_msnr_fixed", "archive_quarterly_fixed", "archive_smc_fixed"}

for _name in sorted(StrategyRegistry.list_strategies()):
    if _name.startswith("archive_"):
        continue
    archive_name = f"archive_{_name}"
    src_cls = StrategyRegistry.get(_name)
    if src_cls is None:
        continue

    class _ArchiveWrapper(src_cls):
        pass

    _ArchiveWrapper.name = archive_name
    _ArchiveWrapper.description = f"Archive wrapper for {_name}"

    try:
        StrategyRegistry.register(_ArchiveWrapper)
    except Exception:
        pass