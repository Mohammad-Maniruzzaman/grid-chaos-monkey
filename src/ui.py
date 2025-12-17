import streamlit as st
import requests
import time
import pandas as pd
import plotly.graph_objects as go
import os
import google.generativeai as genai

# --- CONFIGURATION ---
API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="GridChaos Overwatch",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS (FORCE VISIBILITY) ---
st.markdown("""
<style>
    /* 1. Force Global Dark Background */
    .stApp {
        background-color: #0e1117;
        color: #FFFFFF;
    }
    
    /* 2. SIDEBAR VISIBILITY */
    /* Force sidebar background */
    section[data-testid="stSidebar"] {
        background-color: #161616;
    }
    /* Force all text in sidebar to be White */
    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3, 
    section[data-testid="stSidebar"] span, 
    section[data-testid="stSidebar"] div,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] p {
        color: #FFFFFF !important;
    }

    /* 3. INPUT LABELS (Dropdowns & Sliders) */
    /* This targets the text ABOVE the box */
    .stSelectbox label, .stSlider label, .stNumberInput label {
        color: #FFFFFF !important;
        font-size: 16px !important;
        font-weight: bold !important;
    }
    
    /* 4. METRIC CARDS (Voltage, Load, Gen) */
    div[data-testid="stMetric"] {
        background-color: #1E1E1E;
        border: 1px solid #555;
        padding: 15px;
        border-radius: 8px;
    }
    /* The Label (e.g. "Min Voltage") */
    div[data-testid="stMetricLabel"] label, 
    div[data-testid="stMetricLabel"] div,
    div[data-testid="stMetricLabel"] p {
        color: #CCCCCC !important; /* Light Grey */
        font-size: 16px !important;
    }
    /* The Value (e.g. "1.000 p.u.") */
    div[data-testid="stMetricValue"] div {
        color: #FFFFFF !important; /* Bright White */
        font-size: 24px !important;
    }

    /* 5. BUTTONS */
    .stButton>button {
        background-color: #D32F2F;
        color: white !important;
        border: 1px solid #FF5252;
        border-radius: 5px;
        height: 3em;
        width: 100%;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #FF5252;
        border-color: white;
    }
    
    /* 6. Headers (War Room, etc) */
    h1, h2, h3 {
        color: #FFFFFF !important;
    }
</style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.title("⚡ GridChaos Overwatch")
st.caption("RESILIENCE ORCHESTRATION PLATFORM // v4.3 HIGH-VISIBILITY")
st.divider()

# --- HELPER: AI ANALYSIS ---
def get_ai_analysis(volts, load, gen, status):
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key: return "⚠️ **AI Offline:** Key not found."

    try:
        genai.configure(api_key=api_key)
        # Dynamic Model Discovery
        valid_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                valid_models.append(m.name)
        
        if not valid_models:
            return "❌ **AI Error:** No compatible models found."

        selected_model = next((m for m in valid_models if 'flash' in m), valid_models[0])
        model = genai.GenerativeModel(selected_model)
        
        prompt = f"""
        Act as a Senior SRE. Analyze Grid Telemetry:
        - Status: {status}
        - Voltage: {volts:.3f} p.u. (Target: 1.0)
        - Load: {load:.1f} MW
        Provide Root Cause Analysis and 3 Remediation Steps. Concise.
        """
        
        with st.spinner(f'⚡ Analyzing via {selected_model}...'):
            response = model.generate_content(prompt)
            return response.text

    except Exception as e:
        return f"❌ **AI Failed:** {str(e)}"

# --- SIDEBAR: CONTROL PLANE ---
with st.sidebar:
    st.header("📜 WAR ROOM SCENARIOS")
    
    with st.expander("🌊 Hurricane Ida (2021)", expanded=False):
        st.write("**Context:** Flood protection trips lines.")
        if st.button("TRIGGER IDA"):
            requests.post(f"{API_URL}/inject/scenario/hurricane_ida")
            st.toast("Simulated: Hurricane Ida", icon="🌊")

    with st.expander("🔥 Heatwave (2023)", expanded=False):
        st.write("**Context:** Temps >95°F. Grid Sag.")
        if st.button("TRIGGER HEATWAVE"):
            requests.post(f"{API_URL}/inject/scenario/heatwave_2023")
            st.toast("Simulated: Heatwave", icon="🔥")

    with st.expander("⚡ EV Fleet Spike (2024)", expanded=False):
        st.write("**Context:** 50+ Buses sync-charging.")
        if st.button("TRIGGER EV SPIKE"):
            requests.post(f"{API_URL}/inject/scenario/ev_fleet_spike")
            st.toast("Simulated: EV Load Spike", icon="⚡")
            
    with st.expander("🌪️ Superstorm Sandy (2012)", expanded=False):
        st.write("**Context:** Generator Protection Trip.")
        if st.button("TRIGGER SANDY"):
            requests.post(f"{API_URL}/inject/scenario/sandy_2012")
            st.toast("Simulated: Generator Trip", icon="🌪️")

    with st.expander("🌲 Northeast Blackout (2003)", expanded=False):
        st.write("**Context:** Tree Contact Cascade.")
        if st.button("TRIGGER 2003 CASCADE"):
            requests.post(f"{API_URL}/inject/scenario/blackout_2003")
            st.toast("Simulated: Cascade Failure", icon="🌲")

    st.markdown("---")
    
    st.header("🎮 MANUAL FAULT INJECTION")
    with st.expander("Manual Overrides", expanded=True):
        
        st.markdown("**1. Physical Layer**")
        line_id = st.selectbox("Select Transmission Line ID", options=[0, 1, 2, 3, 4], index=0)
        if st.button("✂️ TRIP LINE"):
            requests.post(f"{API_URL}/inject/line_trip/{line_id}")
            st.toast(f"Manual Trip: Line {line_id}", icon="✂️")
        
        st.markdown("---")
        
        st.markdown("**2. Cyber Layer**")
        multiplier = st.slider("Load Spike Multiplier (x)", 1.0, 5.0, 1.5)
        if st.button("👾 INJECT LOAD SPIKE"):
            requests.post(f"{API_URL}/inject/load_spike/{multiplier}")
            st.toast(f"Manual Load Spike: {multiplier}x", icon="👾")

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
            
            # Metrics
            metric_volts.metric("Min Voltage", f"{volts:.3f} p.u.", delta=f"{(volts-1.0):.3f}", delta_color="inverse" if volts < 0.95 else "off")
            metric_load.metric("Grid Load", f"{data['total_load_mw']:.1f} MW")
            metric_gen.metric("Generation", f"{data['generation_mw']:.1f} MW")
            
            # Status Badge (FIXED: White Text on Amber for UNSTABLE)
            status_color = "#00C851" # Green
            text_color = "white"
            
            if status == "UNSTABLE":
                status_color = "#FF8800" # Darker Amber/Orange (Better contrast for white text)
                text_color = "white"     # FORCE WHITE TEXT
            elif status == "CRITICAL" or status == "BLACKOUT":
                status_color = "#ff4444" # Red
                text_color = "white"
                
            metric_status.markdown(f"""<div style="background-color: {status_color}; padding: 15px; border-radius: 8px; text-align: center; border: 1px solid #444;"><h4 style="color: {text_color}; margin:0; padding:0; font-weight:bold;">SYSTEM: {status}</h4></div>""", unsafe_allow_html=True)

            st.session_state.history.append({"time": pd.Timestamp.now(), "voltage": volts})
            if len(st.session_state.history) > 60: st.session_state.history.pop(0)
            chart_placeholder.plotly_chart(draw_chart(st.session_state.history), use_container_width=True)
            
        except Exception:
            metric_status.error("Connecting...")
        time.sleep(3)