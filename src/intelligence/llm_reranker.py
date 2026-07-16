"""
===========================================================
TribeIQ LLM Reranker
===========================================================

Applies bounded LLM adjustments to deterministically ranked
recommendation candidates.

The LLM never creates events and never performs final
selection.
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

from intelligence.context_builder import (
    build_reranking_context,
    build_system_prompt
)

from intelligence.llm_client import (
    NVIDIAClient,
    LLMClientError,
    create_client
)

from intelligence.schemas import (
    LLMRerankingResponse,
    parse_llm_response
)


# ===========================================================
# Configuration
# ===========================================================

MAXIMUM_LLM_ADJUSTMENT = 5.0


# ===========================================================
# Helpers
# ===========================================================

def safe_float(
    value: Any,
    default: float = 0.0
) -> float:

    try:
        return float(value)

    except (TypeError, ValueError):
        return default


def safe_text(
    value: Any
) -> str:

    if value is None:
        return ""

    return str(value).strip()


def clamp_score(
    value: Any,
    minimum: float = 0.0,
    maximum: float = 100.0
) -> float:

    numeric = safe_float(value)

    return max(
        minimum,
        min(numeric, maximum)
    )


# ===========================================================
# Fallback Response
# ===========================================================

def build_fallback_response(
    property_name: str,
    ranked_candidates: List[Dict[str, Any]],
    reason: str = ""
) -> LLMRerankingResponse:

    fallback_data = {
        "property_name": property_name,
        "candidates": [
            {
                "event_id": safe_text(
                    candidate.get(
                        "event_id",
                        ""
                    )
                ),
                "rank": index,
                "adjustment": 0.0,
                "confidence": 0.0,
                "reasoning": (
                    [reason]
                    if reason
                    else []
                ),
                "risk_flags": []
            }
            for index, candidate in enumerate(
                ranked_candidates,
                start=1
            )
            if safe_text(
                candidate.get(
                    "event_id",
                    ""
                )
            )
        ],
        "summary": (
            reason
            or "Deterministic ranking preserved."
        ),
        "fallback_used": True
    }

    allowed_event_ids = [
        safe_text(
            candidate.get(
                "event_id",
                ""
            )
        )
        for candidate in ranked_candidates
        if safe_text(
            candidate.get(
                "event_id",
                ""
            )
        )
    ]

    return parse_llm_response(
        data=fallback_data,
        allowed_event_ids=allowed_event_ids,
        maximum_adjustment=MAXIMUM_LLM_ADJUSTMENT
    )


# ===========================================================
# LLM Request
# ===========================================================

def request_llm_reranking(
    property_name: str,
    profile: Dict[str, Any],
    ranked_candidates: List[Dict[str, Any]],
    history: Optional[pd.DataFrame] = None,
    client: Optional[NVIDIAClient] = None
) -> LLMRerankingResponse:

    if not isinstance(ranked_candidates, list):
        ranked_candidates = []

    if not ranked_candidates:

        return build_fallback_response(
            property_name=property_name,
            ranked_candidates=[],
            reason="No candidates available for LLM reranking."
        )

    allowed_event_ids = [
        safe_text(
            candidate.get(
                "event_id",
                ""
            )
        )
        for candidate in ranked_candidates
        if safe_text(
            candidate.get(
                "event_id",
                ""
            )
        )
    ]

    if not allowed_event_ids:

        return build_fallback_response(
            property_name=property_name,
            ranked_candidates=ranked_candidates,
            reason="No valid event IDs available."
        )

    if client is None:
        client = create_client()

    if client is None:

        return build_fallback_response(
            property_name=property_name,
            ranked_candidates=ranked_candidates,
            reason="NVIDIA API key is not configured."
        )

    context = build_reranking_context(
        property_name=property_name,
        profile=profile,
        ranked_candidates=ranked_candidates,
        history=history
    )

    try:

        raw_response = client.complete_json(
            system_prompt=build_system_prompt(),
            user_payload=context
        )

        response = parse_llm_response(
            data=raw_response,
            allowed_event_ids=allowed_event_ids,
            maximum_adjustment=MAXIMUM_LLM_ADJUSTMENT
        )

        response.model = client.model

        if not response.candidates:

            return build_fallback_response(
                property_name=property_name,
                ranked_candidates=ranked_candidates,
                reason="LLM returned no valid candidates."
            )

        return response

    except LLMClientError as error:

        return build_fallback_response(
            property_name=property_name,
            ranked_candidates=ranked_candidates,
            reason=f"LLM fallback: {error}"
        )

    except Exception as error:

        return build_fallback_response(
            property_name=property_name,
            ranked_candidates=ranked_candidates,
            reason=f"Unexpected LLM fallback: {error}"
        )


# ===========================================================
# Apply LLM Adjustments
# ===========================================================

def apply_llm_response(
    ranked_candidates: List[Dict[str, Any]],
    response: LLMRerankingResponse
) -> List[Dict[str, Any]]:

    if not isinstance(ranked_candidates, list):
        return []

    result_map = {
        item.event_id: item
        for item in response.candidates
    }

    reranked = []

    for candidate in ranked_candidates:

        if not isinstance(candidate, dict):
            continue

        output = candidate.copy()

        event_id = safe_text(
            candidate.get(
                "event_id",
                ""
            )
        )

        llm_result = result_map.get(event_id)

        deterministic_score = clamp_score(
            candidate.get(
                "final_score",
                0.0
            )
        )

        if llm_result is None:

            adjustment = 0.0
            confidence = 0.0
            llm_rank = None
            reasoning = []
            risk_flags = []

        else:

            adjustment = safe_float(
                llm_result.adjustment
            )

            confidence = safe_float(
                llm_result.confidence
            )

            llm_rank = llm_result.rank

            reasoning = list(
                llm_result.reasoning
            )

            risk_flags = list(
                llm_result.risk_flags
            )

        adjusted_score = clamp_score(
            deterministic_score
            + adjustment
        )

        output["deterministic_score"] = round(
            deterministic_score,
            4
        )

        output["llm_adjustment"] = round(
            adjustment,
            4
        )

        output["llm_confidence"] = round(
            confidence,
            4
        )

        output["llm_rank"] = llm_rank

        output["llm_reasoning"] = reasoning

        output["llm_risk_flags"] = risk_flags

        output["llm_fallback_used"] = (
            response.fallback_used
        )

        output["llm_model"] = response.model
        
        output["estimated_budget_range"] = llm_result.estimated_budget_range if llm_result else "INR 3,000 - 8,000"
        output["suggested_vendor_categories"] = llm_result.suggested_vendor_categories if llm_result else "None"
        output["suggested_materials"] = llm_result.suggested_materials if llm_result else "None"
        output["ticket_recommendation"] = llm_result.ticket_recommendation if llm_result else "Free"
        output["explanation"] = llm_result.explanation if llm_result else ""

        output["final_score"] = round(
            adjusted_score,
            4
        )

        reranked.append(output)

    reranked.sort(
        key=lambda candidate: (
            candidate.get(
                "final_score",
                0.0
            ),
            -(
                candidate.get(
                    "llm_rank"
                )
                or 999999
            ),
            candidate.get(
                "deterministic_score",
                0.0
            )
        ),
        reverse=True
    )

    for index, candidate in enumerate(
        reranked,
        start=1
    ):
        candidate["rank"] = index

    return reranked


# ===========================================================
# Complete LLM Reranking
# ===========================================================

def rerank_with_llm(
    property_name: str,
    profile: Dict[str, Any],
    ranked_candidates: List[Dict[str, Any]],
    history: Optional[pd.DataFrame] = None,
    client: Optional[NVIDIAClient] = None
) -> List[Dict[str, Any]]:

    if not isinstance(ranked_candidates, list):
        return []

    if not ranked_candidates:
        return []

    response = request_llm_reranking(
        property_name=property_name,
        profile=profile,
        ranked_candidates=ranked_candidates,
        history=history,
        client=client
    )

    return apply_llm_response(
        ranked_candidates=ranked_candidates,
        response=response
    )