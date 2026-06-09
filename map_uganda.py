import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import re
import urllib.parse  # Safely encodes dynamic text strings for Google URLs

# Configure wide responsive presentation layout
st.set_page_config(layout="wide", page_title="Uganda Operations Portal", page_icon="🇺🇬")

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

# App Title Header Section
st.markdown('<div class="main-title">🇺🇬 Uganda Operations Network Portal</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Live Diagnostics Management and Infrastructure Geo-Spatial Logistics Explorer</div>', unsafe_allow_html=True)

# 1. Safe Excel Data Ingestion with Dynamic Sheet Tracking
@st.cache_data
def load_and_analyze_datasets():
    base_df = pd.read_excel("Untitled spreadsheet (1).xlsx", sheet_name="Sheet1")
    ug_stations = base_df[base_df['Country'] == 'Uganda'].copy()
    
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
        tickets_df = pd.read_excel(tickets_file)
        
    ug_tickets = tickets_df[tickets_df['Country'] == 'Uganda'].copy()
    return ug_stations, ug_tickets

ug_stations, ug_tickets = load_and_analyze_datasets()

# 2. Parse and Clean Field Deployment List
visit_list_raw = """
TA00648, TA00227, TA00225, TA00229, TA00226, TA00231, TA00233, TA00228,
TA00512, TA00232, TA00482, TA00222, TA00220, TA00224TA00653, TA00697,
TA00699, TA00208, TA00695, TA00207, TA00206, TA00708, TA00703, TA00707,
TA00218, TA00219, TA00654, TA00649, TA00650, TA00037, TA00446, TA00036,
TA00221, TA00709, TA00032, TA00205, TA00216, TA0033, TA00220, TA00215,
TA00209, TA00208, TA00207, TA00446
"""
parsed_ids = re.findall(r'TA\d+', visit_list_raw)
clean_visit_ids = list(dict.fromkeys((idx if idx != "TA0033" else "TA00033") for idx in parsed_ids))

# Locate columns dynamically
def find_column(columns, keywords, default=None):
    for col in columns:
        upper = str(col).upper()
        if any(k in upper for k in keywords):
            return col
    return default

station_id_col = find_column(ug_stations.columns, ['ID', 'STATION ID', 'STATION'], default='ID')
station_name_col = find_column(ug_stations.columns, ['NAME', 'SITE', 'LOCATION'], default='Name')
lat_col = find_column(ug_stations.columns, ['LATITUDE', 'LAT'], default='Latitude')
lon_col = find_column(ug_stations.columns, ['LONGITUDE', 'LON', 'LONG'], default='Longitude')
ticket_station_col = find_column(ug_tickets.columns, ['STATION ID', 'STATION', 'ID'], default='Station ID')
ticket_category_col = find_column(ug_tickets.columns, ['ISSUE CATEGORY', 'CATEGORY', 'TICKET TYPE'], default='Issue Category')

# Normalize identifiers for clean cross-referencing
ug_stations[station_id_col] = ug_stations[station_id_col].astype(str).str.strip()
ug_tickets[ticket_station_col] = ug_tickets[ticket_station_col].astype(str).str.strip()

# Find link column
link_col = None
for col in ug_tickets.columns:
    if any(k in str(col).upper() for k in ['LINK', 'URL', 'HYPERLINK', 'TICKET']):
        link_col = col
        break

def clean_txt(val):
    if pd.isna(val): return ""
    return str(val).strip().replace("'", "'").replace('"', '"').replace("\n", "<br>")

# ---------------------------------------------------------
# 🎛️ SIDEBAR CONTROL CONSOLE
# ---------------------------------------------------------
st.sidebar.header("🎛️ Control Center")

st.sidebar.subheader("📍 Deployment Stops")
user_itinerary_input = st.sidebar.text_area("Modify Station Target IDs:", value=", ".join(clean_visit_ids), height=120)
parsed_user_ids = re.findall(r'TA\d+', user_itinerary_input)
clean_visit_ids = list(dict.fromkeys((idx if idx != "TA0033" else "TA00033") for idx in parsed_user_ids))

st.sidebar.subheader("⚠️ Filter Categories")
all_categories = sorted(ug_tickets[ticket_category_col].dropna().unique().tolist())
selected_categories = st.sidebar.multiselect("Active Maintenance Types:", options=all_categories, default=all_categories)
filtered_tickets = ug_tickets[ug_tickets[ticket_category_col].isin(selected_categories)]
ticket_lookup = filtered_tickets.set_index(ticket_station_col)

st.sidebar.subheader("🗺️ Toggle Map Layers")
show_all_stations = st.sidebar.checkbox("Uganda all Stations", value=True)
show_all_tickets = st.sidebar.checkbox("Active Open Tickets (UG)", value=True)
show_itinerary = st.sidebar.checkbox("Sites Scheduled to be Visited (UG)", value=True)
show_arcus = st.sidebar.checkbox("ARCUS Sites", value=True)
show_unvisited = st.sidebar.checkbox("Open Tickets NOT scheduled for Visit", value=True)

st.sidebar.subheader("🔍 Target Asset Focus")
station_options = ["None"] + sorted(ug_stations[station_name_col].dropna().unique().tolist())
searched_station = st.sidebar.selectbox("Isolate Specific Site Node:", station_options)

# Google Route Planner Parameter Setup Inside Control Side Panel
st.sidebar.subheader("🚗 Google Maps Router Engine")
route_origin = st.sidebar.text_input("Route Starting Point:", value="Kampala, Uganda")
route_destination = st.sidebar.text_input("Route Endpoint Destination:", value="Entebbe, Uganda")
travel_mode = st.sidebar.selectbox("Travel Transit Mode:", ["driving", "walking", "bicycling", "transit"])

# --- KPI METRICS LOGIC COMPILATION ---
stations_with_tickets_and_visited = [s_id for s_id in clean_visit_ids if s_id in ticket_lookup.index]
resolved_on_trip = len(stations_with_tickets_and_visited)
total_open_tickets = len(filtered_tickets)
total_unvisited_faults = len([s_id for s_id in ug_stations[station_id_col].values if s_id in ticket_lookup.index and s_id not in clean_visit_ids])

def is_arcus_row(row):
    return any("ARCUS" in str(val).upper() for val in row if pd.notna(val))

arcus_ids = list({str(row[station_id_col]).strip() for _, row in ug_stations.iterrows() if is_arcus_row(row)})
arcus_count = len(arcus_ids)
arcus_with_tickets = len([s_id for s_id in arcus_ids if s_id in ticket_lookup.index])

c1, c2, c3, c4, c5, c6 = st.columns(6)
metric_rows = [
    (c1, 'No of stations', len(ug_stations), '#0F172A'),
    (c2, 'No of tickets', total_open_tickets, '#D97706'),
    (c3, 'No to be visited', len(clean_visit_ids), '#2563EB'),
    (c4, 'No with ticket not to be visited', total_unvisited_faults, '#DC2626'),
    (c5, 'No. of ARCUS', arcus_count, '#7C3AED'),
    (c6, 'Arcus with tickets', arcus_with_tickets, '#A855F7'),
]
for col, label, value, color in metric_rows:
    with col:
        st.markdown(f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value" style="color: {color};">{value}</div></div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 📊 PRESENTATION VIEW ENGINE INTERFACE (MAP WINDOWS)
# ---------------------------------------------------------
map_tab, route_tab = st.tabs(["🗺️ Geospatial Network Explorer Map", "🚗 Live Google Routing Plan Planner"])

with map_tab:
    m = folium.Map(location=[1.3733, 32.2903], zoom_start=7.5, tiles="CartoDB Positron")

    # Initialize Exactly Requested Layers
    layer_all_stations = folium.FeatureGroup(name="Uganda all Stations")
    layer_all_tickets = folium.FeatureGroup(name="Active Open Tickets (UG)")
    layer_visit_itinerary = folium.FeatureGroup(name="Sites Scheduled to be Visited (UG)")
    layer_arcus_subset = folium.FeatureGroup(name="ARCUS Sites")
    layer_tickets_not_visited = folium.FeatureGroup(name="Open Tickets NOT scheduled for Visit.")
    layer_search_highlight = folium.FeatureGroup(name="⭐ Targeted Asset Focus Location")

    def create_styled_popup(title, station_id, station_name, banner_color="#475569"):
        return f'<div style="font-family:\'Inter\',sans-serif;font-size:12px;color:#334155;width:260px;line-height:1.4;padding:2px;"><div style="font-size:11px;font-weight:700;color:white;background-color:{banner_color};padding:5px 8px;border-radius:4px;margin-bottom:6px;text-transform:uppercase;">{title}</div><b>ID:</b> <code style="background-color:#F1F5F9; padding:1px 3px; border-radius:3px;">{clean_txt(station_id)}</code><br><b>Name:</b> {clean_txt(station_name)}</div>'

    def create_detailed_ticket_popup(title, station_id, station_name, t_row, link_col, banner_color, btn_color, bg_light, border_light, text_light):
        ticket_link = ""
        if link_col and link_col in t_row.index:
            raw_url = t_row[link_col]
            if pd.notna(raw_url) and str(raw_url).strip().startswith("http"):
                ticket_link = str(raw_url).strip()
        fields_html = f"<b>Station ID:</b> <code style='background-color:#F1F5F9; padding:1px 3px; border-radius:3px;'>{clean_txt(station_id)}</code><br><b>Station Name:</b> {clean_txt(station_name)}<br>"
        for col in t_row.index:
            if col in [link_col, 'Station ID', 'Country', 'Latitude', 'Longitude', station_id_col]: continue
            val = t_row[col]
            if pd.notna(val) and str(val).strip() != "":
                fields_html += f"<b>{col}:</b> {clean_txt(val)}<br>"
        link_html = f"<div style='margin-bottom:10px;background-color:{bg_light};border:1px solid {border_light};padding:8px;border-radius:6px;'><span style='color:{text_light}; font-weight:700; font-size:10px; display:block; margin-bottom:4px;'>🔗 PRIMARY SYSTEM LINK:</span><a href='{clean_txt(ticket_link)}' target='_blank' style='display:block;text-align:center;background-color:{btn_color};color:white;padding:7px 10px;font-weight:600;text-decoration:none;border-radius:4px;font-size:11px;'>LAUNCH TICKETING PORTAL ↗</a></div>" if ticket_link else ""
        return f'<div style="font-family:\'Inter\',sans-serif;font-size:12px;color:#334155;width:310px;line-height:1.5;padding:2px;"><div style="font-size:11px;font-weight:700;color:white;background-color:{banner_color};padding:5px 8px;border-radius:4px;margin-bottom:8px;text-transform:uppercase;">{title}</div>{link_html}<div style="background-color:#F8FAFC;border:1px solid #E2E8F0;padding:8px;border-radius:6px;max-height:200px;overflow-y:auto;">{fields_html}</div></div>'

    # Processing Loop Map Plotter
    for _, row in ug_stations.iterrows():
        s_id = row[station_id_col]
        s_name = row[station_name_col]
        lat, lon = row[lat_col], row[lon_col]
        
        if show_all_stations:
            p_html1 = create_styled_popup("Grid Node Asset", s_id, s_name, banner_color="#64748B")
            folium.CircleMarker([lat, lon], radius=4, color="#94A3B8", weight=1.5, fill=True, fill_color="#CBD5E1", fill_opacity=0.7, popup=folium.Popup(p_html1, max_width=350)).add_to(layer_all_stations)

        if s_id in ticket_lookup.index:
            t_data = ticket_lookup.loc[s_id]
            t_row = t_data.iloc[0] if isinstance(t_data, pd.DataFrame) else t_data
            if show_all_tickets:
                p_html2 = create_detailed_ticket_popup("🔧 Active Maintenance Alert", s_id, s_name, t_row, link_col, "#D97706", "#2563EB", "#FFFBEB", "#FDE68A", "#B45309")
                folium.Marker([lat, lon], icon=folium.Icon(color="orange", icon="wrench", prefix="fa"), popup=folium.Popup(p_html2, max_width=350)).add_to(layer_all_tickets)
            if show_unvisited and (s_id not in clean_visit_ids):
                p_html5 = create_detailed_ticket_popup("🚨 Unvisited Open Fault", s_id, s_name, t_row, link_col, "#DC2626", "#DC2626", "#FEF2F2", "#FCA5A5", "#DC2626")
                folium.Marker([lat, lon], icon=folium.Icon(color="red", icon="exclamation-triangle", prefix="fa"), popup=folium.Popup(p_html5, max_width=380)).add_to(layer_tickets_not_visited)

        if show_itinerary and (s_id in clean_visit_ids):
            p_html3 = create_styled_popup("Scheduled Route Target", s_id, s_name, banner_color="#2563EB")
            folium.CircleMarker([lat, lon], radius=11, color="#2563EB", weight=3, fill=True, fill_color="#3B82F6", fill_opacity=0.15, popup=folium.Popup(p_html3, max_width=350)).add_to(layer_visit_itinerary)

        if show_arcus and is_arcus_row(row):
            p_html4 = create_styled_popup("ARCUS Partnership Node", s_id, s_name, banner_color="#7C3AED")
            folium.Marker([lat, lon], icon=folium.Icon(color="purple", icon="star", prefix="fa"), popup=folium.Popup(p_html4, max_width=350)).add_to(layer_arcus_subset)

    if searched_station != "None":
        m_row = ug_stations[ug_stations[station_name_col] == searched_station].iloc[0]
        p_html7 = create_styled_popup("Isolated Search Node", m_row[station_id_col], m_row[station_name_col], banner_color="#EF4444")
        folium.Marker([m_row[lat_col], m_row[lon_col]], icon=folium.Icon(color="red", icon="flag", prefix="fa"), popup=folium.Popup(p_html7, max_width=350)).add_to(layer_search_highlight)

    # Bind active layers natively based on checkboxes 
    if show_all_stations: layer_all_stations.add_to(m)
    if show_all_tickets: layer_all_tickets.add_to(m)
    if show_itinerary: layer_visit_itinerary.add_to(m)
    if show_arcus: layer_arcus_subset.add_to(m)
    if show_unvisited: layer_tickets_not_visited.add_to(m)
    if searched_station != "None": layer_search_highlight.add_to(m)

    legend_html = f'''
         <div style="position: fixed; bottom: 35px; left: 35px; width: 310px; border: 1px solid #E2E8F0; background-color: rgba(255, 255, 255, 0.98); border-radius: 10px; padding: 14px; font-size: 12px; font-family: 'Inter', sans-serif; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); z-index: 9999; line-height: 1.6; color: #334155;">
         <b style="font-size: 13px; color: #0F172A; display: block; border-bottom: 1px solid #F1F5F9; padding-bottom: 5px; margin-bottom: 8px; font-weight:600;">🗺️ Operational Map Legend</b>
         <div style="display: grid; gap: 4px;">
           {"<div><i style='background:#CBD5E1;width:9px;height:9px;border-radius:50%;display:inline-block;margin-right:9px;border:1.5px solid #94A3B8;'></i> Uganda all Stations</div>" if show_all_stations else ""}
           {"<div><span style='color:#F59E0B;font-weight:bold;margin-right:7px;font-size:13px;'>🔧</span> Active Open Tickets</div>" if show_all_tickets else ""}
           {"<div><i style='border:2.5px solid #2563EB;background:rgba(59,130,246,0.15);width:11px;height:11px;border-radius:50%;display:inline-block;margin-right:7px;'></i> Sites Scheduled to be Visited</div>" if show_itinerary else ""}
           {"<div><span style='color:#7C3AED;font-weight:bold;margin-right:9px;'>★</span> ARCUS Sites</div>" if show_arcus else ""}
           {"<div><span style='color:#DC2626;font-weight:bold;margin-right:7px;'>⚠️</span> <span style='color:#DC2626;'>Open Tickets NOT on Itinerary</span></div>" if show_unvisited else ""}
         </div></div>
         '''
    m.get_root().html.add_child(folium.Element(legend_html))
    m.save("uganda_map.html")
    st_folium(m, use_container_width=True, height=650)

with route_tab:
    st.subheader("🚗 Live Road Route Network Planner")
    st.markdown("Generates real-world road path driving directions showing highway routing, mileage distances, and time estimates.")
    
    # Clean and URL-encode input strings safely for browser transportation strings
    encoded_origin = urllib.parse.quote_plus(route_origin)
    encoded_destination = urllib.parse.quote_plus(route_destination)
    
    # Open-access URL configuration layout forcing true vehicle grid road routing directions
    google_backup_url = f"https://maps.google.com/maps?q={encoded_origin}&daddr={encoded_destination}&output=embed"

    # FIXED: Modern st.iframe syntax without the invalid container width parameter
    st.iframe(src=google_backup_url, height=580)
    
    # Provide deep external mobile-ready application outlink button launcher
    st.markdown("### 📱 Native Device Navigation Launcher")
    native_app_url = f"https://maps.google.com/maps?q={encoded_origin}&destination={encoded_destination}&travelmode={travel_mode}"
    st.link_button("Launch Native Turn-by-Turn GPS Navigation ↗", native_app_url, use_container_width=True)