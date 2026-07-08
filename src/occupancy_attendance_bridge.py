"""
===========================================================
TribeIQ Occupancy Attendance Bridge
===========================================================

Frontend-safe integration layer connecting:
1. Warden resident timeline data
2. Occupancy forecasting
3. Attendance prediction
4. Monthly best-date intelligence

This module keeps the Streamlit frontend independent from
the internal intelligence implementation.
===========================================================
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Union

import pandas as pd


# ===========================================================
# Project Paths
# ===========================================================

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
INTELLIGENCE_DIR = CURRENT_DIR / "intelligence"

for path in (
    PROJECT_ROOT,
    CURRENT_DIR,
    INTELLIGENCE_DIR,
):

    path_string = str(path)

    if path_string not in sys.path:

        sys.path.insert(
            0,
            path_string,
        )


# ===========================================================
# Intelligence Imports
# ===========================================================

try:

    from intelligence.occupancy_forecaster import (
        PROPERTY_CAPACITY,
        forecast_all_properties,
        forecast_property_month,
        forecast_property_occupancy,
        load_resident_export,
        normalize_property_name,
        parse_event_date,
        rank_best_occupancy_dates,
    )

    from intelligence.attendance_predictor import (
        predict_event_attendance,
        predict_event_month,
        rank_best_event_dates,
    )

except ModuleNotFoundError:

    from occupancy_forecaster import (
        PROPERTY_CAPACITY,
        forecast_all_properties,
        forecast_property_month,
        forecast_property_occupancy,
        load_resident_export,
        normalize_property_name,
        parse_event_date,
        rank_best_occupancy_dates,
    )

    from attendance_predictor import (
        predict_event_attendance,
        predict_event_month,
        rank_best_event_dates,
    )


# ===========================================================
# Type Aliases
# ===========================================================

PathLike = Union[
    str,
    Path,
]


# ===========================================================
# Resident Timeline Cache
# ===========================================================

_RESIDENT_TIMELINE_CACHE: Optional[
    pd.DataFrame
] = None

_RESIDENT_SOURCE_CACHE: Optional[
    str
] = None


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


def empty_history() -> pd.DataFrame:

    return pd.DataFrame()


def normalize_history(
    history: Optional[
        pd.DataFrame
    ],
) -> pd.DataFrame:

    if isinstance(
        history,
        pd.DataFrame,
    ):

        return history.copy()

    return empty_history()


# ===========================================================
# Resident Timeline Access
# ===========================================================

def get_resident_timeline(
    resident_path: Optional[
        PathLike
    ] = None,
    force_reload: bool = False,
) -> pd.DataFrame:

    global _RESIDENT_TIMELINE_CACHE
    global _RESIDENT_SOURCE_CACHE

    requested_source = (
        str(
            Path(
                resident_path
            ).resolve()
        )
        if resident_path is not None
        else "__auto__"
    )

    cache_matches = (
        _RESIDENT_TIMELINE_CACHE
        is not None
        and not force_reload
        and _RESIDENT_SOURCE_CACHE
        == requested_source
    )

    if cache_matches:

        return (
            _RESIDENT_TIMELINE_CACHE
            .copy()
        )

    residents = load_resident_export(
        resident_path
    )

    _RESIDENT_TIMELINE_CACHE = (
        residents.copy()
    )

    _RESIDENT_SOURCE_CACHE = (
        requested_source
    )

    return residents


def clear_resident_timeline_cache() -> None:

    global _RESIDENT_TIMELINE_CACHE
    global _RESIDENT_SOURCE_CACHE

    _RESIDENT_TIMELINE_CACHE = None
    _RESIDENT_SOURCE_CACHE = None


# ===========================================================
# Property Capacity API
# ===========================================================

def get_property_capacities() -> Dict[
    str,
    int,
]:

    return dict(
        PROPERTY_CAPACITY
    )


def get_property_capacity(
    property_name: str,
) -> int:

    canonical_property = (
        normalize_property_name(
            property_name
        )
    )

    if not canonical_property:

        raise ValueError(
            f"Unknown property: "
            f"{property_name}"
        )

    return int(
        PROPERTY_CAPACITY[
            canonical_property
        ]
    )


# ===========================================================
# Single-Date Occupancy API
# ===========================================================

def get_property_occupancy(
    property_name: str,
    event_date: Any,
    resident_path: Optional[
        PathLike
    ] = None,
    force_reload: bool = False,
) -> Dict[str, Any]:

    residents = get_resident_timeline(
        resident_path=resident_path,
        force_reload=force_reload,
    )

    return forecast_property_occupancy(
        dataframe=residents,
        property_name=property_name,
        event_date=event_date,
    )


def get_all_property_occupancy(
    event_date: Any,
    resident_path: Optional[
        PathLike
    ] = None,
    force_reload: bool = False,
) -> Dict[
    str,
    Dict[str, Any],
]:

    residents = get_resident_timeline(
        resident_path=resident_path,
        force_reload=force_reload,
    )

    return forecast_all_properties(
        dataframe=residents,
        event_date=event_date,
    )


# ===========================================================
# Monthly Occupancy API
# ===========================================================

def get_property_month_forecast(
    property_name: str,
    year: int,
    month: int,
    start_date: Optional[
        Any
    ] = None,
    resident_path: Optional[
        PathLike
    ] = None,
    force_reload: bool = False,
) -> pd.DataFrame:

    residents = get_resident_timeline(
        resident_path=resident_path,
        force_reload=force_reload,
    )

    return forecast_property_month(
        dataframe=residents,
        property_name=property_name,
        year=int(year),
        month=int(month),
        start_date=start_date,
    )


def get_best_occupancy_dates(
    property_name: str,
    year: int,
    month: int,
    start_date: Optional[
        Any
    ] = None,
    top_n: int = 10,
    resident_path: Optional[
        PathLike
    ] = None,
    force_reload: bool = False,
) -> pd.DataFrame:

    residents = get_resident_timeline(
        resident_path=resident_path,
        force_reload=force_reload,
    )

    return rank_best_occupancy_dates(
        dataframe=residents,
        property_name=property_name,
        year=int(year),
        month=int(month),
        start_date=start_date,
        top_n=int(top_n),
    )


# ===========================================================
# Single Event Attendance API
# ===========================================================

def get_event_attendance_prediction(
    property_name: str,
    event_name: str,
    category: str,
    event_date: Any,
    history: Optional[
        pd.DataFrame
    ] = None,
    resident_path: Optional[
        PathLike
    ] = None,
    force_reload: bool = False,
) -> Dict[str, Any]:

    residents = get_resident_timeline(
        resident_path=resident_path,
        force_reload=force_reload,
    )

    event_history = normalize_history(
        history
    )

    return predict_event_attendance(
        residents=residents,
        history=event_history,
        property_name=property_name,
        event_name=event_name,
        category=category,
        event_date=event_date,
    )


# ===========================================================
# Monthly Attendance API
# ===========================================================

def get_event_month_predictions(
    property_name: str,
    event_name: str,
    category: str,
    year: int,
    month: int,
    history: Optional[
        pd.DataFrame
    ] = None,
    start_date: Optional[
        Any
    ] = None,
    resident_path: Optional[
        PathLike
    ] = None,
    force_reload: bool = False,
) -> pd.DataFrame:

    residents = get_resident_timeline(
        resident_path=resident_path,
        force_reload=force_reload,
    )

    event_history = normalize_history(
        history
    )

    return predict_event_month(
        residents=residents,
        history=event_history,
        property_name=property_name,
        event_name=event_name,
        category=category,
        year=int(year),
        month=int(month),
        start_date=start_date,
    )


# ===========================================================
# Best Event Date API
# ===========================================================

def get_best_event_dates(
    property_name: str,
    event_name: str,
    category: str,
    year: int,
    month: int,
    history: Optional[
        pd.DataFrame
    ] = None,
    start_date: Optional[
        Any
    ] = None,
    top_n: int = 10,
    resident_path: Optional[
        PathLike
    ] = None,
    force_reload: bool = False,
) -> pd.DataFrame:

    residents = get_resident_timeline(
        resident_path=resident_path,
        force_reload=force_reload,
    )

    event_history = normalize_history(
        history
    )

    return rank_best_event_dates(
        residents=residents,
        history=event_history,
        property_name=property_name,
        event_name=event_name,
        category=category,
        year=int(year),
        month=int(month),
        start_date=start_date,
        top_n=int(top_n),
    )


# ===========================================================
# Recommendation-Date Intelligence API
# ===========================================================

def build_recommendation_date_intelligence(
    property_name: str,
    event_name: str,
    category: str,
    event_date: Any,
    history: Optional[
        pd.DataFrame
    ] = None,
    resident_path: Optional[
        PathLike
    ] = None,
    force_reload: bool = False,
) -> Dict[str, Any]:

    target_date = parse_event_date(
        event_date
    )

    prediction = (
        get_event_attendance_prediction(
            property_name=property_name,
            event_name=event_name,
            category=category,
            event_date=target_date,
            history=history,
            resident_path=resident_path,
            force_reload=force_reload,
        )
    )

    return {
        "event_date":
            prediction.get(
                "event_date"
            ),
        "weekday":
            target_date.day_name(),
        "property_name":
            prediction.get(
                "property_name"
            ),
        "event_name":
            prediction.get(
                "event_name"
            ),
        "category":
            prediction.get(
                "category"
            ),
        "total_capacity":
            prediction.get(
                "total_capacity",
                0,
            ),
        "active_residents":
            prediction.get(
                "active_residents",
                0,
            ),
        "occupied_beds":
            prediction.get(
                "occupied_beds",
                0,
            ),
        "available_beds":
            prediction.get(
                "available_beds",
                0,
            ),
        "occupancy_percent":
            prediction.get(
                "occupancy_percent",
                0.0,
            ),
        "predicted_turnout_rate":
            prediction.get(
                "predicted_turnout_rate",
                0.0,
            ),
        "predicted_attendance":
            prediction.get(
                "predicted_attendance",
                0,
            ),
        "confidence_score":
            prediction.get(
                "confidence_score",
                0.0,
            ),
        "confidence_label":
            prediction.get(
                "confidence_label",
                "Low",
            ),
        "prediction_source":
            prediction.get(
                "prediction_source",
                "default",
            ),
    }