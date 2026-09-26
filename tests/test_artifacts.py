import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(not (ROOT / "artifacts" / "metadata.json").exists(), reason="Generate artifacts first")
def test_artifact_provenance_and_primary_scenario():
    metadata = json.loads((ROOT / "artifacts" / "metadata.json").read_text())
    data_path = ROOT / "data" / "kittiwake_gpdd_6633.xlsx"
    assert metadata["data_sha256"] == hashlib.sha256(data_path.read_bytes()).hexdigest()
    assert metadata["initial_population"] == 138
    risk = pd.read_csv(ROOT / "artifacts" / "extinction_risk.csv")
    primary = risk[(risk.horizon == 30) & (risk.threshold == 10)]
    assert set(primary.model) == {"Demographic", "Environmental", "Combined", "AICc-weighted"}
    assert primary.probability.between(0, 1).all()

