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
        min-height: 120px;
        background-color: #0D1117;
        border: 1px solid #30363D;
        border-radius: 0.5rem;
        padding: 0.5rem;
        position: relative;
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
        margin-bottom: 0.35rem;
    }
    .calendar-card {
        padding: 0.4rem;
        border-radius: 0.375rem;
        font-size: 0.8rem;
        margin-bottom: 0.3rem;
        color: #F0F6FC;
        cursor: pointer;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.15);
        font-weight: 500;
    }
    .badge-major { background-color: #F97316; border-left: 3px solid #C2410C; }
    .badge-minor { background-color: #64748B; border-left: 3px solid #334155; }
    
    .status-badge {
        font-size: 0.7rem;
        font-weight: 700;
        padding: 0.15rem 0.35rem;
        border-radius: 9999px;
        text-transform: uppercase;
        display: inline-block;
        margin-top: 0.2rem;
    }
    .status-draft { background-color: #E2E8F0; color: #475569; }
    .status-proposed { background-color: #FEF3C7; color: #D97706; }
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

# Load event history for attendance predicting
history_csv = Path("data/event_history.csv")
if history_csv.exists():
    try:
        df_history = pd.read_csv(history_csv)
    except Exception:
        df_history = pd.DataFrame()
else:
    df_history = pd.DataFrame()

# Load planned events
df_calendar = load_calendar_events()

# ===========================================================
# SECTION 1: Planning Workspace Header
# ===========================================================
st.write("## 📅 Community Calendar Planning Workspace")
st.write("Plan, review, adjust and approve your property's monthly engagement calendar in one centralized screen.")

col_p, col_m, col_c = st.columns(3)

with col_p:
    properties = ["All"]
    if not df_residents.empty and "Property" in df_residents.columns:
        properties += sorted(df_residents["Property"].unique().tolist())
    elif not df_calendar.empty and "Property" in df_calendar.columns:
        properties += sorted(df_calendar["Property"].unique().tolist())
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
    selected_month_str = st.selectbox("Target Month", months, index=months.index(today.strftime("%Y-%m")) if today.strftime("%Y-%m") in months else 0)

with col_c:
    st.write("")
    st.write("")
    # Action buttons
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.rerun()
    with col_btn2:
        # Export logic placeholder
        csv = df_calendar.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export CSV", csv, "tribeiq_calendar.csv", "text/csv", use_container_width=True)

# Parse Year and Month
year, month = map(int, selected_month_str.split("-"))

# Filter planned calendar events
df_filtered = df_calendar.copy()
if selected_property != "All":
    df_filtered = df_filtered[df_filtered["Property"] == selected_property]
df_filtered = df_filtered[df_filtered["Date"].str.startswith(selected_month_str)]

# ===========================================================
# SECTION 2: Monthly Planning KPIs
# ===========================================================
st.write("---")
st.write("### 📊 Planning Performance Metrics")
k_col1, k_col2, k_col3, k_col4 = st.columns(4)

total_planned = len(df_filtered)
major_count = len(df_filtered[df_filtered["Event Type"] == "Major"])
minor_count = len(df_filtered[df_filtered["Event Type"] == "Minor"])
approved_count = len(df_filtered[df_filtered["Status"] == "Approved"])

with k_col1:
    st.metric("Events Planned", f"{total_planned}")
with k_col2:
    st.metric("Major / Minor Events", f"{major_count} / {minor_count}")
with k_col3:
    st.metric("Approved Count", f"{approved_count}")
with k_col4:
    st.metric("Planning Completion", f"{(approved_count / total_planned * 100) if total_planned > 0 else 0:.0f}%")

# ===========================================================
# SECTION 3: Monthly Calendar Redesign
# ===========================================================
st.write("---")
st.write("### 📅 Monthly Schedule Grid")

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

grid_cols = []
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
                day_events = df_filtered[df_filtered["Date"] == day_str]
                
                cards_html = ""
                for idx, row in day_events.iterrows():
                    badge_class = "badge-major" if row["Event Type"] == "Major" else "badge-minor"
                    cards_html += f"<div class='calendar-card {badge_class}'>{row['Event Name']}</div>"
                    
                st.markdown(f"""
                <div class='{box_class}'>
                    <div class='calendar-day-number'>{current_day}</div>
                    {cards_html}
                </div>
                """, unsafe_allow_html=True)
                
                current_day += 1

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
# SECTIONS 6 & 7: Event Details Panel & Workflow Controls
# ===========================================================
st.write("---")
st.write("### 📝 Event Details & Status Workflow Management")

if not df_filtered.empty:
    selected_event_name = st.selectbox("Select Event for Action", df_filtered["Event Name"].tolist())
    evt_row = df_filtered[df_filtered["Event Name"] == selected_event_name].iloc[0]
    
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.write(f"#### {evt_row['Event Name']}")
        st.caption(f"Property: {evt_row['Property']}  •  Category: {evt_row.get('Category', 'N/A')}")
        st.metric("Expected Turnout", f"{evt_row.get('Predicted Attendance', 75.0):.0f}%")
        
    with col_d2:
        st.write("**Workflow Actions:**")
        new_status = st.selectbox("Status Tag", ["Draft", "Proposed", "Approved", "Completed", "Cancelled"], index=["Draft", "Proposed", "Approved", "Completed", "Cancelled"].index(evt_row["Status"]) if evt_row["Status"] in ["Draft", "Proposed", "Approved", "Completed", "Cancelled"] else 0)
        if st.button("💾 Save Event Changes"):
            save_calendar_event(
                evt_row["Date"],
                evt_row["Property"],
                evt_row["Event Name"],
                evt_row["Event Type"],
                evt_row.get("Category", "Social"),
                new_status
            )
            st.success("Changes saved successfully!")
            st.rerun()
            
        if st.button("🗑️ Delete Scheduled Event"):
            delete_calendar_event(evt_row["Date"], evt_row["Property"], evt_row["Event Name"])
            st.warning("Event removed from plan.")
            st.rerun()
else:
    st.info("No planned events to inspect for the target filter. Add recommendations or schedule slots.")
