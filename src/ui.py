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


# =========================================================
# CONFIG
# =========================================================
API_URL = os.getenv("API_URL", "http://localhost:8000")          # inside compose: http://backend:8000
API_URL_HOST = os.getenv("API_URL_HOST", "http://localhost:8000")  # browser-friendly (docs link)

READ_ONLY_MODE = os.getenv("READ_ONLY_MODE", "false").lower() == "true"
DEFAULT_POLL_SECONDS = float(os.getenv("UI_POLL_SECONDS", "4"))
MAX_HISTORY = int(os.getenv("UI_MAX_HISTORY", "180"))

st.set_page_config(
    page_title="GridChaos // Command Center",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================================================
# STYLING (Netflix-ish)
# =========================================================
st.markdown(
    """
<style>
.block-container { padding-top: 1.2rem; padding-bottom: 1.2rem; }
[data-testid="stSidebar"] { padding-top: 1.0rem; }

.gc-card {
  border: 1px solid rgba(255,255,255,0.08);
  background: rgba(255,255,255,0.03);
  border-radius: 14px;
  padding: 14px 14px 10px 14px;
}
.gc-card h4 {
  margin: 0 0 8px 0;
  font-weight: 600;
  font-size: 14px;
  letter-spacing: 0.3px;
  opacity: 0.9;
}
.gc-kpi { font-size: 28px; font-weight: 700; line-height: 1.1; }
.gc-sub { font-size: 12px; opacity: 0.75; }

.gc-pill {
  display: inline-block;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.4px;
  border: 1px solid rgba(255,255,255,0.14);
  background: rgba(255,255,255,0.04);
}
.gc-pill-green { color: #9BE7B2; border-color: rgba(155,231,178,0.35); background: rgba(155,231,178,0.08); }
.gc-pill-amber { color: #FFD48A; border-color: rgba(255,212,138,0.35); background: rgba(255,212,138,0.08); }
.gc-pill-red   { color: #FF8A8A; border-color: rgba(255,138,138,0.35); background: rgba(255,138,138,0.08); }
.gc-pill-gray  { color: #CFCFCF; border-color: rgba(255,255,255,0.16); background: rgba(255,255,255,0.04); }

.gc-accent { color: rgba(229,9,20,1); font-weight: 800; letter-spacing: 0.4px; }

/* BaseWeb dropdown portal readability */
div[data-baseweb="popover"] ul[role="listbox"],
div[data-baseweb="popover"] div[role="listbox"] { background-color: rgba(31,31,31,1) !important; }
div[data-baseweb="popover"] [role="option"],
div[data-baseweb="popover"] [role="option"] * { color: #FFFFFF !important; }
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

# =========================================================
# HELPERS
# =========================================================
def api_get(path: str, timeout: float = 2.0):
    return requests.get(f"{API_URL}{path}", timeout=timeout)

def api_post(path: str, json: dict = None, timeout: float = 4.0):
    return requests.post(f"{API_URL}{path}", json=json, timeout=timeout)

@st.cache_data(ttl=30)
def fetch_scenarios():
    try:
        r = api_get("/scenarios", timeout=2.0)
        r.raise_for_status()
        return r.json().get("scenarios", [])
    except Exception:
        return []

def pill_for_status(status: str) -> str:
    status = (status or "UNKNOWN").upper()
    if status == "HEALTHY":
        return '<span class="gc-pill gc-pill-green">HEALTHY</span>'
    if status == "UNSTABLE":
        return '<span class="gc-pill gc-pill-amber">UNSTABLE</span>'
    if status == "CRITICAL":
        return '<span class="gc-pill gc-pill-red">CRITICAL</span>'
    if status == "BLACKOUT":
        return '<span class="gc-pill gc-pill-gray">BLACKOUT</span>'
    return f'<span class="gc-pill gc-pill-gray">{status}</span>'

def draw_voltage(history):
    df = pd.DataFrame(history) if history else pd.DataFrame({"time": [], "voltage": []})

    fig = go.Figure()
    if not df.empty and "time" in df.columns and "voltage" in df.columns:
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
        height=340,
        margin=dict(l=16, r=16, t=18, b=10),
        yaxis=dict(range=[0.0, 1.1], title="Voltage (p.u.)"),
        xaxis=dict(showticklabels=False),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig

def draw_solver_time(history):
    df = pd.DataFrame(history) if history else pd.DataFrame({"time": [], "solve_time_ms": []})
    if df.empty or "solve_time_ms" not in df.columns:
        df = pd.DataFrame({"time": [], "solve_time_ms": []})
    df = df.dropna(subset=["solve_time_ms"])

    fig = go.Figure()
    if not df.empty:
        fig.add_trace(
            go.Scatter(
                x=df["time"],
                y=df["solve_time_ms"],
                mode="lines",
                line=dict(width=2),
                hovertemplate="Solver: %{y:.2f} ms<extra></extra>",
            )
        )

    fig.update_layout(
        template="plotly_dark",
        height=220,
        margin=dict(l=16, r=16, t=18, b=10),
        yaxis=dict(title="Solve Time (ms)"),
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
    exec_mode = snapshot.get("execution_mode", "sandbox")
    containment = snapshot.get("containment_action")

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
- execution_mode: {exec_mode}
- containment_action: {containment}

Snapshot:
- status: {status}
- min_voltage_pu: {volts:.3f} (target ~1.0)
- total_load_mw: {load:.1f}
- generation_mw: {gen:.1f}

Output:
1) Root cause hypothesis (1–3 bullets)
2) Blast radius / containment assessment (1–2 bullets)
3) Three remediation steps (grid-operator style)
Keep it concise and operational.
""".strip()

        resp = model.generate_content(prompt)
        text = getattr(resp, "text", None)
        if not text:
            return f"AI Error: empty response (model={selected})."
        return text

    except Exception as e:
        return f"AI Failed: {str(e)}"


# =========================================================
# SESSION STATE
# =========================================================
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

# New: Persist operator intent (so UI never looks "wrong")
if "requested_execution_mode" not in st.session_state:
    st.session_state.requested_execution_mode = "guardrailed"
if "requested_max_load_loss_pct" not in st.session_state:
    st.session_state.requested_max_load_loss_pct = 0.20


# =========================================================
# HEADER
# =========================================================
left, right = st.columns([3, 2])
with left:
    st.markdown("## GridChaos Command Center")
    st.caption("Control Plane • Observability • Safety Guardrails • AI RCA")
with right:
    st.markdown(
        "<div style='text-align:right; padding-top:8px;'>"
        "<span class='gc-accent'>SAFE CHAOS</span>"
        "<div class='gc-sub'>Microservices • Auditability • Containment</div>"
        "</div>",
        unsafe_allow_html=True,
    )
st.divider()


# =========================================================
# SNAPSHOT REFRESH
# =========================================================
def refresh_snapshot():
    try:
        r = api_get("/status", timeout=2.0)
        r.raise_for_status()
        st.session_state.snapshot = r.json()
    except Exception:
        st.session_state.snapshot = None


# =========================================================
# SIDEBAR (Control Plane)
# =========================================================
with st.sidebar:
    st.subheader("Control Plane")

    st.link_button("Open API Docs", f"{API_URL_HOST}/docs")

    # Health badge
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
        label_map = {
            s["key"]: f"{s.get('display_name', s['key'])} • Target: {s.get('target','—')}"
            for s in scenarios
            if s.get("key")
        }
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

    st.markdown("### Execution Mode")
    mode_label = st.radio(
        "Mode",
        options=["Sandbox (Uncontained)", "Guardrailed (Contained)"],
        index=1,
        disabled=READ_ONLY_MODE,
    )
    execution_mode = "sandbox" if mode_label.startswith("Sandbox") else "guardrailed"

    max_load_loss_pct = st.slider(
        "Blast Radius Limit (load loss %)",
        min_value=5,
        max_value=90,
        value=int(round(float(st.session_state.requested_max_load_loss_pct) * 100)),
        step=5,
        disabled=(READ_ONLY_MODE or execution_mode != "guardrailed"),
    ) / 100.0

    # Persist operator intent
    st.session_state.requested_execution_mode = execution_mode
    st.session_state.requested_max_load_loss_pct = float(max_load_loss_pct)

    st.markdown("### Experiment Lifecycle")
    c1, c2 = st.columns(2)

    with c1:
        if st.button("Start Experiment", type="primary", disabled=READ_ONLY_MODE):
            payload = {
                "execution_mode": st.session_state.requested_execution_mode,
                "max_load_loss_pct": float(st.session_state.requested_max_load_loss_pct),
                "notes": f"UI start • {mode_label}",
            }
            r = api_post(f"/experiments/start/{st.session_state.scenario}", json=payload)
            if r.status_code >= 300:
                st.error(r.text)
            else:
                # If API echoes these fields, reflect them; otherwise keep UI intent.
                try:
                    started = r.json()
                    st.session_state.requested_execution_mode = started.get(
                        "execution_mode", st.session_state.requested_execution_mode
                    )
                    if "max_load_loss_pct" in started:
                        st.session_state.requested_max_load_loss_pct = float(started["max_load_loss_pct"])
                except Exception:
                    pass

                st.success("Experiment started.")
                refresh_snapshot()

    with c2:
        if st.button("End Experiment", disabled=READ_ONLY_MODE):
            r = api_post("/experiments/end")
            if r.status_code >= 300:
                st.error(r.text)
            else:
                st.success("Experiment ended.")
                refresh_snapshot()

    if st.button("Inject Scenario", disabled=READ_ONLY_MODE):
        r = api_post(f"/inject/scenario/{st.session_state.scenario}")
        if r.status_code >= 300:
            st.error(r.text)
        else:
            st.success("Scenario injected.")
            refresh_snapshot()

    st.markdown("---")
    b1, b2 = st.columns(2)
    with b1:
        if st.button("Reset System", disabled=READ_ONLY_MODE):
            r = api_post("/reset")
            if r.status_code >= 300:
                st.error(r.text)
            else:
                st.success("System reset.")
                refresh_snapshot()
    with b2:
        manual_refresh = st.button("Refresh")

    st.markdown("---")
    st.markdown("### Refresh Policy")
    live = st.toggle("Live Updates", value=True)
    st.session_state.poll_seconds = st.slider(
        "Poll interval (sec)", 2.0, 10.0, float(st.session_state.poll_seconds), 1.0
    )

    st.markdown("### RCA Review Mode")
    st.caption("If RCA is running, live refresh pauses to keep the snapshot stable.")
    st.write(f"Freeze refresh: **{st.session_state.freeze_refresh}**")


# =========================================================
# MAIN CONTENT (Tabs)
# =========================================================
def should_refresh():
    if manual_refresh:
        return True
    if live and not st.session_state.freeze_refresh:
        return True
    return False

if should_refresh():
    refresh_snapshot()

snap = st.session_state.snapshot

tabs = st.tabs(["Command", "Observability", "AI RCA", "Runbook"])

with tabs[0]:
    if not snap:
        st.error("API not reachable. Confirm backend is running and API_URL is correct.")
        st.code(f"API_URL={API_URL}\nAPI_URL_HOST={API_URL_HOST}")
    else:
        status = snap.get("status", "UNKNOWN")
        volts = float(snap.get("min_voltage_pu", 0.0))
        load = float(snap.get("total_load_mw", 0.0))
        gen = float(snap.get("generation_mw", 0.0))
        solve_ms = snap.get("solve_time_ms")
        ctx = snap.get("context", {}) or {}

        active_mode = snap.get("execution_mode", "sandbox")
        containment = snap.get("containment_action")
        blast_tripped = bool(snap.get("blast_radius_triggered", False))
        blast_reason = snap.get("blast_radius_reason")

        if containment == "AUTO_ABORT_ROLLBACK":
            st.error("🛑 SAFETY TRIP: Blast Radius Containment Activated (AUTO_ABORT_ROLLBACK)")
            if blast_reason:
                st.warning(blast_reason)
        elif blast_tripped and blast_reason:
            st.warning(f"⚠️ Blast Radius Warning: {blast_reason}")

        k1, k2, k3, k4, k5 = st.columns([1.2, 1.0, 1.0, 1.0, 1.2])

        with k1:
            st.markdown(
                f"""
<div class="gc-card">
  <h4>Status</h4>
  {pill_for_status(status)}
  <div class="gc-sub" style="margin-top:8px;">
    Active: <b>{active_mode}</b> · Requested: <b>{st.session_state.requested_execution_mode}</b>
  </div>
</div>
""",
                unsafe_allow_html=True,
            )

        with k2:
            st.markdown(
                f"""
<div class="gc-card">
  <h4>Min Voltage</h4>
  <div class="gc-kpi">{volts:.3f}</div>
  <div class="gc-sub">p.u. (target ~1.000)</div>
</div>
""",
                unsafe_allow_html=True,
            )

        with k3:
            st.markdown(
                f"""
<div class="gc-card">
  <h4>Total Load</h4>
  <div class="gc-kpi">{load:.1f}</div>
  <div class="gc-sub">MW</div>
</div>
""",
                unsafe_allow_html=True,
            )

        with k4:
            st.markdown(
                f"""
<div class="gc-card">
  <h4>Generation</h4>
  <div class="gc-kpi">{gen:.1f}</div>
  <div class="gc-sub">MW</div>
</div>
""",
                unsafe_allow_html=True,
            )

        with k5:
            ms_txt = "—"
            try:
                ms_txt = "—" if solve_ms is None else f"{float(solve_ms):.2f}"
            except Exception:
                ms_txt = "—"
            st.markdown(
                f"""
<div class="gc-card">
  <h4>Solver Time</h4>
  <div class="gc-kpi">{ms_txt}</div>
  <div class="gc-sub">ms</div>
</div>
""",
                unsafe_allow_html=True,
            )

        st.markdown("---")
        st.subheader("Voltage Telemetry")

        # Persist voltage + solver time
        solve_ms_val = None
        try:
            solve_ms_val = None if solve_ms is None else float(solve_ms)
        except Exception:
            solve_ms_val = None

        st.session_state.history.append(
            {
                "time": pd.Timestamp.now(),
                "voltage": volts,
                "solve_time_ms": solve_ms_val,
            }
        )
        if len(st.session_state.history) > MAX_HISTORY:
            st.session_state.history.pop(0)

        st.plotly_chart(draw_voltage(st.session_state.history), use_container_width=True)

        st.subheader("Compute Health (Solver Time)")
        st.plotly_chart(draw_solver_time(st.session_state.history), use_container_width=True)

        st.markdown("---")
        with st.expander("Experiment Context", expanded=False):
            st.json(ctx)

with tabs[1]:
    if not snap:
        st.warning("No snapshot available.")
    else:
        st.subheader("Operational Signals")
        rows = [
            ("status", snap.get("status")),
            ("execution_mode", snap.get("execution_mode")),
            ("containment_action", snap.get("containment_action")),
            ("blast_radius_triggered", snap.get("blast_radius_triggered")),
            ("blast_radius_reason", snap.get("blast_radius_reason")),
            ("estimated_load_loss_pct", snap.get("estimated_load_loss_pct")),
            ("solve_time_ms", snap.get("solve_time_ms")),
        ]
        st.dataframe(
            pd.DataFrame(rows, columns=["signal", "value"]),
            use_container_width=True,
            hide_index=True,
        )
        st.caption("Grafana: http://localhost:3000 • InfluxDB: http://localhost:8086")

with tabs[2]:
    st.subheader("AI Incident Analysis (RCA)")
    st.caption("Generates a concise incident-style analysis tied to the current experiment context.")

    if not snap:
        st.warning("No snapshot available.")
    else:
        a, b = st.columns([1, 1])
        with a:
            if st.button("Run RCA", type="primary"):
                st.session_state.freeze_refresh = True
                with st.spinner("Generating RCA..."):
                    st.session_state.ai_rca = get_ai_analysis(snap)
        with b:
            if st.button("Clear RCA"):
                st.session_state.ai_rca = ""
                st.session_state.freeze_refresh = False

        if st.session_state.freeze_refresh:
            st.info("Live refresh paused while reviewing RCA. Click Clear RCA to resume.")

        if st.session_state.ai_rca:
            st.info(st.session_state.ai_rca)
        else:
            st.caption("Click Run RCA to generate analysis. Set GOOGLE_API_KEY to enable.")

with tabs[3]:
    st.subheader("Runbook (Demo + Interview)")
    st.markdown(
        """
### 2-Minute Demo
1) Start **Sandbox** → inject **Hurricane Ida** → show blackout persists  
2) Start **Guardrailed** → inject **Hurricane Ida** → show **SAFETY TRIP** then baseline returns to **HEALTHY**  
3) Point to context fields (scenario/phase/mutation_source/simulation_id) for auditability

### Interview Lines
- “Single-writer control plane prevents concurrent mutation of mutable grid state.”
- “Guardrailed mode enforces blast radius containment with an auto-abort rollback.”
- “We emit correlated telemetry for repeatability and audit trails.”
        """.strip()
    )

# =========================================================
# AUTO-REFRESH LOOP
# =========================================================
if live and not st.session_state.freeze_refresh:
    time.sleep(float(st.session_state.poll_seconds))
    st.rerun()
