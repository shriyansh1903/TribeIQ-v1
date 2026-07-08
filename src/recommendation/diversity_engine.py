"""
===========================================================
TribeIQ Diversity Engine
===========================================================

Optimizes ranked recommendations for:

1. Event uniqueness
2. Category diversity
3. Audience diversity
4. Recommendation quality
5. Major/minor event structure

This module performs deterministic final selection.
===========================================================
"""

from typing import Any, Dict, List, Optional, Set

try:
    from recommendation.config import (
        MAJOR_EVENT_COUNT,
        MINOR_EVENT_COUNT,
        MINIMUM_FINAL_SCORE,
        REQUIRE_CATEGORY_DIVERSITY,
        REQUIRE_EVENT_UNIQUENESS
    )

    from recommendation.feature_builder import (
        safe_float,
        safe_text,
        normalize_text,
        to_token_set
    )

except ModuleNotFoundError:
    from config import (
        MAJOR_EVENT_COUNT,
        MINOR_EVENT_COUNT,
        MINIMUM_FINAL_SCORE,
        REQUIRE_CATEGORY_DIVERSITY,
        REQUIRE_EVENT_UNIQUENESS
    )

    from feature_builder import (
        safe_float,
        safe_text,
        normalize_text,
        to_token_set
    )


# ===========================================================
# Helpers
# ===========================================================

def get_event_id(
    candidate: Dict[str, Any]
) -> str:

    event_id = safe_text(
        candidate.get(
            "event_id",
            ""
        )
    )

    if event_id:

        return normalize_text(event_id)

    return normalize_text(
        candidate.get(
            "event_name",
            ""
        )
    )


def get_category(
    candidate: Dict[str, Any]
) -> str:

    return normalize_text(
        candidate.get(
            "category",
            "unknown"
        )
    )


def get_final_score(
    candidate: Dict[str, Any]
) -> float:

    return safe_float(
        candidate.get(
            "final_score",
            0.0
        )
    )


def get_event_data(
    candidate: Dict[str, Any]
) -> Dict[str, Any]:

    event_data = candidate.get(
        "event_data",
        {}
    )

    if not isinstance(event_data, dict):

        return {}

    return event_data


# ===========================================================
# Event Type Detection
# ===========================================================

def get_event_type(
    candidate: Dict[str, Any]
) -> str:

    event_data = get_event_data(
        candidate
    )

    possible_keys = (
        "Event Type",
        "event_type",
        "Type",
        "type",
        "Scale",
        "scale"
    )

    for key in possible_keys:

        value = normalize_text(
            event_data.get(
                key,
                ""
            )
        )

        if value:

            return value

    return ""


def is_major_eligible(
    candidate: Dict[str, Any]
) -> bool:

    event_type = get_event_type(
        candidate
    )

    if not event_type:

        return True

    major_labels = {
        "major",
        "large",
        "flagship",
        "premium"
    }

    minor_labels = {
        "minor",
        "small",
        "micro"
    }

    if event_type in major_labels:

        return True

    if event_type in minor_labels:

        return False

    return True


def is_minor_eligible(
    candidate: Dict[str, Any]
) -> bool:

    event_type = get_event_type(
        candidate
    )

    if not event_type:

        return True

    minor_labels = {
        "minor",
        "small",
        "micro"
    }

    major_labels = {
        "major",
        "large",
        "flagship",
        "premium"
    }

    if event_type in minor_labels:

        return True

    if event_type in major_labels:

        return False

    return True


# ===========================================================
# Audience Extraction
# ===========================================================

def get_audience_tokens(
    candidate: Dict[str, Any]
) -> Set[str]:

    event_data = get_event_data(
        candidate
    )

    audience_fields = (
        "Target Audience",
        "target_audience",
        "Audience",
        "audience",
        "Target Interests",
        "target_interests",
        "Interests",
        "Target Age Band",
        "Target Occupation"
    )

    tokens = set()

    for field in audience_fields:

        tokens.update(
            to_token_set(
                event_data.get(
                    field
                )
            )
        )

    return tokens


# ===========================================================
# Similarity
# ===========================================================

def calculate_set_similarity(
    left: Set[str],
    right: Set[str]
) -> float:

    if not left or not right:

        return 0.0

    union = left.union(
        right
    )

    if not union:

        return 0.0

    intersection = left.intersection(
        right
    )

    return (
        len(intersection)
        / len(union)
    ) * 100.0


def calculate_candidate_similarity(
    left: Dict[str, Any],
    right: Dict[str, Any]
) -> float:

    score = 0.0

    if get_category(left) == get_category(right):

        score += 50.0

    audience_similarity = calculate_set_similarity(
        get_audience_tokens(left),
        get_audience_tokens(right)
    )

    score += (
        audience_similarity
        * 0.50
    )

    return min(
        score,
        100.0
    )


# ===========================================================
# Candidate Validation
# ===========================================================

def is_candidate_valid(
    candidate: Dict[str, Any]
) -> bool:

    if not isinstance(candidate, dict):

        return False

    if not safe_text(
        candidate.get(
            "event_name",
            ""
        )
    ):

        return False

    if (
        get_final_score(candidate)
        < MINIMUM_FINAL_SCORE
    ):

        return False

    return True


def is_duplicate(
    candidate: Dict[str, Any],
    selected: List[Dict[str, Any]]
) -> bool:

    candidate_id = get_event_id(
        candidate
    )

    for item in selected:

        if (
            get_event_id(item)
            == candidate_id
        ):

            return True

    return False


# ===========================================================
# Diversity Adjustment
# ===========================================================

def calculate_diversity_adjustment(
    candidate: Dict[str, Any],
    selected: List[Dict[str, Any]]
) -> float:

    if not selected:

        return 0.0

    adjustment = 0.0

    candidate_category = get_category(
        candidate
    )

    selected_categories = {
        get_category(item)
        for item in selected
    }

    if (
        REQUIRE_CATEGORY_DIVERSITY
        and candidate_category
        and candidate_category
        not in selected_categories
    ):

        adjustment += 8.0

    maximum_similarity = max(
        calculate_candidate_similarity(
            candidate,
            item
        )
        for item in selected
    )

    if maximum_similarity <= 25.0:

        adjustment += 7.0

    elif maximum_similarity <= 50.0:

        adjustment += 3.0

    elif maximum_similarity >= 80.0:

        adjustment -= 10.0

    return adjustment


# ===========================================================
# Major Event Selection
# ===========================================================

def select_major_event(
    ranked_candidates: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:

    eligible = [
        candidate
        for candidate in ranked_candidates
        if (
            is_candidate_valid(candidate)
            and is_major_eligible(candidate)
        )
    ]

    if eligible:

        return eligible[0].copy()

    valid = [
        candidate
        for candidate in ranked_candidates
        if is_candidate_valid(candidate)
    ]

    if not valid:

        return None

    return valid[0].copy()


# ===========================================================
# Minor Event Selection
# ===========================================================

def select_minor_events(
    ranked_candidates: List[Dict[str, Any]],
    major_event: Optional[Dict[str, Any]],
    count: int = MINOR_EVENT_COUNT
) -> List[Dict[str, Any]]:

    selected = []

    comparison_set = []

    if major_event is not None:

        comparison_set.append(
            major_event
        )

    candidates = []

    for candidate in ranked_candidates:

        if not is_candidate_valid(
            candidate
        ):

            continue

        if (
            REQUIRE_EVENT_UNIQUENESS
            and is_duplicate(
                candidate,
                comparison_set
            )
        ):

            continue

        if not is_minor_eligible(
            candidate
        ):

            continue

        diversity_adjustment = (
            calculate_diversity_adjustment(
                candidate,
                comparison_set
                + selected
            )
        )

        selection_score = (
            get_final_score(candidate)
            + diversity_adjustment
        )

        output = candidate.copy()

        output[
            "diversity_adjustment"
        ] = round(
            diversity_adjustment,
            4
        )

        output[
            "selection_score"
        ] = round(
            selection_score,
            4
        )

        candidates.append(
            output
        )

    candidates.sort(
        key=lambda candidate: (
            candidate.get(
                "selection_score",
                0.0
            ),
            candidate.get(
                "final_score",
                0.0
            )
        ),
        reverse=True
    )

    used_categories = {
        get_category(major_event)
    } if major_event else set()

    if REQUIRE_CATEGORY_DIVERSITY:

        for candidate in candidates:

            if len(selected) >= count:

                break

            category = get_category(
                candidate
            )

            if category in used_categories:

                continue

            if is_duplicate(
                candidate,
                selected
            ):

                continue

            selected.append(
                candidate
            )

            used_categories.add(
                category
            )

    for candidate in candidates:

        if len(selected) >= count:

            break

        if is_duplicate(
            candidate,
            selected
        ):

            continue

        selected.append(
            candidate
        )

    return selected[:count]


# ===========================================================
# Final Diversified Selection
# ===========================================================

def select_diverse_recommendations(
    ranked_candidates: List[Dict[str, Any]]
) -> Dict[str, Any]:

    if not isinstance(
        ranked_candidates,
        list
    ):

        ranked_candidates = []

    valid_candidates = [
        candidate
        for candidate in ranked_candidates
        if is_candidate_valid(candidate)
    ]

    valid_candidates.sort(
        key=get_final_score,
        reverse=True
    )

    major_event = None

    if MAJOR_EVENT_COUNT > 0:

        major_event = select_major_event(
            valid_candidates
        )

    minor_events = select_minor_events(
        ranked_candidates=valid_candidates,
        major_event=major_event,
        count=MINOR_EVENT_COUNT
    )

    return {
        "major_event": major_event,
        "minor_events": minor_events,
        "candidate_count":
            len(valid_candidates),
        "selected_count":
            (
                (1 if major_event else 0)
                + len(minor_events)
            )
    }