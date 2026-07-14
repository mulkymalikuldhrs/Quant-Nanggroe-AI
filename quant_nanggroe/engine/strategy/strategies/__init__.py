# Package init

__all__ = [
    'base_strategy',
    'cot_strategy',
    'crypto_specific',
    'fundamental_strategy',
    'ict_strategy',
    'market_making',
    'mean_reversion',
    'momentum',
    'pairs_trading',
    'regime_based',
    'smc_strategy',
    'statistical_arbitrage',
    'supply_demand_strategy',
    'support_resistance_strategy',
    'trend_follow',
    'volatility_arbitrage',
    'wyckoff_strategy',
    # Fibonacci (5)
    'fibonacci_retracement',
    'fibonacci_extension',
    'fibonacci_fan',
    'fibonacci_time',
    'fibonacci_arc',
    # Candlestick (12)
    'doji_pattern',
    'hammer_pattern',
    'engulfing_pattern',
    'morning_star',
    'evening_star',
    'three_white_soldiers',
    'three_black_crows',
    'piercing_line',
    'dark_cloud',
    'harami_pattern',
    'shooting_star',
    'inverted_hammer',
    # Hedge Fund (20)
    'pairs_cointegration',
    'stat_arb_zscore',
    'momentum_factor',
    'value_factor',
    'quality_factor',
    'size_factor',
    'carry_trade',
    'risk_parity',
    'trend_following_cta',
    'mean_reversion_stat',
    'volatility_selling',
    'options_straddle',
    'macro_rates',
    'macro_fx',
    'momentum_crash_filter',
    'regime_hmm',
    'hurst_exponent',
    'half_life_mean_reversion',
    'entropy_strategy',
    'kelly_optimal',
    # Technical (25)
    'adx_strategy',
    'cci_strategy',
    'mfi_strategy',
    'obv_strategy',
    'williams_r',
    'stochastic_oscillator',
    'ichimoku_cloud',
    'parabolic_sar',
    'aroon_strategy',
    'vortex_strategy',
    'dmi_strategy',
    'elder_ray',
    'choppiness_index',
    'relative_vigor',
    'kaufman_ama',
    't3_strategy',
    'hull_ma',
    'dema_strategy',
    'tema_strategy',
    'trix_strategy',
    'elder_triple_screen',
    'monte_carlo_barrier',
    'pivot_points',
    'camarilla_pivot',
    'woodie_pivot',
    # ML-Simple (10)
    'linear_regression_channel',
    'polynomial_regression',
    'kmeans_regime',
    'pca_strategy',
    'bayesian_ridge',
    'rsi_divergence_macd',
    'multi_indicator_voting',
    'adaptive_moving_average',
    'kalman_filter',
    'particle_filter',
    # Volatility (8)
    'garch_vol',
    'ewma_vol',
    'bollinger_squeeze',
    'atr_breakout',
    'keltner_squeeze',
    'volatility_regime',
    'vix_term_structure',
    'vol_surface_arb',
    # Macro (10)
    'commodity_trend',
    'gold_inflation',
    'yield_curve',
    'dxy_momentum',
    'em_carry',
    'crypto_funding',
    'on_chain_momentum',
    'social_sentiment',
    'options_put_call',
    'dark_pool_flow',
]

from . import base_strategy
from .base_strategy import BaseStrategy
from . import cot_strategy
from . import crypto_specific
from . import fundamental_strategy
from . import ict_strategy
from . import market_making
from . import mean_reversion
from . import momentum
from . import pairs_trading
from . import regime_based
from . import smc_strategy
from . import statistical_arbitrage
from . import supply_demand_strategy
from . import support_resistance_strategy
from . import trend_follow
from . import volatility_arbitrage
from . import wyckoff_strategy
from . import fibonacci_retracement
from . import fibonacci_extension
from . import fibonacci_fan
from . import fibonacci_time
from . import fibonacci_arc
from . import doji_pattern
from . import hammer_pattern
from . import engulfing_pattern
from . import morning_star
from . import evening_star
from . import three_white_soldiers
from . import three_black_crows
from . import piercing_line
from . import dark_cloud
from . import harami_pattern
from . import shooting_star
from . import inverted_hammer
from . import pairs_cointegration
from . import stat_arb_zscore
from . import momentum_factor
from . import value_factor
from . import quality_factor
from . import size_factor
from . import carry_trade
from . import risk_parity
from . import trend_following_cta
from . import mean_reversion_stat
from . import volatility_selling
from . import options_straddle
from . import macro_rates
from . import macro_fx
from . import momentum_crash_filter
from . import regime_hmm
from . import hurst_exponent
from . import half_life_mean_reversion
from . import entropy_strategy
from . import kelly_optimal
from . import adx_strategy
from . import cci_strategy
from . import mfi_strategy
from . import obv_strategy
from . import williams_r
from . import stochastic_oscillator
from . import ichimoku_cloud
from . import parabolic_sar
from . import aroon_strategy
from . import vortex_strategy
from . import dmi_strategy
from . import elder_ray
from . import choppiness_index
from . import relative_vigor
from . import kaufman_ama
from . import t3_strategy
from . import hull_ma
from . import dema_strategy
from . import tema_strategy
from . import trix_strategy
from . import elder_triple_screen
from . import monte_carlo_barrier
from . import pivot_points
from . import camarilla_pivot
from . import woodie_pivot
from . import linear_regression_channel
from . import polynomial_regression
from . import kmeans_regime
from . import pca_strategy
from . import bayesian_ridge
from . import rsi_divergence_macd
from . import multi_indicator_voting
from . import adaptive_moving_average
from . import kalman_filter
from . import particle_filter
from . import garch_vol
from . import ewma_vol
from . import bollinger_squeeze
from . import atr_breakout
from . import keltner_squeeze
from . import volatility_regime
from . import vix_term_structure
from . import vol_surface_arb
from . import commodity_trend
from . import gold_inflation
from . import yield_curve
from . import dxy_momentum
from . import em_carry
from . import crypto_funding
from . import on_chain_momentum
from . import social_sentiment
from . import options_put_call
from . import dark_pool_flow

# Convenience registry
def list_strategies() -> list:
    """Return names of all registered strategy modules."""
    return [m for m in __all__ if m not in ("base_strategy",)]

# Name mapping for create_strategy
_NAME_MAP = {
    # Existing
    "mean_reversion": "MeanReversionStrategy",
    "momentum": "MomentumStrategy",
    "pairs_trading": "PairsTradingStrategy",
    "trend_follow": "TrendFollowStrategy",
    "smc_strategy": "SMCStrategy",
    "ict_strategy": "ICTStrategy",
    "cot_strategy": "COTStrategy",
    "fundamental_strategy": "FundamentalStrategy",
    "market_making": "MarketMakingStrategy",
    "regime_based": "RegimeBasedStrategy",
    "statistical_arbitrage": "StatisticalArbitrageStrategy",
    "supply_demand_strategy": "SupplyDemandStrategy",
    "support_resistance_strategy": "SupportResistanceStrategy",
    "volatility_arbitrage": "VolatilityArbitrageStrategy",
    "wyckoff_strategy": "WyckoffStrategy",
    "crypto_specific": "CryptoSpecificStrategy",
    # Fibonacci (5)
    "fibonacci_retracement": "FibonacciRetracementStrategy",
    "fibonacci_extension": "FibonacciExtensionStrategy",
    "fibonacci_fan": "FibonacciFanStrategy",
    "fibonacci_time": "FibonacciTimeStrategy",
    "fibonacci_arc": "FibonacciArcStrategy",
    # Candlestick (12)
    "doji_pattern": "DojiPatternStrategy",
    "hammer_pattern": "HammerPatternStrategy",
    "engulfing_pattern": "EngulfingPatternStrategy",
    "morning_star": "MorningStarStrategy",
    "evening_star": "EveningStarStrategy",
    "three_white_soldiers": "ThreeWhiteSoldiersStrategy",
    "three_black_crows": "ThreeBlackCrowsStrategy",
    "piercing_line": "PiercingLineStrategy",
    "dark_cloud": "DarkCloudCoverStrategy",
    "harami_pattern": "HaramiPatternStrategy",
    "shooting_star": "ShootingStarStrategy",
    "inverted_hammer": "InvertedHammerStrategy",
    # Hedge Fund (20)
    "pairs_cointegration": "PairsCointegrationStrategy",
    "stat_arb_zscore": "StatArbZscoreStrategy",
    "momentum_factor": "MomentumFactorStrategy",
    "value_factor": "ValueFactorStrategy",
    "quality_factor": "QualityFactorStrategy",
    "size_factor": "SizeFactorStrategy",
    "carry_trade": "CarryTradeStrategy",
    "risk_parity": "RiskParityStrategy",
    "trend_following_cta": "TrendFollowingCTAStrategy",
    "mean_reversion_stat": "MeanReversionStatStrategy",
    "volatility_selling": "VolatilitySellingStrategy",
    "options_straddle": "OptionsStraddleStrategy",
    "macro_rates": "MacroRatesStrategy",
    "macro_fx": "MacroFXStrategy",
    "momentum_crash_filter": "MomentumCrashFilterStrategy",
    "regime_hmm": "RegimeHMMStrategy",
    "hurst_exponent": "HurstExponentStrategy",
    "half_life_mean_reversion": "HalfLifeMeanReversionStrategy",
    "entropy_strategy": "EntropyStrategy",
    "kelly_optimal": "KellyOptimalStrategy",
    # Technical (25)
    "adx_strategy": "ADXStrategy",
    "cci_strategy": "CCIStrategy",
    "mfi_strategy": "MFIStrategy",
    "obv_strategy": "OBVStrategy",
    "williams_r": "WilliamsRStrategy",
    "stochastic_oscillator": "StochasticOscillatorStrategy",
    "ichimoku_cloud": "IchimokuCloudStrategy",
    "parabolic_sar": "ParabolicSARStrategy",
    "aroon_strategy": "AroonStrategy",
    "vortex_strategy": "VortexStrategy",
    "dmi_strategy": "DMIStrategy",
    "elder_ray": "ElderRayStrategy",
    "choppiness_index": "ChoppinessIndexStrategy",
    "relative_vigor": "RelativeVigorStrategy",
    "kaufman_ama": "KaufmanAMAStrategy",
    "t3_strategy": "T3Strategy",
    "hull_ma": "HullMAStrategy",
    "dema_strategy": "DEMAStrategy",
    "tema_strategy": "TEMAStrategy",
    "trix_strategy": "TRIXStrategy",
    "elder_triple_screen": "ElderTripleScreenStrategy",
    "monte_carlo_barrier": "MonteCarloBarrierStrategy",
    "pivot_points": "PivotPointsStrategy",
    "camarilla_pivot": "CamarillaPivotStrategy",
    "woodie_pivot": "WoodiePivotStrategy",
    # ML-Simple (10)
    "linear_regression_channel": "LinearRegressionChannelStrategy",
    "polynomial_regression": "PolynomialRegressionStrategy",
    "kmeans_regime": "KMeansRegimeStrategy",
    "pca_strategy": "PCAStrategy",
    "bayesian_ridge": "BayesianRidgeStrategy",
    "rsi_divergence_macd": "RSIDivergenceMACDStrategy",
    "multi_indicator_voting": "MultiIndicatorVotingStrategy",
    "adaptive_moving_average": "AdaptiveMovingAverageStrategy",
    "kalman_filter": "KalmanFilterStrategy",
    "particle_filter": "ParticleFilterStrategy",
    # Volatility (8)
    "garch_vol": "GARCHVolStrategy",
    "ewma_vol": "EWMAVolStrategy",
    "bollinger_squeeze": "BollingerSqueezeStrategy",
    "atr_breakout": "ATRBreakoutStrategy",
    "keltner_squeeze": "KeltnerSqueezeStrategy",
    "volatility_regime": "VolatilityRegimeStrategy",
    "vix_term_structure": "VIXTermStructureStrategy",
    "vol_surface_arb": "VolSurfaceArbStrategy",
    # Macro (10)
    "commodity_trend": "CommodityTrendStrategy",
    "gold_inflation": "GoldInflationStrategy",
    "yield_curve": "YieldCurveStrategy",
    "dxy_momentum": "DXYMomentumStrategy",
    "em_carry": "EMCarryStrategy",
    "crypto_funding": "CryptoFundingStrategy",
    "on_chain_momentum": "OnChainMomentumStrategy",
    "social_sentiment": "SocialSentimentStrategy",
    "options_put_call": "OptionsPutCallStrategy",
    "dark_pool_flow": "DarkPoolFlowStrategy",
}


def create_strategy(name: str):
    """Create a strategy instance by name (case-insensitive, flexible matching)."""
    lower = name.lower().replace("strategy", "").replace("_", "")
    # Direct match first
    for mod_name, class_name in _NAME_MAP.items():
        if mod_name.lower().replace("_", "") == lower or class_name.lower().replace("strategy", "") == lower:
            mod = globals().get(mod_name)
            if mod:
                cls = getattr(mod, class_name, None)
                if cls:
                    return cls()
    raise ValueError(f"Unknown strategy: {name!r}. Available: {list(_NAME_MAP.keys())}")
