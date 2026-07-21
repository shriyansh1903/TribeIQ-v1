import pandas as pd
from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"

# File Paths
PROPERTIES_CSV = DATA_DIR / "properties.csv"
EVENTS_CSV = DATA_DIR / "events.csv"
EVENT_CATEGORIES_CSV = DATA_DIR / "event_categories.csv"
PROPERTY_TYPES_CSV = DATA_DIR / "property_types.csv"
VENDOR_CATEGORIES_CSV = DATA_DIR / "vendor_categories.csv"
MATERIAL_CATEGORIES_CSV = DATA_DIR / "material_categories.csv"

def init_master_data_files():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Properties
    if not PROPERTIES_CSV.exists():
        pd.DataFrame([
            {"Property ID": "P001", "Property Name": "Tribe Moro", "Property Type": "Commune", "City": "Pune", "State": "Maharashtra", "Capacity": 296, "Status": "Active"},
            {"Property ID": "P002", "Property Name": "Tribe Vara", "Property Type": "Student Accommodation", "City": "Pune", "State": "Maharashtra", "Capacity": 192, "Status": "Active"},
            {"Property ID": "P003", "Property Name": "Tribe Wamba", "Property Type": "Suite", "City": "Pune", "State": "Maharashtra", "Capacity": 210, "Status": "Active"}
        ]).to_csv(PROPERTIES_CSV, index=False)
        
    # 2. Event Categories
    if not EVENT_CATEGORIES_CSV.exists():
        pd.DataFrame([
            {"Category": "Flea Market", "Description": "Local business and retail markets"},
            {"Category": "Food & Beverage", "Description": "Dining, festivals and culinary pop-ups"},
            {"Category": "Retail", "Description": "Fashion, sneakers and lifestyle shopping"},
            {"Category": "Entertainment", "Description": "Music, comedy, open mic and movie screening"},
            {"Category": "Community", "Description": "Quiz leagues, meetups and networking"},
            {"Category": "Sports", "Description": "Active leagues and screening events"},
            {"Category": "Workshops", "Description": "Skill bootcamps and wellness seminars"},
            {"Category": "Wellness", "Description": "Yoga and mental health retreats"}
        ]).to_csv(EVENT_CATEGORIES_CSV, index=False)
        
    # 3. Property Types
    if not PROPERTY_TYPES_CSV.exists():
        pd.DataFrame([
            {"Property Type": "Student Accommodation", "Preferred Categories": "Sports, Games, Movie Night, Career Events, Food Festivals", "Restricted Categories": "Premium Dining, Wine & Cheese"},
            {"Property Type": "Commune", "Preferred Categories": "Networking, Comedy, Live Music, Wellness", "Restricted Categories": ""},
            {"Property Type": "Suite", "Preferred Categories": "Premium Dining, Brunch, Wine & Cheese, Yoga, Wellness", "Restricted Categories": ""}
        ]).to_csv(PROPERTY_TYPES_CSV, index=False)
        
    # 4. Vendor Categories
    if not VENDOR_CATEGORIES_CSV.exists():
        pd.DataFrame([
            {"Category": "Lighting", "Status": "Active"},
            {"Category": "Sound", "Status": "Active"},
            {"Category": "DJ", "Status": "Active"},
            {"Category": "Band", "Status": "Active"},
            {"Category": "Décor", "Status": "Active"},
            {"Category": "Printing", "Status": "Active"},
            {"Category": "Food", "Status": "Active"},
            {"Category": "Security", "Status": "Active"},
            {"Category": "Photography", "Status": "Active"}
        ]).to_csv(VENDOR_CATEGORIES_CSV, index=False)
        
    # 5. Material Categories
    if not MATERIAL_CATEGORIES_CSV.exists():
        pd.DataFrame([
            {"Category": "Furniture", "Status": "Active"},
            {"Category": "Lighting", "Status": "Active"},
            {"Category": "Audio", "Status": "Active"},
            {"Category": "Branding", "Status": "Active"},
            {"Category": "Cleaning", "Status": "Active"},
            {"Category": "Games", "Status": "Active"},
            {"Category": "Sports", "Status": "Active"},
            {"Category": "Electrical", "Status": "Active"}
        ]).to_csv(MATERIAL_CATEGORIES_CSV, index=False)

import streamlit as st

@st.cache_data
def get_properties_df():
    from src.services import property_service
    return property_service.get_properties()

def save_properties_df(df):
    from src.services import property_service
    st.cache_data.clear()
    property_service.save_properties(df)
    # Dynamically update the in-memory capacities of other engines
    update_capacities_config()

@st.cache_data
def get_event_categories_df():
    init_master_data_files()
    return pd.read_csv(EVENT_CATEGORIES_CSV).fillna("")

def save_event_categories_df(df):
    df.to_csv(EVENT_CATEGORIES_CSV, index=False)
    st.cache_data.clear()

@st.cache_data
def get_property_types_df():
    init_master_data_files()
    return pd.read_csv(PROPERTY_TYPES_CSV).fillna("")

def save_property_types_df(df):
    df.to_csv(PROPERTY_TYPES_CSV, index=False)
    st.cache_data.clear()

@st.cache_data
def get_vendor_categories_df():
    init_master_data_files()
    return pd.read_csv(VENDOR_CATEGORIES_CSV).fillna("")

def save_vendor_categories_df(df):
    df.to_csv(VENDOR_CATEGORIES_CSV, index=False)
    st.cache_data.clear()

@st.cache_data
def get_material_categories_df():
    init_master_data_files()
    return pd.read_csv(MATERIAL_CATEGORIES_CSV).fillna("")

def save_material_categories_df(df):
    df.to_csv(MATERIAL_CATEGORIES_CSV, index=False)
    st.cache_data.clear()

def update_capacities_config():
    # Update PROPERTY_CAPACITY dynamically in forecasters
    try:
        df = pd.read_csv(PROPERTIES_CSV)
        active_props = df[df["Status"] == "Active"]
        caps = {row["Property Name"]: int(row["Capacity"]) for idx, row in active_props.iterrows()}
        
        # Inject into occupancy forecaster
        import intelligence.occupancy_forecaster as of
        of.PROPERTY_CAPACITY.update(caps)
        
        # Inject into occupancy_attendance_bridge
        import occupancy_attendance_bridge as oab
        oab.PROPERTY_CAPACITY.update(caps)
    except Exception:
        pass
