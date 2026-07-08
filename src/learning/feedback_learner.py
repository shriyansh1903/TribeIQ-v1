"""
===========================================================
TribeIQ Feedback Learner
===========================================================

Learns adaptive recommendation signals from stored outcomes.

Responsibilities:
1. Read completed recommendation outcomes
2. Calculate property-event performance
3. Calculate category performance
4. Estimate learning confidence
5. Produce bounded learning adjustments

This module never performs final recommendation selection.
===========================================================
"""

import sys
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd


# ===========================================================
# Permanent Import Path Fix
# ===========================================================

SRC_DIR = Path(__file__).resolve().parents[1]

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


# ===========================================================
# Project Imports
# ===========================================================

from learning.signal_store import (
    get_event_signals,
    get_property_signals
)


# ===========================================================
# Configuration
# ===========================================================

MAXIMUM_LEARNING_ADJUSTMENT = 5.0

MINIMUM_OUTCOMES_FOR_CONFIDENCE = 3

FULL_CONFIDENCE_OUTCOME_COUNT = 10


# ===========================================================
# Helpers
# ===========================================================

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


def safe_text(value: Any) -> str:

    if value is None:
        return ""

    return str(value).strip()


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


def clamp_adjustment(value: Any) -> float:

    numeric = safe_float(value)

    return max(
        -MAXIMUM_LEARNING_ADJUSTMENT,
        min(
            numeric,
            MAXIMUM_LEARNING_ADJUSTMENT
        )
    )


# ===========================================================
# Completed Outcomes
# ===========================================================

def get_completed_outcomes(
    records: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:

    if not isinstance(records, list):
        return []

    return [
        record
        for record in records
        if (
            isinstance(record, dict)
            and bool(
                record.get(
                    "completed",
                    False
                )
            )
        )
    ]


# ===========================================================
# Outcome Performance
# ===========================================================

def calculate_outcome_performance(
    record: Dict[str, Any]
) -> float:

    attendance = clamp_score(
        record.get(
            "attendance_percent",
            0.0
        )
    )

    feedback = safe_float(
        record.get(
            "feedback_score",
            0.0
        )
    )

    if feedback <= 5.0:
        feedback = (
            feedback / 5.0
        ) * 100.0

    feedback = clamp_score(feedback)

    success = clamp_score(
        record.get(
            "success_score",
            0.0
        )
    )

    return clamp_score(
        attendance * 0.35
        + feedback * 0.30
        + success * 0.35
    )


def calculate_average_performance(
    records: List[Dict[str, Any]]
) -> float:

    outcomes = get_completed_outcomes(records)

    if not outcomes:
        return 50.0

    scores = [
        calculate_outcome_performance(record)
        for record in outcomes
    ]

    return clamp_score(
        sum(scores) / len(scores)
    )


# ===========================================================
# Learning Confidence
# ===========================================================

def calculate_learning_confidence(
    outcome_count: int
) -> float:

    if outcome_count <= 0:
        return 0.0

    if (
        outcome_count
        < MINIMUM_OUTCOMES_FOR_CONFIDENCE
    ):

        return (
            outcome_count
            / MINIMUM_OUTCOMES_FOR_CONFIDENCE
        ) * 0.30

    confidence = (
        outcome_count
        / FULL_CONFIDENCE_OUTCOME_COUNT
    )

    return max(
        0.0,
        min(confidence, 1.0)
    )


# ===========================================================
# Property-Event Learning
# ===========================================================

def calculate_event_learning_signal(
    property_name: str,
    event_id: str
) -> Dict[str, Any]:

    records = get_event_signals(
        property_name=property_name,
        event_id=event_id
    )

    outcomes = get_completed_outcomes(records)

    outcome_count = len(outcomes)

    if outcome_count <= 0:

        return {
            "performance": 50.0,
            "confidence": 0.0,
            "adjustment": 0.0,
            "outcome_count": 0
        }

    performance = calculate_average_performance(
        outcomes
    )

    confidence = calculate_learning_confidence(
        outcome_count
    )

    raw_adjustment = (
        (performance - 50.0)
        / 50.0
    ) * MAXIMUM_LEARNING_ADJUSTMENT

    adjustment = clamp_adjustment(
        raw_adjustment * confidence
    )

    return {
        "performance": round(
            performance,
            4
        ),
        "confidence": round(
            confidence,
            4
        ),
        "adjustment": round(
            adjustment,
            4
        ),
        "outcome_count": outcome_count
    }


# ===========================================================
# Category Learning
# ===========================================================

def calculate_category_learning_signal(
    property_name: str,
    category: str
) -> Dict[str, Any]:

    records = get_property_signals(
        property_name
    )

    target_category = safe_text(
        category
    ).lower()

    category_records = [
        record
        for record in records
        if (
            safe_text(
                record.get(
                    "category",
                    ""
                )
            ).lower()
            == target_category
        )
    ]

    outcomes = get_completed_outcomes(
        category_records
    )

    outcome_count = len(outcomes)

    if outcome_count <= 0:

        return {
            "performance": 50.0,
            "confidence": 0.0,
            "adjustment": 0.0,
            "outcome_count": 0
        }

    performance = calculate_average_performance(
        outcomes
    )

    confidence = calculate_learning_confidence(
        outcome_count
    )

    raw_adjustment = (
        (performance - 50.0)
        / 50.0
    ) * MAXIMUM_LEARNING_ADJUSTMENT

    adjustment = clamp_adjustment(
        raw_adjustment * confidence
    )

    return {
        "performance": round(
            performance,
            4
        ),
        "confidence": round(
            confidence,
            4
        ),
        "adjustment": round(
            adjustment,
            4
        ),
        "outcome_count": outcome_count
    }


# ===========================================================
# Candidate Learning Signal
# ===========================================================

def calculate_candidate_learning_signal(
    candidate: Dict[str, Any]
) -> Dict[str, Any]:

    if not isinstance(candidate, dict):

        return {
            "event_signal": {},
            "category_signal": {},
            "adjustment": 0.0
        }

    property_name = safe_text(
        candidate.get(
            "property_name",
            ""
        )
    )

    event_id = safe_text(
        candidate.get(
            "event_id",
            ""
        )
    )

    category = safe_text(
        candidate.get(
            "category",
            ""
        )
    )

    event_signal = calculate_event_learning_signal(
        property_name=property_name,
        event_id=event_id
    )

    category_signal = (
        calculate_category_learning_signal(
            property_name=property_name,
            category=category
        )
    )

    event_confidence = safe_float(
        event_signal.get(
            "confidence",
            0.0
        )
    )

    category_confidence = safe_float(
        category_signal.get(
            "confidence",
            0.0
        )
    )

    if event_confidence > 0.0:

        adjustment = (
            safe_float(
                event_signal.get(
                    "adjustment",
                    0.0
                )
            ) * 0.70
            + safe_float(
                category_signal.get(
                    "adjustment",
                    0.0
                )
            ) * 0.30
        )

    elif category_confidence > 0.0:

        adjustment = safe_float(
            category_signal.get(
                "adjustment",
                0.0
            )
        )

    else:

        adjustment = 0.0

    return {
        "event_signal":
            event_signal,
        "category_signal":
            category_signal,
        "adjustment": round(
            clamp_adjustment(adjustment),
            4
        )
    }


# ===========================================================
# Candidate Enrichment
# ===========================================================

def enrich_candidate_with_learning(
    candidate: Dict[str, Any]
) -> Dict[str, Any]:

    if not isinstance(candidate, dict):
        return {}

    output = candidate.copy()

    learning_signal = (
        calculate_candidate_learning_signal(
            candidate
        )
    )

    adjustment = safe_float(
        learning_signal.get(
            "adjustment",
            0.0
        )
    )

    current_score = clamp_score(
        candidate.get(
            "final_score",
            0.0
        )
    )

    output["learning_signal"] = learning_signal

    output["learning_adjustment"] = round(
        adjustment,
        4
    )

    output["final_score"] = round(
        clamp_score(
            current_score + adjustment
        ),
        4
    )

    return output


# ===========================================================
# Batch Learning Processing
# ===========================================================

def enrich_candidates_with_learning(
    candidates: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:

    if not isinstance(candidates, list):
        return []

    enriched = []

    for candidate in candidates:

        if not isinstance(candidate, dict):
            continue

        output = enrich_candidate_with_learning(
            candidate
        )

        if output:
            enriched.append(output)

    enriched.sort(
        key=lambda candidate: candidate.get(
            "final_score",
            0.0
        ),
        reverse=True
    )

    for index, candidate in enumerate(
        enriched,
        start=1
    ):
        candidate["rank"] = index

    return enriched