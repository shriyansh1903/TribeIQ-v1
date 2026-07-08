"""
===========================================================
TribeIQ Recommendation Schemas
===========================================================

Canonical data contracts for the recommendation system.
===========================================================
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


# ===========================================================
# Signal Scores
# ===========================================================

@dataclass
class SignalScores:

    resident_affinity: float = 0.0

    property_event_affinity: float = 0.0

    historical_performance: float = 0.0

    similar_community: float = 0.0

    interest_match: float = 0.0

    predicted_success: float = 0.0

    novelty: float = 0.0

    budget_efficiency: float = 0.0

    llm_adjustment: float = 0.0

    def to_dict(self) -> Dict[str, float]:

        return asdict(self)


# ===========================================================
# Penalty Scores
# ===========================================================

@dataclass
class PenaltyScores:

    recent_event: float = 0.0

    repeat_fatigue: float = 0.0

    category_saturation: float = 0.0

    budget_risk: float = 0.0

    low_confidence: float = 0.0

    def to_dict(self) -> Dict[str, float]:

        return asdict(self)


# ===========================================================
# Recommendation Candidate
# ===========================================================

@dataclass
class RecommendationCandidate:

    event_id: str

    event_name: str

    category: str

    property_name: str

    event_data: Dict[str, Any] = field(

        default_factory=dict

    )

    signals: SignalScores = field(

        default_factory=SignalScores

    )

    penalties: PenaltyScores = field(

        default_factory=PenaltyScores

    )

    base_score: float = 0.0

    final_score: float = 0.0

    confidence: float = 0.0

    reasons: List[str] = field(

        default_factory=list

    )

    risk_flags: List[str] = field(

        default_factory=list

    )

    metadata: Dict[str, Any] = field(

        default_factory=dict

    )

    def to_dict(self) -> Dict[str, Any]:

        data = asdict(self)

        data["score_breakdown"] = {

            "signals": self.signals.to_dict(),

            "penalties": self.penalties.to_dict()

        }

        return data


# ===========================================================
# LLM Reranking Result
# ===========================================================

@dataclass
class LLMRerankingResult:

    event_id: str

    rank: int

    adjustment: float = 0.0

    confidence: float = 0.0

    reasoning: List[str] = field(

        default_factory=list

    )

    risk_flags: List[str] = field(

        default_factory=list

    )

    def to_dict(self) -> Dict[str, Any]:

        return asdict(self)


# ===========================================================
# Final Recommendation
# ===========================================================

@dataclass
class FinalRecommendation:

    property_name: str

    major_event: Optional[Dict[str, Any]] = None

    minor_events: List[Dict[str, Any]] = field(

        default_factory=list

    )

    candidate_count: int = 0

    recommendation_version: str = "2.0.0"

    metadata: Dict[str, Any] = field(

        default_factory=dict

    )

    def to_dict(self) -> Dict[str, Any]:

        return asdict(self)


# ===========================================================
# Validation Helpers
# ===========================================================

def clamp_score(

    value: float,

    minimum: float = 0.0,

    maximum: float = 100.0

) -> float:

    try:

        value = float(value)

    except (TypeError, ValueError):

        return minimum

    return max(

        minimum,

        min(value, maximum)

    )


def clamp_confidence(value: float) -> float:

    try:

        value = float(value)

    except (TypeError, ValueError):

        return 0.0

    return max(

        0.0,

        min(value, 1.0)

    )