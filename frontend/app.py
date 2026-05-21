import requests
import streamlit as st
import pandas as pd

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Amexio HR Dashboard", layout="wide")
st.title("Amexio HR Dashboard")
st.subheader("Training Budget — 2026")

# ── Fetch aggregated data from the backend ──────────────────────────────────
@st.cache_data(show_spinner=False)
def fetch_data():
    r = requests.get(f"{API_URL}/data")
    r.raise_for_status()
    return r.json()

try:
    data = fetch_data()
except Exception as e:
    st.error(f"Could not reach the backend at {API_URL}. Make sure uvicorn is running.\n\n{e}")
    st.stop()

# ── Company-wide metrics ─────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Budget", f"€{data['total_budget']:,.0f}")
col2.metric("Total Spent", f"€{data['total_spent']:,.0f}")
col3.metric("Remaining", f"€{data['total_remaining']:,.0f}")
col4.metric("Utilisation", f"{data['utilisation_pct']}%")

st.divider()

# ── Department breakdown ─────────────────────────────────────────────────────
st.subheader("By Department")

dept_rows = [
    {
        "Department": d["name"],
        "Budget (€)": f"{d['budget']:,.0f}",
        "Spent (€)": f"{d['spent']:,.0f}",
        "Remaining (€)": f"{d['remaining']:,.0f}",
        "Utilisation": f"{d['utilisation_pct']}%",
    }
    for d in data["by_department"]
]
st.table(dept_rows)

st.divider()

# ── AI Insights panel ────────────────────────────────────────────────────────
st.subheader("AI Insights")

if st.button("Generate Insights", type="primary"):
    with st.spinner("Generating summary via local LLM…"):
        try:
            r = requests.post(f"{API_URL}/summary")
            r.raise_for_status()
            summary = r.json()
            st.session_state["summary"] = summary
        except Exception as e:
            st.error(f"LLM request failed: {e}")

if "summary" in st.session_state:
    brief_tab, standard_tab = st.tabs(["Brief Summary", "Standard Summary"])
    with brief_tab:
        st.write(st.session_state["summary"]["brief"])
    with standard_tab:
        st.write(st.session_state["summary"]["standard"])

st.divider()

# ── Budget forecast panel ───────────────────────────────────────────────────
st.subheader("Budget Forecast")

if st.button("Generate Forecast", type="secondary"):
    with st.spinner("Forecasting next training budget…"):
        try:
            r = requests.get(f"{API_URL}/forecast")
            r.raise_for_status()
            st.session_state["forecast"] = r.json()
        except Exception as e:
            st.error(f"Forecast request failed: {e}")

if "forecast" in st.session_state:
    forecast = st.session_state["forecast"]
    metric_col, status_col = st.columns([2, 1])
    metric_col.metric("Forecast Budget", f"€{forecast['forecast_budget']:,.0f}")
    status_col.metric("Model Ready", "Yes" if forecast.get("model_ready") else "No")
    st.caption(forecast.get("note", ""))
    st.subheader("Per-department forecasts")
    rows = []
    for d in forecast.get("by_department_forecasts", []):
        rows.append({"Department": d["name"], "Forecast Budget (€)": f"€{d['forecast_budget']:,.0f}"})
    if rows:
        st.table(rows)

    # ── Projection charts
    st.subheader("Forecast projections")

    def _linear_projection(current: float, target: float, periods: int = 6) -> pd.DataFrame:
        steps = periods - 1
        values = [current + (target - current) * (i / steps) for i in range(periods)]
        idx = ["Now"] + [f"T+{i}" for i in range(1, periods)]
        return pd.DataFrame({"Forecast": values}, index=idx)

    # Company-level projection
    company_current = data.get("total_budget", 0.0)
    company_target = forecast.get("forecast_budget", company_current)
    company_df = _linear_projection(company_current, company_target, periods=6)
    st.caption("Company-level budget: current vs forecast")
    st.line_chart(company_df)

    # Department selector and projection
    dept_names = [d["name"] for d in data.get("by_department", [])]
    if dept_names:
        sel = st.selectbox("Select department to view projection", options=dept_names)
        # find current and forecast for selection
        current_dept = next((d for d in data.get("by_department", []) if d["name"] == sel), None)
        forecast_dept = next((d for d in forecast.get("by_department_forecasts", []) if d.get("name") == sel), None)
        if current_dept and forecast_dept:
            cur = current_dept.get("budget", 0.0)
            tgt = forecast_dept.get("forecast_budget", cur)
            st.caption(f"{sel}: current budget vs forecast")
            st.line_chart(_linear_projection(cur, tgt, periods=6))

    # Quick comparison bar chart for all departments: current vs forecast
    comp_rows = []
    for d in data.get("by_department", []):
        name = d["name"]
        cur = d.get("budget", 0.0)
        fobj = next((x for x in forecast.get("by_department_forecasts", []) if x.get("name") == name), None)
        tgt = fobj.get("forecast_budget", cur) if fobj else cur
        comp_rows.append({"Department": name, "Current": cur, "Forecast": tgt})
    if comp_rows:
        comp_df = pd.DataFrame(comp_rows).set_index("Department")
        st.caption("Current vs Forecast by department")
        st.bar_chart(comp_df)
