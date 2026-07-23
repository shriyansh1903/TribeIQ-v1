import sys
import streamlit as st
import pandas as pd
import datetime
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import importlib
import src.auth.session_manager as session_mgr

# Force reload session_mgr if running in long-lived Streamlit server process with stale module cache
if not hasattr(session_mgr, "ALL_SYSTEM_PERMISSIONS") or not hasattr(session_mgr, "get_user_effective_permissions"):
    importlib.reload(session_mgr)

ALL_SYSTEM_PERMISSIONS = getattr(session_mgr, "ALL_SYSTEM_PERMISSIONS", [
    "Dashboard", "Resident Profiles", "Recommendations", "Log Event", 
    "Analytics", "Settings", "Vendor Management", "Community Calendar", 
    "Master Data", "User Management", "Master Event Planner", "AI Community Copilot"
])
ROLE_PERMISSIONS = getattr(session_mgr, "ROLE_PERMISSIONS", {})
require_login = getattr(session_mgr, "require_login")
logout = getattr(session_mgr, "logout")

def get_user_effective_permissions(u_doc: dict) -> list:
    if hasattr(session_mgr, "get_user_effective_permissions"):
        return session_mgr.get_user_effective_permissions(u_doc)
    if not u_doc:
        return []
    u_role = u_doc.get("role", "Read Only")
    if u_role in ["Admin", "SuperAdmin"]:
        return ALL_SYSTEM_PERMISSIONS.copy()
    c_perms = u_doc.get("permissions")
    if c_perms is not None and isinstance(c_perms, list):
        return c_perms
    return ROLE_PERMISSIONS.get(u_role, ["Dashboard", "Community Calendar", "Settings"])

from src.auth.auth_service import auth_service
from src.repositories import UsersRepository
from ui.styles import load_css

st.set_page_config(
    page_title="TribeIQ - User Administration",
    page_icon="👤",
    layout="wide"
)

# Protect page: only Admin users can load it
require_login("User Management")
load_css()

users_repo = UsersRepository()

st.markdown("## 👤 User Operations & Administration")
st.markdown("*Create, edit, reset passwords, manage system permissions, and update credentials.*")
st.write("")

# ---------------------------------------------------------
# Load User Data
# ---------------------------------------------------------
try:
    users_list = users_repo.find_all()
except Exception as e:
    st.error(f"Failed to query users database: {str(e)}")
    users_list = []

# Format as DataFrame
if users_list:
    df_users = pd.DataFrame(users_list)
    # Remove password hash from display
    if "password_hash" in df_users.columns:
        df_users = df_users.drop(columns=["password_hash"])
    # Add summary of permissions column for registry grid
    if not df_users.empty:
        df_users["effective_permissions"] = df_users.apply(
            lambda r: "All Pages (Admin)" if r.get("role") in ["Admin", "SuperAdmin"]
            else f"Custom ({len(r.get('permissions'))} pages)" if isinstance(r.get("permissions"), list)
            else f"Role Default ({r.get('role', 'Read Only')})",
            axis=1
        )
else:
    df_users = pd.DataFrame()

# ---------------------------------------------------------
# SECTION 1: Users Grid Registry
# ---------------------------------------------------------
st.markdown("### 📋 User Accounts Registry")

if df_users.empty:
    st.info("No users registered in the system database.")
else:
    # Filter / Search bar
    search_query = st.text_input("🔍 Search Users (Username / Email / Display Name / Role)", "").strip().lower()
    
    filtered_df = df_users.copy()
    if search_query:
        mask = (
            filtered_df["username"].astype(str).str.lower().str.contains(search_query) |
            filtered_df["email"].astype(str).str.lower().str.contains(search_query) |
            filtered_df["display_name"].astype(str).str.lower().str.contains(search_query) |
            filtered_df["role"].astype(str).str.lower().str.contains(search_query)
        )
        filtered_df = filtered_df[mask]

    # Paginated view
    page_size = 10
    total_rows = len(filtered_df)
    total_pages = max(1, (total_rows - 1) // page_size + 1)
    
    page_key = "user_mgmt_current_page"
    if page_key not in st.session_state:
        st.session_state[page_key] = 1
        
    col_prev, col_info, col_next = st.columns([1, 4, 1])
    with col_prev:
        if st.button("⬅️ Previous", key="um_btn_prev") and st.session_state[page_key] > 1:
            st.session_state[page_key] -= 1
    with col_info:
        st.write(f"<p style='text-align: center;'>Page {st.session_state[page_key]} of {total_pages} (Total Records: {total_rows})</p>", unsafe_allow_html=True)
    with col_next:
        if st.button("Next ➡", key="um_btn_next") and st.session_state[page_key] < total_pages:
            st.session_state[page_key] += 1
            
    start_idx = (st.session_state[page_key] - 1) * page_size
    end_idx = min(start_idx + page_size, total_rows)
    
    st.dataframe(filtered_df.iloc[start_idx:end_idx], use_container_width=True)

st.write("---")

# ---------------------------------------------------------
# SECTION 2: User Action Center
# ---------------------------------------------------------
col_menu, col_workspace = st.columns([1, 2])

with col_menu:
    st.markdown("### ⚡ Action Panel")
    action = st.radio("Choose Action", ["Add New User", "Edit User Attributes", "Manage Permissions", "Reset Password", "Enable / Disable Account"])

if action == "Add New User":
    with col_workspace:
        with st.container(border=True):
            st.markdown("#### ➕ Register New System User")
            
            new_username = st.text_input("Username", key="new_username").strip()
            new_display = st.text_input("Display Name", key="new_display").strip()
            new_email = st.text_input("Email Address", key="new_email").strip()
            new_pwd = st.text_input("Password", type="password", key="new_pwd")
            new_confirm = st.text_input("Confirm Password", type="password", key="new_confirm")
            
            new_role = st.selectbox("Assign User Role", ["Admin", "Community Manager", "Read Only"], key="new_role")
            
            if st.button("💾 Create User Account", type="primary", use_container_width=True):
                if not new_username or not new_pwd:
                    st.error("Username and password are required.")
                elif new_pwd != new_confirm:
                    st.error("Passwords do not match.")
                else:
                    uid, msg = auth_service.create_user(
                        username=new_username,
                        email=new_email,
                        display_name=new_display,
                        password=new_pwd,
                        role=new_role
                    )
                    if uid:
                        st.success(f"User account '{new_username}' created successfully!")
                        st.rerun()
                    else:
                        st.error(f"Failed: {msg}")

elif action == "Edit User Attributes":
    with col_workspace:
        if df_users.empty:
            st.info("No users available to edit.")
        else:
            with st.container(border=True):
                st.markdown("#### ✏️ Modify User Attributes")
                selected_username = st.selectbox("Select User", df_users["username"].tolist(), key="edit_select")
                
                # Fetch user doc
                u_doc = users_repo.find_by_username(selected_username)
                if not u_doc:
                    st.error("User not found.")
                    st.stop()
                    
                edit_display = st.text_input("Display Name", value=u_doc.get("display_name", ""), key="edit_display")
                edit_email = st.text_input("Email Address", value=u_doc.get("email", ""), key="edit_email")
                edit_role = st.selectbox("Assign User Role", ["Admin", "Community Manager", "Read Only"], index=["Admin", "Community Manager", "Read Only"].index(u_doc.get("role", "Read Only")), key="edit_role")
                
                if st.button("💾 Save Attributes", type="primary", use_container_width=True):
                    update_data = {
                        "display_name": edit_display,
                        "email": edit_email,
                        "role": edit_role,
                        "updated_at": datetime.datetime.now(datetime.timezone.utc)
                    }
                    if users_repo.update(str(u_doc["_id"]), update_data):
                        st.success(f"Attributes updated successfully for '{selected_username}'!")
                        st.rerun()
                    else:
                        st.error("Failed to update user record.")

elif action == "Manage Permissions":
    with col_workspace:
        if df_users.empty:
            st.info("No users available to configure permissions.")
        else:
            with st.container(border=True):
                st.markdown("#### 🔐 Access & Page Permissions Management")
                st.markdown("Configure granular page-level access control for individual user accounts.")
                
                selected_username = st.selectbox("Select User Account", df_users["username"].tolist(), key="perm_user_select")
                
                u_doc = users_repo.find_by_username(selected_username)
                if not u_doc:
                    st.error("User not found.")
                    st.stop()
                
                user_role = u_doc.get("role", "Read Only")
                custom_perms = u_doc.get("permissions")
                has_custom = custom_perms is not None and isinstance(custom_perms, list)
                
                # Header status callout
                st.info(f"**Selected User:** `{selected_username}` | **Base Role:** `{user_role}` | **Status:** `{'Custom Overrides Active' if has_custom else 'Inherited from Role'}`")
                
                if user_role in ["Admin", "SuperAdmin"]:
                    st.warning("⚡ Administrator profiles have unrestricted access across all system pages by default.")
                
                current_allowed = get_user_effective_permissions(u_doc)
                
                st.markdown("##### ⚙️ Page Access Control Matrix")
                
                # Preset actions
                p_col1, p_col2, p_col3 = st.columns(3)
                preset_all = p_col1.button("🌐 Select All Pages", use_container_width=True, key="btn_perm_all")
                preset_role = p_col2.button("🔄 Reset to Role Default", use_container_width=True, key="btn_perm_reset")
                preset_read = p_col3.button("👁️ Read-Only Preset", use_container_width=True, key="btn_perm_readonly")
                
                if preset_role:
                    update_data = {
                        "permissions": None,
                        "updated_at": datetime.datetime.now(datetime.timezone.utc)
                    }
                    if users_repo.update(str(u_doc["_id"]), update_data):
                        st.success(f"Reset permissions for '{selected_username}' to role default ({user_role}).")
                        st.rerun()
                    else:
                        st.error("Failed to reset permissions.")
                
                cols = st.columns(2)
                selected_pages = []
                
                for idx, page_item in enumerate(ALL_SYSTEM_PERMISSIONS):
                    c = cols[idx % 2]
                    
                    default_checked = (page_item in current_allowed)
                    if preset_all:
                        default_checked = True
                    elif preset_read:
                        default_checked = (page_item in ROLE_PERMISSIONS["Read Only"])
                        
                    checked = c.checkbox(
                        label=f"📄 {page_item}",
                        value=default_checked,
                        key=f"perm_chk_{selected_username}_{page_item}"
                    )
                    if checked:
                        selected_pages.append(page_item)
                
                st.write("")
                if st.button("💾 Save Custom Permissions Matrix", type="primary", use_container_width=True, key="btn_save_perms"):
                    update_data = {
                        "permissions": selected_pages,
                        "updated_at": datetime.datetime.now(datetime.timezone.utc)
                    }
                    if users_repo.update(str(u_doc["_id"]), update_data):
                        st.success(f"Custom permissions updated successfully for user '{selected_username}'! ({len(selected_pages)} pages enabled)")
                        st.rerun()
                    else:
                        st.error("Failed to update user permissions.")

elif action == "Reset Password":
    with col_workspace:
        if df_users.empty:
            st.info("No users available.")
        else:
            with st.container(border=True):
                st.markdown("#### 🔑 Reset Password")
                selected_username = st.selectbox("Select User", df_users["username"].tolist(), key="pwd_select")
                
                u_doc = users_repo.find_by_username(selected_username)
                if not u_doc:
                    st.error("User not found.")
                    st.stop()
                    
                new_pwd = st.text_input("New Password", type="password", key="pwd_reset_new")
                confirm_pwd = st.text_input("Confirm New Password", type="password", key="pwd_reset_conf")
                
                if st.button("🔑 Save Reset Password", type="primary", use_container_width=True):
                    if not new_pwd:
                        st.error("Password cannot be empty.")
                    elif new_pwd != confirm_pwd:
                        st.error("Passwords do not match.")
                    else:
                        if auth_service.reset_password(str(u_doc["_id"]), new_pwd):
                            st.success(f"Password reset successfully for '{selected_username}'!")
                        else:
                            st.error("Failed to reset password.")

elif action == "Enable / Disable Account":
    with col_workspace:
        if df_users.empty:
            st.info("No users available.")
        else:
            with st.container(border=True):
                st.markdown("#### 📁 Access Control Settings")
                selected_username = st.selectbox("Select User", df_users["username"].tolist(), key="status_select")
                
                u_doc = users_repo.find_by_username(selected_username)
                if not u_doc:
                    st.error("User not found.")
                    st.stop()
                    
                current_status = u_doc.get("status", "Active")
                st.write(f"Current Access Status: **{current_status}**")
                
                action_btn_label = "Disable Account" if current_status == "Active" else "Enable Account"
                
                if st.button(action_btn_label, use_container_width=True):
                    next_status = "Inactive" if current_status == "Active" else "Active"
                    update_data = {
                        "status": next_status,
                        "updated_at": datetime.datetime.now(datetime.timezone.utc)
                    }
                    if users_repo.update(str(u_doc["_id"]), update_data):
                        st.success(f"Account for '{selected_username}' set to '{next_status}' successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to update status.")
