"""Regression test: ExchangeManager.aggregate with no booked capital.

Reproduces the live bug where get_aggregated_portfolio() built
Portfolio(initial_capital=0.0) and failed quant_nanggroe.types.positions
`gt=0` validation on every /api/trading/positions call in dev mode.
"""

import pytest

from quant_nanggroe.exchange.manager import ExchangeManager


@pytest.mark.asyncio
async def test_aggregate_with_zero_capital_is_valid():
    # ponytail: no exchanges registered -> total_initial == total_cash == 0.0
    em = ExchangeManager()
    portfolio = await em.get_aggregated_portfolio()
    assert portfolio.initial_capital > 0  # gt=0 constraint must hold
