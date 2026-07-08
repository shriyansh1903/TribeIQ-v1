"""
===========================================================
TribeIQ Recommendation Engine
===========================================================

Backward-compatible entry point for the complete hybrid
recommendation system.

Responsibilities:
1. Preserve the existing backend interface
2. Prepare property and event data
3. Call the recommendation pipeline
4. Return major and minor recommendations
===========================================================
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


# ===========================================================
# Permanent Import Path Fix
# ===========================================================

SRC_DIR = Path(__file__).resolve().parent

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


# ===========================================================
# Project Imports
# ===========================================================

from recommendation.pipeline import (
    run_recommendation_pipeline
)


# ===========================================================
# Helpers
# ===========================================================

def safe_text(value: Any) -> str:

    if value is None:
        return ""

    return str(value).strip()


def safe_dataframe(
    value: Any
) -> pd.DataFrame:

    if isinstance(value, pd.DataFrame):
        return value.copy()

    return pd.DataFrame()


def dataframe_to_records(
    value: Any
) -> List[Dict[str, Any]]:

    if isinstance(value, pd.DataFrame):

        return value.to_dict(
            orient="records"
        )

    if isinstance(value, list):

        return [
            item
            for item in value
            if isinstance(item, dict)
        ]

    return []


def normalize_profiles(
    profiles: Any
) -> Dict[str, Dict[str, Any]]:

    if isinstance(profiles, dict):

        return {
            safe_text(property_name): profile
            for property_name, profile in profiles.items()
            if (
                safe_text(property_name)
                and isinstance(profile, dict)
            )
        }

    return {}


# ===========================================================
# Recommendation Engine
# ===========================================================

class RecommendationEngine:

    def __init__(
        self,
        events: Any,
        profiles: Optional[
            Dict[str, Dict[str, Any]]
        ] = None,
        history: Optional[pd.DataFrame] = None,
        use_llm: bool = True,
        use_learning: bool = True
    ):

        self.events = dataframe_to_records(
            events
        )

        self.profiles = normalize_profiles(
            profiles
        )

        self.history = safe_dataframe(
            history
        )

        self.use_llm = bool(
            use_llm
        )

        self.use_learning = bool(
            use_learning
        )

    # =======================================================
    # Profile Resolution
    # =======================================================

    def get_profile(
        self,
        property_name: str,
        profile: Optional[
            Dict[str, Any]
        ] = None
    ) -> Dict[str, Any]:

        if isinstance(profile, dict):
            return profile

        if property_name in self.profiles:
            return self.profiles[
                property_name
            ]

        target = safe_text(
            property_name
        ).lower()

        for name, stored_profile in (
            self.profiles.items()
        ):

            if (
                safe_text(name).lower()
                == target
            ):

                return stored_profile

        return {}

    # =======================================================
    # Generate Recommendations
    # =======================================================

    def recommend(
        self,
        property_name: str,
        profile: Optional[
            Dict[str, Any]
        ] = None,
        save_signals: bool = True
    ) -> Dict[str, Any]:

        property_name = safe_text(
            property_name
        )

        if not property_name:

            return {
                "property_name": "",
                "major_event": None,
                "minor_events": [],
                "selected_count": 0,
                "candidate_count": 0,
                "ranked_candidates": [],
                "error":
                    "Property name is required."
            }

        resolved_profile = self.get_profile(
            property_name=property_name,
            profile=profile
        )

        profiles = dict(
            self.profiles
        )

        if property_name not in profiles:

            profiles[property_name] = (
                resolved_profile
            )

        return run_recommendation_pipeline(
            property_name=property_name,
            profile=resolved_profile,
            events=self.events,
            profiles=profiles,
            history=self.history,
            use_llm=self.use_llm,
            use_learning=self.use_learning,
            save_signals=save_signals
        )

    # =======================================================
    # Ranked Candidates
    # =======================================================

    def rank(
        self,
        property_name: str,
        profile: Optional[
            Dict[str, Any]
        ] = None
    ) -> List[Dict[str, Any]]:

        result = self.recommend(
            property_name=property_name,
            profile=profile,
            save_signals=False
        )

        return result.get(
            "ranked_candidates",
            []
        )


# ===========================================================
# Functional Interface
# ===========================================================

def generate_recommendations(
    property_name: str,
    profile: Dict[str, Any],
    events: Any,
    profiles: Optional[
        Dict[str, Dict[str, Any]]
    ] = None,
    history: Optional[pd.DataFrame] = None,
    use_llm: bool = True,
    use_learning: bool = True,
    save_signals: bool = True
) -> Dict[str, Any]:

    engine = RecommendationEngine(
        events=events,
        profiles=profiles,
        history=history,
        use_llm=use_llm,
        use_learning=use_learning
    )

    return engine.recommend(
        property_name=property_name,
        profile=profile,
        save_signals=save_signals
    )