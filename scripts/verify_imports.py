"""Verify all 50 migrated strategy files import correctly (env-isolated)."""
import sys

# Add project root + deps to path
sys.path.insert(0, r"D:\repositories\Quant-Nanggroe-AI-worktree")
sys.path.insert(0, r"C:\Users\Hi\.tmp_qna_lib")

# Remove Hermes venv from path (broken native wheels)
sys.path = [p for p in sys.path if "hermes-agent" not in p and "hermes" not in p]

import importlib

strategy_names = [
    "adaptive_moving_average", "adx_strategy", "aroon_strategy", "atr_breakout",
    "bayesian_ridge", "bollinger_squeeze", "camarilla_pivot", "carry_trade",
    "cci_strategy", "choppiness_index", "commodity_trend", "cot_strategy",
    "crypto_funding", "crypto_specific", "dark_cloud", "dark_pool_flow",
    "dema_strategy", "dmi_strategy", "doji_pattern", "dxy_momentum",
    "elder_ray", "elder_triple_screen", "em_carry", "engulfing_pattern",
    "entropy_strategy", "evening_star", "ewma_vol", "fibonacci_arc",
    "fibonacci_extension", "fibonacci_fan", "fibonacci_retracement",
    "fibonacci_time", "fundamental_strategy", "garch_vol", "gold_inflation",
    "half_life_mean_reversion", "hammer_pattern", "harami_pattern",
    "hull_ma", "hurst_exponent", "ichimoku_cloud", "ict_strategy",
    "inverted_hammer", "kalman_filter", "kaufman_ama", "kelly_optimal",
    "keltner_squeeze", "kmeans_regime", "linear_regression_channel", "macro_fx",
]

ok, fail = [], []
for s in strategy_names:
    try:
        mod = importlib.import_module(f"quant_nanggroe.engine.strategies.{s}")
        classes = [n for n in dir(mod) if n.endswith("Strategy")]
        ok.append((s, classes))
        print(f"  OK  {s}: {classes}")
    except Exception as e:
        fail.append((s, str(e)))
        print(f"  FAIL {s}: {e}")

print(f"\n=== RESULTS ===")
print(f"Total: {len(strategy_names)}")
print(f"Success: {len(ok)}")
print(f"Failure: {len(fail)}")
if fail:
    for s, e in fail:
        print(f"  - {s}: {e}")
