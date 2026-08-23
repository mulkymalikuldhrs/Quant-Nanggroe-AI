"""Archive strategies — re-export all for AutoRegistry discovery."""
from quant_nanggroe.engine.strategies.archive.archive_macro_rates import ArchiveMacroRatesStrategy
from quant_nanggroe.engine.strategies.archive.archive_market_making import ArchiveMarketMakingStrategy
from quant_nanggroe.engine.strategies.archive.archive_mean_reversion_stat import ArchiveMeanReversionStatStrategy
from quant_nanggroe.engine.strategies.archive.archive_mfi_strategy import ArchiveMfiStrategy
from quant_nanggroe.engine.strategies.archive.archive_momentum import ArchiveMomentumStrategy
from quant_nanggroe.engine.strategies.archive.archive_momentum_crash_filter import ArchiveMomentumCrashFilterStrategy
from quant_nanggroe.engine.strategies.archive.archive_momentum_factor import ArchiveMomentumFactorStrategy
from quant_nanggroe.engine.strategies.archive.archive_monte_carlo_barrier import ArchiveMonteCarloBarrierStrategy
from quant_nanggroe.engine.strategies.archive.archive_morning_star import ArchiveMorningStarStrategy
from quant_nanggroe.engine.strategies.archive.archive_multi_indicator_voting import ArchiveMultiIndicatorVotingStrategy
from quant_nanggroe.engine.strategies.archive.archive_new_proposals import ArchiveNewProposalsStrategy
from quant_nanggroe.engine.strategies.archive.archive_obv_strategy import ArchiveObvStrategy
from quant_nanggroe.engine.strategies.archive.archive_on_chain_momentum import ArchiveOnChainMomentumStrategy
from quant_nanggroe.engine.strategies.archive.archive_options_put_call import ArchiveOptionsPutCallStrategy
from quant_nanggroe.engine.strategies.archive.archive_options_straddle import ArchiveOptionsStraddleStrategy
from quant_nanggroe.engine.strategies.archive.archive_pairs_cointegration import ArchivePairsCointegrationStrategy
from quant_nanggroe.engine.strategies.archive.archive_pairs_trading import ArchivePairsTradingStrategy
from quant_nanggroe.engine.strategies.archive.archive_parabolic_sar import ArchiveParabolicSarStrategy
from quant_nanggroe.engine.strategies.archive.archive_particle_filter import ArchiveParticleFilterStrategy
from quant_nanggroe.engine.strategies.archive.archive_pca_strategy import ArchivePcaStrategy
from quant_nanggroe.engine.strategies.archive.archive_piercing_line import ArchivePiercingLineStrategy
from quant_nanggroe.engine.strategies.archive.archive_pivot_points import ArchivePivotPointsStrategy
from quant_nanggroe.engine.strategies.archive.archive_polynomial_regression import ArchivePolynomialRegressionStrategy
from quant_nanggroe.engine.strategies.archive.archive_quality_factor import ArchiveQualityFactorStrategy
from quant_nanggroe.engine.strategies.archive.archive_regime_based import ArchiveRegimeBasedStrategy
from quant_nanggroe.engine.strategies.archive.archive_regime_hmm import ArchiveRegimeHmmStrategy
from quant_nanggroe.engine.strategies.archive.archive_relative_vigor import ArchiveRelativeVigorStrategy
from quant_nanggroe.engine.strategies.archive.archive_risk_parity import ArchiveRiskParityStrategy
from quant_nanggroe.engine.strategies.archive.archive_rsi_divergence_macd import ArchiveRsiDivergenceMacdStrategy
from quant_nanggroe.engine.strategies.archive.archive_shooting_star import ArchiveShootingStarStrategy
from quant_nanggroe.engine.strategies.archive.archive_size_factor import ArchiveSizeFactorStrategy
from quant_nanggroe.engine.strategies.archive.archive_social_sentiment import ArchiveSocialSentimentStrategy
from quant_nanggroe.engine.strategies.archive.archive_stat_arb_zscore import ArchiveStatArbZscoreStrategy
from quant_nanggroe.engine.strategies.archive.archive_stochastic_oscillator import ArchiveStochasticOscillatorStrategy
from quant_nanggroe.engine.strategies.archive.archive_supply_demand_strategy import ArchiveSupplyDemandStrategy
from quant_nanggroe.engine.strategies.archive.archive_support_resistance_strategy import ArchiveSupportResistanceStrategy
from quant_nanggroe.engine.strategies.archive.archive_t3_strategy import ArchiveT3Strategy
from quant_nanggroe.engine.strategies.archive.archive_tema_strategy import ArchiveTemaStrategy
from quant_nanggroe.engine.strategies.archive.archive_three_black_crows import ArchiveThreeBlackCrowsStrategy
from quant_nanggroe.engine.strategies.archive.archive_three_white_soldiers import ArchiveThreeWhiteSoldiersStrategy
from quant_nanggroe.engine.strategies.archive.archive_trend_follow import ArchiveTrendFollowStrategy
from quant_nanggroe.engine.strategies.archive.archive_trend_following_cta import ArchiveTrendFollowingCtaStrategy
from quant_nanggroe.engine.strategies.archive.archive_trix_strategy import ArchiveTrixStrategy
from quant_nanggroe.engine.strategies.archive.archive_value_factor import ArchiveValueFactorStrategy
from quant_nanggroe.engine.strategies.archive.archive_vix_term_structure import ArchiveVixTermStructureStrategy
from quant_nanggroe.engine.strategies.archive.archive_vol_surface_arb import ArchiveVolSurfaceArbStrategy
from quant_nanggroe.engine.strategies.archive.archive_volatility_arbitrage import ArchiveVolatilityArbitrageStrategy
from quant_nanggroe.engine.strategies.archive.archive_volatility_regime import ArchiveVolatilityRegimeStrategy
from quant_nanggroe.engine.strategies.archive.archive_volatility_selling import ArchiveVolatilitySellingStrategy
from quant_nanggroe.engine.strategies.archive.archive_vortex_strategy import ArchiveVortexStrategy
from quant_nanggroe.engine.strategies.archive.archive_williams_r import ArchiveWilliamsRStrategy
from quant_nanggroe.engine.strategies.archive.archive_woodie_pivot import ArchiveWoodiePivotStrategy
from quant_nanggroe.engine.strategies.archive.archive_wyckoff_strategy import ArchiveWyckoffStrategy
from quant_nanggroe.engine.strategies.archive.archive_yield_curve import ArchiveYieldCurveStrategy
from quant_nanggroe.engine.strategies.archive.msnr_fixed import MSNRStrategyFixed
from quant_nanggroe.engine.strategies.archive.quarterly_fixed import QuarterlyTheoryStrategyFixed
from quant_nanggroe.engine.strategies.archive.smc_fixed import SMCStrategyFixed

__all__ = [
    "ArchiveMacroRatesStrategy",
    "ArchiveMarketMakingStrategy",
    "ArchiveMeanReversionStatStrategy",
    "ArchiveMfiStrategy",
    "ArchiveMomentumStrategy",
    "ArchiveMomentumCrashFilterStrategy",
    "ArchiveMomentumFactorStrategy",
    "ArchiveMonteCarloBarrierStrategy",
    "ArchiveMorningStarStrategy",
    "ArchiveMultiIndicatorVotingStrategy",
    "ArchiveNewProposalsStrategy",
    "ArchiveObvStrategy",
    "ArchiveOnChainMomentumStrategy",
    "ArchiveOptionsPutCallStrategy",
    "ArchiveOptionsStraddleStrategy",
    "ArchivePairsCointegrationStrategy",
    "ArchivePairsTradingStrategy",
    "ArchiveParabolicSarStrategy",
    "ArchiveParticleFilterStrategy",
    "ArchivePcaStrategy",
    "ArchivePiercingLineStrategy",
    "ArchivePivotPointsStrategy",
    "ArchivePolynomialRegressionStrategy",
    "ArchiveQualityFactorStrategy",
    "ArchiveRegimeBasedStrategy",
    "ArchiveRegimeHmmStrategy",
    "ArchiveRelativeVigorStrategy",
    "ArchiveRiskParityStrategy",
    "ArchiveRsiDivergenceMacdStrategy",
    "ArchiveShootingStarStrategy",
    "ArchiveSizeFactorStrategy",
    "ArchiveSocialSentimentStrategy",
    "ArchiveStatArbZscoreStrategy",
    "ArchiveStochasticOscillatorStrategy",
    "ArchiveSupplyDemandStrategy",
    "ArchiveSupportResistanceStrategy",
    "ArchiveT3Strategy",
    "ArchiveTemaStrategy",
    "ArchiveThreeBlackCrowsStrategy",
    "ArchiveThreeWhiteSoldiersStrategy",
    "ArchiveTrendFollowStrategy",
    "ArchiveTrendFollowingCtaStrategy",
    "ArchiveTrixStrategy",
    "ArchiveValueFactorStrategy",
    "ArchiveVixTermStructureStrategy",
    "ArchiveVolSurfaceArbStrategy",
    "ArchiveVolatilityArbitrageStrategy",
    "ArchiveVolatilityRegimeStrategy",
    "ArchiveVolatilitySellingStrategy",
    "ArchiveVortexStrategy",
    "ArchiveWilliamsRStrategy",
    "ArchiveWoodiePivotStrategy",
    "ArchiveWyckoffStrategy",
    "ArchiveYieldCurveStrategy",
    "MSNRStrategyFixed",
    "QuarterlyTheoryStrategyFixed",
    "SMCStrategyFixed",
]
