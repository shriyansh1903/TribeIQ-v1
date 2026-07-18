"""
===========================================================
TribeIQ Recommendation Pipeline
===========================================================

Orchestrates the complete hybrid recommendation system.
===========================================================
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

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

from recommendation.candidate_generator import (
    generate_candidates
)

from recommendation.affinity_engine import (
    enrich_candidates_with_affinity
)

from recommendation.collaborative_engine import (
    enrich_candidates_with_collaborative_signals
)

from recommendation.exploration_engine import (
    enrich_candidates_with_exploration
)

from recommendation.ranking_engine import (
    rank_candidates
)

from recommendation.diversity_engine import (
    select_diverse_recommendations
)

from intelligence.llm_reranker import (
    rerank_with_llm
)

from learning.feedback_learner import (
    enrich_candidates_with_learning
)

from learning.signal_store import (
    log_recommendation
)


# ===========================================================
# Helpers
# ===========================================================

def safe_profile(
    profile: Any
) -> Dict[str, Any]:

    if isinstance(profile, dict):
        return profile

    return {}


def safe_events(
    events: Any
) -> List[Dict[str, Any]]:

    if not isinstance(events, list):
        return []

    return [
        event
        for event in events
        if isinstance(event, dict)
    ]


def safe_history(
    history: Any
) -> pd.DataFrame:

    if isinstance(history, pd.DataFrame):
        return history.copy()

    return pd.DataFrame()


# ===========================================================
# Recommendation Logging
# ===========================================================

def log_selected_recommendations(
    property_name: str,
    selection: Dict[str, Any]
) -> None:

    major_event = selection.get(
        "major_event"
    )

    if isinstance(major_event, dict):

        log_recommendation(
            property_name=property_name,
            candidate=major_event,
            recommendation_type="major",
            rank=1
        )

    minor_events = selection.get(
        "minor_events",
        []
    )

    if not isinstance(minor_events, list):
        return

    for index, candidate in enumerate(
        minor_events,
        start=1
    ):

        if not isinstance(candidate, dict):
            continue

        log_recommendation(
            property_name=property_name,
            candidate=candidate,
            recommendation_type="minor",
            rank=index
        )


# ===========================================================
# Complete Pipeline
# ===========================================================

def run_recommendation_pipeline(
    property_name: str,
    profile: Dict[str, Any],
    events: List[Dict[str, Any]],
    profiles: Optional[
        Dict[str, Dict[str, Any]]
    ] = None,
    history: Optional[pd.DataFrame] = None,
    use_llm: bool = True,
    use_learning: bool = True,
    save_signals: bool = True
) -> Dict[str, Any]:

    profile = safe_profile(profile)

    events = safe_events(events)

    history = safe_history(history)

    if not isinstance(profiles, dict):

        profiles = {
            property_name: profile
        }

    # -------------------------------------------------------
    # Stage 1: Candidate Generation
    # -------------------------------------------------------

    candidates = generate_candidates(
        property_name=property_name,
        profile=profile,
        events=events,
        history=history
    )

    # -------------------------------------------------------
    # Stage 2: Affinity Signals
    # -------------------------------------------------------

    candidates = (
        enrich_candidates_with_affinity(
            candidates
        )
    )

    # -------------------------------------------------------
    # Stage 3: Collaborative Signals
    # -------------------------------------------------------

    candidates = (
        enrich_candidates_with_collaborative_signals(
            candidates=candidates,
            profiles=profiles,
            history=history
        )
    )

    # -------------------------------------------------------
    # Stage 4: Exploration
    # -------------------------------------------------------

    candidates = (
        enrich_candidates_with_exploration(
            candidates
        )
    )

    # -------------------------------------------------------
    # Stage 5: Deterministic Ranking
    # -------------------------------------------------------

    candidates = rank_candidates(
        candidates,
        property_name=property_name
    )

    # -------------------------------------------------------
    # Stage 6: Continuous Learning
    # -------------------------------------------------------

    if use_learning:

        candidates = (
            enrich_candidates_with_learning(
                candidates
            )
        )

    # -------------------------------------------------------
    # Stage 7: LLM Contextual Reranking
    # -------------------------------------------------------

    if use_llm:

        candidates = rerank_with_llm(
            property_name=property_name,
            profile=profile,
            ranked_candidates=candidates,
            history=history
        )

    # -------------------------------------------------------
    # Stage 8: Final Diversity Selection
    # -------------------------------------------------------

    selection = (
        select_diverse_recommendations(
            candidates
        )
    )

    # -------------------------------------------------------
    # Stage 9: Signal Persistence
    # -------------------------------------------------------

    if save_signals:

        log_selected_recommendations(
            property_name=property_name,
            selection=selection
        )

    # -------------------------------------------------------
    # Final Result
    # -------------------------------------------------------

    return {
        "property_name":
            property_name,
        "major_event":
            selection.get(
                "major_event"
            ),
        "minor_events":
            selection.get(
                "minor_events",
                []
            ),
        "selected_count":
            selection.get(
                "selected_count",
                0
            ),
        "candidate_count":
            selection.get(
                "candidate_count",
                0
            ),
        "ranked_candidates":
            candidates,
        "pipeline": {
            "candidate_generation":
                True,
            "affinity_engine":
                True,
            "collaborative_engine":
                True,
            "exploration_engine":
                True,
            "ranking_engine":
                True,
            "learning_engine":
                use_learning,
            "llm_reranking":
                use_llm,
            "diversity_engine":
                True
        }
    }