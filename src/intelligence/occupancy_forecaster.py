"""
===========================================================
TribeIQ Occupancy Forecaster
===========================================================

Central date-aware occupancy intelligence for TribeIQ.

Responsibilities:
1. Load the current Warden resident export
2. Normalize property, room, bed and date fields
3. Exclude invalid and test property records
4. Calculate current occupancy using today's date
5. Forecast active residents for any future event date
6. Prevent duplicate active bed assignments
7. Use verified physical bed capacities
8. Calculate property occupancy percentages
9. Forecast occupancy across a month
10. Rank occupancy dates for downstream scheduling

Core occupancy rule:

    Move In Date <= target date < Move Out Date

The Move Out Date is treated as the first date on which
the resident is no longer occupying the property.
===========================================================
"""

from __future__ import annotations

import calendar
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd


# ===========================================================
# Project Paths
# ===========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"


# ===========================================================
# Verified Physical Capacity
# ===========================================================

PROPERTY_CAPACITY = {
    "Tribe Vara": 192,
    "Tribe Moro": 296,
    "Tribe Wamba": 210,
}


PROPERTY_ALIASES = {
    "tribe vara": "Tribe Vara",
    "vara": "Tribe Vara",
    "tribe vara ": "Tribe Vara",

    "tribe moro": "Tribe Moro",
    "moro": "Tribe Moro",
    "tribe moro ": "Tribe Moro",

    "tribe wamba": "Tribe Wamba",
    "wamba": "Tribe Wamba",
    "tribe wamba ": "Tribe Wamba",
}


REQUIRED_COLUMNS = (
    "Property",
    "Room",
    "Beds",
    "Move In Date",
    "Move Out Date",
)


OPTIONAL_COLUMNS = (
    "Room Type",
    "Bed Count",
    "Term End Date",
)


# ===========================================================
# Type Aliases
# ===========================================================

DateLike = Union[
    str,
    date,
    datetime,
    pd.Timestamp,
]


# ===========================================================
# Basic Helpers
# ===========================================================

def get_ist_today() -> pd.Timestamp:
    """
    Get current date normalized in Indian Standard Time (UTC+5:30)
    to match the properties' local check-in/check-out boundaries.
    """
    from datetime import datetime, timezone, timedelta
    ist = timezone(timedelta(hours=5, minutes=30))
    today_ist = datetime.now(ist).date()
    return pd.Timestamp(today_ist).normalize()


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


def normalize_property_name(
    value: Any,
) -> str:

    raw_name = safe_text(
        value
    )

    if not raw_name:
        return ""

    normalized_key = (
        raw_name
        .casefold()
        .strip()
    )

    return PROPERTY_ALIASES.get(
        normalized_key,
        "",
    )


def normalize_room_name(
    value: Any,
) -> str:

    return (
        safe_text(value)
        .casefold()
    )


def normalize_bed_name(
    value: Any,
) -> str:

    return (
        safe_text(value)
        .casefold()
    )


def parse_event_date(
    value: DateLike,
) -> pd.Timestamp:

    parsed = pd.to_datetime(
        value,
        errors="coerce",
        dayfirst=False,
    )

    if pd.isna(parsed):

        raise ValueError(
            f"Invalid event date: {value}"
        )

    return pd.Timestamp(
        parsed
    ).normalize()


def safe_percentage(
    numerator: float,
    denominator: float,
) -> float:

    if denominator <= 0:
        return 0.0

    return round(
        (
            float(numerator)
            / float(denominator)
        )
        * 100.0,
        2,
    )


# ===========================================================
# Resident File Discovery
# ===========================================================

def is_resident_export(
    dataframe: pd.DataFrame,
) -> bool:

    if not isinstance(
        dataframe,
        pd.DataFrame,
    ):
        return False

    if dataframe.empty:
        return False

    columns = {
        safe_text(column)
        for column
        in dataframe.columns
    }

    return all(
        column in columns
        for column
        in REQUIRED_COLUMNS
    )


def find_resident_file() -> Optional[Path]:

    if not DATA_DIR.exists():
        return None

    preferred_names = (
        "Residents.csv",
        "residents.csv",
        "Resident.csv",
        "resident.csv",
        "warden_residents.csv",
        "warden_resident_export.csv",
    )

    csv_files = sorted(
        DATA_DIR.rglob("*.csv")
    )

    for preferred_name in preferred_names:

        for path in csv_files:

            if (
                path.name.casefold()
                != preferred_name.casefold()
            ):
                continue

            try:

                dataframe = pd.read_csv(
                    path,
                    low_memory=False,
                )

            except Exception:
                continue

            if is_resident_export(
                dataframe
            ):
                return path

    for path in csv_files:

        try:

            dataframe = pd.read_csv(
                path,
                low_memory=False,
            )

        except Exception:
            continue

        if is_resident_export(
            dataframe
        ):
            return path

    return None


# ===========================================================
# Resident Data Loading
# ===========================================================

def load_resident_export(
    path: Optional[
        Union[str, Path]
    ] = None,
) -> pd.DataFrame:

    if path is None:

        resident_path = (
            find_resident_file()
        )

        if resident_path is None:

            raise FileNotFoundError(
                "No valid Warden resident export "
                "was found inside the data folder."
            )

    else:

        resident_path = Path(
            path
        )

    if not resident_path.exists():

        raise FileNotFoundError(
            f"Resident export not found: "
            f"{resident_path}"
        )

    dataframe = pd.read_csv(
        resident_path,
        low_memory=False,
    )

    missing_columns = [
        column
        for column
        in REQUIRED_COLUMNS
        if column not in dataframe.columns
    ]

    if missing_columns:

        raise ValueError(
            "Resident export is missing required "
            "columns: "
            + ", ".join(
                missing_columns
            )
        )

    return prepare_resident_timeline(
        dataframe
    )


# ===========================================================
# Timeline Preparation
# ===========================================================

def prepare_resident_timeline(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:

    prepared = dataframe.copy()

    prepared[
        "_source_row"
    ] = range(
        len(prepared)
    )

    prepared[
        "_property"
    ] = prepared[
        "Property"
    ].apply(
        normalize_property_name
    )

    prepared = prepared[
        prepared[
            "_property"
        ].isin(
            PROPERTY_CAPACITY.keys()
        )
    ].copy()

    prepared[
        "_room"
    ] = prepared[
        "Room"
    ].apply(
        normalize_room_name
    )

    prepared[
        "_bed"
    ] = prepared[
        "Beds"
    ].apply(
        normalize_bed_name
    )

    prepared[
        "_move_in"
    ] = pd.to_datetime(
        prepared[
            "Move In Date"
        ],
        errors="coerce",
    ).dt.normalize()

    prepared[
        "_move_out"
    ] = pd.to_datetime(
        prepared[
            "Move Out Date"
        ],
        errors="coerce",
    ).dt.normalize()

    if (
        "Term End Date"
        in prepared.columns
    ):

        prepared[
            "_term_end"
        ] = pd.to_datetime(
            prepared[
                "Term End Date"
            ],
            errors="coerce",
        ).dt.normalize()

    else:

        prepared[
            "_term_end"
        ] = pd.NaT

    # -------------------------------------------------------
    # Effective Move-Out Date
    # -------------------------------------------------------
    #
    # Prefer Move Out Date.
    #
    # If Move Out Date is missing, use Term End Date.
    #
    # The resulting date is EXCLUSIVE:
    #
    #     target_date < effective_move_out
    #
    # -------------------------------------------------------

    prepared[
        "_effective_move_out"
    ] = prepared[
        "_move_out"
    ].copy()

    missing_move_out = (
        prepared[
            "_effective_move_out"
        ].isna()
    )

    prepared.loc[
        missing_move_out,
        "_effective_move_out",
    ] = prepared.loc[
        missing_move_out,
        "_term_end",
    ]

    # -------------------------------------------------------
    # Physical Bed Identity
    # -------------------------------------------------------

    prepared[
        "_physical_bed_key"
    ] = (
        prepared[
            "_property"
        ].astype(str)
        + "||"
        + prepared[
            "_room"
        ].astype(str)
        + "||"
        + prepared[
            "_bed"
        ].astype(str)
    )

    prepared[
        "_has_physical_bed"
    ] = (
        prepared[
            "_room"
        ].ne("")
        & prepared[
            "_bed"
        ].ne("")
    )

    # -------------------------------------------------------
    # A resident cannot be placed on the timeline without
    # a valid move-in date.
    # -------------------------------------------------------

    prepared = prepared[
        prepared[
            "_move_in"
        ].notna()
    ].copy()

    prepared = prepared.sort_values(
        by=[
            "_property",
            "_move_in",
            "_source_row",
        ],
        ascending=[
            True,
            True,
            True,
        ],
    ).reset_index(
        drop=True
    )

    return prepared


# ===========================================================
# Active Resident Logic
# ===========================================================

def get_active_residents(
    dataframe: pd.DataFrame,
    property_name: str,
    event_date: DateLike,
) -> pd.DataFrame:

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

    target_date = parse_event_date(
        event_date
    )

    property_rows = dataframe[
        dataframe[
            "_property"
        ]
        == canonical_property
    ].copy()

    # -------------------------------------------------------
    # Frozen TribeIQ Occupancy Rule
    # -------------------------------------------------------
    #
    # A resident is active when:
    #
    # Move In Date <= target date < Move Out Date
    #
    # Examples:
    #
    # Check date: 4 July
    # Move in:    1 July
    # Move out:   3 July
    # Result:     NOT ACTIVE
    #
    # Check date: 4 July
    # Move in:    1 July
    # Move out:   5 July
    # Result:     ACTIVE
    #
    # Check date: 5 July
    # Move in:    1 July
    # Move out:   5 July
    # Result:     NOT ACTIVE
    #
    # -------------------------------------------------------

    active_mask = (
        property_rows[
            "_move_in"
        ].le(
            target_date
        )
        & (
            property_rows[
                "_effective_move_out"
            ].isna()
            | property_rows[
                "_effective_move_out"
            ].gt(
                target_date
            )
        )
    )

    active = property_rows[
        active_mask
    ].copy()

    return active


# ===========================================================
# Duplicate Resolution
# ===========================================================

def resolve_active_bed_assignments(
    active_residents: pd.DataFrame,
) -> Tuple[
    pd.DataFrame,
    pd.DataFrame,
]:

    if active_residents.empty:

        return (
            active_residents.copy(),
            pd.DataFrame(),
        )

    with_bed = active_residents[
        active_residents[
            "_has_physical_bed"
        ]
    ].copy()

    without_bed = active_residents[
        ~active_residents[
            "_has_physical_bed"
        ]
    ].copy()

    duplicate_assignments = (
        with_bed[
            with_bed.duplicated(
                subset=[
                    "_physical_bed_key"
                ],
                keep=False,
            )
        ]
        .sort_values(
            by=[
                "_physical_bed_key",
                "_move_in",
                "_source_row",
            ]
        )
        .copy()
    )

    # -------------------------------------------------------
    # If multiple active records claim the same physical bed,
    # keep the latest assignment.
    # -------------------------------------------------------

    with_bed = (
        with_bed
        .sort_values(
            by=[
                "_physical_bed_key",
                "_move_in",
                "_source_row",
            ],
            ascending=[
                True,
                False,
                False,
            ],
        )
        .drop_duplicates(
            subset=[
                "_physical_bed_key"
            ],
            keep="first",
        )
    )

    resolved = pd.concat(
        [
            with_bed,
            without_bed,
        ],
        ignore_index=True,
    )

    return (
        resolved,
        duplicate_assignments,
    )


# ===========================================================
# Single-Date Occupancy Forecast
# ===========================================================

def forecast_property_occupancy(
    dataframe: pd.DataFrame,
    property_name: str,
    event_date: DateLike,
) -> Dict[str, Any]:

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

    target_date = parse_event_date(
        event_date
    )

    capacity = PROPERTY_CAPACITY[
        canonical_property
    ]

    active_residents = (
        get_active_residents(
            dataframe=dataframe,
            property_name=(
                canonical_property
            ),
            event_date=target_date,
        )
    )

    resolved_residents, duplicates = (
        resolve_active_bed_assignments(
            active_residents
        )
    )

    occupied_physical_beds = int(
        resolved_residents[
            resolved_residents[
                "_has_physical_bed"
            ]
        ][
            "_physical_bed_key"
        ]
        .nunique()
    )

    active_without_bed = int(
        (
            ~resolved_residents[
                "_has_physical_bed"
            ]
        ).sum()
    )

    active_resident_count = int(
        len(
            resolved_residents
        )
    )

    occupied_beds = min(
        active_resident_count,
        capacity,
    )

    occupancy_percent = safe_percentage(
        occupied_beds,
        capacity,
    )

    available_beds = max(
        capacity - occupied_beds,
        0,
    )

    duplicate_bed_count = int(
        duplicates[
            "_physical_bed_key"
        ].nunique()
        if not duplicates.empty
        else 0
    )

    return {
        "property_name":
            canonical_property,

        "event_date":
            target_date.date().isoformat(),

        "total_capacity":
            int(capacity),

        "active_residents":
            active_resident_count,

        "occupied_beds":
            int(occupied_beds),

        "occupied_physical_beds":
            occupied_physical_beds,

        "active_without_bed":
            active_without_bed,

        "available_beds":
            int(available_beds),

        "occupancy_percent":
            occupancy_percent,

        "duplicate_bed_assignments":
            duplicate_bed_count,

        "forecast_source":
            "Warden move-in/move-out timeline",
    }


# ===========================================================
# All-Property Occupancy Forecast
# ===========================================================

def forecast_all_properties(
    dataframe: pd.DataFrame,
    event_date: DateLike,
) -> Dict[
    str,
    Dict[str, Any],
]:

    forecasts: Dict[
        str,
        Dict[str, Any],
    ] = {}

    for property_name in (
        PROPERTY_CAPACITY
    ):

        forecasts[
            property_name
        ] = (
            forecast_property_occupancy(
                dataframe=dataframe,
                property_name=(
                    property_name
                ),
                event_date=event_date,
            )
        )

    return forecasts


# ===========================================================
# Current Occupancy API
# ===========================================================

def get_current_occupancy(
    property_name: str,
    resident_path: Optional[
        Union[str, Path]
    ] = None,
    reference_date: Optional[
        DateLike
    ] = None,
) -> Dict[str, Any]:

    """
    Return the current occupancy for one property.

    By default, the calculation uses today's actual date.

    reference_date exists primarily for testing and historical
    validation.
    """

    residents = load_resident_export(
        resident_path
    )

    if reference_date is None:

        target_date = get_ist_today()

    else:

        target_date = parse_event_date(
            reference_date
        )

    forecast = (
        forecast_property_occupancy(
            dataframe=residents,
            property_name=property_name,
            event_date=target_date,
        )
    )

    forecast[
        "occupancy_type"
    ] = "current"

    forecast[
        "as_of_date"
    ] = (
        target_date
        .date()
        .isoformat()
    )

    return forecast


def get_current_occupancy_all_properties(
    resident_path: Optional[
        Union[str, Path]
    ] = None,
    reference_date: Optional[
        DateLike
    ] = None,
) -> Dict[
    str,
    Dict[str, Any],
]:

    """
    Return current occupancy for every verified property.

    By default, the calculation uses today's actual date.
    """

    residents = load_resident_export(
        resident_path
    )

    if reference_date is None:

        target_date = get_ist_today()

    else:

        target_date = parse_event_date(
            reference_date
        )

    forecasts = forecast_all_properties(
        dataframe=residents,
        event_date=target_date,
    )

    for forecast in forecasts.values():

        forecast[
            "occupancy_type"
        ] = "current"

        forecast[
            "as_of_date"
        ] = (
            target_date
            .date()
            .isoformat()
        )

    return forecasts


# ===========================================================
# Monthly Forecast
# ===========================================================

def forecast_property_month(
    dataframe: pd.DataFrame,
    property_name: str,
    year: int,
    month: int,
    start_date: Optional[
        DateLike
    ] = None,
) -> pd.DataFrame:

    if month < 1 or month > 12:

        raise ValueError(
            "Month must be between 1 and 12."
        )

    _, days_in_month = (
        calendar.monthrange(
            year,
            month,
        )
    )

    first_day = pd.Timestamp(
        year=year,
        month=month,
        day=1,
    )

    last_day = pd.Timestamp(
        year=year,
        month=month,
        day=days_in_month,
    )

    if start_date is not None:

        requested_start = (
            parse_event_date(
                start_date
            )
        )

        first_day = max(
            first_day,
            requested_start,
        )

    if first_day > last_day:
        return pd.DataFrame()

    forecasts: List[
        Dict[str, Any]
    ] = []

    current_date = first_day

    while current_date <= last_day:

        forecast = (
            forecast_property_occupancy(
                dataframe=dataframe,
                property_name=(
                    property_name
                ),
                event_date=current_date,
            )
        )

        forecast[
            "weekday"
        ] = current_date.day_name()

        forecast[
            "day_of_month"
        ] = current_date.day

        forecast[
            "is_weekend"
        ] = (
            current_date.weekday()
            >= 5
        )

        forecasts.append(
            forecast
        )

        current_date += pd.Timedelta(
            days=1
        )

    return pd.DataFrame(
        forecasts
    )


# ===========================================================
# Best Occupancy Dates
# ===========================================================

def rank_best_occupancy_dates(
    dataframe: pd.DataFrame,
    property_name: str,
    year: int,
    month: int,
    start_date: Optional[
        DateLike
    ] = None,
    top_n: int = 10,
) -> pd.DataFrame:

    monthly_forecast = (
        forecast_property_month(
            dataframe=dataframe,
            property_name=(
                property_name
            ),
            year=year,
            month=month,
            start_date=start_date,
        )
    )

    if monthly_forecast.empty:
        return monthly_forecast

    ranked = (
        monthly_forecast
        .sort_values(
            by=[
                "occupancy_percent",
                "active_residents",
                "event_date",
            ],
            ascending=[
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
        "occupancy_rank"
    ] = range(
        1,
        len(ranked) + 1,
    )

    return ranked


# ===========================================================
# Future Event-Date Occupancy API
# ===========================================================

def get_occupancy_forecast(
    property_name: str,
    event_date: DateLike,
    resident_path: Optional[
        Union[str, Path]
    ] = None,
) -> Dict[str, Any]:

    """
    Calculate occupancy for a specific future or historical date.

    This is the API used by event scheduling and attendance
    prediction.
    """

    residents = load_resident_export(
        resident_path
    )

    forecast = (
        forecast_property_occupancy(
            dataframe=residents,
            property_name=property_name,
            event_date=event_date,
        )
    )

    forecast[
        "occupancy_type"
    ] = "event_date"

    return forecast


# ===========================================================
# Best Dates This Month API
# ===========================================================

def get_best_dates_this_month(
    property_name: str,
    resident_path: Optional[
        Union[str, Path]
    ] = None,
    reference_date: Optional[
        DateLike
    ] = None,
    top_n: int = 10,
) -> pd.DataFrame:

    residents = load_resident_export(
        resident_path
    )

    if reference_date is None:

        reference = get_ist_today()

    else:

        reference = parse_event_date(
            reference_date
        )

    return rank_best_occupancy_dates(
        dataframe=residents,
        property_name=property_name,
        year=reference.year,
        month=reference.month,
        start_date=reference,
        top_n=top_n,
    )


# ===========================================================
# Module Diagnostic
# ===========================================================

if __name__ == "__main__":

    print(
        "Testing TribeIQ occupancy engine..."
    )

    residents = load_resident_export()

    today = get_ist_today()

    print(
        f"\nOccupancy date: "
        f"{today.date().isoformat()}"
    )

    forecasts = (
        get_current_occupancy_all_properties(
            reference_date=today
        )
    )

    for property_name, forecast in (
        forecasts.items()
    ):

        print(
            "\n"
            f"{property_name}\n"
            f"  Active residents: "
            f"{forecast['active_residents']}\n"
            f"  Capacity: "
            f"{forecast['total_capacity']}\n"
            f"  Occupancy: "
            f"{forecast['occupancy_percent']}%\n"
            f"  Available beds: "
            f"{forecast['available_beds']}"
        )

    print(
        "\nOccupancy engine test completed."
    )