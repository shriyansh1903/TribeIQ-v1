"""
===========================================================
TribeIQ Frontend-Backend Integration Test
===========================================================
"""

import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


from ui_data_bridge import (
    generate_property_recommendations,
    load_application_data,
    normalize_recommendation_result,
    validate_application_data
)


def run_test():

    print(
        "Testing TribeIQ frontend-backend integration...\n"
    )

    data = load_application_data()

    assert isinstance(data, dict)

    assert isinstance(
        data.get("residents"),
        pd.DataFrame
    )

    assert isinstance(
        data.get("profiles"),
        dict
    )

    assert isinstance(
        data.get("events"),
        pd.DataFrame
    )

    assert isinstance(
        data.get("history"),
        pd.DataFrame
    )

    errors = validate_application_data(
        data
    )

    if errors:

        raise AssertionError(
            "Application data validation failed: "
            + " | ".join(errors)
        )

    print(
        f"Residents connected: "
        f"{len(data['residents'])}"
    )

    print(
        f"Properties connected: "
        f"{len(data['profiles'])}"
    )

    print(
        f"Events connected: "
        f"{len(data['events'])}"
    )

    print(
        f"History connected: "
        f"{len(data['history'])}"
    )

    property_name = next(
        iter(data["profiles"])
    )

    print(
        f"\nTesting property: {property_name}"
    )

    result = generate_property_recommendations(
        property_name=property_name,
        data=data,
        use_llm=True,
        use_learning=True,
        save_signals=False
    )

    assert isinstance(
        result,
        dict
    )

    assert (
        result.get("property_name")
        == property_name
    )

    assert isinstance(
        result.get("ranked_candidates"),
        list
    )

    assert len(
        result.get(
            "ranked_candidates",
            []
        )
    ) > 0

    assert isinstance(
        result.get("minor_events"),
        list
    )

    assert (
        result.get("major_event") is None
        or isinstance(
            result.get("major_event"),
            dict
        )
    )

    assert (
        result.get("candidate_count", 0)
        == len(
            result.get(
                "ranked_candidates",
                []
            )
        )
    )

    expected_selected_count = (
        (
            1
            if isinstance(
                result.get("major_event"),
                dict
            )
            else 0
        )
        + len(
            result.get(
                "minor_events",
                []
            )
        )
    )

    assert (
        result.get("selected_count")
        == expected_selected_count
    )

    for candidate in result.get(
        "ranked_candidates",
        []
    ):

        assert "event_id" in candidate
        assert "event_name" in candidate
        assert "category" in candidate
        assert "rank" in candidate
        assert "final_score" in candidate
        assert "llm_adjustment" in candidate
        assert "learning_adjustment" in candidate

    print(
        "\nFrontend-backend integration test passed."
    )

    print(
        f"Candidates evaluated: "
        f"{result['candidate_count']}"
    )

    print(
        f"Events selected: "
        f"{result['selected_count']}"
    )

    major_event = result.get(
        "major_event"
    )

    if isinstance(major_event, dict):

        print(
            f"Major event: "
            f"{major_event.get('event_name')}"
        )

    for index, event in enumerate(
        result.get(
            "minor_events",
            []
        ),
        start=1
    ):

        print(
            f"Minor event {index}: "
            f"{event.get('event_name')}"
        )

    print(
        "\nTribeIQ frontend and backend are connected."
    )


if __name__ == "__main__":

    run_test()