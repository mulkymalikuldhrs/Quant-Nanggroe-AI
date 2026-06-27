# exchange.solana.wallet

## Class: 

Information about a single SPL token account.

Attributes
----------
address:
    The token account address (Base58).
mint:
    The SPL token mint address (Base58).
owner:
    The wallet public key that owns this account.
amount:
    Raw token amount (as integer, before decimals adjustment).
decimals:
    Token decimals.
ui_amount:
    Human-readable token balance (float).

*Line: 34*

---

## Class: 

Solana wallet service for keypair management and balance queries.

Parameters
----------
private_key_bs58:
    Base58-encoded private key (Ed25519 keypair bytes).
rpc_url:
    Solana JSON-RPC endpoint URL.
mnemonic:
    BIP39 mnemonic phrase (alternative to ``private_key_bs58``).
derivation_path:
    BIP44 derivation path when using mnemonic.
    Defaults to ``m/44'/501'/0'/0'``.

Raises
------
ValueError
    If neither ``private_key_bs58`` nor ``mnemonic`` is provided.

Examples
--------
.. code-block:: python

    wallet = SolanaWallet(
        private_key_bs58="4zEM...qL3z",
        rpc_url="https://api.mainnet-beta.solana.com",
    )
    balance = await wallet.get_sol_balance()

**Methods:** __init__, public_key, keypair, sign_message, __repr__

*Line: 67*

---

## Function: 

*Line: 98*

---

## Function: 

The wallet's public key as a Base58 string.

*Line: 143*

---

## Function: 

The underlying ``solders.Keypair`` instance (use with caution).

*Line: 148*

---

## Function: 

Sign a message with the wallet's private key.

Parameters
----------
message:
    Raw bytes to sign.

Returns
-------
bytes
    The Ed25519 signature.

*Line: 308*

---

## Function: 

*Line: 323*

---

