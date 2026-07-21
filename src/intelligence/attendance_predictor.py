"""
===========================================================
TribeIQ Attendance Predictor
===========================================================

Production attendance prediction for recommended events.

Responsibilities:
1. Use event-date occupancy forecasts
2. Learn turnout behaviour from historical events
3. Apply property, event and category-level evidence
4. Use occupancy as the available resident population
5. Predict attendance count and turnout percentage
6. Calculate prediction confidence
7. Rank candidate event dates by expected attendance
===========================================================
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


# ===========================================================
# Permanent Import Path Fix
# ===========================================================

CURRENT_DIR = Path(__file__).resolve().parent
SRC_DIR = CURRENT_DIR.parent
PROJECT_ROOT = SRC_DIR.parent

for path in (
    CURRENT_DIR,
    SRC_DIR,
    PROJECT_ROOT,
):

    path_string = str(path)

    if path_string not in sys.path:

        sys.path.insert(
            0,
            path_string,
        )


# ===========================================================
# Occupancy Imports
# ===========================================================

try:

    from intelligence.occupancy_forecaster import (
        forecast_property_month,
        forecast_property_occupancy,
        normalize_property_name,
        parse_event_date,
    )

except ModuleNotFoundError:

    from occupancy_forecaster import (
        forecast_property_month,
        forecast_property_occupancy,
        normalize_property_name,
        parse_event_date,
    )


# ===========================================================
# Prediction Configuration
# ===========================================================

DEFAULT_TURNOUT_RATE = 0.20

MIN_TURNOUT_RATE = 0.02

MAX_TURNOUT_RATE = 0.95

PROPERTY_WEIGHT = 0.20

CATEGORY_WEIGHT = 0.25

EVENT_WEIGHT = 0.35

GLOBAL_WEIGHT = 0.20

MIN_HISTORY_FOR_HIGH_CONFIDENCE = 5


# ===========================================================
# Basic Helpers
# ===========================================================

def safe_text(
    value: Any,
) -> str:

    if value is None:
        return ""

    try:

        if pd.isna(value):
            return ""

    except (TypeError, ValueError):
        pass

    return str(value).strip()


def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:

    try:

        numeric = float(value)

        if pd.isna(numeric):
            return default

        return numeric

    except (TypeError, ValueError):
        return default


def normalize_text(
    value: Any,
) -> str:

    return (
        safe_text(value)
        .casefold()
        .strip()
    )


def clamp_turnout_rate(
    value: float,
) -> float:

    return max(
        MIN_TURNOUT_RATE,
        min(
            float(value),
            MAX_TURNOUT_RATE,
        ),
    )


def find_column(
    dataframe: pd.DataFrame,
    candidates: tuple,
) -> Optional[str]:

    if not isinstance(
        dataframe,
        pd.DataFrame,
    ):

        return None

    normalized_columns = {
        normalize_text(column)
        .replace("_", " ")
        .replace("-", " "):
            column
        for column
        in dataframe.columns
    }

    for candidate in candidates:

        normalized_candidate = (
            normalize_text(candidate)
            .replace("_", " ")
            .replace("-", " ")
        )

        if (
            normalized_candidate
            in normalized_columns
        ):

            return normalized_columns[
                normalized_candidate
            ]

    return None


# ===========================================================
# History Preparation
# ===========================================================

def prepare_event_history(
    history: pd.DataFrame,
) -> pd.DataFrame:

    if not isinstance(
        history,
        pd.DataFrame,
    ):

        return pd.DataFrame()

    if history.empty:
        return pd.DataFrame()

    prepared = history.copy()

    property_column = find_column(
        prepared,
        (
            "Property",
            "Property Name",
        ),
    )

    event_column = find_column(
        prepared,
        (
            "Event Name",
            "Event",
            "Name",
        ),
    )

    category_column = find_column(
        prepared,
        (
            "Category",
            "Event Category",
        ),
    )

    attendance_percent_column = find_column(
        prepared,
        (
            "Attendance %",
            "Attendance Percent",
            "Attendance Percentage",
        ),
    )

    actual_attendance_column = find_column(
        prepared,
        (
            "Actual Attendance",
            "Attendance Count",
            "Attendees",
        ),
    )

    occupancy_column = find_column(
        prepared,
        (
            "Predicted Active Residents",
            "Active Residents",
            "Occupied Beds",
            "Resident Population",
        ),
    )

    if property_column is not None:

        prepared[
            "_property"
        ] = prepared[
            property_column
        ].apply(
            normalize_property_name
        )

    else:

        prepared[
            "_property"
        ] = ""

    if event_column is not None:

        prepared[
            "_event_name"
        ] = prepared[
            event_column
        ].apply(
            normalize_text
        )

    else:

        prepared[
            "_event_name"
        ] = ""

    if category_column is not None:

        prepared[
            "_category"
        ] = prepared[
            category_column
        ].apply(
            normalize_text
        )

    else:

        prepared[
            "_category"
        ] = ""

    prepared[
        "_turnout_rate"
    ] = pd.NA

    if (
        actual_attendance_column is not None
        and occupancy_column is not None
    ):

        actual_attendance = pd.to_numeric(
            prepared[
                actual_attendance_column
            ],
            errors="coerce",
        )

        active_population = pd.to_numeric(
            prepared[
                occupancy_column
            ],
            errors="coerce",
        )

        valid_evidence = (
            (active_population > 0)
            & (actual_attendance > 0)
        )

        prepared.loc[
            valid_evidence,
            "_turnout_rate",
        ] = (
            actual_attendance[
                valid_evidence
            ]
            / active_population[
                valid_evidence
            ]
        )

    if attendance_percent_column is not None:

        attendance_percent = pd.to_numeric(
            prepared[
                attendance_percent_column
            ],
            errors="coerce",
        )

        missing_turnout = (
            prepared[
                "_turnout_rate"
            ].isna()
            & (attendance_percent > 0)
        )

        prepared.loc[
            missing_turnout,
            "_turnout_rate",
        ] = (
            attendance_percent[
                missing_turnout
            ]
            / 100.0
        )

    prepared[
        "_turnout_rate"
    ] = pd.to_numeric(
        prepared[
            "_turnout_rate"
        ],
        errors="coerce",
    )

    prepared = prepared[
        prepared[
            "_turnout_rate"
        ].notna()
        & (prepared["_turnout_rate"] > 0)
    ].copy()

    prepared[
        "_turnout_rate"
    ] = prepared[
        "_turnout_rate"
    ].clip(
        lower=MIN_TURNOUT_RATE,
        upper=MAX_TURNOUT_RATE,
    )

    return prepared


# ===========================================================
# Historical Signal Extraction
# ===========================================================

def get_average_turnout(
    dataframe: pd.DataFrame,
) -> Optional[float]:

    if dataframe.empty:
        return None

    values = pd.to_numeric(
        dataframe[
            "_turnout_rate"
        ],
        errors="coerce",
    ).dropna()

    if values.empty:
        return None

    return float(
        values.mean()
    )


def calculate_historical_turnout(
    history: pd.DataFrame,
    property_name: str,
    event_name: str,
    category: str,
) -> Dict[str, Any]:

    prepared = prepare_event_history(
        history
    )

    canonical_property = (
        normalize_property_name(
            property_name
        )
    )

    normalized_event = normalize_text(
        event_name
    )

    normalized_category = normalize_text(
        category
    )

    if prepared.empty:

        return {
            "turnout_rate":
                DEFAULT_TURNOUT_RATE,
            "history_count":
                0,
            "event_history_count":
                0,
            "category_history_count":
                0,
            "property_history_count":
                0,
            "global_history_count":
                0,
            "signal_source":
                "default",
        }

    global_history = prepared

    property_history = prepared[
        prepared[
            "_property"
        ]
        == canonical_property
    ]

    category_history = property_history[
        property_history[
            "_category"
        ]
        == normalized_category
    ]

    event_history = property_history[
        property_history[
            "_event_name"
        ]
        == normalized_event
    ]

    signals: List[
        tuple
    ] = []

    event_rate = get_average_turnout(
        event_history
    )

    if event_rate is not None:

        signals.append(
            (
                event_rate,
                EVENT_WEIGHT,
            )
        )

    category_rate = get_average_turnout(
        category_history
    )

    if category_rate is not None:

        signals.append(
            (
                category_rate,
                CATEGORY_WEIGHT,
            )
        )

    property_rate = get_average_turnout(
        property_history
    )

    if property_rate is not None:

        signals.append(
            (
                property_rate,
                PROPERTY_WEIGHT,
            )
        )

    global_rate = get_average_turnout(
        global_history
    )

    if global_rate is not None:

        signals.append(
            (
                global_rate,
                GLOBAL_WEIGHT,
            )
        )

    if not signals:

        turnout_rate = (
            DEFAULT_TURNOUT_RATE
        )

        signal_source = "default"

    else:

        total_weight = sum(
            weight
            for _, weight
            in signals
        )

        turnout_rate = sum(
            rate * weight
            for rate, weight
            in signals
        ) / total_weight

        signal_source = "historical"

    total_relevant_history = (
        len(event_history)
        + len(category_history)
        + len(property_history)
    )

    return {
        "turnout_rate":
            round(
                clamp_turnout_rate(
                    turnout_rate
                ),
                4,
            ),
        "history_count":
            int(
                total_relevant_history
            ),
        "event_history_count":
            int(
                len(event_history)
            ),
        "category_history_count":
            int(
                len(category_history)
            ),
        "property_history_count":
            int(
                len(property_history)
            ),
        "global_history_count":
            int(
                len(global_history)
            ),
        "signal_source":
            signal_source,
    }


# ===========================================================
# Confidence Calculation
# ===========================================================

def calculate_prediction_confidence(
    history_signal: Dict[
        str,
        Any,
    ],
    occupancy_forecast: Dict[
        str,
        Any,
    ],
) -> Dict[str, Any]:

    event_count = int(
        history_signal.get(
            "event_history_count",
            0,
        )
    )

    category_count = int(
        history_signal.get(
            "category_history_count",
            0,
        )
    )

    property_count = int(
        history_signal.get(
            "property_history_count",
            0,
        )
    )

    duplicate_beds = int(
        occupancy_forecast.get(
            "duplicate_bed_assignments",
            0,
        )
    )

    confidence_score = 35.0

    confidence_score += min(
        event_count * 8.0,
        32.0,
    )

    confidence_score += min(
        category_count * 3.0,
        15.0,
    )

    confidence_score += min(
        property_count * 1.0,
        10.0,
    )

    if duplicate_beds > 0:

        confidence_score -= min(
            duplicate_beds * 2.0,
            15.0,
        )

    confidence_score = max(
        0.0,
        min(
            confidence_score,
            100.0,
        ),
    )

    if confidence_score >= 75.0:

        confidence_label = "High"

    elif confidence_score >= 50.0:

        confidence_label = "Medium"

    else:

        confidence_label = "Low"

    return {
        "confidence_score":
            round(
                confidence_score,
                1,
            ),
        "confidence_label":
            confidence_label,
    }


# ===========================================================
# Single Event Attendance Prediction
# ===========================================================

def predict_event_attendance(
    residents: pd.DataFrame,
    history: pd.DataFrame,
    property_name: str,
    event_name: str,
    category: str,
    event_date: Any,
) -> Dict[str, Any]:

    occupancy = (
        forecast_property_occupancy(
            dataframe=residents,
            property_name=property_name,
            event_date=event_date,
        )
    )

    historical_signal = (
        calculate_historical_turnout(
            history=history,
            property_name=property_name,
            event_name=event_name,
            category=category,
        )
    )

    turnout_rate = safe_float(
        historical_signal.get(
            "turnout_rate",
            DEFAULT_TURNOUT_RATE,
        ),
        DEFAULT_TURNOUT_RATE,
    )

    active_residents = int(
        occupancy.get(
            "active_residents",
            0,
        )
    )

    predicted_attendance = int(
        round(
            active_residents
            * turnout_rate
        )
    )

    predicted_attendance = max(
        0,
        min(
            predicted_attendance,
            active_residents,
        ),
    )

    confidence = (
        calculate_prediction_confidence(
            history_signal=(
                historical_signal
            ),
            occupancy_forecast=(
                occupancy
            ),
        )
    )

    return {
        "property_name":
            occupancy[
                "property_name"
            ],
        "event_name":
            safe_text(
                event_name
            ),
        "category":
            safe_text(
                category
            ),
        "event_date":
            occupancy[
                "event_date"
            ],
        "total_capacity":
            occupancy[
                "total_capacity"
            ],
        "active_residents":
            active_residents,
        "occupied_beds":
            occupancy[
                "occupied_beds"
            ],
        "available_beds":
            occupancy[
                "available_beds"
            ],
        "occupancy_percent":
            occupancy[
                "occupancy_percent"
            ],
        "predicted_turnout_rate":
            round(
                turnout_rate * 100.0,
                2,
            ),
        "predicted_attendance":
            predicted_attendance,
        "confidence_score":
            confidence[
                "confidence_score"
            ],
        "confidence_label":
            confidence[
                "confidence_label"
            ],
        "history_count":
            historical_signal[
                "history_count"
            ],
        "event_history_count":
            historical_signal[
                "event_history_count"
            ],
        "category_history_count":
            historical_signal[
                "category_history_count"
            ],
        "property_history_count":
            historical_signal[
                "property_history_count"
            ],
        "prediction_source":
            historical_signal[
                "signal_source"
            ],
        "duplicate_bed_assignments":
            occupancy[
                "duplicate_bed_assignments"
            ],
    }


# ===========================================================
# Monthly Attendance Prediction
# ===========================================================

def predict_event_month(
    residents: pd.DataFrame,
    history: pd.DataFrame,
    property_name: str,
    event_name: str,
    category: str,
    year: int,
    month: int,
    start_date: Optional[Any] = None,
) -> pd.DataFrame:

    occupancy_month = (
        forecast_property_month(
            dataframe=residents,
            property_name=property_name,
            year=year,
            month=month,
            start_date=start_date,
        )
    )

    if occupancy_month.empty:

        return pd.DataFrame()

    historical_signal = (
        calculate_historical_turnout(
            history=history,
            property_name=property_name,
            event_name=event_name,
            category=category,
        )
    )

    turnout_rate = safe_float(
        historical_signal.get(
            "turnout_rate",
            DEFAULT_TURNOUT_RATE,
        ),
        DEFAULT_TURNOUT_RATE,
    )

    predictions = []

    for _, occupancy in (
        occupancy_month.iterrows()
    ):

        active_residents = int(
            occupancy[
                "active_residents"
            ]
        )

        predicted_attendance = int(
            round(
                active_residents
                * turnout_rate
            )
        )

        predicted_attendance = max(
            0,
            min(
                predicted_attendance,
                active_residents,
            ),
        )

        confidence = (
            calculate_prediction_confidence(
                history_signal=(
                    historical_signal
                ),
                occupancy_forecast=(
                    occupancy.to_dict()
                ),
            )
        )

        predictions.append({
            "property_name":
                occupancy[
                    "property_name"
                ],
            "event_name":
                safe_text(
                    event_name
                ),
            "category":
                safe_text(
                    category
                ),
            "event_date":
                occupancy[
                    "event_date"
                ],
            "weekday":
                occupancy[
                    "weekday"
                ],
            "day_of_month":
                int(
                    occupancy[
                        "day_of_month"
                    ]
                ),
            "total_capacity":
                int(
                    occupancy[
                        "total_capacity"
                    ]
                ),
            "active_residents":
                active_residents,
            "occupancy_percent":
                safe_float(
                    occupancy[
                        "occupancy_percent"
                    ]
                ),
            "predicted_turnout_rate":
                round(
                    turnout_rate * 100.0,
                    2,
                ),
            "predicted_attendance":
                predicted_attendance,
            "confidence_score":
                confidence[
                    "confidence_score"
                ],
            "confidence_label":
                confidence[
                    "confidence_label"
                ],
        })

    return pd.DataFrame(
        predictions
    )


# ===========================================================
# Best Event Dates
# ===========================================================

def rank_best_event_dates(
    residents: pd.DataFrame,
    history: pd.DataFrame,
    property_name: str,
    event_name: str,
    category: str,
    year: int,
    month: int,
    start_date: Optional[Any] = None,
    top_n: int = 10,
) -> pd.DataFrame:

    predictions = predict_event_month(
        residents=residents,
        history=history,
        property_name=property_name,
        event_name=event_name,
        category=category,
        year=year,
        month=month,
        start_date=start_date,
    )

    if predictions.empty:

        return predictions

    ranked = (
        predictions
        .sort_values(
            by=[
                "predicted_attendance",
                "occupancy_percent",
                "confidence_score",
                "event_date",
            ],
            ascending=[
                False,
                False,
                False,
                True,
            ],
        )
        .head(
            max(
                int(top_n),
                1,
            )
        )
        .reset_index(
            drop=True
        )
    )

    ranked[
        "date_rank"
    ] = range(
        1,
        len(ranked) + 1,
    )

    return ranked