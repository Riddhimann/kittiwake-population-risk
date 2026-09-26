"""Input validation for annual population time series."""

from pathlib import Path

import numpy as np
import pandas as pd

REQUIRED = ["SampleYear", "Population"]


def load_population(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if path.suffix.lower() == ".xlsx":
        frame = pd.read_excel(path, sheet_name="Sheet1")
    elif path.suffix.lower() == ".csv":
        frame = pd.read_csv(path)
    else:
        raise ValueError("Input must be .xlsx or .csv")
    missing = set(REQUIRED) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    frame = frame[REQUIRED].copy()
    frame[REQUIRED] = frame[REQUIRED].apply(pd.to_numeric, errors="raise")
    if frame.isna().any().any() or not np.isfinite(frame.to_numpy()).all():
        raise ValueError("Years and populations must be finite and complete.")
    if frame.SampleYear.duplicated().any() or not frame.SampleYear.is_monotonic_increasing:
        raise ValueError("SampleYear must be unique and strictly increasing.")
    if (frame.Population <= 0).any():
        raise ValueError("Observed populations must be positive.")
    gaps = np.diff(frame.SampleYear.to_numpy(float))
    if not np.all(gaps > 0):
        raise ValueError("Observation intervals must be positive.")
    if len(frame) < 8:
        raise ValueError("At least eight observations are required.")
    return frame.reset_index(drop=True)


def arrays(frame: pd.DataFrame):
    return frame.SampleYear.to_numpy(float), frame.Population.to_numpy(float)

