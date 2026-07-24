"""Multi-provider weighted vote aggregation.

Provides:
- _timeout_call() — Execute a signal function with thread-based timeout guard
- aggregate() — Collect votes from ALL_PROVIDERS, apply market context boost
  (DXY trend), compute weighted buy/sell confidence, log votes to CSV,
  return final decision with confidence score.

Flow:
1. Load market context (DXY, currency strength)
2. Iterate ALL_PROVIDERS, collect votes
3. Apply context boost (strong DXY → reduce opposite bias confidence)
4. Weighted sum → final {bias, confidence, votes}

Related sections in hedge_fund.py: lines 6111-6203
"""
# TODO: Extract from quant_nanggroe.hedge_fund.hedge_fund
from quant_nanggroe.hedge_fund.hedge_fund import (
    aggregate,
    _timeout_call,
    ALL_PROVIDERS,
    VOTE_LOG,
    log,
)
