"""
===========================================================
TribeIQ Selection Logic
===========================================================

Backward-compatible selection interface for the hybrid
recommendation system.

Responsibilities:
1. Preserve existing selection imports
2. Accept ranked recommendation candidates
3. Apply final diversity constraints
4. Return one major and two minor events
===========================================================
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


# ===========================================================
# Permanent Import Path Fix
# ===========================================================

SRC_DIR = Path(__file__).resolve().parent

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


# ===========================================================
# Project Imports
# ===========================================================

from recommendation.diversity_engine import (
    select_diverse_recommendations
)


# ===========================================================
# Helpers
# ===========================================================

def safe_candidates(
    candidates: Any
) -> List[Dict[str, Any]]:

    if not isinstance(candidates, list):
        return []

    return [
        candidate
        for candidate in candidates
        if isinstance(candidate, dict)
    ]


# ===========================================================
# Complete Selection
# ===========================================================

def select_recommendations(
    ranked_candidates: List[Dict[str, Any]]
) -> Dict[str, Any]:

    candidates = safe_candidates(
        ranked_candidates
    )

    return select_diverse_recommendations(
        candidates
    )


# ===========================================================
# Major Event Selection
# ===========================================================

def select_major_event(
    ranked_candidates: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:

    result = select_recommendations(
        ranked_candidates
    )

    return result.get(
        "major_event"
    )


# ===========================================================
# Minor Event Selection
# ===========================================================

def select_minor_events(
    ranked_candidates: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:

    result = select_recommendations(
        ranked_candidates
    )

    minor_events = result.get(
        "minor_events",
        []
    )

    if not isinstance(minor_events, list):
        return []

    return minor_events


# ===========================================================
# Legacy Alias
# ===========================================================

def select_events(
    ranked_candidates: List[Dict[str, Any]]
) -> Dict[str, Any]:

    return select_recommendations(
        ranked_candidates
    )