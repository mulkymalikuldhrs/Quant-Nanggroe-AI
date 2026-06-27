# engine.strategy.parser

## Function: 

Parse a YAML strategy file into a validated StrategyConfig.

Args:
    yaml_path: Path to the YAML strategy file.

Returns:
    Validated StrategyConfig instance.

Raises:
    FileNotFoundError: If the YAML file does not exist.
    ValueError: If the YAML content fails validation.
    yaml.YAMLError: If the file is not valid YAML.

*Line: 48*

---

## Function: 

Parse a YAML strategy string into a validated StrategyConfig.

Args:
    yaml_content: YAML strategy content as a string.

Returns:
    Validated StrategyConfig instance.

Raises:
    ValueError: If the YAML content fails validation.
    yaml.YAMLError: If the content is not valid YAML.

*Line: 88*

---

## Function: 

Validate a StrategyConfig for semantic correctness.

Performs checks beyond Pydantic schema validation:
- Entry rules reference valid indicators
- Exit rules are consistent (not contradictory)
- Risk rules are reasonable
- Universe is non-empty after filtering
- Timeframe is valid

Args:
    config: StrategyConfig to validate.

Returns:
    List of validation error strings. Empty list means valid.

*Line: 120*

---

## Function: 

Generate executable Python code from a StrategyConfig.

Creates a self-contained Python function that implements the strategy's
entry and exit logic. The generated code uses pandas and numpy
for indicator computation and signal generation.

Args:
    config: StrategyConfig to convert to code.

Returns:
    Python code string that defines a signal generator function.

*Line: 220*

---

## Function: 

Convert a strategy name to a valid Python class name.

Args:
    name: Strategy name string.

Returns:
    Valid Python identifier (CamelCase).

*Line: 380*

---

## Function: 

Convert an indicator name and params to a pandas computation expression.

Args:
    indicator: Indicator name (e.g., 'rsi', 'sma', 'volume').
    params: Indicator parameters (e.g., {'period': 14}).

Returns:
    Python code string for computing the indicator.

*Line: 396*

---

