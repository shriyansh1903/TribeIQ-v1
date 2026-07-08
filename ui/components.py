"""
===========================================================
TribeIQ UI Components
===========================================================

Reusable UI Components

Every page should use ONLY the functions defined here.
"""

import streamlit as st
import plotly.express as px
import pandas as pd


# ==========================================================
# Page
# ==========================================================

def page_header(title, subtitle=""):

    st.title(title)

    if subtitle:
        st.html(
            f"<p style='color:#8B949E;font-size:18px;margin-top:-12px'>{subtitle}</p>"
        )

    st.html("<br>")


# ==========================================================
# Section
# ==========================================================

def section_header(title):

    st.markdown(f"## {title}")


# ==========================================================
# Property Selector
# ==========================================================

def property_selector(properties):

    return st.selectbox(

        "Select Property",

        properties,

        index=0

    )


# ==========================================================
# Metric Cards
# ==========================================================

def metric_row(metrics):

    cols = st.columns(len(metrics))

    for col, metric in zip(cols, metrics):

        with col:

            st.metric(

                metric["title"],

                metric["value"],

                metric.get("delta")

            )


# ==========================================================
# Recommendation Cards
# ==========================================================

def recommendation_card(event, badge="Recommended"):

    score = round(event["final_score"], 2)

    reasons = event["reasons"]

    with st.container():

        col_left, col_right = st.columns([3, 1])

        with col_left:

            st.markdown(
                f"### {event['event_name']}"
            )

            st.caption(
                f"{event['category']}  •  {event.get('event_type', '')}  •  {event.get('priority', '')}"
            )

        with col_right:

            st.metric(
                label=badge,
                value=f"{score}"
            )

        if reasons:

            st.write("**Why this event?**")

            for reason in reasons:
                st.write(f"• {reason}")


# ==========================================================
# Major Recommendation
# ==========================================================

def major_event_card(event):

    recommendation_card(

        event,

        badge="⭐ Best Match"

    )


# ==========================================================
# Minor Recommendation
# ==========================================================

def minor_event_card(event):

    recommendation_card(

        event,

        badge="Alternative"

    )


# ==========================================================
# Score Breakdown
# ==========================================================

def recommendation_breakdown(breakdown):

    rows = []

    for metric, values in breakdown.items():

        rows.append({

            "Metric": metric,

            "Raw Score": round(values["raw_score"],2),

            "Weight": values["weight"],

            "Contribution": round(values["weighted_score"],2)

        })

    st.dataframe(

        pd.DataFrame(rows),

        width="stretch",

        hide_index=True

    )


# ==========================================================
# Property Summary
# ==========================================================

def property_summary(profile):

    metric_row([

        {

            "title":"Residents",

            "value":profile["Resident Count"]

        },

        {

            "title":"Average Age",

            "value":round(profile["Average Age"],1)

        },

        {

            "title":"Average Tenure",

            "value":round(profile["Average Tenure"],1)

        },

        {

            "title":"Community Stage",

            "value":profile["Community Stage"]

        }

    ])


# ==========================================================
# Community Badges
# ==========================================================

def community_badges(profile):

    c1,c2,c3,c4 = st.columns(4)

    c1.success(profile["Community Size"])

    c2.info(profile["Dominant Occupation"])

    c3.warning(profile["Dominant Age Band"])

    c4.success(profile["Dominant Region"])


# ==========================================================
# Interest Tags
# ==========================================================

def interest_tags(interests):

    df = pd.DataFrame({

        "Interest":interests.keys(),

        "Residents":interests.values()

    })

    fig = px.bar(

        df,

        x="Residents",

        y="Interest",

        orientation="h"

    )

    fig.update_layout(

        height=420,

        margin=dict(

            l=10,

            r=10,

            t=20,

            b=10

        )

    )

    st.plotly_chart(

        fig,

        use_container_width=True

    )


# ==========================================================
# Pie Chart
# ==========================================================

def pie_chart(data, title):

    df = pd.DataFrame({

        "Category":list(data.keys()),

        "Value":list(data.values())

    })

    fig = px.pie(

        df,

        names="Category",

        values="Value",

        hole=0.55,

        title=title

    )

    fig.update_layout(

        margin=dict(

            l=20,

            r=20,

            t=50,

            b=20

        )

    )

    st.plotly_chart(

        fig,

        use_container_width=True

    )


# ==========================================================
# Bar Chart
# ==========================================================

def bar_chart(data, title):

    df = pd.DataFrame({

        "Category":list(data.keys()),

        "Value":list(data.values())

    })

    fig = px.bar(

        df,

        x="Category",

        y="Value",

        title=title

    )

    fig.update_layout(

        margin=dict(

            l=20,

            r=20,

            t=50,

            b=20

        )

    )

    st.plotly_chart(

        fig,

        use_container_width=True

    )


# ==========================================================
# Horizontal Bar
# ==========================================================

def horizontal_bar_chart(data, title):

    df = pd.DataFrame({

        "Category":list(data.keys()),

        "Value":list(data.values())

    })

    fig = px.bar(

        df,

        x="Value",

        y="Category",

        orientation="h",

        title=title

    )

    fig.update_layout(

        margin=dict(

            l=20,

            r=20,

            t=50,

            b=20

        )

    )

    st.plotly_chart(

        fig,

        use_container_width=True

    )


# ==========================================================
# History Table
# ==========================================================

def history_table(df):

    st.dataframe(

        df,

        width="stretch",

        hide_index=True

    )


# ==========================================================
# Download Button
# ==========================================================

def download_button(label, data, filename):

    st.download_button(

        label,

        data,

        file_name=filename,

        mime="text/csv"

    )