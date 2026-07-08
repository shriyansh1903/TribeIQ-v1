"""
===========================================================
TribeIQ Event Loader
===========================================================

Responsibilities

1. Load events.csv
2. Validate required columns
3. Convert comma-separated fields into Python lists
4. Normalize text
5. Return a clean DataFrame
"""

import pandas as pd

from config import EVENTS_DATA, EVENT_COLUMNS


# ===========================================================
# Helpers
# ===========================================================

def clean_text(value):

    if pd.isna(value):
        return ""

    return str(value).strip()


def split_list(value):
    """
    Converts:

    Sports,Music,Movies

    into

    ["Sports","Music","Movies"]
    """

    if pd.isna(value):
        return []

    value = str(value).strip()

    if value == "":
        return []

    return [item.strip() for item in value.split(",")]


# ===========================================================
# Validation
# ===========================================================

def validate(df):

    missing = []

    for column in EVENT_COLUMNS:

        if column not in df.columns:
            missing.append(column)

    if missing:

        raise Exception(

            "Missing Event Columns:\n"

            + "\n".join(missing)

        )


# ===========================================================
# Load
# ===========================================================

def load_events():

    df = pd.read_csv(EVENTS_DATA)

    df.columns = df.columns.str.strip()

    validate(df)

    # -----------------------------------
    # Columns containing multiple values
    # -----------------------------------

    multi_value_columns = [

        "Target Occupation",

        "Target Age Band",

        "Target Tenure Band",

        "Target Interests"

    ]

    for column in multi_value_columns:

        if column in df.columns:

            df[column] = df[column].apply(split_list)

    # -----------------------------------
    # Clean remaining text columns
    # -----------------------------------

    for column in df.columns:

        if column not in multi_value_columns:

            if df[column].dtype == object:

                df[column] = df[column].apply(clean_text)

    return df


# ===========================================================
# Test
# ===========================================================

def run():

    df = load_events()

    print()

    print("=" * 70)

    print("EVENT DATABASE LOADED")

    print("=" * 70)

    print()

    print(df.head())

    print()

    print(df.iloc[0]["Target Interests"])

    print(type(df.iloc[0]["Target Interests"]))

    print()

    print(df.shape)


if __name__ == "__main__":

    run()