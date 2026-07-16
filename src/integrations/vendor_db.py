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

def load_vendors() -> pd.DataFrame:
    """
    Loads vendors from data/vendors.csv. Creates default sample vendors if missing.
    """
    if VENDORS_CSV.exists():
        try:
            return pd.read_csv(VENDORS_CSV)
        except Exception:
            pass

    # Create default sample vendors
    VENDORS_CSV.parent.mkdir(parents=True, exist_ok=True)
    sample_vendors = [
        {
            "Vendor ID": "VND001",
            "Vendor Name": "Pune Sound Systems",
            "Vendor Category": "Sound",
            "Contact Person": "Rajesh Kumar",
            "Phone Number": "+919876543210",
            "Email Address": "rajesh@punesound.in",
            "GST Number": "27AAAAA1111A1Z1",
            "Address": "Kothrud, Pune",
            "Description": "Professional audio equipment and speakers.",
            "Active / Inactive Status": "Active",
            "Base Amount": 10000.0,
            "GST Percentage": 18,
            "GST Amount": 1800.0,
            "Final Cost": 11800.0
        },
        {
            "Vendor ID": "VND002",
            "Vendor Name": "Deccan Lights & LED",
            "Vendor Category": "Lighting",
            "Contact Person": "Amit Joshi",
            "Phone Number": "+919922881100",
            "Email Address": "amit@deccanlights.com",
            "GST Number": "27BBBBB2222B2Z2",
            "Address": "Shivajinagar, Pune",
            "Description": "Ambient lighting and outdoor LEDs.",
            "Active / Inactive Status": "Active",
            "Base Amount": 8000.0,
            "GST Percentage": 18,
            "GST Amount": 1440.0,
            "Final Cost": 9440.0
        },
        {
            "Vendor ID": "VND003",
            "Vendor Name": "Good Food Catering",
            "Vendor Category": "Food & Beverage",
            "Contact Person": "Sneha Patil",
            "Phone Number": "+919555112233",
            "Email Address": "contact@goodfoodpune.com",
            "GST Number": "27CCCCC3333C3Z3",
            "Address": "Viman Nagar, Pune",
            "Description": "High-quality catering, snacks and meals.",
            "Active / Inactive Status": "Active",
            "Base Amount": 15000.0,
            "GST Percentage": 12,
            "GST Amount": 1800.0,
            "Final Cost": 16800.0
        }
    ]
    df = pd.DataFrame(sample_vendors)
    df.to_csv(VENDORS_CSV, index=False)
    update_vendor_statistics()
    return df

def save_vendors(df: pd.DataFrame) -> None:
    VENDORS_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(VENDORS_CSV, index=False)
    update_vendor_statistics()

def add_vendor(vendor_data: Dict[str, Any]) -> bool:
    try:
        df = load_vendors()
        # Generate new unique ID
        if df.empty:
            next_id = "VND001"
        else:
            ids = df["Vendor ID"].str.replace("VND", "").astype(int).tolist()
            next_id = f"VND{max(ids) + 1:03d}"
            
        vendor_data["Vendor ID"] = next_id
        new_row = pd.DataFrame([vendor_data])
        df = pd.concat([df, new_row], ignore_index=True)
        save_vendors(df)
        return True
    except Exception:
        return False

def edit_vendor(vendor_id: str, updated_fields: Dict[str, Any]) -> bool:
    try:
        df = load_vendors()
        mask = df["Vendor ID"] == vendor_id
        if not mask.any():
            return False
            
        for col, val in updated_fields.items():
            df.loc[mask, col] = val
            
        save_vendors(df)
        return True
    except Exception:
        return False

def delete_or_deactivate_vendor(vendor_id: str) -> str:
    """
    Deletes the vendor from data/vendors.csv.
    If the vendor is linked to any historical events in event_history.csv,
    it marks the status as 'Inactive' instead of deleting it to preserve integrity.
    """
    try:
        df = load_vendors()
        mask = df["Vendor ID"] == vendor_id
        if not mask.any():
            return "Vendor not found."

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

        if is_linked:
            df.loc[mask, "Active / Inactive Status"] = "Inactive"
            save_vendors(df)
            return "Vendor is linked to historical events. Marked as Inactive instead of deleting."
        else:
            df = df[~mask]
            save_vendors(df)
            return "Vendor successfully deleted."
    except Exception as e:
        return f"Error: {str(e)}"

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
