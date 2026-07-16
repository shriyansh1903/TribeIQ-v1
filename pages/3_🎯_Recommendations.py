"""
===========================================================
TribeIQ Recommendations Page
===========================================================

Recommendation interface with:

1. Property selection
2. Recommendation generation
3. Manual event-date intelligence
4. Conflict-free monthly scheduling
5. Unified Event Intelligence Cards
6. Future occupancy prediction
7. Attendance prediction
8. Candidate ranking
===========================================================
"""

from __future__ import annotations

import html
import sys
import textwrap
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st


# ===========================================================
# Project Paths
# ===========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
INTELLIGENCE_DIR = SRC_DIR / "intelligence"

for path in (
    PROJECT_ROOT,
    SRC_DIR,
    INTELLIGENCE_DIR,
):
    path_string = str(path.resolve())

    if path_string not in sys.path:
        sys.path.insert(0, path_string)


# ===========================================================
# Backend Imports
# ===========================================================

from ui_data_bridge import (
    SESSION_ERROR_KEY,
    SESSION_RUNNING_KEY,
    generate_property_recommendations,
    get_session_property,
    get_session_result,
    load_application_data,
    save_error_to_session,
    save_result_to_session,
    validate_application_data,
    save_predictions_to_csv,
)

from recommendation_date_bridge import (
    enrich_recommendation_result_for_date,
    enrich_recommendation_result_with_best_dates,
)

from ui.components import (
    metric_row,
    page_header,
    section_header,
)


# ===========================================================
# Session Keys
# ===========================================================

DATE_MODE_KEY = "tribeiq_recommendation_date_mode"
MANUAL_DATE_KEY = "tribeiq_manual_event_date"
FORECAST_MONTH_KEY = "tribeiq_forecast_month"

DATED_RESULT_KEY = (
    "tribeiq_dated_recommendation_result"
)

DATED_RESULT_SOURCE_KEY = (
    "tribeiq_dated_result_source"
)


# ===========================================================
# Basic Helpers
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
    except (TypeError, ValueError):
        pass

    text = str(value).strip()

    return text or default


def safe_html(
    value: Any,
    default: str = "",
) -> str:

    return html.escape(
        safe_text(value, default),
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

    except (TypeError, ValueError):
        return default


def safe_int(
    value: Any,
    default: int = 0,
) -> int:

    try:
        return int(
            round(float(value))
        )

    except (TypeError, ValueError):
        return default


def safe_list(
    value: Any,
) -> List[Any]:

    if isinstance(value, list):
        return value

    return []


def get_event_name(
    event: Dict[str, Any],
) -> str:

    return safe_text(
        event.get("event_name"),
        "Unknown Event",
    )


def get_event_category(
    event: Dict[str, Any],
) -> str:

    return safe_text(
        event.get("category"),
        "Uncategorised",
    )


def normalize_event_name(
    value: Any,
) -> str:

    return (
        safe_text(value)
        .casefold()
        .strip()
    )


def get_unique_events(
    events: Any,
) -> List[Dict[str, Any]]:

    if not isinstance(events, list):
        return []

    seen = set()
    unique = []

    for event in events:

        if not isinstance(event, dict):
            continue

        name = normalize_event_name(
            get_event_name(event)
        )

        if not name or name in seen:
            continue

        seen.add(name)
        unique.append(event)

    return unique


def render_html(
    markup: str,
) -> None:

    clean_markup = textwrap.dedent(
        markup
    ).strip()

    st.html(clean_markup)


# ===========================================================
# Cached Application Data
# ===========================================================

@st.cache_data(show_spinner=False)
def get_application_data() -> Dict[str, Any]:

    data = load_application_data()

    if isinstance(data, dict):
        return data

    return {}


# ===========================================================
# Unified Event Intelligence Card
# ===========================================================

def render_event_intelligence_card(
    event: Dict[str, Any],
    label: str,
    has_date_intelligence: bool,
    show_adjustments: bool = True,
) -> None:

    if not isinstance(event, dict):
        return

    event_name = safe_html(
        get_event_name(event)
    )

    category = safe_html(
        get_event_category(event)
    )

    card_label = safe_html(label)

    score = safe_float(
        event.get("final_score")
    )

    llm_adjustment = safe_float(
        event.get("llm_adjustment")
    )

    learning_adjustment = safe_float(
        event.get("learning_adjustment")
    )

    est_budget = safe_html(event.get("estimated_budget_range", "INR 3,000 - 8,000"))
    suggested_vendors = safe_html(event.get("suggested_vendor_categories", "None"))
    suggested_mats = safe_html(event.get("suggested_materials", "None"))
    ticket_rec = safe_html(event.get("ticket_recommendation", "Free"))
    
    ai_explanation = safe_html(event.get("explanation", ""))
    if not ai_explanation and event.get("llm_reasoning"):
        ai_explanation = safe_html(" ".join(event.get("llm_reasoning")))
    if not ai_explanation:
        ai_explanation = "This event fits property demographics and matches historically active community preferences."

    # -------------------------------------------------------
    # Standard Recommendation Card
    # -------------------------------------------------------

    if not has_date_intelligence:

        if (
            show_adjustments
            and (
                "llm_adjustment" in event
                or "learning_adjustment" in event
            )
        ):

            adjustment_html = f"""
            <div class="score-grid">
                <div>
                    <div class="score-label">
                        FINAL SCORE
                    </div>
                    <div class="score-value">
                        {score:.2f}
                    </div>
                </div>

                <div>
                    <div class="score-label">
                        AI ADJUSTMENT
                    </div>
                    <div class="score-value-green">
                        {llm_adjustment:+.2f}
                    </div>
                </div>

                <div>
                    <div class="score-label">
                        LEARNING
                    </div>
                    <div class="score-value-purple">
                        {learning_adjustment:+.2f}
                    </div>
                </div>
            </div>
            """

        else:

            adjustment_html = f"""
            <div class="score-grid">
                <div>
                    <div class="score-label">
                        FINAL SCORE
                    </div>
                    <div class="score-value">
                        {score:.2f}
                    </div>
                </div>
            </div>
            """

        render_html(
            f"""
            <div class="recommendation-card">
                <div class="recommendation-label">
                    {card_label}
                </div>

                <div class="recommendation-name">
                    {event_name}
                </div>

                <div class="recommendation-category">
                    {category}
                </div>

                {adjustment_html}

                <div style="
                    margin-top:1.15rem;
                    padding:0.95rem 1rem;
                    border-radius:0.8rem;
                    background:rgba(128,128,128,0.08);
                ">
                    <div class="score-label">
                        AI EXPLANATION
                    </div>
                    <div style="
                        margin-top:0.35rem;
                        line-height:1.5;
                        font-size:0.95rem;
                    ">
                        {ai_explanation}
                    </div>
                </div>

                <div style="
                    display:grid;
                    grid-template-columns:repeat(2,minmax(0,1fr));
                    gap:0.9rem;
                    margin-top:1.25rem;
                    padding-top:1rem;
                    border-top:1px solid rgba(128,128,128,0.18);
                ">
                    <div>
                        <div class="score-label">
                            ESTIMATED BUDGET
                        </div>
                        <div style="font-weight:700; font-size:0.95rem;">
                            {est_budget}
                        </div>
                    </div>

                    <div>
                        <div class="score-label">
                            TICKET RECOMMENDATION
                        </div>
                        <div style="font-weight:700; font-size:0.95rem;">
                            {ticket_rec}
                        </div>
                    </div>

                    <div>
                        <div class="score-label">
                            SUGGESTED VENDORS
                        </div>
                        <div style="font-weight:700; font-size:0.85rem; opacity:0.85;">
                            {suggested_vendors}
                        </div>
                    </div>

                    <div>
                        <div class="score-label">
                            SUGGESTED MATERIALS
                        </div>
                        <div style="font-weight:700; font-size:0.85rem; opacity:0.85;">
                            {suggested_mats}
                        </div>
                    </div>
                </div>
            </div>
            """
        )

        return

    # -------------------------------------------------------
    # Date-Aware Event Intelligence Card
    # -------------------------------------------------------

    formatted_event_date = safe_html(
        event.get("formatted_event_date"),
        safe_text(
            event.get("event_date"),
            "Not available",
        ),
    )

    date_context = safe_html(
        event.get("date_context"),
        safe_text(
            event.get("weekday"),
            "Date intelligence available",
        ),
    )

    date_reason = safe_html(
        event.get("date_reason"),
        (
            "Selected using event fit, occupancy, "
            "attendance potential and conflict-free "
            "schedule spacing."
        ),
    )

    active_residents = safe_int(
        event.get("active_residents")
    )

    occupancy_percent = safe_float(
        event.get("occupancy_percent")
    )

    predicted_attendance = safe_int(
        event.get("predicted_attendance")
    )

    predicted_turnout_rate = safe_float(
        event.get("predicted_turnout_rate")
    )

    confidence = safe_html(
        event.get("attendance_confidence"),
        "Low",
    )

    confidence_score = safe_float(
        event.get(
            "attendance_confidence_score"
        )
    )

    date_suitability_score = safe_float(
        event.get("date_suitability_score")
    )

    render_html(
        f"""
        <div class="recommendation-card">

            <div style="
                display:flex;
                justify-content:space-between;
                align-items:flex-start;
                gap:1rem;
            ">
                <div>
                    <div class="recommendation-label">
                        {card_label}
                    </div>

                    <div class="recommendation-name">
                        {event_name}
                    </div>

                    <div class="recommendation-category">
                        {category}
                    </div>
                </div>

                <div style="text-align:right;">
                    <div class="score-label">
                        SCORE
                    </div>

                    <div class="score-value">
                        {score:.1f}
                    </div>
                </div>
            </div>

            <div style="
                margin-top:1.35rem;
                padding-top:1.15rem;
                border-top:1px solid rgba(128,128,128,0.22);
            ">
                <div class="score-label">
                    BEST DATE
                </div>

                <div style="
                    font-size:1.35rem;
                    font-weight:700;
                    margin-top:0.25rem;
                ">
                    {formatted_event_date}
                </div>

                <div style="
                    margin-top:0.3rem;
                    opacity:0.78;
                ">
                    {date_context}
                </div>
            </div>

            <div style="
                display:grid;
                grid-template-columns:repeat(2,minmax(0,1fr));
                gap:0.9rem;
                margin-top:1.25rem;
            ">
                <div>
                    <div class="score-label">
                        OCCUPANCY
                    </div>
                    <div class="score-value">
                        {occupancy_percent:.1f}%
                    </div>
                </div>

                <div>
                    <div class="score-label">
                        ACTIVE RESIDENTS
                    </div>
                    <div class="score-value">
                        {active_residents:,}
                    </div>
                </div>

                <div>
                    <div class="score-label">
                        EXPECTED
                    </div>
                    <div class="score-value">
                        {predicted_attendance:,}
                    </div>
                </div>

                <div>
                    <div class="score-label">
                        TURNOUT
                    </div>
                    <div class="score-value">
                        {predicted_turnout_rate:.1f}%
                    </div>
                </div>
            </div>

            <div style="
                display:flex;
                justify-content:space-between;
                gap:1rem;
                flex-wrap:wrap;
                margin-top:1.15rem;
                padding-top:1rem;
                border-top:1px solid rgba(128,128,128,0.18);
            ">
                <div>
                    <div class="score-label">
                        CONFIDENCE
                    </div>
                    <div style="font-weight:700;">
                        {confidence} ({confidence_score:.1f})
                    </div>
                </div>

                <div style="text-align:right;">
                    <div class="score-label">
                        DATE SUITABILITY
                    </div>
                    <div style="font-weight:700;">
                        {date_suitability_score:.1f}
                    </div>
                </div>
            </div>

            <div style="
                margin-top:1.15rem;
                padding:0.95rem 1rem;
                border-radius:0.8rem;
                background:rgba(128,128,128,0.08);
            ">
                <div class="score-label">
                    AI EXPLANATION
                </div>

                <div style="
                    margin-top:0.35rem;
                    line-height:1.5;
                    font-size:0.95rem;
                ">
                    {ai_explanation}
                </div>
            </div>

            <div style="
                display:grid;
                grid-template-columns:repeat(2,minmax(0,1fr));
                gap:0.9rem;
                margin-top:1.25rem;
                padding-top:1rem;
                border-top:1px solid rgba(128,128,128,0.18);
            ">
                <div>
                    <div class="score-label">
                        ESTIMATED BUDGET
                    </div>
                    <div style="font-weight:700; font-size:0.95rem;">
                        {est_budget}
                    </div>
                </div>

                <div>
                    <div class="score-label">
                        TICKET RECOMMENDATION
                    </div>
                    <div style="font-weight:700; font-size:0.95rem;">
                        {ticket_rec}
                    </div>
                </div>

                <div>
                    <div class="score-label">
                        SUGGESTED VENDORS
                    </div>
                    <div style="font-weight:700; font-size:0.85rem; opacity:0.85;">
                        {suggested_vendors}
                    </div>
                </div>

                <div>
                    <div class="score-label">
                        SUGGESTED MATERIALS
                    </div>
                    <div style="font-weight:700; font-size:0.85rem; opacity:0.85;">
                        {suggested_mats}
                    </div>
                </div>
            </div>

            <div style="
                margin-top:1.15rem;
                padding:0.95rem 1rem;
                border-radius:0.8rem;
                background:rgba(128,128,128,0.08);
            ">
                <div class="score-label">
                    WHY THIS DATE?
                </div>

                <div style="
                    margin-top:0.35rem;
                    line-height:1.5;
                    font-size:0.95rem;
                ">
                    {date_reason}
                </div>
            </div>

        </div>
        """
    )


# ===========================================================
# Monthly Schedule Summary
# ===========================================================

def render_schedule_summary(
    dated_result: Dict[str, Any],
) -> None:

    if not isinstance(dated_result, dict):
        return

    if (
        dated_result.get("date_mode")
        != "conflict_free_monthly_schedule"
    ):
        return

    scheduled_event_count = safe_int(
        dated_result.get("scheduled_event_count")
    )

    unique_date_count = safe_int(
        dated_result.get("unique_date_count")
    )

    conflict_free = bool(
        dated_result.get("schedule_conflict_free")
    )

    schedule_month = safe_int(
        dated_result.get("schedule_month")
    )

    schedule_year = safe_int(
        dated_result.get("schedule_year")
    )

    month_label = ""

    if schedule_month and schedule_year:

        try:
            month_label = date(
                schedule_year,
                schedule_month,
                1,
            ).strftime("%B %Y")

        except ValueError:
            month_label = ""

    metric_row([
        {
            "title": "Schedule Status",
            "value": (
                "Conflict-Free"
                if conflict_free
                else "Review Needed"
            ),
        },
        {
            "title": "Events Scheduled",
            "value": scheduled_event_count,
        },
        {
            "title": "Unique Dates",
            "value": unique_date_count,
        },
        {
            "title": "Schedule Month",
            "value": (
                month_label
                or "Selected Month"
            ),
        },
    ])

    if conflict_free:
        st.success(
            "Every recommended event has a unique "
            "date in the monthly schedule."
        )

    else:
        st.warning(
            "The generated schedule contains a date "
            "conflict and should be reviewed."
        )


# ===========================================================
# Ranking Table
# ===========================================================

def build_ranking_dataframe(
    result: Dict[str, Any],
) -> pd.DataFrame:

    if not isinstance(result, dict):
        return pd.DataFrame()

    rows = []

    candidates = safe_list(
        result.get("ranked_candidates")
    )

    seen_events = set()

    for candidate in candidates:

        if not isinstance(candidate, dict):
            continue

        event_name = get_event_name(
            candidate
        )

        normalized_name = (
            normalize_event_name(event_name)
        )

        if not normalized_name:
            continue

        if normalized_name in seen_events:
            continue

        seen_events.add(normalized_name)

        rows.append({
            "Rank": len(rows) + 1,
            "Event": event_name,
            "Category": get_event_category(
                candidate
            ),
            "Final Score": safe_float(
                candidate.get("final_score")
            ),
            "AI Adjustment": safe_float(
                candidate.get("llm_adjustment")
            ),
            "Learning Adjustment": safe_float(
                candidate.get(
                    "learning_adjustment"
                )
            ),
        })

    return pd.DataFrame(rows)


# ===========================================================
# Page Header
# ===========================================================

page_header(
    "🎯 Smart Recommendations",
    "Generate property-specific event recommendations using "
    "resident affinity, collaborative intelligence, continuous "
    "learning, NVIDIA-powered AI reranking, occupancy forecasting "
    "and attendance prediction.",
)


# ===========================================================
# Load Backend Data
# ===========================================================

try:
    application_data = get_application_data()

except Exception as error:
    st.error(
        f"Unable to load application data: {error}"
    )
    st.stop()


if not isinstance(application_data, dict):
    st.error(
        "Application data did not return "
        "a valid dictionary."
    )
    st.stop()


data_errors = validate_application_data(
    application_data
)

if data_errors:

    for error in data_errors:
        st.error(error)

    st.stop()


profiles = application_data.get("profiles")

if not isinstance(profiles, dict):
    profiles = {}


property_names = sorted(
    profiles.keys()
)

if not property_names:
    st.error(
        "No property profiles are available."
    )
    st.stop()


history = application_data.get(
    "history",
    pd.DataFrame(),
)

if not isinstance(history, pd.DataFrame):
    history = pd.DataFrame()


# ===========================================================
# Property Selection
# ===========================================================

previous_property = get_session_property(
    st.session_state
)

default_index = 0

if previous_property in property_names:
    default_index = property_names.index(
        previous_property
    )


selected_property = st.selectbox(
    "Select Property",
    options=property_names,
    index=default_index,
)


# ===========================================================
# Generate Recommendations
# ===========================================================

generate_clicked = st.button(
    "Generate Recommendations",
    type="primary",
    use_container_width=True,
    disabled=bool(
        st.session_state.get(
            SESSION_RUNNING_KEY,
            False,
        )
    ),
)


if generate_clicked:

    st.session_state[
        SESSION_RUNNING_KEY
    ] = True

    st.session_state[
        SESSION_ERROR_KEY
    ] = ""

    st.session_state.pop(
        DATED_RESULT_KEY,
        None,
    )

    st.session_state.pop(
        DATED_RESULT_SOURCE_KEY,
        None,
    )

    try:

        with st.spinner(
            "Running the complete recommendation "
            "intelligence pipeline..."
        ):

            generated_result = (
                generate_property_recommendations(
                    property_name=selected_property,
                    data=application_data,
                    use_llm=True,
                    use_learning=True,
                    save_signals=True,
                )
            )

            if not isinstance(
                generated_result,
                dict,
            ):
                raise TypeError(
                    "Recommendation pipeline returned "
                    "an invalid result."
                )

            save_result_to_session(
                session_state=st.session_state,
                result=generated_result,
            )
            save_predictions_to_csv(generated_result)

    except Exception as error:

        save_error_to_session(
            session_state=st.session_state,
            error=error,
        )

    finally:

        st.session_state[
            SESSION_RUNNING_KEY
        ] = False


# ===========================================================
# Error State
# ===========================================================

recommendation_error = (
    st.session_state.get(
        SESSION_ERROR_KEY,
        "",
    )
)

if recommendation_error:
    st.error(
        "Recommendation pipeline failed: "
        f"{recommendation_error}"
    )


# ===========================================================
# Recommendation Results
# ===========================================================

raw_result = get_session_result(
    st.session_state
)

if not isinstance(raw_result, dict) or not raw_result:

    st.info(
        "Select a property and click "
        "'Generate Recommendations' to run the "
        "complete backend intelligence pipeline."
    )

    st.stop()


result = raw_result

result_property = safe_text(
    result.get("property_name"),
    selected_property,
)


# ===========================================================
# Recommendation Summary
# ===========================================================

st.divider()

section_header(
    f"Recommendations for {result_property}"
)

pipeline_data = result.get("pipeline")

if not isinstance(pipeline_data, dict):
    pipeline_data = {}

llm_reranking_active = bool(
    pipeline_data.get(
        "llm_reranking",
        False,
    )
)

metric_row([
    {
        "title": "Candidates Evaluated",
        "value": safe_int(
            result.get("candidate_count")
        ),
    },
    {
        "title": "Events Selected",
        "value": safe_int(
            result.get("selected_count")
        ),
    },
    {
        "title": "AI Reranking",
        "value": (
            "Active"
            if llm_reranking_active
            else "Inactive"
        ),
    },
])


# ===========================================================
# Date Planning Controls
# ===========================================================

st.html(
    "<br>",
)

section_header(
    "Event Date Intelligence"
)

st.caption(
    "Choose a specific event date or allow TribeIQ "
    "to identify the strongest date in a selected month "
    "using predicted occupancy and attendance."
)

date_mode = st.radio(
    "Date Planning Mode",
    options=(
        "Choose a specific date",
        "Recommend the best date",
    ),
    horizontal=True,
    key=DATE_MODE_KEY,
)

today = date.today()


# ===========================================================
# Manual Date Mode
# ===========================================================

if date_mode == "Choose a specific date":

    stored_manual_date = (
        st.session_state.get(
            MANUAL_DATE_KEY
        )
    )

    if not isinstance(
        stored_manual_date,
        date,
    ):
        stored_manual_date = today

    if stored_manual_date < today:
        stored_manual_date = today

    selected_event_date = st.date_input(
        "Event Date",
        value=stored_manual_date,
        min_value=today,
        key=MANUAL_DATE_KEY,
    )

    expected_source = (
        f"manual:"
        f"{selected_event_date.isoformat()}"
    )

    stored_source = (
        st.session_state.get(
            DATED_RESULT_SOURCE_KEY,
            "",
        )
    )

    if (
        stored_source
        and stored_source != expected_source
    ):

        st.session_state.pop(
            DATED_RESULT_KEY,
            None,
        )

        st.session_state.pop(
            DATED_RESULT_SOURCE_KEY,
            None,
        )

    apply_date_clicked = st.button(
        "Calculate Occupancy and Attendance",
        type="primary",
        use_container_width=True,
    )

    if apply_date_clicked:

        try:

            with st.spinner(
                "Calculating event-date occupancy "
                "and attendance predictions..."
            ):

                generated_dated_result = (
                    enrich_recommendation_result_for_date(
                        recommendation_result=result,
                        property_name=result_property,
                        event_date=selected_event_date,
                        history=history,
                    )
                )

                if not isinstance(
                    generated_dated_result,
                    dict,
                ):
                    raise TypeError(
                        "Date intelligence returned "
                        "an invalid result."
                    )

                st.session_state[
                    DATED_RESULT_KEY
                ] = generated_dated_result
                save_predictions_to_csv(generated_dated_result)

                st.session_state[
                    DATED_RESULT_SOURCE_KEY
                ] = expected_source

        except Exception as error:

            st.session_state.pop(
                DATED_RESULT_KEY,
                None,
            )

            st.error(
                "Unable to calculate date intelligence: "
                f"{error}"
            )


# ===========================================================
# Best Date Mode
# ===========================================================

else:

    current_month_start = date(
        today.year,
        today.month,
        1,
    )

    stored_forecast_month = (
        st.session_state.get(
            FORECAST_MONTH_KEY
        )
    )

    if not isinstance(
        stored_forecast_month,
        date,
    ):
        stored_forecast_month = (
            current_month_start
        )

    if (
        stored_forecast_month
        < current_month_start
    ):
        stored_forecast_month = (
            current_month_start
        )

    selected_month = st.date_input(
        "Select Month",
        value=stored_forecast_month,
        min_value=current_month_start,
        key=FORECAST_MONTH_KEY,
    )

    expected_source = (
        f"best:"
        f"{selected_month.year}-"
        f"{selected_month.month:02d}"
    )

    stored_source = (
        st.session_state.get(
            DATED_RESULT_SOURCE_KEY,
            "",
        )
    )

    if (
        stored_source
        and stored_source != expected_source
    ):

        st.session_state.pop(
            DATED_RESULT_KEY,
            None,
        )

        st.session_state.pop(
            DATED_RESULT_SOURCE_KEY,
            None,
        )

    find_best_date_clicked = st.button(
        "Find Best Event Dates",
        type="primary",
        use_container_width=True,
    )

    if find_best_date_clicked:

        forecast_start_date: Optional[
            date
        ] = None

        if (
            selected_month.year == today.year
            and selected_month.month == today.month
        ):
            forecast_start_date = today

        try:

            with st.spinner(
                "Forecasting occupancy and ranking "
                "the best event dates..."
            ):

                generated_dated_result = (
                    enrich_recommendation_result_with_best_dates(
                        recommendation_result=result,
                        property_name=result_property,
                        year=selected_month.year,
                        month=selected_month.month,
                        history=history,
                        start_date=forecast_start_date,
                    )
                )

                if not isinstance(
                    generated_dated_result,
                    dict,
                ):
                    raise TypeError(
                        "Best-date intelligence returned "
                        "an invalid result."
                    )

                st.session_state[
                    DATED_RESULT_KEY
                ] = generated_dated_result
                save_predictions_to_csv(generated_dated_result)

                st.session_state[
                    DATED_RESULT_SOURCE_KEY
                ] = expected_source

        except Exception as error:

            st.session_state.pop(
                DATED_RESULT_KEY,
                None,
            )

            st.error(
                "Unable to find the best event dates: "
                f"{error}"
            )


# ===========================================================
# Select Result for Rendering
# ===========================================================

raw_dated_result = (
    st.session_state.get(
        DATED_RESULT_KEY
    )
)

dated_result = (
    raw_dated_result
    if isinstance(
        raw_dated_result,
        dict,
    )
    else None
)

display_result = (
    dated_result
    if dated_result is not None
    else result
)

if not isinstance(display_result, dict):
    display_result = {}

has_date_intelligence = (
    dated_result is not None
)


# ===========================================================
# Monthly Schedule Summary
# ===========================================================

if has_date_intelligence:

    render_schedule_summary(
        dated_result
    )


# ===========================================================
# Major Event
# ===========================================================

st.html(
    "<br>",
)

major_event = display_result.get(
    "major_event"
)

if not isinstance(major_event, dict):
    major_event = None

if major_event is not None:

    section_header(
        "Major Event"
    )

    render_event_intelligence_card(
        event=major_event,
        label="Major Event",
        has_date_intelligence=(
            has_date_intelligence
        ),
        show_adjustments=(
            not has_date_intelligence
        ),
    )


# ===========================================================
# Minor Events
# ===========================================================

minor_events = get_unique_events(
    display_result.get(
        "minor_events"
    )
)

major_event_name = ""

if isinstance(major_event, dict):

    major_event_name = (
        normalize_event_name(
            get_event_name(
                major_event
            )
        )
    )

minor_events = [
    event
    for event in minor_events
    if normalize_event_name(
        get_event_name(event)
    ) != major_event_name
]

if minor_events:

    st.html(
        "<br>",
    )

    section_header(
        "Minor Events"
    )

    for index, event in enumerate(
        minor_events,
        start=1,
    ):

        render_event_intelligence_card(
            event=event,
            label=f"Minor Event {index}",
            has_date_intelligence=(
                has_date_intelligence
            ),
            show_adjustments=(
                not has_date_intelligence
            ),
        )

        if index < len(minor_events):

            st.html(
                "<br>",
            )


# ===========================================================
# Empty Recommendation State
# ===========================================================

if (
    major_event is None
    and not minor_events
):

    st.warning(
        "The recommendation pipeline completed, "
        "but no valid event recommendations were returned."
    )


# ===========================================================
# Full Candidate Ranking
# ===========================================================

ranking_dataframe = (
    build_ranking_dataframe(
        result
    )
)

if not ranking_dataframe.empty:

    st.html(
        "<br>",
    )

    with st.expander(
        "View Full Candidate Ranking"
    ):

        st.dataframe(
            ranking_dataframe,
            width="stretch",
            hide_index=True,
        )