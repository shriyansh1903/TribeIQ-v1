"""
===========================================================
TribeIQ Property Profile Page
===========================================================

Live property intelligence using:

1. Backend-generated property profiles
2. Current date-aware occupancy
3. Active resident records
4. Resident interest intelligence

Current occupancy rule:

    Move In Date <= today < Move Out Date

The same central occupancy engine is used by:
- Dashboard
- Property Profile
- Future event scheduling
- Attendance prediction
===========================================================
"""

from __future__ import annotations

import ast
import json
import sys
import textwrap
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
    load_application_data,
)

from intelligence.occupancy_forecaster import (
    get_active_residents,
    get_current_occupancy,
    load_resident_export,
)

from ui.components import (
    history_table,
    metric_row,
    page_header,
    section_header,
)


# ===========================================================
# Basic Helpers
# ===========================================================

def safe_text(
    value: Any,
) -> str:

    if value is None:
        return ""

    try:

        if pd.isna(value):
            return ""

    except (
        TypeError,
        ValueError,
    ):
        pass

    return str(value).strip()


def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:

    try:

        numeric = float(value)

        if pd.isna(numeric):
            return default

        return numeric

    except (
        TypeError,
        ValueError,
    ):
        return default


def safe_int(
    value: Any,
    default: int = 0,
) -> int:

    try:

        return int(
            round(
                float(value)
            )
        )

    except (
        TypeError,
        ValueError,
    ):
        return default


def normalize_column_name(
    value: Any,
) -> str:

    return (
        safe_text(value)
        .lower()
        .replace("_", " ")
        .replace("-", " ")
    )


def profile_value(
    profile: Dict[str, Any],
    keys: tuple,
    default: Any = "",
) -> Any:

    if not isinstance(
        profile,
        dict,
    ):
        return default

    normalized_profile = {
        normalize_column_name(key): value
        for key, value in profile.items()
    }

    for key in keys:

        normalized_key = (
            normalize_column_name(key)
        )

        if normalized_key in normalized_profile:

            return normalized_profile[
                normalized_key
            ]

    return default


# ===========================================================
# Interest Normalization
# ===========================================================

def normalize_interest_name(
    value: Any,
) -> str:

    if value is None:
        return ""

    current = value

    if isinstance(
        current,
        (
            list,
            tuple,
            set,
        ),
    ):

        if not current:
            return ""

        current = next(
            iter(current)
        )

    text = str(current).strip()

    for _ in range(8):

        previous = text

        try:

            decoded = json.loads(text)

            if isinstance(
                decoded,
                list,
            ):

                text = (
                    str(decoded[0]).strip()
                    if decoded
                    else ""
                )

            elif isinstance(
                decoded,
                str,
            ):

                text = decoded.strip()

        except Exception:

            try:

                decoded = ast.literal_eval(
                    text
                )

                if isinstance(
                    decoded,
                    (
                        list,
                        tuple,
                        set,
                    ),
                ):

                    decoded = list(decoded)

                    text = (
                        str(decoded[0]).strip()
                        if decoded
                        else ""
                    )

                elif isinstance(
                    decoded,
                    str,
                ):

                    text = decoded.strip()

            except Exception:
                pass

        text = text.strip()

        while (
            text
            and text[0] in '[{"\''
        ):
            text = text[1:].strip()

        while (
            text
            and text[-1] in ']}"\''
        ):
            text = text[:-1].strip()

        if text == previous:
            break

    text = " ".join(
        text.split()
    )

    return text


def build_unique_interest_dataframe(
    top_interests: Any,
) -> pd.DataFrame:

    interest_scores = {}

    if isinstance(
        top_interests,
        dict,
    ):

        iterable = (
            top_interests.items()
        )

    elif isinstance(
        top_interests,
        list,
    ):

        iterable = (
            (
                raw_interest,
                1.0,
            )
            for raw_interest
            in top_interests
        )

    else:

        iterable = []

    for (
        raw_interest,
        raw_score,
    ) in iterable:

        interest = (
            normalize_interest_name(
                raw_interest
            )
        )

        if not interest:
            continue

        canonical_key = (
            interest.casefold()
        )

        if canonical_key not in interest_scores:

            interest_scores[
                canonical_key
            ] = {
                "Interest": interest,
                "Resident Signal": 0.0,
            }

        interest_scores[
            canonical_key
        ][
            "Resident Signal"
        ] += safe_float(
            raw_score
        )

    if not interest_scores:

        return pd.DataFrame(
            columns=[
                "Interest",
                "Resident Signal",
            ]
        )

    dataframe = pd.DataFrame(
        list(
            interest_scores.values()
        )
    )

    return (
        dataframe
        .sort_values(
            "Resident Signal",
            ascending=False,
        )
        .reset_index(
            drop=True
        )
    )


# ===========================================================
# Profile Card Renderer
# ===========================================================

def render_profile_card(
    container,
    label: str,
    value: str,
    description: str,
) -> None:

    html = textwrap.dedent(
        f"""
        <div class="profile-card">
            <div class="profile-label">{label}</div>
            <div class="profile-value">{value}</div>
            <div class="profile-description">{description}</div>
        </div>
        """
    ).strip()

    with container:

        st.html(html)


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
# Live Occupancy Helpers
# ===========================================================

def load_property_occupancy(
    property_name: str,
) -> Dict[str, Any]:

    try:

        occupancy = (
            get_current_occupancy(
                property_name=property_name
            )
        )

        if isinstance(
            occupancy,
            dict,
        ):
            return occupancy

    except Exception as error:

        st.warning(
            "Current occupancy could not be "
            "calculated from the resident timeline: "
            f"{error}"
        )

    return {}


def load_active_property_residents(
    property_name: str,
) -> pd.DataFrame:

    try:

        resident_timeline = (
            load_resident_export()
        )

        from datetime import datetime, timezone, timedelta
        ist = timezone(timedelta(hours=5, minutes=30))
        today = pd.Timestamp(datetime.now(ist).date()).normalize()

        active_residents = (
            get_active_residents(
                dataframe=resident_timeline,
                property_name=property_name,
                event_date=today,
            )
        )

        if isinstance(
            active_residents,
            pd.DataFrame,
        ):
            return active_residents.copy()

    except Exception as error:

        st.warning(
            "Active resident records could not "
            f"be loaded: {error}"
        )

    return pd.DataFrame()


def prepare_resident_display(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:

    if not isinstance(
        dataframe,
        pd.DataFrame,
    ):
        return pd.DataFrame()

    if dataframe.empty:
        return pd.DataFrame()

    display_dataframe = (
        dataframe.copy()
    )

    internal_columns = [
        column
        for column
        in display_dataframe.columns
        if str(column).startswith("_")
    ]

    display_dataframe = (
        display_dataframe.drop(
            columns=internal_columns,
            errors="ignore",
        )
    )

    return (
        display_dataframe
        .reset_index(
            drop=True
        )
    )


# ===========================================================
# Page Header
# ===========================================================

page_header(
    "👥 Property Profile",
    "Explore live occupancy, active resident intelligence "
    "and the property profiles used directly by the "
    "recommendation backend.",
)


# ===========================================================
# Load Application Data
# ===========================================================

try:

    application_data = (
        get_application_data()
    )

except Exception as error:

    st.error(
        "Unable to load property data: "
        f"{error}"
    )

    st.stop()


profiles = application_data.get(
    "profiles"
)


if not isinstance(
    profiles,
    dict,
) or not profiles:

    st.error(
        "No property profiles are available."
    )

    st.stop()


# ===========================================================
# Property Selection
# ===========================================================

property_names = sorted(
    profiles.keys()
)


recommended_property = (
    get_session_property(
        st.session_state
    )
)


default_index = 0


if recommended_property in property_names:

    default_index = (
        property_names.index(
            recommended_property
        )
    )


selected_property = st.selectbox(
    "Select Property",
    options=property_names,
    index=default_index,
)


profile = profiles.get(
    selected_property
)


if not isinstance(
    profile,
    dict,
):
    profile = {}


# ===========================================================
# Live Current Occupancy
# ===========================================================

current_occupancy = (
    load_property_occupancy(
        selected_property
    )
)


active_property_residents = (
    load_active_property_residents(
        selected_property
    )
)


property_residents = (
    prepare_resident_display(
        active_property_residents
    )
)


current_residents = safe_int(
    current_occupancy.get(
        "active_residents"
    )
)


total_capacity = safe_int(
    current_occupancy.get(
        "total_capacity"
    )
)


occupancy_percent = safe_float(
    current_occupancy.get(
        "occupancy_percent"
    )
)


available_beds = safe_int(
    current_occupancy.get(
        "available_beds"
    )
)


as_of_date = safe_text(
    current_occupancy.get(
        "as_of_date"
    )
)


# ===========================================================
# Profile Intelligence
# ===========================================================

average_age = safe_float(
    profile_value(
        profile,
        (
            "Average Age",
            "Avg Age",
        ),
        0.0,
    )
)


average_tenure = safe_float(
    profile_value(
        profile,
        (
            "Average Tenure",
            "Avg Tenure",
        ),
        0.0,
    )
)


# ===========================================================
# Live Occupancy Metrics
# ===========================================================

metric_row([
    {
        "title": "Current Residents",
        "value": f"{current_residents:,}",
    },
    {
        "title": "Current Occupancy",
        "value": f"{occupancy_percent:.1f}%",
    },
    {
        "title": "Total Capacity",
        "value": f"{total_capacity:,}",
    },
    {
        "title": "Available Beds",
        "value": f"{available_beds:,}",
    },
])


if as_of_date:

    st.caption(
        "Live occupancy calculated from the Warden "
        "move-in/move-out timeline as of "
        f"{as_of_date}."
    )


# ===========================================================
# Resident Profile Metrics
# ===========================================================

st.divider()


section_header(
    "Resident Profile"
)


metric_row([
    {
        "title": "Average Age",
        "value": (
            f"{average_age:.1f}"
            if average_age > 0
            else "N/A"
        ),
    },
    {
        "title": "Average Tenure",
        "value": (
            f"{average_tenure:.1f} days"
            if average_tenure > 0
            else "N/A"
        ),
    },
    {
        "title": "Occupancy Status",
        "value": (
            "High"
            if occupancy_percent >= 90.0
            else
            "Moderate"
            if occupancy_percent >= 70.0
            else
            "Low"
        ),
    },
])


# ===========================================================
# Community Intelligence
# ===========================================================

st.divider()


section_header(
    "Community Intelligence"
)


dominant_occupation = safe_text(
    profile_value(
        profile,
        (
            "Dominant Occupation",
            "Top Occupation",
        ),
        "Unknown",
    )
) or "Unknown"


dominant_age_band = safe_text(
    profile_value(
        profile,
        (
            "Dominant Age Band",
            "Age Band",
        ),
        "Unknown",
    )
) or "Unknown"


community_stage = safe_text(
    profile_value(
        profile,
        (
            "Community Stage",
            "Lifecycle Stage",
        ),
        "Unknown",
    )
) or "Unknown"


column_1, column_2, column_3 = (
    st.columns(3)
)


render_profile_card(
    column_1,
    "Dominant Occupation",
    dominant_occupation,
    (
        "The strongest occupational segment represented "
        "within this property profile."
    ),
)


render_profile_card(
    column_2,
    "Dominant Age Band",
    dominant_age_band,
    (
        "The primary age segment influencing event "
        "affinity and recommendation scoring."
    ),
)


render_profile_card(
    column_3,
    "Community Stage",
    community_stage,
    (
        "The community lifecycle context used by the "
        "recommendation intelligence pipeline."
    ),
)


# ===========================================================
# Interest Intelligence
# ===========================================================

st.divider()


section_header(
    "Top Resident Interests"
)


top_interests = profile_value(
    profile,
    (
        "Top Interests",
        "Interests",
    ),
    {},
)


interest_dataframe = (
    build_unique_interest_dataframe(
        top_interests
    )
)


if not interest_dataframe.empty:

    top_interest_dataframe = (
        interest_dataframe
        .head(10)
        .copy()
    )


    chart_dataframe = (
        top_interest_dataframe
        .set_index(
            "Interest"
        )
    )


    st.bar_chart(
        chart_dataframe
    )


    st.dataframe(
        top_interest_dataframe,
        width="stretch",
        hide_index=True,
    )


else:

    st.info(
        "No structured interest data is "
        "available for this property."
    )


# ===========================================================
# Current Active Resident Records
# ===========================================================

st.divider()


section_header(
    "Current Active Resident Records"
)


st.caption(
    "Only residents who are active today are shown. "
    "Residents who have already moved out and residents "
    "whose move-in date is still in the future are excluded."
)


if property_residents.empty:

    st.info(
        "No active resident records were found "
        "for the selected property today."
    )


else:

    history_table(
        property_residents
    )