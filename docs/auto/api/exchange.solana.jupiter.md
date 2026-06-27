# exchange.solana.jupiter

## Class: 

A single route in a Jupiter quote.

Attributes
----------
in_mint:
    Input token mint address.
out_mint:
    Output token mint address.
in_amount:
    Input amount (raw, smallest unit).
out_amount:
    Expected output amount (raw, smallest unit).
price_impact_pct:
    Estimated price impact as a percentage.
label:
    DEX or label used for this route step.

*Line: 45*

---

## Class: 

A swap quote from Jupiter V6.

Attributes
----------
input_mint:
    Input token mint address.
output_mint:
    Output token mint address.
in_amount:
    Input amount (raw).
out_amount:
    Expected output amount (raw).
other_amount_threshold:
    Minimum output amount given slippage.
price_impact_pct:
    Estimated price impact as a percentage.
route_plan:
    Ordered list of route steps.
slippage_bps:
    Slippage tolerance in basis points.
created_at:
    Timestamp when the quote was fetched.

*Line: 74*

---

## Class: 

Result of a Jupiter V6 swap execution.

Attributes
----------
signature:
    Transaction signature on Solana.
input_mint:
    Input token mint.
output_mint:
    Output token mint.
in_amount:
    Input amount.
out_amount:
    Output amount received.
status:
    Transaction status (confirmed, failed, etc.).
slot:
    Slot number of the confirmed transaction.
fee:
    Transaction fee paid (lamports).

*Line: 114*

---

## Class: 

Jupiter V6 API client for swap quotes and execution.

Parameters
----------
rpc_url:
    Solana JSON-RPC endpoint for transaction sending.
api_url:
    Jupiter V6 API base URL. Defaults to the public endpoint.
timeout:
    HTTP request timeout in seconds.

Examples
--------
.. code-block:: python

    client = JupiterV6Client(rpc_url="https://api.mainnet-beta.solana.com")
    quote = await client.get_quote(
        input_mint=SOL_MINT,
        output_mint=USDC_MINT,
        amount=1_000_000,
        slippage_bps=50,
    )

**Methods:** __init__, estimate_price_impact, __repr__

*Line: 153*

---

## Function: 

*Line: 178*

---

## Function: 

Estimate price impact from a swap.

Parameters
----------
in_amount:
    Raw input amount.
out_amount:
    Raw output amount.
reference_price:
    Reference price (output per input in human-readable units).
input_decimals:
    Input token decimals.
output_decimals:
    Output token decimals.

Returns
-------
float
    Estimated price impact as a percentage (0–100).

*Line: 436*

---

## Function: 

*Line: 511*

---

