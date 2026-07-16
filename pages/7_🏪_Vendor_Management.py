import sys
import json
from pathlib import Path
import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ui.components import page_header
from integrations.vendor_db import (
    load_vendors, add_vendor, edit_vendor, 
    delete_or_deactivate_vendor, get_vendor_categories,
    update_vendor_statistics, VENDOR_SUMMARY_CSV
)

# Page Header
page_header(
    "🏪 Vendor Management",
    "Centralized vendor database to track performance, categorise expenses, and log event vendor bills."
)

# Load current vendors
vendors_df = load_vendors()

# -----------------------------------------------------------
# Search & Filter
# -----------------------------------------------------------
st.subheader("Filter & Search Vendors")
col1, col2, col3 = st.columns(3)
with col1:
    search_query = st.text_input("🔍 Search Vendors", placeholder="Search by name, contact...", help="Search by Vendor Name, Category, or Contact Person.")
with col2:
    all_cats = ["All"] + get_vendor_categories()
    filter_category = st.selectbox("Category", options=all_cats)
with col3:
    filter_status = st.selectbox("Status", options=["All", "Active", "Inactive"])

# Apply Filters
filtered_df = vendors_df.copy()
if search_query:
    mask = (
        filtered_df["Vendor Name"].astype(str).str.contains(search_query, case=False, na=False) |
        filtered_df["Vendor Category"].astype(str).str.contains(search_query, case=False, na=False) |
        filtered_df["Contact Person"].astype(str).str.contains(search_query, case=False, na=False)
    )
    filtered_df = filtered_df[mask]

if filter_category != "All":
    filtered_df = filtered_df[filtered_df["Vendor Category"] == filter_category]
    
if filter_status != "All":
    filtered_df = filtered_df[filtered_df["Active / Inactive Status"] == filter_status]

# -----------------------------------------------------------
# Vendors Data Grid
# -----------------------------------------------------------
st.subheader("Vendor Directory")

if filtered_df.empty:
    st.info("No matching vendors found.")
else:
    # Display clean table
    display_cols = ["Vendor ID", "Vendor Name", "Vendor Category", "Contact Person", "Phone Number", "Email Address", "Active / Inactive Status", "Final Cost"]
    st.dataframe(filtered_df[display_cols], use_container_width=True, hide_index=True)

# -----------------------------------------------------------
# Add Vendor (Expander Form)
# -----------------------------------------------------------
st.divider()
add_expander = st.expander("➕ Add New Vendor", expanded=False)
with add_expander:
    with st.form("add_vendor_form"):
        col_a, col_b = st.columns(2)
        with col_a:
            v_name = st.text_input("Vendor Name", placeholder="e.g. Pune AV Rentals")
            
            # Categories with custom addition support
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
            v_address = st.text_input("Address")
            v_desc = st.text_area("Description / Notes", height=80)
            
            # Financials live input
            v_base = st.number_input("Base Amount (INR)", min_value=0.0, value=0.0, step=100.0)
            v_gst_pct = st.selectbox("GST Percentage", options=[12, 18], index=1)
            
            # Live calculations
            gst_amt = round((v_base * v_gst_pct) / 100.0, 2)
            final_cost = round(v_base + gst_amt, 2)
            st.write(f"**GST Amount:** {gst_amt}")
            st.write(f"**Final Cost (auto-calculated):** {final_cost}")

        v_status = st.selectbox("Status", options=["Active", "Inactive"])
        
        submit_add = st.form_submit_button("Add Vendor", type="primary", use_container_width=True)
        if submit_add:
            category_to_save = v_custom_cat if v_cat_selected == "Add Custom Category..." else v_cat_selected
            if not v_name or not category_to_save:
                st.error("Vendor Name and Category are required.")
            else:
                new_vendor = {
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
                    st.success(f"Vendor '{v_name}' added successfully!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Failed to add vendor.")

# -----------------------------------------------------------
# Manage Selected Vendor (Edit / Delete / Toggle Status)
# -----------------------------------------------------------
if not vendors_df.empty:
    st.divider()
    st.subheader("🛠️ Manage Selected Vendor")
    
    vendor_options = [f"{row['Vendor Name']} [{row['Vendor ID']}]" for _, row in vendors_df.iterrows()]
    selected_vendor_lbl = st.selectbox("Select Vendor to Manage", options=vendor_options)
    
    selected_vendor_id = selected_vendor_lbl.split("[")[-1].rstrip("]")
    selected_vendor_row = vendors_df[vendors_df["Vendor ID"] == selected_vendor_id].iloc[0]

    act_col1, act_col2 = st.columns(2)
    with act_col1:
        show_edit = st.checkbox("📝 Edit Selected Vendor Details", value=False)
    with act_col2:
        show_delete = st.checkbox("❌ Delete / Deactivate Vendor", value=False)

    if show_edit:
        st.markdown("#### Edit Vendor Details")
        with st.form("edit_vendor_form"):
            col_a, col_b = st.columns(2)
            with col_a:
                edit_name = st.text_input("Vendor Name", value=selected_vendor_row["Vendor Name"])
                edit_cat = st.selectbox("Vendor Category", options=get_vendor_categories(), index=get_vendor_categories().index(selected_vendor_row["Vendor Category"]) if selected_vendor_row["Vendor Category"] in get_vendor_categories() else 0)
                edit_contact = st.text_input("Contact Person", value=selected_vendor_row.get("Contact Person", ""))
                edit_phone = st.text_input("Phone Number", value=selected_vendor_row.get("Phone Number", ""))
                edit_email = st.text_input("Email Address", value=selected_vendor_row.get("Email Address", ""))
            
            with col_b:
                edit_gst_num = st.text_input("GST Number (Optional)", value=str(selected_vendor_row.get("GST Number", "")), max_chars=15)
                edit_address = st.text_input("Address", value=str(selected_vendor_row.get("Address", "")))
                edit_desc = st.text_area("Description / Notes", value=str(selected_vendor_row.get("Description", "")), height=80)
                
                edit_base = st.number_input("Base Amount (INR)", min_value=0.0, value=float(selected_vendor_row.get("Base Amount", 0.0)), step=100.0)
                edit_gst_pct = st.selectbox("GST Percentage", options=[12, 18], index=[12, 18].index(int(selected_vendor_row.get("GST Percentage", 18))))
                
                edit_gst_amt = round((edit_base * edit_gst_pct) / 100.0, 2)
                edit_final_cost = round(edit_base + edit_gst_amt, 2)
                st.write(f"**GST Amount:** {edit_gst_amt}")
                st.write(f"**Final Cost (auto-calculated):** {edit_final_cost}")

            edit_status = st.selectbox("Status", options=["Active", "Inactive"], index=["Active", "Inactive"].index(selected_vendor_row["Active / Inactive Status"]))
            
            submit_edit = st.form_submit_button("Save Changes", type="primary", use_container_width=True)
            if submit_edit:
                updated_fields = {
                    "Vendor Name": edit_name,
                    "Vendor Category": edit_cat,
                    "Contact Person": edit_contact,
                    "Phone Number": edit_phone,
                    "Email Address": edit_email,
                    "GST Number": edit_gst_num,
                    "Address": edit_address,
                    "Description": edit_desc,
                    "Active / Inactive Status": edit_status,
                    "Base Amount": edit_base,
                    "GST Percentage": edit_gst_pct,
                    "GST Amount": edit_gst_amt,
                    "Final Cost": edit_final_cost
                }
                if edit_vendor(selected_vendor_id, updated_fields):
                    st.success(f"Vendor '{edit_name}' changes saved successfully!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Failed to edit vendor details.")

    if show_delete:
        st.warning(f"⚠️ Are you sure you want to permanently delete **{selected_vendor_row['Vendor Name']}**?")
        st.write("Note: If the vendor is linked to historical events, they will be automatically marked as Inactive instead of deletion to preserve audit trials.")
        confirm_del = st.checkbox("I confirm deletion of this vendor.")
        if confirm_del:
            if st.button("Delete Vendor", type="primary", use_container_width=True):
                result_msg = delete_or_deactivate_vendor(selected_vendor_id)
                st.success(result_msg)
                st.cache_data.clear()
                st.rerun()

# -----------------------------------------------------------
# Vendor History & Performance Analytics
# -----------------------------------------------------------
st.divider()
st.subheader("📈 Vendor Performance & History")

# Load summaries
update_vendor_statistics()
if VENDOR_SUMMARY_CSV.exists():
    summary_df = pd.read_csv(VENDOR_SUMMARY_CSV)
    if not summary_df.empty:
        st.dataframe(summary_df, use_container_width=True, hide_index=True)
        
        # Display small analytics charts
        st.markdown("#### Vendor Spend by Category")
        spend_by_cat = summary_df.groupby("Category")["Total Amount Paid"].sum().reset_index()
        st.bar_chart(data=spend_by_cat, x="Category", y="Total Amount Paid", use_container_width=True)
        
        # Vendor Ratings Chart
        st.markdown("#### Vendor Ratings Comparison")
        rating_df = summary_df[summary_df["Average Rating"] > 0]
        if not rating_df.empty:
            st.bar_chart(data=rating_df, x="Vendor Name", y="Average Rating", use_container_width=True)
    else:
        st.info("No vendor histories found yet. Run events using the Log Event page to populate.")
else:
    st.info("No vendor performance statistics loaded.")
