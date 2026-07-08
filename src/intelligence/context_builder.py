"""
===========================================================
TribeIQ LLM Context Builder
===========================================================
"""

import sys
from pathlib import Path
from datetime import date, datetime
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

from recommendation.config import LLM_CANDIDATE_LIMIT

from recommendation.feature_builder import (
    safe_float,
    safe_text,
    normalize_text,
    prepare_history
)


# ===========================================================
# Configuration
# ===========================================================

MAX_HISTORY_RECORDS = 20
MAX_REASON_ITEMS = 5
MAX_RISK_ITEMS = 5
MAX_TEXT_LENGTH = 500


# ===========================================================
# JSON Safety
# ===========================================================

def make_json_safe(value: Any) -> Any:

    if value is None:
        return None

    if isinstance(value, (str, int, bool)):
        return value

    if isinstance(value, float):

        if pd.isna(value):
            return None

        return value

    if isinstance(
        value,
        (datetime, date, pd.Timestamp)
    ):
        return value.isoformat()

    if isinstance(value, dict):

        return {
            str(key): make_json_safe(item)
            for key, item in value.items()
        }

    if isinstance(
        value,
        (list, tuple, set)
    ):

        return [
            make_json_safe(item)
            for item in value
        ]

    try:

        if pd.isna(value):
            return None

    except (TypeError, ValueError):
        pass

    return str(value)


# ===========================================================
# Text Safety
# ===========================================================

def limit_text(
    value: Any,
    maximum: int = MAX_TEXT_LENGTH
) -> str:

    text = safe_text(value)

    if len(text) <= maximum:
        return text

    return text[:maximum].rstrip()


def clean_text_list(
    value: Any,
    maximum_items: int
) -> List[str]:

    if not isinstance(value, list):
        return []

    cleaned = []

    for item in value:

        text = limit_text(item)

        if not text:
            continue

        cleaned.append(text)

        if len(cleaned) >= maximum_items:
            break

    return cleaned


# ===========================================================
# Property Context
# ===========================================================

def build_property_context(
    property_name: str,
    profile: Dict[str, Any]
) -> Dict[str, Any]:

    if not isinstance(profile, dict):
        profile = {}

    allowed_fields = (
        "Resident Count",
        "Average Age",
        "Median Age",
        "Average Tenure",
        "Median Tenure",
        "Community Size",
        "Community Stage",
        "Dominant Occupation",
        "Dominant Age Band",
        "Dominant Region",
        "Top Interests",
        "Gender Distribution",
        "Occupation Distribution",
        "Age Distribution",
        "Tenure Distribution",
        "Region Distribution"
    )

    context = {
        "property_name": safe_text(
            property_name
        )
    }

    for field in allowed_fields:

        if field not in profile:
            continue

        context[field] = make_json_safe(
            profile[field]
        )

    return context


# ===========================================================
# Candidate Context
# ===========================================================

def build_candidate_context(
    candidate: Dict[str, Any],
    rank: int
) -> Dict[str, Any]:

    if not isinstance(candidate, dict):
        return {}

    signals = candidate.get(
        "signals",
        {}
    )

    penalties = candidate.get(
        "penalties",
        {}
    )

    collaborative = candidate.get(
        "collaborative_signal",
        {}
    )

    features = candidate.get(
        "features",
        {}
    )

    if not isinstance(features, dict):
        features = {}

    historical_features = features.get(
        "history",
        {}
    )

    if not isinstance(
        historical_features,
        dict
    ):
        historical_features = {}

    event_data = candidate.get(
        "event_data",
        {}
    )

    if not isinstance(event_data, dict):
        event_data = {}

    return make_json_safe({
        "event_id": safe_text(
            candidate.get(
                "event_id",
                ""
            )
        ),
        "event_name": safe_text(
            candidate.get(
                "event_name",
                ""
            )
        ),
        "category": safe_text(
            candidate.get(
                "category",
                "Unknown"
            )
        ),
        "current_rank": rank,
        "candidate_score": round(
            safe_float(
                candidate.get(
                    "candidate_score",
                    0.0
                )
            ),
            4
        ),
        "base_score": round(
            safe_float(
                candidate.get(
                    "base_score",
                    0.0
                )
            ),
            4
        ),
        "final_score": round(
            safe_float(
                candidate.get(
                    "final_score",
                    0.0
                )
            ),
            4
        ),
        "signals":
            signals
            if isinstance(signals, dict)
            else {},
        "penalties":
            penalties
            if isinstance(penalties, dict)
            else {},
        "historical_evidence":
            historical_features,
        "collaborative_evidence":
            collaborative
            if isinstance(collaborative, dict)
            else {},
        "event_metadata":
            event_data,
        "reasons": clean_text_list(
            candidate.get(
                "reasons",
                []
            ),
            MAX_REASON_ITEMS
        ),
        "risk_flags": clean_text_list(
            candidate.get(
                "risk_flags",
                []
            ),
            MAX_RISK_ITEMS
        )
    })


# ===========================================================
# History Context
# ===========================================================

def filter_property_history(
    history: pd.DataFrame,
    property_name: str
) -> pd.DataFrame:

    if history.empty:
        return history.copy()

    if "Property" not in history.columns:

        return pd.DataFrame(
            columns=history.columns
        )

    mask = (
        history["Property"]
        .astype(str)
        .str.strip()
        .str.lower()
        == normalize_text(property_name)
    )

    return history.loc[mask].copy()


def build_history_context(
    property_name: str,
    history: Optional[pd.DataFrame]
) -> List[Dict[str, Any]]:

    prepared = prepare_history(history)

    if prepared.empty:
        return []

    property_history = filter_property_history(
        prepared,
        property_name
    )

    if property_history.empty:
        return []

    if "Date" in property_history.columns:

        property_history = (
            property_history
            .sort_values(
                "Date",
                ascending=False,
                na_position="last"
            )
        )

    allowed_columns = [
        column
        for column in (
            "Date",
            "Property",
            "Event Name",
            "Category",
            "Attendance %",
            "Average Feedback",
            "Success Score",
            "Budget Planned",
            "Budget Spent"
        )
        if column in property_history.columns
    ]

    if not allowed_columns:
        return []

    records = (
        property_history[
            allowed_columns
        ]
        .head(MAX_HISTORY_RECORDS)
        .to_dict(
            orient="records"
        )
    )

    return make_json_safe(records)


# ===========================================================
# System Prompt
# ===========================================================

def build_system_prompt() -> str:

    return """
You are the contextual reranking layer of TribeIQ.

You receive:
1. One property profile.
2. Existing recommendation candidates.
3. Numerical scoring evidence.
4. Historical event performance.

Rules:
- Never create an event outside the candidate list.
- Never change an event_id.
- Return every supplied candidate exactly once.
- Rank candidates from strongest to weakest.
- adjustment must be between -5.0 and 5.0.
- Use numerical evidence before subjective reasoning.
- Penalize repetition, fatigue, weak evidence and contextual risk.
- Reward resident fit, historical performance, diversity and credible exploration.
- Never override deterministic constraints.
- Return valid JSON only.

Required JSON structure:
{
  "property_name": "string",
  "candidates": [
    {
      "event_id": "string",
      "rank": 1,
      "adjustment": 0.0,
      "confidence": 0.0,
      "reasoning": ["string"],
      "risk_flags": ["string"]
    }
  ],
  "summary": "string"
}
""".strip()


# ===========================================================
# Complete Reranking Context
# ===========================================================

def build_reranking_context(
    property_name: str,
    profile: Dict[str, Any],
    ranked_candidates: List[Dict[str, Any]],
    history: Optional[pd.DataFrame] = None
) -> Dict[str, Any]:

    if not isinstance(
        ranked_candidates,
        list
    ):
        ranked_candidates = []

    candidate_limit = max(
        1,
        int(LLM_CANDIDATE_LIMIT)
    )

    candidates = []
    seen_event_ids = set()

    for candidate in ranked_candidates:

        if not isinstance(candidate, dict):
            continue

        event_id = safe_text(
            candidate.get(
                "event_id",
                ""
            )
        )

        if not event_id:
            continue

        if event_id in seen_event_ids:
            continue

        seen_event_ids.add(event_id)

        candidates.append(candidate)

        if len(candidates) >= candidate_limit:
            break

    candidate_context = [
        build_candidate_context(
            candidate,
            rank=index
        )
        for index, candidate in enumerate(
            candidates,
            start=1
        )
    ]

    return make_json_safe({
        "task":
            "Rerank the supplied candidates using only the provided evidence.",
        "property":
            build_property_context(
                property_name,
                profile
            ),
        "candidates":
            candidate_context,
        "recent_history":
            build_history_context(
                property_name,
                history
            ),
        "constraints": {
            "candidate_count":
                len(candidate_context),
            "allowed_event_ids": [
                candidate["event_id"]
                for candidate in candidate_context
            ],
            "maximum_adjustment":
                5.0,
            "new_events_allowed":
                False
        }
    })