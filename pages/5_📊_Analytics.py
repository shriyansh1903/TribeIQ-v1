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

from datetime import date, datetime
import datetime as dt_module

st.markdown("## 📊 Executive Intelligence Dashboard")
st.markdown(f"*Analytics & Reporting Center — {date.today().strftime('%B %d, %Y')}*")
st.write("")

# ===========================================================
# Workspace View Mode Selection
# ===========================================================
view_mode = st.radio(
    "Workspace Mode",
    ["👔 Executive Dashboard", "🎯 Operational Analytics"],
    horizontal=True,
    label_visibility="collapsed"
)

if view_mode == "👔 Executive Dashboard":
    hist_df = load_history_data()
    from integrations.executive_analytics import render_executive_dashboard
    render_executive_dashboard(hist_df)
    st.stop()


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
        "🏢 Target Property",
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


st.write("---")
st.markdown("### 📊 Core Performance Metrics")

metric_row([
    {"title": "Events Logged", "value": len(filtered_history)},
    {"title": "Average Attendance", "value": f"{average_attendance:.1f}%"},
    {"title": "Average Feedback", "value": f"{average_feedback:.2f}/5"},
    {"title": "Average Success", "value": f"{average_success:.1f}"}
])


# ===========================================================
# Recommendation Intelligence
# ===========================================================

st.write("---")

st.markdown(
    "### 🧠 Recommendation Intelligence"
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

st.write("---")

st.markdown(
    "### 📚 Continuous Learning Pipeline"
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

    st.write("---")

    st.markdown(
        "### 📈 Event Performance Analytics"
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

    st.write("---")

    st.markdown(
        "### 🏷️ Category Performance Benchmarks"
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

st.write("---")

st.markdown(
    "### 📜 Event History & Records"
)


if filtered_history.empty:

    st.info(
        "No event history is available for the "
        "selected property."
    )

else:
    # -------------------------------------------------------
    # Advanced Search & Filter Controls
    # -------------------------------------------------------
    from datetime import date, datetime
    import datetime as dt_module

    # Prepare data for filtering
    history_df = filtered_history.copy()
    if date_column is not None and date_column in history_df.columns:
        history_df["Parsed_Date"] = pd.to_datetime(history_df[date_column], errors="coerce")
    else:
        history_df["Parsed_Date"] = pd.Timestamp.now()

    # Search Bar
    search_query = st.text_input(
        "🔍 Search Event History...",
        value="",
        help="Search events by Property, Event Name, Category, Vendor Name, Notes, or Learnings."
    )

    # Filters Expander
    filters_expander = st.expander("🛠️ Filters & Sorting Options", expanded=False)
    with filters_expander:
        f_col1, f_col2, f_col3 = st.columns(3)
        
        with f_col1:
            prop_options = ["All"] + sorted(list(history_df["Property"].dropna().unique())) if "Property" in history_df.columns else ["All"]
            filter_prop = st.selectbox("Property Filter", options=prop_options)
            
            cat_options = ["All"] + sorted(list(history_df["Category"].dropna().unique())) if "Category" in history_df.columns else ["All"]
            filter_cat = st.selectbox("Category Filter", options=cat_options)

        with f_col2:
            vendor_col = "Vendor Name" if "Vendor Name" in history_df.columns else "Vendor"
            vendor_options = ["All"]
            if vendor_col in history_df.columns:
                unique_vendors = sorted(list(history_df[vendor_col].dropna().astype(str).unique()))
                if "None" in unique_vendors:
                    unique_vendors.remove("None")
                vendor_options.extend(unique_vendors)
            filter_vendor = st.selectbox("Vendor Filter", options=vendor_options)
            
            filter_ticketed = st.selectbox("Ticketed Filter", options=["All", "Ticketed", "Non-ticketed"])

        with f_col3:
            min_date = history_df["Parsed_Date"].min() if not history_df.empty and pd.notna(history_df["Parsed_Date"].min()) else date.today()
            max_date = history_df["Parsed_Date"].max() if not history_df.empty and pd.notna(history_df["Parsed_Date"].max()) else date.today()
            
            date_range = st.date_input(
                "Date Range Filter",
                value=(min_date.date() if hasattr(min_date, "date") else min_date, max_date.date() if hasattr(max_date, "date") else max_date)
            )
            
            sort_fields = {
                "Date": "Parsed_Date",
                "Attendance": "Actual Attendance" if "Actual Attendance" in history_df.columns else "Actual Attendee Count",
                "Success Score": "Success Score",
                "Revenue": "Revenue Collected" if "Revenue Collected" in history_df.columns else "Revenue",
                "Property": "Property"
            }
            available_sort_fields = {k: v for k, v in sort_fields.items() if v in history_df.columns or v == "Parsed_Date" or v == "Property"}
            sort_by_label = st.selectbox("Sort By", options=list(available_sort_fields.keys()))
            sort_order = st.selectbox("Sort Order", options=["Descending", "Ascending"])

    # Apply Search Query
    if search_query:
        search_cols = ["Event Name", "Property", "Category", "Vendor Name", "Vendor", "Notes", "Learnings"]
        search_mask = pd.Series(False, index=history_df.index)
        for col in search_cols:
            if col in history_df.columns:
                search_mask |= history_df[col].astype(str).str.contains(search_query, case=False, na=False)
        history_df = history_df[search_mask]

    # Apply Filter Options
    if filter_prop != "All" and "Property" in history_df.columns:
        history_df = history_df[history_df["Property"] == filter_prop]
        
    if filter_cat != "All" and "Category" in history_df.columns:
        history_df = history_df[history_df["Category"] == filter_cat]
        
    vendor_field = "Vendor Name" if "Vendor Name" in history_df.columns else "Vendor"
    if filter_vendor != "All" and vendor_field in history_df.columns:
        history_df = history_df[history_df[vendor_field].astype(str) == filter_vendor]
        
    if "Ticketed Event" in history_df.columns:
        if filter_ticketed == "Ticketed":
            history_df = history_df[history_df["Ticketed Event"] == True]
        elif filter_ticketed == "Non-ticketed":
            history_df = history_df[(history_df["Ticketed Event"] == False) | (history_df["Ticketed Event"].isna())]

    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_d, end_d = date_range
        history_df = history_df[
            (history_df["Parsed_Date"].dt.date >= start_d) &
            (history_df["Parsed_Date"].dt.date <= end_d)
        ]

    # Apply Sorting Selection
    sort_col = available_sort_fields.get(sort_by_label, "Parsed_Date")
    if sort_col in history_df.columns:
        history_df = history_df.sort_values(by=sort_col, ascending=(sort_order == "Ascending"))

    # Cleanup display columns
    display_history = history_df.drop(columns=["Parsed_Date"], errors="ignore")

    if date_column is not None and date_column in display_history.columns:
        parsed_dates = pd.to_datetime(display_history[date_column], errors="coerce")
        display_history[date_column] = parsed_dates.dt.strftime("%Y-%m-%d").fillna(display_history[date_column].astype(str))

    # Convert to Excel
    from io import BytesIO
    excel_buffer = BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        display_history.to_excel(writer, index=False, sheet_name='Event History')
    excel_data = excel_buffer.getvalue()

    st.download_button(
        label="📥 Download Event History (Excel)",
        data=excel_data,
        file_name="event_history.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

    history_table(display_history)

    # -------------------------------------------------------
    # Event Management Controls (Edit / Delete)
    # -------------------------------------------------------
    st.markdown("---")
    st.markdown("### 🛠️ Manage Selected Event")

    if display_history.empty:
        st.info("No matching historical events found to manage.")
    else:
        # Create event selection list
        event_options = []
        event_row_map = {}
        for idx, row in display_history.iterrows():
            event_id = row.get("Event ID", f"row-{idx}")
            label = f"{row.get('Date', 'N/A')} | {row.get('Property', 'N/A')} | {row.get('Event Name', 'N/A')} [{event_id}]"
            event_options.append(label)
            event_row_map[label] = (row, event_id)

        selected_label = st.selectbox("Select Event to Edit/Delete", options=event_options)
        selected_row, selected_event_id = event_row_map[selected_label]

        action_col1, action_col2 = st.columns(2)
        with action_col1:
            show_edit = st.checkbox("📝 Edit Selected Event Details", value=False)
        with action_col2:
            show_delete = st.checkbox("❌ Delete Selected Event Details", value=False)

        # Star selector display helper
        def get_star_string(val: float) -> str:
            full_stars = int(val)
            remainder = val - full_stars
            star_str = "★" * full_stars
            if remainder >= 0.75:
                star_str += "¾"
            elif remainder >= 0.5:
                star_str += "½"
            elif remainder >= 0.25:
                star_str += "¼"
            empty_stars = 5 - len(star_str)
            if remainder > 0 and remainder < 1.0:
                empty_stars = 5 - full_stars - 1
            star_str += "☆" * max(0, empty_stars)
            return f"{val:.2f} ({star_str})"

        # -------------------------------------------------------
        # Edit Form
        # -------------------------------------------------------
        if show_edit:
            st.markdown("#### Edit Event Outcome Details")
            
            # Prepare properties list and event names list
            all_property_names = sorted(list(profiles.keys())) if profiles else ["Tribe Moro", "Tribe Student Housing", "Tribe Luxury Co-Living"]
            prop_idx = all_property_names.index(selected_row["Property"]) if "Property" in selected_row and selected_row["Property"] in all_property_names else 0

            # Gather catalogue event list
            cat_event_name_column = find_event_name_column(events_dataframe)
            all_event_names = []
            if cat_event_name_column is not None and not events_dataframe.empty:
                all_event_names = sorted(events_dataframe[cat_event_name_column].dropna().unique().tolist())
            if "Event Name" in selected_row and selected_row["Event Name"] not in all_event_names:
                all_event_names.append(selected_row["Event Name"])
            all_event_names = sorted(all_event_names)
            event_idx = all_event_names.index(selected_row["Event Name"]) if "Event Name" in selected_row and selected_row["Event Name"] in all_event_names else 0

            with st.form("edit_logged_event_form"):
                st.markdown("### 📋 1. Event Details")
                edit_col1, edit_col2 = st.columns(2)
                with edit_col1:
                    edit_property = st.selectbox("Property", options=all_property_names, index=prop_idx)
                    edit_date = st.date_input(
                        "Event Date",
                        value=pd.to_datetime(selected_row["Date"]).date() if pd.notna(selected_row.get("Date")) else date.today()
                    )
                with edit_col2:
                    edit_event_name = st.selectbox("Event Name", options=all_event_names, index=event_idx)
                    
                    def parse_time(time_val, default_t):
                        if pd.isna(time_val) or not time_val:
                            return default_t
                        try:
                            return datetime.strptime(str(time_val).strip(), "%H:%M:%S").time()
                        except Exception:
                            try:
                                return datetime.strptime(str(time_val).strip(), "%H:%M").time()
                            except Exception:
                                return default_t
                                
                    edit_start_time = st.time_input("Event Start Time", value=parse_time(selected_row.get("Event Start Time"), dt_module.time(18, 0)))
                    edit_end_time = st.time_input("Event End Time", value=parse_time(selected_row.get("Event End Time"), dt_module.time(20, 0)))

                st.markdown("### 👥 2. Attendance")
                edit_att_col1, edit_att_col2 = st.columns(2)
                with edit_att_col1:
                    edit_actual_attendance = st.number_input(
                        "Actual Attendance",
                        min_value=0,
                        value=int(selected_row.get("Actual Attendance", 0)) if pd.notna(selected_row.get("Actual Attendance")) else 0,
                        step=1
                    )
                with edit_att_col2:
                    current_feedback = float(selected_row.get("Average Feedback", 4.0)) if pd.notna(selected_row.get("Average Feedback")) else 4.0
                    feedback_options = [i * 0.25 for i in range(21)]
                    closest_idx = min(range(len(feedback_options)), key=lambda i: abs(feedback_options[i] - current_feedback))
                    edit_feedback_score = st.selectbox("Feedback Rating", options=feedback_options, index=closest_idx, format_func=get_star_string)

                st.markdown("### 💸 3. Budget")
                edit_bud_col1, edit_bud_col2 = st.columns(2)
                with edit_bud_col1:
                    edit_estimated_budget = st.number_input(
                        "Estimated Budget (INR)",
                        min_value=0.0,
                        value=float(selected_row.get("Estimated Budget", selected_row.get("Budget Planned", 0.0))) if pd.notna(selected_row.get("Estimated Budget")) or pd.notna(selected_row.get("Budget Planned")) else 0.0,
                        step=100.0
                    )
                with edit_bud_col2:
                    edit_actual_budget = st.number_input(
                        "Actual Budget (INR)",
                        min_value=0.0,
                        value=float(selected_row.get("Actual Budget", selected_row.get("Budget Spent", 0.0))) if pd.notna(selected_row.get("Actual Budget")) or pd.notna(selected_row.get("Budget Spent")) else 0.0,
                        step=100.0
                    )

                st.markdown("### 🎫 4. Ticketing")
                edit_is_ticketed = st.checkbox("Ticketed Event", value=bool(selected_row.get("Ticketed Event", False)) if pd.notna(selected_row.get("Ticketed Event")) else False)
                edit_ticket_price = float(selected_row.get("Ticket Price", 0.0)) if pd.notna(selected_row.get("Ticket Price")) else 0.0
                edit_tickets_available = int(selected_row.get("Tickets Available", 0)) if pd.notna(selected_row.get("Tickets Available")) else 0
                edit_tickets_sold = int(selected_row.get("Tickets Sold", 0)) if pd.notna(selected_row.get("Tickets Sold")) else 0
                
                edit_t_col1, edit_t_col2 = st.columns(2)
                with edit_t_col1:
                    edit_ticket_price = st.number_input("Ticket Price (INR)", min_value=0.0, value=edit_ticket_price, step=10.0)
                    edit_tickets_available = st.number_input("Tickets Available", min_value=0, value=edit_tickets_available, step=1)
                with edit_t_col2:
                    edit_tickets_sold = st.number_input("Tickets Sold", min_value=0, value=edit_tickets_sold, step=1)
                    edit_revenue_collected = edit_ticket_price * edit_tickets_sold
                    st.number_input("Revenue Collected (auto-calculated)", min_value=0.0, value=float(edit_revenue_collected), disabled=True)

                st.markdown("### 🏪 5. Vendor")
                edit_vendor_used = st.checkbox("Vendor Used", value=bool(selected_row.get("Vendor Used", False)) if pd.notna(selected_row.get("Vendor Used")) else False)
                
                edit_vendors_data_list = []
                edit_vendor_name = "None"
                
                if edit_vendor_used:
                    try:
                        from integrations.vendor_db import load_vendors
                        vendors_df = load_vendors()
                        active_vendors = vendors_df[vendors_df["Active / Inactive Status"] == "Active"]
                        vendor_options = [f"{row['Vendor Name']} [{row['Vendor ID']}]" for _, row in active_vendors.iterrows()]
                    except Exception:
                        vendor_options = []
                        
                    prev_used_str = selected_row.get("Vendors Used", "[]")
                    prev_used = []
                    if pd.notna(prev_used_str) and str(prev_used_str).strip():
                        try:
                            prev_used = json.loads(prev_used_str)
                        except Exception:
                            pass
                    
                    prev_ids = [v.get("vendor_id") for v in prev_used]
                    default_selected_lbls = []
                    for opt in vendor_options:
                        opt_id = opt.split("[")[-1].rstrip("]") if "[" in opt else "other"
                        if opt_id in prev_ids:
                            default_selected_lbls.append(opt)
                            
                    edit_selected_lbls = st.multiselect(
                        "Select Vendors Hired",
                        options=vendor_options,
                        default=default_selected_lbls,
                        help="Choose one or more vendors from the central database."
                    )
                    
                    if edit_selected_lbls:
                        for lbl in edit_selected_lbls:
                            st.markdown(f"**Vendor Details: {lbl}**")
                            c_cost, c_gst = st.columns(2)
                            with c_cost:
                                v_id = lbl.split("[")[-1].rstrip("]") if "[" in lbl else "other"
                                prev_match = next((v for v in prev_used if str(v.get("vendor_id")) == str(v_id)), None)
                                
                                if prev_match:
                                    def_base = float(prev_match.get("base_cost", 0.0))
                                    def_gst = int(prev_match.get("gst_percent", 18))
                                else:
                                    db_row = vendors_df[vendors_df["Vendor ID"] == v_id].iloc[0] if v_id != "other" and not vendors_df.empty else None
                                    def_base = float(db_row["Base Amount"]) if db_row is not None else 0.0
                                    def_gst = int(db_row["GST Percentage"]) if db_row is not None else 18
                                
                                edit_base_cost = st.number_input(f"Base Cost for {lbl.split(' [')[0]} (INR)", min_value=0.0, value=def_base, key=f"edit_base_cost_{v_id}")
                            with c_gst:
                                edit_gst_pct = st.selectbox(f"GST % for {lbl.split(' [')[0]}", options=[12, 18], index=[12, 18].index(def_gst), key=f"edit_gst_pct_{v_id}")
                            
                            edit_gst_amt = round((edit_base_cost * edit_gst_pct) / 100.0, 2)
                            edit_final_cost = round(edit_base_cost + edit_gst_amt, 2)
                            
                            edit_vendors_data_list.append({
                                "vendor_id": v_id,
                                "name": lbl.split(" [")[0],
                                "category": db_row["Vendor Category"] if v_id != "other" and not vendors_df.empty else "Miscellaneous",
                                "base_cost": edit_base_cost,
                                "gst_percent": edit_gst_pct,
                                "gst_amount": edit_gst_amt,
                                "final_cost": edit_final_cost
                            })
                        edit_vendor_name = ", ".join([v["name"] for v in edit_vendors_data_list])

            st.markdown("### 🏪 6. Stall Management")
            edit_has_stalls = st.checkbox("This event includes stalls", value=bool(selected_row.get("Has Stalls", False)) if pd.notna(selected_row.get("Has Stalls")) else False)
            edit_stalls_data_list = []
            
            if edit_has_stalls:
                try:
                    from integrations.vendor_db import load_vendors
                    vendors_df = load_vendors()
                    active_vendors = vendors_df[vendors_df["Active / Inactive Status"] == "Active"]
                    vendor_options = [f"{row['Vendor Name']} [{row['Vendor ID']}]" for _, row in active_vendors.iterrows()]
                except Exception:
                    vendor_options = []
                    
                prev_stalls_str = selected_row.get("Stalls Data", "[]")
                prev_stalls = []
                if pd.notna(prev_stalls_str) and str(prev_stalls_str).strip():
                    try:
                        prev_stalls = json.loads(prev_stalls_str)
                    except Exception:
                        pass
                
                edit_num_stalls = st.number_input("Number of Stalls", min_value=1, value=max(len(prev_stalls), 1), step=1)
                for i in range(int(edit_num_stalls)):
                    st.markdown(f"**Stall #{i+1} Details**")
                    col_s1, col_s2, col_s3 = st.columns(3)
                    with col_s1:
                        prev_stall = prev_stalls[i] if i < len(prev_stalls) else {}
                        prev_vendor_id = prev_stall.get("vendor_id", "")
                        
                        default_v_idx = 0
                        for idx, opt in enumerate(vendor_options):
                            opt_id = opt.split("[")[-1].rstrip("]") if "[" in opt else ""
                            if opt_id == prev_vendor_id:
                                default_v_idx = idx
                                break
                                
                        stall_vendor = st.selectbox(f"Vendor for Stall #{i+1}", options=vendor_options, index=default_v_idx, key=f"edit_stall_vendor_{i}")
                        v_id = stall_vendor.split("[")[-1].rstrip("]") if "[" in stall_vendor else "other"
                        
                        v_row = vendors_df[vendors_df["Vendor ID"] == v_id].iloc[0] if v_id != "other" and not vendors_df.empty else None
                        v_name = v_row["Vendor Name"] if v_row is not None else "Other"
                        v_cat = v_row["Vendor Category"] if v_row is not None else "Miscellaneous"
                        
                        stall_name = st.text_input(f"Stall #{i+1} Name", value=prev_stall.get("stall_name", f"{v_name} Stall"), key=f"edit_stall_name_{i}")
                    with col_s2:
                        from integrations.stall_db import DEFAULT_STALL_CATEGORIES
                        try:
                            cat_idx = DEFAULT_STALL_CATEGORIES.index(prev_stall.get("stall_category", v_cat))
                        except Exception:
                            cat_idx = 0
                        stall_cat = st.selectbox(f"Stall #{i+1} Category", options=DEFAULT_STALL_CATEGORIES, index=cat_idx, key=f"edit_stall_cat_{i}")
                        
                        prev_size = prev_stall.get("stall_size", "Medium")
                        size_idx = ["Small", "Medium", "Large"].index(prev_size) if prev_size in ["Small", "Medium", "Large"] else 1
                        stall_size = st.selectbox(f"Stall #{i+1} Size", options=["Small", "Medium", "Large"], index=size_idx, key=f"edit_stall_size_{i}")
                    with col_s3:
                        rental_amt = st.number_input(f"Rental Amount for Stall #{i+1} (INR)", min_value=0.0, value=float(prev_stall.get("rental_amount", 0.0)), step=100.0, key=f"edit_stall_rental_{i}")
                        
                        prev_status = prev_stall.get("status", "Confirmed")
                        status_opts = ["Reserved", "Confirmed", "Cancelled", "Completed"]
                        status_idx = status_opts.index(prev_status) if prev_status in status_opts else 1
                        stall_status = st.selectbox(f"Stall #{i+1} Status", options=status_opts, index=status_idx, key=f"edit_stall_status_{i}")
                    
                    stall_notes = st.text_input(f"Notes for Stall #{i+1}", value=prev_stall.get("notes", ""), key=f"edit_stall_notes_{i}")
                    
                    edit_stalls_data_list.append({
                        "vendor_id": v_id,
                        "stall_name": stall_name,
                        "stall_category": stall_cat,
                        "rental_amount": rental_amt,
                        "stall_size": stall_size,
                        "status": stall_status,
                        "notes": stall_notes
                    })
                tot_stall_rev = sum([s["rental_amount"] for s in edit_stalls_data_list])
                st.write(f"**Total Stall Revenue (auto-calculated):** INR {tot_stall_rev}")

            st.markdown("### 📦 7. Materials & Procurement")
            edit_requires_materials = st.checkbox("This event requires materials", value=bool(selected_row.get("Requires Materials", False)) if pd.notna(selected_row.get("Requires Materials")) else False)
            edit_materials_data_list = []
            
            if edit_requires_materials:
                try:
                    from integrations.vendor_db import load_vendors
                    vendors_df = load_vendors()
                    active_vendors = vendors_df[vendors_df["Active / Inactive Status"] == "Active"]
                    vendor_options = ["None"] + [f"{row['Vendor Name']} [{row['Vendor ID']}]" for _, row in active_vendors.iterrows()]
                except Exception:
                    vendor_options = ["None"]
                    
                prev_mats_str = selected_row.get("Materials Data", "[]")
                prev_mats = []
                if pd.notna(prev_mats_str) and str(prev_mats_str).strip():
                    try:
                        prev_mats = json.loads(prev_mats_str)
                    except Exception:
                        pass
                
                edit_num_mats = st.number_input("Number of Materials", min_value=1, value=max(len(prev_mats), 1), step=1)
                for i in range(int(edit_num_mats)):
                    st.markdown(f"**Material #{i+1} Details**")
                    col_m1, col_m2, col_m3 = st.columns(3)
                    with col_m1:
                        prev_mat = prev_mats[i] if i < len(prev_mats) else {}
                        mat_name = st.text_input(f"Material Name #{i+1}", value=prev_mat.get("name", ""), key=f"edit_mat_name_{i}")
                        from integrations.material_db import DEFAULT_MATERIAL_CATEGORIES
                        prev_cat = prev_mat.get("category", "Furniture")
                        cat_idx = DEFAULT_MATERIAL_CATEGORIES.index(prev_cat) if prev_cat in DEFAULT_MATERIAL_CATEGORIES else 0
                        mat_cat = st.selectbox(f"Material Category #{i+1}", options=DEFAULT_MATERIAL_CATEGORIES, index=cat_idx, key=f"edit_mat_cat_{i}")
                    with col_m2:
                        qty = st.number_input(f"Quantity Required #{i+1}", min_value=1, value=int(prev_mat.get("quantity", 1)), step=1, key=f"edit_mat_qty_{i}")
                        unit = st.text_input(f"Unit #{i+1}", value=prev_mat.get("unit", "Pcs"), key=f"edit_mat_unit_{i}")
                        
                        prev_vendor_id = prev_mat.get("vendor_id", "None")
                        default_v_idx = 0
                        for idx, opt in enumerate(vendor_options):
                            opt_id = opt.split("[")[-1].rstrip("]") if "[" in opt else "None"
                            if opt_id == prev_vendor_id:
                                default_v_idx = idx
                                break
                        mat_vendor = st.selectbox(f"Vendor (Optional) #{i+1}", options=vendor_options, index=default_v_idx, key=f"edit_mat_vendor_{i}")
                        v_id = mat_vendor.split("[")[-1].rstrip("]") if "[" in mat_vendor else "None"
                    with col_m3:
                        unit_cost = st.number_input(f"Unit Cost (INR) #{i+1}", min_value=0.0, value=float(prev_mat.get("unit_cost", 0.0)), step=10.0, key=f"edit_mat_unit_cost_{i}")
                        
                        from integrations.material_db import PROCUREMENT_STATUS_BADGES
                        prev_status = prev_mat.get("status", "Not Ordered")
                        status_opts = list(PROCUREMENT_STATUS_BADGES.keys())
                        status_idx = status_opts.index(prev_status) if prev_status in status_opts else 0
                        mat_status = st.selectbox(f"Procurement Status #{i+1}", options=status_opts, index=status_idx, key=f"edit_mat_status_{i}")
                        
                    mat_notes = st.text_input(f"Notes #{i+1}", value=prev_mat.get("notes", ""), key=f"edit_mat_notes_{i}")
                    
                    edit_materials_data_list.append({
                        "name": mat_name,
                        "category": mat_cat,
                        "quantity": qty,
                        "unit": unit,
                        "vendor_id": v_id,
                        "unit_cost": unit_cost,
                        "status": mat_status,
                        "notes": mat_notes
                    })
                tot_proc_cost = sum([m["quantity"] * m["unit_cost"] for m in edit_materials_data_list])
                st.write(f"**Total Procurement Cost (auto-calculated):** INR {tot_proc_cost}")

            st.markdown("### 📝 8. Notes & Learnings")
            edit_notes = st.text_area("Notes", value=str(selected_row.get("Notes", "")) if pd.notna(selected_row.get("Notes")) else "")
            edit_learnings = st.text_area("Learnings", value=str(selected_row.get("Learnings", "")) if pd.notna(selected_row.get("Learnings")) else "")

            save_submitted = st.form_submit_button("💾 Save Changes", type="primary", use_container_width=True)

            if save_submitted:
                # Calculate Turnout Rate Automatically
                from occupancy_forecaster import load_resident_export, get_active_residents
                residents_timeline = load_resident_export()
                event_timestamp = pd.Timestamp(edit_date).normalize()
                active_res = get_active_residents(
                    dataframe=residents_timeline,
                    property_name=edit_property,
                    event_date=event_timestamp
                )
                active_count = len(active_res)
                if active_count > 0:
                    new_turnout_pct = (float(edit_actual_attendance) / float(active_count)) * 100.0
                    new_turnout_pct = min(new_turnout_pct, 100.0)
                else:
                    new_turnout_pct = 0.0

                new_success_score = calculate_success_score(
                    attendance_percent=new_turnout_pct,
                    feedback_score=edit_feedback_score,
                    budget_planned=edit_estimated_budget,
                    budget_spent=edit_actual_budget,
                )
                
                pred_attendance = safe_int(selected_row.get("Predicted Attendance"))
                has_prediction = pd.notna(selected_row.get("Predicted Attendance")) and str(selected_row.get("Predicted Attendance")).strip() != ""
                
                new_pred_error = calculate_prediction_error(
                    actual_attendance=int(edit_actual_attendance),
                    predicted_attendance=pred_attendance,
                    has_prediction=has_prediction
                )

                import pytz
                ist_tz = pytz.timezone("Asia/Kolkata")
                now_ist = datetime.now(ist_tz)
                last_modified_timestamp = now_ist.isoformat()

                updated_data = {
                    "Date": edit_date.isoformat(),
                    "Property": edit_property,
                    "Event Name": edit_event_name,
                    "Attendance %": round(new_turnout_pct, 2),
                    "Actual Attendance": int(edit_actual_attendance),
                    "Average Feedback": round(edit_feedback_score, 2),
                    "Success Score": new_success_score,
                    "Budget Planned": round(edit_estimated_budget, 2),
                    "Budget Spent": round(edit_actual_budget, 2),
                    "Estimated Budget": edit_estimated_budget,
                    "Actual Budget": edit_actual_budget,
                    "Ticketed Event": edit_is_ticketed,
                    "Ticket Price": edit_ticket_price,
                    "Tickets Available": edit_tickets_available,
                    "Tickets Sold": edit_tickets_sold,
                    "Revenue Collected": edit_revenue_collected,
                    "Vendor Used": edit_vendor_used,
                    "Vendor Name": edit_vendor_name if edit_vendor_used else "None",
                    "Vendors Used": json.dumps(edit_vendors_data_list),
                    "Has Stalls": edit_has_stalls,
                    "Stalls Data": json.dumps(edit_stalls_data_list),
                    "Requires Materials": edit_requires_materials,
                    "Materials Data": json.dumps(edit_materials_data_list),
                    "Notes": safe_text(edit_notes),
                    "Learnings": safe_text(edit_learnings),
                    "Last Modified Timestamp": last_modified_timestamp,
                    "Attendance Prediction Error": new_pred_error.get("error_count"),
                    "Absolute Attendance Error": new_pred_error.get("absolute_error"),
                    "Attendance Error %": new_pred_error.get("error_percent"),
                }

                from ui_data_bridge import update_logged_event
                success = update_logged_event(selected_event_id, updated_data)
                if success:
                    # Update summaries
                    from integrations.vendor_db import update_vendor_statistics
                    update_vendor_statistics()
                    
                    from integrations.stall_db import add_stalls_for_event
                    add_stalls_for_event(
                        event_id=selected_event_id,
                        event_name=edit_event_name,
                        event_date=edit_date.isoformat(),
                        property_name=edit_property,
                        stalls_list=edit_stalls_data_list if edit_has_stalls else []
                    )
                    
                    from integrations.material_db import add_materials_for_event
                    add_materials_for_event(
                        event_id=selected_event_id,
                        event_name=edit_event_name,
                        event_date=edit_date.isoformat(),
                        property_name=edit_property,
                        materials_list=edit_materials_data_list if edit_requires_materials else []
                    )
                    
                    st.toast(f"Successfully updated event: {edit_event_name}!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Failed to update event details.")

        # -------------------------------------------------------
        # Delete Confirmation
        # -------------------------------------------------------
        if show_delete:
            st.warning(f"⚠️ Are you sure you want to permanently delete **{selected_row.get('Event Name')}** on **{selected_row.get('Date')}**?")
            confirm_del = st.checkbox("I confirm that I want to delete this event log permanently.")
            if confirm_del:
                if st.button("Confirm and Delete", type="primary", use_container_width=True):
                    from ui_data_bridge import delete_logged_event
                    success = delete_logged_event(
                        date_val=selected_row.get("Date"),
                        property_val=selected_row.get("Property"),
                        event_val=selected_row.get("Event Name")
                    )
                    if success:
                        from integrations.stall_db import add_stalls_for_event
                        add_stalls_for_event(
                            event_id=selected_event_id,
                            event_name=selected_row.get("Event Name"),
                            event_date=selected_row.get("Date"),
                            property_name=selected_row.get("Property"),
                            stalls_list=[]
                        )
                        from integrations.material_db import add_materials_for_event
                        add_materials_for_event(
                            event_id=selected_event_id,
                            event_name=selected_row.get("Event Name"),
                            event_date=selected_row.get("Date"),
                            property_name=selected_row.get("Property"),
                            materials_list=[]
                        )
                        st.toast("Event successfully deleted.")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("Failed to delete event record.")

# ===========================================================
# History Management (Danger Zone - Global Operations)
# ===========================================================
st.write("---")
st.markdown("### ⚠️ Global History Operations")

manage_col1, manage_col2 = st.columns(2)

with manage_col1:
    st.info("To edit or delete individual events, use the search/filter tool and the 'Manage Selected Event' section above.")

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