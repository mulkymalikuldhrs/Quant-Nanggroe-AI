# Auto-export archive strategies for AutoRegistry import side-effects.
# Each module registers its Strategy subclass on import; importing here
# ensures they are available as `archive_<ClassName>` keys via the
# quant_nanggroe.engine.strategies.archive.<module> dotted path.
#
# Generated — manual edits discouraged. The archive namespace is
# discovered at scan time by quant_nanggroe.engine.registry.

# flake8: noqa

from .archive_macro_rates import *
from .archive_market_making import *
from .archive_mean_reversion_stat import *
from .archive_mfi_strategy import *
from .archive_momentum import *
from .archive_momentum_crash_filter import *
from .archive_momentum_factor import *
from .archive_monte_carlo_barrier import *
from .archive_morning_star import *
from .archive_multi_indicator_voting import *
from .archive_new_proposals import *
from .archive_obv_strategy import *
from .archive_on_chain_momentum import *
from .archive_options_put_call import *
from .archive_options_straddle import *
from .archive_pairs_cointegration import *
from .archive_pairs_trading import *
from .archive_parabolic_sar import *
from .archive_particle_filter import *
from .archive_pca_strategy import *
from .archive_piercing_line import *
from .archive_pivot_points import *
from .archive_polynomial_regression import *
from .archive_quality_factor import *
from .archive_quarterly import *
from .archive_quarterly_fixed import *
from .archive_regime_based import *
from .archive_regime_hmm import *
from .archive_relative_vigor import *
from .archive_risk_parity import *
from .archive_rsi_divergence_macd import *
from .archive_shooting_star import *
from .archive_size_factor import *
from .archive_social_sentiment import *
from .archive_stat_arb_zscore import *
from .archive_stochastic_oscillator import *
from .archive_supply_demand_strategy import *
from .archive_support_resistance_strategy import *
from .archive_t3_strategy import *
from .archive_tema_strategy import *
from .archive_three_black_crows import *
from .archive_three_white_soldiers import *
from .archive_trend_follow import *
from .archive_trend_following_cta import *
from .archive_trix_strategy import *
from .archive_value_factor import *
from .archive_vix_term_structure import *
from .archive_vol_surface_arb import *
from .archive_volatility_arbitrage import *
from .archive_volatility_regime import *
from .archive_volatility_selling import *
from .archive_volume_delta import *
from .archive_vortex_strategy import *
from .archive_williams_r import *
from .archive_woodie_pivot import *
from .archive_wyckoff import *
from .archive_wyckoff_strategy import *
from .archive_yield_curve import *