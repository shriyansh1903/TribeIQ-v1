"""
===========================================================
TribeIQ Recommendation System Test
===========================================================

Tests the complete recommendation pipeline without requiring
the Streamlit UI.
===========================================================
"""

import sys
from pathlib import Path

import pandas as pd


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

from recommendation.pipeline import (
    run_recommendation_pipeline
)


# ===========================================================
# Test Data
# ===========================================================

PROPERTY_NAME = "Test Property"

PROFILE = {
    "Resident Count": 120,
    "Average Age": 29,
    "Average Tenure": 1.8,
    "Community Size": "Medium",
    "Community Stage": "Established",
    "Dominant Occupation": "Technology",
    "Dominant Age Band": "25-34",
    "Dominant Region": "Urban",
    "Top Interests": {
        "Technology": 40,
        "Fitness": 35,
        "Music": 30,
        "Food": 25
    }
}


EVENTS = [
    {
        "Event ID": "E001",
        "Event Name": "Tech Networking Night",
        "Category": "Networking",
        "Event Type": "Major",
        "Target Interests": "Technology, Networking",
        "Target Occupation": "Technology",
        "Target Age Band": "25-34",
        "Target Community Size": "Medium",
        "Target Community Stage": "Established"
    },
    {
        "Event ID": "E002",
        "Event Name": "Community Fitness Challenge",
        "Category": "Fitness",
        "Event Type": "Minor",
        "Target Interests": "Fitness, Wellness",
        "Target Occupation": "Technology, Business",
        "Target Age Band": "25-34",
        "Target Community Size": "Medium",
        "Target Community Stage": "Established"
    },
    {
        "Event ID": "E003",
        "Event Name": "Live Music Evening",
        "Category": "Entertainment",
        "Event Type": "Minor",
        "Target Interests": "Music",
        "Target Age Band": "25-34",
        "Target Community Size": "Medium"
    },
    {
        "Event ID": "E004",
        "Event Name": "Food Festival",
        "Category": "Food",
        "Event Type": "Major",
        "Target Interests": "Food",
        "Target Community Size": "Medium"
    }
]


PROFILES = {
    PROPERTY_NAME: PROFILE,
    "Similar Property": {
        "Resident Count": 130,
        "Average Age": 30,
        "Average Tenure": 2.0,
        "Community Size": "Medium",
        "Community Stage": "Established",
        "Dominant Occupation": "Technology",
        "Dominant Age Band": "25-34",
        "Dominant Region": "Urban",
        "Top Interests": {
            "Technology": 35,
            "Fitness": 30,
            "Music": 20
        }
    }
}


HISTORY = pd.DataFrame([
    {
        "Date": "2025-01-10",
        "Property": "Similar Property",
        "Event Name": "Tech Networking Night",
        "Category": "Networking",
        "Attendance %": 88,
        "Average Feedback": 4.6,
        "Success Score": 91,
        "Budget Planned": 5000,
        "Budget Spent": 4800
    },
    {
        "Date": "2025-03-15",
        "Property": "Similar Property",
        "Event Name": "Community Fitness Challenge",
        "Category": "Fitness",
        "Attendance %": 82,
        "Average Feedback": 4.3,
        "Success Score": 86,
        "Budget Planned": 2500,
        "Budget Spent": 2400
    }
])


# ===========================================================
# Test
# ===========================================================

def run_test():

    print(
        "Testing TribeIQ recommendation system...\n"
    )

    result = run_recommendation_pipeline(
        property_name=PROPERTY_NAME,
        profile=PROFILE,
        events=EVENTS,
        profiles=PROFILES,
        history=HISTORY,
        use_llm=False,
        use_learning=False,
        save_signals=False
    )

    assert isinstance(
        result,
        dict
    )

    assert (
        result["property_name"]
        == PROPERTY_NAME
    )

    assert isinstance(
        result["ranked_candidates"],
        list
    )

    assert len(
        result["ranked_candidates"]
    ) > 0

    print(
        "Pipeline test passed."
    )

    print(
        f"Candidates: "
        f"{result['candidate_count']}"
    )

    print(
        f"Selected: "
        f"{result['selected_count']}"
    )

    major = result.get(
        "major_event"
    )

    if major:

        print(
            f"Major Event: "
            f"{major.get('event_name')}"
        )

    for index, event in enumerate(
        result.get(
            "minor_events",
            []
        ),
        start=1
    ):

        print(
            f"Minor Event {index}: "
            f"{event.get('event_name')}"
        )

    print(
        "\nRecommendation system is working."
    )


if __name__ == "__main__":

    run_test()

