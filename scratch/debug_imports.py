print("1. Importing sys and time...")
import sys
import time

print("2. Importing pandas...")
import pandas as pd

print("3. Importing streamlit...")
import streamlit as st

print("4. Importing path...")
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

print("5. Importing db_manager...")
from src.database import db_manager

print("6. Importing child services...")
from src.services import property_service, resident_service, calendar_service, vendor_service

print("7. Importing integrations calendar_db...")
from src.integrations.calendar_db import load_calendar_events

print("8. Importing integrations vendor_db...")
from src.integrations.vendor_db import load_vendors

print("9. Importing integrations master_data_db...")
from src.integrations.master_data_db import get_properties_df

print("10. Importing ui_data_bridge...")
from src.ui_data_bridge import load_application_data

print("11. Calling load_application_data()...")
start = time.time()
data = load_application_data()
print(f"12. Call complete in {time.time() - start:.2f} seconds.")
print("Keys loaded:", list(data.keys()))
