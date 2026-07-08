"""
===========================================================
TribeIQ Recommendation Configuration
===========================================================

Central configuration for the hybrid recommendation system.

All ranking weights, penalties, thresholds and system
behaviour are defined here.
===========================================================
"""

# ===========================================================
# Candidate Generation
# ===========================================================

CANDIDATE_POOL_SIZE = 20

MINIMUM_CANDIDATES = 3


# ===========================================================
# Ranking Signal Weights
# ===========================================================

SIGNAL_WEIGHTS = {

    "resident_affinity": 0.25,

    "property_event_affinity": 0.15,

    "historical_performance": 0.15,

    "similar_community": 0.10,

    "interest_match": 0.10,

    "predicted_success": 0.10,

    "novelty": 0.05,

    "budget_efficiency": 0.05,

    "llm_adjustment": 0.05

}


# ===========================================================
# Ranking Penalties
# ===========================================================

PENALTY_WEIGHTS = {

    "recent_event": 0.15,

    "repeat_fatigue": 0.20,

    "category_saturation": 0.10,

    "budget_risk": 0.10,

    "low_confidence": 0.05

}


# ===========================================================
# Cold Start Configuration
# ===========================================================

COLD_START_HISTORY_THRESHOLD = 10

COLD_START_WEIGHTS = {

    "content": 0.40,

    "resident_profile": 0.30,

    "rule_engine": 0.20,

    "historical": 0.05,

    "collaborative": 0.05

}


# ===========================================================
# Mature System Configuration
# ===========================================================

MATURE_SYSTEM_WEIGHTS = {

    "content": 0.20,

    "resident_profile": 0.20,

    "rule_engine": 0.15,

    "historical": 0.25,

    "collaborative": 0.20

}


# ===========================================================
# Exploration vs Exploitation
# ===========================================================

EXPLORATION_RATE = 0.15

EXPLORATION_BONUS = 5.0

MINIMUM_EXPLORATION_CONFIDENCE = 0.60


# ===========================================================
# Recency and Fatigue
# ===========================================================

RECENT_EVENT_WINDOW_DAYS = 90

REPEAT_FATIGUE_WINDOW_DAYS = 180

CATEGORY_SATURATION_WINDOW_DAYS = 90

MAX_CATEGORY_EVENTS_IN_WINDOW = 2


# ===========================================================
# LLM Reranking
# ===========================================================

LLM_ENABLED = True

LLM_MAX_ADJUSTMENT = 5.0

LLM_MIN_CONFIDENCE = 0.60

LLM_CANDIDATE_LIMIT = 20


# ===========================================================
# Final Selection
# ===========================================================

MAJOR_EVENT_COUNT = 1

MINOR_EVENT_COUNT = 2

MINIMUM_FINAL_SCORE = 0.0

REQUIRE_CATEGORY_DIVERSITY = True

REQUIRE_EVENT_UNIQUENESS = True


# ===========================================================
# Feedback Learning
# ===========================================================

MINIMUM_HISTORY_FOR_COLLABORATIVE = 10

MINIMUM_HISTORY_FOR_PREDICTION = 25

MINIMUM_HISTORY_FOR_FULL_LEARNING = 50


# ===========================================================
# Evaluation
# ===========================================================

EVALUATION_K = 3

EVALUATION_METRICS = [

    "precision_at_3",

    "hit_rate_at_3",

    "ndcg_at_3",

    "attendance_lift",

    "feedback_lift",

    "success_score_lift",

    "budget_efficiency",

    "diversity",

    "novelty",

    "coverage",

    "repeat_rate"

]


# ===========================================================
# Validation
# ===========================================================

def validate_config():

    signal_total = sum(SIGNAL_WEIGHTS.values())

    if abs(signal_total - 1.0) > 0.0001:

        raise ValueError(

            "SIGNAL_WEIGHTS must sum to 1.0"

        )

    if not 0.0 <= EXPLORATION_RATE <= 1.0:

        raise ValueError(

            "EXPLORATION_RATE must be between 0 and 1"

        )

    if LLM_MAX_ADJUSTMENT < 0:

        raise ValueError(

            "LLM_MAX_ADJUSTMENT cannot be negative"

        )


validate_config()