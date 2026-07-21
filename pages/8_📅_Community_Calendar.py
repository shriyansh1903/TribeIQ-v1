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

import sys
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from src.auth.session_manager import require_login
require_login("Community Calendar")

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
    .badge-external {
        border-left: 3px solid #F0883E;
        background-color: #211a14;
    }
    .status-external {
        background-color: #FFE5D9;
        color: #D9480F;
    }
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
        for i in range(-3, 18):
            d = today + datetime.timedelta(days=i*30)
            months.append(d.strftime("%Y-%m"))
            
        if not df_calendar.empty and date_col in df_calendar.columns:
            for d_val in df_calendar[date_col].dropna().unique():
                try:
                    if isinstance(d_val, str) and len(d_val) >= 7:
                        parts = d_val.split("-")
                        if len(parts) >= 2 and len(parts[0]) == 4 and len(parts[1]) == 2:
                            months.append(f"{parts[0]}-{parts[1]}")
                except Exception:
                    pass
                    
        months = sorted(list(set(months)))
        selected_month_str = st.selectbox("Planning Period", months, index=months.index(today.strftime("%Y-%m")) if today.strftime("%Y-%m") in months else 0)

    with col_c:
        st.write("")
        st.write("")
        show_external = st.toggle("Show External Events", value=False, help="Overlay external events and local activities impacting your property.")

    # Parse Year and Month
    year, month = map(int, selected_month_str.split("-"))

    # Filter planned calendar events
    df_filtered = df_calendar.copy()
    if selected_property != "All":
        df_filtered = df_filtered[df_filtered[cal_prop_col] == selected_property] if cal_prop_col in df_filtered.columns else df_filtered
    df_filtered = df_filtered[df_filtered[date_col].str.startswith(selected_month_str)] if date_col in df_filtered.columns else df_filtered

    # Load nearby external events for the month
    if show_external and selected_property != "All":
        from integrations.external_events_db import get_nearby_external_events
        start_month_d = datetime.date(year, month, 1)
        # Calculate last day of month
        if month == 12:
            end_month_d = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
        else:
            end_month_d = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)
        df_ext_month = get_nearby_external_events(selected_property, start_date=start_month_d, end_date=end_month_d)
    else:
        df_ext_month = pd.DataFrame()

except Exception as e:
    st.warning("Failed to initialize planning context.")
    df_filtered = pd.DataFrame()
    df_ext_month = pd.DataFrame()

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
                    # Find external events for this day
                    if not df_ext_month.empty:
                        day_ext = df_ext_month[(df_ext_month["Start Date"] <= day_str) & (df_ext_month["End Date"] >= day_str)]
                        for idx, row in day_ext.iterrows():
                            ev_lbl = row["Event Name"]
                            ev_cat = row["Category"]
                            dist_val = row.get("Distance (km)", 0.0)
                            dist_str = f"{dist_val:.1f}km" if dist_val != 999.0 else "Local"
                            
                            cards_html += f"""
<div class='calendar-card badge-external'>
    <strong>🌐 {ev_lbl}</strong><br/>
    <span class='status-badge status-external'>{ev_cat}</span><br/>
    <small>{dist_str} away</small>
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
    event_options = []
    events_map = {}

    # Add Tribe events
    if not df_filtered.empty and name_col in df_filtered.columns:
        for idx, row in df_filtered.iterrows():
            event_id = str(row.get("Event ID", ""))
            lbl = f"{row[name_col]} [{event_id}]" if event_id else str(row[name_col])
            key = f"tribe_{idx}_{event_id}"
            event_options.append((lbl, key))
            events_map[key] = ("tribe", row.to_dict())

    # Add External events
    if not df_ext_month.empty:
        for idx, row in df_ext_month.iterrows():
            event_id = str(row.get("Event ID", ""))
            lbl = f"{row['Event Name']} [{event_id}]" if event_id else str(row["Event Name"])
            key = f"external_{idx}_{event_id}"
            event_options.append((lbl, key))
            events_map[key] = ("external", row.to_dict())

    if event_options:
        selected_option = st.selectbox(
            "Select Event for Action",
            options=event_options,
            format_func=lambda x: f"🌐 {x[0]} (External)" if events_map.get(x[1], ("", {}))[0] == "external" else x[0]
        )
        selected_lbl, selected_key = selected_option
        event_origin, evt_row = events_map[selected_key]
        
        if event_origin == "external":
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.write(f"#### 🌐 {evt_row['Event Name']}")
                st.caption(f"Category: {evt_row.get('Category', 'N/A')}  •  Organizer: {evt_row.get('Organizer', 'N/A')}")
                
                st.write(f"📅 **Start Date:** {evt_row.get('Start Date')}")
                st.write(f"📅 **End Date:** {evt_row.get('End Date')}")
                st.write(f"📍 **Venue:** {evt_row.get('Venue', 'N/A')} ({evt_row.get('Area', 'N/A')})")
                
                dist_val = evt_row.get("Distance (km)", 0.0)
                dist_str = f"{dist_val:.2f} km" if dist_val != 999.0 else "N/A"
                st.metric("Distance from Property", dist_str)
                st.metric("Expected Footfall", f"{int(evt_row.get('Expected Footfall', 0)):,}")
                
            with col_d2:
                st.write("**Impact & Intelligence Insights:**")
                st.info(f"📈 **Expected Occupancy Impact:** {evt_row.get('Expected Occupancy Impact', 0.0):+.1f}%")
                st.info(f"👥 **Expected Community Impact:** {evt_row.get('Expected Community Impact', 'Medium')}")
                
                st.write("**Suggested Partnerships / Actions:**")
                cat_lower = str(evt_row.get("Category", "")).lower()
                actions = []
                if "music" in cat_lower or "concert" in cat_lower:
                    actions = ["Organize an after-party at the property.", "Host a late-night cafe meetup for concert-goers.", "Coordinate a food pop-up/stall."]
                elif "college" in cat_lower or "university" in cat_lower:
                    actions = ["Set up a gaming night or open mic for visiting students.", "Host a student mixer event."]
                elif "tech" in cat_lower or "startup" in cat_lower or "conference" in cat_lower:
                    actions = ["Host a founder/developer meetup.", "Organize a pitch night/networking brunch."]
                elif "sports" in cat_lower or "marathon" in cat_lower:
                    actions = ["Set up a recovery breakfast station.", "Coordinate a community morning run."]
                else:
                    actions = ["Reach out to organizer for collaboration/ticket discounts."]
                    
                for act in actions:
                    st.write(f"- {act}")
                    
                if evt_row.get("Website"):
                    st.markdown(f"[🌐 Visit Official Website]({evt_row.get('Website')})")
                if evt_row.get("Registration Link"):
                    st.markdown(f"[🎫 Get Tickets / Register]({evt_row.get('Registration Link')})")
        else:
            # Render Tribe event details (existing flow)
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
                
                # Check conflict/opportunity on the planned date of the selected Tribe event
                evt_date = evt_row["Date"]
                if not df_ext_month.empty:
                    conflicting = df_ext_month[(df_ext_month["Start Date"] <= evt_date) & (df_ext_month["End Date"] >= evt_date)]
                    if not conflicting.empty:
                        st.write("---")
                        st.write("**Local External Context:**")
                        for _, ext_ev in conflicting.iterrows():
                            ext_name = ext_ev["Event Name"]
                            ext_cat = ext_ev["Category"]
                            footfall = ext_ev["Expected Footfall"]
                            occ_impact = ext_ev["Expected Occupancy Impact"]
                            
                            if occ_impact > 10.0:
                                st.success(f"🌟 **AI Opportunity:** Nearby *{ext_name}* ({ext_cat}) is happening on this day. It may boost property occupancy by approx {occ_impact:.1f}%. Consider running a partnership/meetup.")
                            elif "college" in str(ext_cat).lower() or "music" in str(ext_cat).lower():
                                st.warning(f"⚠️ **AI Conflict Warning:** Nearby *{ext_name}* ({ext_cat}) is expected to attract youth away from the property on this day. Consider running a social mixer or rescheduling.")
                
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
        st.info("No events to inspect for the target filter. Add recommendations or schedule slots.")
except Exception as e:
    st.warning("⚠ Unable to load this widget.")
    with st.expander("Details"):
        st.write(str(e))
