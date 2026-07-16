"""
===========================================================
TribeIQ Application Entry Point
===========================================================

Main frontend shell for the fully integrated TribeIQ system.
===========================================================
"""

import sys
from pathlib import Path

import streamlit as st


# ===========================================================
# Project Paths
# ===========================================================

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


# ===========================================================
# Page Configuration
# ===========================================================

st.set_page_config(
    page_title="TribeIQ",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ===========================================================
# Shared Session State
# ===========================================================

SESSION_DEFAULTS = {
    "tribeiq_recommendation_result": None,
    "tribeiq_recommendation_property": "",
    "tribeiq_recommendation_error": "",
    "tribeiq_recommendation_running": False,
    "tribeiq_last_logged_event": None
}


for key, default_value in SESSION_DEFAULTS.items():

    if key not in st.session_state:

        st.session_state[key] = default_value


# ===========================================================
# Global UI Styling
# ===========================================================

from ui.styles import load_css


load_css()


# ===========================================================
# Auto Sync on Startup check
# ===========================================================
if "auto_synced_on_startup" not in st.session_state:
    st.session_state["auto_synced_on_startup"] = True
    try:
        import sys
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
        from integrations.sync import WardenSyncEngine
        engine = WardenSyncEngine()
        status = engine.load_sync_status()
        if status.get("auto_sync_on_startup", False):
            engine.sync_everything()
    except Exception:
        pass


# ===========================================================
# Navigation  (Streamlit 1.58+ requires st.navigation)
# ===========================================================

from pathlib import Path as _Path

_PAGES_DIR = _Path(__file__).resolve().parent / "pages"


pages = [
    st.Page(_PAGES_DIR / "1_🏠_Dashboard.py", title="Dashboard", icon="📊", default=True),
    st.Page(_PAGES_DIR / "2_👥_Property_Profile.py", title="Property Profile", icon="👥"),
    st.Page(_PAGES_DIR / "3_🎯_Recommendations.py", title="Smart Recommendations", icon="🎯"),
    st.Page(_PAGES_DIR / "4_📝_Log_Event.py", title="Log Event", icon="📝"),
    st.Page(_PAGES_DIR / "5_📊_Analytics.py", title="Analytics", icon="📈"),
    st.Page(_PAGES_DIR / "6_⚙️_Settings.py", title="Settings", icon="⚙️"),
    st.Page(_PAGES_DIR / "7_🏪_Vendor_Management.py", title="Vendor Management", icon="🏪"),
]

with st.sidebar:
    st.markdown("### System Controls")
    if st.button("🔄 Refresh System", use_container_width=True):
        st.cache_data.clear()
        for key, val in SESSION_DEFAULTS.items():
            st.session_state[key] = val
        if "tribeiq_dated_recommendation_result" in st.session_state:
            st.session_state["tribeiq_dated_recommendation_result"] = None
        if "tribeiq_dated_result_source" in st.session_state:
            st.session_state["tribeiq_dated_result_source"] = ""
        st.toast("System cache and state refreshed!")
        st.rerun()

nav = st.navigation(pages)
nav.run()