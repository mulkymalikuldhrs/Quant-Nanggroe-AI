# engine.backtest.psr

## Class: 

*Line: 27*

---

## Class: 

*Line: 38*

---

## Class: 

*Line: 49*

---

## Function: 

Compute annualized Sharpe ratio from a return series.

*Line: 58*

---

## Function: 

Compute skewness and excess kurtosis of a return series.

*Line: 66*

---

## Function: 

Compute the Probabilistic Sharpe Ratio (PSR).

``PSR = Z{ (SR_obs - SR_bench) * sqrt(N-1) / sqrt(1 - skew*SR + (kurt-1)/4 * SR^2) }``

where ``Z`` is the standard normal CDF.

Args:
    returns: Array of periodic returns (e.g., daily).
    sharpe_benchmark: Benchmark Sharpe to exceed. 0.0 means any positive Sharpe.
    annual_factor: Number of periods per year for annualization.

Returns:
    PSRResult with the PSR and significance decision.

*Line: 80*

---

## Function: 

Estimate effective number of independent trials.

When strategies share data (same historical period, overlapping assets),
the effective number is lower than the raw count.

Uses a simple shrinkage: ``N_eff = N / (1 + rho * (N - 1))``

*Line: 118*

---

## Function: 

Estimate the expected maximum Sharpe ratio under the null (no alpha).

Uses the approximation from Bailey et al. (2014):

``E[max(SR)] ~ (1 - gamma) * Z{1 - 1/N} + gamma * Z{1 - 1/(N*e)}``

where gamma ≈ 0.5772 (Euler-Mascheroni constant) and Z is the normal PPF.

*Line: 131*

---

## Function: 

Compute the Deflated Sharpe Ratio (DSR).

``DSR = PSR{SR_threshold = E[max(SR) | N, T]}``

Uses the expected maximum Sharpe given the number of trials as the
benchmark, adjusting for the inflation caused by multiple testing.

Args:
    returns: Array of periodic returns.
    num_trials: Number of strategies/parameter combinations tested.
    num_observations: Length of return series (defaults to len(returns)).
    annual_factor: Number of periods per year.
    correlation: Average correlation between strategy returns.

Returns:
    DSRResult with DSR value and significance decision.

*Line: 153*

---

## Function: 

Full statistical validation for a backtested strategy.

Computes PSR + DSR (if num_trials > 1) and generates diagnostic notes.

Args:
    strategy_name: Name of the strategy being validated.
    returns: Array of periodic returns.
    num_trials: Number of strategies tested in the research process.
    annual_factor: Number of periods per year.

Returns:
    ValidationReport with all results and interpretation notes.

*Line: 195*

---

## Function: 

Compute PSR for a range of benchmark Sharpe values.

Useful for plotting the "PSR efficient frontier."

Args:
    returns: Array of periodic returns.
    sharpe_range: Array of benchmark Sharpe values to test.
    annual_factor: Number of periods per year.

Returns:
    Array of PSR values corresponding to each benchmark Sharpe.

*Line: 256*

---

