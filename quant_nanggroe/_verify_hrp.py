import logging
logging.disable(logging.CRITICAL)
import numpy as np
from quant_nanggroe.engine.portfolio import hrp_allocator as M

# 1) 8-asset HRP path
np.random.seed(7)
syms = [f"A{i}" for i in range(8)]
vols = {s: 0.1 + 0.05 * i for i, s in enumerate(syms)}
R = np.random.randn(500, 8)
C = np.clip(np.corrcoef(R.T), -0.95, 0.95)
np.fill_diagonal(C, 1.0)
corr = {(syms[i], syms[j]): float(C[i, j]) for i in range(8) for j in range(i + 1, 8)}

w = M.allocate(vols, corr)
assert set(w) == set(syms)
tot = sum(w.values())
assert abs(tot - 1.0) < 1e-9, tot
assert all(v >= 0 for v in w.values())
print("TEST1 8-asset HRP: sum=%.6f nonneg=%s OK" % (tot, all(v >= 0 for v in w.values())))

# 2) boundary: n=5 -> RP, n=6 -> HRP
import quant_nanggroe.engine.portfolio.risk_parity_bridgewater as RP
events = []
RP.RiskParityAllocator.compute_risk_parity_weights = lambda self, v, c=None: (events.append("RP"), {s: 1.0 / len(v) for s in v})[1]
M.HRPAllocator.compute_hrp_weights = lambda self, v, c=None: (events.append("HRP"), {s: 1.0 / len(v) for s in v})[1]
events.clear(); M.allocate({f"W{i}": 0.2 for i in range(5)}); assert events[-1] == "RP", events
events.clear(); M.allocate({f"W{i}": 0.2 for i in range(6)}); assert events[-1] == "HRP", events
print("TEST2 boundary n=5->RP n=6->HRP OK")

# 3) equal-vol -> near-equal weights
eq = {f"X{i}": 0.2 for i in range(7)}
ew = M.allocate(eq)
assert abs(sum(ew.values()) - 1.0) < 1e-9
assert max(ew.values()) - min(ew.values()) < 1e-9
print("TEST3 equal-vol 7: sum=%.6f spread=%.6f OK" % (sum(ew.values()), max(ew.values()) - min(ew.values())))

# 4) single asset
one = M.allocate({"Z": 0.15})
assert one == {"Z": 1.0}
print("TEST4 single-asset OK")

# 5) no correlations provided
nc = M.allocate({f"Y{i}": 0.1 + 0.02 * i for i in range(9)})
assert abs(sum(nc.values()) - 1.0) < 1e-9 and all(v >= 0 for v in nc.values())
print("TEST5 9-asset no-corr: sum=%.6f OK" % sum(nc.values()))

print("ALL HRP TESTS PASSED")
