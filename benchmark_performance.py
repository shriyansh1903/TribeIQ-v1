import sys
import time
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

print("=" * 60)
print(" TribeIQ Performance Benchmarking Suite")
print("=" * 60)

# Import key data routines
start_import = time.perf_counter()
from ui_data_bridge import load_application_data, generate_property_recommendations
from integrations.calendar_db import load_calendar_events
from integrations.vendor_db import load_vendors, update_vendor_statistics
from integrations.material_db import load_materials
from integrations.stall_db import load_stalls
import streamlit as st
import datetime
import cleaner
import feature_engineering
import profile_generator
import intelligence.copilot_orchestrator as copilot
end_import = time.perf_counter()
print(f"Imports completed in {(end_import - start_import)*1000:.2f} ms")

# Benchmark Startup (Data Loading Layer)
print("\n[1] Central Data Loader (Startup)")
t1 = time.perf_counter()
data = load_application_data()
t2 = time.perf_counter()
print(f"  First Load: {(t2 - t1)*1000:.2f} ms")

t1 = time.perf_counter()
data = load_application_data()
t2 = time.perf_counter()
print(f"  Second Load (Cached): {(t2 - t1)*1000:.2f} ms")

# Benchmark Dashboard / Calendar Databases
print("\n[2] Databases & Calendars")
t1 = time.perf_counter()
df_cal = load_calendar_events()
t2 = time.perf_counter()
print(f"  Calendar Load: {(t2 - t1)*1000:.2f} ms")

t1 = time.perf_counter()
df_cal = load_calendar_events()
t2 = time.perf_counter()
print(f"  Calendar Load (Cached): {(t2 - t1)*1000:.2f} ms")

# Benchmark Vendor & Material Summaries
print("\n[3] Vendors & Materials")
t1 = time.perf_counter()
vendors = load_vendors()
t2 = time.perf_counter()
print(f"  Vendors Load: {(t2 - t1)*1000:.2f} ms")

t1 = time.perf_counter()
vendors = load_vendors()
t2 = time.perf_counter()
print(f"  Vendors Load (Cached): {(t2 - t1)*1000:.2f} ms")

# Benchmark Recommendations Generation
print("\n[4] Recommendations Engine")
t1 = time.perf_counter()
try:
    res = generate_property_recommendations("Tribe Moro", data)
    t2 = time.perf_counter()
    print(f"  Recommendations generation: {(t2 - t1)*1000:.2f} ms")
except Exception as e:
    print(f"  Failed: {e}")

# Benchmark Copilot Context Building
print("\n[5] AI Copilot Context Assembly")
t1 = time.perf_counter()
try:
    context = copilot.build_system_state_context()
    t2 = time.perf_counter()
    print(f"  Context Assembly: {(t2 - t1)*1000:.2f} ms")
except Exception as e:
    print(f"  Failed: {e}")

print("\n" + "=" * 60)
print(" Benchmark execution completed successfully.")
print("=" * 60)
