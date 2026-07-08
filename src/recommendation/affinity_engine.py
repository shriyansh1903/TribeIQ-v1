"""
===========================================================
TribeIQ Affinity Engine
===========================================================

Calculates:

1. Resident affinity
2. Property-event affinity
3. Interest affinity
4. Historical performance
5. Budget efficiency
6. Novelty

This module does not perform final ranking or selection.
===========================================================
"""

from typing import Any, Dict, List

try:
    from recommendation.feature_builder import safe_float

except ModuleNotFoundError:
    from feature_builder import safe_float


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


def weighted_average(
    values: List[tuple]
) -> float:

    weighted_total = 0.0

    weight_total = 0.0

    for value, weight in values:

        numeric_value = safe_float(value)

        numeric_weight = safe_float(weight)

        if numeric_weight <= 0:

            continue

        weighted_total += (
            numeric_value
            * numeric_weight
        )

        weight_total += numeric_weight

    if weight_total <= 0:

        return 0.0

    return clamp_score(
        weighted_total
        / weight_total
    )


# ===========================================================
# Feature Access
# ===========================================================

def get_content_features(
    candidate: Dict[str, Any]
) -> Dict[str, Any]:

    return (
        candidate
        .get("features", {})
        .get("content", {})
    )


def get_history_features(
    candidate: Dict[str, Any]
) -> Dict[str, Any]:

    return (
        candidate
        .get("features", {})
        .get("history", {})
    )


# ===========================================================
# Resident Affinity
# ===========================================================

def calculate_resident_affinity(
    candidate: Dict[str, Any]
) -> float:

    content = get_content_features(
        candidate
    )

    return weighted_average([
        (
            content.get(
                "interest_match",
                0.0
            ),
            0.40
        ),
        (
            content.get(
                "occupation_match",
                0.0
            ),
            0.25
        ),
        (
            content.get(
                "age_match",
                0.0
            ),
            0.20
        ),
        (
            content.get(
                "community_stage_match",
                0.0
            ),
            0.15
        )
    ])


# ===========================================================
# Property-Event Affinity
# ===========================================================

def calculate_property_event_affinity(
    candidate: Dict[str, Any]
) -> float:

    content = get_content_features(
        candidate
    )

    history = get_history_features(
        candidate
    )

    content_affinity = weighted_average([
        (
            content.get(
                "community_size_match",
                0.0
            ),
            0.50
        ),
        (
            content.get(
                "community_stage_match",
                0.0
            ),
            0.50
        )
    ])

    historical_affinity = weighted_average([
        (
            history.get(
                "historical_success",
                0.0
            ),
            0.40
        ),
        (
            history.get(
                "historical_attendance",
                0.0
            ),
            0.30
        ),
        (
            history.get(
                "historical_feedback",
                0.0
            ),
            0.30
        )
    ])

    event_history_count = safe_float(
        history.get(
            "event_history_count",
            0.0
        )
    )

    if event_history_count <= 0:

        return content_affinity

    if event_history_count < 3:

        return weighted_average([
            (
                content_affinity,
                0.70
            ),
            (
                historical_affinity,
                0.30
            )
        ])

    return weighted_average([
        (
            content_affinity,
            0.40
        ),
        (
            historical_affinity,
            0.60
        )
    ])


# ===========================================================
# Historical Performance
# ===========================================================

def calculate_historical_performance(
    candidate: Dict[str, Any]
) -> float:

    history = get_history_features(
        candidate
    )

    event_history_count = safe_float(
        history.get(
            "event_history_count",
            0.0
        )
    )

    if event_history_count <= 0:

        return 50.0

    return weighted_average([
        (
            history.get(
                "historical_success",
                0.0
            ),
            0.40
        ),
        (
            history.get(
                "historical_attendance",
                0.0
            ),
            0.30
        ),
        (
            history.get(
                "historical_feedback",
                0.0
            ),
            0.30
        )
    ])


# ===========================================================
# Interest Match
# ===========================================================

def calculate_interest_match(
    candidate: Dict[str, Any]
) -> float:

    content = get_content_features(
        candidate
    )

    return clamp_score(
        content.get(
            "interest_match",
            0.0
        )
    )


# ===========================================================
# Budget Efficiency
# ===========================================================

def calculate_budget_efficiency(
    candidate: Dict[str, Any]
) -> float:

    history = get_history_features(
        candidate
    )

    event_history_count = safe_float(
        history.get(
            "event_history_count",
            0.0
        )
    )

    if event_history_count <= 0:

        return 50.0

    return clamp_score(
        history.get(
            "budget_efficiency",
            0.0
        )
    )


# ===========================================================
# Novelty
# ===========================================================

def calculate_novelty(
    candidate: Dict[str, Any]
) -> float:

    history = get_history_features(
        candidate
    )

    event_history_count = safe_float(
        history.get(
            "event_history_count",
            0.0
        )
    )

    days_since_last_event = safe_float(
        history.get(
            "days_since_last_event",
            -1.0
        ),
        default=-1.0
    )

    repeat_count = safe_float(
        history.get(
            "repeat_count",
            0.0
        )
    )

    if event_history_count <= 0:

        return 100.0

    if days_since_last_event < 0:

        recency_novelty = 100.0

    elif days_since_last_event >= 365:

        recency_novelty = 100.0

    else:

        recency_novelty = (
            days_since_last_event
            / 365.0
        ) * 100.0

    repeat_penalty = min(
        repeat_count * 15.0,
        60.0
    )

    novelty = (
        recency_novelty
        - repeat_penalty
    )

    return clamp_score(novelty)


# ===========================================================
# Complete Affinity Signals
# ===========================================================

def calculate_affinity_signals(
    candidate: Dict[str, Any]
) -> Dict[str, float]:

    if not isinstance(candidate, dict):

        return {
            "resident_affinity": 0.0,
            "property_event_affinity": 0.0,
            "historical_performance": 0.0,
            "interest_match": 0.0,
            "budget_efficiency": 0.0,
            "novelty": 0.0
        }

    return {
        "resident_affinity":
            calculate_resident_affinity(
                candidate
            ),
        "property_event_affinity":
            calculate_property_event_affinity(
                candidate
            ),
        "historical_performance":
            calculate_historical_performance(
                candidate
            ),
        "interest_match":
            calculate_interest_match(
                candidate
            ),
        "budget_efficiency":
            calculate_budget_efficiency(
                candidate
            ),
        "novelty":
            calculate_novelty(
                candidate
            )
    }


# ===========================================================
# Batch Affinity Processing
# ===========================================================

def enrich_candidates_with_affinity(
    candidates: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:

    if not isinstance(candidates, list):

        return []

    enriched = []

    for candidate in candidates:

        if not isinstance(candidate, dict):

            continue

        output = candidate.copy()

        output["affinity_signals"] = (
            calculate_affinity_signals(
                candidate
            )
        )

        enriched.append(output)

    return enriched
