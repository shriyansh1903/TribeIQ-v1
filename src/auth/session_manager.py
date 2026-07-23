import streamlit as st
import datetime
from src.auth.auth_service import auth_service
from src.config import settings, logger

# Roles & Permissions Mapping
ROLE_PERMISSIONS = {
    "Admin": [
        "Dashboard", "Resident Profiles", "Recommendations", "Log Event", 
        "Analytics", "Settings", "Vendor Management", "Community Calendar", 
        "Master Data", "User Management", "Master Event Planner", "AI Community Copilot"
    ],
    "Community Manager": [
        "Dashboard", "Resident Profiles", "Recommendations", "Log Event", 
        "Analytics", "Settings", "Vendor Management", "Community Calendar", 
        "Master Data", "Master Event Planner", "AI Community Copilot"
    ],
    "Read Only": [
        "Dashboard", "Community Calendar", "Settings"
    ]
}

ALL_SYSTEM_PERMISSIONS = [
    "Dashboard",
    "Resident Profiles",
    "Recommendations",
    "Log Event",
    "Analytics",
    "Settings",
    "Vendor Management",
    "Community Calendar",
    "Master Data",
    "User Management",
    "Master Event Planner",
    "AI Community Copilot"
]

def get_user_effective_permissions(user: dict) -> list:
    """Returns list of allowed page names for given user dict, evaluating custom permission overrides."""
    if not user:
        return []
    user_role = user.get("role", "Read Only")
    if user_role in ["Admin", "SuperAdmin"]:
        return ALL_SYSTEM_PERMISSIONS.copy()
    custom_perms = user.get("permissions")
    if custom_perms is not None and isinstance(custom_perms, list):
        return custom_perms
    return ROLE_PERMISSIONS.get(user_role, ["Dashboard", "Community Calendar", "Settings"])

def init_session():
    """Initializes session configuration state attributes."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.user = None
        st.session_state.last_activity = None
        st.session_state.remember_me = False

def check_session_expiry():
    """Checks session expiry based on inactivity timeout."""
    if not st.session_state.get("authenticated"):
        return
        
    # Skip expiry if "Remember Me" is checked
    if st.session_state.get("remember_me"):
        return

    timeout_duration = datetime.timedelta(minutes=30)
    now = datetime.datetime.now(datetime.timezone.utc)
    last_act = st.session_state.get("last_activity")
    
    if last_act:
        # Make last_act timezone aware if missing
        if last_act.tzinfo is None:
            last_act = last_act.replace(tzinfo=datetime.timezone.utc)
            
        if now - last_act > timeout_duration:
            logout()
            st.warning("Session expired due to inactivity. Please log in again.")
            st.rerun()

    st.session_state.last_activity = now

def logout():
    """Logs out current user session."""
    user = st.session_state.get("user")
    if user:
        logger.info(f"User logout: User '{user.get('username')}' logged out.")
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.last_activity = None
    st.session_state.remember_me = False
    st.rerun()

def render_login_form():
    """Renders a beautiful unified Login UI panel."""
    # Ensure layout aligns nicely
    st.write("")
    st.write("")
    
    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
        with st.container(border=True):
            st.markdown(f"<h2 style='text-align: center; color: #FEF3C7;'>🔒 {settings.APP_NAME}</h2>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #8B949E;'>Sign in to access your dashboard</p>", unsafe_allow_html=True)
            st.write("")

            username = st.text_input("Username", placeholder="Enter username", key="login_username")
            password = st.text_input("Password", type="password", placeholder="Enter password", key="login_password")
            
            col_rem, col_blank = st.columns([1, 1])
            with col_rem:
                remember_me = st.checkbox("Remember Me", value=False, key="login_remember")
                
            st.write("")
            login_btn = st.button("Sign In", type="primary", use_container_width=True, key="login_btn")
            
            forgot_pwd = st.button("Forgot Password?", key="forgot_pwd_btn", use_container_width=True)
            if forgot_pwd:
                st.info("ℹ Please contact your system administrator to request a password reset.")

            if login_btn:
                if not username or not password:
                    st.error("Please specify both username and password.")
                else:
                    user_doc, status_msg = auth_service.authenticate_user(username, password)
                    if user_doc:
                        st.session_state.authenticated = True
                        st.session_state.user = user_doc
                        st.session_state.remember_me = remember_me
                        st.session_state.last_activity = datetime.datetime.now(datetime.timezone.utc)
                        st.success("Successfully authenticated!")
                        st.rerun()
                    else:
                        st.error(status_msg)

            st.write("---")
            st.markdown(f"<p style='text-align: center; font-size: 0.8rem; color: #8B949E;'>System Version: v2.2.0 Platform Foundation</p>", unsafe_allow_html=True)

def require_login(page_name: str):
    """
    Page guard middleware. Checks if session is active and checks page level permissions.
    """
    init_session()
    check_session_expiry()

    if not st.session_state.authenticated or not st.session_state.user:
        st.session_state.authenticated = False
        st.session_state.user = None
        render_login_form()
        st.stop()

    # User is authenticated. Verify permission access matrix.
    user = st.session_state.user or {}
    user_role = user.get("role", "Read Only")

    # Admin and SuperAdmin roles have complete access to all pages
    if user_role in ["Admin", "SuperAdmin"]:
        return

    allowed_pages = get_user_effective_permissions(user)
    
    if page_name not in allowed_pages:
        st.error(f"⛔ Access Denied: Your account role/permissions ({user_role}) do not allow access to the '{page_name}' page.")
        # Offer logout
        if st.button("Return to Login/Logout"):
            logout()
        st.stop()

    # If role is Read Only, inject message advising user they have limited permission
    if user_role == "Read Only":
        st.caption("ℹ Read-Only Mode: Your user profile allows read-only visibility across this environment.")

def get_current_user():
    """Returns currently authenticated user dict from session state or None."""
    if hasattr(st, "session_state") and "user" in st.session_state:
        return st.session_state.user
    return None

