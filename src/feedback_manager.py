"""
===========================================================
TribeIQ Feedback Manager
===========================================================

Manages event history.

Responsible for:

• Logging completed events
• Historical statistics
• Success score calculation
• History queries used by Recommendation Engine
"""

from datetime import datetime, timedelta

import pandas as pd

from config import EVENT_HISTORY


# ===========================================================
# Load / Save
# ===========================================================

def load_history():

    try:

        history = pd.read_csv(EVENT_HISTORY)

    except FileNotFoundError:

        return pd.DataFrame()

    if "Date" in history.columns:

        history["Date"] = pd.to_datetime(

            history["Date"],

            errors="coerce"

        )

    return history


def save_history(history):

    history.to_csv(

        EVENT_HISTORY,

        index=False

    )


# ===========================================================
# Success Score
# ===========================================================

def calculate_success_score(

    attendance_percent,

    average_feedback,

    planned_budget,

    actual_budget

):

    attendance_component = attendance_percent

    feedback_component = (

        average_feedback / 5

    ) * 100

    if planned_budget <= 0:

        budget_component = 100

    else:

        variance = abs(

            planned_budget -

            actual_budget

        )

        budget_component = max(

            0,

            100 -

            (

                variance /

                planned_budget

            ) * 100

        )

    score = (

        attendance_component * 0.40 +

        feedback_component * 0.40 +

        budget_component * 0.20

    )

    return round(score, 2)


# ===========================================================
# Add Event
# ===========================================================

def log_event(record):

    history = load_history()

    record["Success Score"] = calculate_success_score(

        record["Attendance %"],

        record["Average Feedback"],

        record["Budget Planned"],

        record["Budget Spent"]

    )

    history.loc[len(history)] = record

    save_history(history)


# ===========================================================
# Property History
# ===========================================================

def property_history(property_name):

    history = load_history()

    return history[

        history["Property"] == property_name

    ]


# ===========================================================
# Event History
# ===========================================================

def event_history(event_name):

    history = load_history()

    return history[

        history["Event Name"] == event_name

    ]


# ===========================================================
# Average Success
# ===========================================================

def average_success(event_name):

    history = event_history(event_name)

    if history.empty:

        return 0

    return round(

        history["Success Score"].mean(),

        2

    )


# ===========================================================
# Times Conducted
# ===========================================================

def times_conducted(

    property_name,

    event_name

):

    history = load_history()

    filtered = history[

        (history["Property"] == property_name)

        &

        (history["Event Name"] == event_name)

    ]

    return len(filtered)


# ===========================================================
# Recently Conducted
# ===========================================================

def recently_conducted(

    property_name,

    event_name,

    gap_days

):

    history = load_history()

    if history.empty:

        return False

    latest = history[

        (history["Property"] == property_name)

        &

        (history["Event Name"] == event_name)

    ]

    if latest.empty:

        return False

    last_date = latest["Date"].max()

    if pd.isna(last_date):

        return False

    return (

        datetime.today()

        -

        last_date

    ).days < gap_days


# ===========================================================
# Historical Bonus
# ===========================================================

def history_bonus(event_name):

    score = average_success(event_name)

    return score / 10


# ===========================================================
# Repeat Penalty
# ===========================================================

def repeat_penalty(

    property_name,

    event_name

):

    count = times_conducted(

        property_name,

        event_name

    )

    if count <= 2:

        return 0

    return (count - 2) * 2


# ===========================================================
# Recent Penalty
# ===========================================================

def recent_penalty(

    property_name,

    event_name,

    repeat_gap

):

    if recently_conducted(

        property_name,

        event_name,

        repeat_gap

    ):

        return 15

    return 0


# ===========================================================
# History Modifier
# ===========================================================

def history_modifier(

    property_name,

    event

):

    bonus = history_bonus(

        event["Event Name"]

    )

    recent = recent_penalty(

        property_name,

        event["Event Name"],

        int(event["Repeat Gap (Days)"])

    )

    repeat = repeat_penalty(

        property_name,

        event["Event Name"]

    )

    modifier = (

        bonus

        -

        recent

        -

        repeat

    )

    return {

        "bonus": round(bonus, 2),

        "recent_penalty": round(recent, 2),

        "repeat_penalty": round(repeat, 2),

        "modifier": round(modifier, 2)

    }


# ===========================================================
# Test
# ===========================================================

def run():

    history = load_history()

    print(history.head())

    print()

    print("Events Logged :", len(history))


if __name__ == "__main__":

    run()