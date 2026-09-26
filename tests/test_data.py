import numpy as np
import pandas as pd
import pytest

from population_risk.data import load_population


def valid_frame():
    return pd.DataFrame({"SampleYear": np.arange(2000, 2010), "Population": np.arange(10, 20)})


@pytest.mark.parametrize("problem", ["duplicate", "unsorted", "zero", "missing", "short", "column"])
def test_invalid_inputs(tmp_path, problem):
    frame = valid_frame()
    if problem == "duplicate":
        frame.loc[1, "SampleYear"] = frame.loc[0, "SampleYear"]
    elif problem == "unsorted":
        frame = frame.iloc[::-1]
    elif problem == "zero":
        frame.loc[2, "Population"] = 0
    elif problem == "missing":
        frame.loc[2, "Population"] = np.nan
    elif problem == "short":
        frame = frame.iloc[:7]
    else:
        frame = frame.rename(columns={"Population": "Count"})
    path = tmp_path / "data.csv"
    frame.to_csv(path, index=False)
    with pytest.raises(ValueError):
        load_population(path)


def test_csv_and_excel_are_equivalent(tmp_path):
    frame = valid_frame()
    csv_path, xlsx_path = tmp_path / "data.csv", tmp_path / "data.xlsx"
    frame.to_csv(csv_path, index=False)
    frame.to_excel(xlsx_path, index=False)
    pd.testing.assert_frame_equal(load_population(csv_path), load_population(xlsx_path))

