"""
===========================================================
TribeIQ Production Pipeline Test
===========================================================

Tests the recommendation system using the real project data.

This version permanently fixes event/history CSV discovery by
searching the complete data directory instead of depending on
specific filenames.
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
DATA_DIR = PROJECT_ROOT / "data"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


# ===========================================================
# Project Imports
# ===========================================================

from main import (
    prepare_residents,
    prepare_profiles
)

from recommendation_engine import (
    RecommendationEngine
)


# ===========================================================
# CSV Helpers
# ===========================================================

def normalize_column_name(value):

    return (
        str(value)
        .strip()
        .lower()
        .replace("_", " ")
        .replace("-", " ")
    )


def read_csv_safely(path):

    try:
        return pd.read_csv(path)

    except Exception:
        return pd.DataFrame()


def find_all_csv_files():

    if not DATA_DIR.exists():
        return []

    return list(
        DATA_DIR.rglob("*.csv")
    )


# ===========================================================
# Event Catalogue Detection
# ===========================================================

def is_event_catalogue(dataframe):

    if dataframe.empty:
        return False

    columns = {
        normalize_column_name(column)
        for column in dataframe.columns
    }

    event_name_columns = {
        "event name",
        "event",
        "name"
    }

    category_columns = {
        "category",
        "event category"
    }

    has_event_name = bool(
        columns.intersection(
            event_name_columns
        )
    )

    has_category = bool(
        columns.intersection(
            category_columns
        )
    )

    history_markers = {
        "attendance %",
        "attendance",
        "average feedback",
        "avg feedback",
        "success score"
    }

    looks_like_history = bool(
        columns.intersection(
            history_markers
        )
    )

    return (
        has_event_name
        and has_category
        and not looks_like_history
    )


def find_event_catalogue():

    preferred_names = (
        "event_catalogue.csv",
        "event_catalog.csv",
        "events.csv",
        "events_cleaned.csv",
        "event_master.csv",
        "event_library.csv"
    )

    csv_files = find_all_csv_files()

    for preferred_name in preferred_names:

        for path in csv_files:

            if (
                path.name.lower()
                == preferred_name
            ):

                dataframe = read_csv_safely(
                    path
                )

                if not dataframe.empty:

                    return dataframe, path

    for path in csv_files:

        dataframe = read_csv_safely(
            path
        )

        if is_event_catalogue(
            dataframe
        ):

            return dataframe, path

    return pd.DataFrame(), None


# ===========================================================
# Event History Detection
# ===========================================================

def is_event_history(dataframe):

    if dataframe.empty:
        return False

    columns = {
        normalize_column_name(column)
        for column in dataframe.columns
    }

    event_columns = {
        "event name",
        "event",
        "name"
    }

    property_columns = {
        "property",
        "property name"
    }

    outcome_columns = {
        "attendance %",
        "attendance",
        "average feedback",
        "avg feedback",
        "feedback",
        "success score"
    }

    has_event = bool(
        columns.intersection(
            event_columns
        )
    )

    has_property = bool(
        columns.intersection(
            property_columns
        )
    )

    has_outcome = bool(
        columns.intersection(
            outcome_columns
        )
    )

    return (
        has_event
        and has_property
        and has_outcome
    )


def find_event_history():

    preferred_names = (
        "event_history.csv",
        "events_history.csv",
        "historical_events.csv",
        "history.csv",
        "event_log.csv"
    )

    csv_files = find_all_csv_files()

    for preferred_name in preferred_names:

        for path in csv_files:

            if (
                path.name.lower()
                == preferred_name
            ):

                dataframe = read_csv_safely(
                    path
                )

                if not dataframe.empty:

                    return dataframe, path

    for path in csv_files:

        dataframe = read_csv_safely(
            path
        )

        if is_event_history(
            dataframe
        ):

            return dataframe, path

    return pd.DataFrame(), None


# ===========================================================
# Test
# ===========================================================

def run_test():

    print(
        "Testing TribeIQ production pipeline...\n"
    )

    # -------------------------------------------------------
    # Stage 1: Residents
    # -------------------------------------------------------

    residents = prepare_residents()

    assert isinstance(
        residents,
        pd.DataFrame
    )

    assert not residents.empty

    print(
        f"Residents loaded: {len(residents)}"
    )

    # -------------------------------------------------------
    # Stage 2: Property Profiles
    # -------------------------------------------------------

    profiles = prepare_profiles(
        residents
    )

    assert isinstance(
        profiles,
        dict
    )

    assert len(profiles) > 0

    print(
        f"Property profiles: {len(profiles)}"
    )

    # -------------------------------------------------------
    # Stage 3: Event Catalogue
    # -------------------------------------------------------

    events, event_path = (
        find_event_catalogue()
    )

    if events.empty:

        csv_files = find_all_csv_files()

        print(
            "\nCSV files found:"
        )

        for path in csv_files:

            dataframe = read_csv_safely(
                path
            )

            print(
                f"- {path.relative_to(PROJECT_ROOT)}"
            )

            print(
                f"  Columns: "
                f"{list(dataframe.columns)}"
            )

        raise FileNotFoundError(
            "\nNo valid event catalogue was found.\n"
            "The event catalogue must contain at least:\n"
            "- Event Name\n"
            "- Category"
        )

    print(
        f"Events loaded: {len(events)}"
    )

    print(
        f"Event file: "
        f"{event_path.relative_to(PROJECT_ROOT)}"
    )

    # -------------------------------------------------------
    # Stage 4: Event History
    # -------------------------------------------------------

    history, history_path = (
        find_event_history()
    )

    print(
        f"History records: {len(history)}"
    )

    if history_path is not None:

        print(
            f"History file: "
            f"{history_path.relative_to(PROJECT_ROOT)}"
        )

    else:

        print(
            "No event history file found. "
            "Continuing with empty history."
        )

    # -------------------------------------------------------
    # Stage 5: Recommendation Engine
    # -------------------------------------------------------

    engine = RecommendationEngine(
        events=events,
        profiles=profiles,
        history=history,
        use_llm=True,
        use_learning=True
    )

    # -------------------------------------------------------
    # Stage 6: Test First Property
    # -------------------------------------------------------

    property_name = next(
        iter(profiles)
    )

    profile = profiles[
        property_name
    ]

    print(
        f"\nTesting property: {property_name}"
    )

    result = engine.recommend(
        property_name=property_name,
        profile=profile,
        save_signals=False
    )

    # -------------------------------------------------------
    # Stage 7: Validate Result
    # -------------------------------------------------------

    assert isinstance(
        result,
        dict
    )

    assert (
        result.get("property_name")
        == property_name
    )

    ranked_candidates = result.get(
        "ranked_candidates",
        []
    )

    assert isinstance(
        ranked_candidates,
        list
    )

    if not ranked_candidates:

        raise AssertionError(
            "The pipeline produced zero candidates. "
            "Check event catalogue column mappings."
        )

    for candidate in ranked_candidates:

        assert isinstance(
            candidate,
            dict
        )

        assert candidate.get(
            "event_id"
        )

        assert candidate.get(
            "event_name"
        )

        assert "final_score" in candidate
        assert "rank" in candidate
        assert "learning_adjustment" in candidate
        assert "llm_adjustment" in candidate

    # -------------------------------------------------------
    # Stage 8: Validate Selection
    # -------------------------------------------------------

    major_event = result.get(
        "major_event"
    )

    minor_events = result.get(
        "minor_events",
        []
    )

    assert (
        major_event is None
        or isinstance(
            major_event,
            dict
        )
    )

    assert isinstance(
        minor_events,
        list
    )

    # -------------------------------------------------------
    # Results
    # -------------------------------------------------------

    print(
        "\nProduction pipeline test passed."
    )

    print(
        f"Candidates: "
        f"{len(ranked_candidates)}"
    )

    print(
        f"Selected: "
        f"{result.get('selected_count', 0)}"
    )

    print(
        "\nTop Ranked Candidates:"
    )

    for candidate in ranked_candidates[:5]:

        print(
            f"{candidate.get('rank')}. "
            f"{candidate.get('event_name')} | "
            f"Score: "
            f"{candidate.get('final_score')} | "
            f"LLM: "
            f"{candidate.get('llm_adjustment')} | "
            f"Learning: "
            f"{candidate.get('learning_adjustment')}"
        )

    print(
        "\nFinal Selection:"
    )

    if isinstance(
        major_event,
        dict
    ):

        print(
            f"Major Event: "
            f"{major_event.get('event_name')}"
        )

    for index, event in enumerate(
        minor_events,
        start=1
    ):

        print(
            f"Minor Event {index}: "
            f"{event.get('event_name')}"
        )

    print(
        "\nTribeIQ production pipeline is working."
    )


if __name__ == "__main__":

    run_test()