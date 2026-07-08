"""
===========================================================
TribeIQ Integration Health
===========================================================

Final health-check layer for the integrated application.
===========================================================
"""

from typing import Any, Dict

import pandas as pd

from ui_data_bridge import (
    load_application_data,
    validate_application_data
)


def get_integration_health() -> Dict[str, Any]:

    try:

        data = load_application_data()

        errors = validate_application_data(
            data
        )

        residents = data.get(
            "residents",
            pd.DataFrame()
        )

        profiles = data.get(
            "profiles",
            {}
        )

        events = data.get(
            "events",
            pd.DataFrame()
        )

        history = data.get(
            "history",
            pd.DataFrame()
        )

        return {
            "healthy":
                len(errors) == 0,
            "errors":
                errors,
            "resident_count":
                len(residents)
                if isinstance(
                    residents,
                    pd.DataFrame
                )
                else 0,
            "property_count":
                len(profiles)
                if isinstance(
                    profiles,
                    dict
                )
                else 0,
            "event_count":
                len(events)
                if isinstance(
                    events,
                    pd.DataFrame
                )
                else 0,
            "history_count":
                len(history)
                if isinstance(
                    history,
                    pd.DataFrame
                )
                else 0
        }

    except Exception as error:

        return {
            "healthy":
                False,
            "errors":
                [str(error)],
            "resident_count":
                0,
            "property_count":
                0,
            "event_count":
                0,
            "history_count":
                0
        }