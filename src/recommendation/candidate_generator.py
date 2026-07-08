"""
===========================================================
TribeIQ Candidate Generator
===========================================================

Generates the initial candidate pool for each property.

Responsibilities:
1. Build recommendation features
2. Calculate content relevance
3. Calculate historical relevance
4. Apply cold-start behaviour
5. Return the strongest candidate events

This module does not perform final ranking or selection.
===========================================================
"""

from typing import Any, Dict, List, Optional

import pandas as pd

try:
    from recommendation.config import (
        CANDIDATE_POOL_SIZE,
        MINIMUM_CANDIDATES
    )

    from recommendation.feature_builder import (
        build_event_features,
        get_event_name,
        get_event_category,
        safe_float
    )

except ModuleNotFoundError:
    from config import (
        CANDIDATE_POOL_SIZE,
        MINIMUM_CANDIDATES
    )

    from feature_builder import (
        build_event_features,
        get_event_name,
        get_event_category,
        safe_float
    )


# ===========================================================
# Helpers
# ===========================================================

def clamp_score(
    value: Any,
    minimum: float = 0.0,
    maximum: float = 100.0
) -> float:

    numeric = safe_float(value)

    return max(
        minimum,
        min(numeric, maximum)
    )


def safe_average(
    values: List[float]
) -> float:

    valid = [
        safe_float(value)
        for value in values
    ]

    if not valid:

        return 0.0

    return sum(valid) / len(valid)


# ===========================================================
# Event Identifier
# ===========================================================

def get_event_id(
    event: Dict[str, Any],
    index: int
) -> str:

    possible_keys = (
        "Event ID",
        "event_id",
        "ID",
        "id"
    )

    for key in possible_keys:

        value = event.get(key)

        if value is not None:

            text = str(value).strip()

            if text:

                return text

    event_name = get_event_name(event)

    if event_name:

        return (
            event_name
            .strip()
            .lower()
            .replace(" ", "_")
        )

    return f"event_{index}"


# ===========================================================
# Content Relevance
# ===========================================================

def calculate_content_relevance(
    features: Dict[str, Any]
) -> float:

    content = features.get(
        "content",
        {}
    )

    interest_match = safe_float(
        content.get(
            "interest_match",
            0.0
        )
    )

    occupation_match = safe_float(
        content.get(
            "occupation_match",
            0.0
        )
    )

    age_match = safe_float(
        content.get(
            "age_match",
            0.0
        )
    )

    community_size_match = safe_float(
        content.get(
            "community_size_match",
            0.0
        )
    )

    community_stage_match = safe_float(
        content.get(
            "community_stage_match",
            0.0
        )
    )

    score = (
        interest_match * 0.35
        + occupation_match * 0.20
        + age_match * 0.15
        + community_size_match * 0.15
        + community_stage_match * 0.15
    )

    return clamp_score(score)


# ===========================================================
# Historical Relevance
# ===========================================================

def calculate_historical_relevance(
    features: Dict[str, Any]
) -> float:

    history = features.get(
        "history",
        {}
    )

    success = safe_float(
        history.get(
            "historical_success",
            0.0
        )
    )

    attendance = safe_float(
        history.get(
            "historical_attendance",
            0.0
        )
    )

    feedback = safe_float(
        history.get(
            "historical_feedback",
            0.0
        )
    )

    budget_efficiency = safe_float(
        history.get(
            "budget_efficiency",
            0.0
        )
    )

    event_history_count = safe_float(
        history.get(
            "event_history_count",
            0.0
        )
    )

    if event_history_count <= 0:

        return 0.0

    score = safe_average([
        success,
        attendance,
        feedback,
        budget_efficiency
    ])

    return clamp_score(score)


# ===========================================================
# Candidate Relevance
# ===========================================================

def calculate_candidate_relevance(
    features: Dict[str, Any]
) -> float:

    content_score = calculate_content_relevance(
        features
    )

    historical_score = calculate_historical_relevance(
        features
    )

    history = features.get(
        "history",
        {}
    )

    property_history_count = safe_float(
        history.get(
            "property_history_count",
            0.0
        )
    )

    if property_history_count <= 0:

        relevance = content_score

    elif property_history_count < 10:

        relevance = (
            content_score * 0.80
            + historical_score * 0.20
        )

    elif property_history_count < 25:

        relevance = (
            content_score * 0.65
            + historical_score * 0.35
        )

    else:

        relevance = (
            content_score * 0.50
            + historical_score * 0.50
        )

    return clamp_score(relevance)


# ===========================================================
# Candidate Builder
# ===========================================================

def build_candidate(
    property_name: str,
    profile: Dict[str, Any],
    event: Dict[str, Any],
    history: Optional[pd.DataFrame],
    index: int
) -> Optional[Dict[str, Any]]:

    if not isinstance(event, dict):

        return None

    event_name = get_event_name(event)

    if not event_name:

        return None

    features = build_event_features(
        property_name=property_name,
        profile=profile,
        event=event,
        history=history
    )

    content_relevance = (
        calculate_content_relevance(
            features
        )
    )

    historical_relevance = (
        calculate_historical_relevance(
            features
        )
    )

    candidate_relevance = (
        calculate_candidate_relevance(
            features
        )
    )

    return {
        "event_id": get_event_id(
            event,
            index
        ),
        "event_name": event_name,
        "category": get_event_category(
            event
        ),
        "property_name": property_name,
        "event_data": event.copy(),
        "features": features,
        "candidate_scores": {
            "content_relevance":
                content_relevance,
            "historical_relevance":
                historical_relevance,
            "candidate_relevance":
                candidate_relevance
        },
        "candidate_score":
            candidate_relevance
    }


# ===========================================================
# Candidate Generation
# ===========================================================

def generate_candidates(
    property_name: str,
    profile: Dict[str, Any],
    events: List[Dict[str, Any]],
    history: Optional[pd.DataFrame] = None,
    pool_size: Optional[int] = None
) -> List[Dict[str, Any]]:

    if not property_name:

        return []

    if not isinstance(profile, dict):

        profile = {}

    if not isinstance(events, list):

        return []

    if history is None:

        history = pd.DataFrame()

    if not isinstance(history, pd.DataFrame):

        history = pd.DataFrame()

    if pool_size is None:

        pool_size = CANDIDATE_POOL_SIZE

    try:

        pool_size = int(pool_size)

    except (TypeError, ValueError):

        pool_size = CANDIDATE_POOL_SIZE

    pool_size = max(
        MINIMUM_CANDIDATES,
        pool_size
    )

    candidates = []

    seen_event_ids = set()

    for index, event in enumerate(events):

        candidate = build_candidate(
            property_name=property_name,
            profile=profile,
            event=event,
            history=history,
            index=index
        )

        if candidate is None:

            continue

        event_id = candidate["event_id"]

        if event_id in seen_event_ids:

            continue

        seen_event_ids.add(event_id)

        candidates.append(candidate)

    candidates.sort(
        key=lambda candidate: (
            candidate.get(
                "candidate_score",
                0.0
            ),
            candidate.get(
                "event_name",
                ""
            )
        ),
        reverse=True
    )

    return candidates[:pool_size]