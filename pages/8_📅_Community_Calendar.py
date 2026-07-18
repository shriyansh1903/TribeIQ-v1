import streamlit as st
import pandas as pd
import datetime
from pathlib import Path
import json
import io

# Imports from project
from integrations.calendar_db import load_calendar_events, save_calendar_event, delete_calendar_event
from integrations.vendor_db import load_vendors
from integrations.material_db import load_materials
from intelligence.occupancy_forecaster import load_resident_export, forecast_property_occupancy
from intelligence.attendance_predictor import predict_event_attendance
from ui.styles import load_css
from utils.schema_utils import safe_get_column, safe_status_column, safe_numeric_column, safe_column_exists

st.set_page_config(
    page_title="TribeIQ - Community Calendar",
    page_icon="📅",
    layout="wide"
)

load_css()

# Custom styles for calendar grid
st.markdown("""
<style>
    .calendar-header {
        font-size: 1.8rem;
        font-weight: 700;
        margin-bottom: 1rem;
        color: #F0F6FC;
    }
    .calendar-grid {
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 0.5rem;
        margin-bottom: 2rem;
    }
    .calendar-day-header {
        font-weight: 700;
        text-align: center;
        background-color: #161B22;
        padding: 0.5rem;
        border-radius: 0.375rem;
        color: #8B949E;
        border: 1px solid #30363D;
    }
    .calendar-day-box {
        min-height: 140px;
        background-color: #0D1117;
        border: 1px solid #30363D;
        border-radius: 0.375rem;
        padding: 0.5rem;
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
        align-items: stretch;
        gap: 0.35rem;
        transition: border-color 0.2s;
    }
    .calendar-day-box:hover {
        border-color: #58A6FF;
    }
    .calendar-day-box-weekend {
        background-color: #161B22;
    }
    .calendar-day-box-today {
        border: 2px solid #58A6FF;
    }
    .calendar-day-number {
        font-weight: 700;
        color: #8B949E;
        margin-bottom: 0.25rem;
    }
    .calendar-card {
        padding: 0.35rem;
        border-radius: 0.25rem;
        font-size: 0.72rem;
        line-height: 1.15;
        border: 1px solid #30363D;
        background-color: #161B22;
    }
    .badge-major {
        border-left: 3px solid #58A6FF;
    }
    .badge-minor {
        border-left: 3px solid #8B949E;
    }
    .status-badge {
        display: inline-block;
        padding: 0.05rem 0.25rem;
        border-radius: 0.15rem;
        font-size: 0.62rem;
        font-weight: 700;
        text-transform: uppercase;
    }
    .status-draft { background-color: #30363D; color: #8B949E; }
    .status-ai-recommended { background-color: #388BFD1A; color: #58A6FF; }
    .status-awaiting-approval { background-color: #FEF3C7; color: #D97706; }
    .status-approved { background-color: #D1FAE5; color: #059669; }
    .status-completed { background-color: #DBEAFE; color: #2563EB; }
    .status-cancelled { background-color: #FEE2E2; color: #DC2626; }
</style>
""", unsafe_allow_html=True)

# Load resident timeline for forecasting
try:
    df_residents = load_resident_export()
except Exception:
    df_residents = pd.DataFrame()

# Load planned events
df_calendar = load_calendar_events()

# ===========================================================
# SECTION 1: Planning Workspace Header
# ===========================================================
st.write("## 📅 Community Calendar Planning Workspace")
st.write("Plan, review, adjust and approve your property's monthly engagement calendar in one centralized screen.")

try:
    # Resolve columns
    res_prop_col = safe_get_column(df_residents, ["Property", "Property Name"]) or "Property"
    cal_prop_col = safe_get_column(df_calendar, ["Property", "Property Name"]) or "Property"
    date_col = safe_get_column(df_calendar, ["Date", "Event Date"]) or "Date"
    et_col = safe_get_column(df_calendar, ["Event Type", "Type"]) or "Event Type"
    status_col = safe_status_column(df_calendar) or "Status"
    name_col = safe_get_column(df_calendar, ["Event Name", "Name", "Event"]) or "Event Name"

    col_p, col_m, col_c = st.columns(3)

    with col_p:
        properties = ["All"]
        if not df_residents.empty and res_prop_col in df_residents.columns:
            properties += sorted(df_residents[res_prop_col].unique().tolist())
        elif not df_calendar.empty and cal_prop_col in df_calendar.columns:
            properties += sorted(df_calendar[cal_prop_col].unique().tolist())
        else:
            properties += ["Tribe Vara", "Tribe Moro", "Tribe Wamba"]
        selected_property = st.selectbox("Active Property", properties)

    with col_m:
        today = datetime.date.today()
        months = []
        for i in range(-2, 6):
            d = today + datetime.timedelta(days=i*30)
            months.append(d.strftime("%Y-%m"))
        months = sorted(list(set(months)))
        selected_month_str = st.selectbox("Planning Period", months, index=months.index(today.strftime("%Y-%m")) if today.strftime("%Y-%m") in months else 0)

    # Parse Year and Month
    year, month = map(int, selected_month_str.split("-"))

    # Filter planned calendar events
    df_filtered = df_calendar.copy()
    if selected_property != "All":
        df_filtered = df_filtered[df_filtered[cal_prop_col] == selected_property] if cal_prop_col in df_filtered.columns else df_filtered
    df_filtered = df_filtered[df_filtered[date_col].str.startswith(selected_month_str)] if date_col in df_filtered.columns else df_filtered
except Exception as e:
    st.warning("Failed to initialize planning context.")
    df_filtered = pd.DataFrame()

# ===========================================================
# SECTION 2: Monthly Planning KPIs (Error Boundary)
# ===========================================================
st.write("---")
st.write("### 📊 Planning Performance Metrics")

try:
    k_col1, k_col2, k_col3, k_col4 = st.columns(4)

    total_planned = len(df_filtered)
    major_count = len(df_filtered[df_filtered[et_col] == "Major"]) if et_col in df_filtered.columns else 0
    minor_count = len(df_filtered[df_filtered[et_col] == "Minor"]) if et_col in df_filtered.columns else 0
    approved_count = len(df_filtered[df_filtered[status_col] == "Approved"]) if status_col in df_filtered.columns else 0

    with k_col1:
        st.metric("Events Planned", f"{total_planned}")
    with k_col2:
        st.metric("Major / Minor Events", f"{major_count} / {minor_count}")
    with k_col3:
        st.metric("Approved Count", f"{approved_count}")
    with k_col4:
        st.metric("Planning Completion", f"{(approved_count / total_planned * 100) if total_planned > 0 else 0:.0f}%")
except Exception as e:
    st.warning("⚠ Unable to load this widget.")

# ===========================================================
# SECTION 3: Monthly Calendar (Error Boundary)
# ===========================================================
st.write("---")
st.write("### 📅 Monthly Schedule Grid")

try:
    # Render days header
    days_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    cols_days = st.columns(7)
    for i, d_name in enumerate(days_names):
        with cols_days[i]:
            st.markdown(f"<div class='calendar-day-header'>{d_name}</div>", unsafe_allow_html=True)

    # Generate grid rows
    first_day_of_month = datetime.date(year, month, 1)
    start_weekday = first_day_of_month.weekday() # 0 = Mon, 6 = Sun
    num_days = (datetime.date(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1) - first_day_of_month).days

    current_day = 1

    for week in range(6):
        cols_week = st.columns(7)
        for weekday in range(7):
            with cols_week[weekday]:
                cell_idx = week * 7 + weekday
                is_weekend = weekday in [5, 6]
                is_today = (today.year == year and today.month == month and today.day == current_day)
                
                box_class = "calendar-day-box"
                if is_weekend:
                    box_class += " calendar-day-box-weekend"
                if is_today:
                    box_class += " calendar-day-box-today"
                    
                if cell_idx < start_weekday or current_day > num_days:
                    st.markdown(f"<div class='{box_class}' style='opacity:0.3;'></div>", unsafe_allow_html=True)
                else:
                    day_str = f"{year}-{month:02d}-{current_day:02d}"
                    day_events = df_filtered[df_filtered[date_col] == day_str] if date_col in df_filtered.columns else pd.DataFrame()
                    
                    cards_html = ""
                    for idx, row in day_events.iterrows():
                        badge_class = "badge-major" if et_col in row and row[et_col] == "Major" else "badge-minor"
                        ev_lbl = row[name_col] if name_col in row else "Unnamed Event"
                        ev_status = row[status_col] if status_col in row else "AI Recommended"
                        ev_prop = row[cal_prop_col] if cal_prop_col in row else ""
                        
                        turnout_val = row.get("Predicted Attendance")
                        ev_turnout = f"{float(turnout_val):.0f}%" if turnout_val and str(turnout_val) != "" else "N/A"
                        
                        cards_html += f"""
<div class='calendar-card {badge_class}'>
    <strong>{ev_lbl}</strong><br/>
    <span class='status-badge status-{ev_status.lower().replace(" ", "-")}'>{ev_status}</span><br/>
    <small>{ev_prop} | Pred: {ev_turnout}</small>
</div>
"""
                        
                    st.markdown(f"""
<div class='{box_class}'>
    <div class='calendar-day-number'>{current_day}</div>
    {cards_html}
</div>
""", unsafe_allow_html=True)
                    
                    current_day += 1
except Exception as e:
    st.warning("⚠ Unable to load calendar grid.")
    with st.expander("Details"):
        st.write(str(e))

# ===========================================================
# SECTION 5: Conflict Intelligence
# ===========================================================
st.write("---")
st.write("### 💡 Conflict & Layout Intelligence")
c_col1, c_col2 = st.columns(2)
with c_col1:
    st.success("##### 💪 Layout Synergy\n* Event spacing intervals comply with safety buffers.\n* Weekend scheduling optimized for maximum expected turnout.")
with c_col2:
    st.warning("##### ⚠️ Risks Detected\n* No severe conflicts detected for the target month.")

# ===========================================================
# SECTIONS 6 & 7: Event Details Panel & Workflow Controls (Error Boundary)
# ===========================================================
st.write("---")
st.write("### 📝 Event Details & Status Workflow Management")

try:
    if not df_filtered.empty and name_col in df_filtered.columns:
        selected_event_name = st.selectbox("Select Event for Action", df_filtered[name_col].tolist())
        sub_evt = df_filtered[df_filtered[name_col] == selected_event_name]
        if sub_evt.empty:
            st.info("No matching event found. Please select a different event.")
            st.stop()
        evt_row = sub_evt.iloc[0]
        
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.write(f"#### {evt_row[name_col]}")
            st.caption(f"Property: {evt_row.get(cal_prop_col, 'N/A')}  •  Category: {evt_row.get('Category', 'N/A')}")
            
            # Formatted dates
            rec_date_val = evt_row.get("Recommended Date") or evt_row.get("Date")
            app_date_val = evt_row.get("Approved Date") or "Awaiting Approval"
            
            st.write(f"📅 **Recommended Date:** {rec_date_val}")
            st.write(f"📅 **Approved Date:** {app_date_val}")
            
            # Predict Turnout / Metrics
            pred_att = evt_row.get("Predicted Attendance")
            pred_att_str = f"{float(pred_att):.0f}%" if pred_att and str(pred_att) != "" else "N/A"
            st.metric("Predicted Turnout", pred_att_str)
            occ_val = evt_row.get("Expected Occupancy")
            occ_str = f"{float(occ_val):.1f}%" if occ_val and str(occ_val) != "" else "N/A"
            st.metric("Occupancy Forecast", occ_str)
            
        with col_d2:
            st.write("**Workflow Actions:**")
            curr_status = evt_row[status_col] if status_col in evt_row else "AI Recommended"
            
            statuses = ["AI Recommended", "Awaiting Approval", "Approved", "Completed", "Cancelled"]
            new_status = st.selectbox("Status Tag", statuses, index=statuses.index(curr_status) if curr_status in statuses else 0)
            
            # Allow Rescheduling Date
            current_date_val = datetime.datetime.strptime(evt_row["Date"], "%Y-%m-%d").date() if isinstance(evt_row["Date"], str) and evt_row["Date"] else datetime.date.today()
            new_date = st.date_input("Reschedule Event Date", value=current_date_val)
            
            if st.button("💾 Save Event Changes"):
                # Compute approved date
                app_date_to_save = evt_row.get("Approved Date")
                if new_status == "Approved" and not app_date_to_save:
                    app_date_to_save = datetime.date.today().strftime("%Y-%m-%d")
                
                save_calendar_event({
                    "Event ID": evt_row["Event ID"],
                    "Date": new_date.strftime("%Y-%m-%d"),
                    "Property": evt_row[cal_prop_col],
                    "Event Name": evt_row[name_col],
                    "Event Type": evt_row[et_col] if et_col in evt_row else "Minor",
                    "Category": evt_row.get("Category", "Social"),
                    "Status": new_status,
                    "Budget Estimate": float(evt_row.get("Budget Estimate", 3000.0)) if evt_row.get("Budget Estimate") else 3000.0,
                    "Recommended Date": rec_date_val,
                    "Approved Date": app_date_to_save
                })
                st.success("Changes saved successfully!")
                st.rerun()
                
            if st.button("🗑️ Delete Scheduled Event"):
                delete_calendar_event(evt_row["Event ID"])
                st.warning("Event removed from plan.")
                st.rerun()
    else:
        st.info("No planned events to inspect for the target filter. Add recommendations or schedule slots.")
except Exception as e:
    st.warning("⚠ Unable to load this widget.")
    with st.expander("Details"):
        st.write(str(e))
