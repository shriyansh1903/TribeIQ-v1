import pandas as pd
from pathlib import Path
import os
import uuid

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CALENDAR_CSV = PROJECT_ROOT / "data" / "planned_calendar.csv"

def init_calendar_db():
    if not CALENDAR_CSV.exists():
        CALENDAR_CSV.parent.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(columns=[
            "Event ID", "Event Name", "Property", "Category", "Date", "Time",
            "Status", "Event Type", "Budget Estimate", "Ticket Recommendation",
            "Assigned Vendors", "Assigned Materials", "Notes",
            "Predicted Attendance", "Expected Occupancy", "Recommendation Score"
        ])
        df.to_csv(CALENDAR_CSV, index=False)

def load_calendar_events():
    init_calendar_db()
    try:
        df = pd.read_csv(CALENDAR_CSV)
        # Avoid NaN values
        df = df.fillna("")
        return df
    except Exception:
        return pd.DataFrame()

def save_calendar_event(event_dict):
    init_calendar_db()
    df = load_calendar_events()
    
    if "Event ID" not in event_dict or not event_dict["Event ID"]:
        event_dict["Event ID"] = f"PC{uuid.uuid4().hex[:6].upper()}"
        
    # Check if duplicate Event ID
    if not df.empty and event_dict["Event ID"] in df["Event ID"].values:
        # Update existing
        idx = df[df["Event ID"] == event_dict["Event ID"]].index[0]
        for col in df.columns:
            if col in event_dict:
                df.at[idx, col] = event_dict[col]
    else:
        # Append new
        new_row = {col: event_dict.get(col, "") for col in df.columns}
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        
    df.to_csv(CALENDAR_CSV, index=False)
    
    # Sync with event_history.csv if Approved / Completed
    if event_dict.get("Status") in ["Approved", "Completed"]:
        sync_approved_event_to_history(event_dict)
        
    return event_dict["Event ID"]

def delete_calendar_event(event_id):
    df = load_calendar_events()
    if not df.empty and event_id in df["Event ID"].values:
        df = df[df["Event ID"] != event_id]
        df.to_csv(CALENDAR_CSV, index=False)
        return True
    return False

def sync_approved_event_to_history(event_dict):
    history_csv = PROJECT_ROOT / "data" / "event_history.csv"
    if not history_csv.exists():
        return
        
    try:
        h_df = pd.read_csv(history_csv)
    except Exception:
        return
        
    event_id = event_dict.get("Event ID", "")
    
    # Find matching row in history or append
    # Wait, history has "Event ID" column. If matched, update it.
    row_data = {
        "Date": event_dict.get("Date", ""),
        "Property": event_dict.get("Property", ""),
        "Event ID": event_id,
        "Event Name": event_dict.get("Event Name", ""),
        "Category": event_dict.get("Category", ""),
        "Attendance %": 0.0,
        "Actual Attendance": 0,
        "Average Feedback": 0.0,
        "Success Score": 0.0,
        "Budget Planned": event_dict.get("Budget Estimate", 0.0),
        "Budget Spent": 0.0,
        "Recommendation Type": event_dict.get("Event Type", "Minor"),
        "Recommendation Score": event_dict.get("Recommendation Score", 0.0),
        "Predicted Event Date": event_dict.get("Date", ""),
        "Predicted Weekday": pd.to_datetime(event_dict.get("Date")).strftime("%A") if event_dict.get("Date") else "",
        "Total Capacity": 100,
        "Predicted Active Residents": 100,
        "Predicted Occupancy %": event_dict.get("Expected Occupancy", 0.0),
        "Predicted Turnout Rate": 0.0,
        "Predicted Attendance": event_dict.get("Predicted Attendance", 0.0),
        "Attendance Confidence Score": 0.0,
        "Attendance Confidence": "High",
        "Attendance Prediction Error": 0.0,
        "Absolute Attendance Error": 0.0,
        "Attendance Error %": 0.0,
        "Notes": event_dict.get("Notes", ""),
        "Image Data": ""
    }
    
    if not h_df.empty and event_id in h_df["Event ID"].values:
        idx = h_df[h_df["Event ID"] == event_id].index[0]
        for col in h_df.columns:
            if col in row_data:
                h_df.at[idx, col] = row_data[col]
    else:
        new_row_df = pd.DataFrame([row_data])
        h_df = pd.concat([h_df, new_row_df], ignore_index=True)
        
    h_df.to_csv(history_csv, index=False)
