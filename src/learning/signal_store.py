"""
===========================================================
TribeIQ Learning Signal Store
===========================================================

Stores recommendation outcomes and learning signals.

Responsibilities:
1. Persist recommendation decisions
2. Persist attendance and feedback outcomes
3. Read historical learning signals
4. Handle missing or corrupted files safely
5. Preserve backward compatibility
===========================================================
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


# ===========================================================
# Permanent Import Path Fix
# ===========================================================

SRC_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SRC_DIR.parent

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


# ===========================================================
# Storage Configuration
# ===========================================================

DATA_DIR = PROJECT_ROOT / "data"
LEARNING_DIR = DATA_DIR / "learning"

SIGNAL_STORE_FILE = (
    LEARNING_DIR / "recommendation_signals.jsonl"
)


# ===========================================================
# Helpers
# ===========================================================

def ensure_store_directory() -> None:

    LEARNING_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


def utc_timestamp() -> str:

    return datetime.now(
        timezone.utc
    ).isoformat()


def safe_text(value: Any) -> str:

    if value is None:
        return ""

    return str(value).strip()


def safe_float(
    value: Any,
    default: float = 0.0
) -> float:

    try:

        numeric = float(value)

        if pd.isna(numeric):
            return default

        return numeric

    except (TypeError, ValueError):
        return default


def make_json_safe(value: Any) -> Any:

    if value is None:
        return None

    if isinstance(
        value,
        (str, int, bool)
    ):
        return value

    if isinstance(value, float):

        if pd.isna(value):
            return None

        return value

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

    if isinstance(
        value,
        (datetime, pd.Timestamp)
    ):

        return value.isoformat()

    try:

        if pd.isna(value):
            return None

    except (TypeError, ValueError):
        pass

    return str(value)


# ===========================================================
# Record Validation
# ===========================================================

def normalize_signal_record(
    record: Dict[str, Any]
) -> Dict[str, Any]:

    if not isinstance(record, dict):
        return {}

    normalized = {
        "timestamp": safe_text(
            record.get(
                "timestamp",
                utc_timestamp()
            )
        ),
        "property_name": safe_text(
            record.get(
                "property_name",
                ""
            )
        ),
        "event_id": safe_text(
            record.get(
                "event_id",
                ""
            )
        ),
        "event_name": safe_text(
            record.get(
                "event_name",
                ""
            )
        ),
        "category": safe_text(
            record.get(
                "category",
                ""
            )
        ),
        "recommendation_type": safe_text(
            record.get(
                "recommendation_type",
                ""
            )
        ),
        "rank": int(
            safe_float(
                record.get(
                    "rank",
                    0
                )
            )
        ),
        "recommended_score": safe_float(
            record.get(
                "recommended_score",
                0.0
            )
        ),
        "attendance_percent": safe_float(
            record.get(
                "attendance_percent",
                0.0
            )
        ),
        "feedback_score": safe_float(
            record.get(
                "feedback_score",
                0.0
            )
        ),
        "success_score": safe_float(
            record.get(
                "success_score",
                0.0
            )
        ),
        "selected": bool(
            record.get(
                "selected",
                False
            )
        ),
        "completed": bool(
            record.get(
                "completed",
                False
            )
        ),
        "metadata": make_json_safe(
            record.get(
                "metadata",
                {}
            )
        )
    }

    if not normalized["property_name"]:
        return {}

    if not normalized["event_id"]:
        return {}

    return normalized


# ===========================================================
# Write Signal
# ===========================================================

def append_signal(
    record: Dict[str, Any]
) -> bool:

    normalized = normalize_signal_record(
        record
    )

    if not normalized:
        return False

    ensure_store_directory()

    try:

        with SIGNAL_STORE_FILE.open(
            "a",
            encoding="utf-8"
        ) as file:

            file.write(
                json.dumps(
                    normalized,
                    ensure_ascii=False
                )
            )

            file.write("\n")

        return True

    except OSError:
        return False


# ===========================================================
# Read Signals
# ===========================================================

def load_signals() -> List[Dict[str, Any]]:

    if not SIGNAL_STORE_FILE.exists():
        return []

    records = []

    try:

        with SIGNAL_STORE_FILE.open(
            "r",
            encoding="utf-8"
        ) as file:

            for line in file:

                line = line.strip()

                if not line:
                    continue

                try:

                    record = json.loads(line)

                except json.JSONDecodeError:
                    continue

                normalized = normalize_signal_record(
                    record
                )

                if normalized:
                    records.append(normalized)

    except OSError:
        return []

    return records


def load_signals_dataframe() -> pd.DataFrame:

    records = load_signals()

    if not records:

        return pd.DataFrame()

    return pd.DataFrame(records)


# ===========================================================
# Recommendation Logging
# ===========================================================

def log_recommendation(
    property_name: str,
    candidate: Dict[str, Any],
    recommendation_type: str,
    rank: int
) -> bool:

    if not isinstance(candidate, dict):
        return False

    return append_signal({
        "timestamp":
            utc_timestamp(),
        "property_name":
            property_name,
        "event_id":
            candidate.get(
                "event_id",
                ""
            ),
        "event_name":
            candidate.get(
                "event_name",
                ""
            ),
        "category":
            candidate.get(
                "category",
                ""
            ),
        "recommendation_type":
            recommendation_type,
        "rank":
            rank,
        "recommended_score":
            candidate.get(
                "final_score",
                0.0
            ),
        "selected":
            True,
        "completed":
            False,
        "metadata": {
            "signals":
                candidate.get(
                    "signals",
                    {}
                ),
            "penalties":
                candidate.get(
                    "penalties",
                    {}
                ),
            "llm_adjustment":
                candidate.get(
                    "llm_adjustment",
                    0.0
                ),
            "exploration_bonus":
                candidate.get(
                    "exploration_bonus",
                    0.0
                )
        }
    })


# ===========================================================
# Outcome Logging
# ===========================================================

def log_outcome(
    property_name: str,
    event_id: str,
    event_name: str,
    attendance_percent: float,
    feedback_score: float,
    success_score: float,
    category: str = "",
    metadata: Optional[Dict[str, Any]] = None
) -> bool:

    return append_signal({
        "timestamp":
            utc_timestamp(),
        "property_name":
            property_name,
        "event_id":
            event_id,
        "event_name":
            event_name,
        "category":
            category,
        "recommendation_type":
            "outcome",
        "rank":
            0,
        "recommended_score":
            0.0,
        "attendance_percent":
            attendance_percent,
        "feedback_score":
            feedback_score,
        "success_score":
            success_score,
        "selected":
            True,
        "completed":
            True,
        "metadata":
            metadata or {}
    })


# ===========================================================
# Query Helpers
# ===========================================================

def get_property_signals(
    property_name: str
) -> List[Dict[str, Any]]:

    target = safe_text(
        property_name
    ).lower()

    return [
        record
        for record in load_signals()
        if safe_text(
            record.get(
                "property_name",
                ""
            )
        ).lower() == target
    ]


def get_event_signals(
    property_name: str,
    event_id: str
) -> List[Dict[str, Any]]:

    property_target = safe_text(
        property_name
    ).lower()

    event_target = safe_text(
        event_id
    ).lower()

    return [
        record
        for record in load_signals()
        if (
            safe_text(
                record.get(
                    "property_name",
                    ""
                )
            ).lower()
            == property_target
            and
            safe_text(
                record.get(
                    "event_id",
                    ""
                )
            ).lower()
            == event_target
        )
    ]