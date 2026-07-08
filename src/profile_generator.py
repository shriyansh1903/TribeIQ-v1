"""
===========================================================
TribeIQ Property Profile Generator
===========================================================

Input:
    Residents_Features.csv

Outputs:
    property_summary.csv
    property_profiles.json
"""

import ast
import json
from collections import Counter

import pandas as pd

from config import (
    FEATURE_DATA,
    PROPERTY_SUMMARY,
    PROPERTY_PROFILES,
    COLUMNS
)


# ===========================================================
# Helpers
# ===========================================================

def percentage(series):

    if series.empty:
        return {}

    return (
        series
        .fillna("Unknown")
        .value_counts(normalize=True)
        .mul(100)
        .round(2)
        .to_dict()
    )


def dominant(series):

    if series.dropna().empty:
        return "Unknown"

    return series.mode().iloc[0]


def community_size(count):

    if count < 75:
        return "Small"

    if count <= 150:
        return "Medium"

    return "Large"


def community_stage(tenure_distribution):

    new_pct = tenure_distribution.get("New", 0)

    old_pct = tenure_distribution.get("1+ Years", 0)

    if new_pct >= 40:
        return "Growing"

    if old_pct >= 40:
        return "Established"

    return "Balanced"


# ===========================================================
# Interest Parsing
# ===========================================================

def normalize_interest(value):

    if pd.isna(value):
        return []

    text = str(value).strip()

    if text == "":
        return []

    try:

        parsed = ast.literal_eval(text)

        if isinstance(parsed, list):

            return [

                str(item).strip().title()

                for item in parsed

                if str(item).strip()

            ]

    except Exception:

        pass

    return [

        item.strip().title()

        for item in text.split(",")

        if item.strip()

    ]


def extract_top_interests(series):

    counter = Counter()

    for value in series:

        interests = normalize_interest(value)

        for interest in interests:

            counter[interest] += 1

    return dict(counter.most_common(15))


# ===========================================================
# Property Profile
# ===========================================================

def create_property_profile(property_name, group):

    resident_count = len(group)

    gender_distribution = percentage(group[COLUMNS["gender"]])

    occupation_distribution = percentage(group["Occupation"])

    age_distribution = percentage(group["Age Band"])

    tenure_distribution = percentage(group["Tenure Band"])

    region_distribution = percentage(group["Region"])

    interests = extract_top_interests(

        group[COLUMNS["interests"]]

    )

    profile = {

        "Property": property_name,

        "Resident Count": resident_count,

        "Community Size": community_size(resident_count),

        "Community Stage": community_stage(

            tenure_distribution

        ),

        "Average Age": round(

            group["Age"].mean(),

            2

        ),

        "Median Age": round(

            group["Age"].median(),

            2

        ),

        "Average Tenure": round(

            group["Tenure Days"].mean(),

            2

        ),

        "Median Tenure": round(

            group["Tenure Days"].median(),

            2

        ),

        "Gender Distribution": gender_distribution,

        "Occupation Distribution": occupation_distribution,

        "Age Distribution": age_distribution,

        "Tenure Distribution": tenure_distribution,

        "Region Distribution": region_distribution,

        "Top Interests": interests,

        "Dominant Occupation": dominant(

            group["Occupation"]

        ),

        "Dominant Age Band": dominant(

            group["Age Band"]

        ),

        "Dominant Tenure Band": dominant(

            group["Tenure Band"]

        ),

        "Dominant Region": dominant(

            group["Region"]

        )

    }

    return profile


# ===========================================================
# Generate Profiles
# ===========================================================

def generate_profiles(df):

    profiles = {}

    summary = []

    property_column = COLUMNS["property"]

    for property_name, group in df.groupby(property_column):

        profile = create_property_profile(

            property_name,

            group

        )

        profiles[property_name] = profile

        summary.append({

            "Property": property_name,

            "Residents": profile["Resident Count"],

            "Community Size": profile["Community Size"],

            "Community Stage": profile["Community Stage"],

            "Average Age": profile["Average Age"],

            "Average Tenure": profile["Average Tenure"],

            "Dominant Occupation": profile["Dominant Occupation"],

            "Dominant Age Band": profile["Dominant Age Band"],

            "Dominant Region": profile["Dominant Region"]

        })

    return profiles, pd.DataFrame(summary)


# ===========================================================
# Save
# ===========================================================

def save_profiles(

    profiles,

    summary

):

    summary.to_csv(

        PROPERTY_SUMMARY,

        index=False

    )

    with open(

        PROPERTY_PROFILES,

        "w",

        encoding="utf-8"

    ) as file:

        json.dump(

            profiles,

            file,

            indent=4

        )

    print()

    print("Property Profiles Generated")

    print(f"Properties : {len(profiles)}")

    print(f"Summary    : {PROPERTY_SUMMARY}")

    print(f"Profiles   : {PROPERTY_PROFILES}")


# ===========================================================
# Run
# ===========================================================

def run():

    df = pd.read_csv(FEATURE_DATA)

    profiles, summary = generate_profiles(df)

    save_profiles(

        profiles,

        summary

    )

    return profiles


if __name__ == "__main__":

    run()