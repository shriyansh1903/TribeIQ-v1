"""
===========================================================
TribeIQ UI Theme
===========================================================

Global styling for the entire Streamlit application.

This file controls:
- Theme
- Colors
- Typography
- Cards
- Sidebar
- Tables
- Buttons
- Inputs
- Expanders
- Tabs
===========================================================
"""

import streamlit as st


# ==========================================================
# Theme
# ==========================================================

PRIMARY = "#58A6FF"
PRIMARY_DARK = "#388BFD"

BACKGROUND = "#0D1117"

CARD = "#161B22"

TEXT = "#F0F6FC"

SUBTEXT = "#8B949E"

BORDER = "#30363D"

SUCCESS = "#3FB950"

WARNING = "#D29922"

DANGER = "#F85149"


# ==========================================================
# Page Config
# ==========================================================

def page_config():

    st.set_page_config(

        page_title="TribeIQ",

        page_icon="🎯",

        layout="wide",

        initial_sidebar_state="expanded"

    )


# ==========================================================
# CSS
# ==========================================================

def load_css():

    st.html(f"""

<style>

/* ==========================================================
Hide Streamlit Branding
========================================================== */

#MainMenu {{
    visibility:hidden;
}}

footer {{
    visibility:hidden;
}}

header[data-testid="stHeader"] {{
    background-color: transparent !important;
}}
[data-testid="stHeaderActionElements"] {{
    display: none;
}}


/* ==========================================================
Main App
========================================================== */

html, body, [class*="css"] {{

    font-family:
    "Inter",
    "Segoe UI",
    sans-serif;

}}

.stApp {{

    background:
        radial-gradient(
            circle at 85% 0%,
            rgba(88, 166, 255, 0.08),
            transparent 28%
        ),
        {BACKGROUND};

    color:{TEXT};

}}


/* ==========================================================
Content Width
========================================================== */

.block-container {{

    max-width: 1500px;
    padding-top:2rem;
    padding-bottom:3rem;
    padding-left:3rem;
    padding-right:3rem;

}}


/* ==========================================================
Sidebar
========================================================== */

section[data-testid="stSidebar"] {{

    background:{BACKGROUND};

    border-right:1px solid #21262D;

}}

section[data-testid="stSidebar"] > div {{

    background:{BACKGROUND};

}}

section[data-testid="stSidebar"] * {{

    color:#C9D1D9 !important;

}}

section[data-testid="stSidebar"] .stButton button {{

    width:100%;

}}


[data-testid="stSidebarNav"] {{

    padding-top: 1rem;

}}


[data-testid="stSidebarNav"] a {{

    border-radius: 10px;
    margin: 4px 10px;
    padding: 10px 12px;
    transition:
        background 0.2s ease,
        border-color 0.2s ease;

}}


[data-testid="stSidebarNav"] a:hover {{

    background: {CARD};

}}


[data-testid="stSidebarNav"]
a[aria-current="page"] {{

    background:
        rgba(
            88,
            166,
            255,
            0.14
        );
    border:
        1px solid
        rgba(
            88,
            166,
            255,
            0.25
        );

}}


/* ==========================================================
Headers
========================================================== */

h1 {{

    color:{TEXT};

    font-size:40px;

    font-weight:700;

    letter-spacing: -0.02em;

}}

h2 {{

    color:{TEXT};

    font-weight:700;

    letter-spacing: -0.02em;

}}

h3 {{

    color:{TEXT};

}}

h4 {{

    color:{TEXT} !important;

}}

p, label {{

    color:#C9D1D9;

}}


[data-testid="stCaptionContainer"] {{

    color:{SUBTEXT};

}}


/* ==========================================================
Metric Cards
========================================================== */

.metric-card {{

    background:{CARD};

    border-radius:18px;

    padding:22px;

    border:1px solid {BORDER};

}}

.metric-title {{

    color:{SUBTEXT};

    font-size:14px;

}}

.metric-value {{

    color:{TEXT};

    font-size:34px;

    font-weight:700;

}}


/* ==========================================================
Recommendation Cards
========================================================== */

.rec-card {{

    background:{CARD};

    border-radius:20px;

    padding:24px;

    border:1px solid {BORDER};

    margin-bottom:18px;

}}

.rec-title {{

    color:{TEXT};

    font-size:24px;

    font-weight:700;

}}

.rec-score {{

    color:{PRIMARY};

    font-size:28px;

    font-weight:700;

}}


/* ==========================================================
Containers
========================================================== */

div[data-testid="stVerticalBlock"]>div:has(div.stMetric) {{

    background:{CARD};

    border-radius:18px;

    border:1px solid {BORDER};

    padding:18px;

}}


/* ==========================================================
Metrics
========================================================== */

[data-testid="stMetric"] {{

    background:{CARD};

    border-radius:14px;

    border:1px solid {BORDER};

    padding:18px;

}}

[data-testid="stMetricLabel"] {{

    color:{SUBTEXT};

}}

[data-testid="stMetricValue"] {{

    color:{TEXT};

}}


/* ==========================================================
Buttons
========================================================== */

.stButton button {{

    border-radius:10px;
    min-height:44px;
    font-weight:700;
    transition: all 0.2s ease;
    background:{PRIMARY};
    color:white;
    border:none;

}}

.stButton button:hover {{

    background:{PRIMARY_DARK};
    color:white;

}}

.stButton button[kind="primary"] {{

    background: #238636;
    color: #FFFFFF;
    border: 1px solid #2EA043;

}}

.stButton button[kind="primary"]:hover {{

    background: #2EA043;
    border-color: #3FB950;

}}

.stButton button:not([kind="primary"]) {{

    background: #21262D;
    color: #F0F6FC;
    border: 1px solid #30363D;

}}

.stButton button:not([kind="primary"]):hover {{

    background: #30363D;
    border-color: #8B949E;

}}


/* ==========================================================
Inputs
========================================================== */

.stTextInput input,

.stNumberInput input,

.stDateInput input,

.stSelectbox div,

textarea {{

    background:{CARD};

    border-radius:10px;

    border-color:{BORDER};

    color:{TEXT};

}}

textarea {{

    min-height:120px;

}}

div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
div[data-baseweb="textarea"] > div {{

    background: {CARD};
    border-color: {BORDER};
    color: {TEXT};

}}

input,
textarea {{

    color: {TEXT} !important;

}}


/* ==========================================================
Forms
========================================================== */

[data-testid="stForm"] {{

    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 18px;
    padding: 24px;

}}


/* ==========================================================
Tabs
========================================================== */

.stTabs [data-baseweb="tab"] {{

    font-weight:600;

}}

.stTabs [aria-selected="true"] {{

    color:{PRIMARY};

}}


/* ==========================================================
Tables
========================================================== */

thead tr th {{

    background:{PRIMARY};

    color:white;

}}

tbody tr:hover {{

    background:#21262D;

}}


/* ==========================================================
Alerts
========================================================== */

.stSuccess {{

    border-radius:14px;

}}

.stInfo {{

    border-radius:14px;

}}

.stWarning {{

    border-radius:14px;

}}

.stError {{

    border-radius:14px;

}}


/* ==========================================================
DataFrames
========================================================== */

[data-testid="stDataFrame"] {{

    border: 1px solid {BORDER};
    border-radius: 12px;
    overflow: hidden;

}}


/* ==========================================================
Expander
========================================================== */

[data-testid="stExpander"] {{

    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 12px;

}}


.streamlit-expanderHeader {{

    font-weight:600;

    color:{TEXT};

}}


/* ==========================================================
Profile Cards
========================================================== */

.profile-card {{

    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 18px;
    padding: 24px;
    min-height: 210px;

}}

.profile-label {{

    color: {SUBTEXT};
    font-size: 12px;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 10px;

}}

.profile-value {{

    color: {TEXT};
    font-size: 22px;
    font-weight: 800;
    margin-bottom: 8px;

}}

.profile-description {{

    color: {SUBTEXT};
    font-size: 14px;
    line-height: 1.6;

}}


/* ==========================================================
Recommendation Display Cards
========================================================== */

.recommendation-card {{

    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 18px;
    padding: 24px;
    margin-bottom: 16px;
    min-height: 245px;

}}

.recommendation-label {{

    color: {SUBTEXT};
    font-size: 12px;
    font-weight: 800;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 10px;

}}

.recommendation-name {{

    color: {TEXT};
    font-size: 23px;
    font-weight: 800;
    line-height: 1.25;
    margin-bottom: 8px;

}}

.recommendation-category {{

    color: {SUBTEXT};
    font-size: 14px;
    margin-bottom: 22px;

}}

.score-grid {{

    display: flex;
    gap: 24px;
    flex-wrap: wrap;

}}

.score-label {{

    color: {SUBTEXT};
    font-size: 11px;
    font-weight: 700;
    margin-bottom: 4px;

}}

.score-value {{

    color: {PRIMARY};
    font-size: 19px;
    font-weight: 800;

}}

.score-value-green {{

    color: {SUCCESS};
    font-size: 19px;
    font-weight: 800;

}}

.score-value-purple {{

    color: #D2A8FF;
    font-size: 19px;
    font-weight: 800;

}}


/* ==========================================================
Event Context Cards
========================================================== */

.event-context-card {{

    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 18px;
    padding: 22px;
    margin-bottom: 18px;

}}

.event-context-label {{

    color: {SUBTEXT};
    font-size: 12px;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 8px;

}}

.event-context-name {{

    color: {TEXT};
    font-size: 22px;
    font-weight: 800;
    margin-bottom: 6px;

}}

.event-context-meta {{

    color: {SUBTEXT};
    font-size: 14px;
    line-height: 1.7;

}}


/* ==========================================================
Divider
========================================================== */

hr {{

    border-color: #21262D;
    margin-top:2rem;
    margin-bottom:2rem;

}}

</style>
""")

    st.html(f"""
<style>

/* Scrollbar styles */

::-webkit-scrollbar {{
    width: 10px;
    height: 10px;
}}

::-webkit-scrollbar-track {{
    background: {BACKGROUND};
}}

::-webkit-scrollbar-thumb {{
    background: {BORDER};
    border-radius: 10px;
}}

::-webkit-scrollbar-thumb:hover {{
    background: #484F58;
}}

@media (max-width: 900px) {{

    .block-container {{
        padding-left: 1.2rem;
        padding-right: 1.2rem;
    }}

}}

</style>
""")


# ==========================================================
# Apply Theme
# ==========================================================

def apply_theme():

    try:

        page_config()

    except Exception:

        pass

    load_css()
