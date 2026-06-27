# security.credential_inference

## Class: 

Supported exchange/broker types.

Attributes
----------
ALPACA:
    Alpaca paper/live trading (US equities).
BINANCE:
    Binance cryptocurrency exchange.
COINBASE:
    Coinbase Pro cryptocurrency exchange.
OKX:
    OKX cryptocurrency exchange.
BYBIT:
    Bybit cryptocurrency exchange.
KRAKEN:
    Kraken cryptocurrency exchange.
SOLANA:
    Solana blockchain (Jupiter V6 swaps).
UNKNOWN:
    Could not detect exchange type.

*Line: 36*

---

## Class: 

Result of a credential completeness and validity check.

Attributes
----------
exchange_type:
    Detected exchange type.
is_complete:
    Whether all required credentials are present.
is_valid:
    Whether the credentials were verified as valid.
missing_fields:
    List of missing required fields.
warnings:
    List of non-critical warnings.
error:
    Error message if validation failed.
details:
    Additional details about the check.

*Line: 73*

---

## Class: 

Smart credential detection and validation.

Detects the exchange/broker from API key format, validates
credential completeness, and optionally tests credential validity
via read-only operations.

Examples
--------
.. code-block:: python

    inference = CredentialInference()

    # Detect exchange type
    exchange = inference.detect_exchange("PKABCD1234...")
    assert exchange == ExchangeType.ALPACA

    # Validate credentials
    check = inference.validate_credentials(
        exchange_type=ExchangeType.ALPACA,
        api_key="YOUR_API_KEY_HERE",
        api_secret="YOUR_API_SECRET_HERE",
    )
    assert check.is_complete

**Methods:** detect_exchange, validate_credentials, get_required_fields, __repr__

*Line: 162*

---

## Function: 

Detect the exchange/broker type from API key format.

Parameters
----------
api_key:
    The API key to analyze.
api_secret:
    Optional API secret (used for additional heuristics).
passphrase:
    Optional passphrase (narrows down exchanges that require it).

Returns
-------
ExchangeType
    Detected exchange type, or ``UNKNOWN`` if not recognized.

*Line: 188*

---

## Function: 

Validate credential completeness for a specific exchange.

Parameters
----------
exchange_type:
    The target exchange type.
api_key:
    API key.
api_secret:
    API secret.
passphrase:
    Optional passphrase.

Returns
-------
CredentialCheck
    Validation result with missing fields and warnings.

*Line: 252*

---

## Function: 

Get the list of required credential fields for an exchange.

Parameters
----------
exchange_type:
    Target exchange type.

Returns
-------
list of str
    Required field names.

*Line: 443*

---

## Function: 

*Line: 467*

---

