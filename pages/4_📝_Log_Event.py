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

    render_html(
        f"""
        <div class="event-context-card">
            <div class="event-context-label">
                LIVE RECOMMENDATION CONTEXT
            </div>

            <div class="event-context-name">
                {context_status}
            </div>

            <div class="event-context-meta">
                Select one of the recommended events below.
                The saved real outcome will feed the
                continuous-learning and attendance-prediction
                systems.
            </div>
        </div>
        """
    )

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

        render_html(
            f"""
            <div class="event-context-card">
                <div class="event-context-label">
                    {recommendation_type}
                </div>

                <div class="event-context-name">
                    {event_name}
                </div>

                <div class="event-context-meta">
                    {category}
                </div>

                <div style="
                    display:grid;
                    grid-template-columns:
                        repeat(4,minmax(0,1fr));
                    gap:0.8rem;
                    margin-top:1rem;
                ">
                    <div>
                        <div class="event-context-label">
                            SCORE
                        </div>
                        <div class="event-context-name">
                            {final_score:.1f}
                        </div>
                    </div>

                    <div>
                        <div class="event-context-label">
                            DATE
                        </div>
                        <div class="event-context-meta">
                            {date_value}
                        </div>
                    </div>

                    <div>
                        <div class="event-context-label">
                            OCCUPANCY
                        </div>
                        <div class="event-context-name">
                            {occupancy_percent:.1f}%
                        </div>
                    </div>

                    <div>
                        <div class="event-context-label">
                            EXPECTED
                        </div>
                        <div class="event-context-name">
                            {predicted_attendance:,}
                        </div>
                    </div>
                </div>

                <div class="event-context-meta"
                    style="margin-top:0.8rem;">
                    Predicted active residents:
                    {active_residents:,}
                </div>
            </div>
            """
        )

    else:

        render_html(
            f"""
            <div class="event-context-card">
                <div class="event-context-label">
                    {recommendation_type}
                </div>

                <div class="event-context-name">
                    {event_name}
                </div>

                <div class="event-context-meta">
                    {category} · Recommendation score:
                    {final_score:.1f}
                </div>
            </div>
            """
        )


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

# Property and Event selection outside the form to allow dynamic pre-population
selection_col1, selection_col2 = st.columns(2)
with selection_col1:
    selected_property = st.selectbox(
        "Property",
        options=property_names,
        index=default_property_index,
        help="The specific co-living property where the event was hosted.",
    )

with selection_col2:
    selected_event_name = st.selectbox(
        "Event",
        options=event_names,
        help="The name of the event that was executed.",
    )

# Retrieve recommendation context if selected event is in active recommendations
selected_rec = next(
    (item for item in recommended_events if item.get("event_name") == selected_event_name),
    None
)

# Set defaults
def_rec_type = "manual"
def_rec_score = 0.0
def_pred_date = date.today()
def_capacity = 0
def_active = 0
def_occupancy = 0.0
def_turnout = 0.0
def_attendance = 0
def_confidence_label = "None"
def_confidence_score = 0.0

if selected_rec:
    if selected_rec.get("recommendation_type") == "major":
        def_rec_type = "major"
    else:
        def_rec_type = "minor"
    def_rec_score = float(selected_rec.get("final_score", 0.0))
    pred_date_str = selected_rec.get("predicted_event_date") or selected_rec.get("event_date")
    if pred_date_str:
        try:
            def_pred_date = pd.to_datetime(pred_date_str).date()
        except Exception:
            pass
    def_capacity = int(selected_rec.get("total_capacity", 0))
    def_active = int(selected_rec.get("active_residents", 0))
    def_occupancy = float(selected_rec.get("occupancy_percent", 0.0))
    def_turnout = float(selected_rec.get("predicted_turnout_rate", 0.0))
    def_attendance = int(selected_rec.get("predicted_attendance", 0))
    def_confidence_label = str(selected_rec.get("confidence_label", "None"))
    def_confidence_score = float(selected_rec.get("confidence_score", 0.0))

with st.form(
    "event_outcome_form",
    clear_on_submit=False,
):

    form_column_1, form_column_2 = (
        st.columns(2)
    )

    with form_column_1:

        event_date = st.date_input(
            "Event Execution Date",
            value=date.today(),
            help="The date on which this event took place.",
        )

        feedback_score = (
            st.selectbox(
                "Average Feedback Rating (0-5 Stars)",
                options=[i * 0.25 for i in range(21)],  # 0.00 to 5.00 in steps of 0.25
                index=16,  # Default to 4.00
                format_func=get_star_string,
                help="Select the average satisfaction rating given by the attending residents, represented as 1 to 5 stars (supports quarter, half, and full stars).",
            )
        )

    with form_column_2:

        actual_attendance = (
            st.number_input(
                "Actual Attendee Count",
                min_value=0,
                value=def_attendance,
                step=1,
                help="The total physical headcount of residents who checked in or attended the event.",
            )
        )

    budget_column_1, budget_column_2 = (
        st.columns(2)
    )

    with budget_column_1:

        budget_planned = (
            st.number_input(
                "Planned Budget (INR)",
                min_value=0.0,
                value=0.0,
                step=100.0,
                help="The budget initially approved/allocated for organizing this event in Indian Rupees (INR).",
            )
        )

    with budget_column_2:

        budget_spent = (
            st.number_input(
                "Actual Budget Spent (INR)",
                min_value=0.0,
                value=0.0,
                step=100.0,
                help="The total final cost incurred to run the event in Indian Rupees (INR).",
            )
        )

    st.markdown("---")
    with st.expander("Prediction & Recommendation Metadata (Optional)", expanded=False):
        st.markdown("<p style='font-size: 13px; color: #8B949E;'>Use these fields to manually enter or override the forecast/recommendation metadata that will be logged in the database.</p>", unsafe_allow_html=True)
        meta_col1, meta_col2 = st.columns(2)
        with meta_col1:
            rec_type_val = st.selectbox(
                "Recommendation Type",
                options=["manual", "major", "minor"],
                index=["manual", "major", "minor"].index(def_rec_type),
                help="The classification of this event recommendation."
            )
            rec_score_val = st.number_input(
                "Recommendation Score",
                min_value=0.0,
                max_value=1.0,
                value=def_rec_score,
                step=0.01,
                help="The final score computed by the recommendation engine."
            )
            pred_date_val = st.date_input(
                "Predicted Event Date",
                value=def_pred_date,
                help="The date recommended/predicted for this event."
            )
            capacity_val = st.number_input(
                "Total Capacity",
                min_value=0,
                value=def_capacity,
                step=1,
                help="The total physical bed capacity of the property."
            )
            active_val = st.number_input(
                "Predicted Active Residents",
                min_value=0,
                value=def_active,
                step=1,
                help="The number of residents expected to be active on the event date."
            )
        with meta_col2:
            occupancy_val = st.number_input(
                "Predicted Occupancy %",
                min_value=0.0,
                max_value=100.0,
                value=def_occupancy,
                step=0.1,
                help="The occupancy rate predicted for the property on that date."
            )
            turnout_val = st.number_input(
                "Predicted Turnout Rate (%)",
                min_value=0.0,
                max_value=100.0,
                value=def_turnout,
                step=0.1,
                help="The expected turnout rate predicted for this event."
            )
            attendance_val = st.number_input(
                "Predicted Attendance",
                min_value=0,
                value=def_attendance,
                step=1,
                help="The turnout attendee count predicted for this event."
            )
            conf_label_val = st.selectbox(
                "Attendance Confidence",
                options=["None", "Low", "Medium", "High"],
                index=["None", "Low", "Medium", "High"].index(def_confidence_label),
                help="The confidence level label of the prediction."
            )
            conf_score_val = st.number_input(
                "Attendance Confidence Score",
                min_value=0.0,
                max_value=100.0,
                value=def_confidence_score,
                step=0.1,
                help="The numerical confidence score of the attendance prediction."
            )

    st.markdown("---")

    notes = st.text_area(
        "Notes",
        placeholder=(
            "Add observations, resident reactions "
            "or operational notes..."
        ),
        help="Any qualitative observations, reactions, or logistics notes about the event outcome.",
    )

    submitted = st.form_submit_button(
        "Save Event Outcome",
        type="primary",
        use_container_width=True,
    )


# ===========================================================
# Save Outcome
# ===========================================================

if submitted:

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
        recommendation_score = safe_float(selected_recommendation.get("final_score"))
    else:
        event_id = ""
        category = ""
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

    # Calculate prediction error based on user-entered predicted attendance
    has_prediction = bool(attendance_val > 0)
    prediction_error = (
        calculate_prediction_error(
            actual_attendance=int(actual_attendance),
            predicted_attendance=int(attendance_val),
            has_prediction=has_prediction,
        )
    )

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
                budget_planned
            ),
            budget_spent=(
                budget_spent
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

    history_record = {
        "Date":
            event_date.isoformat(),

        "Property":
            selected_property,

        "Event ID":
            event_id,

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
                budget_planned,
                2,
            ),

        "Budget Spent":
            round(
                budget_spent,
                2,
            ),

        "Recommendation Type":
            rec_type_val,

        "Recommendation Score":
            round(
                rec_score_val,
                4,
            ),

        "Predicted Event Date":
            pred_date_val.isoformat()
            if has_prediction
            else "",

        "Predicted Weekday":
            pred_date_val.strftime("%A")
            if has_prediction
            else "",

        "Total Capacity":
            int(
                capacity_val
            ),

        "Predicted Active Residents":
            int(
                active_val
            ),

        "Predicted Occupancy %":
            round(
                safe_float(
                    occupancy_val
                ),
                2,
            ),

        "Predicted Turnout Rate":
            round(
                safe_float(
                    turnout_val
                ),
                2,
            ),

        "Predicted Attendance":
            int(
                attendance_val
            )
            if has_prediction
            else "",

        "Attendance Confidence Score":
            round(
                safe_float(
                    conf_score_val
                ),
                2,
            ),

        "Attendance Confidence":
            conf_label_val,

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
    }

    # -------------------------------------------------------
    # Save CSV History
    # -------------------------------------------------------

    history_saved, history_message = (
        save_history_record(
            history_record
        )
    )

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
                            budget_planned
                        ),

                    "budget_spent":
                        float(
                            budget_spent
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