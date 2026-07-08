"""
===========================================================
TribeIQ Exploration Engine
===========================================================

Balances exploitation of proven events with controlled
exploration of promising new events.

Responsibilities:
1. Identify exploration candidates
2. Calculate exploration confidence
3. Apply controlled exploration bonuses
4. Preserve deterministic and reproducible behaviour
5. Prevent low-quality random recommendations

This module does not perform final ranking or selection.
===========================================================
"""

from typing import Any, Dict, List

try:
    from recommendation.config import (
        EXPLORATION_RATE,
        EXPLORATION_BONUS,
        MINIMUM_EXPLORATION_CONFIDENCE
    )

    from recommendation.feature_builder import (
        safe_float,
        safe_text
    )

except ModuleNotFoundError:
    from config import (
        EXPLORATION_RATE,
        EXPLORATION_BONUS,
        MINIMUM_EXPLORATION_CONFIDENCE
    )

    from feature_builder import (
        safe_float,
        safe_text
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


def clamp_confidence(
    value: Any
) -> float:

    numeric = safe_float(value)

    return max(
        0.0,
        min(numeric, 1.0)
    )


def get_history_features(
    candidate: Dict[str, Any]
) -> Dict[str, Any]:

    return (
        candidate
        .get("features", {})
        .get("history", {})
    )


def get_candidate_score(
    candidate: Dict[str, Any]
) -> float:

    return clamp_score(
        candidate.get(
            "candidate_score",
            0.0
        )
    )


# ===========================================================
# Stable Exploration Key
# ===========================================================

def build_stable_key(
    candidate: Dict[str, Any]
) -> str:

    property_name = safe_text(
        candidate.get(
            "property_name",
            ""
        )
    ).lower()

    event_id = safe_text(
        candidate.get(
            "event_id",
            ""
        )
    ).lower()

    event_name = safe_text(
        candidate.get(
            "event_name",
            ""
        )
    ).lower()

    return (
        f"{property_name}|"
        f"{event_id}|"
        f"{event_name}"
    )


def stable_exploration_value(
    candidate: Dict[str, Any]
) -> float:

    key = build_stable_key(
        candidate
    )

    if not key:

        return 1.0

    value = 0

    for index, character in enumerate(
        key,
        start=1
    ):

        value += (
            index
            * ord(character)
        )

    return (
        value % 10000
    ) / 10000.0


# ===========================================================
# Exploration Eligibility
# ===========================================================

def is_unexplored(
    candidate: Dict[str, Any]
) -> bool:

    history = get_history_features(
        candidate
    )

    event_history_count = safe_float(
        history.get(
            "event_history_count",
            0.0
        )
    )

    return event_history_count <= 0


def calculate_exploration_confidence(
    candidate: Dict[str, Any]
) -> float:

    affinity = candidate.get(
        "affinity_signals",
        {}
    )

    if not isinstance(
        affinity,
        dict
    ):

        affinity = {}

    content_score = get_candidate_score(
        candidate
    )

    resident_affinity = clamp_score(
        affinity.get(
            "resident_affinity",
            content_score
        )
    )

    property_affinity = clamp_score(
        affinity.get(
            "property_event_affinity",
            content_score
        )
    )

    interest_match = clamp_score(
        affinity.get(
            "interest_match",
            0.0
        )
    )

    novelty = clamp_score(
        affinity.get(
            "novelty",
            100.0
        )
    )

    confidence_score = (
        content_score * 0.35
        + resident_affinity * 0.25
        + property_affinity * 0.20
        + interest_match * 0.15
        + novelty * 0.05
    )

    return clamp_confidence(
        confidence_score / 100.0
    )


def is_exploration_eligible(
    candidate: Dict[str, Any]
) -> bool:

    if not isinstance(
        candidate,
        dict
    ):

        return False

    if not safe_text(
        candidate.get(
            "event_name",
            ""
        )
    ):

        return False

    if not is_unexplored(
        candidate
    ):

        return False

    confidence = (
        calculate_exploration_confidence(
            candidate
        )
    )

    return (
        confidence
        >= MINIMUM_EXPLORATION_CONFIDENCE
    )


# ===========================================================
# Exploration Bonus
# ===========================================================

def calculate_exploration_bonus(
    candidate: Dict[str, Any]
) -> float:

    if not is_exploration_eligible(
        candidate
    ):

        return 0.0

    stable_value = stable_exploration_value(
        candidate
    )

    if stable_value > EXPLORATION_RATE:

        return 0.0

    confidence = (
        calculate_exploration_confidence(
            candidate
        )
    )

    confidence_range = (
        1.0
        - MINIMUM_EXPLORATION_CONFIDENCE
    )

    if confidence_range <= 0:

        confidence_factor = 1.0

    else:

        confidence_factor = (
            confidence
            - MINIMUM_EXPLORATION_CONFIDENCE
        ) / confidence_range

    confidence_factor = clamp_confidence(
        confidence_factor
    )

    bonus = (
        EXPLORATION_BONUS
        * (
            0.50
            + (
                confidence_factor
                * 0.50
            )
        )
    )

    return max(
        0.0,
        min(
            bonus,
            EXPLORATION_BONUS
        )
    )


# ===========================================================
# Candidate Enrichment
# ===========================================================

def enrich_candidate_with_exploration(
    candidate: Dict[str, Any]
) -> Dict[str, Any]:

    if not isinstance(
        candidate,
        dict
    ):

        return {}

    output = candidate.copy()

    confidence = (
        calculate_exploration_confidence(
            candidate
        )
    )

    eligible = is_exploration_eligible(
        candidate
    )

    bonus = calculate_exploration_bonus(
        candidate
    )

    output["exploration_confidence"] = round(
        confidence,
        4
    )

    output["exploration_eligible"] = eligible

    output["exploration_bonus"] = round(
        bonus,
        4
    )

    output["exploration_selected"] = (
        bonus > 0.0
    )

    return output


# ===========================================================
# Batch Exploration Processing
# ===========================================================

def enrich_candidates_with_exploration(
    candidates: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:

    if not isinstance(
        candidates,
        list
    ):

        return []

    enriched = []

    for candidate in candidates:

        if not isinstance(
            candidate,
            dict
        ):

            continue

        output = (
            enrich_candidate_with_exploration(
                candidate
            )
        )

        if output:

            enriched.append(
                output
            )

    return enriched