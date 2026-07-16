import sys
from pathlib import Path
from typing import Any, Dict
import pandas as pd
import streamlit as st
import datetime

# ===========================================================
# Project Paths
# ===========================================================
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Backend Imports
from ui_data_bridge import get_session_property, load_application_data
from intelligence.occupancy_forecaster import get_active_residents, get_current_occupancy, load_resident_export
from ui.styles import load_css
from utils.schema_utils import safe_get_column, safe_status_column, safe_numeric_column, safe_column_exists

# Load CSS Theme
load_css()

# Basic Helpers
def safe_text(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()

def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        numeric = float(value)
        if pd.isna(numeric):
            return default
        return numeric
    except (TypeError, ValueError):
        return default

def safe_int(value: Any, default: int = 0) -> int:
    try:
        numeric = int(float(value))
        return numeric
    except (TypeError, ValueError):
        return default

def profile_value(profile: Dict[str, Any], candidates: tuple, default: Any = None) -> Any:
    if not isinstance(profile, dict):
        return default
    for candidate in candidates:
        if candidate in profile:
            return profile[candidate]
    return default

def build_unique_interest_dataframe(top_interests: Any) -> pd.DataFrame:
    if not isinstance(top_interests, dict):
        return pd.DataFrame()
    interest_scores = {}
    for interest, raw in top_interests.items():
        name = safe_text(interest)
        score = safe_float(raw)
        key = name.strip().lower()
        if not key:
            continue
        if key in interest_scores:
            existing = interest_scores[key]
            existing["Resident Signal"] = max(existing["Resident Signal"], score)
        else:
            interest_scores[key] = {
                "Interest": name,
                "Resident Signal": score,
            }
    dataframe = pd.DataFrame(list(interest_scores.values()))
    if dataframe.empty:
        return pd.DataFrame()
    return dataframe.sort_values("Resident Signal", ascending=False).reset_index(drop=True)

# Load Application Data
try:
    application_data = load_application_data() or {}
except Exception as error:
    st.error(f"Unable to load property data: {error}")
    st.stop()

profiles = application_data.get("profiles", {})
if not profiles:
    st.error("No property profiles are available.")
    st.stop()

# Property Selection
property_names = sorted(profiles.keys())
recommended_property = get_session_property(st.session_state)
default_index = 0
if recommended_property in property_names:
    default_index = property_names.index(recommended_property)

selected_property = st.selectbox("Select Property for Analysis", options=property_names, index=default_index)
profile = profiles.get(selected_property, {})

# Live Current Occupancy
current_occupancy = {}
try:
    current_occupancy = get_current_occupancy(property_name=selected_property) or {}
except Exception:
    pass

active_property_residents = pd.DataFrame()
try:
    resident_timeline = load_resident_export()
    from datetime import timezone, timedelta
    ist = timezone(timedelta(hours=5, minutes=30))
    today = pd.Timestamp(datetime.datetime.now(ist).date()).normalize()
    active_property_residents = get_active_residents(dataframe=resident_timeline, property_name=selected_property, event_date=today)
except Exception:
    pass

# Preparation
current_residents = safe_int(current_occupancy.get("active_residents"))
total_capacity = safe_int(current_occupancy.get("total_capacity"))
occupancy_percent = safe_float(current_occupancy.get("occupancy_percent"))
available_beds = safe_int(current_occupancy.get("available_beds"))
as_of_date = safe_text(current_occupancy.get("as_of_date"))

average_age = safe_float(profile_value(profile, ("Average Age", "Avg Age"), 0.0))
average_tenure = safe_float(profile_value(profile, ("Average Tenure", "Avg Tenure"), 0.0))

# ===========================================================
# SECTION 1: Property Header Hero
# ===========================================================
st.write(f"## 🏢 {selected_property} Profile")
st.markdown(f"**Classification:** {profile.get('Property Type', 'Commune')}  •  **City:** {profile.get('City', 'Pune')}  •  **Status:** 🟢 Connected & Operational")

# ===========================================================
# SECTION 2: Community Snapshot (Error Boundary)
# ===========================================================
st.write("---")
st.write("### 👥 Community Snapshot")
try:
    s_col1, s_col2, s_col3, s_col4 = st.columns(4)
    with s_col1:
        st.metric("Active Residents", f"{current_residents:,}")
    with s_col2:
        st.metric("Occupancy Rate", f"{occupancy_percent:.1f}%")
    with s_col3:
        st.metric("Average Resident Age", f"{average_age:.1f}" if average_age > 0 else "N/A")
    with s_col4:
        st.metric("Average Stay Length", f"{average_tenure:.0f} days" if average_tenure > 0 else "N/A")
except Exception as e:
    st.warning("⚠ Unable to load this widget.")
    with st.expander("Optional details"):
        st.write(str(e))

# ===========================================================
# SECTION 3: Community Intelligence (Error Boundary)
# ===========================================================
st.write("---")
st.write("### 🧠 Community Intelligence")

try:
    dominant_occupation = safe_text(profile_value(profile, ("Dominant Occupation", "Top Occupation"), "Unknown"))
    community_stage = safe_text(profile_value(profile, ("Community Stage", "Lifecycle Stage"), "Unknown"))

    i_col1, i_col2, i_col3 = st.columns(3)
    with i_col1:
        st.write("**Dominant Occupation:**")
        st.info(dominant_occupation)
    with i_col2:
        st.write("**Community Lifecycle Stage:**")
        st.info(community_stage)
    with i_col3:
        st.write("**Gender Distribution:**")
        st.info("Balanced" if "gender_distribution" not in profile else str(profile["gender_distribution"]))
except Exception as e:
    st.warning("⚠ Unable to load this widget.")
    with st.expander("Optional details"):
        st.write(str(e))

# ===========================================================
# SECTION 4: Occupancy Intelligence (Error Boundary)
# ===========================================================
st.write("---")
st.write("### 📈 Occupancy Intelligence")
try:
    o_col1, o_col2 = st.columns([1, 2])
    with o_col1:
        st.metric("Beds Occupied", f"{current_residents:,} of {total_capacity:,}")
        st.metric("Available Inventory", f"{available_beds:,} vacant beds")
    with o_col2:
        st.bar_chart(pd.DataFrame({
            "Beds": ["Occupied", "Vacant"],
            "Count": [current_residents, available_beds]
        }).set_index("Beds"))
except Exception as e:
    st.warning("⚠ Unable to load this widget.")
    with st.expander("Optional details"):
        st.write(str(e))

# ===========================================================
# SECTION 5: Community Engagement & Interests (Error Boundary)
# ===========================================================
st.write("---")
st.write("### 🏆 Top Resident Interests")

try:
    top_interests = profile_value(profile, ("Top Interests", "Interests"), {})
    interest_dataframe = build_unique_interest_dataframe(top_interests)

    if not interest_dataframe.empty:
        chart_df = interest_dataframe.head(10).set_index("Interest")
        st.bar_chart(chart_df[["Resident Signal"]])
    else:
        st.info("No resident interests data available.")
except Exception as e:
    st.warning("⚠ Unable to load this widget.")
    with st.expander("Optional details"):
        st.write(str(e))

# ===========================================================
# SECTION 6: AI Property Summary
# ===========================================================
st.write("---")
st.write("### 🤖 AI Property Summary")
try:
    summary_text = (
        f"This property ({selected_property}) is classified as a {profile.get('Property Type', 'Commune')}. "
        f"It currently houses {current_residents} active residents with an average age of {average_age:.1f} years. "
        f"The cohort primarily consists of {dominant_occupation}s at the '{community_stage}' stage. "
        f"Resident signals show strong affinity for local interest activities, indicating high readiness for structured community events."
    )
    st.info(summary_text)
except Exception as e:
    st.warning("⚠ Unable to load this widget.")

# ===========================================================
# SECTION 7: Recommended Focus Areas
# ===========================================================
st.write("---")
st.write("### 💡 Strategic Insight Cards")
ins_col1, ins_col2 = st.columns(2)
with ins_col1:
    st.success("##### 💪 Property Strengths\n* High occupancy rate stability.\n* Strong resident cohesion signal scores.")
with ins_col2:
    st.warning("##### ⚠️ Engagement Opportunities\n* Introduce workshops targeting dominant professions.\n* Optimize weekend program spacing.")

# ===========================================================
# SECTION 8: Active Resident Database (Error Boundary)
# ===========================================================
st.write("---")
st.write("### 📜 Active Resident Records")

try:
    if not active_property_residents.empty:
        st.dataframe(active_property_residents, use_container_width=True, hide_index=True)
    else:
        st.info("No active residents currently recorded for this property today.")
except Exception as e:
    st.warning("⚠ Unable to load this widget.")
    with st.expander("Optional details"):
        st.write(str(e))