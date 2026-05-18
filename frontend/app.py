import requests
import streamlit as st

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
