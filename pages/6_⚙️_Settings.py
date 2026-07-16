import sys
from pathlib import Path
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ui.components import page_header, section_header
from integrations.sync import WardenSyncEngine

# Page Header
page_header(
    "⚙️ Settings",
    "Configure API credentials and manage the synchronization between Warden and TribeIQ."
)

st.subheader("Warden API Integration")

# Load current sync engine and status
engine = WardenSyncEngine()
status = engine.load_sync_status()

# Connection Details & Status Dashboard
col1, col2 = st.columns(2)
with col1:
    st.markdown("### Integration Details")
    is_mock = engine.client.auth.mock_mode
    status_label = "● Connected (Sandbox/Mock Mode)" if is_mock else "● Connected (Production API)"
    
    st.write(f"**Connection Status:** {status_label}")
    st.write(f"**API Health:** `{status.get('health', 'Unknown')}`")
    st.write(f"**Last Sync Time:** `{status.get('last_sync_time', 'Never')}`")
    st.write(f"**Sync Status:** `{status.get('status', 'Never')}`")

with col2:
    st.markdown("### Cached Datasets")
    st.write(f"**Residents Synced:** `{status.get('residents_synced', 0)}`")
    st.write(f"**Properties Synced:** `{status.get('properties_synced', 0)}`")
    st.write(f"**Bookings Synced:** `{status.get('bookings_synced', 0)}`")

# Sync Buttons Actions
st.divider()
st.subheader("Manual Synchronization Controls")

btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)

with btn_col1:
    if st.button("Sync Residents", use_container_width=True):
        with st.spinner("Syncing residents..."):
            res = engine.sync_residents()
            if res.get("success"):
                st.success(f"Synced {res['count']} residents successfully!")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(f"Sync failed: {res.get('error')}")

with btn_col2:
    if st.button("Sync Properties", use_container_width=True):
        with st.spinner("Syncing properties..."):
            res = engine.sync_properties()
            if res.get("success"):
                st.success(f"Synced {res['count']} properties successfully!")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(f"Sync failed: {res.get('error')}")

with btn_col3:
    if st.button("Sync Bookings", use_container_width=True):
        with st.spinner("Syncing bookings..."):
            res = engine.sync_bookings()
            if res.get("success"):
                st.success(f"Synced {res['count']} bookings successfully!")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(f"Sync failed: {res.get('error')}")

with btn_col4:
    if st.button("Sync Everything", type="primary", use_container_width=True):
        with st.spinner("Syncing everything and rebuilding downstream profiles..."):
            res = engine.sync_everything()
            if res.get("success"):
                st.success("Full synchronization completed successfully!")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(f"Full sync failed: {res.get('error')}")
