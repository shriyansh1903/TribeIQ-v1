"""
===========================================================
TribeIQ Dashboard Page
===========================================================

Live dashboard using date-aware occupancy intelligence.

Current resident rule:

    Move In Date <= today < Move Out Date

The Dashboard uses the same central occupancy engine as:
1. Property Profile
2. Future event scheduling
3. Attendance prediction
===========================================================
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

import pandas as pd
import streamlit as st


# ===========================================================
# Project Paths
# ===========================================================

PROJECT_ROOT = Path(
    __file__
).resolve().parents[1]

SRC_DIR = (
    PROJECT_ROOT
    / "src"
)

INTELLIGENCE_DIR = (
    SRC_DIR
    / "intelligence"
)


for path in (
    PROJECT_ROOT,
    SRC_DIR,
    INTELLIGENCE_DIR,
):

    path_string = str(
        path.resolve()
    )

    if path_string not in sys.path:

        sys.path.insert(
            0,
            path_string,
        )


# ===========================================================
# Backend Imports
# ===========================================================

from ui_data_bridge import (
    get_session_property,
    get_session_result,
    load_application_data,
)

from intelligence.occupancy_forecaster import (
    get_current_occupancy_all_properties,
)

from ui.components import (
    history_table,
    metric_row,
    page_header,
    section_header,
)


# CSS is loaded globally by app.py via ui.styles.load_css()


# ===========================================================
# Cached Application Data
# ===========================================================

@st.cache_data(
    show_spinner=False,
)
def get_application_data() -> Dict[str, Any]:

    data = load_application_data()

    if isinstance(
        data,
        dict,
    ):

        return data

    return {}


# ===========================================================
# Current Occupancy
# ===========================================================

def load_current_occupancy() -> Dict[
    str,
    Dict[str, Any],
]:

    try:

        forecasts = (
            get_current_occupancy_all_properties()
        )

        if isinstance(
            forecasts,
            dict,
        ):

            return forecasts

    except Exception as error:

        st.warning(
            "Current occupancy could not be calculated "
            f"from the resident timeline: {error}"
        )

    return {}


# ===========================================================
# Page Header
# ===========================================================

page_header(
    "🏠 Dashboard",
    "Live overview of current occupancy, resident intelligence, "
    "event performance and recommendation activity.",
)

# ===========================================================
# Warden API Integration Sidebar Widget
# ===========================================================
try:
    from integrations.sync import WardenSyncEngine
    sync_engine = WardenSyncEngine()
    sync_status = sync_engine.load_sync_status()

    st.sidebar.divider()
    st.sidebar.subheader("🔌 Warden API Integration")
    is_mock = sync_engine.client.auth.mock_mode
    status_text = "● Connected (Sandbox)" if is_mock else "● Connected (Live API)"
    st.sidebar.markdown(f"**Status:** {status_text}")
    st.sidebar.write(f"**Last Sync:** `{sync_status.get('last_sync_time', 'Never')}`")
    st.sidebar.write(f"**Residents Synced:** `{sync_status.get('residents_synced', 0)}`")
    st.sidebar.write(f"**Bookings Synced:** `{sync_status.get('bookings_synced', 0)}`")
    st.sidebar.write(f"**Properties Synced:** `{sync_status.get('properties_synced', 0)}`")
    st.sidebar.write(f"**API Health:** `{sync_status.get('health', 'Unknown')}`")
except Exception:
    pass


# ===========================================================
# Load Application Data
# ===========================================================

try:

    data = get_application_data()

except Exception as error:

    st.error(
        f"Unable to load dashboard data: {error}"
    )

    st.stop()


residents = data.get(
    "residents"
)


if not isinstance(
    residents,
    pd.DataFrame,
):

    residents = pd.DataFrame()


profiles = data.get(
    "profiles"
)


if not isinstance(
    profiles,
    dict,
):

    profiles = {}


events = data.get(
    "events"
)


if not isinstance(
    events,
    pd.DataFrame,
):

    events = pd.DataFrame()


history = data.get(
    "history"
)


if not isinstance(
    history,
    pd.DataFrame,
):

    history = pd.DataFrame()


# ===========================================================
# Load Live Date-Aware Occupancy
# ===========================================================

current_occupancy = (
    load_current_occupancy()
)


current_residents = sum(
    int(
        forecast.get(
            "active_residents",
            0,
        )
    )
    for forecast
    in current_occupancy.values()
    if isinstance(
        forecast,
        dict,
    )
)


total_capacity = sum(
    int(
        forecast.get(
            "total_capacity",
            0,
        )
    )
    for forecast
    in current_occupancy.values()
    if isinstance(
        forecast,
        dict,
    )
)


if total_capacity > 0:

    overall_occupancy_percent = (
        current_residents
        / total_capacity
    ) * 100.0

else:

    overall_occupancy_percent = 0.0


# ===========================================================
# Shared Recommendation State
# ===========================================================

recommendation_result = (
    get_session_result(
        st.session_state
    )
)


recommendation_property = (
    get_session_property(
        st.session_state
    )
)


# ===========================================================
# Main Dashboard Metrics
# ===========================================================

metric_row([
    {
        "title":
            "Current Residents",

        "value":
            f"{current_residents:,}",
    },
    {
        "title":
            "Current Occupancy",

        "value":
            f"{overall_occupancy_percent:.1f}%",
    },
    {
        "title":
            "Properties",

        "value":
            len(
                current_occupancy
            )
            if current_occupancy
            else len(
                profiles
            ),
    },
    {
        "title":
            "Events Available",

        "value":
            len(
                events
            ),
    },
])


# ===========================================================
# Property Occupancy Overview
# ===========================================================

st.divider()


section_header(
    "Current Property Occupancy"
)


if current_occupancy:

    property_columns = st.columns(
        len(
            current_occupancy
        )
    )


    for column, (
        property_name,
        forecast,
    ) in zip(
        property_columns,
        current_occupancy.items(),
    ):

        if not isinstance(
            forecast,
            dict,
        ):

            continue


        active_residents = int(
            forecast.get(
                "active_residents",
                0,
            )
        )


        capacity = int(
            forecast.get(
                "total_capacity",
                0,
            )
        )


        occupancy_percent = float(
            forecast.get(
                "occupancy_percent",
                0.0,
            )
        )


        available_beds = int(
            forecast.get(
                "available_beds",
                0,
            )
        )


        with column:

            st.subheader(
                property_name
            )


            st.metric(
                "Current Residents",
                f"{active_residents:,}",
            )


            st.metric(
                "Occupancy",
                f"{occupancy_percent:.1f}%",
            )


            st.caption(
                f"{active_residents:,} of "
                f"{capacity:,} beds occupied · "
                f"{available_beds:,} available"
            )


    first_forecast = next(
        iter(
            current_occupancy.values()
        ),
        {},
    )


    if isinstance(
        first_forecast,
        dict,
    ):

        as_of_date = first_forecast.get(
            "as_of_date"
        )


        if as_of_date:

            st.caption(
                "Occupancy calculated from the Warden "
                f"move-in/move-out timeline as of {as_of_date}."
            )


else:

    st.warning(
        "Live occupancy data are unavailable. "
        "Check the Warden resident export."
    )


# ===========================================================
# Recommendation Activity
# ===========================================================

st.divider()


section_header(
    "Recommendation Activity"
)


if isinstance(
    recommendation_result,
    dict,
):

    activity_1, activity_2, activity_3 = (
        st.columns(3)
    )


    with activity_1:

        st.metric(
            "Active Property",
            recommendation_property
            or "Unknown",
        )


    with activity_2:

        st.metric(
            "Candidates Evaluated",
            recommendation_result.get(
                "candidate_count",
                0,
            )
            or 0,
        )


    with activity_3:

        st.metric(
            "Events Selected",
            recommendation_result.get(
                "selected_count",
                0,
            )
            or 0,
        )


    major_event = (
        recommendation_result.get(
            "major_event"
        )
    )


    if isinstance(
        major_event,
        dict,
    ):

        st.success(
            "Current top recommendation: "
            f"{major_event.get(
                'event_name',
                'Unknown Event'
            )}"
        )


else:

    st.info(
        "No recommendations have been generated "
        "in this session yet."
    )


# ===========================================================
# System Status
# ===========================================================

st.divider()


section_header(
    "System Status"
)


metric_row([
    {
        "title":
            "Resident Timeline",

        "value":
            "Connected"
            if current_occupancy
            else "Unavailable",
    },
    {
        "title":
            "Recommendation Backend",

        "value":
            "Connected"
            if (
                not events.empty
                and bool(
                    profiles
                )
            )
            else "Unavailable",
    },
    {
        "title":
            "Learning Loop",

        "value":
            "Active"
            if not history.empty
            else "Ready",
    },
])


# ===========================================================
# Recent Event Outcomes
# ===========================================================

if not history.empty:

    st.divider()

    st.subheader(
        "Recent Event Outcomes"
    )

    history_table(
        history
        .tail(10)
        .iloc[::-1]
    )
