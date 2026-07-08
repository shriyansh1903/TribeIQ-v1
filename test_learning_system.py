"""
===========================================================
TribeIQ Continuous Learning System Test
===========================================================

Tests:

1. Recommendation signal storage
2. Outcome signal storage
3. Property-event learning
4. Category learning
5. Candidate score adaptation
===========================================================
"""

import sys
from pathlib import Path


# ===========================================================
# Project Paths
# ===========================================================

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


# ===========================================================
# Project Imports
# ===========================================================

from learning.signal_store import (
    log_outcome
)

from learning.feedback_learner import (
    calculate_event_learning_signal,
    calculate_category_learning_signal,
    enrich_candidate_with_learning
)


# ===========================================================
# Test Configuration
# ===========================================================

PROPERTY_NAME = "Learning Test Property"

EVENT_ID = "LEARN-E001"

EVENT_NAME = "Learning Test Event"

CATEGORY = "Technology"


# ===========================================================
# Test
# ===========================================================

def run_test():

    print(
        "Testing TribeIQ continuous learning system...\n"
    )

    # -------------------------------------------------------
    # Stage 1: Store Successful Outcomes
    # -------------------------------------------------------

    outcomes = [
        {
            "attendance": 92,
            "feedback": 4.8,
            "success": 94
        },
        {
            "attendance": 88,
            "feedback": 4.6,
            "success": 90
        },
        {
            "attendance": 95,
            "feedback": 4.9,
            "success": 96
        }
    ]

    for outcome in outcomes:

        saved = log_outcome(
            property_name=PROPERTY_NAME,
            event_id=EVENT_ID,
            event_name=EVENT_NAME,
            attendance_percent=outcome[
                "attendance"
            ],
            feedback_score=outcome[
                "feedback"
            ],
            success_score=outcome[
                "success"
            ],
            category=CATEGORY
        )

        assert saved is True

    # -------------------------------------------------------
    # Stage 2: Event Learning Signal
    # -------------------------------------------------------

    event_signal = (
        calculate_event_learning_signal(
            property_name=PROPERTY_NAME,
            event_id=EVENT_ID
        )
    )

    assert isinstance(
        event_signal,
        dict
    )

    assert event_signal[
        "outcome_count"
    ] >= 3

    assert event_signal[
        "performance"
    ] > 50.0

    assert event_signal[
        "confidence"
    ] > 0.0

    assert event_signal[
        "adjustment"
    ] > 0.0

    # -------------------------------------------------------
    # Stage 3: Category Learning Signal
    # -------------------------------------------------------

    category_signal = (
        calculate_category_learning_signal(
            property_name=PROPERTY_NAME,
            category=CATEGORY
        )
    )

    assert isinstance(
        category_signal,
        dict
    )

    assert category_signal[
        "outcome_count"
    ] >= 3

    assert category_signal[
        "performance"
    ] > 50.0

    assert category_signal[
        "adjustment"
    ] > 0.0

    # -------------------------------------------------------
    # Stage 4: Candidate Adaptation
    # -------------------------------------------------------

    candidate = {
        "property_name":
            PROPERTY_NAME,
        "event_id":
            EVENT_ID,
        "event_name":
            EVENT_NAME,
        "category":
            CATEGORY,
        "final_score":
            70.0
    }

    enriched = enrich_candidate_with_learning(
        candidate
    )

    assert isinstance(
        enriched,
        dict
    )

    assert "learning_signal" in enriched

    assert "learning_adjustment" in enriched

    assert enriched[
        "learning_adjustment"
    ] > 0.0

    assert enriched[
        "final_score"
    ] > candidate[
        "final_score"
    ]

    # -------------------------------------------------------
    # Results
    # -------------------------------------------------------

    print(
        "Continuous learning system test passed.\n"
    )

    print(
        "Event Learning Signal:"
    )

    print(
        event_signal
    )

    print(
        "\nCategory Learning Signal:"
    )

    print(
        category_signal
    )

    print(
        "\nCandidate Score:"
    )

    print(
        f"Before: "
        f"{candidate['final_score']}"
    )

    print(
        f"Learning Adjustment: "
        f"{enriched['learning_adjustment']}"
    )

    print(
        f"After: "
        f"{enriched['final_score']}"
    )

    print(
        "\nTribeIQ continuous learning is working."
    )


if __name__ == "__main__":

    run_test()