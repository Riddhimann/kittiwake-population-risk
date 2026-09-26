import numpy as np
import pytest

from population_risk.deterministic import fit_deterministic
from population_risk.stochastic import (
    StochasticFit,
    binomial_interval,
    fit_stochastic,
    simulate_paths,
)


@pytest.fixture
def synthetic():
    years = np.arange(2000, 2030, dtype=float)
    population = 180 / (1 + np.exp(-0.3 * (years - 2010)))
    return years, population


def test_deterministic_models_are_finite(synthetic):
    years, population = synthetic
    fits = fit_deterministic(years, population)
    assert set(fits) == {"Logistic", "Gompertz", "Exponential"}
    assert all(np.isfinite([fit.aic, fit.aicc, fit.bic, fit.rmse]).all() for fit in fits.values())
    assert fits["Logistic"].rmse < 1e-5


def test_stochastic_models_are_reproducible(synthetic):
    years, population = synthetic
    first = fit_stochastic(years, population, starts=3, seed=8)
    second = fit_stochastic(years, population, starts=3, seed=8)
    for name in first:
        assert first[name].aicc == pytest.approx(second[name].aicc)
        assert first[name].parameters == pytest.approx(second[name].parameters)


def mock_fit(sigma=0.0):
    return StochasticFit("Demographic", {"growth_rate": 0.2, "carrying_capacity": 100,
                                          "sigma_demographic": sigma}, np.eye(3), 0, 0, 0, 0, True, "")


def test_threshold_is_checked_at_initial_state():
    _, hit, first_hit = simulate_paths(mock_fit(), initial=8, horizon=5, simulations=20,
                                       threshold=10, seed=1)
    assert hit.all()
    assert (first_hit == 0).all()


def test_noiseless_paths_and_reproducibility():
    first = simulate_paths(mock_fit(), initial=50, horizon=5, simulations=10, threshold=10, seed=2)
    second = simulate_paths(mock_fit(), initial=50, horizon=5, simulations=10, threshold=10, seed=2)
    np.testing.assert_array_equal(first[0], second[0])
    assert not first[1].any()
    assert (first[0] >= 0).all()


def test_wilson_interval_handles_zero_events():
    low, high = binomial_interval(0, 20_000)
    assert low >= 0
    assert 0 < high < 0.001

