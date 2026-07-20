import sys
from pathlib import Path
from typing import Any, Dict, List
import pandas as pd
import streamlit as st
import datetime

# ===========================================================
# Project Paths
# ===========================================================
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from src.auth.session_manager import require_login
require_login("Recommendations")

# Backend Imports
from ui_data_bridge import (
    generate_property_recommendations,
    get_session_property,
    get_session_result,
    load_application_data,
    save_result_to_session,
    save_predictions_to_csv,
)
from recommendation_date_bridge import (
    enrich_recommendation_result_for_date,
    enrich_recommendation_result_with_best_dates,
)
from ui.styles import load_css
from utils.schema_utils import safe_get_column, safe_status_column, safe_numeric_column, safe_column_exists

# Load CSS Theme
load_css()

# Basic Helpers
def safe_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        pass
    return str(value).strip()

def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        numeric = float(value)
        if pd.isna(numeric):
            return default
        return numeric
    except (TypeError, ValueError):
        return default

def safe_int(value: Any, default: int = 0) -> int:
    try:
        numeric = int(float(value))
        return numeric
    except (TypeError, ValueError):
        return default

# Load Application Data
application_data = load_application_data() or {}
profiles = application_data.get("profiles", {})
events = application_data.get("events", pd.DataFrame())

# Select Property
property_names = sorted(profiles.keys())
recommended_property = get_session_property(st.session_state)
default_index = 0
if recommended_property in property_names:
    default_index = property_names.index(recommended_property)

# ===========================================================
# SECTION 1: Recommendation Workspace Header
# ===========================================================
st.write("## 🎯 AI Smart Recommendations Workspace")
st.write("Flagship Community Intelligence & Turnout Forecaster")

selected_property = st.selectbox("Active Property", options=property_names, index=default_index)
profile = profiles.get(selected_property, {})

col_h1, col_h2, col_h3 = st.columns(3)
with col_h1:
    st.metric("Property Type", profile.get("Property Type", "Commune"))
with col_h2:
    st.metric("Total Residents", f"{profile.get('Resident Count', 100)}")
with col_h3:
    st.metric("Community Stage", profile.get("Community Stage", "Growing"))

# Actions row
col_act1, col_act2 = st.columns(2)
with col_act1:
    if st.button("⚡ Generate AI Recommendations", use_container_width=True):
        with st.spinner("Analyzing demographics and history..."):
            res = generate_property_recommendations(selected_property, application_data)
            if res:
                today = datetime.date.today()
                if today.month == 12:
                    planning_year = today.year + 1
                    planning_month = 1
                else:
                    planning_year = today.year
                    planning_month = today.month + 1
                
                history_df = application_data.get("history", pd.DataFrame())
                start_date_val = datetime.date(planning_year, planning_month, 1)
                
                enriched = enrich_recommendation_result_with_best_dates(
                    recommendation_result=res,
                    property_name=selected_property,
                    year=planning_year,
                    month=planning_month,
                    history=history_df,
                    start_date=start_date_val
                )
                save_result_to_session(st.session_state, enriched)
                st.success("Recommendations generated successfully!")
                st.rerun()

with col_act2:
    if st.button("🔄 Refresh Pipeline Cache", use_container_width=True):
        st.cache_data.clear()
        st.success("Cache cleared.")
        st.rerun()

# Get Recommendations
rec_result = get_session_result(st.session_state)

if rec_result and isinstance(rec_result, dict):
    # ===========================================================
    # SECTION 2: Recommendation Summary (Error Boundary)
    # ===========================================================
    st.write("---")
    st.write("### 👔 Executive Summary")
    
    try:
        major_event = rec_result.get("major_event", {})
        minor_events = rec_result.get("minor_events", [])
        
        avg_score = rec_result.get("average_score", 85.0)
        expected_turnout = major_event.get("predicted_turnout_rate", 78.5) if isinstance(major_event, dict) else 78.5
        
        s_col1, s_col2, s_col3 = st.columns(3)
        with s_col1:
            st.metric("Major Event Recommendation", major_event.get("event_name", "N/A") if isinstance(major_event, dict) else "N/A")
        with s_col2:
            st.metric("Minor Events Selected", len(minor_events))
        with s_col3:
            st.metric("Avg Recommendation Score", f"{avg_score:.1f}")
    except Exception as e:
        st.warning("⚠ Unable to load this widget.")

    # ===========================================================
    # SECTION 3: Major Event Card (Error Boundary)
    # ===========================================================
    st.write("---")
    st.write("### ⭐ Top Major Event Match")
    
    try:
        if isinstance(major_event, dict) and major_event:
            col_m1, col_m2 = st.columns(2)
            
            # Date Handling
            ai_date = major_event.get("predicted_event_date")
            if isinstance(ai_date, str):
                try:
                    ai_date = datetime.datetime.strptime(ai_date, "%Y-%m-%d").date()
                except:
                    ai_date = datetime.date.today()
            elif not isinstance(ai_date, datetime.date):
                ai_date = datetime.date.today()
                
            ai_date_str = ai_date.strftime("%Y-%m-%d")
            
            with col_m1:
                st.success(f"#### {major_event.get('event_name', 'N/A')}")
                st.caption(f"Category: {major_event.get('category', 'N/A')}  •  Type: Major Event")
                st.metric("Recommendation Match Score", f"{major_event.get('final_score', 92.0):.1f}")
            with col_m2:
                st.write("**Operational Intelligence:**")
                st.markdown(f"* **AI Suggested Date:** {major_event.get('formatted_event_date', ai_date_str)}")
                st.markdown(f"* **Predicted Turnout:** {expected_turnout:.1f}%")
                st.markdown(f"* **Suggested Budget:** INR {major_event.get('cost_estimate', 5000.0)}")
                st.markdown(f"* **Vendors Needed:** {major_event.get('recommended_vendors', 'Band, Sound, Catering')}")
                
            # Date Customizer and Approval
            c_d1, c_d2 = st.columns(2)
            with c_d1:
                sched_date = st.date_input("Schedule Date", value=ai_date, key="major_sched_date")
            with c_d2:
                st.write("")
                st.write("")
                if st.button("👍 Approve Major Event", key="approve_major_btn", type="primary", use_container_width=True):
                    from integrations.calendar_db import save_calendar_event, save_recommendation_history
                    
                    event_dict = {
                        "Event Name": major_event.get("event_name", "Major Event"),
                        "Property": selected_property,
                        "Category": major_event.get("category", "Social"),
                        "Date": sched_date.strftime("%Y-%m-%d"),
                        "Time": "18:00",
                        "Status": "Approved",
                        "Event Type": "Major",
                        "Budget Estimate": safe_float(major_event.get("cost_estimate"), 5000.0),
                        "Ticket Recommendation": "Yes" if major_event.get("ticket_eligible") == "Yes" else "No",
                        "Assigned Vendors": major_event.get("recommended_vendors", ""),
                        "Assigned Materials": major_event.get("suggested_materials", ""),
                        "Notes": "Approved directly from Smart Recommendations.",
                        "Predicted Attendance": safe_int(major_event.get("predicted_attendance"), 50),
                        "Expected Occupancy": safe_float(major_event.get("predicted_turnout_rate"), 75.0),
                        "Recommendation Score": safe_float(major_event.get("final_score"), 90.0),
                        "Recommended Date": ai_date_str,
                        "Approved Date": datetime.date.today().strftime("%Y-%m-%d")
                    }
                    save_calendar_event(event_dict)
                    
                    # Log history
                    save_recommendation_history({
                        "Generated Time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Approved Time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Approver": "Community Manager",
                        "Property": selected_property,
                        "Event Name": major_event.get("event_name"),
                        "Category": major_event.get("category"),
                        "Event Type": "Major",
                        "AI Suggested Date": ai_date_str,
                        "Approved Date": sched_date.strftime("%Y-%m-%d"),
                        "Recommendation Score": safe_float(major_event.get("final_score"), 90.0),
                        "Status": "Approved"
                    })
                    st.success("Major event approved and scheduled!")
                    st.rerun()
    except Exception as e:
        st.warning("⚠ Unable to load this widget.")
        with st.expander("Debugging Details"):
            st.exception(e)

    # ===========================================================
    # SECTION 4: Minor Event Cards (Error Boundary)
    # ===========================================================
    st.write("---")
    st.write("### 🎭 Supporting Alternative Matches (Minor Events)")
    
    try:
        if minor_events:
            cols_minor = st.columns(len(minor_events))
            for idx, m_ev in enumerate(minor_events):
                if not isinstance(m_ev, dict):
                    continue
                
                # Date Handling
                m_ai_date = m_ev.get("predicted_event_date")
                if isinstance(m_ai_date, str):
                    try:
                        m_ai_date = datetime.datetime.strptime(m_ai_date, "%Y-%m-%d").date()
                    except:
                        m_ai_date = datetime.date.today()
                elif not isinstance(m_ai_date, datetime.date):
                    m_ai_date = datetime.date.today()
                    
                m_ai_date_str = m_ai_date.strftime("%Y-%m-%d")
                
                with cols_minor[idx]:
                    st.info(f"##### {m_ev.get('event_name', 'N/A')}")
                    st.caption(f"Category: {m_ev.get('category', 'N/A')}")
                    st.metric("Match Score", f"{m_ev.get('final_score', 80.0):.1f}")
                    st.markdown(f"**AI Suggested Date:** {m_ev.get('formatted_event_date', m_ai_date_str)}")
                    st.markdown(f"**Turnout:** {m_ev.get('predicted_turnout_rate', 70.0):.1f}%")
                    
                    m_sched_date = st.date_input("Schedule Date", value=m_ai_date, key=f"minor_sched_date_{idx}")
                    if st.button("👍 Approve Event", key=f"approve_minor_btn_{idx}", use_container_width=True):
                        from integrations.calendar_db import save_calendar_event, save_recommendation_history
                        
                        event_dict = {
                            "Event Name": m_ev.get("event_name", "Minor Event"),
                            "Property": selected_property,
                            "Category": m_ev.get("category", "Social"),
                            "Date": m_sched_date.strftime("%Y-%m-%d"),
                            "Time": "18:00",
                            "Status": "Approved",
                            "Event Type": "Minor",
                            "Budget Estimate": safe_float(m_ev.get("cost_estimate"), 3000.0),
                            "Ticket Recommendation": "Yes" if m_ev.get("ticket_eligible") == "Yes" else "No",
                            "Assigned Vendors": m_ev.get("recommended_vendors", ""),
                            "Assigned Materials": m_ev.get("suggested_materials", ""),
                            "Notes": "Approved directly from Smart Recommendations.",
                            "Predicted Attendance": safe_int(m_ev.get("predicted_attendance"), 30),
                            "Expected Occupancy": safe_float(m_ev.get("predicted_turnout_rate"), 65.0),
                            "Recommendation Score": safe_float(m_ev.get("final_score"), 80.0),
                            "Recommended Date": m_ai_date_str,
                            "Approved Date": datetime.date.today().strftime("%Y-%m-%d")
                        }
                        save_calendar_event(event_dict)
                        
                        # Log history
                        save_recommendation_history({
                            "Generated Time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "Approved Time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "Approver": "Community Manager",
                            "Property": selected_property,
                            "Event Name": m_ev.get("event_name"),
                            "Category": m_ev.get("category"),
                            "Event Type": "Minor",
                            "AI Suggested Date": m_ai_date_str,
                            "Approved Date": m_sched_date.strftime("%Y-%m-%d"),
                            "Recommendation Score": safe_float(m_ev.get("final_score"), 80.0),
                            "Status": "Approved"
                        })
                        st.success(f"Minor Event '{m_ev.get('event_name')}' approved!")
                        st.rerun()
    except Exception as e:
        st.warning("⚠ Unable to load this widget.")

    # ===========================================================
    # SECTION 5: Spacing Spans Timeline Preview (Error Boundary)
    # ===========================================================
    st.write("---")
    st.write("### 📅 Monthly Schedule Spacing & Spans Preview")
    
    try:
        timeline_rows = []
        if isinstance(major_event, dict) and major_event:
            timeline_rows.append({"Event": major_event.get("event_name"), "Type": "Major", "Date": major_event.get("formatted_event_date", "Day 10")})
        for m_ev in minor_events:
            if isinstance(m_ev, dict):
                timeline_rows.append({"Event": m_ev.get("event_name"), "Type": "Minor", "Date": m_ev.get("formatted_event_date", "Day 15")})
                
        if timeline_rows:
            st.dataframe(pd.DataFrame(timeline_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No schedule timeline rows parsed.")
    except Exception as e:
        st.warning("⚠ Unable to load this widget.")

    # ===========================================================
    # SECTION 6: Attendance Intelligence (Error Boundary)
    # ===========================================================
    st.write("---")
    st.write("### 📊 Turnout Intelligence")
    
    try:
        chart_data = []
        if isinstance(major_event, dict) and major_event:
            chart_data.append({"Event Name": major_event.get("event_name"), "Turnout Score %": safe_float(major_event.get("predicted_turnout_rate"), 75.0)})
        for m_ev in minor_events:
            if isinstance(m_ev, dict):
                chart_data.append({"Event Name": m_ev.get("event_name"), "Turnout Score %": safe_float(m_ev.get("predicted_turnout_rate"), 70.0)})
                
        if chart_data:
            st.bar_chart(pd.DataFrame(chart_data).set_index("Event Name"))
    except Exception as e:
        st.warning("⚠ Unable to load this widget.")

    # ===========================================================
    # SECTION 7: Strategic Focus Area Insights
    # ===========================================================
    st.write("---")
    st.write("### 💡 Recommended Focus Insights")
    
    col_ins1, col_ins2 = st.columns(2)
    with col_ins1:
        st.success("##### 💪 Strengths & Synergy\n* High alignment with resident interest profiles.\n* Weekend slot availability ensures low scheduling conflicts.")
    with col_ins2:
        st.warning("##### ⚠️ Risks & Considerations\n* Procurement lead times require immediate vendor reservation.\n* Verify weather constraints for outdoor segments.")

    # ===========================================================
    # SECTION 8: All Evaluated Candidate Rankings (Error Boundary)
    # ===========================================================
    st.write("---")
    st.write("### 📋 All Evaluated Event Candidates")
    
    try:
        candidates = rec_result.get("ranked_candidates", rec_result.get("candidates", []))
        if candidates:
            df_cand = pd.DataFrame(candidates)
            cols_to_show = [c for c in ["event_name", "category", "base_score", "final_score", "rank"] if safe_column_exists(df_cand, c)]
            
            display_cols = []
            for col in cols_to_show:
                display_cols.append(safe_get_column(df_cand, [col]))
                
            sort_col = safe_get_column(df_cand, ["final_score", "score"])
            if sort_col and sort_col in df_cand.columns:
                st.dataframe(df_cand[display_cols].sort_values(by=sort_col, ascending=False).head(10), use_container_width=True, hide_index=True)
            else:
                st.dataframe(df_cand[display_cols].head(10), use_container_width=True, hide_index=True)
        else:
            st.info("No candidates list returned.")
    except Exception as e:
        st.warning("⚠ Unable to load this widget.")
        with st.expander("Optional details"):
            st.write(str(e))

else:
    st.info("No recommendations generated for this session yet. Select a property and click 'Generate AI Recommendations' above to run the pipeline.")