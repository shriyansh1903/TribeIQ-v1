import sys
from pathlib import Path
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ui.components import page_header
from integrations.sync import WardenSyncEngine

# Page Header
page_header(
    "⚙️ Settings",
    "Configure API credentials, manage synchronization, and access emergency fallback uploader tools."
)

st.subheader("Warden API Integration")

# Load sync engine and status
engine = WardenSyncEngine()
status = engine.load_sync_status()

# -----------------------------------------------------------
# Connection Status & Configuration
# -----------------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    st.markdown("### Configuration")
    
    is_mock = engine.client.auth.mock_mode
    status_label = "🟢 Connected (Sandbox/Mock Mode)" if is_mock else "🟢 Connected (Live API)"
    if status.get("health") == "Unhealthy":
        status_label = "🔴 Connection Failed"
    elif status.get("status") == "Offline Mode":
        status_label = "🔵 Offline Mode"

    st.write(f"**Connection Status:** {status_label}")
    st.write(f"**API Health:** `{status.get('health', 'Unknown')}`")
    st.write(f"**API Response Time:** `{status.get('api_response_time_ms', 0)} ms`")
    
    # Connection testing button
    if st.button("Test Connection", use_container_width=True):
        with st.spinner("Testing connection..."):
            test_res = engine.test_connection()
            if test_res.get("success"):
                st.success(f"✓ Connection Successful! Response time: {test_res['response_time_ms']} ms")
            else:
                st.error(f"Connection Failed: {test_res.get('error')}")
            st.cache_data.clear()
            st.rerun()

    # Startup auto-sync toggle
    auto_sync = st.checkbox(
        "Automatically sync on application startup",
        value=status.get("auto_sync_on_startup", False),
        help="If checked, TribeIQ will automatically fetch latest resident data on page startup."
    )
    if auto_sync != status.get("auto_sync_on_startup", False):
        status["auto_sync_on_startup"] = auto_sync
        engine.save_sync_status(status)
        st.toast("Auto-sync setting updated!")

with col2:
    st.markdown("### Synchronization Audits")
    st.write(f"**Last Successful Sync:** `{status.get('last_successful_sync', 'N/A')}`")
    st.write(f"**Last Failed Sync:** `{status.get('last_failed_sync', 'N/A')}`")
    st.write(f"**Sync Duration:** `{status.get('sync_duration_seconds', 0.0)} s`")
    st.write(f"**Residents Sync Count:** `{status.get('residents_imported', 0)}`")
    st.write(f"**Bookings Sync Count:** `{status.get('bookings_imported', 0)}`")
    st.write(f"**Properties Sync Count:** `{status.get('properties_imported', 0)}`")

# -----------------------------------------------------------
# Manual Synchronization Controls
# -----------------------------------------------------------
st.divider()
st.subheader("Manual Synchronization Controls")

progress_placeholder = st.empty()

if st.button("Sync Everything", type="primary", use_container_width=True):
    def progress_callback(msg: str):
        progress_placeholder.info(f"Sync Progress: {msg}")

    res = engine.sync_everything(progress_callback=progress_callback)
    if res.get("success"):
        if res.get("changed", True):
            st.success("Full synchronization completed successfully and downstream databases rebuilt!")
        else:
            st.success("Sync completed. No resident changes detected. Downstream files preserved.")
        st.cache_data.clear()
        st.rerun()
    else:
        st.error(f"Sync failed: {res.get('error')}")

# -----------------------------------------------------------
# Emergency Import (Fallback Option)
# -----------------------------------------------------------
st.divider()
st.subheader("🚨 Emergency Import (Fallback)")
st.warning("Only use this uploader as a fallback when the Warden API connection is completely offline.")

uploaded_file = st.file_uploader(
    "Drag & Drop Residents.csv",
    type=["csv"],
    help="Upload a new spreadsheet to replace the principal database manually."
)

if uploaded_file is not None:
    file_id = f"manual_upload_{uploaded_file.name}_{uploaded_file.size}"
    if st.session_state.get("last_uploaded_file_id") != file_id:
        try:
            file_bytes = uploaded_file.getvalue()
            import pandas as pd
            from io import BytesIO
            test_df = pd.read_csv(BytesIO(file_bytes), nrows=5)
            test_df.columns = test_df.columns.str.strip()
            
            # Basic validation
            from config import REQUIRED_COLUMNS, RAW_DATA
            missing = [col for col in REQUIRED_COLUMNS if col not in test_df.columns]
            if missing:
                st.error(f"Invalid spreadsheet format. Missing columns: {', '.join(missing)}")
            else:
                # Backup old database first
                engine._create_backup()
                
                with open(RAW_DATA, "wb") as f:
                    f.write(file_bytes)
                
                # Automatically rebuild downstream databases/profiles
                import cleaner
                import feature_engineering
                import profile_generator

                cleaner.run()
                feature_engineering.run()
                profile_generator.run()
                
                st.session_state["last_uploaded_file_id"] = file_id
                st.cache_data.clear()
                st.toast("Emergency manual database import complete and updated downstream successfully!")
                st.rerun()
        except Exception as e:
            st.error(f"Emergency import failed: {e}")
