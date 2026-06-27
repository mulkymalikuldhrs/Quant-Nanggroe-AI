# engine.strategy.strategies.__init__

## Function: 

Create a strategy instance by name.

Args:
    name: Strategy name (must be in the registry).
    params: Optional strategy parameters.

Returns:
    Instantiated BaseStrategy subclass.

Raises:
    ValueError: If the strategy name is not registered.

*Line: 107*

---

## Function: 

List all registered strategy names.

Returns:
    Sorted list of strategy names.

*Line: 132*

---

## Function: 

Get metadata for a registered strategy.

Args:
    name: Strategy name.

Returns:
    Dict with description, asset_classes, timeframes, category.

Raises:
    ValueError: If the strategy name is not registered.

*Line: 141*

---

## Function: 

Register a new strategy class.

Args:
    name: Strategy name for the registry.
    strategy_cls: Strategy class (must extend BaseStrategy).
    metadata: Optional metadata dict.

Raises:
    TypeError: If strategy_cls does not extend BaseStrategy.

*Line: 158*

---

