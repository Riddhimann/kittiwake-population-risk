from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(not (ROOT / "artifacts" / "metadata.json").exists(), reason="Generate artifacts first")
def test_dashboard_sections_render():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    assert not app.exception
    for section in ["Model evidence", "Forecast scenarios", "Risk explorer", "Use your data", "Method & interview"]:
        app.sidebar.radio[0].set_value(section).run()
        assert not app.exception, section

