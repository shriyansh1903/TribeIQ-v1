"""
===========================================================
TribeIQ Analytics Page
===========================================================

Frontend integration for event history, recommendation
performance and continuous-learning outcomes.
===========================================================
"""

import sys
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
import streamlit as st


# ===========================================================
# Project Paths
# ===========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
DATA_DIR = PROJECT_ROOT / "data"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


# ===========================================================
# Backend Imports
# ===========================================================

from learning.signal_store import (
    load_signals_dataframe
)

from ui_data_bridge import (
    get_session_property,
    get_session_result,
    load_application_data
)

from ui.components import (
    history_table,
    metric_row,
    page_header,
    section_header
)


# ===========================================================
# Page Configuration
# ===========================================================

# CSS is loaded globally by app.py via ui.styles.load_css()


# ===========================================================
# Helpers
# ===========================================================

def safe_text(value: Any) -> str:

    if value is None:
        return ""

    return str(value).strip()


def safe_float(
    value: Any,
    default: float = 0.0
) -> float:

    try:

        numeric = float(value)

        if pd.isna(numeric):
            return default

        return numeric

    except (TypeError, ValueError):
        return default


def normalize_column_name(
    value: Any
) -> str:

    return (
        safe_text(value)
        .lower()
        .replace("_", " ")
        .replace("-", " ")
    )


def find_column(
    dataframe: pd.DataFrame,
    candidates: tuple
) -> Optional[str]:

    if not isinstance(dataframe, pd.DataFrame):
        return None

    normalized_lookup = {
        normalize_column_name(column):
            column
        for column in dataframe.columns
    }

    for candidate in candidates:

        normalized_candidate = (
            normalize_column_name(
                candidate
            )
        )

        if (
            normalized_candidate
            in normalized_lookup
        ):

            return normalized_lookup[
                normalized_candidate
            ]

    return None


def numeric_series(
    dataframe: pd.DataFrame,
    column: Optional[str]
) -> pd.Series:

    if (
        column is None
        or column not in dataframe.columns
    ):

        return pd.Series(
            dtype="float64"
        )

    return pd.to_numeric(
        dataframe[column],
        errors="coerce"
    ).dropna()


# ===========================================================
# History Loading
# ===========================================================

def is_event_history(
    dataframe: pd.DataFrame
) -> bool:

    if dataframe.empty:
        return False

    columns = {
        normalize_column_name(column)
        for column in dataframe.columns
    }

    has_event = bool(
        columns.intersection({
            "event name",
            "event",
            "name"
        })
    )

    has_property = bool(
        columns.intersection({
            "property",
            "property name"
        })
    )

    has_outcome = bool(
        columns.intersection({
            "attendance %",
            "attendance",
            "average feedback",
            "avg feedback",
            "feedback",
            "success score"
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
        "event_log.csv"
    )

    csv_files = sorted(
        DATA_DIR.rglob("*.csv")
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


@st.cache_data(
    show_spinner=False
)
def load_history_data() -> pd.DataFrame:

    history_path = find_history_file()

    if history_path is None:
        return pd.DataFrame()

    try:

        return pd.read_csv(
            history_path
        )

    except Exception:

        return pd.DataFrame()


@st.cache_data(
    show_spinner=False
)
def get_application_data() -> Dict[str, Any]:

    return load_application_data()


# ===========================================================
# Page Header
# ===========================================================

page_header(
    "📊 Analytics",
    "Track event performance, recommendation quality and "
    "the real outcomes feeding TribeIQ's continuous-learning "
    "system."
)


# ===========================================================
# Load Data
# ===========================================================

try:

    application_data = (
        get_application_data()
    )

except Exception:

    application_data = {}


history = load_history_data()

learning_signals = (
    load_signals_dataframe()
)

recommendation_result = (
    get_session_result(
        st.session_state
    )
)

recommended_property = (
    get_session_property(
        st.session_state
    )
)


# ===========================================================
# Property Selection
# ===========================================================

profiles = application_data.get(
    "profiles",
    {}
)

property_names = []

if isinstance(profiles, dict):

    property_names.extend(
        safe_text(name)
        for name in profiles.keys()
        if safe_text(name)
    )


history_property_column = find_column(
    history,
    (
        "Property",
        "Property Name"
    )
)


if history_property_column is not None:

    property_names.extend(
        safe_text(value)
        for value in history[
            history_property_column
        ].dropna().tolist()
        if safe_text(value)
    )


property_names = sorted(
    set(property_names)
)


selected_property = "All Properties"


if property_names:

    property_options = (
        ["All Properties"]
        + property_names
    )

    default_index = 0

    if (
        recommended_property
        in property_options
    ):

        default_index = (
            property_options.index(
                recommended_property
            )
        )

    selected_property = st.selectbox(
        "Property",
        options=property_options,
        index=default_index
    )


# ===========================================================
# Filter History
# ===========================================================

filtered_history = history.copy()


if (
    selected_property
    != "All Properties"
    and history_property_column
    is not None
):

    filtered_history = history[
        history[
            history_property_column
        ]
        .astype(str)
        .str.strip()
        .str.lower()
        == selected_property.lower()
    ].copy()


# ===========================================================
# Column Resolution
# ===========================================================

attendance_column = find_column(
    filtered_history,
    (
        "Attendance %",
        "Attendance",
        "Attendance Percent"
    )
)

feedback_column = find_column(
    filtered_history,
    (
        "Average Feedback",
        "Avg Feedback",
        "Feedback",
        "Feedback Score"
    )
)

success_column = find_column(
    filtered_history,
    (
        "Success Score",
        "Success"
    )
)

event_name_column = find_column(
    filtered_history,
    (
        "Event Name",
        "Event",
        "Name"
    )
)

category_column = find_column(
    filtered_history,
    (
        "Category",
        "Event Category"
    )
)

date_column = find_column(
    filtered_history,
    (
        "Date",
        "Event Date"
    )
)


# ===========================================================
# Core Metrics
# ===========================================================

attendance_values = numeric_series(
    filtered_history,
    attendance_column
)

feedback_values = numeric_series(
    filtered_history,
    feedback_column
)

success_values = numeric_series(
    filtered_history,
    success_column
)


average_attendance = (
    float(attendance_values.mean())
    if not attendance_values.empty
    else 0.0
)

average_feedback = (
    float(feedback_values.mean())
    if not feedback_values.empty
    else 0.0
)

average_success = (
    float(success_values.mean())
    if not success_values.empty
    else 0.0
)


metric_row([
    {"title": "Events Logged", "value": len(filtered_history)},
    {"title": "Average Attendance", "value": f"{average_attendance:.1f}%"},
    {"title": "Average Feedback", "value": f"{average_feedback:.2f}/5"},
    {"title": "Average Success", "value": f"{average_success:.1f}"}
])


# ===========================================================
# Recommendation Intelligence
# ===========================================================

st.divider()

section_header(
    "Recommendation Intelligence"
)


if isinstance(
    recommendation_result,
    dict
):

    ranked_candidates = (
        recommendation_result.get(
            "ranked_candidates",
            []
        )
    )

    selected_count = (
        recommendation_result.get(
            "selected_count",
            0
        )
    )

    candidate_count = (
        recommendation_result.get(
            "candidate_count",
            0
        )
    )

    top_score = 0.0

    if isinstance(
        ranked_candidates,
        list
    ) and ranked_candidates:

        top_score = max(
            safe_float(
                candidate.get(
                    "final_score",
                    0.0
                )
            )
            for candidate
            in ranked_candidates
            if isinstance(
                candidate,
                dict
            )
        )

    recommendation_metric_1, \
        recommendation_metric_2, \
        recommendation_metric_3 = (
            st.columns(3)
        )


    with recommendation_metric_1:

        st.metric(
            "Candidates Evaluated",
            candidate_count
        )


    with recommendation_metric_2:

        st.metric(
            "Events Selected",
            selected_count
        )


    with recommendation_metric_3:

        st.metric(
            "Top Recommendation Score",
            f"{top_score:.2f}"
        )


else:

    st.info(
        "Generate recommendations to display live "
        "recommendation intelligence here."
    )


# ===========================================================
# Continuous Learning
# ===========================================================

st.divider()

section_header(
    "Continuous Learning"
)


filtered_signals = (
    learning_signals.copy()
)


if (
    isinstance(
        filtered_signals,
        pd.DataFrame
    )
    and not filtered_signals.empty
    and selected_property
    != "All Properties"
    and "property_name"
    in filtered_signals.columns
):

    filtered_signals = (
        filtered_signals[
            filtered_signals[
                "property_name"
            ]
            .astype(str)
            .str.strip()
            .str.lower()
            == selected_property.lower()
        ].copy()
    )


if (
    isinstance(
        filtered_signals,
        pd.DataFrame
    )
    and not filtered_signals.empty
):

    completed_signals = (
        filtered_signals[
            filtered_signals.get(
                "completed",
                False
            ).fillna(False)
            .astype(bool)
        ].copy()
        if "completed"
        in filtered_signals.columns
        else pd.DataFrame()
    )


    learning_metric_1, \
        learning_metric_2, \
        learning_metric_3 = (
            st.columns(3)
        )


    with learning_metric_1:

        st.metric(
            "Learning Signals",
            len(filtered_signals)
        )


    with learning_metric_2:

        st.metric(
            "Completed Outcomes",
            len(completed_signals)
        )


    with learning_metric_3:

        if (
            not completed_signals.empty
            and "success_score"
            in completed_signals.columns
        ):

            learned_success = (
                pd.to_numeric(
                    completed_signals[
                        "success_score"
                    ],
                    errors="coerce"
                )
                .dropna()
                .mean()
            )

            if pd.isna(learned_success):
                learned_success = 0.0

        else:

            learned_success = 0.0


        st.metric(
            "Learned Success",
            f"{learned_success:.1f}"
        )


else:

    st.info(
        "No continuous-learning signals are available yet. "
        "Log completed event outcomes to begin learning."
    )


# ===========================================================
# Performance Charts
# ===========================================================

if not filtered_history.empty:

    st.divider()

    section_header(
        "Event Performance"
    )


    chart_dataframe = (
        filtered_history.copy()
    )


    if event_name_column is not None:

        chart_dataframe[
            "Event"
        ] = chart_dataframe[
            event_name_column
        ].astype(str)


        performance_columns = {}


        if attendance_column is not None:

            chart_dataframe[
                "Attendance"
            ] = pd.to_numeric(
                chart_dataframe[
                    attendance_column
                ],
                errors="coerce"
            )

            performance_columns[
                "Attendance"
            ] = "Attendance"


        if success_column is not None:

            chart_dataframe[
                "Success"
            ] = pd.to_numeric(
                chart_dataframe[
                    success_column
                ],
                errors="coerce"
            )

            performance_columns[
                "Success"
            ] = "Success"


        available_chart_columns = list(
            performance_columns.keys()
        )


        if available_chart_columns:

            chart_data = (
                chart_dataframe[
                    [
                        "Event"
                    ]
                    + available_chart_columns
                ]
                .dropna(
                    how="all",
                    subset=(
                        available_chart_columns
                    )
                )
                .set_index(
                    "Event"
                )
            )


            if not chart_data.empty:

                st.bar_chart(
                    chart_data
                )


# ===========================================================
# Category Performance
# ===========================================================

if (
    not filtered_history.empty
    and category_column is not None
):

    st.divider()

    section_header(
        "Category Performance"
    )


    category_data = (
        filtered_history.copy()
    )


    aggregation_columns = {}


    if attendance_column is not None:

        category_data[
            attendance_column
        ] = pd.to_numeric(
            category_data[
                attendance_column
            ],
            errors="coerce"
        )

        aggregation_columns[
            attendance_column
        ] = "mean"


    if feedback_column is not None:

        category_data[
            feedback_column
        ] = pd.to_numeric(
            category_data[
                feedback_column
            ],
            errors="coerce"
        )

        aggregation_columns[
            feedback_column
        ] = "mean"


    if success_column is not None:

        category_data[
            success_column
        ] = pd.to_numeric(
            category_data[
                success_column
            ],
            errors="coerce"
        )

        aggregation_columns[
            success_column
        ] = "mean"


    if aggregation_columns:

        category_summary = (
            category_data
            .groupby(
                category_column,
                dropna=False
            )
            .agg(
                aggregation_columns
            )
            .reset_index()
        )


        st.dataframe(
            category_summary,
            width="stretch",
            hide_index=True
        )


# ===========================================================
# Event History Table
# ===========================================================

st.divider()

section_header(
    "Event History"
)


if filtered_history.empty:

    st.info(
        "No event history is available for the "
        "selected property."
    )

else:

    display_history = (
        filtered_history.copy()
    )


    if date_column is not None:

        parsed_dates = pd.to_datetime(
            display_history[
                date_column
            ],
            errors="coerce"
        )

        display_history[
            date_column
        ] = parsed_dates.dt.strftime(
            "%Y-%m-%d"
        ).fillna(
            display_history[
                date_column
            ].astype(str)
        )


    history_table(display_history)


# ===========================================================
# History Management (Danger Zone)
# ===========================================================
st.divider()
st.subheader("⚠️ History Management")

manage_col1, manage_col2 = st.columns(2)

with manage_col1:
    st.markdown("### Delete a Specific Logged Event")
    if filtered_history.empty:
        st.info("No events available to delete.")
    else:
        events_list = []
        events_keys = []
        prop_col = history_property_column if history_property_column is not None else "Property"
        for _, row in filtered_history.iterrows():
            d_val = str(row.get(date_column, "")).strip() if date_column is not None else ""
            p_val = str(row.get(prop_col, "")).strip()
            e_val = str(row.get(event_name_column, "")).strip() if event_name_column is not None else ""
            if d_val and p_val and e_val:
                events_list.append(f"{d_val} | {p_val} | {e_val}")
                events_keys.append((d_val, p_val, e_val))
        
        if events_list:
            selected_event_idx = st.selectbox("Select Event to Delete", range(len(events_list)), format_func=lambda x: events_list[x])
            if st.button("Delete Selected Event", type="primary", use_container_width=True):
                target_date, target_prop, target_event = events_keys[selected_event_idx]
                from ui_data_bridge import delete_logged_event
                success = delete_logged_event(target_date, target_prop, target_event)
                if success:
                    st.toast(f"Deleted event: {target_event} ({target_date})")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Failed to delete event.")
        else:
            st.info("No valid history records found to delete.")

with manage_col2:
    st.markdown("### Clear All History")
    st.warning("This action cannot be undone. It will clear all rows from the event history database.")
    confirm_clear = st.checkbox("I understand and want to clear the entire event history.")
    if st.button("Clear All Event History", type="secondary", disabled=not confirm_clear, use_container_width=True):
        from ui_data_bridge import clear_all_history
        success = clear_all_history()
        if success:
            st.toast("Event history cleared successfully!")
            st.cache_data.clear()
            st.rerun()
        else:
            st.error("Failed to clear event history.")