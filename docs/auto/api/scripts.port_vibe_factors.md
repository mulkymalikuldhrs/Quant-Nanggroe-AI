# scripts.port_vibe_factors

## Function: 

Extract helper functions from a factor source file.

Returns (source_without_helpers, [(func_name, func_source), ...])

*Line: 15*

---

## Function: 

Transform a Vibe-Trading factor file to use unique names and correct imports.

Returns (transformed_source, [(helper_name, helper_source), ...])

*Line: 53*

---

## Function: 

Collect all factors from a Vibe-Trading zoo directory.

Returns ([(stem, transformed_source), ...], {helper_name: helper_source})

*Line: 151*

---

## Function: 

Generate a module file from a list of transformed factor sources.

*Line: 179*

---

## Function: 

*Line: 263*

---

