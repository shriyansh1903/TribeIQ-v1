import sys
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
    
from src.integrations.external_events_db import (
    init_external_events_db, load_external_events,
    save_external_event, delete_external_event,
    get_nearby_external_events, haversine_distance
)

print("Initializing External Events Database...")
init_external_events_db()

print("Loading events...")
df = load_external_events()
print(f"Total events found: {len(df)}")
assert not df.empty, "Seeding failed! Database is empty."

print("Testing Haversine distance...")
dist = haversine_distance(12.9716, 77.5946, 13.0035, 77.5891)
print(f"Distance between Bengaluru Centre and Palace Grounds: {dist:.2f} km")
assert dist > 0 and dist < 10, "Distance calculation is incorrect."

print("Testing Proximity Filter...")
nearby = get_nearby_external_events("Tribe Vara")
print(f"Events near Tribe Vara: {len(nearby)}")
assert not nearby.empty, "Tribe Vara is in Bengaluru and should have nearby events."

print("Testing CRUD: Save new event...")
test_id = save_external_event({
    "Event Name": "Test Concert",
    "Category": "Music Festivals",
    "City": "Bengaluru",
    "Start Date": "2027-09-01",
    "End Date": "2027-09-01",
    "Expected Footfall": 100,
    "Status": "Active"
})
print(f"New event saved with ID: {test_id}")
df_after = load_external_events()
assert test_id in df_after["Event ID"].values, "Save event failed."

print("Testing CRUD: Delete event...")
success = delete_external_event(test_id)
assert success, "Deletion report returned failure."
df_final = load_external_events()
assert test_id not in df_final["Event ID"].values, "Delete event failed."

print("All External Events integration tests passed successfully!")
