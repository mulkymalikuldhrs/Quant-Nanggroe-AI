import math
from quant_nanggroe.engine.risk.manager import RiskManager, RiskState


def test_downside_deviation_and_sortino():
    rm = RiskManager.__new__(RiskManager)
    rm.state = RiskState(peak_equity=1000.0, current_equity=1000.0)

    # 1. Base case: empty history
    assert rm.downside_deviation() == 0.0
    assert rm.sortino_ratio() == 0.0

    # 2. Base case: 1 return
    rm.state.returns_history = [0.05]
    assert rm.downside_deviation() == 0.0
    assert rm.sortino_ratio() == 0.0

    # 3. Normal case: mix of returns
    rm.state.returns_history = [0.05, -0.03, 0.03, -0.08, 0.04]
    dd = rm.downside_deviation()
    sr = rm.sortino_ratio()

    # Hand-calculated downside deviation:
    # returns = [0.05, -0.03, 0.03, -0.08, 0.04]
    # downside diffs from 0.0: [-0.03, -0.08] -> squared: [0.0009, 0.0064]
    # sum = 0.0073 -> mean = 0.0073 / 5 = 0.00146 -> sqrt = 0.0382099...
    exp_dd = math.sqrt(0.00146)
    assert abs(dd - exp_dd) < 1e-9

    # Mean return = 0.002. Sortino = 0.002 * 252 / dd = 0.504 / 0.0382099 = 13.1903
    exp_sr = 0.002 * 252.0 / exp_dd
    assert abs(sr - exp_sr) < 1e-9

    # 4. Perfect positive: zero downside deviation
    rm.state.returns_history = [0.05, 0.03, 0.04]
    assert rm.downside_deviation() == 0.0
    assert rm.sortino_ratio() == 0.0
    print("ALL TESTS PASSED")


if __name__ == '__main__':
    test_downside_deviation_and_sortino()
