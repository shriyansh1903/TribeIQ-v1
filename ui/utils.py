# ui/utils.py

"""
===========================================================
TribeIQ UI Utilities
===========================================================

Helper functions used throughout the Streamlit frontend.

These functions DO NOT create UI components.
They only format, transform and safely load data.
"""

from pathlib import Path
from datetime import datetime

import json
import pandas as pd


# ===========================================================
# Formatting
# ===========================================================

def format_percentage(value):

    if value is None or pd.isna(value):
        return "-"

    return f"{value:.1f}%"


def format_score(value):

    if value is None or pd.isna(value):
        return "-"

    return f"{value:.2f}"


def format_currency(value):

    if value is None or pd.isna(value):
        return "₹0"

    return f"₹{value:,.0f}"


def format_days(days):

    if days is None or pd.isna(days):
        return "-"

    if days < 30:
        return f"{int(days)} Days"

    months = days / 30.4

    if months < 12:
        return f"{months:.1f} Months"

    years = months / 12

    return f"{years:.1f} Years"


def format_date(date):

    if pd.isna(date):
        return "-"

    if isinstance(date, str):

        try:

            date = pd.to_datetime(date)

        except Exception:

            return date

    return date.strftime("%d %b %Y")


# ===========================================================
# Badge Colors
# ===========================================================

def priority_color(priority):

    colors = {

        "High": "#DC2626",

        "Medium": "#F59E0B",

        "Low": "#16A34A"

    }

    return colors.get(priority, "#6B7280")


def stage_color(stage):

    colors = {

        "Growing": "#3B82F6",

        "Balanced": "#16A34A",

        "Established": "#9333EA"

    }

    return colors.get(stage, "#6B7280")


def size_color(size):

    colors = {

        "Small": "#F59E0B",

        "Medium": "#2563EB",

        "Large": "#16A34A"

    }

    return colors.get(size, "#6B7280")


# ===========================================================
# Safe Loaders
# ===========================================================

def load_json(filepath):

    filepath = Path(filepath)

    if not filepath.exists():

        return {}

    with open(filepath, "r", encoding="utf-8") as file:

        return json.load(file)


def load_csv(filepath):

    filepath = Path(filepath)

    if not filepath.exists():

        return pd.DataFrame()

    return pd.read_csv(filepath)


# ===========================================================
# Data Helpers
# ===========================================================

def property_list(profiles):

    return sorted(list(profiles.keys()))


def latest_update(filepath):

    filepath = Path(filepath)

    if not filepath.exists():

        return "-"

    modified = datetime.fromtimestamp(

        filepath.stat().st_mtime

    )

    return modified.strftime("%d %b %Y %I:%M %p")


# ===========================================================
# Text Helpers
# ===========================================================

def truncate(text, length=80):

    if text is None:

        return ""

    text = str(text)

    if len(text) <= length:

        return text

    return text[:length] + "..."


def capitalize_words(text):

    if text is None:

        return ""

    return str(text).title()


# ===========================================================
# Download Helper
# ===========================================================

def dataframe_to_csv(df):

    return df.to_csv(index=False).encode("utf-8")