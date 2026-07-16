import os
import pandas as pd
import uuid
from pathlib import Path
from typing import List, Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STALLS_CSV = PROJECT_ROOT / "data" / "stalls.csv"
STALL_SUMMARY_CSV = PROJECT_ROOT / "outputs" / "stall_summary.csv"
EVENT_HISTORY_CSV = PROJECT_ROOT / "data" / "event_history.csv"

DEFAULT_STALL_CATEGORIES = [
    "Food", "Beverage", "Coffee", "Bakery", "Fashion", "Accessories",
    "Books", "Art", "Handmade", "Plants", "Retail", "Games",
    "Sponsor Booth", "Information Booth", "Miscellaneous"
]

def load_stalls() -> pd.DataFrame:
    """
    Loads stalls from data/stalls.csv. Returns empty dataframe with columns if missing.
    """
    if STALLS_CSV.exists():
        try:
            return pd.read_csv(STALLS_CSV)
        except Exception:
            pass
            
    cols = [
        "Stall ID", "Event ID", "Event Name", "Date", "Property", "Vendor ID", 
        "Stall Name", "Stall Category", "Rental Amount", "Stall Size", "Status", "Notes"
    ]
    df = pd.DataFrame(columns=cols)
    STALLS_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(STALLS_CSV, index=False)
    return df

def save_stalls(df: pd.DataFrame) -> None:
    STALLS_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(STALLS_CSV, index=False)
    update_stall_summary()

def add_stalls_for_event(
    event_id: str, 
    event_name: str, 
    event_date: str, 
    property_name: str, 
    stalls_list: List[Dict[str, Any]]
) -> None:
    """
    Removes existing stalls for the given event ID and appends the new ones to data/stalls.csv.
    """
    df = load_stalls()
    
    # Filter out existing stalls for this event
    if not df.empty:
        df = df[df["Event ID"].astype(str) != str(event_id)]
        
    new_rows = []
    for idx, stall in enumerate(stalls_list):
        stall_id = stall.get("Stall ID")
        if not stall_id:
            stall_id = f"STL-{uuid.uuid4().hex[:6]}"
            
        new_rows.append({
            "Stall ID": stall_id,
            "Event ID": event_id,
            "Event Name": event_name,
            "Date": event_date,
            "Property": property_name,
            "Vendor ID": stall.get("vendor_id"),
            "Stall Name": stall.get("stall_name"),
            "Stall Category": stall.get("stall_category"),
            "Rental Amount": float(stall.get("rental_amount", 0.0)),
            "Stall Size": stall.get("stall_size", "Medium"),
            "Status": stall.get("status", "Confirmed"),
            "Notes": stall.get("notes", "")
        })
        
    if new_rows:
        new_df = pd.DataFrame(new_rows)
        df = pd.concat([df, new_df], ignore_index=True)
        
    save_stalls(df)

def update_stall_summary() -> None:
    """
    Aggregates stall counts, occupancy rates, and revenue details, and generates outputs/stall_summary.csv.
    Also updates the Total Revenue Generated metric in Vendor summary database.
    """
    stalls_df = load_stalls()
    if stalls_df.empty:
        # Create empty summary
        cols = [
            "Total Stall Revenue", "Number of Stalls", "Occupied Stalls", 
            "Available Stalls", "Average Stall Revenue", "Highest Revenue Event"
        ]
        pd.DataFrame(columns=cols).to_csv(STALL_SUMMARY_CSV, index=False)
        return
        
    try:
        total_rev = stalls_df["Rental Amount"].sum()
        num_stalls = len(stalls_df)
        
        # Stalls are occupied if status is Reserved, Confirmed, or Completed
        occupied_mask = stalls_df["Status"].isin(["Reserved", "Confirmed", "Completed"])
        occupied_count = len(stalls_df[occupied_mask])
        available_count = num_stalls - occupied_count
        avg_rev = round(total_rev / num_stalls, 2) if num_stalls > 0 else 0.0
        
        # Highest revenue event
        event_revs = stalls_df.groupby("Event Name")["Rental Amount"].sum()
        highest_event = event_revs.idxmax() if not event_revs.empty else "N/A"
        
        summary = {
            "Total Stall Revenue": total_rev,
            "Number of Stalls": num_stalls,
            "Occupied Stalls": occupied_count,
            "Available Stalls": available_count,
            "Average Stall Revenue": avg_rev,
            "Highest Revenue Event": highest_event
        }
        pd.DataFrame([summary]).to_csv(STALL_SUMMARY_CSV, index=False)
        
        # Update vendor summaries to include stall rental payments
        # Total Revenue Generated = sum of stall rental payments for that vendor
        from integrations.vendor_db import load_vendors, save_vendors
        vendors_df = load_vendors()
        if not vendors_df.empty:
            for idx, vendor in vendors_df.iterrows():
                v_id = vendor["Vendor ID"]
                v_stalls = stalls_df[(stalls_df["Vendor ID"] == v_id) & occupied_mask]
                v_revenue = v_stalls["Rental Amount"].sum()
                vendors_df.at[idx, "Total Revenue Generated"] = float(v_revenue)
            save_vendors(vendors_df)
            
    except Exception:
        pass
