import sys
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from src.database import db_manager

def reset_events_and_recommendations():
    print("=========================================================")
    print("Clearing Planned Calendar & Recommendation History")
    print("=========================================================")

    # 1. Reset CSV files
    planned_cal_path = PROJECT_ROOT / "data" / "planned_calendar.csv"
    rec_hist_path = PROJECT_ROOT / "data" / "recommendation_history.csv"

    cal_cols = [
        "Event ID", "Event Name", "Property", "Category", "Date", "Time",
        "Status", "Event Type", "Budget Estimate", "Ticket Recommendation",
        "Assigned Vendors", "Assigned Materials", "Notes",
        "Predicted Attendance", "Expected Occupancy", "Recommendation Score",
        "Recommended Date", "Approved Date"
    ]
    pd.DataFrame(columns=cal_cols).to_csv(planned_cal_path, index=False)
    print(f" - Reset '{planned_cal_path.name}' to empty headers.")

    rec_cols = [
        "Recommendation ID", "Generated Time", "Approved Time", "Approver",
        "Property", "Event Name", "Category", "Event Type",
        "AI Suggested Date", "Approved Date", "Recommendation Score", "Status"
    ]
    pd.DataFrame(columns=rec_cols).to_csv(rec_hist_path, index=False)
    print(f" - Reset '{rec_hist_path.name}' to empty headers.")

    # 2. Reset MongoDB collections
    if db_manager.ping_check():
        try:
            cal_coll = db_manager.get_collection("calendar_events")
            r1 = cal_coll.delete_many({})
            print(f" - Cleared MongoDB collection 'calendar_events' ({r1.deleted_count} documents removed).")
        except Exception as e:
            print(f" - Error clearing MongoDB 'calendar_events': {e}")

        try:
            rec_coll = db_manager.get_collection("recommendations")
            r2 = rec_coll.delete_many({})
            print(f" - Cleared MongoDB collection 'recommendations' ({r2.deleted_count} documents removed).")
        except Exception as e:
            print(f" - Error clearing MongoDB 'recommendations': {e}")

        try:
            evt_coll = db_manager.get_collection("events")
            r3 = evt_coll.delete_many({"Event ID": {"$regex": "EVT_TEST|TEST_|EVT-"}})
            print(f" - Cleared test entries from MongoDB collection 'events' ({r3.deleted_count} documents removed).")
        except Exception as e:
            print(f" - Error clearing MongoDB 'events': {e}")
    else:
        print(" - MongoDB is offline. CSV files were reset successfully.")

    print("=========================================================")
    print("Reset Complete! You can now start fresh.")
    print("=========================================================")

if __name__ == "__main__":
    reset_events_and_recommendations()
