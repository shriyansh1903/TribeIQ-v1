"""
===========================================================
TribeIQ Data Cleaner
===========================================================

Responsibilities

1. Remove duplicate residents
2. Standardize text fields
3. Parse date columns
4. Keep only required columns
5. Save Residents_Cleaned.csv

This file NEVER creates features.
"""

import pandas as pd

from loader import load_residents
from validator import validate_residents
from config import (
    CLEAN_DATA,
    REQUIRED_COLUMNS,
    COLUMNS
)


# ===========================================================
# Helper Functions
# ===========================================================

def clean_text(series):

    return (
        series
        .astype(str)
        .str.strip()
        .replace("nan", pd.NA)
    )


def clean_datetime(series):

    return (
        pd.to_datetime(
            series,
            errors="coerce",
            utc=True
        )
        .dt.tz_convert(None)
    )


# ===========================================================
# Cleaning Pipeline
# ===========================================================

def clean_residents(df):

    print("Cleaning resident dataset...\n")

    # Keep only required columns
    df = df[REQUIRED_COLUMNS].copy()

    # Remove duplicates
    before = len(df)

    df = df.drop_duplicates()

    removed = before - len(df)

    print(f"Removed duplicate rows : {removed}")

    # -----------------------------
    # Clean text columns
    # -----------------------------

    text_columns = [

        COLUMNS["resident_id"],
        COLUMNS["name"],
        COLUMNS["gender"],
        COLUMNS["property"],
        COLUMNS["status"],
        COLUMNS["type"],
        COLUMNS["hometown"],
        COLUMNS["interests"],
        COLUMNS["company"],
        COLUMNS["college"],
        COLUMNS["course"]

    ]

    for column in text_columns:

        if column in df.columns:

            df[column] = clean_text(df[column])

    # -----------------------------
    # Date columns
    # -----------------------------

    date_columns = [

        COLUMNS["dob"],
        COLUMNS["move_in"],
        COLUMNS["move_out"]

    ]

    for column in date_columns:

        if column in df.columns:

            df[column] = clean_datetime(df[column])

    return df


# ===========================================================
# Save
# ===========================================================

def save(df):

    df.to_csv(CLEAN_DATA, index=False)

    print()

    print("Residents_Cleaned.csv created successfully.")

    print(f"Location : {CLEAN_DATA}")

    print(f"Rows : {len(df)}")

    print(f"Columns : {len(df.columns)}")


# ===========================================================
# Run
# ===========================================================

def run():

    df = load_residents()

    validate_residents(df)

    cleaned = clean_residents(df)

    save(cleaned)

    return cleaned


if __name__ == "__main__":

    run()