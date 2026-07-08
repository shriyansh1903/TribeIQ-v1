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


from occupancy_attendance_bridge import (
    build_recommendation_date_intelligence,
    clear_resident_timeline_cache,
    get_all_property_occupancy,
    get_best_event_dates,
    get_best_occupancy_dates,
    get_event_attendance_prediction,
    get_event_month_predictions,
    get_property_capacities,
    get_property_capacity,
    get_property_month_forecast,
    get_property_occupancy,
    get_resident_timeline,
)


def run_test():

    print(
        "Testing TribeIQ occupancy-attendance bridge...\n"
    )

    assert RESIDENT_FILE.exists(), (
        "Residents.csv was not found at: "
        f"{RESIDENT_FILE}"
    )

    clear_resident_timeline_cache()

    residents = get_resident_timeline(
        resident_path=RESIDENT_FILE,
        force_reload=True,
    )

    assert isinstance(
        residents,
        pd.DataFrame,
    )

    assert not residents.empty

    print(
        f"Resident timeline rows: "
        f"{len(residents)}"
    )

    capacities = get_property_capacities()

    expected_capacities = {
        "Tribe Vara": 192,
        "Tribe Moro": 296,
        "Tribe Wamba": 210,
    }

    assert capacities == expected_capacities

    assert (
        get_property_capacity(
            "Tribe Vara"
        )
        == 192
    )

    assert (
        get_property_capacity(
            "vara"
        )
        == 192
    )

    assert (
        get_property_capacity(
            "MORO"
        )
        == 296
    )

    assert (
        get_property_capacity(
            "wamba"
        )
        == 210
    )

    print(
        f"Verified capacity: "
        f"{sum(capacities.values())} beds"
    )

    reference_date = pd.Timestamp(
        date.today()
    ).normalize()

    property_name = "Tribe Vara"

    occupancy = get_property_occupancy(
        property_name=property_name,
        event_date=reference_date,
        resident_path=RESIDENT_FILE,
    )

    assert isinstance(
        occupancy,
        dict,
    )

    assert (
        occupancy[
            "property_name"
        ]
        == property_name
    )

    assert (
        occupancy[
            "total_capacity"
        ]
        == 192
    )

    assert (
        0.0
        <= occupancy[
            "occupancy_percent"
        ]
        <= 100.0
    )

    assert (
        occupancy[
            "occupied_beds"
        ]
        <= occupancy[
            "total_capacity"
        ]
    )

    print(
        f"{property_name}: "
        f"{occupancy['occupied_beds']}/"
        f"{occupancy['total_capacity']} occupied "
        f"({occupancy['occupancy_percent']:.2f}%)"
    )

    all_occupancy = get_all_property_occupancy(
        event_date=reference_date,
        resident_path=RESIDENT_FILE,
    )

    assert isinstance(
        all_occupancy,
        dict,
    )

    assert set(
        all_occupancy.keys()
    ) == set(
        expected_capacities.keys()
    )

    for (
        current_property,
        current_forecast,
    ) in all_occupancy.items():

        assert (
            current_forecast[
                "total_capacity"
            ]
            == expected_capacities[
                current_property
            ]
        )

        assert (
            0.0
            <= current_forecast[
                "occupancy_percent"
            ]
            <= 100.0
        )

    monthly_occupancy = (
        get_property_month_forecast(
            property_name=property_name,
            year=reference_date.year,
            month=reference_date.month,
            start_date=reference_date,
            resident_path=RESIDENT_FILE,
        )
    )

    assert isinstance(
        monthly_occupancy,
        pd.DataFrame,
    )

    assert not monthly_occupancy.empty

    assert monthly_occupancy[
        "event_date"
    ].is_unique

    print(
        f"Monthly occupancy dates: "
        f"{len(monthly_occupancy)}"
    )

    best_occupancy_dates = (
        get_best_occupancy_dates(
            property_name=property_name,
            year=reference_date.year,
            month=reference_date.month,
            start_date=reference_date,
            top_n=5,
            resident_path=RESIDENT_FILE,
        )
    )

    assert isinstance(
        best_occupancy_dates,
        pd.DataFrame,
    )

    assert not best_occupancy_dates.empty

    assert len(
        best_occupancy_dates
    ) <= 5

    assert best_occupancy_dates[
        "event_date"
    ].is_unique

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

    prediction = (
        get_event_attendance_prediction(
            property_name=property_name,
            event_name="Movie Night",
            category="Entertainment",
            event_date=reference_date,
            history=history,
            resident_path=RESIDENT_FILE,
        )
    )

    assert isinstance(
        prediction,
        dict,
    )

    assert (
        prediction[
            "predicted_attendance"
        ]
        >= 0
    )

    assert (
        prediction[
            "predicted_attendance"
        ]
        <= prediction[
            "active_residents"
        ]
    )

    assert (
        0.0
        <= prediction[
            "predicted_turnout_rate"
        ]
        <= 100.0
    )

    print(
        "\nAttendance prediction:"
    )

    print(
        f"Active residents: "
        f"{prediction['active_residents']}"
    )

    print(
        f"Predicted attendance: "
        f"{prediction['predicted_attendance']}"
    )

    print(
        f"Confidence: "
        f"{prediction['confidence_label']} "
        f"({prediction['confidence_score']:.1f})"
    )

    monthly_predictions = (
        get_event_month_predictions(
            property_name=property_name,
            event_name="Movie Night",
            category="Entertainment",
            year=reference_date.year,
            month=reference_date.month,
            history=history,
            start_date=reference_date,
            resident_path=RESIDENT_FILE,
        )
    )

    assert isinstance(
        monthly_predictions,
        pd.DataFrame,
    )

    assert not monthly_predictions.empty

    assert monthly_predictions[
        "event_date"
    ].is_unique

    best_event_dates = (
        get_best_event_dates(
            property_name=property_name,
            event_name="Movie Night",
            category="Entertainment",
            year=reference_date.year,
            month=reference_date.month,
            history=history,
            start_date=reference_date,
            top_n=5,
            resident_path=RESIDENT_FILE,
        )
    )

    assert isinstance(
        best_event_dates,
        pd.DataFrame,
    )

    assert not best_event_dates.empty

    assert len(
        best_event_dates
    ) <= 5

    assert best_event_dates[
        "event_date"
    ].is_unique

    assert list(
        best_event_dates[
            "date_rank"
        ]
    ) == list(
        range(
            1,
            len(best_event_dates) + 1,
        )
    )

    intelligence = (
        build_recommendation_date_intelligence(
            property_name=property_name,
            event_name="Movie Night",
            category="Entertainment",
            event_date=reference_date,
            history=history,
            resident_path=RESIDENT_FILE,
        )
    )

    required_fields = (
        "event_date",
        "weekday",
        "property_name",
        "event_name",
        "category",
        "total_capacity",
        "active_residents",
        "occupied_beds",
        "available_beds",
        "occupancy_percent",
        "predicted_turnout_rate",
        "predicted_attendance",
        "confidence_score",
        "confidence_label",
        "prediction_source",
    )

    for field in required_fields:

        assert field in intelligence

    assert (
        intelligence[
            "property_name"
        ]
        == property_name
    )

    assert (
        intelligence[
            "event_name"
        ]
        == "Movie Night"
    )

    assert (
        intelligence[
            "total_capacity"
        ]
        == 192
    )

    assert (
        intelligence[
            "predicted_attendance"
        ]
        <= intelligence[
            "active_residents"
        ]
    )

    print(
        "\nBest event dates:"
    )

    print(
        best_event_dates[
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
        "\nOccupancy-attendance bridge test passed."
    )


if __name__ == "__main__":

    run_test()