"""Strategy loader, registry, and hot-reload system.

Provides:
- StrategyLoader: Loads strategies from YAML files with inheritance support
- StrategyRegistry: Central registry for managing loaded strategies
- Hot-reload: Watch for YAML file changes and auto-reload
- Template discovery: Auto-discover and load built-in strategy templates

Strategy Inheritance:
    Strategies can inherit from a base strategy using the ``base_strategy`` field.
    The child strategy overrides specific fields while inheriting the rest.

    .. code-block:: yaml

        # base_strategy.yaml
        name: "Base Momentum"
        entry_rules:
          - indicator: "rsi"
            operator: "lt"
            value: 30
        exit_rules:
          - indicator: "rsi"
            operator: "gt"
            value: 70
        risk_rules:
          max_position_pct: 10.0
          stop_loss_pct: 3.0
          max_daily_trades: 5

        # child_strategy.yaml
        name: "Aggressive Momentum"
        base_strategy: "Base Momentum"
        entry_rules:
          - indicator: "rsi"
            operator: "lt"
            value: 35
        risk_rules:
          max_position_pct: 20.0
          stop_loss_pct: 2.0
          max_daily_trades: 10
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set

from quant_nanggroe.engine.strategy.schema import StrategyConfig, StrategyType
from quant_nanggroe.engine.strategy.parser import (
    parse_strategy,
    validate_strategy,
)

# Lazy import for strategy implementations to avoid circular imports
_strategy_module = None


def _get_strategy_module():
    """Lazy import of the strategies module."""
    global _strategy_module
    if _strategy_module is None:
        from quant_nanggroe.engine.strategy.strategies import create_strategy as _create
        _strategy_module = _create
    return _strategy_module

logger = logging.getLogger(__name__)

# ── Default template directory ────────────────────────────────────────

_TEMPLATES_DIR = Path(__file__).parent / "templates"


class StrategyLoadError(Exception):
    """Error loading a strategy."""


class StrategyLoader:
    """Loads strategies from YAML files with inheritance support.

    The loader resolves strategy inheritance by merging the base strategy
    with the child strategy. Child fields override base fields.

    Features:
        - Load strategies from YAML files with validation
        - Strategy inheritance via ``base_strategy`` field
        - File-based caching with hash-based invalidation
        - Template directory auto-discovery
        - List all available strategies (templates + custom)

    Example:
        >>> loader = StrategyLoader()
        >>> config = loader.load("strategies/momentum.yaml")
        >>> config = loader.load("strategies/aggressive.yaml")  # inherits from momentum
        >>> templates = loader.list_templates()
        >>> all_strategies = loader.list_all()
    """

    def __init__(self, search_paths: Optional[List[str]] = None):
        """Initialize the strategy loader.

        Args:
            search_paths: List of directories to search for strategy YAML files.
                          Used for resolving base_strategy references.
        """
        self._search_paths = [Path(p) for p in (search_paths or [])]
        # Always include templates directory
        if _TEMPLATES_DIR not in self._search_paths:
            self._search_paths.append(_TEMPLATES_DIR)
        self._cache: Dict[str, StrategyConfig] = {}
        self._file_hashes: Dict[str, str] = {}
        self._load_errors: Dict[str, str] = {}

    def add_search_path(self, path: str) -> None:
        """Add a directory to the search path for strategy files.

        Args:
            path: Directory path to add.
        """
        p = Path(path)
        if p.is_dir() and p not in self._search_paths:
            self._search_paths.append(p)

    def load(self, yaml_path: str | Path) -> StrategyConfig:
        """Load a strategy from a YAML file.

        If the strategy specifies a ``base_strategy``, the base is loaded
        first and merged with the child strategy.

        Args:
            yaml_path: Path to the YAML strategy file.

        Returns:
            Validated StrategyConfig with inheritance resolved.

        Raises:
            StrategyLoadError: If loading or validation fails.
        """
        path = Path(yaml_path).resolve()

        # Check cache
        cache_key = str(path)
        if cache_key in self._cache:
            current_hash = self._compute_file_hash(path)
            if current_hash == self._file_hashes.get(cache_key):
                return self._cache[cache_key]

        try:
            config = parse_strategy(path)
        except (FileNotFoundError, ValueError) as e:
            self._load_errors[str(path)] = str(e)
            raise StrategyLoadError(f"Failed to load strategy from {path}: {e}") from e

        # Resolve inheritance
        if config.base_strategy:
            config = self._resolve_inheritance(config)

        # Validate the resolved config
        errors = validate_strategy(config)
        if errors:
            self._load_errors[config.name] = "; ".join(errors)
            raise StrategyLoadError(
                f"Strategy '{config.name}' validation failed:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )

        # Cache
        self._cache[cache_key] = config
        self._file_hashes[cache_key] = self._compute_file_hash(path)
        # Clear any previous load error for this path
        self._load_errors.pop(str(path), None)
        self._load_errors.pop(config.name, None)

        logger.info(f"Loaded strategy: {config.name} from {path}")
        return config

    def load_by_name(self, name: str) -> StrategyConfig:
        """Load a strategy by name, searching all search paths.

        Searches for a YAML file whose strategy name matches the given name.
        Also searches the templates directory.

        Args:
            name: Strategy name to search for.

        Returns:
            StrategyConfig for the found strategy.

        Raises:
            StrategyLoadError: If the strategy is not found.
        """
        # Check cache first for previously loaded strategies
        for cache_key, config in self._cache.items():
            if config.name == name:
                current_hash = self._compute_file_hash(Path(cache_key))
                if current_hash == self._file_hashes.get(cache_key):
                    return config

        # Search search paths for the strategy file
        slug = name.lower().replace(" ", "_")
        for search_path in self._search_paths:
            if not search_path.is_dir():
                continue
            for ext in (".yaml", ".yml"):
                # Try slug name
                candidate = search_path / f"{slug}{ext}"
                if candidate.exists():
                    try:
                        return self.load(candidate)
                    except StrategyLoadError:
                        pass

                # Try all files in directory and match by internal name
                for yaml_file in sorted(search_path.glob(f"*{ext}")):
                    try:
                        config = self.load(yaml_file)
                        if config.name == name:
                            return config
                    except StrategyLoadError:
                        continue

        raise StrategyLoadError(
            f"Strategy '{name}' not found in search paths: "
            f"{[str(p) for p in self._search_paths]}"
        )

    def load_directory(self, directory: str | Path) -> List[StrategyConfig]:
        """Load all YAML strategy files from a directory.

        Args:
            directory: Path to directory containing YAML strategy files.

        Returns:
            List of loaded StrategyConfig instances.
        """
        dir_path = Path(directory)
        if not dir_path.is_dir():
            raise StrategyLoadError(f"Not a directory: {dir_path}")

        configs = []
        seen_names: Set[str] = set()

        for ext in ("*.yaml", "*.yml"):
            for yaml_file in sorted(dir_path.glob(ext)):
                try:
                    config = self.load(yaml_file)
                    if config.name not in seen_names:
                        configs.append(config)
                        seen_names.add(config.name)
                except StrategyLoadError as e:
                    logger.warning(f"Skipping {yaml_file}: {e}")

        logger.info(f"Loaded {len(configs)} strategies from {dir_path}")
        return configs

    def load_templates(self) -> List[StrategyConfig]:
        """Load all built-in strategy templates.

        Returns:
            List of StrategyConfig instances from the templates directory.
        """
        if not _TEMPLATES_DIR.is_dir():
            logger.warning(f"Templates directory not found: {_TEMPLATES_DIR}")
            return []

        return self.load_directory(_TEMPLATES_DIR)

    def list_templates(self) -> List[Dict[str, str]]:
        """List all available strategy templates with metadata.

        Returns:
            List of dicts with 'name', 'description', 'file', 'tags' keys.
        """
        if not _TEMPLATES_DIR.is_dir():
            return []

        templates = []
        for ext in ("*.yaml", "*.yml"):
            for yaml_file in sorted(_TEMPLATES_DIR.glob(ext)):
                try:
                    config = self.load(yaml_file)
                    templates.append({
                        "name": config.name,
                        "description": config.description,
                        "file": yaml_file.name,
                        "tags": config.tags,
                        "timeframe": config.timeframe,
                        "symbols": config.universe.symbols,
                    })
                except StrategyLoadError as e:
                    logger.warning(f"Error listing template {yaml_file}: {e}")

        return templates

    def list_all(self) -> List[Dict[str, str]]:
        """List all available strategies (templates + loaded).

        Returns:
            List of dicts with strategy metadata.
        """
        seen_names: Set[str] = set()
        strategies: List[Dict[str, str]] = []

        # Templates first
        for template in self.list_templates():
            if template["name"] not in seen_names:
                strategies.append({**template, "source": "template"})
                seen_names.add(template["name"])

        # Then cached strategies
        for cache_key, config in self._cache.items():
            if config.name not in seen_names:
                strategies.append({
                    "name": config.name,
                    "description": config.description,
                    "file": Path(cache_key).name,
                    "tags": config.tags,
                    "timeframe": config.timeframe,
                    "symbols": config.universe.symbols,
                    "source": "custom",
                })
                seen_names.add(config.name)

        return strategies

    def get_load_errors(self) -> Dict[str, str]:
        """Get any load errors encountered.

        Returns:
            Dict mapping strategy path/name to error message.
        """
        return dict(self._load_errors)

    def clear_cache(self) -> None:
        """Clear the strategy cache, forcing reload on next access."""
        self._cache.clear()
        self._file_hashes.clear()

    def _resolve_inheritance(self, config: StrategyConfig) -> StrategyConfig:
        """Resolve strategy inheritance by merging with base strategy.

        The child strategy's fields override the base strategy's fields.
        List fields (entry_rules, exit_rules) are replaced, not merged.

        Args:
            config: StrategyConfig with base_strategy reference.

        Returns:
            Merged StrategyConfig.

        Raises:
            StrategyLoadError: If the base strategy cannot be found or loaded.
        """
        base_name = config.base_strategy
        if not base_name:
            return config

        # Detect circular inheritance
        chain: Set[str] = {config.name}

        # Search for base strategy file
        base_path = self._find_strategy_file(base_name)
        if not base_path:
            raise StrategyLoadError(
                f"Base strategy '{base_name}' not found in search paths: "
                f"{[str(p) for p in self._search_paths]}"
            )

        # Load base (may be recursive)
        try:
            base_config = self.load(base_path)
        except StrategyLoadError as e:
            raise StrategyLoadError(
                f"Failed to load base strategy '{base_name}': {e}"
            ) from e

        # Check for circular inheritance
        if base_config.name in chain:
            raise StrategyLoadError(
                f"Circular inheritance detected: '{config.name}' -> '{base_config.name}'"
            )

        # Merge: child overrides base
        merged = self._merge_configs(base_config, config)
        return merged

    def _find_strategy_file(self, strategy_name: str) -> Optional[Path]:
        """Find a strategy YAML file by name.

        Searches for files named <strategy_name>.yaml or <strategy_name>.yml
        in the search paths.

        Args:
            strategy_name: Strategy name to search for.

        Returns:
            Path to the strategy file, or None if not found.
        """
        # Normalize name for file matching
        slug = strategy_name.lower().replace(" ", "_")

        for search_path in self._search_paths:
            if not search_path.is_dir():
                continue
            for ext in (".yaml", ".yml"):
                # Try slug name match
                candidate = search_path / f"{slug}{ext}"
                if candidate.exists():
                    return candidate

                # Try original name
                candidate = search_path / f"{strategy_name}{ext}"
                if candidate.exists():
                    return candidate

        return None

    @staticmethod
    def _merge_configs(
        base: StrategyConfig, child: StrategyConfig
    ) -> StrategyConfig:
        """Merge a child strategy config with its base.

        Child fields override base fields. List fields are replaced entirely.
        Nested model fields (universe, risk_rules) are deep-merged.

        Args:
            base: Base strategy config.
            child: Child strategy config (overrides).

        Returns:
            Merged StrategyConfig.
        """
        # Start with base config as dict
        merged_data = base.model_dump()

        # Override with child's non-default fields
        child_data = child.model_dump()

        for key, value in child_data.items():
            if key == "base_strategy":
                continue  # Don't carry over inheritance reference
            if key == "name":
                merged_data["name"] = value  # Always use child's name
                continue

            # For list fields, replace if non-empty
            if isinstance(value, list) and len(value) > 0:
                merged_data[key] = value
            elif not isinstance(value, list) and value is not None:
                # For model fields, override if non-default
                base_value = merged_data.get(key)
                if value != base_value:
                    merged_data[key] = value

        return StrategyConfig(**merged_data)

    @staticmethod
    def _compute_file_hash(path: Path) -> str:
        """Compute a hash of a file's contents for change detection.

        Args:
            path: Path to the file.

        Returns:
            MD5 hex digest of the file contents.
        """
        try:
            return hashlib.md5(path.read_bytes()).hexdigest()
        except OSError:
            return ""

    def check_for_changes(self) -> List[str]:
        """Check if any cached strategy files have changed on disk.

        Returns:
            List of strategy names whose files have changed.
        """
        changed = []
        for cache_key, config in self._cache.items():
            path = Path(cache_key)
            current_hash = self._compute_file_hash(path)
            if current_hash != self._file_hashes.get(cache_key, ""):
                changed.append(config.name)
        return changed

    def reload_changed(self) -> List[StrategyConfig]:
        """Reload all strategy files that have changed on disk.

        Returns:
            List of reloaded StrategyConfig instances.
        """
        changed_names = self.check_for_changes()
        reloaded = []

        for cache_key in list(self._cache.keys()):
            config = self._cache[cache_key]
            if config.name in changed_names:
                try:
                    # Remove from cache to force reload
                    del self._cache[cache_key]
                    if cache_key in self._file_hashes:
                        del self._file_hashes[cache_key]

                    new_config = self.load(cache_key)
                    reloaded.append(new_config)
                    logger.info(f"Hot-reloaded strategy: {new_config.name}")
                except StrategyLoadError as e:
                    logger.error(f"Failed to reload {cache_key}: {e}")

        return reloaded


class StrategyRegistry:
    """Central registry for managing loaded strategies.

    Provides strategy lookup, listing, and lifecycle management.
    Thread-safe for concurrent access.

    Features:
        - Register/unregister strategies
        - Look up by name or tag
        - Load from directory (including templates)
        - Validate all registered strategies
        - Health status monitoring

    Example:
        >>> registry = StrategyRegistry()
        >>> registry.register(config)
        >>> config = registry.get("Momentum Alpha")
        >>> names = registry.list_names()
    """

    def __init__(self) -> None:
        """Initialize the strategy registry."""
        self._strategies: Dict[str, StrategyConfig] = {}
        self._load_errors: Dict[str, str] = {}
        self._registered_at: Dict[str, float] = {}
        self._loader: Optional[StrategyLoader] = None

    def _ensure_loader(self) -> StrategyLoader:
        """Get or create the strategy loader."""
        if self._loader is None:
            self._loader = StrategyLoader()
        return self._loader

    def register(self, config: StrategyConfig) -> None:
        """Register a strategy configuration.

        Args:
            config: StrategyConfig to register.

        Raises:
            ValueError: If a strategy with the same name is already registered.
        """
        if config.name in self._strategies:
            raise ValueError(f"Strategy '{config.name}' is already registered")

        self._strategies[config.name] = config
        self._registered_at[config.name] = time.time()
        logger.info(f"Registered strategy: {config.name}")

    def register_or_update(self, config: StrategyConfig) -> None:
        """Register or update a strategy configuration.

        If a strategy with the same name already exists, it will be updated.

        Args:
            config: StrategyConfig to register or update.
        """
        is_update = config.name in self._strategies
        self._strategies[config.name] = config
        self._registered_at[config.name] = time.time()
        if is_update:
            logger.info(f"Updated strategy: {config.name}")
        else:
            logger.info(f"Registered strategy: {config.name}")

    def unregister(self, name: str) -> None:
        """Unregister a strategy.

        Args:
            name: Strategy name to unregister.

        Raises:
            KeyError: If the strategy is not registered.
        """
        if name not in self._strategies:
            raise KeyError(f"Strategy '{name}' not found in registry")
        del self._strategies[name]
        if name in self._registered_at:
            del self._registered_at[name]
        if name in self._load_errors:
            del self._load_errors[name]
        logger.info(f"Unregistered strategy: {name}")

    def get(self, name: str) -> StrategyConfig:
        """Get a registered strategy by name.

        Args:
            name: Strategy name.

        Returns:
            The StrategyConfig instance.

        Raises:
            KeyError: If the strategy is not registered.
        """
        if name not in self._strategies:
            raise KeyError(f"Strategy '{name}' not found in registry")
        return self._strategies[name]

    def has(self, name: str) -> bool:
        """Check if a strategy is registered.

        Args:
            name: Strategy name.

        Returns:
            True if registered.
        """
        return name in self._strategies

    def list_names(self, tag: Optional[str] = None) -> List[str]:
        """List registered strategy names, optionally filtered by tag.

        Args:
            tag: Optional tag filter.

        Returns:
            Sorted list of strategy names.
        """
        if tag is None:
            return sorted(self._strategies.keys())

        return sorted(
            name for name, config in self._strategies.items()
            if tag.lower() in [t.lower() for t in config.tags]
        )

    def list_all(self) -> List[StrategyConfig]:
        """List all registered strategies.

        Returns:
            List of all StrategyConfig instances.
        """
        return list(self._strategies.values())

    def list_by_tag(self, tag: str) -> List[StrategyConfig]:
        """List strategies filtered by tag.

        Args:
            tag: Tag to filter by.

        Returns:
            List of StrategyConfig instances matching the tag.
        """
        return [
            config for config in self._strategies.values()
            if tag.lower() in [t.lower() for t in config.tags]
        ]

    def list_by_symbol(self, symbol: str) -> List[StrategyConfig]:
        """List strategies that include a given symbol in their universe.

        Args:
            symbol: Symbol to search for.

        Returns:
            List of StrategyConfig instances whose universe includes the symbol.
        """
        symbol_upper = symbol.upper()
        return [
            config for config in self._strategies.values()
            if symbol_upper in config.universe.symbols
        ]

    def load_from_directory(self, directory: str | Path) -> int:
        """Load and register all strategies from a directory.

        Args:
            directory: Path to directory containing YAML strategy files.

        Returns:
            Number of strategies successfully registered.
        """
        loader = self._ensure_loader()
        configs = loader.load_directory(directory)

        count = 0
        for config in configs:
            try:
                self.register(config)
                count += 1
            except ValueError:
                # Already registered, update instead
                self._strategies[config.name] = config
                count += 1
                logger.warning(f"Updated existing strategy: {config.name}")

        return count

    def load_templates(self) -> int:
        """Load all built-in strategy templates into the registry.

        Returns:
            Number of template strategies successfully registered.
        """
        loader = self._ensure_loader()
        configs = loader.load_templates()

        count = 0
        for config in configs:
            self.register_or_update(config)
            count += 1

        logger.info(f"Loaded {count} strategy templates into registry")
        return count

    def get_load_errors(self) -> Dict[str, str]:
        """Get any load errors from the registry.

        Returns:
            Dict mapping strategy name to error message.
        """
        return dict(self._load_errors)

    def validate_all(self) -> Dict[str, List[str]]:
        """Validate all registered strategies.

        Returns:
            Dict mapping strategy name to list of validation errors.
        """
        results = {}
        for name, config in self._strategies.items():
            errors = validate_strategy(config)
            if errors:
                results[name] = errors
        return results

    def health(self) -> Dict:
        """Get registry health status.

        Returns:
            Dict with registry statistics.
        """
        return {
            "total_strategies": len(self._strategies),
            "strategy_names": list(self._strategies.keys()),
            "tags": sorted(set(
                tag
                for config in self._strategies.values()
                for tag in config.tags
            )),
            "load_errors": len(self._load_errors),
            "validation_issues": len(self.validate_all()),
            "templates_loaded": sum(
                1 for c in self._strategies.values()
                if any(t in c.tags for t in ["momentum", "trend", "mean-reversion", "crypto", "forex", "factor"])
            ),
        }

    def clear(self) -> None:
        """Clear all registered strategies."""
        self._strategies.clear()
        self._load_errors.clear()
        self._registered_at.clear()

    def create_strategy_instance(self, name: str):
        """Create a strategy instance from a registered config's strategy_type.

        If the config has a strategy_type, creates the corresponding
        BaseStrategy subclass using the strategy_params from the config.

        Args:
            name: Strategy name in the registry.

        Returns:
            A BaseStrategy subclass instance.

        Raises:
            KeyError: If the strategy is not registered.
            ValueError: If the strategy has no strategy_type.
        """
        if name not in self._strategies:
            raise KeyError(f"Strategy '{name}' not found in registry")

        config = self._strategies[name]
        if config.strategy_type is None:
            raise ValueError(
                f"Strategy '{name}' has no strategy_type. "
                f"Set strategy_type to create a strategy instance."
            )

        create_fn = _get_strategy_module()
        strategy_name = config.strategy_type.value  # Convert enum to string
        # Map from StrategyType enum value to registry name
        type_to_name = {
            "mean_reversion": "MeanReversion",
            "momentum": "Momentum",
            "pairs_trading": "PairsTrading",
            "volatility_arbitrage": "VolatilityArbitrage",
            "statistical_arbitrage": "StatisticalArbitrage",
            "market_making": "MarketMaking",
            "regime_based": "RegimeBased",
            "crypto_specific": "CryptoSpecific",
        }

        registry_name = type_to_name.get(strategy_name, strategy_name)
        return create_fn(registry_name, params=config.strategy_params)


class StrategyWatcher:
    """Watch for YAML file changes and auto-reload strategies.

    Uses file system polling to detect changes. Can be run as an
    async background task.

    Example:
        >>> watcher = StrategyWatcher(registry, loader, "strategies/")
        >>> await watcher.start()  # starts watching in background
        >>> await watcher.stop()   # stops watching
    """

    def __init__(
        self,
        registry: StrategyRegistry,
        loader: StrategyLoader,
        watch_dir: str | Path,
        poll_interval: float = 5.0,
        on_reload: Optional[Callable[[StrategyConfig], None]] = None,
    ):
        """Initialize the strategy watcher.

        Args:
            registry: StrategyRegistry to update on reload.
            loader: StrategyLoader for reloading changed files.
            watch_dir: Directory to watch for changes.
            poll_interval: Seconds between file change checks.
            on_reload: Optional callback called when a strategy is reloaded.
        """
        self._registry = registry
        self._loader = loader
        self._watch_dir = Path(watch_dir)
        self._poll_interval = poll_interval
        self._on_reload = on_reload
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start watching for file changes."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._watch_loop())
        logger.info(f"Started strategy watcher on {self._watch_dir}")

    async def stop(self) -> None:
        """Stop watching for file changes."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Stopped strategy watcher")

    async def _watch_loop(self) -> None:
        """Main watch loop that polls for file changes."""
        while self._running:
            try:
                changed = self._loader.reload_changed()
                for config in changed:
                    # Update registry
                    self._registry._strategies[config.name] = config
                    if self._on_reload:
                        self._on_reload(config)
            except Exception as e:
                logger.error(f"Strategy watcher error: {e}")

            await asyncio.sleep(self._poll_interval)
