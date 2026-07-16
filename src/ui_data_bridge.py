"""
===========================================================
TribeIQ UI Data Bridge
===========================================================

Single integration layer between the Streamlit frontend and
the recommendation backend.

Responsibilities:
1. Load production data safely
2. Build and cache backend-ready data
3. Run the recommendation engine
4. Normalize backend results for the UI
5. Preserve recommendation state across pages
6. Prevent frontend code from depending on backend internals
===========================================================
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


# ===========================================================
# Project Paths
# ===========================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
DATA_DIR = PROJECT_ROOT / "data"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


# ===========================================================
# Project Imports
# ===========================================================

from main import (
    prepare_residents,
    prepare_profiles
)

from recommendation_engine import (
    RecommendationEngine
)


# ===========================================================
# Session State Keys
# ===========================================================

SESSION_RESULT_KEY = "tribeiq_recommendation_result"
SESSION_PROPERTY_KEY = "tribeiq_recommendation_property"
SESSION_ERROR_KEY = "tribeiq_recommendation_error"
SESSION_RUNNING_KEY = "tribeiq_recommendation_running"


# ===========================================================
# Helpers
# ===========================================================

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


def normalize_column_name(
    value: Any
) -> str:

    return (
        safe_text(value)
        .lower()
        .replace("_", " ")
        .replace("-", " ")
    )


def safe_dataframe(
    value: Any
) -> pd.DataFrame:

    if isinstance(value, pd.DataFrame):
        return value.copy()

    return pd.DataFrame()


# ===========================================================
# CSV Discovery
# ===========================================================

def find_all_csv_files() -> List[Path]:

    if not DATA_DIR.exists():
        return []

    return sorted(
        DATA_DIR.rglob("*.csv")
    )


def read_csv_safely(
    path: Path
) -> pd.DataFrame:

    try:
        return pd.read_csv(path)

    except Exception:
        return pd.DataFrame()


def is_event_catalogue(
    dataframe: pd.DataFrame
) -> bool:

    if dataframe.empty:
        return False

    columns = {
        normalize_column_name(column)
        for column in dataframe.columns
    }

    has_event = bool(
        columns.intersection({
            "event name",
            "event",
            "name"
        })
    )

    has_category = bool(
        columns.intersection({
            "category",
            "event category"
        })
    )

    has_outcome = bool(
        columns.intersection({
            "attendance %",
            "attendance",
            "average feedback",
            "avg feedback",
            "feedback",
            "success score"
        })
    )

    return (
        has_event
        and has_category
        and not has_outcome
    )


def is_event_history(
    dataframe: pd.DataFrame
) -> bool:

    if dataframe.empty:
        return False

    columns = {
        normalize_column_name(column)
        for column in dataframe.columns
    }

    has_event = bool(
        columns.intersection({
            "event name",
            "event",
            "name"
        })
    )

    has_property = bool(
        columns.intersection({
            "property",
            "property name"
        })
    )

    has_outcome = bool(
        columns.intersection({
            "attendance %",
            "attendance",
            "average feedback",
            "avg feedback",
            "feedback",
            "success score"
        })
    )

    return (
        has_event
        and has_property
        and has_outcome
    )


def load_event_data() -> Tuple[
    pd.DataFrame,
    pd.DataFrame
]:

    events = pd.DataFrame()
    history = pd.DataFrame()

    csv_files = find_all_csv_files()

    for path in csv_files:

        dataframe = read_csv_safely(
            path
        )

        if dataframe.empty:
            continue

        if (
            events.empty
            and is_event_catalogue(dataframe)
        ):
            events = dataframe.copy()

        if (
            history.empty
            and is_event_history(dataframe)
        ):
            history = dataframe.copy()

        if (
            not events.empty
            and not history.empty
        ):
            break

    return events, history


# ===========================================================
# Production Data Loading
# ===========================================================

def load_application_data() -> Dict[str, Any]:

    residents = prepare_residents()

    profiles = prepare_profiles(
        residents
    )

    events, history = load_event_data()

    return {
        "residents":
            safe_dataframe(residents),
        "profiles":
            profiles
            if isinstance(profiles, dict)
            else {},
        "events":
            safe_dataframe(events),
        "history":
            safe_dataframe(history)
    }


# ===========================================================
# Data Validation
# ===========================================================

def validate_application_data(
    data: Dict[str, Any]
) -> List[str]:

    errors = []

    if not isinstance(data, dict):

        return [
            "Application data is invalid."
        ]

    residents = data.get(
        "residents"
    )

    profiles = data.get(
        "profiles"
    )

    events = data.get(
        "events"
    )

    if (
        not isinstance(residents, pd.DataFrame)
        or residents.empty
    ):

        errors.append(
            "Resident data is unavailable."
        )

    if (
        not isinstance(profiles, dict)
        or not profiles
    ):

        errors.append(
            "Property profiles are unavailable."
        )

    if (
        not isinstance(events, pd.DataFrame)
        or events.empty
    ):

        errors.append(
            "Event catalogue is unavailable."
        )

    return errors


# ===========================================================
# Engine Factory
# ===========================================================

def create_recommendation_engine(
    data: Dict[str, Any],
    use_llm: bool = True,
    use_learning: bool = True
) -> RecommendationEngine:

    errors = validate_application_data(
        data
    )

    if errors:

        raise ValueError(
            " ".join(errors)
        )

    return RecommendationEngine(
        events=data["events"],
        profiles=data["profiles"],
        history=data.get(
            "history",
            pd.DataFrame()
        ),
        use_llm=use_llm,
        use_learning=use_learning
    )


# ===========================================================
# Result Normalization
# ===========================================================

def normalize_candidate(
    candidate: Any
) -> Optional[Dict[str, Any]]:

    if not isinstance(candidate, dict):
        return None

    event_id = safe_text(
        candidate.get(
            "event_id",
            ""
        )
    )

    event_name = safe_text(
        candidate.get(
            "event_name",
            ""
        )
    )

    if not event_name:
        return None

    output = dict(candidate)

    output["event_id"] = event_id

    output["event_name"] = event_name

    output["category"] = safe_text(
        candidate.get(
            "category",
            "Unknown"
        )
    ) or "Unknown"

    output["rank"] = int(
        safe_float(
            candidate.get(
                "rank",
                0
            )
        )
    )

    output["final_score"] = round(
        safe_float(
            candidate.get(
                "final_score",
                0.0
            )
        ),
        4
    )

    output["llm_adjustment"] = round(
        safe_float(
            candidate.get(
                "llm_adjustment",
                0.0
            )
        ),
        4
    )

    output["learning_adjustment"] = round(
        safe_float(
            candidate.get(
                "learning_adjustment",
                0.0
            )
        ),
        4
    )

    return output


def normalize_recommendation_result(
    result: Any,
    property_name: str
) -> Dict[str, Any]:

    if not isinstance(result, dict):

        raise ValueError(
            "Recommendation backend returned an invalid result."
        )

    major_event = normalize_candidate(
        result.get(
            "major_event"
        )
    )

    minor_events = []

    raw_minor_events = result.get(
        "minor_events",
        []
    )

    if isinstance(raw_minor_events, list):

        for candidate in raw_minor_events:

            normalized = normalize_candidate(
                candidate
            )

            if normalized is not None:
                minor_events.append(normalized)

    ranked_candidates = []

    raw_ranked_candidates = result.get(
        "ranked_candidates",
        []
    )

    if isinstance(
        raw_ranked_candidates,
        list
    ):

        for candidate in raw_ranked_candidates:

            normalized = normalize_candidate(
                candidate
            )

            if normalized is not None:
                ranked_candidates.append(
                    normalized
                )

    return {
        "property_name":
            safe_text(property_name),
        "major_event":
            major_event,
        "minor_events":
            minor_events,
        "selected_count":
            (
                (1 if major_event else 0)
                + len(minor_events)
            ),
        "candidate_count":
            len(ranked_candidates),
        "ranked_candidates":
            ranked_candidates,
        "pipeline":
            result.get(
                "pipeline",
                {}
            )
            if isinstance(
                result.get("pipeline"),
                dict
            )
            else {}
    }


# ===========================================================
# Recommendation Execution
# ===========================================================

def generate_property_recommendations(
    property_name: str,
    data: Dict[str, Any],
    use_llm: bool = True,
    use_learning: bool = True,
    save_signals: bool = True
) -> Dict[str, Any]:

    property_name = safe_text(
        property_name
    )

    if not property_name:

        raise ValueError(
            "A property must be selected."
        )

    profiles = data.get(
        "profiles",
        {}
    )

    if property_name not in profiles:

        raise KeyError(
            f"Property profile not found: {property_name}"
        )

    engine = create_recommendation_engine(
        data=data,
        use_llm=use_llm,
        use_learning=use_learning
    )

    result = engine.recommend(
        property_name=property_name,
        profile=profiles[property_name],
        save_signals=save_signals
    )

    return normalize_recommendation_result(
        result=result,
        property_name=property_name
    )


# ===========================================================
# Streamlit Session Integration
# ===========================================================

def save_result_to_session(
    session_state: Any,
    result: Dict[str, Any]
) -> None:

    session_state[
        SESSION_RESULT_KEY
    ] = result

    session_state[
        SESSION_PROPERTY_KEY
    ] = result.get(
        "property_name",
        ""
    )

    session_state[
        SESSION_ERROR_KEY
    ] = ""

    session_state[
        SESSION_RUNNING_KEY
    ] = False


def save_error_to_session(
    session_state: Any,
    error: Any
) -> None:

    session_state[
        SESSION_ERROR_KEY
    ] = safe_text(error)

    session_state[
        SESSION_RUNNING_KEY
    ] = False


def get_session_result(
    session_state: Any
) -> Optional[Dict[str, Any]]:

    result = session_state.get(
        SESSION_RESULT_KEY
    )

    if isinstance(result, dict):
        return result

    return None


def get_session_property(
    session_state: Any
) -> str:

    return safe_text(
        session_state.get(
            SESSION_PROPERTY_KEY,
            ""
        )
    )


def clear_session_result(
    session_state: Any
) -> None:

    for key in (
        SESSION_RESULT_KEY,
        SESSION_PROPERTY_KEY,
        SESSION_ERROR_KEY,
        SESSION_RUNNING_KEY
    ):

        if key in session_state:
            del session_state[key]


def delete_logged_event(
    date_val: str,
    property_val: str,
    event_val: str
) -> bool:

    history_path = DATA_DIR / "event_history.csv"
    if not history_path.exists():
        return False

    try:
        df = pd.read_csv(history_path)
        if df.empty:
            return False

        mask = (
            (df["Date"].astype(str).str.strip() == str(date_val).strip()) &
            (df["Property"].astype(str).str.strip().str.lower() == str(property_val).strip().lower()) &
            (df["Event Name"].astype(str).str.strip().str.lower() == str(event_val).strip().lower())
        )

        if not mask.any():
            return False

        df = df[~mask]
        df.to_csv(history_path, index=False)
        return True

    except Exception:
        return False


def clear_all_history() -> bool:

    history_path = DATA_DIR / "event_history.csv"
    if not history_path.exists():
        return False

    try:
        df = pd.read_csv(history_path, nrows=0)
        df.to_csv(history_path, index=False)
        return True

    except Exception:
        return False


def parse_recommendation_row(event: Dict[str, Any], rec_type: str, property_name: str) -> Dict[str, Any]:
    from datetime import date
    import pandas as pd
    
    pred_date_str = event.get("predicted_event_date") or event.get("event_date") or date.today().isoformat()
    if isinstance(pred_date_str, date):
        pred_date_str = pred_date_str.isoformat()
    
    return {
        "Property": property_name,
        "Event Name": event.get("event_name", ""),
        "Recommendation Type": rec_type,
        "Recommendation Score": float(event.get("final_score", 0.0)),
        "Predicted Event Date": pred_date_str,
        "Total Capacity": int(event.get("total_capacity", 0)),
        "Predicted Active Residents": int(event.get("active_residents", 0)),
        "Predicted Occupancy %": float(event.get("occupancy_percent", 0.0)),
        "Predicted Turnout Rate": float(event.get("predicted_turnout_rate", 0.0)),
        "Predicted Attendance": int(event.get("predicted_attendance", 0)),
        "Attendance Confidence": str(event.get("confidence_label", "None")),
        "Attendance Confidence Score": float(event.get("confidence_score", 0.0)),
        "Event ID": event.get("event_id", ""),
        "Category": event.get("category", "")
    }


def save_predictions_to_csv(result: Dict[str, Any]) -> None:
    if not isinstance(result, dict):
        return
        
    property_name = result.get("property_name", "")
    if not property_name:
        return
        
    major_event = result.get("major_event")
    minor_events = result.get("minor_events") or []
    
    rows = []
    if isinstance(major_event, dict):
        rows.append(parse_recommendation_row(major_event, "major", property_name))
        
    for minor_event in minor_events:
        if isinstance(minor_event, dict):
            rows.append(parse_recommendation_row(minor_event, "minor", property_name))
            
    if not rows:
        return
        
    import pandas as pd
    from pathlib import Path
    
    predictions_df = pd.DataFrame(rows)
    output_path = Path("data/predictions_history.csv")
    
    if output_path.exists():
        try:
            existing_df = pd.read_csv(output_path)
            combined_df = pd.concat([existing_df, predictions_df], ignore_index=True)
            combined_df.drop_duplicates(subset=["Property", "Predicted Event Date", "Event Name"], keep="last", inplace=True)
            predictions_df = combined_df
        except Exception:
            pass
            
    output_path.parent.mkdir(parents=True, exist_ok=True)
    predictions_df.to_csv(output_path, index=False)


def update_logged_event(event_id_val: str, updated_fields: Dict[str, Any]) -> bool:
    history_path = DATA_DIR / "event_history.csv"
    if not history_path.exists():
        return False
        
    try:
        df = pd.read_csv(history_path)
        if df.empty:
            return False
            
        if "Event ID" in df.columns:
            mask = df["Event ID"].astype(str).str.strip() == str(event_id_val).strip()
        else:
            return False
            
        if not mask.any():
            return False
            
        for col, val in updated_fields.items():
            if col not in df.columns:
                df[col] = None
            df.loc[mask, col] = val
            
        df.to_csv(history_path, index=False)
        return True
    except Exception:
        return False