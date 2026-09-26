"""Euler-Gaussian stochastic logistic models and uncertainty calculations."""

from dataclasses import asdict, dataclass

import numpy as np
from scipy.optimize import minimize

MODEL_PARAMETERS = {
    "Demographic": ("growth_rate", "carrying_capacity", "sigma_demographic"),
    "Environmental": ("growth_rate", "carrying_capacity", "sigma_environmental"),
    "Combined": ("growth_rate", "carrying_capacity", "sigma_demographic", "sigma_environmental"),
}


@dataclass
class StochasticFit:
    name: str
    parameters: dict
    covariance: np.ndarray
    log_likelihood: float
    aic: float
    aicc: float
    bic: float
    success: bool
    message: str

    def summary(self):
        result = asdict(self)
        result.pop("covariance")
        return result


def conditional_mean(population, dt, growth_rate, carrying_capacity):
    return population + growth_rate * population * (1 - population / carrying_capacity) * dt


def conditional_variance(population, dt, name, parameters):
    if name == "Demographic":
        return parameters[2] ** 2 * population * dt
    if name == "Environmental":
        return parameters[2] ** 2 * population**2 * dt
    return (parameters[2] ** 2 * population + parameters[3] ** 2 * population**2) * dt


def negative_log_likelihood(parameters, years, populations, name):
    parameters = np.asarray(parameters, dtype=float)
    if not np.isfinite(parameters).all() or parameters[0] <= 0 or parameters[1] <= 0 or np.any(parameters[2:] < 0):
        return np.inf
    dt = np.diff(years)
    previous, observed = populations[:-1], populations[1:]
    mean = conditional_mean(previous, dt, parameters[0], parameters[1])
    variance = conditional_variance(previous, dt, name, parameters)
    if np.any(variance <= 0) or not np.isfinite(mean).all() or not np.isfinite(variance).all():
        return np.inf
    return float(0.5 * np.sum(np.log(2 * np.pi * variance) + (observed - mean) ** 2 / variance))


def _numerical_hessian(function, point):
    point = np.asarray(point, dtype=float)
    n = len(point)
    hessian = np.zeros((n, n))
    steps = 1e-4 * np.maximum(np.abs(point), 1.0)
    f0 = function(point)
    for i in range(n):
        ei = np.zeros(n)
        ei[i] = steps[i]
        hessian[i, i] = (function(point + ei) - 2 * f0 + function(point - ei)) / steps[i] ** 2
        for j in range(i):
            ej = np.zeros(n)
            ej[j] = steps[j]
            value = (function(point + ei + ej) - function(point + ei - ej)
                     - function(point - ei + ej) + function(point - ei - ej)) / (4 * steps[i] * steps[j])
            hessian[i, j] = hessian[j, i] = value
    return hessian


def fit_stochastic(years, populations, starts=8, seed=42):
    years = np.asarray(years, dtype=float)
    populations = np.asarray(populations, dtype=float)
    rng = np.random.default_rng(seed)
    maximum = populations.max()
    results = {}
    for name, labels in MODEL_PARAMETERS.items():
        count = len(labels)
        scale = np.std(np.diff(populations))
        base = np.array([0.3, maximum * 0.9, max(scale / np.sqrt(populations.mean()), 0.1)]
                        + ([max(scale / populations.mean(), 0.01)] if name == "Combined" else []))
        bounds = [(1e-6, 3), (maximum * 0.25, maximum * 20)] + [(1e-8, 100)] * (count - 2)
        candidates = [base]
        for _ in range(starts - 1):
            candidate = base * np.exp(rng.normal(0, 0.7, count))
            candidate[0] = np.clip(candidate[0], 1e-5, 2.5)
            candidate[1] = np.clip(candidate[1], maximum * 0.3, maximum * 15)
            candidates.append(candidate)
        attempts = [minimize(negative_log_likelihood, candidate,
                             args=(years, populations, name), method="L-BFGS-B", bounds=bounds)
                    for candidate in candidates]
        valid = [attempt for attempt in attempts if np.isfinite(attempt.fun)]
        if not valid:
            raise RuntimeError(f"All {name} optimizations failed")
        best = min(valid, key=lambda attempt: attempt.fun)
        if hasattr(best.hess_inv, "todense"):
            covariance = np.asarray(best.hess_inv.todense())
        else:
            def objective(p):
                return negative_log_likelihood(p, years, populations, name)

            hessian = _numerical_hessian(objective, best.x)
            covariance = np.linalg.pinv(hessian)
        log_likelihood = -float(best.fun)
        k, n = count, len(populations) - 1
        aic = 2 * k - 2 * log_likelihood
        aicc = aic + 2 * k * (k + 1) / (n - k - 1) if n > k + 1 else np.inf
        bic = k * np.log(n) - 2 * log_likelihood
        results[name] = StochasticFit(name, dict(zip(labels, best.x)), covariance,
                                      log_likelihood, aic, aicc, bic, bool(best.success), str(best.message))
    return results


def parameter_vector(fit: StochasticFit):
    return np.array([fit.parameters[label] for label in MODEL_PARAMETERS[fit.name]])


def deterministic_path(initial, horizon, growth_rate, carrying_capacity, dt=1.0):
    path = np.empty(horizon + 1, dtype=float)
    path[0] = initial
    for step in range(horizon):
        path[step + 1] = max(conditional_mean(path[step], dt, growth_rate, carrying_capacity), 0)
    return path


def simulate_paths(fit, initial, horizon, simulations=20_000, seed=42, dt=1.0,
                   threshold=10.0, absorbing=True):
    if initial < 0 or horizon < 1 or simulations < 1 or threshold < 0:
        raise ValueError("Invalid simulation arguments")
    params = parameter_vector(fit)
    rng = np.random.default_rng(seed)
    paths = np.empty((simulations, horizon + 1), dtype=float)
    paths[:, 0] = initial
    hit = np.full(simulations, initial <= threshold)
    first_hit = np.where(hit, 0, -1)
    for step in range(horizon):
        current = paths[:, step]
        mean = conditional_mean(current, dt, params[0], params[1])
        variance = conditional_variance(current, dt, fit.name, params)
        proposed = mean + np.sqrt(np.maximum(variance, 0)) * rng.standard_normal(simulations)
        next_values = np.maximum(proposed, 0)
        newly_hit = (~hit) & (next_values <= threshold)
        first_hit[newly_hit] = step + 1
        hit |= newly_hit
        if absorbing:
            next_values[hit] = 0
        paths[:, step + 1] = next_values
    return paths, hit, first_hit


def binomial_interval(successes, total, confidence=0.95):
    """Wilson score interval, stable at zero or full observed events."""
    if total <= 0 or successes < 0 or successes > total:
        raise ValueError("Invalid binomial counts")
    from scipy.stats import norm
    z = norm.ppf(0.5 + confidence / 2)
    p = successes / total
    denominator = 1 + z**2 / total
    center = (p + z**2 / (2 * total)) / denominator
    half = z * np.sqrt(p * (1 - p) / total + z**2 / (4 * total**2)) / denominator
    return max(0.0, center - half), min(1.0, center + half)


def trajectory_intervals(fit, initial, horizon, simulations=20_000, seed=42):
    paths, hit, first_hit = simulate_paths(fit, initial, horizon, simulations, seed)
    quantiles = np.quantile(paths, [0.025, 0.5, 0.975], axis=0)
    cumulative = np.array([(first_hit >= 0) & (first_hit <= step) for step in range(horizon + 1)]).mean(axis=1)
    return paths.mean(axis=0), quantiles, cumulative, int(hit.sum())
