import pandas as pd
from pathlib import Path
import os
import uuid
import math
import datetime
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXTERNAL_EVENTS_CSV = PROJECT_ROOT / "data" / "external_events.csv"

# Coordinates mapping for properties
PROPERTY_COORDS = {
    "Tribe Moro": {"lat": 28.6139, "lon": 77.2090, "city": "Delhi"},
    "Tribe Vara": {"lat": 12.9716, "lon": 77.5946, "city": "Bengaluru"},
    "Tribe Student Housing": {"lat": 18.5204, "lon": 73.8567, "city": "Pune"},
    "Tribe Luxury Co-Living": {"lat": 12.9716, "lon": 77.5946, "city": "Bengaluru"},
}

DEFAULT_COORDS = {"lat": 12.9716, "lon": 77.5946, "city": "Bengaluru"}

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance in kilometers between two lat/lon coordinates."""
    try:
        lat1, lon1, lat2, lon2 = map(float, [lat1, lon1, lat2, lon2])
        R = 6371.0  # Earth radius in km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
        c = 2 * math.asin(math.sqrt(a))
        return R * c
    except Exception:
        return 999.0

def get_property_info(property_name):
    """Retrieve coordinates and city for a given property name."""
    return PROPERTY_COORDS.get(property_name, DEFAULT_COORDS)

def init_external_events_db():
    if not EXTERNAL_EVENTS_CSV.exists():
        EXTERNAL_EVENTS_CSV.parent.mkdir(parents=True, exist_ok=True)
        
        # Schema definition
        columns = [
            "Event ID", "Event Name", "Category", "Description", "City", "Area",
            "Latitude", "Longitude", "Property Radius (km)", "Start Date", "End Date",
            "Expected Footfall", "Target Audience", "Organizer", "Venue", "Website",
            "Registration Link", "Free/Paid", "Estimated Popularity", "Expected Occupancy Impact",
            "Expected Community Impact", "Tags", "Status", "Created By", "Last Updated"
        ]
        
        # Seed Data (Realistic local events)
        seed_data = [
            {
                "Event ID": "EXT-001",
                "Event Name": "Bengaluru Tech Summit 2027",
                "Category": "Tech Conferences",
                "Description": "Largest tech and startup summit in South Asia.",
                "City": "Bengaluru",
                "Area": "Palace Grounds",
                "Latitude": 13.0035,
                "Longitude": 77.5891,
                "Property Radius (km)": 10.0,
                "Start Date": "2027-08-18",
                "End Date": "2027-08-20",
                "Expected Footfall": 15000,
                "Target Audience": "Tech Professionals, Founders, Students",
                "Organizer": "Karnataka Biotech & IT Society",
                "Venue": "Bengaluru Palace Grounds",
                "Website": "https://www.bengalurutechsummit.com",
                "Registration Link": "https://www.bengalurutechsummit.com/register",
                "Free/Paid": "Paid",
                "Estimated Popularity": "High",
                "Expected Occupancy Impact": 15.0,
                "Expected Community Impact": "High",
                "Tags": "technology, startup, networking",
                "Status": "Active",
                "Created By": "System Seed",
                "Last Updated": datetime.datetime.now().isoformat()
            },
            {
                "Event ID": "EXT-002",
                "Event Name": "Bengaluru Music & Food Carnival",
                "Category": "Music Festivals",
                "Description": "Weekend concert and food festival showcasing local artists and international cuisines.",
                "City": "Bengaluru",
                "Area": "Indiranagar",
                "Latitude": 12.9719,
                "Longitude": 77.6412,
                "Property Radius (km)": 5.0,
                "Start Date": "2027-08-19",
                "End Date": "2027-08-19",
                "Expected Footfall": 8000,
                "Target Audience": "Youth, Working Professionals",
                "Organizer": "Vibe Events",
                "Venue": "Ezone Club Ground",
                "Website": "https://www.carnivalbengaluru.com",
                "Registration Link": "https://www.carnivalbengaluru.com/tickets",
                "Free/Paid": "Paid",
                "Estimated Popularity": "High",
                "Expected Occupancy Impact": 5.0,
                "Expected Community Impact": "High",
                "Tags": "music, food, concert",
                "Status": "Active",
                "Created By": "System Seed",
                "Last Updated": datetime.datetime.now().isoformat()
            },
            {
                "Event ID": "EXT-003",
                "Event Name": "Delhi University Fest (DuFest)",
                "Category": "College Festivals",
                "Description": "Annual cultural fest bringing together college students across North Delhi.",
                "City": "Delhi",
                "Area": "North Campus",
                "Latitude": 28.6892,
                "Longitude": 77.2106,
                "Property Radius (km)": 8.0,
                "Start Date": "2027-08-20",
                "End Date": "2027-08-22",
                "Expected Footfall": 12000,
                "Target Audience": "Students, Youth",
                "Organizer": "Delhi University Cultural Committee",
                "Venue": "DU North Campus Grounds",
                "Website": "https://www.du.ac.in",
                "Registration Link": "https://www.du.ac.in/fest",
                "Free/Paid": "Free",
                "Estimated Popularity": "High",
                "Expected Occupancy Impact": 8.0,
                "Expected Community Impact": "High",
                "Tags": "students, music, dance, competition",
                "Status": "Active",
                "Created By": "System Seed",
                "Last Updated": datetime.datetime.now().isoformat()
            },
            {
                "Event ID": "EXT-004",
                "Event Name": "Pune Half Marathon 2027",
                "Category": "Sports Events",
                "Description": "Annual marathon drawing fitness enthusiasts and professional runners from across Maharashtra.",
                "City": "Pune",
                "Area": "Balewadi",
                "Latitude": 18.5752,
                "Longitude": 73.7801,
                "Property Radius (km)": 6.0,
                "Start Date": "2027-08-22",
                "End Date": "2027-08-22",
                "Expected Footfall": 5000,
                "Target Audience": "Fitness Enthusiasts, Runners",
                "Organizer": "Pune Runners Club",
                "Venue": "Balewadi Sports Complex",
                "Website": "https://www.punehalfmarathon.com",
                "Registration Link": "https://www.punehalfmarathon.com/run",
                "Free/Paid": "Paid",
                "Estimated Popularity": "Medium",
                "Expected Occupancy Impact": -5.0,  # Road blocks might prevent some check-ins/visitors
                "Expected Community Impact": "Medium",
                "Tags": "fitness, marathon, community",
                "Status": "Active",
                "Created By": "System Seed",
                "Last Updated": datetime.datetime.now().isoformat()
            }
        ]
        df = pd.DataFrame(seed_data, columns=columns)
        df.to_csv(EXTERNAL_EVENTS_CSV, index=False)
    else:
        # Verify columns exist, add if missing
        try:
            df = pd.read_csv(EXTERNAL_EVENTS_CSV)
            expected_cols = [
                "Event ID", "Event Name", "Category", "Description", "City", "Area",
                "Latitude", "Longitude", "Property Radius (km)", "Start Date", "End Date",
                "Expected Footfall", "Target Audience", "Organizer", "Venue", "Website",
                "Registration Link", "Free/Paid", "Estimated Popularity", "Expected Occupancy Impact",
                "Expected Community Impact", "Tags", "Status", "Created By", "Last Updated"
            ]
            updated = False
            for col in expected_cols:
                if col not in df.columns:
                    df[col] = ""
                    updated = True
            if updated:
                df.to_csv(EXTERNAL_EVENTS_CSV, index=False)
        except Exception:
            pass

@st.cache_data
def load_external_events():
    init_external_events_db()
    try:
        df = pd.read_csv(EXTERNAL_EVENTS_CSV)
        df = df.fillna("")
        return df
    except Exception:
        return pd.DataFrame()

def save_external_event(event_dict):
    init_external_events_db()
    st.cache_data.clear()
    
    try:
        df = pd.read_csv(EXTERNAL_EVENTS_CSV)
    except Exception:
        df = pd.DataFrame()
        
    event_id = event_dict.get("Event ID")
    if not event_id:
        event_id = f"EXT-{uuid.uuid4().hex[:6].upper()}"
        event_dict["Event ID"] = event_id
        
    event_dict["Last Updated"] = datetime.datetime.now().isoformat()
    
    if df.empty:
        new_df = pd.DataFrame([event_dict])
        new_df.to_csv(EXTERNAL_EVENTS_CSV, index=False)
        return event_id
        
    match_mask = df["Event ID"] == event_id
    if match_mask.any():
        idx = df[match_mask].index[0]
        for col in df.columns:
            if col in event_dict:
                df.at[idx, col] = event_dict[col]
    else:
        new_row_df = pd.DataFrame([event_dict])
        df = pd.concat([df, new_row_df], ignore_index=True)
        
    df.to_csv(EXTERNAL_EVENTS_CSV, index=False)
    return event_id

def delete_external_event(event_id):
    init_external_events_db()
    st.cache_data.clear()
    
    try:
        df = pd.read_csv(EXTERNAL_EVENTS_CSV)
        if not df.empty:
            df = df[df["Event ID"] != event_id]
            df.to_csv(EXTERNAL_EVENTS_CSV, index=False)
            return True
    except Exception:
        pass
    return False

def get_nearby_external_events(property_name, start_date=None, end_date=None, radius_km=None):
    """Retrieve external events that affect a property based on city and Haversine distance."""
    events_df = load_external_events()
    if events_df.empty:
        return pd.DataFrame()
        
    prop_info = get_property_info(property_name)
    prop_lat = prop_info["lat"]
    prop_lon = prop_info["lon"]
    prop_city = prop_info["city"]
    
    # Filter by city or city match first
    city_mask = events_df["City"].astype(str).str.lower() == prop_city.lower()
    filtered_df = events_df[city_mask].copy()
    
    # Calculate proximity distance
    distances = []
    for idx, row in filtered_df.iterrows():
        e_lat = row.get("Latitude")
        e_lon = row.get("Longitude")
        if e_lat != "" and e_lon != "":
            dist = haversine_distance(prop_lat, prop_lon, e_lat, e_lon)
        else:
            dist = 999.0
        distances.append(dist)
    filtered_df["Distance (km)"] = distances
    
    # Filter by proximity / radius
    if radius_km is not None:
        filtered_df = filtered_df[filtered_df["Distance (km)"] <= float(radius_km)]
    else:
        # Otherwise filter by individual event property radius
        radius_mask = []
        for idx, row in filtered_df.iterrows():
            limit = float(row.get("Property Radius (km)") or 5.0)
            dist = row.get("Distance (km)")
            radius_mask.append(dist <= limit)
        filtered_df = filtered_df[radius_mask]
        
    # Date range filters (YYYY-MM-DD string comparisons)
    if start_date:
        start_str = start_date.isoformat() if isinstance(start_date, (datetime.date, datetime.datetime)) else str(start_date)
        filtered_df = filtered_df[filtered_df["End Date"] >= start_str]
    if end_date:
        end_str = end_date.isoformat() if isinstance(end_date, (datetime.date, datetime.datetime)) else str(end_date)
        filtered_df = filtered_df[filtered_df["Start Date"] <= end_str]
        
    # Exclude archived status
    if "Status" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["Status"].astype(str).str.lower() != "archived"]
        
    return filtered_df
