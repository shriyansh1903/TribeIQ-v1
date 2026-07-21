import pandas as pd
from pathlib import Path
import os
import uuid
import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CALENDAR_CSV = PROJECT_ROOT / "data" / "planned_calendar.csv"
REC_HISTORY_CSV = PROJECT_ROOT / "data" / "recommendation_history.csv"

def init_calendar_db():
    if not CALENDAR_CSV.exists():
        CALENDAR_CSV.parent.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(columns=[
            "Event ID", "Event Name", "Property", "Category", "Date", "Time",
            "Status", "Event Type", "Budget Estimate", "Ticket Recommendation",
            "Assigned Vendors", "Assigned Materials", "Notes",
            "Predicted Attendance", "Expected Occupancy", "Recommendation Score",
            "Recommended Date", "Approved Date"
        ])
        df.to_csv(CALENDAR_CSV, index=False)
    else:
        # Verify columns exist, add if missing
        try:
            df = pd.read_csv(CALENDAR_CSV)
            updated = False
            for col in ["Recommended Date", "Approved Date"]:
                if col not in df.columns:
                    df[col] = ""
                    updated = True
            if updated:
                df.to_csv(CALENDAR_CSV, index=False)
        except Exception:
            pass

import streamlit as st

def init_rec_history_db():
    if not REC_HISTORY_CSV.exists():
        REC_HISTORY_CSV.parent.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(columns=[
            "Recommendation ID", "Generated Time", "Approved Time", "Approver",
            "Property", "Event Name", "Category", "Event Type",
            "AI Suggested Date", "Approved Date", "Recommendation Score", "Status"
        ])
        df.to_csv(REC_HISTORY_CSV, index=False)

def load_calendar_events_csv() -> pd.DataFrame:
    init_calendar_db()
    if CALENDAR_CSV.exists():
        try:
            return pd.read_csv(CALENDAR_CSV)
        except Exception:
            pass
    return pd.DataFrame()

@st.cache_data
def load_calendar_events():
    from src.services import calendar_service
    return calendar_service.get_calendar_events()

def save_calendar_event_csv(event_dict):
    init_calendar_db()
    try:
        df = pd.read_csv(CALENDAR_CSV)
    except Exception:
        df = pd.DataFrame()

    event_id = event_dict.get("Event ID")
    if not event_id:
        event_id = f"EVT-{uuid.uuid4().hex[:6].upper()}"
        event_dict["Event ID"] = event_id

    if not df.empty and "Event ID" in df.columns and event_id in df["Event ID"].values:
        idx = df[df["Event ID"] == event_id].index[0]
        for col in df.columns:
            if col in event_dict:
                df.at[idx, col] = event_dict[col]
    else:
        new_row = {col: event_dict.get(col, "") for col in df.columns}
        for k, v in event_dict.items():
            new_row[k] = v
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    df.to_csv(CALENDAR_CSV, index=False)
    return event_id

def delete_calendar_event_csv(event_id):
    if CALENDAR_CSV.exists():
        try:
            df = pd.read_csv(CALENDAR_CSV)
            if "Event ID" in df.columns:
                df = df[df["Event ID"] != event_id]
                df.to_csv(CALENDAR_CSV, index=False)
                return True
        except Exception:
            pass
    return False

def save_calendar_event(event_dict):
    from src.services import calendar_service
    st.cache_data.clear()

    # Clean empty/invalid Event ID before validation
    if not event_dict.get("Event ID") or str(event_dict.get("Event ID")).strip().lower() in ["none", ""]:
        event_dict.pop("Event ID", None)

    # Validate event schema via Pydantic model
    try:
        from src.models.event import Event
        validated_obj = Event.model_validate(event_dict) if hasattr(Event, "model_validate") else Event(**event_dict)
        validated_dict = validated_obj.model_dump(by_alias=True) if hasattr(validated_obj, "model_dump") else validated_obj.dict(by_alias=True)
        for k, v in validated_dict.items():
            if v is not None:
                event_dict[k] = v
    except Exception as e:
        print(f"Pydantic Event validation notice: {e}")

    # Remove Event ID if None was re-introduced by model dump
    if not event_dict.get("Event ID") or str(event_dict.get("Event ID")).strip().lower() in ["none", ""]:
        event_dict.pop("Event ID", None)

    event_id = calendar_service.save_calendar_event(event_dict)
    event_dict["Event ID"] = event_id
    save_calendar_event_csv(event_dict)
    
    # Sync with event_history.csv if Approved / Completed
    if event_dict.get("Status") in ["Approved", "Completed"]:
        sync_approved_event_to_history(event_dict)
        
    return event_id

def delete_calendar_event(event_id):
    from src.services import calendar_service
    st.cache_data.clear()
    delete_calendar_event_csv(event_id)
    return calendar_service.delete_calendar_event(event_id)

def sync_approved_event_to_history(event_dict):
    history_csv = PROJECT_ROOT / "data" / "event_history.csv"
    if not history_csv.exists():
        return
        
    try:
        h_df = pd.read_csv(history_csv)
        # Cast potential empty string columns to object dtype to avoid float64 TypeError crashes
        for col in ["Image Data", "Notes", "Attendance Confidence", "Recommendation Type", "Category", "Event Name", "Property", "Event ID", "Date"]:
            if col in h_df.columns:
                h_df[col] = h_df[col].astype(object)
    except Exception:
        return
        
    event_id = event_dict.get("Event ID", "")
    
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
        "Predicted Event Date": event_dict.get("Recommended Date", event_dict.get("Date", "")),
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
        # Only overwrite fields that were explicitly modified/provided in event_dict (avoid zeroing out forecasts)
        key_mapping = {
            "Budget Planned": "Budget Estimate",
            "Recommendation Type": "Event Type",
            "Predicted Occupancy %": "Expected Occupancy",
            "Predicted Attendance": "Predicted Attendance",
            "Recommendation Score": "Recommendation Score",
            "Notes": "Notes"
        }
        for col in h_df.columns:
            if col in row_data:
                dict_key = key_mapping.get(col, col)
                if dict_key in event_dict or col in ["Date", "Predicted Weekday", "Predicted Event Date", "Property", "Event ID", "Event Name", "Category"]:
                    h_df.at[idx, col] = row_data[col]
    else:
        new_row_df = pd.DataFrame([row_data])
        h_df = pd.concat([h_df, new_row_df], ignore_index=True)
        
    h_df.to_csv(history_csv, index=False)

    # Live sync to MongoDB events collection
    try:
        from src.services.child_services import event_history_service
        event_history_service.save_event_history(row_data)
    except Exception as ex:
        print(f"MongoDB event_history sync notice: {ex}")

def save_recommendation_history(rec_dict):
    st.cache_data.clear()
    init_rec_history_db()
    try:
        df = pd.read_csv(REC_HISTORY_CSV)
    except Exception:
        df = pd.DataFrame()
        
    if "Recommendation ID" not in rec_dict or not rec_dict["Recommendation ID"]:
        rec_dict["Recommendation ID"] = f"REC{uuid.uuid4().hex[:6].upper()}"
        
    # Prevent duplicate Recommendation ID
    match_idx = None
    if not df.empty and rec_dict["Recommendation ID"] in df["Recommendation ID"].values:
        match_idx = df[df["Recommendation ID"] == rec_dict["Recommendation ID"]].index[0]
        
    if match_idx is not None:
        for col in df.columns:
            if col in rec_dict:
                df.at[match_idx, col] = rec_dict[col]
    else:
        new_row = {col: rec_dict.get(col, "") for col in df.columns}
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        
    df.to_csv(REC_HISTORY_CSV, index=False)

    # Live sync to MongoDB recommendations collection
    try:
        from src.services.child_services import recommendation_service
        recommendation_service.save_recommendation(rec_dict)
    except Exception as ex:
        print(f"MongoDB recommendation sync notice: {ex}")

