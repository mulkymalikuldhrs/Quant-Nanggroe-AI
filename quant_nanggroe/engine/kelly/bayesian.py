from scipy import stats

from quant_nanggroe.engine.kelly.base import BaseKelly, KellyMethod, KellyParameters, KellyResult


class BayesianKelly(BaseKelly):
    def __init__(self, alpha_prior: float = 1.0, beta_prior: float = 1.0, confidence: float = 0.05):
        self.alpha_prior = alpha_prior
        self.beta_prior = beta_prior
        self.confidence = confidence

    def compute(self, params: KellyParameters) -> KellyResult:
        n_wins = params.win_rate * self._effective_n(params)
        n_losses = self._effective_n(params) - n_wins
        alpha_post = self.alpha_prior + n_wins
        beta_post = self.beta_prior + n_losses
        p_lower = stats.beta.ppf(self.confidence / 2, alpha_post, beta_post)
        stats.beta.ppf(1 - self.confidence / 2, alpha_post, beta_post)
        p_robust = max(0.01, min(0.99, p_lower))
        b = params.avg_win / params.avg_loss if params.avg_loss != 0 else 0
        q = 1 - p_robust
        f_full = (b * p_robust - q) / b if b > 0 else 0
        f_star = max(0, f_full * params.regime_multiplier)
        f_star = min(f_star, params.leverage_max)
        g = self._growth_rate(f_star, p_robust, b)
        return KellyResult(f_star=f_star, method=KellyMethod.BAYESIAN, growth_rate=g, parameters=params)

    def _effective_n(self, params: KellyParameters) -> int:
        return max(30, int(1.0 / (1 - params.win_rate + 0.01)))
