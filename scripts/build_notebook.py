"""Build an executed, GitHub-readable walkthrough from generated artifacts."""

import contextlib
import io
import json
import os
import platform
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build():
    cells, namespace = [], {}
    execution_count = 0

    def markdown(source):
        cells.append({"cell_type": "markdown", "metadata": {}, "source": source.splitlines(True)})

    def code(source):
        nonlocal execution_count
        execution_count += 1
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exec(compile(source, "01_kittiwake_population_risk.ipynb", "exec"), namespace)
        outputs = []
        if output.getvalue():
            outputs.append({"output_type": "stream", "name": "stdout",
                            "text": output.getvalue().splitlines(True)})
        cells.append({"cell_type": "code", "metadata": {}, "source": source.splitlines(True),
                      "execution_count": execution_count, "outputs": outputs})

    markdown("""# Kittiwake population dynamics and quasi-extinction risk

This executed notebook presents the validated data, fitted-model evidence, chronological holdout and corrected risk scenario. Reusable logic is in `population_risk/`; the notebook reads the exact artifacts used by the dashboard.

**Boundary:** 36 historical observations, 1949–1984. Results describe a conditional local-population scenario, not current global species risk.
""")
    code("""from pathlib import Path
import sys
import json
import pandas as pd

ROOT = Path.cwd() if (Path.cwd() / 'data').exists() else Path.cwd().parent
sys.path.insert(0, str(ROOT))
from population_risk.data import load_population

data = load_population(ROOT / 'data/kittiwake_gpdd_6633.xlsx')
metadata = json.loads((ROOT / 'artifacts/metadata.json').read_text())
print(data.to_string(index=False))
print(f"Observations: {len(data)}; window: {int(data.SampleYear.min())}–{int(data.SampleYear.max())}")
""")
    markdown("""## Deterministic evidence

Exponential, logistic and Gompertz curves are fit under a common Gaussian residual likelihood. AICc is used because the sample is small. Good fit does not identify an ecological mechanism.

![Deterministic fits](../artifacts/figures/deterministic_fits.png)
""")
    code("""deterministic = pd.read_csv(ROOT / 'artifacts/deterministic_models.csv')
print(deterministic[['model', 'aicc', 'bic', 'rmse', 'akaike_weight']].round(4).to_string(index=False))
""")
    markdown("""## Stochastic transition evidence

All stochastic candidates use the same Euler-logistic conditional mean. Their variance scales as population, squared population, or both. These labels describe equations rather than proven causes.
""")
    code("""stochastic = pd.read_csv(ROOT / 'artifacts/stochastic_models.csv')
columns = ['model', 'growth_rate', 'carrying_capacity', 'sigma_demographic', 'sigma_environmental', 'aicc', 'akaike_weight']
print(stochastic[columns].round(4).to_string(index=False))
""")
    markdown("""## Chronological validation

The first 27 observations are fitted; the final nine are tested. Persistence repeats the previous observation. This asks a different question from full-data AICc.
""")
    code("""validation = pd.read_csv(ROOT / 'artifacts/holdout_validation.csv')
print(validation.round(4).to_string(index=False))
""")
    markdown("""## Corrected quasi-extinction scenario

The original notebook starts at the first value (8) while setting quasi-extinction to ≤10, but checks only after taking a step. The corrected primary scenario starts from the final observed population (138 in 1984), uses 20,000 paths and treats threshold crossing as absorbing.
""")
    code("""risk = pd.read_csv(ROOT / 'artifacts/extinction_risk.csv')
primary = risk[(risk.horizon == 30) & (risk.threshold == 10)]
print(primary[['model', 'events', 'simulations', 'probability', 'mc_ci_low', 'mc_ci_high']].round(6).to_string(index=False))
""")
    markdown("""![Risk sensitivity](../artifacts/figures/risk_sensitivity.png)

Zero simulated events do not prove zero risk; the finite-run upper interval remains positive. The AICc-weighted value averages only this candidate set and does not include parameter or broader structural uncertainty.

## Reproduce

```bash
python -m pip install -r requirements-dev.txt
python -m population_risk
python -m pytest -q
python -m streamlit run app.py
```

Read the [methodology](../docs/METHODOLOGY.md), [project audit](../docs/PROJECT_AUDIT.md), [data card](../docs/DATA_CARD.md), and [interview guide](../docs/INTERVIEW_GUIDE.md).
""")
    notebook = {"cells": cells, "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": platform.python_version()}},
        "nbformat": 4, "nbformat_minor": 4}
    target = ROOT / "notebooks" / "01_kittiwake_population_risk.ipynb"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(notebook, indent=1), encoding="utf-8")
    print(f"Executed {execution_count} cells and wrote {target}")


if __name__ == "__main__":
    os.chdir(ROOT)
    build()

