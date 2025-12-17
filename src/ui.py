import streamlit as st
import requests
import time
import pandas as pd
import plotly.graph_objects as go
import os

# --- CONFIGURATION ---
API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="GridChaos Overwatch",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS ---
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #FFFFFF !important; }
    p, div, h1, h2, h3, h4, span, label { color: #E0E0E0 !important; }
    div[data-testid="stMetric"] {
        background-color: #1E1E1E; border: 1px solid #444;
        padding: 15px; border-radius: 8px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.5);
    }
    div[data-testid="stMetric"] label { color: #AAAAAA !important; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #FFFFFF !important; }
    section[data-testid="stSidebar"] { background-color: #161616; }
    .stButton>button {
        background-color: #D32F2F; color: white !important;
        border: none; height: 3em; width: 100%; font-weight: bold;
    }
    .stButton>button:hover { background-color: #FF5252; }
</style>
""", unsafe_allow_html=True)

# --- HEADER ---
col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    st.title("⚡ GridChaos Overwatch")
    st.caption("RESILIENCE ORCHESTRATION PLATFORM // v2.7 COMPLETE")

st.divider()

# --- HELPER: AI ANALYSIS ---
def get_ai_analysis(volts, load, gen, status):
    with st.spinner('🤖 AI Agent is analyzing system telemetry...'):
        time.sleep(1.5)
        if status == "HEALTHY":
            return "✅ **AI Assessment:** Nominal Operation. Voltage Profile: Stable (1.0 p.u)."
        if volts == 0.0 or status == "BLACKOUT":
            return "💀 **CRITICAL INCIDENT:** Voltage Collapse. Root Cause: N-1 line loss + Load saturation."
        if volts < 0.96 or status == "UNSTABLE":
            return "⚠️ **RISK HIGH:** Severe Undervoltage. Recommendation: Shed 15% Load."
    return "Analyzing..."

# --- SIDEBAR: MISSION CONTROL ---
with st.sidebar:
    st.header("📜 WAR ROOM SCENARIOS")
    
    # 1. Hurricane Ida
    with st.expander("🌊 Hurricane Ida (2021)", expanded=False):
        st.write("**Context:** Flash floods caused multi-feeder protection trips.")
        if st.button("TRIGGER IDA SIMULATION"):
            requests.post(f"{API_URL}/inject/scenario/hurricane_ida")
            st.toast("Substation Flooding Simulated", icon="🌊")

    # 2. Heatwave 2023
    with st.expander("🔥 Heatwave (2023)", expanded=False):
        st.write("**Context:** Sustained temps >95°F. Reactive reserves depleted.")
        if st.button("TRIGGER HEATWAVE"):
            requests.post(f"{API_URL}/inject/scenario/heatwave_2023")
            st.toast("Voltage Collapse Sequence Started", icon="🔥")

    # 3. EV Fleet Spike
    with st.expander("⚡ EV Fleet Spike (2024)", expanded=False):
        st.write("**Context:** 50+ Buses sync-charging. 40MW step-change.")
        if st.button("TRIGGER EV SPIKE"):
            requests.post(f"{API_URL}/inject/scenario/ev_fleet_spike")
            st.toast("Bus 14 Overload Initiated", icon="⚡")
            
    # 4. Superstorm Sandy
    with st.expander("🌪️ Superstorm Sandy (2012)", expanded=False):
        st.write("**Context:** Relay mis-operation tripped Generators.")
        if st.button("TRIGGER SANDY"):
            requests.post(f"{API_URL}/inject/scenario/sandy_2012")
            st.toast("Generator Protection Trip", icon="🌪️")

    # 5. Blackout 2003
    with st.expander("🌲 Northeast Blackout (2003)", expanded=False):
        st.write("**Context:** Vegetation contact + High Load = Cascade.")
        if st.button("TRIGGER 2003 CASCADE"):
            requests.post(f"{API_URL}/inject/scenario/blackout_2003")
            st.toast("Cascade Sequence Started", icon="🌲")

    st.markdown("---")
    
    # --- MANUAL CONTROL (RESTORED) ---
    st.header("🎮 MANUAL CONTROL")
    with st.expander("Manual Fault Injection", expanded=False):
        line_id = st.selectbox("Select Line", options=[0, 1, 2, 3, 4], index=0)
        if st.button("✂️ CUT LINE"):
            requests.post(f"{API_URL}/inject/line_trip/{line_id}")
            st.toast(f"Line {line_id} Cut", icon="✂️")
        
        multiplier = st.slider("Load Spike", 1.0, 5.0, 1.5)
        if st.button("👾 INJECT SPIKE"):
            requests.post(f"{API_URL}/inject/load_spike/{multiplier}")

    st.markdown("---")
    
    if st.button("🔄 SYSTEM RESET", type="primary"):
        requests.post(f"{API_URL}/reset")
        st.toast("System Normalized", icon="✅")

# --- MAIN DASHBOARD ---
col1, col2, col3, col4 = st.columns(4)
metric_volts = col1.empty()
metric_load = col2.empty()
metric_gen = col3.empty()
metric_status = col4.empty()

# AI Section
st.markdown("### 🤖 AI SRE Assistant")
ai_placeholder = st.empty()
if st.button("RUN ROOT CAUSE ANALYSIS", type="primary"):
    try:
        snap = requests.get(f"{API_URL}/status").json()
        analysis = get_ai_analysis(snap['min_voltage_pu'], snap['total_load_mw'], snap['generation_mw'], snap['status'])
        ai_placeholder.info(analysis)
    except:
        ai_placeholder.error("API Error")

# Chart Section
st.subheader("📉 Real-Time Voltage Telemetry")
chart_placeholder = st.empty()

def draw_chart(history):
    df = pd.DataFrame(history)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['time'], y=df['voltage'], mode='lines', line=dict(color='#00CC96', width=3), fill='tozeroy', fillcolor='rgba(0, 204, 150, 0.1)'))
    fig.add_hline(y=0.96, line_dash="dash", line_color="#FFBB33", annotation_text="WARNING")
    fig.add_hline(y=0.90, line_dash="dash", line_color="#FF4B4B", annotation_text="CRITICAL")
    fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=350, margin=dict(l=10, r=10, t=10, b=10), yaxis=dict(range=[0.0, 1.1], title="Voltage (p.u.)", fixedrange=True), xaxis=dict(showticklabels=False, fixedrange=True))
    return fig

# --- EVENT LOOP ---
if "history" not in st.session_state:
    st.session_state.history = []

if st.toggle("🔴 LIVE DATA FEED", value=True):
    while True:
        try:
            res = requests.get(f"{API_URL}/status", timeout=1)
            data = res.json()
            volts = data['min_voltage_pu']
            status = data['status']
            
            # 1. Update Standard Metrics
            metric_volts.metric("Min Voltage", f"{volts:.3f} p.u.", delta=f"{(volts-1.0):.3f}", delta_color="inverse" if volts < 0.95 else "off")
            metric_load.metric("Grid Load", f"{data['total_load_mw']:.1f} MW")
            metric_gen.metric("Generation", f"{data['generation_mw']:.1f} MW")
            
            # 2. CUSTOM STATUS BADGE
            status_color = "#00C851" # Green
            text_color = "white"
            
            if status == "UNSTABLE":
                status_color = "#ea9c00ff" # Yellow
                text_color = "black"
            elif status == "CRITICAL" or status == "BLACKOUT":
                status_color = "#ff4444" # Red
                text_color = "white"
                
            metric_status.markdown(
                f"""
                <div style="background-color: {status_color}; padding: 15px; border-radius: 8px; text-align: center; border: 1px solid #444;">
                    <h4 style="color: {text_color}; margin:0; padding:0; font-weight:bold;">SYSTEM: {status}</h4>
                </div>
                """,
                unsafe_allow_html=True
            )

            # 3. Chart
            st.session_state.history.append({"time": pd.Timestamp.now(), "voltage": volts})
            if len(st.session_state.history) > 60: st.session_state.history.pop(0)
            chart_placeholder.plotly_chart(draw_chart(st.session_state.history), use_container_width=True)
            
        except Exception:
            metric_status.error("Connecting...")
        
        time.sleep(3)