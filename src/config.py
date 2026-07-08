"""
===========================================================
TribeIQ Configuration File
===========================================================

Central configuration for the entire project.

Contains:
- File paths
- Column mappings
- Validation columns
- Scoring weights
- History weights
"""

import os

# ===========================================================
# BASE DIRECTORIES
# ===========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PROJECT_ROOT = os.path.dirname(BASE_DIR)

DATA_DIR = os.path.join(PROJECT_ROOT, "data")

OUTPUT_DIR = os.path.join(PROJECT_ROOT, "outputs")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ===========================================================
# INPUT FILES
# ===========================================================

RAW_DATA = os.path.join(DATA_DIR, "Residents.csv")

EVENTS_DATA = os.path.join(DATA_DIR, "events.csv")

EVENT_HISTORY = os.path.join(DATA_DIR, "event_history.csv")

# ===========================================================
# OUTPUT FILES
# ===========================================================

CLEAN_DATA = os.path.join(OUTPUT_DIR, "Residents_Cleaned.csv")

FEATURE_DATA = os.path.join(OUTPUT_DIR, "Residents_Features.csv")

PROPERTY_SUMMARY = os.path.join(OUTPUT_DIR, "property_summary.csv")

PROPERTY_PROFILES = os.path.join(OUTPUT_DIR, "property_profiles.json")

RECOMMENDATION_REPORT = os.path.join(
    OUTPUT_DIR,
    "recommendation_report.csv"
)

# ===========================================================
# RESIDENT COLUMN MAPPING
# ===========================================================

COLUMNS = {

    "resident_id": "Resident ID",

    "name": "Name",

    "gender": "Gender",

    "dob": "Date Of Birth",

    "property": "Property",

    "status": "Status",

    "type": "Type",

    "move_in": "Move In Date",

    "move_out": "Move Out Date",

    "hometown": "Hometown",

    "interests": "Interests",

    "company": "Company Name",

    "college": "College Name",

    "course": "Course Name"

}

# ===========================================================
# REQUIRED RESIDENT COLUMNS
# ===========================================================

REQUIRED_COLUMNS = list(COLUMNS.values())

# ===========================================================
# REQUIRED EVENT COLUMNS
# ===========================================================

EVENT_COLUMNS = [

    "Event ID",

    "Event Name",

    "Category",

    "Subcategory",

    "Description",

    "Primary Objective",

    "Target Occupation",

    "Target Age Band",

    "Target Tenure Band",

    "Target Interests",

    "Community Size",

    "Budget",

    "Planning Effort",

    "Indoor/Outdoor",

    "Weather Dependency",

    "Expected Attendance %",

    "Networking Score",

    "Community Building Score",

    "Entertainment Score",

    "Learning Score",

    "Physical Activity Score",

    "Suitable For New Residents",

    "Suitable For Long-term Residents",

    "Suitable For Students",

    "Suitable For Working Professionals",

    "Recommended Frequency",

    "Event Type",

    "Ideal Community Stage",

    "Priority",

    "Ideal Group Size",

    "Maximum Capacity",

    "Event Duration (Hours)",

    "Vendor Required",

    "Equipment Required",

    "Food Included",

    "Repeat Gap (Days)",

    "Suitable Season",

    "Festival Linked",

    "Cost Estimate (₹)",

    "Community Impact"

]

# ===========================================================
# RECOMMENDATION WEIGHTS
# ===========================================================

DEFAULT_WEIGHTS = {

    "occupation": 25,

    "age": 15,

    "tenure": 20,

    "interest": 20,

    "community_size": 10,

    "community_stage": 10

}

# ===========================================================
# HISTORY WEIGHTS
# ===========================================================

HISTORY_WEIGHTS = {

    "success_bonus": 10,

    "recent_penalty": 15,

    "repeat_penalty": 8

}

# ===========================================================
# COMMUNITY SIZE
# ===========================================================

COMMUNITY_SIZE_RULES = {

    "Small": (0, 74),

    "Medium": (75, 150),

    "Large": (151, 100000)

}