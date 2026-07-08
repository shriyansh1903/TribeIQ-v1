"""
===========================================================
TribeIQ Recommendation Date Bridge
===========================================================

Conflict-free monthly event scheduling bridge.

Responsibilities:
1. Enrich events with future occupancy intelligence
2. Predict attendance for the assigned event date
3. Score dates differently for different event types
4. Assign one unique date to every selected event
5. Deliberately spread major and minor events
6. Preserve manual-date and single-event APIs
7. Return card-ready date intelligence

Current scheduling signals:
- Predicted attendance
- Future occupancy
- Attendance confidence
- Event-specific weekday/weekend suitability
- Schedule spacing
- Unique-date enforcement

Holiday and weather signals will be added as the next
dedicated scheduling layer.
===========================================================
"""

from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import pandas as pd


# ===========================================================
# Project Paths
# ===========================================================

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
INTELLIGENCE_DIR = CURRENT_DIR / "intelligence"

for path in (
    PROJECT_ROOT,
    CURRENT_DIR,
    INTELLIGENCE_DIR,
):
    path_string = str(path.resolve())

    if path_string not in sys.path:
        sys.path.insert(0, path_string)


# ===========================================================
# Intelligence Imports
# ===========================================================

try:
    from intelligence.occupancy_forecaster import (
        forecast_property_occupancy,
        load_resident_export,
        normalize_property_name,
        parse_event_date,
    )

    from intelligence.attendance_predictor import (
        predict_event_attendance,
        rank_best_event_dates,
    )

except ModuleNotFoundError:
    from occupancy_forecaster import (
        forecast_property_occupancy,
        load_resident_export,
        normalize_property_name,
        parse_event_date,
    )

    from attendance_predictor import (
        predict_event_attendance,
        rank_best_event_dates,
    )


# ===========================================================
# Type Aliases
# ===========================================================

DateLike = Union[
    str,
    date,
    datetime,
    pd.Timestamp,
]


# ===========================================================
# Scheduler Configuration
# ===========================================================

DEFAULT_MINIMUM_SPACING_DAYS = 3

MAJOR_EVENT_SPACING_DAYS = 5

DATE_CANDIDATE_LIMIT = 31


# ===========================================================
# Resident Timeline Cache
# ===========================================================

_RESIDENT_CACHE: Optional[pd.DataFrame] = None


def _get_residents() -> pd.DataFrame:
    global _RESIDENT_CACHE

    if _RESIDENT_CACHE is None:
        _RESIDENT_CACHE = load_resident_export()

    return _RESIDENT_CACHE.copy()


# ===========================================================
# Basic Helpers
# ===========================================================

def _safe_text(value: Any) -> str:
    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass

    return str(value).strip()


def _safe_int(
    value: Any,
    default: int = 0,
) -> int:
    try:
        numeric = float(value)

        if pd.isna(numeric):
            return default

        return int(round(numeric))

    except (TypeError, ValueError):
        return default


def _safe_float(
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


def _normalize_text(value: Any) -> str:
    return (
        _safe_text(value)
        .casefold()
        .replace("_", " ")
        .replace("-", " ")
        .strip()
    )


def _empty_history() -> pd.DataFrame:
    return pd.DataFrame()


def _normalize_history(
    history: Optional[pd.DataFrame],
) -> pd.DataFrame:
    if isinstance(history, pd.DataFrame):
        return history.copy()

    return _empty_history()


def _event_identity(
    event: Dict[str, Any],
) -> str:
    event_id = _safe_text(
        event.get("event_id")
    )

    if event_id:
        return event_id.casefold()

    return (
        f"{_safe_text(event.get('event_name')).casefold()}"
        f"|{_safe_text(event.get('category')).casefold()}"
    )


def _valid_event(
    event: Any,
) -> bool:
    return (
        isinstance(event, dict)
        and bool(
            _safe_text(
                event.get("event_name")
            )
        )
    )


# ===========================================================
# Event Date Preference Intelligence
# ===========================================================

def _event_preference_profile(
    event: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build a lightweight event-specific date preference.

    This is intentionally deterministic.

    Holiday and weather intelligence will be added later
    without changing the public scheduling API.
    """

    event_name = _normalize_text(
        event.get("event_name")
    )

    category = _normalize_text(
        event.get("category")
    )

    combined = (
        f"{event_name} {category}"
    )

    outdoor_terms = (
        "outdoor",
        "garden",
        "picnic",
        "walk",
        "hike",
        "sports",
        "sport",
        "fitness",
        "run",
        "running",
        "cycling",
        "bike",
        "barbecue",
        "bbq",
        "festival",
        "market",
    )

    social_terms = (
        "social",
        "mixer",
        "party",
        "movie",
        "game night",
        "quiz",
        "trivia",
        "celebration",
        "dinner",
        "brunch",
        "community",
    )

    workshop_terms = (
        "workshop",
        "class",
        "training",
        "seminar",
        "career",
        "study",
        "skill",
        "education",
        "learning",
    )

    wellness_terms = (
        "wellness",
        "yoga",
        "meditation",
        "mindfulness",
        "fitness",
        "health",
    )

    if any(
        term in combined
        for term in outdoor_terms
    ):
        return {
            "profile":
                "outdoor",
            "preferred_weekdays":
                {5, 6},
            "acceptable_weekdays":
                {4},
            "preference_reason":
                "Weekend fit for an outdoor activity",
        }

    if any(
        term in combined
        for term in social_terms
    ):
        return {
            "profile":
                "social",
            "preferred_weekdays":
                {4, 5},
            "acceptable_weekdays":
                {3, 6},
            "preference_reason":
                "Strong end-of-week and weekend social fit",
        }

    if any(
        term in combined
        for term in workshop_terms
    ):
        return {
            "profile":
                "workshop",
            "preferred_weekdays":
                {1, 2, 3},
            "acceptable_weekdays":
                {0, 4},
            "preference_reason":
                "Strong workday fit for a structured activity",
        }

    if any(
        term in combined
        for term in wellness_terms
    ):
        return {
            "profile":
                "wellness",
            "preferred_weekdays":
                {5, 6},
            "acceptable_weekdays":
                {1, 2, 3},
            "preference_reason":
                "Good weekend and midweek wellness fit",
        }

    return {
        "profile":
            "general",
        "preferred_weekdays":
            {4, 5, 6},
        "acceptable_weekdays":
            {2, 3},
        "preference_reason":
            "Good late-week and weekend community fit",
    }


def _weekday_fit_score(
    event: Dict[str, Any],
    event_date: pd.Timestamp,
) -> Tuple[float, str]:
    preference = (
        _event_preference_profile(event)
    )

    weekday_number = (
        event_date.weekday()
    )

    preferred = preference[
        "preferred_weekdays"
    ]

    acceptable = preference[
        "acceptable_weekdays"
    ]

    if weekday_number in preferred:
        return (
            100.0,
            preference[
                "preference_reason"
            ],
        )

    if weekday_number in acceptable:
        return (
            72.0,
            (
                f"Acceptable {event_date.day_name()} "
                "fit for this event"
            ),
        )

    return (
        38.0,
        (
            f"Lower {event_date.day_name()} "
            "fit for this event"
        ),
    )


# ===========================================================
# Candidate Date Scoring
# ===========================================================

def _score_candidate_date(
    event: Dict[str, Any],
    row: pd.Series,
) -> Dict[str, Any]:
    target_date = parse_event_date(
        row.get("event_date")
    )

    weekday_fit, weekday_reason = (
        _weekday_fit_score(
            event=event,
            event_date=target_date,
        )
    )

    active_residents = _safe_int(
        row.get("active_residents")
    )

    total_capacity = _safe_int(
        row.get("total_capacity")
    )

    occupancy_percent = _safe_float(
        row.get("occupancy_percent")
    )

    predicted_attendance = _safe_int(
        row.get("predicted_attendance")
    )

    turnout_percent = _safe_float(
        row.get("predicted_turnout_rate")
    )

    confidence_score = _safe_float(
        row.get("confidence_score")
    )

    if active_residents > 0:
        attendance_population_score = (
            predicted_attendance
            / active_residents
            * 100.0
        )
    else:
        attendance_population_score = 0.0

    schedule_score = (
        attendance_population_score * 0.30
        + occupancy_percent * 0.30
        + weekday_fit * 0.30
        + confidence_score * 0.10
    )

    return {
        "event_date":
            target_date,
        "weekday":
            target_date.day_name(),
        "total_capacity":
            total_capacity,
        "active_residents":
            active_residents,
        "occupancy_percent":
            round(
                occupancy_percent,
                2,
            ),
        "predicted_turnout_rate":
            round(
                turnout_percent,
                2,
            ),
        "predicted_attendance":
            predicted_attendance,
        "confidence_score":
            round(
                confidence_score,
                1,
            ),
        "confidence_label":
            _safe_text(
                row.get(
                    "confidence_label",
                    "Low",
                )
            ),
        "weekday_fit_score":
            round(
                weekday_fit,
                1,
            ),
        "date_suitability_score":
            round(
                schedule_score,
                2,
            ),
        "weekday_reason":
            weekday_reason,
    }


def _build_event_date_candidates(
    event: Dict[str, Any],
    property_name: str,
    year: int,
    month: int,
    history: Optional[pd.DataFrame],
    start_date: Optional[DateLike],
) -> List[Dict[str, Any]]:
    residents = _get_residents()

    event_history = _normalize_history(
        history
    )

    ranked_dates = rank_best_event_dates(
        residents=residents,
        history=event_history,
        property_name=property_name,
        event_name=_safe_text(
            event.get("event_name")
        ),
        category=_safe_text(
            event.get("category")
        ),
        year=int(year),
        month=int(month),
        start_date=start_date,
        top_n=DATE_CANDIDATE_LIMIT,
    )

    if ranked_dates.empty:
        return []

    candidates = []

    for _, row in ranked_dates.iterrows():
        candidates.append(
            _score_candidate_date(
                event=event,
                row=row,
            )
        )

    candidates.sort(
        key=lambda item: (
            -item[
                "date_suitability_score"
            ],
            -item[
                "predicted_attendance"
            ],
            -item[
                "occupancy_percent"
            ],
            item[
                "event_date"
            ],
        )
    )

    for index, candidate in enumerate(
        candidates,
        start=1,
    ):
        candidate[
            "event_candidate_rank"
        ] = index

    return candidates


# ===========================================================
# Conflict And Spacing Helpers
# ===========================================================

def _days_from_assigned_dates(
    target_date: pd.Timestamp,
    assigned_dates: List[pd.Timestamp],
) -> List[int]:
    return [
        abs(
            (
                target_date.normalize()
                - assigned.normalize()
            ).days
        )
        for assigned in assigned_dates
    ]


def _is_date_available(
    target_date: pd.Timestamp,
    used_dates: Set[str],
) -> bool:
    return (
        target_date.date().isoformat()
        not in used_dates
    )


def _meets_spacing(
    target_date: pd.Timestamp,
    assigned_dates: List[pd.Timestamp],
    minimum_spacing_days: int,
) -> bool:
    if not assigned_dates:
        return True

    distances = _days_from_assigned_dates(
        target_date,
        assigned_dates,
    )

    return all(
        distance >= minimum_spacing_days
        for distance in distances
    )


def _spacing_bonus(
    target_date: pd.Timestamp,
    assigned_dates: List[pd.Timestamp],
) -> float:
    if not assigned_dates:
        return 100.0

    distances = _days_from_assigned_dates(
        target_date,
        assigned_dates,
    )

    nearest_distance = min(
        distances
    )

    return min(
        nearest_distance * 12.5,
        100.0,
    )


# ===========================================================
# Card-Ready Result Builder
# ===========================================================

def _build_scheduled_event_result(
    event: Dict[str, Any],
    candidate: Dict[str, Any],
    schedule_rank: int,
) -> Dict[str, Any]:
    target_date = candidate[
        "event_date"
    ]

    occupancy_percent = _safe_float(
        candidate.get(
            "occupancy_percent"
        )
    )

    if occupancy_percent >= 90.0:
        occupancy_context = (
            "High occupancy"
        )
    elif occupancy_percent >= 70.0:
        occupancy_context = (
            "Moderate occupancy"
        )
    else:
        occupancy_context = (
            "Lower occupancy"
        )

    if target_date.weekday() >= 5:
        day_context = "Weekend"
    else:
        day_context = "Workday"

    date_context = (
        f"{day_context} · "
        f"{occupancy_context}"
    )

    date_reason = (
        f"{candidate['weekday_reason']} + "
        f"{occupancy_context.lower()} + "
        "conflict-free schedule spacing"
    )

    return {
        "event_id":
            _safe_text(
                event.get("event_id")
            ),
        "event_name":
            _safe_text(
                event.get("event_name")
            ),
        "category":
            _safe_text(
                event.get("category")
            ),
        "final_score":
            _safe_float(
                event.get("final_score")
            ),
        "event_date":
            target_date
            .date()
            .isoformat(),
        "formatted_event_date":
            target_date.strftime(
                "%A, %d %B %Y"
            ),
        "weekday":
            target_date.day_name(),
        "total_capacity":
            _safe_int(
                candidate.get(
                    "total_capacity"
                )
            ),
        "active_residents":
            _safe_int(
                candidate.get(
                    "active_residents"
                )
            ),
        "occupancy_percent":
            _safe_float(
                candidate.get(
                    "occupancy_percent"
                )
            ),
        "predicted_turnout_rate":
            _safe_float(
                candidate.get(
                    "predicted_turnout_rate"
                )
            ),
        "predicted_attendance":
            _safe_int(
                candidate.get(
                    "predicted_attendance"
                )
            ),
        "attendance_confidence_score":
            _safe_float(
                candidate.get(
                    "confidence_score"
                )
            ),
        "attendance_confidence":
            _safe_text(
                candidate.get(
                    "confidence_label",
                    "Low",
                )
            ),
        "weekday_fit_score":
            _safe_float(
                candidate.get(
                    "weekday_fit_score"
                )
            ),
        "date_suitability_score":
            _safe_float(
                candidate.get(
                    "date_suitability_score"
                )
            ),
        "date_rank":
            _safe_int(
                candidate.get(
                    "event_candidate_rank",
                    1,
                ),
                1,
            ),
        "schedule_rank":
            schedule_rank,
        "date_context":
            date_context,
        "date_reason":
            date_reason,
        "schedule_conflict":
            False,
    }


# ===========================================================
# Core: Enrich Single Event For Manual Date
# ===========================================================

def enrich_event_for_date(
    event: Dict[str, Any],
    property_name: str,
    event_date: DateLike,
    history: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    canonical_property = (
        normalize_property_name(
            property_name
        )
    )

    if not canonical_property:
        raise ValueError(
            f"Unknown property: {property_name}"
        )

    target_date = parse_event_date(
        event_date
    )

    residents = _get_residents()

    event_history = _normalize_history(
        history
    )

    event_name = _safe_text(
        event.get("event_name")
    )

    category = _safe_text(
        event.get("category")
    )

    occupancy = (
        forecast_property_occupancy(
            dataframe=residents,
            property_name=canonical_property,
            event_date=target_date,
        )
    )

    attendance = (
        predict_event_attendance(
            residents=residents,
            history=event_history,
            property_name=canonical_property,
            event_name=event_name,
            category=category,
            event_date=target_date,
        )
    )

    active_residents = _safe_int(
        occupancy.get(
            "active_residents"
        )
    )

    predicted_attendance = min(
        _safe_int(
            attendance.get(
                "predicted_attendance"
            )
        ),
        active_residents,
    )

    weekday_fit, weekday_reason = (
        _weekday_fit_score(
            event=event,
            event_date=target_date,
        )
    )

    occupancy_percent = _safe_float(
        occupancy.get(
            "occupancy_percent"
        )
    )

    return {
        "event_id":
            _safe_text(
                event.get("event_id")
            ),
        "event_name":
            event_name,
        "category":
            category,
        "final_score":
            _safe_float(
                event.get("final_score")
            ),
        "event_date":
            target_date.date().isoformat(),
        "formatted_event_date":
            target_date.strftime(
                "%A, %d %B %Y"
            ),
        "weekday":
            target_date.day_name(),
        "total_capacity":
            _safe_int(
                occupancy.get(
                    "total_capacity"
                )
            ),
        "active_residents":
            active_residents,
        "occupancy_percent":
            occupancy_percent,
        "predicted_turnout_rate":
            _safe_float(
                attendance.get(
                    "predicted_turnout_rate"
                )
            ),
        "predicted_attendance":
            max(
                predicted_attendance,
                0,
            ),
        "attendance_confidence_score":
            _safe_float(
                attendance.get(
                    "confidence_score"
                )
            ),
        "attendance_confidence":
            _safe_text(
                attendance.get(
                    "confidence_label",
                    "Low",
                )
            ),
        "weekday_fit_score":
            weekday_fit,
        "date_suitability_score":
            weekday_fit,
        "date_rank":
            1,
        "date_context":
            (
                "Weekend"
                if target_date.weekday() >= 5
                else "Workday"
            ),
        "date_reason":
            weekday_reason,
        "schedule_conflict":
            False,
    }


# ===========================================================
# Core: Find Best Date For One Event
# ===========================================================

def find_best_date_for_event(
    event: Dict[str, Any],
    property_name: str,
    year: int,
    month: int,
    history: Optional[pd.DataFrame] = None,
    start_date: Optional[DateLike] = None,
) -> Dict[str, Any]:
    canonical_property = (
        normalize_property_name(
            property_name
        )
    )

    if not canonical_property:
        raise ValueError(
            f"Unknown property: {property_name}"
        )

    candidates = (
        _build_event_date_candidates(
            event=event,
            property_name=canonical_property,
            year=year,
            month=month,
            history=history,
            start_date=start_date,
        )
    )

    if not candidates:
        raise ValueError(
            f"No valid dates found for "
            f"{_safe_text(event.get('event_name'))} "
            f"in {year}-{month:02d}."
        )

    return _build_scheduled_event_result(
        event=event,
        candidate=candidates[0],
        schedule_rank=1,
    )


# ===========================================================
# Core: Manual Date Recommendation Enrichment
# ===========================================================

def enrich_recommendation_result_for_date(
    recommendation_result: Dict[str, Any],
    property_name: str,
    event_date: DateLike,
    history: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    major_source = recommendation_result.get(
        "major_event",
        {},
    )

    major_event = (
        enrich_event_for_date(
            event=major_source,
            property_name=property_name,
            event_date=event_date,
            history=history,
        )
        if _valid_event(major_source)
        else {}
    )

    minor_events = []

    for minor in recommendation_result.get(
        "minor_events",
        [],
    ):
        if not _valid_event(minor):
            continue

        minor_events.append(
            enrich_event_for_date(
                event=minor,
                property_name=property_name,
                event_date=event_date,
                history=history,
            )
        )

    return {
        "property_name":
            _safe_text(
                recommendation_result.get(
                    "property_name",
                    property_name,
                )
            ),
        "candidate_count":
            _safe_int(
                recommendation_result.get(
                    "candidate_count"
                )
            ),
        "selected_count":
            _safe_int(
                recommendation_result.get(
                    "selected_count"
                )
            ),
        "date_mode":
            "manual",
        "major_event":
            major_event,
        "minor_events":
            minor_events,
    }


# ===========================================================
# Conflict-Free Monthly Schedule Builder
# ===========================================================

def _select_candidate_for_schedule(
    event: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    used_dates: Set[str],
    assigned_dates: List[pd.Timestamp],
    minimum_spacing_days: int,
) -> Dict[str, Any]:
    if not candidates:
        raise ValueError(
            f"No date candidates available for "
            f"{_safe_text(event.get('event_name'))}."
        )

    unique_candidates = [
        candidate
        for candidate in candidates
        if _is_date_available(
            candidate["event_date"],
            used_dates,
        )
    ]

    if not unique_candidates:
        raise ValueError(
            "The month does not contain enough unique "
            "eligible dates for all selected events."
        )

    spaced_candidates = [
        candidate
        for candidate in unique_candidates
        if _meets_spacing(
            target_date=(
                candidate["event_date"]
            ),
            assigned_dates=assigned_dates,
            minimum_spacing_days=(
                minimum_spacing_days
            ),
        )
    ]

    candidate_pool = (
        spaced_candidates
        if spaced_candidates
        else unique_candidates
    )

    best_candidate = None
    best_schedule_score = None

    for candidate in candidate_pool:
        spacing_score = _spacing_bonus(
            target_date=(
                candidate["event_date"]
            ),
            assigned_dates=assigned_dates,
        )

        combined_schedule_score = (
            candidate[
                "date_suitability_score"
            ] * 0.80
            + spacing_score * 0.20
        )

        if (
            best_candidate is None
            or combined_schedule_score
            > best_schedule_score
        ):
            best_candidate = (
                candidate.copy()
            )

            best_candidate[
                "date_suitability_score"
            ] = round(
                combined_schedule_score,
                2,
            )

            best_schedule_score = (
                combined_schedule_score
            )

    return best_candidate


def enrich_recommendation_result_with_best_dates(
    recommendation_result: Dict[str, Any],
    property_name: str,
    year: int,
    month: int,
    history: Optional[pd.DataFrame] = None,
    start_date: Optional[DateLike] = None,
) -> Dict[str, Any]:
    """
    Build one conflict-free monthly schedule.

    Rules:
    1. Major event is scheduled first.
    2. Every event receives a unique date.
    3. Major event receives wider spacing protection.
    4. Minor events are deliberately spread.
    5. If ideal spacing is impossible, unique dates are
       still guaranteed.
    """

    canonical_property = (
        normalize_property_name(
            property_name
        )
    )

    if not canonical_property:
        raise ValueError(
            f"Unknown property: {property_name}"
        )

    major_source = recommendation_result.get(
        "major_event",
        {},
    )

    minor_sources = [
        event
        for event
        in recommendation_result.get(
            "minor_events",
            [],
        )
        if _valid_event(event)
    ]

    schedule_events = []

    if _valid_event(major_source):
        schedule_events.append(
            (
                "major",
                major_source,
            )
        )

    seen_events = {
        _event_identity(major_source)
    } if _valid_event(major_source) else set()

    for minor in minor_sources:
        identity = _event_identity(
            minor
        )

        if identity in seen_events:
            continue

        seen_events.add(
            identity
        )

        schedule_events.append(
            (
                "minor",
                minor,
            )
        )

    used_dates: Set[str] = set()

    assigned_dates: List[
        pd.Timestamp
    ] = []

    scheduled_major: Dict[
        str,
        Any
    ] = {}

    scheduled_minors: List[
        Dict[str, Any]
    ] = []

    for schedule_rank, (
        event_type,
        event,
    ) in enumerate(
        schedule_events,
        start=1,
    ):
        candidates = (
            _build_event_date_candidates(
                event=event,
                property_name=canonical_property,
                year=int(year),
                month=int(month),
                history=history,
                start_date=start_date,
            )
        )

        minimum_spacing = (
            MAJOR_EVENT_SPACING_DAYS
            if event_type == "major"
            else DEFAULT_MINIMUM_SPACING_DAYS
        )

        selected_candidate = (
            _select_candidate_for_schedule(
                event=event,
                candidates=candidates,
                used_dates=used_dates,
                assigned_dates=assigned_dates,
                minimum_spacing_days=(
                    minimum_spacing
                ),
            )
        )

        selected_date = (
            selected_candidate[
                "event_date"
            ]
        )

        used_dates.add(
            selected_date
            .date()
            .isoformat()
        )

        assigned_dates.append(
            selected_date
        )

        scheduled_event = (
            _build_scheduled_event_result(
                event=event,
                candidate=(
                    selected_candidate
                ),
                schedule_rank=(
                    schedule_rank
                ),
            )
        )

        if event_type == "major":
            scheduled_major = (
                scheduled_event
            )
        else:
            scheduled_minors.append(
                scheduled_event
            )

    all_dates = []

    if scheduled_major:
        all_dates.append(
            scheduled_major[
                "event_date"
            ]
        )

    all_dates.extend(
        event["event_date"]
        for event
        in scheduled_minors
    )

    unique_date_count = len(
        set(all_dates)
    )

    return {
        "property_name":
            _safe_text(
                recommendation_result.get(
                    "property_name",
                    property_name,
                )
            ),
        "candidate_count":
            _safe_int(
                recommendation_result.get(
                    "candidate_count"
                )
            ),
        "selected_count":
            _safe_int(
                recommendation_result.get(
                    "selected_count",
                    len(schedule_events),
                )
            ),
        "date_mode":
            "conflict_free_monthly_schedule",
        "schedule_year":
            int(year),
        "schedule_month":
            int(month),
        "scheduled_event_count":
            len(all_dates),
        "unique_date_count":
            unique_date_count,
        "schedule_conflict_free":
            (
                len(all_dates)
                == unique_date_count
            ),
        "major_event":
            scheduled_major,
        "minor_events":
            scheduled_minors,
    }