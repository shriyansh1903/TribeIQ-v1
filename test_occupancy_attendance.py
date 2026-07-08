import sys
from datetime import date
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
INTELLIGENCE_DIR = SRC_DIR / "intelligence"
RESIDENT_FILE = PROJECT_ROOT / "data" / "Residents.csv"

for path in (
    PROJECT_ROOT,
    SRC_DIR,
    INTELLIGENCE_DIR,
):

    path_string = str(path)

    if path_string not in sys.path:

        sys.path.insert(
            0,
            path_string,
        )


from occupancy_forecaster import (
    PROPERTY_CAPACITY,
    forecast_all_properties,
    forecast_property_month,
    forecast_property_occupancy,
    load_resident_export,
)

from attendance_predictor import (
    predict_event_attendance,
    rank_best_event_dates,
)


def run_test():

    print(
        "Testing TribeIQ occupancy and "
        "attendance intelligence...\n"
    )

    assert RESIDENT_FILE.exists(), (
        "Residents.csv was not found at: "
        f"{RESIDENT_FILE}"
    )

    residents = load_resident_export(
        RESIDENT_FILE
    )

    assert isinstance(
        residents,
        pd.DataFrame,
    )

    assert not residents.empty

    print(
        f"Valid resident timeline rows: "
        f"{len(residents)}"
    )

    expected_capacities = {
        "Tribe Vara": 192,
        "Tribe Moro": 296,
        "Tribe Wamba": 210,
    }

    assert (
        PROPERTY_CAPACITY
        == expected_capacities
    )

    print(
        "Verified total physical capacity: "
        f"{sum(PROPERTY_CAPACITY.values())} beds"
    )

    reference_date = pd.Timestamp(
        date.today()
    ).normalize()

    all_forecasts = (
        forecast_all_properties(
            dataframe=residents,
            event_date=reference_date,
        )
    )

    assert isinstance(
        all_forecasts,
        dict,
    )

    assert set(
        all_forecasts.keys()
    ) == set(
        expected_capacities.keys()
    )

    for (
        property_name,
        capacity,
    ) in expected_capacities.items():

        forecast = (
            all_forecasts[
                property_name
            ]
        )

        assert (
            forecast[
                "property_name"
            ]
            == property_name
        )

        assert (
            forecast[
                "total_capacity"
            ]
            == capacity
        )

        assert (
            forecast[
                "active_residents"
            ]
            >= 0
        )

        assert (
            forecast[
                "occupied_beds"
            ]
            >= 0
        )

        assert (
            forecast[
                "occupied_beds"
            ]
            <= capacity
        )

        assert (
            forecast[
                "available_beds"
            ]
            >= 0
        )

        assert (
            0.0
            <= forecast[
                "occupancy_percent"
            ]
            <= 100.0
        )

        print(
            f"{property_name}: "
            f"{forecast['occupied_beds']}/"
            f"{capacity} occupied "
            f"({forecast['occupancy_percent']:.2f}%)"
        )

    test_property = "Tribe Vara"

    single_forecast = (
        forecast_property_occupancy(
            dataframe=residents,
            property_name=test_property,
            event_date=reference_date,
        )
    )

    assert (
        single_forecast[
            "total_capacity"
        ]
        == 192
    )

    monthly_forecast = (
        forecast_property_month(
            dataframe=residents,
            property_name=test_property,
            year=reference_date.year,
            month=reference_date.month,
            start_date=reference_date,
        )
    )

    assert isinstance(
        monthly_forecast,
        pd.DataFrame,
    )

    assert not monthly_forecast.empty

    assert monthly_forecast[
        "event_date"
    ].is_unique

    assert all(
        monthly_forecast[
            "occupancy_percent"
        ].between(
            0.0,
            100.0,
        )
    )

    print(
        f"\nMonthly occupancy dates tested: "
        f"{len(monthly_forecast)}"
    )

    history = pd.DataFrame(
        [
            {
                "Property":
                    "Tribe Vara",
                "Event Name":
                    "Movie Night",
                "Category":
                    "Entertainment",
                "Actual Attendance":
                    30,
                "Predicted Active Residents":
                    150,
            },
            {
                "Property":
                    "Tribe Vara",
                "Event Name":
                    "Movie Night",
                "Category":
                    "Entertainment",
                "Actual Attendance":
                    36,
                "Predicted Active Residents":
                    160,
            },
            {
                "Property":
                    "Tribe Vara",
                "Event Name":
                    "Game Night",
                "Category":
                    "Entertainment",
                "Actual Attendance":
                    25,
                "Predicted Active Residents":
                    150,
            },
        ]
    )

    attendance_prediction = (
        predict_event_attendance(
            residents=residents,
            history=history,
            property_name=test_property,
            event_name="Movie Night",
            category="Entertainment",
            event_date=reference_date,
        )
    )

    assert isinstance(
        attendance_prediction,
        dict,
    )

    assert (
        attendance_prediction[
            "property_name"
        ]
        == test_property
    )

    assert (
        attendance_prediction[
            "predicted_attendance"
        ]
        >= 0
    )

    assert (
        attendance_prediction[
            "predicted_attendance"
        ]
        <= attendance_prediction[
            "active_residents"
        ]
    )

    assert (
        0.0
        <= attendance_prediction[
            "occupancy_percent"
        ]
        <= 100.0
    )

    assert (
        0.0
        <= attendance_prediction[
            "predicted_turnout_rate"
        ]
        <= 100.0
    )

    print(
        "\nAttendance prediction:"
    )

    print(
        f"Event: "
        f"{attendance_prediction['event_name']}"
    )

    print(
        f"Active residents: "
        f"{attendance_prediction['active_residents']}"
    )

    print(
        f"Occupancy: "
        f"{attendance_prediction['occupancy_percent']:.2f}%"
    )

    print(
        f"Predicted turnout rate: "
        f"{attendance_prediction['predicted_turnout_rate']:.2f}%"
    )

    print(
        f"Predicted attendance: "
        f"{attendance_prediction['predicted_attendance']}"
    )

    print(
        f"Confidence: "
        f"{attendance_prediction['confidence_label']} "
        f"({attendance_prediction['confidence_score']:.1f})"
    )

    best_dates = (
        rank_best_event_dates(
            residents=residents,
            history=history,
            property_name=test_property,
            event_name="Movie Night",
            category="Entertainment",
            year=reference_date.year,
            month=reference_date.month,
            start_date=reference_date,
            top_n=5,
        )
    )

    assert isinstance(
        best_dates,
        pd.DataFrame,
    )

    assert not best_dates.empty

    assert len(
        best_dates
    ) <= 5

    assert best_dates[
        "event_date"
    ].is_unique

    assert list(
        best_dates[
            "date_rank"
        ]
    ) == list(
        range(
            1,
            len(best_dates) + 1,
        )
    )

    print(
        "\nBest event dates:"
    )

    print(
        best_dates[
            [
                "date_rank",
                "event_date",
                "weekday",
                "active_residents",
                "occupancy_percent",
                "predicted_attendance",
                "confidence_label",
            ]
        ].to_string(
            index=False
        )
    )

    print(
        "\nOccupancy and attendance "
        "intelligence test passed."
    )


if __name__ == "__main__":

    run_test()