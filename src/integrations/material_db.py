import os
import pandas as pd
import uuid
from pathlib import Path
from typing import List, Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MATERIALS_CSV = PROJECT_ROOT / "data" / "materials.csv"
MATERIAL_SUMMARY_CSV = PROJECT_ROOT / "outputs" / "material_summary.csv"

DEFAULT_MATERIAL_CATEGORIES = [
    "Furniture", "Audio", "Lighting", "Stage", "Decoration", "Branding",
    "Registration", "Games", "Sports Equipment", "Food Service",
    "Electrical", "Cleaning", "Safety", "Miscellaneous"
]

PROCUREMENT_STATUS_BADGES = {
    "Not Ordered": "⚪ Not Ordered",
    "Ordered": "🟡 Ordered",
    "Procured": "🔵 Procured",
    "Delivered": "🟢 Delivered",
    "Returned": "🟣 Returned"
}

import streamlit as st

@st.cache_data
def load_materials() -> pd.DataFrame:
    """
    Loads materials from data/materials.csv. Returns empty dataframe with columns if missing.
    """
    if MATERIALS_CSV.exists():
        try:
            return pd.read_csv(MATERIALS_CSV)
        except Exception:
            pass
            
    cols = [
        "Material ID", "Event ID", "Event Name", "Date", "Property", "Material Name", 
        "Category", "Quantity Required", "Unit", "Vendor ID", "Procurement Status", 
        "Unit Cost", "Total Cost", "Notes"
    ]
    df = pd.DataFrame(columns=cols)
    MATERIALS_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(MATERIALS_CSV, index=False)
    return df

def save_materials(df: pd.DataFrame) -> None:
    st.cache_data.clear()
    MATERIALS_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(MATERIALS_CSV, index=False)
    update_material_summary()

def add_materials_for_event(
    event_id: str, 
    event_name: str, 
    event_date: str, 
    property_name: str, 
    materials_list: List[Dict[str, Any]]
) -> None:
    """
    Removes existing materials for the given event ID and appends the new ones to data/materials.csv.
    """
    df = load_materials()
    
    # Filter out existing materials for this event
    if not df.empty:
        df = df[df["Event ID"].astype(str) != str(event_id)]
        
    new_rows = []
    for idx, mat in enumerate(materials_list):
        mat_id = mat.get("Material ID")
        if not mat_id:
            mat_id = f"MAT-{uuid.uuid4().hex[:6]}"
            
        qty = float(mat.get("quantity", 1.0))
        unit_cost = float(mat.get("unit_cost", 0.0))
        total_cost = round(qty * unit_cost, 2)
            
        new_rows.append({
            "Material ID": mat_id,
            "Event ID": event_id,
            "Event Name": event_name,
            "Date": event_date,
            "Property": property_name,
            "Material Name": mat.get("name"),
            "Category": mat.get("category"),
            "Quantity Required": qty,
            "Unit": mat.get("unit", "Pcs"),
            "Vendor ID": mat.get("vendor_id", "None"),
            "Procurement Status": mat.get("status", "Not Ordered"),
            "Unit Cost": unit_cost,
            "Total Cost": total_cost,
            "Notes": mat.get("notes", "")
        })
        
    if new_rows:
        new_df = pd.DataFrame(new_rows)
        df = pd.concat([df, new_df], ignore_index=True)
        
    save_materials(df)

def update_material_summary() -> None:
    """
    Aggregates material costs, counts, and status details, and generates outputs/material_summary.csv.
    """
    mats_df = load_materials()
    if mats_df.empty:
        cols = [
            "Total Procurement Spend", "Materials Ordered", "Materials Pending", 
            "Materials Delivered"
        ]
        pd.DataFrame(columns=cols).to_csv(MATERIAL_SUMMARY_CSV, index=False)
        return
        
    try:
        total_spend = mats_df["Total Cost"].sum()
        ordered_count = len(mats_df[mats_df["Procurement Status"] == "Ordered"])
        pending_count = len(mats_df[mats_df["Procurement Status"].isin(["Not Ordered", "Ordered"])])
        delivered_count = len(mats_df[mats_df["Procurement Status"] == "Delivered"])
        
        summary = {
            "Total Procurement Spend": total_spend,
            "Materials Ordered": ordered_count,
            "Materials Pending": pending_count,
            "Materials Delivered": delivered_count
        }
        pd.DataFrame([summary]).to_csv(MATERIAL_SUMMARY_CSV, index=False)
    except Exception:
        pass
