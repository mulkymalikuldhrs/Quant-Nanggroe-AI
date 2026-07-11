"""Test visualization dashboard"""
import sys; sys.path.insert(0, '..')
import numpy as np; import pandas as pd
from quant_nanggroe.engine.visualization.chart_factory import ChartFactory
from quant_nanggroe.engine.visualization.dashboard import QNADashboard

cf = ChartFactory()
print(f"ChartFactory: plotly={cf._HAS_PLOTLY if hasattr(cf, '_HAS_PLOTLY') else 'check'}")

dash = QNADashboard()
returns = pd.Series(np.random.randn(252) * 0.02)
metrics = dash.compute_metrics(returns)
print(f"Dashboard: Sharpe={metrics.sharpe_ratio:.2f}, DD={metrics.max_drawdown*100:.2f}%")

overview = dash.build_overview(returns, pd.DataFrame({"close": 100 + np.cumsum(np.random.randn(252))}))
print(f"Overview: {len(overview['charts'])} charts")
print("TEST PASSED")
