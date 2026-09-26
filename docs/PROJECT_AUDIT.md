# Source-project audit

The supplied folder contains `Project Final.pdf`, `Project.docx`, a presentation, several spreadsheets and exploratory notebooks. `ID6633.ipynb` is the closest code source for the final report. The report credits **Riddhimann Chattopadhyay**, Department of Statistics, Ramakrishna Mission Residential College (Autonomous), Narendrapur.

The original report and notebooks remain untouched in the source folder. They are not copied to GitHub because the title page contains student identifiers and the notebooks contain absolute Windows paths. The repository includes the attributed dataset, a document audit and a clean implementation.

| Report claim or objective | Repository implementation |
| --- | --- |
| Fit exponential, logistic and Gompertz growth | Bounded nonlinear fits with comparable likelihood criteria |
| Compare deterministic models with AIC | AIC, AICc, BIC, RMSE and Akaike weights |
| Fit demographic/environmental/combined noise | Multi-start transition MLE with annual-gap handling |
| Compare stochastic models | AIC, AICc, BIC, Akaike weights and convergence records |
| Confidence and prediction intervals | Reproducible simulation quantiles; conditional limitations disclosed |
| Forecast future population | Thirty-year scenarios from the final observation |
| Estimate extinction probability | Absorbing quasi-extinction, Wilson Monte Carlo intervals, threshold/horizon sensitivity |
| Generalizable UI | Upload-driven Streamlit fitting interface with schema validation |
| Small-data limitation | AICc and a chronological 75:25 holdout against persistence |
| Single-model limitation | All candidate risks plus AICc-weighted scenario summary |

## Material corrections

1. **Wrong simulation origin.** The report defines quasi-extinction as `N ≤ 10`, while the notebook function defaults to the first observation, `N0 = 8`. It checks the threshold only after taking a step, even though the initial state is already below the threshold. The new primary scenario starts at the final observation, 138 in 1984, and checks the initial state.
2. **Horizon mismatch.** The report quotes 30 years; notebook variants run 50 years or horizons from 100 to 1,000. The new analysis declares 30 years as primary and reports 10/30/50/100-year sensitivity.
3. **Non-reproducible risk.** Some extinction calls have no fixed seed and only 1,000 simulations. The new run uses fixed independent seeds, 20,000 simulations per model/scenario and binomial Monte Carlo intervals.
4. **Invented covariance.** One notebook uses `diag([0.0005, 1.0, 0.01])` as a “user-tunable” covariance. It is not estimated evidence. The new results do not use that matrix.
5. **Circular interval coverage.** A notebook builds intervals from the same simulated paths used to measure their coverage. That describes empirical quantiles by construction, not out-of-sample calibration. The new dashboard calls them conditional simulation bands and does not claim validated 95% coverage.
6. **AIC inconsistency.** The deterministic code estimates residual variance but does not consistently count it as a likelihood parameter and uses `ddof=k` inside the variance estimate. The rebuild uses Gaussian MLE variance, counts it, and adds AICc for the small sample.
7. **Combined boundary.** The reported combined model sets environmental noise effectively to zero and adds a parameter penalty. This is a boundary/nested-model outcome, not independent confirmation of a purely demographic mechanism. The new report states that caveat.
8. **Mechanism overclaim.** Variance scaling that fits best cannot by itself identify demographic biology. Observation error and omitted covariates can mimic process noise. Results are described as candidate mathematical models.
9. **Negative populations.** Gaussian Euler steps can be negative. The new simulation truncates at zero and makes threshold crossing absorbing, and documents this numerical choice.
10. **Current conservation claims.** The historical local series cannot justify present global species recommendations. The dashboard and report label outputs as conditional historical scenarios.
11. **Hard-coded file paths and duplicated cells.** The notebooks depend on `C:\Users\...`, redefine functions and mix environmental/demographic parameter variables. The package accepts relative CSV/XLSX inputs and has one tested implementation per operation.
12. **No baseline or temporal validation.** Full-sample fit plots do not test forecasting. The rebuild reserves the final quarter and includes a persistence comparator.

## Deliberate scope

This implementation does not add random forests merely because the report mentions them as future work. Thirty-six observations cannot support an expansive black-box search credibly. The stronger extension is small-sample correction, honest temporal validation, model averaging, explicit scenario sensitivity and robust uncertainty language.

