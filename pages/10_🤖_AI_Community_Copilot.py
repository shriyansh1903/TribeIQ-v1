import sys
import time
from pathlib import Path
from datetime import date

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from intelligence.copilot_orchestrator import ask_copilot
from ui.styles import load_css

# ===========================================================
# Page Configuration
# ===========================================================

load_css()

# ===========================================================
# Session State Initialization
# ===========================================================

if "copilot_chat_history" not in st.session_state:
    st.session_state["copilot_chat_history"] = []

# ===========================================================
# SECTION 1: Copilot Header
# ===========================================================

st.markdown("## 🤖 AI Community Copilot")
st.markdown(f"*Conversational intelligence layer \u2014 {date.today().strftime('%B %d, %Y')}*")
st.write("")

# Header metrics row
h_col1, h_col2, h_col3, h_col4 = st.columns(4)
with h_col1:
    msg_count = len(st.session_state["copilot_chat_history"])
    st.metric("Messages", f"{msg_count}")
with h_col2:
    user_msgs = sum(1 for m in st.session_state["copilot_chat_history"] if m["role"] == "user")
    st.metric("Queries Sent", f"{user_msgs}")
with h_col3:
    st.metric("Knowledge Sources", "7")
with h_col4:
    status = "Active" if msg_count > 0 else "Ready"
    st.metric("Session Status", status)

# Action buttons
act_col1, act_col2 = st.columns(2)
with act_col1:
    if st.button("🧹 Clear Conversation", use_container_width=True):
        st.session_state["copilot_chat_history"] = []
        st.rerun()
with act_col2:
    if st.button("🔄 New Chat Session", use_container_width=True):
        st.session_state["copilot_chat_history"] = []
        st.rerun()

# ===========================================================
# SECTION 4: Knowledge Sources (compact row)
# ===========================================================

st.write("---")
st.markdown("### 🔗 Connected Knowledge Sources")

ks_col1, ks_col2, ks_col3, ks_col4, ks_col5, ks_col6, ks_col7 = st.columns(7)
with ks_col1:
    st.markdown("✅ **Warden**")
with ks_col2:
    st.markdown("✅ **Recommendations**")
with ks_col3:
    st.markdown("✅ **Analytics**")
with ks_col4:
    st.markdown("✅ **Calendar**")
with ks_col5:
    st.markdown("✅ **Vendors**")
with ks_col6:
    st.markdown("✅ **Materials**")
with ks_col7:
    st.markdown("✅ **Learning Engine**")

# ===========================================================
# SECTION 3: Suggested Questions
# ===========================================================

st.write("---")
st.markdown("### 💡 Suggested Questions")

suggested_prompts = [
    "Compare attendance across all properties",
    "Generate a monthly executive summary",
    "Which event category performs best?",
    "Show top 5 vendors by rating",
    "What is the current occupancy forecast?",
    "Analyse budget variance trends",
    "Recommend next month's calendar plan",
    "Which property has highest engagement?"
]

# Display in 2 rows of 4
row1_cols = st.columns(4)
row2_cols = st.columns(4)
clicked_prompt = None

for idx, prompt_text in enumerate(suggested_prompts[:4]):
    with row1_cols[idx]:
        if st.button(prompt_text, key=f"sugg_{idx}", use_container_width=True):
            clicked_prompt = prompt_text

for idx, prompt_text in enumerate(suggested_prompts[4:]):
    with row2_cols[idx]:
        if st.button(prompt_text, key=f"sugg_{idx+4}", use_container_width=True):
            clicked_prompt = prompt_text

# ===========================================================
# SECTION 5: Smart Actions
# ===========================================================

st.write("---")
st.markdown("### ⚡ Smart Actions")

sa_col1, sa_col2, sa_col3, sa_col4, sa_col5, sa_col6 = st.columns(6)
with sa_col1:
    st.page_link("pages/3_🎯_Recommendations.py", label="🎯 Recommendations", use_container_width=True)
with sa_col2:
    st.page_link("pages/8_📅_Community_Calendar.py", label="📅 Calendar", use_container_width=True)
with sa_col3:
    st.page_link("pages/5_📊_Analytics.py", label="📊 Analytics", use_container_width=True)
with sa_col4:
    st.page_link("pages/7_🏪_Vendor_Management.py", label="🏪 Vendors", use_container_width=True)
with sa_col5:
    st.page_link("pages/4_📝_Log_Event.py", label="📝 Log Event", use_container_width=True)
with sa_col6:
    st.page_link("pages/9_🗃️_Master_Data.py", label="🗃️ Master Data", use_container_width=True)

# ===========================================================
# SECTION 2 & 6: Conversation Workspace
# ===========================================================

st.write("---")
st.markdown("### 💬 Conversation")

# Render chat history
if not st.session_state["copilot_chat_history"]:
    st.markdown(
        "*No messages yet. Type a question below or click a suggested question to begin.*"
    )

for msg in st.session_state["copilot_chat_history"]:
    role_name = "You" if msg["role"] == "user" else "Copilot"

    with st.chat_message(msg["role"]):
        st.markdown(f"**{role_name}**")
        st.write(msg["content"])

        # Smart action tokens
        content = msg["content"]
        if "[ACTION: recommendations]" in content:
            st.page_link("pages/3_🎯_Recommendations.py", label="🎯 Launch Smart Recommendations", use_container_width=True)
        if "[ACTION: calendar]" in content:
            st.page_link("pages/8_📅_Community_Calendar.py", label="📅 Open Community Calendar", use_container_width=True)
        if "[ACTION: vendors]" in content:
            st.page_link("pages/7_🏪_Vendor_Management.py", label="🏪 Open Vendor Management", use_container_width=True)
        if "[ACTION: analytics]" in content:
            st.page_link("pages/5_📊_Analytics.py", label="📊 Open Analytics", use_container_width=True)

# Chat input
user_query = st.chat_input("Ask the TribeIQ Copilot...")

# Handle suggested prompt clicks
if clicked_prompt:
    user_query = clicked_prompt

if user_query:
    # 1. User Message
    st.session_state["copilot_chat_history"].append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.markdown("**You**")
        st.write(user_query)

    # 2. Copilot Response
    with st.chat_message("assistant"):
        st.markdown("**Copilot**")
        with st.spinner("AI Community Copilot is thinking..."):
            # Call orchestrator (unchanged)
            response = ask_copilot(user_query, st.session_state["copilot_chat_history"])

            # Simulated typing delay (unchanged)
            time.sleep(0.8)

            def stream_response(text):
                for word in text.split(" "):
                    yield word + " "
                    time.sleep(0.015)
            st.write_stream(stream_response(response))

            # Smart action tokens (unchanged)
            if "[ACTION: recommendations]" in response:
                st.page_link("pages/3_🎯_Recommendations.py", label="🎯 Launch Smart Recommendations", use_container_width=True)
            if "[ACTION: calendar]" in response:
                st.page_link("pages/8_📅_Community_Calendar.py", label="📅 Open Community Calendar", use_container_width=True)
            if "[ACTION: vendors]" in response:
                st.page_link("pages/7_🏪_Vendor_Management.py", label="🏪 Open Vendor Management", use_container_width=True)
            if "[ACTION: analytics]" in response:
                st.page_link("pages/5_📊_Analytics.py", label="📊 Open Analytics", use_container_width=True)

            st.session_state["copilot_chat_history"].append({"role": "assistant", "content": response})
            st.rerun()
