# engine.risk.var

## Class: 

VaR calculation result.

*Line: 44*

---

## Class: 

Unified VaR Calculator with CVaR as primary metric.

Provides three calculation methods and automatically selects
the most appropriate based on data availability.

IMPORTANT: CVaR (Conditional Value at Risk / Expected Shortfall)
is used as the PRIMARY risk metric, not VaR. CVaR captures the
expected magnitude of losses beyond the VaR threshold.

**Methods:** __init__, calculate, _select_method, _get_z_score, _parametric_var, _historical_var, _monte_carlo_var, _bootstrap_ci

*Line: 54*

---

## Function: 

*Line: 65*

---

## Function: 

Calculate VaR and CVaR.

Args:
    returns: Array of historical returns.
    confidence_level: Confidence level (0.90, 0.95, 0.99).
    method: 'auto', 'parametric', 'historical', 'monte_carlo'.
    portfolio_value: Portfolio value for monetary VaR.
    num_simulations: Simulations for Monte Carlo method.

Returns:
    VaRResult with VaR and CVaR values.

*Line: 68*

---

## Function: 

Select the most appropriate VaR method based on data availability.

*Line: 113*

---

## Function: 

Get z-score for a given confidence level.

Uses the standard lookup table for common levels, falls back
to scipy for others.

Args:
    confidence_level: Confidence level (e.g. 0.90, 0.95, 0.99).

Returns:
    Z-score (positive value).

*Line: 123*

---

## Function: 

Parametric VaR (Variance-Covariance method).

Assumes returns are normally distributed.

Formulas:
    VaR = -μ + z_α * σ  (loss perspective)
    CVaR = -μ + σ * φ(z_α) / (1-α)

Where:
    z_α = z-score at confidence level α
    φ = standard normal PDF
    μ = mean return
    σ = standard deviation of returns

The CVaR formula correctly accounts for the mean return
and uses the well-known parametric result for normal distributions.

*Line: 145*

---

## Function: 

Historical VaR using empirical distribution.

Simply takes the percentile of the empirical return distribution.

VaR: the (1-α) percentile of losses
CVaR: the MEAN of losses beyond VaR (not VaR * sqrt(n/n) or similar).
      This is the correct historical CVaR formula — average of the
      tail losses beyond the VaR threshold.

*Line: 195*

---

## Function: 

Monte Carlo VaR through simulation.

Generates random scenarios from the fitted distribution
and computes VaR/CVaR from the simulated distribution.

*Line: 230*

---

## Function: 

Bootstrap confidence interval for VaR.

*Line: 274*

---

