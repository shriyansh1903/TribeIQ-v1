"""
===========================================================
TribeIQ Main Pipeline
===========================================================

Runs the complete TribeIQ backend pipeline.

Responsibilities:
1. Load and validate resident data
2. Clean resident data
3. Build property profiles
4. Load event catalogue and event history
5. Run the hybrid recommendation system
6. Save recommendation outputs

The Streamlit UI remains separate from this file.
===========================================================
"""

import sys
from pathlib import Path
from typing import Any, Dict

import pandas as pd


# ===========================================================
# Project Paths
# ===========================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = Path(__file__).resolve().parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


# ===========================================================
# Existing Backend Imports
# ===========================================================

from loader import load_residents
from validator import validate_residents

from recommendation_engine import (
    RecommendationEngine
)


# ===========================================================
# Optional Existing Module Imports
# ===========================================================

try:
    from cleaner import clean_residents

except ImportError:
    clean_residents = None


try:
    from feature_engineering import create_features
    from profile_generator import generate_profiles
    def build_property_profiles(residents):
        residents = create_features(residents)
        profiles, _ = generate_profiles(residents)
        return profiles
except ImportError:
    build_property_profiles = None


# ===========================================================
# Data Discovery
# ===========================================================

DATA_DIR = PROJECT_ROOT / "data"

EVENT_FILE_NAMES = (
    "Events.csv",
    "events.csv",
    "Event_Catalogue.csv",
    "Event_Catalog.csv",
    "Events_Cleaned.csv"
)

HISTORY_FILE_NAMES = (
    "Event_History.csv",
    "event_history.csv",
    "Events_History.csv",
    "Historical_Events.csv"
)

OUTPUT_DIR = DATA_DIR / "outputs"

RECOMMENDATION_OUTPUT = (
    OUTPUT_DIR / "Recommendations.csv"
)


# ===========================================================
# Helpers
# ===========================================================

def find_data_file(
    file_names: tuple
) -> Path | None:

    search_directories = (
        DATA_DIR,
        DATA_DIR / "raw",
        DATA_DIR / "processed",
        DATA_DIR / "cleaned"
    )

    for directory in search_directories:

        for file_name in file_names:

            path = directory / file_name

            if path.exists():
                return path

    return None


def load_csv_if_available(
    file_names: tuple
) -> pd.DataFrame:

    path = find_data_file(
        file_names
    )

    if path is None:
        return pd.DataFrame()

    try:

        return pd.read_csv(path)

    except Exception:
        return pd.DataFrame()


def safe_text(value: Any) -> str:

    if value is None:
        return ""

    return str(value).strip()


# ===========================================================
# Resident Preparation
# ===========================================================

def prepare_residents() -> pd.DataFrame:

    residents = load_residents()

    validate_residents(residents)

    if clean_residents is not None:

        residents = clean_residents(
            residents
        )

    return residents


# ===========================================================
# Profile Builder Fallback
# ===========================================================

def build_profiles_fallback(
    residents: pd.DataFrame
) -> Dict[str, Dict[str, Any]]:

    if residents.empty:
        return {}

    property_column = None

    for column in (
        "Property",
        "property",
        "Property Name",
        "property_name"
    ):

        if column in residents.columns:

            property_column = column

            break

    if property_column is None:
        return {}

    profiles = {}

    for property_name, group in residents.groupby(
        property_column,
        dropna=True
    ):

        name = safe_text(
            property_name
        )

        if not name:
            continue

        profile = {
            "Resident Count":
                int(len(group))
        }

        for age_column in (
            "Age",
            "age"
        ):

            if age_column in group.columns:

                ages = pd.to_numeric(
                    group[age_column],
                    errors="coerce"
                )

                if ages.notna().any():

                    profile["Average Age"] = (
                        float(ages.mean())
                    )

                break

        for interest_column in (
            "Interests",
            "interests"
        ):

            if interest_column in group.columns:

                interests = (
                    group[interest_column]
                    .dropna()
                    .astype(str)
                    .str.split(
                        r"[,;|/]"
                    )
                    .explode()
                    .str.strip()
                )

                interests = interests[
                    interests != ""
                ]

                profile["Top Interests"] = (
                    interests
                    .value_counts()
                    .head(10)
                    .to_dict()
                )

                break

        profiles[name] = profile

    return profiles


def prepare_profiles(
    residents: pd.DataFrame
) -> Dict[str, Dict[str, Any]]:

    if build_property_profiles is None:

        return build_profiles_fallback(
            residents
        )

    try:

        profiles = build_property_profiles(
            residents
        )

    except Exception:

        return build_profiles_fallback(
            residents
        )

    if isinstance(profiles, dict):
        return profiles

    return build_profiles_fallback(
        residents
    )


# ===========================================================
# Recommendation Output
# ===========================================================

def flatten_recommendations(
    results: Dict[
        str,
        Dict[str, Any]
    ]
) -> pd.DataFrame:

    rows = []

    for property_name, result in results.items():

        major_event = result.get(
            "major_event"
        )

        if isinstance(major_event, dict):

            rows.append({
                "Property":
                    property_name,
                "Recommendation Type":
                    "Major",
                "Rank":
                    1,
                "Event ID":
                    major_event.get(
                        "event_id",
                        ""
                    ),
                "Event Name":
                    major_event.get(
                        "event_name",
                        ""
                    ),
                "Category":
                    major_event.get(
                        "category",
                        ""
                    ),
                "Score":
                    major_event.get(
                        "final_score",
                        0.0
                    )
            })

        minor_events = result.get(
            "minor_events",
            []
        )

        if not isinstance(
            minor_events,
            list
        ):
            continue

        for index, event in enumerate(
            minor_events,
            start=1
        ):

            if not isinstance(event, dict):
                continue

            rows.append({
                "Property":
                    property_name,
                "Recommendation Type":
                    "Minor",
                "Rank":
                    index,
                "Event ID":
                    event.get(
                        "event_id",
                        ""
                    ),
                "Event Name":
                    event.get(
                        "event_name",
                        ""
                    ),
                "Category":
                    event.get(
                        "category",
                        ""
                    ),
                "Score":
                    event.get(
                        "final_score",
                        0.0
                    )
            })

    return pd.DataFrame(rows)


def save_recommendations(
    results: Dict[
        str,
        Dict[str, Any]
    ]
) -> pd.DataFrame:

    output = flatten_recommendations(
        results
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    output.to_csv(
        RECOMMENDATION_OUTPUT,
        index=False
    )

    return output


# ===========================================================
# Run
# ===========================================================

def run() -> Dict[str, Dict[str, Any]]:

    print(
        "Starting TribeIQ pipeline...\n"
    )

    residents = prepare_residents()

    profiles = prepare_profiles(
        residents
    )

    events = load_csv_if_available(
        EVENT_FILE_NAMES
    )

    history = load_csv_if_available(
        HISTORY_FILE_NAMES
    )

    if events.empty:

        raise FileNotFoundError(
            "No event catalogue CSV was found "
            "inside the data directory."
        )

    if not profiles:

        raise ValueError(
            "No property profiles could be built."
        )

    engine = RecommendationEngine(
        events=events,
        profiles=profiles,
        history=history,
        use_llm=True,
        use_learning=True
    )

    results = {}

    for property_name, profile in (
        profiles.items()
    ):

        print(
            f"Generating recommendations: "
            f"{property_name}"
        )

        results[property_name] = (
            engine.recommend(
                property_name=property_name,
                profile=profile,
                save_signals=True
            )
        )

    output = save_recommendations(
        results
    )

    print()
    print(
        "TribeIQ pipeline completed successfully."
    )
    print(
        f"Properties : {len(results)}"
    )
    print(
        f"Recommendations : {len(output)}"
    )
    print(
        f"Output : {RECOMMENDATION_OUTPUT}"
    )

    return results


if __name__ == "__main__":

    run()