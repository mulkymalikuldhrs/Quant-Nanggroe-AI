# exchange.solana.rugcheck

## Class: 

Trading safety verdict.

Attributes
----------
GO:
    Token passes all safety checks — safe to trade.
CAUTION:
    Token has some concerns — trade with care.
NO_GO:
    Token has serious red flags — do not trade.

*Line: 52*

---

## Class: 

Comprehensive token safety analysis report.

Attributes
----------
mint:
    Token mint address.
symbol:
    Token symbol (if available).
name:
    Token name (if available).
mint_authority_revoked:
    Whether the mint authority has been revoked.
freeze_authority_revoked:
    Whether the freeze authority has been revoked.
lp_burn_pct:
    Percentage of LP tokens burned (0–100).
top_holder_pct:
    Percentage of supply held by top holder (0–100).
top_10_holder_pct:
    Percentage of supply held by top 10 holders (0–100).
holder_count:
    Number of token holders.
safety_score:
    Computed safety score (0–100, higher = safer).
verdict:
    Overall Go/No-Go verdict.
warnings:
    List of specific warnings identified.
checked_at:
    When this report was generated.

*Line: 74*

---

## Class: 

Token safety checker for Solana tokens.

Performs on-chain queries to assess the safety of a token before trading.
Checks mint authority, freeze authority, LP burn status, and holder
concentration.

Parameters
----------
rpc_url:
    Solana JSON-RPC endpoint URL.
timeout:
    HTTP request timeout in seconds.

Examples
--------
.. code-block:: python

    checker = RugChecker()
    report = await checker.check_token(
        mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    )
    print(f"Score: {report.safety_score}, Verdict: {report.verdict}")

**Methods:** __init__, _compute_score, _compute_verdict, __repr__

*Line: 128*

---

## Function: 

*Line: 153*

---

## Function: 

Compute the safety score for a token.

Scoring:
- Mint authority revoked: up to 30 points
- Freeze authority revoked: up to 25 points
- LP burn: up to 25 points (100% burn = 25, 0% = 0)
- Holder concentration: up to 20 points (lower top holder = higher score)

Parameters
----------
mint_revoked:
    Whether the mint authority is revoked.
freeze_revoked:
    Whether the freeze authority is revoked.
lp_burn_pct:
    LP burn percentage (0–100).
top_holder_pct:
    Top holder's percentage of supply (0–100).

Returns
-------
float
    Safety score (0–100).

*Line: 471*

---

## Function: 

Determine the Go/No-Go verdict based on score and warnings.

Rules:
- Score >= 80 and ≤ 1 warning → GO
- Score >= 50 or ≤ 2 warnings → CAUTION
- Otherwise → NO_GO

Parameters
----------
score:
    Safety score (0–100).
warnings:
    List of warning strings.

Returns
-------
SafetyVerdict

*Line: 520*

---

## Function: 

*Line: 556*

---

