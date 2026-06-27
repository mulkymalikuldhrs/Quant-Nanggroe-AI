# security.keyvault

## Class: 

Raised when a required secret is not found in environment variables.

**Methods:** __init__

*Line: 37*

---

## Class: 

Secure secrets manager — environment variables only.

All secrets are loaded from ``os.environ``. There is no fallback
to config files, .env files, or hardcoded defaults.

Examples
--------
.. code-block:: python

    vault = KeyVault()

    # Required secret — raises if missing
    api_key = vault.get_secret("ALPACA_API_KEY")

    # Optional secret — returns None or default
    redis_url = vault.get_optional_secret("REDIS_URL", default="redis://localhost:6379")

    # Check if a secret exists
    if vault.has_secret("BINANCE_API_KEY"):
        key = vault.get_secret("BINANCE_API_KEY")

**Methods:** __init__, get_secret, get_optional_secret, has_secret, require_secrets, clear_cache, mask_value, __repr__

*Line: 48*

---

## Function: 

*Line: 40*

---

## Function: 

*Line: 71*

---

## Function: 

Get a secret from environment variables.

Parameters
----------
key_name:
    Environment variable name.
required:
    If ``True`` (default), raises :class:`SecretNotFoundError`
    when the variable is not set or is empty.

Returns
-------
str
    The secret value.

Raises
------
SecretNotFoundError
    If ``required=True`` and the variable is not set or empty.

*Line: 74*

---

## Function: 

Get an optional secret from environment variables.

Parameters
----------
key_name:
    Environment variable name.
default:
    Default value if the variable is not set.

Returns
-------
str or None
    The secret value, or ``default`` if not set.

*Line: 109*

---

## Function: 

Check if a secret exists in environment variables.

Parameters
----------
key_name:
    Environment variable name.

Returns
-------
bool
    ``True`` if the variable is set and non-empty.

*Line: 134*

---

## Function: 

Validate that multiple required secrets are available.

Parameters
----------
key_names:
    List of environment variable names to check.

Raises
------
SecretNotFoundError
    If any required secret is missing. Only reports the
    first missing key.

*Line: 150*

---

## Function: 

Clear the internal secret cache.

Forces re-reading from environment variables on next access.

*Line: 167*

---

## Function: 

Mask a secret value for safe display.

Parameters
----------
value:
    The secret value to mask.
show_length:
    Number of characters to show at the start.

Returns
-------
str
    Masked value like ``"abcd****"``.

*Line: 175*

---

## Function: 

*Line: 196*

---

