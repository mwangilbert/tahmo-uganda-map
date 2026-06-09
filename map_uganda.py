import streamlit as st
import pandas as pd
import folium
import zipfile
from streamlit_folium import st_folium
from fastkml import kml
from shapely.geometry import LineString, Point

# Configure wide responsive presentation layout
st.set_page_config(layout="wide", page_title="Global Operations Portal", page_icon="🌐")

# Premium Custom CSS UI Theme Styles
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght=400;500;600;700&display=swap');
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', sans-serif;
        background-color: #FAFAFA;
    }
    .main-title { 
        font-size: 2.2rem !important; 
        font-weight: 700; 
        color: #0F172A; 
        margin-bottom: 0.1rem;
        letter-spacing: -0.025em;
    }
    .sub-title { 
        font-size: 1.05rem !important; 
        color: #64748B; 
        margin-bottom: 1.75rem; 
        font-weight: 400;
    }
    .metric-card {
        background: white;
        padding: 18px;
        border-radius: 12px;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px -1px rgba(0, 0, 0, 0.05);
        border: 1px solid #E2E8F0;
        text-align: left;
    }
    .metric-label {
        font-size: 0.85rem;
        font-weight: 500;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 4px;
    }
    .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #0F172A;
    }
    </style>
    """, unsafe_allow_html=True)

# 1. Safe Data Ingestion with Dynamic Sheet Tracking
@st.cache_data
def load_and_analyze_datasets():
    try:
        base_df = pd.read_excel("Untitled spreadsheet (1).xlsx", sheet_name="Sheet1")
    except Exception:
        base_df = pd.DataFrame({
            'ID': ['ST-001', 'ST-002', 'ARCUS-01', 'ARCUS-02'],
            'Name': ['Nairobi Hub', 'Kampala Base', 'Mombasa ARCUS Node', 'Entebbe ARCUS Node'],
            'Latitude': [-1.2921, 0.3476, -4.0435, 0.0511],
            'Longitude': [36.8219, 32.5825, 39.6682, 32.4424],
            'Country': ['Kenya', 'Uganda', 'Kenya', 'Uganda']
        })
        
    tickets_file = "20260608- Tickets status.xlsx"
    try:
        xl = pd.ExcelFile(tickets_file)
        target_sheet = xl.sheet_names[0]
        for sheet in xl.sheet_names:
            if "OPENTICKETS" in sheet.upper():
                target_sheet = sheet
                break
        tickets_df = pd.read_excel(tickets_file, sheet_name=target_sheet)
    except Exception:
        tickets_df = pd.DataFrame({
            'Station ID': ['ARCUS-01', 'ST-002', 'ARCUS-02'],
            'Issue Category': ['Hardware Breakdown', 'Power Outage', 'Sensor Clean'],
            'Status': ['Open', 'Open', 'Scheduled Visit'],
            'Country': ['Kenya', 'Uganda', 'Uganda'],
            'Link': ['https://ticket.system/arcus-01', 'https://ticket.system/st-002', '']
        })
        
    return base_df, tickets_df

base_df, tickets_df = load_and_analyze_datasets()

# Helper to locate column names dynamically
def find_column(columns, keywords, default=None):
    for col in columns:
        upper = str(col).upper()
        if any(k in upper for k in keywords):
            return col
    return default if default in columns else None

station_id_col = find_column(base_df.columns, ['ID', 'STATION ID', 'STATION'], default='ID')
station_name_col = find_column(base_df.columns, ['NAME', 'SITE', 'LOCATION'], default='Name')
lat_col = find_column(base_df.columns, ['LATITUDE', 'LAT'], default='Latitude')
lon_col = find_column(base_df.columns, ['LONGITUDE', 'LON', 'LONG'], default='Longitude')
country_col = find_column(base_df.columns, ['COUNTRY'], default='Country')

ticket_station_col = find_column(tickets_df.columns, ['STATION ID', 'STATION', 'ID'], default='Station ID')
ticket_category_col = find_column(tickets_df.columns, ['ISSUE CATEGORY', 'CATEGORY', 'TICKET TYPE'], default='Issue Category')
ticket_status_col = find_column(tickets_df.columns, ['STATUS', 'STAGE', 'STATE'], default='Status')
ticket_country_col = find_column(tickets_df.columns, ['COUNTRY'], default='Country')

def pick_col_or_fallback(df, candidate, fallbacks=None):
    if candidate and candidate in df.columns:
        return candidate
    if fallbacks:
        for f in fallbacks:
            if f in df.columns:
                return f
    return df.columns[0] if len(df.columns) > 0 else None

station_id_col = pick_col_or_fallback(base_df, station_id_col, fallbacks=['ID', 'Station ID', 'STATION_ID'])
station_name_col = pick_col_or_fallback(base_df, station_name_col, fallbacks=['Name', 'SITE', 'Location'])
lat_col = pick_col_or_fallback(base_df, lat_col, fallbacks=['Latitude', 'Lat'])
lon_col = pick_col_or_fallback(base_df, lon_col, fallbacks=['Longitude', 'Lon', 'Long'])
country_col = pick_col_or_fallback(base_df, country_col, fallbacks=['Country', 'COUNTRY'])

ticket_station_col = pick_col_or_fallback(tickets_df, ticket_station_col, fallbacks=['Station ID', 'Station', 'ID'])
ticket_category_col = pick_col_or_fallback(tickets_df, ticket_category_col, fallbacks=['Issue Category', 'Category'])
ticket_status_col = pick_col_or_fallback(tickets_df, ticket_status_col, fallbacks=['Status', 'STATE'])
ticket_country_col = pick_col_or_fallback(tickets_df, ticket_country_col, fallbacks=['Country'])

# Clean Strings
base_df[station_id_col] = base_df[station_id_col].astype(str).str.strip()
tickets_df[ticket_station_col] = tickets_df[ticket_station_col].astype(str).str.strip()

# KMZ Parser
@st.cache_data
def parse_kmz_route(kmz_path="route.kmz"):
    try:
        with zipfile.ZipFile(kmz_path, 'r') as z:
            kml_filename = [f for f in z.namelist() if f.endswith('.kml')][0]
            with z.open(kml_filename) as f:
                kml_content = f.read()
        k = kml.KML()
        k.from_string(kml_content)
        lines = []
        def extract_features(element):
            if hasattr(element, 'features'):
                for feature in element.features: extract_features(feature)
            if hasattr(element, 'geometry') and element.geometry:
                if isinstance(element.geometry, LineString):
                    lines.append([[c[1], c[0]] for c in element.geometry.coords])
        extract_features(k)
        return lines
    except Exception:
        return []

route_lines = parse_kmz_route()

# ---------------------------------------------------------
# 🎛️ SIDEBAR CONTROL CONSOLE (Upgraded Filters)
# ---------------------------------------------------------
st.sidebar.header("🎛️ Control Center")

# 1. Scope Selection (Forces Uganda default if available)
available_countries = sorted(list(set(base_df[country_col].dropna().unique()) | set(tickets_df[ticket_country_col].dropna().unique())))
default_country_idx = available_countries.index("Uganda") if "Uganda" in available_countries else 0
selected_country = st.sidebar.selectbox("🗺️ Select Target Country Scope:", available_countries, index=default_country_idx)

# Filter base dataframes down by the chosen country scope
country_stations = base_df[base_df[country_col] == selected_country].copy()
country_tickets = tickets_df[tickets_df[ticket_country_col] == selected_country].copy()

# 2. Ticket Status Filter Block
st.sidebar.subheader("📋 Ticket Workflow State")
if ticket_status_col in country_tickets.columns:
    unique_statuses = sorted(country_tickets[ticket_status_col].dropna().
