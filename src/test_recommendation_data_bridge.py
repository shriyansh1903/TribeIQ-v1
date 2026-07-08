"""
===========================================================
TribeIQ Recommendation Date Bridge Test
===========================================================

Permanent import-safe test.

This test:
1. Finds recommendation_date_bridge.py automatically
2. Does not assume the bridge is inside src/
3. Adds the actual bridge folder to sys.path
4. Loads the module from its exact file location
5. Prints the discovered location before testing
===========================================================
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import date
from pathlib import Path

import pandas as pd


# ===========================================================
# Project Paths
# ===========================================================

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
INTELLIGENCE_DIR = SRC_DIR / "intelligence"


# ===========================================================
# Permanent Python Path Setup
# ===========================================================

for path in (
    PROJECT_ROOT,
    SRC_DIR,
    INTELLIGENCE_DIR,
):
    if path.exists():

        path_string = str(
            path.resolve()
        )

        if path_string not in sys.path:

            sys.path.insert(
                0,
                path_string,
            )


# ===========================================================
# Find Bridge File Automatically
# ===========================================================

bridge_candidates = [
    PROJECT_ROOT
    / "recommendation_date_bridge.py",

    SRC_DIR
    / "recommendation_date_bridge.py",

    INTELLIGENCE_DIR
    / "recommendation_date_bridge.py",
]


BRIDGE_FILE = None


for candidate in bridge_candidates:

    if candidate.is_file():

        BRIDGE_FILE = candidate.resolve()

        break


if BRIDGE_FILE is None:

    discovered_files = list(
        PROJECT_ROOT.rglob(
            "recommendation_date_bridge.py"
        )
    )

    discovered_files = [
        path.resolve()
        for path in discovered_files
        if ".venv" not in path.parts
        and "__pycache__" not in path.parts
    ]

    if discovered_files:

        BRIDGE_FILE = discovered_files[0]


if BRIDGE_FILE is None:

    raise FileNotFoundError(
        "\n\n"
        "recommendation_date_bridge.py "
        "does not exist anywhere inside:\n"
        f"{PROJECT_ROOT}\n\n"
        "Create/save the file first, then rerun "
        "this test."
    )


# ===========================================================
# Add Actual Bridge Folder to Python Path
# ===========================================================

BRIDGE_DIR = BRIDGE_FILE.parent

bridge_dir_string = str(
    BRIDGE_DIR
)

if bridge_dir_string not in sys.path:

    sys.path.insert(
        0,
        bridge_dir_string,
    )


print(
    "Using recommendation date bridge:"
)

print(
    BRIDGE_FILE
)

print()


# ===========================================================
# Load Bridge From Exact File Location
# ===========================================================

MODULE_NAME = (
    "recommendation_date_bridge"
)


module_spec = (
    importlib.util.spec_from_file_location(
        MODULE_NAME,
        BRIDGE_FILE,
    )
)


if (
    module_spec is None
    or module_spec.loader is None
):

    raise ImportError(
        "Python could not create an import "
        "specification for:\n"
        f"{BRIDGE_FILE}"
    )


recommendation_date_bridge = (
    importlib.util.module_from_spec(
        module_spec
    )
)


sys.modules[
    MODULE_NAME
] = recommendation_date_bridge


module_spec.loader.exec_module(
    recommendation_date_bridge
)


# ===========================================================
# Required Functions
# ===========================================================

enrich_event_for_date = (
    recommendation_date_bridge
    .enrich_event_for_date
)

enrich_recommendation_result_for_date = (
    recommendation_date_bridge
    .enrich_recommendation_result_for_date
)

enrich_recommendation_result_with_best_dates = (
    recommendation_date_bridge
    .enrich_recommendation_result_with_best_dates
)

find_best_date_for_event = (
    recommendation_date_bridge
    .find_best_date_for_event
)


# ===========================================================
# Test Data
# ===========================================================

def build_test_history() -> pd.DataFrame:

    return pd.DataFrame(
        [
            {
                "Property":
                    "Tribe Vara",
                "Event Name":
                    "Movie Night",
                "Category":
                    "Entertainment",
                "Actual Attendance":
                    30,
                "Predicted Active Residents":
                    150,
            },
            {
                "Property":
                    "Tribe Vara",
                "Event Name":
                    "Movie Night",
                "Category":
                    "Entertainment",
                "Actual Attendance":
                    36,
                "Predicted Active Residents":
                    160,
            },
            {
                "Property":
                    "Tribe Vara",
                "Event Name":
                    "Game Night",
                "Category":
                    "Entertainment",
                "Actual Attendance":
                    25,
                "Predicted Active Residents":
                    150,
            },
        ]
    )


def build_test_recommendation_result():

    return {
        "property_name":
            "Tribe Vara",

        "candidate_count":
            3,

        "selected_count":
            3,

        "major_event": {
            "event_id":
                "event_001",

            "event_name":
                "Movie Night",

            "category":
                "Entertainment",

            "final_score":
                0.91,
        },

        "minor_events": [
            {
                "event_id":
                    "event_002",

                "event_name":
                    "Game Night",

                "category":
                    "Entertainment",

                "final_score":
                    0.84,
            },
            {
                "event_id":
                    "event_003",

                "event_name":
                    "Yoga Session",

                "category":
                    "Wellness",

                "final_score":
                    0.79,
            },
        ],
    }


# ===========================================================
# Validation
# ===========================================================

def validate_enriched_event(
    event,
):

    required_fields = (
        "event_name",
        "category",
        "event_date",
        "weekday",
        "total_capacity",
        "active_residents",
        "occupancy_percent",
        "predicted_turnout_rate",
        "predicted_attendance",
        "attendance_confidence_score",
        "attendance_confidence",
    )

    assert isinstance(
        event,
        dict,
    )

    for field in required_fields:

        assert field in event, (
            f"Missing field: {field}"
        )

    assert (
        event[
            "total_capacity"
        ]
        == 192
    )

    assert (
        event[
            "active_residents"
        ]
        >= 0
    )

    assert (
        0.0
        <= event[
            "occupancy_percent"
        ]
        <= 100.0
    )

    assert (
        0.0
        <= event[
            "predicted_turnout_rate"
        ]
        <= 100.0
    )

    assert (
        event[
            "predicted_attendance"
        ]
        >= 0
    )

    assert (
        event[
            "predicted_attendance"
        ]
        <= event[
            "active_residents"
        ]
    )


# ===========================================================
# Main Test
# ===========================================================

def run_test():

    print(
        "Testing TribeIQ recommendation "
        "date bridge...\n"
    )

    history = build_test_history()

    recommendation_result = (
        build_test_recommendation_result()
    )

    property_name = "Tribe Vara"

    reference_date = pd.Timestamp(
        date.today()
    ).normalize()


    # -------------------------------------------------------
    # Manual Event Date
    # -------------------------------------------------------

    print(
        "Testing manual event date..."
    )

    enriched_event = (
        enrich_event_for_date(
            event=(
                recommendation_result[
                    "major_event"
                ]
            ),
            property_name=property_name,
            event_date=reference_date,
            history=history,
        )
    )

    validate_enriched_event(
        enriched_event
    )


    # -------------------------------------------------------
    # Best Event Date
    # -------------------------------------------------------

    print(
        "Testing best event date..."
    )

    best_date_event = (
        find_best_date_for_event(
            event=(
                recommendation_result[
                    "major_event"
                ]
            ),
            property_name=property_name,
            year=reference_date.year,
            month=reference_date.month,
            history=history,
            start_date=reference_date,
        )
    )

    validate_enriched_event(
        best_date_event
    )

    assert (
        best_date_event[
            "date_rank"
        ]
        == 1
    )


    # -------------------------------------------------------
    # Full Manual Recommendation
    # -------------------------------------------------------

    print(
        "Testing complete manual "
        "recommendation..."
    )

    manual_result = (
        enrich_recommendation_result_for_date(
            recommendation_result=(
                recommendation_result
            ),
            property_name=property_name,
            event_date=reference_date,
            history=history,
        )
    )

    assert (
        manual_result[
            "date_mode"
        ]
        == "manual"
    )

    validate_enriched_event(
        manual_result[
            "major_event"
        ]
    )

    for event in manual_result[
        "minor_events"
    ]:

        validate_enriched_event(
            event
        )


    # -------------------------------------------------------
    # Full Best-Date Recommendation
    # -------------------------------------------------------

    print(
        "Testing complete best-date "
        "recommendation..."
    )

    best_date_result = (
        enrich_recommendation_result_with_best_dates(
            recommendation_result=(
                recommendation_result
            ),
            property_name=property_name,
            year=reference_date.year,
            month=reference_date.month,
            history=history,
            start_date=reference_date,
        )
    )

    assert (
        best_date_result[
            "date_mode"
        ]
        == "best_date"
    )

    all_events = [
        best_date_result[
            "major_event"
        ],
        *best_date_result[
            "minor_events"
        ],
    ]

    for event in all_events:

        validate_enriched_event(
            event
        )

        assert (
            event[
                "date_rank"
            ]
            == 1
        )


    # -------------------------------------------------------
    # Final Output
    # -------------------------------------------------------

    print(
        "\nRecommended event dates:"
    )

    for event in all_events:

        print(
            f"{event['event_name']}: "
            f"{event['event_date']} "
            f"({event['weekday']}) | "
            f"Occupancy "
            f"{event['occupancy_percent']:.2f}% | "
            f"Predicted attendance "
            f"{event['predicted_attendance']}"
        )

    print(
        "\nRecommendation date bridge "
        "test passed."
    )


if __name__ == "__main__":

    run_test()