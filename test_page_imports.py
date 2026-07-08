"""Test script to check all pages for import errors."""
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SRC_DIR))

# Test imports for each page
print("Testing Dashboard imports...")
try:
    from ui_data_bridge import get_session_property, get_session_result, load_application_data
    from ui.styles import load_css
    from ui.components import history_table, metric_row, page_header, section_header
    print("  OK")
except Exception as e:
    print(f"  FAIL: {e}")

print("\nTesting Property Profile imports...")
try:
    import ast
    import json
    from ui_data_bridge import get_session_property, load_application_data
    from ui.styles import load_css
    from ui.components import history_table, metric_row, page_header, section_header
    print("  OK")
except Exception as e:
    print(f"  FAIL: {e}")

print("\nTesting Recommendations imports...")
try:
    from ui_data_bridge import (
        SESSION_ERROR_KEY, SESSION_RUNNING_KEY,
        generate_property_recommendations, get_session_property,
        get_session_result, load_application_data,
        save_error_to_session, save_result_to_session,
        validate_application_data,
    )
    from recommendation_date_bridge import (
        enrich_recommendation_result_for_date,
        enrich_recommendation_result_with_best_dates,
    )
    from ui.components import metric_row, page_header, section_header
    print("  OK")
except Exception as e:
    print(f"  FAIL: {e}")

print("\nTesting Log Event imports...")
try:
    from learning.signal_store import log_outcome
    from ui_data_bridge import get_session_property, get_session_result, load_application_data
    from ui.styles import load_css
    from ui.components import page_header, section_header
    print("  OK")
except Exception as e:
    print(f"  FAIL: {e}")

print("\nTesting Analytics imports...")
try:
    from learning.signal_store import load_signals_dataframe
    from ui_data_bridge import get_session_property, get_session_result, load_application_data
    from ui.styles import load_css
    from ui.components import history_table, metric_row, page_header, section_header
    print("  OK")
except Exception as e:
    print(f"  FAIL: {e}")

print("\nTesting data loading...")
try:
    data = load_application_data()
    print(f"  Residents: {len(data.get('residents', []))} rows")
    print(f"  Profiles: {len(data.get('profiles', {}))} properties")
    print(f"  Events: {len(data.get('events', []))} rows")
    print(f"  History: {len(data.get('history', []))} rows")
except Exception as e:
    print(f"  FAIL: {e}")

print("\nAll import tests complete.")
