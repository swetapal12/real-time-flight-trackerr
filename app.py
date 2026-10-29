import streamlit as st
import pandas as pd
import requests
import pydeck as pdk

# Page Configuration
st.set_page_config(page_title="Global Real-Time Flight Tracker", layout="wide")

st.title("✈️ Global Real-Time Flight Tracker")
st.markdown("Processing high-velocity streaming ADS-B flight vector data powered by *OpenSky Network*.")

# 1. Fetch live flight data
@st.cache_data(ttl=30)  # Caches data for 30 seconds to respect API limits
def fetch_flight_data():
    url = "https://opensky-network.org/api/states/all"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        columns = [
            "icao24", "callsign", "origin_country", "time_position", "last_contact",
            "longitude", "latitude", "baro_altitude", "on_ground", "velocity",
            "true_track", "vertical_rate", "sensors", "geo_altitude", "squawk", "spi", "position_source"
        ]
        
        df = pd.DataFrame(data['states'], columns=columns)
        
        # Clean up missing coordinates or missing country names
        df = df.dropna(subset=['latitude', 'longitude'])
        df['callsign'] = df['callsign'].str.strip()
        df['velocity'] = df['velocity'].fillna(0)
        df['baro_altitude'] = df['baro_altitude'].fillna(0)
        
        return df
    except Exception as e:
        st.error(f"Error fetching API data: {e}")
        return pd.DataFrame()

# Load Data
with st.spinner("Fetching live global air traffic data..."):
    df = fetch_flight_data()

if not df.empty:
    # 2. Key Metrics Row
    col1, col2, col3, col4 = st.columns(4)
    active_flights = len(df[~df['on_ground']])
    countries_count = df['origin_country'].nunique()
    avg_speed = df['velocity'].mean() * 3.6  # Convert m/s to km/h
    
    col1.metric("Active Airborne Flights", f"{active_flights:,}")
    col2.metric("Countries Represented", f"{countries_count}")
    col3.metric("Average Speed", f"{round(avg_speed, 1)} km/h")
    col4.metric("Total Tracked Vectors", f"{len(df):,}")

    st.markdown("---")

    # 3. Sidebar Filters
    st.sidebar.header("Filter Options")
    selected_country = st.sidebar.selectbox(
        "Filter by Origin Country",
        options=["All"] + sorted(list(df['origin_country'].unique()))
    )

    filtered_df = df if selected_country == "All" else df[df['origin_country'] == selected_country]

    # 4. Interactive Geospatial Map (PyDeck)
    st.subheader("🌐 Live 3D Flight Map")
    
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=filtered_df,
        get_position="[longitude, latitude]",
        get_color="[255, 140, 0, 200]",  # Orange markers
        get_radius=40000,
        pickable=True,
    )

    view_state = pdk.ViewState(
        latitude=filtered_df['latitude'].mean() if not filtered_df.empty else 20.0,
        longitude=filtered_df['longitude'].mean() if not filtered_df.empty else 0.0,
        zoom=1.8,
        pitch=30,
    )

    tooltip = {
        "html": "<b>Callsign:</b> {callsign}<br/>"
                "<b>Country:</b> {origin_country}<br/>"
                "<b>Velocity:</b> {velocity} m/s<br/>"
                "<b>Altitude:</b> {baro_altitude} m",
        "style": {"backgroundColor": "black", "color": "white"}
    }

    st.pydeck_chart(pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style="mapbox://styles/mapbox/dark-v9",
        tooltip=tooltip
    ))

    # 5. Data Analytics Table
    st.subheader("📊 Live Flight Details")
    st.dataframe(
        filtered_df[['callsign', 'origin_country', 'velocity', 'baro_altitude', 'longitude', 'latitude']],
        use_container_width=True
    )