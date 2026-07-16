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
        color: #1E293B;
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
        background-color: #F1F5F9;
        padding: 0.5rem;
        border-radius: 0.375rem;
        color: #475569;
    }
    .calendar-day-box {
        min-height: 120px;
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 0.5rem;
        padding: 0.5rem;
        position: relative;
    }
    .calendar-day-number {
        font-weight: 700;
        color: #64748B;
        margin-bottom: 0.35rem;
    }
    .calendar-card {
        padding: 0.4rem;
        border-radius: 0.375rem;
        font-size: 0.8rem;
        margin-bottom: 0.3rem;
        color: #FFFFFF;
        cursor: pointer;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
        font-weight: 500;
    }
    .badge-major { background-color: #F97316; border-left: 3px solid #C2410C; } /* Major Event - Orange */
    .badge-minor { background-color: #64748B; border-left: 3px solid #334155; } /* Minor Event - Gray/blue */
    .badge-ticketed { background-color: #10B981; border-left: 3px solid #047857; } /* Ticketed - Green */
    .badge-flea { background-color: #EC4899; border-left: 3px solid #BE185D; } /* Flea Market - Pink */
    .badge-workshop { background-color: #06B6D4; border-left: 3px solid #0E7490; } /* Workshop - Cyan */
    .badge-entertainment { background-color: #EF4444; border-left: 3px solid #B91C1C; } /* Entertainment - Red */
    .badge-sports { background-color: #3B82F6; border-left: 3px solid #1D4ED8; } /* Sports - Blue */
    .badge-community { background-color: #8B5CF6; border-left: 3px solid #6D28D9; } /* Community - Indigo */
    
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
    
    .summary-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 0.5rem;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    }
</style>
""", unsafe_allow_html=True)

st.title("📅 Community Calendar Workspace")
st.write("Plan, review, adjust and approve your property's monthly engagement calendar in one centralized screen.")

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
# Filters Section
# ===========================================================
col_p, col_m, col_c, col_s, col_t, col_type = st.columns(6)

with col_p:
    properties = ["All"]
    if not df_residents.empty and "Property" in df_residents.columns:
        properties += sorted(df_residents["Property"].unique().tolist())
    elif not df_calendar.empty and "Property" in df_calendar.columns:
        properties += sorted(df_calendar["Property"].unique().tolist())
    else:
        properties += ["Tribe Moro", "Tribe Student", "Tribe Suite"]
    selected_property = st.selectbox("Property", properties)

with col_m:
    # Build list of months
    today = datetime.date.today()
    months = []
    for i in range(-2, 6):
        d = today + datetime.timedelta(days=i*30)
        months.append(d.strftime("%Y-%m"))
    months = sorted(list(set(months)))
    selected_month_str = st.selectbox("Month", months, index=months.index(today.strftime("%Y-%m")) if today.strftime("%Y-%m") in months else 0)
    year_val, month_val = map(int, selected_month_str.split("-"))

with col_c:
    categories = ["All"]
    if not df_calendar.empty:
        categories += sorted(df_calendar["Category"].unique().tolist())
    else:
        categories += ["Flea Market", "Food & Beverage", "Retail", "Entertainment", "Community", "Sports", "Workshops"]
    categories = list(set(categories))
    selected_category = st.selectbox("Event Category", categories)

with col_s:
    statuses = ["All", "Draft", "Proposed", "Approved", "Completed", "Cancelled"]
    selected_status = st.selectbox("Status", statuses)

with col_t:
    ticketing = ["All", "Ticketed", "Free"]
    selected_ticket = st.selectbox("Ticket Preference", ticketing)

with col_type:
    event_types = ["All", "Major", "Minor"]
    selected_type = st.selectbox("Event Type", event_types)

# Apply filters
df_filtered = df_calendar.copy()

if not df_filtered.empty:
    # Filter by property
    if selected_property != "All":
        df_filtered = df_filtered[df_filtered["Property"] == selected_property]
    
    # Filter by month/year
    df_filtered["Date"] = pd.to_datetime(df_filtered["Date"])
    df_filtered = df_filtered[(df_filtered["Date"].dt.year == year_val) & (df_filtered["Date"].dt.month == month_val)]
    
    # Filter by category
    if selected_category != "All":
        df_filtered = df_filtered[df_filtered["Category"] == selected_category]
        
    # Filter by status
    if selected_status != "All":
        df_filtered = df_filtered[df_filtered["Status"] == selected_status]
        
    # Filter by ticketing
    if selected_ticket == "Ticketed":
        df_filtered = df_filtered[df_filtered["Ticket Recommendation"] == "Ticketed"]
    elif selected_ticket == "Free":
        df_filtered = df_filtered[df_filtered["Ticket Recommendation"] == "Free"]
        
    # Filter by major/minor
    if selected_type != "All":
        df_filtered = df_filtered[df_filtered["Event Type"] == selected_type]

# ===========================================================
# Metrics / Month Summary Cards
# ===========================================================
st.write("---")
st.write("### 📊 Month Summary")

planned_count = len(df_filtered)
major_count = len(df_filtered[df_filtered["Event Type"] == "Major"])
minor_count = len(df_filtered[df_filtered["Event Type"] == "Minor"])

expected_attendance = 0
expected_revenue = 0
expected_budget = 0
avg_occupancy = 0.0

if not df_filtered.empty:
    expected_attendance = int(df_filtered["Predicted Attendance"].apply(lambda x: float(x) if x != "" else 0.0).sum())
    expected_budget = float(df_filtered["Budget Estimate"].apply(lambda x: float(x) if x != "" else 0.0).sum())
    
    # Let's check expected revenue (e.g. ticket price * attendance if ticketed)
    expected_revenue = 0.0  # Optional fallback
    
    occupancies = df_filtered["Expected Occupancy"].apply(lambda x: float(x) if x != "" else 0.0)
    if not occupancies.empty and occupancies.sum() > 0:
        avg_occupancy = occupancies.mean()

m_col1, m_col2, m_col3, m_col4, m_col5, m_col6, m_col7 = st.columns(7)

with m_col1:
    st.markdown(f'<div class="summary-card"><div class="score-label">EVENTS PLANNED</div><div class="score-value" style="font-size:1.6rem;">{planned_count}</div></div>', unsafe_allow_html=True)
with m_col2:
    st.markdown(f'<div class="summary-card"><div class="score-label">MAJOR EVENTS</div><div class="score-value" style="font-size:1.6rem; color:#F97316;">{major_count}</div></div>', unsafe_allow_html=True)
with m_col3:
    st.markdown(f'<div class="summary-card"><div class="score-label">MINOR EVENTS</div><div class="score-value" style="font-size:1.6rem; color:#64748B;">{minor_count}</div></div>', unsafe_allow_html=True)
with m_col4:
    st.markdown(f'<div class="summary-card"><div class="score-label">EXP. ATTENDANCE</div><div class="score-value" style="font-size:1.6rem;">{expected_attendance:,}</div></div>', unsafe_allow_html=True)
with m_col5:
    st.markdown(f'<div class="summary-card"><div class="score-label">EXP. BUDGET</div><div class="score-value" style="font-size:1.6rem; color:#EF4444;">₹{expected_budget:,.0f}</div></div>', unsafe_allow_html=True)
with m_col6:
    st.markdown(f'<div class="summary-card"><div class="score-label">EXP. REVENUE</div><div class="score-value" style="font-size:1.6rem; color:#10B981;">₹{expected_revenue:,.0f}</div></div>', unsafe_allow_html=True)
with m_col7:
    st.markdown(f'<div class="summary-card"><div class="score-label">AVG OCCUPANCY</div><div class="score-value" style="font-size:1.6rem; color:#3B82F6;">{avg_occupancy:.1f}%</div></div>', unsafe_allow_html=True)

# ===========================================================
# Calendar Days Rendering
# ===========================================================
st.write("---")

# Find the start and end of the selected month
import calendar
month_days = calendar.monthrange(year_val, month_val)[1]
first_day_weekday = calendar.monthrange(year_val, month_val)[0] # 0 = Monday, 6 = Sunday

# Shift so Sunday is 0 or Monday is 0. Let's make Monday = 0
weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Render Weekdays Header
st.write("#### 📆 Monthly Grid")
cols_headers = st.columns(7)
for idx, day_name in enumerate(weekdays):
    with cols_headers[idx]:
        st.markdown(f'<div class="calendar-day-header">{day_name}</div>', unsafe_allow_html=True)

# Render Days Grid
day_counter = 1
finished = False

# We will group filtered events by date day
events_by_day = {}
if not df_filtered.empty:
    for idx, row in df_filtered.iterrows():
        day_num = int(row["Date"].day)
        if day_num not in events_by_day:
            events_by_day[day_num] = []
        events_by_day[day_num].append(row)

# Fill empty slots before day 1
current_week_cols = st.columns(7)
col_idx = 0
for i in range(first_day_weekday):
    with current_week_cols[col_idx]:
        st.markdown('<div class="calendar-day-box" style="background-color:#F8FAFC; opacity:0.5;"></div>', unsafe_allow_html=True)
    col_idx += 1

while not finished:
    with current_week_cols[col_idx]:
        # Box header
        day_events = events_by_day.get(day_counter, [])
        events_html = ""
        for ev in day_events:
            ev_id = ev["Event ID"]
            name = ev["Event Name"]
            ev_type = ev["Event Type"]
            cat = ev["Category"]
            ticket = ev["Ticket Recommendation"]
            status = ev["Status"]
            
            # Badge styles
            badge_class = "badge-minor"
            if ev_type == "Major":
                badge_class = "badge-major"
            elif ticket == "Ticketed":
                badge_class = "badge-ticketed"
            elif "flea" in cat.lower():
                badge_class = "badge-flea"
            elif "workshop" in cat.lower():
                badge_class = "badge-workshop"
            elif "entertainment" in cat.lower() or "show" in cat.lower() or "mic" in cat.lower():
                badge_class = "badge-entertainment"
            elif "sports" in cat.lower() or "tournament" in cat.lower():
                badge_class = "badge-sports"
            elif "community" in cat.lower() or "social" in cat.lower():
                badge_class = "badge-community"
                
            status_style = "status-draft"
            if status.lower() == "proposed":
                status_style = "status-proposed"
            elif status.lower() == "approved":
                status_style = "status-approved"
            elif status.lower() == "completed":
                status_style = "status-completed"
            elif status.lower() == "cancelled":
                status_style = "status-cancelled"
                
            events_html += f"""
            <div class="calendar-card {badge_class}">
                <strong>{name}</strong><br>
                <span class="status-badge {status_style}">{status}</span>
            </div>
            """
            
        st.markdown(f"""
        <div class="calendar-day-box">
            <div class="calendar-day-number">{day_counter}</div>
            {events_html}
        </div>
        """, unsafe_allow_html=True)
        
    day_counter += 1
    col_idx += 1
    
    if day_counter > month_days:
        finished = True
        # Fill rest of the week
        while col_idx < 7:
            with current_week_cols[col_idx]:
                st.markdown('<div class="calendar-day-box" style="background-color:#F8FAFC; opacity:0.5;"></div>', unsafe_allow_html=True)
            col_idx += 1
            
    if col_idx == 7 and not finished:
        current_week_cols = st.columns(7)
        col_idx = 0

# ===========================================================
# Edit & Reschedule Side Panel / Control Section
# ===========================================================
st.write("---")
st.write("### ⚙️ Event Rescheduling & Planning Controls")

if df_calendar.empty:
    st.info("No planned events found. Generate recommendations first and save them to the calendar.")
else:
    event_titles = {row["Event ID"]: f"{row['Date']} | {row['Property']} | {row['Event Name']}" for idx, row in df_calendar.iterrows()}
    
    col_sel, col_action = st.columns([3, 1])
    with col_sel:
        selected_event_id = st.selectbox("Select Planned Event", list(event_titles.keys()), format_func=lambda x: event_titles[x])
        
    selected_row = df_calendar[df_calendar["Event ID"] == selected_event_id].iloc[0]
    
    # -------------------------------------------------------
    # Interactive Rescheduler / Drag & Drop Simulation
    # -------------------------------------------------------
    st.write("#### 📅 Reschedule Event")
    new_date = st.date_input("Target Execution Date", value=pd.to_datetime(selected_row["Date"]).date())
    new_time = st.text_input("Execution Time", value=selected_row["Time"])
    
    # Recalculations & AI Conflict Check
    date_str = new_date.strftime("%Y-%m-%d")
    property_name = selected_row["Property"]
    event_name = selected_row["Event Name"]
    category = selected_row["Category"]
    
    # Perform Live recalculation of occupancy and attendance
    recalc_occ = 0.0
    recalc_att = 0
    if not df_residents.empty:
        try:
            occ_res = forecast_property_occupancy(df_residents, property_name, date_str)
            recalc_occ = occ_res.get("occupancy_percent", 0.0)
            
            att_res = predict_event_attendance(df_residents, df_history, property_name, event_name, category, date_str)
            recalc_att = int(att_res.get("predicted_attendance", 0))
        except Exception:
            recalc_occ = float(selected_row["Expected Occupancy"] or 0.0)
            recalc_att = int(selected_row["Predicted Attendance"] or 0)
            
    # AI Conflict Checks
    warnings = []
    # 1. Duplicate dates check
    other_events_on_date = df_calendar[
        (df_calendar["Date"] == date_str) & 
        (df_calendar["Property"] == property_name) & 
        (df_calendar["Event ID"] != selected_event_id)
    ]
    if not other_events_on_date.empty:
        warnings.append(f"⚠️ **Duplicate Event Date**: Another event ('{other_events_on_date.iloc[0]['Event Name']}') is already planned on {date_str} for {property_name}.")
        
    # 2. Events too close together
    event_dates = pd.to_datetime(df_calendar[
        (df_calendar["Property"] == property_name) & 
        (df_calendar["Event ID"] != selected_event_id)
    ]["Date"])
    spacing_threshold = 5 if selected_row["Event Type"] == "Major" else 3
    too_close = False
    for ed in event_dates:
        days_diff = abs((pd.to_datetime(date_str) - ed).days)
        if days_diff < spacing_threshold:
            too_close = True
            break
    if too_close:
        warnings.append(f"⚠️ **Spacing Spacing Conflict**: Scheduled date {date_str} is within the {spacing_threshold}-day spacing buffer zone of another planned activity.")
        
    # 3. Low occupancy
    if recalc_occ < 75.0:
        warnings.append(f"⚠️ **Low Occupancy Forecast**: Forecasted occupancy on {date_str} is {recalc_occ:.1f}% (below 75.0% threshold). Consider rescheduling to a day with higher active resident population.")
        
    # 4. Weekend suitability
    day_of_week = pd.to_datetime(date_str).strftime("%A")
    weekend_categories = ["Sports", "Flea Market", "Workshops", "Entertainment"]
    if category in weekend_categories and day_of_week in ["Monday", "Tuesday", "Wednesday", "Thursday"]:
        warnings.append(f"⚠️ **Weekend Suitability**: '{event_name}' ({category}) typically performs much better on weekends, but is scheduled on a {day_of_week}.")
        
    # Suggest better date if conflicts exist
    if warnings:
        st.error("### ⚠️ AI Conflict Warnings detected")
        for w in warnings:
            st.markdown(w)
            
        # Find better date
        better_date_str = date_str
        max_occupancy = 0.0
        better_date_found = None
        
        # Look for dates within 7 days
        target_ts = pd.to_datetime(date_str)
        for offset in range(-7, 8):
            if offset == 0:
                continue
            cand_ts = target_ts + pd.Timedelta(days=offset)
            cand_str = cand_ts.strftime("%Y-%m-%d")
            
            # Check spacing or duplicate conflicts on candidate
            cand_duplicates = df_calendar[
                (df_calendar["Date"] == cand_str) & 
                (df_calendar["Property"] == property_name) & 
                (df_calendar["Event ID"] != selected_event_id)
            ]
            if not cand_duplicates.empty:
                continue
                
            try:
                c_occ = forecast_property_occupancy(df_residents, property_name, cand_str)
                c_occ_pct = c_occ.get("occupancy_percent", 0.0)
                if c_occ_pct > max_occupancy and c_occ_pct >= 75.0:
                    max_occupancy = c_occ_pct
                    better_date_found = cand_str
            except Exception:
                pass
                
        if better_date_found:
            st.info(f"💡 **Suggested Better Date**: {better_date_found} (Expected Occupancy: {max_occupancy:.1f}% with no schedule spacing conflicts)")
    else:
        st.success("✅ **AI Conflict Check Passed**: No scheduler conflicts found.")
        
    st.write("---")
    st.write("#### 📝 Edit Event Details")
    
    col_d1, col_d2 = st.columns(2)
    
    with col_d1:
        edit_name = st.text_input("Event Name", value=selected_row["Event Name"])
        edit_cat = st.selectbox("Category", ["Flea Market", "Food & Beverage", "Retail", "Entertainment", "Community", "Sports", "Workshops"], index=["Flea Market", "Food & Beverage", "Retail", "Entertainment", "Community", "Sports", "Workshops"].index(selected_row["Category"]) if selected_row["Category"] in ["Flea Market", "Food & Beverage", "Retail", "Entertainment", "Community", "Sports", "Workshops"] else 0)
        edit_type = st.selectbox("Event Type", ["Major", "Minor"], index=0 if selected_row["Event Type"] == "Major" else 1)
        edit_status = st.selectbox("Approval Workflow Status", ["Draft", "Proposed", "Approved", "Completed", "Cancelled"], index=["Draft", "Proposed", "Approved", "Completed", "Cancelled"].index(selected_row["Status"]) if selected_row["Status"] in ["Draft", "Proposed", "Approved", "Completed", "Cancelled"] else 0)
        edit_budget = st.number_input("Budget Estimate (INR)", value=float(selected_row["Budget Estimate"] or 5000))
        edit_ticket = st.selectbox("Ticket Recommendation", ["Free", "Ticketed"], index=0 if selected_row["Ticket Recommendation"] == "Free" else 1)
        
    with col_d2:
        vendors_df = load_vendors()
        vendor_names = sorted(vendors_df["Vendor Name"].tolist()) if not vendors_df.empty else []
        edit_vendors = st.multiselect("Assigned Vendors", vendor_names, default=[v.strip() for v in selected_row["Assigned Vendors"].split(",") if v.strip() in vendor_names])
        
        materials_df = load_materials()
        material_names = sorted(materials_df["Material Name"].unique().tolist()) if not materials_df.empty else []
        edit_materials = st.multiselect("Assigned Materials", material_names, default=[m.strip() for m in selected_row["Assigned Materials"].split(",") if m.strip() in material_names])
        
        edit_notes = st.text_area("Notes", value=selected_row["Notes"])
        
    if st.button("💾 Save Calendar Changes", type="primary", use_container_width=True):
        updated_event = {
            "Event ID": selected_event_id,
            "Event Name": edit_name,
            "Property": property_name,
            "Category": edit_cat,
            "Date": date_str,
            "Time": new_time,
            "Status": edit_status,
            "Event Type": edit_type,
            "Budget Estimate": edit_budget,
            "Ticket Recommendation": edit_ticket,
            "Assigned Vendors": ", ".join(edit_vendors),
            "Assigned Materials": ", ".join(edit_materials),
            "Notes": edit_notes,
            "Predicted Attendance": recalc_att,
            "Expected Occupancy": recalc_occ,
            "Recommendation Score": float(selected_row["Recommendation Score"] or 0.0)
        }
        save_calendar_event(updated_event)
        st.success("Successfully updated event calendar schedule and synchronized outputs!")
        st.rerun()

    if st.button("🗑️ Delete Planned Event", type="secondary", use_container_width=True):
        delete_calendar_event(selected_event_id)
        st.warning("Removed planned event from the calendar registry.")
        st.rerun()

# ===========================================================
# Exports Section
# ===========================================================
st.write("---")
st.write("### 📥 Export Calendar Worksheets")

col_ex1, col_ex2, col_ex3 = st.columns(3)

with col_ex1:
    if not df_filtered.empty:
        csv_data = df_filtered.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export Month to CSV",
            data=csv_data,
            file_name=f"tribeiq_calendar_{selected_month_str}.csv",
            mime="text/csv",
            use_container_width=True
        )

with col_ex2:
    if not df_filtered.empty:
        # Export to Excel
        output_buffer = io.BytesIO()
        with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
            df_filtered.to_excel(writer, index=False, sheet_name="Calendar Plans")
        excel_data = output_buffer.getvalue()
        st.download_button(
            label="📥 Export Month to Excel",
            data=excel_data,
            file_name=f"tribeiq_calendar_{selected_month_str}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

with col_ex3:
    # PDF printing option using browser context
    st.markdown("""
        <button onclick="window.print()" style="
            width: 100%;
            background-color: #3B82F6;
            color: white;
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 0.375rem;
            cursor: pointer;
            font-weight: 600;
            font-size: 1rem;
            text-align: center;
        ">📥 Print Calendar / Save to PDF</button>
    """, unsafe_allow_html=True)
