# Methodology and interpretation contract

## Objective

Given annual observations `(t_i, N_i)`, compare simple population-growth curves and stochastic logistic transition models, then estimate the conditional probability of first reaching a user-defined quasi-extinction threshold within a specified horizon.

The probability is conditional on the historical record, candidate model, estimated parameters, Euler approximation, absorbing threshold convention and scenario start. It is not a species-wide conservation status.

## Deterministic models

The exponential model is `N(t)=N0 exp(r(t−t_origin))`. Logistic and Gompertz curves use carrying capacity `K`, growth-rate/shape parameter `r`, and midpoint `t0`. Parameters are estimated by bounded nonlinear least squares.

For comparable Gaussian residual likelihoods, residual variance is estimated by `RSS/n` and counted as an additional likelihood parameter. The project reports AIC, small-sample-corrected AIC (AICc), BIC, RMSE and AICc weights. AICc is primary because `n=36`.

## Stochastic transition models

All candidates share the Euler logistic conditional mean:

`μ_i = N_i + r N_i (1 − N_i/K) Δt_i`.

Their Gaussian conditional variances are:

- demographic: `σ_d² N_i Δt_i`
- environmental: `σ_e² N_i² Δt_i`
- combined: `(σ_d² N_i + σ_e² N_i²) Δt_i`

The transition log-likelihood sums normal log densities for `N_(i+1) | N_i`. Positive/bounded parameters are estimated with multi-start L-BFGS-B optimization. The analysis reports convergence status, AIC/AICc/BIC and AICc weights. A boundary estimate in the combined model needs nonstandard inferential treatment; ordinary regular-model AIC and Hessian standard errors are only approximate there.

The model names refer to how variance scales with `N`, not proven ecological causes. Sampling/observation error is unmodelled and can be confounded with process variation.

## Chronological holdout

The first 75% (27 observations, 1949–1975) is fitted once; the final 25% (9 observations, 1976–1984) is held out. Deterministic curves extrapolate to holdout calendar years. Stochastic models predict each next value conditionally on the actual previous observation using parameters frozen at the cutoff. Persistence predicts the previous observed value.

MAE and RMSE compare all models. Stochastic models also report the mean negative log predictive density (`mean_log_score`) using their fitted conditional variance. With only nine test values, rankings are unstable and descriptive.

## Forward simulations

The primary scenario starts at `N=138`, the final observation in 1984. Each step draws from the fitted Euler Gaussian transition, truncates negative proposals to zero, and makes threshold crossing absorbing. This preserves first-passage interpretation but is only one discretization/boundary convention.

Twenty thousand paths are generated per model/scenario with recorded seeds. The 2.5%, median and 97.5% path quantiles are conditional process-uncertainty bands. They do not integrate parameter uncertainty, model uncertainty, observation error or future covariates.

Quasi-extinction is the first `N ≤ q`. The primary `q=10`, horizon `H=30` follows the report; sensitivity covers thresholds 5, 10, 25 and 50 and horizons 10, 30, 50 and 100. Simulation estimates include Wilson 95% binomial intervals. When zero events occur, the estimate is zero but the upper confidence limit remains positive.

An AICc-weighted summary computes `Σ w_m p_m` across the three fitted stochastic candidates. It communicates within-set model uncertainty; it is not a full Bayesian probability, has no single-binomial interval and ignores models outside the set.

## Reproducibility

The run records the source file hash, seed, simulation count, direct package versions and settings. Tests cover invalid input, deterministic recovery, optimizer reproducibility, initial threshold handling, path non-negativity, seeded simulation equality, Monte Carlo intervals, artifact provenance and dashboard navigation.

The full data is used after the chronological validation to estimate final descriptive parameters and scenarios. Validation results and full-data scenario results answer different questions and are stored separately.

