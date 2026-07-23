"""
===========================================================
TribeIQ Recommendation Feature Builder
===========================================================

Builds normalized recommendation signals from:

1. Property profiles
2. Event metadata
3. Event history
4. Historical feedback

This module does not rank or select events.
===========================================================
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd

try:
    from recommendation.config import (
        RECENT_EVENT_WINDOW_DAYS,
        REPEAT_FATIGUE_WINDOW_DAYS,
        CATEGORY_SATURATION_WINDOW_DAYS
    )
except ModuleNotFoundError:
    from config import (
        RECENT_EVENT_WINDOW_DAYS,
        REPEAT_FATIGUE_WINDOW_DAYS,
        CATEGORY_SATURATION_WINDOW_DAYS
    )
# ===========================================================
# Generic Helpers
# ===========================================================

def safe_float(
    value: Any,
    default: float = 0.0
) -> float:

    try:

        if pd.isna(value):

            return default

        return float(value)

    except (TypeError, ValueError):

        return default


def safe_text(value: Any) -> str:

    if value is None:

        return ""

    try:

        if pd.isna(value):

            return ""

    except (TypeError, ValueError):

        pass

    return str(value).strip()


def normalize_text(value: Any) -> str:

    return safe_text(value).lower()


def normalize_score(
    value: Any,
    minimum: float = 0.0,
    maximum: float = 100.0
) -> float:

    numeric = safe_float(value)

    if maximum <= minimum:

        return 0.0

    normalized = (

        (numeric - minimum)

        / (maximum - minimum)

    ) * 100.0

    return max(

        0.0,

        min(normalized, 100.0)

    )


def safe_mean(
    values: pd.Series,
    default: float = 0.0
) -> float:

    numeric = pd.to_numeric(

        values,

        errors="coerce"

    ).dropna()

    if numeric.empty:

        return default

    return float(numeric.mean())


# ===========================================================
# Collection Helpers
# ===========================================================

def to_token_set(value: Any) -> set:

    if value is None:
        return set()

    raw_items = []

    if isinstance(value, dict):
        raw_items = [str(k) for k in value.keys()]

    elif isinstance(value, (list, tuple, set)):
        raw_items = [str(k) for k in value]

    else:
        text = safe_text(value)

        if not text:
            return set()

        for sep in [",", ";", "|", "/", "&", "-"]:
            text = text.replace(sep, ",")

        raw_items = [t for t in text.split(",") if t]

    tokens = set()

    for item in raw_items:
        norm = normalize_text(item)

        if norm:
            tokens.add(norm)
            words = [w.strip() for w in norm.split() if len(w.strip()) > 2]

            for w in words:
                tokens.add(w)

                if w.endswith('s') and len(w) > 3:
                    tokens.add(w[:-1])

                if w.endswith('es') and len(w) > 4:
                    tokens.add(w[:-2])

                if w.endswith('ing') and len(w) > 5:
                    tokens.add(w[:-3])

    return tokens


def overlap_score(
    left: Any,
    right: Any
) -> float:

    left_set = to_token_set(left)

    right_set = to_token_set(right)

    if not right_set:
        return 50.0

    if not left_set:
        return 0.0

    overlap = left_set.intersection(
        right_set
    )

    if not overlap:
        return 0.0

    ratio = len(overlap) / float(min(len(left_set), len(right_set)) + 1e-5)

    return min(100.0, max(0.0, ratio * 100.0))


# ===========================================================
# Event Field Helpers
# ===========================================================

def get_event_value(
    event: Dict[str, Any],
    *keys: str,
    default: Any = None
) -> Any:

    for key in keys:

        if key in event:

            value = event[key]

            if value is not None:

                return value

    return default


def get_event_name(
    event: Dict[str, Any]
) -> str:

    return safe_text(

        get_event_value(

            event,

            "Event Name",

            "event_name",

            "name",

            default=""

        )

    )


def get_event_category(
    event: Dict[str, Any]
) -> str:

    return safe_text(

        get_event_value(

            event,

            "Category",

            "category",

            default="Unknown"

        )

    )


# ===========================================================
# History Preparation
# ===========================================================

def prepare_history(
    history: Optional[pd.DataFrame]
) -> pd.DataFrame:

    if history is None:

        return pd.DataFrame()

    if not isinstance(history, pd.DataFrame):

        return pd.DataFrame()

    prepared = history.copy()

    if prepared.empty:

        return prepared

    if "Date" in prepared.columns:

        prepared["Date"] = pd.to_datetime(

            prepared["Date"],

            errors="coerce",

            utc=True

        )

    numeric_columns = [

        "Attendance %",

        "Average Feedback",

        "Success Score",

        "Budget Planned",

        "Budget Spent"

    ]

    for column in numeric_columns:

        if column in prepared.columns:

            prepared[column] = pd.to_numeric(

                prepared[column],

                errors="coerce"

            )

    return prepared


def filter_property_history(
    history: pd.DataFrame,
    property_name: str
) -> pd.DataFrame:

    if history.empty:

        return history.copy()

    if "Property" not in history.columns:

        return pd.DataFrame(

            columns=history.columns

        )

    mask = (

        history["Property"]

        .astype(str)

        .str.strip()

        .str.lower()

        == normalize_text(property_name)

    )

    return history.loc[mask].copy()


def filter_event_history(
    history: pd.DataFrame,
    event_name: str
) -> pd.DataFrame:

    if history.empty:

        return history.copy()

    if "Event Name" not in history.columns:

        return pd.DataFrame(

            columns=history.columns

        )

    mask = (

        history["Event Name"]

        .astype(str)

        .str.strip()

        .str.lower()

        == normalize_text(event_name)

    )

    return history.loc[mask].copy()


# ===========================================================
# Time Features
# ===========================================================

def days_since_last_event(
    property_history: pd.DataFrame,
    event_name: str
) -> Optional[int]:

    event_history = filter_event_history(

        property_history,

        event_name

    )

    if event_history.empty:

        return None

    if "Date" not in event_history.columns:

        return None

    dates = event_history["Date"].dropna()

    if dates.empty:

        return None

    latest = dates.max()

    now = pd.Timestamp.now(

        tz="UTC"

    )

    return max(

        0,

        int(

            (now - latest).days

        )

    )


def count_recent_events(
    property_history: pd.DataFrame,
    window_days: int,
    event_name: Optional[str] = None,
    category: Optional[str] = None
) -> int:

    if property_history.empty:

        return 0

    if "Date" not in property_history.columns:

        return 0

    cutoff = pd.Timestamp.now(

        tz="UTC"

    ) - pd.Timedelta(

        days=window_days

    )

    recent = property_history.loc[

        property_history["Date"] >= cutoff

    ].copy()

    if event_name:

        recent = filter_event_history(

            recent,

            event_name

        )

    if category and "Category" in recent.columns:

        recent = recent.loc[

            recent["Category"]

            .astype(str)

            .str.strip()

            .str.lower()

            == normalize_text(category)

        ]

    return len(recent)


# ===========================================================
# Profile Features
# ===========================================================

def build_profile_features(
    profile: Dict[str, Any]
) -> Dict[str, Any]:

    if not isinstance(profile, dict):

        profile = {}

    return {

        "resident_count": safe_float(

            profile.get(

                "Resident Count",

                0

            )

        ),

        "average_age": safe_float(

            profile.get(

                "Average Age",

                0

            )

        ),

        "average_tenure": safe_float(

            profile.get(

                "Average Tenure",

                0

            )

        ),

        "community_size": safe_text(

            profile.get(

                "Community Size",

                ""

            )

        ),

        "community_stage": safe_text(

            profile.get(

                "Community Stage",

                ""

            )

        ),

        "dominant_occupation": safe_text(

            profile.get(

                "Dominant Occupation",

                ""

            )

        ),

        "dominant_age_band": safe_text(

            profile.get(

                "Dominant Age Band",

                ""

            )

        ),

        "dominant_region": safe_text(

            profile.get(

                "Dominant Region",

                ""

            )

        ),

        "top_interests": profile.get(

            "Top Interests",

            {}

        )

    }


# ===========================================================
# Content Features
# ===========================================================

def build_content_features(
    profile: Dict[str, Any],
    event: Dict[str, Any]
) -> Dict[str, float]:

    profile_features = build_profile_features(

        profile

    )

    event_interests = get_event_value(

        event,

        "Interests",

        "Target Interests",

        "target_interests",

        default=[]

    )

    event_occupations = get_event_value(

        event,

        "Occupation",

        "Target Occupation",

        "Target Occupations",

        default=[]

    )

    event_age_bands = get_event_value(

        event,

        "Age Band",

        "Target Age Band",

        "Target Age Bands",

        default=[]

    )

    event_community_sizes = get_event_value(

        event,

        "Community Size",

        "Target Community Size",

        default=[]

    )

    event_community_stages = get_event_value(

        event,

        "Community Stage",

        "Target Community Stage",

        default=[]

    )

    return {

        "interest_match": overlap_score(

            profile_features["top_interests"],

            event_interests

        ),

        "occupation_match": overlap_score(

            [

                profile_features[

                    "dominant_occupation"

                ]

            ],

            event_occupations

        ),

        "age_match": overlap_score(

            [

                profile_features[

                    "dominant_age_band"

                ]

            ],

            event_age_bands

        ),

        "community_size_match": overlap_score(

            [

                profile_features[

                    "community_size"

                ]

            ],

            event_community_sizes

        ),

        "community_stage_match": overlap_score(

            [

                profile_features[

                    "community_stage"

                ]

            ],

            event_community_stages

        )

    }


# ===========================================================
# Historical Features
# ===========================================================

def build_historical_features(
    property_name: str,
    event: Dict[str, Any],
    history: pd.DataFrame
) -> Dict[str, float]:

    prepared_history = prepare_history(

        history

    )

    property_history = filter_property_history(

        prepared_history,

        property_name

    )

    event_name = get_event_name(event)

    category = get_event_category(event)

    event_history = filter_event_history(

        property_history,

        event_name

    )

    historical_success = 0.0

    attendance = 0.0

    feedback = 0.0

    budget_efficiency = 0.0

    if not event_history.empty:

        if "Success Score" in event_history.columns:

            historical_success = safe_mean(

                event_history["Success Score"]

            )

        if "Attendance %" in event_history.columns:

            attendance = safe_mean(

                event_history["Attendance %"]

            )

        if "Average Feedback" in event_history.columns:

            feedback = normalize_score(

                safe_mean(

                    event_history[

                        "Average Feedback"

                    ]

                ),

                minimum=0.0,

                maximum=5.0

            )

        if (

            "Budget Planned" in event_history.columns

            and

            "Budget Spent" in event_history.columns

        ):

            planned = safe_mean(

                event_history["Budget Planned"]

            )

            spent = safe_mean(

                event_history["Budget Spent"]

            )

            if planned > 0:

                ratio = spent / planned

                budget_efficiency = max(

                    0.0,

                    min(

                        100.0,

                        100.0 - (

                            abs(1.0 - ratio)

                            * 100.0

                        )

                    )

                )

    last_event_days = days_since_last_event(

        property_history,

        event_name

    )

    recent_event_count = count_recent_events(

        property_history,

        RECENT_EVENT_WINDOW_DAYS,

        event_name=event_name

    )

    repeat_count = count_recent_events(

        property_history,

        REPEAT_FATIGUE_WINDOW_DAYS,

        event_name=event_name

    )

    category_count = count_recent_events(

        property_history,

        CATEGORY_SATURATION_WINDOW_DAYS,

        category=category

    )

    return {

        "historical_success": historical_success,

        "historical_attendance": attendance,

        "historical_feedback": feedback,

        "budget_efficiency": budget_efficiency,

        "days_since_last_event":

            float(last_event_days)

            if last_event_days is not None

            else -1.0,

        "recent_event_count": float(

            recent_event_count

        ),

        "repeat_count": float(

            repeat_count

        ),

        "recent_category_count": float(

            category_count

        ),

        "property_history_count": float(

            len(property_history)

        ),

        "event_history_count": float(

            len(event_history)

        )

    }


# ===========================================================
# Complete Feature Vector
# ===========================================================

def build_event_features(
    property_name: str,
    profile: Dict[str, Any],
    event: Dict[str, Any],
    history: Optional[pd.DataFrame] = None
) -> Dict[str, Any]:

    content_features = build_content_features(

        profile,

        event

    )

    historical_features = build_historical_features(

        property_name,

        event,

        prepare_history(history)

    )

    profile_features = build_profile_features(

        profile

    )

    return {

        "property_name": property_name,

        "event_name": get_event_name(event),

        "category": get_event_category(event),

        "profile": profile_features,

        "content": content_features,

        "history": historical_features

    }


# ===========================================================
# Batch Feature Builder
# ===========================================================

def build_candidate_features(
    property_name: str,
    profile: Dict[str, Any],
    events: List[Dict[str, Any]],
    history: Optional[pd.DataFrame] = None
) -> List[Dict[str, Any]]:

    if not isinstance(events, list):

        return []

    prepared_history = prepare_history(

        history

    )

    features = []

    for event in events:

        if not isinstance(event, dict):

            continue

        event_name = get_event_name(event)

        if not event_name:

            continue

        features.append(

            build_event_features(

                property_name=property_name,

                profile=profile,

                event=event,

                history=prepared_history

            )

        )

    return features