"""
===========================================================
TribeIQ Feature Engineering
===========================================================

Creates resident-level features.

Input:
    Residents_Cleaned.csv

Output:
    Residents_Features.csv
"""

import pandas as pd

from config import CLEAN_DATA, FEATURE_DATA, COLUMNS


# ===========================================================
# REGION MAPPING
# ===========================================================

STATE_REGION = {

    "maharashtra": "West",
    "gujarat": "West",
    "goa": "West",

    "delhi": "North",
    "haryana": "North",
    "punjab": "North",
    "uttar pradesh": "North",
    "rajasthan": "North",

    "karnataka": "South",
    "kerala": "South",
    "tamil nadu": "South",
    "telangana": "South",
    "andhra pradesh": "South",

    "bihar": "East",
    "jharkhand": "East",
    "west bengal": "East",
    "assam": "East",
    "odisha": "East",

    "madhya pradesh": "Central",
    "chhattisgarh": "Central"

}


# ===========================================================
# AGE BAND
# ===========================================================

def age_band(age):

    if pd.isna(age):
        return "Unknown"

    if age <= 22:
        return "18-22"

    if age <= 27:
        return "23-27"

    if age <= 35:
        return "28-35"

    return "35+"


# ===========================================================
# TENURE BAND
# ===========================================================

def tenure_band(days):

    if pd.isna(days):
        return "Unknown"

    if days <= 30:
        return "New"

    if days <= 90:
        return "1-3 Months"

    if days <= 180:
        return "3-6 Months"

    if days <= 365:
        return "6-12 Months"

    return "1+ Years"


# ===========================================================
# OCCUPATION
# ===========================================================

def occupation(row):

    resident_type = str(row[COLUMNS["type"]]).lower()

    if "student" in resident_type:
        return "Student"

    if "working" in resident_type:
        return "Working Professional"

    company = str(row[COLUMNS["company"]])

    college = str(row[COLUMNS["college"]])

    if company != "nan":
        return "Working Professional"

    if college != "nan":
        return "Student"

    return "Unknown"


# ===========================================================
# REGION
# ===========================================================

def region(text):

    if pd.isna(text):
        return "Unknown"

    text = str(text).lower()

    for state in STATE_REGION:

        if state in text:
            return STATE_REGION[state]

    return "Unknown"


# ===========================================================
# FEATURE ENGINEERING
# ===========================================================

def create_features(df):

    from datetime import datetime, timezone, timedelta
    ist = timezone(timedelta(hours=5, minutes=30))
    today = pd.Timestamp(datetime.now(ist).date()).normalize()

    # ---------------- AGE ----------------

    df["Age"] = (

        (today - df[COLUMNS["dob"]])

        .dt.days

        /365.25

    ).round()

    df["Age"] = df["Age"].astype("Int64")

    df["Age Band"] = df["Age"].apply(age_band)

    # ---------------- TENURE ----------------

    df["Tenure Days"] = (

        today -

        df[COLUMNS["move_in"]]

    ).dt.days

    df["Tenure Band"] = df["Tenure Days"].apply(tenure_band)

    # ---------------- OCCUPATION ----------------

    df["Occupation"] = df.apply(occupation, axis=1)

    # ---------------- REGION ----------------

    df["Region"] = df[COLUMNS["hometown"]].apply(region)

    return df


# ===========================================================
# SAVE
# ===========================================================

def save(df):

    df.to_csv(FEATURE_DATA, index=False)

    print()

    print("Residents_Features.csv generated.")

    print(df.shape)


# ===========================================================
# RUN
# ===========================================================

def run():

    df = pd.read_csv(

        CLEAN_DATA,

        parse_dates=[

            COLUMNS["dob"],
            COLUMNS["move_in"],
            COLUMNS["move_out"]

        ]

    )

    df = create_features(df)

    save(df)

    return df


if __name__ == "__main__":

    run()