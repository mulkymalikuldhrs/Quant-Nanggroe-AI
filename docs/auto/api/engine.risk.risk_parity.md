# engine.risk.risk_parity

## Class: 

Risk parity calculation methods.

*Line: 33*

---

## Class: 

Risk contribution of an asset.

Attributes:
    asset: Asset name.
    weight: Portfolio weight.
    marginal_risk: Marginal risk contribution.
    risk_contribution: Proportional risk contribution.
    risk_budget: Target risk budget.
    deviation: Deviation from target risk budget.

*Line: 43*

---

## Class: 

Result from risk parity optimization.

*Line: 64*

---

## Class: 

Risk Parity Portfolio Optimizer.

Allocates capital such that each asset contributes equally to
portfolio risk, rather than allocating equal capital.

Formula: RC_i = w_i * (Σw)_i / (w'Σw) = 1/N for all i

Enhanced with risk budget analysis and portfolio summary from ai-hedge-fund.

**Methods:** __init__, optimize, get_risk_budget_analysis, get_portfolio_summary, _inverse_volatility, _covariance_based, _equal_risk_contribution, _hierarchical_risk_parity, _risk_contributions

*Line: 77*

---

## Function: 

*Line: 88*

---

## Function: 

Optimize portfolio using risk parity.

Args:
    returns: Returns matrix (n_assets x n_periods).
    asset_names: List of asset names.
    method: Risk parity method.

Returns:
    RiskParityResult with optimized weights and metrics.

*Line: 103*

---

## Function: 

Analyze risk budget for each asset.

Provides a detailed breakdown of each asset's risk contribution
and its deviation from the equal-risk target.

Args:
    weights: Portfolio weights.
    cov_matrix: Covariance matrix.
    asset_names: Asset names.

Returns:
    List of RiskContribution objects with detailed analysis.

*Line: 174*

---

## Function: 

Get summary of risk parity portfolio.

Includes concentration metrics (HHI), weight distribution,
and convergence status.

Args:
    result: RiskParityResult from optimization.

Returns:
    Dict with portfolio summary metrics.

*Line: 215*

---

## Function: 

Inverse volatility weighting: w_i = σ_i^(-1) / Σ(σ_j^(-1)).

*Line: 247*

---

## Function: 

Iterative covariance-based risk parity.

*Line: 255*

---

## Function: 

Equal risk contribution via gradient descent.

*Line: 275*

---

## Function: 

Hierarchical risk parity using clustering.

*Line: 301*

---

## Function: 

Calculate risk contribution of each asset: RC_i = w_i * (Σw)_i / (w'Σw).

*Line: 337*

---

