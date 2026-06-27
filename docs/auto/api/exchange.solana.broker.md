# exchange.solana.broker

## Class: 

Solana broker adapter implementing ExchangeInterface.

Uses Jupiter V6 for swap execution and the Solana RPC for
account queries and transaction management.

Parameters
----------
config:
    Exchange configuration. ``exchange_id`` should be ``"solana"``.
    ``api_key`` is the Base58-encoded private key.
    ``api_secret`` is unused (pass ``None``).
rpc_url:
    Solana JSON-RPC endpoint.
jupiter_url:
    Jupiter V6 API base URL.

Examples
--------
.. code-block:: python

    config = ExchangeConfig(
        exchange_id="solana",
        api_key="YOUR_API_KEY_HERE",  # Base58 private key
    )
    broker = SolanaBroker(config)
    await broker.connect()
    balance = await broker.get_balance()

**Methods:** __init__, is_connected, state, name, _require_wallet, _require_jupiter, _parse_symbol, __repr__

*Line: 55*

---

## Function: 

*Line: 85*

---

## Function: 

*Line: 165*

---

## Function: 

*Line: 169*

---

## Function: 

*Line: 173*

---

## Function: 

Ensure wallet is initialized.

*Line: 507*

---

## Function: 

Ensure Jupiter client is initialized.

*Line: 515*

---

## Function: 

Parse a trading pair symbol into input/output mints.

Parameters
----------
symbol:
    Trading pair like ``"SOL/USDC"``.
side:
    BUY means swap quote→base, SELL means swap base→quote.

Returns
-------
tuple of (input_mint, output_mint)

*Line: 524*

---

## Function: 

*Line: 563*

---

