import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd

# Lazy import FastF1 inside try-except to handle micropip issues
def load_fastf1():
    try:
        import fastf1
        from fastf1 import plotting
        fastf1.Cache.enable_cache('f1_cache')
        return fastf1, plotting
    except ModuleNotFoundError as e:
        st.error("FastF1 or a required dependency like 'micropip' is not installed.")
        st.stop()

# Load FastF1
fastf1, plotting = load_fastf1()

# Enable plotting theme
plotting.setup_mpl()

# Team color mapping
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

# Apply F1-themed Streamlit style
st.set_page_config(page_title="🏎️ F1 Telemetry Analyzer", layout="wide")
st.markdown("""
    <style>
        .main {
            background-color: #0f0f0f;
            color: white;
        }
        .css-1d391kg, .css-1kyxreq, .css-1v3fvcr {
            background-color: #1c1c1e;
            color: white;
        }
        .stButton>button {
            background-color: #DC0000;
            color: white;
            border-radius: 8px;
        }
    </style>
""", unsafe_allow_html=True)

st.title("🏁 Formula 1 Telemetry & Race Analysis")
st.markdown("Analyze real F1 telemetry and compare drivers like never before.")

# Sidebar - Selections
year = st.sidebar.selectbox("Select Year", list(range(2024, 2018, -1)))
try:
    gp_list = fastf1.events.get_event_schedule(year)['EventName'].tolist()
except Exception as e:
    st.error(f"Failed to load event schedule for {year}: {e}")
    st.stop()

selected_gp = st.sidebar.selectbox("Select Grand Prix", gp_list)
session_type = st.sidebar.selectbox("Session", ['FP1', 'FP2', 'FP3', 'Q', 'R'])

# Load session
try:
    session = fastf1.get_session(year, selected_gp, session_type)
    session.load()
    st.success(f"{session_type} Session Loaded for {selected_gp} {year}")
except Exception as e:
    st.error(f"Error loading session: {e}")
    st.stop()

# Driver selection
try:
    drivers = session.laps['Driver'].unique()
    driver1 = st.selectbox("Select Driver 1", drivers)
    driver2 = st.selectbox("Select Driver 2", drivers)

    lap1 = session.laps.pick_driver(driver1).pick_fastest()
    lap2 = session.laps.pick_driver(driver2).pick_fastest()

    telemetry1 = lap1.get_car_data().add_distance()
    telemetry2 = lap2.get_car_data().add_distance()

    # Get team names for colors
    team1 = lap1['Team']
    team2 = lap2['Team']
    color1 = TEAM_COLORS.get(team1, "#FFFFFF")
    color2 = TEAM_COLORS.get(team2, "#FFFFFF")
except Exception as e:
    st.error(f"Error preparing lap or telemetry data: {e}")
    st.stop()

# Plot function
def plot_telemetry(metric, ylabel):
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(telemetry1['Distance'], telemetry1[metric], label=f"{driver1} ({team1})", color=color1)
    ax.plot(telemetry2['Distance'], telemetry2[metric], label=f"{driver2} ({team2})", color=color2)
    ax.set_xlabel("Distance (m)")
    ax.set_ylabel(ylabel)
    ax.set_title(f"{ylabel} Comparison")
    ax.legend()
    ax.grid(True, linestyle='--', alpha=0.5)
    st.pyplot(fig)

st.subheader("📊 Telemetry Comparison")
plot_telemetry('Speed', 'Speed (km/h)')
plot_telemetry('Throttle', 'Throttle (%)')
plot_telemetry('Brake', 'Brakes (On/Off)')
plot_telemetry('Gear', 'Gear')
plot_telemetry('RPM', 'Engine RPM')

# Fastest lap summary
st.subheader("📝 Fastest Lap Summary")
summary_df = pd.DataFrame({
    'Driver': [driver1, driver2],
    'Team': [team1, team2],
    'LapTime (s)': [lap1['LapTime'].total_seconds(), lap2['LapTime'].total_seconds()],
    'Compound': [lap1['Compound'], lap2['Compound']],
    'TrackStatus': [lap1['TrackStatus'], lap2['TrackStatus']]
})
st.table(summary_df)

# Lap-by-lap comparison section
st.subheader("🔁 Lap-by-Lap Time Comparison")
driver1_laps = session.laps.pick_driver(driver1).pick_quicklaps()
driver2_laps = session.laps.pick_driver(driver2).pick_quicklaps()

lap_comparison_df = pd.DataFrame({
    'LapNumber': driver1_laps['LapNumber'],
    f'{driver1} LapTime (s)': driver1_laps['LapTime'].dt.total_seconds(),
    f'{driver2} LapTime (s)': driver2_laps['LapTime'].dt.total_seconds()
}).dropna()

fig2, ax2 = plt.subplots(figsize=(10, 4))
ax2.plot(lap_comparison_df['LapNumber'], lap_comparison_df[f'{driver1} LapTime (s)'], label=driver1, color=color1)
ax2.plot(lap_comparison_df['LapNumber'], lap_comparison_df[f'{driver2} LapTime (s)'], label=driver2, color=color2)
ax2.set_xlabel("Lap Number")
ax2.set_ylabel("Lap Time (s)")
ax2.set_title("Lap-by-Lap Comparison")
ax2.legend()
ax2.grid(True, linestyle='--', alpha=0.5)
st.pyplot(fig2)

st.markdown("---")
st.markdown("Built with ❤️ for Formula 1 fans by Legion Gamer")

