"""Tests for quant library integration wrappers.

These are graceful-degradation tests — they verify the wrappers return None
when optional dependencies (vollib, pyql, ffn) are not installed.

TODO: Add functional tests for OptionsPricer, FixedIncomeCalculator,
PortfolioMetrics when libraries are installed (e.g. mark with
@pytest.mark.integration and test actual pricing/calculations).
"""

from quant_nanggroe.data.models.options import OptionsPricer, OptionPrice
from quant_nanggroe.data.models.fixed_income import FixedIncomeCalculator
from quant_nanggroe.data.models.metrics import PortfolioMetrics


class TestOptionsPricer:
    def test_init_no_vollib(self):
        pricer = OptionsPricer()
        assert pricer._vollib is None

    def test_black_scholes_no_vollib_returns_none(self):
        pricer = OptionsPricer()
        result = pricer.black_scholes("c", 100, 100, 1, 0.05, 0.2)
        assert result is None

    def test_option_price_dataclass(self):
        op = OptionPrice(price=10.0, delta=0.5, gamma=0.1, vega=0.2, theta=-0.05, rho=0.3)
        assert op.price == 10.0
        assert op.delta == 0.5
        assert op.gamma == 0.1
        assert op.vega == 0.2
        assert op.theta == -0.05
        assert op.rho == 0.3


class TestFixedIncomeCalculator:
    def test_init_no_pyql(self):
        calc = FixedIncomeCalculator()
        assert calc._ql is None

    def test_bond_price_no_pyql_returns_none(self):
        calc = FixedIncomeCalculator()
        result = calc.bond_price(1000, 0.05, 10, 0.04)
        assert result is None


class TestPortfolioMetrics:
    def test_init_no_ffn(self):
        pm = PortfolioMetrics()
        assert pm._ffn is None

    def test_calc_sharpe_no_ffn_returns_none(self):
        pm = PortfolioMetrics()
        result = pm.calc_sharpe([0.01, 0.02, -0.01])
        assert result is None

    def test_calc_max_drawdown_no_ffn_returns_none(self):
        pm = PortfolioMetrics()
        result = pm.calc_max_drawdown([100, 95, 90, 85])
        assert result is None
