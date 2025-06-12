import streamlit as st
import pandas as pd
import io
import plotly.graph_objects as go

st.set_page_config(page_title="F1 Telemetry Analyzer", layout="wide")

# Animated header with entrance effect
st.markdown("""
    <style>
        @keyframes fadeInMove {
            0% {opacity: 0; transform: translateY(-20px);}
            100% {opacity: 1; transform: translateY(0);}
        }
        .header-container {
            display: flex;
            align-items: center;
            background-color: #20232A;
            padding: 10px;
            border-radius: 10px;
            animation: fadeInMove 1s ease-in-out;
        }
        .header-title {
            margin: 0;
            color: #61dafb;
        }
        .header-subtitle {
            margin: 0;
            color: #FFFFFF;
            font-size: 16px;
        }
        .logo {
            animation: pulse 2s infinite;
            margin-right: 15px;
        }
        @keyframes pulse {
            0% {transform: scale(1);}
            50% {transform: scale(1.1);}
            100% {transform: scale(1);}
        }
    </style>
    <div class='header-container'>
        <img src='https://upload.wikimedia.org/wikipedia/commons/3/33/F1.svg' width='60' class='logo'>
        <div>
            <h1 class='header-title'>Formula 1 Telemetry & Race Analysis</h1>
            <p class='header-subtitle'>Visualize. Compare. Optimize. Elevate your race insights.</p>
        </div>
    </div>
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
year = st.sidebar.selectbox("Select Year", list(range(2024, 2018, -1)), key='year_selector')
try:
    gp_list = fastf1.events.get_event_schedule(year)['EventName'].tolist()
except Exception as e:
    st.error(f"Failed to load schedule: {e}")
    st.stop()

selected_gp = st.sidebar.selectbox("Select Grand Prix", gp_list, key='gp_selector')
session_type = st.sidebar.selectbox("Session", ['FP1', 'FP2', 'FP3', 'Q', 'R'], key='session_selector')

@st.cache_data(show_spinner="Loading session data...")
def load_session_data(year, gp, session_type):
    session = fastf1.get_session(year, gp, session_type)
    session.load()
    return session

with st.spinner(f"🚥 Warming up the tires and loading {selected_gp} {session_type} data..."):
    try:
        session = load_session_data(year, selected_gp, session_type)
        drivers = session.laps['Driver'].unique()
    except Exception as e:
        st.error(f"Error loading session: {e}")
        st.stop()

# Driver selection
driver1 = st.selectbox("Select Driver 1", drivers, key='driver1_selector')
driver2 = st.selectbox("Select Driver 2", drivers, key='driver2_selector')

driver1_laps = session.laps.pick_driver(driver1).pick_quicklaps()['LapNumber'].tolist()
driver2_laps = session.laps.pick_driver(driver2).pick_quicklaps()['LapNumber'].tolist()

selected_lap1 = st.selectbox(f"Select Lap for {driver1}", driver1_laps, key=f"lap_select_{driver1}")
selected_lap2 = st.selectbox(f"Select Lap for {driver2}", driver2_laps, key=f"lap_select_{driver2}")

lap1 = session.laps.pick_driver(driver1).loc[session.laps['LapNumber'] == selected_lap1].iloc[0]
lap2 = session.laps.pick_driver(driver2).loc[session.laps['LapNumber'] == selected_lap2].iloc[0]

telemetry1 = lap1.get_car_data().add_distance()
telemetry2 = lap2.get_car_data().add_distance()

team1 = lap1['Team']
team2 = lap2['Team']
color1 = TEAM_COLORS.get(team1, "#FFFFFF")
color2 = TEAM_COLORS.get(team2, "#FFFFFF")

# Telemetry comparison section
st.subheader("📊 Telemetry Comparison")

telemetry_metrics = {
    'Speed': 'Speed (km/h)',
    'Throttle': 'Throttle (%)',
    'Brake': 'Brake (On/Off)',
    'RPM': 'Engine RPM',
    'DRS': 'DRS Activation',
    'nGear': 'Gear Number'
}

selected_metrics = st.multiselect("Select telemetry metrics to compare", list(telemetry_metrics.keys()), default=['Speed'], key='metric_selector')

for metric in selected_metrics:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=telemetry1['Distance'], y=telemetry1[metric], mode='lines', name=f"{driver1} ({team1})", line=dict(color=color1)))
    fig.add_trace(go.Scatter(x=telemetry2['Distance'], y=telemetry2[metric], mode='lines', name=f"{driver2} ({team2})", line=dict(color=color2)))
    fig.update_layout(
        title=f"{telemetry_metrics[metric]} Comparison",
        xaxis_title="Distance (m)",
        yaxis_title=telemetry_metrics[metric],
        template='plotly_dark'
    )
    st.plotly_chart(fig, use_container_width=True)

# Sector analysis
st.subheader("⏱️ Sector Analysis")
sectors = ['Sector 1 Time', 'Sector 2 Time', 'Sector 3 Time']
sector_data = {
    'Driver': [driver1, driver2],
    'Sector 1 Time (s)': [lap1['Sector1Time'].total_seconds(), lap2['Sector1Time'].total_seconds()],
    'Sector 2 Time (s)': [lap1['Sector2Time'].total_seconds(), lap2['Sector2Time'].total_seconds()],
    'Sector 3 Time (s)': [lap1['Sector3Time'].total_seconds(), lap2['Sector3Time'].total_seconds()]
}

st.table(pd.DataFrame(sector_data))

# Detailed race summaries
st.subheader("📑 Detailed Race Summaries")

lap_summaries = session.laps.groupby('Driver').agg(
    Total_Laps=('LapNumber', 'max'),
    Average_Lap_Time=('LapTime', lambda x: x.mean().total_seconds()),
    Best_Lap_Time=('LapTime', lambda x: x.min().total_seconds()),
    Pit_Stops=('PitOutTime', lambda x: x.notna().sum())
).reset_index()

st.dataframe(lap_summaries)

# Animation control
st.subheader("🎞️ Speed Animation Preview")
animation_speed = st.slider("Animation Speed (lower is faster)", min_value=10, max_value=100, value=50, step=10, key='animation_speed_slider')

if st.button("Start Speed Animation", key='start_animation_button'):
    from time import sleep

    placeholder = st.empty()
    for i in range(1, len(telemetry1), 20):
        fig_anim = go.Figure()
        fig_anim.add_trace(go.Scatter(x=telemetry1['Distance'][:i], y=telemetry1['Speed'][:i], mode='lines', name=driver1, line=dict(color=color1)))
        fig_anim.update_layout(
            title=f"{driver1} - Speed Animation",
            xaxis_title="Distance (m)",
            yaxis_title="Speed (km/h)",
            template='plotly_dark'
        )
        placeholder.plotly_chart(fig_anim, use_container_width=True)
        sleep(animation_speed / 1000)

# Lap summary
st.subheader("🗘️ Lap Summary")
sum_df = pd.DataFrame({
    'Driver': [driver1, driver2],
    'Team': [team1, team2],
    'Lap Time (s)': [lap1['LapTime'].total_seconds(), lap2['LapTime'].total_seconds()],
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

fig2 = go.Figure()
fig2.add_trace(go.Scatter(x=comparison_df['Lap'], y=comparison_df[driver1], mode='lines+markers', name=driver1, line=dict(color=color1)))
fig2.add_trace(go.Scatter(x=comparison_df['Lap'], y=comparison_df[driver2], mode='lines+markers', name=driver2, line=dict(color=color2)))
fig2.update_layout(
    title="Lap-by-Lap Time Comparison",
    xaxis_title="Lap Number",
    yaxis_title="Lap Time (s)",
    template='plotly_dark'
)
st.plotly_chart(fig2, use_container_width=True)

# Export section
st.subheader("📁 Export Data")
if st.button("Download Telemetry CSV", key='csv_download_button'):
    csv_df = pd.DataFrame({
        'Distance': telemetry1['Distance'],
        f'{driver1}_Speed': telemetry1['Speed'],
        f'{driver2}_Speed': telemetry2['Speed']
    }).dropna()
    csv = csv_df.to_csv(index=False).encode('utf-8')
    st.download_button("Download Telemetry CSV", csv, file_name="telemetry_comparison.csv", mime="text/csv")

if st.button("Download PDF Plot", key='pdf_download_button'):
    import matplotlib.pyplot as plt

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
