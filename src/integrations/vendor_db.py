import os
import json
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VENDORS_CSV = PROJECT_ROOT / "data" / "vendors.csv"
VENDOR_SUMMARY_CSV = PROJECT_ROOT / "outputs" / "vendor_summary.csv"
EVENT_HISTORY_CSV = PROJECT_ROOT / "data" / "event_history.csv"

DEFAULT_CATEGORIES = [
    "Sound", "Lighting", "Production", "LED", "Tables", "Chairs",
    "Artist", "DJ", "Band", "Food & Beverage", "Décor", "Printing",
    "Photography", "Videography", "Security", "Cleaning", "Miscellaneous"
]

def get_vendor_categories() -> List[str]:
    """
    Returns list of predefined categories, plus any custom categories defined in vendors database.
    """
    categories = list(DEFAULT_CATEGORIES)
    if VENDORS_CSV.exists():
        try:
            df = pd.read_csv(VENDORS_CSV)
            if "Vendor Category" in df.columns:
                unique_cats = df["Vendor Category"].dropna().unique().tolist()
                for cat in unique_cats:
                    if cat not in categories:
                        categories.append(cat)
        except Exception:
            pass
    return categories

def load_vendors_csv() -> pd.DataFrame:
    if VENDORS_CSV.exists():
        try:
            return pd.read_csv(VENDORS_CSV)
        except Exception:
            pass
    return pd.DataFrame()

import streamlit as st

@st.cache_data
def load_vendors() -> pd.DataFrame:
    from src.services import vendor_service
    return vendor_service.get_vendors()

def save_vendors(df: pd.DataFrame) -> None:
    # This is called during CSV fallback saving, let's keep CSV writing intact as fallback
    st.cache_data.clear()
    VENDORS_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(VENDORS_CSV, index=False)
    update_vendor_statistics()

def add_vendor(vendor_data: Dict[str, Any]) -> bool:
    from src.services import vendor_service
    st.cache_data.clear()
    return vendor_service.add_vendor(vendor_data)

def edit_vendor(vendor_id: str, updated_fields: Dict[str, Any]) -> bool:
    from src.services import vendor_service
    st.cache_data.clear()
    return vendor_service.edit_vendor(vendor_id, updated_fields)

def delete_or_deactivate_vendor(vendor_id: str) -> str:
    from src.services import vendor_service
    st.cache_data.clear()
    # Check if linked to history
    is_linked = False
    if EVENT_HISTORY_CSV.exists():
        try:
            history_df = pd.read_csv(EVENT_HISTORY_CSV)
            if "Vendors Used" in history_df.columns:
                for _, row in history_df.iterrows():
                    v_used_str = row.get("Vendors Used", "[]")
                    try:
                        v_used = json.loads(v_used_str)
                        if any(str(v.get("vendor_id")) == str(vendor_id) for v in v_used):
                            is_linked = True
                            break
                    except Exception:
                        pass
        except Exception:
            pass

    action = "deactivate" if is_linked else "delete"
    success = vendor_service.delete_or_deactivate_vendor(vendor_id, action)
    update_vendor_statistics()
    if success:
        return "Vendor is linked to historical events. Marked as Inactive instead of deleting." if is_linked else "Vendor successfully deleted."
    return "Failed to perform operation."

def update_vendor_statistics() -> None:
    """
    Calculates number of events, last event date, average rating, average cost,
    total amount paid, and total revenue generated for each vendor.
    Generates outputs/vendor_summary.csv.
    """
    if not VENDORS_CSV.exists():
        return
        
    try:
        vendors_df = pd.read_csv(VENDORS_CSV)
        summary_rows = []
        
        # Parse history data
        history_df = pd.DataFrame()
        if EVENT_HISTORY_CSV.exists():
            try:
                history_df = pd.read_csv(EVENT_HISTORY_CSV)
            except Exception:
                pass

        for _, vendor in vendors_df.iterrows():
            vendor_id = vendor["Vendor ID"]
            vendor_name = vendor["Vendor Name"]
            vendor_cat = vendor["Vendor Category"]
            
            # Defaults
            events_count = 0
            last_event_date = "N/A"
            total_cost = 0.0
            total_paid = 0.0
            total_revenue = 0.0
            ratings = []

            if not history_df.empty:
                for _, row in history_df.iterrows():
                    v_used_str = row.get("Vendors Used", "[]")
                    try:
                        v_used = json.loads(v_used_str) if pd.notna(v_used_str) and str(v_used_str).strip() else []
                    except Exception:
                        v_used = []
                        
                    # Find if this vendor was used in this event row
                    matching_vendor = next((v for v in v_used if str(v.get("vendor_id")) == str(vendor_id)), None)
                    if matching_vendor:
                        events_count += 1
                        event_date = row.get("Date", "N/A")
                        if last_event_date == "N/A" or event_date > last_event_date:
                            last_event_date = event_date
                            
                        # Extract rating
                        rating_val = row.get("Average Feedback")
                        if pd.notna(rating_val):
                            ratings.append(float(rating_val))
                            
                        # Costs
                        final_cost = float(matching_vendor.get("final_cost", 0.0))
                        total_paid += final_cost
                        
                        # Stall rental revenue generated by vendor if category matches stalls
                        # Let's say if vendor paid rent to the community, it's saved in the stall rental structure
                        revenue_val = float(matching_vendor.get("revenue_generated", 0.0))
                        total_revenue += revenue_val

            avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else 0.0
            avg_cost = round(total_paid / events_count, 2) if events_count > 0 else 0.0

            summary_rows.append({
                "Vendor ID": vendor_id,
                "Vendor Name": vendor_name,
                "Category": vendor_cat,
                "Number of Events": events_count,
                "Last Event": last_event_date,
                "Average Rating": avg_rating,
                "Average Cost": avg_cost,
                "Total Amount Paid": total_paid,
                "Total Revenue Generated": total_revenue
            })
            
        summary_df = pd.DataFrame(summary_rows)
        VENDOR_SUMMARY_CSV.parent.mkdir(parents=True, exist_ok=True)
        summary_df.to_csv(VENDOR_SUMMARY_CSV, index=False)
    except Exception:
        pass
