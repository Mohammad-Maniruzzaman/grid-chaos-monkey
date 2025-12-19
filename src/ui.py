import os
import time
import requests
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

try:
    import google.generativeai as genai
except Exception:
    genai = None


# =========================
# CONFIG
# =========================
# Internal API URL (used by Streamlit inside docker-compose network)
API_URL = os.getenv("API_URL", "http://localhost:8000")

# Operator-facing host URL (browser-friendly; only used for the docs link and health badge)
API_URL_HOST = os.getenv("API_URL_HOST", "http://localhost:8000")

READ_ONLY_MODE = os.getenv("READ_ONLY_MODE", "false").lower() == "true"
DEFAULT_POLL_SECONDS = float(os.getenv("UI_POLL_SECONDS", "4"))
MAX_HISTORY = int(os.getenv("UI_MAX_HISTORY", "120"))

st.set_page_config(
    page_title="GridChaos // Command Center",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================
# MINIMAL CSS (dropdown portal readability — Streamlit 1.52.2)
# =========================
st.markdown(
    """
<style>
/* BaseWeb dropdown portal: keep option text visible (including hover) */
div[data-baseweb="popover"] ul[role="listbox"],
div[data-baseweb="popover"] div[role="listbox"] {
  background-color: rgba(31,31,31,1) !important;
}

div[data-baseweb="popover"] [role="option"],
div[data-baseweb="popover"] [role="option"] * {
  color: #FFFFFF !important;
}

div[data-baseweb="popover"] [role="option"]:hover,
div[data-baseweb="popover"] [role="option"]:hover * {
  background-color: rgba(60,60,60,1) !important;
  color: #FFFFFF !important;
}

div[data-baseweb="popover"] [role="option"][aria-selected="true"] {
  background-color: rgba(229,9,20,0.65) !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# =========================
# HELPERS
# =========================
def api_get(path: str, timeout: float = 2.0):
    return requests.get(f"{API_URL}{path}", timeout=timeout)

def api_post(path: str, timeout: float = 4.0):
    return requests.post(f"{API_URL}{path}", timeout=timeout)

def host_get(path: str, timeout: float = 2.0):
    """Operator-facing check (localhost). Does NOT affect internal UI calls."""
    return requests.get(f"{API_URL_HOST}{path}", timeout=timeout)

@st.cache_data(ttl=30)
def fetch_scenarios():
    try:
        r = api_get("/scenarios", timeout=2.0)
        r.raise_for_status()
        return r.json().get("scenarios", [])
    except Exception:
        return []

def draw_voltage(history):
    df = pd.DataFrame(history) if history else pd.DataFrame({"time": [], "voltage": []})

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["time"],
            y=df["voltage"],
            mode="lines",
            fill="tozeroy",
            line=dict(width=3),
            hovertemplate="Min Voltage: %{y:.3f} p.u.<extra></extra>",
        )
    )
    fig.add_hline(y=0.96, line_dash="dash", annotation_text="Warning")
    fig.add_hline(y=0.90, line_dash="dash", annotation_text="Critical")

    fig.update_layout(
        template="plotly_dark",
        height=360,
        margin=dict(l=20, r=20, t=20, b=20),
        yaxis=dict(range=[0.0, 1.1], title="Voltage (p.u.)"),
        xaxis=dict(showticklabels=False),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig

def get_ai_analysis(snapshot: dict) -> str:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return "AI Offline: GOOGLE_API_KEY not set."

    if genai is None:
        return "AI Offline: google-generativeai library not available."

    ctx = snapshot.get("context", {}) or {}
    status = snapshot.get("status", "UNKNOWN")
    volts = float(snapshot.get("min_voltage_pu", 0.0))
    load = float(snapshot.get("total_load_mw", 0.0))
    gen = float(snapshot.get("generation_mw", 0.0))

    try:
        genai.configure(api_key=api_key)

        compatible = []
        for m in genai.list_models():
            methods = getattr(m, "supported_generation_methods", [])
            if "generateContent" in methods:
                compatible.append(m.name)

        if not compatible:
            return "AI Error: No compatible Gemini models found for this API key."

        selected = next((m for m in compatible if "flash" in m.lower()), compatible[0])
        model = genai.GenerativeModel(selected)

        prompt = f"""
Act as a Senior SRE. Provide an incident-style analysis of grid telemetry.

Experiment Context:
- experiment_id: {ctx.get("experiment_id")}
- scenario: {ctx.get("scenario")}
- phase: {ctx.get("phase")}
- mutation_source: {ctx.get("mutation_source")}

Snapshot:
- status: {status}
- min_voltage_pu: {volts:.3f} (target ~1.0)
- total_load_mw: {load:.1f}
- generation_mw: {gen:.1f}

Output:
1) Root cause hypothesis (1–3 bullets)
2) Three remediation steps (grid-operator style)
Keep it concise and operational.
""".strip()

        resp = model.generate_content(prompt)
        text = getattr(resp, "text", None)
        if not text:
            return f"AI Error: empty response (model={selected})."
        return text

    except Exception as e:
        return f"AI Failed: {str(e)}"


# =========================
# SESSION STATE
# =========================
if "history" not in st.session_state:
    st.session_state.history = []
if "snapshot" not in st.session_state:
    st.session_state.snapshot = None
if "scenario" not in st.session_state:
    st.session_state.scenario = "heatwave_2023"
if "poll_seconds" not in st.session_state:
    st.session_state.poll_seconds = DEFAULT_POLL_SECONDS
if "ai_rca" not in st.session_state:
    st.session_state.ai_rca = ""
if "freeze_refresh" not in st.session_state:
    st.session_state.freeze_refresh = False


# =========================
# HEADER
# =========================
st.title("GridChaos Command Center")
st.caption("Control Plane • Observability • AI RCA • Traceability")
st.divider()


# =========================
# SIDEBAR: CONTROL PLANE (operator-friendly)
# =========================
with st.sidebar:
    st.subheader("Control Plane")

    # Operator: one clean entry point (no Docker-internal hostnames)
    st.link_button("Open API Docs", f"{API_URL_HOST}/docs")

    # Operator health badge (based on host URL)
    try:
        r = api_get("/status", timeout=2.0)
        if r.status_code == 200:
            st.success("API Online")
        else:
            st.warning(f"API Degraded ({r.status_code})")
    except Exception:
        st.error("API Unreachable")

    if READ_ONLY_MODE:
        st.warning("Read-only mode is ON (mutations disabled).")
    else:
        st.success("Live control enabled.")

    st.markdown("---")

    scenarios = fetch_scenarios()
    if scenarios:
        # Expect: [{"key": "...", "display_name": "...", "target": "..."}]
        label_map = {s["key"]: f"{s.get('display_name', s['key'])} • Target: {s.get('target','—')}" for s in scenarios if s.get("key")}
        keys = list(label_map.keys())
        if keys and st.session_state.scenario not in keys:
            st.session_state.scenario = keys[0]

        st.session_state.scenario = st.selectbox(
            "Scenario",
            options=keys,
            index=keys.index(st.session_state.scenario) if st.session_state.scenario in keys else 0,
            format_func=lambda k: label_map.get(k, k),
        )
    else:
        st.warning("Scenario registry not reachable. Using manual key.")
        st.session_state.scenario = st.text_input("Scenario key", value=st.session_state.scenario)

    st.markdown("### Experiment Lifecycle")
    c1, c2 = st.columns(2)

    with c1:
        if st.button("Start", disabled=READ_ONLY_MODE):
            r = api_post(f"/experiments/start/{st.session_state.scenario}")
            if r.status_code >= 300:
                st.error(r.text)
            else:
                st.success("Experiment started.")

    with c2:
        if st.button("End", disabled=READ_ONLY_MODE):
            r = api_post("/experiments/end")
            if r.status_code >= 300:
                st.error(r.text)
            else:
                st.success("Experiment ended.")

    if st.button("Inject Scenario", disabled=READ_ONLY_MODE):
        r = api_post(f"/inject/scenario/{st.session_state.scenario}")
        if r.status_code >= 300:
            st.error(r.text)
        else:
            st.success("Scenario injected.")

    st.markdown("---")
    st.markdown("### Manual Fault Injection")

    with st.expander("Physical (Line Trip)", expanded=True):
        line_id = st.selectbox("Line ID", options=[0, 1, 2, 3, 4], index=0)
        if st.button("Trip Line", disabled=READ_ONLY_MODE):
            r = api_post(f"/inject/line_trip/{line_id}")
            if r.status_code >= 300:
                st.error(r.text)
            else:
                st.success(f"Line {line_id} tripped.")

    with st.expander("Cyber (Load Spike)", expanded=True):
        multiplier = st.slider("Multiplier", 1.0, 5.0, 1.5, 0.1)
        if st.button("Inject Load Spike", disabled=READ_ONLY_MODE):
            r = api_post(f"/inject/load_spike/{multiplier}")
            if r.status_code >= 300:
                st.error(r.text)
            else:
                st.success(f"Load spiked by {multiplier}x.")

    st.markdown("---")
    if st.button("Reset System", disabled=READ_ONLY_MODE):
        r = api_post("/reset")
        if r.status_code >= 300:
            st.error(r.text)
        else:
            st.success("System reset.")

    st.markdown("---")
    st.markdown("### Refresh")
    live = st.toggle("Live Updates", value=True)
    st.session_state.poll_seconds = st.slider(
        "Poll interval (sec)",
        2.0,
        10.0,
        float(st.session_state.poll_seconds),
        1.0,
    )
    manual_refresh = st.button("Refresh now")


# =========================
# SNAPSHOT FETCH
# =========================
def refresh_snapshot():
    try:
        r = api_get("/status", timeout=2.0)
        r.raise_for_status()
        st.session_state.snapshot = r.json()
    except Exception:
        pass

if manual_refresh:
    refresh_snapshot()
elif live:
    refresh_snapshot()

snap = st.session_state.snapshot


# =========================
# MAIN DASHBOARD
# =========================
if snap:
    status = snap.get("status", "UNKNOWN")
    volts = float(snap.get("min_voltage_pu", 0.0))
    load = float(snap.get("total_load_mw", 0.0))
    gen = float(snap.get("generation_mw", 0.0))
    ctx = snap.get("context", {}) or {}

    status_map = {
        "HEALTHY": "🟢 HEALTHY",
        "UNSTABLE": "🟠 UNSTABLE",
        "CRITICAL": "🔴 CRITICAL",
        "BLACKOUT": "⚫ BLACKOUT",
    }

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Min Voltage (p.u.)", f"{volts:.3f}", f"{(volts - 1.0):+.3f}")
    k2.metric("Total Load (MW)", f"{load:.1f}")
    k3.metric("Generation (MW)", f"{gen:.1f}")
    k4.metric("Grid Status", status_map.get(status, status))

    st.subheader("Voltage Telemetry")
    st.session_state.history.append({"time": pd.Timestamp.now(), "voltage": volts})
    if len(st.session_state.history) > MAX_HISTORY:
        st.session_state.history.pop(0)
    st.plotly_chart(draw_voltage(st.session_state.history), use_container_width=True)

    st.subheader("AI Incident Analysis")
    ai_area = st.container()
    a, b, c = st.columns([1, 1, 2])

    with a:
        if st.button("Run RCA", type="primary"):
            st.session_state.freeze_refresh = True
            with st.spinner("Generating RCA..."):
                st.session_state.ai_rca = get_ai_analysis(snap)

    with b:
        if st.button("Clear RCA"):
            st.session_state.ai_rca = ""
            st.session_state.freeze_refresh = False

    with c:
        if st.session_state.freeze_refresh:
            st.info("Live refresh paused while reviewing RCA. Click Clear RCA to resume.")

    if st.session_state.ai_rca:
        ai_area.info(st.session_state.ai_rca)
    else:
        ai_area.caption("Run RCA to generate an incident-style analysis tied to the current experiment context.")

    with st.expander("Experiment Context", expanded=False):
        st.json(ctx)

else:
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Min Voltage (p.u.)", "—")
    k2.metric("Total Load (MW)", "—")
    k3.metric("Generation (MW)", "—")
    k4.metric("Grid Status", "CONNECTING")
    st.warning("API not reachable. Confirm backend is running and API_URL is correct.")


# =========================
# CONTROLLED AUTO-REFRESH
# =========================
if live and not st.session_state.freeze_refresh:
    time.sleep(float(st.session_state.poll_seconds))
    st.rerun()
