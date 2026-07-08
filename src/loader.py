"""
===========================================================
TribeIQ Data Loader
===========================================================

Responsible for:
1. Loading Residents.csv
2. Loading events.csv
3. Standardizing column names

No cleaning or validation happens here.
"""

import pandas as pd

from config import RAW_DATA, EVENTS_DATA


def load_residents():
    """
    Load resident dataset.
    """

    df = pd.read_csv(RAW_DATA)

    # Remove accidental leading/trailing spaces
    df.columns = df.columns.str.strip()

    return df


def load_events():
    """
    Load event knowledge base.
    """

    df = pd.read_csv(EVENTS_DATA)

    df.columns = df.columns.str.strip()

    return df


def preview(df, rows=5):
    """
    Print a quick preview of a dataframe.
    """

    print("\nShape :", df.shape)
    print("\nColumns:")
    print(df.columns.tolist())

    print("\nPreview:")
    print(df.head(rows))


def run():
    """
    Test loader.
    """

    residents = load_residents()
    events = load_events()

    print("=" * 60)
    print("RESIDENT DATA")
    print("=" * 60)
    preview(residents)

    print("\n")

    print("=" * 60)
    print("EVENT KNOWLEDGE BASE")
    print("=" * 60)
    preview(events)


if __name__ == "__main__":
    run()