import sys
import json
from pathlib import Path
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="TribeIQ - Vendor Management",
    page_icon="🏪",
    layout="wide"
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from src.auth.session_manager import require_login
require_login("Vendor Management")

from ui.components import page_header
from integrations.vendor_db import (
    load_vendors, add_vendor, edit_vendor, 
    delete_or_deactivate_vendor, get_vendor_categories,
    update_vendor_statistics, VENDOR_SUMMARY_CSV
)
from ui.styles import load_css
from utils.schema_utils import safe_get_column, safe_status_column, safe_numeric_column, safe_column_exists

# Load CSS Theme
load_css()

# Load current vendors
vendors_df = load_vendors()

# ===========================================================
# SECTION 1: Vendor Workspace Header
# ===========================================================
st.write("## 🏪 Vendor Workspace & Supplier Ledger")
st.write("Track supplier profiles, billing details, satisfaction ratings, and procurement activity.")

try:
    # Resolve columns
    status_col = safe_status_column(vendors_df) or "Active / Inactive Status"
    fc_col = safe_get_column(vendors_df, ["Final Cost", "Cost", "Total Spent", "Spend"]) or "Final Cost"
    name_col = safe_get_column(vendors_df, ["Vendor Name", "Name", "Vendor"]) or "Vendor Name"
    cat_col = safe_get_column(vendors_df, ["Vendor Category", "Category", "Vendor Category"]) or "Vendor Category"
    id_col = safe_get_column(vendors_df, ["Vendor ID", "ID", "Vendor ID"]) or "Vendor ID"
    cp_col = safe_get_column(vendors_df, ["Contact Person", "Contact", "Contact Person"]) or "Contact Person"
    rating_col = safe_get_column(vendors_df, ["Average Rating", "Rating", "Average Rating"]) or "Average Rating"
    base_col = safe_get_column(vendors_df, ["Base Amount", "Base", "Base Amount"]) or "Base Amount"

    # Calculate counts
    total_vendors = len(vendors_df)
    active_vendors = len(vendors_df[vendors_df[status_col].astype(str).str.strip().str.lower() == "active"]) if not vendors_df.empty and status_col in vendors_df.columns else 0
    inactive_vendors = len(vendors_df[vendors_df[status_col].astype(str).str.strip().str.lower() == "inactive"]) if not vendors_df.empty and status_col in vendors_df.columns else 0
    total_spend = vendors_df[fc_col].sum() if not vendors_df.empty and fc_col in vendors_df.columns else 0.0

    col_h1, col_h2, col_h3, col_h4 = st.columns(4)
    with col_h1:
        st.metric("Total Suppliers Registered", f"{total_vendors}")
    with col_h2:
        st.metric("Active Partners", f"{active_vendors}")
    with col_h3:
        st.metric("Inactive Records", f"{inactive_vendors}")
    with col_h4:
        st.metric("Total Settled Procurement", f"₹{total_spend:,.0f}")
except Exception as e:
    st.warning("⚠ Unable to load this widget.")

col_qa1, col_qa2 = st.columns(2)
with col_qa1:
    csv_v = vendors_df.to_csv(index=False).encode("utf-8") if not vendors_df.empty else b""
    st.download_button("📥 Export Vendor Catalog CSV", data=csv_v, file_name="vendors_catalog.csv", mime="text/csv", use_container_width=True)
with col_qa2:
    if st.button("🔄 Reload Registry Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ===========================================================
# SECTION 2: Executive KPI Cards (Error Boundary)
# ===========================================================
st.write("---")
st.write("### 📊 Executive Performance KPIs")

try:
    k_col1, k_col2, k_col3 = st.columns(3)
    avg_rating = vendors_df[rating_col].mean() if not vendors_df.empty and rating_col in vendors_df.columns else 4.2
    avg_cost = vendors_df[fc_col].mean() if not vendors_df.empty and fc_col in vendors_df.columns else 0.0

    with k_col1:
        st.metric("Average Supplier Rating", f"{avg_rating:.2f} / 5.0")
    with k_col2:
        st.metric("Average Base Cost", f"₹{avg_cost:,.2f}")
    with k_col3:
        if not vendors_df.empty and fc_col in vendors_df.columns and name_col in vendors_df.columns:
            sorted_v = vendors_df.sort_values(by=fc_col, ascending=False)
            top_v = sorted_v.iloc[0][name_col] if len(sorted_v) > 0 else "N/A"
            st.metric("Primary Contractor", top_v)
        else:
            st.metric("Primary Contractor", "N/A")
except Exception as e:
    st.warning("⚠ Unable to load this widget.")

# ===========================================================
# SECTION 3: Vendor Directory Table (Error Boundary)
# ===========================================================
st.write("---")
st.write("### 📜 Directory Listings")

try:
    col_search, col_f_cat, col_f_stat = st.columns(3)
    with col_search:
        search_query = st.text_input("🔍 Search Directory", placeholder="Search by name, category...", key="v_search")
    with col_f_cat:
        all_cats = ["All"] + get_vendor_categories()
        filter_category = st.selectbox("Category Group", options=all_cats)
    with col_f_stat:
        filter_status = st.selectbox("Status Group", options=["All", "Active", "Inactive"])

    # Apply Filters
    filtered_df = vendors_df.copy()
    if search_query:
        mask = (
            filtered_df[name_col].astype(str).str.contains(search_query, case=False, na=False) |
            filtered_df[cat_col].astype(str).str.contains(search_query, case=False, na=False) |
            filtered_df[cp_col].astype(str).str.contains(search_query, case=False, na=False)
        )
        filtered_df = filtered_df[mask]

    if filter_category != "All":
        filtered_df = filtered_df[filtered_df[cat_col] == filter_category]
        
    if filter_status != "All":
        filtered_df = filtered_df[filtered_df[status_col] == filter_status]

    if filtered_df.empty:
        st.info("No matching vendors recorded in database.")
    else:
        display_cols = [c for c in [id_col, name_col, cat_col, cp_col, status_col, fc_col] if c in filtered_df.columns]
        st.dataframe(filtered_df[display_cols], use_container_width=True, hide_index=True)
except Exception as e:
    st.warning("⚠ Unable to load this widget.")

# ===========================================================
# SECTION 4: Add New Vendor
# ===========================================================
st.write("---")
st.write("### ➕ Register New Vendor Profile")

try:
    with st.form("add_vendor_form"):
        col_a, col_b = st.columns(2)
        with col_a:
            v_name = st.text_input("Vendor Name", placeholder="e.g. Pune Sound & Light System")
            pre_cats = get_vendor_categories()
            v_cat_selected = st.selectbox("Vendor Category", options=pre_cats + ["Add Custom Category..."])
            v_custom_cat = ""
            if v_cat_selected == "Add Custom Category...":
                v_custom_cat = st.text_input("Enter Custom Category")
            v_contact = st.text_input("Contact Person")
            v_phone = st.text_input("Phone Number")
            v_email = st.text_input("Email Address")
        with col_b:
            v_gst_num = st.text_input("GST Number (Optional)", max_chars=15)
            v_address = st.text_input("Office Address")
            v_desc = st.text_area("Notes / Description", height=80)
            v_base = st.number_input("Base Amount (INR)", min_value=0.0, value=0.0, step=100.0)
            v_gst_pct = st.selectbox("GST Class %", options=[12, 18], index=1)
            
            gst_amt = round((v_base * v_gst_pct) / 100.0, 2)
            final_cost = round(v_base + gst_amt, 2)
            st.write(f"**Calculated GST:** ₹{gst_amt}")
            st.write(f"**Calculated Final Cost:** ₹{final_cost}")
            
        v_status = st.selectbox("Status", options=["Active", "Inactive"])
        submit_add = st.form_submit_button("💾 Add Vendor to Ledger", type="primary", use_container_width=True)
        if submit_add:
            category_to_save = v_custom_cat if v_cat_selected == "Add Custom Category..." else v_cat_selected
            if not v_name or not category_to_save:
                st.error("Vendor Name and Category are required.")
            else:
                new_v_id = f"VND{len(vendors_df)+1:03d}"
                new_vendor = {
                    "Vendor ID": new_v_id,
                    "Vendor Name": v_name,
                    "Vendor Category": category_to_save,
                    "Contact Person": v_contact,
                    "Phone Number": v_phone,
                    "Email Address": v_email,
                    "GST Number": v_gst_num,
                    "Address": v_address,
                    "Description": v_desc,
                    "Active / Inactive Status": v_status,
                    "Base Amount": v_base,
                    "GST Percentage": v_gst_pct,
                    "GST Amount": gst_amt,
                    "Final Cost": final_cost
                }
                if add_vendor(new_vendor):
                    st.success(f"Vendor '{v_name}' registered successfully with ID {new_v_id}!")
                    st.cache_data.clear()
                    st.rerun()
except Exception as e:
    st.warning("⚠ Unable to load this form.")
    with st.expander("Details"):
        st.write(str(e))

# ===========================================================
# SECTION 8: Quick Actions & Management (Error Boundary)
# ===========================================================
if not vendors_df.empty:
    st.write("---")
    st.write("### 🛠️ Manage Selected Vendor Profile")
    
    try:
        vendor_options = []
        vendor_map = {}
        for idx, row in vendors_df.iterrows():
            v_name = str(row[name_col]) if name_col in row and pd.notna(row[name_col]) else "Unnamed Vendor"
            v_id = str(row[id_col]) if id_col in row and pd.notna(row[id_col]) else f"VND{idx+1:03d}"
            lbl = f"{v_name} [{v_id}]"
            vendor_options.append(lbl)
            vendor_map[lbl] = (v_id, row)

        if not vendor_options:
            st.info("No vendor profiles recorded in database.")
        else:
            selected_vendor_lbl = st.selectbox("Choose Vendor", options=vendor_options)
            if selected_vendor_lbl and selected_vendor_lbl in vendor_map:
                selected_vendor_id, row_data = vendor_map[selected_vendor_lbl]
                
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    st.write(f"#### Profile: {row_data.get(name_col, 'N/A')}")
                    st.markdown(f"* **Category:** {row_data.get(cat_col, 'N/A')}")
                    st.markdown(f"* **Contact:** {row_data.get(cp_col, 'N/A')} ({row_data.get('Phone Number', 'N/A')})")
                    st.markdown(f"* **Email:** {row_data.get('Email Address', 'N/A')}")
                    st.markdown(f"* **GST Number:** {row_data.get('GST Number', 'N/A')}")
                    st.markdown(f"* **Base Amount:** ₹{float(row_data.get(base_col, 0.0)):,.2f}")
                    st.markdown(f"* **Status:** {row_data.get(status_col, 'Active')}")
                    
                with col_e2:
                    st.write("**Quick Actions:**")
                    current_stat = row_data.get(status_col, "Active")
                    if st.button("Deactivate Vendor Record" if current_stat == "Active" else "Reactivate Vendor Record", use_container_width=True):
                        new_stat = "Inactive" if current_stat == "Active" else "Active"
                        updated = row_data.to_dict()
                        updated[status_col] = new_stat
                        if edit_vendor(selected_vendor_id, updated):
                            st.success("Vendor status toggled successfully!")
                            st.cache_data.clear()
                            st.rerun()
                            
                    if st.button("🗑️ Delete Vendor Permanently", use_container_width=True):
                        if delete_or_deactivate_vendor(selected_vendor_id):
                            st.warning("Vendor record removed from database.")
                            st.cache_data.clear()
                            st.rerun()
    except Exception as e:
        st.warning("⚠ Unable to load this widget.")
        with st.expander("Details"):
            st.write(str(e))
