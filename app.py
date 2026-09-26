"""Interactive, historical population-risk research dashboard."""

import json
import tempfile
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from population_risk.data import arrays, load_population
from population_risk.deterministic import fit_deterministic
from population_risk.stochastic import fit_stochastic

ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / "artifacts"

st.set_page_config(page_title="Kittiwake Risk Lab", page_icon="◌", layout="wide")
st.markdown("""<style>
.block-container {max-width: 1260px; padding-top: 2.4rem; padding-bottom: 3rem;}
h1 {font-family: Georgia, serif; font-weight: 500 !important; font-size: 3.25rem !important; letter-spacing:-1px;}
h2 {font-family: Georgia, serif; font-weight: 500 !important;}
[data-testid="stSidebar"] {border-right:1px solid #d9dfda;}
[data-testid="stMetric"] {border:1px solid #d9dfda;border-radius:10px;padding:18px;background:#fff;}
[data-testid="stMetricValue"] {font-size:1.7rem;}
.eyebrow {font-size:.74rem;letter-spacing:.18em;color:#23727c;font-weight:700;}
.intro {font-size:1.12rem;line-height:1.7;color:#65737a;max-width:850px;}
</style>""", unsafe_allow_html=True)

if not (ARTIFACTS / "metadata.json").exists():
    st.title("Kittiwake Risk Lab")
    st.info("Generate the study artifacts first: `python -m population_risk`.")
    st.stop()


@st.cache_data
def load_artifacts(signature):
    del signature
    names = ["observations", "deterministic_models", "stochastic_models", "holdout_validation",
             "forecast_trajectories", "risk_sensitivity", "extinction_risk"]
    return {name: pd.read_csv(ARTIFACTS / f"{name}.csv") for name in names}


metadata = json.loads((ARTIFACTS / "metadata.json").read_text(encoding="utf-8"))
tables = load_artifacts((ARTIFACTS / "metadata.json").stat().st_mtime_ns)

with st.sidebar:
    st.markdown("### ◌ KITTIWAKE / RISK LAB")
    st.caption("POPULATION DYNAMICS × UNCERTAINTY")
    st.divider()
    section = st.radio("Explore", ["Overview", "Model evidence", "Forecast scenarios",
                                    "Risk explorer", "Use your data", "Method & interview"])
    st.divider()
    st.caption(f"RECORD\n\n{metadata['start_year']} → {metadata['end_year']}")
    st.caption("Historical local population/index · GPDD Main ID 6633")

st.markdown('<div class="eyebrow">CONSERVATION MODELLING / REPRODUCIBLE CASE STUDY</div>', unsafe_allow_html=True)
st.title("How uncertain is population persistence?")
st.markdown('<p class="intro">Deterministic growth curves describe the average shape. Stochastic logistic models ask how demographic and environmental variation changes the range of plausible futures.</p>', unsafe_allow_html=True)
st.divider()

if section == "Overview":
    stochastic = tables["stochastic_models"].sort_values("aicc")
    best = stochastic.iloc[0]
    primary = tables["extinction_risk"]
    primary = primary[(primary.horizon == 30) & (primary.threshold == 10) & (primary.model == best.model)].iloc[0]
    cols = st.columns(4)
    cols[0].metric("Annual observations", metadata["rows"])
    cols[1].metric("Observed window", f"{metadata['start_year']}–{metadata['end_year']}")
    cols[2].metric("Best stochastic AICc", best.model)
    cols[3].metric("30-year risk · threshold 10", f"{primary.probability:.2%}")
    st.image(str(ARTIFACTS / "figures" / "observed_population.png"), width="stretch")
    left, right = st.columns([1.2, 1])
    with left:
        st.markdown("## The corrected question")
        st.write("Starting from the final recorded population of 138 in 1984, how often does a fitted stochastic logistic process first reach a chosen quasi-extinction threshold within a chosen horizon?")
    with right:
        st.markdown("## What changed")
        st.write("The original simulation started from 8 while using a threshold of 10. This rebuild starts at the final observation, fixes seeds, reports Monte Carlo intervals and exposes threshold sensitivity.")
    st.warning("This local historical scenario is not a current forecast for the global species and is not an IUCN assessment.")
    st.download_button("Download generated results", (ARTIFACTS / "RESULTS.md").read_text(encoding="utf-8"), "RESULTS.md", "text/markdown")

elif section == "Model evidence":
    st.markdown("## Fit is evidence, not mechanism")
    tab1, tab2, tab3 = st.tabs(["Deterministic curves", "Stochastic likelihoods", "Time holdout"])
    with tab1:
        st.image(str(ARTIFACTS / "figures" / "deterministic_fits.png"), width="stretch")
        st.dataframe(tables["deterministic_models"][["model", "aicc", "bic", "rmse", "akaike_weight"]], hide_index=True, width="stretch")
        st.caption("AICc adds a small-sample correction. Curve comparison assumes independent Gaussian residuals around calendar-time growth functions.")
    with tab2:
        st.image(str(ARTIFACTS / "figures" / "stochastic_aicc.png"), width="stretch")
        st.dataframe(tables["stochastic_models"][["model", "growth_rate", "carrying_capacity", "sigma_demographic", "sigma_environmental", "aicc", "akaike_weight"]], hide_index=True, width="stretch")
        st.caption("Noise labels describe mathematical variance scaling. Model selection alone cannot identify a biological cause.")
    with tab3:
        st.image(str(ARTIFACTS / "figures" / "holdout_validation.png"), width="stretch")
        st.dataframe(tables["holdout_validation"], hide_index=True, width="stretch")
        st.caption("The first 75% is fitted once; the last 25% is evaluated chronologically. Persistence repeats the previous observed population.")

elif section == "Forecast scenarios":
    st.markdown("## Conditional paths from 1984")
    selected = st.multiselect("Models", ["Demographic", "Environmental", "Combined"], default=["Demographic", "Environmental", "Combined"])
    chart_data = tables["forecast_trajectories"]
    chart_data = chart_data[chart_data.model.isin(selected)]
    if selected:
        bands = alt.Chart(chart_data).mark_area(opacity=0.12).encode(
            x=alt.X("year:Q", title="Scenario year"), y=alt.Y("lower_95:Q", title="Population"),
            y2="upper_95:Q", color="model:N")
        lines = alt.Chart(chart_data).mark_line().encode(x="year:Q", y="median:Q", color="model:N",
                                                        tooltip=["model", "year", "median", "lower_95", "upper_95"])
        threshold = alt.Chart(pd.DataFrame({"y": [10]})).mark_rule(strokeDash=[5, 4], color="#b64d45").encode(y="y:Q")
        st.altair_chart((bands + lines + threshold).properties(height=420).interactive(), width="stretch")
    st.write("Bands are empirical 2.5%–97.5% quantiles from forward simulations conditional on fitted parameters. They include process variation but omit parameter and model-structure uncertainty.")

elif section == "Risk explorer":
    st.markdown("## Assumptions drive tail risk")
    threshold = st.select_slider("Quasi-extinction threshold", options=[5, 10, 25, 50], value=10)
    horizon = st.select_slider("Horizon after 1984", options=[10, 30, 50, 100], value=30)
    risk = tables["extinction_risk"]
    risk = risk[(risk.threshold == threshold) & (risk.horizon == horizon)]
    cols = st.columns(len(risk))
    for column, row in zip(cols, risk.itertuples()):
        column.metric(row.model, f"{row.probability:.2%}")
        if pd.notna(row.mc_ci_low):
            column.caption(f"Monte Carlo 95% interval: {row.mc_ci_low:.2%}–{row.mc_ci_high:.2%}")
    st.image(str(ARTIFACTS / "figures" / "risk_sensitivity.png"), width="stretch")
    st.caption("AICc-weighted risk averages fitted-model probabilities. It has no single-binomial Monte Carlo interval and does not cover structural uncertainty outside the candidate set.")
    st.download_button("Download risk sensitivity table", (ARTIFACTS / "risk_sensitivity.csv").read_bytes(), "risk_sensitivity.csv", "text/csv")

elif section == "Use your data":
    st.markdown("## Run the same model family on another time series")
    st.write("Upload CSV or XLSX data with numeric `SampleYear` and positive `Population` columns. Results remain in this session and are not added to the repository.")
    upload = st.file_uploader("Population time series", type=["csv", "xlsx"])
    if upload:
        suffix = Path(upload.name).suffix.lower()
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temporary:
            temporary.write(upload.getbuffer())
            temporary_path = Path(temporary.name)
        try:
            custom = load_population(temporary_path)
            years, populations = arrays(custom)
            if st.button("Fit models", type="primary"):
                with st.spinner("Fitting deterministic and stochastic candidates…"):
                    deterministic = fit_deterministic(years, populations)
                    stochastic = fit_stochastic(years, populations)
                st.success(f"Validated {len(custom)} observations from {int(years[0])} to {int(years[-1])}.")
                st.dataframe(pd.DataFrame([{"model": name, "AICc": fit.aicc, "RMSE": fit.rmse}
                                           for name, fit in deterministic.items()]), hide_index=True)
                st.dataframe(pd.DataFrame([{"model": name, "AICc": fit.aicc, **fit.parameters}
                                           for name, fit in stochastic.items()]), hide_index=True)
                st.caption("Fit summaries only. Define an ecologically meaningful threshold and validate data provenance before simulating risk.")
        except (ValueError, RuntimeError) as exc:
            st.error(str(exc))

else:
    st.markdown("## Explain the project in three minutes")
    st.markdown("""
1. Fit exponential, logistic and Gompertz curves; compare them with AICc.
2. Express logistic increments with demographic, environmental or combined variance.
3. Estimate parameters by transition maximum likelihood and compare stochastic candidates.
4. Validate on the final quarter of the time series against persistence.
5. Simulate from the last observation, define quasi-extinction explicitly, and report sensitivity and Monte Carlo uncertainty.
6. State the boundary: this is a historical local index with 36 observations, not a present-day species assessment.
""")
    st.markdown("### Reproduce")
    st.code("python -m pip install -r requirements.txt\npython -m population_risk\npython -m streamlit run app.py", language="bash")
    st.download_button("Download interview guide", (ROOT / "docs" / "INTERVIEW_GUIDE.md").read_text(encoding="utf-8"), "INTERVIEW_GUIDE.md", "text/markdown")
    with st.expander("Exact run metadata"):
        st.json(metadata)

st.divider()
st.caption("Historical statistical case study · GPDD Main ID 6633 · Scenario risk is conditional on model, threshold, horizon and numerical assumptions.")
