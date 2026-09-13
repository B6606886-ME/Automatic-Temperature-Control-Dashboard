import os
import time
import json
import base64
import random
import pandas as pd
import paho.mqtt.client as mqtt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

st.set_page_config(
    page_title="Automatic Temperature Control System for Mobile Blood Units",
    page_icon="🩸",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ----------------- Futuristic Cyberpunk Styling -----------------
st.markdown("""
<style>
    .stApp {
        background: radial-gradient(circle at 50% 10%, #0d1527 0%, #050811 100%);
        color: #e2e8f0;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .project-header-box {
        background: rgba(15, 23, 42, 0.85);
        border: 1px solid rgba(0, 242, 254, 0.4);
        border-radius: 16px;
        padding: 14px 20px;
        box-shadow: 0 0 25px rgba(0, 242, 254, 0.15);
        margin-bottom: 20px;
    }
    .project-code-badge {
        background: rgba(255, 51, 102, 0.2);
        color: #ff3366;
        border: 1px solid #ff3366;
        padding: 3px 10px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 1px;
        display: inline-block;
        margin-bottom: 6px;
    }
    .meta-label { color: #38bdf8; font-weight: 700; font-size: 12px; }
    .meta-value { color: #e2e8f0; font-size: 13px; }
    .cyber-card {
        background: rgba(15, 23, 42, 0.7);
        border: 1px solid rgba(56, 189, 248, 0.35);
        border-radius: 14px;
        padding: 12px 10px;
        text-align: center;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.4);
    }
    .node-title { font-size: 11px; font-weight: 700; letter-spacing: 0.8px; }
    .node-val { font-size: 20px; font-weight: 900; margin: 3px 0; }
    .node-sub { font-size: 10px; color: #94a3b8; }
    .neon-cyan { color: #00f2fe; text-shadow: 0 0 10px rgba(0, 242, 254, 0.6); }
    .neon-red { color: #ff3366; text-shadow: 0 0 10px rgba(255, 51, 102, 0.6); }
    .neon-green { color: #00ff88; text-shadow: 0 0 10px rgba(0, 255, 136, 0.6); }
    .neon-orange { color: #ff9900; text-shadow: 0 0 10px rgba(255, 153, 0, 0.6); }
    .neon-purple { color: #c084fc; text-shadow: 0 0 10px rgba(192, 132, 252, 0.6); }
    [data-testid="stMetric"] {
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 10px 14px;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- Mapping Functions -----------------
def map_cond_fan(pwm):
    if pwm >= 200: return "HIGH", 3
    elif pwm >= 120: return "MED", 2
    elif pwm > 0: return "LOW", 1
    return "OFF", 0

def map_evap_fan(pwm):
    if pwm >= 200: return "HIGH", 3
    elif pwm >= 130: return "MED", 2
    elif pwm > 0: return "LOW", 1
    return "OFF", 0

def map_comp(rpm):
    if rpm >= 2300: return "HIGH", 3
    elif rpm >= 1500: return "MED", 2
    elif rpm > 0: return "LOW", 1
    return "OFF", 0

# ----------------- Base64 Logo Loader -----------------
def get_image_base64(filename):
    if os.path.exists(filename):
        with open(filename, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return None

img_b64 = get_image_base64("watermarked_img_15331780600498095677.png")

# ----------------- MQTT In-Memory Daemon -----------------
MQTT_BROKER = "broker.hivemq.com"
MQTT_TELEMETRY_TOPIC = "cooler/dual_mega_esp32/telemetry"
MQTT_CONTROL_TOPIC = "cooler/dual_mega_esp32/control"

@st.cache_resource
def get_shared_telemetry():
    return {
        "_received_ts": 0,
        "_raw_str": "Waiting for MQTT message...",
        "temp_1": 0.0,
        "temp_2": 0.0,
        "temp_3": 0.0,
        "temp_avg": 0.0,
        "comp_rpm": 0,
        "evap_pwm": 0,
        "cond_pwm": 0
    }

telemetry_store = get_shared_telemetry()

def on_message(client, userdata, msg):
    try:
        raw_text = msg.payload.decode('utf-8')
        payload = json.loads(raw_text)
        telemetry_store["_received_ts"] = time.time()
        telemetry_store["_raw_str"] = raw_text
        for field in ["temp_1", "temp_2", "temp_3", "temp_avg", "comp_rpm", "evap_pwm", "cond_pwm"]:
            if field in payload:
                telemetry_store[field] = payload[field]
    except Exception:
        pass

@st.cache_resource
def start_mqtt_daemon():
    client_id = f"Streamlit-Watcher-{random.randint(10000, 99999)}"
    client = mqtt.Client(client_id=client_id)
    client.on_message = on_message
    try:
        client.connect(MQTT_BROKER, 1883, 60)
        client.subscribe(MQTT_TELEMETRY_TOPIC, qos=0)
        client.loop_start()
    except Exception:
        pass
    return client

mqtt_client = start_mqtt_daemon()

# ดึงข้อมูลจาก In-Memory Store
now_ts = time.time()
last_ts = telemetry_store.get("_received_ts", 0)
esp_online = (now_ts - last_ts) < 5.0 if last_ts > 0 else False

t1 = float(telemetry_store.get("temp_1", 0.0))
t2 = float(telemetry_store.get("temp_2", 0.0))
t3 = float(telemetry_store.get("temp_3", 0.0))
t_avg = float(telemetry_store.get("temp_avg", 0.0))
rpm = int(telemetry_store.get("comp_rpm", 0))
evap_pwm = int(telemetry_store.get("evap_pwm", 0))
cond_pwm = int(telemetry_store.get("cond_pwm", 0))

mega1_online = esp_online and (t1 > 0.0 or t2 > 0.0 or t3 > 0.0)
mega2_online = esp_online and ("comp_rpm" in telemetry_store and rpm >= 0)

# เช็คสถานะการทำงานจริงของเครื่องจักร
hardware_running = (rpm > 0 or evap_pwm > 0 or cond_pwm > 0)

if "system_active" not in st.session_state:
    st.session_state.system_active = hardware_running
else:
    if hardware_running:
        st.session_state.system_active = True

# ----------------- History Buffer (Max 120 points) -----------------
if "history" not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=[
        "time", "temp_1", "temp_2", "temp_3", "temp_avg", "comp_stage", "evap_fan_stage", "cond_fan_stage"
    ])

if esp_online and t_avg > 0:
    cur_time = time.strftime("%H:%M:%S")
    _, c_st = map_comp(rpm)
    _, e_st = map_evap_fan(evap_pwm)
    _, cd_st = map_cond_fan(cond_pwm)

    new_row = pd.DataFrame([{
        "time": cur_time,
        "temp_1": t1, "temp_2": t2, "temp_3": t3, "temp_avg": t_avg,
        "comp_stage": c_st, "evap_fan_stage": e_st, "cond_fan_stage": cd_st
    }])
    st.session_state.history = pd.concat([st.session_state.history, new_row], ignore_index=True).tail(120)

is_safe = (20.0 <= t_avg <= 24.0)
comp_lbl, _ = map_comp(rpm)
evap_lbl, _ = map_evap_fan(evap_pwm)
cond_lbl, _ = map_cond_fan(cond_pwm)

# ----------------- Header & Project Metadata -----------------
top_logo_col, top_title_col = st.columns([2.5, 7.5])

with top_logo_col:
    if img_b64:
        st.markdown(f"""
            <div style="display:flex; justify-content:center; align-items:center; height:100%;">
                <img src="data:image/png;base64,{img_b64}" style="max-width:100%; border-radius:12px; box-shadow:0 0 15px rgba(0,242,254,0.3);">
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <div class='cyber-card neon-cyan' style='padding: 10px;'>
                <div style='font-size: 10px; color:#94a3b8;'>RESEARCH LAB</div>
                <div style='font-size: 14px; font-weight: 800;'>SYSTEM & CONTROL</div>
                <div style='font-size: 10px; color:#38bdf8;'>ENGINEERING LABORATORY</div>
            </div>
        """, unsafe_allow_html=True)

with top_title_col:
    st.markdown("""
        <div>
            <span class="project-code-badge">EP-2568-03-05 | MECHANICAL ENGINEERING CAPSTONE PROJECT</span>
            <h2 style='margin:0; font-size: 21px; line-height: 1.35; letter-spacing: 0.8px;' class='neon-cyan'>
                AUTOMATIC TEMPERATURE CONTROL SYSTEM<br>
                FOR MOBILE BLOOD REFRIGERATION UNITS
            </h2>
            <p style='margin:4px 0 0 0; color: #94a3b8; font-size: 12.5px;'>
                School of Mechanical Engineering, Suranaree University of Technology
            </p>
        </div>
    """, unsafe_allow_html=True)

st.markdown("""
<div class="project-header-box">
    <div style="display: flex; flex-wrap: wrap; justify-content: space-between; gap: 10px;">
        <div>
            <span class="meta-label">👥 Team:</span><br>
            <span class="meta-value">Ms. Supattra Naiwikun | Mr. Phreerapat Thongkliang | Mr. Ratchanon Surat</span>
        </div>
        <div>
            <span class="meta-label">🎓 Advisor:</span><br>
            <span class="meta-value">Assoc. Prof. Dr. Jiraphon Srisertpol</span>
        </div>
        <div>
            <span class="meta-label">🎯 Target Spec:</span><br>
            <span class="meta-value" style="color:#00ff88; font-weight:bold;">Platelet 20.0°C – 24.0°C</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ----------------- 3-Tier Hardware Status -----------------
st.markdown("<h5 style='letter-spacing:1px; color:#38bdf8;'>🛡️ 3-TIER HARDWARE BUS STATUS</h5>", unsafe_allow_html=True)
b1, b2, b3, b4 = st.columns(4)

with b1:
    m1_color = "#00ff88" if mega1_online else "#ff3366"
    m1_text = "ACTIVE (DATA OK)" if mega1_online else "OFFLINE"
    st.markdown(f"""
        <div class="cyber-card" style="border-color: {m1_color};">
            <div class="node-title" style="color:{m1_color};">MEGA 1 (SENSORS & FANS)</div>
            <div style="font-size:16px; font-weight:bold; color:{m1_color};">{m1_text}</div>
            <div class="node-sub">DS18B20 PROBES (3x)</div>
        </div>
    """, unsafe_allow_html=True)

with b2:
    m2_color = "#00ff88" if mega2_online else "#ff3366"
    m2_text = "ACTIVE (RELAY OK)" if mega2_online else "OFFLINE"
    st.markdown(f"""
        <div class="cyber-card" style="border-color: {m2_color};">
            <div class="node-title" style="color:{m2_color};">MEGA 2 (COMPRESSOR)</div>
            <div style="font-size:16px; font-weight:bold; color:{m2_color};">{m2_text}</div>
            <div class="node-sub">SPEED STAGES LINKED</div>
        </div>
    """, unsafe_allow_html=True)

with b3:
    esp_color = "#00ff88" if esp_online else "#ff3366"
    sec_ago = f"{now_ts - last_ts:.1f}s ago" if last_ts > 0 else "NEVER"
    esp_text = f"ONLINE ({sec_ago})" if esp_online else "DISCONNECTED"
    st.markdown(f"""
        <div class="cyber-card" style="border-color: {esp_color};">
            <div class="node-title" style="color:{esp_color};">ESP32 (GATEWAY)</div>
            <div style="font-size:16px; font-weight:bold; color:{esp_color};">{esp_text}</div>
            <div class="node-sub">HIVEMQ BRIDGE SYNC</div>
        </div>
    """, unsafe_allow_html=True)

with b4:
    mqtt_is_ok = mqtt_client.is_connected()
    mqtt_color = "#00ff88" if mqtt_is_ok else "#ff3366"
    mqtt_text = "CONNECTED" if mqtt_is_ok else "CONNECTING..."
    st.markdown(f"""
        <div class="cyber-card" style="border-color: {mqtt_color};">
            <div class="node-title" style="color:{mqtt_color};">HIVEMQ BROKER</div>
            <div style="font-size:16px; font-weight:bold; color:{mqtt_color};">{mqtt_text}</div>
            <div class="node-sub">PORT 1883 (TCP)</div>
        </div>
    """, unsafe_allow_html=True)

st.write("")

# ----------------- Master Power Control Panel -----------------
ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([4, 3, 3])

with ctrl_col1:
    is_running = st.session_state.system_active or hardware_running
    sys_status_str = "🟢 SYSTEM OPERATIONAL (ACTIVE)" if is_running else "🔴 SYSTEM STOPPED (STANDBY)"
    status_cls = "neon-green" if is_running else "neon-red"
    st.markdown(f"""
        <div style="padding-top: 5px;">
            <span style="font-size:12px; color:#94a3b8; letter-spacing:1px; font-weight:bold;">MASTER SYSTEM POWER:</span>
            <div style="font-size:18px; font-weight:bold; margin-top:2px;" class="{status_cls}">{sys_status_str}</div>
        </div>
    """, unsafe_allow_html=True)

with ctrl_col2:
    if st.button("🟢 START / ACTIVATE SYSTEM", use_container_width=True, type="primary"):
        st.session_state.system_active = True
        try:
            mqtt_client.publish(MQTT_CONTROL_TOPIC, "1")
            st.toast("⚡ เริ่มระบบ: ส่งคำสั่ง 1 สำเร็จ!", icon="🟢")
        except Exception:
            pass

with ctrl_col3:
    if st.button("🔴 STOP / EMERGENCY SHUTDOWN", use_container_width=True):
        st.session_state.system_active = False
        try:
            mqtt_client.publish(MQTT_CONTROL_TOPIC, "0")
            st.toast("⚠️ หยุดระบบ: ส่งคำสั่ง 0 สำเร็จ!", icon="🛑")
        except Exception:
            pass

st.write("")

# ----------------- Section 1: Active Process Flow -----------------
st.markdown("<h5 style='letter-spacing:1px; color:#38bdf8;'>⚡ ACTIVE PROCESS SCHEMATIC</h5>", unsafe_allow_html=True)
n1, arr1, n2, arr2, n3, arr3, n4 = st.columns([2.8, 0.4, 2.8, 0.4, 2.8, 0.4, 3.4])

with n1:
    comp_run = (rpm > 0)
    st.markdown(f"""
    <div class="cyber-card" style="border-color: rgba(255, 51, 102, 0.5);">
        <div class="node-title neon-red">① COMPRESSOR</div>
        <div class="node-val neon-red">{comp_lbl} ({rpm} RPM)</div>
        <div class="node-sub">MEGA 2 CONTROLLER</div>
        <div style="margin-top:4px; font-size:10.5px; color:{'#00ff88' if comp_run else '#ff3366'};">
            ● STATE: {'RUNNING' if comp_run else 'STANDBY'}
        </div>
    </div>
    """, unsafe_allow_html=True)

with arr1:
    st.markdown("<h3 style='text-align: center; color: #ff3366; margin-top: 22px;'>➔</h3>", unsafe_allow_html=True)

with n2:
    cond_run = (cond_pwm > 0)
    st.markdown(f"""
    <div class="cyber-card" style="border-color: rgba(255, 153, 0, 0.5);">
        <div class="node-title neon-orange">② CONDENSER (4 FANS)</div>
        <div class="node-val neon-orange">{cond_lbl} (PWM {cond_pwm})</div>
        <div class="node-sub">MEGA 1 (L298N PWM)</div>
        <div style="margin-top:4px; font-size:10.5px; color:{'#00ff88' if cond_run else '#64748b'};">
            ● 4x 24V FANS {'ACTIVE' if cond_run else 'STANDBY'}
        </div>
    </div>
    """, unsafe_allow_html=True)

with arr2:
    st.markdown("<h3 style='text-align: center; color: #c084fc; margin-top: 22px;'>➔</h3>", unsafe_allow_html=True)

with n3:
    evap_run = (evap_pwm > 0)
    st.markdown(f"""
    <div class="cyber-card" style="border-color: rgba(192, 132, 252, 0.5);">
        <div class="node-title neon-purple">③ EVAPORATOR (1 FAN)</div>
        <div class="node-val neon-purple">{evap_lbl} (PWM {evap_pwm})</div>
        <div class="node-sub">MEGA 1 (INTERNAL CIRC)</div>
        <div style="margin-top:4px; font-size:10.5px; color:{'#00ff88' if evap_run else '#64748b'};">
            ● 1x 24V FAN {'ACTIVE' if evap_run else 'STANDBY'}
        </div>
    </div>
    """, unsafe_allow_html=True)

with arr3:
    st.markdown("<h3 style='text-align: center; color: #00f2fe; margin-top: 22px;'>➔</h3>", unsafe_allow_html=True)

with n4:
    status_color = "#00ff88" if (is_safe and t_avg > 0) else "#ff3366"
    status_label = "IN RANGE" if is_safe else "OUT OF LIMITS"
    st.markdown(f"""
    <div class="cyber-card" style="border-color: {status_color};">
        <div class="node-title" style="color: {status_color};">④ CHAMBER CORE (3x PROBES)</div>
        <div class="node-val" style="color: {status_color}; text-shadow: 0 0 10px {status_color}; font-size: 20px;">
            AVG: {t_avg:.2f} °C
        </div>
        <div style="font-size:10px; color:#94a3b8; font-family: monospace; background: rgba(0,0,0,0.35); padding: 3px; border-radius: 4px; margin: 3px 0;">
            T1:{t1:.1f}°C | T2:{t2:.1f}°C | T3:{t3:.1f}°C
        </div>
        <div style="margin-top:2px; font-size:10px; color:{status_color}; font-weight:bold;">
            ● STATUS: {status_label}
        </div>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# ----------------- Section 2: Metrics Bar -----------------
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Chamber Average", f"{t_avg:.2f} °C", delta="Safe (20-24°C)" if is_safe else "Alert", delta_color="normal" if is_safe else "inverse")
m2.metric("Compressor", f"{comp_lbl}", f"{rpm} RPM")
m3.metric("Condenser Fans", f"{cond_lbl}", f"PWM {cond_pwm}")
m4.metric("Evaporator Fan", f"{evap_lbl}", f"PWM {evap_pwm}")
m5.metric("ESP32 Stream", "ONLINE" if esp_online else "OFFLINE", sec_ago)

st.write("")

# ----------------- Section 3: Live Control Matrix Graph -----------------
st.markdown("<h5 style='letter-spacing:1px; color:#38bdf8;'>📊 REAL-TIME COORDINATED CONTROL MATRIX</h5>", unsafe_allow_html=True)

hist = st.session_state.history

if not hist.empty:
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.07,
        subplot_titles=(
            "1) Chamber Thermal Profile (T1, T2, T3 & Average)",
            "2) DC Compressor Multi-Stage Response (2500 RPM=High, 2000 RPM=Med, 0 RPM=Low)",
            "3) Evaporator Fan Response (PWM 255=High, 160=Med, 100=Low)",
            "4) Condenser Fans Response (PWM 255=High, 150=Med, 80=Low)"
        )
    )

    t_data = hist["time"].tolist()

    fig.add_trace(go.Scatter(
        x=t_data + t_data[::-1],
        y=[24.0]*len(t_data) + [20.0]*len(t_data),
        fill='toself',
        fillcolor='rgba(0, 255, 136, 0.12)',
        line=dict(color='rgba(255,255,255,0)'),
        name='Safe Region (20-24°C)',
        hoverinfo='skip'
    ), row=1, col=1)

    fig.add_trace(go.Scatter(x=t_data, y=[24.0]*len(t_data), mode='lines', line=dict(color='#f59e0b', width=1.5, dash='dot'), name='Upper Bound (24°C)'), row=1, col=1)
    fig.add_trace(go.Scatter(x=t_data, y=[22.0]*len(t_data), mode='lines', line=dict(color='#06b6d4', width=1.5, dash='dash'), name='Setpoint (22°C)'), row=1, col=1)
    fig.add_trace(go.Scatter(x=t_data, y=[20.0]*len(t_data), mode='lines', line=dict(color='#3b82f6', width=1.5, dash='dot'), name='Lower Bound (20°C)'), row=1, col=1)
    
    fig.add_trace(go.Scatter(x=t_data, y=hist["temp_1"], mode='lines', line=dict(color='rgba(148, 163, 184, 0.5)', width=1), name='T1 (Top)'), row=1, col=1)
    fig.add_trace(go.Scatter(x=t_data, y=hist["temp_2"], mode='lines', line=dict(color='rgba(148, 163, 184, 0.5)', width=1), name='T2 (Mid)'), row=1, col=1)
    fig.add_trace(go.Scatter(x=t_data, y=hist["temp_3"], mode='lines', line=dict(color='rgba(148, 163, 184, 0.5)', width=1), name='T3 (Bot)'), row=1, col=1)
    fig.add_trace(go.Scatter(x=t_data, y=hist["temp_avg"], mode='lines+markers', line=dict(color='#ff3366', width=2.5), name='AVG Temp (°C)'), row=1, col=1)

    fig.add_trace(go.Scatter(x=t_data, y=hist["comp_stage"], mode='lines+markers', line=dict(color='#38bdf8', width=2), name='Comp Stage'), row=2, col=1)
    fig.add_trace(go.Scatter(x=t_data, y=hist["evap_fan_stage"], mode='lines+markers', line=dict(color='#c084fc', width=2), name='Evap Fan (1x)'), row=3, col=1)
    fig.add_trace(go.Scatter(x=t_data, y=hist["cond_fan_stage"], mode='lines+markers', line=dict(color='#ff9900', width=2), name='Cond Fans (4x)'), row=4, col=1)

    stage_axis = dict(
        tickmode='array',
        tickvals=[0, 1, 2, 3],
        ticktext=['<b>OFF</b>', '<b>Low</b>', '<b>Med</b>', '<b>High</b>'],
        range=[-0.2, 3.4],
        gridcolor='rgba(255, 255, 255, 0.08)'
    )

    fig.update_layout(
        height=780,
        margin=dict(l=40, r=20, t=40, b=30),
        plot_bgcolor='#0b1329',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#94a3b8'),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10, color='#e2e8f0'))
    )

    fig.update_yaxes(title_text="<b>Temp (°C)</b>", gridcolor='rgba(255, 255, 255, 0.08)', row=1, col=1)
    fig.update_yaxes(title_text="<b>Compressor</b>", title_font=dict(color='#38bdf8'), **stage_axis, row=2, col=1)
    fig.update_yaxes(title_text="<b>Evap Fan (1x)</b>", title_font=dict(color='#c084fc'), **stage_axis, row=3, col=1)
    fig.update_yaxes(title_text="<b>Cond Fans (4x)</b>", title_font=dict(color='#ff9900'), **stage_axis, row=4, col=1)
    fig.update_xaxes(title_text="<b>Time (HH:MM:SS)</b>", gridcolor='rgba(255, 255, 255, 0.08)', row=4, col=1)

    for annotation in fig['layout']['annotations']:
        annotation['font'] = dict(size=11, color='#38bdf8')

    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("📡 ได้รับสัญญาณข้อมูลแล้ว กำลังเริ่มต้นวาดกราฟ...")

# ----------------- Debug Stream Inspector -----------------
with st.expander("🔍 RAW MQTT TELEMETRY INSPECTOR", expanded=False):
    st.write(f"**Topic:** `{MQTT_TELEMETRY_TOPIC}`")
    st.code(telemetry_store.get("_raw_str", "No payload yet"), language="json")

time.sleep(1.0)
st.rerun()
