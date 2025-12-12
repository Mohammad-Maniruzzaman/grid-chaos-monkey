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

# --- CUSTOM CSS (HIGH CONTRAST & STABILITY) ---
st.markdown("""
<style>
    /* 1. Force Background & Text Colors */
    .stApp {
        background-color: #0e1117;
        color: #FFFFFF !important;
    }
    
    /* 2. Fix Text Visibility Globally */
    p, div, h1, h2, h3, h4, span, label {
        color: #E0E0E0 !important;
    }
    
    /* 3. High Contrast Cards */
    div[data-testid="stMetric"] {
        background-color: #1E1E1E;
        border: 1px solid #444;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.5);
    }
    div[data-testid="stMetric"] label {
        color: #AAAAAA !important; /* Muted label text */
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #FFFFFF !important; /* Bright Value text */
    }

    /* 4. Sidebar Contrast */
    section[data-testid="stSidebar"] {
        background-color: #161616;
    }
    
    /* 5. Buttons */
    .stButton>button {
        background-color: #D32F2F; /* Darker Red (Less jarring) */
        color: white !important;
        border: none;
        height: 3em;
        width: 100%;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #FF5252;
    }
</style>
""", unsafe_allow_html=True)

# --- HEADER ---
col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    st.title("⚡ GridChaos Overwatch")
    st.caption("RESILIENCE ORCHESTRATION PLATFORM // v2.1")

st.divider()

# --- SIDEBAR: MISSION CONTROL ---
with st.sidebar:
    st.header("🎮 COMMAND CENTER")
    
    with st.container():
        st.subheader("Physical Layer")
        line_id = st.selectbox("Select Transmission Line", options=[1, 2, 3, 4, 5], index=0)
        if st.button("✂️ CUT LINE"):
            try:
                requests.post(f"{API_URL}/inject/line_trip/{line_id}")
                st.toast(f"Line {line_id} Tripped!", icon="🔥")
            except:
                st.error("API Error")

    st.markdown("---")

    with st.container():
        st.subheader("Cyber Layer")
        multiplier = st.slider("Load Spike Severity", 1.0, 3.0, 1.5)
        if st.button("👾 INJECT LOAD SPIKE"):
            try:
                requests.post(f"{API_URL}/inject/load_spike/{multiplier}")
                st.toast("Botnet Activated", icon="👾")
            except:
                st.error("API Error")

    st.markdown("---")
    
    if st.button("🔄 SYSTEM RESET"):
        try:
            requests.post(f"{API_URL}/reset")
            st.toast("System Normalized", icon="✅")
        except:
            st.error("API Error")

# --- MAIN DASHBOARD ---

# 1. TOP ROW: METRICS
# We create empty slots once to prevent layout shifting
col1, col2, col3, col4 = st.columns(4)
metric_volts = col1.empty()
metric_load = col2.empty()
metric_gen = col3.empty()
metric_status = col4.empty()

# 2. CHART AREA
st.subheader("📉 Real-Time Voltage Telemetry")
chart_placeholder = st.empty()

# --- HELPER: DRAW CHART ---
def draw_chart(history):
    df = pd.DataFrame(history)
    fig = go.Figure()
    
    # Line
    fig.add_trace(go.Scatter(
        x=df['time'], 
        y=df['voltage'],
        mode='lines', # Removed markers to reduce flickering
        line=dict(color='#00CC96', width=3),
        fill='tozeroy', 
        fillcolor='rgba(0, 204, 150, 0.1)'
    ))
    
    # Threshold
    fig.add_hline(y=0.90, line_dash="dash", line_color="#FF4B4B")

    # Layout
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=350,
        margin=dict(l=10, r=10, t=10, b=10),
        yaxis=dict(range=[0.8, 1.1], title="Voltage (p.u.)", fixedrange=True), # Fixed range prevents jumping
        xaxis=dict(showticklabels=False, fixedrange=True)
    )
    return fig

# --- EVENT LOOP ---
if "history" not in st.session_state:
    st.session_state.history = []

# Monitoring Toggle (Allows pausing to stop the flicker completely)
if st.toggle("🔴 LIVE DATA FEED", value=True):
    while True:
        try:
            # Get Data
            res = requests.get(f"{API_URL}/status", timeout=1)
            data = res.json()
            volts = data['min_voltage_pu']
            status = data['status']
            
            # UPDATE METRICS
            metric_volts.metric(
                "Min Voltage", 
                f"{volts:.3f} p.u.", 
                delta=f"{(volts-1.0):.3f}", 
                delta_color="inverse" if volts < 0.95 else "off"
            )
            metric_load.metric("Grid Load", f"{data['total_load_mw']:.1f} MW")
            metric_gen.metric("Generation", f"{data['generation_mw']:.1f} MW")
            
            if status == "HEALTHY":
                metric_status.success(f"SYSTEM: {status}")
            elif status == "UNSTABLE":
                metric_status.warning(f"SYSTEM: {status}")
            else:
                metric_status.error(f"SYSTEM: {status}")

            # UPDATE CHART
            st.session_state.history.append({"time": pd.Timestamp.now(), "voltage": volts})
            if len(st.session_state.history) > 60: 
                st.session_state.history.pop(0)
            
            # Render chart
            chart_placeholder.plotly_chart(draw_chart(st.session_state.history), use_container_width=True)
            
        except Exception:
            metric_status.error("Connecting...")
        
        # INCREASED SLEEP TO REDUCE FLICKER (3 Seconds)
        time.sleep(3)
else:
    st.info("Monitoring Paused.")