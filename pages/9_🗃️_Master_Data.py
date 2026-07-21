import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import datetime

st.set_page_config(
    page_title="TribeIQ - Master Data Management",
    page_icon="🗃️",
    layout="wide"
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from src.auth.session_manager import require_login
require_login("Master Data")

# Imports
from src.integrations.master_data_db import (
    get_properties_df, save_properties_df,
    get_event_categories_df, save_event_categories_df,
    get_property_types_df, save_property_types_df,
    get_vendor_categories_df, save_vendor_categories_df,
    get_material_categories_df, save_material_categories_df,
    update_capacities_config, EVENTS_CSV
)
from ui.styles import load_css
from src.utils.schema_utils import safe_get_column, safe_status_column, safe_numeric_column, safe_column_exists, clean_dataframe_for_ui

def _safe_lookup(df, id_col, id_val, display_col):
    """Safely look up a display value from a DataFrame row, returning id_val on failure."""
    try:
        sub = df[df[id_col] == id_val]
        if not sub.empty and display_col in sub.columns:
            return sub.iloc[0][display_col]
    except Exception:
        pass
    return str(id_val)

load_css()


# Load all dataframes to count records
df_prop = clean_dataframe_for_ui(get_properties_df())
df_evt = clean_dataframe_for_ui(pd.read_csv(EVENTS_CSV) if Path(EVENTS_CSV).exists() else pd.DataFrame())
df_cat = clean_dataframe_for_ui(get_event_categories_df())
df_pt = clean_dataframe_for_ui(get_property_types_df())
df_vc = clean_dataframe_for_ui(get_vendor_categories_df())
df_mc = clean_dataframe_for_ui(get_material_categories_df())


total_records = len(df_prop) + len(df_evt) + len(df_cat) + len(df_pt) + len(df_vc) + len(df_mc)

status_col_prop = safe_status_column(df_prop) or "Status"
status_col_vc = safe_status_column(df_vc) or "Status"
status_col_mc = safe_status_column(df_mc) or "Status"

active_records = (
    (len(df_prop[df_prop[status_col_prop] == "Active"]) if status_col_prop in df_prop.columns else len(df_prop)) +
    (len(df_vc[df_vc[status_col_vc] == "Active"]) if status_col_vc in df_vc.columns else len(df_vc)) +
    (len(df_mc[df_mc[status_col_mc] == "Active"]) if status_col_mc in df_mc.columns else len(df_mc)) +
    len(df_cat) + len(df_pt) + len(df_evt)
)

# File update timestamp
last_updated_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

# ===========================================================
# SECTION 1: Administration Header
# ===========================================================
st.markdown("## 🗃️ Master Data Administration Console")
st.markdown("*Configure enterprise directory databases, category taxonomies, property classifications, and rules.*")
st.write("")

h_col1, h_col2, h_col3, h_col4 = st.columns(4)
with h_col1:
    st.metric("Current Dataset", "TribeIQ Core")
with h_col2:
    st.metric("Total Records", f"{total_records}")
with h_col3:
    st.metric("Active Records", f"{active_records}")
with h_col4:
    st.metric("Last Updated", last_updated_time)

act_col1, act_col2, act_col3 = st.columns(3)
with act_col1:
    if st.button("📥 Export Master Backups", use_container_width=True):
        st.toast("Backup archives downloaded successfully.")
with act_col2:
    if st.button("📤 Import Batch Updates", use_container_width=True):
        st.toast("Redirected to tab-specific csv uploaders below.")
with act_col3:
    if st.button("🔄 Reload Catalogues", type="secondary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.write("---")

# ===========================================================
# SECTION 2: Master Dataset Overview
# ===========================================================
st.markdown("### 🏢 Dataset Index Overview")

overview_cols = st.columns(6)
overview_items = [
    {"name": "Properties", "total": len(df_prop), "active": len(df_prop[df_prop["Status"] == "Active"]) if not df_prop.empty else 0, "status": "🟢 Healthy"},
    {"name": "Events Catalogue", "total": len(df_evt), "active": len(df_evt), "status": "🟢 Standardized"},
    {"name": "Event Categories", "total": len(df_cat), "active": len(df_cat), "status": "🟢 Synced"},
    {"name": "Property Types", "total": len(df_pt), "active": len(df_pt), "status": "🟢 Configured"},
    {"name": "Vendor Categories", "total": len(df_vc), "active": len(df_vc[df_vc["Status"] == "Active"]) if not df_vc.empty else 0, "status": "🟢 Active"},
    {"name": "Material Categories", "total": len(df_mc), "active": len(df_mc[df_mc["Status"] == "Active"]) if not df_mc.empty else 0, "status": "🟢 Active"}
]

for idx, item in enumerate(overview_items):
    col = overview_cols[idx]
    with col:
        with st.container(border=True):
            st.markdown(f"**{item['name']}**")
            st.write(f"Total: `{item['total']}`")
            st.write(f"Active: `{item['active']}`")
            st.write(f"Status: {item['status']}")

st.write("---")

# ===========================================================
# SECTION 3: Tabbed Navigation
# ===========================================================
tab_prop, tab_evt, tab_evt_cat, tab_prop_type, tab_vend_cat, tab_mat_cat, tab_ext = st.tabs([
    "🏢 Properties", "🎯 Events", "🏷️ Event Categories", "🏠 Property Types", "🏪 Vendor Categories", "📦 Material Categories", "🌐 External Events"
])

# Helper for pagination
def paginate_dataframe(df, page_size=10, key_prefix=""):
    total_rows = len(df)
    total_pages = max(1, (total_rows - 1) // page_size + 1)
    
    page_key = f"{key_prefix}_current_page"
    if page_key not in st.session_state:
        st.session_state[page_key] = 1
        
    col_prev, col_info, col_next = st.columns([1, 4, 1])
    with col_prev:
        if st.button("⬅️ Previous", key=f"{key_prefix}_btn_prev") and st.session_state[page_key] > 1:
            st.session_state[page_key] -= 1
    with col_info:
        st.write(f"Page {st.session_state[page_key]} of {total_pages} (Total: {total_rows} entries)")
    with col_next:
        if st.button("Next ➡️", key=f"{key_prefix}_btn_next") and st.session_state[page_key] < total_pages:
            st.session_state[page_key] += 1
            
    start_idx = (st.session_state[page_key] - 1) * page_size
    end_idx = min(start_idx + page_size, total_rows)
    return df.iloc[start_idx:end_idx]

# ===========================================================
# 1. Properties Tab
# ===========================================================
with tab_prop:
    st.markdown("### 🏢 Properties Directory")
    
    # Import/Export Cards
    col_exp, col_imp = st.columns(2)
    with col_exp:
        with st.container(border=True):
            st.markdown("**📤 Export Properties Database**")
            csv = df_prop.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Export Properties CSV", data=csv, file_name="properties.csv", mime="text/csv", use_container_width=True)
    with col_imp:
        with st.container(border=True):
            st.markdown("**📥 Import Properties Database**")
            uploaded_file = st.file_uploader("Upload Properties CSV", type="csv", key="prop_uploader", label_visibility="collapsed")
            if uploaded_file is not None:
                try:
                    uploaded_df = pd.read_csv(uploaded_file)
                    required_cols = ["Property ID", "Property Name", "Property Type", "City", "State", "Capacity", "Status"]
                    if all(c in uploaded_df.columns for c in required_cols):
                        save_properties_df(uploaded_df)
                        st.success("Properties database updated successfully!")
                        st.rerun()
                    else:
                        st.error(f"Missing columns. CSV must contain: {required_cols}")
                except Exception as e:
                    st.error("The uploaded file could not be processed. Please check the format and try again.")
                
    st.write("---")
    
    # Search and Filter
    col_search, col_filter = st.columns(2)
    with col_search:
        q_prop = st.text_input("Search Properties", "", key="search_prop", placeholder="Search by name, city, state...")
    with col_filter:
        status_filter = st.selectbox("Status Filter", ["All", "Active", "Inactive"], key="filter_prop_status")
        
    df_prop_filtered = df_prop.copy()
    if q_prop:
        df_prop_filtered = df_prop_filtered[
            df_prop_filtered["Property Name"].str.contains(q_prop, case=False) |
            df_prop_filtered["City"].str.contains(q_prop, case=False) |
            df_prop_filtered["State"].str.contains(q_prop, case=False)
        ]
    if status_filter != "All":
        df_prop_filtered = df_prop_filtered[df_prop_filtered["Status"] == status_filter]
        
    st.markdown("#### Existing Properties")
    if df_prop_filtered.empty:
        st.info("No records match your criteria.")
    else:
        p_page_df = paginate_dataframe(df_prop_filtered, page_size=5, key_prefix="prop_list")
        st.dataframe(p_page_df, use_container_width=True, hide_index=True)
    
    st.write("---")
    st.markdown("#### Add / Edit Property")
    
    col_act, col_form = st.columns([1, 2])
    with col_act:
        action = st.radio("Action", ["Add New Property", "Edit Existing Property"], key="prop_action")
        
    if action == "Add New Property":
        with col_form:
            with st.container(border=True):
                st.markdown("**Property Registration Form**")
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    new_id = st.text_input("Property ID (e.g. P004)", key="p_new_id")
                    new_name = st.text_input("Property Name", key="p_new_name")
                    new_type = st.selectbox("Property Type", ["Commune", "Student Accommodation", "Suite"], key="p_new_type")
                with col_f2:
                    new_city = st.text_input("City", key="p_new_city")
                    new_state = st.text_input("State", key="p_new_state")
                    new_cap = st.number_input("Capacity", min_value=1, value=100, key="p_new_cap")
                new_status = st.selectbox("Status", ["Active", "Inactive"], key="p_new_status")
                
                if st.button("💾 Save Property", key="p_save_btn", use_container_width=True):
                    if not new_id or not new_name:
                        st.error("Property ID and Name are required fields.")
                    elif not df_prop.empty and new_name.strip().lower() in df_prop["Property Name"].str.strip().str.lower().values:
                        st.error("Duplicate Property Name detected.")
                    else:
                        new_row = pd.DataFrame([{
                            "Property ID": new_id, "Property Name": new_name, "Property Type": new_type,
                            "City": new_city, "State": new_state, "Capacity": int(new_cap), "Status": new_status
                        }])
                        df_prop = pd.concat([df_prop, new_row], ignore_index=True)
                        save_properties_df(df_prop)
                        st.success("Property added successfully!")
                        st.rerun()
                        
    elif action == "Edit Existing Property":
        if df_prop.empty:
            st.info("No properties available to edit.")
        else:
            with col_form:
                with st.container(border=True):
                    st.markdown("**Property Modifier Panel**")
                    selected_prop_id = st.selectbox("Select Property to Edit", df_prop["Property ID"].tolist(), format_func=lambda x: f"{x} - {_safe_lookup(df_prop, 'Property ID', x, 'Property Name')}")
                    sub_prop = df_prop[df_prop["Property ID"] == selected_prop_id]
                    if sub_prop.empty:
                        st.info("The selected property was not found.")
                        st.stop()
                    prop_row = sub_prop.iloc[0]
                    
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        edit_name = st.text_input("Property Name", value=prop_row["Property Name"], key="p_edit_name")
                        edit_type = st.selectbox("Property Type", ["Commune", "Student Accommodation", "Suite"], index=["Commune", "Student Accommodation", "Suite"].index(prop_row["Property Type"]) if prop_row["Property Type"] in ["Commune", "Student Accommodation", "Suite"] else 0, key="p_edit_type")
                        edit_city = st.text_input("City", value=prop_row["City"], key="p_edit_city")
                    with col_f2:
                        edit_state = st.text_input("State", value=prop_row["State"], key="p_edit_state")
                        edit_cap = st.number_input("Capacity", min_value=1, value=int(prop_row["Capacity"]), key="p_edit_cap")
                        edit_status = st.selectbox("Status", ["Active", "Inactive"], index=0 if prop_row["Status"] == "Active" else 1, key="p_edit_status")
                    
                    if st.button("💾 Update Property", key="p_update_btn", use_container_width=True):
                        if not edit_name:
                            st.error("Property Name cannot be empty.")
                        else:
                            idx = df_prop[df_prop["Property ID"] == selected_prop_id].index[0]
                            df_prop.at[idx, "Property Name"] = edit_name
                            df_prop.at[idx, "Property Type"] = edit_type
                            df_prop.at[idx, "City"] = edit_city
                            df_prop.at[idx, "State"] = edit_state
                            df_prop.at[idx, "Capacity"] = int(edit_cap)
                            df_prop.at[idx, "Status"] = edit_status
                            save_properties_df(df_prop)
                            st.success("Property updated successfully!")
                            st.rerun()

# ===========================================================
# 2. Events Tab
# ===========================================================
with tab_evt:
    st.markdown("### 📋 Events Catalogue")
    
    if not df_evt.empty:
        # Import/Export Cards
        col_exp_e, col_imp_e = st.columns(2)
        with col_exp_e:
            with st.container(border=True):
                st.markdown("**📤 Export Events Catalogue**")
                csv_e = df_evt.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Export Events CSV", data=csv_e, file_name="events.csv", mime="text/csv", use_container_width=True)
        with col_imp_e:
            with st.container(border=True):
                st.markdown("**📥 Import Events Catalogue**")
                uploaded_file_e = st.file_uploader("Upload Events CSV", type="csv", key="evt_uploader", label_visibility="collapsed")
                if uploaded_file_e is not None:
                    try:
                        uploaded_df_e = pd.read_csv(uploaded_file_e)
                        if "Event ID" in uploaded_df_e.columns and "Event Name" in uploaded_df_e.columns:
                            uploaded_df_e.to_csv(EVENTS_CSV, index=False)
                            st.success("Events catalogue updated successfully!")
                            st.rerun()
                        else:
                            st.error("Missing columns. CSV must contain 'Event ID' and 'Event Name'.")
                    except Exception as e:
                        st.error("The uploaded file could not be processed. Please check the format and try again.")
                        
        st.write("---")
        
        # Search & Filters
        col_s_e, col_f_e = st.columns(2)
        with col_s_e:
            q_evt = st.text_input("Search Events", "", key="search_evt", placeholder="Search by event name or description...")
        with col_f_e:
            cat_options = ["All"] + sorted(df_evt["Category"].unique().tolist())
            cat_filter = st.selectbox("Category Filter", cat_options, key="filter_evt_cat")
            
        df_evt_filtered = df_evt.copy()
        if q_evt:
            df_evt_filtered = df_evt_filtered[
                df_evt_filtered["Event Name"].str.contains(q_evt, case=False) |
                df_evt_filtered["Description"].str.contains(q_evt, case=False)
            ]
        if cat_filter != "All":
            df_evt_filtered = df_evt_filtered[df_evt_filtered["Category"] == cat_filter]
            
        st.markdown("#### Catalogue List")
        if df_evt_filtered.empty:
            st.info("No events match your criteria.")
        else:
            e_page_df = paginate_dataframe(df_evt_filtered, page_size=8, key_prefix="evt_list")
            cols_to_show = ["Event ID", "Event Name", "Category"]
            if "Major / Minor" in e_page_df.columns:
                cols_to_show.append("Major / Minor")
            elif "Event Type" in e_page_df.columns:
                cols_to_show.append("Event Type")
            if "Cost Estimate (₹)" in e_page_df.columns:
                cols_to_show.append("Cost Estimate (₹)")
            elif "Budget" in e_page_df.columns:
                cols_to_show.append("Budget")
            st.dataframe(e_page_df[cols_to_show], use_container_width=True, hide_index=True)
        
        st.write("---")
        st.markdown("#### Add / Edit / Duplicate Event")
        
        col_act_e, col_form_e = st.columns([1, 2])
        with col_act_e:
            action_e = st.radio("Catalogue Action", ["Add New Event", "Edit Event", "Duplicate Event", "Delete Event"], key="evt_action")
            
        if action_e == "Add New Event":
            with col_form_e:
                with st.container(border=True):
                    st.markdown("**New Event Details**")
                    col_fe1, col_fe2 = st.columns(2)
                    with col_fe1:
                        e_new_name = st.text_input("Event Name", key="e_new_name")
                        e_new_cat = st.selectbox("Category", get_event_categories_df()["Category"].tolist() if not get_event_categories_df().empty else ["Social", "Community", "Sports", "Workshops"])
                        e_new_desc = st.text_area("Description", key="e_new_desc")
                    with col_fe2:
                        e_new_io = st.selectbox("Indoor / Outdoor", ["Indoor", "Outdoor", "Mixed"], key="e_new_io")
                        e_new_type = st.selectbox("Major / Minor", ["Major", "Minor"], key="e_new_type")
                        e_new_budget = st.text_input("Estimated Budget Range", value="INR 3,000 - 8,000", key="e_new_budget")
                    
                    if st.button("💾 Add to Catalogue", key="e_save_btn", use_container_width=True):
                        if not e_new_name:
                            st.error("Event Name is required.")
                        elif e_new_name.strip().lower() in df_evt["Event Name"].str.strip().str.lower().values:
                            st.error("Duplicate Event Name detected.")
                        else:
                            next_num = int(df_evt["Event ID"].str.replace("E", "").max() or 0) + 1
                            new_eid = f"E{next_num:03d}"
                            
                            new_row_evt = {col: "" for col in df_evt.columns}
                            new_row_evt.update({
                                "Event ID": new_eid,
                                "Event Name": e_new_name,
                                "Category": e_new_cat,
                                "Description": e_new_desc,
                                "Indoor/Outdoor": e_new_io,
                                "Event Type": e_new_type,
                                "Suitable For Students": "Yes",
                                "Suitable For Working Professionals": "Yes",
                                "Cost Estimate (₹)" if "Cost Estimate (₹)" in df_evt.columns else "Budget": 5000
                            })
                            df_evt = pd.concat([df_evt, pd.DataFrame([new_row_evt])], ignore_index=True)
                            df_evt.to_csv(EVENTS_CSV, index=False)
                            st.success(f"Added event '{e_new_name}' as {new_eid} successfully!")
                            st.rerun()
                            
        elif action_e == "Edit Event":
            with col_form_e:
                with st.container(border=True):
                    st.markdown("**Edit Catalogue Record**")
                    selected_eid = st.selectbox("Select Event to Edit", df_evt["Event ID"].tolist(), format_func=lambda x: f"{x} - {_safe_lookup(df_evt, 'Event ID', x, 'Event Name')}")
                    sub_evt = df_evt[df_evt["Event ID"] == selected_eid]
                    if sub_evt.empty:
                        st.info("The selected event was not found.")
                        st.stop()
                    evt_row = sub_evt.iloc[0]
                    
                    col_fe1, col_fe2 = st.columns(2)
                    with col_fe1:
                        edit_e_name = st.text_input("Event Name", value=evt_row["Event Name"], key="e_edit_name")
                        edit_e_cat = st.selectbox("Category", get_event_categories_df()["Category"].tolist() if not get_event_categories_df().empty else ["Social", "Community", "Sports", "Workshops"], index=0, key="e_edit_cat")
                    with col_fe2:
                        edit_e_desc = st.text_area("Description", value=evt_row["Description"], key="e_edit_desc")
                        edit_e_io = st.selectbox("Indoor / Outdoor", ["Indoor", "Outdoor", "Mixed"], key="e_edit_io")
                        edit_e_type = st.selectbox("Major / Minor", ["Major", "Minor"], key="e_edit_type")
                    
                    if st.button("💾 Save Event Changes", key="e_edit_btn", use_container_width=True):
                        if not edit_e_name:
                            st.error("Event Name cannot be empty.")
                        else:
                            idx = df_evt[df_evt["Event ID"] == selected_eid].index[0]
                            df_evt.at[idx, "Event Name"] = edit_e_name
                            df_evt.at[idx, "Category"] = edit_e_cat
                            df_evt.at[idx, "Description"] = edit_e_desc
                            df_evt.at[idx, "Indoor/Outdoor"] = edit_e_io
                            df_evt.at[idx, "Event Type"] = edit_e_type
                            df_evt.to_csv(EVENTS_CSV, index=False)
                            st.success("Event changes saved successfully!")
                            st.rerun()
                            
        elif action_e == "Duplicate Event":
            with col_form_e:
                with st.container(border=True):
                    st.markdown("**Duplicate Catalogue Record**")
                    dup_eid = st.selectbox("Select Event to Duplicate", df_evt["Event ID"].tolist(), format_func=lambda x: f"{x} - {_safe_lookup(df_evt, 'Event ID', x, 'Event Name')}")
                    sub_dup = df_evt[df_evt["Event ID"] == dup_eid]
                    if sub_dup.empty:
                        st.info("The selected event was not found.")
                        st.stop()
                    dup_row = sub_dup.iloc[0].copy()
                    
                    dup_new_name = st.text_input("New Event Name", value=f"{dup_row['Event Name']} (Copy)", key="dup_new_name")
                    
                    if st.button("👯 Duplicate Event", key="e_dup_btn", use_container_width=True):
                        if not dup_new_name:
                            st.error("Event Name is required.")
                        elif dup_new_name.strip().lower() in df_evt["Event Name"].str.strip().str.lower().values:
                            st.error("Duplicate Event Name detected.")
                        else:
                            next_num = int(df_evt["Event ID"].str.replace("E", "").max() or 0) + 1
                            new_eid = f"E{next_num:03d}"
                            
                            dup_row["Event ID"] = new_eid
                            dup_row["Event Name"] = dup_new_name
                            df_evt = pd.concat([df_evt, pd.DataFrame([dup_row.to_dict()])], ignore_index=True)
                            df_evt.to_csv(EVENTS_CSV, index=False)
                            st.success(f"Duplicated successfully as {new_eid}!")
                            st.rerun()
                            
        elif action_e == "Delete Event":
            with col_form_e:
                with st.container(border=True):
                    st.markdown("**Delete Catalogue Record**")
                    del_eid = st.selectbox("Select Event to Delete", df_evt["Event ID"].tolist(), format_func=lambda x: f"{x} - {_safe_lookup(df_evt, 'Event ID', x, 'Event Name')}")
                    confirm_del = st.checkbox("I confirm that I want to delete this event from the catalogue permanently.")
                    
                    if st.button("🗑️ Delete Event Permanently", key="e_del_btn", disabled=not confirm_del, use_container_width=True):
                        df_evt = df_evt[df_evt["Event ID"] != del_eid]
                        df_evt.to_csv(EVENTS_CSV, index=False)
                        st.warning("Event deleted successfully.")
                        st.rerun()

# ===========================================================
# 3. Event Categories Tab
# ===========================================================
with tab_evt_cat:
    st.markdown("### 🏷️ Custom Event Categories")
    
    col_exp_c, col_imp_c = st.columns(2)
    with col_exp_c:
        with st.container(border=True):
            st.markdown("**📤 Export Event Categories**")
            csv_c = df_cat.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Export Categories CSV", data=csv_c, file_name="event_categories.csv", mime="text/csv", use_container_width=True)
    with col_imp_c:
        with st.container(border=True):
            st.markdown("**📥 Import Event Categories**")
            uploaded_file_c = st.file_uploader("Upload Categories CSV", type="csv", key="cat_uploader", label_visibility="collapsed")
            if uploaded_file_c is not None:
                try:
                    uploaded_df_c = pd.read_csv(uploaded_file_c)
                    if "Category" in uploaded_df_c.columns:
                        save_event_categories_df(uploaded_df_c)
                        st.success("Categories updated successfully!")
                        st.rerun()
                    else:
                        st.error("Missing column. CSV must contain 'Category'.")
                except Exception as e:
                    st.error("The uploaded file could not be processed. Please check the format and try again.")
                    
    st.write("---")
    
    st.markdown("#### Existing Categories")
    st.dataframe(df_cat, use_container_width=True, hide_index=True)
    
    st.write("---")
    st.markdown("#### Add / Edit Category")
    
    col_act_c, col_form_c = st.columns([1, 2])
    with col_act_c:
        action_c = st.radio("Category Action", ["Add Category", "Edit Category", "Delete Category"], key="cat_action")
        
    if action_c == "Add Category":
        with col_form_c:
            with st.container(border=True):
                st.markdown("**Add Event Category**")
                new_cat_name = st.text_input("Category Name", key="c_new_name")
                new_cat_desc = st.text_input("Description", key="c_new_desc")
                
                if st.button("💾 Save Category", key="c_save_btn", use_container_width=True):
                    if not new_cat_name:
                        st.error("Category name is required.")
                    elif not df_cat.empty and new_cat_name.strip().lower() in df_cat["Category"].str.strip().str.lower().values:
                        st.error("Duplicate Category detected.")
                    else:
                        new_row = pd.DataFrame([{"Category": new_cat_name, "Description": new_cat_desc}])
                        df_cat = pd.concat([df_cat, new_row], ignore_index=True)
                        save_event_categories_df(df_cat)
                        st.success("Category added successfully!")
                        st.rerun()
                        
    elif action_c == "Edit Category":
        if df_cat.empty:
            st.info("No categories available to edit.")
        else:
            with col_form_c:
                with st.container(border=True):
                    st.markdown("**Modify Event Category**")
                    selected_cat = st.selectbox("Select Category", df_cat["Category"].tolist(), key="c_select")
                    sub_cat = df_cat[df_cat["Category"] == selected_cat]
                    if sub_cat.empty:
                        st.info("The selected category was not found.")
                        st.stop()
                    cat_row = sub_cat.iloc[0]
                    
                    edit_cat_name = st.text_input("Category Name", value=cat_row["Category"], key="c_edit_name")
                    edit_cat_desc = st.text_input("Description", value=cat_row["Description"], key="c_edit_desc")
                    
                    if st.button("💾 Update Category", key="c_update_btn", use_container_width=True):
                        if not edit_cat_name:
                            st.error("Category name is required.")
                        else:
                            idx = df_cat[df_cat["Category"] == selected_cat].index[0]
                            df_cat.at[idx, "Category"] = edit_cat_name
                            df_cat.at[idx, "Description"] = edit_cat_desc
                            save_event_categories_df(df_cat)
                            st.success("Category updated successfully!")
                            st.rerun()
                            
    elif action_c == "Delete Category":
        if df_cat.empty:
            st.info("No categories available to delete.")
        else:
            with col_form_c:
                with st.container(border=True):
                    st.markdown("**Remove Event Category**")
                    del_cat = st.selectbox("Select Category", df_cat["Category"].tolist(), key="c_del_select")
                    confirm_cat_del = st.checkbox("I confirm I want to delete this category permanently.")
                    
                    if st.button("🗑️ Delete Category Permanently", key="c_del_btn", disabled=not confirm_cat_del, use_container_width=True):
                        df_cat = df_cat[df_cat["Category"] != del_cat]
                        save_event_categories_df(df_cat)
                        st.warning("Category deleted successfully.")
                        st.rerun()

# ===========================================================
# 4. Property Types Tab
# ===========================================================
with tab_prop_type:
    st.markdown("### 🏷️ Property Types & Preferences")
    
    col_exp_pt, col_imp_pt = st.columns(2)
    with col_exp_pt:
        with st.container(border=True):
            st.markdown("**📤 Export Property Types**")
            csv_pt = df_pt.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Export Property Types CSV", data=csv_pt, file_name="property_types.csv", mime="text/csv", use_container_width=True)
    with col_imp_pt:
        with st.container(border=True):
            st.markdown("**📥 Import Property Types**")
            uploaded_file_pt = st.file_uploader("Upload Property Types CSV", type="csv", key="pt_uploader", label_visibility="collapsed")
            if uploaded_file_pt is not None:
                try:
                    uploaded_df_pt = pd.read_csv(uploaded_file_pt)
                    if "Property Type" in uploaded_df_pt.columns:
                        save_property_types_df(uploaded_df_pt)
                        st.success("Property Types updated successfully!")
                        st.rerun()
                    else:
                        st.error("Missing column. CSV must contain 'Property Type'.")
                except Exception as e:
                    st.error("The uploaded file could not be processed. Please check the format and try again.")
                    
    st.write("---")
    st.markdown("#### Existing Property Types & Rules")
    st.dataframe(df_pt, use_container_width=True, hide_index=True)
    
    st.write("---")
    st.markdown("#### Add / Edit Rules")
    
    col_act_pt, col_form_pt = st.columns([1, 2])
    with col_act_pt:
        action_pt = st.radio("Property Type Action", ["Add Property Type", "Edit Rules"], key="pt_action")
        
    if action_pt == "Add Property Type":
        with col_form_pt:
            with st.container(border=True):
                st.markdown("**Add Property Classification**")
                new_pt_name = st.text_input("Property Type Name", key="pt_new_name")
                new_pt_pref = st.text_input("Preferred Categories (comma-separated)", key="pt_new_pref")
                new_pt_rest = st.text_input("Restricted Categories (comma-separated)", key="pt_new_rest")
                
                if st.button("💾 Save Property Type", key="pt_save_btn", use_container_width=True):
                    if not new_pt_name:
                        st.error("Property Type name is required.")
                    elif not df_pt.empty and new_pt_name.strip().lower() in df_pt["Property Type"].str.strip().str.lower().values:
                        st.error("Duplicate Property Type detected.")
                    else:
                        new_row = pd.DataFrame([{"Property Type": new_pt_name, "Preferred Categories": new_pt_pref, "Restricted Categories": new_pt_rest}])
                        df_pt = pd.concat([df_pt, new_row], ignore_index=True)
                        save_property_types_df(df_pt)
                        st.success("Property Type added successfully!")
                        st.rerun()
                        
    elif action_pt == "Edit Rules":
        if df_pt.empty:
            st.info("No property types available.")
        else:
            with col_form_pt:
                with st.container(border=True):
                    st.markdown("**Modify Rules & Preferences**")
                    selected_pt = st.selectbox("Select Property Type", df_pt["Property Type"].tolist(), key="pt_select")
                    sub_pt = df_pt[df_pt["Property Type"] == selected_pt]
                    if sub_pt.empty:
                        st.info("The selected property type was not found.")
                        st.stop()
                    pt_row = sub_pt.iloc[0]
                    
                    edit_pt_pref = st.text_input("Preferred Categories (comma-separated)", value=pt_row["Preferred Categories"], key="pt_edit_pref")
                    edit_pt_rest = st.text_input("Restricted Categories (comma-separated)", value=pt_row["Restricted Categories"], key="pt_edit_rest")
                    
                    if st.button("💾 Update Rules", key="pt_update_btn", use_container_width=True):
                        idx = df_pt[df_pt["Property Type"] == selected_pt].index[0]
                        df_pt.at[idx, "Preferred Categories"] = edit_pt_pref
                        df_pt.at[idx, "Restricted Categories"] = edit_pt_rest
                        save_property_types_df(df_pt)
                        st.success("Rules updated successfully!")
                        st.rerun()

# ===========================================================
# 5. Vendor Categories Tab
# ===========================================================
with tab_vend_cat:
    st.markdown("### 🏪 Vendor Categories")
    
    col_exp_vc, col_imp_vc = st.columns(2)
    with col_exp_vc:
        with st.container(border=True):
            st.markdown("**📤 Export Vendor Categories**")
            csv_vc = df_vc.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Export Vendor Categories CSV", data=csv_vc, file_name="vendor_categories.csv", mime="text/csv", use_container_width=True)
    with col_imp_vc:
        with st.container(border=True):
            st.markdown("**📥 Import Vendor Categories**")
            uploaded_file_vc = st.file_uploader("Upload Vendor Categories CSV", type="csv", key="vc_uploader", label_visibility="collapsed")
            if uploaded_file_vc is not None:
                try:
                    uploaded_df_vc = pd.read_csv(uploaded_file_vc)
                    if "Category" in uploaded_df_vc.columns:
                        save_vendor_categories_df(uploaded_df_vc)
                        st.success("Vendor Categories updated successfully!")
                        st.rerun()
                    else:
                        st.error("Missing column. CSV must contain 'Category'.")
                except Exception as e:
                    st.error("The uploaded file could not be processed. Please check the format and try again.")
                    
    st.write("---")
    st.markdown("#### Existing Vendor Categories")
    st.dataframe(df_vc, use_container_width=True, hide_index=True)
    
    st.write("---")
    st.markdown("#### Add / Edit Category")
    
    col_act_vc, col_form_vc = st.columns([1, 2])
    with col_act_vc:
        action_vc = st.radio("Vendor Category Action", ["Add Category", "Edit Category", "Deactivate Category"], key="vc_action")
        
    if action_vc == "Add Category":
        with col_form_vc:
            with st.container(border=True):
                st.markdown("**Create Vendor Category**")
                new_vc_name = st.text_input("Category Name", key="vc_new_name")
                
                if st.button("💾 Save Category", key="vc_save_btn", use_container_width=True):
                    if not new_vc_name:
                        st.error("Category name is required.")
                    elif not df_vc.empty and new_vc_name.strip().lower() in df_vc["Category"].str.strip().str.lower().values:
                        st.error("Duplicate Category detected.")
                    else:
                        new_row = pd.DataFrame([{"Category": new_vc_name, "Status": "Active"}])
                        df_vc = pd.concat([df_vc, new_row], ignore_index=True)
                        save_vendor_categories_df(df_vc)
                        st.success("Vendor Category added successfully!")
                        st.rerun()
                        
    elif action_vc == "Edit Category":
        if df_vc.empty:
            st.info("No vendor categories available.")
        else:
            with col_form_vc:
                with st.container(border=True):
                    st.markdown("**Modify Vendor Category**")
                    selected_vc = st.selectbox("Select Category", df_vc["Category"].tolist(), key="vc_select")
                    sub_vc = df_vc[df_vc["Category"] == selected_vc]
                    if sub_vc.empty:
                        st.info("The selected vendor category was not found.")
                        st.stop()
                    vc_row = sub_vc.iloc[0]
                    
                    edit_vc_name = st.text_input("Category Name", value=vc_row["Category"], key="vc_edit_name")
                    edit_vc_status = st.selectbox("Status", ["Active", "Inactive"], index=0 if vc_row["Status"] == "Active" else 1, key="vc_edit_status")
                    
                    if st.button("💾 Update Category", key="vc_update_btn", use_container_width=True):
                        if not edit_vc_name:
                            st.error("Category name is required.")
                        else:
                            idx = df_vc[df_vc["Category"] == selected_vc].index[0]
                            df_vc.at[idx, "Category"] = edit_vc_name
                            df_vc.at[idx, "Status"] = edit_vc_status
                            save_vendor_categories_df(df_vc)
                            st.success("Vendor Category updated successfully!")
                            st.rerun()
                            
    elif action_vc == "Deactivate Category":
        if df_vc.empty:
            st.info("No vendor categories available.")
        else:
            with col_form_vc:
                with st.container(border=True):
                    st.markdown("**Deactivate Vendor Category**")
                    deact_vc = st.selectbox("Select Category", df_vc["Category"].tolist(), key="vc_deact_select")
                    if st.button("Deactivate Category", key="vc_deact_btn", use_container_width=True):
                        idx = df_vc[df_vc["Category"] == deact_vc].index[0]
                        df_vc.at[idx, "Status"] = "Inactive"
                        save_vendor_categories_df(df_vc)
                        st.warning("Category deactivated successfully.")
                        st.rerun()

# ===========================================================
# 6. Material Categories Tab
# ===========================================================
with tab_mat_cat:
    st.markdown("### 📦 Material Categories")
    
    col_exp_mc, col_imp_mc = st.columns(2)
    with col_exp_mc:
        with st.container(border=True):
            st.markdown("**📤 Export Material Categories**")
            csv_mc = df_mc.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Export Material Categories CSV", data=csv_mc, file_name="material_categories.csv", mime="text/csv", use_container_width=True)
    with col_imp_mc:
        with st.container(border=True):
            st.markdown("**📥 Import Material Categories**")
            uploaded_file_mc = st.file_uploader("Upload Material Categories CSV", type="csv", key="mc_uploader", label_visibility="collapsed")
            if uploaded_file_mc is not None:
                try:
                    uploaded_df_mc = pd.read_csv(uploaded_file_mc)
                    if "Category" in uploaded_df_mc.columns:
                        save_material_categories_df(uploaded_df_mc)
                        st.success("Material Categories updated successfully!")
                        st.rerun()
                    else:
                        st.error("Missing column. CSV must contain 'Category'.")
                except Exception as e:
                    st.error("The uploaded file could not be processed. Please check the format and try again.")
                    
    st.write("---")
    st.markdown("#### Existing Material Categories")
    st.dataframe(df_mc, use_container_width=True, hide_index=True)
    
    st.write("---")
    st.markdown("#### Add / Edit Category")
    
    col_act_mc, col_form_mc = st.columns([1, 2])
    with col_act_mc:
        action_mc = st.radio("Material Category Action", ["Add Category", "Edit Category", "Deactivate Category"], key="mc_action")
        
    if action_mc == "Add Category":
        with col_form_mc:
            with st.container(border=True):
                st.markdown("**Create Material Category**")
                new_mc_name = st.text_input("Category Name", key="mc_new_name")
                
                if st.button("💾 Save Category", key="mc_save_btn", use_container_width=True):
                    if not new_mc_name:
                        st.error("Category name is required.")
                    elif not df_mc.empty and new_mc_name.strip().lower() in df_mc["Category"].str.strip().str.lower().values:
                        st.error("Duplicate Category detected.")
                    else:
                        new_row = pd.DataFrame([{"Category": new_mc_name, "Status": "Active"}])
                        df_mc = pd.concat([df_mc, new_row], ignore_index=True)
                        save_material_categories_df(df_mc)
                        st.success("Material Category added successfully!")
                        st.rerun()
                        
    elif action_mc == "Edit Category":
        if df_mc.empty:
            st.info("No material categories available.")
        else:
            with col_form_mc:
                with st.container(border=True):
                    st.markdown("**Modify Material Category**")
                    selected_mc = st.selectbox("Select Category", df_mc["Category"].tolist(), key="mc_select")
                    sub_mc = df_mc[df_mc["Category"] == selected_mc]
                    if sub_mc.empty:
                        st.info("The selected material category was not found.")
                        st.stop()
                    mc_row = sub_mc.iloc[0]
                    
                    edit_mc_name = st.text_input("Category Name", value=mc_row["Category"], key="mc_edit_name")
                    edit_mc_status = st.selectbox("Status", ["Active", "Inactive"], index=0 if mc_row["Status"] == "Active" else 1, key="mc_edit_status")
                    
                    if st.button("💾 Update Category", key="mc_update_btn", use_container_width=True):
                        if not edit_mc_name:
                            st.error("Category name is required.")
                        else:
                            idx = df_mc[df_mc["Category"] == selected_mc].index[0]
                            df_mc.at[idx, "Category"] = edit_mc_name
                            df_mc.at[idx, "Status"] = edit_mc_status
                            save_material_categories_df(df_mc)
                            st.success("Material Category updated successfully!")
                            st.rerun()
                            
    elif action_mc == "Deactivate Category":
        if df_mc.empty:
            st.info("No material categories available.")
        else:
            with col_form_mc:
                with st.container(border=True):
                    st.markdown("**Deactivate Material Category**")
                    deact_mc = st.selectbox("Select Category", df_mc["Category"].tolist(), key="mc_deact_select")
                    if st.button("Deactivate Category", key="mc_deact_btn", use_container_width=True):
                        idx = df_mc[df_mc["Category"] == deact_mc].index[0]
                        df_mc.at[idx, "Status"] = "Inactive"
                        save_material_categories_df(df_mc)
                        st.warning("Category deactivated successfully.")
                        st.rerun()

with tab_ext:
    st.write("### 🌐 External Events Context Registry")
    st.write("Manage external events (festivals, conferences, college fests) that occur near properties to provide planning awareness.")
    
    from src.integrations.external_events_db import load_external_events, save_external_event, delete_external_event
    df_ext = clean_dataframe_for_ui(load_external_events())
    
    # 1. Table & Export
    st.markdown("#### 📋 Existing Registry")
    if df_ext.empty:
        st.info("No external events found.")
    else:
        df_ext_display = df_ext.copy()

        page_size = 5
        total_rows = len(df_ext_display)
        total_pages = max(1, (total_rows - 1) // page_size + 1)
        
        page_key = "ext_current_page"
        if page_key not in st.session_state:
            st.session_state[page_key] = 1
            
        col_prev, col_info, col_next = st.columns([1, 4, 1])
        with col_prev:
            if st.button("⬅️ Prev", key="ext_btn_prev") and st.session_state[page_key] > 1:
                st.session_state[page_key] -= 1
        with col_info:
            st.write(f"<p style='text-align: center;'>Page {st.session_state[page_key]} of {total_pages} (Total: {total_rows})</p>", unsafe_allow_html=True)
        with col_next:
            if st.button("Next ➡", key="ext_btn_next") and st.session_state[page_key] < total_pages:
                st.session_state[page_key] += 1
                
        start_idx = (st.session_state[page_key] - 1) * page_size
        end_idx = min(start_idx + page_size, total_rows)
        
        st.dataframe(df_ext_display.iloc[start_idx:end_idx], use_container_width=True)
        
        csv_data = df_ext.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export Registry (CSV)",
            data=csv_data,
            file_name="external_events.csv",
            mime="text/csv",
            use_container_width=True,
            key="ext_export_btn"
        )
        
    st.write("---")
    
    # 2. CSV Import / Bulk Import
    st.markdown("#### 📤 CSV Import / Bulk Import")
    uploaded_file = st.file_uploader("Upload external_events.csv to merge/bulk import", type=["csv"], key="ext_uploader")
    if uploaded_file is not None:
        try:
            up_df = pd.read_csv(uploaded_file)
            required_fields = ["Event Name", "Category", "City", "Start Date", "End Date"]
            missing = [f for f in required_fields if f not in up_df.columns]
            if missing:
                st.error(f"Invalid schema. Missing required columns: {', '.join(missing)}")
            else:
                if st.button("⚡ Execute Bulk Import"):
                    for _, row in up_df.iterrows():
                        save_external_event(row.to_dict())
                    st.success("Successfully imported/merged external events!")
                    st.rerun()
        except Exception as e:
            st.error(f"Failed to parse CSV file: {str(e)}")
            
    st.write("---")
    
    # 3. Actions Workspace
    col_menu_ext, col_form_ext = st.columns([1, 2])
    with col_menu_ext:
        action_ext = st.radio("Actions Menu", ["Add External Event", "Edit External Event", "Archive/Delete Event"], key="ext_action")
        
    if action_ext == "Add External Event":
        with col_form_ext:
            with st.container(border=True):
                st.markdown("**Create New External Event**")
                
                new_ext_name = st.text_input("Event Name", key="ext_new_name")
                new_ext_cat = st.selectbox("Category", ["Tech Conferences", "Music Festivals", "College Festivals", "Sports Events", "Exhibitions", "Weekend Markets", "Holiday Celebrations", "Corporate Events", "Local Concerts", "City Festivals"], key="ext_new_cat")
                new_ext_desc = st.text_area("Description", key="ext_new_desc")
                
                col1, col2 = st.columns(2)
                with col1:
                    new_ext_city = st.selectbox("City", ["Bengaluru", "Delhi", "Pune", "Mumbai", "Hyderabad"], key="ext_new_city")
                    new_ext_area = st.text_input("Area", key="ext_new_area")
                    new_ext_lat = st.number_input("Latitude", value=12.9716, format="%.4f", key="ext_new_lat")
                    new_ext_lon = st.number_input("Longitude", value=77.5946, format="%.4f", key="ext_new_lon")
                with col2:
                    new_ext_rad = st.number_input("Affecting Radius (km)", value=5.0, min_value=0.5, max_value=50.0, key="ext_new_rad")
                    new_ext_start = st.date_input("Start Date", key="ext_new_start")
                    new_ext_end = st.date_input("End Date", key="ext_new_end")
                    new_ext_foot = st.number_input("Expected Footfall", value=1000, min_value=1, key="ext_new_foot")
                    
                col3, col4 = st.columns(2)
                with col3:
                    new_ext_audience = st.text_input("Target Audience", value="All", key="ext_new_audience")
                    new_ext_org = st.text_input("Organizer", key="ext_new_org")
                    new_ext_venue = st.text_input("Venue", key="ext_new_venue")
                    new_ext_web = st.text_input("Website Link", key="ext_new_web")
                with col4:
                    new_ext_reg = st.text_input("Registration Link", key="ext_new_reg")
                    new_ext_type = st.selectbox("Free/Paid", ["Free", "Paid"], key="ext_new_type")
                    new_ext_pop = st.selectbox("Popularity", ["Low", "Medium", "High"], key="ext_new_pop")
                    new_ext_occ = st.number_input("Expected Occupancy Impact %", value=5.0, min_value=-50.0, max_value=100.0, key="ext_new_occ")
                    
                new_ext_comm = st.selectbox("Expected Community Impact", ["Low", "Medium", "High"], key="ext_new_comm")
                new_ext_tags = st.text_input("Tags (comma separated)", key="ext_new_tags")
                
                if st.button("💾 Save External Event", key="ext_save_btn", use_container_width=True):
                    if not new_ext_name:
                        st.error("Event Name is required.")
                    else:
                        save_external_event({
                            "Event Name": new_ext_name,
                            "Category": new_ext_cat,
                            "Description": new_ext_desc,
                            "City": new_ext_city,
                            "Area": new_ext_area,
                            "Latitude": new_ext_lat,
                            "Longitude": new_ext_lon,
                            "Property Radius (km)": new_ext_rad,
                            "Start Date": new_ext_start.strftime("%Y-%m-%d"),
                            "End Date": new_ext_end.strftime("%Y-%m-%d"),
                            "Expected Footfall": new_ext_foot,
                            "Target Audience": new_ext_audience,
                            "Organizer": new_ext_org,
                            "Venue": new_ext_venue,
                            "Website": new_ext_web,
                            "Registration Link": new_ext_reg,
                            "Free/Paid": new_ext_type,
                            "Estimated Popularity": new_ext_pop,
                            "Expected Occupancy Impact": new_ext_occ,
                            "Expected Community Impact": new_ext_comm,
                            "Tags": new_ext_tags,
                            "Status": "Active",
                            "Created By": "Manager"
                        })
                        st.success("External Event registered successfully!")
                        st.rerun()
                        
    elif action_ext == "Edit External Event":
        if df_ext.empty:
            st.info("No external events registered yet.")
        else:
            with col_form_ext:
                with st.container(border=True):
                    st.markdown("**Modify Existing External Event**")
                    selected_lbl = st.selectbox("Select Event", [f"{r['Event Name']} [{r['Event ID']}]" for _, r in df_ext.iterrows()], key="ext_edit_select")
                    event_id = selected_lbl.split("[")[-1].rstrip("]")
                    sub_e = df_ext[df_ext["Event ID"] == event_id]
                    if sub_e.empty:
                        st.info("Event not found.")
                        st.stop()
                    e_row = sub_e.iloc[0]
                    
                    edit_ext_name = st.text_input("Event Name", value=e_row["Event Name"], key="ext_edit_name")
                    edit_ext_cat = st.selectbox("Category", ["Tech Conferences", "Music Festivals", "College Festivals", "Sports Events", "Exhibitions", "Weekend Markets", "Holiday Celebrations", "Corporate Events", "Local Concerts", "City Festivals"], index=["Tech Conferences", "Music Festivals", "College Festivals", "Sports Events", "Exhibitions", "Weekend Markets", "Holiday Celebrations", "Corporate Events", "Local Concerts", "City Festivals"].index(e_row["Category"]) if e_row["Category"] in ["Tech Conferences", "Music Festivals", "College Festivals", "Sports Events", "Exhibitions", "Weekend Markets", "Holiday Celebrations", "Corporate Events", "Local Concerts", "City Festivals"] else 0, key="ext_edit_cat")
                    edit_ext_desc = st.text_area("Description", value=e_row["Description"], key="ext_edit_desc")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        edit_ext_city = st.selectbox("City", ["Bengaluru", "Delhi", "Pune", "Mumbai", "Hyderabad"], index=["Bengaluru", "Delhi", "Pune", "Mumbai", "Hyderabad"].index(e_row["City"]) if e_row["City"] in ["Bengaluru", "Delhi", "Pune", "Mumbai", "Hyderabad"] else 0, key="ext_edit_city")
                        edit_ext_area = st.text_input("Area", value=e_row["Area"], key="ext_edit_area")
                        edit_ext_lat = st.number_input("Latitude", value=float(e_row["Latitude"]) if e_row["Latitude"] != "" else 12.9716, format="%.4f", key="ext_edit_lat")
                        edit_ext_lon = st.number_input("Longitude", value=float(e_row["Longitude"]) if e_row["Longitude"] != "" else 77.5946, format="%.4f", key="ext_edit_lon")
                    with col2:
                        edit_ext_rad = st.number_input("Affecting Radius (km)", value=float(e_row["Property Radius (km)"]) if e_row["Property Radius (km)"] != "" else 5.0, min_value=0.5, max_value=50.0, key="ext_edit_rad")
                        edit_ext_start = st.date_input("Start Date", value=datetime.datetime.strptime(e_row["Start Date"], "%Y-%m-%d").date() if e_row["Start Date"] else datetime.date.today(), key="ext_edit_start")
                        edit_ext_end = st.date_input("End Date", value=datetime.datetime.strptime(e_row["End Date"], "%Y-%m-%d").date() if e_row["End Date"] else datetime.date.today(), key="ext_edit_end")
                        edit_ext_foot = st.number_input("Expected Footfall", value=int(e_row["Expected Footfall"]) if e_row["Expected Footfall"] != "" else 1000, min_value=1, key="ext_edit_foot")
                        
                    col3, col4 = st.columns(2)
                    with col3:
                        edit_ext_audience = st.text_input("Target Audience", value=e_row["Target Audience"], key="ext_edit_audience")
                        edit_ext_org = st.text_input("Organizer", value=e_row["Organizer"], key="ext_edit_org")
                        edit_ext_venue = st.text_input("Venue", value=e_row["Venue"], key="ext_edit_venue")
                        edit_ext_web = st.text_input("Website Link", value=e_row["Website"], key="ext_edit_web")
                    with col4:
                        edit_ext_reg = st.text_input("Registration Link", value=e_row["Registration Link"], key="ext_edit_reg")
                        edit_ext_type = st.selectbox("Free/Paid", ["Free", "Paid"], index=0 if e_row["Free/Paid"] == "Free" else 1, key="ext_edit_type")
                        edit_ext_pop = st.selectbox("Popularity", ["Low", "Medium", "High"], index=["Low", "Medium", "High"].index(e_row["Estimated Popularity"]) if e_row["Estimated Popularity"] in ["Low", "Medium", "High"] else 1, key="ext_edit_pop")
                        edit_ext_occ = st.number_input("Expected Occupancy Impact %", value=float(e_row["Expected Occupancy Impact"]) if e_row["Expected Occupancy Impact"] != "" else 5.0, min_value=-50.0, max_value=100.0, key="ext_edit_occ")
                        
                    edit_ext_comm = st.selectbox("Expected Community Impact", ["Low", "Medium", "High"], index=["Low", "Medium", "High"].index(e_row["Expected Community Impact"]) if e_row["Expected Community Impact"] in ["Low", "Medium", "High"] else 1, key="ext_edit_comm")
                    edit_ext_tags = st.text_input("Tags (comma separated)", value=e_row["Tags"], key="ext_edit_tags")
                    edit_ext_status = st.selectbox("Status", ["Active", "Archived"], index=0 if e_row["Status"] == "Active" else 1, key="ext_edit_status")
                    
                    if st.button("💾 Update External Event", key="ext_update_btn", use_container_width=True):
                        if not edit_ext_name:
                            st.error("Event Name is required.")
                        else:
                            save_external_event({
                                "Event ID": event_id,
                                "Event Name": edit_ext_name,
                                "Category": edit_ext_cat,
                                "Description": edit_ext_desc,
                                "City": edit_ext_city,
                                "Area": edit_ext_area,
                                "Latitude": edit_ext_lat,
                                "Longitude": edit_ext_lon,
                                "Property Radius (km)": edit_ext_rad,
                                "Start Date": edit_ext_start.strftime("%Y-%m-%d"),
                                "End Date": edit_ext_end.strftime("%Y-%m-%d"),
                                "Expected Footfall": edit_ext_foot,
                                "Target Audience": edit_ext_audience,
                                "Organizer": edit_ext_org,
                                "Venue": edit_ext_venue,
                                "Website": edit_ext_web,
                                "Registration Link": edit_ext_reg,
                                "Free/Paid": edit_ext_type,
                                "Estimated Popularity": edit_ext_pop,
                                "Expected Occupancy Impact": edit_ext_occ,
                                "Expected Community Impact": edit_ext_comm,
                                "Tags": edit_ext_tags,
                                "Status": edit_ext_status
                            })
                            st.success("External Event updated successfully!")
                            st.rerun()
                            
    elif action_ext == "Archive/Delete Event":
        if df_ext.empty:
            st.info("No external events registered yet.")
        else:
            with col_form_ext:
                with st.container(border=True):
                    st.markdown("**Archive or Delete External Event**")
                    selected_lbl = st.selectbox("Select Event", [f"{r['Event Name']} [{r['Event ID']}]" for _, r in df_ext.iterrows()], key="ext_del_select")
                    event_id = selected_lbl.split("[")[-1].rstrip("]")
                    
                    col_b1, col_b2 = st.columns(2)
                    with col_b1:
                        if st.button("📁 Archive Event", key="ext_archive_btn", use_container_width=True):
                            save_external_event({"Event ID": event_id, "Status": "Archived"})
                            st.warning("Event archived successfully.")
                            st.rerun()
                    with col_b2:
                        if st.button("🗑️ Delete Event", key="ext_del_btn", use_container_width=True):
                            delete_external_event(event_id)
                            st.error("Event deleted from database.")
                            st.rerun()
