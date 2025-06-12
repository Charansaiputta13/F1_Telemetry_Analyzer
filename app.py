import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import io
import os

st.set_page_config(page_title="F1 Telemetry Analyzer", layout="wide")
st.markdown("""
    <h1 style='display: flex; align-items: center;'>
        <img src='https://upload.wikimedia.org/wikipedia/commons/3/33/F1.svg' width='60' style='margin-right: 10px;'>
        Formula 1 Telemetry & Race Analysis
    </h1>
""", unsafe_allow_html=True)

# Load FastF1 and setup cache
def load_fastf1():
    try:
        import fastf1
        from fastf1 import plotting
        fastf1.Cache.enable_cache('f1_cache')
        return fastf1, plotting
    except ModuleNotFoundError:
        st.error("FastF1 or required dependencies are missing. Please ensure 'fastf1' is installed.")
        st.stop()

fastf1, plotting = load_fastf1()
plotting.setup_mpl()

# Set team colors
TEAM_COLORS = {
    "Red Bull": "#1E41FF",
    "Ferrari": "#DC0000",
    "Mercedes": "#00D2BE",
    "McLaren": "#FF8700",
    "Aston Martin": "#006F62",
    "Alpine": "#0090FF",
    "Williams": "#005AFF",
    "RB": "#6692FF",
    "Kick Sauber": "#52E252",
    "Haas": "#B6BABD"
}

# Sidebar controls
year = st.sidebar.selectbox("Select Year", list(range(2024, 2018, -1)))
try:
    gp_list = fastf1.events.get_event_schedule(year)['EventName'].tolist()
except Exception as e:
    st.error(f"Failed to load schedule: {e}")
    st.stop()

selected_gp = st.sidebar.selectbox("Select Grand Prix", gp_list)
session_type = st.sidebar.selectbox("Session", ['FP1', 'FP2', 'FP3', 'Q', 'R'])

@st.cache_data(show_spinner=True)
def load_session_data(year, gp, session_type):
    session = fastf1.get_session(year, gp, session_type)
    session.load()
    return session

try:
    session = load_session_data(year, selected_gp, session_type)
    drivers = session.laps['Driver'].unique()
except Exception as e:
    st.error(f"Error loading session: {e}")
    st.stop()

# Driver selection
driver1 = st.selectbox("Select Driver 1", drivers)
driver2 = st.selectbox("Select Driver 2", drivers)

lap1 = session.laps.pick_driver(driver1).pick_fastest()
lap2 = session.laps.pick_driver(driver2).pick_fastest()
telemetry1 = lap1.get_car_data().add_distance()
telemetry2 = lap2.get_car_data().add_distance()

team1 = lap1['Team']
team2 = lap2['Team']
color1 = TEAM_COLORS.get(team1, "#FFFFFF")
color2 = TEAM_COLORS.get(team2, "#FFFFFF")

# Telemetry plot function
def plot_metric(metric, label):
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(telemetry1['Distance'], telemetry1[metric], label=f"{driver1} ({team1})", color=color1)
    ax.plot(telemetry2['Distance'], telemetry2[metric], label=f"{driver2} ({team2})", color=color2)
    ax.set_xlabel("Distance (m)")
    ax.set_ylabel(label)
    ax.set_title(f"{label} Comparison")
    ax.legend()
    ax.grid(True, linestyle='--', alpha=0.5)
    st.pyplot(fig)

# Telemetry comparison section
st.subheader("📊 Telemetry Comparison")
telemetry_metrics = {
    'Speed': 'Speed (km/h)',
    'Throttle': 'Throttle (%)',
    'Brake': 'Brake (On/Off)',
    'RPM': 'Engine RPM',
    'DRS': 'DRS',
    'nGear': 'Gear Number'
}
for metric, label in telemetry_metrics.items():
    if metric in telemetry1.columns and metric in telemetry2.columns:
        plot_metric(metric, label)
    else:
        st.warning(f"'{metric}' data not available.")

# Simple animation using Streamlit's line chart updates
st.subheader("🎞️ Speed Animation Preview")
if st.button("Show Streamlit Animation"):
    from time import sleep
    import numpy as np
    
    placeholder = st.empty()
    for i in range(1, len(telemetry1), 20):
        fig, ax = plt.subplots()
        ax.plot(telemetry1['Distance'][:i], telemetry1['Speed'][:i], color=color1, label=driver1)
        ax.set_xlim(0, telemetry1['Distance'].max())
        ax.set_ylim(0, telemetry1['Speed'].max())
        ax.set_title(f"{driver1} - Speed Animation Preview")
        ax.set_xlabel("Distance (m)")
        ax.set_ylabel("Speed (km/h)")
        ax.legend()
        ax.grid(True, linestyle='--', alpha=0.5)
        placeholder.pyplot(fig)
        sleep(0.05)

# Lap summary
st.subheader("🗘️ Fastest Lap Summary")
sum_df = pd.DataFrame({
    'Driver': [driver1, driver2],
    'Team': [team1, team2],
    'LapTime (s)': [lap1['LapTime'].total_seconds(), lap2['LapTime'].total_seconds()],
    'Compound': [lap1['Compound'], lap2['Compound']],
    'TrackStatus': [lap1['TrackStatus'], lap2['TrackStatus']]
})
st.table(sum_df)

# Lap-by-lap comparison
st.subheader("🔁 Lap-by-Lap Time Comparison")
df1 = session.laps.pick_driver(driver1).pick_quicklaps()
df2 = session.laps.pick_driver(driver2).pick_quicklaps()
comparison_df = pd.DataFrame({
    'Lap': df1['LapNumber'],
    driver1: df1['LapTime'].dt.total_seconds(),
    driver2: df2['LapTime'].dt.total_seconds()
}).dropna()

fig2, ax2 = plt.subplots(figsize=(10, 4))
ax2.plot(comparison_df['Lap'], comparison_df[driver1], label=driver1, color=color1)
ax2.plot(comparison_df['Lap'], comparison_df[driver2], label=driver2, color=color2)
ax2.set_xlabel("Lap")
ax2.set_ylabel("Lap Time (s)")
ax2.set_title("Lap-by-Lap Comparison")
ax2.legend()
ax2.grid(True, linestyle='--', alpha=0.4)
st.pyplot(fig2)

# Export section
st.subheader("📁 Export Data")
if st.button("Download CSV"):
    csv_df = pd.DataFrame({
        'Distance': telemetry1['Distance'],
        f'{driver1}_Speed': telemetry1['Speed'],
        f'{driver2}_Speed': telemetry2['Speed']
    }).dropna()
    csv = csv_df.to_csv(index=False).encode('utf-8')
    st.download_button("Download Telemetry CSV", csv, file_name="telemetry_comparison.csv", mime="text/csv")

if st.button("Download PDF Plot"):
    pdf_fig, pdf_ax = plt.subplots()
    pdf_ax.plot(telemetry1['Distance'], telemetry1['Speed'], label=driver1, color=color1)
    pdf_ax.plot(telemetry2['Distance'], telemetry2['Speed'], label=driver2, color=color2)
    pdf_ax.set_xlabel("Distance")
    pdf_ax.set_ylabel("Speed")
    pdf_ax.set_title("Speed Comparison")
    pdf_ax.legend()
    pdf_buf = io.BytesIO()
    pdf_fig.savefig(pdf_buf, format='pdf')
    pdf_buf.seek(0)
    st.download_button("Download PDF", pdf_buf, file_name="speed_plot.pdf")
    plt.close(pdf_fig)

st.markdown("---")
st.markdown("Built with ❤️ by Legion Gamer")
