import sys
from pathlib import Path
import datetime
from typing import List, Dict, Any, Optional
import pandas as pd
import streamlit as st

# ===========================================================
# Project Paths & Imports
# ===========================================================
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    from src.auth.session_manager import require_login, get_current_user
except ImportError:
    from auth.session_manager import require_login, get_current_user

require_login("Master Event Planner")


try:
    from src.ui_data_bridge import load_application_data
    from src.ui.styles import load_css
    from src.utils.schema_utils import safe_get_column, safe_status_column
    from src.services.master_planner_service import master_planner_service
except ImportError:
    from ui_data_bridge import load_application_data
    from ui.styles import load_css
    from utils.schema_utils import safe_get_column, safe_status_column
    from services.master_planner_service import master_planner_service

# Load CSS Theme
load_css()

# Fetch Calendar & Master Data
data = load_application_data() or {}
try:
    from src.integrations.calendar_db import load_calendar_events
    df_calendar = load_calendar_events()
except Exception as e:
    st.warning("⚠ Calendar data source temporarily unavailable.")
    df_calendar = pd.DataFrame()

# Get Current User Info
user_info = get_current_user() or {}
current_username = user_info.get("username", "Manager")

# Dynamic Department Sourcing (Task 1)
available_departments = master_planner_service.get_available_departments()

# ===========================================================
# Header & Navigation State
# ===========================================================
st.write("## 📋 Master Event Planner")
st.write("Centralized operational execution and workspace manager for approved community events.")

# Store selected event/workspace in session state
if "selected_planner_event_id" not in st.session_state:
    st.session_state["selected_planner_event_id"] = None

# If an event workspace is open, show back button
if st.session_state["selected_planner_event_id"]:
    if st.button("⬅ Back to All Events", key="back_to_events_btn"):
        st.session_state["selected_planner_event_id"] = None
        st.rerun()

# ===========================================================
# EVENT WORKSPACE VIEW
# ===========================================================
if st.session_state["selected_planner_event_id"]:
    selected_ev_id = st.session_state["selected_planner_event_id"]
    
    # Resolve event record from df_calendar
    event_record = {}
    if not df_calendar.empty:
        id_col = safe_get_column(df_calendar, ["Event ID", "ID", "id"]) or "Event ID"
        matched = df_calendar[df_calendar[id_col].astype(str) == str(selected_ev_id)]
        if not matched.empty:
            event_record = matched.iloc[0].to_dict()
    
    if not event_record:
        event_record = {
            "Event ID": selected_ev_id,
            "Event Name": "Approved Community Event",
            "Category": "Social",
            "Property": "All Properties",
            "Date": datetime.date.today().strftime("%Y-%m-%d"),
            "Status": "Approved"
        }
        
    workspace = master_planner_service.get_or_create_workspace(str(selected_ev_id), event_record, created_by=current_username)
    workspace_id = workspace["workspace_id"]
    
    st.write("---")
    st.write(f"### 🚀 Event Workspace: **{workspace.get('event_name', 'Event')}**")
    st.caption(f"Workspace ID: `{workspace_id}` | Property: **{workspace.get('property_name', workspace.get('property', 'N/A'))}** | Date: **{workspace.get('date', 'N/A')}** | Category: **{workspace.get('category', 'N/A')}** | Manager: **{workspace.get('community_manager', current_username)}**")

    # -----------------------------------------------------------
    # WORKSPACE SECTIONS EXACTLY AS SPECIFIED (1 to 6)
    # -----------------------------------------------------------
    
    # 1. OVERVIEW
    st.write("#### 1. 📌 Overview")
    col_ov1, col_ov2, col_ov3, col_ov4 = st.columns(4)
    with col_ov1:
        st.metric("Event Name", workspace.get("event_name", "N/A"))
    with col_ov2:
        st.metric("Category", workspace.get("category", "N/A"))
    with col_ov3:
        st.metric("Scheduled Date", workspace.get("date", "N/A"))
    with col_ov4:
        st.metric("Status", workspace.get("status", "Approved"))
        
    with st.expander("📝 Event Details & Operational Notes", expanded=True):
        st.write(f"**Budget Estimate:** ₹{event_record.get('Budget Estimate', 5000):,.0f}")
        st.write(f"**Assigned Vendors:** {event_record.get('Assigned Vendors', 'None / Local Team')}")
        st.write(f"**Assigned Materials:** {event_record.get('Assigned Materials', 'Standard Venue Inventory')}")
        st.write(f"**Created By:** {workspace.get('created_by', 'System')} on {workspace.get('created_at', 'N/A')[:10]}")
        st.write(f"**Last Updated:** {workspace.get('last_updated', 'N/A')[:19]}")

    # ===========================================================
    # AI EVENT PLANNING ASSISTANT INTELLIGENCE CARDS (FEATURES 1-9)
    # ===========================================================
    try:
        from src.intelligence.event_planning_ai import event_planning_ai
        
        ev_category = workspace.get("category", "Social")
        ev_name = workspace.get("event_name", "Event")
        ev_prop = workspace.get("property_name", workspace.get("property", "All Properties"))
        ev_date = workspace.get("date", datetime.date.today().strftime("%Y-%m-%d"))
        
        ai_summary = event_planning_ai.generate_planning_summary(ev_name, ev_category, ev_prop, ev_date)
        ai_resources = event_planning_ai.get_suggested_resources(ev_category)
        ai_risks = event_planning_ai.get_risk_checklist(ev_category)
        ai_insights = event_planning_ai.get_planning_insights(ev_category)
        past_events = event_planning_ai.find_similar_past_events(ev_name, ev_category, ev_prop)
        ai_confidence = event_planning_ai.get_planning_confidence_score(ev_category, len(past_events))
        
        with st.expander("🤖 AI Planning Assistant Insights & Risk Guidance", expanded=True):
            # Feature 1 & Feature 8: AI Summary & Confidence Score
            st.markdown(f"##### 🎯 AI Executive Briefing (Confidence: `{ai_confidence['confidence_level']}` - {ai_confidence['score']}%)")
            st.caption(f"💡 **Explainability:** {ai_confidence['reason']}")
            
            c_ai1, c_ai2 = st.columns(2)
            with c_ai1:
                st.write(f"• **Objective:** {ai_summary['objective']}")
                st.write(f"• **Target Audience:** {ai_summary['expected_audience']}")
                st.write(f"• **Timeline Guidance:** {ai_summary['preparation_timeline']}")
            with c_ai2:
                st.write(f"• **Est. Manpower:** {ai_summary['estimated_manpower']}")
                st.write(f"• **Expected Turnout:** {ai_summary['expected_attendance_range']}")
                st.write(f"• **Budget Window:** {ai_summary['recommended_budget_range']}")

            # Feature 6: Operational Planning Insights
            if ai_insights:
                st.markdown("##### 💡 Planning Insights")
                for ins in ai_insights:
                    st.info(f"**{ins['tag']}** — {ins['explanation']}")

            # Feature 4: Suggested Resources (Non-binding Recommendations)
            st.markdown("##### 🧰 AI Suggested Resources (Guidance Only)")
            c_res1, c_res2, c_res3, c_res4 = st.columns(4)
            with c_res1:
                st.write("**Typical Vendors:**")
                for v in ai_resources.get("vendors", []):
                    st.write(f"- {v}")
            with c_res2:
                st.write("**Recommended Materials:**")
                for m in ai_resources.get("materials", []):
                    st.write(f"- {m}")
            with c_res3:
                st.write("**Key Equipment:**")
                for eq in ai_resources.get("equipment", []):
                    st.write(f"- {eq}")
            with c_res4:
                st.write("**Est. Manpower:**")
                for mp in ai_resources.get("manpower", []):
                    st.write(f"- {mp}")

            # Feature 5: Risk Checklist
            st.markdown("##### ⚠️ Operational Risk Checklist")
            for r_idx, r_item in enumerate(ai_risks):
                chk_key = f"risk_chk_{workspace_id}_{r_idx}"
                st.checkbox(r_item["risk_item"], value=False, key=chk_key)

            # Feature 9: Similar Past Events
            if past_events:
                st.markdown("##### 📚 Similar Past Events History & Lessons")
                for pe in past_events:
                    st.write(f"• **{pe['event_name']}** ({pe['date']}) at {pe['property']} — Turnout: **{pe['actual_turnout']}**, Rating: ⭐ **{pe['rating']}**")
                    st.caption(f"  *Lesson Learned:* {pe['lessons_learned']}")

    except Exception as ex_ai:
        st.warning("⚠ AI Planning Assistant features temporarily unavailable.")
        with st.expander("Details"):
            st.write(str(ex_ai))

    # 2. AI TASK TEMPLATE & 4. USER ASSIGNMENTS (TASK MANAGEMENT)
    st.write("---")
    st.write("#### 2. 🤖 AI Task Template & Tasks")
    
    tasks = master_planner_service.get_tasks_for_workspace(workspace_id)
    
    # Fetch registered system users for dropdown assignment
    registered_users = ["Unassigned"]
    try:
        from src.repositories import UsersRepository
        u_repo = UsersRepository()
        for u in u_repo.find_all():
            uname = u.get("username") or u.get("display_name")
            if uname and uname not in registered_users:
                registered_users.append(uname)
    except Exception:
        pass

    # Action Row: Add Custom Task
    col_ta1, col_ta2 = st.columns([3, 1])
    with col_ta2:
        if st.button("➕ Add Custom Task", use_container_width=True, key="add_task_modal_btn"):
            st.session_state["show_add_task_form"] = True

    if st.session_state.get("show_add_task_form", False):
        with st.form("new_task_form"):
            st.write("##### Add New Workspace Task")
            n_title = st.text_input("Task Title")
            n_desc = st.text_area("Description")
            c_dept, c_prio, c_user = st.columns(3)
            with c_dept:
                n_dept = st.selectbox("Department", available_departments)
            with c_prio:
                n_prio = st.selectbox("Priority", ["High", "Medium", "Low"])
            with c_user:
                add_user_options = list(registered_users)
                if current_username and current_username not in add_user_options:
                    add_user_options.append(current_username)
                def_idx = add_user_options.index(current_username) if current_username in add_user_options else 0
                n_user = st.selectbox("Assigned To", add_user_options, index=def_idx)
            n_due = st.date_input("Due Date", value=datetime.date.today())
            
            submit_task = st.form_submit_button("Save Task")
            if submit_task and n_title:
                master_planner_service.create_task({
                    "workspace_id": workspace_id,
                    "event_id": str(selected_ev_id),
                    "title": n_title,
                    "description": n_desc,
                    "department": n_dept,
                    "assigned_user": n_user if n_user else "Unassigned",
                    "due_date": n_due.strftime("%Y-%m-%d"),
                    "priority": n_prio,
                    "status": "Pending"
                })
                st.session_state["show_add_task_form"] = False
                st.success("Task added!")
                st.rerun()

    # Display Task List & Interactive Editing
    if tasks:
        df_tasks = pd.DataFrame(tasks)
        for idx, task in enumerate(tasks):
            t_id = task["task_id"]
            t_status = task.get("status", "Pending")
            
            with st.container():
                c_t1, c_t2, c_t3, c_t4, c_t5, c_t6 = st.columns([3, 2, 2, 2, 2, 1])
                with c_t1:
                    st.markdown(f"**{task.get('title')}**")
                    if task.get("description"):
                        st.caption(task.get("description"))
                with c_t2:
                    st.write(f"🏢 `{task.get('department', 'Operations')}`")
                with c_t3:
                    curr_assigned = task.get("assigned_user", "Unassigned") or "Unassigned"
                    item_user_options = list(registered_users)
                    if curr_assigned not in item_user_options:
                        item_user_options.append(curr_assigned)
                    curr_idx = item_user_options.index(curr_assigned)
                    new_user = st.selectbox("Assigned To", item_user_options, index=curr_idx, key=f"t_user_{t_id}_{idx}")
                    if new_user != task.get("assigned_user"):
                        master_planner_service.update_task(t_id, {"assigned_user": new_user})
                        st.rerun()
                with c_t4:
                    st.caption(f"📅 Due: {task.get('due_date', 'N/A')}")
                    st.caption(f"Priority: **{task.get('priority', 'Medium')}**")
                    if task.get("suggested_timeline"):
                        st.caption(f"💡 *Timeline:* {task.get('suggested_timeline')}")

                with c_t5:
                    new_stat = st.selectbox("Status", ["Pending", "In Progress", "Completed"], index=["Pending", "In Progress", "Completed"].index(t_status) if t_status in ["Pending", "In Progress", "Completed"] else 0, key=f"t_stat_{t_id}_{idx}")
                    if new_stat != t_status:
                        master_planner_service.update_task(t_id, {"status": new_stat})
                        st.rerun()
                with c_t6:
                    if st.button("🗑️", key=f"del_t_{t_id}_{idx}", help="Delete Task"):
                        master_planner_service.delete_task(t_id)
                        st.rerun()
            st.divider()
    else:
        st.info("No tasks generated for this workspace yet.")

    # ---------------------------------------------------------
    # TASK ASSIGNMENT & USER ALLOCATION MANAGER
    # ---------------------------------------------------------
    st.write("---")
    st.markdown("#### 👤 Task Assignment & User Allocation Manager")
    st.markdown("*Assign workspace tasks to registered users, manage team workloads, and execute bulk assignments.*")
    
    if tasks:
        # Quick Action Buttons
        col_qa1, col_qa2, col_qa3 = st.columns(3)
        with col_qa1:
            if st.button("🙋‍♂️ Assign All Unassigned to Me", use_container_width=True, key="btn_assign_me"):
                unassigned_count = 0
                for t in tasks:
                    if not t.get("assigned_user") or str(t.get("assigned_user")).strip().lower() in ["unassigned", "none", ""]:
                        master_planner_service.update_task(t["task_id"], {"assigned_user": current_username})
                        unassigned_count += 1
                if unassigned_count > 0:
                    st.success(f"Assigned {unassigned_count} unassigned tasks to '{current_username}'!")
                    st.rerun()
                else:
                    st.info("No unassigned tasks found in this workspace.")

        with col_qa2:
            if st.button("⚖️ Auto-Distribute Tasks Evenly", use_container_width=True, key="btn_auto_distribute"):
                assignable_users = [u for u in registered_users if u != "Unassigned"]
                if not assignable_users:
                    st.warning("No registered users available for distribution.")
                else:
                    unassigned_tasks = [t for t in tasks if not t.get("assigned_user") or str(t.get("assigned_user")).strip().lower() in ["unassigned", "none", ""]]
                    if not unassigned_tasks:
                        st.info("All workspace tasks are already assigned.")
                    else:
                        for u_i, t_item in enumerate(unassigned_tasks):
                            assigned_target = assignable_users[u_i % len(assignable_users)]
                            master_planner_service.update_task(t_item["task_id"], {"assigned_user": assigned_target})
                        st.success(f"Distributed {len(unassigned_tasks)} tasks across {len(assignable_users)} team members!")
                        st.rerun()

        with col_qa3:
            if st.button("🔄 Reset All Tasks to Unassigned", use_container_width=True, key="btn_reset_assignments"):
                for t in tasks:
                    master_planner_service.update_task(t["task_id"], {"assigned_user": "Unassigned"})
                st.success("Reset all workspace task assignments to Unassigned.")
                st.rerun()

        # Bulk Assignment Form Panel
        with st.expander("⚡ Bulk Task Assignment Tool", expanded=False):
            with st.form("bulk_assignment_form"):
                st.write("##### Select Tasks & Target Assignee")
                target_user = st.selectbox("Target Assignee", [u for u in registered_users if u != "Unassigned"], key="bulk_target_user")
                
                # Checkbox list of tasks
                task_options = {f"[{t.get('department', 'Ops')}] {t.get('title')} (Currently: {t.get('assigned_user', 'Unassigned')})": t["task_id"] for t in tasks}
                selected_task_labels = st.multiselect("Select Workspace Tasks", list(task_options.keys()), key="bulk_selected_tasks")
                
                if st.form_submit_button("💾 Apply Bulk Assignment", type="primary", use_container_width=True):
                    if not selected_task_labels:
                        st.error("Please select at least one task to assign.")
                    else:
                        count_updated = 0
                        for lbl in selected_task_labels:
                            t_id_to_assign = task_options[lbl]
                            master_planner_service.update_task(t_id_to_assign, {"assigned_user": target_user})
                            count_updated += 1
                        st.success(f"Assigned {count_updated} tasks to '{target_user}' successfully!")
                        st.rerun()

        # User Workload Cards Grid
        st.markdown("##### 📊 Team Member Allocation & Workload")
        user_tasks_map = {u: [] for u in registered_users}
        for t in tasks:
            u_assigned = t.get("assigned_user", "Unassigned") or "Unassigned"
            if u_assigned not in user_tasks_map:
                user_tasks_map[u_assigned] = []
            user_tasks_map[u_assigned].append(t)

        u_cols = st.columns(min(3, max(1, len(user_tasks_map))))
        for u_idx, (u_name, u_task_list) in enumerate(user_tasks_map.items()):
            col_target = u_cols[u_idx % len(u_cols)]
            with col_target:
                with st.container(border=True):
                    st.markdown(f"**👤 {u_name}**")
                    comp_count = sum(1 for t in u_task_list if str(t.get("status")).strip().lower() == "completed")
                    st.caption(f"Assigned Tasks: **{len(u_task_list)}** | Completed: **{comp_count}**")
                    
                    if u_task_list:
                        with st.expander(f"View Tasks ({len(u_task_list)})", expanded=False):
                            for ut_idx, ut in enumerate(u_task_list):
                                st.markdown(f"• **{ut.get('title')}** (`{ut.get('status', 'Pending')}`)")
                                cur_t_id = ut.get("task_id")
                                r_opts = list(registered_users)
                                r_idx = r_opts.index(u_name) if u_name in r_opts else 0
                                re_user = st.selectbox(
                                    "Reassign To", r_opts, index=r_idx, key=f"reassign_{cur_t_id}_{u_idx}_{ut_idx}"
                                )
                                if re_user != u_name:
                                    master_planner_service.update_task(cur_t_id, {"assigned_user": re_user})
                                    st.rerun()
                    else:
                        st.caption("No tasks assigned.")

    # 3. DEPARTMENT WORKSTREAMS (Task 1: Dynamic Department Tabs)
    st.write("---")
    st.write("#### 3. 🏢 Department Workstreams")
    if tasks:
        df_tasks = pd.DataFrame(tasks)
        if "department" in df_tasks.columns:
            depts = sorted(df_tasks["department"].unique().tolist())
            dept_tabs = st.tabs([f"🏢 {d}" for d in depts])
            for d_idx, d_name in enumerate(depts):
                with dept_tabs[d_idx]:
                    d_tasks = df_tasks[df_tasks["department"] == d_name]
                    st.dataframe(d_tasks[["title", "assigned_user", "due_date", "priority", "status"]], use_container_width=True, hide_index=True)
    else:
        st.caption("No department workstream data available.")

    # 4. USER ASSIGNMENTS SUMMARY
    st.write("---")
    st.write("#### 4. 👤 User Assignments Summary")
    if tasks:
        df_tasks = pd.DataFrame(tasks)
        if "assigned_user" in df_tasks.columns:
            user_counts = df_tasks["assigned_user"].value_counts().reset_index()
            user_counts.columns = ["Assigned User", "Total Tasks"]
            st.dataframe(user_counts, use_container_width=True, hide_index=True)

    # 5. PROGRESS TRACKER (Task 5: Centralized Progress Engine)
    st.write("---")
    st.write("#### 5. 📈 Progress Tracker")
    prog_data = master_planner_service.calculate_event_progress_by_workspace(workspace_id)
    
    col_pr1, col_pr2, col_pr3, col_pr4 = st.columns(4)
    with col_pr1:
        st.metric("Total Tasks", f"{prog_data['total']}")
    with col_pr2:
        st.metric("Completed", f"{prog_data['completed']}")
    with col_pr3:
        st.metric("In Progress", f"{prog_data['in_progress']}")
    with col_pr4:
        st.metric("Pending", f"{prog_data['pending']}")
        
    st.write(f"**Overall Workspace Completion: {prog_data['percentage']}%**")
    st.progress(float(prog_data['percentage']) / 100.0)

    # 6. RUN OF SHOW (TIMELINE EDITOR)
    st.write("---")
    st.write("#### 6. ⏱️ Run of Show (Planning Timeline Editor)")
    st.caption("CRUD Planning Editor for event day schedule sequence. No live updates.")
    
    ros_items = master_planner_service.get_run_of_show(workspace_id)
    
    # Form to add new timeline item
    with st.expander("➕ Add Run of Show Slot", expanded=False):
        with st.form("new_ros_form"):
            c_r1, c_r2 = st.columns(2)
            with c_r1:
                ros_time = st.text_input("Start Time (e.g. 18:00)", value="18:00")
                ros_activity = st.text_input("Activity / Item Name")
            with c_r2:
                ros_lead = st.text_input("Responsible Lead", value=current_username)
                ros_notes = st.text_input("Notes / Tech Cue")
            submit_ros = st.form_submit_button("Add Timeline Slot")
            if submit_ros and ros_activity:
                master_planner_service.create_ros_item({
                    "workspace_id": workspace_id,
                    "event_id": str(selected_ev_id),
                    "start_time": ros_time,
                    "activity": ros_activity,
                    "lead": ros_lead,
                    "notes": ros_notes
                })
                st.success("Run of Show slot added!")
                st.rerun()

    # Display & Edit ROS Items
    if ros_items:
        for r_idx, item in enumerate(ros_items):
            ros_id = item["ros_id"]
            c_ros1, c_ros2, c_ros3, c_ros4, c_ros5 = st.columns([2, 3, 2, 3, 1])
            with c_ros1:
                st.markdown(f"⏱️ **{item.get('start_time', 'N/A')}**")
            with c_ros2:
                st.markdown(f"**{item.get('activity', 'N/A')}**")
            with c_ros3:
                st.caption(f"Lead: {item.get('lead', 'N/A')}")
            with c_ros4:
                st.caption(f"Notes: {item.get('notes', 'None')}")
            with c_ros5:
                if st.button("🗑️", key=f"del_ros_{ros_id}_{r_idx}"):
                    master_planner_service.delete_ros_item(ros_id)
                    st.rerun()
            st.divider()
    else:
        st.info("No Run of Show schedule added yet. Use the expander above to create the event day timeline.")


# ===========================================================
# LANDING PAGE SECTIONS (Task 7: Landing Page Summary Cards)
# ===========================================================
else:
    st.write("---")
    
    # Task 7: Summary Metric Cards for Landing Page
    landing_metrics = master_planner_service.get_landing_page_summary_metrics(df_calendar)
    
    m_c1, m_c2, m_c3, m_c4, m_c5 = st.columns(5)
    with m_c1:
        st.metric("📅 Upcoming Events", f"{landing_metrics['upcoming']}")
    with m_c2:
        st.metric("⚡ Ongoing Events", f"{landing_metrics['ongoing']}")
    with m_c3:
        st.metric("✅ Completed (Month)", f"{landing_metrics['completed_this_month']}")
    with m_c4:
        st.metric("📈 Avg Progress", f"{landing_metrics['avg_progress']}%")
    with m_c5:
        st.metric("🚨 Overdue Tasks", f"{landing_metrics['overdue_tasks']}", delta=f"-{landing_metrics['overdue_tasks']}" if landing_metrics['overdue_tasks'] else None, delta_color="inverse")
        
    st.write("---")

    # Categorize events from Calendar DB
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    
    upcoming_events = []
    ongoing_events = []
    completed_events = []
    
    if not df_calendar.empty:
        date_col = safe_get_column(df_calendar, ["Date", "Event Date"]) or "Date"
        status_col = safe_status_column(df_calendar) or "Status"
        id_col = safe_get_column(df_calendar, ["Event ID", "ID", "id"]) or "Event ID"
        
        for _, row in df_calendar.iterrows():
            ev_dict = row.to_dict()
            ev_date = str(row.get(date_col, ""))
            ev_status = str(row.get(status_col, ""))
            
            if ev_status == "Cancelled":
                continue
            elif ev_status == "Completed":
                completed_events.append(ev_dict)
            elif ev_date == today_str or ev_status == "In Progress":
                ongoing_events.append(ev_dict)
            else:
                upcoming_events.append(ev_dict)
                
    # Helper to render event list cards (Task 5: Using calculate_event_progress service)
    def render_event_section(title: str, event_list: List[Dict[str, Any]], icon: str):
        st.write(f"### {icon} {title} ({len(event_list)})")
        if not event_list:
            st.caption(f"No {title.lower()} found.")
            return
            
        for idx, ev in enumerate(event_list):
            ev_id = ev.get("Event ID", ev.get("Event Name", f"EVT-{idx}"))
            ev_name = ev.get("Event Name", "Untitled Event")
            ev_prop = ev.get("Property", "All Properties")
            ev_date = ev.get("Date", "N/A")
            ev_cat = ev.get("Category", "Social")
            ev_status = ev.get("Status", "Approved")
            
            # Use Task 5 centralized progress calculation service method
            prog = master_planner_service.calculate_event_progress(str(ev_id))
            
            with st.container():
                c_ev1, c_ev2, c_ev3, c_ev4, c_ev5 = st.columns([3, 2, 2, 2, 2])
                with c_ev1:
                    st.markdown(f"##### **{ev_name}**")
                    st.caption(f"Category: {ev_cat} | Status: `{ev_status}`")
                with c_ev2:
                    st.write(f"🏢 **{ev_prop}**")
                with c_ev3:
                    st.write(f"📅 {ev_date}")
                with c_ev4:
                    st.write(f"Progress: **{prog['percentage']}%** ({prog['completed']}/{prog['total']} tasks)")
                    st.progress(float(prog['percentage']) / 100.0)
                with c_ev5:
                    if st.button("🚀 Open Workspace", key=f"open_ws_{ev_id}_{idx}", use_container_width=True):
                        st.session_state["selected_planner_event_id"] = str(ev_id)
                        st.rerun()
                    if st.button("🗑️ Delete Event", key=f"del_ev_{ev_id}_{idx}", use_container_width=True):
                        from src.integrations.calendar_db import delete_calendar_event
                        delete_calendar_event(str(ev_id))
                        st.success(f"Deleted event '{ev_name}'")
                        st.rerun()
            st.divider()

    # 1. UPCOMING EVENTS
    render_event_section("Upcoming Events", upcoming_events, "📅")
    
    # 2. ONGOING EVENTS
    st.write("---")
    render_event_section("Ongoing Events", ongoing_events, "⚡")
    
    # 3. COMPLETED EVENTS
    st.write("---")
    render_event_section("Completed Events", completed_events, "✅")
