"""Generate figures and a concise empirical report from saved computations."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

COLORS = {"Observed": "#20313d", "Logistic": "#b4832f", "Gompertz": "#2c7182",
          "Exponential": "#9a6672", "Demographic": "#b4832f",
          "Environmental": "#2c7182", "Combined": "#7f6a93"}


def markdown_table(frame):
    display = frame.copy()
    for column in display.select_dtypes(include="number"):
        display[column] = display[column].map(lambda value: f"{value:.4f}" if pd.notna(value) else "—")
    lines = ["| " + " | ".join(map(str, display.columns)) + " |",
             "| " + " | ".join(["---"] * len(display.columns)) + " |"]
    lines += ["| " + " | ".join(map(str, row)) + " |" for row in display.to_numpy()]
    return "\n".join(lines)


def figures(data, deterministic, stochastic, validation, trajectories, sensitivity, output):
    output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False,
                         "font.size": 10, "figure.dpi": 140})

    def save(fig, name):
        fig.tight_layout()
        fig.savefig(output / name, bbox_inches="tight")
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(data.SampleYear, data.Population, color=COLORS["Observed"], marker="o", linewidth=1.4)
    ax.set(title="Black-legged Kittiwake · GPDD Main ID 6633", xlabel="Sample year", ylabel="Recorded population")
    save(fig, "observed_population.png")

    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.scatter(data.SampleYear, data.Population, color=COLORS["Observed"], label="Observed", zorder=3)
    for name, group in deterministic.groupby("model"):
        ax.plot(group.year, group.predicted, label=name, color=COLORS[name])
    ax.set(title="Deterministic growth curves", xlabel="Year", ylabel="Population")
    ax.legend()
    save(fig, "deterministic_fits.png")

    fig, ax = plt.subplots(figsize=(9, 4))
    summary = stochastic.sort_values("aicc", ascending=False)
    ax.barh(summary.model, summary.aicc, color=[COLORS[x] for x in summary.model])
    ax.set(title="Stochastic model comparison", xlabel="AICc · lower is better")
    save(fig, "stochastic_aicc.png")

    fig, ax = plt.subplots(figsize=(11, 5))
    for name, group in trajectories.groupby("model"):
        ax.plot(group.year, group["median"], label=name, color=COLORS[name])
        ax.fill_between(group.year, group.lower_95, group.upper_95, color=COLORS[name], alpha=0.12)
    ax.axhline(10, color="#b64d45", linestyle="--", label="Threshold 10")
    ax.scatter([data.SampleYear.iloc[-1]], [data.Population.iloc[-1]], color="#20313d", zorder=4, label="1984 origin")
    ax.set(title="Conditional population scenarios from the last observation", xlabel="Scenario year", ylabel="Population")
    ax.legend(ncol=2)
    save(fig, "forecast_intervals.png")

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    risk = sensitivity[sensitivity.threshold == 10]
    for name, group in risk.groupby("model"):
        axes[0].plot(group.horizon, group.probability, marker="o", label=name, color=COLORS[name])
    axes[0].set(title="Quasi-extinction risk by horizon", xlabel="Years after 1984", ylabel="Estimated probability", ylim=(-0.02, 1.02))
    axes[0].legend()
    risk30 = sensitivity[sensitivity.horizon == 30]
    for name, group in risk30.groupby("model"):
        axes[1].plot(group.threshold, group.probability, marker="o", label=name, color=COLORS[name])
    axes[1].set(title="30-year risk by threshold", xlabel="Quasi-extinction threshold", ylabel="Estimated probability", ylim=(-0.02, 1.02))
    save(fig, "risk_sensitivity.png")

    fig, ax = plt.subplots(figsize=(10, 4))
    for name, group in validation.groupby("model"):
        ax.scatter(group.model, group.mae, color=COLORS.get(name, "#72808a"), s=65)
    ax.set(title="Chronological holdout error", ylabel="MAE · lower is better", xlabel="")
    ax.tick_params(axis="x", rotation=30)
    save(fig, "holdout_validation.png")


def write_results(output, metadata, deterministic_summary, stochastic_summary, validation, risk, sensitivity):
    primary = risk[(risk.horizon == 30) & (risk.threshold == 10)].copy()
    text = f"""# Generated results

Data SHA-256: `{metadata['data_sha256']}`. {metadata['rows']} annual observations,
{metadata['start_year']}–{metadata['end_year']}. Simulations start at the final observed
population, **{metadata['initial_population']:.0f}**, and seed {metadata['seed']}.

## Deterministic growth curves

{markdown_table(deterministic_summary[['model', 'aicc', 'bic', 'rmse', 'akaike_weight']])}

AICc is primary because only 36 observations are available. These scores compare in-sample
Gaussian residual models; they do not establish biological truth.

## Stochastic logistic models

{markdown_table(stochastic_summary[['model', 'growth_rate', 'carrying_capacity', 'sigma_demographic', 'sigma_environmental', 'aicc', 'akaike_weight']])}

The transition likelihood uses each observed year gap and the report's Euler–Gaussian
approximation. The combined model can reduce to a boundary case, so asymptotic parameter
uncertainty and information-criterion interpretations require caution.

## Chronological holdout

{markdown_table(validation[['model', 'mae', 'rmse', 'mean_log_score']])}

Models are fitted on the first {metadata['training_rows']} observations and evaluated on the
remaining {metadata['test_rows']}. Persistence predicts the previous observed population.
The deterministic curves forecast calendar year; stochastic models make one-step conditional
predictions using the previous observed value. `mean_log_score` is available only for stochastic models.

## Quasi-extinction scenario

{markdown_table(primary[['model', 'horizon', 'threshold', 'events', 'simulations', 'probability', 'mc_ci_low', 'mc_ci_high']])}

This is a **conditional model scenario**, not a forecast of the global species or an IUCN
assessment. Quasi-extinction means the simulated local index first reaches or falls below 10.
The start is the last recorded value (1984), not the first value of 8 that is already below the
report's threshold. A zero-event result means the risk was below the resolution of this Monte
Carlo run; the Wilson upper bound remains positive.

![Risk sensitivity](figures/risk_sensitivity.png)

## Interpretation limits

- The record contains one local population/index with 36 annual observations and ends in 1984.
- Observation error, sampling protocol, interventions, dispersal, age structure and covariates are absent.
- Gaussian Euler transitions can produce negative proposals; simulations truncate at zero and make
  quasi-extinction absorbing. This numerical convention materially affects tail risk.
- Prediction bands and extinction probabilities condition on fitted parameters. They omit full
  parameter and structural uncertainty, so they are narrower than a complete predictive analysis.
- AIC/AICc ranks candidates in this set. It cannot prove that demographic variability is literally
  the ecological mechanism, especially when the combined fit reaches a boundary.
- Threshold and horizon choices are scenarios. See `risk_sensitivity.csv` before quoting one number.
- The original report's 53.1% result is not reproduced because its code starts at population 8 while
  defining values at or below 10 as quasi-extinct, and notebook horizons do not consistently match the report.
"""
    (output / "RESULTS.md").write_text(text, encoding="utf-8")
