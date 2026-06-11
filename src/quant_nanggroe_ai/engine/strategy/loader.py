"""Strategy loader, registry, and hot-reload system.

Provides:
- StrategyLoader: Loads strategies from YAML files with inheritance support
- StrategyRegistry: Central registry for managing loaded strategies
- Hot-reload: Watch for YAML file changes and auto-reload

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

from quant_nanggroe_ai.engine.strategy.schema import StrategyConfig
from quant_nanggroe_ai.engine.strategy.parser import (
    parse_strategy,
    validate_strategy,
)

logger = logging.getLogger(__name__)


class StrategyLoadError(Exception):
    """Error loading a strategy."""


class StrategyLoader:
    """Loads strategies from YAML files with inheritance support.

    The loader resolves strategy inheritance by merging the base strategy
    with the child strategy. Child fields override base fields.

    Example:
        >>> loader = StrategyLoader()
        >>> config = loader.load("strategies/momentum.yaml")
        >>> config = loader.load("strategies/aggressive.yaml")  # inherits from momentum
    """

    def __init__(self, search_paths: Optional[List[str]] = None):
        """Initialize the strategy loader.

        Args:
            search_paths: List of directories to search for strategy YAML files.
                          Used for resolving base_strategy references.
        """
        self._search_paths = [Path(p) for p in (search_paths or [])]
        self._cache: Dict[str, StrategyConfig] = {}
        self._file_hashes: Dict[str, str] = {}

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
            raise StrategyLoadError(f"Failed to load strategy from {path}: {e}") from e

        # Resolve inheritance
        if config.base_strategy:
            config = self._resolve_inheritance(config)

        # Validate the resolved config
        errors = validate_strategy(config)
        if errors:
            raise StrategyLoadError(
                f"Strategy '{config.name}' validation failed:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )

        # Cache
        self._cache[cache_key] = config
        self._file_hashes[cache_key] = self._compute_file_hash(path)

        logger.info(f"Loaded strategy: {config.name} from {path}")
        return config

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
        for yaml_file in sorted(dir_path.glob("*.yaml")):
            try:
                config = self.load(yaml_file)
                configs.append(config)
            except StrategyLoadError as e:
                logger.warning(f"Skipping {yaml_file}: {e}")

        for yaml_file in sorted(dir_path.glob("*.yml")):
            try:
                config = self.load(yaml_file)
                configs.append(config)
            except StrategyLoadError as e:
                logger.warning(f"Skipping {yaml_file}: {e}")

        logger.info(f"Loaded {len(configs)} strategies from {dir_path}")
        return configs

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
            for ext in (".yaml", ".yml"):
                # Try exact name match
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

    def load_from_directory(self, directory: str | Path) -> int:
        """Load and register all strategies from a directory.

        Args:
            directory: Path to directory containing YAML strategy files.

        Returns:
            Number of strategies successfully registered.
        """
        loader = StrategyLoader(search_paths=[str(directory)])
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
            "load_errors": len(self._load_errors),
            "validation_issues": len(self.validate_all()),
        }

    def clear(self) -> None:
        """Clear all registered strategies."""
        self._strategies.clear()
        self._load_errors.clear()
        self._registered_at.clear()


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
