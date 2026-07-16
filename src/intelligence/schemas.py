"""
===========================================================
TribeIQ Intelligence Schemas
===========================================================

Canonical data contracts for the LLM intelligence layer.

The LLM may only rerank existing candidates and return
bounded contextual adjustments.
===========================================================
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List


# ===========================================================
# Helpers
# ===========================================================

def clamp_adjustment(
    value: Any,
    maximum: float = 5.0
) -> float:

    try:
        numeric = float(value)

    except (TypeError, ValueError):
        return 0.0

    return max(
        -maximum,
        min(numeric, maximum)
    )


def clamp_confidence(
    value: Any
) -> float:

    try:
        numeric = float(value)

    except (TypeError, ValueError):
        return 0.0

    return max(
        0.0,
        min(numeric, 1.0)
    )


def safe_text_list(
    value: Any
) -> List[str]:

    if not isinstance(value, list):
        return []

    return [
        str(item).strip()
        for item in value
        if str(item).strip()
    ]


# ===========================================================
# LLM Candidate Result
# ===========================================================

@dataclass
class LLMCandidateResult:

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

    estimated_budget_range: str = "INR 3,000 - 8,000"

    suggested_vendor_categories: str = "None"

    suggested_materials: str = "None"

    ticket_recommendation: str = "Free"

    explanation: str = ""

    def validate(
        self,
        maximum_adjustment: float = 5.0
    ) -> None:

        self.event_id = str(
            self.event_id
        ).strip()

        try:
            self.rank = max(
                1,
                int(self.rank)
            )

        except (TypeError, ValueError):
            self.rank = 1

        self.adjustment = clamp_adjustment(
            self.adjustment,
            maximum_adjustment
        )

        self.confidence = clamp_confidence(
            self.confidence
        )

        self.reasoning = safe_text_list(
            self.reasoning
        )

        self.risk_flags = safe_text_list(
            self.risk_flags
        )

        self.estimated_budget_range = str(self.estimated_budget_range).strip()
        self.suggested_vendor_categories = str(self.suggested_vendor_categories).strip()
        self.suggested_materials = str(self.suggested_materials).strip()
        self.ticket_recommendation = str(self.ticket_recommendation).strip()
        self.explanation = str(self.explanation).strip()

    def to_dict(self) -> Dict[str, Any]:

        return asdict(self)


# ===========================================================
# LLM Reranking Response
# ===========================================================

@dataclass
class LLMRerankingResponse:

    property_name: str

    candidates: List[LLMCandidateResult] = field(
        default_factory=list
    )

    summary: str = ""

    model: str = ""

    fallback_used: bool = False

    def validate(
        self,
        allowed_event_ids: List[str],
        maximum_adjustment: float = 5.0
    ) -> None:

        allowed = {
            str(event_id).strip()
            for event_id in allowed_event_ids
        }

        validated = []

        seen = set()

        for candidate in self.candidates:

            if not isinstance(
                candidate,
                LLMCandidateResult
            ):
                continue

            candidate.validate(
                maximum_adjustment
            )

            if candidate.event_id not in allowed:
                continue

            if candidate.event_id in seen:
                continue

            seen.add(
                candidate.event_id
            )

            validated.append(
                candidate
            )

        validated.sort(
            key=lambda item: item.rank
        )

        for index, candidate in enumerate(
            validated,
            start=1
        ):
            candidate.rank = index

        self.candidates = validated

        self.property_name = str(
            self.property_name
        ).strip()

        self.summary = str(
            self.summary
        ).strip()

        self.model = str(
            self.model
        ).strip()

        self.fallback_used = bool(
            self.fallback_used
        )

    def to_dict(self) -> Dict[str, Any]:

        return {
            "property_name":
                self.property_name,
            "candidates": [
                candidate.to_dict()
                for candidate in self.candidates
            ],
            "summary":
                self.summary,
            "model":
                self.model,
            "fallback_used":
                self.fallback_used
        }


# ===========================================================
# Dictionary Parser
# ===========================================================

def parse_llm_response(
    data: Dict[str, Any],
    allowed_event_ids: List[str],
    maximum_adjustment: float = 5.0
) -> LLMRerankingResponse:

    if not isinstance(data, dict):
        data = {}

    raw_candidates = data.get(
        "candidates",
        []
    )

    parsed_candidates = []

    if isinstance(raw_candidates, list):

        for item in raw_candidates:

            if not isinstance(item, dict):
                continue

            parsed_candidates.append(
                LLMCandidateResult(
                    event_id=item.get(
                        "event_id",
                        ""
                    ),
                    rank=item.get(
                        "rank",
                        1
                    ),
                    adjustment=item.get(
                        "adjustment",
                        0.0
                    ),
                    confidence=item.get(
                        "confidence",
                        0.0
                    ),
                    reasoning=item.get(
                        "reasoning",
                        []
                    ),
                    risk_flags=item.get(
                        "risk_flags",
                        []
                    ),
                    estimated_budget_range=item.get(
                        "estimated_budget_range",
                        "INR 3,000 - 8,000"
                    ),
                    suggested_vendor_categories=item.get(
                        "suggested_vendor_categories",
                        "None"
                    ),
                    suggested_materials=item.get(
                        "suggested_materials",
                        "None"
                    ),
                    ticket_recommendation=item.get(
                        "ticket_recommendation",
                        "Free"
                    ),
                    explanation=item.get(
                        "explanation",
                        ""
                    )
                )
            )

    response = LLMRerankingResponse(
        property_name=data.get(
            "property_name",
            ""
        ),
        candidates=parsed_candidates,
        summary=data.get(
            "summary",
            ""
        ),
        model=data.get(
            "model",
            ""
        ),
        fallback_used=data.get(
            "fallback_used",
            False
        )
    )

    response.validate(
        allowed_event_ids=allowed_event_ids,
        maximum_adjustment=maximum_adjustment
    )

    return response