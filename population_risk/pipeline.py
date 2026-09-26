"""End-to-end reproducible analysis."""

import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path

import numpy as np
import pandas as pd

from .data import arrays, load_population
from .deterministic import fit_deterministic, predict_curve
from .reporting import figures, write_results
from .stochastic import (
    MODEL_PARAMETERS,
    binomial_interval,
    conditional_mean,
    conditional_variance,
    fit_stochastic,
    parameter_vector,
    simulate_paths,
    trajectory_intervals,
)


def _weights(frame, criterion="aicc"):
    delta = frame[criterion] - frame[criterion].min()
    raw = np.exp(-0.5 * delta)
    return raw / raw.sum()


def _validation(years, populations, cutoff, seed):
    train_years, train_pop = years[:cutoff], populations[:cutoff]
    test_years, test_pop = years[cutoff:], populations[cutoff:]
    rows = []
    deterministic = fit_deterministic(train_years, train_pop)
    for name, fit in deterministic.items():
        predicted = predict_curve(fit, test_years, train_years[0])
        errors = test_pop - predicted
        rows.append({"model": name, "mae": np.mean(np.abs(errors)),
                     "rmse": np.sqrt(np.mean(errors**2)), "mean_log_score": np.nan})
    persistence = populations[cutoff - 1:-1]
    errors = test_pop - persistence
    rows.append({"model": "Persistence", "mae": np.mean(np.abs(errors)),
                 "rmse": np.sqrt(np.mean(errors**2)), "mean_log_score": np.nan})
    stochastic = fit_stochastic(train_years, train_pop, seed=seed)
    dt = np.diff(years)[cutoff - 1:]
    previous = populations[cutoff - 1:-1]
    for name, fit in stochastic.items():
        params = parameter_vector(fit)
        predicted = conditional_mean(previous, dt, params[0], params[1])
        variance = conditional_variance(previous, dt, name, params)
        errors = test_pop - predicted
        log_score = 0.5 * (np.log(2 * np.pi * variance) + errors**2 / variance)
        rows.append({"model": name, "mae": np.mean(np.abs(errors)),
                     "rmse": np.sqrt(np.mean(errors**2)), "mean_log_score": np.mean(log_score)})
    return pd.DataFrame(rows).sort_values("mae")


def run(data_path="data/kittiwake_gpdd_6633.xlsx", output="artifacts", simulations=20_000, seed=42):
    data_path, output = Path(data_path), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    frame = load_population(data_path)
    years, populations = arrays(frame)
    cutoff = int(len(frame) * 0.75)
    print("[1/5] Deterministic growth models", flush=True)
    deterministic = fit_deterministic(years, populations)
    deterministic_summary = pd.DataFrame([{**fit.summary(), "model": name,
                                           **fit.parameters} for name, fit in deterministic.items()])
    deterministic_summary["akaike_weight"] = _weights(deterministic_summary)
    grid = np.linspace(years.min(), years.max(), 400)
    deterministic_predictions = pd.concat([
        pd.DataFrame({"model": name, "year": grid,
                      "predicted": predict_curve(fit, grid, years.min())})
        for name, fit in deterministic.items()], ignore_index=True)

    print("[2/5] Stochastic MLE and chronological validation", flush=True)
    stochastic = fit_stochastic(years, populations, seed=seed)
    stochastic_summary = []
    for name, fit in stochastic.items():
        row = {"model": name, **fit.summary(), **fit.parameters}
        row.pop("parameters")
        for field in ("sigma_demographic", "sigma_environmental"):
            row.setdefault(field, np.nan)
        standard_errors = np.sqrt(np.maximum(np.diag(fit.covariance), 0))
        for label, standard_error in zip(MODEL_PARAMETERS[name], standard_errors):
            row[f"se_{label}"] = standard_error
        stochastic_summary.append(row)
    stochastic_summary = pd.DataFrame(stochastic_summary)
    stochastic_summary["akaike_weight"] = _weights(stochastic_summary)
    validation = _validation(years, populations, cutoff, seed)

    print("[3/5] Forecast scenarios and quasi-extinction sensitivity", flush=True)
    horizon_max = 100
    trajectory_rows, risk_rows = [], []
    for index, (name, fit) in enumerate(stochastic.items()):
        paths, hit, first_hit = simulate_paths(fit, populations[-1], horizon_max,
                                               simulations, seed + index)
        del paths, hit, first_hit
        mean, quantiles, cumulative, events = trajectory_intervals(
            fit, populations[-1], 30, simulations, seed + index)
        for step in range(31):
            trajectory_rows.append({"model": name, "step": step, "year": int(years[-1] + step),
                                    "mean": mean[step], "lower_95": quantiles[0, step],
                                    "median": quantiles[1, step], "upper_95": quantiles[2, step],
                                    "cumulative_risk": cumulative[step]})
        for threshold in (5, 10, 25, 50):
            # Reuse random streams but simulate the chosen absorbing threshold correctly.
            threshold_paths, _, threshold_hits = simulate_paths(
                fit, populations[-1], horizon_max, simulations, seed + index, threshold=threshold)
            del threshold_paths
            for horizon in (10, 30, 50, 100):
                count = int(np.sum((threshold_hits >= 0) & (threshold_hits <= horizon)))
                low, high = binomial_interval(count, simulations)
                risk_rows.append({"model": name, "horizon": horizon, "threshold": threshold,
                                  "events": count, "simulations": simulations,
                                  "probability": count / simulations,
                                  "mc_ci_low": low, "mc_ci_high": high})
    trajectories = pd.DataFrame(trajectory_rows)
    sensitivity = pd.DataFrame(risk_rows)
    risk = sensitivity.copy()

    # AICc-weighted scenario summary: weighted probability, not a pooled simulation.
    weights = stochastic_summary.set_index("model").akaike_weight
    averaged = []
    for (horizon, threshold), group in sensitivity.groupby(["horizon", "threshold"]):
        probability = sum(row.probability * weights[row.model] for row in group.itertuples())
        averaged.append({"model": "AICc-weighted", "horizon": horizon, "threshold": threshold,
                         "events": np.nan, "simulations": simulations,
                         "probability": probability, "mc_ci_low": np.nan, "mc_ci_high": np.nan})
    risk = pd.concat([risk, pd.DataFrame(averaged)], ignore_index=True)

    print("[4/5] Save tables, figures and provenance", flush=True)
    tables = {"deterministic_models": deterministic_summary,
              "deterministic_predictions": deterministic_predictions,
              "stochastic_models": stochastic_summary, "holdout_validation": validation,
              "forecast_trajectories": trajectories, "risk_sensitivity": sensitivity,
              "extinction_risk": risk, "observations": frame}
    for name, table in tables.items():
        table.to_csv(output / f"{name}.csv", index=False)
    metadata = {"data_sha256": hashlib.sha256(data_path.read_bytes()).hexdigest(),
                "rows": len(frame), "start_year": int(years[0]), "end_year": int(years[-1]),
                "initial_population": float(populations[-1]), "training_rows": cutoff,
                "test_rows": len(frame) - cutoff, "simulations": simulations, "seed": seed,
                "primary_horizon": 30, "primary_threshold": 10,
                "quasi_extinction_rule": "first simulated N <= threshold; absorbing thereafter",
                "versions": {name: importlib.metadata.version(name) for name in
                             ["numpy", "pandas", "scipy", "matplotlib", "openpyxl", "streamlit"]},
                "python": platform.python_version()}
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    figures(frame, deterministic_predictions, stochastic_summary, validation, trajectories,
            sensitivity, output / "figures")
    write_results(output, metadata, deterministic_summary, stochastic_summary,
                  validation, risk, sensitivity)
    print("[5/5] Complete", flush=True)
    print(stochastic_summary[["model", "aicc", "akaike_weight"]].to_string(index=False))
    print(risk[(risk.horizon == 30) & (risk.threshold == 10)][
        ["model", "probability", "mc_ci_low", "mc_ci_high"]].to_string(index=False))
    return metadata
