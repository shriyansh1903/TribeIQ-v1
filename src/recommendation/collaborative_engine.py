"""
===========================================================
TribeIQ Collaborative Engine
===========================================================

Calculates recommendation signals from similar properties.

Responsibilities:
1. Compare property profiles
2. Find similar communities
3. Measure event performance in similar properties
4. Produce a collaborative recommendation signal

This module does not perform final ranking or selection.
===========================================================
"""

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

try:
    from recommendation.config import (
        MINIMUM_HISTORY_FOR_COLLABORATIVE
    )

    from recommendation.feature_builder import (
        safe_float,
        safe_text,
        normalize_text,
        normalize_score,
        safe_mean,
        prepare_history
    )

except ModuleNotFoundError:
    from config import (
        MINIMUM_HISTORY_FOR_COLLABORATIVE
    )

    from feature_builder import (
        safe_float,
        safe_text,
        normalize_text,
        normalize_score,
        safe_mean,
        prepare_history
    )


# ===========================================================
# Constants
# ===========================================================

MAX_SIMILAR_PROPERTIES = 5

MINIMUM_PROPERTY_SIMILARITY = 20.0


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


def exact_match_score(
    left: Any,
    right: Any
) -> float:

    left_text = normalize_text(left)

    right_text = normalize_text(right)

    if not left_text or not right_text:

        return 0.0

    return 100.0 if left_text == right_text else 0.0


def numeric_similarity(
    left: Any,
    right: Any
) -> float:

    left_value = safe_float(left)

    right_value = safe_float(right)

    maximum = max(
        abs(left_value),
        abs(right_value),
        1.0
    )

    difference = abs(
        left_value - right_value
    )

    similarity = (
        1.0
        - min(
            difference / maximum,
            1.0
        )
    ) * 100.0

    return clamp_score(similarity)


def weighted_average(
    values: List[Tuple[float, float]]
) -> float:

    total = 0.0

    weight_total = 0.0

    for value, weight in values:

        numeric_value = safe_float(value)

        numeric_weight = safe_float(weight)

        if numeric_weight <= 0:

            continue

        total += (
            numeric_value
            * numeric_weight
        )

        weight_total += numeric_weight

    if weight_total <= 0:

        return 0.0

    return clamp_score(
        total / weight_total
    )


# ===========================================================
# Profile Similarity
# ===========================================================

def calculate_property_similarity(
    source_profile: Dict[str, Any],
    target_profile: Dict[str, Any]
) -> float:

    if not isinstance(source_profile, dict):

        source_profile = {}

    if not isinstance(target_profile, dict):

        target_profile = {}

    resident_similarity = numeric_similarity(
        source_profile.get(
            "Resident Count",
            0
        ),
        target_profile.get(
            "Resident Count",
            0
        )
    )

    age_similarity = numeric_similarity(
        source_profile.get(
            "Average Age",
            0
        ),
        target_profile.get(
            "Average Age",
            0
        )
    )

    tenure_similarity = numeric_similarity(
        source_profile.get(
            "Average Tenure",
            0
        ),
        target_profile.get(
            "Average Tenure",
            0
        )
    )

    size_similarity = exact_match_score(
        source_profile.get(
            "Community Size",
            ""
        ),
        target_profile.get(
            "Community Size",
            ""
        )
    )

    stage_similarity = exact_match_score(
        source_profile.get(
            "Community Stage",
            ""
        ),
        target_profile.get(
            "Community Stage",
            ""
        )
    )

    occupation_similarity = exact_match_score(
        source_profile.get(
            "Dominant Occupation",
            ""
        ),
        target_profile.get(
            "Dominant Occupation",
            ""
        )
    )

    age_band_similarity = exact_match_score(
        source_profile.get(
            "Dominant Age Band",
            ""
        ),
        target_profile.get(
            "Dominant Age Band",
            ""
        )
    )

    region_similarity = exact_match_score(
        source_profile.get(
            "Dominant Region",
            ""
        ),
        target_profile.get(
            "Dominant Region",
            ""
        )
    )

    return weighted_average([
        (
            resident_similarity,
            0.15
        ),
        (
            age_similarity,
            0.10
        ),
        (
            tenure_similarity,
            0.10
        ),
        (
            size_similarity,
            0.15
        ),
        (
            stage_similarity,
            0.20
        ),
        (
            occupation_similarity,
            0.15
        ),
        (
            age_band_similarity,
            0.10
        ),
        (
            region_similarity,
            0.05
        )
    ])


# ===========================================================
# Similar Property Discovery
# ===========================================================

def find_similar_properties(
    property_name: str,
    profiles: Dict[str, Dict[str, Any]],
    limit: int = MAX_SIMILAR_PROPERTIES
) -> List[Dict[str, Any]]:

    if not isinstance(profiles, dict):

        return []

    if property_name not in profiles:

        return []

    source_profile = profiles[property_name]

    similar_properties = []

    for other_name, other_profile in profiles.items():

        if normalize_text(other_name) == normalize_text(
            property_name
        ):

            continue

        similarity = calculate_property_similarity(
            source_profile,
            other_profile
        )

        if similarity < MINIMUM_PROPERTY_SIMILARITY:

            continue

        similar_properties.append({
            "property_name": other_name,
            "similarity": similarity
        })

    similar_properties.sort(
        key=lambda item: item.get(
            "similarity",
            0.0
        ),
        reverse=True
    )

    return similar_properties[:limit]


# ===========================================================
# Event History Filtering
# ===========================================================

def filter_history_by_property(
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


def filter_history_by_event(
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
# Similar Property Event Performance
# ===========================================================

def calculate_event_performance(
    event_history: pd.DataFrame
) -> float:

    if event_history.empty:

        return 0.0

    components = []

    if "Success Score" in event_history.columns:

        components.append((
            safe_mean(
                event_history["Success Score"]
            ),
            0.40
        ))

    if "Attendance %" in event_history.columns:

        components.append((
            safe_mean(
                event_history["Attendance %"]
            ),
            0.30
        ))

    if "Average Feedback" in event_history.columns:

        feedback = normalize_score(
            safe_mean(
                event_history["Average Feedback"]
            ),
            minimum=0.0,
            maximum=5.0
        )

        components.append((
            feedback,
            0.30
        ))

    if not components:

        return 0.0

    return weighted_average(components)


# ===========================================================
# Collaborative Signal
# ===========================================================

def calculate_similar_community_signal(
    property_name: str,
    event_name: str,
    profiles: Dict[str, Dict[str, Any]],
    history: Optional[pd.DataFrame]
) -> Dict[str, Any]:

    prepared_history = prepare_history(
        history
    )

    default_result = {
        "score": 50.0,
        "confidence": 0.0,
        "supporting_properties": [],
        "observation_count": 0
    }

    if prepared_history.empty:

        return default_result

    if len(prepared_history) < MINIMUM_HISTORY_FOR_COLLABORATIVE:

        return default_result

    similar_properties = find_similar_properties(
        property_name,
        profiles
    )

    if not similar_properties:

        return default_result

    weighted_scores = []

    supporting_properties = []

    observation_count = 0

    for property_data in similar_properties:

        similar_property_name = property_data[
            "property_name"
        ]

        similarity = safe_float(
            property_data.get(
                "similarity",
                0.0
            )
        )

        property_history = filter_history_by_property(
            prepared_history,
            similar_property_name
        )

        event_history = filter_history_by_event(
            property_history,
            event_name
        )

        if event_history.empty:

            continue

        performance = calculate_event_performance(
            event_history
        )

        weight = similarity / 100.0

        weighted_scores.append((
            performance,
            weight
        ))

        observation_count += len(
            event_history
        )

        supporting_properties.append({
            "property_name":
                similar_property_name,
            "similarity":
                round(similarity, 2),
            "event_performance":
                round(performance, 2),
            "observations":
                len(event_history)
        })

    if not weighted_scores:

        return default_result

    score = weighted_average(
        weighted_scores
    )

    confidence = min(
        1.0,
        (
            observation_count
            / 10.0
        )
    )

    return {
        "score": round(
            score,
            4
        ),
        "confidence": round(
            confidence,
            4
        ),
        "supporting_properties":
            supporting_properties,
        "observation_count":
            observation_count
    }


# ===========================================================
# Candidate Enrichment
# ===========================================================

def enrich_candidate_with_collaborative_signal(
    candidate: Dict[str, Any],
    profiles: Dict[str, Dict[str, Any]],
    history: Optional[pd.DataFrame]
) -> Dict[str, Any]:

    if not isinstance(candidate, dict):

        return {}

    output = candidate.copy()

    property_name = safe_text(
        candidate.get(
            "property_name",
            ""
        )
    )

    event_name = safe_text(
        candidate.get(
            "event_name",
            ""
        )
    )

    result = calculate_similar_community_signal(
        property_name=property_name,
        event_name=event_name,
        profiles=profiles,
        history=history
    )

    output["collaborative_signal"] = result

    return output


# ===========================================================
# Batch Collaborative Processing
# ===========================================================

def enrich_candidates_with_collaborative_signals(
    candidates: List[Dict[str, Any]],
    profiles: Dict[str, Dict[str, Any]],
    history: Optional[pd.DataFrame]
) -> List[Dict[str, Any]]:

    if not isinstance(candidates, list):

        return []

    enriched = []

    for candidate in candidates:

        if not isinstance(candidate, dict):

            continue

        enriched.append(
            enrich_candidate_with_collaborative_signal(
                candidate=candidate,
                profiles=profiles,
                history=history
            )
        )

    return enriched