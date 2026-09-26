"""Deterministic growth curves fitted with a comparable Gaussian likelihood."""

from dataclasses import asdict, dataclass

import numpy as np
from scipy.optimize import curve_fit


@dataclass
class CurveFit:
    name: str
    parameters: dict
    covariance: np.ndarray
    predictions: np.ndarray
    log_likelihood: float
    aic: float
    aicc: float
    bic: float
    rmse: float
    success: bool = True

    def summary(self):
        result = asdict(self)
        result.pop("covariance")
        result.pop("predictions")
        return result


def logistic(t, carrying_capacity, growth_rate, midpoint):
    return carrying_capacity / (1 + np.exp(-growth_rate * (np.asarray(t) - midpoint)))


def gompertz(t, carrying_capacity, growth_rate, midpoint):
    return carrying_capacity * np.exp(-np.exp(-growth_rate * (np.asarray(t) - midpoint)))


def exponential(t, initial_scale, growth_rate, origin):
    return initial_scale * np.exp(growth_rate * (np.asarray(t) - origin))


def _criteria(observed, predicted, parameter_count):
    residuals = np.asarray(observed) - np.asarray(predicted)
    n = len(residuals)
    rss = float(residuals @ residuals)
    variance_mle = max(rss / n, np.finfo(float).tiny)
    log_likelihood = -0.5 * n * (np.log(2 * np.pi * variance_mle) + 1)
    # Variance is estimated and counts as one likelihood parameter.
    k = parameter_count + 1
    aic = 2 * k - 2 * log_likelihood
    aicc = aic + (2 * k * (k + 1)) / (n - k - 1) if n > k + 1 else np.inf
    bic = k * np.log(n) - 2 * log_likelihood
    return log_likelihood, aic, aicc, bic, np.sqrt(rss / n)


def fit_deterministic(years, populations):
    years = np.asarray(years, dtype=float)
    populations = np.asarray(populations, dtype=float)
    low, high = years.min(), years.max()
    upper_k = max(populations.max() * 10, 1_000)
    specifications = {
        "Logistic": (logistic, [populations.max(), 0.15, np.median(years)],
                     ([populations.max() * 0.5, 1e-6, low - 100], [upper_k, 5, high + 100]),
                     ["carrying_capacity", "growth_rate", "midpoint"]),
        "Gompertz": (gompertz, [populations.max(), 0.1, np.median(years)],
                    ([populations.max() * 0.5, 1e-6, low - 100], [upper_k, 5, high + 100]),
                    ["carrying_capacity", "growth_rate", "midpoint"]),
        "Exponential": (lambda t, n0, r: exponential(t, n0, r, low), [populations[0], 0.05],
                        ([1e-6, -2], [upper_k, 2]), ["initial_scale", "growth_rate"]),
    }
    results = {}
    for name, (function, initial, bounds, labels) in specifications.items():
        params, covariance = curve_fit(function, years, populations, p0=initial,
                                       bounds=bounds, maxfev=100_000)
        predicted = function(years, *params)
        values = _criteria(populations, predicted, len(params))
        results[name] = CurveFit(name, dict(zip(labels, params)), covariance,
                                 predicted, *values)
    return results


def predict_curve(fit: CurveFit, years, origin):
    params = fit.parameters
    if fit.name == "Logistic":
        return logistic(years, **params)
    if fit.name == "Gompertz":
        return gompertz(years, **params)
    return exponential(years, origin=origin, **params)


def prediction_intervals(fit: CurveFit, years, origin, residual_variance, confidence=0.95,
                         simulations=20_000, seed=42):
    """Parameter and observation intervals via asymptotic parametric simulation."""

    years = np.asarray(years, dtype=float)
    mean = predict_curve(fit, years, origin)
    parameter_mean = np.array(list(fit.parameters.values()))
    covariance = (fit.covariance + fit.covariance.T) / 2
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    covariance_psd = eigenvectors @ np.diag(np.maximum(eigenvalues, 0)) @ eigenvectors.T
    rng = np.random.default_rng(seed)
    draws = rng.multivariate_normal(parameter_mean, covariance_psd, simulations)
    if fit.name in {"Logistic", "Gompertz"}:
        draws[:, 0] = np.maximum(draws[:, 0], 1e-6)
        draws[:, 1] = np.maximum(draws[:, 1], 1e-8)
    else:
        draws[:, 0] = np.maximum(draws[:, 0], 1e-6)
    predictions = np.empty((simulations, len(years)))
    for i, params in enumerate(draws):
        if fit.name == "Logistic":
            predictions[i] = logistic(years, *params)
        elif fit.name == "Gompertz":
            predictions[i] = gompertz(years, *params)
        else:
            predictions[i] = exponential(years, *params, origin)
    alpha = 1 - confidence
    confidence_band = np.quantile(predictions, [alpha / 2, 1 - alpha / 2], axis=0)
    observation_draws = predictions + rng.normal(0, np.sqrt(residual_variance), predictions.shape)
    prediction_band = np.quantile(observation_draws, [alpha / 2, 1 - alpha / 2], axis=0)
    return mean, confidence_band, prediction_band
