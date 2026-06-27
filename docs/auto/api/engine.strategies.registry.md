# engine.strategies.registry

## Class: 

Registry for trading strategy implementations.

Automatically discovers and registers strategies.
Use the ``register`` decorator to add new strategies.

**Methods:** register, get, list_strategies, create, create_all, count

*Line: 15*

---

## Function: 

Register a strategy class.

Usage::

    @StrategyRegistry.register
    class WyckoffStrategy(Strategy):
        name = "wyckoff"
        ...

*Line: 23*

---

## Function: 

Get a registered strategy class by name.

*Line: 37*

---

## Function: 

List all registered strategy names.

*Line: 42*

---

## Function: 

Create a strategy instance by name.

*Line: 47*

---

## Function: 

Create instances of all registered strategies.

*Line: 56*

---

## Function: 

Return number of registered strategies.

*Line: 66*

---

