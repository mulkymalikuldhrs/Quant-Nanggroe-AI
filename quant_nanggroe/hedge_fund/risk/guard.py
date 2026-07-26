"""Risk guard integration — external risk approval before trade execution."""

from quant_nanggroe.hedge_fund.utils.config import log


def risk_guard_approve(proposal):
    try:
        from quant_nanggroe.hedge_fund.tools.risk_guard import approve as rg_approve
    except Exception as e:
        log.error(f"Risk guard import FAILED: {e}")
        return {"status": "VETOED", "reasons": [f"import_failed: {e}"]}

    try:
        return rg_approve(proposal)
    except Exception as e:
        log.error(f"Risk guard execution FAILED: {e}")
        return {"status": "VETOED", "reasons": [f"execution_failed: {e}"]}
