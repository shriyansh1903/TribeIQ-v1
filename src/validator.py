"""
===========================================================
TribeIQ Data Validator
===========================================================

Responsible for validating:

1. Resident dataset
2. Event dataset

No cleaning happens here.

This module only checks whether the data is suitable for processing.
"""

from config import REQUIRED_COLUMNS, EVENT_COLUMNS


# ===========================================================
# Resident Validation
# ===========================================================

def validate_residents(df):

    print("\nValidating resident dataset...")

    missing_columns = []

    for column in REQUIRED_COLUMNS:

        if column not in df.columns:
            missing_columns.append(column)

    if missing_columns:

        print("\nMissing Resident Columns:")

        for column in missing_columns:
            print(f"  - {column}")

        raise Exception("Resident dataset validation failed.")

    duplicate_rows = df.duplicated().sum()

    print(f"Duplicate Rows : {duplicate_rows}")

    print("Resident dataset validation passed.\n")

    return True


# ===========================================================
# Event Validation
# ===========================================================

def validate_events(df):

    print("Validating event dataset...")

    missing_columns = []

    for column in EVENT_COLUMNS:

        if column not in df.columns:
            missing_columns.append(column)

    if missing_columns:

        print("\nMissing Event Columns:")

        for column in missing_columns:
            print(f"  - {column}")

        raise Exception("Event dataset validation failed.")

    duplicate_events = df.duplicated().sum()

    print(f"Duplicate Events : {duplicate_events}")

    print("Event dataset validation passed.\n")

    return True


# ===========================================================
# Test
# ===========================================================

def run():

    from loader import load_residents, load_events

    residents = load_residents()

    events = load_events()

    validate_residents(residents)

    validate_events(events)

    print("=" * 60)
    print("ALL VALIDATIONS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    run()