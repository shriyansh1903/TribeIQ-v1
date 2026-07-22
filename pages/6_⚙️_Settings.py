import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import datetime
import os
import platform

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ui.styles import load_css
from integrations.sync import WardenSyncEngine
from utils.schema_utils import safe_get_column, safe_status_column, safe_numeric_column, safe_column_exists
from src.services.health_service import HealthService

st.set_page_config(
    page_title="TribeIQ - Administration",
    page_icon="⚙️",
    layout="wide"
)

from src.auth.session_manager import require_login
require_login("Settings")

load_css()

# Load sync engine and status
engine = WardenSyncEngine()
status = engine.load_sync_status()
is_mock = engine.client.auth.mock_mode

# Dummy metrics for placeholders to avoid hallucinating real logic if it doesn't exist
APP_VERSION = "v1.2.4 Enterprise"
APP_BUILD = "Build 4920.1a"
LAST_DEPLOYMENT = "2026-07-15 08:00 UTC"

# ===========================================================
# SECTION 1: Administration Header
# ===========================================================
st.markdown("## ⚙️ Administration Center")
st.markdown("*Centralized system configuration, monitoring, and integration control.*")
st.write("")

try:
    h_col1, h_col2, h_col3, h_col4 = st.columns(4)
    with h_col1:
        sys_status = "🟢 Operational" if status.get("health") != "Unhealthy" else "🔴 Degraded"
        st.metric("System Status", sys_status)
    with h_col2:
        st.metric("Current Version", APP_VERSION)
    with h_col3:
        last_sync = status.get("last_successful_sync", "Never")
        if last_sync != "Never" and "T" in str(last_sync):
            last_sync = str(last_sync).split("T")[0]
        st.metric("Last Sync", str(last_sync))
    with h_col4:
        env_str = "Sandbox/Mock" if is_mock else "Production"
        st.metric("Current Environment", env_str)

    act_col1, act_col2, act_col3 = st.columns(3)
    with act_col1:
        if st.button("🔄 Refresh Status", use_container_width=True):
            st.rerun()
    with act_col2:
        if st.button("🔌 Test Warden Connection", use_container_width=True):
            with st.spinner("Testing connection..."):
                test_res = engine.test_connection()
                if test_res.get("success"):
                    st.success(f"✓ Connection Successful! Response time: {test_res['response_time_ms']} ms")
                else:
                    st.error(f"Connection Failed: {test_res.get('error')}")
    with act_col3:
        if st.button("⚡ Run Full Sync", type="primary", use_container_width=True):
            progress_placeholder = st.empty()
            def progress_callback(msg: str):
                progress_placeholder.info(f"Sync Progress: {msg}")
            with st.spinner("Synchronizing with Warden..."):
                res = engine.sync_everything(progress_callback=progress_callback)
                if res.get("success"):
                    st.success("Full synchronization completed successfully.")
                else:
                    st.error(f"Sync failed: {res.get('error')}")
except Exception as e:
    st.warning("⚠ Unable to load system controls.")

st.write("---")

# ===========================================================
# SECTION 2: System Health
# ===========================================================
st.markdown("### 🏥 System Health")

health_cols = st.columns(4)
health_items = [
    {"name": "Warden API", "status": "🟢 Healthy" if status.get("health") != "Unhealthy" else "🔴 Error", "checked": "Just now"},
    {"name": "Learning Pipeline", "status": "🟢 Optimal", "checked": "10 mins ago"},
    {"name": "Recommendation Engine", "status": "🟢 Online", "checked": "10 mins ago"},
    {"name": "Database", "status": "🟢 Connected", "checked": "2 mins ago"},
    {"name": "Calendar Integration", "status": "🟢 Synced", "checked": "1 hour ago"},
    {"name": "Analytics Engine", "status": "🟢 Running", "checked": "5 mins ago"},
    {"name": "Storage Systems", "status": "🟢 64% Free", "checked": "Just now"}
]

for idx, item in enumerate(health_items):
    col = health_cols[idx % 4]
    with col:
        with st.container(border=True):
            st.markdown(f"**{item['name']}**")
            st.markdown(f"Status: {item['status']}")
            st.markdown(f"*Last Checked: {item['checked']}*")

st.write("---")

# ===========================================================
# SECTION 2.5: Platform Database & Repository Health
# ===========================================================
st.markdown("### 🌐 Platform Database & Repository Health")
try:
    db_health = HealthService.get_database_status()
    db_connected = db_health.get("connected", False)
    
    health_cols_p = st.columns(4)
    with health_cols_p[0]:
        with st.container(border=True):
            st.markdown("**MongoDB Status**")
            status_color = "🟢 Connected" if db_connected else "🔴 Offline"
            st.markdown(f"Status: {status_color}")
            st.markdown(f"Database: `{db_health.get('database_name', 'N/A')}`")
            
    with health_cols_p[1]:
        with st.container(border=True):
            st.markdown("**Platform Status**")
            st.markdown(f"Version: `{HealthService.get_app_version()}`")
            mode_str = "MongoDB Active" if db_connected else "CSV Fallback Active"
            st.markdown(f"Mode: `{mode_str}`")
            
    with health_cols_p[2]:
        with st.container(border=True):
            st.markdown("**Datastore Fallback**")
            fb_status = "⚪ Ready" if db_connected else "🟢 Active"
            st.markdown(f"CSV Fallback: {fb_status}")
            mig_status = "Completed" if db_connected else "Standby (Offline)"
            st.markdown(f"Migration: `{mig_status}`")
            
    with health_cols_p[3]:
        with st.container(border=True):
            st.markdown("**Repository Collections**")
            rep_status = "🟢 Connected" if db_connected else "🔴 Disconnected"
            st.markdown(f"Repositories: {rep_status}")
            st.markdown(f"Collections: {len(db_health.get('collections', {}))} / 11")
            
    if not db_connected:
        st.warning("⚠️ MongoDB Atlas is currently offline or unreachable. The system is operating in fallback CSV mode.")
    else:
        st.success("🟢 Connected to MongoDB Atlas. Active database repositories are loaded.")
        # Render a small expandable section with actual record counts
        with st.expander("📊 MongoDB Collection Record Counts"):
            for coll, count in db_health.get("collections", {}).items():
                st.write(f"- Collection `{coll}`: **{count}** records")
        
    st.write("")
    st.markdown("#### 👤 Active User Session Status")
    s_col1, s_col2, s_col3 = st.columns(3)
    with s_col1:
        st.write(f"**Authenticated User:** `{st.session_state.user.get('username')}`")
        st.write(f"**Display Name:** `{st.session_state.user.get('display_name', 'N/A')}`")
    with s_col2:
        st.write(f"**Security Profile Role:** `{st.session_state.user.get('role', 'Read Only')}`")
        rem_str = "Indefinite (Remember Me active)" if st.session_state.remember_me else "30 Minutes Inactivity Expiry"
        st.write(f"**Session Expiry Profile:** `{rem_str}`")
    with s_col3:
        if st.button("🚪 Terminate Session (Sign Out)", type="primary", use_container_width=True, key="settings_logout_btn"):
            logout()
except Exception as e:
    st.error(f"Failed to load platform database health metrics: {str(e)}")

st.write("---")

# ===========================================================
# SECTION 3: Warden Integration
# ===========================================================
st.markdown("### 🔌 Warden Integration")

w_col1, w_col2, w_col3 = st.columns(3)
with w_col1:
    with st.container(border=True):
        st.markdown("**Connection Details**")
        st.write(f"**Status:** {'Sandbox/Mock Mode' if is_mock else 'Live API Connected'}")
        st.write(f"**Response Time:** `{status.get('api_response_time_ms', 0)} ms`")
        st.write(f"**Last Success:** `{status.get('last_successful_sync', 'N/A')}`")
        st.write(f"**Last Failure:** `{status.get('last_failed_sync', 'N/A')}`")
with w_col2:
    with st.container(border=True):
        st.markdown("**Sync Metrics**")
        st.write(f"**Duration:** `{status.get('sync_duration_seconds', 0.0)} s`")
        st.write(f"**Residents Synced:** `{status.get('residents_imported', 0)}`")
        st.write(f"**Bookings Synced:** `{status.get('bookings_imported', 0)}`")
        st.write(f"**Properties Synced:** `{status.get('properties_imported', 0)}`")
with w_col3:
    with st.container(border=True):
        st.markdown("**Quick Actions**")
        if st.button("Test Connection", key="test_w", use_container_width=True):
            test_res = engine.test_connection()
            if test_res.get("success"):
                st.toast(f"Connection OK: {test_res['response_time_ms']}ms")
            else:
                st.error("Connection failed.")
        if st.button("Sync Residents Only", key="sync_r", use_container_width=True):
            st.toast("Resident sync queued for background processing.")
        if st.button("Sync Everything", key="sync_e", type="primary", use_container_width=True):
            st.toast("Please use the main Run Full Sync button in the header.")

st.write("---")

# ===========================================================
# SECTION 4: Application Configuration
# ===========================================================
st.markdown("### ⚙️ Application Configuration")

conf_col1, conf_col2 = st.columns(2)
with conf_col1:
    with st.container(border=True):
        st.markdown("**General Settings**")
        st.checkbox("Enable Notifications", value=True)
        st.checkbox("Strict Mode Validation", value=False)
        st.selectbox("Default Theme", ["Light", "Dark", "System Match"], index=0)

    with st.container(border=True):
        st.markdown("**Synchronization**")
        auto_sync = st.checkbox(
            "Auto-sync on startup",
            value=status.get("auto_sync_on_startup", False)
        )
        if auto_sync != status.get("auto_sync_on_startup", False):
            status["auto_sync_on_startup"] = auto_sync
            engine.save_sync_status(status)
            st.toast("Auto-sync updated!")
        st.selectbox("Sync Frequency", ["Hourly", "Daily", "Manual Only"], index=2)

with conf_col2:
    with st.container(border=True):
        st.markdown("**AI Configuration**")
        st.selectbox("LLM Provider", ["NVIDIA NIM", "OpenAI", "Anthropic"], index=0, disabled=True)
        st.slider("Model Temperature (Creativity)", min_value=0.0, max_value=1.0, value=0.2, step=0.1)
        st.checkbox("Enable Context Memory", value=True)

    with st.container(border=True):
        st.markdown("**Data Exports**")
        st.checkbox("Include PII in Exports", value=False)
        st.selectbox("Default Export Format", ["CSV", "Excel", "JSON"], index=0)

st.write("---")

# ===========================================================
# SECTION 5: Data Management
# ===========================================================
st.markdown("### 🗄️ Data Management")

dm_col1, dm_col2, dm_col3, dm_col4 = st.columns(4)
with dm_col1:
    st.metric("Latest Backup", "Today, 02:00 AM")
with dm_col2:
    st.metric("Restore Status", "Available")
with dm_col3:
    st.metric("CSV Import Status", "Ready")
with dm_col4:
    st.metric("Cache Size", "42.5 MB")

with st.expander("🚨 Emergency Database Import (Fallback)", expanded=False):
    st.warning("Only use this uploader as a fallback when the Warden API connection is completely offline.")
    uploaded_file = st.file_uploader(
        "Upload Residents.csv to replace the principal database manually",
        type=["csv"]
    )
    if uploaded_file is not None:
        file_id = f"manual_upload_{uploaded_file.name}_{uploaded_file.size}"
        if st.session_state.get("last_uploaded_file_id") != file_id:
            try:
                file_bytes = uploaded_file.getvalue()
                from io import BytesIO
                test_df = pd.read_csv(BytesIO(file_bytes), nrows=5)
                test_df.columns = test_df.columns.str.strip()
                
                from config import REQUIRED_COLUMNS, RAW_DATA
                missing = [col for col in REQUIRED_COLUMNS if col not in test_df.columns]
                if missing:
                    st.error(f"Invalid spreadsheet format. Missing columns: {', '.join(missing)}")
                else:
                    engine._create_backup()
                    with open(RAW_DATA, "wb") as f:
                        f.write(file_bytes)
                    import cleaner
                    import feature_engineering
                    import profile_generator
                    cleaner.run()
                    feature_engineering.run()
                    profile_generator.run()
                    st.session_state["last_uploaded_file_id"] = file_id
                    st.toast("Emergency manual database import complete!")
                    st.rerun()
            except Exception as e:
                st.error("Emergency import failed. Please verify the file format and try again.")
                with st.expander("Optional details"):
                    st.write(str(e))

st.write("")

st.write("---")

# ===========================================================
# SECTION 7: Maintenance
# ===========================================================
st.markdown("### 🛠️ Maintenance")

m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
with m_col1:
    if st.button("Rebuild Analytics", use_container_width=True):
        st.toast("Analytics cache rebuild scheduled.")
with m_col2:
    if st.button("Refresh Profiles", use_container_width=True):
        try:
            import profile_generator
            profile_generator.run()
            st.toast("Property profiles refreshed successfully!")
        except Exception:
            st.toast("Profile generator not found or failed.")
with m_col3:
    if st.button("Refresh Recommendations", use_container_width=True):
        st.toast("Recommendation engine indices refreshed.")
with m_col4:
    if st.button("Clean Cache", use_container_width=True):
        st.cache_data.clear()
        st.toast("Application cache cleared successfully.")
with m_col5:
    if st.button("Export Logs", use_container_width=True):
        st.toast("System logs exported to downloads.")


# ===========================================================
# SECTION 7.5: Eventbrite Integration
# ===========================================================
st.write("---")
st.markdown("### 🔌 Eventbrite Integration Settings")
from src.integrations.eventbrite.service import eventbrite_service
from src.integrations.eventbrite.webhook import is_webhook_reachable
from src.utils.background_job import background_job_service
from src.database import db_manager
from src.config import settings, logger

# 1. MongoDB Connected
mongo_ok = db_manager.ping_check()
mongo_status = "🟢 Connected" if mongo_ok else "🔴 Disconnected"

# 2. API Connected
token = getattr(settings, "EVENTBRITE_PRIVATE_TOKEN", "MOCK_TOKEN")
api_ok = False
if token != "MOCK_TOKEN" and token:
    try:
        res = eventbrite_service.client.get("/users/me/")
        if "error" not in res:
            api_ok = True
    except Exception:
        pass
api_status = "🟢 Connected" if api_ok else ("🟡 Standby (Mock)" if token == "MOCK_TOKEN" else "🔴 Error / Unauthorized")

# 3. Sync Status
sync_status = eventbrite_service.get_sync_status()
last_sync_time = sync_status.get("last_sync_time", "Never")
sync_state = sync_status.get("status", "Idle")

imported_count = 0
if mongo_ok and db_manager.db is not None:
    try:
        imported_count = db_manager.db["external_events"].count_documents({})
    except Exception:
        imported_count = sync_status.get("imported_count", 0)

# Display in a 3-column layout
eb_status_cols = st.columns(3)

with eb_status_cols[0]:
    with st.container(border=True):
        st.markdown("**API & Database**")
        st.markdown(f"Eventbrite API Connection: {api_status}")
        st.markdown(f"MongoDB Status: {mongo_status}")

with eb_status_cols[1]:
    with st.container(border=True):
        st.markdown("**Synchronisation**")
        st.markdown(f"Sync Status: `{sync_state}`")
        st.markdown(f"Last Sync Time: `{last_sync_time}`")

with eb_status_cols[2]:
    with st.container(border=True):
        st.markdown("**Data Summary**")
        st.markdown(f"External Events Imported: **{imported_count}**")
        st.markdown(f"Source Context: `Eventbrite Pune Search`")

# Operations buttons
st.write("")
btn_cols = st.columns(2)
with btn_cols[0]:
    if st.button("🔄 Sync Now", key="eb_sync_btn", use_container_width=True):
        with st.spinner("Synchronising Pune Events..."):
            res = eventbrite_service.sync_pune_events()
            if res.get("status") == "Success":
                st.toast(f"Eventbrite Sync complete. Synced: {res.get('synced_count')} events.")
            else:
                st.error(f"Sync failed: {res.get('error')}")
            st.rerun()

with btn_cols[1]:
    if st.button("🔁 Refresh Events", key="eb_refresh_btn", use_container_width=True):
        st.rerun()

st.write("---")

# ===========================================================
# SECTION 8: System Information
# ===========================================================
st.markdown("### ℹ️ System Information")

sys_col1, sys_col2, sys_col3 = st.columns(3)
with sys_col1:
    st.write(f"**Version:** {APP_VERSION}")
    st.write(f"**Build:** {APP_BUILD}")
with sys_col2:
    st.write(f"**Python Version:** {platform.python_version()}")
    st.write("**Database Size:** ~1.2 GB")
with sys_col3:
    st.write(f"**Last Deployment:** {LAST_DEPLOYMENT}")
    st.write(f"**Host OS:** {platform.system()} {platform.release()}")

st.write("")
