"""Risk guard integration — external risk approval before trade execution.

Provides:
- risk_guard_approve() — Calls tools.risk_guard.approve() with a trade proposal
  (symbol, action, volume, price, SL, account balance, daily PnL, volatility).
  Returns APPROVED or VETOED with reasons.

The risk guard is defined externally in hedge_fund/tools/risk_guard.py and
provides position sizing, daily loss limits, and volatility-based vetoes.

Related sections in hedge_fund.py: lines 6426-6451 (risk guard call in run_once)
"""
# TODO: Extract risk guard integration from quant_nanggroe.hedge_fund.hedge_fund
# The risk guard call is embedded within run_once(). It should be extracted
# as a standalone function.

# from quant_nanggroe.hedge_fund.tools.risk_guard import approve as _rg_approve
# def risk_guard_approve(proposal: dict) -> dict:
#     """Approve or veto a trade proposal through the risk guard."""
#     return _rg_approve(proposal)
