"""
===========================================================
TribeIQ Log Event Page
===========================================================

Production frontend integration for completed event outcomes.

Responsibilities:
1. Log completed event performance
2. Save outcomes to the existing event history CSV
3. Send outcomes to the continuous-learning backend
4. Connect recommendations to future learning signals
5. Preserve occupancy and attendance predictions
6. Calculate prediction error from actual outcomes
7. Display live Major and Minor recommendation context
===========================================================
"""

from __future__ import annotations

import html
import sys
import textwrap
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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

DATA_DIR = (
    PROJECT_ROOT
    / "data"
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

from learning.signal_store import log_outcome

from ui_data_bridge import (
    get_session_property,
    get_session_result,
    load_application_data,
)
from utils.schema_utils import safe_get_column, safe_status_column, safe_numeric_column, safe_column_exists

from ui.components import (
    page_header,
)


# ===========================================================
# Session Keys
# ===========================================================

DATED_RESULT_KEY = (
    "tribeiq_dated_recommendation_result"
)

LAST_LOGGED_EVENT_KEY = (
    "tribeiq_last_logged_event"
)


# ===========================================================
# Helpers
# ===========================================================

def safe_text(
    value: Any,
    default: str = "",
) -> str:

    if value is None:
        return default

    try:

        if pd.isna(value):
            return default

    except (
        TypeError,
        ValueError,
    ):
        pass

    text = str(value).strip()

    return text if text else default


def safe_html(
    value: Any,
    default: str = "",
) -> str:

    return html.escape(
        safe_text(
            value,
            default,
        ),
        quote=True,
    )


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


def get_star_string(val: float) -> str:
    """
    Generate a 5-star rating representation supporting quarter, half, and full stars.
    """
    try:
        val = float(val)
    except (TypeError, ValueError):
        val = 0.0
    if val <= 0.0:
        return "☆☆☆☆☆ (0.00)"
    if val >= 5.0:
        return "★★★★★ (5.00)"
        
    full = int(val)
    frac = val - full
    frac_sym = ""
    if frac == 0.25:
        frac_sym = "¼"
    elif frac == 0.5:
        frac_sym = "½"
    elif frac == 0.75:
        frac_sym = "¾"
        
    stars = "★" * full
    if frac_sym:
        stars += frac_sym
    
    empty = 5 - full - (1 if frac > 0 else 0)
    stars += "☆" * empty
    return f"{stars} ({val:.2f})"


def safe_dict(
    value: Any,
) -> Dict[str, Any]:

    if isinstance(value, dict):
        return value

    return {}


def safe_list(
    value: Any,
) -> List[Any]:

    if isinstance(value, list):
        return value

    return []


def normalize_column_name(
    value: Any,
) -> str:

    return (
        safe_text(value)
        .lower()
        .replace("_", " ")
        .replace("-", " ")
    )


def normalize_event_name(
    value: Any,
) -> str:

    return (
        safe_text(value)
        .casefold()
        .strip()
    )


def render_html(
    markup: str,
) -> None:

    clean_markup = textwrap.dedent(
        markup
    ).strip()

    st.html(clean_markup)


def calculate_success_score(
    attendance_percent: float,
    feedback_score: float,
    budget_planned: float,
    budget_spent: float,
) -> float:

    attendance_score = max(
        0.0,
        min(
            safe_float(
                attendance_percent
            ),
            100.0,
        ),
    )

    feedback_score_100 = (
        max(
            0.0,
            min(
                safe_float(
                    feedback_score
                ),
                5.0,
            ),
        )
        / 5.0
    ) * 100.0

    if budget_planned > 0:

        budget_ratio = (
            budget_spent
            / budget_planned
        )

        if budget_ratio <= 1.0:

            budget_score = 100.0

        else:

            overspend = (
                budget_ratio
                - 1.0
            )

            budget_score = max(
                0.0,
                100.0
                - (
                    overspend
                    * 100.0
                ),
            )

    else:

        budget_score = 100.0

    success_score = (
        attendance_score
        * 0.40
        + feedback_score_100
        * 0.40
        + budget_score
        * 0.20
    )

    return round(
        max(
            0.0,
            min(
                success_score,
                100.0,
            ),
        ),
        2,
    )


# ===========================================================
# Event History Discovery
# ===========================================================

def is_event_history(
    dataframe: pd.DataFrame,
) -> bool:

    if not isinstance(
        dataframe,
        pd.DataFrame,
    ):
        return False

    if dataframe.empty:
        return False

    columns = {
        normalize_column_name(
            column
        )
        for column
        in dataframe.columns
    }

    has_event = bool(
        columns.intersection({
            "event name",
            "event",
            "name",
        })
    )

    has_property = bool(
        columns.intersection({
            "property",
            "property name",
        })
    )

    has_outcome = bool(
        columns.intersection({
            "attendance %",
            "attendance",
            "actual attendance",
            "average feedback",
            "avg feedback",
            "feedback",
            "success score",
        })
    )

    return (
        has_event
        and has_property
        and has_outcome
    )


def find_history_file() -> Optional[Path]:

    if not DATA_DIR.exists():
        return None

    preferred_names = (
        "event_history.csv",
        "events_history.csv",
        "historical_events.csv",
        "history.csv",
        "event_log.csv",
    )

    csv_files = sorted(
        DATA_DIR.rglob(
            "*.csv"
        )
    )

    for preferred_name in preferred_names:

        for path in csv_files:

            if (
                path.name.lower()
                == preferred_name
            ):
                return path

    for path in csv_files:

        try:

            dataframe = pd.read_csv(
                path
            )

        except Exception:
            continue

        if is_event_history(
            dataframe
        ):
            return path

    return None


def get_history_output_path() -> Path:

    existing_path = (
        find_history_file()
    )

    if existing_path is not None:
        return existing_path

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    return (
        DATA_DIR
        / "event_history.csv"
    )


# ===========================================================
# History Persistence
# ===========================================================

def save_history_record(
    record: Dict[str, Any],
) -> Tuple[bool, str]:

    output_path = (
        get_history_output_path()
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    new_row = pd.DataFrame([
        record
    ])

    try:

        if output_path.exists():

            try:

                history = pd.read_csv(
                    output_path
                )

            except Exception:

                history = pd.DataFrame()

            if history.empty:

                updated_history = new_row

            else:

                all_columns = list(
                    dict.fromkeys(
                        list(
                            history.columns
                        )
                        + list(
                            new_row.columns
                        )
                    )
                )

                history = history.reindex(
                    columns=all_columns
                )

                new_row = new_row.reindex(
                    columns=all_columns
                )

                updated_history = pd.concat(
                    [
                        history,
                        new_row,
                    ],
                    ignore_index=True,
                )

        else:

            updated_history = new_row

        updated_history.to_csv(
            output_path,
            index=False,
        )

        try:

            display_path = str(
                output_path.relative_to(
                    PROJECT_ROOT
                )
            )

        except ValueError:

            display_path = str(
                output_path
            )

        return (
            True,
            display_path,
        )

    except Exception as error:

        return (
            False,
            safe_text(error),
        )


# ===========================================================
# Recommendation Context
# ===========================================================

def get_active_recommendation_result() -> Dict[str, Any]:

    dated_result = (
        st.session_state.get(
            DATED_RESULT_KEY
        )
    )

    if (
        isinstance(dated_result, dict)
        and dated_result
    ):
        return dated_result

    normal_result = (
        get_session_result(
            st.session_state
        )
    )

    if (
        isinstance(normal_result, dict)
        and normal_result
    ):
        return normal_result

    return {}


def get_recommended_events(
    result: Any,
) -> List[Dict[str, Any]]:

    if not isinstance(
        result,
        dict,
    ):
        return []

    events = []
    seen_names = set()

    major_event = result.get(
        "major_event"
    )

    if isinstance(
        major_event,
        dict,
    ):

        event = dict(
            major_event
        )

        event[
            "recommendation_type"
        ] = "Major"

        event_name = (
            normalize_event_name(
                event.get(
                    "event_name"
                )
            )
        )

        if event_name:

            seen_names.add(
                event_name
            )

            events.append(
                event
            )

    minor_events = safe_list(
        result.get(
            "minor_events"
        )
    )

    for candidate in minor_events:

        if not isinstance(
            candidate,
            dict,
        ):
            continue

        event = dict(
            candidate
        )

        event_name = (
            normalize_event_name(
                event.get(
                    "event_name"
                )
            )
        )

        if not event_name:
            continue

        if event_name in seen_names:
            continue

        seen_names.add(
            event_name
        )

        event[
            "recommendation_type"
        ] = "Minor"

        events.append(
            event
        )

    return events


def find_recommended_event(
    event_name: str,
    recommended_events: List[
        Dict[str, Any]
    ],
) -> Optional[Dict[str, Any]]:

    target = (
        normalize_event_name(
            event_name
        )
    )

    for event in recommended_events:

        candidate_name = (
            normalize_event_name(
                event.get(
                    "event_name"
                )
            )
        )

        if candidate_name == target:
            return event

    return None


# ===========================================================
# Recommendation Context Rendering
# ===========================================================

def render_recommendation_context(
    recommended_events: List[
        Dict[str, Any]
    ],
    dated_context_active: bool,
) -> None:

    if not recommended_events:
        return

    major_events = [
        event
        for event in recommended_events
        if safe_text(
            event.get(
                "recommendation_type"
            )
        ) == "Major"
    ]

    minor_events = [
        event
        for event in recommended_events
        if safe_text(
            event.get(
                "recommendation_type"
            )
        ) == "Minor"
    ]

    context_status = (
        "Recommendation and date-prediction data are connected."
        if dated_context_active
        else
        "Recommendation data are connected."
    )

    context_status = safe_html(
        context_status
    )

    st.info(f"**LIVE RECOMMENDATION CONTEXT**\n\n### {context_status}\n\nSelect one of the recommended events below. The saved real outcome will feed the continuous-learning and attendance-prediction systems.")

    if major_events:

        major_event = major_events[0]

        render_recommendation_context_card(
            event=major_event,
            label="Major Event",
        )

    for index, event in enumerate(
        minor_events,
        start=1,
    ):

        render_recommendation_context_card(
            event=event,
            label=f"Minor Event {index}",
        )


def render_recommendation_context_card(
    event: Dict[str, Any],
    label: str,
) -> None:

    if not isinstance(
        event,
        dict,
    ):
        return

    event_name = safe_html(
        event.get(
            "event_name"
        ),
        "Unknown Event",
    )

    category = safe_html(
        event.get(
            "category"
        ),
        "Uncategorised",
    )

    recommendation_type = safe_html(
        label
    )

    final_score = safe_float(
        event.get(
            "final_score"
        )
    )

    formatted_event_date = safe_html(
        event.get(
            "formatted_event_date"
        ),
        safe_text(
            event.get(
                "event_date"
            ),
            "",
        ),
    )

    predicted_attendance = safe_int(
        event.get(
            "predicted_attendance"
        )
    )

    active_residents = safe_int(
        event.get(
            "active_residents"
        )
    )

    occupancy_percent = safe_float(
        event.get(
            "occupancy_percent"
        )
    )

    has_date_data = bool(
        formatted_event_date
        or "predicted_attendance" in event
        or "active_residents" in event
        or "occupancy_percent" in event
    )

    if has_date_data:
        date_value = (
            formatted_event_date
            if formatted_event_date
            else "Date not assigned"
        )
        with st.container(border=True):
            st.markdown(f"**{recommendation_type}**")
            st.markdown(f"#### {event_name}")
            st.caption(category)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Score", f"{final_score:.1f}")
            c2.metric("Date", date_value)
            c3.metric("Occupancy", f"{occupancy_percent:.1f}%")
            c4.metric("Expected", f"{predicted_attendance:,}")
            st.caption(f"Predicted active residents: {active_residents:,}")
    else:
        with st.container(border=True):
            st.markdown(f"**{recommendation_type}**")
            st.markdown(f"#### {event_name}")
            st.caption(f"{category} · Recommendation score: {final_score:.1f}")


# ===========================================================
# Event Catalogue Helpers
# ===========================================================

def find_event_name_column(
    dataframe: pd.DataFrame,
) -> Optional[str]:

    if not isinstance(
        dataframe,
        pd.DataFrame,
    ):
        return None

    for column in (
        "Event Name",
        "event_name",
        "Event",
        "event",
        "Name",
        "name",
    ):

        if column in dataframe.columns:
            return column

    return None


def get_catalogue_event_details(
    event_name: str,
    events_dataframe: pd.DataFrame,
    event_name_column: Optional[str],
) -> Dict[str, str]:

    details = {
        "event_id": "",
        "category": "",
    }

    if not isinstance(
        events_dataframe,
        pd.DataFrame,
    ):
        return details

    if events_dataframe.empty:
        return details

    if event_name_column is None:
        return details

    target = (
        normalize_event_name(
            event_name
        )
    )

    normalized_names = (
        events_dataframe[
            event_name_column
        ]
        .astype(str)
        .map(
            normalize_event_name
        )
    )

    matching_rows = (
        events_dataframe[
            normalized_names
            == target
        ]
    )

    if matching_rows.empty:
        return details

    event_row = (
        matching_rows.iloc[0]
    )

    for column in (
        "Event ID",
        "event_id",
        "ID",
        "id",
    ):

        if column in matching_rows.columns:

            details[
                "event_id"
            ] = safe_text(
                event_row.get(
                    column
                )
            )

            break

    for column in (
        "Category",
        "category",
        "Event Category",
        "event_category",
    ):

        if column in matching_rows.columns:

            details[
                "category"
            ] = safe_text(
                event_row.get(
                    column
                )
            )

            break

    return details


# ===========================================================
# Prediction Context Helpers
# ===========================================================

def extract_prediction_context(
    recommendation: Optional[
        Dict[str, Any]
    ],
) -> Dict[str, Any]:

    if not isinstance(
        recommendation,
        dict,
    ):

        return {
            "predicted_event_date": "",
            "predicted_weekday": "",
            "total_capacity": 0,
            "predicted_active_residents": 0,
            "predicted_occupancy_percent": 0.0,
            "predicted_turnout_rate": 0.0,
            "predicted_attendance": 0,
            "attendance_confidence_score": 0.0,
            "attendance_confidence": "",
            "has_prediction": False,
        }

    predicted_attendance = safe_int(
        recommendation.get(
            "predicted_attendance"
        )
    )

    predicted_active_residents = safe_int(
        recommendation.get(
            "active_residents"
        )
    )

    has_prediction = bool(
        (
            "predicted_attendance"
            in recommendation
        )
        or (
            "active_residents"
            in recommendation
        )
        or (
            "occupancy_percent"
            in recommendation
        )
    )

    return {
        "predicted_event_date":
            safe_text(
                recommendation.get(
                    "event_date"
                )
            ),

        "predicted_weekday":
            safe_text(
                recommendation.get(
                    "weekday"
                )
            ),

        "total_capacity":
            safe_int(
                recommendation.get(
                    "total_capacity"
                )
            ),

        "predicted_active_residents":
            predicted_active_residents,

        "predicted_occupancy_percent":
            safe_float(
                recommendation.get(
                    "occupancy_percent"
                )
            ),

        "predicted_turnout_rate":
            safe_float(
                recommendation.get(
                    "predicted_turnout_rate"
                )
            ),

        "predicted_attendance":
            predicted_attendance,

        "attendance_confidence_score":
            safe_float(
                recommendation.get(
                    "attendance_confidence_score"
                )
            ),

        "attendance_confidence":
            safe_text(
                recommendation.get(
                    "attendance_confidence"
                )
            ),

        "has_prediction":
            has_prediction,
    }


def calculate_prediction_error(
    actual_attendance: int,
    predicted_attendance: int,
    has_prediction: bool,
) -> Dict[str, Any]:

    if not has_prediction:

        return {
            "error_count": "",
            "absolute_error": "",
            "error_percent": "",
        }

    error_count = (
        actual_attendance
        - predicted_attendance
    )

    absolute_error = abs(
        error_count
    )

    if actual_attendance > 0:

        error_percent = (
            absolute_error
            / actual_attendance
        ) * 100.0

    elif predicted_attendance == 0:

        error_percent = 0.0

    else:

        error_percent = 100.0

    return {
        "error_count":
            int(error_count),

        "absolute_error":
            int(absolute_error),

        "error_percent":
            round(
                error_percent,
                2,
            ),
    }


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
# Page Header
# ===========================================================

page_header(
    "📝 Log Event Outcome",
    "Record real event performance and send the outcome "
    "directly into TribeIQ's continuous-learning and "
    "attendance-prediction systems.",
)


# ===========================================================
# Load Data
# ===========================================================

try:

    application_data = (
        get_application_data()
    )

except Exception as error:

    st.error(
        "Unable to load application data: "
        f"{error}"
    )

    st.stop()


profiles = application_data.get(
    "profiles"
)

if not isinstance(
    profiles,
    dict,
):
    profiles = {}


events_dataframe = application_data.get(
    "events"
)

if not isinstance(
    events_dataframe,
    pd.DataFrame,
):
    events_dataframe = pd.DataFrame()


if not profiles:

    st.error(
        "No property profiles are available."
    )

    st.stop()


# ===========================================================
# Shared Recommendation Context
# ===========================================================

recommendation_result = (
    get_active_recommendation_result()
)

recommended_property = (
    get_session_property(
        st.session_state
    )
)

recommended_events = (
    get_recommended_events(
        recommendation_result
    )
)


# ===========================================================
# Property Options
# ===========================================================

property_names = sorted(
    profiles.keys()
)

default_property_index = 0

if recommended_property in property_names:

    default_property_index = (
        property_names.index(
            recommended_property
        )
    )


# ===========================================================
# Event Options
# ===========================================================

event_name_column = (
    find_event_name_column(
        events_dataframe
    )
)

catalogue_event_names = []

if event_name_column is not None:

    catalogue_event_names = sorted({
        safe_text(value)
        for value
        in events_dataframe[
            event_name_column
        ].dropna().tolist()
        if safe_text(value)
    })


recommended_event_names = [
    safe_text(
        event.get(
            "event_name"
        )
    )
    for event
    in recommended_events
    if safe_text(
        event.get(
            "event_name"
        )
    )
]


event_names = list(
    dict.fromkeys(
        recommended_event_names
        + catalogue_event_names
    )
)


if not event_names:

    st.error(
        "No events are available to log."
    )

    st.stop()


# ===========================================================
# Recommendation Context Display
# ===========================================================

if recommended_events:

    dated_context_active = isinstance(
        st.session_state.get(
            DATED_RESULT_KEY
        ),
        dict,
    )

    render_recommendation_context(
        recommended_events=(
            recommended_events
        ),
        dated_context_active=(
            dated_context_active
        ),
    )

else:

    st.info(
        "No active recommendation context is available. "
        "You can still log an event manually, or generate "
        "recommendations first to connect the outcome to "
        "TribeIQ's recommendation intelligence."
    )


# ===========================================================
# Event Outcome Form
# ===========================================================

try:
    container = st.container()

    st.markdown("### 📋 1. Event Details")
    detail_col1, detail_col2 = st.columns(2)
    with detail_col1:
        selected_property = st.selectbox(
            "Property",
            options=property_names,
            index=default_property_index,
            help="The specific co-living property where the event was hosted.",
        )
        event_date = st.date_input(
            "Event Date",
            value=date.today(),
            help="The date on which this event took place.",
        )
    with detail_col2:
        selected_event_name = st.selectbox(
            "Event",
            options=event_names,
            help="The name of the event that was executed.",
        )
        import datetime
        time_col1, time_col2 = st.columns(2)
        with time_col1:
            event_start_time = st.time_input(
                "Event Start Time",
                value=datetime.time(18, 0),
                help="The time when the event was scheduled to start."
            )
        with time_col2:
            event_end_time = st.time_input(
                "Event End Time",
                value=datetime.time(20, 0),
                help="The time when the event was scheduled to end."
            )

    st.markdown("### 👥 2. Turnout & Attendance")
    attend_col1, attend_col2 = st.columns(2)
    with attend_col1:
        actual_attendance = st.number_input(
            "Actual Attendance",
            min_value=0,
            value=0,
            step=1,
            help="The total physical headcount of residents who checked in or attended the event.",
        )
    with attend_col2:
        feedback_score = st.selectbox(
            "Feedback Rating",
            options=[i * 0.25 for i in range(21)],  # 0.00 to 5.00 in steps of 0.25
            index=16,  # Default to 4.00
            format_func=get_star_string,
            help="Select the average satisfaction rating given by the attending residents.",
        )
    st.info("Attendance Percentage: Automatically calculated on save based on actual attendance and active resident timeline.")

    st.markdown("### 💸 3. Budget & Financials")
    budget_col1, budget_col2 = st.columns(2)
    with budget_col1:
        estimated_budget = st.number_input(
            "Estimated Budget (INR)",
            min_value=0.0,
            value=0.0,
            step=100.0,
            help="The budget initially approved/allocated for organizing this event."
        )
    with budget_col2:
        actual_budget = st.number_input(
            "Actual Budget (INR)",
            min_value=0.0,
            value=0.0,
            step=100.0,
            help="The total final cost incurred to run the event."
        )

    st.markdown("### 🎫 4. Ticketing Details")
    is_ticketed = st.checkbox("Ticketed Event", help="Check this box if residents had to purchase tickets to attend.")
    
    ticket_price = 0.0
    tickets_available = 0
    tickets_sold = 0
    revenue_collected = 0.0
    
    if is_ticketed:
        ticket_col1, ticket_col2 = st.columns(2)
        with ticket_col1:
            ticket_price = st.number_input(
                "Ticket Price (INR)",
                min_value=0.0,
                value=0.0,
                step=10.0,
                help="Price per ticket sold to residents."
            )
            tickets_available = st.number_input(
                "Tickets Available",
                min_value=0,
                value=0,
                step=1,
                help="Total number of tickets made available for sale."
            )
        with ticket_col2:
            tickets_sold = st.number_input(
                "Tickets Sold",
                min_value=0,
                value=0,
                step=1,
                help="Total number of tickets actually purchased by residents."
            )
            revenue_collected = ticket_price * tickets_sold
            st.number_input(
                "Revenue Collected (auto-calculated)",
                min_value=0.0,
                value=float(revenue_collected),
                disabled=True,
                help="Total ticketing revenue collected (calculated as Ticket Price * Tickets Sold)."
            )

    st.markdown("### 🏪 5. Hired Vendors")
    vendor_used = st.checkbox("Vendor Used", help="Check this box if external vendors were hired.")
    
    vendors_data_list = []
    vendor_name = "None"
    
    if vendor_used:
        try:
            from integrations.vendor_db import load_vendors
            vendors_df = load_vendors()
            
            # Schema-safe columns
            status_col = safe_status_column(vendors_df) or "Active / Inactive Status"
            name_col = safe_get_column(vendors_df, ["Vendor Name", "Name"]) or "Vendor Name"
            id_col = safe_get_column(vendors_df, ["Vendor ID", "ID"]) or "Vendor ID"
            base_col = safe_get_column(vendors_df, ["Base Amount", "Cost"]) or "Base Amount"
            gst_pct_col = safe_get_column(vendors_df, ["GST Percentage", "GST %"]) or "GST Percentage"
            cat_col = safe_get_column(vendors_df, ["Vendor Category", "Category"]) or "Vendor Category"
            
            active_vendors = vendors_df[vendors_df[status_col].astype(str).str.strip().str.lower() == "active"] if status_col in vendors_df.columns else vendors_df
            vendor_options = [f"{row[name_col]} [{row[id_col]}]" for _, row in active_vendors.iterrows()] if name_col in active_vendors.columns and id_col in active_vendors.columns else []
        except Exception:
            vendor_options = []
            
        selected_vendor_lbls = st.multiselect(
            "Select Vendors Hired",
            options=vendor_options,
            help="Choose one or more vendors from the central database."
        )
        
        if selected_vendor_lbls:
            for lbl in selected_vendor_lbls:
                st.markdown(f"**Vendor Details: {lbl}**")
                c_cost, c_gst = st.columns(2)
                with c_cost:
                    v_id = lbl.split("[")[-1].rstrip("]") if "[" in lbl else "other"
                    db_row = vendors_df[vendors_df[id_col] == v_id].iloc[0] if v_id != "other" and not vendors_df.empty and id_col in vendors_df.columns else None
                    db_base = float(db_row[base_col]) if db_row is not None and base_col in db_row else 0.0
                    db_gst_pct = int(db_row[gst_pct_col]) if db_row is not None and gst_pct_col in db_row else 18
                    
                    base_cost = st.number_input(f"Base Cost for {lbl.split(' [')[0]} (INR)", min_value=0.0, value=db_base, key=f"base_cost_{v_id}")
                with c_gst:
                    gst_pct = st.selectbox(f"GST % for {lbl.split(' [')[0]}", options=[12, 18], index=([12, 18].index(db_gst_pct) if db_gst_pct in [12, 18] else 1), key=f"gst_pct_{v_id}")
                
                gst_amt = round((base_cost * gst_pct) / 100.0, 2)
                final_cost = round(base_cost + gst_amt, 2)
                
                vendors_data_list.append({
                    "vendor_id": v_id,
                    "name": lbl.split(" [")[0],
                    "category": db_row[cat_col] if db_row is not None and cat_col in db_row else "Miscellaneous",
                    "base_cost": base_cost,
                    "gst_percent": gst_pct,
                    "gst_amount": gst_amt,
                    "final_cost": final_cost
                })
            vendor_name = ", ".join([v["name"] for v in vendors_data_list])

    st.markdown("### 🏪 6. Stall Space Rentals")
    has_stalls = st.checkbox("This event includes stalls", help="Check this box if this event featured food festival stalls, popups, or booths.")
    stalls_data_list = []
    
    if has_stalls:
        try:
            from integrations.vendor_db import load_vendors
            vendors_df = load_vendors()
            active_vendors = vendors_df[vendors_df["Active / Inactive Status"] == "Active"]
            vendor_options = [f"{row['Vendor Name']} [{row['Vendor ID']}]" for _, row in active_vendors.iterrows()]
        except Exception:
            vendor_options = []
            
        num_stalls = st.number_input("Number of Stalls", min_value=1, value=1, step=1)
        for i in range(int(num_stalls)):
            st.markdown(f"**Stall #{i+1} Details**")
            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1:
                stall_vendor = st.selectbox(f"Vendor for Stall #{i+1}", options=vendor_options, key=f"stall_vendor_{i}")
                v_id = stall_vendor.split("[")[-1].rstrip("]") if "[" in stall_vendor else "other"
                
                v_row = vendors_df[vendors_df["Vendor ID"] == v_id].iloc[0] if v_id != "other" and not vendors_df.empty else None
                v_name = v_row["Vendor Name"] if v_row is not None else "Other"
                v_cat = v_row["Vendor Category"] if v_row is not None else "Miscellaneous"
                
                stall_name = st.text_input(f"Stall #{i+1} Name", value=f"{v_name} Stall", key=f"stall_name_{i}")
            with col_s2:
                from integrations.stall_db import DEFAULT_STALL_CATEGORIES
                try:
                    cat_idx = DEFAULT_STALL_CATEGORIES.index(v_cat)
                except Exception:
                    cat_idx = 0
                stall_cat = st.selectbox(f"Stall #{i+1} Category", options=DEFAULT_STALL_CATEGORIES, index=cat_idx, key=f"stall_cat_{i}")
                stall_size = st.selectbox(f"Stall #{i+1} Size", options=["Small", "Medium", "Large"], index=1, key=f"stall_size_{i}")
            with col_s3:
                rental_amt = st.number_input(f"Rental Amount for Stall #{i+1} (INR)", min_value=0.0, value=0.0, step=100.0, key=f"stall_rental_{i}")
                stall_status = st.selectbox(f"Stall #{i+1} Status", options=["Reserved", "Confirmed", "Cancelled", "Completed"], index=1, key=f"stall_status_{i}")
            
            stall_notes = st.text_input(f"Notes for Stall #{i+1}", key=f"stall_notes_{i}")
            
            stalls_data_list.append({
                "vendor_id": v_id,
                "stall_name": stall_name,
                "stall_category": stall_cat,
                "rental_amount": rental_amt,
                "stall_size": stall_size,
                "status": stall_status,
                "notes": stall_notes
            })
            
        tot_stall_rev = sum([s["rental_amount"] for s in stalls_data_list])
        st.write(f"**Total Stall Revenue (auto-calculated):** INR {tot_stall_rev}")

    st.markdown("### 📦 7. Procured Materials")
    requires_materials = st.checkbox("This event requires materials", help="Check this box if this event requires decorations, staging, branding, or equipment.")
    materials_data_list = []
    
    if requires_materials:
        try:
            from integrations.vendor_db import load_vendors
            vendors_df = load_vendors()
            active_vendors = vendors_df[vendors_df["Active / Inactive Status"] == "Active"]
            vendor_options = ["None"] + [f"{row['Vendor Name']} [{row['Vendor ID']}]" for _, row in active_vendors.iterrows()]
        except Exception:
            vendor_options = ["None"]
            
        num_materials = st.number_input("Number of Materials", min_value=1, value=1, step=1)
        for i in range(int(num_materials)):
            st.markdown(f"**Material #{i+1} Details**")
            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1:
                mat_name = st.text_input(f"Material Name #{i+1}", key=f"mat_name_{i}")
                from integrations.material_db import DEFAULT_MATERIAL_CATEGORIES
                mat_cat = st.selectbox(f"Material Category #{i+1}", options=DEFAULT_MATERIAL_CATEGORIES, key=f"mat_cat_{i}")
            with col_m2:
                qty = st.number_input(f"Quantity Required #{i+1}", min_value=1, value=1, step=1, key=f"mat_qty_{i}")
                unit = st.text_input(f"Unit (e.g. Pcs, Box, kg) #{i+1}", value="Pcs", key=f"mat_unit_{i}")
                mat_vendor = st.selectbox(f"Vendor (Optional) #{i+1}", options=vendor_options, key=f"mat_vendor_{i}")
                v_id = mat_vendor.split("[")[-1].rstrip("]") if "[" in mat_vendor else "None"
            with col_m3:
                unit_cost = st.number_input(f"Unit Cost (INR) #{i+1}", min_value=0.0, value=0.0, step=10.0, key=f"mat_unit_cost_{i}")
                from integrations.material_db import PROCUREMENT_STATUS_BADGES
                mat_status = st.selectbox(f"Procurement Status #{i+1}", options=list(PROCUREMENT_STATUS_BADGES.keys()), index=0, key=f"mat_status_{i}")
            
            mat_notes = st.text_input(f"Notes for Material #{i+1}", key=f"mat_notes_{i}")
            
            materials_data_list.append({
                "name": mat_name,
                "category": mat_cat,
                "quantity": qty,
                "unit": unit,
                "vendor_id": v_id,
                "unit_cost": unit_cost,
                "status": mat_status,
                "notes": mat_notes
            })
            
        tot_proc_cost = sum([m["quantity"] * m["unit_cost"] for m in materials_data_list])
        st.write(f"**Total Procurement Cost (auto-calculated):** INR {tot_proc_cost}")

    st.markdown("### 📝 8. Operational Learnings & Notes")
    notes = st.text_area(
        "Notes",
        placeholder="Add observations, resident reactions or operational notes...",
        help="Any qualitative observations, reactions, or logistics notes about the event outcome."
    )
    learnings = st.text_area(
        "Learnings",
        placeholder="What went well? What can be improved for future events?",
        help="Key takeaways or recommendations for improvement in future community events."
    )

    submitted = st.button(
        "Save Event Outcome",
        type="primary",
        use_container_width=True,
    )
except Exception as e:
    submitted = False
    st.warning("⚠ Unable to load this widget.")
    with st.expander("Optional details"):
        st.write(str(e))


# ===========================================================
# Save Outcome
# ===========================================================

if submitted:

    # Fetch current time in India Standard Time
    import pytz
    ist_tz = pytz.timezone("Asia/Kolkata")
    now_ist = datetime.datetime.now(ist_tz)
    logged_timestamp = now_ist.isoformat()
    logged_date = now_ist.date().isoformat()
    logged_time = now_ist.time().strftime("%H:%M:%S")

    selected_recommendation = (
        find_recommended_event(
            event_name=(
                selected_event_name
            ),
            recommended_events=(
                recommended_events
            ),
        )
    )

    if isinstance(
        selected_recommendation,
        dict,
    ):
        event_id = safe_text(selected_recommendation.get("event_id"))
        category = safe_text(selected_recommendation.get("category"))
        recommendation_type = safe_text(selected_recommendation.get("recommendation_type"))
        recommendation_score = safe_float(selected_recommendation.get("final_score"))
    else:
        event_id = ""
        category = ""
        recommendation_type = "manual"
        recommendation_score = 0.0

    catalogue_details = (
        get_catalogue_event_details(
            event_name=selected_event_name,
            events_dataframe=events_dataframe,
            event_name_column=event_name_column,
        )
    )

    if not event_id:
        event_id = safe_text(catalogue_details.get("event_id"))

    if not category:
        category = safe_text(catalogue_details.get("category"))

    if not event_id:
        event_id = (
            selected_event_name
            .strip()
            .lower()
            .replace(" ", "-")
        )

    # -------------------------------------------------------
    # Prediction Context Lookup
    # -------------------------------------------------------
    prediction_context = extract_prediction_context(selected_recommendation)
    predicted_attendance = safe_int(prediction_context.get("predicted_attendance"))
    has_prediction = bool(prediction_context.get("has_prediction"))

    prediction_error = (
        calculate_prediction_error(
            actual_attendance=int(actual_attendance),
            predicted_attendance=predicted_attendance,
            has_prediction=has_prediction,
        )
    )

    # Calculate Turnout Rate Automatically
    from occupancy_forecaster import load_resident_export, get_active_residents
    
    residents_timeline = load_resident_export()
    event_timestamp = pd.Timestamp(event_date).normalize()
    active_res = get_active_residents(
        dataframe=residents_timeline,
        property_name=selected_property,
        event_date=event_timestamp
    )
    active_count = len(active_res)
    
    if active_count > 0:
        attendance_percent = (float(actual_attendance) / float(active_count)) * 100.0
        attendance_percent = min(attendance_percent, 100.0)
    else:
        attendance_percent = 0.0

    # -------------------------------------------------------
    # Success Score
    # -------------------------------------------------------

    success_score = (
        calculate_success_score(
            attendance_percent=(
                attendance_percent
            ),
            feedback_score=(
                feedback_score
            ),
            budget_planned=(
                estimated_budget
            ),
            budget_spent=(
                actual_budget
            ),
        )
    )

    # -------------------------------------------------------
    # Production History Record
    # -------------------------------------------------------

    import re
    url_pattern = re.compile(
        r'(https?://[^\s<>"]+|www\.[^\s<>"]+|drive\.google\.com/[^\s<>"]+)'
    )
    link_match = url_pattern.search(notes)
    image_data_link = link_match.group(0) if link_match else ""

    import uuid
    unique_event_id = f"{event_id}-{uuid.uuid4().hex[:8]}" if event_id else uuid.uuid4().hex[:12]

    history_record = {
        "Date":
            event_date.isoformat(),

        "Property":
            selected_property,

        "Event ID":
            unique_event_id,

        "Event Name":
            selected_event_name,

        "Category":
            category,

        "Attendance %":
            round(
                attendance_percent,
                2,
            ),

        "Actual Attendance":
            int(
                actual_attendance
            ),

        "Average Feedback":
            round(
                feedback_score,
                2,
            ),

        "Success Score":
            success_score,

        "Budget Planned":
            round(
                estimated_budget,
                2,
            ),

        "Budget Spent":
            round(
                actual_budget,
                2,
            ),

        "Recommendation Type":
            recommendation_type,

        "Recommendation Score":
            round(
                recommendation_score,
                4,
            ),

        "Predicted Event Date":
            prediction_context.get(
                "predicted_event_date"
            ),

        "Predicted Weekday":
            prediction_context.get(
                "predicted_weekday"
            ),

        "Total Capacity":
            prediction_context.get(
                "total_capacity"
            ),

        "Predicted Active Residents":
            prediction_context.get(
                "predicted_active_residents"
            ),

        "Predicted Occupancy %":
            round(
                safe_float(
                    prediction_context.get(
                        "predicted_occupancy_percent"
                    )
                ),
                2,
            ),

        "Predicted Turnout Rate":
            round(
                safe_float(
                    prediction_context.get(
                        "predicted_turnout_rate"
                    )
                ),
                2,
            ),

        "Predicted Attendance":
            predicted_attendance
            if has_prediction
            else "",

        "Attendance Confidence Score":
            round(
                safe_float(
                    prediction_context.get(
                        "attendance_confidence_score"
                    )
                ),
                2,
            ),

        "Attendance Confidence":
            prediction_context.get(
                "attendance_confidence"
            ),

        "Attendance Prediction Error":
            prediction_error.get(
                "error_count"
            ),

        "Absolute Attendance Error":
            prediction_error.get(
                "absolute_error"
            ),

        "Attendance Error %":
            prediction_error.get(
                "error_percent"
            ),

        "Notes":
            safe_text(
                notes
            ),

        "Image Data":
            image_data_link,

        # New Redesigned Fields
        "Event Start Time":
            event_start_time.strftime("%H:%M:%S"),

        "Event End Time":
            event_end_time.strftime("%H:%M:%S"),

        "Estimated Budget":
            estimated_budget,

        "Actual Budget":
            actual_budget,

        "Ticketed Event":
            is_ticketed,

        "Ticket Price":
            ticket_price,

        "Tickets Available":
            tickets_available,

        "Tickets Sold":
            tickets_sold,

        "Revenue Collected":
            revenue_collected,

        "Vendor Used":
            vendor_used,

        "Vendor Name":
            vendor_name,

        "Vendors Used":
            json.dumps(vendors_data_list),

        "Has Stalls":
            has_stalls,

        "Stalls Data":
            json.dumps(stalls_data_list),

        "Requires Materials":
            requires_materials,

        "Materials Data":
            json.dumps(materials_data_list),

        "Learnings":
            safe_text(
                learnings
            ),

        "Logged Timestamp":
            logged_timestamp,

        "Logged Date":
            logged_date,

        "Logged Time":
            logged_time,

        "Created Timestamp":
            logged_timestamp,

        "Last Modified Timestamp":
            logged_timestamp,
    }

    # -------------------------------------------------------
    # Save CSV History
    # -------------------------------------------------------

    history_saved, history_message = (
        save_history_record(
            history_record
        )
    )

    if history_saved:
        try:
            from integrations.vendor_db import update_vendor_statistics
            update_vendor_statistics()
            
            if has_stalls:
                from integrations.stall_db import add_stalls_for_event
                add_stalls_for_event(
                    event_id=unique_event_id,
                    event_name=selected_event_name,
                    event_date=event_date.isoformat(),
                    property_name=selected_property,
                    stalls_list=stalls_data_list
                )
                
            if requires_materials:
                from integrations.material_db import add_materials_for_event
                add_materials_for_event(
                    event_id=unique_event_id,
                    event_name=selected_event_name,
                    event_date=event_date.isoformat(),
                    property_name=selected_property,
                    materials_list=materials_data_list
                )
        except Exception:
            pass

    # -------------------------------------------------------
    # Save Continuous-Learning Signal
    # -------------------------------------------------------

    try:

        learning_saved = bool(
            log_outcome(
                property_name=(
                    selected_property
                ),
                event_id=(
                    event_id
                ),
                event_name=(
                    selected_event_name
                ),
                attendance_percent=(
                    attendance_percent
                ),
                feedback_score=(
                    feedback_score
                ),
                success_score=(
                    success_score
                ),
                category=(
                    category
                ),
                metadata={
                    "event_date":
                        event_date.isoformat(),

                    "actual_attendance":
                        int(
                            actual_attendance
                        ),

                    "budget_planned":
                        float(
                            estimated_budget
                        ),

                    "budget_spent":
                        float(
                            actual_budget
                        ),

                    "recommendation_type":
                        recommendation_type,

                    "recommendation_score":
                        recommendation_score,

                    "predicted_event_date":
                        prediction_context.get(
                            "predicted_event_date"
                        ),

                    "total_capacity":
                        prediction_context.get(
                            "total_capacity"
                        ),

                    "predicted_active_residents":
                        prediction_context.get(
                            "predicted_active_residents"
                        ),

                    "predicted_occupancy_percent":
                        prediction_context.get(
                            "predicted_occupancy_percent"
                        ),

                    "predicted_turnout_rate":
                        prediction_context.get(
                            "predicted_turnout_rate"
                        ),

                    "predicted_attendance":
                        predicted_attendance
                        if has_prediction
                        else None,

                    "attendance_confidence_score":
                        prediction_context.get(
                            "attendance_confidence_score"
                        ),

                    "attendance_confidence":
                        prediction_context.get(
                            "attendance_confidence"
                        ),

                    "attendance_prediction_error":
                        prediction_error.get(
                            "error_count"
                        ),

                    "absolute_attendance_error":
                        prediction_error.get(
                            "absolute_error"
                        ),

                    "attendance_error_percent":
                        prediction_error.get(
                            "error_percent"
                        ),

                    "notes":
                        safe_text(
                            notes
                        ),
                },
            )
        )

    except Exception:

        learning_saved = False

    # -------------------------------------------------------
    # Result Messages
    # -------------------------------------------------------

    if history_saved and learning_saved:

        st.success(
            "Event outcome saved successfully. "
            "The event history, prediction history and "
            "continuous-learning system have been updated."
        )

        st.session_state[
            LAST_LOGGED_EVENT_KEY
        ] = history_record

        st.cache_data.clear()

    elif history_saved:

        st.warning(
            "The event was saved to history and prediction "
            "tracking, but the continuous-learning signal "
            "could not be stored."
        )

        st.session_state[
            LAST_LOGGED_EVENT_KEY
        ] = history_record

        st.cache_data.clear()

    elif learning_saved:

        st.warning(
            "The continuous-learning signal was stored, "
            "but the event history CSV could not be updated. "
            f"History error: {history_message}"
        )

    else:

        st.error(
            "The event outcome could not be saved. "
            f"History error: {history_message}"
        )


# ===========================================================
# Latest Logged Outcome
# ===========================================================

latest_event = (
    st.session_state.get(
        LAST_LOGGED_EVENT_KEY
    )
)

if isinstance(
    latest_event,
    dict,
):

    st.divider()

    st.subheader(
        "Latest Logged Outcome"
    )

    metric_1, metric_2, metric_3 = (
        st.columns(3)
    )

    with metric_1:

        attendance_value = safe_float(
            latest_event.get(
                "Attendance %"
            )
        )

        st.metric(
            "Attendance",
            f"{attendance_value:.1f}%",
        )

    with metric_2:

        feedback_value = safe_float(
            latest_event.get(
                "Average Feedback"
            )
        )

        st.metric(
            "Feedback",
            f"{feedback_value:.1f}/5",
        )

    with metric_3:

        success_value = safe_float(
            latest_event.get(
                "Success Score"
            )
        )

        st.metric(
            "Success Score",
            f"{success_value:.1f}",
        )

    predicted_attendance = (
        latest_event.get(
            "Predicted Attendance"
        )
    )

    if predicted_attendance not in (
        "",
        None,
    ):

        st.subheader(
            "Prediction Performance"
        )

        (
            prediction_metric_1,
            prediction_metric_2,
            prediction_metric_3,
        ) = st.columns(3)

        with prediction_metric_1:

            st.metric(
                "Predicted Attendance",
                safe_int(
                    predicted_attendance
                ),
            )

        with prediction_metric_2:

            st.metric(
                "Actual Attendance",
                safe_int(
                    latest_event.get(
                        "Actual Attendance"
                    )
                ),
            )

        with prediction_metric_3:

            error_value = safe_int(
                latest_event.get(
                    "Attendance Prediction Error"
                )
            )

            st.metric(
                "Prediction Error",
                f"{error_value:+d}",
            )

        error_percent = safe_float(
            latest_event.get(
                "Attendance Error %"
            )
        )

        absolute_error = safe_int(
            latest_event.get(
                "Absolute Attendance Error"
            )
        )

        st.caption(
            "Absolute prediction error: "
            f"{absolute_error} residents · "
            f"Error rate: {error_percent:.1f}%"
        )