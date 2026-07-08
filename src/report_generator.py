"""
===========================================================
TribeIQ Report Generator
===========================================================

Generates recommendation reports.

Outputs

recommendation_report.csv
"""

import pandas as pd

from config import RECOMMENDATION_REPORT

from recommendation_engine import generate_recommendations

from selection_logic import build_all_calendars


# ===========================================================
# Build Report
# ===========================================================

def build_report():

    recommendations = generate_recommendations()

    calendars = build_all_calendars(

        recommendations

    )

    rows = []

    for property_name, calendar in calendars.items():

        major = calendar.get("major_event")

        if major is not None:

            rows.append({

                "Property": property_name,

                "Recommendation Type": "Major Event",

                "Event ID": major["event_id"],

                "Event Name": major["event_name"],

                "Category": major["category"],

                "Event Type": major["event_type"],

                "Priority": major["priority"],

                "Community Impact": major["community_impact"],

                "Resident Match Score": major["resident_score"],

                "History Bonus": major["history_bonus"],

                "Recent Penalty": major["recent_penalty"],

                "Repeat Penalty": major["repeat_penalty"],

                "History Modifier": major["history_modifier"],

                "Final Score": major["final_score"],

                "Reasons": " | ".join(

                    major["reasons"]

                )

            })

        for i, minor in enumerate(calendar.get("minor_events", []), start=1):

            rows.append({

                "Property": property_name,

                "Recommendation Type": f"Minor Event {i}",

                "Event ID": minor["event_id"],

                "Event Name": minor["event_name"],

                "Category": minor["category"],

                "Event Type": minor["event_type"],

                "Priority": minor["priority"],

                "Community Impact": minor["community_impact"],

                "Resident Match Score": minor["resident_score"],

                "History Bonus": minor["history_bonus"],

                "Recent Penalty": minor["recent_penalty"],

                "Repeat Penalty": minor["repeat_penalty"],

                "History Modifier": minor["history_modifier"],

                "Final Score": minor["final_score"],

                "Reasons": " | ".join(

                    minor["reasons"]

                )

            })

    return pd.DataFrame(rows)


# ===========================================================
# Save Report
# ===========================================================

def save_report(df):

    df.to_csv(

        RECOMMENDATION_REPORT,

        index=False

    )

    print()

    print("=" * 80)

    print("Recommendation Report Generated")

    print("=" * 80)

    print()

    print(

        f"Saved to: {RECOMMENDATION_REPORT}"

    )

    print(

        f"Properties: {df['Property'].nunique()}"

    )

    print(

        f"Recommendations: {len(df)}"

    )


# ===========================================================
# Run
# ===========================================================

def run():

    report = build_report()

    save_report(report)

    print()

    print(report.head())


if __name__ == "__main__":

    run()