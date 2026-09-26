# Interview guide

## 60-second explanation

“I converted an exploratory conservation-modelling project into a reproducible package. The dataset has 36 annual observations for a historical Black-legged Kittiwake population. I fit exponential, logistic and Gompertz curves, then logistic transition models where variance scales demographically, environmentally or both. I used AICc because the sample is small and added a chronological holdout against persistence. For extinction scenarios I start from the last observation, define quasi-extinction explicitly, run seeded Monte Carlo simulations and report both Monte Carlo intervals and threshold/horizon sensitivity. The key contribution is not one alarming probability; it is making every assumption visible and correcting a simulation that started below its own extinction threshold.”

## Five-minute walkthrough

1. Open the README and show the observed 1949–1984 series.
2. Explain the deterministic shapes and why AICc is preferable to raw AIC here.
3. Show the stochastic variance equations. Stress that labels are mathematical hypotheses, not causal proof.
4. Open the chronological holdout table and compare with persistence.
5. Show the risk explorer at threshold 10/horizon 30, then change the threshold. Explain the Wilson interval when zero events occur.
6. Show `test_threshold_is_checked_at_initial_state`; connect it to the main source-project bug.
7. Finish with the historical/local-data boundary and a realistic next step.

## Questions to prepare for

**Why logistic growth?** It represents density-dependent mean growth with carrying capacity. It is plausible for a saturating trajectory, but plausibility and fit do not prove the mechanism.

**Why Gompertz too?** Its asymmetric sigmoid allows a different timing of growth slowdown. Comparing it prevents choosing logistic only because the trajectory looks S-shaped.

**What does demographic versus environmental noise mean mathematically?** Conditional variance grows as `N` under the demographic candidate and `N²` under the environmental candidate. Combined includes both. The data may not distinguish ecological cause from observation error.

**Why AICc?** AIC's finite-sample bias matters when the observation count is not large relative to the parameter count. AICc adds a correction that vanishes as sample size grows.

**Why include a holdout if AIC selects models?** AIC measures expected relative information loss under assumptions and uses in-sample likelihood. A time holdout asks a separate forecasting question and exposes whether fitted shape generalizes.

**Why persistence?** A population time series can be autocorrelated; repeating the previous observation is a credible simple forecast. A complex model should be compared with it on the same years.

**What was wrong with 53.1%?** The notebook defaults to the first observation, 8, while quasi-extinction is `≤10`, but it does not count the initial condition. It also uses inconsistent horizons and insufficiently controlled random simulation. The corrected scenario starts at 138 in 1984.

**Does zero simulated extinction mean zero risk?** No. It means no event occurred in a finite run under the fitted scenario. The Wilson interval gives a positive upper bound, and parameter/structural uncertainty is not included.

**Why truncate negative values to zero?** A Gaussian Euler step can cross below zero even though populations cannot. Zero is an absorbing numerical boundary. Alternative positive-valued processes or smaller time steps are good sensitivity analyses.

**Are the 95% bands calibrated?** They are conditional simulation quantiles. They include fitted process noise, not full parameter, observation or structural uncertainty. They should not be called empirically validated coverage bands.

**Why no random forest?** Thirty-six time points do not justify a broad flexible-model search without severe overfitting risk. The most defensible extension was better small-sample inference, validation and uncertainty analysis.

**What next?** Retrieve full GPDD metadata, model observation error, add biologically relevant covariates and age structure, compare positive-valued diffusion/discrete-state formulations, propagate parameter uncertainty via bootstrap or Bayesian posterior simulation, and validate on other populations.

## Architecture

```text
XLSX/CSV → schema validation → deterministic fits + stochastic transition MLE
                         ├── AICc/BIC/weights
                         ├── chronological holdout vs persistence
                         └── final-observation simulations
                                  → conditional bands
                                  → first-passage risk + MC intervals
                                  → threshold/horizon sensitivity
                         → CSV/JSON/figures → dashboard + report
```

## Resume bullets

- Rebuilt a stochastic population-viability analysis into a tested Python package with deterministic growth models, transition MLE, AICc comparison and chronological validation.
- Corrected quasi-extinction simulation origin/threshold logic and added 20,000-path Monte Carlo intervals, model averaging, scenario sensitivity and an upload-driven Streamlit dashboard.

Use only claims you can explain and code you understand. The original report is authored by Riddhimann Chattopadhyay; preserve that attribution if presenting or adapting it.

