# engine.strategy.loader

## Function: 

Lazy import of the strategies module.

*Line: 62*

---

## Class: 

Error loading a strategy.

*Line: 77*

---

## Class: 

Loads strategies from YAML files with inheritance support.

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

**Methods:** __init__, add_search_path, load, load_by_name, load_directory, load_templates, list_templates, list_all, get_load_errors, clear_cache, _resolve_inheritance, _find_strategy_file, _merge_configs, _compute_file_hash, check_for_changes, reload_changed

*Line: 81*

---

## Class: 

Central registry for managing loaded strategies.

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

**Methods:** __init__, _ensure_loader, register, register_or_update, unregister, get, has, list_names, list_all, list_by_tag, list_by_symbol, load_from_directory, load_templates, get_load_errors, validate_all, health, clear, create_strategy_instance

*Line: 517*

---

## Class: 

Watch for YAML file changes and auto-reload strategies.

Uses file system polling to detect changes. Can be run as an
async background task.

Example:
    >>> watcher = StrategyWatcher(registry, loader, "strategies/")
    >>> await watcher.start()  # starts watching in background
    >>> await watcher.stop()   # stops watching

**Methods:** __init__

*Line: 816*

---

## Function: 

Initialize the strategy loader.

Args:
    search_paths: List of directories to search for strategy YAML files.
                  Used for resolving base_strategy references.

*Line: 102*

---

## Function: 

Add a directory to the search path for strategy files.

Args:
    path: Directory path to add.

*Line: 117*

---

## Function: 

Load a strategy from a YAML file.

If the strategy specifies a ``base_strategy``, the base is loaded
first and merged with the child strategy.

Args:
    yaml_path: Path to the YAML strategy file.

Returns:
    Validated StrategyConfig with inheritance resolved.

Raises:
    StrategyLoadError: If loading or validation fails.

*Line: 127*

---

## Function: 

Load a strategy by name, searching all search paths.

Searches for a YAML file whose strategy name matches the given name.
Also searches the templates directory.

Args:
    name: Strategy name to search for.

Returns:
    StrategyConfig for the found strategy.

Raises:
    StrategyLoadError: If the strategy is not found.

*Line: 180*

---

## Function: 

Load all YAML strategy files from a directory.

Args:
    directory: Path to directory containing YAML strategy files.

Returns:
    List of loaded StrategyConfig instances.

*Line: 230*

---

## Function: 

Load all built-in strategy templates.

Returns:
    List of StrategyConfig instances from the templates directory.

*Line: 259*

---

## Function: 

List all available strategy templates with metadata.

Returns:
    List of dicts with 'name', 'description', 'file', 'tags' keys.

*Line: 271*

---

## Function: 

List all available strategies (templates + loaded).

Returns:
    List of dicts with strategy metadata.

*Line: 298*

---

## Function: 

Get any load errors encountered.

Returns:
    Dict mapping strategy path/name to error message.

*Line: 329*

---

## Function: 

Clear the strategy cache, forcing reload on next access.

*Line: 337*

---

## Function: 

Resolve strategy inheritance by merging with base strategy.

The child strategy's fields override the base strategy's fields.
List fields (entry_rules, exit_rules) are replaced, not merged.

Args:
    config: StrategyConfig with base_strategy reference.

Returns:
    Merged StrategyConfig.

Raises:
    StrategyLoadError: If the base strategy cannot be found or loaded.

*Line: 342*

---

## Function: 

Find a strategy YAML file by name.

Searches for files named <strategy_name>.yaml or <strategy_name>.yml
in the search paths.

Args:
    strategy_name: Strategy name to search for.

Returns:
    Path to the strategy file, or None if not found.

*Line: 390*

---

## Function: 

Merge a child strategy config with its base.

Child fields override base fields. List fields are replaced entirely.
Nested model fields (universe, risk_rules) are deep-merged.

Args:
    base: Base strategy config.
    child: Child strategy config (overrides).

Returns:
    Merged StrategyConfig.

*Line: 422*

---

## Function: 

Compute a hash of a file's contents for change detection.

Args:
    path: Path to the file.

Returns:
    MD5 hex digest of the file contents.

*Line: 462*

---

## Function: 

Check if any cached strategy files have changed on disk.

Returns:
    List of strategy names whose files have changed.

*Line: 476*

---

## Function: 

Reload all strategy files that have changed on disk.

Returns:
    List of reloaded StrategyConfig instances.

*Line: 490*

---

## Function: 

Initialize the strategy registry.

*Line: 537*

---

## Function: 

Get or create the strategy loader.

*Line: 544*

---

## Function: 

Register a strategy configuration.

Args:
    config: StrategyConfig to register.

Raises:
    ValueError: If a strategy with the same name is already registered.

*Line: 550*

---

## Function: 

Register or update a strategy configuration.

If a strategy with the same name already exists, it will be updated.

Args:
    config: StrategyConfig to register or update.

*Line: 566*

---

## Function: 

Unregister a strategy.

Args:
    name: Strategy name to unregister.

Raises:
    KeyError: If the strategy is not registered.

*Line: 582*

---

## Function: 

Get a registered strategy by name.

Args:
    name: Strategy name.

Returns:
    The StrategyConfig instance.

Raises:
    KeyError: If the strategy is not registered.

*Line: 600*

---

## Function: 

Check if a strategy is registered.

Args:
    name: Strategy name.

Returns:
    True if registered.

*Line: 616*

---

## Function: 

List registered strategy names, optionally filtered by tag.

Args:
    tag: Optional tag filter.

Returns:
    Sorted list of strategy names.

*Line: 627*

---

## Function: 

List all registered strategies.

Returns:
    List of all StrategyConfig instances.

*Line: 644*

---

## Function: 

List strategies filtered by tag.

Args:
    tag: Tag to filter by.

Returns:
    List of StrategyConfig instances matching the tag.

*Line: 652*

---

## Function: 

List strategies that include a given symbol in their universe.

Args:
    symbol: Symbol to search for.

Returns:
    List of StrategyConfig instances whose universe includes the symbol.

*Line: 666*

---

## Function: 

Load and register all strategies from a directory.

Args:
    directory: Path to directory containing YAML strategy files.

Returns:
    Number of strategies successfully registered.

*Line: 681*

---

## Function: 

Load all built-in strategy templates into the registry.

Returns:
    Number of template strategies successfully registered.

*Line: 706*

---

## Function: 

Get any load errors from the registry.

Returns:
    Dict mapping strategy name to error message.

*Line: 723*

---

## Function: 

Validate all registered strategies.

Returns:
    Dict mapping strategy name to list of validation errors.

*Line: 731*

---

## Function: 

Get registry health status.

Returns:
    Dict with registry statistics.

*Line: 744*

---

## Function: 

Clear all registered strategies.

*Line: 766*

---

## Function: 

Create a strategy instance from a registered config's strategy_type.

If the config has a strategy_type, creates the corresponding
BaseStrategy subclass using the strategy_params from the config.

Args:
    name: Strategy name in the registry.

Returns:
    A BaseStrategy subclass instance.

Raises:
    KeyError: If the strategy is not registered.
    ValueError: If the strategy has no strategy_type.

*Line: 772*

---

## Function: 

Initialize the strategy watcher.

Args:
    registry: StrategyRegistry to update on reload.
    loader: StrategyLoader for reloading changed files.
    watch_dir: Directory to watch for changes.
    poll_interval: Seconds between file change checks.
    on_reload: Optional callback called when a strategy is reloaded.

*Line: 828*

---

