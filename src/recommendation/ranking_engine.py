"""
===========================================================
TribeIQ Ranking Engine
===========================================================

Combines all recommendation signals into a final ranking.

Responsibilities:
1. Collect affinity signals
2. Collect collaborative signals
3. Calculate predicted success
4. Apply configurable signal weights
5. Calculate ranking penalties
6. Produce final candidate scores

This module does not perform final calendar selection.
===========================================================
"""

from typing import Any, Dict, List

try:
    from recommendation.config import (
        SIGNAL_WEIGHTS,
        PENALTY_WEIGHTS,
        RECENT_EVENT_WINDOW_DAYS,
        MAX_CATEGORY_EVENTS_IN_WINDOW,
        EXPLORATION_BONUS
    )

    from recommendation.feature_builder import safe_float

    from recommendation.affinity_engine import (
        calculate_affinity_signals
    )

except ModuleNotFoundError:
    from config import (
        SIGNAL_WEIGHTS,
        PENALTY_WEIGHTS,
        RECENT_EVENT_WINDOW_DAYS,
        MAX_CATEGORY_EVENTS_IN_WINDOW,
        EXPLORATION_BONUS
    )

    from feature_builder import safe_float

    from affinity_engine import (
        calculate_affinity_signals
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


# ===========================================================
# Feature Access
# ===========================================================

def get_history_features(
    candidate: Dict[str, Any]
) -> Dict[str, Any]:

    return (
        candidate
        .get("features", {})
        .get("history", {})
    )


def get_collaborative_data(
    candidate: Dict[str, Any]
) -> Dict[str, Any]:

    return candidate.get(
        "collaborative_signal",
        {}
    )


# ===========================================================
# Predicted Success
# ===========================================================

def calculate_predicted_success(
    candidate: Dict[str, Any],
    signals: Dict[str, float]
) -> float:

    history = get_history_features(
        candidate
    )

    history_count = safe_float(
        history.get(
            "event_history_count",
            0.0
        )
    )

    resident_affinity = safe_float(
        signals.get(
            "resident_affinity",
            0.0
        )
    )

    property_affinity = safe_float(
        signals.get(
            "property_event_affinity",
            0.0
        )
    )

    historical_performance = safe_float(
        signals.get(
            "historical_performance",
            50.0
        )
    )

    collaborative = safe_float(
        signals.get(
            "similar_community",
            50.0
        )
    )

    if history_count <= 0:

        score = (
            resident_affinity * 0.45
            + property_affinity * 0.35
            + collaborative * 0.20
        )

    elif history_count < 3:

        score = (
            resident_affinity * 0.30
            + property_affinity * 0.30
            + historical_performance * 0.25
            + collaborative * 0.15
        )

    else:

        score = (
            resident_affinity * 0.20
            + property_affinity * 0.25
            + historical_performance * 0.40
            + collaborative * 0.15
        )

    return clamp_score(score)


# ===========================================================
# Signal Collection
# ===========================================================

def collect_signals(
    candidate: Dict[str, Any]
) -> Dict[str, float]:

    affinity = candidate.get(
        "affinity_signals"
    )

    if not isinstance(affinity, dict):

        affinity = calculate_affinity_signals(
            candidate
        )

    collaborative = get_collaborative_data(
        candidate
    )

    signals = {
        "resident_affinity": clamp_score(
            affinity.get(
                "resident_affinity",
                0.0
            )
        ),
        "property_event_affinity": clamp_score(
            affinity.get(
                "property_event_affinity",
                0.0
            )
        ),
        "historical_performance": clamp_score(
            affinity.get(
                "historical_performance",
                50.0
            )
        ),
        "similar_community": clamp_score(
            collaborative.get(
                "score",
                50.0
            )
        ),
        "interest_match": clamp_score(
            affinity.get(
                "interest_match",
                0.0
            )
        ),
        "predicted_success": 0.0,
        "novelty": clamp_score(
            affinity.get(
                "novelty",
                0.0
            )
        ),
        "budget_efficiency": clamp_score(
            affinity.get(
                "budget_efficiency",
                50.0
            )
        ),
        "llm_adjustment": clamp_score(
            candidate.get(
                "llm_signal",
                50.0
            )
        )
    }

    signals["predicted_success"] = (
        calculate_predicted_success(
            candidate,
            signals
        )
    )

    return signals


# ===========================================================
# Penalty Calculation
# ===========================================================

def calculate_recent_event_penalty(
    candidate: Dict[str, Any]
) -> float:

    history = get_history_features(
        candidate
    )

    days_since = safe_float(
        history.get(
            "days_since_last_event",
            -1.0
        ),
        default=-1.0
    )

    if days_since < 0:

        return 0.0

    if days_since >= RECENT_EVENT_WINDOW_DAYS:

        return 0.0

    return clamp_score(
        (
            1.0
            - (
                days_since
                / RECENT_EVENT_WINDOW_DAYS
            )
        )
        * 100.0
    )


def calculate_repeat_fatigue_penalty(
    candidate: Dict[str, Any]
) -> float:

    history = get_history_features(
        candidate
    )

    repeat_count = safe_float(
        history.get(
            "repeat_count",
            0.0
        )
    )

    return clamp_score(
        repeat_count * 25.0
    )


def calculate_category_saturation_penalty(
    candidate: Dict[str, Any]
) -> float:

    history = get_history_features(
        candidate
    )

    category_count = safe_float(
        history.get(
            "recent_category_count",
            0.0
        )
    )

    if category_count <= MAX_CATEGORY_EVENTS_IN_WINDOW:

        return 0.0

    excess = (
        category_count
        - MAX_CATEGORY_EVENTS_IN_WINDOW
    )

    return clamp_score(
        excess * 25.0
    )


def calculate_budget_risk_penalty(
    candidate: Dict[str, Any]
) -> float:

    history = get_history_features(
        candidate
    )

    history_count = safe_float(
        history.get(
            "event_history_count",
            0.0
        )
    )

    if history_count <= 0:

        return 0.0

    efficiency = safe_float(
        history.get(
            "budget_efficiency",
            50.0
        )
    )

    return clamp_score(
        100.0 - efficiency
    )


def calculate_low_confidence_penalty(
    candidate: Dict[str, Any]
) -> float:

    history = get_history_features(
        candidate
    )

    collaborative = get_collaborative_data(
        candidate
    )

    history_count = safe_float(
        history.get(
            "event_history_count",
            0.0
        )
    )

    collaborative_confidence = clamp_confidence(
        collaborative.get(
            "confidence",
            0.0
        )
    )

    evidence_score = min(
        1.0,
        (
            history_count / 5.0
        )
        + (
            collaborative_confidence * 0.5
        )
    )

    return clamp_score(
        (
            1.0 - evidence_score
        )
        * 100.0
    )


def collect_penalties(
    candidate: Dict[str, Any]
) -> Dict[str, float]:

    return {
        "recent_event":
            calculate_recent_event_penalty(
                candidate
            ),
        "repeat_fatigue":
            calculate_repeat_fatigue_penalty(
                candidate
            ),
        "category_saturation":
            calculate_category_saturation_penalty(
                candidate
            ),
        "budget_risk":
            calculate_budget_risk_penalty(
                candidate
            ),
        "low_confidence":
            calculate_low_confidence_penalty(
                candidate
            )
    }


# ===========================================================
# Weighted Score
# ===========================================================

def calculate_weighted_signal_score(
    signals: Dict[str, float]
) -> float:

    score = 0.0

    for signal_name, weight in SIGNAL_WEIGHTS.items():

        signal_value = safe_float(
            signals.get(
                signal_name,
                0.0
            )
        )

        score += (
            signal_value
            * weight
        )

    return clamp_score(score)


def calculate_weighted_penalty(
    penalties: Dict[str, float]
) -> float:

    penalty = 0.0

    for penalty_name, weight in PENALTY_WEIGHTS.items():

        penalty_value = safe_float(
            penalties.get(
                penalty_name,
                0.0
            )
        )

        penalty += (
            penalty_value
            * weight
        )

    return max(
        0.0,
        penalty
    )


# ===========================================================
# Candidate Ranking
# ===========================================================

def rank_candidate(
    candidate: Dict[str, Any]
) -> Dict[str, Any]:

    if not isinstance(candidate, dict):

        return {}

    output = candidate.copy()

    signals = collect_signals(
        candidate
    )

    penalties = collect_penalties(
        candidate
    )

    base_score = (
        calculate_weighted_signal_score(
            signals
        )
    )

    total_penalty = (
        calculate_weighted_penalty(
            penalties
        )
    )

    exploration_bonus = safe_float(
        candidate.get(
            "exploration_bonus",
            0.0
        )
    )

    exploration_bonus = min(
        max(
            exploration_bonus,
            0.0
        ),
        EXPLORATION_BONUS
    )

    final_score = (
        base_score
        - total_penalty
        + exploration_bonus
    )

    output["signals"] = signals

    output["penalties"] = penalties

    output["base_score"] = round(
        base_score,
        4
    )

    output["total_penalty"] = round(
        total_penalty,
        4
    )

    output["exploration_bonus"] = round(
        exploration_bonus,
        4
    )

    output["final_score"] = round(
        clamp_score(final_score),
        4
    )

    output["score_breakdown"] = {
        "signals": signals,
        "penalties": penalties,
        "base_score":
            output["base_score"],
        "total_penalty":
            output["total_penalty"],
        "exploration_bonus":
            output["exploration_bonus"],
        "final_score":
            output["final_score"]
    }

    return output


# ===========================================================
# Batch Ranking
# ===========================================================

def rank_candidates(
    candidates: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:

    if not isinstance(candidates, list):

        return []

    ranked = []

    for candidate in candidates:

        if not isinstance(candidate, dict):

            continue

        ranked_candidate = rank_candidate(
            candidate
        )

        if ranked_candidate:

            ranked.append(
                ranked_candidate
            )

    ranked.sort(
        key=lambda candidate: (
            candidate.get(
                "final_score",
                0.0
            ),
            candidate.get(
                "candidate_score",
                0.0
            )
        ),
        reverse=True
    )

    for index, candidate in enumerate(
        ranked,
        start=1
    ):

        candidate["rank"] = index

    return ranked